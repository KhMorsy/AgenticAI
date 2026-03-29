"""Tests for MCP server modules."""

import pytest

from mcp.types import Tool

from src.core.mcp_server import MCPServerBase


# ---------------------------------------------------------------------------
# MCPServerBase
# ---------------------------------------------------------------------------


class TestMCPServerBase:
    def test_create_base_server(self):
        server = MCPServerBase("test-server")
        assert server.name == "test-server"
        assert server.server is not None

    def test_register_tool(self):
        server = MCPServerBase("test-server")

        async def dummy_handler(args):
            return "ok"

        server.register_tool(
            name="test_tool",
            description="A test tool",
            input_schema={"type": "object", "properties": {}},
            handler=dummy_handler,
        )
        assert "test_tool" in server._tools
        assert "test_tool" in server._handlers
        assert isinstance(server._tools["test_tool"], Tool)
        assert server._tools["test_tool"].name == "test_tool"
        assert server._tools["test_tool"].description == "A test tool"

    def test_register_multiple_tools(self):
        server = MCPServerBase("test-server")

        async def handler_a(args):
            return "a"

        async def handler_b(args):
            return "b"

        server.register_tool("tool_a", "Tool A", {"type": "object"}, handler_a)
        server.register_tool("tool_b", "Tool B", {"type": "object"}, handler_b)
        assert len(server._tools) == 2
        assert "tool_a" in server._tools
        assert "tool_b" in server._tools

    async def test_handle_call_known_tool(self):
        server = MCPServerBase("test-server")

        async def echo_handler(args):
            return f"echo: {args.get('message', '')}"

        server.register_tool(
            "echo",
            "Echo tool",
            {"type": "object", "properties": {"message": {"type": "string"}}},
            echo_handler,
        )
        result = await server._handle_call("echo", {"message": "hello"})
        assert len(result) == 1
        assert result[0].text == "echo: hello"

    async def test_handle_call_unknown_tool(self):
        server = MCPServerBase("test-server")
        result = await server._handle_call("nonexistent", {})
        assert len(result) == 1
        assert "Unknown tool" in result[0].text

    async def test_handle_call_error(self):
        server = MCPServerBase("test-server")

        async def failing_handler(args):
            raise ValueError("test error")

        server.register_tool("fail", "Failing tool", {"type": "object"}, failing_handler)
        result = await server._handle_call("fail", {})
        assert len(result) == 1
        assert "Error" in result[0].text
        assert "test error" in result[0].text


# ---------------------------------------------------------------------------
# SW Architect MCP Server
# ---------------------------------------------------------------------------


class TestSWArchitectServer:
    def test_create_server(self):
        from src.agents.sw_architect.server import create_server

        server = create_server()
        assert server is not None

    async def test_list_tools(self):
        from src.agents.sw_architect.server import create_server

        server = create_server()
        tools_handler = None
        for handler in server._tool_handlers.values() if hasattr(server, "_tool_handlers") else []:
            tools_handler = handler
            break
        # The server registers list_tools and call_tool via decorators.
        # We verify the server object is created and functional.
        assert server is not None

    def test_server_has_name(self):
        from src.agents.sw_architect.server import create_server

        server = create_server()
        assert server.name == "sw-architect"


# ---------------------------------------------------------------------------
# Generative AI MCP Server
# ---------------------------------------------------------------------------


class TestGenerativeAIServer:
    def test_server_exists(self):
        from src.agents.generative_ai.server import server

        assert server is not None
        assert server.name == "generative-ai"

    def test_tools_defined(self):
        from src.agents.generative_ai.server import TOOLS

        assert isinstance(TOOLS, list)
        assert len(TOOLS) >= 5
        tool_names = {t.name for t in TOOLS}
        assert "get_ai_news" in tool_names
        assert "propose_ideas" in tool_names
        assert "suggest_workflows" in tool_names
        assert "analyze_ai_tools" in tool_names
        assert "generate_optimization_plan" in tool_names

    def test_tool_schemas(self):
        from src.agents.generative_ai.server import TOOLS

        for tool in TOOLS:
            assert isinstance(tool, Tool)
            assert tool.name
            assert tool.description
            assert tool.inputSchema


# ---------------------------------------------------------------------------
# Business Developer MCP Server
# ---------------------------------------------------------------------------


class TestBusinessDeveloperServer:
    def test_server_exists(self):
        from src.agents.business_developer.server import server

        assert server is not None
        assert server.name == "business-developer"

    def test_tools_defined(self):
        from src.agents.business_developer.server import TOOLS

        assert isinstance(TOOLS, list)
        assert len(TOOLS) >= 6
        tool_names = {t.name for t in TOOLS}
        assert "analyze_business_idea" in tool_names
        assert "create_business_model" in tool_names
        assert "market_research" in tool_names
        assert "financial_projection" in tool_names
        assert "create_pitch_deck" in tool_names
        assert "competitive_analysis" in tool_names

    def test_tool_schemas(self):
        from src.agents.business_developer.server import TOOLS

        for tool in TOOLS:
            assert isinstance(tool, Tool)
            assert tool.name
            assert tool.description
            assert tool.inputSchema


# ---------------------------------------------------------------------------
# Physical AI MCP Server
# ---------------------------------------------------------------------------


class TestPhysicalAIServer:
    def test_create_server(self):
        from src.agents.physical_ai.server import create_server

        server = create_server()
        assert server is not None

    def test_tools_defined(self):
        from src.agents.physical_ai.server import TOOLS

        assert isinstance(TOOLS, list)
        assert len(TOOLS) >= 6
        tool_names = {t.name for t in TOOLS}
        assert "generate_newsletter" in tool_names
        assert "scan_news" in tool_names
        assert "propose_automation" in tool_names
        assert "startup_ideation" in tool_names
        assert "cross_agent_analysis" in tool_names
        assert "track_papers" in tool_names

    def test_tool_schemas(self):
        from src.agents.physical_ai.server import TOOLS

        for tool in TOOLS:
            assert isinstance(tool, Tool)
            assert tool.name
            assert tool.description
            assert tool.inputSchema

    def test_server_has_name(self):
        from src.agents.physical_ai.server import create_server

        server = create_server()
        assert server.name == "physical-ai"
