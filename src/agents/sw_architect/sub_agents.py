from __future__ import annotations

from typing import Any

import structlog

log = structlog.get_logger()


class BackendDeveloperAgent:
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.log = log.bind(agent="backend_developer")

    async def execute(self, task: dict[str, Any]) -> dict[str, str]:
        self.log.info("executing_backend_task", project=task.get("project_name"))

        if self.llm_client is not None:
            return await self._llm_generate(task)

        project_name = task.get("project_name", "app").lower().replace(" ", "_")
        tech_stack = task.get("tech_stack", {})
        apis = task.get("apis", [])
        data_models = task.get("data_models", [])

        files: dict[str, str] = {}

        files["requirements.txt"] = self._gen_requirements(tech_stack)
        files[f"{project_name}/__init__.py"] = ""
        files[f"{project_name}/main.py"] = self._gen_main(project_name, apis)
        files[f"{project_name}/models.py"] = self._gen_models(data_models)
        files[f"{project_name}/routes.py"] = self._gen_routes(apis)
        files[f"{project_name}/config.py"] = self._gen_config(project_name)
        files[f"{project_name}/database.py"] = self._gen_database()

        self.log.info("backend_generated", files=len(files))
        return files

    async def _llm_generate(self, task: dict[str, Any]) -> dict[str, str]:
        import json

        prompt = (
            "You are a senior backend developer. Generate production-ready backend code.\n\n"
            f"Task: {json.dumps(task, default=str)}\n\n"
            "Respond with a JSON object where keys are file paths and values are file contents."
        )
        response = await self._call_llm(prompt)
        return json.loads(response)

    async def _call_llm(self, prompt: str) -> str:
        if hasattr(self.llm_client, "chat"):
            resp = await self.llm_client.chat.completions.create(
                model="gpt-4", messages=[{"role": "user", "content": prompt}], temperature=0.2
            )
            return resp.choices[0].message.content
        if hasattr(self.llm_client, "messages"):
            resp = await self.llm_client.messages.create(
                model="claude-sonnet-4-20250514", max_tokens=4096, messages=[{"role": "user", "content": prompt}]
            )
            return resp.content[0].text
        raise RuntimeError(f"Unsupported LLM client: {type(self.llm_client)}")

    @staticmethod
    def _gen_requirements(tech_stack: dict) -> str:
        deps = [
            "fastapi>=0.110.0", "uvicorn[standard]>=0.29.0",
            "pydantic>=2.0.0", "sqlalchemy>=2.0.0",
            "alembic>=1.13.0", "structlog>=24.0.0",
        ]
        if "PostgreSQL" in tech_stack.get("databases", []):
            deps.append("asyncpg>=0.29.0")
        if "Redis" in tech_stack.get("databases", []):
            deps.append("redis>=5.0.0")
        return "\n".join(deps) + "\n"

    @staticmethod
    def _gen_main(project_name: str, apis: list[dict]) -> str:
        return (
            "from fastapi import FastAPI\n"
            "from .routes import router\n"
            "from .config import settings\n\n"
            f'app = FastAPI(title="{project_name}", version="0.1.0")\n'
            'app.include_router(router, prefix="/api/v1")\n\n\n'
            '@app.get("/health")\n'
            "async def health_check():\n"
            '    return {"status": "healthy"}\n'
        )

    @staticmethod
    def _gen_models(data_models: list[dict]) -> str:
        lines = [
            "from datetime import datetime\n",
            "from uuid import uuid4\n\n",
            "from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text\n",
            "from sqlalchemy.dialects.postgresql import JSON, UUID\n",
            "from sqlalchemy.orm import relationship\n\n",
            "from .database import Base\n\n",
        ]
        for model in data_models:
            name = model.get("name", "Model")
            fields = model.get("fields", {})
            lines.append(f"\nclass {name}(Base):\n")
            lines.append(f'    __tablename__ = "{name.lower()}s"\n\n')
            for field_name, field_type in fields.items():
                col = _map_sqlalchemy_type(field_name, field_type)
                lines.append(f"    {field_name} = {col}\n")
            lines.append("\n")
        return "".join(lines)

    @staticmethod
    def _gen_routes(apis: list[dict]) -> str:
        lines = ["from fastapi import APIRouter, Depends, HTTPException\n\n", "router = APIRouter()\n\n"]
        for api in apis:
            method = api.get("method", "GET").lower()
            path = api.get("path", "/").replace("/api/v1", "")
            name = api.get("name", "endpoint").lower().replace(" ", "_")
            description = api.get("description", "")
            if not path or path == "/":
                path = f"/{name}"
            lines.append(f'@router.{method}("{path}")\n')
            lines.append(f"async def {name}():\n")
            lines.append(f'    """{description}"""\n')
            lines.append(f'    return {{"message": "{name}"}}\n\n\n')
        return "".join(lines)

    @staticmethod
    def _gen_config(project_name: str) -> str:
        return (
            "from pydantic_settings import BaseSettings\n\n\n"
            "class Settings(BaseSettings):\n"
            f'    app_name: str = "{project_name}"\n'
            '    database_url: str = "postgresql+asyncpg://localhost:5432/app"\n'
            '    secret_key: str = "change-me"\n'
            '    log_level: str = "INFO"\n'
            "    debug: bool = False\n\n"
            "    model_config = {\"env_file\": \".env\"}\n\n\n"
            "settings = Settings()\n"
        )

    @staticmethod
    def _gen_database() -> str:
        return (
            "from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine\n"
            "from sqlalchemy.orm import DeclarativeBase, sessionmaker\n\n"
            "from .config import settings\n\n"
            "engine = create_async_engine(settings.database_url, echo=settings.debug)\n"
            "async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)\n\n\n"
            "class Base(DeclarativeBase):\n"
            "    pass\n\n\n"
            "async def get_session() -> AsyncSession:\n"
            "    async with async_session() as session:\n"
            "        yield session\n"
        )


