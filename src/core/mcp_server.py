from __future__ import annotations

from collections.abc import Callable, Coroutine, Sequence
from typing import Any

import structlog
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

logger = structlog.get_logger(__name__)

ToolHandler = Callable[[dict[str, Any]], Coroutine[Any, Any, Any]]


class MCPServerBase:
    """Convenience wrapper around the ``mcp`` SDK's :class:`Server`.

    Sub-classes register tools either declaratively via
    :meth:`register_tool` or by overriding :meth:`_register_tools`.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self.server = Server(name)
        self._tools: dict[str, Tool] = {}
        self._handlers: dict[str, ToolHandler] = {}
        self._log = logger.bind(mcp_server=name)
        self._setup_protocol()

    def _setup_protocol(self) -> None:
        @self.server.list_tools()
        async def _list_tools() -> list[Tool]:
            return list(self._tools.values())

        @self.server.call_tool()
        async def _call_tool(name: str, arguments: dict[str, Any] | None) -> Sequence[TextContent]:
            return await self._handle_call(name, arguments or {})

    def register_tool(
        self,
        name: str,
        description: str,
        input_schema: dict[str, Any],
        handler: ToolHandler,
    ) -> None:
        tool = Tool(name=name, description=description, inputSchema=input_schema)
        self._tools[name] = tool
        self._handlers[name] = handler
        self._log.info("tool.registered", tool=name)

    async def _handle_call(self, name: str, arguments: dict[str, Any]) -> Sequence[TextContent]:
        handler = self._handlers.get(name)
        if handler is None:
            self._log.error("tool.unknown", tool=name)
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

        self._log.info("tool.called", tool=name)
        try:
            result = await handler(arguments)
            text = result if isinstance(result, str) else str(result)
            return [TextContent(type="text", text=text)]
        except Exception as exc:
            self._log.error("tool.error", tool=name, error=str(exc))
            return [TextContent(type="text", text=f"Error: {exc}")]

    async def _register_tools(self) -> None:
        """Override in sub-classes to register tools at startup."""

    async def start(self) -> None:
        """Run the MCP server over stdio until the transport closes."""
        await self._register_tools()
        self._log.info("server.starting", tool_count=len(self._tools))

        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options(),
            )
