"""
BrainAgent - The "Brain" (MM - Mechanical Module) of the entity.

Responsible for executing tasks, generating code, and responding to users.
Runs on a 1-second async loop.
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Callable, Optional
from dataclasses import dataclass, field

from living_entity.agents.abstract import AbstractAgent, AgentConfig
from living_entity.agents.spirit import SpiritCommand
from living_entity.execution.executor import FunctionExecutor, ExecutionResult
from living_entity.execution.focus import FocusModule, TaskPriority
from living_entity.memory.context_reducer import ContextReducer
from living_entity.prompts.brain_prompts import (
    BRAIN_SYSTEM_PROMPT,
    BRAIN_CODE_PROMPT,
    BRAIN_CONTINUATION_PROMPT,
)
from living_entity.utils.logging import get_logger


@dataclass
class BrainAction:
    """An action taken by the Brain."""
    type: str  # "code", "response", "file_operation"
    content: str
    result: Optional[ExecutionResult] = None
    timestamp: datetime = field(default_factory=datetime.now)
    success: bool = True
    error: Optional[str] = None


class BrainAgent(AbstractAgent):
    """
    The Brain Agent (MM - Mechanical Module).
    
    Responsibilities:
    - Executing tasks from Spirit
    - Generating and running Python code
    - Responding to users
    - File operations
    
    Runs on a 1-second async loop.
    """
    
    LOOP_INTERVAL = 1.0  # seconds
    
    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        model: str = "gpt-3.5-turbo",
        config: Optional[AgentConfig] = None,
        executor: Optional[FunctionExecutor] = None,
        focus: Optional[FocusModule] = None,
        client_kwargs: Optional[dict] = None,
        memory=None,
        tools=None,
    ):
        """
        Initialize the Brain Agent.
        
        :param api_key: API key for LLM provider
        :param base_url: Base URL for API
        :param model: Model name
        :param config: Agent configuration
        :param executor: Code executor
        :param focus: Focus module for complex tasks
        :param client_kwargs: Additional client kwargs
        :param memory: Shared memory matrix for context
        :param tools: ToolRegistry for available tools
        """
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            model=model,
            config=config,
            client_kwargs=client_kwargs,
        )
        
        # Tool Registry
        self._tools = tools
        
        # Build system prompt with tool descriptions
        system_prompt = BRAIN_SYSTEM_PROMPT
        if tools:
            tool_descriptions = tools.get_tools_description()
            system_prompt = system_prompt.replace(
                "## Доступные функции для кода:",
                f"## Доступные инструменты:\n{tool_descriptions}\n\n## Как вызывать инструменты:"
            )
        self.set_system_prompt(system_prompt)
        
        # Executor
        self.executor = executor or FunctionExecutor()
        
        # Focus module
        self.focus = focus or FocusModule()
        
        # Memory
        self._memory = memory
        
        # Context reducer
        self._context_reducer: Optional[ContextReducer] = None
        
        # Command queue (populated by Spirit)
        self._command_queue: Optional[asyncio.Queue[SpiritCommand]] = None
        
        # Action history
        self._action_history: list[BrainAction] = []
        self._max_history = 50
        
        # Running state
        self._running = False
        self._loop_task: Optional[asyncio.Task] = None
        
        # Current task context
        self._current_task: Optional[SpiritCommand] = None
        self._task_context: str = ""
        
        # Callbacks
        self._on_action: Optional[Callable[[BrainAction], None]] = None
        self._on_output: Optional[Callable[[str], None]] = None
    
    def set_command_queue(self, queue: asyncio.Queue[SpiritCommand]) -> None:
        """Set the command queue from Spirit."""
        self._command_queue = queue
    
    def set_context_reducer(self, reducer: ContextReducer) -> None:
        """Set the context reducer."""
        self._context_reducer = reducer
    
    def set_output_callback(self, callback: Callable[[str], None]) -> None:
        """Set the output callback for say_to_user."""
        self._on_output = callback
        self.executor.set_output_callback(callback)
    
    def on_action(self, callback: Callable[[BrainAction], None]) -> None:
        """Register callback for actions."""
        self._on_action = callback
    
    async def process(self) -> None:
        """
        Main processing cycle.
        
        1. Check for pending tasks from Spirit
        2. Continue or start task execution
        3. Process results
        """
        # Get next command if not working on one
        if self._current_task is None and self._command_queue:
            try:
                self._current_task = self._command_queue.get_nowait()
                self._task_context = ""
                self.logger.action(f"New task: {self._current_task.content[:50]}...")
            except asyncio.QueueEmpty:
                pass
        
        if self._current_task is None:
            return
        
        # Process the current task
        await self._process_task()
    
    async def _process_task(self) -> None:
        """Process the current task."""
        task = self._current_task
        if not task:
            return
        
        # Check if this is a focus task
        if task.type == "focus":
            await self._handle_focus_task(task)
            return
        
        # Check if this is a direct response from Spirit (type="do")
        # These should be sent directly without LLM modification
        if task.type == "do":
            self.logger.action(f"Direct response: {task.content[:50]}...")
            
            # Send the response directly
            if self._on_output:
                self._on_output(task.content)
            
            # Record action
            action = BrainAction(
                type="response",
                content=task.content,
                result=ExecutionResult(success=True, task_ended=True, user_messages=[task.content]),
                success=True,
            )
            self._record_action(action)
            
            # Task complete
            self._current_task = None
            return
        
        # For other task types, use LLM
        # Retrieve relevant memories if memory is available
        memories_context = ""
        if hasattr(self, '_memory') and self._memory:
            memories = self._memory.auto_associative_search(
                task.content,
                max_results=5,
            )
            if memories:
                memories_list = [f"- {m.entry.text}" for m in memories]
                memories_context = "\n".join(memories_list)
                self.logger.info(f"[ММ] Найденные воспоминания:\n{memories_context}", module="brain")
        
        # Regular delegation
        prompt = BRAIN_CODE_PROMPT.format(
            task=task.content,
            priority=task.priority,
            context=self._task_context if self._task_context else (memories_context if memories_context else "Нет предыдущего контекста"),
        )
        
        # Reduce context if needed
        if self._context_reducer:
            history = self.get_history()
            if self._context_reducer.needs_reduction(history):
                reduced = await self._context_reducer.reduce(history)
                self.set_history(reduced)
        
        # Get response from LLM
        try:
            response = await self.think(prompt, include_history=True, json_mode=True)
        except Exception as e:
            self.logger.error(f"Brain thinking failed: {e}", module="brain")
            self._current_task = None
            return
        
        # Parse response
        parsed = self.parse_json_response(response)
        if not parsed:
            self.logger.warning("Failed to parse Brain response", module="brain")
            self._current_task = None
            return
        
        # Execute action
        action = await self._execute_action(parsed)
        
        # Record action
        self._record_action(action)
        
        # Check if task is complete
        if action.result and action.result.task_ended:
            self.logger.action(f"Task completed: {task.content[:50]}...")
            self._current_task = None
            self._task_context = ""
        elif not action.success:
            # Retry or abort on failure
            await self._handle_failure(action)
    
    async def _execute_action(self, parsed: dict[str, Any]) -> BrainAction:
        """Execute an action from parsed response."""
        action_type = parsed.get("action_type", "response")
        reasoning = parsed.get("reasoning", "")
        
        self.logger.action(f"Action: {action_type} - {reasoning}")
        
        action = BrainAction(type=action_type, content="")
        
        try:
            if action_type == "tool_call":
                tool_calls = parsed.get("tool_calls", [])
                action.content = f"Tool calls: {len(tool_calls)}"
                
                all_messages = []
                all_results = []
                
                for tc in tool_calls:
                    tool_name = tc.get("tool", "")
                    tool_args = tc.get("args", {})
                    
                    self.logger.action(f"Calling tool: {tool_name} with {tool_args}")
                    
                    # Execute via ToolRegistry if available
                    if self._tools and tool_name:
                        result = self._tools.execute(tool_name, **tool_args)
                        all_results.append(result)
                        
                        if result.success:
                            self.logger.action(f"Tool {tool_name} succeeded: {result.output}")
                            # Collect user messages
                            if tool_name == "say_to_user" and "text" in tool_args:
                                all_messages.append(tool_args["text"])
                        else:
                            self.logger.error(f"Tool {tool_name} failed: {result.error}", module="brain")
                            action.error = result.error
                    else:
                        self.logger.warning(f"Tool {tool_name} not found or tools not available", module="brain")
                
                # Send all messages to user
                for msg in all_messages:
                    if self._on_output:
                        self._on_output(msg)
                
                action.success = all(r.success for r in all_results) if all_results else True
                action.result = ExecutionResult(
                    success=action.success,
                    task_ended=True,
                    user_messages=all_messages,
                    output=str([r.output for r in all_results]),
                )
                
            elif action_type == "response":
                response_text = parsed.get("response", "")
                action.content = response_text
                
                if response_text and self._on_output:
                    self._on_output(response_text)
                
                # Mark task as complete after response
                action.result = ExecutionResult(
                    success=True,
                    task_ended=True,
                    user_messages=[response_text] if response_text else [],
                )
            
            # Legacy support for code execution
            elif action_type == "code":
                code = parsed.get("code", "")
                action.content = code
                
                if code:
                    result = await self.executor.execute_async(code)
                    action.result = result
                    action.success = result.success
                    
                    if not result.success:
                        action.error = result.error
                    else:
                        for msg in result.user_messages:
                            if self._on_output:
                                self._on_output(msg)
            
            else:
                action.success = False
                action.error = f"Unknown action type: {action_type}"
                
        except Exception as e:
            action.success = False
            action.error = str(e)
            self.logger.error(f"Action execution error: {e}", module="brain")
        
        return action
    
    async def _handle_focus_task(self, task: SpiritCommand) -> None:
        """Handle a complex focus task."""
        # Create focus task
        task_id = f"focus_{datetime.now().timestamp()}"
        
        priority = {
            "high": TaskPriority.HIGH,
            "medium": TaskPriority.MEDIUM,
            "low": TaskPriority.LOW,
        }.get(task.priority, TaskPriority.MEDIUM)
        
        focus_task = self.focus.create_task(
            task_id=task_id,
            title=task.content[:50],
            description=task.content,
            priority=priority,
        )
        
        # Ask LLM to decompose the task
        decomposition_prompt = f"""Разбей следующую сложную задачу на простые шаги:

