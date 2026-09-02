---
name: study-area-map
description: Use when building a study-area location or setting map for a paper — nested locator panels (country → province → site), shaded-relief DEM basemaps, multi-panel map composition, zoom leader lines, in-panel map legends, north arrows and scale bars — in R with ggplot2 + sf + terra. Also covers sourcing boundary and elevation data, including reading ArcGIS and MapGIS files.
---

# study-area-map

This skill covers what is specific to maps: projection, window, relief, panel composition, and map furniture. `relief_basemap.R` is self-contained — it sets `LW`, `LW_DAT`, `TXT_PT`, `TXT_GG`, registers a font and supplies `theme_map_pub()`, but only where those names are not already defined, so a house-style preamble loaded alongside it still wins.

The two overlap at rfigure.skill's *China Maps And Site Distributions* section. This skill goes further there, and corrects one measured error in it — see **Composition**.

## Reference implementation

Two project-independent modules under `reference/`. Source `relief_basemap.R`
first; it carries the typographic constants, font registration and map theme
that `palettes.R` and the figure script rely on.

- **`relief_basemap.R`** — `ensure_font()`, `theme_map_pub()`,
  `inscribed_window()`, `fit_aspect()`, `win_aspect()`, `load_dem()` with its
  no-data assertion, `locate_na()`, `relief_rgb()`, `north_needle()`,
  `elev_legend()`, `legend_backing()`, `pin_panel()`, `panel_margins()`,
  `with_font_device()`, `box_in()`, `add_leaders()`
- **`palettes.R`** — `pal_hypso()`, `elev_breaks()`, `elev_labels()`,
  `assert_accent_unique()`, `PAL_SURROUND`/`BRK_SURROUND`

Set the region constants in the figure script, not in the modules. That is what
lets several figures in one paper share one basemap.

## Decide before drawing

A locator map answers one question: *where is this, and why does the location matter?* Everything that does not serve that question is clutter.

Fix these three before writing code, because each one constrains the layout:

**How many zoom levels.** Two (country → site) is usually enough. Three (country → province → site) only when the province is itself the reason — an administrative dataset, a provincial policy, a regional geological unit. Each extra level costs a panel and buys less than the previous one.

**One accent colour means "study area", everywhere.** Country panel highlight, province panel outline, main-panel boundary — all the same hex. If the main panel draws its boundary in black while the locators use red, the reader is decoding two symbols for one object. Reserve that hex: nothing else in the figure may use it, including point fills.

**What the main panel must show that a plain outline cannot.** Usually the terrain reason for the study: a basin floor against its mountain rim, a coastal gradient, a fault-bounded graben. If the answer is "nothing", the relief basemap is decoration and a clean vector map is better.

## Projection and window

Use one projected CRS for every layer — polygons, lines, points, labels, rasters. Never mix raw lon/lat with projected `geom_sf()`.

### Take the inscribed rectangle, not the bounding box

A lon/lat rectangle transformed into a conic projection is a **curved quadrilateral**, not a rectangle. Both naive choices fail:

- `st_bbox()` of the transformed rectangle → corners fall *outside* the data, leaving blank wedges in the frame.
- Feeding lon/lat limits to `coord_sf(default_crs = 4326)` → the same curvature, handled invisibly.

For a raster basemap that must fill the frame edge to edge, take the **inscribed** rectangle: sample each geographic edge, then take the innermost x on the left edge, outermost-innermost on the right, and likewise for y.

```r
to_m <- function(lon, lat, crs) sf::st_coordinates(sf::st_transform(
  sf::st_as_sf(data.frame(x = lon, y = lat), coords = c("x", "y"), crs = 4326), crs))

n  <- 400
sL <- to_m(rep(LON[1], n), seq(LAT[1], LAT[2], length.out = n), CRS_M)
sR <- to_m(rep(LON[2], n), seq(LAT[1], LAT[2], length.out = n), CRS_M)
sB <- to_m(seq(LON[1], LON[2], length.out = n), rep(LAT[1], n), CRS_M)
sT <- to_m(seq(LON[1], LON[2], length.out = n), rep(LAT[2], n), CRS_M)
W <- c(xmin = max(sL[, 1]), xmax = min(sR[, 1]),
       ymin = max(sB[, 2]), ymax = min(sT[, 2]))
```

