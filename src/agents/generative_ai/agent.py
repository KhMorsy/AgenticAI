from __future__ import annotations

from datetime import datetime, timezone

import httpx
import structlog
from pydantic import BaseModel, Field

from .sources import AISourceAggregator, SourceCategory

log = structlog.get_logger()


class NewsItem(BaseModel):
    title: str
    url: str
    source: str
    summary: str
    published: datetime | None = None
    category: SourceCategory


class AINewsSummary(BaseModel):
    topics: list[str]
    items: list[NewsItem]
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_sources_checked: int = 0


class IdeaProposal(BaseModel):
    title: str
    description: str
    feasibility: str = Field(description="low | medium | high")
    estimated_impact: str = Field(description="low | medium | high")
    required_resources: list[str] = Field(default_factory=list)
    related_technologies: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)


class WorkflowOptimization(BaseModel):
    area: str
    current_pain_point: str
    proposed_improvement: str
    tools_suggested: list[str] = Field(default_factory=list)
    expected_time_savings: str = ""
    implementation_complexity: str = Field(description="low | medium | high")


class ToolAnalysis(BaseModel):
    domain: str
    tools: list[ToolEntry]
    recommendation: str
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ToolEntry(BaseModel):
    name: str
    url: str
    description: str
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    pricing_model: str = ""
    best_for: str = ""


class OptimizationPlan(BaseModel):
    process: str
    current_state: str
    target_state: str
    steps: list[OptimizationStep]
    expected_outcomes: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


class OptimizationStep(BaseModel):
    order: int
    action: str
    description: str
    tools: list[str] = Field(default_factory=list)
    dependencies: list[int] = Field(default_factory=list)


# Rebuild forward-ref models
ToolAnalysis.model_rebuild()
OptimizationPlan.model_rebuild()


