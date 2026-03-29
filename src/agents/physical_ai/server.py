from __future__ import annotations

import asyncio
import json
from typing import Any

import structlog
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .agent import PhysicalAIAgent

logger = structlog.get_logger(__name__)

TOOLS: list[Tool] = [
    Tool(
        name="generate_newsletter",
        description=(
            "Generate a daily Physical AI newsletter. Scrapes latest news, research papers, "
            "and industry updates, then compiles them into a formatted newsletter."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "topics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of topics to cover in the newsletter (e.g., 'humanoid robots', 'sim-to-real')",
                },
            },
            "required": ["topics"],
        },
    ),
    Tool(
        name="scan_news",
        description=(
            "Scan the internet for the latest Physical AI, robotics, and embodied AI news. "
            "Returns ranked news items from multiple sources."
        ),
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
    Tool(
        name="propose_automation",
        description=(
            "Propose automation ideas for given work routines using Physical AI and robotics. "
            "Suggests technologies, implementation steps, and related products."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "routines": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of work routines to automate (e.g., 'warehouse picking')",
                },
            },
            "required": ["routines"],
        },
    ),
    Tool(
        name="startup_ideation",
        description=(
            "Generate a startup plan in the Physical AI space for a given domain. "
            "Includes problem statement, solution, market analysis, and milestones."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "The domain or industry vertical for the startup (e.g., 'agriculture')",
                },
            },
            "required": ["domain"],
        },
    ),
    Tool(
        name="cross_agent_analysis",
        description=(
            "Perform a comprehensive cross-agent analysis on a topic, leveraging perspectives "
            "from all agents: technical, market, AI, business, and Physical AI."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "The topic to analyze across all agent perspectives",
                },
            },
            "required": ["topic"],
        },
    ),
    Tool(
        name="track_papers",
        description=(
            "Track the latest research papers from ArXiv related to Physical AI, robotics, "
            "and embodied AI. Filter by keywords."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Keywords to search for in research papers (e.g., 'robot learning')",
                },
            },
            "required": ["keywords"],
        },
    ),
]


def _serialize(obj: Any) -> str:
    return json.dumps(obj.model_dump(mode="json") if hasattr(obj, "model_dump") else obj, indent=2, default=str)


async def _handle_tool_call(agent: PhysicalAIAgent, name: str, arguments: dict[str, Any]) -> str:
    match name:
        case "generate_newsletter":
            result = await agent.generate_daily_newsletter(arguments["topics"])
            return _serialize(result)
        case "scan_news":
            results = await agent.scan_physical_ai_news()
            return json.dumps([r.model_dump(mode="json") for r in results], indent=2, default=str)
        case "propose_automation":
            results = await agent.propose_automation_ideas(arguments["routines"])
            return json.dumps([r.model_dump(mode="json") for r in results], indent=2, default=str)
        case "startup_ideation":
            result = await agent.startup_ideation(arguments["domain"])
            return _serialize(result)
        case "cross_agent_analysis":
            result = await agent.cross_agent_analysis(arguments["topic"])
            return _serialize(result)
        case "track_papers":
            results = await agent.track_research_papers(arguments["keywords"])
            return json.dumps([r.model_dump(mode="json") for r in results], indent=2, default=str)
        case _:
            raise ValueError(f"Unknown tool: {name}")


def create_server() -> Server:
    server = Server("physical-ai")
    agent = PhysicalAIAgent()

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return TOOLS

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        logger.info("tool_called", tool=name, arguments=arguments)
        try:
            result = await _handle_tool_call(agent, name, arguments)
            return [TextContent(type="text", text=result)]
        except Exception as exc:
            logger.error("tool_error", tool=name, error=str(exc))
            return [TextContent(type="text", text=json.dumps({"error": str(exc)}))]

    return server


def main() -> None:
    server = create_server()

    async def _run() -> None:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    asyncio.run(_run())


if __name__ == "__main__":
    main()
