from __future__ import annotations

import asyncio
import json

import structlog
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .agent import SWArchitectAgent

log = structlog.get_logger()


def create_server() -> Server:
    server = Server("sw-architect")
    agent = SWArchitectAgent()

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="analyze_idea",
                description=(
                    "Analyze an idea and create a structured project plan "
                    "with goals, features, tech stack, and milestones"
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "idea": {
                            "type": "string",
                            "description": "The product idea or concept to analyze",
                        },
                    },
                    "required": ["idea"],
                },
            ),
            Tool(
                name="design_architecture",
                description=(
                    "Design system architecture including components, "
                    "APIs, data models, and tech stack from a project plan"
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "plan": {
                            "type": "object",
                            "description": "The project plan (ProjectPlan JSON)",
                            "properties": {
                                "name": {"type": "string"},
                                "description": {"type": "string"},
                                "goals": {"type": "array", "items": {"type": "string"}},
                                "features": {"type": "array", "items": {"type": "string"}},
                                "constraints": {"type": "array", "items": {"type": "string"}},
                                "milestones": {"type": "array", "items": {"type": "string"}},
                                "tech_stack": {
                                    "type": "object",
                                    "properties": {
                                        "languages": {"type": "array", "items": {"type": "string"}},
                                        "frameworks": {"type": "array", "items": {"type": "string"}},
                                        "databases": {"type": "array", "items": {"type": "string"}},
                                        "infrastructure": {"type": "array", "items": {"type": "string"}},
                                        "tools": {"type": "array", "items": {"type": "string"}},
                                    },
                                },
                            },
                            "required": ["name", "description"],
                        },
                    },
                    "required": ["plan"],
                },
            ),
            Tool(
                name="generate_project",
                description="Generate complete project code using sub-agents for backend, frontend, DevOps, and QA",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "architecture": {
                            "type": "object",
                            "description": "The system architecture (Architecture JSON)",
                            "properties": {
                                "project_name": {"type": "string"},
                                "style": {"type": "string"},
                                "components": {"type": "array", "items": {"type": "object"}},
                                "apis": {"type": "array", "items": {"type": "object"}},
                                "data_models": {"type": "array", "items": {"type": "object"}},
                                "tech_stack": {"type": "object"},
                                "diagrams": {"type": "object"},
                            },
                            "required": ["project_name"],
                        },
                    },
                    "required": ["architecture"],
                },
            ),
            Tool(
                name="review_code",
                description="Review code quality, find issues, security concerns, and provide improvement suggestions",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "The source code to review",
                        },
                    },
                    "required": ["code"],
                },
            ),
            Tool(
                name="create_deployment_plan",
                description=(
                    "Create deployment configuration including "
                    "Dockerfile, Kubernetes manifests, and CI/CD pipeline"
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project": {
                            "type": "object",
                            "description": "The project output (ProjectOutput JSON)",
                            "properties": {
                                "project_name": {"type": "string"},
                                "backend_code": {"type": "object"},
                                "frontend_code": {"type": "object"},
                                "devops_configs": {"type": "object"},
                                "tests": {"type": "object"},
                                "documentation": {"type": "object"},
                            },
                            "required": ["project_name"],
                        },
                    },
                    "required": ["project"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        log.info("tool_called", tool=name)

        try:
            if name == "analyze_idea":
                result = await agent.analyze_idea(arguments["idea"])
                return [TextContent(type="text", text=result.model_dump_json(indent=2))]

            if name == "design_architecture":
                from .agent import ProjectPlan

                plan = ProjectPlan.model_validate(arguments["plan"])
                result = await agent.design_architecture(plan)
                return [TextContent(type="text", text=result.model_dump_json(indent=2))]

            if name == "generate_project":
                from .agent import Architecture

                arch = Architecture.model_validate(arguments["architecture"])
                result = await agent.generate_project(arch)
                return [TextContent(type="text", text=result.model_dump_json(indent=2))]

            if name == "review_code":
                result = await agent.review_code(arguments["code"])
                return [TextContent(type="text", text=result.model_dump_json(indent=2))]

            if name == "create_deployment_plan":
                from .agent import ProjectOutput

                project = ProjectOutput.model_validate(arguments["project"])
                result = await agent.create_deployment_plan(project)
                return [TextContent(type="text", text=result.model_dump_json(indent=2))]

            raise ValueError(f"Unknown tool: {name}")

        except Exception as e:
            log.error("tool_error", tool=name, error=str(e))
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

    return server


async def run_server():
    server = create_server()
    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        log.info("sw_architect_server_started")
        await server.run(read_stream, write_stream, options)


def main():
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