The mirror-image failure is worse and quieter: for a **country panel**, taking the bbox of a transformed lon/lat rectangle *clips real land*. In a Lambert projection of China, a 73–136°E × 17.5–54.5°N rectangle loses roughly 600 km off the south — Yunnan, Guangxi, Guangdong, Hainan, Taiwan, Hong Kong and Macau all vanish, and the map still looks plausible. For country panels take `st_bbox()` of the **data**, never of a coordinate rectangle.

Take it from *every* layer that has to fit, via `bbox_union()`. One layer's bbox is not a proxy for the others, and boundary-line layers are the usual trap: they frequently hold only selected segments — disputed sections, maritime lines — so their extent can stop far short of the polygons. A real case: a national line layer whose northernmost feature sat at 38.68°N, used alone as the window, cut 14.9° of latitude and 12.3° of longitude off a country map and dropped 99 prefecture units. The frame still looked like a plausible map.

Then verify rather than eyeball it — at locator-panel size a missing province is invisible:

```r
clip <- sf::st_as_sfc(sf::st_bbox(W, crs = sf::st_crs(prov)))
stopifnot(all(lengths(sf::st_within(sf::st_geometry(prov), clip)) > 0))
```

### coord_sf() goes last, and prove it

`geom_sf()` does not return a layer. It returns a list containing the layer **and a default `coord_sf()`**, and adding any coord replaces the one already on the plot. So a single `geom_sf()` placed after your `coord_sf(xlim =, ylim =)` throws the limits away and the panel silently falls back to the data extent.

```r
rng <- function(p) { bp <- ggplot_build(p)$layout$panel_params[[1]]
                     c(bp$x_range, bp$y_range) }
p <- ggplot() + geom_sf(data = pt) + coord_sf(xlim = c(2, 4), ylim = c(2, 4), expand = FALSE)
rng(p)                      # 2 4 2 4
rng(p + geom_sf(data = pt)) # -0.5 10.5 -0.5 10.5
```

ggplot's only warning is an easily-missed `Adding new coordinate system, which will replace the existing one`, and the figure still looks like a map — just of the wrong extent, at the wrong aspect, letterboxed inside its slot with a band of white where the reader expects data.

Two consequences. Never put `coord_sf()` inside a layer list that a caller might extend — a `map_layers()` helper must return layers only. And check the built plot rather than trusting the code:

```r
assert_window(p, W)   # compares ggplot_build()'s panel range against the window
```

### Fix the slot first, then expand the window

`coord_sf()` enforces a fixed aspect ratio. Drop a map into a layout slot whose shape differs and it letterboxes *inside* that slot: the drawn panel is narrower than its cell, and two side-by-side locator panels end up visibly unequal. Hand-tuned offsets never converge.

Reverse the order. Compute the exact slot size in mm, then expand each geographic window outward — only ever outward, so no content is lost — until it matches that slot's aspect ratio.

```r
fit_aspect <- function(bb, target) {
  dx <- bb[["xmax"]] - bb[["xmin"]]; dy <- bb[["ymax"]] - bb[["ymin"]]
  if (dx / dy < target) {
    pad <- (target * dy - dx) / 2
    bb[["xmin"]] <- bb[["xmin"]] - pad; bb[["xmax"]] <- bb[["xmax"]] + pad
  } else {
    pad <- (dx / target - dy) / 2
    bb[["ymin"]] <- bb[["ymin"]] - pad; bb[["ymax"]] <- bb[["ymax"]] + pad
  }
  bb
}
W_CN <- fit_aspect(W_CN, slot_w_mm / slot_h_mm)
```

With the window matched to the slot, `panel` fills its cell exactly and every frame in the figure is the same width.

## Relief basemap

### Multiply the hillshade in, never alpha-blend it

The reflex — hillshade layer, hypsometric raster on top at `alpha = 0.5` — washes every colour toward grey. Raising alpha buries the relief; lowering it buries the colour. There is no setting that gives both, because alpha compositing *interpolates toward the layer underneath* instead of modulating brightness.

Classify the elevation, look up the class colour, **multiply** by a hillshade coefficient normalised to mean 1, and emit an RGB raster. Classed bands stay crisp, relief stays visible, saturation is untouched.

