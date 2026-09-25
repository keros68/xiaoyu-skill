# Window and projection

Use one projected CRS for every layer — polygons, lines, points, labels, rasters. Never mix raw lon/lat with projected `geom_sf()`.

## Take the inscribed rectangle, not the bounding box

A lon/lat rectangle transformed into a conic projection is a **curved quadrilateral**, not a rectangle. Both naive choices fail:

- `st_bbox()` of the transformed rectangle → corners fall *outside* the data, leaving blank wedges in the frame.
- Feeding lon/lat limits to `coord_sf(default_crs = 4326)` → the same curvature, handled invisibly.

For a raster basemap that must fill the frame edge to edge, take the **inscribed** rectangle: `inscribed_window(lon, lat, crs)` samples each geographic edge and keeps the innermost x and y on every side.

The mirror-image failure is worse and quieter: for a **country panel**, taking the bbox of a transformed lon/lat rectangle *clips real land*. In a Lambert projection of China, a 73–136°E × 17.5–54.5°N rectangle loses roughly 600 km off the south — Yunnan, Guangxi, Guangdong, Hainan, Taiwan, Hong Kong and Macau all vanish, and the map still looks plausible. For country panels take `st_bbox()` of the **data**, never of a coordinate rectangle.

Take it from *every* layer that has to fit, via `bbox_union()`. One layer's bbox is not a proxy for the others, and boundary-line layers are the usual trap: they frequently hold only selected segments — disputed sections, maritime lines — so their extent can stop far short of the polygons. A real case: a national line layer whose northernmost feature sat at 38.68°N, used alone as the window, cut 14.9° of latitude and 12.3° of longitude off a country map and dropped 99 prefecture units. The frame still looked like a plausible map.

Then verify rather than eyeball it — at locator-panel size a missing province is invisible:

```r
clip <- sf::st_as_sfc(sf::st_bbox(W, crs = sf::st_crs(prov)))
stopifnot(all(lengths(sf::st_within(sf::st_geometry(prov), clip)) > 0))
```

## coord_sf() goes last, and prove it

`geom_sf()` does not return a layer. It returns a list containing the layer **and a default `coord_sf()`**, and adding any coord replaces the one already on the plot. So a single `geom_sf()` placed after your `coord_sf(xlim =, ylim =)` throws the limits away and the panel silently falls back to the data extent.

```r
rng <- function(p) { bp <- ggplot_build(p)$layout$panel_params[[1]]
                     c(bp$x_range, bp$y_range) }
p <- ggplot() + geom_sf(data = pt) + coord_sf(xlim = c(2, 4), ylim = c(2, 4), expand = FALSE)
rng(p)                      # 2 4 2 4
rng(p + geom_sf(data = pt)) # -0.5 10.5 -0.5 10.5
```

ggplot's only warning is an easily-missed `Adding new coordinate system, which will replace the existing one`, and the figure still looks like a map — just of the wrong extent, at the wrong aspect, letterboxed inside its slot with a band of white where the reader expects data.

Two consequences. Never put `coord_sf()` inside a layer list that a caller might extend — a layer helper must return layers only. And check the built plot rather than trusting the code: `assert_window(p, W)` compares `ggplot_build()`'s panel range against the window.

## Fix the slot first, then expand the window

`coord_sf()` enforces a fixed aspect ratio. Drop a map into a layout slot whose shape differs and it letterboxes *inside* that slot: the drawn panel is narrower than its cell, and two side-by-side locator panels end up visibly unequal. Hand-tuned offsets never converge.

Reverse the order. Compute the exact slot size in mm, then expand each geographic window outward with `fit_aspect(W, slot_w_mm / slot_h_mm)` — only ever outward, so no content is lost — until it matches that slot's aspect ratio. With the window matched to the slot, the panel fills its cell exactly and every frame in the figure is the same width.

When the panel width is fixed and the height is free, go the other way: `panel_h <- panel_w / win_aspect(W)`.
