# thematic.R -- thematic content on a study-area panel: land-use and other
# categorical rasters, graduated point symbols, and a hand-drawn legend block
# for any mix of fill, point and line keys.
#
# Source relief_basemap.R first; this file uses its constants (LW, TXT_PT,
# TXT_GG), frac_fun(), assert_inside() and shade_factor().

# ---------------------------------------------------------- categorical ------

# Class codes -> RGB raster, optionally multiplied by hillshade.
#
# Colouring by lookup instead of a fill scale keeps every class at its exact
# colour, lets relief sit under the classes the same way it does in
# relief_rgb(), and pairs with legend_rows_block(), which draws the legend by
# hand because an RGB raster has no guide.
#
#   r         single-layer SpatRaster of integer class codes
#   codes     class codes, in legend order
#   cols      one colour per code
#   dem       optional elevation raster on the same grid as r; adds relief
#   strength  hillshade swing; keep lower than for a hypsometric basemap
#             (0.15-0.25), or shading starts to read as a class boundary
#
# Every code present in r must be listed: an unlisted code would otherwise draw
# as a hole that looks like no-data. Class shares are printed so that a class
# too small to see at print size is noticed before it earns a legend row.
class_rgb <- function(r, codes, cols, dem = NULL, strength = 0.20,
                      alt = 40, azim = 315, min_share = 0.005) {
  stopifnot(length(codes) == length(cols))
  v   <- as.vector(values(r)[, 1])
  idx <- match(v, codes)
  unknown <- sort(unique(v[!is.na(v) & is.na(idx)]))
  if (length(unknown)) stop(sprintf(
    "class codes without a colour: %s. List every code present in the raster.",
    paste(unknown, collapse = ", ")))
  ok <- !is.na(idx)
  f <- rep(1, length(v))
  if (!is.null(dem)) {
    if (!isTRUE(terra::compareGeom(r, dem, stopOnError = FALSE)))
      stop("dem must share the class raster's grid; resample it with terra::resample(dem, r)")
    f <- shade_factor(dem, strength, alt, azim)
  }

  cm  <- grDevices::col2rgb(cols)
  out <- matrix(NA_real_, length(v), 3)
  out[ok, ] <- t(cm[, idx[ok]]) * f[ok]
  rr <- rast(r, nlyrs = 3)
  values(rr) <- pmin(pmax(out, 0), 255)
  names(rr) <- c("r", "g", "b")
  terra::RGB(rr) <- 1:3

  share <- tabulate(idx[ok], nbins = length(codes)) / sum(ok)
  cat(sprintf("[classes] %s\n", paste(sprintf("%s %.1f%%", codes, 100 * share),
                                      collapse = "  ")))
  small <- codes[share < min_share]
  if (length(small)) warning(sprintf(
    "classes below %.1f%% of the panel will barely show at print size: %s",
    100 * min_share, paste(small, collapse = ", ")))
  rr
}

# ---------------------------------------------------------- graduated --------

# Graduated point sizes: class a numeric variable into a few size steps.
#
# A few discrete sizes read better than a continuous size scale at locator
# scale, and a hand-drawn legend can show exactly the sizes on the map.
#
#   x       numeric values
#   breaks  class edges, length length(sizes) + 1; open ends allowed (-Inf/Inf)
#   sizes   ggplot point sizes, small to large; the same numbers go to
#           geom_sf(size =) and to legend_rows_block(), so the key matches
#   digits  rounding for the generated labels
graduated_sizes <- function(x, breaks, sizes, digits = 1) {
  stopifnot(length(breaks) == length(sizes) + 1)
  k <- findInterval(x, breaks, rightmost.closed = TRUE, all.inside = TRUE)
  b <- round(breaks, digits)
  labs <- ifelse(is.infinite(breaks[-length(breaks)]), paste0("< ", b[-1]),
          ifelse(is.infinite(breaks[-1]), paste0("≥ ", b[-length(b)]),
                 paste0(b[-length(b)], "–", b[-1])))
  n <- tabulate(k, nbins = length(sizes))
  cat(sprintf("[sizes] %s\n", paste(sprintf("%s: %d", labs, n), collapse = "  ")))
  list(size = sizes[k], class = k, labels = labs, sizes = sizes)
}

