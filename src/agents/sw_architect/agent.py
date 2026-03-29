from __future__ import annotations

import structlog
from pydantic import BaseModel, Field

log = structlog.get_logger()


class Component(BaseModel):
    name: str
    description: str
    technology: str
    responsibilities: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)


class API(BaseModel):
    name: str
    method: str
    path: str
    description: str
    request_schema: dict | None = None
    response_schema: dict | None = None
    authentication: bool = True


class DataModel(BaseModel):
    name: str
    fields: dict[str, str]
    relationships: list[str] = Field(default_factory=list)
    indexes: list[str] = Field(default_factory=list)


class TechStack(BaseModel):
    languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    databases: list[str] = Field(default_factory=list)
    infrastructure: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)


class ProjectPlan(BaseModel):
    name: str
    description: str
    goals: list[str] = Field(default_factory=list)
    features: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    milestones: list[str] = Field(default_factory=list)
    tech_stack: TechStack = Field(default_factory=TechStack)


class Architecture(BaseModel):
    project_name: str
    style: str = "microservices"
    components: list[Component] = Field(default_factory=list)
    apis: list[API] = Field(default_factory=list)
    data_models: list[DataModel] = Field(default_factory=list)
    tech_stack: TechStack = Field(default_factory=TechStack)
    diagrams: dict[str, str] = Field(default_factory=dict)


class CodeReview(BaseModel):
    score: float = Field(ge=0, le=10)
    summary: str
    issues: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    security_concerns: list[str] = Field(default_factory=list)
    approved: bool = False


class ProjectOutput(BaseModel):
    project_name: str
    backend_code: dict[str, str] = Field(default_factory=dict)
    frontend_code: dict[str, str] = Field(default_factory=dict)
    devops_configs: dict[str, str] = Field(default_factory=dict)
    tests: dict[str, str] = Field(default_factory=dict)
    documentation: dict[str, str] = Field(default_factory=dict)


class DeploymentPlan(BaseModel):
    project_name: str
    environment: str = "production"
    strategy: str = "rolling"
    dockerfile: str = ""
    kubernetes_manifests: dict[str, str] = Field(default_factory=dict)
    ci_cd_pipeline: str = ""
    environment_variables: dict[str, str] = Field(default_factory=dict)
    health_checks: list[str] = Field(default_factory=list)
    rollback_plan: str = ""


