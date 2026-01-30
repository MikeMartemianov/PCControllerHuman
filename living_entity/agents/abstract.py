"""
Abstract base class for all agents with LLM API abstraction.
"""

import asyncio
import json
from abc import ABC, abstractmethod
from typing import Any, Optional

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from living_entity.utils.logging import get_logger, LogLevel


class AgentConfig(BaseModel):
    """Configuration for an agent."""
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1024, ge=1)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)


class AbstractAgent(ABC):
    """
    Abstract base class for LLM-powered agents.
    
    Provides:
    - AsyncOpenAI client initialization with custom base_url
    - Universal think() method for LLM requests
    - Automatic retry with exponential backoff
    - Error handling for network issues
    """
    
    MAX_RETRIES = 3
    BASE_RETRY_DELAY = 1.0  # seconds
    
    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        model: str = "gpt-3.5-turbo",
        config: Optional[AgentConfig] = None,
        client_kwargs: Optional[dict] = None,
    ):
        """
        Initialize the agent with API configuration.
        
        :param api_key: API key for the LLM provider
        :param base_url: Base URL for the API (None for OpenAI default)
        :param model: Model name to use
        :param config: Agent configuration
        :param client_kwargs: Additional kwargs for the OpenAI client
        """
        self.model = model
        self.config = config or AgentConfig()
        self.logger = get_logger()
        
        # Build client kwargs
        client_params = {
            "api_key": api_key,
        }
        if base_url:
            client_params["base_url"] = base_url
        if client_kwargs:
            client_params.update(client_kwargs)
        
        # Initialize async client
        self._client = AsyncOpenAI(**client_params)
        
        # Conversation history
        self._history: list[dict[str, str]] = []
        self._system_prompt: str = ""
    
    def set_system_prompt(self, prompt: str) -> None:
        """Set the system prompt for the agent."""
        self._system_prompt = prompt
    
    def add_to_history(self, role: str, content: str) -> None:
        """Add a message to the conversation history."""
        self._history.append({"role": role, "content": content})
    
    def clear_history(self) -> None:
        """Clear the conversation history."""
        self._history.clear()
    
    def get_history(self) -> list[dict[str, str]]:
        """Get a copy of the conversation history."""
        return self._history.copy()
    
    def set_history(self, history: list[dict[str, str]]) -> None:
        """Replace the conversation history."""
        self._history = history.copy()
    
    async def think(
        self,
        prompt: str,
        context: Optional[str] = None,
        include_history: bool = True,
        json_mode: bool = False,
    ) -> str:
        """
        Send a request to the LLM and get a response.
        
        :param prompt: The user prompt
        :param context: Optional additional context
        :param include_history: Whether to include conversation history
        :param json_mode: Whether to request JSON output
        :return: The LLM response text
        """
        messages = []
        
        # Add system prompt
        if self._system_prompt:
            messages.append({"role": "system", "content": self._system_prompt})
        
        # Add context if provided
        if context:
            messages.append({"role": "system", "content": f"Context:\n{context}"})
        
        # Add history if requested
        if include_history:
            messages.extend(self._history)
        
        # Add current prompt
        messages.append({"role": "user", "content": prompt})
        
        # Make request with retry
        response = await self._request_with_retry(messages, json_mode)
        
        # Add to history
        self.add_to_history("user", prompt)
        self.add_to_history("assistant", response)
        
        return response
    
    async def _request_with_retry(
        self,
        messages: list[dict[str, str]],
        json_mode: bool = False,
    ) -> str:
        """
        Make an API request with exponential backoff retry and rate limit handling.
        
        :param messages: The messages to send
        :param json_mode: Whether to request JSON output
        :return: The response text
        """
        import re
        last_error = None
        
        for attempt in range(self.MAX_RETRIES):
            try:
                kwargs = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": self.config.temperature,
                    "max_tokens": self.config.max_tokens,
                    "top_p": self.config.top_p,
                    "frequency_penalty": self.config.frequency_penalty,
                    "presence_penalty": self.config.presence_penalty,
                }
                
                if json_mode:
                    kwargs["response_format"] = {"type": "json_object"}
                
                response = await self._client.chat.completions.create(**kwargs)
                
                content = response.choices[0].message.content
                return content if content else ""
                
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                
                # Check for rate limit errors
                wait_time = self._extract_wait_time(error_str)
                
                if wait_time:
                    self.logger.warning(
                        f"Rate limit hit. Waiting {wait_time} seconds...",
                        module="agent"
                    )
                    await asyncio.sleep(wait_time)
                    continue
                
                # Regular retry with exponential backoff
                delay = self.BASE_RETRY_DELAY * (2 ** attempt)
                
                self.logger.warning(
                    f"API request failed (attempt {attempt + 1}/{self.MAX_RETRIES}): {e}",
                    module="agent"
                )
                
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(delay)
        
        # All retries failed
        self.logger.error(f"API request failed after {self.MAX_RETRIES} attempts", module="agent")
        raise last_error or Exception("Unknown API error")
    
    def _extract_wait_time(self, error_message: str) -> Optional[float]:
        """
        Extract wait time from rate limit error messages.
        
        Handles various API error formats:
        - "rate limit exceeded. retry after 60 seconds"
        - "please try again in 1m30s"
        - "retry-after: 120"
        - "limit exceeded, wait 2 minutes"
        
        :param error_message: Error message string
        :return: Wait time in seconds or None if not a rate limit error
        """
        import re
        
        # Check if this is a rate limit error
        rate_limit_keywords = ['rate limit', 'rate_limit', 'too many requests', 'quota exceeded', 
                               'limit exceeded', 'retry after', 'retry-after', 'please try again']
        
        if not any(kw in error_message for kw in rate_limit_keywords):
            return None
        
        # Try to extract seconds
        # Pattern: "60 seconds", "retry after 120", "wait 30 sec"
        seconds_match = re.search(r'(\d+)\s*(?:second|sec|s\b)', error_message)
        if seconds_match:
            return float(seconds_match.group(1)) + 1  # Add 1 second buffer
        
        # Pattern: "2 minutes", "wait 5 min"
        minutes_match = re.search(r'(\d+)\s*(?:minute|min|m\b)', error_message)
        if minutes_match:
            return float(minutes_match.group(1)) * 60 + 1
        
        # Pattern: "1 hour", "2 hours"
        hours_match = re.search(r'(\d+)\s*(?:hour|hr|h\b)', error_message)
        if hours_match:
            return float(hours_match.group(1)) * 3600 + 1
        
        # Pattern: "1m30s", "2m15s"
        combined_match = re.search(r'(\d+)m(\d+)s', error_message)
        if combined_match:
            minutes = int(combined_match.group(1))
            seconds = int(combined_match.group(2))
            return minutes * 60 + seconds + 1
        
        # Pattern: retry-after header value (just a number)
        retry_after_match = re.search(r'retry[_-]?after[:\s]+(\d+)', error_message)
        if retry_after_match:
            return float(retry_after_match.group(1)) + 1
        
        # Default wait time if rate limit detected but no specific time
        self.logger.info("Rate limit detected but no wait time specified. Waiting 60 seconds.", module="agent")
        return 60.0
    
    def parse_json_response(self, response: str) -> Optional[dict[str, Any]]:
        """
        Parse a JSON response from the LLM.
        
        Handles common issues like markdown code blocks and truncated JSON.
        
        :param response: The raw response text
        :return: Parsed JSON dict or None if parsing fails
        """
        # Remove markdown code blocks if present
        text = response.strip()
        
        if text.startswith("```"):
            # Find the end of the first line (language identifier)
            first_newline = text.find("\n")
            if first_newline > 0:
                text = text[first_newline + 1:]
            
            # Remove trailing ```
            if text.endswith("```"):
                text = text[:-3]
            
            text = text.strip()
        
        # Try to parse JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse JSON response: {e}", module="agent")
            
            # Try to find JSON object in the response
            start = text.find("{")
            end = text.rfind("}") + 1
            
            if start >= 0 and end > start:
                json_text = text[start:end]
                try:
                    return json.loads(json_text)
                except json.JSONDecodeError:
                    # Try to repair truncated JSON
                    repaired = self._repair_json(json_text)
                    if repaired:
                        try:
                            return json.loads(repaired)
                        except:
                            pass
            
            return None
    
    def _repair_json(self, text: str) -> Optional[str]:
        """
        Attempt to repair truncated JSON.
        
        :param text: Potentially broken JSON text
        :return: Repaired JSON or None
        """
        # Count brackets
        open_braces = text.count('{')
        close_braces = text.count('}')
        open_brackets = text.count('[')
        close_brackets = text.count(']')
        
        # Check for unclosed string
        in_string = False
        escaped = False
        for char in text:
            if escaped:
                escaped = False
                continue
            if char == '\\':
                escaped = True
                continue
            if char == '"':
                in_string = not in_string
        
        repaired = text
        
        # Close unclosed string
        if in_string:
            repaired += '"'
        
        # Add missing closing brackets/braces
        repaired += ']' * (open_brackets - close_brackets)
        repaired += '}' * (open_braces - close_braces)
        
        return repaired if repaired != text else None
    
    @abstractmethod
    async def process(self) -> None:
        """
        Main processing method for the agent.
        Must be implemented by subclasses.
        """
        pass
    
    @abstractmethod
    async def run_loop(self, interval: float) -> None:
        """
        Run the agent's main loop at the specified interval.
        Must be implemented by subclasses.
        
        :param interval: Loop interval in seconds
        """
        pass
