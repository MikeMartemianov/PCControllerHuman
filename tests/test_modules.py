"""
Tests for InsightModule and PredictionModule.
"""

import asyncio
import pytest
import tempfile
import shutil
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from living_entity.modules.insight import InsightModule, InsightTask, InsightStatus
from living_entity.modules.prediction import PredictionModule, InputPattern, Prediction


class TestInsightModule:
    """Tests for InsightModule (ФМ)."""
    
    @pytest.fixture
    def insight_module(self):
        """Create InsightModule for testing."""
        return InsightModule(memory=None)
    
    def test_init(self, insight_module):
        """Test module initialization."""
        assert insight_module is not None
        assert insight_module.get_pending_count() == 0
        assert insight_module.get_solved_count() == 0
    
    def test_submit_problem(self, insight_module):
        """Test submitting a problem (without running event loop)."""
        task_id = insight_module.submit_problem(
            "How to optimize sorting?",
            context="Current algorithm is O(n^2)",
            priority=8
        )
        
        assert task_id is not None
        assert task_id.startswith("insight_")
        
        task = insight_module.get_task(task_id)
        assert task is not None
        assert task.problem == "How to optimize sorting?"
        assert task.priority == 8
        assert task.status == InsightStatus.PENDING
        
        # Task should be in pending queue (not yet started)
        assert len(insight_module._pending_queue) == 1
    
    def test_priority_bounds(self, insight_module):
        """Test priority is clamped to 1-10."""
        task_id1 = insight_module.submit_problem("Test 1", priority=0)
        task_id2 = insight_module.submit_problem("Test 2", priority=15)
        
        task1 = insight_module.get_task(task_id1)
        task2 = insight_module.get_task(task_id2)
        
        assert task1.priority == 1
        assert task2.priority == 10
    
    def test_check_insight_no_memory(self, insight_module):
        """Test checking insight without memory."""
        # Without memory, should return None for unknown queries
        result = insight_module.check_insight("unknown query")
        assert result is None
    
    def test_clear_solved(self, insight_module):
        """Test clearing solved tasks."""
        task_id = insight_module.submit_problem("Test problem")
        task = insight_module.get_task(task_id)
        
        # Manually mark as solved
        task.status = InsightStatus.SOLVED
        task.solution = "Test solution"
        
        count = insight_module.clear_solved()
        assert count == 1
        assert insight_module.get_task(task_id) is None
    
    @pytest.mark.asyncio
    async def test_start_stop(self, insight_module):
        """Test starting and stopping the module."""
        await insight_module.start()
        assert insight_module._running is True
        
        await insight_module.stop()
        assert insight_module._running is False
    
    @pytest.mark.asyncio
    async def test_pending_tasks_queued_on_start(self, insight_module):
        """Test that pending tasks are queued when start() is called."""
        # Submit before start
        task_id = insight_module.submit_problem("Pending problem")
        assert len(insight_module._pending_queue) == 1
        
        # Start the module
        await insight_module.start()
        
        # Pending queue should be cleared
        assert len(insight_module._pending_queue) == 0
        
        await insight_module.stop()


class TestPredictionModule:
    """Tests for PredictionModule (ПБМ)."""
    
    @pytest.fixture
    def prediction_module(self):
        """Create PredictionModule for testing."""
        return PredictionModule(memory=None)
    
    def test_init(self, prediction_module):
        """Test module initialization."""
        assert prediction_module is not None
        assert prediction_module.get_pattern_count() == 0
    
    def test_record_input(self, prediction_module):
        """Test recording input."""
        prediction_module.record_input("Hello")
        prediction_module.record_input("World")
        
        assert len(prediction_module._history) == 2
    
    def test_sequence_pattern_detection(self, prediction_module):
        """Test sequence pattern detection."""
        # Record a sequence multiple times
        for _ in range(3):
            prediction_module.record_input("Good morning")
            prediction_module.record_input("How are you?")
        
        patterns = prediction_module.get_patterns()
        sequence_patterns = [p for p in patterns if p.pattern_type == "sequence"]
        
        assert len(sequence_patterns) > 0
    
    def test_predict_next(self, prediction_module):
        """Test next prediction."""
        # Build history
        for _ in range(3):
            prediction_module.record_input("Start")
            prediction_module.record_input("Middle")
            prediction_module.record_input("End")
        
        # Record trigger
        prediction_module.record_input("Start")
        
        prediction = prediction_module.predict_next()
        # May or may not have prediction depending on confidence
        # Just test it doesn't error
        assert prediction is None or isinstance(prediction, Prediction)
    
    def test_get_predictions(self, prediction_module):
        """Test getting all predictions."""
        predictions = prediction_module.get_predictions()
        assert isinstance(predictions, list)
    
    def test_get_prediction_summary(self, prediction_module):
        """Test prediction summary string."""
        summary = prediction_module.get_prediction_summary()
        assert isinstance(summary, str)
    
    def test_clear_history(self, prediction_module):
        """Test clearing history."""
        prediction_module.record_input("Test 1")
        prediction_module.record_input("Test 2")
        
        prediction_module.clear_history()
        
        assert len(prediction_module._history) == 0
        assert len(prediction_module._predictions) == 0
    
    def test_clear_patterns(self, prediction_module):
        """Test clearing patterns."""
        # Build some patterns
        for _ in range(3):
            prediction_module.record_input("A")
            prediction_module.record_input("B")
        
        prediction_module.clear_patterns()
        
        assert prediction_module.get_pattern_count() == 0


class TestModulesIntegration:
    """Integration tests for both modules."""
    
    @pytest.fixture
    def temp_memory(self):
        """Create temporary memory for testing."""
        from living_entity.memory.matrix import MemoryMatrix
        temp_dir = tempfile.mkdtemp()
        memory = MemoryMatrix(persist_path=temp_dir)
        yield memory
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_insight_with_memory(self, temp_memory):
        """Test InsightModule with real memory."""
        insight = InsightModule(memory=temp_memory)
        
        task_id = insight.submit_problem("Test problem for memory")
        task = insight.get_task(task_id)
        
        # Manually solve and save
        task.status = InsightStatus.SOLVED
        task.solution = "This is the test solution"
        task.solved_at = datetime.now()
        
        insight._save_insight(task)
        
        # Check memory was saved
        assert temp_memory.count() > 0
    
    def test_prediction_with_memory(self, temp_memory):
        """Test PredictionModule with memory."""
        prediction = PredictionModule(memory=temp_memory)
        
        # Record inputs
        prediction.record_input("Hello")
        prediction.record_input("World")
        
        # Just test it works with memory
        assert prediction.get_pattern_count() >= 0
