"""GraphWorker QThread for async LangGraph execution."""

import asyncio
import logging
from typing import Any

from PySide6.QtCore import QThread, Signal

from core.graphs.open_canvas import graph

logger = logging.getLogger(__name__)


class GraphWorker(QThread):
    """Worker thread for running the graph asynchronously.

    This worker creates its own asyncio event loop and runs the LangGraph
    graph asynchronously. It properly cleans up database connections after
    execution to prevent thread-local connection leaks.

    Signals:
        finished: Emitted when graph execution completes successfully (result, run_token)
        error: Emitted when graph execution fails (error_message, run_token)
    """

    finished = Signal(dict, str)  # result, run_token
    error = Signal(str, str)      # error, run_token

    def __init__(self, state: dict[str, Any], config: dict[str, Any], run_token: str):
        """Initialize the graph worker.

        Args:
            state: The initial state for the graph
            config: The configuration for the graph execution
            run_token: A unique token to identify this execution run
        """
        super().__init__()
        self.state = state
        self.config = config
        self.run_token = run_token

    def run(self):
        """Run the graph in the worker thread.

        This method:
        1. Creates a new asyncio event loop
        2. Executes the graph asynchronously
        3. Emits the result or error
        4. Cleans up database connections
        """
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            result = loop.run_until_complete(
                graph.ainvoke(self.state, self.config)
            )

            loop.close()
            self.finished.emit(result, self.run_token)
        except Exception as e:
            logger.exception("Graph execution failed: %s", e)
            self.error.emit(str(e), self.run_token)
        finally:
            # Explicitly close thread-local database connections
            # This prevents connection leaks when worker threads terminate
            from core.persistence import Database
            db = Database()
            db.close()
