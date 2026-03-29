from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any

import structlog
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)

_DEFAULT_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


class NewsletterSection(BaseModel):
    title: str
    content: str
    links: list[str] = Field(default_factory=list)


class NewsletterData(BaseModel):
    """Data model fed into the newsletter template."""

    title: str
    subtitle: str = ""
    date: str = Field(default_factory=lambda: datetime.date.today().isoformat())
    sections: list[NewsletterSection] = Field(default_factory=list)
    footer: str = ""


class ReportData(BaseModel):
    """Data model fed into the report template."""

    title: str
    author: str = ""
    date: str = Field(default_factory=lambda: datetime.date.today().isoformat())
    summary: str = ""
    sections: list[dict[str, Any]] = Field(default_factory=list)
    conclusions: str = ""


_BUILTIN_NEWSLETTER = """\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>{{ title }}</title></head>
<body>
<h1>{{ title }}</h1>
{% if subtitle %}<h2>{{ subtitle }}</h2>{% endif %}
<p><em>{{ date }}</em></p>
{% for section in sections %}
<h3>{{ section.title }}</h3>
<div>{{ section.content }}</div>
{% if section.links %}
<ul>
{% for link in section.links %}<li><a href="{{ link }}">{{ link }}</a></li>
{% endfor %}
</ul>
{% endif %}
{% endfor %}
{% if footer %}<footer><p>{{ footer }}</p></footer>{% endif %}
</body>
</html>
"""

_BUILTIN_REPORT = """\
# {{ title }}

{% if author %}**Author:** {{ author }}  {% endif %}
**Date:** {{ date }}

{% if summary %}## Summary
{{ summary }}
{% endif %}

{% for section in sections %}
## {{ section.get("title", "Section") }}
{{ section.get("content", "") }}
{% endfor %}

{% if conclusions %}## Conclusions
{{ conclusions }}
{% endif %}
"""


class TemplateEngine:
    """Jinja2-based rendering engine with built-in newsletter and report templates."""

    def __init__(self, templates_dir: str | Path | None = None) -> None:
        self._templates_dir = Path(templates_dir) if templates_dir else _DEFAULT_TEMPLATES_DIR
        loaders = []
        if self._templates_dir.is_dir():
            loaders.append(FileSystemLoader(str(self._templates_dir)))

        self._env = Environment(
            loader=FileSystemLoader(str(self._templates_dir)) if loaders else None,  # type: ignore[arg-type]
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self._log = logger.bind(component="template_engine")

    def render_template(self, template_name: str, context: dict[str, Any]) -> str:
        self._log.info("render.template", template=template_name)
        tmpl = self._env.get_template(template_name)
        return tmpl.render(**context)

    def render_string(self, template_string: str, context: dict[str, Any]) -> str:
        tmpl = self._env.from_string(template_string)
        return tmpl.render(**context)

    def render_newsletter(self, data: NewsletterData) -> str:
        self._log.info("render.newsletter", title=data.title)
        return self.render_string(_BUILTIN_NEWSLETTER, data.model_dump())

    def render_report(self, data: ReportData) -> str:
        self._log.info("render.report", title=data.title)
        return self.render_string(_BUILTIN_REPORT, data.model_dump())
