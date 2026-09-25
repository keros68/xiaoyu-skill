# Composition and zoom leaders

## Compose with gtable

patchwork is adequate for one map with one inset. It stops being the right tool once panel sizes must be exact, because the numbers leader-line geometry needs *are* the slot sizes.

Compose with `gridExtra::arrangeGrob()` and explicit `grid::unit(..., "mm")` widths and heights. Slot sizes then become constants you chose rather than values you have to recover afterwards. `pin_panel(p, w_mm, h_mm)` forces a panel cell to an exact size (and sets `respect = FALSE` so `coord_fixed` does not re-constrain it).

For an inset *inside* a single panel, use `corner_inset(p_inset, W, x, y)`, which wraps `annotation_custom(ggplotGrob(...))` in the parent's data coordinates after stripping the inset's margins, background and legend.

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

Measured with ggplot2 4.0.3, patchwork 1.3.2, sf 1.1.2. Size the inset's own window with `fit_aspect(bb, inset_aspect(W, x, y))` first, or `coord_sf` letterboxes it inside its box and its edges stop aligning.

## Every ggplotGrob call needs a font-aware device open

`ggplotGrob()` measures text against the *current* graphics device. With no device open it falls back to the default pdf device, where Arial does not exist — you get `failed to find or load PDF CID font`, or worse, silently wrong widths that corrupt every mm computation downstream. Wrap all grob building and unit conversion in `with_font_device({ ... })`, which opens a ragg device and closes it afterwards.

## Derive panel rectangles analytically

Once slot sizes are pinned, every panel rectangle is arithmetic, not introspection. Measure the non-panel margins of each plot once with `panel_margins(p)` (`side`, `left`, `top`, `bot` in mm); panel positions then follow from the layout constants you chose.

## Zoom leader lines

Dashed lines from the highlight box in one panel to the corners of the next panel are the strongest single cue that a figure is a professional map rather than three boxes parked side by side. They are also the element most likely to collide with something.

`box_in(bb, W, rect)` maps a geographic box into panel millimetres (y measured down from the top); `add_leaders(base, segs, fig_h_mm)` draws the segments over the composed gtable. Drawing them *under* the panels hides them — panels are opaque.

**The collision rule.** A leader pair fans from the highlight box to two corners of the target panel, so it sweeps across the whole side of the source panel that faces the target. **Nothing else can occupy that side.** In particular a corner inset — the standard bottom-right South China Sea box — sits precisely where the cone passes when the next panel is below.

Three ways out:

1. **Widen the main window so the inset is unnecessary.** Extend the window until every layer that must appear falls inside the main frame. This removes an element and the conflict at once, and is usually the best answer.
2. **Keep the inset and drop the leader pair that would cross it.** First make the corner empty — see below. A locator panel whose highlight is a filled accent-coloured patch already points at the next panel; the leaders are reinforcement, not the only cue.
3. **Drop the leader lines entirely.** Legitimate — many journals' figures have none — but then the panels need some other cue tying them together (shared accent colour, matched frames). Panels that are not a zoom sequence, such as several thematic maps of one area, never take leaders.

Also clear the target side: put the main panel's latitude labels on the **right** (`scale_y_continuous(position = "right")`) when leaders arrive from the left, or they cross the tick labels.

## A corner inset has to land on empty ground

A window fitted to the land has no empty corner. Fitting the window to the region puts coastline in every corner, so the box covers real map. Measured on a China panel fitted to the mainland, a box occupying the right 23% and bottom 43% of the panel covered 537,524 km² of the country — a quarter of the box — across eight province-level units. Nothing about the figure looks wrong; the reader simply loses that land and cannot tell how much.

There is no box placement that fixes this, because the obstruction is the window, not the box. Widen the window on that side until the corner is open sea (`widen_for_inset()`), which is why published national maps carrying a corner inset extend well past the coast. Widening changes the aspect, which changes the panel height, which moves the box, so iterate to a fixed point and assert:

```r
for (i in 1:12) {
  W <- widen_for_inset(W, IX, IY, region, side = "xmax")
  h <- min(max(col_w / win_aspect(W), h_min), h_max)
  W <- fit_aspect(W, col_w / h)
  if (inset_is_clear(W, IX, IY, region)) break
}
assert_inset_clear(W, IX, IY, region)
```

The cost is real and worth stating: the same panel went from 38.1 mm tall to 32.9 mm, and the window now reaches 148°E, so the country is drawn smaller. That is the price of the inset, and it is why widening the window to include the far territory outright is usually the better of the two options.
