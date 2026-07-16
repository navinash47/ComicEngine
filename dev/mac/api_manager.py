"""Unified Mac API clients: HF image providers, Google, OpenAI, Anthropic."""

from __future__ import annotations

import base64
import io
import os
from pathlib import Path
from typing import Any

from PIL import Image

from dev.shared.phase1_prompt import (
    IMAGE_ASPECT_RATIO,
    MODEL_FLUX,
    MODEL_NANO_BANANA,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

# Env key placeholders (fill in repo-root .env; never commit secrets):
#   FAL_KEY=...
#   HF_TOKEN=...
#   GOOGLE_API_KEY=...
#   OPENAI_API_KEY=...
#   ANTHROPIC_API_KEY=...


class EnvKeys:
    """Load repo-root .env once; raise only when a key is actually needed."""

    def __init__(self, env_path: Path | None = None) -> None:
        self.env_path = env_path or (REPO_ROOT / ".env")
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        if self.env_path.is_file():
            try:
                from dotenv import load_dotenv

                load_dotenv(self.env_path)
            except ImportError:
                pass
        self._loaded = True

    def get(self, name: str) -> str | None:
        self._ensure_loaded()
        value = (os.getenv(name) or "").strip()
        return value or None

    def require(self, name: str) -> str:
        value = self.get(name)
        if not value:
            raise RuntimeError(f"{name} is missing or empty (set it in {self.env_path})")
        return value

    def hf_token(self) -> str:
        token = self.get("HF_TOKEN") or self.get("HUGGING_FACE_HUB_TOKEN")
        if not token:
            raise RuntimeError(
                f"HF_TOKEN (or HUGGING_FACE_HUB_TOKEN) is missing or empty "
                f"(set it in {self.env_path})"
            )
        return token

    def fal_or_hf(self) -> str:
        """fal-ai: prefer FAL_KEY, fall back to HF_TOKEN."""
        return self.get("FAL_KEY") or self.hf_token()


class HuggingFaceImage:
    """text_to_image via huggingface_hub.InferenceClient + inference providers."""

    PROVIDERS = (
        "fal-ai",
        "together",
        "replicate",
        "nscale",
        "wavespeed",
        "hf-inference",
    )

    def __init__(
        self,
        keys: EnvKeys,
        provider: str = "fal-ai",
        api_key: str | None = None,
    ) -> None:
        if provider not in self.PROVIDERS:
            raise ValueError(
                f"unknown provider {provider!r}; expected one of {self.PROVIDERS}"
            )
        self.keys = keys
        self.provider = provider
        self._api_key = api_key
        self._client: Any = None

    def _resolve_key(self) -> str:
        if self._api_key:
            return self._api_key
        if self.provider == "fal-ai":
            return self.keys.fal_or_hf()
        return self.keys.hf_token()

    def _client_for(self) -> Any:
        if self._client is None:
            from huggingface_hub import InferenceClient

            self._client = InferenceClient(
                provider=self.provider,
                api_key=self._resolve_key(),
            )
        return self._client

    def text_to_image(
        self,
        prompt: str,
        model: str = MODEL_FLUX,
        **kwargs: Any,
    ) -> Image.Image:
        image = self._client_for().text_to_image(prompt, model=model, **kwargs)
        if not isinstance(image, Image.Image):
            raise TypeError(f"expected PIL.Image, got {type(image).__name__}")
        return image


class GoogleAPI:
    """Google GenAI: chat + Nano Banana image generation."""

    def __init__(self, keys: EnvKeys) -> None:
        self.keys = keys
        self._client: Any = None

    def _client_for(self) -> Any:
        if self._client is None:
            from google import genai

            self._client = genai.Client(api_key=self.keys.require("GOOGLE_API_KEY"))
        return self._client

    def chat(
        self,
        prompt: str,
        model: str = "gemini-3.5-flash",
        **kwargs: Any,
    ) -> str:
        response = self._client_for().models.generate_content(
            model=model,
            contents=prompt,
            **kwargs,
        )
        text = getattr(response, "text", None)
        if text:
            return text
        raise RuntimeError("Google chat response had no text")

    def _image_bytes_from_interactions(
        self,
        prompt: str,
        model: str,
        aspect_ratio: str,
        **kwargs: Any,
    ) -> bytes:
        interaction = self._client_for().interactions.create(
            model=model,
            input=prompt,
            response_format={
                "type": "image",
                "aspect_ratio": aspect_ratio,
            },
            **kwargs,
        )
        out = getattr(interaction, "output_image", None)
        if out is None:
            raise RuntimeError("interactions response missing output_image")
        data = getattr(out, "data", None)
        if not data:
            raise RuntimeError("interactions output_image has empty data")
        if isinstance(data, bytes):
            return data
        return base64.b64decode(data)

    def _image_bytes_from_generate_content(
        self,
        prompt: str,
        model: str,
        aspect_ratio: str,
        **kwargs: Any,
    ) -> bytes:
        from google.genai import types

        response = self._client_for().models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
                image_config=types.ImageConfig(aspect_ratio=aspect_ratio),
            ),
            **kwargs,
        )
        parts: list[Any] = []
        if getattr(response, "candidates", None):
            content = response.candidates[0].content
            parts = getattr(content, "parts", None) or []
        for part in parts:
            inline = getattr(part, "inline_data", None)
            if inline is not None and getattr(inline, "data", None):
                data = inline.data
                if isinstance(data, bytes):
                    return data
                return base64.b64decode(data)
        raise RuntimeError("generate_content response had no inline image data")

    def text_to_image(
        self,
        prompt: str,
        model: str = MODEL_NANO_BANANA,
        aspect_ratio: str = IMAGE_ASPECT_RATIO,
        **kwargs: Any,
    ) -> Image.Image:
        try:
            raw = self._image_bytes_from_interactions(
                prompt, model=model, aspect_ratio=aspect_ratio, **kwargs
            )
        except Exception as exc:
            if type(exc).__name__ not in ("AttributeError", "TypeError", "ValidationError"):
                raise
            raw = self._image_bytes_from_generate_content(
                prompt, model=model, aspect_ratio=aspect_ratio, **kwargs
            )
        return Image.open(io.BytesIO(raw))


