"""
Custom logging system for LivingEntity with real-time output.
"""

import logging
import sys
from datetime import datetime
from enum import Enum
from typing import Optional, Callable

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False


class LogLevel(Enum):
    """Log levels for entity logging."""
    DEBUG = 10
    INFO = 20
    THOUGHT = 25  # Spirit thoughts
    ACTION = 26   # Brain actions
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


class EntityLogger:
    """
    Custom logger for LivingEntity with color-coded output.
    
    Features:
    - Real-time "thoughts" display for Spirit
    - Real-time "actions" display for Brain
    - Color-coded output by module
    - Configurable log levels
    """
    
    # Color mapping for modules
    COLORS = {
        "spirit": Fore.CYAN if COLORAMA_AVAILABLE else "",
        "brain": Fore.GREEN if COLORAMA_AVAILABLE else "",
        "memory": Fore.MAGENTA if COLORAMA_AVAILABLE else "",
        "executor": Fore.YELLOW if COLORAMA_AVAILABLE else "",
        "core": Fore.BLUE if COLORAMA_AVAILABLE else "",
        "error": Fore.RED if COLORAMA_AVAILABLE else "",
        "reset": Style.RESET_ALL if COLORAMA_AVAILABLE else "",
    }
    
    # Level icons
    ICONS = {
        LogLevel.DEBUG: "🔍",
        LogLevel.INFO: "ℹ️",
        LogLevel.THOUGHT: "💭",
        LogLevel.ACTION: "⚡",
        LogLevel.WARNING: "⚠️",
        LogLevel.ERROR: "❌",
        LogLevel.CRITICAL: "🔥",
    }
    
    def __init__(
        self,
        name: str = "LivingEntity",
        level: LogLevel = LogLevel.INFO,
        show_timestamp: bool = True,
        output_callback: Optional[Callable[[str], None]] = None,
    ):
        """
        Initialize the entity logger.
        
        :param name: Logger name
        :param level: Minimum log level to display
        :param show_timestamp: Whether to show timestamps
        :param output_callback: Optional callback for log output
        """
        self.name = name
        self.level = level
        self.show_timestamp = show_timestamp
        self.output_callback = output_callback
        self._handlers: list[Callable[[str, LogLevel, str], None]] = []
        
        # Configure standard logging as fallback
        self._std_logger = logging.getLogger(name)
        self._std_logger.setLevel(logging.DEBUG)
        
        if not self._std_logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            self._std_logger.addHandler(handler)
    
    def add_handler(self, handler: Callable[[str, LogLevel, str], None]) -> None:
        """Add a custom log handler."""
        self._handlers.append(handler)
    
    def remove_handler(self, handler: Callable[[str, LogLevel, str], None]) -> None:
        """Remove a custom log handler."""
        if handler in self._handlers:
            self._handlers.remove(handler)
    
    def _format_message(
        self,
        message: str,
        level: LogLevel,
        module: str = "core",
    ) -> str:
        """Format a log message with colors and icons."""
        parts = []
        
        # Timestamp
        if self.show_timestamp:
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            parts.append(f"[{timestamp}]")
        
        # Icon
        icon = self.ICONS.get(level, "")
        if icon:
            parts.append(icon)
        
        # Module with color
        color = self.COLORS.get(module, self.COLORS["core"])
        reset = self.COLORS["reset"]
        parts.append(f"{color}[{module.upper()}]{reset}")
        
        # Message
        if level == LogLevel.ERROR or level == LogLevel.CRITICAL:
            parts.append(f"{self.COLORS['error']}{message}{reset}")
        else:
            parts.append(message)
        
        return " ".join(parts)
    
    def _log(self, message: str, level: LogLevel, module: str = "core") -> None:
        """Internal logging method."""
        if level.value < self.level.value:
            return
        
        formatted = self._format_message(message, level, module)
        
        # Print to console
        print(formatted, flush=True)
        
        # Call output callback if set
        if self.output_callback:
            self.output_callback(formatted)
        
        # Call custom handlers
        for handler in self._handlers:
            try:
                handler(message, level, module)
            except Exception:
                pass
    
    def debug(self, message: str, module: str = "core") -> None:
        """Log debug message."""
        self._log(message, LogLevel.DEBUG, module)
    
    def info(self, message: str, module: str = "core") -> None:
        """Log info message."""
        self._log(message, LogLevel.INFO, module)
    
    def thought(self, message: str) -> None:
        """Log Spirit thought."""
        self._log(message, LogLevel.THOUGHT, "spirit")
    
    def action(self, message: str) -> None:
        """Log Brain action."""
        self._log(message, LogLevel.ACTION, "brain")
    
    def warning(self, message: str, module: str = "core") -> None:
        """Log warning message."""
        self._log(message, LogLevel.WARNING, module)
    
    def error(self, message: str, module: str = "core") -> None:
        """Log error message."""
        self._log(message, LogLevel.ERROR, module)
    
    def critical(self, message: str, module: str = "core") -> None:
        """Log critical message."""
        self._log(message, LogLevel.CRITICAL, module)
    
    def memory(self, message: str) -> None:
        """Log memory operation."""
        self._log(message, LogLevel.INFO, "memory")
    
    def executor(self, message: str) -> None:
        """Log executor operation."""
        self._log(message, LogLevel.INFO, "executor")
    
    def set_level(self, level: LogLevel) -> None:
        """Set minimum log level."""
        self.level = level


# Global logger instance
_default_logger: Optional[EntityLogger] = None


def get_logger(name: str = "LivingEntity") -> EntityLogger:
    """Get or create the default logger instance."""
    global _default_logger
    if _default_logger is None:
        _default_logger = EntityLogger(name)
    return _default_logger


def set_log_level(level: LogLevel) -> None:
    """Set the global log level."""
    get_logger().set_level(level)
