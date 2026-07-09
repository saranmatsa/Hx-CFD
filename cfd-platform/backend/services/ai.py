"""
AI service layer with provider abstraction.
Supports multiple AI providers: NIM, OpenAI, Anthropic, Ollama, LM Studio.
"""

import os
import json
from typing import Dict, Any, Optional, List, Callable, AsyncIterator
from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import structlog

from core.config import get_settings
from core.errors import AIError, ConfigurationError
from core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class AIProviderType(str, Enum):
    """Supported AI provider types."""
    NIM = "nim"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    LM_STUDIO = "lm_studio"
    GROQ = "groq"
    GEMINI = "gemini"


@dataclass
class Message:
    """Chat message."""
    role: str  # "user", "assistant", "system"
    content: str
    name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChatCompletion:
    """Chat completion response."""
    content: str
    model: str
    provider: AIProviderType
    usage: Dict[str, int] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StreamChunk:
    """Streaming response chunk."""
    content: str
    done: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseAIProvider(ABC):
    """Abstract base class for AI providers."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the provider.
        
        Args:
            config: Provider configuration
        """
        self.config = config
        self._logger = logger.bind(provider=self.__class__.__name__)

    @abstractmethod
    async def chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> ChatCompletion:
        """
        Send a chat completion request.
        
        Args:
            messages: List of chat messages
            model: Model to use (provider-specific)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Chat completion response
        """
        pass

    @abstractmethod
    async def stream(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> AsyncIterator[StreamChunk]:
        """
        Send a streaming chat completion request.
        
        Args:
            messages: List of chat messages
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Yields:
            Stream chunks
        """
        pass

    @abstractmethod
    def list_models(self) -> List[str]:
        """List available models."""
        pass

    def validate_config(self) -> bool:
        """Validate provider configuration."""
        return True


class NIMProvider(BaseAIProvider):
    """NVIDIA NIM provider."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key") or os.environ.get("NIM_API_KEY", "")
        self.base_url = config.get("base_url", "https://integrate.api.nvidia.com/v1")

    def validate_config(self) -> bool:
        """Validate NIM configuration."""
        if not self.api_key:
            self._logger.warning("NIM API key not configured")
            return False
        return True

    async def chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> ChatCompletion:
        """Send chat completion to NIM."""
        import httpx
        
        model = model or self.config.get("model", "meta/llama-3.1-70b-instruct")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens or 4096,
            **kwargs,
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            
            if response.status_code != 200:
                raise AIError(f"NIM API error: {response.text}")
            
            data = response.json()
            
            return ChatCompletion(
                content=data["choices"][0]["message"]["content"],
                model=model,
                provider=AIProviderType.NIM,
                usage=data.get("usage", {}),
            )

    async def stream(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> AsyncIterator[StreamChunk]:
        """Send streaming chat completion to NIM."""
        import httpx
        
        model = model or self.config.get("model", "meta/llama-3.1-70b-instruct")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens or 4096,
            "stream": True,
            **kwargs,
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        if data.get("choices"):
                            content = data["choices"][0].get("delta", {}).get("content", "")
                            if content:
                                yield StreamChunk(content=content)
                        elif data.get("error"):
                            raise AIError(f"NIM streaming error: {data['error']}")
                
                yield StreamChunk(content="", done=True)

    def list_models(self) -> List[str]:
        """List available NIM models."""
        return [
            "meta/llama-3.1-70b-instruct",
            "meta/llama-3.1-405b-instruct",
            "mistralai/mixtral-8x7b-instruct-v0.1",
            "nvidia/nemotron-4-340b-instruct",
        ]


class OpenAIProvider(BaseAIProvider):
    """OpenAI provider."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key") or os.environ.get("OPENAI_API_KEY", "")
        self.base_url = config.get("base_url", "https://api.openai.com/v1")

    def validate_config(self) -> bool:
        """Validate OpenAI configuration."""
        if not self.api_key:
            self._logger.warning("OpenAI API key not configured")
            return False
        return True

    async def chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> ChatCompletion:
        """Send chat completion to OpenAI."""
        import httpx
        
        model = model or self.config.get("model", "gpt-4o")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens or 4096,
            **kwargs,
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            
            if response.status_code != 200:
                raise AIError(f"OpenAI API error: {response.text}")
            
            data = response.json()
            
            return ChatCompletion(
                content=data["choices"][0]["message"]["content"],
                model=model,
                provider=AIProviderType.OPENAI,
                usage=data.get("usage", {}),
            )

    async def stream(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> AsyncIterator[StreamChunk]:
        """Send streaming chat completion to OpenAI."""
        import httpx
        
        model = model or self.config.get("model", "gpt-4o")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens or 4096,
            "stream": True,
            **kwargs,
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        if data.get("choices"):
                            content = data["choices"][0].get("delta", {}).get("content", "")
                            if content:
                                yield StreamChunk(content=content)
                        elif "error" in data:
                            raise AIError(f"OpenAI streaming error: {data['error']}")
                
                yield StreamChunk(content="", done=True)

    def list_models(self) -> List[str]:
        """List available OpenAI models."""
        return [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
        ]


class AnthropicProvider(BaseAIProvider):
    """Anthropic Claude provider."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key") or os.environ.get("ANTHROPIC_API_KEY", "")
        self.base_url = config.get("base_url", "https://api.anthropic.com/v1")

    def validate_config(self) -> bool:
        """Validate Anthropic configuration."""
        if not self.api_key:
            self._logger.warning("Anthropic API key not configured")
            return False
        return True

    async def chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> ChatCompletion:
        """Send chat completion to Anthropic."""
        import httpx
        
        model = model or self.config.get("model", "claude-sonnet-4-20250514")
        
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        
        # Anthropic uses system message separately
        system_message = ""
        anthropic_messages = []
        for msg in messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                anthropic_messages.append({"role": msg.role, "content": msg.content})
        
        payload = {
            "model": model,
            "messages": anthropic_messages,
            "temperature": temperature,
            "max_tokens": max_tokens or 4096,
        }
        
        if system_message:
            payload["system"] = system_message
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/messages",
                headers=headers,
                json=payload,
            )
            
            if response.status_code != 200:
                raise AIError(f"Anthropic API error: {response.text}")
            
            data = response.json()
            
            return ChatCompletion(
                content=data["content"][0]["text"],
                model=model,
                provider=AIProviderType.ANTHROPIC,
                usage={
                    "input_tokens": data.get("usage", {}).get("input_tokens", 0),
                    "output_tokens": data.get("usage", {}).get("output_tokens", 0),
                },
            )

    async def stream(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> AsyncIterator[StreamChunk]:
        """Send streaming chat completion to Anthropic."""
        import httpx
        
        model = model or self.config.get("model", "claude-sonnet-4-20250514")
        
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        
        system_message = ""
        anthropic_messages = []
        for msg in messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                anthropic_messages.append({"role": msg.role, "content": msg.content})
        
        payload = {
            "model": model,
            "messages": anthropic_messages,
            "temperature": temperature,
            "max_tokens": max_tokens or 4096,
            "stream": True,
        }
        
        if system_message:
            payload["system"] = system_message
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/messages",
                headers=headers,
                json=payload,
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        if data.get("type") == "content_block_delta":
                            content = data.get("delta", {}).get("text", "")
                            if content:
                                yield StreamChunk(content=content)
                        elif data.get("type") == "error":
                            raise AIError(f"Anthropic streaming error: {data}")
                
                yield StreamChunk(content="", done=True)

    def list_models(self) -> List[str]:
        """List available Anthropic models."""
        return [
            "claude-opus-4-20250514",
            "claude-sonnet-4-20250514",
            "claude-3-5-sonnet-20241022",
            "claude-3-opus-20240229",
        ]


class OllamaProvider(BaseAIProvider):
    """Ollama local provider."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get("base_url", "http://localhost:11434")

    def validate_config(self) -> bool:
        """Validate Ollama configuration."""
        import httpx
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            self._logger.warning("Ollama not reachable")
            return False

    async def chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> ChatCompletion:
        """Send chat completion to Ollama."""
        import httpx
        
        model = model or self.config.get("model", "llama3.1")
        
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json=payload,
            )
            
            if response.status_code != 200:
                raise AIError(f"Ollama API error: {response.text}")
            
            data = response.json()
            
            return ChatCompletion(
                content=data["message"]["content"],
                model=model,
                provider=AIProviderType.OLLAMA,
            )

    async def stream(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> AsyncIterator[StreamChunk]:
        """Send streaming chat completion to Ollama."""
        import httpx
        
        model = model or self.config.get("model", "llama3.1")
        
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json=payload,
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        data = json.loads(line)
                        content = data.get("message", {}).get("content", "")
                        if content:
                            yield StreamChunk(content=content)
                        if data.get("done"):
                            yield StreamChunk(content="", done=True)
                            break

    def list_models(self) -> List[str]:
        """List available Ollama models."""
        import httpx
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    return [m["name"] for m in data.get("models", [])]
        except Exception:
            pass
        return []


class LMStudioProvider(BaseAIProvider):
    """LM Studio local provider."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get("base_url", "http://localhost:1234/v1")

    def validate_config(self) -> bool:
        """Validate LM Studio configuration."""
        import httpx
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.base_url}/models")
                return response.status_code == 200
        except Exception:
            self._logger.warning("LM Studio not reachable")
            return False

    async def chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> ChatCompletion:
        """Send chat completion to LM Studio."""
        import httpx
        
        model = model or self.config.get("model", "local-model")
        
        headers = {"Content-Type": "application/json"}
        
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens or 4096,
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            
            if response.status_code != 200:
                raise AIError(f"LM Studio API error: {response.text}")
            
            data = response.json()
            
            return ChatCompletion(
                content=data["choices"][0]["message"]["content"],
                model=model,
                provider=AIProviderType.LM_STUDIO,
            )

    async def stream(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> AsyncIterator[StreamChunk]:
        """Send streaming chat completion to LM Studio."""
        import httpx
        
        model = model or self.config.get("model", "local-model")
        
        headers = {"Content-Type": "application/json"}
        
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens or 4096,
            "stream": True,
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        if data.get("choices"):
                            content = data["choices"][0].get("delta", {}).get("content", "")
                            if content:
                                yield StreamChunk(content=content)
                        elif "error" in data:
                            raise AIError(f"LM Studio streaming error: {data['error']}")
                
                yield StreamChunk(content="", done=True)

    def list_models(self) -> List[str]:
        """List available LM Studio models."""
        import httpx
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.base_url}/models")
                if response.status_code == 200:
                    data = response.json()
                    return [m["id"] for m in data.get("data", [])]
        except Exception:
            pass
        return []


class GroqProvider(BaseAIProvider):
    """Groq provider for fast inference."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key") or os.environ.get("GROQ_API_KEY", "")
        self.base_url = config.get("base_url", "https://api.groq.com/openai/v1")

    def validate_config(self) -> bool:
        """Validate Groq configuration."""
        if not self.api_key:
            self._logger.warning("Groq API key not configured")
            return False
        return True

    async def chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> ChatCompletion:
        """Send chat completion to Groq."""
        import httpx
        
        model = model or self.config.get("model", "llama-3.1-70b-versatile")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens or 4096,
            **kwargs,
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            
            if response.status_code != 200:
                raise AIError(f"Groq API error: {response.text}")
            
            data = response.json()
            
            return ChatCompletion(
                content=data["choices"][0]["message"]["content"],
                model=model,
                provider=AIProviderType.GROQ,
                usage=data.get("usage", {}),
            )

    async def stream(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> AsyncIterator[StreamChunk]:
        """Send streaming chat completion to Groq."""
        import httpx
        
        model = model or self.config.get("model", "llama-3.1-70b-versatile")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens or 4096,
            "stream": True,
            **kwargs,
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        if data.get("choices"):
                            content = data["choices"][0].get("delta", {}).get("content", "")
                            if content:
                                yield StreamChunk(content=content)
                        elif "error" in data:
                            raise AIError(f"Groq streaming error: {data['error']}")
                
                yield StreamChunk(content="", done=True)

    def list_models(self) -> List[str]:
        """List available Groq models."""
        return [
            "llama-3.1-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
            "gemma2-9b-it",
        ]


class GeminiProvider(BaseAIProvider):
    """Google Gemini provider."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key") or os.environ.get("GEMINI_API_KEY", "")
        self.base_url = config.get("base_url", "https://generativelanguage.googleapis.com/v1beta")

    def validate_config(self) -> bool:
        """Validate Gemini configuration."""
        if not self.api_key:
            self._logger.warning("Gemini API key not configured")
            return False
        return True

    async def chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> ChatCompletion:
        """Send chat completion to Gemini."""
        import httpx
        
        model = model or self.config.get("model", "gemini-1.5-flash")
        # Convert model name to Gemini format
        gemini_model = model if model.startswith("models/") else f"models/{model}"
        
        # Convert messages to Gemini format
        contents = []
        for msg in messages:
            if msg.role == "user":
                contents.append({"role": "user", "parts": [{"text": msg.content}]})
            elif msg.role == "assistant":
                contents.append({"role": "model", "parts": [{"text": msg.content}]})
        
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens or 2048,
            },
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/{gemini_model}:generateContent?key={self.api_key}",
                json=payload,
            )
            
            if response.status_code != 200:
                raise AIError(f"Gemini API error: {response.text}")
            
            data = response.json()
            content = data["candidates"][0]["content"]["parts"][0]["text"]
            
            return ChatCompletion(
                content=content,
                model=model,
                provider=AIProviderType.GEMINI,
                usage={
                    "prompt_tokens": data.get("usageMetadata", {}).get("promptTokenCount", 0),
                    "completion_tokens": data.get("usageMetadata", {}).get("candidatesTokenCount", 0),
                },
            )

    async def stream(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> AsyncIterator[StreamChunk]:
        """Send streaming chat completion to Gemini."""
        import httpx
        
        model = model or self.config.get("model", "gemini-1.5-flash")
        gemini_model = model if model.startswith("models/") else f"models/{model}"
        
        contents = []
        for msg in messages:
            if msg.role == "user":
                contents.append({"role": "user", "parts": [{"text": msg.content}]})
            elif msg.role == "assistant":
                contents.append({"role": "model", "parts": [{"text": msg.content}]})
        
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens or 2048,
            },
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/{gemini_model}:streamGenerateContent?key={self.api_key}",
                json=payload,
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if content := data.get("candidates"):
                                text = content[0]["content"]["parts"][0].get("text", "")
                                if text:
                                    yield StreamChunk(content=text)
                        except json.JSONDecodeError:
                            continue
                
                yield StreamChunk(content="", done=True)

    def list_models(self) -> List[str]:
        """List available Gemini models."""
        return [
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "gemini-1.5-flash-8b",
            "gemini-2.0-flash-exp",
            "gemini-exp-1206",
        ]


class AIService:
    """
    AI service providing a unified interface for all providers.
    """

    def __init__(self):
        self._providers: Dict[AIProviderType, BaseAIProvider] = {}
        self._default_provider: Optional[AIProviderType] = None
        self._logger = logger.bind(service="AIService")
        self._initialize_providers()

    def _initialize_providers(self) -> None:
        """Initialize configured providers."""
        # Initialize NIM
        if nim_config := settings.AI_PROVIDERS.get("nim"):
            try:
                self._providers[AIProviderType.NIM] = NIMProvider(nim_config)
                if self._default_provider is None:
                    self._default_provider = AIProviderType.NIM
            except Exception as e:
                self._logger.warning("failed_to_initialize_nim", error=str(e))

        # Initialize OpenAI
        if openai_config := settings.AI_PROVIDERS.get("openai"):
            try:
                self._providers[AIProviderType.OPENAI] = OpenAIProvider(openai_config)
                if self._default_provider is None:
                    self._default_provider = AIProviderType.OPENAI
            except Exception as e:
                self._logger.warning("failed_to_initialize_openai", error=str(e))

        # Initialize Anthropic
        if anthropic_config := settings.AI_PROVIDERS.get("anthropic"):
            try:
                self._providers[AIProviderType.ANTHROPIC] = AnthropicProvider(anthropic_config)
            except Exception as e:
                self._logger.warning("failed_to_initialize_anthropic", error=str(e))

        # Initialize Ollama
        if ollama_config := settings.AI_PROVIDERS.get("ollama"):
            try:
                self._providers[AIProviderType.OLLAMA] = OllamaProvider(ollama_config)
                if self._default_provider is None:
                    self._default_provider = AIProviderType.OLLAMA
            except Exception as e:
                self._logger.warning("failed_to_initialize_ollama", error=str(e))

        # Initialize LM Studio
        if lmstudio_config := settings.AI_PROVIDERS.get("lm_studio"):
            try:
                self._providers[AIProviderType.LM_STUDIO] = LMStudioProvider(lmstudio_config)
                if self._default_provider is None:
                    self._default_provider = AIProviderType.LM_STUDIO
            except Exception as e:
                self._logger.warning("failed_to_initialize_lmstudio", error=str(e))

        # Initialize Groq
        if groq_config := settings.AI_PROVIDERS.get("groq"):
            try:
                self._providers[AIProviderType.GROQ] = GroqProvider(groq_config)
                if self._default_provider is None:
                    self._default_provider = AIProviderType.GROQ
            except Exception as e:
                self._logger.warning("failed_to_initialize_groq", error=str(e))

        # Initialize Gemini
        if gemini_config := settings.AI_PROVIDERS.get("gemini"):
            try:
                self._providers[AIProviderType.GEMINI] = GeminiProvider(gemini_config)
                if self._default_provider is None:
                    self._default_provider = AIProviderType.GEMINI
            except Exception as e:
                self._logger.warning("failed_to_initialize_gemini", error=str(e))

        self._logger.info(
            "providers_initialized",
            providers=list(self._providers.keys()),
            default=self._default_provider,
        )

    def get_provider(self, provider_type: Optional[AIProviderType] = None) -> BaseAIProvider:
        """Get a provider instance."""
        provider = provider_type or self._default_provider
        if provider is None:
            raise ConfigurationError("No AI provider configured")
        
        if provider not in self._providers:
            raise ConfigurationError(f"Provider {provider} not configured")
        
        return self._providers[provider]

    def list_providers(self) -> List[Dict[str, Any]]:
        """List all configured providers."""
        return [
            {
                "type": provider_type.value,
                "available": provider.validate_config(),
                "models": provider.list_models() if provider.validate_config() else [],
            }
            for provider_type, provider in self._providers.items()
        ]

    async def chat(
        self,
        messages: List[Dict[str, str]],
        provider: Optional[AIProviderType] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> ChatCompletion:
        """
        Send a chat completion request.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            provider: Provider to use (defaults to configured default)
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Chat completion response
        """
        self._logger.info("chat_request", provider=provider, model=model)
        
        provider_instance = self.get_provider(provider)
        
        # Convert dict messages to Message objects
        msg_objects = [
            Message(role=m["role"], content=m["content"])
            for m in messages
        ]
        
        return await provider_instance.chat(
            messages=msg_objects,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

    async def stream(
        self,
        messages: List[Dict[str, str]],
        provider: Optional[AIProviderType] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> AsyncIterator[StreamChunk]:
        """
        Send a streaming chat completion request.
        
        Args:
            messages: List of message dictionaries
            provider: Provider to use
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Yields:
            Stream chunks
        """
        self._logger.info("stream_request", provider=provider, model=model)
        
        provider_instance = self.get_provider(provider)
        
        msg_objects = [
            Message(role=m["role"], content=m["content"])
            for m in messages
        ]
        
        async for chunk in provider_instance.stream(
            messages=msg_objects,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        ):
            yield chunk

    def set_default_provider(self, provider: AIProviderType) -> None:
        """Set the default provider."""
        if provider not in self._providers:
            raise ConfigurationError(f"Provider {provider} not configured")
        self._default_provider = provider
        self._logger.info("default_provider_set", provider=provider.value)


# Global AI service instance
_ai_service: Optional[AIService] = None


def get_ai_service() -> AIService:
    """Get the global AI service instance."""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service