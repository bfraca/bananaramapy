# Bananarama Package Implementation Plan

## Overview
Create an R package for generating presentation images using Google Gemini images (nanobanana) based on YAML configuration files.

## Package Structure

```
bananarama/
├── R/
│   ├── bananarama.R      # Main user-facing function
│   ├── parse.R           # YAML parsing and validation
│   └── sort.R            # Dependency ordering
├── DESCRIPTION
├── NAMESPACE
└── demo/
    ├── images.yaml
    ├── hadley.jpg
    └── robot.png
```

## Core Functions

### 1. Main Entry Point: `bananarama()`

```r
bananarama <- function(config_path = NULL, output_dir = NULL, force = FALSE) {
```

**Arguments:**
- `config_path`: Path to yaml file (default: `bananarama.yaml`)
- `output_dir`: Where to save generated images (default: `output/` subdirectory next to config)
- `force`: If TRUE, regenerate all images even if they exist

**Behavior:**
1. Parse YAML config
2. Create output directory if needed
3. Topologically sort images by `builds-on` dependencies
4. For each image in order:
   - Print progress with cli
   - Skip if output exists and `force = FALSE` (print skip message)
   - Generate image using ellmer
   - Save to output directory
   - Print completion message

### 2. YAML Parsing: `parse_image_config()`

```r
parse_image_config <- function(config_path) {
```

**Returns:** A list with:
- `defaults`: Named list (style, aspect-ratio, resolution)
- `images`: List of image specs, each with name, description, builds-on (optional). Each image can optionally override the defaults (i.e. style, aspect-ratio, resolution)
- `base_dir`: Directory containing the config (for finding reference images)

### 3. Topological Sort: `sort_by_dependencies()`

```r
sort_by_dependencies <- function(images) {
```

**Input:** List of image specs with optional `builds-on` field
**Output:** Same list reordered so dependencies come first
**Errors:** If circular dependency detected

### 4. Image Generation: `generate_single_image()`

```r
generate_single_image <- function(image_spec, defaults, base_dir, output_dir,
                                   previous_images = list()) {
```

**Process:**
1. Build full prompt from defaults + description
2. Find and replace `[placeholder]` references with `content_image_file()` calls
3. If `builds-on` exists, include the previously generated image
4. Create new ellmer chat session with `image_config` parameters:
   - `aspect_ratio`: from defaults/overrides (e.g., "16:9", "1:1", "4:3")
   - `resolution`: from defaults/overrides (e.g., "1K", "2K", "4K")
5. Send prompt with reference images
6. Save output using `content_image_write()`

### 5. Placeholder Replacement: `resolve_placeholders()`

```r
resolve_placeholders <- function(description, base_dir) {
```

**Input:** Description string like "Draw [hadley] with [robot]"
**Output:** List with:
- `text`: Prompt text with placeholders replaced by hybrid references that include both the original name and ordinal position
- `images`: Vector of image file paths in the order they should be attached

**Logic:**
- Find all `[name]` patterns in order of appearance
- Look for `name.png` or `name.jpg` in base_dir
- Replace each placeholder with hybrid reference: `"[name] (shown in image 1)"`, `"[name] (shown in image 2)"`, etc.
- Return paths in the same order for content_image_file()

**Rationale:** Google's documentation recommends labeling images within prompts to reduce hallucinations. The hybrid approach preserves the descriptive context from the original placeholder name while adding explicit ordinal references for clarity.

**Example:**
- Input: `"Draw [hadley] with [robot] in a garden"`
- Output text: `"Draw hadley (shown in image 1) with robot (shown in image 2) in a garden"`
- Output images: `c("hadley.jpg", "robot.png")`

### 6. Prompt Construction: `build_prompt()`

```r
build_prompt <- function(description, defaults) {
```

Constructs the final prompt sent to Gemini by combining:
1. Style from defaults + overrides
2. The image description (with placeholders kept for context)

```r
paste0(
  defaults$style, "\n\n",
  description
)
```

**Note:** Aspect ratio and resolution are passed as model parameters via `image_config`, not in the prompt text.

## Dependency Handling

For `builds-on`, you must replay the entire conversation history to maintain context:
- When image B builds-on image A, reconstruct the full conversation thread (using `chat$add_turn()`)
- This means: prompt A → generated image A → prompt B
- If A itself built on another image, include that entire chain too

```r
# When generating "B" which builds-on "A":
# 1. Start fresh chat
chat <- chat_gemini(model = "gemini-3-pro-preview")

# 2. Replay the conversation that generated A
chat$add_turn(prompt_A, content_image_file(ref_images_A))

# 3. Now generate B in the same conversation
chat$chat(prompt_B)
```

For longer chains (C builds-on B builds-on A), replay the entire history:
prompt A → image A → prompt B → image B → prompt C

## Output

- Default output directory: `{dirname(config_path)}/output/`
- Generated images saved as: `{output_dir}/{image_name}.png`
- Progress messages via cli:
  - "Generating {name}..." when starting
  - "Skipping {name} (already exists)" when skipping
  - "✓ Generated {name}" when complete

## Error Handling

- Missing reference image file → informative error with path
- Circular dependency in builds-on → error listing the cycle
- Missing builds-on target → error naming the missing image
- Gemini API failure → error with context

## Dependencies

Add to DESCRIPTION Imports:
- ellmer
- yaml
- cli

## Files to Create/Modify

1. **R/bananarama.R** - `bananarama()`, `generate_single_image()`
2. **R/parse.R** - `parse_image_config()`, `build_prompt()`, `resolve_placeholders()`
3. **R/sort.R** - `sort_by_dependencies()`
4. **DESCRIPTION** - Update title, description, add Imports
5. **NAMESPACE** - Export `bananarama`
6. **_pkgdown.yml** - Add `bananarama` to reference index
7. **tests/testthat/test-parse.R** - Tests for YAML parsing and placeholder resolution
8. **tests/testthat/test-sort.R** - Tests for topological sort and cycle detection

## Verification

1. Ensure demo/output/ doesn't exist or is empty
2. Run `bananarama::bananarama("demo/images.yaml")`
3. Verify:
   - Progress messages shown for each image
   - Images generated in dependency order (directions before lost)
   - Images saved in demo/output/
4. Run again - should skip all images (lazy behavior)
5. Delete one image, run again - should only regenerate that one
