from __future__ import annotations

import asyncio
import json

import structlog
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .coordinator import (
    AgentCoordinator,
    AgentType,
    UserRequest,
    Workflow,
    WorkflowStep,
)

log = structlog.get_logger(__name__)

TOOLS: list[Tool] = [
    Tool(
        name="route_request",
        description="Route a request to the appropriate agent based on content analysis or explicit targeting.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The user request or question to route",
                },
                "target_agents": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["sw_architect", "generative_ai", "business_developer", "physical_ai"],
                    },
                    "description": "Optional list of specific agents to target",
                },
                "context": {
                    "type": "object",
                    "description": "Additional context for the request",
                },
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="full_product_pipeline",
        description=(
            "Run the end-to-end product development pipeline: "
            "idea analysis, architecture design, code generation, deployment planning, "
            "business analysis, and financial projections."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "idea": {
                    "type": "string",
                    "description": "The product idea to develop through the full pipeline",
                },
            },
            "required": ["idea"],
        },
    ),
    Tool(
        name="startup_pipeline",
        description=(
            "Run the full startup creation pipeline: startup ideation, market research, "
            "architecture design, business model, competitive analysis, and pitch deck generation."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "The domain or industry for the startup (e.g., 'healthcare', 'logistics')",
                },
            },
            "required": ["domain"],
        },
    ),
    Tool(
        name="daily_briefing",
        description=(
            "Generate a comprehensive daily briefing from all agents, including AI news, "
            "Physical AI newsletter, workflow suggestions, and idea proposals."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "topics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of topics for the briefing (e.g., ['robotics', 'LLM', 'startups'])",
                },
            },
            "required": ["topics"],
        },
    ),
    Tool(
        name="cross_agent_workflow",
        description="Execute a custom cross-agent workflow with ordered steps and dependencies.",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the workflow",
                },
                "steps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "agent": {
                                "type": "string",
                                "enum": ["sw_architect", "generative_ai", "business_developer", "physical_ai"],
                            },
                            "action": {"type": "string"},
                            "parameters": {"type": "object"},
                            "depends_on": {
                                "type": "array",
                                "items": {"type": "integer"},
                            },
                        },
                        "required": ["agent", "action"],
                    },
                    "description": "Ordered list of workflow steps with agent assignments",
                },
            },
            "required": ["name", "steps"],
        },
    ),
]


def _serialize(obj: object) -> str:
    if hasattr(obj, "model_dump"):
        return json.dumps(obj.model_dump(mode="json"), indent=2, default=str)
    return json.dumps(obj, indent=2, default=str)


def create_server() -> tuple[Server, AgentCoordinator]:
    server = Server("agentic-orchestrator")
    coordinator = AgentCoordinator()

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return TOOLS

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        log.info("tool_called", tool=name)
        try:
            result_text = await _handle_tool(coordinator, name, arguments)
            return [TextContent(type="text", text=result_text)]
        except Exception as exc:
            log.error("tool_error", tool=name, error=str(exc))
            return [TextContent(type="text", text=json.dumps({"error": str(exc)}))]

    return server, coordinator


async def _handle_tool(coordinator: AgentCoordinator, name: str, arguments: dict) -> str:
    match name:
        case "route_request":
            target_agents = [AgentType(a) for a in arguments.get("target_agents", [])]
            request = UserRequest(
                query=arguments["query"],
                target_agents=target_agents,
                context=arguments.get("context", {}),
            )
            result = await coordinator.route_request(request)
            return _serialize(result)

        case "full_product_pipeline":
            result = await coordinator.full_product_pipeline(arguments["idea"])
            return _serialize(result)

        case "startup_pipeline":
            result = await coordinator.startup_pipeline(arguments["domain"])
            return _serialize(result)

        case "daily_briefing":
            result = await coordinator.daily_briefing(arguments["topics"])
            return _serialize(result)

        case "cross_agent_workflow":
            steps = [
                WorkflowStep(
                    agent=AgentType(s["agent"]),
                    action=s["action"],
                    parameters=s.get("parameters", {}),
                    depends_on=s.get("depends_on", []),
                )
                for s in arguments["steps"]
            ]
            workflow = Workflow(name=arguments["name"], steps=steps)
            result = await coordinator.cross_agent_workflow(workflow)
            return _serialize(result)

        case _:
            raise ValueError(f"Unknown tool: {name}")


async def _run() -> None:
    server, coordinator = create_server()
    await coordinator.initialize()
    try:
        async with stdio_server() as (read_stream, write_stream):
            log.info("orchestrator_server_started")
            await server.run(read_stream, write_stream, server.create_initialization_options())
    finally:
        await coordinator.shutdown()


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
