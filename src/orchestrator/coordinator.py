from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import structlog
from pydantic import BaseModel, Field

from src.agents.business_developer.agent import BusinessDeveloperAgent
from src.agents.generative_ai.agent import GenerativeAIAgent
from src.agents.physical_ai.agent import PhysicalAIAgent
from src.agents.sw_architect.agent import SWArchitectAgent

logger = structlog.get_logger(__name__)


class AgentType(str, Enum):
    SW_ARCHITECT = "sw_architect"
    GENERATIVE_AI = "generative_ai"
    BUSINESS_DEVELOPER = "business_developer"
    PHYSICAL_AI = "physical_ai"


class UserRequest(BaseModel):
    query: str
    target_agents: list[AgentType] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)


class AgentResponse(BaseModel):
    agent: str
    result: Any = None
    error: str | None = None
    duration_seconds: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WorkflowStep(BaseModel):
    agent: AgentType
    action: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[int] = Field(default_factory=list)


class Workflow(BaseModel):
    name: str
    steps: list[WorkflowStep] = Field(default_factory=list)


class WorkflowResult(BaseModel):
    workflow_name: str
    step_results: list[AgentResponse] = Field(default_factory=list)
    success: bool = True
    total_duration_seconds: float = 0.0


class ProductPipelineResult(BaseModel):
    idea: str
    project_plan: Any = None
    architecture: Any = None
    project_output: Any = None
    deployment_plan: Any = None
    business_analysis: Any = None
    business_model: Any = None
    financial_projection: Any = None
    ai_insights: Any = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StartupPipelineResult(BaseModel):
    domain: str
    startup_plan: Any = None
    architecture: Any = None
    business_analysis: Any = None
    business_model: Any = None
    pitch_deck: Any = None
    competitive_analysis: Any = None
    market_research: Any = None
    ai_tool_analysis: Any = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DailyBriefing(BaseModel):
    topics: list[str] = Field(default_factory=list)
    ai_news: Any = None
    physical_ai_newsletter: Any = None
    workflow_suggestions: Any = None
    idea_proposals: Any = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


_KEYWORD_ROUTES: list[tuple[list[str], AgentType]] = [
    (["architect", "design", "code", "deploy", "review", "backend", "frontend", "devops"], AgentType.SW_ARCHITECT),
    (["ai news", "llm", "genai", "workflow", "optimize", "tool"], AgentType.GENERATIVE_AI),
    (["business", "market", "pitch", "revenue", "startup plan", "swot", "financial"], AgentType.BUSINESS_DEVELOPER),
    (["robot", "physical", "newsletter", "automation", "sensor", "embodied"], AgentType.PHYSICAL_AI),
]