# ---------------------------------------------------------- legend block -----

# One legend block for fill, point and line keys, laid out in millimetres.
#
# Text height is fixed in points, so a block spaced in panel fractions only fits
# the panel it was tuned on. Everything inside this block is computed in mm from
# the panel's printed size, then converted to data coordinates; only the anchor
# is a fraction. Label widths are measured from the registered font, so the
# backing hugs the text instead of guessing.
#
#   items  data.frame with columns
#            label  text
#            type   "fill", "point" or "line"
#          and optionally colour, fill, shape, size, linetype, linewidth
#          (missing columns get sensible defaults). Use the same values the
#          map layers use, so the key is the symbol.
#   panel_w_mm, panel_h_mm  printed panel size
#   anchor  corner of the backing, as fractions of the panel
#   corner  which corner of the block `anchor` is: "br", "bl", "tr" or "tl"
#   ncol    columns; items fill down each column in order
#   title   optional title row
#   backing draw the white backing and border; FALSE for a legend placed
#           outside the map in legend_panel()
#
# Returns a list of annotate() layers with attributes "extent", the block's
# c(x0, x1, y0, y1) in panel fractions, for checking it against a reserved area,
# and "size_mm", its c(width, height).
legend_rows_block <- function(win, items, panel_w_mm, panel_h_mm,
                              anchor = c(0.972, 0.032), corner = "br",
                              ncol = 1, title = NULL,
                              key_mm = 3.0, gap_mm = 1.2, row_gap_mm = 0.9,
                              col_gap_mm = 3.0, pad_mm = 1.2,
                              text_pt = TXT_PT, family = "Arial", backing = TRUE) {
  stopifnot(all(c("label", "type") %in% names(items)),
            all(items$type %in% c("fill", "point", "line")))
  def <- list(colour = "grey25", fill = NA, shape = 21, size = 1.6,
              linetype = "solid", linewidth = LW)
  for (nm in names(def)) if (!nm %in% names(items)) items[[nm]] <- def[[nm]]

  pt_mm <- 25.4 / 72
  txt_h <- text_pt * pt_mm
  # string_width() returns whole pixels; at res = 72 that rounds to whole points
  # and undershoots by ~5%. res = 720 matches the rendered width within 1%.
  width_mm <- function(s) systemfonts::string_width(s, family = family,
                                                    size = text_pt, res = 720) / 10 * pt_mm
  row_h <- max(key_mm, txt_h) + row_gap_mm
  n     <- nrow(items)
  nrow_ <- ceiling(n / ncol)
  col_of <- (seq_len(n) - 1) %/% nrow_ + 1
  row_of <- (seq_len(n) - 1) %% nrow_ + 1
  col_w  <- vapply(seq_len(ncol), function(j)
    key_mm + gap_mm + max(width_mm(items$label[col_of == j]), 0), numeric(1))
  title_h <- if (is.null(title)) 0 else txt_h + row_gap_mm
  inner_w <- max(sum(col_w) + col_gap_mm * (ncol - 1),
                 if (is.null(title)) 0 else width_mm(title))
  block_w <- inner_w + 2 * pad_mm
  block_h <- title_h + nrow_ * row_h - row_gap_mm + 2 * pad_mm

  # block position in mm from the panel's bottom-left
  ax <- anchor[1] * panel_w_mm; ay <- anchor[2] * panel_h_mm
  x0 <- if (substr(corner, 2, 2) == "r") ax - block_w else ax
  y0 <- if (substr(corner, 1, 1) == "t") ay - block_h else ay
  ext <- c(x0 / panel_w_mm, (x0 + block_w) / panel_w_mm,
           y0 / panel_h_mm, (y0 + block_h) / panel_h_mm)
  assert_inside(ext[1:2], ext[3:4], what = "legend block")

  f  <- frac_fun(win)
  X  <- function(mm) f$fx(mm / panel_w_mm)
  Y  <- function(mm) f$fy(mm / panel_h_mm)
  top <- y0 + block_h - pad_mm
  cx  <- x0 + pad_mm + c(0, cumsum(col_w + col_gap_mm))[col_of]   # key left edge
  cy  <- top - title_h - (row_of - 0.5) * row_h + row_gap_mm / 2   # row centre

  layers <- if (backing) list(annotate("rect", xmin = X(x0), xmax = X(x0 + block_w),
                                       ymin = Y(y0), ymax = Y(y0 + block_h),
                                       fill = "white", alpha = 0.88, colour = "grey35",
                                       linewidth = LW * 0.6)) else list()
  if (!is.null(title)) layers <- c(layers, list(
    annotate("text", x = X(x0 + pad_mm), y = Y(top - txt_h / 2), label = title,
             hjust = 0, size = text_pt / ggplot2::.pt, family = family)))
  for (i in seq_len(n)) {
    it <- items[i, ]; k0 <- cx[i]; k1 <- cx[i] + key_mm
    layers <- c(layers, list(switch(it$type,
      fill  = annotate("rect", xmin = X(k0), xmax = X(k1),
                       ymin = Y(cy[i] - key_mm * 0.35), ymax = Y(cy[i] + key_mm * 0.35),
                       fill = it$fill, colour = it$colour, linewidth = LW * 0.5),
      point = annotate("point", x = X(k0 + key_mm / 2), y = Y(cy[i]),
                       shape = it$shape, size = it$size, colour = it$colour,
                       fill = it$fill),
      line  = annotate("segment", x = X(k0), xend = X(k1), y = Y(cy[i]), yend = Y(cy[i]),
                       colour = it$colour, linetype = it$linetype,
                       linewidth = it$linewidth))))
    layers <- c(layers, list(annotate("text", x = X(k1 + gap_mm), y = Y(cy[i]),
                                      label = it$label, hjust = 0,
                                      size = text_pt / ggplot2::.pt, family = family)))
  }
  structure(layers, extent = ext, size_mm = c(block_w, block_h))
}