class FrontendDeveloperAgent:
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.log = log.bind(agent="frontend_developer")

    async def execute(self, task: dict[str, Any]) -> dict[str, str]:
        self.log.info("executing_frontend_task", project=task.get("project_name"))

        if self.llm_client is not None:
            return await self._llm_generate(task)

        project_name = task.get("project_name", "App")
        apis = task.get("apis", [])
        files: dict[str, str] = {}

        files["package.json"] = self._gen_package_json(project_name)
        files["src/App.tsx"] = self._gen_app(project_name)
        files["src/index.tsx"] = self._gen_index()
        files["src/api/client.ts"] = self._gen_api_client(apis)
        files["src/components/Layout.tsx"] = self._gen_layout(project_name)
        files["public/index.html"] = self._gen_html(project_name)

        self.log.info("frontend_generated", files=len(files))
        return files

    async def _llm_generate(self, task: dict[str, Any]) -> dict[str, str]:
        import json

        prompt = (
            "You are a senior frontend developer. Generate production-ready React/TypeScript code.\n\n"
            f"Task: {json.dumps(task, default=str)}\n\n"
            "Respond with a JSON object where keys are file paths and values are file contents."
        )
        if hasattr(self.llm_client, "chat"):
            resp = await self.llm_client.chat.completions.create(
                model="gpt-4", messages=[{"role": "user", "content": prompt}], temperature=0.2
            )
            return json.loads(resp.choices[0].message.content)
        resp = await self.llm_client.messages.create(
            model="claude-sonnet-4-20250514", max_tokens=4096, messages=[{"role": "user", "content": prompt}]
        )
        return json.loads(resp.content[0].text)

    @staticmethod
    def _gen_package_json(project_name: str) -> str:
        import json

        pkg = {
            "name": project_name.lower().replace(" ", "-"),
            "version": "0.1.0",
            "private": True,
            "dependencies": {
                "react": "^18.3.0",
                "react-dom": "^18.3.0",
                "react-router-dom": "^6.23.0",
                "axios": "^1.7.0",
                "typescript": "^5.4.0",
            },
            "scripts": {
                "start": "react-scripts start",
                "build": "react-scripts build",
                "test": "react-scripts test",
            },
        }
        return json.dumps(pkg, indent=2) + "\n"

    @staticmethod
    def _gen_app(project_name: str) -> str:
        return (
            "import React from 'react';\n"
            "import { BrowserRouter, Routes, Route } from 'react-router-dom';\n"
            "import Layout from './components/Layout';\n\n"
            "const App: React.FC = () => {\n"
            "  return (\n"
            "    <BrowserRouter>\n"
            "      <Layout>\n"
            "        <Routes>\n"
            '          <Route path="/" element={<div>Home</div>} />\n'
            "        </Routes>\n"
            "      </Layout>\n"
            "    </BrowserRouter>\n"
            "  );\n"
            "};\n\n"
            "export default App;\n"
        )

    @staticmethod
    def _gen_index() -> str:
        return (
            "import React from 'react';\n"
            "import ReactDOM from 'react-dom/client';\n"
            "import App from './App';\n\n"
            "const root = ReactDOM.createRoot(document.getElementById('root')!);\n"
            "root.render(\n"
            "  <React.StrictMode>\n"
            "    <App />\n"
            "  </React.StrictMode>\n"
            ");\n"
        )

    @staticmethod
    def _gen_api_client(apis: list[dict]) -> str:
        lines = [
            "import axios from 'axios';\n\n",
            "const api = axios.create({\n",
            "  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000',\n",
            "});\n\n",
        ]
        for api_def in apis:
            name = api_def.get("name", "endpoint").replace(" ", "")
            method = api_def.get("method", "GET").lower()
            path = api_def.get("path", "/")
            ts_path = path.replace("{id}", "${id}")
            if method == "get":
                lines.append(f"export const {name} = (id?: string) =>\n")
                lines.append(f"  api.{method}(`{ts_path}`);\n\n")
            elif method in ("post", "put"):
                lines.append(f"export const {name} = (data: Record<string, unknown>, id?: string) =>\n")
                lines.append(f"  api.{method}(`{ts_path}`, data);\n\n")
            else:
                lines.append(f"export const {name} = (id?: string) =>\n")
                lines.append(f"  api.{method}(`{ts_path}`);\n\n")
        lines.append("export default api;\n")
        return "".join(lines)

    @staticmethod
    def _gen_layout(project_name: str) -> str:
        return (
            "import React from 'react';\n\n"
            "interface LayoutProps {\n"
            "  children: React.ReactNode;\n"
            "}\n\n"
            "const Layout: React.FC<LayoutProps> = ({ children }) => {\n"
            "  return (\n"
            "    <div className=\"app-layout\">\n"
            "      <header>\n"
            f'        <h1>{project_name}</h1>\n'
            "      </header>\n"
            "      <main>{children}</main>\n"
            "      <footer>\n"
            f'        <p>&copy; {project_name}</p>\n'
            "      </footer>\n"
            "    </div>\n"
            "  );\n"
            "};\n\n"
            "export default Layout;\n"
        )

    @staticmethod
    def _gen_html(project_name: str) -> str:
        return (
            "<!DOCTYPE html>\n"
            '<html lang="en">\n'
            "<head>\n"
            '  <meta charset="utf-8" />\n'
            '  <meta name="viewport" content="width=device-width, initial-scale=1" />\n'
            f"  <title>{project_name}</title>\n"
            "</head>\n"
            "<body>\n"
            '  <div id="root"></div>\n'
            "</body>\n"
            "</html>\n"
        )


