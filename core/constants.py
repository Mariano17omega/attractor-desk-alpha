"""
Constants for Open Canvas.
Matches the original TypeScript constants.
"""

from core.types import ProgrammingLanguageOptions


# ----- Message Keys -----

OC_SUMMARIZED_MESSAGE_KEY = "__oc_summarized_message"
OC_HIDE_FROM_UI_KEY = "__oc_hide_from_ui"
OC_WEB_SEARCH_RESULTS_MESSAGE_KEY = "__oc_web_search_results_message"


# ----- Namespaces -----

CONTEXT_DOCUMENTS_NAMESPACE = ["context_documents"]


# ----- Default Inputs -----

DEFAULT_INPUTS = {
    "highlighted_code": None,
    "highlighted_text": None,
    "next": None,
    "language": None,
    "artifact_length": None,
    "regenerate_with_emojis": None,
    "reading_level": None,
    "add_comments": None,
    "add_logs": None,
    "fix_bugs": None,
    "port_language": None,
    "custom_quick_action_id": None,
    "web_search_enabled": None,
    "web_search_results": None,
}


# ----- Programming Languages -----

PROGRAMMING_LANGUAGES = [
    {"language": ProgrammingLanguageOptions.TYPESCRIPT, "label": "TypeScript"},
    {"language": ProgrammingLanguageOptions.JAVASCRIPT, "label": "JavaScript"},
    {"language": ProgrammingLanguageOptions.CPP, "label": "C++"},
    {"language": ProgrammingLanguageOptions.JAVA, "label": "Java"},
    {"language": ProgrammingLanguageOptions.PHP, "label": "PHP"},
    {"language": ProgrammingLanguageOptions.PYTHON, "label": "Python"},
    {"language": ProgrammingLanguageOptions.HTML, "label": "HTML"},
    {"language": ProgrammingLanguageOptions.SQL, "label": "SQL"},
    {"language": ProgrammingLanguageOptions.JSON, "label": "JSON"},
    {"language": ProgrammingLanguageOptions.RUST, "label": "Rust"},
    {"language": ProgrammingLanguageOptions.XML, "label": "XML"},
    {"language": ProgrammingLanguageOptions.CLOJURE, "label": "Clojure"},
    {"language": ProgrammingLanguageOptions.CSHARP, "label": "C#"},
    {"language": ProgrammingLanguageOptions.OTHER, "label": "Other"},
]


# ----- Character/Token Limits -----

# ~4 chars per token, max tokens of 75000. 75000 * 4 = 300000
CHARACTER_MAX = 300000


# ----- Models -----

# Models which do NOT support the temperature parameter
TEMPERATURE_EXCLUDED_MODELS = [
    "o1-mini",
    "o3-mini",
    "o1",
    "o4-mini",
]

# Models which do NOT stream back tool calls
NON_STREAMING_TOOL_CALLING_MODELS = [
    "gemini-2.0-flash-exp",
    "gemini-1.5-flash",
    "gemini-2.5-pro-preview-05-06",
    "gemini-2.5-flash-preview-05-20",
]

# Models which do NOT stream back text
NON_STREAMING_TEXT_MODELS = [
    "o1",
    "gemini-2.0-flash-thinking-exp-01-21",
]

# Models which perform CoT before generating a final response
THINKING_MODELS = [
    "accounts/fireworks/models/deepseek-r1",
    "groq/deepseek-r1-distill-llama-70b",
]

# Default model for OpenRouter
DEFAULT_MODEL = "anthropic/claude-3.5-sonnet"

# Default embeddings model for OpenRouter
DEFAULT_EMBEDDING_MODEL = "openai/text-embedding-3-small"
