"""
Tests for ToolRegistry and tool-related behavior.
"""

import pytest

from living_entity.execution.tools import ToolRegistry, Tool, ToolResult


class TestToolRegistry:
    """Tests for ToolRegistry."""

    def test_get_tools_description_includes_all_tools(self):
        """get_tools_description() returns text that includes all registered tools."""
        reg = ToolRegistry()
        desc = reg.get_tools_description()
        assert "say_to_user" in desc
        assert "create_file" in desc
        assert "read_file" in desc
        assert "## Доступные инструменты" in desc

    def test_get_tools_description_filter_by_categories(self):
        """get_tools_description(categories=...) returns only tools from given categories."""
        reg = ToolRegistry()
        # Default tools: communication, filesystem, utility
        all_desc = reg.get_tools_description()
        filesystem_only = reg.get_tools_description(categories=["filesystem"])
        assert "say_to_user" in all_desc
        assert "create_file" in all_desc
        assert "get_time" in all_desc
        assert "create_file" in filesystem_only
        assert "read_file" in filesystem_only
        assert "say_to_user" not in filesystem_only
        assert "get_time" not in filesystem_only

    def test_get_tools_description_empty_categories_filter(self):
        """get_tools_description(categories=[...]) with non-matching list returns header only."""
        reg = ToolRegistry()
        desc = reg.get_tools_description(categories=["nonexistent_category"])
        assert "## Доступные инструменты" in desc
        assert "say_to_user" not in desc

    def test_register_and_execute_tool(self):
        """Register a custom tool and execute it."""
        reg = ToolRegistry()

        def add(a: int, b: int) -> int:
            return a + b

        reg.add_tool(
            add,
            name="add",
            description="Sum two numbers",
            parameters={"a": "First", "b": "Second"},
            returns="Sum",
            category="math",
        )
        result = reg.execute("add", a=2, b=3)
        assert result.success
        assert result.output == 5
        assert "add" in reg.get_tools_description(categories=["math"])

    def test_execute_unknown_tool_returns_failure(self):
        """Executing unknown tool returns ToolResult with success=False."""
        reg = ToolRegistry()
        result = reg.execute("nonexistent_tool", x=1)
        assert not result.success
        assert "not found" in (result.error or "").lower()
