# 示例：一张定位图配四幅专题图（中国 → 太原：地形、土地利用、采样点、土壤有机碳）
#
# 演示：
#   1. 多幅专题图共用一个窗口和一张定位图。窗口、面板尺寸完全相同，读者可以在
#      四幅之间逐点对照；指北针和比例尺只画一次。
#   2. 定位图（中国、山西两级）只用矢量，不画地形：它只回答「在哪里」，安静的底图
#      不和专题图抢视线。
#   3. 分类栅格（土地利用）按类别查色并乘上轻度山影；连续变量（有机碳）分级设色；
#      采样点按数值分三级大小。图例由 legend_rows_block() / elev_legend_block()
#      按毫米排版，键与图面符号取同一组参数。
#   4. 面板约 60 mm 宽时，六类图例放进图内要占去半幅以上，pad_until_clear() 找不到
#      空角。图例因此统一放在各面板下方等高的图例条里（legend_panel()）。
#   5. 专题内容只画在研究区内，区外用浅灰地形衬底，研究区不必靠粗线也能读出。
#
# 土地利用、采样点和有机碳均为模拟数据（固定随机种子生成），仅用于演示版式，
# 不代表太原的实际情况。行政边界与 DEM 同其他示例，运行前把路径改成你自己的：
#   DEM_DIR   ASTER GDEM 压缩瓦片目录，需覆盖 N37-N38 / E111-E113
#   ADM_DIR   含「中国_市.shp」「中国_县.shp」「中国_省line.shp」的行政区划目录
#
# 出两版：taiyuan_thematic.png 300 dpi 为成品，_preview.png 150 dpi 供 README 引用。

SKILL   <- "../reference"          # 从 example/ 目录运行本脚本
DEM_DIR <- "F:/博士毕业论文/山西DEM"
ADM_DIR <- "F:/标准地图/中国省市县标准行政区划数据 审图号GS（2024）0650号/shp格式"

source(file.path(SKILL, "relief_basemap.R"))
source(file.path(SKILL, "palettes.R"))
source(file.path(SKILL, "thematic.R"))
suppressPackageStartupMessages({library(grid); library(gridExtra); library(ggspatial)})
sf_use_s2(FALSE)          # 行政面有自相交，s2 会直接报错

ACC  <- "#C62828"         # 全图唯一强调色：研究区
SEED <- 20260925

# ---------------- 边界 ----------------
shi  <- st_read(file.path(ADM_DIR, "中国_市.shp"), quiet = TRUE)
xian <- st_read(file.path(ADM_DIR, "中国_县.shp"), quiet = TRUE)
bnd  <- st_read(file.path(ADM_DIR, "中国_省line.shp"), quiet = TRUE)
shi$pcode <- substr(as.character(shi$gb), 4, 5)
prov <- aggregate(st_make_valid(shi)["pcode"], by = list(pcode = shi$pcode),
                  FUN = function(x) x[1], do_union = TRUE)
ty   <- shi[substr(as.character(shi$gb), 4, 7) == "1401", ]
ty_x <- xian[substr(as.character(xian$gb), 4, 7) == "1401", ]

CRS_M <- "+proj=aea +lat_1=37.6 +lat_2=38.3 +lat_0=37.95 +lon_0=112.3 +datum=WGS84 +units=m +no_defs"
CRS_C <- "+proj=aea +lat_1=25 +lat_2=47 +lat_0=0 +lon_0=105 +datum=WGS84 +units=m +no_defs"
ty_m   <- st_transform(st_make_valid(ty), CRS_M)
ty_xm  <- st_transform(st_make_valid(ty_x), CRS_M)
prov_c <- st_transform(st_make_valid(prov), CRS_C)
bnd_c  <- st_transform(bnd, CRS_C)

