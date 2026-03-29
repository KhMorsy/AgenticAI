"""Tests for core modules: TaskManager, TemplateEngine, WebScraper, LLMProvider."""

import pytest

from src.core.llm_provider import LLMProviderConfig, LLMProviderType
from src.core.task_manager import TaskManager, TaskPriority, TaskStatus
from src.core.template_engine import (
    NewsletterData,
    NewsletterSection,
    ReportData,
    TemplateEngine,
)
from src.core.web_scraper import ScrapedPage, WebScraper

# ---------------------------------------------------------------------------
# TaskManager
# ---------------------------------------------------------------------------


class TestTaskManager:
    async def test_create_task(self):
        tm = TaskManager()
        task = await tm.create_task(type="test", description="A test task")
        assert task.id is not None
        assert task.type == "test"
        assert task.description == "A test task"
        assert task.status == TaskStatus.PENDING

    async def test_create_task_with_priority(self):
        tm = TaskManager()
        task = await tm.create_task(
            type="urgent",
            description="Critical task",
            priority=TaskPriority.CRITICAL,
        )
        assert task.priority == TaskPriority.CRITICAL

    async def test_update_task_status(self):
        tm = TaskManager()
        task = await tm.create_task(type="test", description="task")
        updated = await tm.update_task(task.id, status=TaskStatus.IN_PROGRESS)
        assert updated.status == TaskStatus.IN_PROGRESS

    async def test_update_task_result(self):
        tm = TaskManager()
        task = await tm.create_task(type="test", description="task")
        updated = await tm.update_task(task.id, result={"output": 42})
        assert updated.result == {"output": 42}

    async def test_update_task_error(self):
        tm = TaskManager()
        task = await tm.create_task(type="test", description="task")
        updated = await tm.update_task(
            task.id, status=TaskStatus.FAILED, error="something broke"
        )
        assert updated.status == TaskStatus.FAILED
        assert updated.error == "something broke"

    async def test_update_nonexistent_task_raises(self):
        tm = TaskManager()
        with pytest.raises(KeyError, match="not found"):
            await tm.update_task("nonexistent-id", status=TaskStatus.COMPLETED)

    async def test_get_task(self):
        tm = TaskManager()
        task = await tm.create_task(type="test", description="lookup")
        found = await tm.get_task(task.id)
        assert found is not None
        assert found.id == task.id

    async def test_get_task_missing_returns_none(self):
        tm = TaskManager()
        assert await tm.get_task("missing") is None

    async def test_list_tasks_all(self):
        tm = TaskManager()
        await tm.create_task(type="a", description="first")
        await tm.create_task(type="b", description="second")
        tasks = await tm.list_tasks()
        assert len(tasks) == 2

    async def test_list_tasks_by_status(self):
        tm = TaskManager()
        t1 = await tm.create_task(type="a", description="one")
        await tm.create_task(type="b", description="two")
        await tm.update_task(t1.id, status=TaskStatus.COMPLETED)
        completed = await tm.list_tasks(status=TaskStatus.COMPLETED)
        assert len(completed) == 1
        assert completed[0].id == t1.id

    async def test_dependency_resolution(self):
        tm = TaskManager()
        t1 = await tm.create_task(type="step1", description="first step")
        t2 = await tm.create_task(
            type="step2", description="depends on step1", depends_on=[t1.id]
        )
        assert t2.status == TaskStatus.BLOCKED

        order = await tm.resolve_dependencies(t2.id)
        assert t1.id in order
        assert t2.id in order
        assert order.index(t1.id) < order.index(t2.id)

    async def test_unblock_after_dependency_completes(self):
        tm = TaskManager()
        t1 = await tm.create_task(type="dep", description="dependency")
        t2 = await tm.create_task(
            type="main", description="blocked", depends_on=[t1.id]
        )
        assert t2.status == TaskStatus.BLOCKED
        await tm.update_task(t1.id, status=TaskStatus.COMPLETED)
        refreshed = await tm.get_task(t2.id)
        assert refreshed is not None
        assert refreshed.status == TaskStatus.PENDING

    async def test_priority_queue_ordering(self):
        tm = TaskManager()
        await tm.create_task(
            type="low", description="low priority", priority=TaskPriority.LOW
        )
        await tm.create_task(
            type="high", description="high priority", priority=TaskPriority.HIGH
        )
        await tm.create_task(
            type="critical",
            description="critical priority",
            priority=TaskPriority.CRITICAL,
        )

        first = await tm.get_next_task()
        assert first is not None
        assert first.priority == TaskPriority.CRITICAL

        second = await tm.get_next_task()
        assert second is not None
        assert second.priority == TaskPriority.HIGH

        third = await tm.get_next_task()
        assert third is not None
        assert third.priority == TaskPriority.LOW

    async def test_get_next_task_empty(self):
        tm = TaskManager()
        assert await tm.get_next_task() is None

    async def test_subtasks(self):
        tm = TaskManager()
        parent = await tm.create_task(type="parent", description="parent task")
        child1 = await tm.create_task(
            type="child", description="child 1", parent_task_id=parent.id
        )
        child2 = await tm.create_task(
            type="child", description="child 2", parent_task_id=parent.id
        )
        subs = await tm.get_subtasks(parent.id)
        sub_ids = {s.id for s in subs}
        assert child1.id in sub_ids
        assert child2.id in sub_ids


