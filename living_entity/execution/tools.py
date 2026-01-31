"""
ToolRegistry - System for registering and managing AI-callable tools.

Replaces sandbox execution with direct function calls.
"""

import os
import inspect
from typing import Any, Callable, Optional
from dataclasses import dataclass, field
from datetime import datetime

from living_entity.utils.logging import get_logger


@dataclass
class Tool:
    """A registered tool that the AI can call."""
    name: str
    description: str
    function: Callable
    parameters: dict = field(default_factory=dict)  # {param_name: description}
    returns: str = ""  # Description of return value
    category: str = "general"
    

@dataclass
class ToolResult:
    """Result from executing a tool."""
    success: bool
    output: Any = None
    error: Optional[str] = None
    tool_name: str = ""
    execution_time: float = 0.0


class ToolRegistry:
    """
    Registry for AI-callable tools with descriptions.
    
    Allows registering custom functions that the AI can call directly.
    No sandbox - functions execute in the main process.
    
    Example:
        ```python
        registry = ToolRegistry()
        
        @registry.register(
            description="Create a file with the given content",
            parameters={"path": "File path", "content": "File content"}
        )
        def create_file(path: str, content: str) -> str:
            with open(path, 'w') as f:
                f.write(content)
            return f"Created {path}"
        
        # Get tool descriptions for AI prompt
        descriptions = registry.get_tools_description()
        
        # Execute a tool
        result = registry.execute("create_file", path="test.txt", content="Hello")
        ```
    """
    
    def __init__(self, output_callback: Optional[Callable[[str], None]] = None):
        """
        Initialize the tool registry.
        
        :param output_callback: Callback for say_to_user tool
        """
        self._tools: dict[str, Tool] = {}
        self._output_callback = output_callback
        self.logger = get_logger()
        
        # Register default tools
        self._register_default_tools()
        
        self.logger.info("ToolRegistry initialized", module="tools")
    
    def _register_default_tools(self) -> None:
        """Register the default built-in tools."""
        
        # say_to_user - Output to user
        @self.register(
            name="say_to_user",
            description="Сказать что-то пользователю. Используй для ответов и сообщений.",
            parameters={"text": "Текст сообщения для пользователя"},
            returns="None",
            category="communication"
        )
        def say_to_user(text: str) -> None:
            if self._output_callback:
                self._output_callback(text)
        
        # create_file - Create a file
        @self.register(
            name="create_file",
            description="Создать файл с указанным содержимым.",
            parameters={"path": "Путь к файлу", "content": "Содержимое файла"},
            returns="Сообщение об успехе или ошибке",
            category="filesystem"
        )
        def create_file(path: str, content: str) -> str:
            try:
                # Create directory if needed
                dir_path = os.path.dirname(path)
                if dir_path:
                    os.makedirs(dir_path, exist_ok=True)
                
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return f"Файл создан: {path}"
            except Exception as e:
                return f"Ошибка создания файла: {e}"
        
        # read_file - Read a file
        @self.register(
            name="read_file",
            description="Прочитать содержимое файла.",
            parameters={"path": "Путь к файлу"},
            returns="Содержимое файла или сообщение об ошибке",
            category="filesystem"
        )
        def read_file(path: str) -> str:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return f.read()
            except FileNotFoundError:
                return f"Файл не найден: {path}"
            except Exception as e:
                return f"Ошибка чтения файла: {e}"
        
        # list_files - List directory contents
        @self.register(
            name="list_files",
            description="Показать содержимое директории.",
            parameters={"path": "Путь к директории (по умолчанию текущая)"},
            returns="Список файлов и папок",
            category="filesystem"
        )
        def list_files(path: str = ".") -> str:
            try:
                items = os.listdir(path)
                result = []
                for item in items:
                    full_path = os.path.join(path, item)
                    if os.path.isdir(full_path):
                        result.append(f"📁 {item}/")
                    else:
                        size = os.path.getsize(full_path)
                        result.append(f"📄 {item} ({size} bytes)")
                return "\n".join(result) if result else "Директория пуста"
            except Exception as e:
                return f"Ошибка: {e}"
        
        # delete_file - Delete a file
        @self.register(
            name="delete_file",
            description="Удалить файл.",
            parameters={"path": "Путь к файлу для удаления"},
            returns="Сообщение об успехе или ошибке",
            category="filesystem"
        )
        def delete_file(path: str) -> str:
            try:
                os.remove(path)
                return f"Файл удалён: {path}"
            except FileNotFoundError:
                return f"Файл не найден: {path}"
            except Exception as e:
                return f"Ошибка удаления: {e}"
        
        # get_time - Get current time
        @self.register(
            name="get_time",
            description="Получить текущее время и дату.",
            parameters={},
            returns="Текущие дата и время",
            category="utility"
        )
        def get_time() -> str:
            now = datetime.now()
            return now.strftime("%Y-%m-%d %H:%M:%S")
    
    def register(
        self,
        name: Optional[str] = None,
        description: str = "",
        parameters: Optional[dict] = None,
        returns: str = "",
        category: str = "general",
    ) -> Callable:
        """
        Decorator to register a function as a tool.
        
        :param name: Tool name (uses function name if None)
        :param description: Description for the AI
        :param parameters: Dict of {param_name: description}
        :param returns: Description of return value
        :param category: Tool category
        :return: Decorator
        """
        def decorator(func: Callable) -> Callable:
            tool_name = name or func.__name__
            
            # Auto-extract parameters if not provided
            params = parameters or {}
            if not params:
                sig = inspect.signature(func)
                for param_name, param in sig.parameters.items():
                    if param_name not in params:
                        params[param_name] = f"Параметр {param_name}"
            
            tool = Tool(
                name=tool_name,
                description=description or func.__doc__ or "Нет описания",
                function=func,
                parameters=params,
                returns=returns,
                category=category,
            )
            
            self._tools[tool_name] = tool
            self.logger.debug(f"Registered tool: {tool_name}", module="tools")
            
            return func
        
        return decorator
    
    def add_tool(
        self,
        func: Callable,
        name: Optional[str] = None,
        description: str = "",
        parameters: Optional[dict] = None,
        returns: str = "",
        category: str = "general",
    ) -> None:
        """
        Add a tool directly (not as decorator).
        
        :param func: The function to register
        :param name: Tool name (uses function name if None)
        :param description: Description for the AI
        :param parameters: Dict of {param_name: description}
        :param returns: Description of return value
        :param category: Tool category
        """
        decorator = self.register(name, description, parameters, returns, category)
        decorator(func)
    
    def remove_tool(self, name: str) -> bool:
        """
        Remove a registered tool.
        
        :param name: Tool name to remove
        :return: True if removed, False if not found
        """
        if name in self._tools:
            del self._tools[name]
            return True
        return False
    
    def get_tool(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self._tools.get(name)
    
    def list_tools(self) -> list[str]:
        """Get list of all registered tool names."""
        return list(self._tools.keys())
    
    def execute(self, tool_name: str, **kwargs) -> ToolResult:
        """
        Execute a registered tool.
        
        :param tool_name: Tool name
        :param kwargs: Arguments to pass to the tool
        :return: ToolResult with success status and output
        """
        import time
        
        tool = self._tools.get(tool_name)
        if not tool:
            return ToolResult(
                success=False,
                error=f"Tool not found: {tool_name}",
                tool_name=tool_name,
            )
        
        start_time = time.time()
        
        try:
            result = tool.function(**kwargs)
            execution_time = time.time() - start_time
            
            self.logger.debug(
                f"Tool executed: {tool_name} ({execution_time:.3f}s)",
                module="tools"
            )
            
            return ToolResult(
                success=True,
                output=result,
                tool_name=tool_name,
                execution_time=execution_time,
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            self.logger.error(f"Tool execution failed: {tool_name} - {e}", module="tools")
            
            return ToolResult(
                success=False,
                error=str(e),
                tool_name=tool_name,
                execution_time=execution_time,
            )
    
    def get_tools_description(self, categories: Optional[list[str]] = None) -> str:
        """
        Get formatted description of tools for AI prompt.
        
        :param categories: Filter by categories (None = all)
        :return: Formatted tools description
        """
        lines = ["## Доступные инструменты:\n"]
        
        # Group by category
        by_category: dict[str, list[Tool]] = {}
        for tool in self._tools.values():
            if categories and tool.category not in categories:
                continue
            if tool.category not in by_category:
                by_category[tool.category] = []
            by_category[tool.category].append(tool)
        
        for category, tools in sorted(by_category.items()):
            lines.append(f"\n### {category.capitalize()}:")
            
            for tool in tools:
                lines.append(f"\n**{tool.name}** - {tool.description}")
                
                if tool.parameters:
                    lines.append("  Параметры:")
                    for param, desc in tool.parameters.items():
                        lines.append(f"    - `{param}`: {desc}")
                
                if tool.returns:
                    lines.append(f"  Возвращает: {tool.returns}")
        
        return "\n".join(lines)
    
    def get_tools_for_prompt(self) -> str:
        """
        Get a compact tools description for system prompts.
        
        :return: Formatted tools list
        """
        lines = ["Доступные функции:"]
        
        for name, tool in self._tools.items():
            params = ", ".join(tool.parameters.keys())
            lines.append(f"- {name}({params}) - {tool.description}")
        
        return "\n".join(lines)
    
    def set_output_callback(self, callback: Callable[[str], None]) -> None:
        """Set the output callback for say_to_user."""
        self._output_callback = callback
