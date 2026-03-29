from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import structlog
from pydantic import BaseModel, Field

from .newsletter import NewsletterCompiler
from .scraper import PhysicalAIScraper

logger = structlog.get_logger(__name__)


class NewsItem(BaseModel):
    title: str
    url: str
    source: str
    summary: str
    published: datetime | None = None
    tags: list[str] = Field(default_factory=list)
    relevance_score: float = 0.0


class ResearchPaper(BaseModel):
    title: str
    authors: list[str]
    abstract: str
    arxiv_id: str
    url: str
    published: datetime | None = None
    categories: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)


class NewsletterSection(BaseModel):
    title: str
    items: list[NewsItem] = Field(default_factory=list)
    papers: list[ResearchPaper] = Field(default_factory=list)
    summary: str = ""


class Newsletter(BaseModel):
    title: str
    date: datetime
    sections: list[NewsletterSection] = Field(default_factory=list)
    html_content: str = ""
    markdown_content: str = ""
    topic_summary: str = ""


class AutomationIdea(BaseModel):
    title: str
    description: str
    feasibility: str
    estimated_impact: str
    required_technologies: list[str] = Field(default_factory=list)
    implementation_steps: list[str] = Field(default_factory=list)
    related_products: list[str] = Field(default_factory=list)


class StartupPlan(BaseModel):
    name: str
    domain: str
    problem_statement: str
    solution: str
    target_market: str
    competitive_landscape: str
    revenue_model: str
    key_milestones: list[str] = Field(default_factory=list)
    required_resources: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    agent_contributions: dict[str, str] = Field(default_factory=dict)


class CrossAgentReport(BaseModel):
    topic: str
    generated_at: datetime
    technical_analysis: str = ""
    market_analysis: str = ""
    ai_insights: str = ""
    business_strategy: str = ""
    physical_ai_perspective: str = ""
    recommendations: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)


