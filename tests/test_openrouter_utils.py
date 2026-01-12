"""Tests for OpenRouter LLM helper behavior."""

from __future__ import annotations

import json

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from pydantic import BaseModel

from core.llm.openrouter import OpenRouterChat


class DemoSchema(BaseModel):
    """Schema for tool testing."""

    foo: str


def test_convert_messages_includes_tool_calls() -> None:
    model = OpenRouterChat(api_key="test-key", model="openai/gpt-4o")
    messages = [
        SystemMessage(content="System"),
        HumanMessage(content="Hello"),
        AIMessage(content="Done", tool_calls=[{"id": "1", "name": "tool", "args": {"x": 1}}]),
        ToolMessage(content="ok", tool_call_id="1"),
    ]

    converted = model._convert_messages(messages)

    assert converted[0]["role"] == "system"
    assert converted[1]["role"] == "user"
    assert converted[2]["role"] == "assistant"
    assert converted[3]["role"] == "tool"

    tool_args = converted[2]["tool_calls"][0]["function"]["arguments"]
    assert json.loads(tool_args) == {"x": 1}


def test_build_request_body_temperature_exclusion() -> None:
    model = OpenRouterChat(api_key="test-key", model="openai/o1-mini", temperature=0.7)
    body = model._build_request_body([{"role": "user", "content": "hi"}], stream=True)

    assert body["model"] == "openai/o1-mini"
    assert body["stream"] is True
    assert "temperature" not in body


def test_build_request_body_includes_temperature_for_supported_models() -> None:
    model = OpenRouterChat(api_key="test-key", model="openai/gpt-4o", temperature=0.7)
    body = model._build_request_body([{"role": "user", "content": "hi"}], stream=False)

    assert body["temperature"] == 0.7


def test_bind_tools_formats_tool_choice() -> None:
    model = OpenRouterChat(api_key="test-key")
    bound = model.bind_tools(
        tools=[
            {
                "name": "do_thing",
                "description": "Do the thing",
                "schema": DemoSchema,
            }
        ],
        tool_choice="do_thing",
    )

    assert bound.tools
    tool = bound.tools[0]["function"]
    assert tool["name"] == "do_thing"
    assert "properties" in tool["parameters"]
    assert bound.tool_choice == {"type": "function", "function": {"name": "do_thing"}}


def test_with_structured_output_sets_tool_choice() -> None:
    model = OpenRouterChat(api_key="test-key")
    configured = model.with_structured_output(DemoSchema, name="structured_output")

    assert configured.streaming is False
    assert configured.tools[0]["function"]["name"] == "structured_output"
    assert configured.tool_choice == {
        "type": "function",
        "function": {"name": "structured_output"},
    }