# ---------------- 共用窗口 ----------------
# 图例放在面板外，窗口只需给研究区留一圈边。
bb_ty <- st_bbox(ty_m)
W_T <- pad_win(c(xmin = bb_ty[["xmin"]], xmax = bb_ty[["xmax"]],
                 ymin = bb_ty[["ymin"]], ymax = bb_ty[["ymax"]]), 0.05)

# ---------------- 版面 ----------------
# 2 x 2 专题图只在外侧标经纬度：右列标纬度，下行标经度。先量出各位置的边距，
# 再解出面板宽度，四幅面板因此严格等大。
FIG_W <- 190; PAD_L <- 2; LOC_W <- 42; GAP_H <- 5; GAP_M <- 3; GAP_V <- 2
win_coord <- function(w) coord_sf(xlim = w[c("xmin", "xmax")], ylim = w[c("ymin", "ymax")],
                                  expand = FALSE)
lon_lat_theme <- function(right, bottom) theme(
  axis.text.y  = if (right)  element_text() else element_blank(),
  axis.ticks.y = if (right)  element_line(linewidth = LW) else element_blank(),
  axis.text.x  = if (bottom) element_text() else element_blank(),
  axis.ticks.x = if (bottom) element_line(linewidth = LW) else element_blank(),
  plot.margin  = margin(0.5, 0.5, 0.5, 0.5, "mm"))
probe <- function(right, bottom) ggplot() + geom_sf(data = ty_m) + win_coord(W_T) +
  scale_y_continuous(position = "right") + theme_map_pub() + lon_lat_theme(right, bottom)
mg <- with_font_device(list(a = panel_margins(probe(FALSE, FALSE)),
                            b = panel_margins(probe(TRUE,  FALSE)),
                            c = panel_margins(probe(FALSE, TRUE)),
                            d = panel_margins(probe(TRUE,  TRUE))))
PW <- (FIG_W - PAD_L - LOC_W - GAP_H - GAP_M - mg$a$side - mg$b$side) / 2
PH <- PW / win_aspect(W_T)

# ---------------- 地形 ----------------
tiles <- vsizip_tiles(DEM_DIR, "^ASTGTM_N3[78]E11[123][.]img[.]zip$")
dem   <- load_dem(tiles, crs = CRS_M, win = W_T, fact = 4)
brk   <- elev_breaks(dem, n = 6)
col_e <- pal_hypso("terrain", length(brk) - 1)
rel   <- relief_rgb(dem, brk, col_e, strength = 0.42)
# 区外衬底：单一浅灰乘山影，地形可辨但不带颜色信息
surround <- relief_rgb(dem, c(-1e5, 1e5), "#E9E9E9", strength = 0.30)
ty_v <- terra::vect(ty_m)

# ---------------- 模拟数据 ----------------
# 平滑随机场：粗格网上的白噪声三次样条插值到 DEM 格网
smooth_noise <- function(r, cells, seed) {
  set.seed(seed)
  co <- rast(ext(r), nrows = cells, ncols = max(2, round(cells * ncol(r) / nrow(r))),
             crs = crs(r))
  values(co) <- stats::rnorm(ncell(co))
  resample(co, r, method = "cubicspline")
}
z1 <- smooth_noise(dem, 10, SEED); z2 <- smooth_noise(dem, 30, SEED + 1)
slope <- terrain(dem, "slope", unit = "degrees")
q <- stats::quantile(values(mask(dem, ty_v)), c(0.02, 0.40, 0.60, 0.97), na.rm = TRUE)
centre <- st_transform(st_sfc(st_point(c(112.55, 37.87)), crs = 4326), CRS_M)
d_ctr  <- terra::distance(dem, terra::vect(centre))

# 土地利用：由高程、坡度、离城区距离和随机场按规则赋类，只为得到形态合理的斑块
LU <- data.frame(code  = 1:6,
                 label = c("Cropland", "Forest", "Grassland", "Water", "Built-up", "Bare land"),
                 col   = c("#E6D78A", "#4E8A4F", "#A9C98A", "#5B9BD5", "#8C8C8C", "#D8C9B0"))