```r
relief_rgb <- function(d, brks, cols, strength = 0.45, wash = 0, alt = 40, azim = 315) {
  sh  <- terra::shade(terra::terrain(d, "slope",  unit = "radians"),
                      terra::terrain(d, "aspect", unit = "radians"),
                      angle = alt, direction = azim)
  v   <- as.vector(terra::values(d)[, 1])
  shv <- as.vector(terra::values(sh)[, 1])
  ok  <- !is.na(v)
  shn <- shv / mean(shv, na.rm = TRUE) * 0.5    # mean -> 0.5, so f averages 1
  shn[is.na(shn)] <- 0.5
  f <- 1 + strength * pmin(pmax((shn - 0.5) * 2, -1), 1)

  cm  <- grDevices::col2rgb(cols) * (1 - wash) + 255 * wash
  idx <- findInterval(v, brks, rightmost.closed = TRUE, all.inside = TRUE)
  out <- matrix(NA_real_, length(v), 3)
  out[ok, ] <- t(cm[, idx[ok]]) * f[ok]

  r <- terra::rast(d, nlyrs = 3)
  terra::values(r) <- pmin(pmax(out, 0), 255)
  terra::RGB(r) <- 1:3
  r
}
```

Draw with `tidyterra::geom_spatraster_rgb()`.

`strength` sets the light/shade swing (0.35–0.45 reads well in print; above 0.55 the shading starts to swamp the classes). `wash` lerps toward white — use 0.20–0.30 for a basemap that carries hundreds of overlaid symbols, 0 for a basemap that *is* the message.

**Classed, not continuous.** Discrete elevation bands give the reader a boundary to hold on to — "the basin floor is the green band" — and they survive greyscale printing. A continuous ramp turns into an undifferentiated smear at 90 mm wide.

### Palette: ship the ramp, derive the breaks

A ramp is reusable; class edges are not. A coastal plain and a plateau basin need different edges, and inheriting another paper's edges puts every boundary in the wrong place — usually producing one class that covers 80% of the map.

`palettes.R` separates the two. `pal_hypso(name, n)` interpolates a named ramp to any class count; `elev_breaks(d, n)` derives round-number edges from the DEM's own 2nd–98th percentile range, letting the open end classes absorb the tails so a single peak cannot stretch the ramp.

```r
brk  <- elev_breaks(dem, n = 6)              # -> [breaks] p2-p98 = 856-1966 m, step 200
cols <- pal_hypso("terrain", length(brk) - 1)
rel  <- relief_rgb(dem, brk, cols, strength = 0.42)
elev_legend(win, cols, elev_labels(brk))     # blanks alternate labels
```

Six ramps, chosen by what the lowland *is*, not by taste: `terrain` (green lowland, general purpose), `arid` (for basins where green would falsely imply vegetation), `alpine` (top class reads as bare rock rather than "hottest"), `muted` (desaturated, an alternative to `relief_rgb(wash = )`), `cvd` (avoids the red/green axis), `gray` (black-and-white printing, anchors spaced evenly in L*). `cols` is a plain character vector throughout, so any other ramp works.

**Show the candidates on the actual terrain before choosing.** `preview_hypso(dem)` renders one DEM under every ramp; a ramp that looks right as swatches often collapses on real relief.

**Then measure separability.** `check_ramp(cols)` reports the smallest Lab distance between *adjacent* classes under normal vision, deuteranopia, protanopia and greyscale — adjacent classes are the pair a reader compares. Measured at six classes: `terrain` 17.1 normal but 4.7 under protanopia; `cvd` holds 19.0/14.5; every colour ramp falls to 1.5–8.4 in greyscale. Two rules follow. When the journal prints in black and white, switch to `gray` rather than tuning a colour ramp. When colour-vision safety matters, `cvd` is the only colour ramp here that survives.

Class count 5–8. Below 5 the relief structure collapses; above 8 adjacent bands stop being distinguishable — `terrain` drops from 21.4 at five classes to 9.4 at ten, and to 0.5 under protanopia.

The accent colour rule is enforceable, not just advisory. `assert_accent_unique()` compares in Lab space, because two reds that differ in hex still read as one colour in print:

```r
assert_accent_unique("#C62828", c(point_fills, river_col, county_col))
# stops with: accent #C62828 collides with #C0392B (Lab distance 7.5 < 25).
# Change the symbol's SHAPE, not the accent.
```

### Assert the no-data fraction

A window that overruns the DEM tile coverage produces a blank sliver along one frame edge. At preview scale it hides under a scale bar or legend and reaches the journal.

Make the loader assert it, and print the figure. When the assertion fires, locate the cells before touching the window — the fix depends on which edge:

