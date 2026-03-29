from __future__ import annotations

import os
from collections.abc import AsyncIterator
from enum import Enum
from typing import Any

import structlog
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = structlog.get_logger(__name__)


class LLMProviderType(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class LLMProviderConfig(BaseModel):
    """Configuration for an LLM backend."""

    provider: LLMProviderType = LLMProviderType.OPENAI
    model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 4096
    api_key: str | None = None
    base_url: str | None = None
    default_system_prompt: str | None = None


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatResponse(BaseModel):
    content: str
    model: str
    usage: TokenUsage | None = None
    finish_reason: str | None = None


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class RateLimiter:
    """Simple token-bucket style rate limiter tracking requests per minute."""

    def __init__(self, max_requests_per_minute: int = 60) -> None:
        self.max_rpm = max_requests_per_minute
        self._timestamps: list[float] = []

    async def acquire(self) -> None:
        import asyncio
        import time

        now = time.monotonic()
        self._timestamps = [t for t in self._timestamps if now - t < 60.0]
        if len(self._timestamps) >= self.max_rpm:
            sleep_for = 60.0 - (now - self._timestamps[0])
            logger.warning("rate_limiter.throttling", sleep_seconds=round(sleep_for, 2))
            await asyncio.sleep(sleep_for)
        self._timestamps.append(time.monotonic())


_RETRIABLE_OPENAI: tuple[type[Exception], ...] = ()
_RETRIABLE_ANTHROPIC: tuple[type[Exception], ...] = ()

try:
    import openai as _openai_mod

    _RETRIABLE_OPENAI = (
        _openai_mod.APIConnectionError,
        _openai_mod.RateLimitError,
        _openai_mod.InternalServerError,
    )
except ImportError:
    pass

try:
    import anthropic as _anthropic_mod

    _RETRIABLE_ANTHROPIC = (
        _anthropic_mod.APIConnectionError,
        _anthropic_mod.RateLimitError,
        _anthropic_mod.InternalServerError,
    )
except ImportError:
    pass

_ALL_RETRIABLE = _RETRIABLE_OPENAI + _RETRIABLE_ANTHROPIC


class LLMProvider:
    """Unified async interface to OpenAI and Anthropic chat APIs."""

    def __init__(self, config: LLMProviderConfig) -> None:
        self.config = config
        self._rate_limiter = RateLimiter()
        self._log = logger.bind(provider=config.provider.value, model=config.model)
        self._openai_client: Any = None
        self._anthropic_client: Any = None
        self._init_client()

    def _init_client(self) -> None:
        if self.config.provider == LLMProviderType.OPENAI:
            import openai

            self._openai_client = openai.AsyncOpenAI(
                api_key=self.config.api_key or os.getenv("OPENAI_API_KEY"),
                base_url=self.config.base_url,
            )
        else:
            import anthropic

            self._anthropic_client = anthropic.AsyncAnthropic(
                api_key=self.config.api_key or os.getenv("ANTHROPIC_API_KEY"),
            )

    @retry(
        retry=retry_if_exception_type(_ALL_RETRIABLE) if _ALL_RETRIABLE else retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        reraise=True,
    )
    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        system_prompt: str | None = None,
    ) -> ChatResponse:
        await self._rate_limiter.acquire()

        temp = temperature if temperature is not None else self.config.temperature
        max_tok = max_tokens or self.config.max_tokens
        sys_prompt = system_prompt or self.config.default_system_prompt

        if self.config.provider == LLMProviderType.OPENAI:
            return await self._chat_openai(messages, temp, max_tok, sys_prompt)
        return await self._chat_anthropic(messages, temp, max_tok, sys_prompt)

    async def _chat_openai(
        self,
        messages: list[ChatMessage],
        temperature: float,
        max_tokens: int,
        system_prompt: str | None,
    ) -> ChatResponse:
        oai_messages: list[dict[str, str]] = []
        if system_prompt:
            oai_messages.append({"role": "system", "content": system_prompt})
        oai_messages.extend(m.model_dump() for m in messages)

        self._log.debug("llm.request", message_count=len(oai_messages))
        resp = await self._openai_client.chat.completions.create(
            model=self.config.model,
            messages=oai_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        choice = resp.choices[0]
        usage = TokenUsage(
            prompt_tokens=resp.usage.prompt_tokens,
            completion_tokens=resp.usage.completion_tokens,
            total_tokens=resp.usage.total_tokens,
        ) if resp.usage else None

        self._log.debug("llm.response", tokens=usage.total_tokens if usage else 0)
        return ChatResponse(
            content=choice.message.content or "",
            model=resp.model,
            usage=usage,
            finish_reason=choice.finish_reason,
        )

    async def _chat_anthropic(
        self,
        messages: list[ChatMessage],
        temperature: float,
        max_tokens: int,
        system_prompt: str | None,
    ) -> ChatResponse:
        anth_messages = [{"role": m.role, "content": m.content} for m in messages]

        kwargs: dict[str, Any] = {
            "model": self.config.model,
            "messages": anth_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        self._log.debug("llm.request", message_count=len(anth_messages))
        resp = await self._anthropic_client.messages.create(**kwargs)
        content = resp.content[0].text if resp.content else ""
        usage = TokenUsage(
            prompt_tokens=resp.usage.input_tokens,
            completion_tokens=resp.usage.output_tokens,
            total_tokens=resp.usage.input_tokens + resp.usage.output_tokens,
        )

        self._log.debug("llm.response", tokens=usage.total_tokens)
        return ChatResponse(
            content=content,
            model=resp.model,
            usage=usage,
            finish_reason=resp.stop_reason or "end_turn",
        )

    async def chat_stream(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        system_prompt: str | None = None,
    ) -> AsyncIterator[str]:
        await self._rate_limiter.acquire()

        temp = temperature if temperature is not None else self.config.temperature
        max_tok = max_tokens or self.config.max_tokens
        sys_prompt = system_prompt or self.config.default_system_prompt

        if self.config.provider == LLMProviderType.OPENAI:
            async for chunk in self._stream_openai(messages, temp, max_tok, sys_prompt):
                yield chunk
        else:
            async for chunk in self._stream_anthropic(messages, temp, max_tok, sys_prompt):
                yield chunk

    async def _stream_openai(
        self,
        messages: list[ChatMessage],
        temperature: float,
        max_tokens: int,
        system_prompt: str | None,
    ) -> AsyncIterator[str]:
        oai_messages: list[dict[str, str]] = []
        if system_prompt:
            oai_messages.append({"role": "system", "content": system_prompt})
        oai_messages.extend(m.model_dump() for m in messages)

        stream = await self._openai_client.chat.completions.create(
            model=self.config.model,
            messages=oai_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content

    async def _stream_anthropic(
        self,
        messages: list[ChatMessage],
        temperature: float,
        max_tokens: int,
        system_prompt: str | None,
    ) -> AsyncIterator[str]:
        anth_messages = [{"role": m.role, "content": m.content} for m in messages]
        kwargs: dict[str, Any] = {
            "model": self.config.model,
            "messages": anth_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        async with self._anthropic_client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield text

    def estimate_tokens(self, text: str) -> int:
        """Rough token estimate (~4 chars per token) for budget checks."""
        return max(1, len(text) // 4)
