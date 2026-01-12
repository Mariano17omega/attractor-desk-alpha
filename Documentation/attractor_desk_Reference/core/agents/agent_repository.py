"""YAML-based agent configuration and repository."""

import logging
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional

import yaml

from ..models import Agent

logger = logging.getLogger(__name__)


DEFAULT_AGENT_YAML = """
name: Kurisu
description: Kurisu, a helpful AI assistant for general tasks
system_prompt: |
  You are an analytical and scientifically oriented agent inspired by 
  the personality of a rational and skeptical researcher. 
  Your responses must prioritize logic, evidence, and conceptual consistency, 
  questioning implicit assumptions and pointing out flaws or inconsistencies when 
  they exist. Explain your reasoning clearly and in a structured manner, 
  maintaining a direct, critical, and confident tone, with light irony only 
  when appropriate. Do not accept unsupported arguments, do not oversimplify 
  complex topics, and do not aim to please—the goal is to analyze, clarify, 
  and correct with intellectual rigor.

is_default: true
""".strip()


class AgentConfigLoader:
    """Loads and validates agent configurations from YAML files."""
    
    REQUIRED_FIELDS = {"name", "system_prompt"}
    
    @classmethod
    def load_from_file(cls, file_path: Path) -> Optional[Agent]:
        """Load an agent from a YAML file.
        
        Args:
            file_path: Path to the YAML file.
            
        Returns:
            Agent instance or None if loading fails.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            
            if not isinstance(data, dict):
                logger.warning(f"Invalid agent YAML format in {file_path}")
                return None
            
            # Validate required fields
            missing = cls.REQUIRED_FIELDS - set(data.keys())
            if missing:
                logger.warning(f"Missing required fields {missing} in {file_path}")
                return None
            
            return Agent(
                id=data.get("id", str(uuid.uuid4())),
                name=data["name"],
                description=data.get("description", ""),
                system_prompt=data["system_prompt"],

                is_default=data.get("is_default", False),
                created_at=datetime.now(),
            )
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error in {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error loading agent from {file_path}: {e}")
            return None
    
    @classmethod
    def load_from_string(cls, content: str) -> Optional[Agent]:
        """Load an agent from a YAML string.
        
        Args:
            content: YAML content as string.
            
        Returns:
            Agent instance or None if loading fails.
        """
        try:
            data = yaml.safe_load(content)
            
            if not isinstance(data, dict):
                return None
            
            missing = cls.REQUIRED_FIELDS - set(data.keys())
            if missing:
                return None
            
            return Agent(
                id=data.get("id", str(uuid.uuid4())),
                name=data["name"],
                description=data.get("description", ""),
                system_prompt=data["system_prompt"],

                is_default=data.get("is_default", False),
                created_at=datetime.now(),
            )
        except Exception:
            return None


class AgentRepository:
    """Repository for managing agent configurations from YAML files."""
    
    def __init__(
        self,
        agents_dir: Optional[Path] = None,
        on_agents_changed: Optional[Callable[[], None]] = None,
    ):
        """Initialize the agent repository.
        
        Args:
            agents_dir: Directory containing agent YAML files.
            on_agents_changed: Callback when agents are reloaded.
        """
        if agents_dir is None:
            agents_dir = Path.home() / ".attractor_desk" / "agents"
        
        self._agents_dir = agents_dir
        self._agents: Dict[str, Agent] = {}
        self._lock = threading.RLock()
        self._on_agents_changed = on_agents_changed
        self._watcher_running = False
        
        # Ensure directory exists
        self._agents_dir.mkdir(parents=True, exist_ok=True)
        
        # Initial load
        self._load_agents()
    
    def _load_agents(self) -> None:
        """Load all agents from the agents directory."""
        with self._lock:
            self._agents.clear()
            
            yaml_files = list(self._agents_dir.glob("*.yaml"))
            yaml_files.extend(self._agents_dir.glob("*.yml"))
            
            if not yaml_files:
                # Create default agent
                self._create_default_agent()
                yaml_files = list(self._agents_dir.glob("*.yaml"))
            
            for file_path in yaml_files:
                agent = AgentConfigLoader.load_from_file(file_path)
                if agent:
                    self._agents[agent.id] = agent
                    logger.debug(f"Loaded agent: {agent.name} ({agent.id})")
            
            logger.info(f"Loaded {len(self._agents)} agents")
    
    def _create_default_agent(self) -> None:
        """Create the default agent YAML file."""
        default_path = self._agents_dir / "default.yaml"
        try:
            with open(default_path, "w", encoding="utf-8") as f:
                f.write(DEFAULT_AGENT_YAML)
            logger.info(f"Created default agent at {default_path}")
        except Exception as e:
            logger.error(f"Failed to create default agent: {e}")
    
    def get_all(self) -> List[Agent]:
        """Get all available agents.
        
        Returns:
            List of all agents, sorted by name.
        """
        with self._lock:
            return sorted(self._agents.values(), key=lambda a: a.name)
    
    def get_by_id(self, agent_id: str) -> Optional[Agent]:
        """Get an agent by ID.
        
        Args:
            agent_id: The agent's unique identifier.
            
        Returns:
            The agent if found, None otherwise.
        """
        with self._lock:
            return self._agents.get(agent_id)
    
    def get_default(self) -> Optional[Agent]:
        """Get the default agent.
        
        Returns:
            The default agent, or the first available agent, or None.
        """
        with self._lock:
            # Find agent marked as default
            for agent in self._agents.values():
                if agent.is_default:
                    return agent
            
            # Fall back to first agent
            agents = self.get_all()
            return agents[0] if agents else None
    
    def reload(self) -> None:
        """Reload agents from configuration files."""
        self._load_agents()
        if self._on_agents_changed:
            self._on_agents_changed()
    
    def start_watching(self) -> None:
        """Start watching the agents directory for changes.
        
        Requires the watchdog library to be installed.
        """
        if self._watcher_running:
            return
        
        try:
            from watchdog.events import FileSystemEventHandler
            from watchdog.observers import Observer
            
            class AgentFileHandler(FileSystemEventHandler):
                def __init__(handler_self, repository: "AgentRepository"):
                    handler_self.repository = repository
                    handler_self._debounce_timer: Optional[threading.Timer] = None
                    handler_self._lock = threading.Lock()
                
                def _debounced_reload(handler_self) -> None:
                    with handler_self._lock:
                        if handler_self._debounce_timer:
                            handler_self._debounce_timer.cancel()
                        handler_self._debounce_timer = threading.Timer(
                            0.5, handler_self.repository.reload
                        )
                        handler_self._debounce_timer.start()
                
                def on_any_event(handler_self, event) -> None:
                    if event.src_path.endswith((".yaml", ".yml")):
                        handler_self._debounced_reload()
            
            self._observer = Observer()
            self._observer.schedule(
                AgentFileHandler(self),
                str(self._agents_dir),
                recursive=False,
            )
            self._observer.start()
            self._watcher_running = True
            logger.info(f"Started watching {self._agents_dir} for changes")
            
        except ImportError:
            logger.warning("watchdog not installed, hot reload disabled")
    
    def stop_watching(self) -> None:
        """Stop watching the agents directory."""
        if self._watcher_running and hasattr(self, "_observer"):
            self._observer.stop()
            self._observer.join()
            self._watcher_running = False
            logger.info("Stopped watching for agent changes")
