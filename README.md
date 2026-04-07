# bananarama

Generate slide background images from YAML configuration files using AI image models.

bananarama avoids the usual tedious loop of copying prompts into a web UI, downloading images, tweaking, and repeating. Your prompts live in version-controlled YAML, and regenerating every image is a single command. No more copy-paste and no more losing track of which prompt produced which image.

## Installation

```bash
# Requires Python 3.12+
pip install bananarama

# Or with uv
uv pip install bananarama
```

For development:

```bash
git clone https://github.com/bfraca/bananaramapy.git
cd bananaramapy
uv sync
```

## Quick start

1. Set your API key:

```bash
export GEMINI_API_KEY="your-api-key"
```

2. Create a `bananarama.yaml` file:

```yaml
defaults:
  style: >
    Flat vector editorial illustration with a muted, desaturated
    color palette. Mid-century modern aesthetic. Calm and approachable.

images:
  - name: robot-factory
    description: >
      Draw a picture of [hadley] overseeing a factory full of robots.
      The robots should be typing at computers.
```

Reference images like `[hadley]` are matched to image files (e.g. `hadley.png`) in the same directory as the YAML file.

3. Generate:

```bash
bananarama generate path/to/bananarama.yaml
```

Images that already exist are skipped unless you pass `--force`.

## CLI commands

```bash
# Generate images from a config
bananarama generate demo/bananarama.yaml

# Force regenerate all images
bananarama generate demo/ --force

# List available models
bananarama models
```

## YAML configuration

### `defaults`

- **`style`**: Style prompt appended to every image description.
- **`description`**: Default description.
- **`aspect-ratio`**: One of `"1:1"`, `"3:2"`, `"16:9"`, etc. Default: `"16:9"`.
- **`resolution`**: One of `"1K"`, `"2K"`, `"4K"`. Default: `"1K"`.
- **`n`**: Number of variants per image. Default: `1`.
- **`model`**: Model to use. Default: `"gemini-3.1-flash-image-preview"`.
- **`force`**: If `true`, regenerate even if files exist. Default: `false`.
- **`seed`**: Integer seed for more deterministic output.

### `output-dir`

Output directory for generated images, relative to the YAML file. Defaults to a directory with the same name as the YAML file.

### `images`

Each image has:

- **`name`** (required): Used as the output filename (`{name}.png`).
- **`description`** (required, unless a default is set): Prompt for image generation. Use `[name]` to reference images in the same directory.
- **`n`**: Number of variants. Files are named `{name}-1.png`, `{name}-2.png`, etc.
- **`style`**, **`aspect-ratio`**, **`resolution`**, **`model`**, **`force`**, **`seed`**: Per-image overrides.

## Large image splitting

Images that exceed `--max-pixels` (default: 16M pixels) are automatically split into a grid of tiles, saved as `{name}_row_col.png`. This is useful for very high-resolution generation.

## Available models

| Model | Provider | Notes |
|---|---|---|
| `gemini-3.1-flash-image-preview` | Google | Default. Fast, ~$0.07/image |
| `gemini-3-pro-image-preview` | Google | Higher quality, 4K support |
| `gemini-2.5-flash-image` | Google | Budget option |

More providers (OpenAI, etc.) coming in Phase 2.

## Development

```bash
# Install dev dependencies
uv sync

# Run tests
uv run pytest

# Lint & format
uv run ruff check .
uv run ruff format .

# Type check
uv run mypy src/
```

## License

MIT