```r
na <- terra::global(is.na(d), "mean", na.rm = FALSE)[[1]]
cat(sprintf("[DEM] %s  no-data %.3f%%\n", paste(dim(d), collapse = "x"), 100 * na))
stopifnot(na <= max_na)

# when it fires:
xy <- terra::xyFromCell(d, which(is.na(terra::values(d)[, 1])))
# convert to panel-relative fractions to see which edge is short
```

### Mask to emphasise, veil to de-emphasise

Two treatments, two jobs:

**Mask** when the panel's job is to make a shape recognisable — a country in a country panel. Render the surrounding world in a muted grey/blue ramp, then render the same DEM masked to the country in the full hypsometric ramp on top. The national outline then reads without any thick boundary line.

**Veil** when the shape must be legible *and* content outside it must stay readable — a province panel where the study area straddles the border. Draw full-colour relief, then overlay `st_difference(window, region)` filled `alpha("white", 0.40–0.50)`. The region sits at full saturation; everything else recedes but stays legible.

Build the mask from your own approved boundary layer, not from a package's bundled geometry.

## Composition

### Compose with gtable

patchwork is adequate for one map with one inset. It stops being the right tool once panel sizes must be exact, because the numbers leader-line geometry needs *are* the slot sizes.

Compose with `gridExtra::arrangeGrob()` and explicit `grid::unit(..., "mm")` widths and heights. Slot sizes then become constants you chose rather than values you have to recover afterwards.

For an inset *inside* a single panel, use `annotation_custom(ggplotGrob(p_inset), xmin =, xmax =, ymin =, ymax =)` in the parent's data coordinates.

**Never size an inset from transformed corner points.** A helper that takes `st_bbox()` of the four transformed corners of a lon/lat rectangle does not reproduce what `coord_sf()` renders, because `coord_sf(default_crs = )` derives its limits differently. Measured on the China extent (72–142°E, 12–56°N, Albers `lon_0 = 105`):

| | main panel ratio | inset ratio | resulting `inset_width` |
|---|---|---|---|
| corner-bbox helper | 1.6865 | 0.8977 | 0.1490 |
| what `coord_sf()` renders | 1.2831 | 0.8750 | 0.1910 |
| error | **+31.4%** | +2.6% | **−22%, about 8 mm at 190 mm** |

An inset placed with that width misses the parent's edge by roughly 8 mm — which is precisely the misalignment such a helper is written to prevent. Read the ratio back from the built plot instead:

```r
panel_ratio <- function(p) {
  bp <- ggplot_build(p)$layout$panel_params[[1]]
  as.numeric(diff(bp$x_range) / diff(bp$y_range))
}
```

Measured with ggplot2 4.0.3, patchwork 1.3.2, sf 1.1.2.

To force a panel to an exact size, overwrite its gtable cell:

```r
g <- ggplotGrob(p)
pl <- g$layout[g$layout$name == "panel", ]
g$widths[pl$l]  <- grid::unit(panel_w, "mm")
g$heights[pl$t] <- grid::unit(panel_h, "mm")
g$respect <- FALSE            # size is pinned; stop coord_fixed re-constraining it
```

### Every ggplotGrob call needs a font-aware device open

`ggplotGrob()` measures text against the *current* graphics device. With no device open it falls back to the default pdf device, where Arial does not exist — you get `failed to find or load PDF CID font`, or worse, silently wrong widths that corrupt every mm computation downstream.

Open a ragg device **before** the first `ggplotGrob()`, close it after the last:

```r
tmp <- tempfile(fileext = ".png")
ragg::agg_png(tmp, width = 190, height = 220, units = "mm", res = 72)
# ... all ggplotGrob() / grid::convertWidth() calls here ...
grDevices::dev.off(); unlink(tmp)
```

### Derive panel rectangles analytically

Once slot sizes are pinned, every panel rectangle is arithmetic, not introspection. Measure only the non-panel margins of the main plot (axis text, plot margins) once:

```r
side_w <- sum(as.numeric(grid::convertWidth(g$widths[-pl$l], "mm")))
top_mm <- sum(as.numeric(grid::convertHeight(g$heights[seq_len(pl$t - 1)], "mm")))
bot_mm <- sum(as.numeric(grid::convertHeight(g$heights[seq(pl$b + 1, length(g$heights))], "mm")))
```

Then panel positions follow from the layout constants you chose.

## Zoom leader lines