# ---------------------------------------------------------------------------
# TemplateEngine
# ---------------------------------------------------------------------------


class TestTemplateEngine:
    def test_render_newsletter(self):
        engine = TemplateEngine()
        data = NewsletterData(
            title="Weekly AI Digest",
            subtitle="Top stories this week",
            date="2026-03-29",
            sections=[
                NewsletterSection(
                    title="Research",
                    content="New papers on transformers and diffusion models.",
                    links=["https://arxiv.org/example"],
                )
            ],
            footer="Powered by AgenticAI",
        )
        html = engine.render_newsletter(data)
        assert "Weekly AI Digest" in html
        assert "Top stories this week" in html
        assert "Research" in html
        assert "html" in html.lower()

    def test_render_report(self):
        engine = TemplateEngine()
        data = ReportData(
            title="Quarterly Review",
            author="AgenticAI System",
            date="2026-03-29",
            summary="A summary of the quarter.",
            sections=[
                {"title": "Revenue", "content": "Revenue grew by 20%."},
                {"title": "Users", "content": "Active users doubled."},
            ],
            conclusions="Continue scaling operations.",
        )
        md = engine.render_report(data)
        assert "Quarterly Review" in md
        assert "AgenticAI System" in md
        assert "Revenue" in md
        assert "Continue scaling" in md

    def test_render_string(self):
        engine = TemplateEngine()
        result = engine.render_string("Hello {{ name }}!", {"name": "World"})
        assert result == "Hello World!"

    def test_render_template_from_dir(self, tmp_path):
        tmpl_dir = tmp_path / "templates"
        tmpl_dir.mkdir()
        (tmpl_dir / "test.html").write_text("<h1>{{ heading }}</h1>")
        engine = TemplateEngine(templates_dir=str(tmpl_dir))
        output = engine.render_template("test.html", {"heading": "Hello"})
        assert "<h1>Hello</h1>" in output

    def test_newsletter_data_defaults(self):
        data = NewsletterData(title="Test")
        assert data.title == "Test"
        assert data.date  # auto-generated
        assert data.sections == []

    def test_report_data_defaults(self):
        data = ReportData(title="Test Report")
        assert data.title == "Test Report"
        assert data.author == ""
        assert data.date  # auto-generated


# ---------------------------------------------------------------------------
# WebScraper
# ---------------------------------------------------------------------------


class TestWebScraper:
    def test_initialization_defaults(self):
        scraper = WebScraper()
        assert scraper._timeout == 30.0
        assert scraper._user_agent == "AgenticSystem/1.0"

    def test_initialization_custom(self):
        scraper = WebScraper(max_concurrent=10, timeout=60.0, user_agent="Test/1.0")
        assert scraper._timeout == 60.0
        assert scraper._user_agent == "Test/1.0"

    def test_parse_html(self):
        html = """
        <html>
        <head><title>Test Page</title></head>
        <body>
            <p>Hello world</p>
            <a href="https://example.com">Link</a>
        </body>
        </html>
        """
        scraper = WebScraper()
        page = scraper.parse_html(html, url="https://test.com", status_code=200)
        assert isinstance(page, ScrapedPage)
        assert page.title == "Test Page"
        assert page.url == "https://test.com"
        assert page.status_code == 200
        assert "Hello world" in page.text
        assert "https://example.com" in page.links

    def test_parse_html_no_title(self):
        html = "<html><body><p>No title</p></body></html>"
        scraper = WebScraper()
        page = scraper.parse_html(html)
        assert page.title == ""

    def test_parse_html_strips_nav_footer(self):
        html = """
        <html>
        <body>
            <nav>Navigation</nav>
            <p>Content</p>
            <footer>Footer</footer>
        </body>
        </html>
        """
        scraper = WebScraper()
        page = scraper.parse_html(html)
        assert "Navigation" not in page.text
        assert "Footer" not in page.text
        assert "Content" in page.text


# ---------------------------------------------------------------------------
# LLMProviderConfig
# ---------------------------------------------------------------------------


class TestLLMProviderConfig:
    def test_default_config(self):
        config = LLMProviderConfig()
        assert config.provider == LLMProviderType.OPENAI
        assert config.model == "gpt-4o"
        assert config.temperature == 0.7
        assert config.max_tokens == 4096

    def test_custom_config(self):
        config = LLMProviderConfig(
            provider=LLMProviderType.ANTHROPIC,
            model="claude-sonnet-4-20250514",
            temperature=0.3,
            max_tokens=8192,
            api_key="test-key",
        )
        assert config.provider == LLMProviderType.ANTHROPIC
        assert config.model == "claude-sonnet-4-20250514"
        assert config.api_key == "test-key"

    def test_config_with_base_url(self):
        config = LLMProviderConfig(base_url="https://custom.api.com")
        assert config.base_url == "https://custom.api.com"

    def test_config_with_system_prompt(self):
        config = LLMProviderConfig(default_system_prompt="You are a helpful assistant.")
        assert config.default_system_prompt == "You are a helpful assistant."
