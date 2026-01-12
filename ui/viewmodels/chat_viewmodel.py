"""
Chat ViewModel for Open Canvas.
Bridges the UI with the Core graph execution.
"""

import asyncio
from typing import Optional
from uuid import uuid4

from PySide6.QtCore import QObject, Signal, Slot, QThread

from langchain_core.messages import HumanMessage, AIMessage

from core.types import ArtifactV3
from core.graphs.open_canvas import graph
from core.store import get_store


class GraphWorker(QThread):
    """Worker thread for running the graph asynchronously."""
    
    finished = Signal(dict)
    error = Signal(str)
    
    def __init__(self, state: dict, config: dict):
        super().__init__()
        self.state = state
        self.config = config
    
    def run(self):
        """Run the graph in the worker thread."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(
                graph.ainvoke(self.state, self.config)
            )
            
            loop.close()
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class ChatViewModel(QObject):
    """
    ViewModel for the chat interface.
    
    Manages conversation state and artifact interactions.
    """
    
    # Signals
    message_added = Signal(str, bool)  # content, is_user
    artifact_changed = Signal()
    is_loading_changed = Signal(bool)
    status_changed = Signal(str)
    error_occurred = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._messages: list = []
        self._artifact: Optional[ArtifactV3] = None
        self._is_loading: bool = False
        self._assistant_id: str = str(uuid4())
        
        self._worker: Optional[GraphWorker] = None
        
        # Settings with defaults
        self._settings: dict = {
            "model": "anthropic/claude-3.5-sonnet",
            "temperature": 0.5,
            "max_tokens": 4096,
            "streaming": True,
            "timeout": 120,
        }
    
    def set_settings(self, settings: dict):
        """Update the settings."""
        self._settings.update(settings)
    
    @property
    def messages(self) -> list:
        """Get the current message list."""
        return self._messages
    
    @property
    def current_artifact(self) -> Optional[ArtifactV3]:
        """Get the current artifact."""
        return self._artifact
    
    @property
    def is_loading(self) -> bool:
        """Check if currently loading."""
        return self._is_loading
    
    def _set_loading(self, loading: bool):
        """Set loading state."""
        self._is_loading = loading
        self.is_loading_changed.emit(loading)
    
    @Slot(str)
    def send_message(self, content: str):
        """
        Send a user message and run the graph.
        
        Args:
            content: The user's message content
        """
        if self._is_loading:
            return
        
        # Add user message
        user_message = HumanMessage(content=content)
        self._messages.append(user_message)
        self.message_added.emit(content, True)
        
        # Start loading
        self._set_loading(True)
        self.status_changed.emit("Processing...")
        
        # Prepare state
        state = {
            "messages": self._messages.copy(),
            "internal_messages": self._messages.copy(),
        }
        
        if self._artifact:
            state["artifact"] = self._artifact
        
        config = {
            "configurable": {
                "assistant_id": self._assistant_id,
                "model": self._settings.get("model", "anthropic/claude-3.5-sonnet"),
                "temperature": self._settings.get("temperature", 0.5),
                "max_tokens": self._settings.get("max_tokens", 4096),
            }
        }
        
        # Run in worker thread
        self._worker = GraphWorker(state, config)
        self._worker.finished.connect(self._on_graph_finished)
        self._worker.error.connect(self._on_graph_error)
        self._worker.start()
    
    def _on_graph_finished(self, result: dict):
        """Handle successful graph execution."""
        self._set_loading(False)
        self.status_changed.emit("Ready")
        
        # Debug: Print result keys
        print(f"[DEBUG] Graph result keys: {list(result.keys())}")
        
        # Update artifact first
        if "artifact" in result and result["artifact"]:
            print(f"[DEBUG] Artifact found in result: {type(result['artifact'])}")
            self._artifact = result["artifact"]
            self.artifact_changed.emit()
            print(f"[DEBUG] Artifact emitted with {len(self._artifact.contents)} contents")
        else:
            print(f"[DEBUG] No artifact in result. 'artifact' key exists: {'artifact' in result}")
        
        # Update messages with error handling
        if "messages" in result:
            new_messages = result["messages"]
            print(f"[DEBUG] Messages in result: {len(new_messages)}")
            for msg in new_messages:
                try:
                    # Skip if already in our list
                    if msg in self._messages:
                        continue
                    
                    if isinstance(msg, AIMessage):
                        content = msg.content if isinstance(msg.content, str) else str(msg.content)
                        if content:
                            self._messages.append(msg)
                            self.message_added.emit(content, False)
                except Exception as e:
                    print(f"[DEBUG] Error processing message: {e}")
    
    def _on_graph_error(self, error: str):
        """Handle graph execution error."""
        self._set_loading(False)
        self.status_changed.emit("Error")
        self.error_occurred.emit(error)
        
        # Add error message to chat
        self.message_added.emit(f"Error: {error}", False)
    
    @Slot()
    def prev_artifact_version(self):
        """Navigate to previous artifact version."""
        if not self._artifact:
            return
        
        if self._artifact.current_index > 1:
            self._artifact.current_index -= 1
            self.artifact_changed.emit()
    
    @Slot()
    def next_artifact_version(self):
        """Navigate to next artifact version."""
        if not self._artifact:
            return
        
        if self._artifact.current_index < len(self._artifact.contents):
            self._artifact.current_index += 1
            self.artifact_changed.emit()
    
    @Slot()
    def clear_conversation(self):
        """Clear the conversation history."""
        self._messages.clear()
        self._artifact = None
        self.artifact_changed.emit()
