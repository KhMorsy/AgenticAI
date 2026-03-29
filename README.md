# AgenticAI

A full agentic system built on the **Model Context Protocol (MCP)** that orchestrates four specialized AI agents to help you build products, stay current on AI, develop businesses, and explore Physical AI / robotics opportunities.

## Architecture

```
                     ┌──────────────────────────┐
                     │   Orchestrator (MCP)      │
                     │  Routes / Pipelines /     │
                     │  Cross-Agent Workflows    │
                     └────────┬─────────────────┘
                              │
         ┌────────────┬───────┴───────┬────────────┐
         ▼            ▼               ▼            ▼
┌─────────────┐ ┌──────────┐ ┌─────────────┐ ┌──────────┐
│ SW Architect│ │ Gen AI   │ │  Business   │ │ Physical │
│   Agent     │ │  Agent   │ │  Developer  │ │ AI Agent │
│   (MCP)     │ │  (MCP)   │ │   (MCP)     │ │  (MCP)   │
└──────┬──────┘ └──────────┘ └──────┬──────┘ └──────────┘
       │                            │
  Sub-agents:                  Sub-agents:
  • Backend Dev                • Market Research
  • Frontend Dev               • Financial Analyst
  • DevOps                     • Marketing Strategy
  • QA Engineer                • Legal & Compliance
                               • Sales Strategy
```

Each agent runs as a standalone **MCP server** communicating over stdio, exposable to any MCP-compatible client (Claude Desktop, Cursor, custom hosts).

## Agents

### 1. SW Architecture Agent (`sw-architect`)
Transforms ideas into production-ready products.

| Tool | Description |
|------|-------------|
| `analyze_idea` | Parse an idea into a structured project plan |
| `design_architecture` | Generate system architecture (components, APIs, data models, tech stack) |
| `generate_project` | Orchestrate sub-agents to produce full project code |
| `review_code` | Perform AI-powered code review |
| `create_deployment_plan` | Generate Docker, K8s, and CI/CD configurations |

**Sub-agents:** Backend Developer, Frontend Developer, DevOps Engineer, QA Engineer

### 2. Generative AI Agent (`generative-ai`)
Keeps you informed about AI advances and optimizes your workflows.

| Tool | Description |
|------|-------------|
| `get_ai_news` | Aggregate latest AI news from 15+ sources (ArXiv, HuggingFace, OpenAI, Anthropic, Google AI, etc.) |
| `propose_ideas` | Generate AI-powered ideas tailored to your context |
| `suggest_workflows` | Recommend workflow optimizations |
| `analyze_ai_tools` | Evaluate AI tools for a specific domain |
| `generate_optimization_plan` | Create step-by-step optimization strategies |

### 3. Business Developer Agent (`business-developer`)
Senior business development assistant with specialized sub-agents.

| Tool | Description |
|------|-------------|
| `analyze_business_idea` | SWOT analysis and opportunity assessment |
| `create_business_model` | Generate a Business Model Canvas |
| `market_research` | Market sizing, personas, trends, barriers |
| `financial_projection` | 3-year financial projections with unit economics |
| `create_pitch_deck` | Generate investor-ready pitch deck content |
| `competitive_analysis` | Analyze competitors and identify market gaps |

**Sub-agents:** Market Research, Financial Analyst, Marketing Strategy, Legal & Compliance, Sales Strategy

### 4. Physical AI Agent (`physical-ai`)
Tracks Physical AI / robotics news and helps you build a startup in the space.

| Tool | Description |
|------|-------------|
| `generate_newsletter` | Daily newsletter with latest Physical AI updates |
| `scan_news` | Scrape news from IEEE, MIT Tech Review, Robot Report, and more |
| `propose_automation` | Suggest automation ideas for your work routines |
| `startup_ideation` | Generate Physical AI startup plans |
| `cross_agent_analysis` | Multi-perspective analysis using all agents |
| `track_papers` | Monitor ArXiv for new robotics / embodied AI papers |

