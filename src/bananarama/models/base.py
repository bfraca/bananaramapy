"""Abstract base class for image generation providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ReferenceImage:
    """A reference image with its data and MIME type."""

    data: bytes
    mime_type: str = "image/png"


@dataclass
class ImageRequest:
    """A request to generate a single image."""

    prompt: str
    reference_images: list[ReferenceImage] = field(default_factory=list)
    aspect_ratio: str = "16:9"
    resolution: str = "1K"
    seed: int | None = None


@dataclass
class TokenUsage:
    """Token usage breakdown by modality."""

    text: int = 0
    image: int = 0


@dataclass
class ImageResult:
    """Result from an image generation request."""

    image_data: bytes
    model: str
    input_tokens: TokenUsage = field(default_factory=TokenUsage)
    output_tokens: TokenUsage = field(default_factory=TokenUsage)


class ImageProvider(ABC):
    """Abstract base for image generation providers.

    Each provider wraps a specific API (Gemini, OpenAI, etc.) and implements
    async generation.  Subclass this ABC and register in the model registry
    to add a new provider.
    """

    @abstractmethod
    async def generate(self, request: ImageRequest) -> ImageResult:
        """Generate a single image from a request."""
        ...

    @abstractmethod
    async def generate_batch(
        self, requests: list[ImageRequest]
    ) -> list[ImageResult | BaseException]:
        """Generate multiple images concurrently.

        Returns a list parallel to the input. Each element is either an
        ImageResult on success or an exception on failure.
        """
        ...
