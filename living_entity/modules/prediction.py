"""
PredictionModule (ПБМ) - Input pattern analysis and prediction.

Analyzes patterns in input data and predicts future inputs
to provide proactive decision support.
"""

import asyncio
import hashlib
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Optional, TYPE_CHECKING

from living_entity.utils.logging import get_logger

if TYPE_CHECKING:
    from living_entity.memory.matrix import MemoryMatrix


@dataclass
class InputPattern:
    """A detected input pattern."""
    id: str
    pattern_type: str  # "sequence", "time_based", "context"
    trigger: str  # What triggers this pattern
    prediction: str  # Predicted next input
    confidence: float  # 0.0 to 1.0
    occurrences: int = 1
    last_seen: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)


@dataclass
class Prediction:
    """A prediction for future input."""
    input_prediction: str
    confidence: float
    reasoning: str
    pattern_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None


class PredictionModule:
    """
    Module for input prediction and proactive decision support.
    
    Features:
    - Records and analyzes input patterns
    - Detects sequences and time-based patterns
    - Predicts likely next inputs
    - Provides predictions to entity for proactive decisions
    
    Example:
        ```python
        predictor = PredictionModule()
        
        # Record inputs
        predictor.record_input("Hello")
        predictor.record_input("How are you?")
        predictor.record_input("What's the weather?")
        
        # Get predictions
        predictions = predictor.get_predictions()
        for pred in predictions:
            print(f"Predicted: {pred.input_prediction} ({pred.confidence:.0%})")
        ```
    """
    
    DEFAULT_HISTORY_SIZE = 100
    PATTERN_CONFIDENCE_THRESHOLD = 0.3
    PREDICTION_EXPIRY_SECONDS = 300  # 5 minutes
    
    def __init__(
        self,
        memory: Optional["MemoryMatrix"] = None,
        history_size: int = DEFAULT_HISTORY_SIZE,
        llm_callback: Optional[Callable] = None,
    ):
        """
        Initialize the Prediction Module.
        
        :param memory: MemoryMatrix for context awareness
        :param history_size: Number of inputs to keep in history
        :param llm_callback: Async callback for LLM-based predictions
        """
        self.memory = memory
        self._llm_callback = llm_callback
        self.logger = get_logger()
        
        # Input history
        self._history: deque[tuple[str, datetime]] = deque(maxlen=history_size)
        
        # Detected patterns
        self._patterns: dict[str, InputPattern] = {}
        
        # Active predictions
        self._predictions: list[Prediction] = []
        
        # Pattern detection settings
        self._min_sequence_length = 2
        self._max_sequence_length = 5
        
        # Processing state
        self._running = False
        self._analyzer_task: Optional[asyncio.Task] = None
        
        # Callbacks
        self._on_prediction: Optional[Callable[[Prediction], None]] = None
        
        self.logger.info("PredictionModule initialized", module="prediction")
    
    def _generate_pattern_id(self, trigger: str, pattern_type: str) -> str:
        """Generate unique ID for a pattern."""
        content = f"{pattern_type}:{trigger}"
        return f"pat_{hashlib.sha256(content.encode()).hexdigest()[:10]}"
    
    def set_llm_callback(self, callback: Callable) -> None:
        """Set the LLM callback for advanced predictions."""
        self._llm_callback = callback
    
    def record_input(self, input_text: str, source: str = "user") -> None:
        """
        Record an input for pattern analysis.
        
        :param input_text: The input text
        :param source: Source of the input
        """
        timestamp = datetime.now()
        self._history.append((input_text, timestamp))
        
        # Analyze for patterns
        self._detect_patterns()
        
        # Update predictions
        self._update_predictions()
        
        self.logger.debug(f"Input recorded: {input_text[:30]}...", module="prediction")
    
    def _detect_patterns(self) -> None:
        """Detect patterns in input history."""
        if len(self._history) < self._min_sequence_length:
            return
        
        history_list = list(self._history)
        
        # Detect sequence patterns (A -> B)
        self._detect_sequence_patterns(history_list)
        
        # Detect time-based patterns
        self._detect_time_patterns(history_list)
    
    def _detect_sequence_patterns(
        self,
        history: list[tuple[str, datetime]]
    ) -> None:
        """Detect simple sequence patterns (if A, then B)."""
        if len(history) < 2:
            return
        
        # Look at recent pairs
        for i in range(len(history) - 1):
            trigger = history[i][0]
            follow = history[i + 1][0]
            
            # Skip if same input
            if trigger.lower() == follow.lower():
                continue
            
            # Create or update pattern
            pattern_id = self._generate_pattern_id(trigger.lower()[:50], "sequence")
            
            if pattern_id in self._patterns:
                pattern = self._patterns[pattern_id]
                pattern.occurrences += 1
                pattern.last_seen = datetime.now()
                # Increase confidence with more occurrences (max 0.9)
                pattern.confidence = min(0.3 + (pattern.occurrences * 0.1), 0.9)
            else:
                self._patterns[pattern_id] = InputPattern(
                    id=pattern_id,
                    pattern_type="sequence",
                    trigger=trigger[:100],
                    prediction=follow[:100],
                    confidence=0.3,
                    occurrences=1,
                )
    
    def _detect_time_patterns(
        self,
        history: list[tuple[str, datetime]]
    ) -> None:
        """Detect time-based patterns (same input at similar times)."""
        if len(history) < 3:
            return
        
        # Group by hour of day
        hour_groups: dict[int, list[str]] = {}
        for text, ts in history:
            hour = ts.hour
            if hour not in hour_groups:
                hour_groups[hour] = []
            hour_groups[hour].append(text.lower()[:50])
        
        # Find repeated inputs at same hour
        for hour, inputs in hour_groups.items():
            if len(inputs) < 2:
                continue
            
            # Find most common input at this hour
            from collections import Counter
            common = Counter(inputs).most_common(1)
            if common and common[0][1] >= 2:
                input_text = common[0][0]
                pattern_id = self._generate_pattern_id(f"hour_{hour}", "time_based")
                
                if pattern_id not in self._patterns:
                    self._patterns[pattern_id] = InputPattern(
                        id=pattern_id,
                        pattern_type="time_based",
                        trigger=f"hour:{hour}",
                        prediction=input_text,
                        confidence=0.4,
                        occurrences=common[0][1],
                        metadata={"hour": hour},
                    )
    
    def _update_predictions(self) -> None:
        """Update active predictions based on current context."""
        # Clear expired predictions
        now = datetime.now()
        self._predictions = [
            p for p in self._predictions
            if not p.expires_at or p.expires_at > now
        ]
        
        if not self._history:
            return
        
        # Get last input
        last_input, last_time = self._history[-1]
        
        # Find matching patterns
        new_predictions = []
        
        for pattern in self._patterns.values():
            if pattern.confidence < self.PATTERN_CONFIDENCE_THRESHOLD:
                continue
            
            # Check sequence patterns
            if pattern.pattern_type == "sequence":
                if last_input.lower()[:50] == pattern.trigger.lower()[:50]:
                    pred = Prediction(
                        input_prediction=pattern.prediction,
                        confidence=pattern.confidence,
                        reasoning=f"Sequence pattern: after '{pattern.trigger[:30]}' often comes this",
                        pattern_id=pattern.id,
                        expires_at=now + timedelta(seconds=self.PREDICTION_EXPIRY_SECONDS),
                    )
                    new_predictions.append(pred)
            
            # Check time patterns
            elif pattern.pattern_type == "time_based":
                current_hour = now.hour
                pattern_hour = pattern.metadata.get("hour")
                if pattern_hour == current_hour:
                    pred = Prediction(
                        input_prediction=pattern.prediction,
                        confidence=pattern.confidence * 0.8,  # Lower confidence for time
                        reasoning=f"Time-based pattern: common input at hour {current_hour}",
                        pattern_id=pattern.id,
                        expires_at=now + timedelta(seconds=self.PREDICTION_EXPIRY_SECONDS),
                    )
                    new_predictions.append(pred)
        
        # Add new predictions (avoid duplicates)
        existing_preds = {p.input_prediction.lower() for p in self._predictions}
        for pred in new_predictions:
            if pred.input_prediction.lower() not in existing_preds:
                self._predictions.append(pred)
                existing_preds.add(pred.input_prediction.lower())
                
                # Notify callback
                if self._on_prediction:
                    self._on_prediction(pred)
        
        # Sort by confidence
        self._predictions.sort(key=lambda p: p.confidence, reverse=True)
        
        # Keep only top N predictions
        self._predictions = self._predictions[:10]
    
    def predict_next(self, context: str = "") -> Optional[Prediction]:
        """
        Get the most likely next input prediction.
        
        :param context: Additional context for prediction
        :return: Most likely prediction or None
        """
        self._update_predictions()
        
        if self._predictions:
            return self._predictions[0]
        
        return None
    
    def get_predictions(self, min_confidence: float = 0.0) -> list[Prediction]:
        """
        Get all active predictions.
        
        :param min_confidence: Minimum confidence threshold
        :return: List of predictions sorted by confidence
        """
        self._update_predictions()
        
        return [
            p for p in self._predictions
            if p.confidence >= min_confidence
        ]
    
    def get_patterns(self) -> list[InputPattern]:
        """Get all detected patterns."""
        return list(self._patterns.values())
    
    def get_pattern_count(self) -> int:
        """Get count of detected patterns."""
        return len(self._patterns)
    
    def get_prediction_summary(self) -> str:
        """Get a human-readable summary of predictions."""
        predictions = self.get_predictions(min_confidence=0.3)
        
        if not predictions:
            return "Нет активных предсказаний"
        
        lines = ["Предсказания:"]
        for i, pred in enumerate(predictions[:5], 1):
            lines.append(
                f"  {i}. \"{pred.input_prediction}\" "
                f"({pred.confidence:.0%}) - {pred.reasoning}"
            )
        
        return "\n".join(lines)
    
    async def predict_with_llm(self, context: str = "") -> Optional[Prediction]:
        """
        Get LLM-based prediction for more complex scenarios.
        
        :param context: Additional context
        :return: LLM-generated prediction
        """
        if not self._llm_callback:
            return None
        
        # Build context from history
        history_context = "\n".join([
            f"- {text}" for text, _ in list(self._history)[-10:]
        ])
        
        prompt = f"""Проанализируй историю ввода и предскажи следующий вход.

История:
{history_context}

{"Дополнительный контекст: " + context if context else ""}

Ответь в формате:
Предсказание: [предсказанный ввод]
Уверенность: [0.0-1.0]
Обоснование: [краткое объяснение]"""
        
        try:
            response = await self._llm_callback(prompt)
            
            # Parse response
            lines = response.strip().split("\n")
            prediction_text = ""
            confidence = 0.5
            reasoning = ""
            
            for line in lines:
                if line.startswith("Предсказание:"):
                    prediction_text = line.split(":", 1)[1].strip()
                elif line.startswith("Уверенность:"):
                    try:
                        confidence = float(line.split(":", 1)[1].strip())
                    except ValueError:
                        pass
                elif line.startswith("Обоснование:"):
                    reasoning = line.split(":", 1)[1].strip()
            
            if prediction_text:
                return Prediction(
                    input_prediction=prediction_text,
                    confidence=confidence,
                    reasoning=reasoning or "LLM prediction",
                    expires_at=datetime.now() + timedelta(seconds=60),
                )
                
        except Exception as e:
            self.logger.error(f"LLM prediction failed: {e}", module="prediction")
        
        return None
    
    def on_prediction(self, callback: Callable[[Prediction], None]) -> None:
        """Register callback for new predictions."""
        self._on_prediction = callback
    
    def clear_history(self) -> None:
        """Clear input history."""
        self._history.clear()
        self._predictions.clear()
    
    def clear_patterns(self) -> None:
        """Clear all detected patterns."""
        self._patterns.clear()
        self._predictions.clear()
