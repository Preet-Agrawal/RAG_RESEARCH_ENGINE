"""
LLM client for interacting with various language model providers.
"""
from typing import Optional, Dict, Any, List
import time
from dataclasses import dataclass

# Optional imports - only needed if using specific providers
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


@dataclass
class LLMResponse:
    """Standardized response from LLM."""
    text: str
    model: str
    tokens_used: int
    latency: float
    metadata: Dict[str, Any]


_RATE_LIMITS = {
    "groq": 0.0,       # Let API reject with 429; we fail over instantly
    "openai": 0.0,
    "anthropic": 0.0,
    "gemini": 0.0,
}


def _is_rate_limit_error(err: Exception) -> bool:
    """Detect rate-limit / quota-exhausted errors across providers."""
    msg = str(err).lower()
    return (
        "429" in msg
        or "rate_limit" in msg
        or "rate limit" in msg
        or "quota" in msg
        or "resource_exhausted" in msg
        or "resource exhausted" in msg
        or "too many requests" in msg
    )


class LLMClient:
    """Unified client for multiple LLM providers."""

    def __init__(self, provider: str = "groq", model: str = "llama3-8b-8192",
                 temperature: float = 0.0, max_tokens: int = 4096, api_key: Optional[str] = None,
                 rate_limit: Optional[float] = None):
        self.provider = provider
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._min_interval = rate_limit if rate_limit is not None else _RATE_LIMITS.get(provider, 0.0)
        self._last_request_time = 0.0

        if provider == "openai":
            if not OPENAI_AVAILABLE:
                raise ImportError("OpenAI library not installed. Install it with: pip install openai")
            self.client = openai.OpenAI(api_key=api_key)
        elif provider == "groq":
            if not OPENAI_AVAILABLE:
                raise ImportError("OpenAI library not installed. Install it with: pip install openai")
            self.client = openai.OpenAI(
                api_key=api_key,
                base_url="https://api.groq.com/openai/v1"
            )
        elif provider == "gemini":
            if not OPENAI_AVAILABLE:
                raise ImportError("OpenAI library not installed. Install it with: pip install openai")
            # Google Gemini via OpenAI-compatible endpoint
            self.client = openai.OpenAI(
                api_key=api_key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
            )
        elif provider == "anthropic":
            if not ANTHROPIC_AVAILABLE:
                raise ImportError("Anthropic library not installed. Install it with: pip install anthropic")
            self.client = Anthropic(api_key=api_key)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def generate(self, prompt: str, system_prompt: Optional[str] = None,
                 **kwargs) -> LLMResponse:
        """
        Generate response from LLM.

        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)
            **kwargs: Additional parameters to override defaults

        Returns:
            LLMResponse object
        """
        # Rate limiting: wait if needed to respect provider limits
        if self._min_interval > 0:
            elapsed = time.time() - self._last_request_time
            if elapsed < self._min_interval:
                time.sleep(self._min_interval - elapsed)

        start_time = time.time()
        self._last_request_time = start_time

        temperature = kwargs.get('temperature', self.temperature)
        max_tokens = kwargs.get('max_tokens', self.max_tokens)

        if self.provider == "openai":
            response = self._generate_openai(prompt, system_prompt, temperature, max_tokens)
        elif self.provider == "groq":
            response = self._generate_openai(prompt, system_prompt, temperature, max_tokens)
        elif self.provider == "gemini":
            response = self._generate_openai(prompt, system_prompt, temperature, max_tokens)
        elif self.provider == "anthropic":
            response = self._generate_anthropic(prompt, system_prompt, temperature, max_tokens)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

        latency = time.time() - start_time
        response.latency = latency
        return response

    def _generate_openai(self, prompt: str, system_prompt: Optional[str],
                         temperature: float, max_tokens: int) -> LLMResponse:
        """Generate response using OpenAI API (or OpenAI-compatible endpoint)."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Gemini 2.5 uses thinking tokens that count against max_tokens —
        # give it more headroom so it can complete reasoning + output.
        effective_max = max_tokens * 3 if self.provider == "gemini" else max_tokens

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=effective_max
        )

        # Guard against None content (happens when Gemini exhausts
        # max_tokens on thinking before producing output text)
        content = response.choices[0].message.content or ""
        finish_reason = response.choices[0].finish_reason

        if not content and finish_reason == "length":
            content = "[Response was cut off before completion. Try increasing max_tokens.]"

        return LLMResponse(
            text=content,
            model=self.model,
            tokens_used=response.usage.total_tokens if response.usage else 0,
            latency=0.0,
            metadata={
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "finish_reason": finish_reason
            }
        )

    def _generate_anthropic(self, prompt: str, system_prompt: Optional[str],
                            temperature: float, max_tokens: int) -> LLMResponse:
        """Generate response using Anthropic API."""
        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}]
        }

        if system_prompt:
            kwargs["system"] = system_prompt

        response = self.client.messages.create(**kwargs)

        return LLMResponse(
            text=response.content[0].text,
            model=self.model,
            tokens_used=response.usage.input_tokens + response.usage.output_tokens,
            latency=0.0,  # Will be set by caller
            metadata={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "stop_reason": response.stop_reason
            }
        )

    def batch_generate(self, prompts: List[str], system_prompt: Optional[str] = None,
                       **kwargs) -> List[LLMResponse]:
        """Generate responses for multiple prompts."""
        responses = []
        for prompt in prompts:
            response = self.generate(prompt, system_prompt, **kwargs)
            responses.append(response)
        return responses


class ResilientLLMClient:
    """
    Wraps multiple LLMClient instances and automatically fails over on errors.

    If the primary client hits a rate limit or quota error, this wrapper
    instantly switches to the next client in the chain — no waiting, no latency.

    Once a client fails, later calls stick with the working one (sticky switch)
    until it also fails. This avoids re-trying a known-rate-limited client on
    every call.
    """

    def __init__(self, clients: List["LLMClient"]):
        if not clients:
            raise ValueError("ResilientLLMClient requires at least one client")
        self.clients = clients
        self._active_idx = 0  # which client to try first

    @property
    def provider(self) -> str:
        return self.clients[self._active_idx].provider

    @property
    def model(self) -> str:
        return self.clients[self._active_idx].model

    def generate(self, prompt: str, system_prompt: Optional[str] = None,
                 **kwargs) -> LLMResponse:
        """
        Try active client first, then fall through the chain on failures.

        Fails over on ANY error (rate-limit, auth, service unavailable,
        transient network issue). Only raises if every provider in the
        chain fails. This gives Groq ↔ Gemini true redundancy.
        """
        last_error = None
        n = len(self.clients)

        # Try all clients, starting from the currently-active one
        for offset in range(n):
            idx = (self._active_idx + offset) % n
            client = self.clients[idx]
            try:
                response = client.generate(prompt, system_prompt, **kwargs)
                # Success — stick with this client for next call
                if idx != self._active_idx:
                    self._active_idx = idx
                return response
            except Exception as e:
                last_error = e
                # Try the next provider/model — no artificial wait
                continue

        # Every provider failed — surface the last error
        raise last_error

    def batch_generate(self, prompts: List[str], system_prompt: Optional[str] = None,
                       **kwargs) -> List[LLMResponse]:
        return [self.generate(p, system_prompt, **kwargs) for p in prompts]