class DevOpsAgent:
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.log = log.bind(agent="devops")

    async def execute(self, task: dict[str, Any]) -> dict[str, str]:
        self.log.info("executing_devops_task", project=task.get("project_name"))

        if self.llm_client is not None:
            return await self._llm_generate(task)

        project_name = task.get("project_name", "app").lower().replace(" ", "-")
        files: dict[str, str] = {}

        files["Dockerfile"] = (
            "FROM python:3.12-slim AS base\n"
            "WORKDIR /app\n"
            "COPY requirements.txt .\n"
            "RUN pip install --no-cache-dir -r requirements.txt\n"
            "COPY . .\n"
            "EXPOSE 8000\n"
            'CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]\n'
        )

        files["docker-compose.yml"] = (
            "version: '3.8'\n"
            "services:\n"
            f"  {project_name}:\n"
            "    build: .\n"
            "    ports:\n"
            '      - "8000:8000"\n'
            "    environment:\n"
            "      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/app\n"
            "    depends_on:\n"
            "      - db\n"
            "  db:\n"
            "    image: postgres:16\n"
            "    environment:\n"
            "      POSTGRES_DB: app\n"
            "      POSTGRES_USER: postgres\n"
            "      POSTGRES_PASSWORD: postgres\n"
            "    volumes:\n"
            "      - pgdata:/var/lib/postgresql/data\n"
            "    ports:\n"
            '      - "5432:5432"\n'
            "volumes:\n"
            "  pgdata:\n"
        )

        files[".github/workflows/ci.yml"] = (
            "name: CI\n"
            "on:\n"
            "  push:\n"
            "    branches: [main]\n"
            "  pull_request:\n"
            "    branches: [main]\n"
            "jobs:\n"
            "  test:\n"
            "    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "    - uses: actions/checkout@v4\n"
            "    - uses: actions/setup-python@v5\n"
            "      with:\n"
            "        python-version: '3.12'\n"
            "    - run: pip install -r requirements.txt\n"
            "    - run: pytest --cov --cov-report=xml\n"
            "  lint:\n"
            "    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "    - uses: actions/checkout@v4\n"
            "    - uses: actions/setup-python@v5\n"
            "      with:\n"
            "        python-version: '3.12'\n"
            "    - run: pip install ruff\n"
            "    - run: ruff check .\n"
        )

        files[f"k8s/{project_name}-deployment.yaml"] = (
            "apiVersion: apps/v1\n"
            "kind: Deployment\n"
            "metadata:\n"
            f"  name: {project_name}\n"
            "spec:\n"
            "  replicas: 3\n"
            "  selector:\n"
            "    matchLabels:\n"
            f"      app: {project_name}\n"
            "  template:\n"
            "    metadata:\n"
            "      labels:\n"
            f"        app: {project_name}\n"
            "    spec:\n"
            "      containers:\n"
            f"      - name: {project_name}\n"
            f"        image: {project_name}:latest\n"
            "        ports:\n"
            "        - containerPort: 8000\n"
            "        resources:\n"
            "          requests:\n"
            "            memory: 256Mi\n"
            "            cpu: 250m\n"
            "          limits:\n"
            "            memory: 512Mi\n"
            "            cpu: 500m\n"
        )

        files[f"k8s/{project_name}-service.yaml"] = (
            "apiVersion: v1\n"
            "kind: Service\n"
            "metadata:\n"
            f"  name: {project_name}\n"
            "spec:\n"
            "  selector:\n"
            f"    app: {project_name}\n"
            "  ports:\n"
            "  - port: 80\n"
            "    targetPort: 8000\n"
            "  type: ClusterIP\n"
        )

        self.log.info("devops_generated", files=len(files))
        return files

    async def _llm_generate(self, task: dict[str, Any]) -> dict[str, str]:
        import json

        prompt = (
            "You are a senior DevOps engineer. Generate Docker, Kubernetes, and CI/CD configurations.\n\n"
            f"Task: {json.dumps(task, default=str)}\n\n"
            "Respond with a JSON object where keys are file paths and values are file contents."
        )
        if hasattr(self.llm_client, "chat"):
            resp = await self.llm_client.chat.completions.create(
                model="gpt-4", messages=[{"role": "user", "content": prompt}], temperature=0.2
            )
            return json.loads(resp.choices[0].message.content)
        resp = await self.llm_client.messages.create(
            model="claude-sonnet-4-20250514", max_tokens=4096, messages=[{"role": "user", "content": prompt}]
        )
        return json.loads(resp.content[0].text)


