# palettes.R — hypsometric ramps, class breaks, and ramp checking
#
# The skill ships ramps, not breaks. Breaks must come from the region's own
# elevation distribution: a coastal plain and a plateau basin need different
# class edges, and reusing another paper's edges produces a map where every
# class boundary falls in the wrong place.

# ---- ramps ----
# Anchor colours, low to high. pal_hypso() interpolates them to whatever class
# count the figure needs. Pick by what the lowland IS, not by taste.
#
#   terrain  green lowland -> yellow -> orange -> red-brown. General purpose.
#   arid     pale sage -> straw -> tan -> deep brown. For basins where green
#            lowland would falsely suggest vegetation.
#   alpine   deep green -> olive -> grey-brown -> pale rock. For high relief
#            where the top class should read as bare rock, not "hottest".
#   muted    the terrain ramp desaturated, for a basemap under heavy overlays
#            (an alternative to relief_rgb(wash =) when you want a fixed set).
#   cvd      blue-green -> khaki -> orange -> brown. Avoids the red/green axis,
#            so classes stay separable under deuteranopia and protanopia.
#   gray     for journals that print figures in black and white. Anchors are
#            evenly spaced in L*, not in RGB, so classes stay equally separable
#            instead of crowding at the light end.
#
# cols is a plain character vector everywhere, so any other ramp works too:
#   relief_rgb(dem, brk, viridisLite::viridis(6))
HYPSO_ANCHORS <- list(
  terrain = c("#6BA857", "#A6CB7E", "#DED28A", "#EEBB6C", "#DB8756", "#AF5138"),
  arid    = c("#9DBE86", "#C6CE95", "#E3D6A0", "#DFB87E", "#C08E62", "#9A6B4C"),
  alpine  = c("#3F7A4E", "#7CA063", "#B0B382", "#C3AE8E", "#B69C90", "#D8CEC6"),
  muted   = c("#A6C79A", "#C8D9AE", "#E7E2BE", "#EFD5AF", "#E0B6A0", "#C99287"),
  cvd     = c("#2E6F6B", "#67998C", "#AFC0A0", "#E4CE96", "#D79A5B", "#9C6134"),
  gray    = c("#E8E8E8", "#C6C6C6", "#A6A6A6", "#868686", "#686868", "#4B4B4B")
)

pal_hypso <- function(name = "terrain", n = 6) {
  stopifnot(name %in% names(HYPSO_ANCHORS), n >= 3)
  grDevices::colorRampPalette(HYPSO_ANCHORS[[name]], space = "Lab")(n)
}

# Neutral ramp for land outside the region of interest, plus a sea ramp.
# Used for the "mask to emphasise" treatment in a country panel.
# Pale enough to recede, saturated enough to still read as sea and land at
# locator size. The first draft ran two steps lighter and the surround went to
# plain white in a 45 mm panel, which reads as missing data rather than context.
PAL_SURROUND <- c("#A3C3DB", "#B5CFE3", "#C6DBEB", "#D7E7F3",   # sea, deep -> shallow
                  "#E2DED5", "#D3CEC3", "#C2BCAF")              # land, low -> high
BRK_SURROUND <- c(-1e5, -4000, -1000, -200, 0, 800, 2500, 1e5)

# ---- breaks from the data ----
# Round-number class edges spanning the DEM's central range. Tails are absorbed
# by the open end classes, so a single snow peak or one sea-level cell cannot
# stretch the ramp and flatten everything else.
#
# Returns length n+1 with +/-1e5 sentinels, ready for relief_rgb().
elev_breaks <- function(d, n = 6, probs = c(0.02, 0.98),
                        steps = c(10, 20, 25, 50, 100, 125, 200, 250, 500, 1000)) {
  stopifnot(n >= 3)
  s <- terra::spatSample(d, min(1e5, terra::ncell(d)), method = "regular",
                         na.rm = TRUE, as.df = TRUE)[, 1]
  q <- stats::quantile(s, probs, na.rm = TRUE)
  step <- steps[which.min(abs(steps - diff(q) / (n - 1)))]
  lo <- ceiling(q[[1]] / step) * step
  inner <- lo + step * seq_len(n - 1) - step
  cat(sprintf("[breaks] p%g-p%g = %.0f-%.0f m, step %g -> %s\n",
              100 * probs[1], 100 * probs[2], q[[1]], q[[2]], step,
              paste(inner, collapse = ", ")))
  c(-1e5, inner, 1e5)
}

# Tick labels for elev_legend(): one per interior boundary, blanking all but
# every `every`-th. Six classes with five 8 pt labels run together into
# "10001250150017502000".
elev_labels <- function(brks, every = 2) {
  inner <- brks[-c(1, length(brks))]
  lab <- format(inner, trim = TRUE, big.mark = "")
  lab[seq_along(lab) %% every != 1] <- ""
  lab
}

