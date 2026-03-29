from __future__ import annotations

import asyncio
import json

import structlog
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .agent import GenerativeAIAgent

log = structlog.get_logger()

server = Server("generative-ai")
agent = GenerativeAIAgent()

TOOLS = [
    Tool(
        name="get_ai_news",
        description="Fetch and summarize the latest AI news filtered by topics.",
        inputSchema={
            "type": "object",
            "properties": {
                "topics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of topics to filter news by (e.g. ['LLM', 'robotics', 'vision'])",
                },
            },
            "required": ["topics"],
        },
    ),
    Tool(
        name="propose_ideas",
        description="Generate AI-powered idea proposals for a given context or project.",
        inputSchema={
            "type": "object",
            "properties": {
                "context": {
                    "type": "string",
                    "description": "Description of the project or domain to generate ideas for",
                },
            },
            "required": ["context"],
        },
    ),
    Tool(
        name="suggest_workflows",
        description="Suggest workflow optimizations leveraging AI tools and techniques.",
        inputSchema={
            "type": "object",
            "properties": {
                "current_workflow": {
                    "type": "string",
                    "description": "Description of the current workflow to optimize",
                },
            },
            "required": ["current_workflow"],
        },
    ),
    Tool(
        name="analyze_ai_tools",
        description="Analyze available AI tools for a specific domain.",
        inputSchema={
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Domain to analyze tools for (e.g. 'nlp', 'vision', 'audio')",
                },
            },
            "required": ["domain"],
        },
    ),
    Tool(
        name="generate_optimization_plan",
        description="Create a step-by-step optimization plan for a process using AI.",
        inputSchema={
            "type": "object",
            "properties": {
                "process": {
                    "type": "string",
                    "description": "The process to create an optimization plan for",
                },
            },
            "required": ["process"],
        },
    ),
]


@server.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    log.info("tool_called", tool=name)

    match name:
        case "get_ai_news":
            result = await agent.get_ai_news(topics=arguments["topics"])
        case "propose_ideas":
            result = await agent.propose_ideas(context=arguments["context"])
        case "suggest_workflows":
            result = await agent.suggest_workflows(current_workflow=arguments["current_workflow"])
        case "analyze_ai_tools":
            result = await agent.analyze_ai_tools(domain=arguments["domain"])
        case "generate_optimization_plan":
            result = await agent.generate_optimization_plan(process=arguments["process"])
        case _:
            return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]

    if isinstance(result, list):
        payload = [item.model_dump(mode="json") for item in result]
    else:
        payload = result.model_dump(mode="json")

    return [TextContent(type="text", text=json.dumps(payload, default=str))]


async def _run() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
