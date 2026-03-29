from __future__ import annotations

from datetime import datetime, timezone

import structlog
from pydantic import BaseModel, Field

from .sub_agents import (
    FinancialAnalystAgent,
    LegalComplianceAgent,
    MarketingStrategyAgent,
    MarketResearchAgent,
    SalesStrategyAgent,
)

log = structlog.get_logger()


class BusinessAnalysis(BaseModel):
    idea: str
    value_proposition: str
    target_audience: str
    market_opportunity: str
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    threats: list[str] = Field(default_factory=list)
    feasibility_score: float = Field(ge=0.0, le=10.0)
    recommendation: str = ""
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RevenueStream(BaseModel):
    name: str
    description: str
    pricing_model: str
    estimated_monthly_revenue: float = 0.0


class BusinessModel(BaseModel):
    name: str
    key_partners: list[str] = Field(default_factory=list)
    key_activities: list[str] = Field(default_factory=list)
    key_resources: list[str] = Field(default_factory=list)
    value_propositions: list[str] = Field(default_factory=list)
    customer_segments: list[str] = Field(default_factory=list)
    customer_relationships: list[str] = Field(default_factory=list)
    channels: list[str] = Field(default_factory=list)
    revenue_streams: list[RevenueStream] = Field(default_factory=list)
    cost_structure: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MarketResearch(BaseModel):
    industry: str
    target_market: str
    market_size_usd: str = ""
    growth_rate: str = ""
    key_trends: list[str] = Field(default_factory=list)
    customer_personas: list[CustomerPersona] = Field(default_factory=list)
    barriers_to_entry: list[str] = Field(default_factory=list)
    regulatory_landscape: str = ""


class CustomerPersona(BaseModel):
    name: str
    demographics: str
    pain_points: list[str] = Field(default_factory=list)
    needs: list[str] = Field(default_factory=list)
    buying_behavior: str = ""


class FinancialProjection(BaseModel):
    model_name: str
    currency: str = "USD"
    monthly_burn_rate: float = 0.0
    breakeven_months: int = 0
    year_1: YearProjection | None = None
    year_2: YearProjection | None = None
    year_3: YearProjection | None = None
    key_assumptions: list[str] = Field(default_factory=list)
    funding_required: float = 0.0


class YearProjection(BaseModel):
    revenue: float = 0.0
    costs: float = 0.0
    profit: float = 0.0
    customers: int = 0
    growth_rate_pct: float = 0.0


class PitchDeck(BaseModel):
    company_name: str
    tagline: str
    slides: list[PitchSlide] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PitchSlide(BaseModel):
    order: int
    title: str
    content: str
    speaker_notes: str = ""


class Competitor(BaseModel):
    name: str
    description: str
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    market_share: str = ""
    funding: str = ""


class CompetitiveAnalysis(BaseModel):
    industry: str
    competitors: list[Competitor] = Field(default_factory=list)
    market_gaps: list[str] = Field(default_factory=list)
    differentiation_opportunities: list[str] = Field(default_factory=list)
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


MarketResearch.model_rebuild()
FinancialProjection.model_rebuild()