Задача: {task.content}

Ответь в формате JSON:
{{
    "steps": [
        {{"id": "step_1", "description": "Описание шага 1"}},
        {{"id": "step_2", "description": "Описание шага 2"}}
    ]
}}
"""
        
        try:
            response = await self.think(decomposition_prompt, include_history=False, json_mode=True)
            parsed = self.parse_json_response(response)
            
            if parsed and "steps" in parsed:
                self.focus.decompose_task(task_id, parsed["steps"])
                await self.focus.start_task(task_id)
                
                self.logger.action(f"Focus task created with {len(parsed['steps'])} steps")
            else:
                self.logger.warning("Failed to decompose focus task", module="brain")
                
        except Exception as e:
            self.logger.error(f"Focus task creation failed: {e}", module="brain")
        
        # Clear current task (focus module handles it now)
        self._current_task = None
    
    async def _handle_failure(self, action: BrainAction) -> None:
        """Handle action failure."""
        # Try to recover or report
        continuation_prompt = BRAIN_CONTINUATION_PROMPT.format(
            previous_action=action.content,
            execution_result=f"ОШИБКА: {action.error}",
        )
        
        try:
            response = await self.think(continuation_prompt, include_history=True, json_mode=True)
            parsed = self.parse_json_response(response)
            
            if parsed:
                # Execute recovery action
                recovery_action = await self._execute_action(parsed)
                self._record_action(recovery_action)
                
                if not recovery_action.success:
                    # Give up after second failure
                    self.logger.error("Task failed after retry", module="brain")
                    self._current_task = None
                    
        except Exception as e:
            self.logger.error(f"Recovery failed: {e}", module="brain")
            self._current_task = None
    
    def _record_action(self, action: BrainAction) -> None:
        """Record an action to history."""
        self._action_history.append(action)
        
        # Trim history
        if len(self._action_history) > self._max_history:
            self._action_history = self._action_history[-self._max_history:]
        
        # Call callback
        if self._on_action:
            self._on_action(action)
    
    async def run_loop(self, interval: Optional[float] = None) -> None:
        """
        Run the Brain's main loop.
        
        :param interval: Loop interval in seconds (default: 1.0)
        """
        self._running = True
        loop_interval = interval or self.LOOP_INTERVAL
        
        self.logger.info(
            f"Brain loop started (interval: {loop_interval}s)",
            module="brain"
        )
        
        while self._running:
            try:
                await self.process()
            except Exception as e:
                self.logger.error(f"Brain loop error: {e}", module="brain")
            
            await asyncio.sleep(loop_interval)
        
        self.logger.info("Brain loop stopped", module="brain")
    
    def start(self) -> asyncio.Task:
        """Start the Brain loop as a background task."""
        if self._loop_task and not self._loop_task.done():
            return self._loop_task
        
        self._loop_task = asyncio.create_task(self.run_loop())
        return self._loop_task
    
    def stop(self) -> None:
        """Stop the Brain loop."""
        self._running = False
        if self._loop_task:
            self._loop_task.cancel()
    
    def is_running(self) -> bool:
        """Check if the Brain is running."""
        return self._running
    
    def get_action_history(self) -> list[BrainAction]:
        """Get the action history."""
        return self._action_history.copy()
    
    def get_current_task(self) -> Optional[SpiritCommand]:
        """Get the current task being processed."""
        return self._current_task
    
    def clear_history(self) -> None:
        """Clear action history."""
        self._action_history.clear()
        super().clear_history()