class GenerativeAIAgent:
    def __init__(self, http_client: httpx.AsyncClient | None = None) -> None:
        self._client = http_client or httpx.AsyncClient(timeout=30.0)
        self._aggregator = AISourceAggregator(client=self._client)
        self._owns_client = http_client is None

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def get_ai_news(self, topics: list[str]) -> AINewsSummary:
        log.info("fetching_ai_news", topics=topics)
        raw_items = await self._aggregator.fetch_all()

        topic_lower = [t.lower() for t in topics]
        filtered: list[NewsItem] = []
        for item in raw_items:
            text = f"{item['title']} {item['summary']}".lower()
            if not topic_lower or any(t in text for t in topic_lower):
                filtered.append(
                    NewsItem(
                        title=item["title"],
                        url=item["url"],
                        source=item["source"],
                        summary=item["summary"],
                        published=item.get("published"),
                        category=item["category"],
                    )
                )

        return AINewsSummary(
            topics=topics,
            items=filtered[:50],
            total_sources_checked=len(self._aggregator.sources),
        )

    async def propose_ideas(self, context: str) -> list[IdeaProposal]:
        log.info("proposing_ideas", context_length=len(context))
        keywords = [w.strip().lower() for w in context.split() if len(w.strip()) > 3]

        templates = [
            IdeaProposal(
                title=f"AI-Powered Automation for {context}",
                description=f"Leverage LLMs and agent frameworks to automate repetitive tasks in {context}.",
                feasibility="high",
                estimated_impact="high",
                required_resources=["LLM API access", "Domain data", "Evaluation pipeline"],
                related_technologies=["LangChain", "AutoGen", "CrewAI"],
                next_steps=["Define task scope", "Prototype with GPT-4", "Evaluate accuracy"],
            ),
            IdeaProposal(
                title=f"RAG Knowledge Base for {context}",
                description=(
                    f"Build a retrieval-augmented generation system to surface relevant knowledge for {context}."
                ),
                feasibility="medium",
                estimated_impact="high",
                required_resources=["Vector database", "Document corpus", "Embedding model"],
                related_technologies=["Pinecone", "Weaviate", "ChromaDB", "OpenAI Embeddings"],
                next_steps=["Collect documents", "Chunk and embed", "Build retrieval pipeline"],
            ),
            IdeaProposal(
                title=f"Multi-Agent Workflow for {context}",
                description=f"Design a multi-agent system where specialized agents collaborate to handle {context}.",
                feasibility="medium",
                estimated_impact="medium",
                required_resources=["Agent framework", "Task definitions", "Orchestration layer"],
                related_technologies=["MCP", "AutoGen", "LangGraph"],
                next_steps=["Identify sub-tasks", "Define agent roles", "Implement orchestration"],
            ),
        ]

        if any(k in keywords for k in ["image", "vision", "visual", "design"]):
            templates.append(
                IdeaProposal(
                    title=f"Computer Vision Pipeline for {context}",
                    description=f"Apply vision models to extract insights from visual data in {context}.",
                    feasibility="medium",
                    estimated_impact="medium",
                    required_resources=["GPU compute", "Training data", "Vision model"],
                    related_technologies=["YOLO", "SAM", "CLIP", "Stable Diffusion"],
                    next_steps=["Collect visual data", "Fine-tune model", "Deploy inference endpoint"],
                )
            )

        return templates

    async def suggest_workflows(self, current_workflow: str) -> list[WorkflowOptimization]:
        log.info("suggesting_workflows", workflow_length=len(current_workflow))
        return [
            WorkflowOptimization(
                area="Code Generation",
                current_pain_point="Manual coding of boilerplate and repetitive patterns",
                proposed_improvement="Use AI code assistants with custom prompts and context injection",
                tools_suggested=["GitHub Copilot", "Cursor", "Aider", "Continue.dev"],
                expected_time_savings="30-50% on boilerplate tasks",
                implementation_complexity="low",
            ),
            WorkflowOptimization(
                area="Documentation",
                current_pain_point="Documentation falls out of date with code changes",
                proposed_improvement="Auto-generate docs from code with LLM summarization and CI hooks",
                tools_suggested=["Mintlify", "Docusaurus + LLM", "Sphinx + GPT"],
                expected_time_savings="60-70% on documentation maintenance",
                implementation_complexity="medium",
            ),
            WorkflowOptimization(
                area="Testing",
                current_pain_point="Insufficient test coverage and slow test authoring",
                proposed_improvement="AI-assisted test generation with mutation testing validation",
                tools_suggested=["CodiumAI", "Diffblue", "pytest-ai"],
                expected_time_savings="40-60% on test writing",
                implementation_complexity="medium",
            ),
            WorkflowOptimization(
                area="Code Review",
                current_pain_point="Slow review cycles and inconsistent feedback quality",
                proposed_improvement="Automated pre-review with AI that flags issues before human review",
                tools_suggested=["CodeRabbit", "Graphite", "Sourcery"],
                expected_time_savings="20-30% reduction in review cycles",
                implementation_complexity="low",
            ),
        ]

    async def analyze_ai_tools(self, domain: str) -> ToolAnalysis:
        log.info("analyzing_ai_tools", domain=domain)
        domain_tools: dict[str, list[ToolEntry]] = {
            "nlp": [
                ToolEntry(
                    name="OpenAI GPT-4",
                    url="https://platform.openai.com",
                    description="State-of-the-art LLM for text generation and understanding",
                    strengths=["Broad knowledge", "Strong reasoning", "Function calling"],
                    weaknesses=["Cost at scale", "Rate limits", "Data privacy concerns"],
                    pricing_model="Pay-per-token",
                    best_for="Complex reasoning and generation tasks",
                ),
                ToolEntry(
                    name="Anthropic Claude",
                    url="https://anthropic.com",
                    description="Safety-focused LLM with large context window",
                    strengths=["200k context", "Strong instruction following", "Safety"],
                    weaknesses=["Smaller ecosystem", "Availability"],
                    pricing_model="Pay-per-token",
                    best_for="Long document analysis and safe deployments",
                ),
            ],
            "vision": [
                ToolEntry(
                    name="OpenAI DALL-E 3",
                    url="https://platform.openai.com",
                    description="Text-to-image generation model",
                    strengths=["Prompt adherence", "Quality", "Safety filters"],
                    weaknesses=["Cost", "Limited editing"],
                    pricing_model="Pay-per-image",
                    best_for="Marketing and creative content",
                ),
            ],
            "default": [
                ToolEntry(
                    name="Hugging Face Transformers",
                    url="https://huggingface.co",
                    description="Open-source ML model hub and library",
                    strengths=["Open source", "Huge model library", "Community"],
                    weaknesses=["Requires ML expertise", "Self-hosting needed"],
                    pricing_model="Free / Inference API paid",
                    best_for="Custom model deployment and research",
                ),
            ],
        }

        tools = domain_tools.get(domain.lower(), domain_tools["default"])
        return ToolAnalysis(
            domain=domain,
            tools=tools,
            recommendation=(
                f"For {domain}, start with managed APIs for prototyping, "
                "then evaluate open-source alternatives for production cost optimization."
            ),
        )

    async def generate_optimization_plan(self, process: str) -> OptimizationPlan:
        log.info("generating_optimization_plan", process=process)
        return OptimizationPlan(
            process=process,
            current_state=f"Manual/semi-automated process for: {process}",
            target_state=f"AI-augmented, largely automated pipeline for: {process}",
            steps=[
                OptimizationStep(
                    order=1,
                    action="Audit Current Process",
                    description="Map existing workflow, identify bottlenecks and manual steps",
                    tools=["Process mapping tools", "Time tracking"],
                ),
                OptimizationStep(
                    order=2,
                    action="Identify AI Opportunities",
                    description="Match bottlenecks to available AI capabilities",
                    tools=["AI capability matrix"],
                    dependencies=[1],
                ),
                OptimizationStep(
                    order=3,
                    action="Prototype Solutions",
                    description="Build proof-of-concept for top-priority automations",
                    tools=["LLM APIs", "Agent frameworks", "Evaluation harness"],
                    dependencies=[2],
                ),
                OptimizationStep(
                    order=4,
                    action="Evaluate & Iterate",
                    description="Measure quality, latency, and cost against baselines",
                    tools=["A/B testing", "Metrics dashboards"],
                    dependencies=[3],
                ),
                OptimizationStep(
                    order=5,
                    action="Deploy & Monitor",
                    description="Roll out to production with observability and fallback paths",
                    tools=["CI/CD", "Monitoring", "Feature flags"],
                    dependencies=[4],
                ),
            ],
            expected_outcomes=[
                "Reduced manual effort by 40-70%",
                "Faster throughput for repetitive tasks",
                "Consistent quality through AI-assisted validation",
            ],
            risks=[
                "LLM hallucination in critical paths",
                "Cost overruns from API usage",
                "Change management resistance",
            ],
        )
