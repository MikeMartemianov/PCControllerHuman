"""
InsightModule (ФМ) - Background problem solving with "eureka" moments.

Processes complex tasks in the background and saves solutions to memory.
When the entity recalls a task, the solution "appears" automatically as an insight.
"""

import asyncio
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional, TYPE_CHECKING

from living_entity.utils.logging import get_logger

if TYPE_CHECKING:
    from living_entity.memory.matrix import MemoryMatrix


class InsightStatus(Enum):
    """Status of an insight task."""
    PENDING = "pending"
    PROCESSING = "processing"
    SOLVED = "solved"
    FAILED = "failed"


@dataclass
class InsightTask:
    """A complex problem submitted for background processing."""
    id: str
    problem: str
    context: str = ""
    status: InsightStatus = InsightStatus.PENDING
    solution: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    solved_at: Optional[datetime] = None
    priority: int = 5  # 1-10, higher = more important
    metadata: dict = field(default_factory=dict)


class InsightModule:
    """
    Module for background problem solving with "eureka" moments.
    
    Features:
    - Accepts complex problems for background processing
    - Uses LLM to solve problems asynchronously
    - Saves solutions to memory with high importance
    - Provides "insight" retrieval for recalled tasks
    
    Example:
        ```python
        insight = InsightModule(memory=memory_matrix, llm_callback=llm_call)
        
        # Submit a complex problem
        task_id = insight.submit_problem(
            "How to optimize this algorithm?",
            context="Current complexity is O(n^2)..."
        )
        
        # Later, check for insights
        solution = insight.check_insight("optimize algorithm")
        if solution:
            print(f"Eureka! {solution}")
        ```
    """
    
    MEMORY_SOURCE = "insight"
    MEMORY_IMPORTANCE = 0.85
    
    def __init__(
        self,
        memory: Optional["MemoryMatrix"] = None,
        llm_callback: Optional[Callable] = None,
        max_concurrent: int = 3,
        processing_delay: float = 2.0,
    ):
        """
        Initialize the Insight Module.
        
        :param memory: MemoryMatrix for storing solutions
        :param llm_callback: Async callback for LLM calls (async def callback(prompt) -> str)
        :param max_concurrent: Maximum concurrent background tasks
        :param processing_delay: Delay before processing (simulates "thinking")
        """
        self.memory = memory
        self._llm_callback = llm_callback
        self.max_concurrent = max_concurrent
        self.processing_delay = processing_delay
        self.logger = get_logger()
        
        # Task storage
        self._tasks: dict[str, InsightTask] = {}
        self._task_queue: asyncio.Queue[str] = asyncio.Queue()
        self._pending_queue: list[str] = []  # Tasks submitted before start()
        
        # Processing state
        self._running = False
        self._processor_task: Optional[asyncio.Task] = None
        
        # Callbacks
        self._on_insight: Optional[Callable[[InsightTask], None]] = None
        
        self.logger.info("InsightModule initialized", module="insight")
    
    def _generate_id(self, problem: str) -> str:
        """Generate unique ID for a problem."""
        timestamp = datetime.now().isoformat()
        content = f"{timestamp}:{problem[:100]}"
        return f"insight_{hashlib.sha256(content.encode()).hexdigest()[:12]}"
    
    def set_llm_callback(self, callback: Callable) -> None:
        """Set the LLM callback for problem solving."""
        self._llm_callback = callback
    
    def submit_problem(
        self,
        problem: str,
        context: str = "",
        priority: int = 5,
        metadata: Optional[dict] = None,
    ) -> str:
        """
        Submit a complex problem for background processing.
        
        :param problem: The problem description
        :param context: Additional context for solving
        :param priority: Priority 1-10 (higher = more important)
        :param metadata: Additional metadata
        :return: Task ID for tracking
        """
        task_id = self._generate_id(problem)
        
        task = InsightTask(
            id=task_id,
            problem=problem,
            context=context,
            priority=min(max(priority, 1), 10),
            metadata=metadata or {},
        )
        
        self._tasks[task_id] = task
        
        # Add to processing queue if running, otherwise store for later
        if self._running:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._queue_task(task_id))
            except RuntimeError:
                # No running loop, will be queued on start()
                self._pending_queue.append(task_id)
        else:
            # Store for queueing when start() is called
            if not hasattr(self, '_pending_queue'):
                self._pending_queue: list[str] = []
            self._pending_queue.append(task_id)
        
        self.logger.info(f"Problem submitted: {problem[:50]}...", module="insight")
        return task_id
    
    async def _queue_task(self, task_id: str) -> None:
        """Add task to processing queue."""
        await self._task_queue.put(task_id)
    
    async def start(self) -> None:
        """Start the background processor."""
        if self._running:
            return
        
        self._running = True
        
        # Queue any pending tasks that were submitted before start()
        for task_id in self._pending_queue:
            await self._queue_task(task_id)
        self._pending_queue.clear()
        
        self._processor_task = asyncio.create_task(self._background_processor())
        self.logger.info("InsightModule processor started", module="insight")
    
    async def stop(self) -> None:
        """Stop the background processor."""
        self._running = False
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
        self.logger.info("InsightModule processor stopped", module="insight")
    
    async def _background_processor(self) -> None:
        """Background task processor loop."""
        while self._running:
            try:
                # Wait for tasks with timeout
                try:
                    task_id = await asyncio.wait_for(
                        self._task_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                task = self._tasks.get(task_id)
                if not task or task.status != InsightStatus.PENDING:
                    continue
                
                # Simulate "thinking" delay
                await asyncio.sleep(self.processing_delay)
                
                # Process the task
                await self._solve_problem(task)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Processor error: {e}", module="insight")
    
    async def _solve_problem(self, task: InsightTask) -> None:
        """Solve a problem using LLM."""
        task.status = InsightStatus.PROCESSING
        
        if not self._llm_callback:
            self.logger.warning("No LLM callback set, using fallback", module="insight")
            task.solution = f"[Pending human insight for: {task.problem[:100]}]"
            task.status = InsightStatus.SOLVED
            task.solved_at = datetime.now()
            self._save_insight(task)
            return
        
        try:
            # Build prompt for problem solving
            prompt = self._build_solve_prompt(task)
            
            # Call LLM
            solution = await self._llm_callback(prompt)
            
            task.solution = solution
            task.status = InsightStatus.SOLVED
            task.solved_at = datetime.now()
            
            # Save to memory
            self._save_insight(task)
            
            self.logger.info(f"Problem solved: {task.problem[:50]}...", module="insight")
            
            # Notify callback
            if self._on_insight:
                self._on_insight(task)
                
        except Exception as e:
            task.status = InsightStatus.FAILED
            task.error = str(e)
            self.logger.error(f"Problem solving failed: {e}", module="insight")
    
    def _build_solve_prompt(self, task: InsightTask) -> str:
        """Build prompt for problem solving."""
        prompt = f"""Ты - модуль глубокого анализа. Реши следующую сложную задачу.

## Задача:
{task.problem}

"""
        if task.context:
            prompt += f"""## Контекст:
{task.context}

"""
        
        prompt += """## Инструкции:
1. Проанализируй задачу глубоко
2. Рассмотри разные подходы
3. Выбери оптимальное решение
4. Объясни решение кратко и ясно

## Решение:"""
        
        return prompt
    
    def _save_insight(self, task: InsightTask) -> None:
        """Save solved insight to memory."""
        if not self.memory or not task.solution:
            return
        
        # Format memory entry
        memory_text = f"[ОЗАРЕНИЕ] Задача: {task.problem[:100]}... Решение: {task.solution[:500]}"
        
        try:
            self.memory.save_memory(
                text=memory_text,
                source=self.MEMORY_SOURCE,
                importance=self.MEMORY_IMPORTANCE,
                metadata={
                    "type": "insight",
                    "task_id": task.id,
                    "priority": task.priority,
                    "solved_at": task.solved_at.isoformat() if task.solved_at else None,
                }
            )
            self.logger.memory(f"Insight saved: {task.problem[:30]}...")
        except Exception as e:
            self.logger.error(f"Failed to save insight: {e}", module="insight")
    
    def check_insight(self, query: str, threshold: float = 0.6) -> Optional[str]:
        """
        Check if there's a relevant insight for a query.
        
        This is the "eureka" moment - when recalling a problem,
        the solution automatically appears from memory.
        
        :param query: Search query (related to a problem)
        :param threshold: Relevance threshold
        :return: Solution if found, None otherwise
        """
        if not self.memory:
            # Check local tasks
            for task in self._tasks.values():
                if task.status == InsightStatus.SOLVED and task.solution:
                    if query.lower() in task.problem.lower():
                        return task.solution
            return None
        
        # Search memory for insights
        results = self.memory.retrieve(
            query=query,
            threshold=threshold,
            max_results=3,
        )
        
        for result in results:
            if result.entry.source == self.MEMORY_SOURCE:
                # Extract solution from memory
                text = result.entry.text
                if "Решение:" in text:
                    return text.split("Решение:", 1)[1].strip()
                return text
        
        return None
    
    def get_pending_count(self) -> int:
        """Get count of pending tasks."""
        return sum(
            1 for t in self._tasks.values()
            if t.status in (InsightStatus.PENDING, InsightStatus.PROCESSING)
        )
    
    def get_solved_count(self) -> int:
        """Get count of solved tasks."""
        return sum(
            1 for t in self._tasks.values()
            if t.status == InsightStatus.SOLVED
        )
    
    def get_task(self, task_id: str) -> Optional[InsightTask]:
        """Get a task by ID."""
        return self._tasks.get(task_id)
    
    def get_all_insights(self) -> list[InsightTask]:
        """Get all solved insights."""
        return [
            t for t in self._tasks.values()
            if t.status == InsightStatus.SOLVED
        ]
    
    def on_insight(self, callback: Callable[[InsightTask], None]) -> None:
        """Register callback for when an insight is ready."""
        self._on_insight = callback
    
    def clear_solved(self) -> int:
        """Clear solved tasks from memory. Returns count removed."""
        to_remove = [
            task_id for task_id, task in self._tasks.items()
            if task.status in (InsightStatus.SOLVED, InsightStatus.FAILED)
        ]
        
        for task_id in to_remove:
            del self._tasks[task_id]
        
        return len(to_remove)