class PhysicalAIAgent:
    def __init__(self) -> None:
        self.scraper = PhysicalAIScraper()
        self.newsletter_compiler = NewsletterCompiler()
        self.log = logger.bind(agent="physical_ai")

    async def scan_physical_ai_news(self) -> list[NewsItem]:
        self.log.info("scanning_physical_ai_news")
        raw_articles = await self.scraper.aggregate_news()
        items = []
        for article in raw_articles:
            item = NewsItem(
                title=article.get("title", ""),
                url=article.get("url", ""),
                source=article.get("source", ""),
                summary=article.get("summary", ""),
                published=article.get("published"),
                tags=article.get("tags", []),
                relevance_score=article.get("relevance_score", 0.0),
            )
            items.append(item)
        items.sort(key=lambda x: x.relevance_score, reverse=True)
        self.log.info("scan_complete", count=len(items))
        return items

    async def track_research_papers(self, keywords: list[str]) -> list[ResearchPaper]:
        self.log.info("tracking_research_papers", keywords=keywords)
        raw_papers = await self.scraper.scrape_arxiv(keywords=keywords)
        papers = []
        for paper in raw_papers:
            rp = ResearchPaper(
                title=paper.get("title", ""),
                authors=paper.get("authors", []),
                abstract=paper.get("abstract", ""),
                arxiv_id=paper.get("arxiv_id", ""),
                url=paper.get("url", ""),
                published=paper.get("published"),
                categories=paper.get("categories", []),
                keywords=paper.get("keywords", []),
            )
            papers.append(rp)
        self.log.info("papers_tracked", count=len(papers))
        return papers

    async def generate_daily_newsletter(self, topics: list[str]) -> Newsletter:
        self.log.info("generating_daily_newsletter", topics=topics)
        news_items, papers = await asyncio.gather(
            self.scan_physical_ai_news(),
            self.track_research_papers(keywords=topics),
        )

        sections = self._organize_sections(news_items, papers, topics)
        now = datetime.now(timezone.utc)

        newsletter = Newsletter(
            title=f"Physical AI Daily — {now.strftime('%B %d, %Y')}",
            date=now,
            sections=sections,
            topic_summary=f"Coverage of {len(topics)} topics with {len(news_items)} articles and {len(papers)} papers.",
        )

        newsletter.html_content = self.newsletter_compiler.format_html(newsletter)
        newsletter.markdown_content = self.newsletter_compiler.format_markdown(newsletter)

        self.log.info("newsletter_generated", sections=len(sections))
        return newsletter

    def _organize_sections(
        self,
        news_items: list[NewsItem],
        papers: list[ResearchPaper],
        topics: list[str],
    ) -> list[NewsletterSection]:
        headlines = [n for n in news_items if n.relevance_score >= 0.7]
        industry = [n for n in news_items if "industry" in n.tags or "company" in n.tags]
        startup_news = [n for n in news_items if "startup" in n.tags or "funding" in n.tags]
        remaining = [n for n in news_items if n not in headlines and n not in industry and n not in startup_news]

        sections = [
            NewsletterSection(
                title="Top Headlines",
                items=headlines[:10],
                summary=f"Top {min(len(headlines), 10)} stories in Physical AI today.",
            ),
            NewsletterSection(
                title="Research & Papers",
                papers=papers[:10],
                summary=f"Latest research across {', '.join(topics[:5])}.",
            ),
            NewsletterSection(
                title="Industry News",
                items=industry[:10],
                summary="Updates from the Physical AI industry.",
            ),
            NewsletterSection(
                title="Startups & Funding",
                items=startup_news[:10],
                summary="Startup ecosystem and funding rounds.",
            ),
            NewsletterSection(
                title="More Stories",
                items=remaining[:10],
                summary="Additional coverage and analysis.",
            ),
        ]
        return [s for s in sections if s.items or s.papers]

    async def propose_automation_ideas(self, routines: list[str]) -> list[AutomationIdea]:
        self.log.info("proposing_automation_ideas", routines=routines)
        ideas = []
        for routine in routines:
            idea = AutomationIdea(
                title=f"Automate: {routine}",
                description=f"Apply Physical AI and robotics to automate '{routine}' "
                f"using sensor fusion, computer vision, and robotic manipulation.",
                feasibility="medium",
                estimated_impact="high",
                required_technologies=self._suggest_technologies(routine),
                implementation_steps=[
                    f"Analyze current workflow for '{routine}'",
                    "Identify repetitive sub-tasks suitable for automation",
                    "Design sensor and actuator requirements",
                    "Prototype with simulation (Isaac Sim / MuJoCo)",
                    "Develop control policies with reinforcement learning",
                    "Deploy and iterate with human-in-the-loop feedback",
                ],
                related_products=self._suggest_products(routine),
            )
            ideas.append(idea)
        self.log.info("automation_ideas_proposed", count=len(ideas))
        return ideas

    def _suggest_technologies(self, routine: str) -> list[str]:
        base = ["Computer Vision", "ROS 2", "SLAM", "Reinforcement Learning"]
        routine_lower = routine.lower()
        if any(w in routine_lower for w in ("pick", "sort", "assemble", "pack")):
            base.extend(["Robotic Manipulation", "Force/Torque Sensing", "Grasp Planning"])
        if any(w in routine_lower for w in ("navigate", "deliver", "transport", "move")):
            base.extend(["Autonomous Navigation", "LiDAR", "Path Planning"])
        if any(w in routine_lower for w in ("inspect", "monitor", "check", "quality")):
            base.extend(["Anomaly Detection", "Thermal Imaging", "Edge AI"])
        return base

    def _suggest_products(self, routine: str) -> list[str]:
        products = ["NVIDIA Isaac", "Boston Dynamics Spot", "Universal Robots"]
        routine_lower = routine.lower()
        if any(w in routine_lower for w in ("warehouse", "logistics", "deliver")):
            products.extend(["Amazon Robotics", "Locus Robotics", "Fetch Robotics"])
        if any(w in routine_lower for w in ("manufacture", "assemble", "weld")):
            products.extend(["FANUC", "ABB Robotics", "KUKA"])
        return products

    async def startup_ideation(self, domain: str) -> StartupPlan:
        self.log.info("startup_ideation", domain=domain)
        news_items = await self.scan_physical_ai_news()
        trending_tags = self._extract_trending_tags(news_items)

        plan = StartupPlan(
            name=f"PhysicalAI-{domain.replace(' ', '-').title()}",
            domain=domain,
            problem_statement=(
                f"Current solutions in '{domain}' lack intelligent physical automation. "
                f"Manual processes remain slow, error-prone, and costly."
            ),
            solution=(
                f"An AI-powered physical automation platform for '{domain}' that combines "
                f"embodied AI agents, robotic systems, and real-time perception to autonomously "
                f"handle complex physical tasks."
            ),
            target_market=f"Enterprises and SMBs in the {domain} sector seeking automation",
            competitive_landscape=(
                f"Emerging market with few integrated solutions. Key trends: {', '.join(trending_tags[:5])}."
            ),
            revenue_model="SaaS platform fees + per-robot licensing + professional services",
            key_milestones=[
                "Validate problem-solution fit with 5 pilot customers",
                "Build MVP with simulation-first approach",
                "Secure seed funding ($2-5M)",
                "Deploy first physical systems at pilot sites",
                "Achieve product-market fit and expand",
            ],
            required_resources=[
                "Robotics engineers (3-5)",
                "ML/AI researchers (2-3)",
                "Full-stack developers (2)",
                "Business development (1-2)",
                f"Domain experts in {domain} (1-2)",
            ],
            risks=[
                "Hardware supply chain constraints",
                "Regulatory compliance in physical automation",
                "Long sales cycles in enterprise robotics",
                "Safety certification requirements",
            ],
            agent_contributions={
                "sw_architect": "System architecture design and technical stack selection",
                "generative_ai": "AI model selection, training pipelines, and prompt engineering",
                "business_developer": "Market analysis, pitch decks, and go-to-market strategy",
                "physical_ai": "Robotics expertise, hardware integration, and automation workflows",
            },
        )
        self.log.info("startup_plan_generated", name=plan.name)
        return plan

    def _extract_trending_tags(self, news_items: list[NewsItem]) -> list[str]:
        tag_counts: dict[str, int] = {}
        for item in news_items:
            for tag in item.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        return sorted(tag_counts, key=tag_counts.get, reverse=True)[:10]  # type: ignore[arg-type]

    async def cross_agent_analysis(self, topic: str) -> CrossAgentReport:
        self.log.info("cross_agent_analysis", topic=topic)
        news_items = await self.scan_physical_ai_news()
        relevant = [n for n in news_items if topic.lower() in n.title.lower() or topic.lower() in n.summary.lower()]

        report = CrossAgentReport(
            topic=topic,
            generated_at=datetime.now(timezone.utc),
            technical_analysis=(
                f"Technical assessment of '{topic}' in Physical AI: "
                f"Found {len(relevant)} directly relevant articles. "
                "Key technical considerations include sensor integration, "
                "real-time control systems, and safety-critical software design."
            ),
            market_analysis=(
                f"Market analysis for '{topic}': The Physical AI market is projected "
                "to grow significantly. Key drivers include labor shortages, "
                "advances in foundation models for robotics, and decreasing hardware costs."
            ),
            ai_insights=(
                f"AI perspective on '{topic}': Foundation models are increasingly being applied "
                "to physical systems. Key developments include vision-language-action models, "
                "sim-to-real transfer learning, and multi-modal perception systems."
            ),
            business_strategy=(
                f"Business strategy for '{topic}': Focus on high-value verticals first, "
                "build strong IP moat, and leverage partnerships with hardware OEMs. "
                "Consider both SaaS and robotics-as-a-service business models."
            ),
            physical_ai_perspective=(
                f"Physical AI lens on '{topic}': Embodied intelligence requires tight integration "
                "of perception, planning, and action. Key challenges include real-world variability, "
                "safety guarantees, and human-robot interaction design."
            ),
            recommendations=[
                f"Conduct deep-dive technical feasibility study on '{topic}'",
                "Engage with 10+ potential customers for problem validation",
                "Build simulation environment for rapid prototyping",
                "Establish partnerships with robotics hardware providers",
                "File provisional patents on novel approaches",
            ],
            sources=[item.url for item in relevant[:10]],
        )
        self.log.info("cross_agent_report_generated", topic=topic, sources=len(report.sources))
        return report