Dashed lines from the highlight box in one panel to the corners of the next panel are the strongest single cue that a figure is a professional map rather than three boxes parked side by side. They are also the element most likely to collide with something.

Map a geographic box into panel millimetres by linear interpolation (y inverted, because grid measures down from the top):

```r
box_in <- function(bb, wn, rect) {
  fxr <- function(v) rect[["x0"]] + (v - wn[["xmin"]]) /
    (wn[["xmax"]] - wn[["xmin"]]) * (rect[["x1"]] - rect[["x0"]])
  fyr <- function(v) rect[["yb"]] - (v - wn[["ymin"]]) /
    (wn[["ymax"]] - wn[["ymin"]]) * (rect[["yb"]] - rect[["yt"]])
  c(x0 = fxr(bb[["xmin"]]), x1 = fxr(bb[["xmax"]]),
    yt = fyr(bb[["ymax"]]), yb = fyr(bb[["ymin"]]))
}
```

Draw the segments as one `grid::segmentsGrob()` in mm over the composed gtable (`grid::grobTree(base_grob, leaders)`). Drawing them *under* the panels hides them — panels are opaque.

**The collision rule.** A leader pair fans from the highlight box to two corners of the target panel, so it sweeps across the whole side of the source panel that faces the target. **Nothing else can occupy that side.** In particular a corner inset — the standard bottom-right South China Sea box — sits precisely where the cone passes when the next panel is below.

Three ways out:

1. **Widen the main window so the inset is unnecessary.** Extend the window until every layer that must appear falls inside the main frame. This removes an element and the conflict at once, and is usually the best answer.
2. **Keep the inset and drop the leader pair that would cross it.** First make the corner empty — see below. A locator panel whose highlight is a filled accent-coloured patch already points at the next panel; the leaders are reinforcement, not the only cue. Use `corner_inset()`, and size the inset's window with `fit_aspect(bb, inset_aspect(win, x, y))` first — an inset whose window aspect does not match its box gets letterboxed by `coord_sf` and its edges stop aligning.
**A corner inset has to land on empty ground, and a window fitted to the land has no empty corner.** Fitting the window to the region puts coastline in every corner, so the box covers real map. Measured on a China panel fitted to the mainland, a box occupying the right 23% and bottom 43% of the panel covered 537,524 km² of the country — a quarter of the box — across eight province-level units. Nothing about the figure looks wrong; the reader simply loses that land and cannot tell how much.

There is no box placement that fixes this, because the obstruction is the window, not the box. Widen the window on that side until the corner is open sea, which is why published national maps carrying a corner inset extend well past the coast. Widening changes the aspect, which changes the panel height, which moves the box, so iterate to a fixed point:

```r
for (i in 1:12) {
  W <- widen_for_inset(W, IX, IY, region, side = "xmax")
  h <- clamp(col_w / win_aspect(W))
  W <- fit_aspect(W, col_w / h)
  if (inset_is_clear(W, IX, IY, region)) break
}
assert_inset_clear(W, IX, IY, region)
```

The cost is real and worth stating: the same panel went from 38.1 mm tall to 32.9 mm, and the window now reaches 148°E, so the country is drawn smaller. That is the price of the inset, and it is why widening the window to include the far territory outright is usually the better of the two options.

3. Drop the leader lines entirely. Legitimate — many journals' figures have none — but then the panels need some other cue tying them together (shared accent colour, matched frames).

Also clear the target side: put the main panel's latitude labels on the **right** (`scale_y_continuous(position = "right")`) when leaders arrive from the left, or they cross the tick labels.

## Map furniture

### An RGB raster has no fill scale, so draw the legend by hand

`geom_spatraster_rgb()` creates no guide. Hand-draw the whole legend block with `annotate()` in data coordinates via fraction helpers — which also gives exact control over position, something `legend.position.inside` never quite delivers.

```r
fx <- function(t) W[["xmin"]] + t * (W[["xmax"]] - W[["xmin"]])
fy <- function(t) W[["ymin"]] + t * (W[["ymax"]] - W[["ymin"]])
```

Order the block: symbol rows on top, a thin separator, then the elevation ramp with its title above and tick labels below. Back it with a `fill = "white", alpha = 0.88` rect and a grey hairline border.

**Lay the block's internals out in millimetres, not in fractions of the panel.** Text height is fixed in points, so fractional spacing tuned on a 90 mm panel collides on a 40 mm one and the tick labels grow into the block's own border. `elev_legend_block()` takes `panel_h_mm` and derives its spacing from it. The rule generalises: fractions are right for *placing* a block, millimetres are right for spacing *inside* it.

