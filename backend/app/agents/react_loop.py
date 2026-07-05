"""Bounded ReAct loop for tool-using LLM agents."""

from __future__ import annotations

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool

from app.core.logging import get_logger
from app.llm import client as llm

logger = get_logger(__name__)

MAX_REACT_ITERATIONS = 6


def run_react_loop(
    *,
    system_prompt: str,
    user_prompt: str,
    tools: list[BaseTool],
    config: dict | None = None,
    max_iterations: int = MAX_REACT_ITERATIONS,
) -> str:
    """Run a ReAct loop until the model responds without tool calls or max iterations."""
    messages: list[BaseMessage] = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]
    model = llm.get_tool_chat_model(temperature=0.2).bind_tools(tools)
    tool_map = {tool.name: tool for tool in tools}

    for iteration in range(max_iterations):
        response = llm.invoke_with_tools(model, messages, config=config)
        if not isinstance(response, AIMessage):
            content = getattr(response, "content", str(response))
            return content if isinstance(content, str) else str(content)

        if not response.tool_calls:
            content = response.content
            return content.strip() if isinstance(content, str) else str(content).strip()

        messages.append(response)
        for call in response.tool_calls:
            tool_name = call.get("name", "")
            tool_args = call.get("args") or {}
            tool_id = call.get("id") or f"call_{iteration}_{tool_name}"
            tool = tool_map.get(tool_name)
            if tool is None:
                observation = f"Unknown tool: {tool_name}"
            else:
                try:
                    observation = tool.invoke(tool_args)
                except Exception as exc:  # pragma: no cover
                    logger.warning("Tool %s failed: %s", tool_name, exc)
                    observation = f"Tool error: {exc}"
            messages.append(ToolMessage(content=str(observation), tool_call_id=tool_id))

    logger.warning("ReAct loop hit max iterations (%s); requesting final summary.", max_iterations)
    messages.append(
        HumanMessage(
            content="Stop calling tools. Write the final 2-3 sentence officer summary now."
        )
    )
    final = llm.invoke_with_tools(model, messages, config=config)
    if isinstance(final, AIMessage):
        content = final.content
        if not final.tool_calls:
            return content.strip() if isinstance(content, str) else str(content).strip()
    return "Validation review completed; manual officer review advised."
