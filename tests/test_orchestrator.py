"""Tests for orchestrator module: coordinator, routing, pipelines, and server."""

import importlib
from unittest.mock import AsyncMock, patch

import pytest

from src.orchestrator.coordinator import (
    AgentCoordinator,
    AgentType,
    DailyBriefing,
    ProductPipelineResult,
    StartupPipelineResult,
    UserRequest,
    Workflow,
    WorkflowResult,
    WorkflowStep,
)


class TestOrchestratorAvailability:
    def test_orchestrator_entry_point_is_configured(self):
        import tomllib
        from pathlib import Path

        pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
        if not pyproject.exists():
            pytest.skip("pyproject.toml not found")
        with open(pyproject, "rb") as f:
            data = tomllib.load(f)
        scripts = data.get("project", {}).get("scripts", {})
        assert "agentic-orchestrator" in scripts

    def test_orchestrator_server_module_importable(self):
        mod = importlib.import_module("src.orchestrator.server")
        assert hasattr(mod, "main")
        assert hasattr(mod, "create_server")
        assert hasattr(mod, "TOOLS")

    def test_orchestrator_coordinator_importable(self):
        mod = importlib.import_module("src.orchestrator.coordinator")
        assert hasattr(mod, "AgentCoordinator")
        assert hasattr(mod, "AgentType")


class TestAgentCoordinator:
    def test_initialization(self):
        coord = AgentCoordinator()
        assert coord.sw_architect is not None
        assert coord.generative_ai is not None
        assert coord.business_developer is not None
        assert coord.physical_ai is not None
        assert coord._initialized is False

    async def test_initialize_sets_flag(self):
        coord = AgentCoordinator()
        await coord.initialize()
        assert coord._initialized is True
        await coord.shutdown()
        assert coord._initialized is False

    def test_get_all_agent_status(self):
        coord = AgentCoordinator()
        status = coord.get_all_agent_status()
        assert status["initialized"] is False
        assert "sw_architect" in status["agents"]
        assert "generative_ai" in status["agents"]
        assert "business_developer" in status["agents"]
        assert "physical_ai" in status["agents"]
        for agent_info in status["agents"].values():
            assert "type" in agent_info
            assert "ready" in agent_info


class TestRequestRouting:
    def test_infer_sw_architect(self):
        coord = AgentCoordinator()
        agents = coord._infer_agents("design an architecture for my backend")
        assert AgentType.SW_ARCHITECT in agents

    def test_infer_generative_ai(self):
        coord = AgentCoordinator()
        agents = coord._infer_agents("get me the latest ai news about LLM")
        assert AgentType.GENERATIVE_AI in agents

    def test_infer_business_developer(self):
        coord = AgentCoordinator()
        agents = coord._infer_agents("create a business plan with revenue model")
        assert AgentType.BUSINESS_DEVELOPER in agents

    def test_infer_physical_ai(self):
        coord = AgentCoordinator()
        agents = coord._infer_agents("find latest newsletter about robot automation")
        assert AgentType.PHYSICAL_AI in agents

    def test_infer_multiple_agents(self):
        coord = AgentCoordinator()
        agents = coord._infer_agents("design architecture for a business robot platform")
        assert len(agents) >= 2

    def test_infer_fallback_to_empty(self):
        coord = AgentCoordinator()
        agents = coord._infer_agents("hello there")
        assert agents == []

    async def test_route_request_defaults_to_genai(self):
        coord = AgentCoordinator()
        request = UserRequest(query="hello world")
        response = await coord.route_request(request)
        assert response.agent == AgentType.GENERATIVE_AI.value

    async def test_route_request_explicit_target(self):
        coord = AgentCoordinator()
        request = UserRequest(
            query="analyze my startup",
            target_agents=[AgentType.BUSINESS_DEVELOPER],
        )
        response = await coord.route_request(request)
        assert response.agent == AgentType.BUSINESS_DEVELOPER.value


class TestProductPipeline:
    async def test_full_product_pipeline(self):
        coord = AgentCoordinator()
        result = await coord.full_product_pipeline("An AI-powered code review SaaS platform")
        assert isinstance(result, ProductPipelineResult)
        assert result.idea == "An AI-powered code review SaaS platform"
        assert result.project_plan is not None
        assert result.architecture is not None
        assert result.project_output is not None
        assert result.deployment_plan is not None
        assert result.business_analysis is not None
        assert result.business_model is not None
        assert result.financial_projection is not None
        assert result.ai_insights is not None


class TestStartupPipeline:
    async def test_startup_pipeline(self):
        coord = AgentCoordinator()
        with patch.object(
            coord.physical_ai.scraper, "aggregate_news", new_callable=AsyncMock
        ) as mock_agg, patch.object(
            coord.physical_ai.scraper, "scrape_news_sources", new_callable=AsyncMock
        ) as mock_news, patch.object(
            coord.physical_ai.scraper, "scrape_industry_blogs", new_callable=AsyncMock
        ) as mock_blogs:
            mock_agg.return_value = []
            mock_news.return_value = []
            mock_blogs.return_value = []

            result = await coord.startup_pipeline("warehouse robotics")
            assert isinstance(result, StartupPipelineResult)
            assert result.domain == "warehouse robotics"
            assert result.startup_plan is not None
            assert result.architecture is not None
            assert result.business_model is not None
            assert result.pitch_deck is not None
            assert result.market_research is not None


class TestDailyBriefing:
    async def test_daily_briefing(self):
        coord = AgentCoordinator()
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body></body></html>"
        mock_response.raise_for_status = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        coord.generative_ai._client = mock_client
        coord.generative_ai._aggregator._client = mock_client

        with patch.object(
            coord.physical_ai.scraper, "aggregate_news", new_callable=AsyncMock
        ) as mock_agg, patch.object(
            coord.physical_ai.scraper, "scrape_arxiv", new_callable=AsyncMock
        ) as mock_arxiv:
            mock_agg.return_value = []
            mock_arxiv.return_value = []

            result = await coord.daily_briefing(["robotics", "LLM"])
            assert isinstance(result, DailyBriefing)
            assert result.topics == ["robotics", "LLM"]
            assert result.ai_news is not None
            assert result.workflow_suggestions is not None
            assert result.idea_proposals is not None


class TestCrossAgentWorkflow:
    async def test_cross_agent_workflow(self):
        coord = AgentCoordinator()
        workflow = Workflow(
            name="test-workflow",
            steps=[
                WorkflowStep(
                    agent=AgentType.SW_ARCHITECT,
                    action="design a REST API",
                    parameters={},
                ),
                WorkflowStep(
                    agent=AgentType.BUSINESS_DEVELOPER,
                    action="market research for API platform",
                    parameters={"industry": "API platforms", "target": "developers"},
                    depends_on=[0],
                ),
            ],
        )
        result = await coord.cross_agent_workflow(workflow)
        assert isinstance(result, WorkflowResult)
        assert result.workflow_name == "test-workflow"
        assert len(result.step_results) == 2
        assert result.success is True
        assert result.total_duration_seconds >= 0


class TestOrchestratorServer:
    def test_server_creation(self):
        from src.orchestrator.server import create_server

        server, coordinator = create_server()
        assert server.name == "agentic-orchestrator"
        assert coordinator is not None

    def test_server_tools(self):
        from src.orchestrator.server import TOOLS

        assert len(TOOLS) == 5
        tool_names = {t.name for t in TOOLS}
        assert "route_request" in tool_names
        assert "full_product_pipeline" in tool_names
        assert "startup_pipeline" in tool_names
        assert "daily_briefing" in tool_names
        assert "cross_agent_workflow" in tool_names
