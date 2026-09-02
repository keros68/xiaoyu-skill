# 示例：太原市区位图
#
# 两级面板：左为山西省定位，右为太原市主图，虚线锥连接。演示分级设色乘山影、
# 先定槽位再撑窗口、图廓件与引线几何。
#
# 数据本仓库不分发，运行前把下面三个路径改成你自己的：
#   DEM_DIR   ASTER GDEM 压缩瓦片目录，需覆盖 N37-N38 / E111-E113
#   ADM_DIR   含「中国_市.shp」「中国_县.shp」的行政区划目录
#   GEBCO     省级面板用的粗 DEM，由 ggmapcn::check_geodata() 自动下载
#
# 出两版：taiyuan_locator.png 300 dpi 为成品，taiyuan_locator_preview.png
# 150 dpi 供 README 引用。两版尺寸一致，只差分辨率。

SKILL   <- "../reference"          # 从 example/ 目录运行本脚本
DEM_DIR <- "F:/博士毕业论文/山西DEM"
ADM_DIR <- "F:/标准地图/中国省市县标准行政区划数据 审图号GS（2024）0650号/shp格式"

source(file.path(SKILL, "relief_basemap.R"))
source(file.path(SKILL, "palettes.R"))
suppressPackageStartupMessages({library(grid); library(gridExtra); library(ggspatial)})
sf_use_s2(FALSE)          # 行政面有自相交，s2 会直接报错

ACC <- "#C62828"          # 全图唯一强调色：研究区

# ---------------- 边界 ----------------
# gb 是 156 加六位国标码，山西省前缀 14，太原市 1401
shi  <- st_read(file.path(ADM_DIR, "中国_市.shp"), quiet = TRUE)
xian <- st_read(file.path(ADM_DIR, "中国_县.shp"), quiet = TRUE)
sx_shi <- shi[substr(as.character(shi$gb), 4, 5) == "14", ]
ty     <- sx_shi[substr(as.character(sx_shi$gb), 4, 7) == "1401", ]
ty_x   <- xian[substr(as.character(xian$gb), 4, 7) == "1401", ]
cat(sprintf("[边界] 山西地级市 %d 个；太原下辖 %d 个区县\n", nrow(sx_shi), nrow(ty_x)))

CRS_M <- "+proj=aea +lat_1=37.6 +lat_2=38.3 +lat_0=37.95 +lon_0=112.3 +datum=WGS84 +units=m +no_defs"
sx_shi <- st_transform(st_make_valid(sx_shi), CRS_M)
ty     <- st_transform(st_make_valid(ty), CRS_M)
ty_x   <- st_transform(st_make_valid(ty_x), CRS_M)

# ---------------- 主图窗口 ----------------
# 图例在图面右下，窗口贴着研究区取就没有空角可放。放大窗口直到图例区不压研究区，
# 研究区因此画得小一些，让出的边缘正是图例落脚的地方。
LEG_X <- c(0.596, 0.972); LEG_Y <- c(0.032, 0.170)
b <- as.numeric(st_bbox(ty))
W_M <- pad_until_clear(c(xmin = b[1], xmax = b[3], ymin = b[2], ymax = b[4]),
                       ty, LEG_X, LEG_Y)

# ---------------- 版面：先定槽位 ----------------
FIG_W <- 190; PAD_L <- 2; GAP_H <- 7
p_probe <- ggplot() + geom_sf(data = ty) +
  coord_sf(xlim = W_M[c("xmin","xmax")], ylim = W_M[c("ymin","ymax")], expand = FALSE) +
  scale_y_continuous(position = "right") + theme_map_pub()
mg <- with_font_device(panel_margins(p_probe))

col_w   <- 0.235 * FIG_W
panel_w <- FIG_W - PAD_L - col_w - GAP_H - mg$side
panel_h <- panel_w / win_aspect(W_M)
cat(sprintf("[版面] 左列 %.1f mm；主图 panel %.1f x %.1f mm\n", col_w, panel_w, panel_h))

# 定位窗口撑到与主图等高的槽位。coord_sf 长宽比固定，窗口形状不符就会留信箱边，
# 两个图框因此不等高。
W_SX <- fit_aspect(st_bbox(st_union(sx_shi)), col_w / panel_h)

# ---------------- 地形 ----------------
# 主图用 30 m ASTER，省级面板用 GEBCO 0.05 度。宽面板不需要 30 m，窄面板不能用 5 km。
tiles <- vsizip_tiles(DEM_DIR, "^ASTGTM_N3[78]E11[123][.]img[.]zip$")
dem_m <- load_dem(tiles, crs = CRS_M, win = W_M, fact = 4)
brk_m <- elev_breaks(dem_m, n = 6)
col_m <- pal_hypso("terrain", length(brk_m) - 1)
rel_m <- relief_rgb(dem_m, brk_m, col_m, strength = 0.42)

if (!requireNamespace("ggmapcn", quietly = TRUE)) stop("省级面板底图需要 ggmapcn")
ggmapcn::check_geodata(files = "gebco_2024_China.tif", quiet = TRUE)
geb <- system.file("extdata", "gebco_2024_China.tif", package = "ggmapcn")
dem_s <- load_dem(geb, crs = CRS_M, win = W_SX, fact = 1, res = 700)
brk_s <- elev_breaks(dem_s, n = 6)
# 定位面板用去饱和色带并再冲淡：它是背景，红色的太原才该是最先被看到的东西
rel_s <- relief_rgb(dem_s, brk_s, pal_hypso("muted", length(brk_s) - 1),
                    strength = 0.26, wash = 0.18)

