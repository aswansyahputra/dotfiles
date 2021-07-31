if (interactive() && requireNamespace("rprofile", quietly = TRUE)) {
  # Startup options
  rprofile::set_startup_options(show.signif.stars = TRUE, max.print = 50)
  # Additional startup options
  options(
    repos = "https://packagemanager.rstudio.com/all/__linux__/focal/latest", 
    download.file.method = "libcurl",
    Ncpus = max(1L, parallel::detectCores() - 1),
    warnPartialMatchArgs = TRUE,
    warnPartialMatchDollar = TRUE,
    warnPartialMatchAttr = TRUE,
    gargle_oauth_email = TRUE,
    usethis.full_name = "Muhammad Aswan Syahputra",
    usethis.description = list(
      `Authors@R` = 'person("Muhammad Aswan", "Syahputra", email = "muhammadaswansyahputra@gmail.com", role = c("aut", "cre"))',
      License = "MIT + file LICENSE",
      Version = "0.0.0.9000"
    ),
    styler.addins_style_transformer = "grkstyle::grk_style_transformer()",
    nvimcom.formatfun = "style_text",
    paint_mask_print = TRUE,
    paint_palette = lapply(c("#fe7f2d","#fcca46","#a1c181","#619b8a","#8b1e3f"), crayon::make_style),
    paint_dark_mode = TRUE,
    paint_max_width = 80
  )

  # Activate useful packages
  suppressMessages(require(usethis))
  suppressMessages(require(conflicted))
  suppressMessages(require(paint))

  # Set conflicted
  conflict_prefer("filter", "dplyr")
  conflict_prefer("select", "dplyr")

  # Not RStudio console
  if (rprofile::is_terminal()) {
    rprofile::set_terminal()
  } else {
    rprofile::set_rstudio()
  }

  .env = rprofile::set_functions()
  attach(.env)
  # Display wifi and no of R sessions
  # Linux only
  rprofile::set_startup_info()
}

# Prints RStudio project on start-up
setHook("rstudio.sessionInit", function(newSession) {
  active_rproj = rprofile::get_active_rproj()
  if (!is.null(active_rproj)) {
    message(glue::glue("{crayon::yellow('R-project:')} {active_rproj}"))
  }
}, action = "append")

grDevices::X11.options(xpos = -3, ypos = 20, width = 8, height = 5, type = "cairo")


