if (interactive() && requireNamespace("rprofile", quietly = TRUE)) {
  # Startup options
  rprofile::set_startup_options(show.signif.stars = TRUE, max.print = 50)
  # Additional startup options
  options(
    repos = c(rspm = "https://packagemanager.rstudio.com/all/latest"),
    download.file.method = "libcurl",
    Ncpus = max(1L, parallel::detectCores() - 1),
    warnPartialMatchArgs = TRUE,
    warnPartialMatchDollar = TRUE,
    warnPartialMatchAttr = TRUE,
    gargle_oauth_email = TRUE,
    usethis.full_name = "Muhammad Aswan Syahputra",
    usethis.protocol  = "ssh",
    usethis.description = list(
      "Authors@R" = utils::person(
        first = "Muhammad Aswan",
        last = "Syahputra",
        email = "muhammadaswansyahputra@gmail.com",
        role = c("aut", "cre")
      ),
      License = "MIT + file LICENSE",
      Version = "0.0.0.9000"
    ),
    usethis.destdir = "~/personal",
    styler.addins_style_transformer = "grkstyle::grk_style_transformer()"
  )
  # Activate useful packages
  suppressMessages(require(usethis))
  suppressMessages(require(conflicted))
  
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
