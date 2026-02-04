"""
Integration tests for LivingEntity.
"""

import asyncio
import os
import pytest
import tempfile
import shutil
from unittest.mock import AsyncMock, MagicMock, patch

from living_entity import LivingCore
from living_entity.core import create_entity, SystemParams


class TestLivingCore:
    """Integration tests for LivingCore orchestrator."""
    
    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for test."""
        memory_path = tempfile.mkdtemp()
        sandbox_path = tempfile.mkdtemp()
        yield memory_path, sandbox_path
        shutil.rmtree(memory_path, ignore_errors=True)
        shutil.rmtree(sandbox_path, ignore_errors=True)
    
    def test_init_default(self, temp_dirs):
        """Test initialization with default parameters."""
        memory_path, sandbox_path = temp_dirs
        
        entity = LivingCore(
            api_key="test-key",
            memory_path=memory_path,
            system_params={"sandbox_path": sandbox_path},
        )
        
        assert entity.model == "llama3-70b-8192"
        assert entity.base_url is None
        assert not entity.is_running()
    
    def test_init_with_custom_provider(self, temp_dirs):
        """Test initialization with Cerebras provider."""
        memory_path, sandbox_path = temp_dirs
        
        entity = LivingCore(
            api_key="test-key",
            base_url="https://api.cerebras.ai/v1",
            model="llama3-70b-8192",
            memory_path=memory_path,
            system_params={"sandbox_path": sandbox_path},
        )
        
        assert entity.base_url == "https://api.cerebras.ai/v1"
        assert entity.model == "llama3-70b-8192"
    
    def test_init_with_system_params(self, temp_dirs):
        """Test initialization with custom system params."""
        memory_path, sandbox_path = temp_dirs
        
        entity = LivingCore(
            api_key="test-key",
            memory_path=memory_path,
            system_params={
                "dm_temperature": 0.1,
                "mm_temperature": 0.0,
                "max_tokens": 2048,
                "dm_interval": 2.0,
                "mm_interval": 0.5,
                "sandbox_path": sandbox_path,
            },
        )
        
        assert entity.params.dm_temperature == 0.1
        assert entity.params.mm_temperature == 0.0
        assert entity.params.max_tokens == 2048
        assert entity.params.dm_interval == 2.0
        assert entity.params.mm_interval == 0.5
    
    def test_output_callback_registration(self, temp_dirs):
        """Test registering output callbacks."""
        memory_path, sandbox_path = temp_dirs
        
        entity = LivingCore(
            api_key="test-key",
            memory_path=memory_path,
            system_params={"sandbox_path": sandbox_path},
        )
        
        received = []
        
        @entity.on_output
        def callback(text):
            received.append(text)
        
        # Manually trigger output
        entity._handle_output("Test message")
        
        assert "Test message" in received
    
    def test_memory_operations(self, temp_dirs):
        """Test memory save and search."""
        memory_path, sandbox_path = temp_dirs
        
        entity = LivingCore(
            api_key="test-key",
            memory_path=memory_path,
            system_params={"sandbox_path": sandbox_path},
        )
        
        # Save memory
        memory_id = entity.save_memory("Important fact", source="test")
        assert memory_id is not None
        
        # Check count
        assert entity.get_memory_count() == 1
        
        # Search
        results = entity.search_memory("Important")
        assert len(results) > 0
    
    def test_clear_all(self, temp_dirs):
        """Test clearing all data."""
        memory_path, sandbox_path = temp_dirs
        
        entity = LivingCore(
            api_key="test-key",
            memory_path=memory_path,
            system_params={"sandbox_path": sandbox_path},
        )
        
        # Add some data
        entity.spirit._current_context.append("Test context")
        
        # Clear all
        entity.clear_all()
        
        assert len(entity.get_spirit_context()) == 0

    def test_register_tool_updates_brain_prompt(self, temp_dirs):
        """After register_tool, Brain's system prompt must contain the new tool."""
        memory_path, sandbox_path = temp_dirs

        entity = LivingCore(
            api_key="test-key",
            memory_path=memory_path,
            system_params={"sandbox_path": sandbox_path},
        )

        def my_custom_tool(x: str) -> str:
            return x

        entity.register_tool(
            my_custom_tool,
            name="my_custom_tool",
            description="A custom test tool",
            parameters={"x": "Input string"},
            returns="Same string",
        )

        prompt = entity.brain._system_prompt
        assert "my_custom_tool" in prompt
        assert "A custom test tool" in prompt

    def test_sync_tools_output_callback(self, temp_dirs):
        """sync_tools_output_callback sets registry callback to core handler."""
        memory_path, sandbox_path = temp_dirs

        entity = LivingCore(
            api_key="test-key",
            memory_path=memory_path,
            system_params={"sandbox_path": sandbox_path},
        )

        entity.sync_tools_output_callback()
        assert entity.tools._output_callback == entity._handle_output


