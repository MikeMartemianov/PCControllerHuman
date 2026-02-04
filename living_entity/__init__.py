"""
LivingEntity - Python library for autonomous AI agents.

Main exports:
    - LivingCore: Main orchestrator class
    - MemoryMatrix: Vector memory with RAG
    - ToolRegistry: Custom tools registration
    - FunctionExecutor: Sandboxed code execution (legacy)
    - InsightModule: Background problem solving (ФМ)
    - PredictionModule: Input prediction (ПБМ)
"""

from living_entity.core import LivingCore
from living_entity.memory.matrix import MemoryMatrix
from living_entity.execution.executor import FunctionExecutor
from living_entity.execution.tools import ToolRegistry
from living_entity.modules.insight import InsightModule
from living_entity.modules.prediction import PredictionModule

__version__ = "1.2.0"
__all__ = [
    "LivingCore",
    "MemoryMatrix",
    "FunctionExecutor",
    "ToolRegistry",
    "InsightModule",
    "PredictionModule",
]
