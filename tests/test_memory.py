"""
Tests for memory modules.
"""

import os
import pytest
import tempfile
import shutil
from datetime import datetime

from living_entity.memory.matrix import MemoryMatrix, MemoryEntry


class TestMemoryMatrix:
    """Tests for MemoryMatrix."""
    
    @pytest.fixture
    def temp_memory_path(self):
        """Create a temporary directory for memory storage."""
        path = tempfile.mkdtemp()
        yield path
        shutil.rmtree(path, ignore_errors=True)
    
    def test_init(self, temp_memory_path):
        """Test memory initialization."""
        memory = MemoryMatrix(persist_path=temp_memory_path)
        
        assert memory.persist_path == temp_memory_path
        assert memory.count() == 0
    
    def test_save_memory(self, temp_memory_path):
        """Test saving a memory."""
        memory = MemoryMatrix(persist_path=temp_memory_path)
        
        memory_id = memory.save_memory(
            text="This is a test memory",
            source="test",
            importance=0.8,
        )
        
        assert memory_id is not None
        assert len(memory_id) == 16
        assert memory.count() == 1
    
    def test_save_memory_with_metadata(self, temp_memory_path):
        """Test saving memory with metadata."""
        memory = MemoryMatrix(persist_path=temp_memory_path)
        
        memory_id = memory.save_memory(
            text="Memory with metadata",
            source="test",
            importance=0.5,
            metadata={"tag": "important", "category": "test"},
        )
        
        assert memory_id is not None
    
    def test_retrieve_similar(self, temp_memory_path):
        """Test retrieving similar memories."""
        memory = MemoryMatrix(persist_path=temp_memory_path)
        
        # Save some memories
        memory.save_memory("I love programming in Python", source="test")
        memory.save_memory("The weather is nice today", source="test")
        memory.save_memory("Python is a great language", source="test")
        
        # Search for Python-related memories
        results = memory.retrieve("Python programming", threshold=0.3)
        
        # Should find at least one result
        assert len(results) > 0
    
    def test_retrieve_with_threshold(self, temp_memory_path):
        """Test that threshold filters results."""
        memory = MemoryMatrix(persist_path=temp_memory_path)
        
        memory.save_memory("Cats are cute animals", source="test")
        memory.save_memory("Dogs are loyal pets", source="test")
        
        # High threshold should return fewer results
        high_threshold_results = memory.retrieve("birds", threshold=0.9)
        low_threshold_results = memory.retrieve("birds", threshold=0.1)
        
        assert len(high_threshold_results) <= len(low_threshold_results)
    
    def test_auto_associative_search(self, temp_memory_path):
        """Test automatic associative search."""
        memory = MemoryMatrix(persist_path=temp_memory_path)
        
        memory.save_memory("The meeting is at 3 PM", source="test")
        memory.save_memory("John called earlier", source="test")
        
        results = memory.auto_associative_search("What meetings do I have?")
        
        # Should return results (relaxed threshold)
        assert isinstance(results, list)
    
    def test_delete_memory(self, temp_memory_path):
        """Test deleting a memory."""
        memory = MemoryMatrix(persist_path=temp_memory_path)
        
        memory_id = memory.save_memory("To be deleted", source="test")
        assert memory.count() == 1
        
        result = memory.delete_memory(memory_id)
        assert result is True
        assert memory.count() == 0
    
    def test_get_all_memories(self, temp_memory_path):
        """Test getting all memories."""
        memory = MemoryMatrix(persist_path=temp_memory_path)
        
        memory.save_memory("Memory 1", source="test")
        memory.save_memory("Memory 2", source="test")
        memory.save_memory("Memory 3", source="test")
        
        all_memories = memory.get_all_memories()
        
        assert len(all_memories) == 3
        assert all(isinstance(m, MemoryEntry) for m in all_memories)
    
    def test_get_all_memories_with_limit(self, temp_memory_path):
        """Test getting memories with limit."""
        memory = MemoryMatrix(persist_path=temp_memory_path)
        
        for i in range(10):
            memory.save_memory(f"Memory {i}", source="test")
        
        limited = memory.get_all_memories(limit=5)
        
        assert len(limited) == 5
    
    def test_clear(self, temp_memory_path):
        """Test clearing all memories."""
        memory = MemoryMatrix(persist_path=temp_memory_path)
        
        memory.save_memory("Memory 1", source="test")
        memory.save_memory("Memory 2", source="test")
        
        assert memory.count() == 2
        
        memory.clear()
        
        assert memory.count() == 0
    
    def test_memory_entry_model(self):
        """Test MemoryEntry pydantic model."""
        entry = MemoryEntry(
            id="test123",
            text="Test content",
            source="unit_test",
            importance=0.75,
        )
        
        assert entry.id == "test123"
        assert entry.text == "Test content"
        assert entry.source == "unit_test"
        assert entry.importance == 0.75
        assert isinstance(entry.timestamp, datetime)


class TestMemoryMatrixFallback:
    """Tests for MemoryMatrix fallback mode (no ChromaDB)."""
    
    def test_fallback_save_retrieve(self):
        """Test fallback mode operations."""
        memory = MemoryMatrix(persist_path="./test_fallback")
        
        # Force fallback mode
        memory._collection = None
        memory._fallback_memory = []
        
        # Save
        memory_id = memory.save_memory("Fallback test", source="test")
        assert memory_id is not None
        
        # Should be in fallback storage
        assert len(memory._fallback_memory) == 1
        
        # Retrieve (fallback uses substring matching)
        results = memory.retrieve("Fallback")
        assert len(results) > 0
