"""
Modules package for LivingEntity.

Contains specialized processing modules:
- InsightModule (ФМ): Background problem solving with "eureka" memory storage
- PredictionModule (ПБМ): Input pattern analysis and prediction
"""

from living_entity.modules.insight import InsightModule, InsightTask
from living_entity.modules.prediction import PredictionModule, InputPattern

__all__ = ["InsightModule", "InsightTask", "PredictionModule", "InputPattern"]