class SWArchitectAgent:
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.log = log.bind(agent="sw_architect")
        self._sub_agents: dict | None = None

    def _get_sub_agents(self):
        if self._sub_agents is None:
            from .sub_agents import (
                BackendDeveloperAgent,
                DevOpsAgent,
                FrontendDeveloperAgent,
                QAAgent,
            )

            self._sub_agents = {
                "backend": BackendDeveloperAgent(llm_client=self.llm_client),
                "frontend": FrontendDeveloperAgent(llm_client=self.llm_client),
                "devops": DevOpsAgent(llm_client=self.llm_client),
                "qa": QAAgent(llm_client=self.llm_client),
            }
        return self._sub_agents

    async def analyze_idea(self, idea: str) -> ProjectPlan:
        self.log.info("analyzing_idea", idea_length=len(idea))

        if self.llm_client is not None:
            return await self._llm_analyze_idea(idea)

        words = idea.lower().split()
        features = []
        tech = TechStack()

        if any(w in words for w in ("web", "website", "app", "application", "platform")):
            features.extend(["User authentication", "Dashboard", "REST API"])
            tech.frameworks.extend(["FastAPI", "React"])
            tech.languages.extend(["Python", "TypeScript"])
            tech.databases.append("PostgreSQL")

        if any(w in words for w in ("api", "backend", "server", "service")):
            features.extend(["API endpoints", "Rate limiting", "Authentication"])
            tech.frameworks.append("FastAPI")
            tech.languages.append("Python")
            tech.databases.append("PostgreSQL")

        if any(w in words for w in ("mobile", "ios", "android")):
            features.extend(["Mobile UI", "Push notifications", "Offline support"])
            tech.frameworks.append("React Native")
            tech.languages.append("TypeScript")

        if any(w in words for w in ("data", "analytics", "ml", "ai")):
            features.extend(["Data pipeline", "Analytics dashboard", "ML model serving"])
            tech.frameworks.extend(["Pandas", "scikit-learn"])
            tech.languages.append("Python")
            tech.databases.append("Redis")

        if not features:
            features = ["Core functionality", "User interface", "Data storage", "API layer"]
            tech.languages.append("Python")
            tech.frameworks.append("FastAPI")
            tech.databases.append("SQLite")

        tech.infrastructure.extend(["Docker", "Kubernetes"])
        tech.tools.extend(["GitHub Actions", "Prometheus", "Grafana"])

        plan = ProjectPlan(
            name=self._derive_project_name(idea),
            description=idea,
            goals=[
                f"Build a functional product: {idea[:80]}",
                "Deliver production-ready code with tests",
                "Provide deployment configurations",
            ],
            features=features,
            constraints=["Must be containerized", "Must include CI/CD", "Must have >80% test coverage"],
            milestones=[
                "Architecture design complete",
                "Backend implementation",
                "Frontend implementation",
                "Testing and QA",
                "Deployment ready",
            ],
            tech_stack=tech,
        )

        self.log.info("idea_analyzed", project_name=plan.name, feature_count=len(plan.features))
        return plan

    async def design_architecture(self, plan: ProjectPlan) -> Architecture:
        self.log.info("designing_architecture", project=plan.name)

        if self.llm_client is not None:
            return await self._llm_design_architecture(plan)

        components = [
            Component(
                name="API Gateway",
                description="Entry point for all client requests",
                technology=next((f for f in plan.tech_stack.frameworks if "Fast" in f or "Flask" in f), "FastAPI"),
                responsibilities=["Request routing", "Authentication", "Rate limiting"],
                dependencies=[],
            ),
            Component(
                name="Core Service",
                description=f"Core business logic for {plan.name}",
                technology=plan.tech_stack.languages[0] if plan.tech_stack.languages else "Python",
                responsibilities=["Business logic", "Data validation", "Event processing"],
                dependencies=["API Gateway"],
            ),
            Component(
                name="Data Store",
                description="Primary data persistence layer",
                technology=plan.tech_stack.databases[0] if plan.tech_stack.databases else "PostgreSQL",
                responsibilities=["Data persistence", "Query optimization", "Data integrity"],
                dependencies=["Core Service"],
            ),
        ]

        if any("React" in f for f in plan.tech_stack.frameworks):
            components.append(
                Component(
                    name="Frontend App",
                    description="User-facing web application",
                    technology="React",
                    responsibilities=["User interface", "State management", "API integration"],
                    dependencies=["API Gateway"],
                )
            )

        apis = [
            API(
                name="Health Check", method="GET", path="/health",
                description="Service health endpoint", authentication=False,
            ),
            API(
                name="List Resources", method="GET",
                path="/api/v1/resources", description="List all resources",
            ),
            API(
                name="Create Resource", method="POST",
                path="/api/v1/resources", description="Create a new resource",
                request_schema={"type": "object", "properties": {"name": {"type": "string"}}},
            ),
            API(
                name="Get Resource", method="GET",
                path="/api/v1/resources/{id}", description="Get resource by ID",
            ),
            API(
                name="Update Resource", method="PUT",
                path="/api/v1/resources/{id}", description="Update a resource",
            ),
            API(
                name="Delete Resource", method="DELETE",
                path="/api/v1/resources/{id}", description="Delete a resource",
            ),
        ]

        data_models = [
            DataModel(
                name="User",
                fields={
                    "id": "UUID", "email": "str", "hashed_password": "str",
                    "created_at": "datetime", "is_active": "bool",
                },
                relationships=["has_many:Resource"],
                indexes=["email"],
            ),
            DataModel(
                name="Resource",
                fields={
                    "id": "UUID", "name": "str", "data": "JSON",
                    "owner_id": "UUID", "created_at": "datetime",
                    "updated_at": "datetime",
                },
                relationships=["belongs_to:User"],
                indexes=["owner_id", "created_at"],
            ),
        ]

        architecture = Architecture(
            project_name=plan.name,
            style="microservices" if len(components) > 3 else "monolith",
            components=components,
            apis=apis,
            data_models=data_models,
            tech_stack=plan.tech_stack,
        )

        self.log.info(
            "architecture_designed",
            project=plan.name,
            components=len(components),
            apis=len(apis),
            models=len(data_models),
        )
        return architecture

    async def generate_project(self, architecture: Architecture) -> ProjectOutput:
        self.log.info("generating_project", project=architecture.project_name)
        agents = self._get_sub_agents()

        backend_task = {
            "type": "backend",
            "project_name": architecture.project_name,
            "components": [c.model_dump() for c in architecture.components if c.name != "Frontend App"],
            "apis": [a.model_dump() for a in architecture.apis],
            "data_models": [m.model_dump() for m in architecture.data_models],
            "tech_stack": architecture.tech_stack.model_dump(),
        }

        frontend_task = {
            "type": "frontend",
            "project_name": architecture.project_name,
            "components": [c.model_dump() for c in architecture.components if c.name == "Frontend App"],
            "apis": [a.model_dump() for a in architecture.apis],
            "tech_stack": architecture.tech_stack.model_dump(),
        }

        devops_task = {
            "type": "devops",
            "project_name": architecture.project_name,
            "components": [c.model_dump() for c in architecture.components],
            "tech_stack": architecture.tech_stack.model_dump(),
        }

        import asyncio

        backend_result, frontend_result, devops_result = await asyncio.gather(
            agents["backend"].execute(backend_task),
            agents["frontend"].execute(frontend_task),
            agents["devops"].execute(devops_task),
        )

        qa_task = {
            "type": "qa",
            "project_name": architecture.project_name,
            "backend_code": backend_result,
            "frontend_code": frontend_result,
            "apis": [a.model_dump() for a in architecture.apis],
        }
        test_result = await agents["qa"].execute(qa_task)

        output = ProjectOutput(
            project_name=architecture.project_name,
            backend_code=backend_result,
            frontend_code=frontend_result,
            devops_configs=devops_result,
            tests=test_result,
            documentation={
                "README.md": self._generate_readme(architecture),
                "API.md": self._generate_api_docs(architecture),
            },
        )

        self.log.info(
            "project_generated",
            project=architecture.project_name,
            backend_files=len(output.backend_code),
            frontend_files=len(output.frontend_code),
            devops_files=len(output.devops_configs),
            test_files=len(output.tests),
        )
        return output

    async def review_code(self, code: str) -> CodeReview:
        self.log.info("reviewing_code", code_length=len(code))

        if self.llm_client is not None:
            return await self._llm_review_code(code)

        issues: list[str] = []
        suggestions: list[str] = []
        security_concerns: list[str] = []
        score = 7.0

        lines = code.split("\n")
        for i, line in enumerate(lines, 1):
            stripped = line.rstrip()
            if len(stripped) > 120:
                issues.append(f"Line {i}: exceeds 120 character limit ({len(stripped)} chars)")
                score -= 0.1

            if "eval(" in line or "exec(" in line:
                security_concerns.append(f"Line {i}: use of eval/exec is a security risk")
                score -= 0.5

            if "password" in line.lower() and ("=" in line) and ("os.environ" not in line) and ("getenv" not in line):
                security_concerns.append(f"Line {i}: possible hardcoded password")
                score -= 0.5

            if "import *" in line:
                issues.append(f"Line {i}: wildcard import")
                score -= 0.2

            if "TODO" in line or "FIXME" in line or "HACK" in line:
                suggestions.append(f"Line {i}: unresolved marker found")

        if not any("def test_" in line or "class Test" in line for line in lines):
            suggestions.append("No test functions found — consider adding tests")

        if not any(line.strip().startswith('"""') or line.strip().startswith("'''") for line in lines):
            suggestions.append("No docstrings found — consider adding documentation")

        if not any("import logging" in line or "import structlog" in line or "getLogger" in line for line in lines):
            suggestions.append("No logging imports found — consider adding structured logging")

        score = max(0.0, min(10.0, score))

        review = CodeReview(
            score=round(score, 1),
            summary=f"Code review complete. Found {len(issues)} issues, {len(security_concerns)} security concerns.",
            issues=issues,
            suggestions=suggestions,
            security_concerns=security_concerns,
            approved=score >= 6.0 and len(security_concerns) == 0,
        )

        self.log.info("code_reviewed", score=review.score, approved=review.approved)
        return review

    async def create_deployment_plan(self, project: ProjectOutput) -> DeploymentPlan:
        self.log.info("creating_deployment_plan", project=project.project_name)

        if self.llm_client is not None:
            return await self._llm_create_deployment_plan(project)

        dockerfile = (
            "FROM python:3.12-slim\n"
            "WORKDIR /app\n"
            "COPY requirements.txt .\n"
            "RUN pip install --no-cache-dir -r requirements.txt\n"
            "COPY . .\n"
            "EXPOSE 8000\n"
            'CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]\n'
        )

        k8s_deployment = (
            "apiVersion: apps/v1\n"
            "kind: Deployment\n"
            "metadata:\n"
            f"  name: {project.project_name.lower().replace(' ', '-')}\n"
            "spec:\n"
            "  replicas: 3\n"
            "  selector:\n"
            "    matchLabels:\n"
            f"      app: {project.project_name.lower().replace(' ', '-')}\n"
            "  template:\n"
            "    metadata:\n"
            "      labels:\n"
            f"        app: {project.project_name.lower().replace(' ', '-')}\n"
            "    spec:\n"
            "      containers:\n"
            f"      - name: {project.project_name.lower().replace(' ', '-')}\n"
            f"        image: {project.project_name.lower().replace(' ', '-')}:latest\n"
            "        ports:\n"
            "        - containerPort: 8000\n"
            "        readinessProbe:\n"
            "          httpGet:\n"
            "            path: /health\n"
            "            port: 8000\n"
            "          initialDelaySeconds: 5\n"
            "          periodSeconds: 10\n"
            "        livenessProbe:\n"
            "          httpGet:\n"
            "            path: /health\n"
            "            port: 8000\n"
            "          initialDelaySeconds: 15\n"
            "          periodSeconds: 20\n"
        )

        k8s_service = (
            "apiVersion: v1\n"
            "kind: Service\n"
            "metadata:\n"
            f"  name: {project.project_name.lower().replace(' ', '-')}-svc\n"
            "spec:\n"
            "  selector:\n"
            f"    app: {project.project_name.lower().replace(' ', '-')}\n"
            "  ports:\n"
            "  - protocol: TCP\n"
            "    port: 80\n"
            "    targetPort: 8000\n"
            "  type: ClusterIP\n"
        )

        ci_cd = (
            "name: CI/CD\n"
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
            "    - run: pytest --cov\n"
            "  deploy:\n"
            "    needs: test\n"
            "    runs-on: ubuntu-latest\n"
            "    if: github.ref == 'refs/heads/main'\n"
            "    steps:\n"
            "    - uses: actions/checkout@v4\n"
            "    - run: docker build -t ${{ github.repository }}:${{ github.sha }} .\n"
            "    - run: docker push ${{ github.repository }}:${{ github.sha }}\n"
        )

        plan = DeploymentPlan(
            project_name=project.project_name,
            environment="production",
            strategy="rolling",
            dockerfile=dockerfile,
            kubernetes_manifests={"deployment.yaml": k8s_deployment, "service.yaml": k8s_service},
            ci_cd_pipeline=ci_cd,
            environment_variables={
                "DATABASE_URL": "postgresql://user:pass@db:5432/app",
                "SECRET_KEY": "change-me-in-production",
                "LOG_LEVEL": "INFO",
                "ALLOWED_ORIGINS": "*",
            },
            health_checks=["/health", "/readiness"],
            rollback_plan="kubectl rollout undo deployment/" + project.project_name.lower().replace(" ", "-"),
        )

        self.log.info("deployment_plan_created", project=project.project_name, strategy=plan.strategy)
        return plan

    async def _llm_analyze_idea(self, idea: str) -> ProjectPlan:
        prompt = (
            "You are a senior software architect. Analyze the following idea and produce a structured project plan.\n\n"
            f"Idea: {idea}\n\n"
            "Respond with a JSON object matching the ProjectPlan schema with fields: "
            "name, description, goals, features, constraints, milestones, tech_stack."
        )
        response = await self._call_llm(prompt)
        return ProjectPlan.model_validate_json(response)

    async def _llm_design_architecture(self, plan: ProjectPlan) -> Architecture:
        prompt = (
            "You are a senior software architect. Design a system architecture for the following project plan.\n\n"
            f"Plan: {plan.model_dump_json()}\n\n"
            "Respond with a JSON object matching the Architecture schema."
        )
        response = await self._call_llm(prompt)
        return Architecture.model_validate_json(response)

    async def _llm_review_code(self, code: str) -> CodeReview:
        prompt = (
            "You are a senior code reviewer. Review the following code.\n\n"
            f"```\n{code}\n```\n\n"
            "Respond with a JSON object matching the CodeReview schema with fields: "
            "score (0-10), summary, issues, suggestions, security_concerns, approved."
        )
        response = await self._call_llm(prompt)
        return CodeReview.model_validate_json(response)

    async def _llm_create_deployment_plan(self, project: ProjectOutput) -> DeploymentPlan:
        prompt = (
            "You are a senior DevOps engineer. Create a deployment plan for the following project.\n\n"
            f"Project: {project.project_name}\n"
            f"Backend files: {list(project.backend_code.keys())}\n"
            f"Frontend files: {list(project.frontend_code.keys())}\n\n"
            "Respond with a JSON object matching the DeploymentPlan schema."
        )
        response = await self._call_llm(prompt)
        return DeploymentPlan.model_validate_json(response)

    async def _call_llm(self, prompt: str) -> str:
        if self.llm_client is None:
            raise RuntimeError("LLM client not configured")

        if hasattr(self.llm_client, "chat") and hasattr(self.llm_client.chat, "completions"):
            response = await self.llm_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            return response.choices[0].message.content

        if hasattr(self.llm_client, "messages"):
            response = await self.llm_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text

        raise RuntimeError(f"Unsupported LLM client type: {type(self.llm_client)}")

    @staticmethod
    def _derive_project_name(idea: str) -> str:
        stop_words = {
            "a", "an", "the", "is", "for", "to", "and", "or",
            "that", "this", "with", "i", "want", "need", "build", "create", "make",
        }
        words = [w for w in idea.split()[:8] if w.lower() not in stop_words]
        name = " ".join(words[:4]).strip(" .,!?")
        return name.title() if name else "New Project"

    @staticmethod
    def _generate_readme(architecture: Architecture) -> str:
        components_list = "\n".join(f"- **{c.name}**: {c.description}" for c in architecture.components)
        tech = architecture.tech_stack
        tech_list = ", ".join(tech.languages + tech.frameworks + tech.databases)
        return (
            f"# {architecture.project_name}\n\n"
            f"## Architecture\n\nStyle: {architecture.style}\n\n"
            f"## Components\n\n{components_list}\n\n"
            f"## Tech Stack\n\n{tech_list}\n\n"
            "## Getting Started\n\n"
            "```bash\ndocker-compose up\n```\n"
        )

    @staticmethod
    def _generate_api_docs(architecture: Architecture) -> str:
        lines = [f"# {architecture.project_name} API Documentation\n"]
        for api in architecture.apis:
            lines.append(f"## {api.method} {api.path}\n")
            lines.append(f"{api.description}\n")
            lines.append(f"- Authentication: {'Required' if api.authentication else 'None'}\n")
        return "\n".join(lines)
