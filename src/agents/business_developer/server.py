from __future__ import annotations

import asyncio
import json

import structlog
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .agent import BusinessAnalysis, BusinessDeveloperAgent, BusinessModel

log = structlog.get_logger()

server = Server("business-developer")
agent = BusinessDeveloperAgent()

TOOLS = [
    Tool(
        name="analyze_business_idea",
        description="Perform a comprehensive SWOT-based analysis of a business idea.",
        inputSchema={
            "type": "object",
            "properties": {
                "idea": {
                    "type": "string",
                    "description": "The business idea to analyze",
                },
            },
            "required": ["idea"],
        },
    ),
    Tool(
        name="create_business_model",
        description="Generate a Business Model Canvas from a business analysis.",
        inputSchema={
            "type": "object",
            "properties": {
                "analysis": {
                    "type": "object",
                    "description": "BusinessAnalysis JSON object from analyze_business_idea",
                },
            },
            "required": ["analysis"],
        },
    ),
    Tool(
        name="market_research",
        description="Conduct market research for a given industry and target segment.",
        inputSchema={
            "type": "object",
            "properties": {
                "industry": {
                    "type": "string",
                    "description": "Industry to research (e.g. 'fintech', 'healthtech')",
                },
                "target": {
                    "type": "string",
                    "description": "Target market segment",
                },
            },
            "required": ["industry", "target"],
        },
    ),
    Tool(
        name="financial_projection",
        description="Create financial projections from a business model.",
        inputSchema={
            "type": "object",
            "properties": {
                "model": {
                    "type": "object",
                    "description": "BusinessModel JSON object from create_business_model",
                },
            },
            "required": ["model"],
        },
    ),
    Tool(
        name="create_pitch_deck",
        description="Generate pitch deck slide content from a business model.",
        inputSchema={
            "type": "object",
            "properties": {
                "model": {
                    "type": "object",
                    "description": "BusinessModel JSON object from create_business_model",
                },
            },
            "required": ["model"],
        },
    ),
    Tool(
        name="competitive_analysis",
        description="Analyze the competitive landscape for an industry.",
        inputSchema={
            "type": "object",
            "properties": {
                "industry": {
                    "type": "string",
                    "description": "Industry to analyze competitors in",
                },
            },
            "required": ["industry"],
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
        case "analyze_business_idea":
            result = await agent.analyze_business_idea(idea=arguments["idea"])
        case "create_business_model":
            analysis = BusinessAnalysis.model_validate(arguments["analysis"])
            result = await agent.create_business_model(analysis=analysis)
        case "market_research":
            result = await agent.market_research(
                industry=arguments["industry"],
                target=arguments["target"],
            )
        case "financial_projection":
            model = BusinessModel.model_validate(arguments["model"])
            result = await agent.financial_projection(model=model)
        case "create_pitch_deck":
            model = BusinessModel.model_validate(arguments["model"])
            result = await agent.create_pitch_deck(model=model)
        case "competitive_analysis":
            result = await agent.competitive_analysis(industry=arguments["industry"])
        case _:
            return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]

    payload = result.model_dump(mode="json")
    return [TextContent(type="text", text=json.dumps(payload, default=str))]


async def _run() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
