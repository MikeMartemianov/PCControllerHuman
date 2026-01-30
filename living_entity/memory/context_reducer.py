"""
ContextReducer - Token management and context compression.
"""

import asyncio
from typing import Optional

from openai import AsyncOpenAI

from living_entity.utils.tokens import TokenCounter, get_model_context_limit
from living_entity.utils.logging import get_logger


COMPRESSION_PROMPT = """Сожми следующий диалог, сохранив ключевую информацию:
- Важные факты и решения
- Ключевые вопросы пользователя
- Результаты выполненных действий
- Контекст, необходимый для продолжения

Ответь кратким резюме на том же языке, что и диалог.

ДИАЛОГ:
{history}

РЕЗЮМЕ:"""


class ContextReducer:
    """
    Context compression and token management.
    
    Features:
    - Token count checking before LLM requests
    - History compression via LLM summarization
    - Configurable token limits per module
    """
    
    # Reserve tokens for system prompt and response
    RESERVED_TOKENS = 1500
    
    def __init__(
        self,
        client: AsyncOpenAI,
        model: str,
        max_context_tokens: Optional[int] = None,
        compression_threshold: float = 0.8,
    ):
        """
        Initialize the context reducer.
        
        :param client: AsyncOpenAI client for compression requests
        :param model: Model name for token counting and compression
        :param max_context_tokens: Maximum context tokens (auto-detected if None)
        :param compression_threshold: Trigger compression at this % of max tokens
        """
        self.client = client
        self.model = model
        self.logger = get_logger()
        
        # Auto-detect context limit if not provided
        if max_context_tokens is None:
            self.max_context_tokens = get_model_context_limit(model)
        else:
            self.max_context_tokens = max_context_tokens
        
        self.compression_threshold = compression_threshold
        self.token_counter = TokenCounter(model)
        
        # Calculate effective limit
        self.effective_limit = int(
            (self.max_context_tokens - self.RESERVED_TOKENS) * compression_threshold
        )
        
        self.logger.info(
            f"ContextReducer initialized: max={self.max_context_tokens}, "
            f"effective={self.effective_limit}",
            module="memory"
        )
    
    def count_tokens(self, messages: list[dict[str, str]]) -> int:
        """
        Count tokens in a message list.
        
        :param messages: List of message dicts
        :return: Token count
        """
        return self.token_counter.count_messages(messages)
    
    def needs_reduction(self, messages: list[dict[str, str]]) -> bool:
        """
        Check if messages need compression.
        
        :param messages: List of message dicts
        :return: True if compression is needed
        """
        token_count = self.count_tokens(messages)
        return token_count > self.effective_limit
    
    async def reduce(
        self,
        messages: list[dict[str, str]],
        preserve_last: int = 4,
    ) -> list[dict[str, str]]:
        """
        Reduce message history by compressing older messages.
        
        :param messages: List of message dicts
        :param preserve_last: Number of recent messages to preserve unchanged
        :return: Reduced message list
        """
        if not self.needs_reduction(messages):
            return messages
        
        self.logger.info("Compressing conversation history...", module="memory")
        
        # Separate system messages, old history, and recent messages
        system_messages = [m for m in messages if m["role"] == "system"]
        non_system = [m for m in messages if m["role"] != "system"]
        
        if len(non_system) <= preserve_last:
            # Not enough messages to compress
            return messages
        
        # Split into to-compress and to-preserve
        to_compress = non_system[:-preserve_last]
        to_preserve = non_system[-preserve_last:]
        
        # Format history for compression
        history_text = self._format_history(to_compress)
        
        # Request compression
        try:
            summary = await self._compress_history(history_text)
        except Exception as e:
            self.logger.error(f"Compression failed: {e}", module="memory")
            # Fallback: just truncate old messages
            return system_messages + to_preserve
        
        # Create new message list with summary
        summary_message = {
            "role": "system",
            "content": f"[Предыдущий контекст диалога]\n{summary}"
        }
        
        result = system_messages + [summary_message] + to_preserve
        
        old_tokens = self.count_tokens(messages)
        new_tokens = self.count_tokens(result)
        
        self.logger.info(
            f"Compressed history: {old_tokens} → {new_tokens} tokens",
            module="memory"
        )
        
        return result
    
    def _format_history(self, messages: list[dict[str, str]]) -> str:
        """Format messages into a readable history string."""
        lines = []
        for msg in messages:
            role = msg["role"].upper()
            content = msg["content"]
            lines.append(f"[{role}]: {content}")
        return "\n\n".join(lines)
    
    async def _compress_history(self, history: str) -> str:
        """Request LLM to compress history."""
        prompt = COMPRESSION_PROMPT.format(history=history)
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500,
        )
        
        return response.choices[0].message.content or ""
    
    def truncate_to_fit(
        self,
        messages: list[dict[str, str]],
        max_tokens: Optional[int] = None,
    ) -> list[dict[str, str]]:
        """
        Truncate messages to fit within token limit (without LLM).
        
        :param messages: List of message dicts
        :param max_tokens: Maximum tokens (uses effective_limit if None)
        :return: Truncated message list
        """
        limit = max_tokens or self.effective_limit
        
        # Always keep system messages
        system_messages = [m for m in messages if m["role"] == "system"]
        non_system = [m for m in messages if m["role"] != "system"]
        
        system_tokens = self.count_tokens(system_messages)
        available_tokens = limit - system_tokens
        
        # Keep adding messages from the end until we hit the limit
        kept_messages = []
        current_tokens = 0
        
        for msg in reversed(non_system):
            msg_tokens = self.token_counter.count(msg.get("content", "")) + 4
            if current_tokens + msg_tokens > available_tokens:
                break
            kept_messages.insert(0, msg)
            current_tokens += msg_tokens
        
        return system_messages + kept_messages
    
    async def smart_reduce(
        self,
        messages: list[dict[str, str]],
        preserve_last: int = 4,
        use_llm: bool = True,
    ) -> list[dict[str, str]]:
        """
        Intelligently reduce context using LLM when beneficial.
        
        :param messages: List of message dicts
        :param preserve_last: Number of recent messages to preserve
        :param use_llm: Whether to use LLM for compression
        :return: Reduced message list
        """
        if not self.needs_reduction(messages):
            return messages
        
        if use_llm:
            try:
                return await self.reduce(messages, preserve_last)
            except Exception as e:
                self.logger.warning(
                    f"LLM compression failed, using truncation: {e}",
                    module="memory"
                )
        
        # Fallback to simple truncation
        return self.truncate_to_fit(messages)
