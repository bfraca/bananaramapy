"""Model registry: maps model names to their providers.

This module provides a central place to look up which provider handles
a given model name. New providers (OpenAI, Stability, etc.) can be added
in Phase 2 by importing their class and registering their model names.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bananarama.models.gemini import GEMINI_MODELS, GeminiProvider

if TYPE_CHECKING:
    from bananarama.models.base import ImageProvider

# Maps model name -> provider class constructor.
# Phase 2: add entries like "gpt-image-1.5": OpenAIProvider, etc.
_PROVIDER_REGISTRY: dict[str, type[GeminiProvider]] = {
    model: GeminiProvider for model in GEMINI_MODELS
}


def get_provider(model: str, **kwargs: str | None) -> ImageProvider:
    """Instantiate the provider for a given model name.

    Raises ValueError if the model is not recognized.
    """
    provider_cls = _PROVIDER_REGISTRY.get(model)
    if provider_cls is None:
        available = ", ".join(sorted(_PROVIDER_REGISTRY.keys()))
        msg = f"Unknown model '{model}'. Available models: {available}"
        raise ValueError(msg)
    return provider_cls(model=model, **kwargs)


def list_models() -> list[str]:
    """Return all registered model names."""
    return sorted(_PROVIDER_REGISTRY.keys())
