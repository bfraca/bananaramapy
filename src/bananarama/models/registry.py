"""Model registry: maps model names to their providers.

This module provides a central place to look up which provider handles
a given model name. Providers register themselves when imported.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bananarama.models.base import ImageProvider

# Maps model name -> (provider class, env var for API key).
_PROVIDER_REGISTRY: dict[str, tuple[type[ImageProvider], str]] = {}


def register_provider(
    model_names: list[str],
    provider_cls: type[ImageProvider],
    api_key_env: str,
) -> None:
    """Register a provider class for a list of model names."""
    for name in model_names:
        _PROVIDER_REGISTRY[name] = (provider_cls, api_key_env)


def get_provider(model: str, **kwargs: str | None) -> ImageProvider:
    """Instantiate the provider for a given model name.

    The API key is resolved from kwargs, then from the environment variable
    associated with the provider. Raises ValueError if the model is unknown.
    """
    entry = _PROVIDER_REGISTRY.get(model)
    if entry is None:
        available = ", ".join(sorted(_PROVIDER_REGISTRY.keys()))
        msg = f"Unknown model '{model}'. Available models: {available}"
        raise ValueError(msg)

    provider_cls, api_key_env = entry

    if "api_key" not in kwargs or kwargs["api_key"] is None:
        kwargs["api_key"] = os.environ.get(api_key_env)

    return provider_cls(model=model, **kwargs)  # type: ignore[call-arg]


def list_models() -> list[str]:
    """Return all registered model names."""
    return sorted(_PROVIDER_REGISTRY.keys())


def get_provider_name(model: str) -> str:
    """Return a human-readable provider name for a model."""
    entry = _PROVIDER_REGISTRY.get(model)
    if entry is None:
        return "Unknown"
    cls_name = entry[0].__name__
    display_names: dict[str, str] = {
        "GeminiProvider": "Google Gemini",
        "OpenAIProvider": "OpenAI",
        "FluxProvider": "FLUX (Together AI)",
    }
    return display_names.get(cls_name, cls_name)


def is_provider_available(model: str) -> bool:
    """Check whether the SDK for a model's provider is importable."""
    entry = _PROVIDER_REGISTRY.get(model)
    if entry is None:
        return False
    provider_cls = entry[0]
    cls_name = provider_cls.__name__
    try:
        if cls_name == "GeminiProvider":
            import google.genai  # noqa: F401
        elif cls_name == "OpenAIProvider":
            import openai  # noqa: F401
        elif cls_name == "FluxProvider":
            import together  # noqa: F401
        return True
    except ImportError:
        return False


def _register_all() -> None:
    """Import and register all built-in providers."""
    from bananarama.models.gemini import GEMINI_MODELS, GeminiProvider

    register_provider(GEMINI_MODELS, GeminiProvider, "GEMINI_API_KEY")

    from bananarama.models.openai import OPENAI_MODELS, OpenAIProvider

    register_provider(OPENAI_MODELS, OpenAIProvider, "OPENAI_API_KEY")

    from bananarama.models.flux import FLUX_MODELS, FluxProvider

    register_provider(FLUX_MODELS, FluxProvider, "TOGETHER_API_KEY")


_register_all()