class OpenAIAPI:
    """OpenAI chat + DALL·E image generation."""

    def __init__(self, keys: EnvKeys) -> None:
        self.keys = keys
        self._client: Any = None

    def _client_for(self) -> Any:
        if self._client is None:
            import openai

            self._client = openai.OpenAI(api_key=self.keys.require("OPENAI_API_KEY"))
        return self._client

    def chat(
        self,
        prompt: str,
        model: str = "gpt-4o-mini",
        **kwargs: Any,
    ) -> str:
        create_kwargs: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            **kwargs,
        }
        if "max_tokens" not in create_kwargs and "max_completion_tokens" not in create_kwargs:
            create_kwargs["max_tokens"] = 1024
        response = self._client_for().chat.completions.create(**create_kwargs)
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("OpenAI chat response had no content")
        return content

    def text_to_image(
        self,
        prompt: str,
        model: str = "dall-e-3",
        size: str = "1024x1024",
        **kwargs: Any,
    ) -> Image.Image:
        import urllib.request

        response = self._client_for().images.generate(
            model=model,
            prompt=prompt,
            size=size,
            **kwargs,
        )
        item = response.data[0]
        b64 = getattr(item, "b64_json", None)
        if b64:
            return Image.open(io.BytesIO(base64.b64decode(b64)))
        url = getattr(item, "url", None)
        if not url:
            raise RuntimeError("OpenAI image response had neither b64_json nor url")
        with urllib.request.urlopen(url) as resp:
            return Image.open(io.BytesIO(resp.read()))


class AnthropicAPI:
    """Anthropic chat (text only)."""

    def __init__(self, keys: EnvKeys) -> None:
        self.keys = keys
        self._client: Any = None

    def _client_for(self) -> Any:
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic(
                api_key=self.keys.require("ANTHROPIC_API_KEY")
            )
        return self._client

    def chat(
        self,
        prompt: str,
        model: str = "claude-haiku-4-5-20251001",
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> str:
        message = self._client_for().messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        )
        blocks = getattr(message, "content", None) or []
        texts = [
            getattr(block, "text", "")
            for block in blocks
            if getattr(block, "type", None) == "text" or hasattr(block, "text")
        ]
        text = "".join(texts).strip()
        if not text:
            raise RuntimeError("Anthropic chat response had no text")
        return text


class ApiManager:
    """Cell-friendly facade over HF / Google / OpenAI / Anthropic clients."""

    def __init__(self, env_path: Path | None = None) -> None:
        self.keys = EnvKeys(env_path)
        self.google = GoogleAPI(self.keys)
        self.openai = OpenAIAPI(self.keys)
        self.anthropic = AnthropicAPI(self.keys)

    def hf_image(
        self,
        prompt: str,
        *,
        provider: str = "fal-ai",
        model: str = MODEL_FLUX,
        api_key: str | None = None,
        **kwargs: Any,
    ) -> Image.Image:
        return HuggingFaceImage(
            self.keys, provider=provider, api_key=api_key
        ).text_to_image(prompt, model=model, **kwargs)

    def google_image(self, prompt: str, **kwargs: Any) -> Image.Image:
        return self.google.text_to_image(prompt, **kwargs)

    def google_chat(self, prompt: str, **kwargs: Any) -> str:
        return self.google.chat(prompt, **kwargs)

    def openai_chat(self, prompt: str, **kwargs: Any) -> str:
        return self.openai.chat(prompt, **kwargs)

    def openai_image(self, prompt: str, **kwargs: Any) -> Image.Image:
        return self.openai.text_to_image(prompt, **kwargs)

    def anthropic_chat(self, prompt: str, **kwargs: Any) -> str:
        return self.anthropic.chat(prompt, **kwargs)
