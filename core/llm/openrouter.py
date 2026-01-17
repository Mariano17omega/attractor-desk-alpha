"""
OpenRouter LLM wrapper for Open Canvas.
Provides a unified interface for all LLM providers via OpenRouter.
"""

import json
from typing import Any, AsyncIterator, Iterator, Optional, Union

import httpx
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from pydantic import Field

from core.config import get_openrouter_api_key
from core.constants import DEFAULT_MODEL, TEMPERATURE_EXCLUDED_MODELS


OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterChat(BaseChatModel):
    """
    Chat model that uses OpenRouter as a unified LLM gateway.
    
    Supports all models available through OpenRouter with a single API key.
    """
    
    model: str = Field(default=DEFAULT_MODEL)
    temperature: float = Field(default=0.5)
    max_tokens: Optional[int] = Field(default=4096)
    timeout: float = Field(default=120.0)
    api_key: Optional[str] = Field(default=None)
    streaming: bool = Field(default=True)
    
    # Tool calling support
    tools: Optional[list[dict[str, Any]]] = Field(default=None)
    tool_choice: Optional[Union[str, dict[str, Any]]] = Field(default=None)
    
    class Config:
        arbitrary_types_allowed = True
    
    @property
    def _llm_type(self) -> str:
        return "openrouter"
    
    @property
    def _identifying_params(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
    
    def _get_api_key(self) -> str:
        """Get the API key, using instance key or global config."""
        if self.api_key:
            return self.api_key
        return get_openrouter_api_key()
    
    def _convert_messages(self, messages: list[BaseMessage]) -> list[dict[str, Any]]:
        """Convert LangChain messages to OpenRouter format."""
        converted = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                converted.append({"role": "system", "content": msg.content})
            elif isinstance(msg, HumanMessage):
                converted.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                message_dict: dict[str, Any] = {"role": "assistant", "content": msg.content}
                if msg.tool_calls:
                    message_dict["tool_calls"] = [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": json.dumps(tc["args"]),
                            },
                        }
                        for tc in msg.tool_calls
                    ]
                converted.append(message_dict)
            elif isinstance(msg, ToolMessage):
                converted.append({
                    "role": "tool",
                    "tool_call_id": msg.tool_call_id,
                    "content": msg.content,
                })
            else:
                # Generic fallback
                converted.append({"role": "user", "content": str(msg.content)})
        return converted
    
    def _build_request_body(
        self,
        messages: list[dict[str, Any]],
        stream: bool = False,
    ) -> dict[str, Any]:
        """Build the request body for OpenRouter API."""
        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
        }
        
        # Only include temperature for models that support it
        model_name = self.model.split("/")[-1] if "/" in self.model else self.model
        if model_name not in TEMPERATURE_EXCLUDED_MODELS:
            body["temperature"] = self.temperature
        
        if self.max_tokens:
            body["max_tokens"] = self.max_tokens
        
        if self.tools:
            body["tools"] = self.tools
            if self.tool_choice:
                body["tool_choice"] = self.tool_choice
        
        return body
    
    def _generate(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Generate a response from the model."""
        converted_messages = self._convert_messages(messages)
        body = self._build_request_body(converted_messages, stream=False)
        
        if stop:
            body["stop"] = stop
        
        headers = {
            "Authorization": f"Bearer {self._get_api_key()}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://attractor-desk.local",
            "X-Title": "Attractor Desk",
        }
        
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(OPENROUTER_API_URL, json=body, headers=headers)
            response.raise_for_status()
            data = response.json()
        
        choice = data["choices"][0]
        message = choice["message"]
        
        # Parse tool calls if present
        tool_calls = []
        if "tool_calls" in message and message["tool_calls"]:
            for tc in message["tool_calls"]:
                try:
                    args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError as e:
                    # Handle malformed JSON from LLM - try to salvage what we can
                    raw_args = tc["function"]["arguments"]
                    # Log the error for debugging
                    import logging
                    logging.warning(
                        f"Failed to parse tool call arguments as JSON: {e}. "
                        f"Raw arguments: {raw_args[:200]}..."
                    )
                    # Try basic cleanup: fix unescaped newlines and quotes
                    try:
                        cleaned = raw_args.replace('\n', '\\n').replace('\r', '\\r')
                        args = json.loads(cleaned)
                    except json.JSONDecodeError:
                        # Last resort: return empty dict - caller should handle gracefully
                        args = {}
                tool_calls.append({
                    "id": tc["id"],
                    "name": tc["function"]["name"],
                    "args": args,
                })
        
        ai_message = AIMessage(
            content=message.get("content", ""),
            tool_calls=tool_calls,
        )
        
        generation = ChatGeneration(message=ai_message)
        return ChatResult(generations=[generation])
    
    def _stream(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        """Stream response chunks from the model."""
        converted_messages = self._convert_messages(messages)
        body = self._build_request_body(converted_messages, stream=True)
        
        if stop:
            body["stop"] = stop
        
        headers = {
            "Authorization": f"Bearer {self._get_api_key()}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://attractor-desk.local",
            "X-Title": "Attractor Desk",
        }
        
        with httpx.Client(timeout=self.timeout) as client:
            with client.stream("POST", OPENROUTER_API_URL, json=body, headers=headers) as response:
                response.raise_for_status()
                
                for line in response.iter_lines():
                    if not line or line.startswith(":"):
                        continue
                    
                    if line.startswith("data: "):
                        line = line[6:]
                    
                    if line == "[DONE]":
                        break
                    
                    try:
                        data = json.loads(line)
                        if "choices" in data and data["choices"]:
                            delta = data["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            
                            if content:
                                chunk = ChatGenerationChunk(
                                    message=AIMessageChunk(content=content)
                                )
                                if run_manager:
                                    run_manager.on_llm_new_token(content)
                                yield chunk
                    except json.JSONDecodeError:
                        continue
    
    def bind_tools(
        self,
        tools: list[dict[str, Any]],
        tool_choice: Optional[Union[str, dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> "OpenRouterChat":
        """Bind tools to the model for tool calling."""
        # Convert to OpenRouter tool format
        openrouter_tools = []
        for tool in tools:
            if "schema" in tool:
                # LangChain style tool definition
                openrouter_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": tool["schema"].model_json_schema() 
                            if hasattr(tool["schema"], "model_json_schema")
                            else tool["schema"],
                    },
                })
            else:
                # Already in OpenAI/OpenRouter format
                openrouter_tools.append(tool)
        
        # Convert tool_choice if it's a string tool name
        formatted_tool_choice = tool_choice
        if isinstance(tool_choice, str) and tool_choice not in ("auto", "none", "required"):
            formatted_tool_choice = {"type": "function", "function": {"name": tool_choice}}
        
        return OpenRouterChat(
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            timeout=self.timeout,
            api_key=self.api_key,
            streaming=self.streaming,
            tools=openrouter_tools,
            tool_choice=formatted_tool_choice,
        )
    
    def with_structured_output(
        self,
        schema: Any,
        method: str = "function_calling",
        **kwargs: Any,
    ) -> "OpenRouterChat":
        """Configure the model for structured output."""
        tool = {
            "type": "function",
            "function": {
                "name": kwargs.get("name", "structured_output"),
                "description": schema.__doc__ or "Generate structured output",
                "parameters": schema.model_json_schema()
                    if hasattr(schema, "model_json_schema")
                    else schema,
            },
        }
        
        return OpenRouterChat(
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            timeout=self.timeout,
            api_key=self.api_key,
            streaming=False,  # Structured output typically doesn't stream
            tools=[tool],
            tool_choice={"type": "function", "function": {"name": tool["function"]["name"]}},
        )


def get_chat_model(
    model: str = DEFAULT_MODEL,
    temperature: float = 0.5,
    max_tokens: Optional[int] = 4096,
    streaming: bool = True,
    **kwargs: Any,
) -> OpenRouterChat:
    """
    Get a configured chat model instance.
    
    Args:
        model: Model identifier (e.g., "anthropic/claude-3.5-sonnet")
        temperature: Sampling temperature (0-1)
        max_tokens: Maximum tokens to generate
        streaming: Whether to enable streaming
        **kwargs: Additional arguments passed to OpenRouterChat
        
    Returns:
        Configured OpenRouterChat instance
    """
    return OpenRouterChat(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        streaming=streaming,
        **kwargs,
    )
