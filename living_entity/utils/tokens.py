"""
Token counting utilities for different LLM providers.
"""

import re
from typing import Optional

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False


class TokenCounter:
    """
    Utility class for counting tokens across different LLM models.
    
    Supports:
    - OpenAI models via tiktoken
    - Approximate counting for Llama/other models
    """
    
    # Approximate tokens per character for different model families
    CHARS_PER_TOKEN = {
        "gpt": 4.0,
        "llama": 3.5,
        "mixtral": 3.5,
        "deepseek": 3.8,
        "default": 4.0,
    }
    
    def __init__(self, model: str = "gpt-3.5-turbo"):
        """
        Initialize token counter for a specific model.
        
        :param model: Model name (e.g., "gpt-4", "llama3-70b-8192")
        """
        self.model = model.lower()
        self._encoder: Optional[object] = None
        self._model_family = self._detect_model_family()
        
        # Try to initialize tiktoken for OpenAI models
        if TIKTOKEN_AVAILABLE and self._model_family == "gpt":
            try:
                self._encoder = tiktoken.encoding_for_model(model)
            except KeyError:
                # Fallback to cl100k_base for newer models
                try:
                    self._encoder = tiktoken.get_encoding("cl100k_base")
                except Exception:
                    self._encoder = None
    
    def _detect_model_family(self) -> str:
        """Detect model family from model name."""
        model_lower = self.model
        
        if "gpt" in model_lower or "text-davinci" in model_lower:
            return "gpt"
        elif "llama" in model_lower:
            return "llama"
        elif "mixtral" in model_lower or "mistral" in model_lower:
            return "mixtral"
        elif "deepseek" in model_lower:
            return "deepseek"
        else:
            return "default"
    
    def count(self, text: str) -> int:
        """
        Count tokens in text.
        
        :param text: Input text
        :return: Number of tokens
        """
        if not text:
            return 0
        
        # Use tiktoken if available for GPT models
        if self._encoder is not None:
            return len(self._encoder.encode(text))
        
        # Approximate counting for other models
        return self._approximate_count(text)
    
    def _approximate_count(self, text: str) -> int:
        """
        Approximate token count based on character count and model family.
        
        Uses heuristics based on typical tokenization patterns.
        """
        chars_per_token = self.CHARS_PER_TOKEN.get(
            self._model_family, 
            self.CHARS_PER_TOKEN["default"]
        )
        
        # Count words and special characters separately
        words = re.findall(r'\w+', text)
        special_chars = re.findall(r'[^\w\s]', text)
        whitespace = len(re.findall(r'\s+', text))
        
        # Approximate: words + special chars + some whitespace overhead
        word_tokens = sum(max(1, len(w) / chars_per_token) for w in words)
        special_tokens = len(special_chars)
        
        return int(word_tokens + special_tokens + whitespace * 0.1)
    
    def count_messages(self, messages: list[dict]) -> int:
        """
        Count tokens in a list of chat messages.
        
        :param messages: List of message dicts with 'role' and 'content'
        :return: Total token count
        """
        total = 0
        
        for message in messages:
            # Count content
            content = message.get("content", "")
            if content:
                total += self.count(content)
            
            # Add overhead for role and message structure
            # Approximately 4 tokens per message for GPT models
            total += 4
        
        # Add 3 tokens for reply priming
        total += 3
        
        return total
    
    def truncate_to_limit(self, text: str, max_tokens: int) -> str:
        """
        Truncate text to fit within token limit.
        
        :param text: Input text
        :param max_tokens: Maximum tokens allowed
        :return: Truncated text
        """
        if self.count(text) <= max_tokens:
            return text
        
        # Binary search for optimal truncation point
        low, high = 0, len(text)
        
        while low < high:
            mid = (low + high + 1) // 2
            if self.count(text[:mid]) <= max_tokens:
                low = mid
            else:
                high = mid - 1
        
        return text[:low]
    
    def fits_context(self, messages: list[dict], max_context: int) -> bool:
        """
        Check if messages fit within context window.
        
        :param messages: List of message dicts
        :param max_context: Maximum context size
        :return: True if messages fit
        """
        return self.count_messages(messages) <= max_context


def get_model_context_limit(model: str) -> int:
    """
    Get the context window size for a model.
    
    :param model: Model name
    :return: Context window size in tokens
    """
    model_lower = model.lower()
    
    # Known context limits
    limits = {
        "gpt-4": 8192,
        "gpt-4-32k": 32768,
        "gpt-4-turbo": 128000,
        "gpt-4o": 128000,
        "gpt-3.5-turbo": 16385,
        "gpt-3.5-turbo-16k": 16385,
        "llama3-70b-8192": 8192,
        "llama3-8b-8192": 8192,
        "llama-3.1-70b-versatile": 32768,
        "llama-3.1-8b-instant": 8192,
        "mixtral-8x7b-32768": 32768,
        "gemma-7b-it": 8192,
        "deepseek-chat": 32768,
        "deepseek-coder": 16384,
    }
    
    # Check for exact match
    if model_lower in limits:
        return limits[model_lower]
    
    # Check for partial matches
    for known_model, limit in limits.items():
        if known_model in model_lower or model_lower in known_model:
            return limit
    
    # Default to conservative limit
    return 4096
