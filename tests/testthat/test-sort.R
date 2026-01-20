test_that("sort_by_dependencies returns empty list unchanged", {
  expect_equal(sort_by_dependencies(list()), list())
})

test_that("sort_by_dependencies returns images without dependencies unchanged", {
  images <- list(
    list(name = "a", description = "Image A"),
    list(name = "b", description = "Image B")
  )
  result <- sort_by_dependencies(images)
  expect_equal(vapply(result, `[[`, character(1), "name"), c("a", "b"))
})

test_that("sort_by_dependencies orders dependencies before dependents", {
  images <- list(
    list(name = "b", description = "Image B", `builds-on` = "a"),
    list(name = "a", description = "Image A")
  )
  result <- sort_by_dependencies(images)
  names <- vapply(result, `[[`, character(1), "name")
  expect_equal(names, c("a", "b"))
})

test_that("sort_by_dependencies handles longer chains", {
  images <- list(
    list(name = "c", description = "Image C", `builds-on` = "b"),
    list(name = "a", description = "Image A"),
    list(name = "b", description = "Image B", `builds-on` = "a")
  )
  result <- sort_by_dependencies(images)
  names <- vapply(result, `[[`, character(1), "name")
  expect_equal(names, c("a", "b", "c"))
})

test_that("sort_by_dependencies handles multiple independent chains", {
  images <- list(
    list(name = "b", description = "Image B", `builds-on` = "a"),
    list(name = "d", description = "Image D", `builds-on` = "c"),
    list(name = "a", description = "Image A"),
    list(name = "c", description = "Image C")
  )
  result <- sort_by_dependencies(images)
  names <- vapply(result, `[[`, character(1), "name")

  # a must come before b, c must come before d
  expect_true(which(names == "a") < which(names == "b"))
  expect_true(which(names == "c") < which(names == "d"))
})

test_that("sort_by_dependencies errors on missing dependency", {
  images <- list(
    list(name = "a", description = "Image A", `builds-on` = "nonexistent")
  )
  expect_error(
    sort_by_dependencies(images),
    "does not exist"
  )
})

test_that("sort_by_dependencies errors on circular dependency", {
  images <- list(
    list(name = "a", description = "Image A", `builds-on` = "b"),
    list(name = "b", description = "Image B", `builds-on` = "a")
  )
  expect_error(
    sort_by_dependencies(images),
    "Circular dependency"
  )
})

test_that("sort_by_dependencies errors on self-reference", {
  images <- list(
    list(name = "a", description = "Image A", `builds-on` = "a")
  )
  expect_error(
    sort_by_dependencies(images),
    "Circular dependency"
  )
})

test_that("sort_by_dependencies errors on longer cycles", {
  images <- list(
    list(name = "a", description = "Image A", `builds-on` = "c"),
    list(name = "b", description = "Image B", `builds-on` = "a"),
    list(name = "c", description = "Image C", `builds-on` = "b")
  )
  expect_error(
    sort_by_dependencies(images),
    "Circular dependency"
  )
})
