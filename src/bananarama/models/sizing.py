"""Shared aspect-ratio and resolution mapping for all providers."""

from __future__ import annotations

# Base dimensions at 1K resolution for each aspect ratio.
# Providers that require explicit pixel sizes use these as a starting point.
_BASE_DIMENSIONS: dict[str, tuple[int, int]] = {
    "1:1": (1024, 1024),
    "2:3": (832, 1216),
    "3:2": (1216, 832),
    "3:4": (896, 1152),
    "4:3": (1152, 896),
    "4:5": (896, 1120),
    "5:4": (1120, 896),
    "9:16": (768, 1344),
    "16:9": (1344, 768),
    "21:9": (1536, 640),
}

# Resolution multipliers relative to 1K base.
_RESOLUTION_SCALE: dict[str, float] = {
    "1K": 1.0,
    "2K": 1.414,  # ~2x pixel area
    "4K": 2.0,  # ~4x pixel area
}

# Provider-specific maximum pixel dimensions.
_PROVIDER_MAX: dict[str, int] = {
    "gemini": 4096,
    "openai": 1536,
    "flux": 2048,
}


def resolve_dimensions(
    aspect_ratio: str,
    resolution: str = "1K",
    provider: str = "gemini",
) -> tuple[int, int]:
    """Return (width, height) for a given aspect ratio, resolution, and provider.

    Dimensions are scaled from a 1K base and clamped to provider limits.
    Values are rounded to the nearest multiple of 64 (required by most models).
    """
    base = _BASE_DIMENSIONS.get(aspect_ratio)
    if base is None:
        msg = f"Unsupported aspect ratio: {aspect_ratio}"
        raise ValueError(msg)

    scale = _RESOLUTION_SCALE.get(resolution, 1.0)
    w = int(base[0] * scale)
    h = int(base[1] * scale)

    # Clamp to provider max
    max_dim = _PROVIDER_MAX.get(provider, 4096)
    if w > max_dim or h > max_dim:
        ratio = min(max_dim / w, max_dim / h)
        w = int(w * ratio)
        h = int(h * ratio)

    # Round to nearest multiple of 64
    w = max(64, (w // 64) * 64)
    h = max(64, (h // 64) * 64)

    return w, h


def resolve_openai_size(
    aspect_ratio: str,
    resolution: str = "1K",
) -> str:
    """Return an OpenAI-compatible size string like '1024x1024'.

    OpenAI only accepts a fixed set of sizes. We pick the closest match.
    """
    openai_sizes: dict[str, str] = {
        "1:1": "1024x1024",
        "2:3": "1024x1536",
        "3:2": "1536x1024",
        "3:4": "1024x1536",
        "4:3": "1536x1024",
        "4:5": "1024x1536",
        "5:4": "1536x1024",
        "9:16": "1024x1536",
        "16:9": "1536x1024",
        "21:9": "1536x1024",
    }
    size = openai_sizes.get(aspect_ratio)
    if size is None:
        msg = f"Unsupported aspect ratio for OpenAI: {aspect_ratio}"
        raise ValueError(msg)
    return size