class TestCreateEntity:
    """Tests for create_entity convenience function."""
    
    def test_create_openai(self):
        """Test creating OpenAI entity."""
        entity = create_entity(
            api_key="test-key",
            provider="openai",
        )
        
        assert entity.base_url is None
        assert entity.model == "gpt-3.5-turbo"
    
    def test_create_cerebras(self):
        """Test creating Cerebras entity."""
        entity = create_entity(
            api_key="test-key",
            provider="cerebras",
        )
        
        assert entity.base_url == "https://api.cerebras.ai/v1"
        assert entity.model == "llama3-70b-8192"
    
    def test_create_groq(self):
        """Test creating Groq entity."""
        entity = create_entity(
            api_key="test-key",
            provider="groq",
        )
        
        assert entity.base_url == "https://api.groq.com/openai/v1"
    
    def test_create_deepseek(self):
        """Test creating DeepSeek entity."""
        entity = create_entity(
            api_key="test-key",
            provider="deepseek",
        )
        
        assert entity.base_url == "https://api.deepseek.com/v1"
        assert entity.model == "deepseek-chat"
    
    def test_create_with_custom_model(self):
        """Test creating entity with custom model."""
        entity = create_entity(
            api_key="test-key",
            provider="openai",
            model="gpt-4",
        )
        
        assert entity.model == "gpt-4"


class TestSystemParams:
    """Tests for SystemParams validation."""
    
    def test_default_params(self):
        """Test default parameter values."""
        params = SystemParams()
        
        assert params.dm_temperature == 0.7
        assert params.mm_temperature == 0.3
        assert params.max_tokens == 1024
        assert params.dm_interval == 3.0
        assert params.mm_interval == 1.0
        assert params.unsafe_mode is False
        assert params.log_level == "INFO"
    
    def test_valid_temperature(self):
        """Test valid temperature values."""
        params = SystemParams(dm_temperature=0.0, mm_temperature=2.0)
        
        assert params.dm_temperature == 0.0
        assert params.mm_temperature == 2.0
    
    def test_invalid_temperature(self):
        """Test invalid temperature raises error."""
        with pytest.raises(ValueError):
            SystemParams(dm_temperature=3.0)
    
    def test_valid_intervals(self):
        """Test valid interval values."""
        params = SystemParams(dm_interval=0.5, mm_interval=0.1)
        
        assert params.dm_interval == 0.5
        assert params.mm_interval == 0.1


@pytest.mark.asyncio
class TestAsyncIntegration:
    """Async integration tests."""
    
    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories."""
        memory_path = tempfile.mkdtemp()
        sandbox_path = tempfile.mkdtemp()
        yield memory_path, sandbox_path
        shutil.rmtree(memory_path, ignore_errors=True)
        shutil.rmtree(sandbox_path, ignore_errors=True)
    
    async def test_start_stop(self, temp_dirs):
        """Test starting and stopping entity."""
        memory_path, sandbox_path = temp_dirs
        
        entity = LivingCore(
            api_key="test-key",
            memory_path=memory_path,
            system_params={"sandbox_path": sandbox_path},
        )
        
        # Mock the API calls
        with patch.object(entity.spirit, 'run_loop', new_callable=AsyncMock) as mock_spirit:
            with patch.object(entity.brain, 'run_loop', new_callable=AsyncMock) as mock_brain:
                await entity.start()
                
                assert entity.is_running()
                
                await entity.stop()
                
                assert not entity.is_running()
    
    async def test_context_manager(self, temp_dirs):
        """Test async context manager usage."""
        memory_path, sandbox_path = temp_dirs
        
        entity = LivingCore(
            api_key="test-key",
            memory_path=memory_path,
            system_params={"sandbox_path": sandbox_path},
        )
        
        with patch.object(entity.spirit, 'run_loop', new_callable=AsyncMock):
            with patch.object(entity.brain, 'run_loop', new_callable=AsyncMock):
                async with entity:
                    assert entity.is_running()
                
                assert not entity.is_running()
    
    async def test_input_signal(self, temp_dirs):
        """Test sending input signal."""
        memory_path, sandbox_path = temp_dirs
        
        entity = LivingCore(
            api_key="test-key",
            memory_path=memory_path,
            system_params={"sandbox_path": sandbox_path},
        )
        
        with patch.object(entity.spirit, 'run_loop', new_callable=AsyncMock):
            with patch.object(entity.brain, 'run_loop', new_callable=AsyncMock):
                await entity.start()
                
                # Send signal
                await entity.input_signal("Hello!", source="test")
                
                # Check queue has the signal
                assert not entity.spirit._signal_queue.empty()
                
                await entity.stop()
