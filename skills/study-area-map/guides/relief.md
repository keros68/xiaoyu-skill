# Relief basemap

## Multiply the hillshade in, never alpha-blend it

The reflex — hillshade layer, hypsometric raster on top at `alpha = 0.5` — washes every colour toward grey. Raising alpha buries the relief; lowering it buries the colour. There is no setting that gives both, because alpha compositing *interpolates toward the layer underneath* instead of modulating brightness.

`relief_rgb(d, brks, cols, strength, wash)` classifies the elevation, looks up the class colour, **multiplies** it by a hillshade coefficient normalised to mean 1 (`shade_factor()`), and emits an RGB raster. Classed bands stay crisp, relief stays visible, saturation is untouched. Draw it with `tidyterra::geom_spatraster_rgb()`.

`strength` sets the light/shade swing (0.35–0.45 reads well in print; above 0.55 the shading starts to swamp the classes). `wash` lerps toward white — use 0.20–0.30 for a basemap that carries hundreds of overlaid symbols, 0 for a basemap that *is* the message. A single grey class, `relief_rgb(dem, c(-1e5, 1e5), "#E9E9E9", strength = 0.30)`, gives a neutral surround that keeps the terrain legible without adding colour.

**Classed, not continuous.** Discrete elevation bands give the reader a boundary to hold on to — "the basin floor is the green band" — and they survive greyscale printing. A continuous ramp turns into an undifferentiated smear at 90 mm wide.

## Palette: ship the ramp, derive the breaks

A ramp is reusable; class edges are not. A coastal plain and a plateau basin need different edges, and inheriting another paper's edges puts every boundary in the wrong place — usually producing one class that covers 80% of the map.

`palettes.R` separates the two. `pal_hypso(name, n)` interpolates a named ramp to any class count; `elev_breaks(d, n)` derives round-number edges from the DEM's own 2nd–98th percentile range, letting the open end classes absorb the tails so a single peak cannot stretch the ramp. `elev_labels(brk)` blanks alternate tick labels.

```r
brk  <- elev_breaks(dem, n = 6)              # -> [breaks] p2-p98 = 856-1966 m, step 200
cols <- pal_hypso("terrain", length(brk) - 1)
rel  <- relief_rgb(dem, brk, cols, strength = 0.42)
elev_legend_block(W, cols, elev_labels(brk), panel_h_mm = panel_h)
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

## Assert the no-data fraction

A window that overruns the DEM tile coverage produces a blank sliver along one frame edge. At preview scale it hides under a scale bar or legend and reaches the journal.

`load_dem()` prints the no-data fraction and stops above `max_na`. When it fires, run `locate_na(d, W)` before touching the window: it reports the no-data cells as panel fractions, and the fix depends on which edge is short. `vsizip_tiles()` reads zipped ASTER/SRTM tiles in place.

## Mask to emphasise, veil to de-emphasise

Two treatments, two jobs:

**Mask** when the panel's job is to make a shape recognisable — a country in a country panel. Render the surrounding world in a muted grey/blue ramp (`PAL_SURROUND`, `BRK_SURROUND`), then render the same DEM masked to the country in the full hypsometric ramp on top. The national outline then reads without any thick boundary line.

**Veil** when the shape must be legible *and* content outside it must stay readable — a province panel where the study area straddles the border. Draw full-colour relief, then overlay `st_difference(window, region)` filled `alpha("white", 0.40–0.50)`. The region sits at full saturation; everything else recedes but stays legible.

Build the mask from your own approved boundary layer, not from a package's bundled geometry.
