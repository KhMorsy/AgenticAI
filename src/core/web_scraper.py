from __future__ import annotations

import asyncio
from typing import Any

import feedparser
import httpx
import structlog
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = structlog.get_logger(__name__)


class ScrapedPage(BaseModel):
    url: str
    status_code: int
    title: str = ""
    text: str = ""
    links: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RSSEntry(BaseModel):
    title: str = ""
    link: str = ""
    summary: str = ""
    published: str = ""
    author: str = ""


class RSSFeed(BaseModel):
    title: str = ""
    link: str = ""
    entries: list[RSSEntry] = Field(default_factory=list)


class SearchResult(BaseModel):
    title: str = ""
    url: str = ""
    snippet: str = ""


class WebScraper:
    """Async web-scraping toolkit with rate limiting and retries."""

    def __init__(
        self,
        *,
        max_concurrent: int = 5,
        timeout: float = 30.0,
        user_agent: str = "AgenticSystem/1.0",
    ) -> None:
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._timeout = timeout
        self._user_agent = user_agent
        self._log = logger.bind(component="web_scraper")

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=self._timeout,
            headers={"User-Agent": self._user_agent},
            follow_redirects=True,
        )

    @retry(
        retry=retry_if_exception_type((httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=15),
        reraise=True,
    )
    async def fetch_url(self, url: str) -> ScrapedPage:
        async with self._semaphore, self._client() as client:
            self._log.info("fetch.start", url=url)
            response = await client.get(url)
            response.raise_for_status()
            page = self.parse_html(response.text, url=url, status_code=response.status_code)
            self._log.info("fetch.done", url=url, status=response.status_code)
            return page

    def parse_html(self, html: str, *, url: str = "", status_code: int = 200) -> ScrapedPage:
        soup = BeautifulSoup(html, "html.parser")

        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else ""

        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)

        links = [
            a["href"]
            for a in soup.find_all("a", href=True)
            if isinstance(a["href"], str) and a["href"].startswith("http")
        ]

        meta: dict[str, Any] = {}
        for tag in soup.find_all("meta"):
            name = tag.get("name") or tag.get("property", "")
            content = tag.get("content", "")
            if name and content:
                meta[str(name)] = content

        return ScrapedPage(
            url=url,
            status_code=status_code,
            title=title,
            text=text,
            links=links,
            metadata=meta,
        )

    @retry(
        retry=retry_if_exception_type((httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=15),
        reraise=True,
    )
    async def fetch_rss(self, feed_url: str) -> RSSFeed:
        async with self._semaphore, self._client() as client:
            self._log.info("rss.fetch", url=feed_url)
            response = await client.get(feed_url)
            response.raise_for_status()

        parsed = feedparser.parse(response.text)
        entries = [
            RSSEntry(
                title=e.get("title", ""),
                link=e.get("link", ""),
                summary=e.get("summary", ""),
                published=e.get("published", ""),
                author=e.get("author", ""),
            )
            for e in parsed.entries
        ]
        return RSSFeed(
            title=parsed.feed.get("title", ""),
            link=parsed.feed.get("link", ""),
            entries=entries,
        )

    async def search_web(self, query: str, *, num_results: int = 5) -> list[SearchResult]:
        """Basic web search via DuckDuckGo HTML.

        This is intentionally lightweight — production use should swap in a
        proper search API key (Google, Bing, Brave, etc.).
        """
        url = "https://html.duckduckgo.com/html/"
        params = {"q": query}

        async with self._semaphore, self._client() as client:
            self._log.info("search.start", query=query)
            response = await client.post(url, data=params)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        results: list[SearchResult] = []
        for item in soup.select(".result")[:num_results]:
            title_el = item.select_one(".result__title")
            snippet_el = item.select_one(".result__snippet")
            link_el = item.select_one(".result__url")
            results.append(
                SearchResult(
                    title=title_el.get_text(strip=True) if title_el else "",
                    url=link_el.get_text(strip=True) if link_el else "",
                    snippet=snippet_el.get_text(strip=True) if snippet_el else "",
                )
            )
        self._log.info("search.done", query=query, count=len(results))
        return results
