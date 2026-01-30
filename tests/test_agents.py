"""
Tests for agent modules.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from living_entity.agents.abstract import AbstractAgent, AgentConfig
from living_entity.agents.spirit import SpiritAgent, Signal
from living_entity.agents.brain import BrainAgent


class ConcreteAgent(AbstractAgent):
    """Concrete implementation for testing."""
    
    async def process(self):
        pass
    
    async def run_loop(self, interval: float):
        pass


class TestAbstractAgent:
    """Tests for AbstractAgent base class."""
    
    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        agent = ConcreteAgent(api_key="test-key")
        
        assert agent.model == "gpt-3.5-turbo"
        assert agent.config.temperature == 0.7
        assert agent.config.max_tokens == 1024
    
    def test_init_with_base_url(self):
        """Test initialization with custom base URL."""
        agent = ConcreteAgent(
            api_key="test-key",
            base_url="https://api.cerebras.ai/v1",
            model="llama3-70b-8192",
        )
        
        assert agent.model == "llama3-70b-8192"
    
    def test_init_with_config(self):
        """Test initialization with custom config."""
        config = AgentConfig(temperature=0.2, max_tokens=2048)
        agent = ConcreteAgent(api_key="test-key", config=config)
        
        assert agent.config.temperature == 0.2
        assert agent.config.max_tokens == 2048
    
    def test_system_prompt(self):
        """Test setting system prompt."""
        agent = ConcreteAgent(api_key="test-key")
        agent.set_system_prompt("You are a helpful assistant.")
        
        assert agent._system_prompt == "You are a helpful assistant."
    
    def test_history_management(self):
        """Test conversation history management."""
        agent = ConcreteAgent(api_key="test-key")
        
        agent.add_to_history("user", "Hello")
        agent.add_to_history("assistant", "Hi there!")
        
        history = agent.get_history()
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["content"] == "Hi there!"
        
        agent.clear_history()
        assert len(agent.get_history()) == 0
    
    def test_parse_json_response_valid(self):
        """Test JSON parsing with valid response."""
        agent = ConcreteAgent(api_key="test-key")
        
        response = '{"key": "value", "number": 42}'
        result = agent.parse_json_response(response)
        
        assert result == {"key": "value", "number": 42}
    
    def test_parse_json_response_with_markdown(self):
        """Test JSON parsing with markdown code block."""
        agent = ConcreteAgent(api_key="test-key")
        
        response = '```json\n{"key": "value"}\n```'
        result = agent.parse_json_response(response)
        
        assert result == {"key": "value"}
    
    def test_parse_json_response_invalid(self):
        """Test JSON parsing with invalid response."""
        agent = ConcreteAgent(api_key="test-key")
        
        response = 'This is not JSON'
        result = agent.parse_json_response(response)
        
        assert result is None


class TestSpiritAgent:
    """Tests for SpiritAgent."""
    
    def test_init(self):
        """Test Spirit initialization."""
        spirit = SpiritAgent(api_key="test-key")
        
        assert spirit.LOOP_INTERVAL == 3.0
        assert not spirit.is_running()
    
    @pytest.mark.asyncio
    async def test_receive_input(self):
        """Test receiving input signal."""
        spirit = SpiritAgent(api_key="test-key")
        
        await spirit.receive_input("Hello", source="user")
        
        assert not spirit._signal_queue.empty()
        signal = await spirit._signal_queue.get()
        assert signal.content == "Hello"
        assert signal.source == "user"
    
    @pytest.mark.asyncio
    async def test_receive_signal(self):
        """Test receiving Signal object."""
        spirit = SpiritAgent(api_key="test-key")
        
        signal = Signal(content="Test signal", source="test", priority="high")
        await spirit.receive_signal(signal)
        
        assert not spirit._signal_queue.empty()
    
    def test_command_queue(self):
        """Test getting command queue."""
        spirit = SpiritAgent(api_key="test-key")
        
        queue = spirit.get_command_queue()
        assert queue is not None
    
    def test_context_management(self):
        """Test context management."""
        spirit = SpiritAgent(api_key="test-key")
        
        spirit._current_context.append("Test 1")
        spirit._current_context.append("Test 2")
        
        context = spirit.get_context()
        assert len(context) == 2
        
        spirit.clear_context()
        assert len(spirit.get_context()) == 0


class TestBrainAgent:
    """Tests for BrainAgent."""
    
    def test_init(self):
        """Test Brain initialization."""
        brain = BrainAgent(api_key="test-key")
        
        assert brain.LOOP_INTERVAL == 1.0
        assert not brain.is_running()
        assert brain.executor is not None
        assert brain.focus is not None
    
    def test_set_command_queue(self):
        """Test setting command queue."""
        brain = BrainAgent(api_key="test-key")
        queue: asyncio.Queue = asyncio.Queue()
        
        brain.set_command_queue(queue)
        assert brain._command_queue is queue
    
    def test_set_output_callback(self):
        """Test setting output callback."""
        brain = BrainAgent(api_key="test-key")
        
        callback = MagicMock()
        brain.set_output_callback(callback)
        
        assert brain._on_output is callback
    
    def test_action_history(self):
        """Test action history management."""
        brain = BrainAgent(api_key="test-key")
        
        # History should be empty initially
        history = brain.get_action_history()
        assert len(history) == 0
        
        # Clear should work on empty
        brain.clear_history()
        assert len(brain.get_action_history()) == 0


class TestAgentIntegration:
    """Integration tests for Spirit and Brain agents."""
    
    @pytest.mark.asyncio
    async def test_spirit_to_brain_communication(self):
        """Test command passing from Spirit to Brain."""
        spirit = SpiritAgent(api_key="test-key")
        brain = BrainAgent(api_key="test-key")
        
        # Connect command queue
        brain.set_command_queue(spirit.get_command_queue())
        
        # Put a command in Spirit's queue
        from living_entity.agents.spirit import SpiritCommand
        command = SpiritCommand(type="delegate", content="Test task", priority="high")
        await spirit._command_queue.put(command)
        
        # Brain should be able to receive it
        assert not brain._command_queue.empty()
