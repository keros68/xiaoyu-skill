# Source data and figure sets

## Content requirements

**Content requirements are the author's to determine, and they constrain the layout.** Where a jurisdiction requires certain territory to appear, or requires an inset carrying it to be named, that decision is the author's; `check_cn_content()` only tests whether the frames a figure draws cover a given list of features. The layout consequence is worth knowing in advance: an inset large enough to carry a name forces the window further out to keep the corner clear, so the region is drawn smaller. Measured on a 45.6 mm locator panel, moving the far islands into an inset took the country panel from 46.7 mm to 32.9 mm and pushed the window east by about 15 degrees. At locator size, putting them in the main frame costs less.

## Boundaries and elevation

**Boundary vectors decide credibility; get them from the authoritative publisher for your region**, not from whatever a plotting package happens to bundle. Record the dataset name, version and download date, and put them in the figure caption. Package-bundled geometry usually documents neither, which is enough reason to prefer a named source.

**Elevation is not a boundary.** GEBCO, ASTER GDEM, SRTM and similar rasters are independent of any administrative dataset, so pairing an open DEM with a named boundary source is normal practice. Cite the DEM separately. `credit_footer()` attaches a source line under the composed figure, so attribution travels with the image when it is lifted into slides.

The skill ships code, not data. Boundary datasets carry their own terms, and DEMs are large and already served:

| need | source | note |
|---|---|---|
| site panel, 30 m | ASTER GDEM v3, NASA Earthdata (login) | manual tile download; `load_dem()` merges them |
| site panel, 30 m | Copernicus DEM GLO-30 | open, no login |
| country panel | GEBCO 2024 via `ggmapcn::check_geodata()` | 0.05°, ~24 MB, auto-downloads |
| any, coarse | `geodata::elevation_30s()` / `elevation_3s()` | not tested here |
| non-China boundaries | `rnaturalearth` | not tested here |

The `ggmapcn` jsDelivr mirror returns HTTP 403; the function falls through to `raw.githubusercontent.com` by itself, so let it retry rather than reporting failure.

At 0.05° (≈ 5 km) GEBCO is right for a country panel and marginal for a province panel. Upsample with `terra::project(..., method = "bilinear", res = 700)` for display, and **state in the caption that provincial relief is generalised** — do not let a 5 km product read as a high-resolution DEM. Site panels need a real 30 m DEM.

A figure script therefore starts with a data block naming every path, and fails loudly on the first missing or non-conforming input rather than rendering something plausible.

## Thematic data in shared examples

Research data (land use, sampling results) are often unpublished or sensitive. For a demonstration, template or skill example, simulate them from a fixed seed — rules on elevation, slope and distance plus a smooth random field give plausible patches — and label them as synthetic in the legend titles and the source line, as `example/taiyuan_thematic.R` does.

## Reading the source GIS files

ArcGIS container formats are ordinary archives. `.lpkx`, `.mpk` and `.ppkx` are 7-Zip; `.aprx` is a zip. Extract them and you have plain shapefiles and File Geodatabases that GDAL reads directly, with no ArcGIS install. MapGIS 6.x (`.WL/.WP/.WT`, `.la/.lm/.pa/.pm`) has no GDAL driver, so those layers must be re-exported from MapGIS, or traced from a CorelDraw or Illustrator version and georeferenced against graticule ticks with an affine transform.

## Keep a figure set on one basemap

When several figures in a paper share a region, the location map and the sampling map should read as one system: identical elevation classes, identical palette, identical frame weight, identical north arrow and legend style, identical graticule spacing.

Put the shared pieces in one sourced module — DEM loader, `relief_rgb()`, elevation breaks and palette, accent colour, river colour, frame weight, north arrow, elevation legend — and have every figure script source it. Then a palette change is one edit and the set cannot drift.

Two things still need explicit syncing because they are computed per figure:

- **Graticule spacing.** Different windows make ggplot choose different break densities. Pin `scale_x_continuous(breaks =)` / `scale_y_continuous(breaks =)` to the same interval across figures.
- **Accent colour exclusivity.** When the detail figure adds point symbols, check none of them reuses the study-area accent. Switch the clashing symbol to a different **shape** rather than reassigning the colour.