lu <- ifel(dem < q[[2]] & slope < 6, 1, 3)
lu <- ifel((dem > q[[3]] & z1 > -0.3) | slope > 18, 2, lu)
lu <- ifel(dem > q[[4]], 6, lu)
lu <- ifel(d_ctr < 9000 + 3000 * z2 & slope < 8, 5, lu)
lu <- ifel(dem < q[[1]] & slope < 2, 4, lu)
lu <- mask(lu, ty_v)

# 采样点：研究区内 60 个，镉含量随离城区距离衰减并叠加对数正态误差
set.seed(SEED + 2)
sites <- st_sf(geometry = st_sample(ty_m, 60, type = "random"))
dist_km <- as.numeric(st_distance(sites, centre)) / 1000
sites$cd <- exp(log(0.22) + 1.1 * exp(-dist_km / 18) + stats::rnorm(nrow(sites), 0, 0.30))
gs <- graduated_sizes(sites$cd, c(-Inf, 0.3, 0.5, Inf), c(1.2, 2.1, 3.2), digits = 1)
sites$size <- gs$size
SITE_FILL <- "#2F5D8A"

# 土壤有机碳：随高程增加并叠加随机场，分六级
soc <- mask(6 + 12 * (dem - q[[1]]) / (q[[4]] - q[[1]]) + 2.2 * z1, ty_v)
brk_soc <- c(-1e5, 8, 10, 12, 14, 16, 1e5)
col_soc <- grDevices::hcl.colors(length(brk_soc) - 1, "YlGnBu", rev = TRUE)

assert_accent_unique(ACC, c(LU$col, SITE_FILL, col_soc, col_e))

# ---------------- 图面 ----------------
tag <- function(txt) annotate("label", x = -Inf, y = Inf, hjust = -0.06, vjust = 1.14,
                              label = txt, size = TXT_GG, family = "Arial",
                              fill = alpha("white", 0.85), label.r = unit(0, "mm"),
                              label.padding = unit(0.7, "mm"))
study <- list(geom_sf(data = ty_xm, fill = NA, colour = alpha("white", 0.7), linewidth = LW * 0.4),
              geom_sf(data = ty_m, fill = NA, colour = ACC, linewidth = LW_DAT))
panel <- function(base, ..., right = FALSE, bottom = FALSE) ggplot() + base + study + list(...) +
  win_coord(W_T) + scale_y_continuous(position = "right") +
  theme_map_pub() + lon_lat_theme(right, bottom)

p_a <- panel(geom_spatraster_rgb(data = rel, maxcell = 4e6),
             north_needle(W_T, ax = 0.945, ay = 0.22), tag("a  Elevation"),
             annotation_scale(location = "bl", width_hint = 0.28, height = unit(1.0, "mm"),
                              text_cex = TXT_PT / 12, text_family = "Arial",
                              line_width = LW / 0.353, pad_x = unit(2.2, "mm"),
                              pad_y = unit(2.2, "mm")))
p_b <- panel(list(geom_spatraster_rgb(data = surround, maxcell = 4e6),
                  geom_spatraster_rgb(data = class_rgb(lu, LU$code, LU$col, dem = dem),
                                      maxcell = 4e6)),
             tag("b  Land use"), right = TRUE)
p_c <- panel(geom_spatraster_rgb(data = surround, maxcell = 4e6),
             geom_sf(data = sites, aes(size = I(size)), shape = 21, fill = SITE_FILL,
                     colour = "white", stroke = 0.25),
             tag("c  Sampling sites"), bottom = TRUE)
p_d <- panel(list(geom_spatraster_rgb(data = surround, maxcell = 4e6),
                  geom_spatraster_rgb(data = relief_rgb(soc, brk_soc, col_soc, strength = 0),
                                      maxcell = 4e6)),
             tag("d  Soil organic carbon"), right = TRUE, bottom = TRUE)
for (p in list(p_a, p_b, p_c, p_d)) assert_window(p, W_T)

