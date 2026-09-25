---
name: study-area-map
description: Use when building a study-area location or setting map for a paper in R with ggplot2 + sf + terra — nested locator panels (country → province → site), shaded-relief DEM basemaps, land-use and other categorical rasters, classed continuous rasters, sampling sites with graduated symbols, one locator with several thematic panels, zoom leader lines, in-panel or strip legends, north arrows and scale bars. Also covers sourcing boundary and elevation data, including reading ArcGIS and MapGIS files.
---

# study-area-map

Builds the frame of a study-area map: projection, window, basemap, thematic layers, panel composition and map furniture. The details that are easy to get wrong carry assertions, so a wrong window, a blank raster edge, a legend on the frame or an inset on land stops the script instead of reaching the journal.

## Modules

Source in this order; later files use earlier ones.

| File | Contents |
|---|---|
| `reference/relief_basemap.R` | constants `LW`, `LW_DAT`, `TXT_PT`, `TXT_GG` (set only if undefined, so a house-style preamble wins), `ensure_font()`, `theme_map_pub()`; windows `inscribed_window()`, `bbox_union()`, `fit_aspect()`, `win_aspect()`, `pad_win()`, `pad_until_clear()`; DEM `load_dem()`, `vsizip_tiles()`, `locate_na()`; relief `shade_factor()`, `relief_rgb()`; furniture `north_needle()`, `elev_legend_block()`, `legend_backing()`, `frac_fun()`, `assert_inside()`, `FRAME_PAD`; insets `inset_aspect()`, `corner_inset()`, `inset_is_clear()`, `assert_inset_clear()`, `widen_for_inset()`; composition `pin_panel()`, `panel_margins()`, `with_font_device()`, `box_in()`, `add_leaders()`, `credit_footer()`; checks `assert_window()`, `check_cn_content()` |
| `reference/palettes.R` | `pal_hypso()`, `elev_breaks()`, `elev_labels()`, `preview_hypso()`, `check_ramp()`, `simulate_cvd()`, `to_gray()`, `assert_accent_unique()`, `PAL_SURROUND`, `BRK_SURROUND` |
| `reference/thematic.R` | `class_rgb()`, `graduated_sizes()`, `legend_rows_block()`, `assert_within_reserved()`, `mm_win()`, `legend_panel()` |

Set region constants (paths, CRS, windows, accent colour) in the figure script, not in the modules, so several figures in one paper can share them.

## Start from the closest example

Copy the matching script from `example/`, change the data block at the top, then adapt. Each writes a 300 dpi PNG and a 150 dpi preview.

| Figure | Start from |
|---|---|
| Locator + one main map, relief basemap | `taiyuan_locator.R` (two levels) |
| Country → province → site with zoom leaders; South China Sea in frame or as corner inset | `taiyuan_three_level.R` (`SCS_INSET`) |
| Locator + several thematic maps of one area (terrain, land use, sites, a continuous variable) | `taiyuan_thematic.R` |

The thematic example uses synthetic land use, sites and SOC generated from a fixed seed; see `guides/data-sources.md` before replacing them with real data.

## Decide before drawing

A location map answers *where is this, and why does the location matter?* Settle these first; each one constrains the layout.

1. **Zoom levels.** Two (country → site) is usually enough. Three only when the province is itself the reason — an administrative dataset, a provincial policy, a regional geological unit. Each extra level costs a panel and buys less than the previous one.
2. **What the main panel shows.** Terrain when relief explains the study (a basin against its rim, a fault-bounded graben); land use, a continuous variable or sampling sites when that is the evidence; a quiet vector map when location is all that matters. A relief basemap that explains nothing is decoration.
3. **How quiet the basemap is.** Locator panels and any panel carrying many symbols get a pale, neutral base (vector fills, a grey relief surround, or `wash`). Full colour is reserved for the panel whose colour is the message.
4. **One accent colour means "study area", everywhere.** Locator highlight, province outline, main-panel boundary — the same hex, used by nothing else, including point fills. `assert_accent_unique()` enforces it.
5. **Where legends go.** Inside the panel needs an empty corner (`pad_until_clear()`); small panels in a set take legend strips below (`legend_panel()`).
6. **Which furniture.** Coordinates when position matters, scale bar when distance matters, north arrow only when orientation is not already clear — once per panel set.

## Workflow

| Step | Do | Details |
|---|---|---|
| 1 Data | Name every path in a data block; one projected CRS for all layers | `guides/data-sources.md` |
| 2 Window | Inscribed rectangle for raster panels; data bbox of every layer for country panels; fix the slot size, then `fit_aspect()`; `coord_sf()` last | `guides/window-and-projection.md` |
| 3 Basemap | `load_dem()` (asserts no-data), `elev_breaks()` from this DEM, preview and check ramps, `relief_rgb()`; mask or veil locators | `guides/relief.md` |
| 4 Thematic layers | `class_rgb()` for classes, classed `relief_rgb(strength = 0)` for continuous values, `graduated_sizes()` for points; mask to the study area over a neutral surround | `guides/thematic-layers.md` |
| 5 Compose | `pin_panel()` sizes, `arrangeGrob()` in mm, margins from `panel_margins()` inside `with_font_device()`; leaders via `box_in()` + `add_leaders()` | `guides/composition.md` |
| 6 Furniture | Hand-drawn legends laid out in mm, needle arrow, clearance from the frame, corner budget | `guides/furniture.md` |
| 7 Check | `assert_window()` on every panel, `check_cn_content()` for national maps, then look at the preview at final size | checklist below |

This skill overlaps with rfigure.skill's *China Maps And Site Distributions* section and corrects one measured error in it: inset sizing from transformed corner points (see `guides/composition.md`).

## Checklist

- [ ] One projected CRS for every layer
- [ ] Raster fills the frame — no blank corners, no-data fraction asserted and printed
- [ ] Country panel window derived from the data bbox of every layer, not a lon/lat rectangle
- [ ] `assert_window()` passes for every panel; every panel frame the intended width, no letterboxing
- [ ] Relief multiplied in, not alpha-blended; elevation classes discrete, edges derived from this DEM, alternate boundaries labelled
- [ ] One accent colour for the study area, used nowhere else; `assert_accent_unique()` passed
- [ ] Every class and symbol on the map appears in the legend, and vice versa; no class too small to see
- [ ] Legends and furniture clear of the frame and of the study area; nothing collides with panel tags
- [ ] Leader lines, if present, collide with nothing; target-side axis labels moved away
- [ ] Boundary source, DEM source, generalised relief and any synthetic data named in the caption or source line
- [ ] Companion figures share the basemap module, window and graticule spacing

## Common mistakes

- Alpha-blending the hillshade, then compensating with a more saturated palette
- `st_bbox()` of a transformed lon/lat rectangle for a country panel — silently amputates the south
- Taking the window from one layer's bbox when several layers must fit — partial line layers cut whole regions off
- A `geom_sf()` added after `coord_sf(xlim =, ylim =)` — the limits are silently discarded
- Sizing an inset from a corner-bbox aspect ratio instead of the rendered panel ratio
- A corner inset dropped into a window fitted to the land — it covers part of the map and nothing looks wrong
- Calling `ggplotGrob()` with no font-aware device open
- A white casing under the accent-coloured boundary: at figure scale it reads pink and no longer matches its legend swatch
- Built-up land or site symbols in a red close to the accent
- Forcing a class legend into a 60 mm panel instead of a legend strip
- Four separate furniture boxes in four corners of a panel that only has two free ones
- Letting a 5 km DEM be described as the study-area DEM
