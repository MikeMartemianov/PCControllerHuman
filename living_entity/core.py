"""
LivingCore - Main orchestrator for the LivingEntity system.

Coordinates Spirit (DM) and Brain (MM) agents with shared memory and execution.
"""

import asyncio
from typing import Any, Callable, Optional

from pydantic import BaseModel, Field

from living_entity.agents.abstract import AgentConfig
from living_entity.agents.spirit import SpiritAgent, Signal
from living_entity.agents.brain import BrainAgent
from living_entity.memory.matrix import MemoryMatrix
from living_entity.memory.context_reducer import ContextReducer
from living_entity.execution.executor import FunctionExecutor
from living_entity.execution.focus import FocusModule
from living_entity.execution.tools import ToolRegistry
from living_entity.utils.logging import get_logger, EntityLogger, LogLevel


class SystemParams(BaseModel):
    """System parameters for LivingCore."""
    dm_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    mm_temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1024, ge=1)
    dm_interval: float = Field(default=3.0, ge=0.5)
    mm_interval: float = Field(default=1.0, ge=0.1)
    context_compression_threshold: float = Field(default=0.8, ge=0.5, le=1.0)
    max_context_tokens: Optional[int] = None
    sandbox_path: str = "./sandbox"
    unsafe_mode: bool = False
    log_level: str = "INFO"


