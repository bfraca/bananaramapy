test_that("preprocess_images adds prompt, paths, and ref_images", {
  tmp <- withr::local_tempdir()
  # Create a valid 1x1 PNG image
  png::writePNG(array(1, c(1, 1, 3)), file.path(tmp, "cat.png"))
  output_dir <- file.path(tmp, "output")

  images <- list(
    list(
      name = "img1",
      description = "A [cat] sitting",
      style = "Watercolor"
    ),
    list(
      name = "img2",
      description = "A simple scene",
      style = NULL
    )
  )

  result <- preprocess_images(images, tmp, output_dir)

  expect_equal(result[[1]]$prompt, "Watercolor\n\nA cat (shown in image 1) sitting")
  expect_equal(result[[1]]$output_path, file.path(output_dir, "img1.png"))
  expect_equal(result[[1]]$ref_image_paths, file.path(tmp, "cat.png"))
  expect_length(result[[1]]$ref_images, 1)

  expect_equal(result[[2]]$prompt, "A simple scene")
  expect_equal(result[[2]]$output_path, file.path(output_dir, "img2.png"))
  expect_equal(result[[2]]$ref_image_paths, character())
  expect_length(result[[2]]$ref_images, 0)
})
