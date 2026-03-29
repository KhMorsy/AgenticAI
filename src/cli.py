from __future__ import annotations

import asyncio
import json

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


@click.group()
@click.option("--config", default=None, type=click.Path(), help="Path to configuration file.")
@click.option("--verbose", is_flag=True, default=False, help="Enable verbose output.")
@click.option(
    "--provider",
    type=click.Choice(["openai", "anthropic"], case_sensitive=False),
    default=None,
    help="LLM provider to use.",
)
@click.option("--model", default=None, help="LLM model name override.")
@click.pass_context
def main(ctx: click.Context, config: str | None, verbose: bool, provider: str | None, model: str | None) -> None:
    """Agentic MCP System — orchestrate SW Architect, GenAI, Business Developer, and Physical AI agents."""
    ctx.ensure_object(dict)
    ctx.obj["config"] = config
    ctx.obj["verbose"] = verbose
    ctx.obj["provider"] = provider
    ctx.obj["model"] = model


@main.command()
@click.pass_context
def start(ctx: click.Context) -> None:
    """Start the orchestrator MCP server."""
    console.print(Panel("[bold green]Starting Agentic Orchestrator MCP Server[/bold green]"))
    from src.orchestrator.server import main as server_main

    server_main()


@main.command()
@click.pass_context
def architect(ctx: click.Context) -> None:
    """Start just the SW Architect agent server."""
    console.print(Panel("[bold blue]Starting SW Architect Agent Server[/bold blue]"))
    from src.agents.sw_architect.server import main as server_main

    server_main()


@main.command()
@click.pass_context
def genai(ctx: click.Context) -> None:
    """Start just the Generative AI agent server."""
    console.print(Panel("[bold magenta]Starting Generative AI Agent Server[/bold magenta]"))
    from src.agents.generative_ai.server import main as server_main

    server_main()


@main.command()
@click.pass_context
def business(ctx: click.Context) -> None:
    """Start just the Business Developer agent server."""
    console.print(Panel("[bold yellow]Starting Business Developer Agent Server[/bold yellow]"))
    from src.agents.business_developer.server import main as server_main

    server_main()


@main.command()
@click.pass_context
def physical(ctx: click.Context) -> None:
    """Start just the Physical AI agent server."""
    console.print(Panel("[bold cyan]Starting Physical AI Agent Server[/bold cyan]"))
    from src.agents.physical_ai.server import main as server_main

    server_main()


@main.command()
@click.argument("idea")
@click.pass_context
def pipeline(ctx: click.Context, idea: str) -> None:
    """Run the full product pipeline for an idea."""
    console.print(Panel(f"[bold green]Full Product Pipeline[/bold green]\n{idea}"))

    async def _run() -> None:
        from src.orchestrator.coordinator import AgentCoordinator

        coordinator = AgentCoordinator()
        await coordinator.initialize()
        try:
            result = await coordinator.full_product_pipeline(idea)
            console.print_json(json.dumps(result.model_dump(mode="json"), default=str))
        finally:
            await coordinator.shutdown()

    asyncio.run(_run())


@main.command()
@click.argument("domain")
@click.pass_context
def startup(ctx: click.Context, domain: str) -> None:
    """Run the startup pipeline for a domain."""
    console.print(Panel(f"[bold green]Startup Pipeline[/bold green]\n{domain}"))

    async def _run() -> None:
        from src.orchestrator.coordinator import AgentCoordinator

        coordinator = AgentCoordinator()
        await coordinator.initialize()
        try:
            result = await coordinator.startup_pipeline(domain)
            console.print_json(json.dumps(result.model_dump(mode="json"), default=str))
        finally:
            await coordinator.shutdown()

    asyncio.run(_run())


@main.command()
@click.argument("topics", nargs=-1, required=True)
@click.pass_context
def briefing(ctx: click.Context, topics: tuple[str, ...]) -> None:
    """Generate daily briefing for given topics."""
    topic_list = list(topics)
    console.print(Panel(f"[bold green]Daily Briefing[/bold green]\nTopics: {', '.join(topic_list)}"))

    async def _run() -> None:
        from src.orchestrator.coordinator import AgentCoordinator

        coordinator = AgentCoordinator()
        await coordinator.initialize()
        try:
            result = await coordinator.daily_briefing(topic_list)
            console.print_json(json.dumps(result.model_dump(mode="json"), default=str))
        finally:
            await coordinator.shutdown()

    asyncio.run(_run())


@main.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show system status of all agents."""
    from src.orchestrator.coordinator import AgentCoordinator

    coordinator = AgentCoordinator()

    info = coordinator.get_all_agent_status()

    table = Table(title="Agentic System Status")
    table.add_column("Agent", style="cyan", no_wrap=True)
    table.add_column("Type", style="magenta")
    table.add_column("Ready", style="green")

    for name, details in info["agents"].items():
        table.add_row(name, details["type"], str(details["ready"]))

    console.print(table)
    console.print(f"\n[bold]Initialized:[/bold] {info['initialized']}")


if __name__ == "__main__":
    main()