# ---------------- 图例条 ----------------
# 四条等高，高度取四个图例块中最高者；块左对齐到面板左缘。
lu_items <- data.frame(label = LU$label, type = "fill", fill = LU$col)
st_items <- data.frame(label = gs$labels, type = "point", shape = 21,
                       fill = SITE_FILL, colour = "white", size = gs$sizes)
TOPLEFT <- c(0.03, 0.97)
probe_h <- 60
LEG_H <- max(attr(legend_rows_block(mm_win(PW, probe_h), lu_items, PW, probe_h, anchor = TOPLEFT,
                                    corner = "tl", ncol = 3, backing = FALSE,
                                    title = "Land use (synthetic)"), "size_mm")[2],
             attr(legend_rows_block(mm_win(PW, probe_h), st_items, PW, probe_h, anchor = TOPLEFT,
                                    corner = "tl", ncol = 3, backing = FALSE,
                                    title = "Cd (mg/kg), synthetic"), "size_mm")[2],
             13) + 1.5
cat(sprintf("[layout] thematic panels %.1f x %.1f mm; legend strips %.1f mm\n", PW, PH, LEG_H))

ramp_strip <- function(cols, labs, title) legend_panel(PW, LEG_H,
  elev_legend_block(mm_win(PW, LEG_H), cols, labs, panel_h_mm = LEG_H, title = title,
                    x = c(0.06, 0.62), anchor = c(0.66, 0.06), backing = FALSE))
rows_strip <- function(items, title) legend_panel(PW, LEG_H,
  legend_rows_block(mm_win(PW, LEG_H), items, PW, LEG_H, anchor = TOPLEFT, corner = "tl",
                    ncol = 3, backing = FALSE, title = title))
l_a <- ramp_strip(col_e, elev_labels(brk), "Elevation (m)")
l_b <- rows_strip(lu_items, "Land use (synthetic)")
l_c <- rows_strip(st_items, "Cd (mg/kg), synthetic")
l_d <- ramp_strip(col_soc, elev_labels(brk_soc, every = 1), "SOC (g/kg), synthetic")

# ---------------- 定位图 ----------------
# 两级矢量定位图占满左列：中国框按窗口长宽比定高，山西框取剩余高度。
row1_h <- PH + mg$a$top + mg$a$bot + LEG_H
row2_h <- PH + mg$c$top + mg$c$bot + LEG_H
FIG_H  <- row1_h + GAP_V + row2_h
GAP_L  <- 4
bb0 <- bbox_union(prov_c, bnd_c)               # 南海诸岛落在主框内
dx <- bb0[["xmax"]] - bb0[["xmin"]]; dy <- bb0[["ymax"]] - bb0[["ymin"]]
W_CN <- c(xmin = bb0[["xmin"]] - 0.02 * dx, xmax = bb0[["xmax"]] + 0.02 * dx,
          ymin = bb0[["ymin"]] - 0.02 * dy, ymax = bb0[["ymax"]] + 0.02 * dy)
LOC_H <- LOC_W / win_aspect(W_CN)
SX_H  <- FIG_H - mg$a$top - LOC_H - GAP_L - mg$c$bot - LEG_H
sx_c  <- prov_c[prov_c$pcode == "14", ]
W_SX  <- fit_aspect(pad_win(st_bbox(sx_c), 0.04), LOC_W / SX_H)
ty_c  <- st_transform(ty_m, CRS_C)
loc_theme <- theme_map_pub() + theme(axis.text = element_blank(), axis.ticks = element_blank(),
                                     plot.margin = margin(0, 0, 0, 0))
p_loc <- ggplot() +
  geom_sf(data = prov_c, fill = "grey90", colour = "white", linewidth = LW * 0.35) +
  geom_sf(data = sx_c, fill = "grey72", colour = "white", linewidth = LW * 0.35) +
  geom_sf(data = bnd_c, colour = "grey35", linewidth = LW * 0.45) +
  geom_sf(data = st_as_sfc(st_bbox(pad_win(st_bbox(sx_c), 0.04), crs = st_crs(CRS_C))), fill = NA,
          colour = "grey20", linewidth = LW * 0.8) +
  tag("China") + win_coord(W_CN) + loc_theme
