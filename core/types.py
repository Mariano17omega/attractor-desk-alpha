"""
Type definitions for Open Canvas.
All types are Pydantic models matching the original TypeScript types.
"""

from enum import Enum
from typing import Any, Literal, Optional, Union
from pydantic import BaseModel, Field


# ----- Enums -----

class ArtifactType(str, Enum):
    """Type of artifact content."""
    CODE = "code"
    TEXT = "text"


class LanguageOptions(str, Enum):
    """Supported natural languages."""
    ENGLISH = "english"
    MANDARIN = "mandarin"
    SPANISH = "spanish"
    FRENCH = "french"
    HINDI = "hindi"


class ProgrammingLanguageOptions(str, Enum):
    """Supported programming languages."""
    TYPESCRIPT = "typescript"
    JAVASCRIPT = "javascript"
    CPP = "cpp"
    JAVA = "java"
    PHP = "php"
    PYTHON = "python"
    HTML = "html"
    SQL = "sql"
    JSON = "json"
    RUST = "rust"
    XML = "xml"
    CLOJURE = "clojure"
    CSHARP = "csharp"
    OTHER = "other"


class ReadingLevelOptions(str, Enum):
    """Reading level options for text artifacts."""
    PIRATE = "pirate"
    CHILD = "child"
    TEENAGER = "teenager"
    COLLEGE = "college"
    PHD = "phd"


class ArtifactLengthOptions(str, Enum):
    """Length options for artifacts."""
    SHORTEST = "shortest"
    SHORT = "short"
    LONG = "long"
    LONGEST = "longest"


# ----- Code Highlight -----

class CodeHighlight(BaseModel):
    """Highlighted code range in an artifact."""
    start_char_index: int = Field(alias="startCharIndex")
    end_char_index: int = Field(alias="endCharIndex")

    class Config:
        populate_by_name = True


# ----- Text Highlight -----

class TextHighlight(BaseModel):
    """Highlighted text in an artifact."""
    full_markdown: str = Field(alias="fullMarkdown")
    markdown_block: str = Field(alias="markdownBlock")
    selected_text: str = Field(alias="selectedText")

    class Config:
        populate_by_name = True


# ----- Artifact Content Types -----

class ArtifactMarkdownV3(BaseModel):
    """Markdown/text artifact content."""
    index: int
    type: Literal["text"] = "text"
    title: str
    full_markdown: str = Field(alias="fullMarkdown")

    class Config:
        populate_by_name = True


class ArtifactCodeV3(BaseModel):
    """Code artifact content."""
    index: int
    type: Literal["code"] = "code"
    title: str
    language: ProgrammingLanguageOptions
    code: str

    class Config:
        populate_by_name = True


ArtifactContent = Union[ArtifactMarkdownV3, ArtifactCodeV3]


class ArtifactV3(BaseModel):
    """Main artifact container with version history."""
    current_index: int = Field(alias="currentIndex")
    contents: list[ArtifactContent]

    class Config:
        populate_by_name = True


# ----- Reflections (Memory) -----

class Reflections(BaseModel):
    """User reflections/memories stored by the system."""
    style_rules: list[str] = Field(
        default_factory=list,
        alias="styleRules",
        description="Style rules to follow for generating content."
    )
    content: list[str] = Field(
        default_factory=list,
        description="Key content to remember about the user."
    )

    class Config:
        populate_by_name = True


# ----- Custom Quick Action -----

class CustomQuickAction(BaseModel):
    """User-defined quick action."""
    id: str = Field(description="UUID for the quick action.")
    title: str = Field(description="Title displayed in UI.")
    prompt: str = Field(description="Prompt to use when invoked.")
    include_reflections: bool = Field(
        default=False,
        alias="includeReflections",
        description="Whether to include user reflections."
    )
    include_prefix: bool = Field(
        default=False,
        alias="includePrefix",
        description="Whether to include default prefix."
    )
    include_recent_history: bool = Field(
        default=False,
        alias="includeRecentHistory",
        description="Whether to include last 5 messages."
    )

    class Config:
        populate_by_name = True


# ----- Search Results -----

class ExaMetadata(BaseModel):
    """Metadata from Exa search results."""
    id: str
    url: str
    title: str
    author: str = ""
    published_date: str = Field(default="", alias="publishedDate")
    image: Optional[str] = None
    favicon: Optional[str] = None

    class Config:
        populate_by_name = True


class SearchResult(BaseModel):
    """Search result from web search."""
    page_content: str = Field(alias="pageContent")
    metadata: ExaMetadata

    class Config:
        populate_by_name = True


# ----- Context Documents -----

class ContextDocument(BaseModel):
    """Document provided as context."""
    name: str
    type: str
    data: str = Field(description="Base64 encoded content or plain text.")
    metadata: Optional[dict[str, Any]] = None


# ----- Graph Input -----

class GraphInput(BaseModel):
    """Input to the main Open Canvas graph."""
    messages: Optional[list[dict[str, Any]]] = None
    
    highlighted_code: Optional[CodeHighlight] = Field(
        default=None, alias="highlightedCode"
    )
    highlighted_text: Optional[TextHighlight] = Field(
        default=None, alias="highlightedText"
    )
    
    artifact: Optional[ArtifactV3] = None
    next: Optional[str] = None
    
    language: Optional[LanguageOptions] = None
    artifact_length: Optional[ArtifactLengthOptions] = Field(
        default=None, alias="artifactLength"
    )
    regenerate_with_emojis: Optional[bool] = Field(
        default=None, alias="regenerateWithEmojis"
    )
    reading_level: Optional[ReadingLevelOptions] = Field(
        default=None, alias="readingLevel"
    )
    
    add_comments: Optional[bool] = Field(default=None, alias="addComments")
    add_logs: Optional[bool] = Field(default=None, alias="addLogs")
    port_language: Optional[ProgrammingLanguageOptions] = Field(
        default=None, alias="portLanguage"
    )
    fix_bugs: Optional[bool] = Field(default=None, alias="fixBugs")
    custom_quick_action_id: Optional[str] = Field(
        default=None, alias="customQuickActionId"
    )
    
    web_search_enabled: Optional[bool] = Field(
        default=None, alias="webSearchEnabled"
    )
    web_search_results: Optional[list[SearchResult]] = Field(
        default=None, alias="webSearchResults"
    )

    class Config:
        populate_by_name = True


# ----- Model Configuration -----

class TemperatureRange(BaseModel):
    """Temperature configuration for a model."""
    min: float = 0
    max: float = 1
    default: float = 0.5
    current: float = 0.5


class MaxTokensRange(BaseModel):
    """Max tokens configuration for a model."""
    min: int = 1
    max: int = 4096
    default: int = 4096
    current: int = 4096


class CustomModelConfig(BaseModel):
    """Configuration for a custom model."""
    provider: str
    temperature_range: TemperatureRange = Field(alias="temperatureRange")
    max_tokens: MaxTokensRange = Field(alias="maxTokens")

    class Config:
        populate_by_name = True


class ModelConfigurationParams(BaseModel):
    """Model configuration parameters."""
    name: str
    label: str
    model_name: Optional[str] = Field(default=None, alias="modelName")
    config: CustomModelConfig
    is_new: bool = Field(default=False, alias="isNew")

    class Config:
        populate_by_name = True
