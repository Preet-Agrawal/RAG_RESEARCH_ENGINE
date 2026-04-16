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
    "groq": 2.1,       # ~30 req/min free tier
    "openai": 0.1,
    "anthropic": 0.2,
}


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
        elif self.provider == "anthropic":
            response = self._generate_anthropic(prompt, system_prompt, temperature, max_tokens)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

        latency = time.time() - start_time
        response.latency = latency
        return response

    def _generate_openai(self, prompt: str, system_prompt: Optional[str],
                         temperature: float, max_tokens: int) -> LLMResponse:
        """Generate response using OpenAI API."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )

        return LLMResponse(
            text=response.choices[0].message.content,
            model=self.model,
            tokens_used=response.usage.total_tokens,
            latency=0.0,  # Will be set by caller
            metadata={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "finish_reason": response.choices[0].finish_reason
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