# ---- choosing a ramp ----
# You cannot pick a ramp you have not seen on your own terrain. This renders the
# same DEM under every named ramp, at the size it will actually print.
#
#   d      SpatRaster (elevation)
#   file   output PNG
#   ramps  which ramps to show
preview_hypso <- function(d, file = "hypso_preview.png", n = 6,
                          ramps = names(HYPSO_ANCHORS), width_mm = 190,
                          strength = 0.40) {
  brk <- elev_breaks(d, n = n)
  ncol <- min(3, length(ramps)); nrow <- ceiling(length(ramps) / ncol)
  asp <- terra::ncol(d) / terra::nrow(d)
  cell_w <- width_mm / ncol
  ragg::agg_png(file, width = width_mm, height = nrow * (cell_w / asp + 5),
                units = "mm", res = 150, background = "white")
  on.exit(grDevices::dev.off(), add = TRUE)
  graphics::par(mfrow = c(nrow, ncol), mar = c(0, 0, 1.2, 0))
  for (nm in ramps) {
    terra::plotRGB(relief_rgb(d, brk, pal_hypso(nm, n), strength = strength),
                   axes = FALSE, mar = NA)
    graphics::title(nm, cex.main = 0.9, font.main = 1)
  }
  cat("[preview] ", file, "\n", sep = "")
  invisible(file)
}

# ---- checking a ramp ----
# Dichromatic simulation, Vienot-Brettel-Mollon. Applied to sRGB values, which
# is the usual implementation; treat it as indicative, not colorimetric.
simulate_cvd <- function(cols, type = c("deutan", "protan", "tritan")) {
  type <- match.arg(type)
  M <- matrix(c(17.8824, 43.5161, 4.11935,
                3.45565, 27.1554, 3.86714,
                0.0299566, 0.184309, 1.46709), 3, 3, byrow = TRUE)
  S <- switch(type,
    deutan = matrix(c(1, 0, 0, 0.494207, 0, 1.24827, 0, 0, 1), 3, 3, byrow = TRUE),
    protan = matrix(c(0, 2.02344, -2.52581, 0, 1, 0, 0, 0, 1), 3, 3, byrow = TRUE),
    tritan = matrix(c(1, 0, 0, 0, 1, 0, -0.395913, 0.801109, 0), 3, 3, byrow = TRUE))
  rgb <- grDevices::col2rgb(cols)
  out <- solve(M) %*% S %*% M %*% rgb
  out <- pmin(pmax(out, 0), 255)
  grDevices::rgb(out[1, ], out[2, ], out[3, ], maxColorValue = 255)
}

# Smallest Lab distance between adjacent classes, in normal vision and under
# each dichromacy. Adjacent classes are what a reader compares, so that is the
# pair that has to stay apart; distant classes may look alike without harm.
#
# `min_d` is a working threshold, not a standard: below roughly 10 the boundary
# between two bands stops being visible at 8 pt legend size.
#
# The verdict covers `require` only. Greyscale is always reported but excluded
# by default, because no hypsometric colour ramp survives a black-and-white
# print: across the ramps here greyscale separation runs 1.5 to 8.4. When the
# journal prints in B/W the answer is the `gray` ramp, not a tweak to a colour
# one, so add "gray" to `require` and switch ramps when it fails.
# Rec.601 luminance, for judging what survives a black-and-white print.
# grDevices::rgb() takes an n x 3 matrix, not 3 x n.
to_gray <- function(cols) {
  y <- colSums(grDevices::col2rgb(cols) * c(0.299, 0.587, 0.114))
  grDevices::rgb(cbind(y, y, y), maxColorValue = 255)
}

check_ramp <- function(cols, min_d = 10, verbose = TRUE,
                       require = c("normal", "deutan", "protan")) {
  lab <- function(x) grDevices::convertColor(t(grDevices::col2rgb(x)) / 255,
                                             "sRGB", "Lab")
  adj_min <- function(x) {
    L <- lab(x)
    min(sqrt(rowSums((L[-1, , drop = FALSE] - L[-nrow(L), , drop = FALSE])^2)))
  }
  res <- c(normal = adj_min(cols),
           deutan = adj_min(simulate_cvd(cols, "deutan")),
           protan = adj_min(simulate_cvd(cols, "protan")),
           gray   = adj_min(to_gray(cols)))
  ok <- min(res[require]) >= min_d
  if (verbose) cat(sprintf(
    "[ramp] adjacent-class min Lab:  normal %.1f  deutan %.1f  protan %.1f  gray %.1f   %s\n",
    res[["normal"]], res[["deutan"]], res[["protan"]], res[["gray"]],
    if (ok) "OK" else sprintf("FAIL (%s below %g)",
      paste(require[res[require] < min_d], collapse = ", "), min_d)))
  invisible(res)
}

# ---- discipline ----
# The study-area accent colour must appear nowhere else in the figure. Call this
# after choosing point/line palettes; it compares in Lab space, because two
# reds that differ in hex can still read as the same colour in print.
assert_accent_unique <- function(accent, others, min_dist = 25) {
  lab <- function(x) grDevices::convertColor(t(grDevices::col2rgb(x)) / 255,
                                             "sRGB", "Lab")
  a <- lab(accent); o <- lab(others)
  dist <- sqrt(rowSums((o - matrix(a, nrow(o), 3, byrow = TRUE))^2))
  bad <- others[dist < min_dist]
  if (length(bad)) stop(sprintf(
    "accent %s collides with: %s (Lab distance %s < %g). Change the symbol's SHAPE, not the accent.",
    accent, paste(bad, collapse = ", "), paste(round(dist[dist < min_dist], 1), collapse = ", "),
    min_dist))
  invisible(TRUE)
}
