# Map furniture

## Add furniture for a reason

- **Coordinates** (ticks or a light graticule) when geographic position matters; on the outer edges only in a panel set.
- **Scale bar** when local distance matters — the main panel of a site map. Locator panels rarely need one.
- **North arrow** only when orientation is not already clear from the graticule or when the journal expects it; once per panel set.
- **A globe or world inset** is optional, not a default ornament.
- **Labels** only for places the reader needs to orient; check collisions and inset edges at final size.

## An RGB raster has no fill scale, so draw the legend by hand

`geom_spatraster_rgb()` creates no guide. Hand-draw the legend block — `elev_legend_block()` for a classed ramp, `legend_rows_block()` for fill, point and line keys — which also gives exact control over position, something `legend.position.inside` never quite delivers. `legend_backing()` adds the white backing for a block assembled by hand; `frac_fun(W)` converts panel fractions to data coordinates.

Order a combined block: symbol rows on top, a thin separator, then the elevation ramp with its title above and tick labels below. Back it with a `fill = "white", alpha = 0.88` rect and a grey hairline border.

**Lay the block's internals out in millimetres, not in fractions of the panel.** Text height is fixed in points, so fractional spacing tuned on a 90 mm panel collides on a 40 mm one and the tick labels grow into the block's own border. Both legend builders take the panel size in mm and derive their spacing from it. The rule generalises: fractions are right for *placing* a block, millimetres are right for spacing *inside* it.

Label ticks at **alternate** class boundaries (`elev_labels()`). Six classes with five labelled boundaries at 8 pt run together into `10001250150017502000`.

Say `Elevation (m)`. `m a.s.l.` spends four characters restating what "elevation" already means.

## Needle north arrow, aspect-corrected

`ggspatial::annotation_north_arrow()` styles look dated next to a modern relief map. `north_needle(W, ax, ay)` draws a slim needle — apex, right base, a notch back up the centreline, left base — plus `N` above, and derives its width from the window aspect, so the same needle keeps its shape in a wide main panel and a tall locator panel.

## Keep furniture clear of the frame

Nothing drawn inside a panel may touch or cross the panel border. A legend box whose edge lands on the frame does not read as a tight fit; at 8 pt its own hairline and the frame merge into one thick, broken line, and the reader can no longer tell where the map ends. The same goes for north arrows, scale bars and panel labels.

Leave a clearance of about 2.5% of panel width and height — `FRAME_PAD`. The built-in blocks default to that and assert it, so a hand-moved legend fails loudly instead of shipping:

```r
assert_inside(c(0.598, 0.977), c(0.030, 0.148), what = "legend backing")
# legend backing reaches the right frame (x 0.598-0.977, ...). Move it inward.
```

Express furniture positions as fractions of the window, never as absolute coordinates. Fractions survive a change of window or panel size; absolute positions silently drift off the panel the next time the extent is edited.

## Zoom out to make room

An in-panel legend that lands on the study area is the normal outcome of fitting the window tightly to it: a tight window has no empty corner. Nudging the legend does not help, because every corner is occupied.

Widen the window instead. The region is drawn at a smaller scale and the margin that frees is what the block sits on. `pad_until_clear()` searches for the smallest padding that clears a given block, padding proportionally so the aspect ratio — and the panel height derived from it — does not drift. The Taiyuan example settles at 19%.

The alternative is to move the legend outside the panel (`legend_panel()`, see `thematic-layers.md`). Zooming out keeps the figure to one panel; an external legend keeps the region at full size and is the only option for small panels.

## Corner budget

An elongated study area leaves exactly two usable corners, on the long axis's off-diagonal. Inventory them before placing anything: north arrow, scale bar, elevation ramp, symbol legend, panel tag. Group the furniture — arrow plus elevation ramp in one box, symbol legend in the other — instead of scattering four small boxes into four corners. Check the render: a panel tag in the top-left and a needle in the top-left collide.
