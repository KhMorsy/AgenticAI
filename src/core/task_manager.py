from __future__ import annotations

import asyncio
import heapq
import uuid
from enum import Enum
from typing import Any

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class TaskPriority(int, Enum):
    LOW = 30
    MEDIUM = 20
    HIGH = 10
    CRITICAL = 0


class Task(BaseModel):
    """A discrete unit of work with optional parent/child relationships."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str = ""
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    result: Any = None
    error: str | None = None
    parent_task_id: str | None = None
    subtask_ids: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class _PrioritizedTask:
    """Wrapper that makes :class:`Task` sortable by priority then creation order."""

    _counter: int = 0

    def __init__(self, task: Task) -> None:
        _PrioritizedTask._counter += 1
        self.priority = task.priority.value
        self.order = _PrioritizedTask._counter
        self.task = task

    def __lt__(self, other: _PrioritizedTask) -> bool:
        return (self.priority, self.order) < (other.priority, other.order)


class TaskManager:
    """Manages the full lifecycle of tasks including dependency resolution."""

    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}
        self._queue: list[_PrioritizedTask] = []
        self._lock = asyncio.Lock()
        self._log = logger.bind(component="task_manager")

    async def create_task(
        self,
        type: str,
        description: str,
        *,
        priority: TaskPriority = TaskPriority.MEDIUM,
        parent_task_id: str | None = None,
        depends_on: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Task:
        task = Task(
            type=type,
            description=description,
            priority=priority,
            parent_task_id=parent_task_id,
            depends_on=depends_on or [],
            metadata=metadata or {},
        )

        async with self._lock:
            self._tasks[task.id] = task

            if parent_task_id and parent_task_id in self._tasks:
                self._tasks[parent_task_id].subtask_ids.append(task.id)

            if self._dependencies_met(task):
                heapq.heappush(self._queue, _PrioritizedTask(task))
            else:
                task.status = TaskStatus.BLOCKED

        self._log.info("task.created", task_id=task.id, type=type, priority=priority.name)
        return task

    async def update_task(
        self,
        task_id: str,
        *,
        status: TaskStatus | None = None,
        result: Any = None,
        error: str | None = None,
    ) -> Task:
        async with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                raise KeyError(f"Task {task_id} not found")

            if status is not None:
                task.status = status
            if result is not None:
                task.result = result
            if error is not None:
                task.error = error

            if status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                self._unblock_dependents(task_id)

        self._log.info("task.updated", task_id=task_id, status=task.status.value)
        return task

    async def get_task(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)

    async def list_tasks(
        self,
        *,
        status: TaskStatus | None = None,
        parent_task_id: str | None = None,
    ) -> list[Task]:
        tasks = self._tasks.values()
        if status is not None:
            tasks = [t for t in tasks if t.status == status]
        if parent_task_id is not None:
            tasks = [t for t in tasks if t.parent_task_id == parent_task_id]
        return list(tasks)

    async def get_next_task(self) -> Task | None:
        async with self._lock:
            while self._queue:
                entry = heapq.heappop(self._queue)
                task = entry.task
                if task.status in (TaskStatus.PENDING, TaskStatus.BLOCKED):
                    if self._dependencies_met(task):
                        task.status = TaskStatus.IN_PROGRESS
                        return task
            return None

    async def get_subtasks(self, task_id: str) -> list[Task]:
        task = self._tasks.get(task_id)
        if task is None:
            return []
        return [self._tasks[sid] for sid in task.subtask_ids if sid in self._tasks]

    def _dependencies_met(self, task: Task) -> bool:
        for dep_id in task.depends_on:
            dep = self._tasks.get(dep_id)
            if dep is None or dep.status != TaskStatus.COMPLETED:
                return False
        return True

    def _unblock_dependents(self, completed_id: str) -> None:
        for task in self._tasks.values():
            if task.status != TaskStatus.BLOCKED:
                continue
            if completed_id not in task.depends_on:
                continue
            if self._dependencies_met(task):
                task.status = TaskStatus.PENDING
                heapq.heappush(self._queue, _PrioritizedTask(task))
                self._log.info("task.unblocked", task_id=task.id)

    async def resolve_dependencies(self, task_id: str) -> list[str]:
        """Return a topological ordering of *task_id* and its transitive dependencies."""
        visited: set[str] = set()
        order: list[str] = []

        def _visit(tid: str) -> None:
            if tid in visited:
                return
            visited.add(tid)
            task = self._tasks.get(tid)
            if task is None:
                return
            for dep in task.depends_on:
                _visit(dep)
            order.append(tid)

        _visit(task_id)
        return order