# ---------------------------------------------------------- outside legends --

# A blank panel whose data coordinates are millimetres, for legends placed
# outside the map. An in-panel legend needs an empty corner; in small multiples
# (a 2 x 2 set at 60 mm per panel) a class legend covers half the panel or more,
# and pad_until_clear() fails, which is the signal to move it here. The legend
# builders take mm_win(w, h) as their window and the same w, h as panel size.
mm_win <- function(w_mm, h_mm) c(xmin = 0, xmax = w_mm, ymin = 0, ymax = h_mm)

legend_panel <- function(w_mm, h_mm, ...) {
  ggplot() + list(...) +
    coord_cartesian(xlim = c(0, w_mm), ylim = c(0, h_mm), expand = FALSE) +
    theme_void() + theme(plot.margin = margin(0, 0, 0, 0))
}

# Does a block stay inside the area reserved for it? Use with a window padded by
# pad_until_clear() for that area, so the block cannot land on the study area.
assert_within_reserved <- function(block, x, y, what = "legend block") {
  e <- attr(block, "extent")
  if (e[1] < x[1] || e[2] > x[2] || e[3] < y[1] || e[4] > y[2]) stop(sprintf(
    "%s (x %.3f-%.3f, y %.3f-%.3f) exceeds its reserved area (x %.3f-%.3f, y %.3f-%.3f). Enlarge the reserved area and re-pad the window, use ncol = 2, or move the legend outside the panel.",
    what, e[1], e[2], e[3], e[4], x[1], x[2], y[1], y[2]))
  invisible(TRUE)
}
