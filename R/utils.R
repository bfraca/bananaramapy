resize_images <- function(dir, width = 300) {
  files <- list.files(dir, pattern = "\\.png$", full.names = TRUE)
  for (file in files) {
    img <- magick::image_read(file)
    img <- magick::image_resize(img, paste0(width, "x"))
    magick::image_write(img, file)
    cli::cli_alert_success("Resized {.path {basename(file)}}")
  }
}
