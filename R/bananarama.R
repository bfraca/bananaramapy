#' Generate presentation images from a YAML configuration
#'
#' @param path Path to a YAML configuration file or a directory containing
#'   `bananarama.yaml`. Defaults to `"bananarama.yaml"` in the current directory.
#' @param output_dir Directory to save generated images, relative to the
#'   YAML configuration file (or an absolute path). Defaults to the
#'   `output-dir` field in the YAML file, or a directory with the same name
#'   as the YAML file (e.g. `bananarama.yaml` outputs to `bananarama/`).
#' @param force If `TRUE`, regenerate all images even if they already exist.
#' @return Invisibly returns a character vector of output file paths.
#' @export
#' @examples
#' \dontrun{
#' bananarama("demo/")
#' bananarama("demo/bananarama.yaml")
#' }
bananarama <- function(
  path = "bananarama.yaml",
  output_dir = NULL,
  force = FALSE
) {
  config_path <- resolve_config_path(path)
  config <- parse_image_config(config_path)

  default_dir <- tools::file_path_sans_ext(basename(config_path))
  output_dir <- output_dir %||% config$output_dir %||% default_dir
  if (!startsWith(output_dir, "/")) {
    output_dir <- file.path(config$base_dir, output_dir)
  }
  if (!dir.exists(output_dir)) {
    dir.create(output_dir, recursive = TRUE)
  }

  images <- preprocess_images(config$images, config$base_dir, output_dir)

  # Figure out which images need to be generated
  tasks <- build_tasks(images, force = force)
  if (length(tasks) == 0) {
    return(invisible(all_output_paths(images)))
  }

  # Generate all images in parallel
  chat <- make_chat(tasks[[1]]$image)
  prompts <- lapply(tasks, function(task) {
    c(list(ellmer::ContentText(task$image$prompt)), task$image$ref_images)
  })

  cli::cli_alert("Generating {length(tasks)} image{?s} in parallel...")
  results <- ellmer::parallel_chat(chat, prompts)

  total_cost <- 0
  for (i in seq_along(tasks)) {
    result <- results[[i]]
    output_path <- tasks[[i]]$output_path
    model <- tasks[[i]]$image$model
    label <- basename(output_path)

    if (inherits(result, "error") || is.null(result)) {
      cli::cli_alert_danger("Failed to generate {.val {label}}")
    } else if (!save_generated_image(result, output_path)) {
      cli::cli_alert_danger(
        "Failed to generate {.val {label}} (no image in response)"
      )
    } else {
      cost <- image_cost(result, model)
      total_cost <- total_cost + cost
      cli::cli_alert_success(
        "Generated {.val {label}} (${round(cost, 3)})"
      )
    }
  }

  if (total_cost > 0) {
    cli::cli_alert_info("Total cost: ${round(total_cost, 3)}")
  }

  invisible(all_output_paths(images))
}

build_tasks <- function(images, force = FALSE) {
  tasks <- list()
  n_skipped <- 0L
  for (image in images) {
    for (output_path in image$output_paths) {
      if (!force && !image$force && file.exists(output_path)) {
        n_skipped <- n_skipped + 1L
        next
      }
      tasks <- c(tasks, list(list(image = image, output_path = output_path)))
    }
  }
  if (n_skipped > 0) {
    cli::cli_alert_info("Skipping {n_skipped} image{?s} (already exist{?s})")
  }
  tasks
}

all_output_paths <- function(images) {
  unlist(lapply(images, function(image) image$output_paths))
}

preprocess_images <- function(images, base_dir, output_dir) {
  lapply(images, preprocess_image, base_dir = base_dir, output_dir = output_dir)
}

preprocess_image <- function(image, base_dir, output_dir) {
  resolved_style <- resolve_placeholders(image$style, base_dir)

  n <- length(resolved_style$images)
  resolved_desc <- resolve_placeholders(image$description, base_dir, n)
  prompt <- paste(
    c(
      resolved_desc$text,
      paste0("Style: ", resolved_style$text, recycle0 = TRUE)
    ),
    collapse = "\n\n"
  )
  ref_image_paths <- c(resolved_style$images, resolved_desc$images)
  ref_images <- lapply(ref_image_paths, ellmer::content_image_file)

  image$prompt <- prompt
  image$ref_image_paths <- ref_image_paths
  image$ref_images <- ref_images

  n <- image[["n"]] %||% 1L
  if (n > 1L) {
    suffixed_names <- paste0(image$name, "-", seq_len(n))
  } else {
    suffixed_names <- image$name
  }
  image$output_paths <- file.path(
    output_dir,
    paste0(suffixed_names, ".png")
  )
  image
}

make_chat <- function(image_spec) {
  image_config <- list(aspectRatio = image_spec$`aspect-ratio`)
  if (image_spec$model == "gemini-3-pro-image-preview") {
    image_config$imageSize <- image_spec$resolution
  }

  gen_config <- list(imageConfig = image_config)
  if (!is.null(image_spec$seed)) {
    gen_config$seed <- as.integer(image_spec$seed)
  }

  ellmer::chat_google_gemini(
    "Draw a picture based on the user's description, carefully following their
    specified style. Do not include text unless explicitly requested.",
    model = image_spec$model,
    api_args = list(
      generationConfig = gen_config
    )
  )
}

# Prices per million tokens, by model and modality.
# Update this list when new models or pricing tiers are released.
model_prices <- list(
  "gemini-3.1-flash-image-preview" = list(
    input = list(text = 0.50, image = 0.50),
    output = list(text = 3.00, image = 60.00)
  ),
  "gemini-3-pro-image-preview" = list(
    input = list(text = 1.25, image = 1.25),
    output = list(text = 5.00, image = 60.00)
  )
)

image_cost <- function(chat, model) {
  turn <- chat$last_turn()
  usage <- turn@json$usageMetadata

  prices <- model_prices[[model]]
  if (is.null(prices)) {
    return(0)
  }

  input_cost <- 0
  for (detail in usage$promptTokensDetails) {
    modality <- tolower(detail$modality)
    price <- prices$input[[modality]] %||% prices$input$text
    input_cost <- input_cost + detail$tokenCount * price / 1e6
  }

  output_cost <- 0
  for (detail in usage$candidatesTokensDetails) {
    modality <- tolower(detail$modality)
    price <- prices$output[[modality]] %||% prices$output$text
    output_cost <- output_cost + detail$tokenCount * price / 1e6
  }

  input_cost + output_cost
}

save_generated_image <- function(chat, output_path) {
  turn <- chat$last_turn()
  image_content <- Find(
    function(x) inherits(x, "ellmer::ContentImageInline"),
    turn@contents
  )
  if (is.null(image_content)) {
    text <- paste(
      vapply(
        Filter(function(x) inherits(x, "ellmer::ContentText"), turn@contents),
        function(x) x@text,
        character(1)
      ),
      collapse = "\n"
    )
    cli::cli_warn(c(
      "Gemini did not return an image for {.val {basename(output_path)}}.",
      i = if (nzchar(text)) "Response: {text}"
    ))
    return(invisible(FALSE))
  }
  writeBin(openssl::base64_decode(image_content@data), output_path)
  invisible(TRUE)
}
