"""Утилиты для MCP инструментов создания рекламной отчетности."""

from typing import Dict, Any, Sequence
from dataclasses import dataclass

from mcp.types import TextContent

try:
    from fastmcp import ToolResult
except ImportError:
    @dataclass
    class ToolResult:
        """Обёртка для ToolResult если он не доступен в fastmcp."""
        content: Sequence[TextContent]
        structured_content: Dict[str, Any] | None = None
        meta: Dict[str, Any] | None = None