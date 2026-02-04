"""
BrainAgent - The "Brain" (MM - Mechanical Module) of the entity.

Responsible for executing tasks based on Spirit's thoughts, generating code, and responding to users.
Runs event-driven when new thoughts from Spirit are available.
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Callable, Optional
from dataclasses import dataclass, field

from living_entity.agents.abstract import AbstractAgent, AgentConfig
from living_entity.agents.spirit import SpiritThought
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
    task_completed: bool = False  # Track if this action completed a task with chat response


class BrainAgent(AbstractAgent):
    """
    The Brain Agent (MM - Mechanical Module).
    
    Responsibilities:
    - Reading Spirit's narrative thoughts
    - Executing actions based on Spirit's guidance
    - Generating and running code
    - Responding to users
    - File operations
    
    Runs event-driven when new thoughts arrive from Spirit.
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
                "## Available tools (injected):",
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
        self._thought_stream: Optional[asyncio.Queue[SpiritThought]] = None
        
        # Action history
        self._action_history: list[BrainAction] = []
        self._max_history = 50
        
        # Running state
        self._running = False
        self._loop_task: Optional[asyncio.Task] = None
        
        # Current task context
        self._current_task: Optional[SpiritThought] = None
        self._current_thought: Optional[SpiritThought] = None
        self._task_context: str = ""
        
        # Event task for run_event_loop
        self._event_task: Optional[asyncio.Task] = None
        
        # Callbacks
        self._on_action: Optional[Callable[[BrainAction], None]] = None
        self._on_output: Optional[Callable[[str], None]] = None
    
    def set_thought_stream(self, stream: asyncio.Queue[SpiritThought]) -> None:
        """Set the thought stream from Spirit."""
        self._thought_stream = stream
    
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
        if self._current_task is None and self._current_thought:
            self._current_task = self._current_thought
            self._task_context = ""
            self.logger.action(f"New task: {self._current_task.guidance[:50]}...")
            self._current_thought = None  # Clear it
        
        if self._current_task is None:
            return
        
        # Process the current task
        await self._process_task()
    
    async def _process_task(self) -> None:
        """Process the current task."""
        task = self._current_task
        if not task:
            return
        
        # Spirit's guidance is what we need to execute
        guidance = task.guidance
        if not guidance:
            self.logger.warning("Empty guidance from Spirit, skipping task", module="brain")
            self._current_task = None
            return
        
        self.logger.action(f"Processing Spirit's guidance: {guidance[:50]}...")
        
        # Retrieve relevant memories if memory is available
        memories_context = ""
        if hasattr(self, '_memory') and self._memory:
            memories = self._memory.auto_associative_search(
                guidance,
                max_results=5,
            )
            if memories:
                memories_list = [f"- {m.entry.text}" for m in memories]
                memories_context = "\n".join(memories_list)
                self.logger.info(f"[ММ] Найденные воспоминания:\n{memories_context}", module="brain")
        
        # Use LLM to understand and execute the guidance
        prompt = BRAIN_CODE_PROMPT.format(
            task=guidance,
            priority="medium",  # Default priority
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
            self.logger.warning("Failed to parse Brain response, attempting correction", module="brain")
            
            # Try to correct the malformed response
            correction_prompt = f"""Your previous response contained invalid JSON. Here is the malformed response:

{response}

Please provide a corrected, valid JSON response for the same task.

Task: {guidance}

Respond with valid JSON only, following the required format."""
            
            try:
                corrected_response = await self.think(correction_prompt, include_history=False, json_mode=True)
                parsed = self.parse_json_response(corrected_response)
                if not parsed:
                    self.logger.error("Failed to parse corrected Brain response", module="brain")
                    self._current_task = None
                    return
                self.logger.info("Successfully corrected malformed JSON response", module="brain")
            except Exception as e:
                self.logger.error(f"Brain correction failed: {e}", module="brain")
                self._current_task = None
                return
        
        # Execute action
        action = await self._execute_action(parsed)
        
        # Record action
        self._record_action(action)
        
        # Check if task is complete
        if action.result and action.result.task_ended:
            self.logger.action(f"Task completed: {guidance[:50]}...")
            self._current_task = None
            self._task_context = ""
        elif action.result and not action.result.task_ended:
            # Continuation needed
            await self._handle_continuation(action)
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
                    
                    # Replace placeholders in args
                    if isinstance(tool_args, dict):
                        for key, value in tool_args.items():
                            if isinstance(value, str) and "{{result}}" in value:
                                # Replace with last result
                                if all_results:
                                    last_result = all_results[-1]
                                    if hasattr(last_result, 'output'):
                                        tool_args[key] = value.replace("{{result}}", str(last_result.output))
                                    else:
                                        tool_args[key] = value.replace("{{result}}", str(last_result))
                    
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
                    task_ended=len(all_messages) > 0,  # Task ended only if we sent messages to user
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
    
    async def _handle_focus_task(self, task: SpiritThought) -> None:
        """Handle a complex focus task."""
        # Create focus task
        task_id = f"focus_{datetime.now().timestamp()}"
        
        priority = TaskPriority.MEDIUM  # Default priority for focus tasks
        
        focus_task = self.focus.create_task(
            task_id=task_id,
            title=task.guidance[:50],
            description=task.guidance,
            priority=priority,
        )
        
        # Ask LLM to decompose the task
        decomposition_prompt = f"""Разбей следующую сложную задачу на простые шаги:

Задача: {task.guidance}

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
    
    async def _handle_continuation(self, action: BrainAction) -> None:
        """Handle task continuation after partial execution."""
        continuation_prompt = BRAIN_CONTINUATION_PROMPT.format(
            previous_action=action.content,
            execution_result=action.result.output if action.result else "No result",
        )
        
        # Update task context
        self._task_context += f"\nPrevious action: {action.content}\nResult: {action.result.output if action.result else 'Failed'}"
        
        # Get continuation from LLM
        response = await self.think(continuation_prompt, include_history=False, json_mode=True)
        parsed = self.parse_json_response(response)
        if not parsed:
            self.logger.warning("Failed to parse continuation response", module="brain")
            return
        
        # Execute continuation
        continuation_action = await self._execute_action(parsed)
        self._record_action(continuation_action)
        
        # Check again
        if continuation_action.result and continuation_action.result.task_ended:
            self.logger.action(f"Task completed after continuation: {self._current_task.guidance[:50] if self._current_task else 'Unknown'}...")
            self._current_task = None
            self._task_context = ""
        elif not continuation_action.success:
            await self._handle_failure(continuation_action)
    
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
    
    async def run_event_loop(self) -> None:
        """
        Run the Brain's event-driven loop.
        
        Waits for thoughts from Spirit and processes them.
        """
        self._running = True
        
        self.logger.info("Brain event loop started", module="brain")
        
        while self._running:
            try:
                # Wait for next thought from Spirit
                thought = await self._thought_stream.get()
                self._current_thought = thought
                await self.process()
                
            except Exception as e:
                self.logger.error(f"Brain event loop error: {e}", module="brain")
                await asyncio.sleep(1)  # Brief pause on error
        
        self.logger.info("Brain event loop stopped", module="brain")
    
    def start(self) -> asyncio.Task:
        """Start the Brain event loop as a background task."""
        if self._event_task and not self._event_task.done():
            return self._event_task
        
        self._event_task = asyncio.create_task(self.run_event_loop())
        return self._event_task
    
    def stop(self) -> None:
        """Stop the Brain event loop."""
        self._running = False
        if self._loop_task:
            self._loop_task.cancel()
    
    def is_running(self) -> bool:
        """Check if the Brain is running."""
        return self._running
    
    def get_action_history(self) -> list[BrainAction]:
        """Get the action history."""
        return self._action_history.copy()
    
    def get_current_thought(self) -> Optional[SpiritThought]:
        """Get the current thought being processed."""
        return self._current_thought
    
    def clear_history(self) -> None:
        """Clear action history."""
        self._action_history.clear()
        super().clear_history()
    
    async def run_loop(self, interval: Optional[float] = None) -> None:
        """
        Run the event-driven Brain loop.
        
        Waits for Spirit thoughts and processes them when available.
        """
        self.logger.info(f"Starting Brain event loop", module="brain")
        
        try:
            while True:
                # Wait for new thought from Spirit
                if self._thought_stream:
                    try:
                        thought = await asyncio.wait_for(
                            self._thought_stream.get(), 
                            timeout=interval
                        )
                        self._current_thought = thought
                        await self.process()
                    except asyncio.TimeoutError:
                        # No thought received, continue waiting
                        pass
                else:
                    # No thought stream set, wait
                    await asyncio.sleep(interval)
                    
        except asyncio.CancelledError:
            self.logger.info("Brain loop cancelled", module="brain")
        except Exception as e:
            self.logger.error(f"Brain loop error: {e}", module="brain")