class LivingCore:
    """
    Main orchestrator for the LivingEntity autonomous AI system.
    
    Coordinates:
    - Spirit Agent (DM) - High-level thinking, 3s cycle
    - Brain Agent (MM) - Execution, 1s cycle
    - Memory Matrix - Vector memory with RAG
    - Function Executor - Sandboxed code execution
    - Focus Module - Complex task handling
    
    Example:
        ```python
        entity = LivingCore(
            api_key="your-api-key",
            base_url="https://api.cerebras.ai/v1",
            model="llama3-70b-8192",
        )
        
        @entity.on_output
        def handle(text):
            print(text)
        
        await entity.start()
        await entity.input_signal("Hello!")
        await asyncio.sleep(10)
        await entity.stop()
        ```
    """
    
    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        model: str = "llama3-70b-8192",
        system_params: Optional[dict] = None,
        memory_path: str = "./memory_db",
        client_kwargs: Optional[dict] = None,
        personality_text: Optional[str] = None,
    ):
        """
        Initialize the LivingCore orchestrator.
        
        :param api_key: API key for the LLM provider (Cerebras, OpenAI, Groq, etc.)
        :param base_url: Base URL for the API. If None, uses OpenAI default.
                        Examples:
                        - Cerebras: "https://api.cerebras.ai/v1"
                        - Groq: "https://api.groq.com/openai/v1"
                        - DeepSeek: "https://api.deepseek.com/v1"
        :param model: Model name (e.g., "llama3-70b-8192", "gpt-4")
        :param system_params: System configuration dict
        :param memory_path: Path for persistent vector memory storage
        :param client_kwargs: Additional kwargs for the OpenAI client (timeout, etc.)
        :param personality_text: Initial personality/context text. The AI will process this
                                 into system memories and use it as personality context.
        """
        # Parse system params
        params_dict = system_params or {}
        self.params = SystemParams(**params_dict)
        
        # Store config
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.memory_path = memory_path
        self.client_kwargs = client_kwargs or {}
        self.personality_text = personality_text
        
        # Personality addition to system prompts
        self._personality_prompt_addition: str = ""
        
        # Initialize logger
        self.logger = get_logger("LivingCore")
        log_level = getattr(LogLevel, self.params.log_level.upper(), LogLevel.INFO)
        self.logger.set_level(log_level)
        
        # Output callbacks
        self._output_callbacks: list[Callable[[str], None]] = []
        
        # Initialize components
        self._init_components()
        
        # Process personality text if provided
        if personality_text:
            self._process_personality(personality_text)
        
        # Running state
        self._running = False
        self._spirit_task: Optional[asyncio.Task] = None
        self._brain_task: Optional[asyncio.Task] = None
        
        self.logger.info(f"LivingCore initialized with model: {model}", module="core")
        if base_url:
            self.logger.info(f"Using provider: {base_url}", module="core")
    
    def _process_personality(self, text: str) -> None:
        """
        Process personality text into memories and prompt additions.
        
        :param text: Personality/context text
        """
        self.logger.info("Processing personality data...", module="core")
        
        # Create personality addition for system prompts
        self._personality_prompt_addition = f"""

## Моя личность и контекст:
{text}
"""
        
        # Update Spirit system prompt
        current_spirit_prompt = self.spirit._system_prompt
        self.spirit.set_system_prompt(current_spirit_prompt + self._personality_prompt_addition)
        
        # Update Brain system prompt  
        current_brain_prompt = self.brain._system_prompt
        self.brain.set_system_prompt(current_brain_prompt + self._personality_prompt_addition)
        
        # Split personality text into pieces and save as foundational memories
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        for line in lines:
            # Skip very short lines
            if len(line) < 10:
                continue
            
            # Save as foundational memory with high importance
            self.memory.save_memory(
                text=line,
                source="personality",
                importance=0.9,
                metadata={"type": "foundational", "origin": "personality_init"}
            )
        
        self.logger.info(f"Personality processed: {len(lines)} foundational memories created", module="core")
    
    def set_personality(self, text: str) -> None:
        """
        Set or update personality at runtime.
        
        :param text: New personality/context text
        """
        self.personality_text = text
        self._process_personality(text)
    
    def _init_components(self) -> None:
        """Initialize all internal components."""
        # Memory Matrix
        self.memory = MemoryMatrix(persist_path=self.memory_path)
        
        # Tool Registry (replaces sandbox for tool execution)
        self.tools = ToolRegistry(output_callback=self._handle_output)
        
        # Function Executor (legacy, for code execution)
        self.executor = FunctionExecutor(
            sandbox_path=self.params.sandbox_path,
            output_callback=self._handle_output,
            unsafe_mode=self.params.unsafe_mode,
        )
        
        # Focus Module
        self.focus = FocusModule()
        
        # Spirit Agent (DM)
        spirit_config = AgentConfig(
            temperature=self.params.dm_temperature,
            max_tokens=self.params.max_tokens,
        )
        self.spirit = SpiritAgent(
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model,
            config=spirit_config,
            memory=self.memory,
            client_kwargs=self.client_kwargs,
        )
        
        # Brain Agent (MM)
        brain_config = AgentConfig(
            temperature=self.params.mm_temperature,
            max_tokens=self.params.max_tokens,
        )
        self.brain = BrainAgent(
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model,
            config=brain_config,
            executor=self.executor,
            focus=self.focus,
            client_kwargs=self.client_kwargs,
            memory=self.memory,  # Pass shared memory
            tools=self.tools,    # Pass ToolRegistry
        )
        
        # Connect Spirit command queue to Brain
        self.brain.set_command_queue(self.spirit.get_command_queue())
        
        # Set output callback on Brain
        self.brain.set_output_callback(self._handle_output)
        
        # Connect Brain actions to Spirit for visibility
        # DM sees MM's actions (tools, results) but not thoughts
        self.brain.on_action(self._handle_brain_action)
        
        # Context reducers (will be initialized with client from agents)
        self._init_context_reducers()
    
    def _init_context_reducers(self) -> None:
        """Initialize context reducers for both agents."""
        from openai import AsyncOpenAI
        
        # Create shared client for compression
        client_params = {"api_key": self.api_key}
        if self.base_url:
            client_params["base_url"] = self.base_url
        client_params.update(self.client_kwargs)
        
        client = AsyncOpenAI(**client_params)
        
        # Spirit reducer
        spirit_reducer = ContextReducer(
            client=client,
            model=self.model,
            max_context_tokens=self.params.max_context_tokens,
            compression_threshold=self.params.context_compression_threshold,
        )
        self.spirit.set_context_reducer(spirit_reducer)
        
        # Brain reducer
        brain_reducer = ContextReducer(
            client=client,
            model=self.model,
            max_context_tokens=self.params.max_context_tokens,
            compression_threshold=self.params.context_compression_threshold,
        )
        self.brain.set_context_reducer(brain_reducer)
    
    def _handle_output(self, text: str) -> None:
        """Handle output from the entity."""
        for callback in self._output_callbacks:
            try:
                callback(text)
            except Exception as e:
                self.logger.error(f"Output callback error: {e}", module="core")
    
    async def start(self) -> None:
        """
        Start the entity's life cycles.
        
        Launches async loops for Spirit (3s) and Brain (1s).
        """
        if self._running:
            self.logger.warning("Entity already running", module="core")
            return
        
        self._running = True
        
        self.logger.info("Starting LivingEntity...", module="core")
        
        # Check if memory cleanup is needed (daily)
        self.memory.check_and_cleanup()
        
        # Start Spirit loop
        self._spirit_task = asyncio.create_task(
            self.spirit.run_loop(self.params.dm_interval)
        )
        
        # Start Brain loop
        self._brain_task = asyncio.create_task(
            self.brain.run_loop(self.params.mm_interval)
        )
        
        self.logger.info(
            f"Entity started - Spirit: {self.params.dm_interval}s, Brain: {self.params.mm_interval}s",
            module="core"
        )
    
    async def stop(self) -> None:
        """
        Gracefully stop all entity processes.
        """
        if not self._running:
            return
        
        self.logger.info("Stopping LivingEntity...", module="core")
        
        self._running = False
        
        # Stop agents
        self.spirit.stop()
        self.brain.stop()
        
        # Wait for tasks to complete
        if self._spirit_task:
            try:
                await asyncio.wait_for(self._spirit_task, timeout=5.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass
        
        if self._brain_task:
            try:
                await asyncio.wait_for(self._brain_task, timeout=5.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass
        
        # Persist memory
        self.memory.persist()
        
        self.logger.info("Entity stopped", module="core")
    
    async def input_signal(self, text: str, source: str = "user") -> None:
        """
        Send an input signal to the entity.
        
        :param text: Input text
        :param source: Source identifier (default: "user")
        """
        if not self._running:
            self.logger.warning("Entity not running, signal ignored", module="core")
            return
        
        self.logger.info(f"Input signal from {source}: {text[:50]}...", module="core")
        
        await self.spirit.receive_input(text, source=source)
    
    def on_output(self, callback: Callable[[str], None]) -> Callable[[str], None]:
        """
        Register a callback for entity output.
        
        Can be used as a decorator:
        
        ```python
        @entity.on_output
        def handle(text):
            print(text)
        ```
        
        :param callback: Function to call with output text
        :return: The callback function (for decorator use)
        """
        self._output_callbacks.append(callback)
        return callback
    
    def remove_output_callback(self, callback: Callable[[str], None]) -> None:
        """Remove an output callback."""
        if callback in self._output_callbacks:
            self._output_callbacks.remove(callback)
    
    def on_thought(self, callback: Callable[[str], None]) -> Callable[[str], None]:
        """
        Register a callback for Spirit thoughts.
        
        :param callback: Function to call with thought text
        :return: The callback function
        """
        self.spirit.on_thought(callback)
        return callback
    
    def on_action(self, callback: Callable) -> Callable:
        """
        Register a callback for Brain actions.
        
        :param callback: Function to call with action
        :return: The callback function
        """
        self.brain.on_action(callback)
        return callback
    
    def is_running(self) -> bool:
        """Check if the entity is running."""
        return self._running
    
    def _handle_brain_action(self, action) -> None:
        """
        Handle Brain action and relay to Spirit for visibility.
        
        DM sees: user request context, action type, result
        DM does NOT see: Brain's internal thoughts
        """
        from living_entity.agents.spirit import Signal
        
        # Build action report for Spirit
        action_type = action.type
        content_preview = action.content[:100] if action.content else ""
        
        # Get result info
        result_info = ""
        user_context = ""
        if action.result:
            if action.result.success:
                result_info = f"Успешно"
                if action.result.output:
                    result_info += f": {str(action.result.output)[:200]}"
            else:
                result_info = f"Ошибка: {action.result.error or 'неизвестно'}"
            
            # Extract user messages for context
            if action.result.user_messages:
                user_context = f"Контекст: {'; '.join(action.result.user_messages[:2])}"
        
        # Format signal for Spirit (without Brain's thoughts)
        signal_content = f"""[Отчёт от ММ]
Действие: {action_type}
{f'Контекст пользователя: {user_context}' if user_context else ''}
Содержание: {content_preview}
Результат: {result_info}"""
        
        # Send to Spirit asynchronously
        import asyncio
        try:
            signal = Signal(
                content=signal_content,
                source="brain_action",
                priority="low",
            )
            asyncio.create_task(self.spirit.receive_signal(signal))
            self.logger.debug(f"Brain action relayed to Spirit: {action_type}", module="core")
        except Exception as e:
            self.logger.warning(f"Failed to relay brain action: {e}", module="core")
    
    def get_memory_count(self) -> int:
        """Get the number of stored memories."""
        return self.memory.count()
    
    def search_memory(self, query: str, max_results: int = 5) -> list:
        """
        Search the entity's memory.
        
        :param query: Search query
        :param max_results: Maximum results to return
        :return: List of matching memories
        """
        return self.memory.retrieve(query, max_results=max_results)
    
    def save_memory(self, text: str, source: str = "external") -> str:
        """
        Directly save something to memory.
        
        :param text: Text to remember
        :param source: Source identifier
        :return: Memory ID
        """
        return self.memory.save_memory(text, source=source)
    
    def get_spirit_context(self) -> list[str]:
        """Get the Spirit's current context."""
        return self.spirit.get_context()
    
    def get_brain_history(self) -> list:
        """Get the Brain's action history."""
        return self.brain.get_action_history()
    
    def clear_all(self) -> None:
        """Clear all context, history, and temporary data."""
        self.spirit.clear_context()
        self.spirit.clear_history()
        self.brain.clear_history()
        self.executor.clear_sandbox()
    
    def register_tool(
        self,
        func: Callable = None,
        name: Optional[str] = None,
        description: str = "",
        parameters: Optional[dict] = None,
        returns: str = "",
        category: str = "custom",
    ) -> Callable:
        """
        Register a custom tool for the AI to use.
        
        Can be used as a decorator or called directly.
        
        Example as decorator:
            ```python
            @entity.register_tool(
                description="Calculate sum of numbers",
                parameters={"a": "First number", "b": "Second number"}
            )
            def add(a: int, b: int) -> int:
                return a + b
            ```
        
        Example direct call:
            ```python
            entity.register_tool(my_function, description="Does something")
            ```
        
        :param func: Function to register (for direct call)
        :param name: Tool name (uses function name if None)
        :param description: Description for the AI
        :param parameters: Dict of {param_name: description}
        :param returns: Description of return value
        :param category: Tool category
        :return: Decorator or the function itself
        """
        if func is not None:
            # Direct call: entity.register_tool(my_func, ...)
            self.tools.add_tool(func, name, description, parameters, returns, category)
            return func
        
        # Decorator usage: @entity.register_tool(...)
        return self.tools.register(name, description, parameters, returns, category)
    
    def get_tools_description(self) -> str:
        """
        Get formatted description of all registered tools.
        
        Useful for including in AI prompts.
        
        :return: Formatted tools description
        """
        return self.tools.get_tools_description()
    
    def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """
        Execute a registered tool by name.
        
        :param tool_name: Tool name
        :param kwargs: Tool arguments
        :return: Tool result
        """
        result = self.tools.execute(tool_name, **kwargs)
        if result.success:
            return result.output
        else:
            raise RuntimeError(f"Tool '{tool_name}' failed: {result.error}")
    
    def list_tools(self) -> list[str]:
        """Get list of all registered tool names."""
        return self.tools.list_tools()
    
    def rebuild_tool_prompts(self) -> None:
        """
        Rebuild Brain's system prompt with current tool descriptions.
        
        Call this after registering new tools to ensure the AI sees them.
        """
        from living_entity.prompts.brain_prompts import BRAIN_SYSTEM_PROMPT
        
        # Build new system prompt with all tools
        tool_descriptions = self.tools.get_tools_description()
        
        new_prompt = BRAIN_SYSTEM_PROMPT.replace(
            "## Доступные функции для кода:",
            f"## Доступные инструменты:\n{tool_descriptions}\n\n## Как вызывать инструменты:"
        )
        
        # Add personality if set
        if self._personality_prompt_addition:
            new_prompt += self._personality_prompt_addition
        
        # Update Brain's system prompt
        self.brain.set_system_prompt(new_prompt)
        
        self.logger.info(f"Rebuilt Brain prompt with {len(self.tools.list_tools())} tools", module="core")
    
    async def __aenter__(self) -> "LivingCore":
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.stop()


# Convenience function for quick creation
def create_entity(
    api_key: str,
    provider: str = "openai",
    model: Optional[str] = None,
    **kwargs: Any,
) -> LivingCore:
    """
    Create a LivingCore entity with common provider presets.
    
    :param api_key: API key
    :param provider: Provider name ("openai", "cerebras", "groq", "deepseek")
    :param model: Model name (uses default for provider if None)
    :param kwargs: Additional kwargs for LivingCore
    :return: LivingCore instance
    """
    providers = {
        "openai": {
            "base_url": None,
            "default_model": "gpt-3.5-turbo",
        },
        "cerebras": {
            "base_url": "https://api.cerebras.ai/v1",
            "default_model": "llama3-70b-8192",
        },
        "groq": {
            "base_url": "https://api.groq.com/openai/v1",
            "default_model": "llama3-70b-8192",
        },
        "deepseek": {
            "base_url": "https://api.deepseek.com/v1",
            "default_model": "deepseek-chat",
        },
    }
    
    provider_config = providers.get(provider.lower(), providers["openai"])
    
    return LivingCore(
        api_key=api_key,
        base_url=provider_config["base_url"],
        model=model or provider_config["default_model"],
        **kwargs,
    )