## Orchestrator Pipelines

The orchestrator coordinates all agents for complex workflows:

| Pipeline | Description |
|----------|-------------|
| `full_product_pipeline` | Idea → Architecture → Code → Deployment → Business Plan → Financials |
| `startup_pipeline` | Domain → Startup Plan → Architecture → Business Model → Pitch Deck |
| `daily_briefing` | AI news + Physical AI newsletter + Workflow suggestions + Idea proposals |
| `cross_agent_workflow` | Custom multi-step workflows with dependency resolution |

## Quick Start

### 1. Install

```bash
# Clone and install
git clone <repo-url> && cd AgenticAI
pip install -e ".[dev]"

# Copy and configure environment
cp .env.example .env
# Edit .env with your API keys
```

### 2. Configure MCP Client

Copy `mcp_config.json` into your MCP client config (e.g., Claude Desktop, Cursor):

**Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "agentic-orchestrator": {
      "command": "python",
      "args": ["-m", "src.orchestrator.server"],
      "cwd": "/path/to/AgenticAI",
      "env": {
        "AGENTIC_LLM_API_KEY": "your-key"
      }
    }
  }
}
```

**Cursor** (`.cursor/mcp.json` in your project):
```json
{
  "mcpServers": {
    "agentic-orchestrator": {
      "command": "python",
      "args": ["-m", "src.orchestrator.server"],
      "env": {
        "AGENTIC_LLM_API_KEY": "your-key"
      }
    }
  }
}
```

### 3. Use the CLI

```bash
# Start the orchestrator MCP server
agentic start

# Start individual agent servers
agentic architect
agentic genai
agentic business
agentic physical

# Run pipelines
agentic pipeline "A SaaS platform for automated code review"
agentic startup "warehouse robotics"
agentic briefing "robotics" "LLMs" "computer vision"

# Check system status
agentic status
```

### 4. Docker

```bash
docker compose up -d
```

## Project Structure

```
src/
├── core/                    # Shared framework
│   ├── base_agent.py        # Abstract base agent class
│   ├── llm_provider.py      # OpenAI / Anthropic abstraction
│   ├── mcp_server.py        # MCP server base class
│   ├── task_manager.py      # Task scheduling & dependencies
│   ├── template_engine.py   # Jinja2 newsletter & report rendering
│   └── web_scraper.py       # Async HTTP, HTML parsing, RSS feeds
├── agents/
│   ├── sw_architect/        # SW Architecture Agent + sub-agents
│   ├── generative_ai/       # GenAI Agent + news sources
│   ├── business_developer/  # Business Agent + sub-agents
│   └── physical_ai/         # Physical AI Agent + scraper + newsletter
├── orchestrator/            # Cross-agent coordinator + MCP server
├── config/                  # Settings (pydantic-settings)
├── templates/               # Jinja2 templates (newsletter, reports)
└── cli.py                   # Click CLI entry point
tests/                       # pytest test suite
```

## Configuration

All settings are loaded from environment variables (prefixed with `AGENTIC_`) or a `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENTIC_LLM_PROVIDER` | `openai` | LLM provider (`openai` or `anthropic`) |
| `AGENTIC_LLM_MODEL` | `gpt-4o` | Model name |
| `AGENTIC_LLM_API_KEY` | — | API key (required for LLM features) |
| `AGENTIC_TEMPERATURE` | `0.7` | Generation temperature |
| `AGENTIC_MAX_TOKENS` | `4096` | Max tokens per response |
| `AGENTIC_SCRAPING_RATE_LIMIT` | `10` | Max concurrent scraping requests |
| `AGENTIC_NEWSLETTER_SCHEDULE` | `daily` | Newsletter frequency |
| `AGENTIC_OUTPUT_DIR` | `./output` | Output directory |
| `AGENTIC_LOG_LEVEL` | `INFO` | Log level |

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src/ tests/

# Type check
mypy src/
```

## License

MIT
