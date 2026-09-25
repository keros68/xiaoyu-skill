# Thematic layers

Functions in `reference/thematic.R`; source it after `relief_basemap.R`. `example/taiyuan_thematic.R` uses all of them.

## Categorical rasters: land use, soil type, geology

`class_rgb(r, codes, cols, dem = NULL, strength = 0.20)` colours a raster of class codes by lookup and returns an RGB raster, so each class keeps its exact colour and the legend is drawn by hand like the elevation legend.

- **List every code.** An unlisted code would draw as a hole that reads as no-data, so the function stops instead.
- **Watch the printed class shares.** A class under about 0.5% of the panel barely shows at print size; the function warns. Merge it, or keep it only if the paper discusses it.
- **Relief under classes is optional and weak.** Pass `dem` on the same grid (`terra::resample(dem, r)` if needed). Keep `strength` at 0.15–0.25: at basemap strength the shading reads as extra class boundaries.
- **Colours follow meaning.** Water blue, forest dark green, cropland pale yellow, built-up grey. Built-up in red collides with the study-area accent; `assert_accent_unique()` catches it.

## Continuous thematic rasters: SOC, NDVI, precipitation

Class them like elevation: `relief_rgb(x, brks, cols, strength = 0)` with breaks chosen for the variable (round numbers, or `elev_breaks()` for percentile-based edges) and a sequential ramp such as `hcl.colors(n, "YlGnBu", rev = TRUE)`. Use a diverging ramp only when the variable has a meaningful midpoint (change, anomaly). `elev_legend_block(title = ...)` draws the legend; `elev_labels(brk, every = 1)` labels every boundary when there are few classes.

## Points: sampling sites, cities, stations

- **Equal-size points** for locations only. One fill, a thin white outline so points stay visible on any background.
- **Graduated sizes** for a value: `graduated_sizes(x, breaks, sizes)` returns per-point sizes, class labels and the size steps, and prints the count per class. Three steps read reliably at locator scale; more become hard to tell apart. Pass the same `sizes` to the legend so the key is the symbol.
- **Category by colour** for site types: a short qualitative palette; none of its colours may be the accent.

## Content inside the study area only

A thematic layer usually exists only inside the study area. Mask it with `terra::mask(x, terra::vect(aoi))` and draw a neutral surround underneath (a single grey relief class). The study area then reads from the change in colour, and the accent boundary line can stay thin.

## Legend blocks

`legend_rows_block(win, items, panel_w_mm, panel_h_mm, ...)` draws fill, point and line keys as one block. Its internal spacing is computed in millimetres from the panel's printed size and label widths are measured from the registered font, so the same call fits a 40 mm and a 120 mm panel. `ncol` sets columns; `title` adds a title row; `corner` and `anchor` place it.

`items` columns mirror the map layers: `type` (`"fill"`, `"point"`, `"line"`), `label`, and any of `fill`, `colour`, `shape`, `size`, `linetype`, `linewidth`. Take them from the same objects the layers use.

The returned layers carry `attr(, "extent")` (panel fractions) and `attr(, "size_mm")`. Use them to reserve space and verify it: `assert_within_reserved(block, x, y)`.

## Legends inside or outside the panel

Inside the panel needs an empty corner. Reserve an area, widen the window with `pad_until_clear()` until the study area clears it, then check each block with `assert_within_reserved()`.

Outside the panel is right when the panels are small. In a 2 × 2 set at about 60 mm per panel, a six-class legend covers half the panel width or more, and `pad_until_clear()` fails at any padding — that failure is the signal. Build each legend in a strip below its panel:

```r
leg <- legend_panel(PW, LEG_H,
  legend_rows_block(mm_win(PW, LEG_H), items, PW, LEG_H, anchor = c(0.03, 0.97),
                    corner = "tl", ncol = 3, backing = FALSE, title = "Land use"))
```

`mm_win()` gives the strip millimetre coordinates, so the legend builders work unchanged; `backing = FALSE` drops the white box that only an in-map legend needs. Give all strips in a row the same height (the tallest block's `size_mm[2]` plus a margin) and align each strip's left edge with its panel frame.

## Several thematic panels of one area

- **One window for all panels**, so a point in one panel sits at the same place in the others. Same panel size, same graticule breaks.
- **North arrow and scale bar once**, in the first panel.
- **Coordinates on the outer edges only**: latitude on the right column, longitude on the bottom row. Measure each position's margins with `panel_margins()` and solve for the panel width so all panels come out the same size.
- **One locator for the set.** The locator column can hold two levels (country, province) with the study area highlighted in the accent colour; leaders are unnecessary because the panels are not a zoom sequence.
