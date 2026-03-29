test_that("compute_output_paths sets output_paths", {
  output_dir <- "/tmp/output"

  images <- list(
    list(name = "img1", n = 1L),
    list(name = "img2", n = 3L)
  )

  result <- compute_output_paths(images, output_dir)

  expect_equal(result[[1]]$output_paths, file.path(output_dir, "img1.png"))
  expect_equal(
    result[[2]]$output_paths,
    file.path(output_dir, c("img2-1.png", "img2-2.png", "img2-3.png"))
  )
})

test_that("preprocess_image adds prompt, paths, and ref_images", {
  tmp <- withr::local_tempdir()
  png::writePNG(array(1, c(1, 1, 3)), file.path(tmp, "cat.png"))

  img1 <- list(
    name = "img1",
    description = "A [cat] sitting",
    style = "Watercolor"
  )
  result1 <- preprocess_image(img1, tmp)
  expect_equal(
    result1$prompt,
    "A cat (shown in image 1) sitting\n\nStyle: Watercolor"
  )
  expect_equal(result1$ref_image_paths, file.path(tmp, "cat.png"))
  expect_length(result1$ref_images, 1)

  img2 <- list(
    name = "img2",
    description = "A simple scene",
    style = NULL
  )
  result2 <- preprocess_image(img2, tmp)
  expect_equal(result2$prompt, "A simple scene")
  expect_equal(result2$ref_image_paths, character())
  expect_length(result2$ref_images, 0)
})

test_that("preprocess_image handles placeholders in style", {
  tmp <- withr::local_tempdir()
  png::writePNG(array(1, c(1, 1, 3)), file.path(tmp, "monet.png"))
  png::writePNG(array(1, c(1, 1, 3)), file.path(tmp, "cat.png"))

  img <- list(
    name = "img1",
    description = "A [cat] sitting",
    style = "In the style of [monet]"
  )

  result <- preprocess_image(img, tmp)

  expect_equal(
    result$prompt,
    "A cat (shown in image 2) sitting\n\nStyle: In the style of monet (shown in image 1)"
  )
  expect_equal(
    result$ref_image_paths,
    c(file.path(tmp, "monet.png"), file.path(tmp, "cat.png"))
  )
  expect_length(result$ref_images, 2)
})

test_that("model_prices covers known models", {
  expect_named(
    model_prices,
    c(
      "gemini-3.1-flash-image-preview",
      "gemini-3-pro-image-preview"
    )
  )
  for (model in names(model_prices)) {
    prices <- model_prices[[model]]
    expect_named(prices, c("input", "output"))
    expect_true("text" %in% names(prices$input))
    expect_true("image" %in% names(prices$output))
  }
})

test_that("compute_output_paths expands n into multiple output_paths", {
  output_dir <- "/tmp/output"

  images <- list(
    list(name = "bicycle", n = 3L),
    list(name = "car", n = 1L)
  )

  result <- compute_output_paths(images, output_dir)

  expect_equal(
    result[[1]]$output_paths,
    file.path(output_dir, c("bicycle-1.png", "bicycle-2.png", "bicycle-3.png"))
  )
  expect_equal(result[[2]]$output_paths, file.path(output_dir, "car.png"))
})