class AgentCoordinator:
    def __init__(self) -> None:
        self.sw_architect = SWArchitectAgent()
        self.generative_ai = GenerativeAIAgent()
        self.business_developer = BusinessDeveloperAgent()
        self.physical_ai = PhysicalAIAgent()
        self._initialized = False
        self._log = logger.bind(component="coordinator")

    async def initialize(self) -> None:
        self._log.info("coordinator.initializing")
        self._initialized = True
        self._log.info("coordinator.initialized")

    async def route_request(self, request: UserRequest) -> AgentResponse:
        targets = request.target_agents or self._infer_agents(request.query)
        if not targets:
            targets = [AgentType.GENERATIVE_AI]

        target = targets[0]
        self._log.info("request.routed", target=target.value, query_length=len(request.query))

        import time

        start = time.monotonic()
        try:
            result = await self._dispatch(target, request.query, request.context)
            duration = time.monotonic() - start
            return AgentResponse(agent=target.value, result=result, duration_seconds=round(duration, 3))
        except Exception as exc:
            duration = time.monotonic() - start
            self._log.error("request.failed", target=target.value, error=str(exc))
            return AgentResponse(agent=target.value, error=str(exc), duration_seconds=round(duration, 3))

    async def cross_agent_workflow(self, workflow: Workflow) -> WorkflowResult:
        self._log.info("workflow.started", name=workflow.name, steps=len(workflow.steps))
        import time

        overall_start = time.monotonic()
        step_results: list[AgentResponse] = []
        completed: dict[int, Any] = {}
        success = True

        for idx, step in enumerate(workflow.steps):
            for dep_idx in step.depends_on:
                if dep_idx >= len(step_results) or step_results[dep_idx].error is not None:
                    step_results.append(
                        AgentResponse(agent=step.agent.value, error=f"Dependency step {dep_idx} not satisfied")
                    )
                    success = False
                    continue

            start = time.monotonic()
            try:
                params = dict(step.parameters)
                for dep_idx in step.depends_on:
                    params[f"step_{dep_idx}_result"] = completed.get(dep_idx)

                result = await self._dispatch(step.agent, step.action, params)
                duration = time.monotonic() - start
                completed[idx] = result
                step_results.append(
                    AgentResponse(agent=step.agent.value, result=result, duration_seconds=round(duration, 3))
                )
            except Exception as exc:
                duration = time.monotonic() - start
                self._log.error("workflow.step_failed", step=idx, error=str(exc))
                step_results.append(
                    AgentResponse(agent=step.agent.value, error=str(exc), duration_seconds=round(duration, 3))
                )
                success = False

        total_duration = time.monotonic() - overall_start
        self._log.info("workflow.completed", name=workflow.name, success=success)
        return WorkflowResult(
            workflow_name=workflow.name,
            step_results=step_results,
            success=success,
            total_duration_seconds=round(total_duration, 3),
        )

    async def full_product_pipeline(self, idea: str) -> ProductPipelineResult:
        self._log.info("pipeline.product.started", idea_length=len(idea))
        result = ProductPipelineResult(idea=idea)

        plan = await self.sw_architect.analyze_idea(idea)
        result.project_plan = plan.model_dump(mode="json")

        architecture = await self.sw_architect.design_architecture(plan)
        result.architecture = architecture.model_dump(mode="json")

        project_output, business_analysis, ai_insights = await asyncio.gather(
            self.sw_architect.generate_project(architecture),
            self.business_developer.analyze_business_idea(idea),
            self.generative_ai.propose_ideas(idea),
        )
        result.project_output = project_output.model_dump(mode="json")
        result.business_analysis = business_analysis.model_dump(mode="json")
        result.ai_insights = [p.model_dump(mode="json") for p in ai_insights]

        deployment_plan, business_model = await asyncio.gather(
            self.sw_architect.create_deployment_plan(project_output),
            self.business_developer.create_business_model(business_analysis),
        )
        result.deployment_plan = deployment_plan.model_dump(mode="json")
        result.business_model = business_model.model_dump(mode="json")

        financial = await self.business_developer.financial_projection(business_model)
        result.financial_projection = financial.model_dump(mode="json")

        self._log.info("pipeline.product.completed", idea=idea[:60])
        return result

    async def startup_pipeline(self, domain: str) -> StartupPipelineResult:
        self._log.info("pipeline.startup.started", domain=domain)
        result = StartupPipelineResult(domain=domain)

        startup_plan, ai_tools, market = await asyncio.gather(
            self.physical_ai.startup_ideation(domain),
            self.generative_ai.analyze_ai_tools(domain),
            self.business_developer.market_research(domain, f"Companies in {domain}"),
        )
        result.startup_plan = startup_plan.model_dump(mode="json")
        result.ai_tool_analysis = ai_tools.model_dump(mode="json")
        result.market_research = market.model_dump(mode="json")

        idea_text = startup_plan.solution
        plan = await self.sw_architect.analyze_idea(idea_text)
        architecture = await self.sw_architect.design_architecture(plan)
        result.architecture = architecture.model_dump(mode="json")

        business_analysis = await self.business_developer.analyze_business_idea(idea_text)
        result.business_analysis = business_analysis.model_dump(mode="json")

        business_model, competitive = await asyncio.gather(
            self.business_developer.create_business_model(business_analysis),
            self.business_developer.competitive_analysis(domain),
        )
        result.business_model = business_model.model_dump(mode="json")
        result.competitive_analysis = competitive.model_dump(mode="json")

        pitch_deck = await self.business_developer.create_pitch_deck(business_model)
        result.pitch_deck = pitch_deck.model_dump(mode="json")

        self._log.info("pipeline.startup.completed", domain=domain)
        return result

    async def daily_briefing(self, topics: list[str]) -> DailyBriefing:
        self._log.info("briefing.started", topics=topics)

        ai_news, newsletter, workflows, ideas = await asyncio.gather(
            self.generative_ai.get_ai_news(topics),
            self.physical_ai.generate_daily_newsletter(topics),
            self.generative_ai.suggest_workflows(", ".join(topics)),
            self.generative_ai.propose_ideas(", ".join(topics)),
        )

        briefing = DailyBriefing(
            topics=topics,
            ai_news=ai_news.model_dump(mode="json"),
            physical_ai_newsletter=newsletter.model_dump(mode="json"),
            workflow_suggestions=[w.model_dump(mode="json") for w in workflows],
            idea_proposals=[p.model_dump(mode="json") for p in ideas],
        )

        self._log.info("briefing.completed", topic_count=len(topics))
        return briefing

    def get_all_agent_status(self) -> dict:
        return {
            "initialized": self._initialized,
            "agents": {
                "sw_architect": {"type": "SWArchitectAgent", "ready": True},
                "generative_ai": {"type": "GenerativeAIAgent", "ready": True},
                "business_developer": {"type": "BusinessDeveloperAgent", "ready": True},
                "physical_ai": {"type": "PhysicalAIAgent", "ready": True},
            },
        }

    async def shutdown(self) -> None:
        self._log.info("coordinator.shutting_down")
        await self.generative_ai.close()
        self._initialized = False
        self._log.info("coordinator.shut_down")

    def _infer_agents(self, query: str) -> list[AgentType]:
        query_lower = query.lower()
        matched: list[AgentType] = []
        for keywords, agent_type in _KEYWORD_ROUTES:
            if any(kw in query_lower for kw in keywords):
                matched.append(agent_type)
        return matched

    async def _dispatch(self, agent_type: AgentType, action: str, context: dict[str, Any]) -> Any:
        match agent_type:
            case AgentType.SW_ARCHITECT:
                return await self._dispatch_sw_architect(action, context)
            case AgentType.GENERATIVE_AI:
                return await self._dispatch_generative_ai(action, context)
            case AgentType.BUSINESS_DEVELOPER:
                return await self._dispatch_business_developer(action, context)
            case AgentType.PHYSICAL_AI:
                return await self._dispatch_physical_ai(action, context)

    async def _dispatch_sw_architect(self, action: str, context: dict[str, Any]) -> Any:
        action_lower = action.lower()
        if "review" in action_lower:
            review = await self.sw_architect.review_code(context.get("code", action))
            return review.model_dump(mode="json")
        plan = await self.sw_architect.analyze_idea(action)
        return plan.model_dump(mode="json")

    async def _dispatch_generative_ai(self, action: str, context: dict[str, Any]) -> Any:
        action_lower = action.lower()
        if "news" in action_lower:
            news = await self.generative_ai.get_ai_news(context.get("topics", [action]))
            return news.model_dump(mode="json")
        if "workflow" in action_lower or "optimize" in action_lower:
            suggestions = await self.generative_ai.suggest_workflows(action)
            return [s.model_dump(mode="json") for s in suggestions]
        if "tool" in action_lower:
            analysis = await self.generative_ai.analyze_ai_tools(context.get("domain", action))
            return analysis.model_dump(mode="json")
        ideas = await self.generative_ai.propose_ideas(action)
        return [i.model_dump(mode="json") for i in ideas]

    async def _dispatch_business_developer(self, action: str, context: dict[str, Any]) -> Any:
        action_lower = action.lower()
        if "market" in action_lower:
            research = await self.business_developer.market_research(
                context.get("industry", action), context.get("target", "General market")
            )
            return research.model_dump(mode="json")
        if "competitive" in action_lower or "competitor" in action_lower:
            analysis = await self.business_developer.competitive_analysis(context.get("industry", action))
            return analysis.model_dump(mode="json")
        analysis = await self.business_developer.analyze_business_idea(action)
        return analysis.model_dump(mode="json")

    async def _dispatch_physical_ai(self, action: str, context: dict[str, Any]) -> Any:
        action_lower = action.lower()
        if "newsletter" in action_lower:
            newsletter = await self.physical_ai.generate_daily_newsletter(context.get("topics", [action]))
            return newsletter.model_dump(mode="json")
        if "automat" in action_lower:
            ideas = await self.physical_ai.propose_automation_ideas(context.get("routines", [action]))
            return [i.model_dump(mode="json") for i in ideas]
        if "startup" in action_lower:
            plan = await self.physical_ai.startup_ideation(context.get("domain", action))
            return plan.model_dump(mode="json")
        report = await self.physical_ai.cross_agent_analysis(action)
        return report.model_dump(mode="json")