p_sx <- ggplot() +
  geom_sf(data = prov_c, fill = "grey90", colour = "white", linewidth = LW * 0.35) +
  geom_sf(data = sx_c, fill = "grey80", colour = "grey35", linewidth = LW * 0.6) +
  geom_sf(data = st_transform(ty_xm, CRS_C), fill = alpha(ACC, 0.25), colour = "white",
          linewidth = LW * 0.3) +
  geom_sf(data = ty_c, fill = NA, colour = ACC, linewidth = LW_DAT) +
  tag("Shanxi") + win_coord(W_SX) + loc_theme
assert_window(p_loc, W_CN); assert_window(p_sx, W_SX)
cat("[content] 中国全图必备内容覆盖核查\n")
check_cn_content(W_CN, crs = CRS_C)

# ---------------- 合成 ----------------
g <- with_font_device(list(
  a = pin_panel(p_a, PW, PH), b = pin_panel(p_b, PW, PH),
  c = pin_panel(p_c, PW, PH), d = pin_panel(p_d, PW, PH),
  la = pin_panel(l_a, PW, LEG_H), lb = pin_panel(l_b, PW, LEG_H),
  lc = pin_panel(l_c, PW, LEG_H), ld = pin_panel(l_d, PW, LEG_H),
  loc = pin_panel(p_loc, LOC_W, LOC_H), sx = pin_panel(p_sx, LOC_W, SX_H)))
# 一格 = 面板 + 其下的图例条；图例条按面板左边距缩进，左缘与面板框对齐
cell <- function(map, leg, m) arrangeGrob(
  map, arrangeGrob(nullGrob(), leg, nullGrob(), ncol = 3,
                   widths = unit(c(m$left, PW, m$side - m$left), "mm")),
  ncol = 1, heights = unit(c(PH + m$top + m$bot, LEG_H), "mm"))
grid4 <- arrangeGrob(cell(g$a, g$la, mg$a), nullGrob(), cell(g$b, g$lb, mg$b),
                     nullGrob(), nullGrob(), nullGrob(),
                     cell(g$c, g$lc, mg$c), nullGrob(), cell(g$d, g$ld, mg$d),
                     ncol = 3,
                     widths  = unit(c(PW + mg$a$side, GAP_M, PW + mg$b$side), "mm"),
                     heights = unit(c(row1_h, GAP_V, row2_h), "mm"))
loc_col <- arrangeGrob(nullGrob(), g$loc, nullGrob(), g$sx, nullGrob(), ncol = 1,
                       heights = unit(c(mg$a$top, LOC_H, GAP_L, SX_H, mg$c$bot + LEG_H), "mm"))
base <- arrangeGrob(nullGrob(), loc_col, nullGrob(), grid4, ncol = 4,
                    widths = unit(c(PAD_L, LOC_W, GAP_H, FIG_W - PAD_L - LOC_W - GAP_H), "mm"))
ft <- credit_footer(base, paste(
  "Land use, sampling sites and SOC are synthetic, for layout demonstration only.",
  "Boundaries: standard map GS(2024)0650. Elevation: ASTER GDEM v3."), FIG_H)

for (v in list(list("taiyuan_thematic.png", 300), list("taiyuan_thematic_preview.png", 150))) {
  ggsave(v[[1]], ft$grob, width = FIG_W, height = ft$height_mm, units = "mm",
         dpi = v[[2]], bg = "white", device = ragg::agg_png)
  cat(sprintf("WROTE %-30s %g x %.1f mm @ %d dpi  %.2f MB\n",
              v[[1]], FIG_W, ft$height_mm, v[[2]], file.info(v[[1]])$size / 1e6))
}
