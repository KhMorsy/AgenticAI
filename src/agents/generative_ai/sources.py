from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

import feedparser
import httpx
import structlog
from bs4 import BeautifulSoup
from pydantic import BaseModel

log = structlog.get_logger()


class SourceCategory(StrEnum):
    RESEARCH = "research"
    INDUSTRY = "industry"
    TOOLS = "tools"
    TUTORIALS = "tutorials"


class AISource(BaseModel):
    name: str
    url: str
    feed_url: str | None = None
    category: SourceCategory
    enabled: bool = True


AI_SOURCES: list[AISource] = [
    AISource(
        name="ArXiv CS.AI",
        url="https://arxiv.org/list/cs.AI/recent",
        feed_url="https://rss.arxiv.org/rss/cs.AI",
        category=SourceCategory.RESEARCH,
    ),
    AISource(
        name="ArXiv CS.LG",
        url="https://arxiv.org/list/cs.LG/recent",
        feed_url="https://rss.arxiv.org/rss/cs.LG",
        category=SourceCategory.RESEARCH,
    ),
    AISource(
        name="ArXiv CS.CL",
        url="https://arxiv.org/list/cs.CL/recent",
        feed_url="https://rss.arxiv.org/rss/cs.CL",
        category=SourceCategory.RESEARCH,
    ),
    AISource(
        name="Hugging Face Blog",
        url="https://huggingface.co/blog",
        feed_url="https://huggingface.co/blog/feed.xml",
        category=SourceCategory.TOOLS,
    ),
    AISource(
        name="OpenAI Blog",
        url="https://openai.com/blog",
        feed_url=None,
        category=SourceCategory.INDUSTRY,
    ),
    AISource(
        name="Anthropic Blog",
        url="https://www.anthropic.com/blog",
        feed_url=None,
        category=SourceCategory.INDUSTRY,
    ),
    AISource(
        name="Google AI Blog",
        url="https://blog.google/technology/ai/",
        feed_url="https://blog.google/technology/ai/rss/",
        category=SourceCategory.INDUSTRY,
    ),
    AISource(
        name="Meta AI Blog",
        url="https://ai.meta.com/blog/",
        feed_url=None,
        category=SourceCategory.RESEARCH,
    ),
    AISource(
        name="DeepMind Blog",
        url="https://deepmind.google/discover/blog/",
        feed_url=None,
        category=SourceCategory.RESEARCH,
    ),
    AISource(
        name="Microsoft AI Blog",
        url="https://blogs.microsoft.com/ai/",
        feed_url="https://blogs.microsoft.com/ai/feed/",
        category=SourceCategory.INDUSTRY,
    ),
    AISource(
        name="Towards Data Science",
        url="https://towardsdatascience.com",
        feed_url="https://towardsdatascience.com/feed",
        category=SourceCategory.TUTORIALS,
    ),
    AISource(
        name="MIT Technology Review - AI",
        url="https://www.technologyreview.com/topic/artificial-intelligence/",
        feed_url="https://www.technologyreview.com/topic/artificial-intelligence/feed",
        category=SourceCategory.INDUSTRY,
    ),
    AISource(
        name="Papers With Code",
        url="https://paperswithcode.com",
        feed_url=None,
        category=SourceCategory.RESEARCH,
    ),
    AISource(
        name="The Batch (Andrew Ng)",
        url="https://www.deeplearning.ai/the-batch/",
        feed_url=None,
        category=SourceCategory.TUTORIALS,
    ),
    AISource(
        name="AI News - VentureBeat",
        url="https://venturebeat.com/category/ai/",
        feed_url="https://venturebeat.com/category/ai/feed/",
        category=SourceCategory.INDUSTRY,
    ),
]


RawNewsItem = dict[str, Any]


def _parse_rss_date(entry: dict[str, Any]) -> datetime | None:
    published = entry.get("published_parsed") or entry.get("updated_parsed")
    if published:
        try:
            from time import mktime
            return datetime.fromtimestamp(mktime(published), tz=timezone.utc)
        except Exception:
            return None
    return None


class AISourceAggregator:
    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        sources: list[AISource] | None = None,
    ) -> None:
        self._client = client or httpx.AsyncClient(timeout=20.0)
        self.sources = sources or [s for s in AI_SOURCES if s.enabled]

    async def fetch_all(self) -> list[RawNewsItem]:
        tasks = [self._fetch_source(src) for src in self.sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        items: list[RawNewsItem] = []
        for src, result in zip(self.sources, results):
            if isinstance(result, Exception):
                log.warning("source_fetch_failed", source=src.name, error=str(result))
                continue
            items.extend(result)

        items.sort(key=lambda x: x.get("published") or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        return items

    async def _fetch_source(self, source: AISource) -> list[RawNewsItem]:
        if source.feed_url:
            return await self._fetch_rss(source)
        return await self._scrape_page(source)

    async def _fetch_rss(self, source: AISource) -> list[RawNewsItem]:
        assert source.feed_url is not None
        log.debug("fetching_rss", source=source.name, url=source.feed_url)
        response = await self._client.get(source.feed_url)
        response.raise_for_status()

        feed = feedparser.parse(response.text)
        items: list[RawNewsItem] = []
        for entry in feed.entries[:20]:
            items.append({
                "title": entry.get("title", ""),
                "url": entry.get("link", ""),
                "source": source.name,
                "summary": entry.get("summary", "")[:500],
                "published": _parse_rss_date(entry),
                "category": source.category,
            })
        return items

    async def _scrape_page(self, source: AISource) -> list[RawNewsItem]:
        log.debug("scraping_page", source=source.name, url=source.url)
        try:
            response = await self._client.get(source.url, follow_redirects=True)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            log.warning("scrape_failed", source=source.name, error=str(exc))
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        items: list[RawNewsItem] = []

        for tag in soup.find_all(["h2", "h3", "article"], limit=15):
            link = tag.find("a")
            if not link:
                continue
            href = link.get("href", "")
            if href and not href.startswith("http"):
                href = source.url.rstrip("/") + "/" + href.lstrip("/")
            title = link.get_text(strip=True)
            if not title:
                continue
            items.append({
                "title": title,
                "url": href,
                "source": source.name,
                "summary": "",
                "published": None,
                "category": source.category,
            })

        return items

    async def fetch_by_category(self, category: SourceCategory) -> list[RawNewsItem]:
        filtered = [s for s in self.sources if s.category == category]
        agg = AISourceAggregator(client=self._client, sources=filtered)
        return await agg.fetch_all()

    def list_sources(self, category: SourceCategory | None = None) -> list[AISource]:
        if category is None:
            return list(self.sources)
        return [s for s in self.sources if s.category == category]
