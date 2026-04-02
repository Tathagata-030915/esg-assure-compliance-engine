"""
LLM Client — Factory Pattern with Circuit Breaker & Exponential Backoff.

WHY THIS EXISTS (Interview Talking Point):
    The original notebook code had a bare try/except that returned error
    strings as audit memos — silently corrupting the output. There was no
    retry logic, no rate limiting beyond a naive sleep(1.5), and the API
    key was hardcoded in the notebook cell.

    This module implements:
    - Factory Pattern: LLMClientFactory abstracts the provider (Groq/OpenAI/local)
    - Exponential Backoff with Jitter: Prevents thundering herd on rate limits
    - Circuit Breaker: After N consecutive failures, stops hammering the API
    - Structured error handling: Custom exceptions, not string returns

Design Patterns Used:
    - Factory Pattern: Provider-agnostic LLM client creation
    - Circuit Breaker: Resilience pattern for external service calls
    - Decorator Pattern: Retry logic wraps the core call
"""

from __future__ import annotations

import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from src.config import Settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


# ─── Custom Exceptions ───────────────────────────────────────────────────────

class LLMError(Exception):
    """Base exception for LLM-related errors."""
    pass


class LLMRateLimitError(LLMError):
    """Raised when we hit API rate limits."""
    pass


class LLMCircuitOpenError(LLMError):
    """Raised when the circuit breaker is open (too many failures)."""
    pass


class LLMResponseError(LLMError):
    """Raised when the LLM returns an unparseable/invalid response."""
    pass


# ─── Circuit Breaker ─────────────────────────────────────────────────────────

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing — reject all calls
    HALF_OPEN = "half_open" # Testing — allow one call through


@dataclass
class CircuitBreaker:
    """
    Circuit Breaker pattern for LLM API calls.

    States:
    - CLOSED: Normal operation, calls go through.
    - OPEN: Too many failures, all calls rejected for `reset_timeout` seconds.
    - HALF_OPEN: After timeout, allow one trial call. If it succeeds, close.
    """
    failure_threshold: int = 5
    reset_timeout: float = 30.0

    def __post_init__(self) -> None:
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            # Check if timeout has elapsed
            if (
                self._last_failure_time is not None
                and time.time() - self._last_failure_time >= self.reset_timeout
            ):
                self._state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker transitioning to HALF_OPEN")
        return self._state

    def record_success(self) -> None:
        """Reset failure count on successful call."""
        self._failure_count = 0
        self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        """Increment failure count; open circuit if threshold exceeded."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning(
                f"Circuit breaker OPEN after {self._failure_count} failures. "
                f"Will retry in {self.reset_timeout}s."
            )

    def allow_request(self) -> bool:
        """Check if a request should be allowed through."""
        current_state = self.state  # Triggers timeout check
        if current_state == CircuitState.CLOSED:
            return True
        elif current_state == CircuitState.HALF_OPEN:
            return True  # Allow one test request
        else:
            return False


# ─── LLM Client Protocol ────────────────────────────────────────────────────

class BaseLLMClient(ABC):
    """Abstract base for LLM providers."""

    @abstractmethod
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Send a prompt and return the completion text."""
        ...


# ─── Groq Client Implementation ─────────────────────────────────────────────

class GroqLLMClient(BaseLLMClient):
    """
    Groq-specific LLM client wrapping the groq Python SDK.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._config = settings.llm

        try:
            from groq import Groq
            self._client = Groq(api_key=self._config.api_key)
        except ImportError:
            raise LLMError(
                "groq package not installed. Run: pip install groq"
            )

        if not self._config.api_key:
            raise LLMError(
                "GROQ_API_KEY not set. Copy .env.example to .env "
                "and add your API key."
            )

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Raw completion call — no retry logic here."""
        completion = self._client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            model=self._config.model,
            temperature=self._config.temperature,
        )
        return completion.choices[0].message.content


# ─── Resilient LLM Client (with retry + circuit breaker) ────────────────────

class ResilientLLMClient:
    """
    Wraps a BaseLLMClient with retry logic, exponential backoff,
    and circuit breaker protection.

    This is the client that the rest of the application should use.

    Usage:
        settings = Settings.get_instance()
        client = LLMClientFactory.create(settings)
        response = client.call("system prompt", "user prompt")
    """

    def __init__(
        self,
        client: BaseLLMClient,
        max_retries: int = 3,
        base_delay: float = 1.5,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ) -> None:
        self._client = client
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._circuit_breaker = circuit_breaker or CircuitBreaker()

    def call(self, system_prompt: str, user_prompt: str) -> str:
        """
        Make an LLM call with retry, backoff, and circuit breaker.

        Raises:
            LLMCircuitOpenError: If circuit breaker is open
            LLMError: If all retries exhausted
        """
        if not self._circuit_breaker.allow_request():
            raise LLMCircuitOpenError(
                "Circuit breaker is OPEN. Too many consecutive failures."
            )

        last_exception: Optional[Exception] = None

        for attempt in range(1, self._max_retries + 1):
            try:
                response = self._client.complete(system_prompt, user_prompt)
                self._circuit_breaker.record_success()
                return response

            except Exception as e:
                last_exception = e
                self._circuit_breaker.record_failure()

                if attempt < self._max_retries:
                    # Exponential backoff with jitter
                    delay = self._base_delay * (2 ** (attempt - 1))
                    jitter = random.uniform(0, delay * 0.1)
                    wait_time = delay + jitter

                    logger.warning(
                        f"LLM call failed (attempt {attempt}/{self._max_retries}): "
                        f"{e}. Retrying in {wait_time:.2f}s..."
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(
                        f"LLM call failed after {self._max_retries} attempts: {e}"
                    )

        raise LLMError(
            f"All {self._max_retries} attempts failed. "
            f"Last error: {last_exception}"
        )


# ─── Factory ─────────────────────────────────────────────────────────────────

class LLMClientFactory:
    """
    Factory for creating configured LLM clients.

    Currently supports: Groq
    Easily extensible to OpenAI, Anthropic, local models, etc.
    """

    @staticmethod
    def create(settings: Optional[Settings] = None) -> ResilientLLMClient:
        """
        Create a production-ready LLM client with retry and circuit breaker.

        Args:
            settings: Application settings (uses singleton if None)

        Returns:
            ResilientLLMClient wrapping the configured provider
        """
        if settings is None:
            settings = Settings.get_instance()

        # Currently only Groq is implemented
        # Future: switch on settings.llm.provider
        base_client = GroqLLMClient(settings)

        return ResilientLLMClient(
            client=base_client,
            max_retries=settings.llm.max_retries,
            base_delay=settings.llm.rate_limit_delay,
        )
