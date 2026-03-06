"""
Execution Engine - High-performance async task scheduling and execution.

Handles task queuing, priority scheduling, concurrency control, retries, and timeouts.
"""

import asyncio
import uuid
from typing import Any, Callable, Dict, List, Optional, Coroutine
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import structlog

logger = structlog.get_logger(__name__)


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = 3
    NORMAL = 2
    HIGH = 1
    CRITICAL = 0


class TaskState(Enum):
    """Task execution states."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


@dataclass
class TaskResult:
    """Result of task execution."""
    task_id: str
    state: TaskState
    result: Any = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    
    @property
    def duration(self) -> Optional[float]:
        """Duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    def __repr__(self) -> str:
        return f"TaskResult({self.task_id}, {self.state.value})"


@dataclass
class Task:
    """Represents a task in the execution queue."""
    task_id: str
    coro: Coroutine
    priority: TaskPriority = TaskPriority.NORMAL
    created_at: datetime = field(default_factory=datetime.utcnow)
    timeout: Optional[float] = None
    max_retries: int = 0
    result: Optional[TaskResult] = None
    
    def __lt__(self, other: "Task") -> bool:
        """
        Comparison for priority queue.
        Lower priority value = higher priority.
        """
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        return self.created_at < other.created_at


class ExecutionEngine:
    """
    Async execution engine for running tasks concurrently.
    
    Features:
    - Priority-based task queue
    - Concurrency limiting via semaphore
    - Automatic retries with backoff
    - Timeout enforcement
    - Result tracking
    """
    
    def __init__(self, max_concurrent: int = 10, timeout: float = 300.0):
        """
        Initialize execution engine.
        
        Args:
            max_concurrent: Maximum concurrent tasks
            timeout: Default timeout for tasks (seconds)
        """
        self.max_concurrent = max_concurrent
        self.default_timeout = timeout
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._queue: asyncio.PriorityQueue[Task] = asyncio.PriorityQueue()
        self._results: Dict[str, TaskResult] = {}
        self._running = False
        self._executor_task: Optional[asyncio.Task] = None
        self._active_tasks: Dict[str, asyncio.Task] = {}
    
    async def submit(
        self,
        coro: Coroutine,
        priority: TaskPriority = TaskPriority.NORMAL,
        timeout: Optional[float] = None,
        max_retries: int = 0,
    ) -> str:
        """
        Submit a task for execution.

        Args:
            coro: Coroutine to execute
            priority: Task priority
            timeout: Task timeout (None = use default)
            max_retries: Number of retries on failure

        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())
        task = Task(
            task_id=task_id,
            coro=coro,
            priority=priority,
            timeout=timeout or self.default_timeout,
            max_retries=max_retries,
        )

        result = TaskResult(task_id=task_id, state=TaskState.PENDING)
        self._results[task_id] = result

        # Use priority.value directly: CRITICAL=0 < HIGH=1 < NORMAL=2 < LOW=3
        # put_nowait avoids yielding so callers can queue multiple tasks before
        # the executor loop picks any up (important for correct priority ordering).
        self._queue.put_nowait((priority.value, task))

        return task_id

    async def initialize(self, max_concurrent: int = None, default_timeout: float = None) -> None:
        """Initialize / reconfigure the execution engine."""
        if max_concurrent is not None:
            self.max_concurrent = max_concurrent
            self._semaphore = asyncio.Semaphore(max_concurrent)
        if default_timeout is not None:
            self.default_timeout = default_timeout
        await logger.ainfo("executor_initialized", max_concurrent=self.max_concurrent)

    async def start(self) -> None:
        """Start the executor loop."""
        if self._running:
            return
        
        self._running = True
        self._executor_task = asyncio.create_task(self._executor_loop())
        await logger.ainfo("executor_started", max_concurrent=self.max_concurrent)
    
    async def stop(self) -> None:
        """Stop the executor loop and wait for pending tasks."""
        self._running = False
        
        if self._executor_task:
            await self._executor_task
        
        # Cancel all active tasks
        for task in self._active_tasks.values():
            if not task.done():
                task.cancel()
        
        await logger.ainfo("executor_stopped")
    
    async def _executor_loop(self) -> None:
        """Main executor loop.

        Acquires a concurrency slot FIRST, then dequeues the highest-priority
        pending task.  This preserves priority ordering: when a slot opens up
        we always pick the most important queued task.
        """
        while self._running:
            # 1. Wait for a concurrency slot to be available.
            try:
                await asyncio.wait_for(self._semaphore.acquire(), timeout=0.1)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            # 2. Wait for a task in the priority queue.
            try:
                try:
                    _, task = await asyncio.wait_for(self._queue.get(), timeout=0.1)
                except asyncio.TimeoutError:
                    # No task available - release the slot and retry.
                    self._semaphore.release()
                    continue
            except asyncio.CancelledError:
                self._semaphore.release()
                break

            # 3. Run the task; the slot is already held and will be released
            #    inside _execute_task_with_slot.
            exec_task = asyncio.create_task(self._execute_task_with_slot(task))
            self._active_tasks[task.task_id] = exec_task

    async def _execute_task_with_slot(self, task: "Task") -> None:
        """Execute a task that has already acquired a semaphore slot."""
        result = self._results[task.task_id]
        result.state = TaskState.RUNNING
        result.started_at = datetime.utcnow()

        retry_count = 0
        try:
            while retry_count <= task.max_retries:
                if retry_count > 0:
                    result.state = TaskState.RETRYING
                    await asyncio.sleep(min(2 ** retry_count, 60))

                try:
                    result.result = await asyncio.wait_for(task.coro, timeout=task.timeout)
                    result.state = TaskState.COMPLETED
                    result.completed_at = datetime.utcnow()
                    await logger.ainfo("task_completed", task_id=task.task_id)
                    return
                except asyncio.TimeoutError:
                    result.error = f"Timeout after {task.timeout}s"
                    retry_count += 1
                    if retry_count > task.max_retries:
                        result.state = TaskState.FAILED
                        result.completed_at = datetime.utcnow()
                        return
                except asyncio.CancelledError:
                    result.state = TaskState.CANCELLED
                    result.completed_at = datetime.utcnow()
                    return
                except Exception as e:
                    result.error = str(e)
                    retry_count += 1
                    if retry_count > task.max_retries:
                        result.state = TaskState.FAILED
                        result.completed_at = datetime.utcnow()
                        await logger.aerror("task_failed", task_id=task.task_id, error=str(e))
                        return
        finally:
            self._semaphore.release()

    async def _execute_task(self, task: Task) -> None:
        """Execute a single task with retries and timeout."""
        result = self._results[task.task_id]
        retry_count = 0
        
        while retry_count <= task.max_retries:
            async with self._semaphore:
                result.state = TaskState.RUNNING
                result.started_at = datetime.utcnow()
                
                try:
                    if retry_count > 0:
                        result.state = TaskState.RETRYING
                        await logger.ainfo("task_retrying", task_id=task.task_id, attempt=retry_count + 1)
                        # Exponential backoff
                        await asyncio.sleep(min(2 ** retry_count, 60))
                    
                    # Execute with timeout
                    result.result = await asyncio.wait_for(task.coro, timeout=task.timeout)
                    result.state = TaskState.COMPLETED
                    result.completed_at = datetime.utcnow()
                    
                    await logger.ainfo("task_completed", task_id=task.task_id, duration=result.duration)
                    break
                    
                except asyncio.TimeoutError:
                    result.error = f"Timeout after {task.timeout}s"
                    retry_count += 1
                    
                    if retry_count > task.max_retries:
                        result.state = TaskState.FAILED
                        result.completed_at = datetime.utcnow()
                        result.retry_count = retry_count
                        await logger.aerror("task_failed_timeout", task_id=task.task_id)
                
                except asyncio.CancelledError:
                    result.state = TaskState.CANCELLED
                    result.completed_at = datetime.utcnow()
                    await logger.ainfo("task_cancelled", task_id=task.task_id)
                    break
                
                except Exception as e:
                    result.error = str(e)
                    retry_count += 1
                    
                    if retry_count > task.max_retries:
                        result.state = TaskState.FAILED
                        result.completed_at = datetime.utcnow()
                        result.retry_count = retry_count
                        await logger.aerror("task_failed_error", task_id=task.task_id, error=str(e))
        
        # Remove from active tasks
        self._active_tasks.pop(task.task_id, None)
    
    async def get_result(self, task_id: str) -> Optional[TaskResult]:
        """Get task result by ID."""
        return self._results.get(task_id)
    
    async def get_results(self, state: Optional[TaskState] = None) -> List[TaskResult]:
        """
        Get all results, optionally filtered by state.
        
        Args:
            state: Filter by task state (None = all)
            
        Returns:
            List of TaskResult objects
        """
        results = list(self._results.values())
        if state:
            results = [r for r in results if r.state == state]
        return results
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get execution engine metrics."""
        results = list(self._results.values())
        completed = [r for r in results if r.state == TaskState.COMPLETED]
        failed = [r for r in results if r.state == TaskState.FAILED]
        
        avg_duration = None
        if completed:
            durations = [r.duration for r in completed if r.duration]
            if durations:
                avg_duration = sum(durations) / len(durations)
        
        return {
            "total_tasks": len(results),
            "completed": len(completed),
            "failed": len(failed),
            "running": len([r for r in results if r.state == TaskState.RUNNING]),
            "pending": len([r for r in results if r.state == TaskState.PENDING]),
            "avg_duration": avg_duration,
            "active_tasks": len(self._active_tasks),
        }
