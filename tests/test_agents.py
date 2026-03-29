"""Tests for all agent modules."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.sw_architect.agent import (
    Architecture,
    ProjectPlan,
    SWArchitectAgent,
    TechStack,
)
from src.agents.generative_ai.agent import (
    AINewsSummary,
    GenerativeAIAgent,
    IdeaProposal,
)
from src.agents.business_developer.agent import (
    BusinessAnalysis,
    BusinessDeveloperAgent,
    BusinessModel,
)
from src.agents.physical_ai.agent import (
    AutomationIdea,
    NewsItem,
    PhysicalAIAgent,
)


# ---------------------------------------------------------------------------
# SWArchitectAgent
# ---------------------------------------------------------------------------


class TestSWArchitectAgent:
    async def test_analyze_idea_returns_project_plan(self, sample_idea):
        agent = SWArchitectAgent()
        plan = await agent.analyze_idea(sample_idea)
        assert isinstance(plan, ProjectPlan)
        assert plan.name
        assert plan.description == sample_idea
        assert len(plan.goals) > 0
        assert len(plan.features) > 0
        assert isinstance(plan.tech_stack, TechStack)

    async def test_analyze_idea_web_keywords(self):
        agent = SWArchitectAgent()
        plan = await agent.analyze_idea("Build a web application for task management")
        assert "FastAPI" in plan.tech_stack.frameworks or "React" in plan.tech_stack.frameworks
        assert any("Python" in lang or "TypeScript" in lang for lang in plan.tech_stack.languages)

    async def test_analyze_idea_mobile_keywords(self):
        agent = SWArchitectAgent()
        plan = await agent.analyze_idea("Create a mobile app for fitness tracking")
        assert "React Native" in plan.tech_stack.frameworks

    async def test_analyze_idea_data_keywords(self):
        agent = SWArchitectAgent()
        plan = await agent.analyze_idea("Build a data analytics dashboard with ML")
        assert any(f in plan.tech_stack.frameworks for f in ["Pandas", "scikit-learn"])

    async def test_analyze_idea_generic(self):
        agent = SWArchitectAgent()
        plan = await agent.analyze_idea("Something completely novel")
        assert isinstance(plan, ProjectPlan)
        assert len(plan.features) > 0

    async def test_design_architecture_returns_architecture(self, sample_idea):
        agent = SWArchitectAgent()
        plan = await agent.analyze_idea(sample_idea)
        arch = await agent.design_architecture(plan)
        assert isinstance(arch, Architecture)
        assert arch.project_name == plan.name
        assert len(arch.components) > 0
        assert len(arch.apis) > 0
        assert len(arch.data_models) > 0

    async def test_design_architecture_style(self, sample_idea):
        agent = SWArchitectAgent()
        plan = await agent.analyze_idea(sample_idea)
        arch = await agent.design_architecture(plan)
        assert arch.style in ("microservices", "monolith")

    async def test_review_code(self):
        agent = SWArchitectAgent()
        code = '''
import os

def hello():
    """Say hello."""
    print("Hello, world!")
'''
        review = await agent.review_code(code)
        assert review.score >= 0
        assert review.score <= 10
        assert review.summary

    async def test_review_code_security_issues(self):
        agent = SWArchitectAgent()
        code = 'eval(input("Enter code: "))\npassword = "secret123"'
        review = await agent.review_code(code)
        assert len(review.security_concerns) > 0
        assert not review.approved

    async def test_derive_project_name(self):
        name = SWArchitectAgent._derive_project_name("Build a cool web app for developers")
        assert isinstance(name, str)
        assert len(name) > 0


# ---------------------------------------------------------------------------
# GenerativeAIAgent
# ---------------------------------------------------------------------------


class TestGenerativeAIAgent:
    async def test_get_ai_news(self, sample_topics):
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body><h2><a href='https://example.com'>Test AI News</a></h2></body></html>"
        mock_response.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        agent = GenerativeAIAgent(http_client=mock_client)
        result = await agent.get_ai_news(sample_topics)
        assert isinstance(result, AINewsSummary)
        assert result.topics == sample_topics
        assert isinstance(result.items, list)
        assert result.total_sources_checked > 0
        await agent.close()

    async def test_propose_ideas(self, sample_idea):
        mock_client = AsyncMock()
        agent = GenerativeAIAgent(http_client=mock_client)
        ideas = await agent.propose_ideas(sample_idea)
        assert isinstance(ideas, list)
        assert len(ideas) >= 3
        for idea in ideas:
            assert isinstance(idea, IdeaProposal)
            assert idea.title
            assert idea.description
            assert idea.feasibility in ("low", "medium", "high")
            assert idea.estimated_impact in ("low", "medium", "high")
        await agent.close()

    async def test_propose_ideas_vision_keywords(self):
        mock_client = AsyncMock()
        agent = GenerativeAIAgent(http_client=mock_client)
        ideas = await agent.propose_ideas("image recognition and visual design tools")
        assert len(ideas) >= 4
        has_vision = any("Vision" in idea.title for idea in ideas)
        assert has_vision
        await agent.close()

    async def test_suggest_workflows(self):
        mock_client = AsyncMock()
        agent = GenerativeAIAgent(http_client=mock_client)
        workflows = await agent.suggest_workflows("software development process")
        assert isinstance(workflows, list)
        assert len(workflows) >= 4
        areas = {w.area for w in workflows}
        assert "Code Generation" in areas
        assert "Testing" in areas
        await agent.close()

    async def test_analyze_ai_tools_known_domain(self):
        mock_client = AsyncMock()
        agent = GenerativeAIAgent(http_client=mock_client)
        analysis = await agent.analyze_ai_tools("nlp")
        assert analysis.domain == "nlp"
        assert len(analysis.tools) > 0
        assert analysis.recommendation
        await agent.close()

    async def test_analyze_ai_tools_unknown_domain(self):
        mock_client = AsyncMock()
        agent = GenerativeAIAgent(http_client=mock_client)
        analysis = await agent.analyze_ai_tools("quantum_computing")
        assert analysis.domain == "quantum_computing"
        assert len(analysis.tools) > 0
        await agent.close()


# ---------------------------------------------------------------------------
# BusinessDeveloperAgent
# ---------------------------------------------------------------------------


class TestBusinessDeveloperAgent:
    async def test_analyze_business_idea(self, sample_idea):
        agent = BusinessDeveloperAgent()
        analysis = await agent.analyze_business_idea(sample_idea)
        assert isinstance(analysis, BusinessAnalysis)
        assert analysis.idea == sample_idea
        assert analysis.value_proposition
        assert analysis.target_audience
        assert len(analysis.strengths) > 0
        assert len(analysis.weaknesses) > 0
        assert len(analysis.opportunities) > 0
        assert len(analysis.threats) > 0
        assert 0.0 <= analysis.feasibility_score <= 10.0

    async def test_create_business_model(self, sample_idea):
        agent = BusinessDeveloperAgent()
        analysis = await agent.analyze_business_idea(sample_idea)
        model = await agent.create_business_model(analysis)
        assert isinstance(model, BusinessModel)
        assert model.name == analysis.idea
        assert len(model.key_partners) > 0
        assert len(model.key_activities) > 0
        assert len(model.revenue_streams) > 0
        assert len(model.customer_segments) > 0

    async def test_business_analysis_recommendation(self, sample_idea):
        agent = BusinessDeveloperAgent()
        analysis = await agent.analyze_business_idea(sample_idea)
        assert analysis.recommendation
        assert len(analysis.recommendation) > 10

    async def test_market_research(self):
        agent = BusinessDeveloperAgent()
        research = await agent.market_research("fintech", "small businesses")
        assert research.industry == "fintech"
        assert research.target_market == "small businesses"
        assert len(research.key_trends) > 0
        assert len(research.customer_personas) > 0

    async def test_competitive_analysis(self):
        agent = BusinessDeveloperAgent()
        analysis = await agent.competitive_analysis("AI SaaS")
        assert analysis.industry == "AI SaaS"
        assert len(analysis.competitors) > 0
        assert len(analysis.market_gaps) > 0


# ---------------------------------------------------------------------------
# PhysicalAIAgent
# ---------------------------------------------------------------------------


class TestPhysicalAIAgent:
    async def test_scan_physical_ai_news(self):
        agent = PhysicalAIAgent()
        with patch.object(agent.scraper, "aggregate_news", new_callable=AsyncMock) as mock_agg:
            mock_agg.return_value = [
                {
                    "title": "New Humanoid Robot",
                    "url": "https://example.com/humanoid",
                    "source": "Robot Report",
                    "summary": "A new humanoid robot was unveiled.",
                    "published": None,
                    "tags": ["humanoid", "robotics"],
                    "relevance_score": 0.9,
                },
                {
                    "title": "AI in Manufacturing",
                    "url": "https://example.com/manufacturing",
                    "source": "IEEE",
                    "summary": "AI is transforming manufacturing.",
                    "published": None,
                    "tags": ["industry"],
                    "relevance_score": 0.5,
                },
            ]
            items = await agent.scan_physical_ai_news()
            assert isinstance(items, list)
            assert len(items) == 2
            assert all(isinstance(item, NewsItem) for item in items)
            assert items[0].relevance_score >= items[1].relevance_score

    async def test_propose_automation_ideas(self, sample_routines):
        agent = PhysicalAIAgent()
        ideas = await agent.propose_automation_ideas(sample_routines)
        assert isinstance(ideas, list)
        assert len(ideas) == len(sample_routines)
        for idea in ideas:
            assert isinstance(idea, AutomationIdea)
            assert idea.title.startswith("Automate:")
            assert idea.feasibility
            assert len(idea.required_technologies) > 0
            assert len(idea.implementation_steps) > 0

    async def test_propose_automation_picks_sorting(self):
        agent = PhysicalAIAgent()
        ideas = await agent.propose_automation_ideas(["pick and sort items"])
        assert len(ideas) == 1
        idea = ideas[0]
        assert "Robotic Manipulation" in idea.required_technologies

    async def test_propose_automation_navigation(self):
        agent = PhysicalAIAgent()
        ideas = await agent.propose_automation_ideas(["navigate warehouse"])
        assert len(ideas) == 1
        idea = ideas[0]
        assert "Autonomous Navigation" in idea.required_technologies

    async def test_suggest_technologies(self):
        agent = PhysicalAIAgent()
        techs = agent._suggest_technologies("warehouse picking and sorting")
        assert "Robotic Manipulation" in techs
        assert "Computer Vision" in techs

    async def test_suggest_products(self):
        agent = PhysicalAIAgent()
        products = agent._suggest_products("warehouse logistics delivery")
        assert "Amazon Robotics" in products or "Locus Robotics" in products

    async def test_startup_ideation(self):
        agent = PhysicalAIAgent()
        with patch.object(agent.scraper, "aggregate_news", new_callable=AsyncMock) as mock_agg:
            mock_agg.return_value = []
            plan = await agent.startup_ideation("agriculture")
            assert plan.domain == "agriculture"
            assert plan.name
            assert plan.problem_statement
            assert plan.solution