class BusinessDeveloperAgent:
    def __init__(self) -> None:
        self._market_research = MarketResearchAgent()
        self._financial = FinancialAnalystAgent()
        self._marketing = MarketingStrategyAgent()
        self._legal = LegalComplianceAgent()
        self._sales = SalesStrategyAgent()

    async def analyze_business_idea(self, idea: str) -> BusinessAnalysis:
        log.info("analyzing_business_idea", idea_length=len(idea))

        market_data = await self._market_research.execute(f"Assess market for: {idea}")
        legal_data = await self._legal.execute(f"Legal considerations for: {idea}")

        return BusinessAnalysis(
            idea=idea,
            value_proposition=f"Solving key pain points in the domain of: {idea}",
            target_audience="Early adopters and SMBs in the target vertical",
            market_opportunity=market_data.get("summary", "Growing market with significant untapped potential"),
            strengths=[
                "Novel approach to an existing problem",
                "Leverages current technology trends",
                "Scalable digital-first model",
            ],
            weaknesses=[
                "Unproven market demand at scale",
                "Requires initial capital investment",
                "Competitive landscape uncertainty",
            ],
            opportunities=[
                "First-mover advantage in niche segment",
                "Partnership potential with established players",
                "Expansion into adjacent markets",
            ],
            threats=[
                "Well-funded competitors may pivot",
                "Regulatory changes",
                "Technology risk",
                *(legal_data.get("risks", [])),
            ],
            feasibility_score=7.0,
            recommendation=(
                "Proceed with lean MVP approach, validate core assumptions with target customers before scaling."
            ),
        )

    async def create_business_model(self, analysis: BusinessAnalysis) -> BusinessModel:
        log.info("creating_business_model", idea=analysis.idea)

        await self._sales.execute(f"Sales strategy for: {analysis.idea}")
        marketing_data = await self._marketing.execute(f"Go-to-market for: {analysis.idea}")

        return BusinessModel(
            name=analysis.idea,
            key_partners=[
                "Technology providers",
                "Distribution partners",
                "Industry consultants",
            ],
            key_activities=[
                "Product development",
                "Customer acquisition",
                "Platform maintenance",
                "Data analysis",
            ],
            key_resources=[
                "Engineering team",
                "Domain expertise",
                "Technology infrastructure",
                "Customer data",
            ],
            value_propositions=analysis.strengths[:3],
            customer_segments=[analysis.target_audience, "Enterprise clients", "Freelancers and consultants"],
            customer_relationships=[
                "Self-service platform",
                "Dedicated account management for enterprise",
                "Community forums",
            ],
            channels=marketing_data.get("channels", ["Direct sales", "Content marketing", "Partnerships"]),
            revenue_streams=[
                RevenueStream(
                    name="Subscription",
                    description="Monthly/annual SaaS subscription",
                    pricing_model="Tiered pricing",
                    estimated_monthly_revenue=50000.0,
                ),
                RevenueStream(
                    name="Enterprise Licensing",
                    description="Custom enterprise deployments",
                    pricing_model="Per-seat licensing",
                    estimated_monthly_revenue=30000.0,
                ),
                RevenueStream(
                    name="Professional Services",
                    description="Consulting and implementation services",
                    pricing_model="Hourly/project-based",
                    estimated_monthly_revenue=20000.0,
                ),
            ],
            cost_structure=[
                "Engineering salaries (40%)",
                "Cloud infrastructure (15%)",
                "Sales & marketing (25%)",
                "Operations & admin (20%)",
            ],
        )

    async def market_research(self, industry: str, target: str) -> MarketResearch:
        log.info("conducting_market_research", industry=industry, target=target)

        raw = await self._market_research.execute(f"Market research: {industry} targeting {target}")

        return MarketResearch(
            industry=industry,
            target_market=target,
            market_size_usd=raw.get("market_size", "$10B+ TAM"),
            growth_rate=raw.get("growth_rate", "15-25% CAGR"),
            key_trends=[
                "Digital transformation acceleration",
                "AI/ML integration across workflows",
                "Shift to subscription/usage-based models",
                "Increased demand for automation",
                "Growing emphasis on data privacy",
            ],
            customer_personas=[
                CustomerPersona(
                    name="Tech-Savvy Startup Founder",
                    demographics="25-40, technical background, urban",
                    pain_points=["Limited resources", "Need to move fast", "Scaling challenges"],
                    needs=["Automation", "Cost-effective tools", "Quick time-to-value"],
                    buying_behavior="Online research, peer recommendations, free trials",
                ),
                CustomerPersona(
                    name="Enterprise Decision Maker",
                    demographics="35-55, management role, enterprise company",
                    pain_points=["Legacy systems", "Compliance requirements", "Integration complexity"],
                    needs=["Reliability", "Security", "Support SLAs"],
                    buying_behavior="RFP process, vendor evaluation, proof of concept",
                ),
            ],
            barriers_to_entry=[
                "High initial R&D investment",
                "Established competitor relationships",
                "Regulatory compliance requirements",
                "Data network effects",
            ],
            regulatory_landscape=raw.get(
                "regulations",
                "Standard industry regulations apply; data privacy (GDPR/CCPA) compliance required.",
            ),
        )

    async def financial_projection(self, model: BusinessModel) -> FinancialProjection:
        log.info("creating_financial_projection", model=model.name)

        await self._financial.execute(f"Financial projection for: {model.name}")

        total_monthly = sum(rs.estimated_monthly_revenue for rs in model.revenue_streams)

        return FinancialProjection(
            model_name=model.name,
            monthly_burn_rate=80000.0,
            breakeven_months=18,
            year_1=YearProjection(
                revenue=total_monthly * 12 * 0.3,
                costs=80000.0 * 12,
                profit=total_monthly * 12 * 0.3 - 80000.0 * 12,
                customers=500,
                growth_rate_pct=0.0,
            ),
            year_2=YearProjection(
                revenue=total_monthly * 12 * 1.0,
                costs=100000.0 * 12,
                profit=total_monthly * 12 * 1.0 - 100000.0 * 12,
                customers=2000,
                growth_rate_pct=300.0,
            ),
            year_3=YearProjection(
                revenue=total_monthly * 12 * 2.5,
                costs=150000.0 * 12,
                profit=total_monthly * 12 * 2.5 - 150000.0 * 12,
                customers=8000,
                growth_rate_pct=300.0,
            ),
            key_assumptions=[
                "30% of target revenue achieved in year 1",
                "3x year-over-year customer growth",
                "Average revenue per customer increases 20% annually",
                "Operating costs grow at 25% annually",
            ],
            funding_required=1500000.0,
        )

    async def create_pitch_deck(self, model: BusinessModel) -> PitchDeck:
        log.info("creating_pitch_deck", model=model.name)

        revenue_summary = ", ".join(rs.name for rs in model.revenue_streams)

        return PitchDeck(
            company_name=model.name,
            tagline="Transforming the industry through intelligent automation",
            slides=[
                PitchSlide(
                    order=1,
                    title="The Problem",
                    content="Current solutions are fragmented, manual, and fail to scale. "
                    "Businesses lose significant time and revenue to inefficient processes.",
                    speaker_notes="Open with a compelling customer story that illustrates the pain point.",
                ),
                PitchSlide(
                    order=2,
                    title="Our Solution",
                    content=f"Value propositions: {', '.join(model.value_propositions)}. "
                    "An integrated platform that automates and optimizes the entire workflow.",
                    speaker_notes="Demo the product or show key screenshots.",
                ),
                PitchSlide(
                    order=3,
                    title="Market Opportunity",
                    content="Large and growing addressable market with strong tailwinds from digital transformation. "
                    f"Target segments: {', '.join(model.customer_segments)}.",
                    speaker_notes="Reference credible market research and size estimates.",
                ),
                PitchSlide(
                    order=4,
                    title="Business Model",
                    content=f"Revenue streams: {revenue_summary}. "
                    f"Key channels: {', '.join(model.channels)}.",
                    speaker_notes="Walk through unit economics and path to profitability.",
                ),
                PitchSlide(
                    order=5,
                    title="Traction",
                    content="Early validation through pilot customers and growing pipeline. "
                    "Key metrics trending positively across engagement and retention.",
                    speaker_notes="Share specific numbers if available: MRR, users, growth rate.",
                ),
                PitchSlide(
                    order=6,
                    title="Team",
                    content="Experienced team with deep domain expertise and strong technical background. "
                    f"Key partners: {', '.join(model.key_partners)}.",
                    speaker_notes="Highlight relevant experience and complementary skills.",
                ),
                PitchSlide(
                    order=7,
                    title="The Ask",
                    content="Seeking seed funding to accelerate product development and go-to-market. "
                    "Funds will be allocated to engineering, sales, and infrastructure.",
                    speaker_notes="Be specific about the amount, use of funds, and milestones.",
                ),
            ],
        )

    async def competitive_analysis(self, industry: str) -> CompetitiveAnalysis:
        log.info("competitive_analysis", industry=industry)

        await self._market_research.execute(f"Competitive landscape: {industry}")

        return CompetitiveAnalysis(
            industry=industry,
            competitors=[
                Competitor(
                    name=f"{industry} Market Leader",
                    description="Established incumbent with broad market presence",
                    strengths=["Brand recognition", "Large customer base", "Deep pockets"],
                    weaknesses=["Slow innovation", "Legacy technology", "High prices"],
                    market_share="35%",
                    funding="Public company",
                ),
                Competitor(
                    name=f"{industry} Challenger",
                    description="Well-funded startup disrupting with modern approach",
                    strengths=["Modern tech stack", "Strong UX", "Aggressive growth"],
                    weaknesses=["Limited track record", "Narrow feature set", "High burn rate"],
                    market_share="10%",
                    funding="Series B ($50M)",
                ),
                Competitor(
                    name=f"{industry} Niche Player",
                    description="Specialized solution for a specific sub-segment",
                    strengths=["Deep domain expertise", "Loyal niche following", "Profitability"],
                    weaknesses=["Limited scale", "Small team", "Narrow market"],
                    market_share="5%",
                    funding="Bootstrapped",
                ),
            ],
            market_gaps=[
                "Lack of integrated end-to-end solutions",
                "Poor automation of manual processes",
                "Limited AI/ML capabilities in existing tools",
                "Underserved mid-market segment",
            ],
            differentiation_opportunities=[
                "AI-native platform architecture",
                "Superior user experience and onboarding",
                "Vertical-specific customization",
                "Usage-based pricing aligned with value delivery",
            ],
        )
