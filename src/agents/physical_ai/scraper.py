from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from typing import Any
from xml.etree import ElementTree

import httpx
import structlog
from bs4 import BeautifulSoup

logger = structlog.get_logger(__name__)

NEWS_SOURCES: list[dict[str, str]] = [
    {
        "name": "IEEE Spectrum Robotics",
        "url": "https://spectrum.ieee.org/feeds/topic/robotics.rss",
        "type": "rss",
    },
    {
        "name": "MIT Technology Review - AI",
        "url": "https://www.technologyreview.com/feed/",
        "type": "rss",
    },
    {
        "name": "The Robot Report",
        "url": "https://www.therobotreport.com/feed/",
        "type": "rss",
    },
    {
        "name": "ROS Discourse",
        "url": "https://discourse.ros.org/latest.rss",
        "type": "rss",
    },
]

ARXIV_BASE_URL = "https://export.arxiv.org/api/query"

INDUSTRY_BLOGS: list[dict[str, str]] = [
    {
        "name": "NVIDIA Robotics Blog",
        "url": "https://blogs.nvidia.com/blog/category/robotics/feed/",
        "type": "rss",
    },
    {
        "name": "Boston Dynamics Blog",
        "url": "https://bostondynamics.com/blog/",
        "type": "html",
    },
    {
        "name": "DeepMind Blog",
        "url": "https://deepmind.google/blog/rss.xml",
        "type": "rss",
    },
    {
        "name": "OpenAI Blog",
        "url": "https://openai.com/blog/rss.xml",
        "type": "rss",
    },
]

SOCIAL_PATTERNS: list[dict[str, str]] = [
    {"platform": "twitter", "query": "physical AI robotics embodied intelligence"},
    {"platform": "linkedin", "query": "physical AI startup robotics automation"},
]

PHYSICAL_AI_TAGS = [
    "robotics", "embodied-ai", "physical-ai", "manipulation",
    "autonomous", "navigation", "perception", "sim-to-real",
    "reinforcement-learning", "foundation-model", "humanoid",
]


