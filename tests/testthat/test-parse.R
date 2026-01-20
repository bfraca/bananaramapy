test_that("parse_defaults handles missing defaults", {
  result <- parse_defaults(NULL)
  expect_equal(result$model, "gemini-2.5-flash-image")
  expect_null(result$style)
  expect_equal(result$`aspect-ratio`, "1:1")
  expect_equal(result$resolution, "1K")
})

test_that("parse_defaults extracts values from named list", {
  defaults <- list(
    style = "chunky gouache",
    `aspect-ratio` = "16:9",
    resolution = "2K",
    model = "gemini-3-pro-image-preview"
  )
  result <- parse_defaults(defaults)
  expect_equal(result$model, "gemini-3-pro-image-preview")
  expect_equal(result$style, "chunky gouache")
  expect_equal(result$`aspect-ratio`, "16:9")
  expect_equal(result$resolution, "2K")
})

test_that("parse_images errors on missing name", {
  images <- list(list(description = "A picture"))
  expect_error(
    parse_images(images, list()),
    "name"
  )
})

test_that("parse_images errors on missing description", {
  images <- list(list(name = "test"))
  expect_error(
    parse_images(images, list()),
    "description"
  )
})

test_that("parse_images merges defaults with overrides", {
  defaults <- list(
    model = "gemini-2.5-flash-image",
    style = "default style",
    `aspect-ratio` = "1:1",
    resolution = "1K"
  )
  images <- list(
    list(name = "img1", description = "desc1"),
    list(name = "img2", description = "desc2", `aspect-ratio` = "16:9"),
    list(
      name = "img3",
      description = "desc3",
      model = "gemini-3-pro-image-preview"
    )
  )

  result <- parse_images(images, defaults)

  expect_equal(result[[1]]$model, "gemini-2.5-flash-image")
  expect_equal(result[[1]]$style, "default style")
  expect_equal(result[[1]]$`aspect-ratio`, "1:1")
  expect_equal(result[[2]]$style, "default style")
  expect_equal(result[[2]]$`aspect-ratio`, "16:9")
  expect_equal(result[[3]]$model, "gemini-3-pro-image-preview")
})

test_that("resolve_placeholders returns unchanged text without placeholders", {
  result <- resolve_placeholders("A simple description", tempdir())
  expect_equal(result$text, "A simple description")
  expect_equal(result$images, character())
})

test_that("resolve_placeholders replaces placeholders with hybrid references", {
  # Create temp images
  tmp <- withr::local_tempdir()
  file.create(file.path(tmp, "hadley.jpg"))
  file.create(file.path(tmp, "robot.png"))

  result <- resolve_placeholders("Draw [hadley] with [robot] in a garden", tmp)

  expect_equal(
    result$text,
    "Draw hadley (shown in image 1) with robot (shown in image 2) in a garden"
  )
  expect_equal(
    result$images,
    c(file.path(tmp, "hadley.jpg"), file.path(tmp, "robot.png"))
  )
})

test_that("resolve_placeholders handles repeated placeholders", {
  tmp <- withr::local_tempdir()
  file.create(file.path(tmp, "robot.png"))

  result <- resolve_placeholders("A [robot] meets another [robot]", tmp)

  expect_equal(
    result$text,
    "A robot (shown in image 1) meets another robot (shown in image 2)"
  )
  expect_length(result$images, 2)
})

test_that("find_image_file finds png files", {
  tmp <- withr::local_tempdir()
  file.create(file.path(tmp, "test.png"))

  result <- find_image_file("test", tmp)
  expect_equal(result, file.path(tmp, "test.png"))
})

test_that("find_image_file finds jpg files", {
  tmp <- withr::local_tempdir()
  file.create(file.path(tmp, "test.jpg"))

  result <- find_image_file("test", tmp)
  expect_equal(result, file.path(tmp, "test.jpg"))
})

test_that("find_image_file errors on missing file", {
  tmp <- withr::local_tempdir()
  expect_error(
    find_image_file("nonexistent", tmp),
    "Cannot find reference image"
  )
})

test_that("build_prompt combines style and description", {
  result <- build_prompt("Draw a cat", "Watercolor style")
  expect_equal(result, "Watercolor style\n\nDraw a cat")
})

test_that("build_prompt handles NULL style", {
  result <- build_prompt("Draw a cat", NULL)
  expect_equal(result, "Draw a cat")
})

test_that("build_prompt handles empty style", {
  result <- build_prompt("Draw a cat", "")
  expect_equal(result, "Draw a cat")
})
