"""
Custom logging system for LivingEntity with real-time output.
Fixed for Windows compatibility.
"""

import logging
import sys
import io
from datetime import datetime
from enum import Enum
from typing import Optional, Callable

# Fix stdout/stderr for Windows subprocess
if sys.stdout is None or not hasattr(sys.stdout, 'write'):
    sys.stdout = io.StringIO()
if sys.stderr is None or not hasattr(sys.stderr, 'write'):
    sys.stderr = io.StringIO()

try:
    from colorama import init, Fore, Style
    init(autoreset=True, wrap=True)
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False
except Exception:
    COLORAMA_AVAILABLE = False


class LogLevel(Enum):
    """Log levels for entity logging."""
    DEBUG = 10
    INFO = 20
    THOUGHT = 25
    ACTION = 26
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


class EntityLogger:
    """Custom logger for LivingEntity with color-coded output."""

    COLORS = {
        "spirit": Fore.CYAN if COLORAMA_AVAILABLE else "",
        "brain": Fore.GREEN if COLORAMA_AVAILABLE else "",
        "memory": Fore.MAGENTA if COLORAMA_AVAILABLE else "",
        "executor": Fore.YELLOW if COLORAMA_AVAILABLE else "",
        "core": Fore.BLUE if COLORAMA_AVAILABLE else "",
        "error": Fore.RED if COLORAMA_AVAILABLE else "",
        "reset": Style.RESET_ALL if COLORAMA_AVAILABLE else "",
    }

    ICONS = {
        LogLevel.DEBUG: "D",
        LogLevel.INFO: "I",
        LogLevel.THOUGHT: "T",
        LogLevel.ACTION: "A",
        LogLevel.WARNING: "W",
        LogLevel.ERROR: "E",
        LogLevel.CRITICAL: "!",
    }

    def __init__(
        self,
        name: str = "LivingEntity",
        level: LogLevel = LogLevel.INFO,
        show_timestamp: bool = True,
        output_callback: Optional[Callable[[str], None]] = None,
    ):
        self.name = name
        self.level = level
        self.show_timestamp = show_timestamp
        self.output_callback = output_callback
        self._handlers: list[Callable[[str, LogLevel, str], None]] = []

        self._std_logger = logging.getLogger(name)
        self._std_logger.setLevel(logging.DEBUG)

        if not self._std_logger.handlers:
            try:
                handler = logging.StreamHandler(sys.stdout)
                handler.setFormatter(logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                ))
                self._std_logger.addHandler(handler)
            except Exception:
                pass

    def add_handler(self, handler: Callable[[str, LogLevel, str], None]) -> None:
        self._handlers.append(handler)

    def remove_handler(self, handler: Callable[[str, LogLevel, str], None]) -> None:
        if handler in self._handlers:
            self._handlers.remove(handler)

    def _format_message(self, message: str, level: LogLevel, module: str = "core") -> str:
        parts = []
        if self.show_timestamp:
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            parts.append(f"[{timestamp}]")
        icon = self.ICONS.get(level, "")
        if icon:
            parts.append(icon)
        color = self.COLORS.get(module, self.COLORS["core"])
        reset = self.COLORS["reset"]
        parts.append(f"{color}[{module.upper()}]{reset}")
        if level in (LogLevel.ERROR, LogLevel.CRITICAL):
            parts.append(f"{self.COLORS['error']}{message}{reset}")
        else:
            parts.append(message)
        return " ".join(parts)

    def _log(self, message: str, level: LogLevel, module: str = "core") -> None:
        if level.value < self.level.value:
            return
        formatted = self._format_message(message, level, module)
        try:
            if sys.stdout and hasattr(sys.stdout, 'write'):
                print(formatted, flush=True)
        except Exception:
            pass
        if self.output_callback:
            try:
                self.output_callback(formatted)
            except Exception:
                pass
        for handler in self._handlers:
            try:
                handler(message, level, module)
            except Exception:
                pass

    def debug(self, message: str, module: str = "core") -> None:
        self._log(message, LogLevel.DEBUG, module)

    def info(self, message: str, module: str = "core") -> None:
        self._log(message, LogLevel.INFO, module)

    def thought(self, message: str) -> None:
        self._log(message, LogLevel.THOUGHT, "spirit")

    def action(self, message: str) -> None:
        self._log(message, LogLevel.ACTION, "brain")

    def warning(self, message: str, module: str = "core") -> None:
        self._log(message, LogLevel.WARNING, module)

    def error(self, message: str, module: str = "core") -> None:
        self._log(message, LogLevel.ERROR, module)

    def critical(self, message: str, module: str = "core") -> None:
        self._log(message, LogLevel.CRITICAL, module)

    def memory(self, message: str) -> None:
        self._log(message, LogLevel.INFO, "memory")

    def executor(self, message: str) -> None:
        self._log(message, LogLevel.INFO, "executor")

    def set_level(self, level: LogLevel) -> None:
        self.level = level


_default_logger: Optional[EntityLogger] = None


def get_logger(name: str = "LivingEntity") -> EntityLogger:
    """Get or create the default logger instance."""
    global _default_logger
    if _default_logger is None:
        _default_logger = EntityLogger(name)
    return _default_logger


def set_log_level(level: LogLevel) -> None:
    """Set the global log level."""
    logger = get_logger()
    logger.set_level(level)
