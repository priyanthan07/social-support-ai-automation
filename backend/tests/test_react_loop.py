"""ReAct loop unit tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage

from app.agents.react_loop import MAX_REACT_ITERATIONS, run_react_loop


def test_react_loop_stops_when_no_tool_calls():
    final_msg = AIMessage(content="Officer summary without tools.")
    with patch("app.agents.react_loop.llm") as mock_llm:
        mock_llm.get_tool_chat_model.return_value.bind_tools.return_value = "model"
        mock_llm.invoke_with_tools.return_value = final_msg

        result = run_react_loop(
            system_prompt="system",
            user_prompt="user",
            tools=[],
        )

    assert result == "Officer summary without tools."
    assert mock_llm.invoke_with_tools.call_count == 1


def test_react_loop_executes_tool_then_stops():
    tool = MagicMock()
    tool.name = "list_detected_flags"
    tool.invoke.return_value = "[]"

    tool_call_msg = AIMessage(
        content="",
        tool_calls=[{"name": "list_detected_flags", "args": {}, "id": "call-1"}],
    )
    final_msg = AIMessage(content="Summary after tool use.")

    with patch("app.agents.react_loop.llm") as mock_llm:
        mock_llm.get_tool_chat_model.return_value.bind_tools.return_value = "model"
        mock_llm.invoke_with_tools.side_effect = [tool_call_msg, final_msg]

        result = run_react_loop(
            system_prompt="system",
            user_prompt="user",
            tools=[tool],
        )

    assert result == "Summary after tool use."
    tool.invoke.assert_called_once_with({})
    assert mock_llm.invoke_with_tools.call_count == 2


def test_react_loop_max_iterations_fallback():
    tool_call_msg = AIMessage(
        content="",
        tool_calls=[{"name": "list_detected_flags", "args": {}, "id": "call-1"}],
    )
    final_msg = AIMessage(content="Forced final summary.")

    with patch("app.agents.react_loop.llm") as mock_llm:
        mock_llm.get_tool_chat_model.return_value.bind_tools.return_value = "model"
        mock_llm.invoke_with_tools.side_effect = [tool_call_msg] * MAX_REACT_ITERATIONS + [
            final_msg
        ]

        tool = MagicMock()
        tool.name = "list_detected_flags"
        tool.invoke.return_value = "[]"

        result = run_react_loop(
            system_prompt="system",
            user_prompt="user",
            tools=[tool],
            max_iterations=MAX_REACT_ITERATIONS,
        )

    assert result == "Forced final summary."
    assert mock_llm.invoke_with_tools.call_count == MAX_REACT_ITERATIONS + 1