Label ticks at **alternate** class boundaries. Six classes with five labelled boundaries at 8 pt run together into `10001250150017502000`.

Say `Elevation (m)`. `m a.s.l.` spends four characters restating what "elevation" already means.

### Needle north arrow, aspect-corrected

`ggspatial::annotation_north_arrow()` styles look dated next to a modern relief map. A slim needle — apex, right base, a notch back up the centreline, left base — plus `N` above reads cleanly at 8 pt.

Fractional coordinates distort with panel aspect ratio, so derive the width from the window:

```r
w <- h * slim * (win[["ymax"]] - win[["ymin"]]) / (win[["xmax"]] - win[["xmin"]])  # slim ≈ 0.22
tri <- data.frame(x = fx(c(ax, ax + w, ax, ax - w)),
                  y = fy(c(ay, ay - h, ay - h * 0.74, ay - h)))
```

The same needle then has the same shape in a wide main panel and a tall locator panel.

### Keep furniture clear of the frame

Nothing drawn inside a panel may touch or cross the panel border. A legend box whose edge lands on the frame does not read as a tight fit; at 8 pt its own hairline and the frame merge into one thick, broken line, and the reader can no longer tell where the map ends. The same goes for north arrows, scale bars and panel labels.

Leave a clearance of about 2.5% of panel width and height — `FRAME_PAD` in `relief_basemap.R`. The built-in blocks default to that and assert it, so a hand-moved legend fails loudly instead of shipping:

```r
assert_inside(c(0.598, 0.977), c(0.030, 0.148), what = "legend backing")
# legend backing reaches the right frame (x 0.598-0.977, ...). Move it inward.
```

Express furniture positions as fractions of the window, never as absolute coordinates. Fractions survive a change of window or panel size; absolute positions silently drift off the panel the next time the extent is edited.

### Zoom out to make room

An in-panel legend that lands on the study area is the normal outcome of fitting the window tightly to it: a tight window has no empty corner. Nudging the legend does not help, because every corner is occupied.

Widen the window instead. The region is drawn at a smaller scale and the margin that frees is what the block sits on. `pad_until_clear()` searches for the smallest padding that clears a given block, padding proportionally so the aspect ratio — and the panel height derived from it — does not drift. The Taiyuan example settles at 19%.

The alternative is to move the legend outside the panel. Both are legitimate; zooming out keeps the figure to one panel, an external legend keeps the region at full size.

### Corner budget

An elongated study area leaves exactly two usable corners, on the long axis's off-diagonal. Inventory them before placing anything: north arrow, scale bar, elevation ramp, symbol legend, panel tag. Group the furniture — arrow plus elevation ramp in one box, symbol legend in the other — instead of scattering four small boxes into four corners.

## Source data

**Content requirements are the author's to determine, and they constrain the layout.** Where a jurisdiction requires certain territory to appear, or requires an inset carrying it to be named, that decision is the author's; `check_cn_content()` only tests whether the frames a figure draws cover a given list of features. The layout consequence is worth knowing in advance: an inset large enough to carry a name forces the window further out to keep the corner clear, so the region is drawn smaller. Measured on a 45.6 mm locator panel, moving the far islands into an inset took the country panel from 46.7 mm to 32.9 mm and pushed the window east by about 15 degrees. At locator size, putting them in the main frame costs less.

**Boundary vectors decide credibility; get them from the authoritative publisher for your region**, not from whatever a plotting package happens to bundle. Record the dataset name, version and download date, and put them in the figure caption. Package-bundled geometry usually documents neither, which is enough reason to prefer a named source.

**Elevation is not a boundary.** GEBCO, ASTER GDEM, SRTM and similar rasters are independent of any administrative dataset, so pairing an open DEM with a named boundary source is normal practice. Cite the DEM separately.

`ggmapcn::basemap_dem()` supplies a GEBCO 2024 raster; see **Distributing this skill** for sources and resolution limits.

**Reading the source GIS files.** ArcGIS container formats are ordinary archives. `.lpkx`, `.mpk` and `.ppkx` are 7-Zip; `.aprx` is a zip. Extract them and you have plain shapefiles and File Geodatabases that GDAL reads directly, with no ArcGIS install. MapGIS 6.x (`.WL/.WP/.WT`, `.la/.lm/.pa/.pm`) has no GDAL driver, so those layers must be re-exported from MapGIS, or traced from a CorelDraw or Illustrator version and georeferenced against graticule ticks with an affine transform.