# ---------------- 主图 ----------------
fx <- function(t) W_M[["xmin"]] + t * (W_M[["xmax"]] - W_M[["xmin"]])
fy <- function(t) W_M[["ymin"]] + t * (W_M[["ymax"]] - W_M[["ymin"]])

p_main <- ggplot() +
  geom_spatraster_rgb(data = rel_m, maxcell = 4e6) +
  geom_sf(data = ty_x, fill = NA, colour = alpha("white", 0.65), linewidth = LW * 0.5) +
  geom_sf(data = ty, fill = NA, colour = ACC, linewidth = LW_DAT * 1.3) +
  elev_legend_block(W_M, col_m, elev_labels(brk_m), panel_h_mm = panel_h) +
  north_needle(W_M) +
  annotate("label", x = Inf, y = Inf, hjust = 1.10, vjust = 1.14, label = "Taiyuan",
           size = TXT_GG, family = "Arial", fill = alpha("white", 0.85),
           label.r = unit(0, "mm"), label.padding = unit(0.7, "mm")) +
  coord_sf(xlim = W_M[c("xmin","xmax")], ylim = W_M[c("ymin","ymax")], expand = FALSE) +
  scale_y_continuous(position = "right") +      # 纬度标注让开左侧，给引线留路
  annotation_scale(location = "bl", width_hint = 0.24, height = unit(1.1, "mm"),
                   text_cex = TXT_PT / 12, text_family = "Arial",
                   line_width = LW / 0.353, pad_x = unit(2.5, "mm"),
                   pad_y = unit(2.5, "mm")) +
  theme_map_pub()

# ---------------- 定位面板 ----------------
ty_box <- st_as_sfc(st_bbox(ty))
p_loc <- ggplot() +
  geom_spatraster_rgb(data = rel_s, maxcell = 2e6) +
  geom_sf(data = sx_shi, fill = NA, colour = alpha("white", 0.6), linewidth = LW * 0.45) +
  geom_sf(data = st_union(sx_shi), fill = NA, colour = "grey15", linewidth = LW * 1.1) +
  geom_sf(data = ty, fill = alpha(ACC, 0.6), colour = ACC, linewidth = LW * 0.6) +
  geom_sf(data = ty_box, fill = NA, colour = ACC, linewidth = LW * 1.2) +
  annotate("label", x = -Inf, y = Inf, hjust = -0.10, vjust = 1.14, label = "Shanxi",
           size = TXT_GG, family = "Arial", fill = alpha("white", 0.85),
           label.r = unit(0, "mm"), label.padding = unit(0.7, "mm")) +
  coord_sf(xlim = W_SX[c("xmin","xmax")], ylim = W_SX[c("ymin","ymax")], expand = FALSE) +
  theme_map_pub() +
  theme(axis.text = element_blank(), axis.ticks = element_blank(),
        plot.margin = margin(0, 0, 0, 0))

assert_window(p_main, W_M)
assert_window(p_loc, W_SX)

# ---------------- 合成 ----------------
grobs <- with_font_device({
  list(main = pin_panel(p_main, panel_w, panel_h),
       loc  = pin_panel(p_loc,  col_w,   panel_h))
})
FIG_H <- panel_h + mg$top + mg$bot

base <- arrangeGrob(
  nullGrob(),
  arrangeGrob(nullGrob(), grobs$loc, nullGrob(), ncol = 1,
              heights = unit(c(mg$top, panel_h, mg$bot), "mm")),
  nullGrob(), grobs$main, ncol = 4,
  widths = unit(c(PAD_L, col_w, GAP_H, panel_w + mg$side), "mm"))

# 引线端点解析求得：槽位尺寸已定死，红框在面板内的位置由窗口比例换算即可
loc_rect  <- c(x0 = PAD_L, x1 = PAD_L + col_w, yt = mg$top, yb = mg$top + panel_h)
main_rect <- c(x0 = PAD_L + col_w + GAP_H + mg$left,
               x1 = PAD_L + col_w + GAP_H + mg$left + panel_w,
               yt = mg$top, yb = mg$top + panel_h)
bx <- box_in(st_bbox(ty_box), W_SX, loc_rect)
segs <- rbind(
  data.frame(x1 = bx[["x1"]], y1 = bx[["yt"]], x2 = main_rect[["x0"]], y2 = main_rect[["yt"]]),
  data.frame(x1 = bx[["x1"]], y1 = bx[["yb"]], x2 = main_rect[["x0"]], y2 = main_rect[["yb"]]))
fig <- add_leaders(base, segs, FIG_H)

for (v in list(list("taiyuan_locator.png", 300),
               list("taiyuan_locator_preview.png", 150))) {
  ggsave(v[[1]], fig, width = FIG_W, height = FIG_H, units = "mm",
         dpi = v[[2]], bg = "white", device = ragg::agg_png)
  cat(sprintf("WROTE %-34s %g x %.1f mm @ %d dpi  %.2f MB\n",
              v[[1]], FIG_W, FIG_H, v[[2]], file.info(v[[1]])$size / 1e6))
}
