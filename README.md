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

### Optional providers

By default only **Google Gemini** is installed. To add other providers:

```bash
# OpenAI (gpt-image-1, gpt-image-1.5)
uv pip install "bananarama[openai]"

# FLUX (flux-2-pro, flux-2-dev, flux-2-schnell) via Together AI
uv pip install "bananarama[flux]"

# All providers
uv pip install "bananarama[all]"
```

### Development

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
  aspect-ratio: "16:9"

images:
  - name: robot-factory
    description: >
      Draw a picture of [hadley] overseeing a factory full of robots.
      The robots should be typing at computers.
```

Reference images like `[hadley]` are matched to image files (e.g. `hadley.png`) in the same directory as the YAML file.

> **Note:** Always quote aspect-ratio values in YAML (e.g. `"16:9"`) to avoid
> PyYAML interpreting them as sexagesimal integers.

3. Generate:

```bash
bananarama generate path/to/bananarama.yaml
```

Images that already exist are skipped unless you pass `--force`.

## CLI commands

### `bananarama generate`

```bash
# Generate images from a config
bananarama generate demo/bananarama.yaml

# Force regenerate all images
bananarama generate demo/ --force

# Preview what would be generated with cost estimates (no API calls)
bananarama generate demo/ --dry-run

# Limit concurrent API calls (default: 5)
bananarama generate demo/ --concurrency 3

# Custom output directory
bananarama generate demo/ --output-dir my-images/
```

### `bananarama models`

```bash
# List all available models with pricing and status
bananarama models

# Filter by provider
bananarama models --provider google
bananarama models --provider openai
bananarama models --provider flux
```

Shows each model's provider, estimated cost per image, and availability status:

| Status | Meaning |
|--------|---------|
| **Ready** | SDK installed and API key set |
| **No Key** | SDK installed but API key missing |
| **No SDK** | SDK package not installed |

### `bananarama costs`

```bash
# Show historical cost summary
bananarama costs
```

Displays total spend, per-model breakdown, and last 10 generation runs.
Costs are tracked in `~/.bananarama/cost-log.csv`.

## Available models

| Model | Provider | Type | Est. $/img |
|---|---|---|---|
| `gemini-3.1-flash-image-preview` | Google Gemini | Token-based | ~$0.018 |
| `gemini-3-pro-image-preview` | Google Gemini | Token-based | ~$0.019 |
| `gemini-2.5-flash-image` | Google Gemini | Token-based | ~$0.018 |
| `gpt-image-1` | OpenAI | Token-based | ~$0.015 |
| `gpt-image-1.5` | OpenAI | Token-based | ~$0.015 |
| `flux-2-pro` | FLUX (Together AI) | Per-image | ~$0.050 |
| `flux-2-dev` | FLUX (Together AI) | Per-image | ~$0.025 |
| `flux-2-schnell` | FLUX (Together AI) | Per-image | ~$0.003 |

## Provider setup

Each provider requires its own API key set as an environment variable:

| Provider | Env var | Get a key |
|---|---|---|
| Google Gemini | `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/apikey) |
| OpenAI | `OPENAI_API_KEY` | [OpenAI Platform](https://platform.openai.com/api-keys) |
| FLUX (Together AI) | `TOGETHER_API_KEY` | [Together AI](https://api.together.ai/settings/api-keys) |

Per-image model selection is supported — just set `model:` on any image entry:

```yaml
images:
  - name: hero
    model: gpt-image-1.5
    description: A dramatic hero shot.
  - name: background
    model: flux-2-schnell
    description: A simple gradient background.
```

## YAML configuration

### `defaults`

- **`style`**: Style prompt appended to every image description.
- **`description`**: Default description.
- **`aspect-ratio`**: One of `"1:1"`, `"2:3"`, `"3:2"`, `"3:4"`, `"4:3"`, `"4:5"`, `"5:4"`, `"9:16"`, `"16:9"`, `"21:9"`. Default: `"16:9"`.
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

## Cost tracking

bananarama tracks costs in two ways:

- **Real-time:** Actual token usage from API responses (Gemini, OpenAI) or flat per-image pricing (FLUX).
- **Benchmark estimates:** `prices.toml` ships with published pricing for `--dry-run` and the `models` table.

After each generation run, costs are appended to `~/.bananarama/cost-log.csv`.
View your spend history with `bananarama costs`.

To override the built-in pricing data, set `BANANARAMA_PRICES` to your own TOML file path.

## Development

```bash
# Install dev dependencies
uv sync

# Run tests
uv run pytest

# Run integration tests (requires API keys)
uv run pytest -m integration

# Lint & format
uv run ruff check .
uv run ruff format .

# Type check
uv run mypy src/
```

## License

MIT — see [LICENSE.md](LICENSE.md).
