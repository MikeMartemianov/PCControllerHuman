"""
FunctionExecutor - Sandboxed Python code execution.
"""

import ast
import io
import sys
import traceback
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional
import asyncio

from living_entity.utils.logging import get_logger


@dataclass
class ExecutionResult:
    """Result of code execution."""
    success: bool
    output: str = ""
    error: str = ""
    return_value: Any = None
    user_messages: list[str] = field(default_factory=list)
    files_created: list[str] = field(default_factory=list)
    files_read: dict[str, str] = field(default_factory=dict)
    task_ended: bool = False


class SandboxViolation(Exception):
    """Raised when code attempts forbidden operations."""
    pass


class FunctionExecutor:
    """
    Sandboxed Python code execution environment.
    
    Features:
    - Restricted exec() with limited globals/locals
    - Safe file operations (create/read in sandbox)
    - say_to_user() callback
    - end() signal for task completion
    - Blocked dangerous modules
    """
    
    # Modules that are ALWAYS blocked
    BLOCKED_MODULES = {
        "os", "subprocess", "shutil", "sys", "importlib",
        "ctypes", "multiprocessing", "socket", "requests",
        "urllib", "http", "ftplib", "smtplib", "telnetlib",
        "pickle", "marshal", "shelve", "dbm", "sqlite3",
        "builtins", "__builtins__",
    }
    
    # Built-in functions that are allowed
    SAFE_BUILTINS = {
        "abs", "all", "any", "ascii", "bin", "bool", "bytearray",
        "bytes", "callable", "chr", "complex", "dict", "divmod",
        "enumerate", "filter", "float", "format", "frozenset",
        "getattr", "hasattr", "hash", "hex", "int", "isinstance",
        "issubclass", "iter", "len", "list", "map", "max", "min",
        "next", "object", "oct", "ord", "pow", "print", "range",
        "repr", "reversed", "round", "set", "slice", "sorted",
        "str", "sum", "tuple", "type", "zip",
        # Math functions
        "True", "False", "None",
    }
    
    def __init__(
        self,
        sandbox_path: str = "./sandbox",
        output_callback: Optional[Callable[[str], None]] = None,
        unsafe_mode: bool = False,
        timeout: float = 30.0,
    ):
        """
        Initialize the executor.
        
        :param sandbox_path: Directory for file operations
        :param output_callback: Callback for say_to_user() messages
        :param unsafe_mode: If True, allow dangerous operations
        :param timeout: Execution timeout in seconds
        """
        self.sandbox_path = Path(sandbox_path)
        self.output_callback = output_callback
        self.unsafe_mode = unsafe_mode
        self.timeout = timeout
        self.logger = get_logger()
        
        # Ensure sandbox exists
        self.sandbox_path.mkdir(parents=True, exist_ok=True)
        
        # Execution state
        self._user_messages: list[str] = []
        self._files_created: list[str] = []
        self._files_read: dict[str, str] = {}
        self._task_ended: bool = False
        
        self.logger.executor(f"Sandbox initialized at {self.sandbox_path}")
    
    def _validate_code(self, code: str) -> None:
        """
        Validate code for safety before execution.
        
        :param code: Python code to validate
        :raises SandboxViolation: If code contains forbidden operations
        """
        if self.unsafe_mode:
            return
        
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            raise SyntaxError(f"Invalid Python syntax: {e}")
        
        for node in ast.walk(tree):
            # Check for import statements
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module_name = ""
                if isinstance(node, ast.Import):
                    module_name = node.names[0].name.split(".")[0]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    module_name = node.module.split(".")[0]
                
                if module_name in self.BLOCKED_MODULES:
                    raise SandboxViolation(
                        f"Import of '{module_name}' is not allowed in sandbox"
                    )
            
            # Check for exec/eval calls
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in ("exec", "eval", "compile", "__import__"):
                        raise SandboxViolation(
                            f"'{node.func.id}' is not allowed in sandbox"
                        )
            
            # Check for attribute access to blocked items
            if isinstance(node, ast.Attribute):
                if node.attr in ("system", "popen", "spawn", "fork"):
                    raise SandboxViolation(
                        f"Access to '{node.attr}' is not allowed in sandbox"
                    )
    
    def _get_safe_globals(self) -> dict[str, Any]:
        """Get the restricted globals for execution."""
        import builtins
        import math
        import json
        import re
        import datetime
        import random
        
        # Start with empty dict
        safe_globals: dict[str, Any] = {}
        
        # Add safe builtins
        for name in self.SAFE_BUILTINS:
            if hasattr(builtins, name):
                safe_globals[name] = getattr(builtins, name)
        
        # Add safe modules
        safe_globals["math"] = math
        safe_globals["json"] = json
        safe_globals["re"] = re
        safe_globals["datetime"] = datetime
        safe_globals["random"] = random
        
        # Add sandbox functions
        safe_globals["say_to_user"] = self._say_to_user
        safe_globals["create_file"] = self._create_file
        safe_globals["read_file"] = self._read_file
        safe_globals["end"] = self._end
        
        # Add print that captures output
        safe_globals["print"] = print
        
        return safe_globals
    
    def _say_to_user(self, text: str) -> None:
        """Send a message to the user."""
        self._user_messages.append(str(text))
        if self.output_callback:
            self.output_callback(str(text))
        self.logger.info(f"say_to_user: {text}", module="executor")
    
    def _create_file(self, path: str, content: str) -> str:
        """Create a file in the sandbox."""
        # Normalize path
        file_path = self.sandbox_path / Path(path).name
        
        # Write file
        file_path.write_text(content, encoding="utf-8")
        self._files_created.append(str(file_path))
        
        self.logger.executor(f"Created file: {file_path}")
        return str(file_path)
    
    def _read_file(self, path: str) -> str:
        """Read a file from the sandbox."""
        # Normalize path
        file_path = self.sandbox_path / Path(path).name
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        content = file_path.read_text(encoding="utf-8")
        self._files_read[str(file_path)] = content
        
        self.logger.executor(f"Read file: {file_path}")
        return content
    
    def _end(self) -> None:
        """Signal task completion."""
        self._task_ended = True
        self.logger.executor("Task ended")
    
    def execute(self, code: str) -> ExecutionResult:
        """
        Execute Python code in the sandbox.
        
        :param code: Python code to execute
        :return: Execution result
        """
        # Reset state
        self._user_messages = []
        self._files_created = []
        self._files_read = {}
        self._task_ended = False
        
        # Validate code
        try:
            self._validate_code(code)
        except (SyntaxError, SandboxViolation) as e:
            return ExecutionResult(
                success=False,
                error=str(e),
            )
        
        # Prepare execution environment
        safe_globals = self._get_safe_globals()
        safe_locals: dict[str, Any] = {}
        
        # Capture output
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        try:
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec(code, safe_globals, safe_locals)
            
            return ExecutionResult(
                success=True,
                output=stdout_capture.getvalue(),
                return_value=safe_locals.get("result"),
                user_messages=self._user_messages.copy(),
                files_created=self._files_created.copy(),
                files_read=self._files_read.copy(),
                task_ended=self._task_ended,
            )
            
        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
            return ExecutionResult(
                success=False,
                output=stdout_capture.getvalue(),
                error=error_msg,
                user_messages=self._user_messages.copy(),
                files_created=self._files_created.copy(),
                files_read=self._files_read.copy(),
            )
    
    async def execute_async(self, code: str) -> ExecutionResult:
        """
        Execute Python code asynchronously with timeout.
        
        :param code: Python code to execute
        :return: Execution result
        """
        try:
            result = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None, self.execute, code
                ),
                timeout=self.timeout
            )
            return result
        except asyncio.TimeoutError:
            return ExecutionResult(
                success=False,
                error=f"Execution timed out after {self.timeout} seconds",
            )
    
    def set_output_callback(self, callback: Callable[[str], None]) -> None:
        """Set the output callback for say_to_user()."""
        self.output_callback = callback
    
    def list_sandbox_files(self) -> list[str]:
        """List all files in the sandbox directory."""
        return [str(f) for f in self.sandbox_path.iterdir() if f.is_file()]
    
    def clear_sandbox(self) -> None:
        """Remove all files from the sandbox."""
        for file in self.sandbox_path.iterdir():
            if file.is_file():
                file.unlink()
        self.logger.executor("Sandbox cleared")
