from __future__ import annotations

import asyncio
import uuid
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

import structlog
from pydantic import BaseModel, Field

from src.core.llm_provider import LLMProvider, LLMProviderConfig

logger = structlog.get_logger(__name__)


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentTask(BaseModel):
    """Represents a unit of work assigned to an agent."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str = ""
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentStatus(BaseModel):
    """Snapshot of an agent's current state."""

    agent_id: str
    agent_type: str
    is_running: bool
    current_task: AgentTask | None = None
    completed_tasks: int = 0
    failed_tasks: int = 0


class BaseAgent(ABC):
    """Abstract base for all agents in the system.

    Provides lifecycle management, LLM access, task tracking,
    and the ability to delegate work to sub-agents.
    """

    def __init__(
        self,
        agent_id: str | None = None,
        agent_type: str = "base",
        llm_config: LLMProviderConfig | None = None,
    ) -> None:
        self.agent_id = agent_id or str(uuid.uuid4())
        self.agent_type = agent_type
        self._is_running = False
        self._current_task: AgentTask | None = None
        self._completed_tasks: int = 0
        self._failed_tasks: int = 0
        self._sub_agents: dict[str, BaseAgent] = {}
        self._llm: LLMProvider | None = None
        self._llm_config = llm_config
        self._log = logger.bind(agent_id=self.agent_id, agent_type=self.agent_type)

    async def initialize(self) -> None:
        """Prepare the agent for work (LLM client, resources, etc.)."""
        self._log.info("agent.initializing")
        if self._llm_config:
            self._llm = LLMProvider(self._llm_config)
        self._is_running = True
        await self._on_initialize()
        self._log.info("agent.initialized")

    @abstractmethod
    async def _on_initialize(self) -> None:
        ...

    async def execute_task(self, task: AgentTask) -> AgentTask:
        """Run a task through this agent's processing pipeline."""
        self._current_task = task
        task.status = TaskStatus.IN_PROGRESS
        self._log.info("task.started", task_id=task.id, task_type=task.type)

        try:
            result = await self._process_task(task)
            task.result = result
            task.status = TaskStatus.COMPLETED
            self._completed_tasks += 1
            self._log.info("task.completed", task_id=task.id)
        except Exception as exc:
            task.status = TaskStatus.FAILED
            task.error = str(exc)
            self._failed_tasks += 1
            self._log.error("task.failed", task_id=task.id, error=str(exc))
        finally:
            self._current_task = None

        return task

    @abstractmethod
    async def _process_task(self, task: AgentTask) -> Any:
        ...

    async def delegate_to_subagent(self, agent: BaseAgent, task: AgentTask) -> AgentTask:
        """Hand a task to a sub-agent, initializing it first if needed."""
        if agent.agent_id not in self._sub_agents:
            self._sub_agents[agent.agent_id] = agent
            if not agent._is_running:
                await agent.initialize()

        self._log.info(
            "task.delegated",
            task_id=task.id,
            target_agent=agent.agent_id,
        )
        return await agent.execute_task(task)

    async def delegate_to_subagents(
        self, assignments: list[tuple[BaseAgent, AgentTask]]
    ) -> list[AgentTask]:
        """Delegate multiple tasks concurrently."""
        coros = [self.delegate_to_subagent(agent, task) for agent, task in assignments]
        return list(await asyncio.gather(*coros, return_exceptions=False))

    def get_status(self) -> AgentStatus:
        return AgentStatus(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            is_running=self._is_running,
            current_task=self._current_task,
            completed_tasks=self._completed_tasks,
            failed_tasks=self._failed_tasks,
        )

    async def shutdown(self) -> None:
        """Tear down the agent and all its sub-agents."""
        self._log.info("agent.shutting_down")
        for sub in self._sub_agents.values():
            await sub.shutdown()
        self._sub_agents.clear()
        self._is_running = False
        await self._on_shutdown()
        self._log.info("agent.shut_down")

    async def _on_shutdown(self) -> None:
        pass

    @property
    def llm(self) -> LLMProvider:
        if self._llm is None:
            raise RuntimeError("LLM provider not initialized — call initialize() first or supply llm_config")
        return self._llm
