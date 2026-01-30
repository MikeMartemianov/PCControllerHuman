"""
FocusModule - Complex task handling with multi-step decomposition.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel

from living_entity.utils.logging import get_logger


class TaskStatus(Enum):
    """Status of a focus task."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Priority levels for tasks."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class TaskStep:
    """A single step in a complex task."""
    id: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class FocusTask:
    """A complex task being processed by the Focus Module."""
    id: str
    title: str
    description: str
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    steps: list[TaskStep] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    result: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def add_step(self, step_id: str, description: str) -> TaskStep:
        """Add a new step to the task."""
        step = TaskStep(id=step_id, description=description)
        self.steps.append(step)
        return step
    
    def get_current_step(self) -> Optional[TaskStep]:
        """Get the current step being worked on."""
        for step in self.steps:
            if step.status in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS):
                return step
        return None
    
    def get_progress(self) -> float:
        """Get task progress as a percentage."""
        if not self.steps:
            return 0.0
        completed = sum(1 for s in self.steps if s.status == TaskStatus.COMPLETED)
        return (completed / len(self.steps)) * 100


class FocusModule:
    """
    Module for handling complex, multi-step tasks.
    
    Features:
    - Task decomposition
    - Progress tracking
    - Step-by-step execution
    - Result aggregation
    """
    
    def __init__(self, max_concurrent_tasks: int = 3):
        """
        Initialize the Focus Module.
        
        :param max_concurrent_tasks: Maximum number of concurrent tasks
        """
        self.max_concurrent_tasks = max_concurrent_tasks
        self.logger = get_logger()
        
        # Task storage
        self._tasks: dict[str, FocusTask] = {}
        self._task_queue: asyncio.Queue[str] = asyncio.Queue()
        
        # Callbacks
        self._on_step_complete: Optional[callable] = None
        self._on_task_complete: Optional[callable] = None
    
    def create_task(
        self,
        task_id: str,
        title: str,
        description: str,
        priority: TaskPriority = TaskPriority.MEDIUM,
        context: Optional[dict] = None,
    ) -> FocusTask:
        """
        Create a new focus task.
        
        :param task_id: Unique task identifier
        :param title: Task title
        :param description: Task description
        :param priority: Task priority
        :param context: Additional context
        :return: Created task
        """
        task = FocusTask(
            id=task_id,
            title=title,
            description=description,
            priority=priority,
            context=context or {},
        )
        
        self._tasks[task_id] = task
        self.logger.info(f"Created focus task: {title}", module="focus")
        
        return task
    
    def add_steps(self, task_id: str, steps: list[tuple[str, str]]) -> None:
        """
        Add steps to a task.
        
        :param task_id: Task ID
        :param steps: List of (step_id, description) tuples
        """
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")
        
        for step_id, description in steps:
            task.add_step(step_id, description)
        
        self.logger.info(
            f"Added {len(steps)} steps to task {task_id}",
            module="focus"
        )
    
    def decompose_task(
        self,
        task_id: str,
        decomposition: list[dict[str, str]],
    ) -> None:
        """
        Decompose a task into steps from LLM output.
        
        :param task_id: Task ID
        :param decomposition: List of step dicts with 'id' and 'description'
        """
        steps = [(d["id"], d["description"]) for d in decomposition]
        self.add_steps(task_id, steps)
    
    async def start_task(self, task_id: str) -> None:
        """
        Start processing a task.
        
        :param task_id: Task ID
        """
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")
        
        task.status = TaskStatus.IN_PROGRESS
        task.started_at = datetime.now()
        
        await self._task_queue.put(task_id)
        self.logger.info(f"Started task: {task.title}", module="focus")
    
    def complete_step(
        self,
        task_id: str,
        step_id: str,
        result: Optional[str] = None,
        error: Optional[str] = None,
    ) -> Optional[TaskStep]:
        """
        Mark a step as completed.
        
        :param task_id: Task ID
        :param step_id: Step ID
        :param result: Step result
        :param error: Error if failed
        :return: The completed step
        """
        task = self._tasks.get(task_id)
        if not task:
            return None
        
        for step in task.steps:
            if step.id == step_id:
                step.completed_at = datetime.now()
                step.result = result
                step.error = error
                
                if error:
                    step.status = TaskStatus.FAILED
                else:
                    step.status = TaskStatus.COMPLETED
                
                self.logger.info(
                    f"Step {step_id} completed: {step.status.value}",
                    module="focus"
                )
                
                # Check if task is complete
                self._check_task_completion(task)
                
                # Call callback
                if self._on_step_complete:
                    self._on_step_complete(task, step)
                
                return step
        
        return None
    
    def _check_task_completion(self, task: FocusTask) -> None:
        """Check if all steps are complete and update task status."""
        if not task.steps:
            return
        
        all_complete = all(
            s.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)
            for s in task.steps
        )
        
        if all_complete:
            has_failures = any(s.status == TaskStatus.FAILED for s in task.steps)
            
            if has_failures:
                task.status = TaskStatus.FAILED
            else:
                task.status = TaskStatus.COMPLETED
            
            task.completed_at = datetime.now()
            
            # Aggregate results
            task.result = self._aggregate_results(task)
            
            self.logger.info(
                f"Task {task.title} completed: {task.status.value}",
                module="focus"
            )
            
            if self._on_task_complete:
                self._on_task_complete(task)
    
    def _aggregate_results(self, task: FocusTask) -> str:
        """Aggregate results from all steps."""
        results = []
        for step in task.steps:
            if step.result:
                results.append(f"[{step.id}] {step.result}")
            elif step.error:
                results.append(f"[{step.id}] ERROR: {step.error}")
        
        return "\n".join(results)
    
    def get_task(self, task_id: str) -> Optional[FocusTask]:
        """Get a task by ID."""
        return self._tasks.get(task_id)
    
    def get_pending_step(self, task_id: str) -> Optional[TaskStep]:
        """Get the next pending step for a task."""
        task = self._tasks.get(task_id)
        if not task:
            return None
        
        for step in task.steps:
            if step.status == TaskStatus.PENDING:
                step.status = TaskStatus.IN_PROGRESS
                step.started_at = datetime.now()
                return step
        
        return None
    
    def get_active_tasks(self) -> list[FocusTask]:
        """Get all active (in-progress) tasks."""
        return [
            t for t in self._tasks.values()
            if t.status == TaskStatus.IN_PROGRESS
        ]
    
    def get_task_summary(self, task_id: str) -> str:
        """Get a summary of a task's status."""
        task = self._tasks.get(task_id)
        if not task:
            return "Task not found"
        
        lines = [
            f"Task: {task.title}",
            f"Status: {task.status.value}",
            f"Progress: {task.get_progress():.1f}%",
            f"Steps: {len(task.steps)}",
        ]
        
        for step in task.steps:
            status_icon = {
                TaskStatus.PENDING: "⏳",
                TaskStatus.IN_PROGRESS: "🔄",
                TaskStatus.COMPLETED: "✅",
                TaskStatus.FAILED: "❌",
            }.get(step.status, "❓")
            
            lines.append(f"  {status_icon} {step.id}: {step.description}")
        
        return "\n".join(lines)
    
    def on_step_complete(self, callback: callable) -> None:
        """Register callback for step completion."""
        self._on_step_complete = callback
    
    def on_task_complete(self, callback: callable) -> None:
        """Register callback for task completion."""
        self._on_task_complete = callback
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task."""
        task = self._tasks.get(task_id)
        if not task:
            return False
        
        if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
            return False
        
        task.status = TaskStatus.CANCELLED
        task.completed_at = datetime.now()
        
        self.logger.info(f"Task cancelled: {task.title}", module="focus")
        return True
    
    def clear_completed(self) -> int:
        """Remove completed/failed/cancelled tasks. Returns count removed."""
        to_remove = [
            task_id for task_id, task in self._tasks.items()
            if task.status in (
                TaskStatus.COMPLETED,
                TaskStatus.FAILED,
                TaskStatus.CANCELLED,
            )
        ]
        
        for task_id in to_remove:
            del self._tasks[task_id]
        
        return len(to_remove)