class QAAgent:
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.log = log.bind(agent="qa")

    async def execute(self, task: dict[str, Any]) -> dict[str, str]:
        self.log.info("executing_qa_task", project=task.get("project_name"))

        if self.llm_client is not None:
            return await self._llm_generate(task)

        project_name = task.get("project_name", "app").lower().replace(" ", "_")
        apis = task.get("apis", [])
        files: dict[str, str] = {}

        files["conftest.py"] = (
            "import pytest\n"
            "from httpx import ASGITransport, AsyncClient\n\n"
            f"from {project_name}.main import app\n\n\n"
            "@pytest.fixture\n"
            "async def client():\n"
            "    transport = ASGITransport(app=app)\n"
            '    async with AsyncClient(transport=transport, base_url="http://test") as ac:\n'
            "        yield ac\n"
        )

        files["test_health.py"] = (
            "import pytest\n\n\n"
            "@pytest.mark.asyncio\n"
            "async def test_health_check(client):\n"
            '    response = await client.get("/health")\n'
            "    assert response.status_code == 200\n"
            '    assert response.json()["status"] == "healthy"\n'
        )

        test_lines = ["import pytest\n\n"]
        for api_def in apis:
            name = api_def.get("name", "endpoint").lower().replace(" ", "_")
            method = api_def.get("method", "GET").lower()
            path = api_def.get("path", "/").replace("{id}", "1")
            test_lines.append("\n@pytest.mark.asyncio\n")
            test_lines.append(f"async def test_{name}(client):\n")
            if method in ("post", "put"):
                test_lines.append(f'    response = await client.{method}("{path}", json={{"name": "test"}})\n')
            else:
                test_lines.append(f'    response = await client.{method}("{path}")\n')
            test_lines.append("    assert response.status_code in (200, 201, 404)\n\n")
        files["test_api.py"] = "".join(test_lines)

        files["pytest.ini"] = (
            "[pytest]\n"
            "asyncio_mode = auto\n"
            "testpaths = tests\n"
            "addopts = --cov --cov-report=term-missing\n"
        )

        self.log.info("qa_generated", files=len(files))
        return files

    async def _llm_generate(self, task: dict[str, Any]) -> dict[str, str]:
        import json

        prompt = (
            "You are a senior QA engineer. Generate comprehensive test suites.\n\n"
            f"Task: {json.dumps(task, default=str)}\n\n"
            "Respond with a JSON object where keys are file paths and values are file contents."
        )
        if hasattr(self.llm_client, "chat"):
            resp = await self.llm_client.chat.completions.create(
                model="gpt-4", messages=[{"role": "user", "content": prompt}], temperature=0.2
            )
            return json.loads(resp.choices[0].message.content)
        resp = await self.llm_client.messages.create(
            model="claude-sonnet-4-20250514", max_tokens=4096, messages=[{"role": "user", "content": prompt}]
        )
        return json.loads(resp.content[0].text)


def _map_sqlalchemy_type(field_name: str, field_type: str) -> str:
    uuid_col = (
        "Column(UUID(as_uuid=True), primary_key=True, default=uuid4)"
        if "id" == field_name
        else "Column(UUID(as_uuid=True), ForeignKey('users.id'))"
    )
    type_map = {
        "UUID": uuid_col,
        "str": "Column(String(255), nullable=False)",
        "int": "Column(Integer, nullable=False)",
        "float": "Column(Float, nullable=False)",
        "bool": "Column(Boolean, default=True)",
        "datetime": "Column(DateTime, default=datetime.utcnow)",
        "JSON": "Column(JSON, default=dict)",
    }

    if field_name == "id":
        return "Column(UUID(as_uuid=True), primary_key=True, default=uuid4)"
    if "id" in field_name and field_name != "id":
        return f"Column(UUID(as_uuid=True), ForeignKey('{field_name.replace('_id', '')}s.id'))"
    return type_map.get(field_type, "Column(String(255))")