class PhysicalAIScraper:
    def __init__(self, timeout: float = 30.0, max_concurrent: int = 5) -> None:
        self.timeout = timeout
        self.max_concurrent = max_concurrent
        self.log = logger.bind(component="scraper")
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def _fetch(self, url: str) -> str | None:
        async with self._semaphore:
            try:
                async with httpx.AsyncClient(
                    timeout=self.timeout,
                    follow_redirects=True,
                    headers={"User-Agent": "PhysicalAI-Agent/1.0 (research newsletter bot)"},
                ) as client:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    return resp.text
            except httpx.HTTPError as exc:
                self.log.warning("fetch_failed", url=url, error=str(exc))
                return None

    def _parse_rss(self, xml_text: str, source_name: str) -> list[dict[str, Any]]:
        articles: list[dict[str, Any]] = []
        try:
            root = ElementTree.fromstring(xml_text)
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            items = root.findall(".//item") or root.findall(".//atom:entry", ns)
            for item in items:
                title = self._xml_text(item, "title", ns)
                link = self._xml_text(item, "link", ns) or self._xml_attr(item, "link", "href", ns)
                description = self._xml_text(item, "description", ns) or self._xml_text(item, "summary", ns)
                pub_date = self._xml_text(item, "pubDate", ns) or self._xml_text(item, "updated", ns)
                published = self._parse_date(pub_date) if pub_date else None

                if title:
                    articles.append({
                        "title": self._clean_html(title),
                        "url": link or "",
                        "source": source_name,
                        "summary": self._clean_html(description or "")[:500],
                        "published": published,
                        "tags": self._extract_tags(title, description or ""),
                        "relevance_score": self._compute_relevance(title, description or ""),
                    })
        except ElementTree.ParseError as exc:
            self.log.warning("rss_parse_failed", source=source_name, error=str(exc))
        return articles

    def _xml_text(self, element: ElementTree.Element, tag: str, ns: dict[str, str]) -> str | None:
        child = element.find(tag) or element.find(f"atom:{tag}", ns)
        return child.text if child is not None and child.text else None

    def _xml_attr(self, element: ElementTree.Element, tag: str, attr: str, ns: dict[str, str]) -> str | None:
        child = element.find(tag) or element.find(f"atom:{tag}", ns)
        return child.get(attr) if child is not None else None

    def _parse_html_blog(self, html_text: str, source_name: str, base_url: str) -> list[dict[str, Any]]:
        articles: list[dict[str, Any]] = []
        try:
            soup = BeautifulSoup(html_text, "html.parser")
            for article in soup.find_all("article")[:20]:
                title_el = article.find(["h1", "h2", "h3"])
                link_el = article.find("a", href=True)
                summary_el = article.find("p")
                if title_el:
                    title = title_el.get_text(strip=True)
                    link = link_el["href"] if link_el else ""
                    if link and not link.startswith("http"):
                        link = base_url.rstrip("/") + "/" + link.lstrip("/")
                    summary = summary_el.get_text(strip=True)[:500] if summary_el else ""
                    articles.append({
                        "title": title,
                        "url": link,
                        "source": source_name,
                        "summary": summary,
                        "published": None,
                        "tags": self._extract_tags(title, summary),
                        "relevance_score": self._compute_relevance(title, summary),
                    })
        except Exception as exc:
            self.log.warning("html_parse_failed", source=source_name, error=str(exc))
        return articles

    async def scrape_news_sources(self) -> list[dict[str, Any]]:
        self.log.info("scraping_news_sources", count=len(NEWS_SOURCES))
        results: list[dict[str, Any]] = []
        tasks = [self._fetch(source["url"]) for source in NEWS_SOURCES]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        for source, response in zip(NEWS_SOURCES, responses):
            if isinstance(response, str):
                articles = self._parse_rss(response, source["name"])
                results.extend(articles)
            else:
                self.log.warning("source_failed", source=source["name"])
        self.log.info("news_sources_scraped", articles=len(results))
        return results

    async def scrape_arxiv(self, keywords: list[str] | None = None) -> list[dict[str, Any]]:
        if not keywords:
            keywords = ["physical AI", "embodied AI", "robotics manipulation", "humanoid robot"]
        query = " OR ".join(f'all:"{kw}"' for kw in keywords)
        params = {
            "search_query": query,
            "start": 0,
            "max_results": 30,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }

        self.log.info("scraping_arxiv", keywords=keywords)
        papers: list[dict[str, Any]] = []
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                resp = await client.get(ARXIV_BASE_URL, params=params)
                resp.raise_for_status()
                papers = self._parse_arxiv_response(resp.text)
        except httpx.HTTPError as exc:
            self.log.warning("arxiv_fetch_failed", error=str(exc))
        self.log.info("arxiv_scraped", papers=len(papers))
        return papers

    def _parse_arxiv_response(self, xml_text: str) -> list[dict[str, Any]]:
        papers: list[dict[str, Any]] = []
        ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
        try:
            root = ElementTree.fromstring(xml_text)
            for entry in root.findall("atom:entry", ns):
                title = entry.findtext("atom:title", "", ns).strip().replace("\n", " ")
                summary = entry.findtext("atom:summary", "", ns).strip().replace("\n", " ")
                published_str = entry.findtext("atom:published", "", ns)
                published = self._parse_date(published_str) if published_str else None

                arxiv_id = ""
                id_text = entry.findtext("atom:id", "", ns)
                id_match = re.search(r"(\d{4}\.\d{4,5})", id_text)
                if id_match:
                    arxiv_id = id_match.group(1)

                authors = [
                    a.findtext("atom:name", "", ns)
                    for a in entry.findall("atom:author", ns)
                ]
                categories = [
                    c.get("term", "")
                    for c in entry.findall("arxiv:primary_category", ns)
                ] + [
                    c.get("term", "")
                    for c in entry.findall("atom:category", ns)
                ]
                categories = list(dict.fromkeys(c for c in categories if c))

                papers.append({
                    "title": title,
                    "authors": authors,
                    "abstract": summary[:1000],
                    "arxiv_id": arxiv_id,
                    "url": f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else id_text,
                    "published": published,
                    "categories": categories,
                    "keywords": self._extract_paper_keywords(title, summary),
                })
        except ElementTree.ParseError as exc:
            self.log.warning("arxiv_parse_failed", error=str(exc))
        return papers

    async def scrape_industry_blogs(self) -> list[dict[str, Any]]:
        self.log.info("scraping_industry_blogs", count=len(INDUSTRY_BLOGS))
        results: list[dict[str, Any]] = []
        tasks = [self._fetch(blog["url"]) for blog in INDUSTRY_BLOGS]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        for blog, response in zip(INDUSTRY_BLOGS, responses):
            if isinstance(response, str):
                if blog["type"] == "rss":
                    articles = self._parse_rss(response, blog["name"])
                else:
                    articles = self._parse_html_blog(response, blog["name"], blog["url"])
                results.extend(articles)
            else:
                self.log.warning("blog_failed", blog=blog["name"])
        self.log.info("industry_blogs_scraped", articles=len(results))
        return results

    async def aggregate_news(self) -> list[dict[str, Any]]:
        self.log.info("aggregating_all_news")
        news_task = self.scrape_news_sources()
        blog_task = self.scrape_industry_blogs()
        news_results, blog_results = await asyncio.gather(news_task, blog_task)

        combined = news_results + blog_results
        seen_urls: set[str] = set()
        deduplicated: list[dict[str, Any]] = []
        for article in combined:
            url = article.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                deduplicated.append(article)
            elif not url:
                deduplicated.append(article)

        deduplicated.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        self.log.info("news_aggregated", total=len(deduplicated))
        return deduplicated

    def _clean_html(self, text: str) -> str:
        if "<" in text and ">" in text:
            soup = BeautifulSoup(text, "html.parser")
            return soup.get_text(strip=True)
        return text.strip()

    def _extract_tags(self, title: str, description: str) -> list[str]:
        combined = f"{title} {description}".lower()
        tags: list[str] = []
        tag_keywords = {
            "robotics": ["robot", "robotic"],
            "embodied-ai": ["embodied ai", "embodied intelligence"],
            "physical-ai": ["physical ai", "physical intelligence"],
            "manipulation": ["manipulat", "grasping", "grasp", "pick and place"],
            "autonomous": ["autonomous", "self-driving", "unmanned"],
            "navigation": ["navigation", "slam", "path planning"],
            "perception": ["perception", "computer vision", "object detection", "lidar"],
            "sim-to-real": ["sim-to-real", "sim2real", "simulation"],
            "reinforcement-learning": ["reinforcement learning", "rl policy", "reward"],
            "foundation-model": ["foundation model", "large model", "vlm", "vla"],
            "humanoid": ["humanoid", "bipedal", "human-like robot"],
            "industry": ["industry", "manufacturing", "factory", "warehouse"],
            "startup": ["startup", "founded", "launch"],
            "funding": ["funding", "raised", "investment", "series"],
            "company": ["announces", "partnership", "acquisition"],
        }
        for tag, kws in tag_keywords.items():
            if any(kw in combined for kw in kws):
                tags.append(tag)
        return tags

    def _compute_relevance(self, title: str, description: str) -> float:
        combined = f"{title} {description}".lower()
        score = 0.0
        high_value = ["physical ai", "embodied ai", "humanoid", "robotics", "manipulation"]
        medium_value = ["autonomous", "perception", "reinforcement learning", "foundation model"]
        low_value = ["ai", "machine learning", "automation", "sensor"]

        for term in high_value:
            if term in combined:
                score += 0.2
        for term in medium_value:
            if term in combined:
                score += 0.1
        for term in low_value:
            if term in combined:
                score += 0.05
        return min(score, 1.0)

    def _extract_paper_keywords(self, title: str, abstract: str) -> list[str]:
        combined = f"{title} {abstract}".lower()
        return [tag for tag in PHYSICAL_AI_TAGS if tag.replace("-", " ") in combined or tag in combined]

    def _parse_date(self, date_str: str) -> datetime | None:
        formats = [
            "%a, %d %b %Y %H:%M:%S %z",
            "%a, %d %b %Y %H:%M:%S %Z",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%d",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        return None
