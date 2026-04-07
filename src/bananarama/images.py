"""Reference image handling: resolving placeholders, resizing, and splitting."""

from __future__ import annotations

import base64
import math
import re
from typing import TYPE_CHECKING

from PIL import Image

if TYPE_CHECKING:
    from pathlib import Path

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".gif")
MAX_REFERENCE_SIZE = (512, 512)
PLACEHOLDER_PATTERN = re.compile(r"\[([^\]]+)\]")

_EXT_TO_MIME: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


def mime_type_for_path(path: Path) -> str:
    """Return the MIME type for an image path based on its extension."""
    from pathlib import PurePosixPath

    suffix = PurePosixPath(str(path)).suffix.lower()
    return _EXT_TO_MIME.get(suffix, "image/png")


def resolve_placeholders(
    description: str | None,
    base_dir: Path,
    start_index: int = 0,
) -> tuple[str | None, list[Path]]:
    """Replace [name] placeholders with text references and collect image paths.

    Returns a tuple of (resolved_text, list_of_image_paths).
    """
    if description is None:
        return None, []

    matches = list(PLACEHOLDER_PATTERN.finditer(description))
    if not matches:
        return description, []

    images: list[Path] = []
    text = description

    for i, match in enumerate(matches):
        name = match.group(1)
        image_path = find_image_file(name, base_dir)
        images.append(image_path)

        ordinal = start_index + i + 1
        replacement = f"{name} (shown in image {ordinal})"
        text = text.replace(f"[{name}]", replacement, 1)

    return text, images


def find_image_file(name: str, base_dir: Path) -> Path:
    """Find an image file by name in a directory, trying common extensions."""
    for ext in IMAGE_EXTENSIONS:
        path = base_dir / f"{name}{ext}"
        if path.exists():
            return path

    msg = (
        f"Cannot find reference image for '{name}'. "
        f"Looked for {name}.png, {name}.jpg, etc. in '{base_dir}'."
    )
    raise FileNotFoundError(msg)


def resize_reference_image(
    path: Path, max_size: tuple[int, int] = MAX_REFERENCE_SIZE
) -> bool:
    """Resize a reference image if it exceeds max_size. Returns True if resized."""
    img = Image.open(path)
    original_size = img.size

    img.thumbnail(max_size, Image.Resampling.LANCZOS)

    if img.size == original_size:
        return False

    img.save(path, format=img.format or "PNG")
    return True


def image_to_base64(path: Path) -> str:
    """Read an image file and return base64-encoded data."""
    return base64.b64encode(path.read_bytes()).decode("ascii")


def split_image(
    image_data: bytes,
    output_dir: Path,
    base_name: str,
    max_pixels: int = 4096 * 4096,
) -> list[Path]:
    """Split a large image into smaller tiles if it exceeds max_pixels.

    If the image is within the limit, it is saved as-is and a single-element
    list is returned. Otherwise, it is split into a grid of roughly equal tiles
    and saved as {base_name}_row_col.png.

    Returns a list of output file paths.
    """
    import io

    img = Image.open(io.BytesIO(image_data))
    width, height = img.size
    total_pixels = width * height

    if total_pixels <= max_pixels:
        out_path = output_dir / f"{base_name}.png"
        img.save(out_path, format="PNG")
        return [out_path]

    # Calculate grid dimensions to keep each tile under max_pixels
    scale = math.sqrt(total_pixels / max_pixels)
    cols = max(1, math.ceil(math.sqrt(scale * width / height)))
    rows = max(1, math.ceil(scale * height / width * cols))

    tile_w = math.ceil(width / cols)
    tile_h = math.ceil(height / rows)

    paths: list[Path] = []
    for r in range(rows):
        for c in range(cols):
            left = c * tile_w
            upper = r * tile_h
            right = min(left + tile_w, width)
            lower = min(upper + tile_h, height)

            tile = img.crop((left, upper, right, lower))
            tile_name = f"{base_name}_{r + 1}_{c + 1}.png"
            tile_path = output_dir / tile_name
            tile.save(tile_path, format="PNG")
            paths.append(tile_path)

    return paths
