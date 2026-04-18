from __future__ import annotations


def wrap_user_input(text: str) -> str:
    return f"<user_input>\n{text}\n</user_input>"


def wrap_tool_result(text: str) -> str:
    return f"<tool_result>\n{text}\n</tool_result>"