## Distributing this skill

The skill ships code, not data. Nothing under `reference/` contains a shapefile or a raster, and that is deliberate for two different reasons.

**Boundary datasets carry their own terms.** Redistributing a copy inside a skill strips it of the provenance a caption has to state, and often of its licence too. Name the source and let the user fetch it.

**DEMs are too large and are already served.** Point the user at a source and let the loader assert coverage:

| need | source | note |
|---|---|---|
| site panel, 30 m | ASTER GDEM v3, NASA Earthdata (login) | manual tile download; `load_dem()` merges them |
| site panel, 30 m | Copernicus DEM GLO-30 | open, no login |
| country panel | GEBCO 2024 via `ggmapcn::check_geodata()` | 0.05°, ~24 MB, auto-downloads |
| any, coarse | `geodata::elevation_30s()` / `elevation_3s()` | not tested here |
| non-China boundaries | `rnaturalearth` | not tested here |

The `ggmapcn` jsDelivr mirror returns HTTP 403; the function falls through to `raw.githubusercontent.com` by itself, so let it retry rather than reporting failure.

At 0.05° (≈ 5 km) GEBCO is right for a country panel and marginal for a province panel. Upsample with `terra::project(..., method = "bilinear", res = 700)` for display, and **state in the caption that provincial relief is generalised** — do not let a 5 km product read as a high-resolution DEM. Site panels need a real 30 m DEM.

A figure script written against this skill therefore starts with a data block naming every path, and fails loudly on the first missing or non-conforming input rather than rendering something plausible.

## Keep a figure set on one basemap

When several figures in a paper share a region, the location map and the sampling map should read as one system: identical elevation classes, identical palette, identical frame weight, identical north arrow and legend style, identical graticule spacing.

Put the shared pieces in one sourced module — DEM loader, `relief_rgb()`, elevation breaks and palette, accent colour, river colour, frame weight, north arrow, elevation legend — and have every figure script source it. Then a palette change is one edit and the set cannot drift.

Two things still need explicit syncing because they are computed per figure:

- **Graticule spacing.** Different windows make ggplot choose different break densities. Pin `scale_x_continuous(breaks =)` / `scale_y_continuous(breaks =)` to the same interval across figures.
- **Accent colour exclusivity.** When the detail figure adds point symbols, check none of them reuses the study-area accent. Switch the clashing symbol to a different **shape** rather than reassigning the colour.

## Checklist

- [ ] One projected CRS for every layer
- [ ] Raster fills the frame — no blank corners, no-data fraction asserted and printed
- [ ] Country panel window derived from data bbox, not a lon/lat rectangle
- [ ] Every panel frame the same width; no letterboxing inside slots
- [ ] Relief multiplied in, not alpha-blended
- [ ] Elevation classes discrete; alternate boundaries labelled
- [ ] One accent colour for the study area, used nowhere else
- [ ] Leader lines, if present, collide with nothing; target-side axis labels moved away
- [ ] Legend self-contained: every symbol on the map appears in it, and vice versa
- [ ] Boundary source, DEM source and any generalised relief all named in the caption
- [ ] Class edges derived from this DEM, not inherited; `assert_accent_unique()` passed
- [ ] Companion figures share the basemap module and graticule spacing

## Common mistakes

- Alpha-blending the hillshade, then compensating with a more saturated palette
- `st_bbox()` of a transformed lon/lat rectangle for a country panel — silently amputates the south
- Taking the window from one layer's bbox when several layers must fit — partial line layers cut whole regions off, and the result still looks like a map
- Sizing an inset from a corner-bbox aspect ratio instead of the rendered panel ratio
- A `geom_sf()` added after `coord_sf(xlim =, ylim =)` — the limits are silently discarded and the panel reverts to the data extent
- A corner inset dropped into a window fitted to the land — it covers part of the map and nothing about the result looks wrong
- Calling `ggplotGrob()` with no font-aware device open
- A white casing under the accent-coloured boundary: at figure scale the casing blends into the line and it reads pink, not red, and no longer matches its own legend swatch
- Two line styles on the map, one entry in the legend
- Four separate furniture boxes in four corners of a panel that only has two free ones
- A legend or arrow whose edge sits on the panel border
- Letting a 5 km DEM be described as the study-area DEM
