"""Memory and RAG command parser for @remember, @forget, and @RAG commands."""

import re
from dataclasses import dataclass
from typing import List, Literal, Optional, Tuple


@dataclass
class MemoryCommand:
    """A parsed memory command."""
    
    command_type: str  # "remember" or "forget"
    content: str  # The content to remember or phrase to forget


@dataclass
class RagCommand:
    """A parsed RAG command."""
    
    action: Literal["on", "off", "toggle"]


class MemoryCommandParser:
    """Parses and extracts memory commands from user input."""
    
    # Pattern for @remember command - captures everything after @remember until end or next command
    REMEMBER_PATTERN = re.compile(
        r"@remember\s+(.+?)(?=@(?:remember|forget|rag)|$)",
        re.IGNORECASE | re.DOTALL,
    )
    
    # Pattern for @forget command - captures everything after @forget until end or next command
    FORGET_PATTERN = re.compile(
        r"@forget\s+(.+?)(?=@(?:remember|forget|rag)|$)",
        re.IGNORECASE | re.DOTALL,
    )
    
    # Pattern for @RAG command - captures optional on/off parameter
    RAG_PATTERN = re.compile(
        r"@rag(?:\s+(on|off))?(?=\s|@|$)",
        re.IGNORECASE,
    )
    
    # Pattern to find and remove all memory commands
    COMMAND_PATTERN = re.compile(
        r"@(?:remember|forget)\s+.+?(?=@(?:remember|forget|rag)|$)",
        re.IGNORECASE | re.DOTALL,
    )
    
    # Pattern to find and remove RAG commands
    RAG_COMMAND_PATTERN = re.compile(
        r"@rag(?:\s+(?:on|off))?(?=\s|@|$)",
        re.IGNORECASE,
    )
    
    @classmethod
    def parse(cls, text: str) -> Tuple[str, List[MemoryCommand]]:
        """Parse user input for memory commands.
        
        Args:
            text: The user's input text.
            
        Returns:
            Tuple of (cleaned_text, list_of_commands).
            cleaned_text has all commands removed.
        """
        commands: List[MemoryCommand] = []
        
        # Extract @remember commands
        for match in cls.REMEMBER_PATTERN.finditer(text):
            content = match.group(1).strip()
            if content:
                commands.append(MemoryCommand(
                    command_type="remember",
                    content=content,
                ))
        
        # Extract @forget commands
        for match in cls.FORGET_PATTERN.finditer(text):
            content = match.group(1).strip()
            if content:
                commands.append(MemoryCommand(
                    command_type="forget",
                    content=content,
                ))
        
        # Remove all commands from the text (including RAG commands)
        cleaned = cls.COMMAND_PATTERN.sub("", text).strip()
        cleaned = cls.RAG_COMMAND_PATTERN.sub("", cleaned).strip()
        
        # Clean up multiple spaces and newlines
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        
        return cleaned, commands
    
    @classmethod
    def extract_rag_command(cls, text: str) -> Optional[RagCommand]:
        """Extract RAG command from text.
        
        Args:
            text: The user's input text.
            
        Returns:
            RagCommand if found, None otherwise.
        """
        match = cls.RAG_PATTERN.search(text)
        if match:
            param = match.group(1)
            if param:
                action = param.lower()
                return RagCommand(action=action)  # type: ignore
            else:
                return RagCommand(action="toggle")
        return None
    
    @classmethod
    def has_commands(cls, text: str) -> bool:
        """Check if text contains any memory commands.
        
        Args:
            text: The text to check.
            
        Returns:
            True if the text contains @remember or @forget commands.
        """
        return bool(cls.COMMAND_PATTERN.search(text))
    
    @classmethod
    def has_rag_command(cls, text: str) -> bool:
        """Check if text contains a RAG command.
        
        Args:
            text: The text to check.
            
        Returns:
            True if the text contains @RAG command.
        """
        return bool(cls.RAG_PATTERN.search(text))
