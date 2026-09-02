# 示例：三级区位图（中国 → 山西 → 太原）
#
# 与 taiyuan_locator.R 的两级版相比，这版多演示三件事：
#   1. 国家面板的窗口按边界线图层的完整范围取，南海诸岛落在主框内。角框放不下，
#      因为引线锥要扫过面板下沿两角，二者必占同一块地方。
#   2. 掩膜与冲淡两种手法：周边国家用中性灰蓝，中国境内才上分层设色，国界因此
#      不必靠粗线也能读出来。
#   3. 两段引线串起三级，端点全部解析求得。
#
# 数据本仓库不分发，运行前把下面两个路径改成你自己的：
#   DEM_DIR   ASTER GDEM 压缩瓦片目录，需覆盖 N37-N38 / E111-E113
#   ADM_DIR   含「中国_市.shp」「中国_县.shp」「中国_省line.shp」的行政区划目录
# 国家与省级面板的粗底图由 ggmapcn::check_geodata() 自动下载。
#
# 出两版：taiyuan_three_level.png 300 dpi 为成品，_preview.png 150 dpi 供 README 引用。

# 南海怎么处理，两种做法二选一：
#   FALSE  窗口取全部要素，南海诸岛与断续线落在国家主框内，三级引线齐全。
#   TRUE   主框只放陆域，南海走右下角框。角框与引线锥占同一块地方，因此这一版
#          只保留山西到主图那一段引线，中国到山西改由红色块本身承担指示。
SCS_INSET <- FALSE
IX <- c(0.808, 0.985); IY <- c(0.020, 0.300)   # 角框在主框内的位置
# 《公开地图内容表示规范》第六条第三款：南海诸岛作中国地图附图时一律称「南海诸岛」。
# 此处不加注记，由使用者按投稿要求自行决定；要加就把名称填进 INSET_LABEL，
# 并相应放宽 IX，名称放不下角框就不能那么小。
INSET_LABEL <- NULL

SKILL   <- "../reference"          # 从 example/ 目录运行本脚本
DEM_DIR <- "F:/博士毕业论文/山西DEM"
ADM_DIR <- "F:/标准地图/中国省市县标准行政区划数据 审图号GS（2024）0650号/shp格式"

source(file.path(SKILL, "relief_basemap.R"))
source(file.path(SKILL, "palettes.R"))
suppressPackageStartupMessages({library(grid); library(gridExtra); library(ggspatial)})
sf_use_s2(FALSE)          # 行政面有自相交，s2 会直接报错

ACC <- "#C62828"          # 全图唯一强调色

# ---------------- 边界 ----------------
# gb 是 156 加六位国标码：4-5 位为省，4-7 位为地级市
shi  <- st_read(file.path(ADM_DIR, "中国_市.shp"), quiet = TRUE)
xian <- st_read(file.path(ADM_DIR, "中国_县.shp"), quiet = TRUE)
bnd  <- st_read(file.path(ADM_DIR, "中国_省line.shp"), quiet = TRUE)
shi$pcode <- substr(as.character(shi$gb), 4, 5)
prov <- aggregate(st_make_valid(shi)["pcode"], by = list(pcode = shi$pcode),
                  FUN = function(x) x[1], do_union = TRUE)
sx_shi <- shi[shi$pcode == "14", ]
ty     <- sx_shi[substr(as.character(sx_shi$gb), 4, 7) == "1401", ]
ty_x   <- xian[substr(as.character(xian$gb), 4, 7) == "1401", ]
cat(sprintf("[边界] 省级 %d 个；山西地级市 %d 个；太原下辖 %d 个\n",
            nrow(prov), nrow(sx_shi), nrow(ty_x)))

CRS_M <- "+proj=aea +lat_1=37.6 +lat_2=38.3 +lat_0=37.95 +lon_0=112.3 +datum=WGS84 +units=m +no_defs"
CRS_C <- "+proj=aea +lat_1=25 +lat_2=47 +lat_0=0 +lon_0=105 +datum=WGS84 +units=m +no_defs"

ty_m   <- st_transform(st_make_valid(ty), CRS_M)
ty_xm  <- st_transform(st_make_valid(ty_x), CRS_M)
prov_c <- st_transform(st_make_valid(prov), CRS_C)
bnd_c  <- st_transform(bnd, CRS_C)
sx_c   <- prov_c[prov_c$pcode == "14", ]

# ---------------- 主图窗口 ----------------
# 图例在图面右下，窗口贴着研究区取就没有空角可放。放大窗口直到图例区不压研究区，
# 研究区因此画得小一些，让出的边缘正是图例落脚的地方。
LEG_X <- c(0.596, 0.972); LEG_Y <- c(0.032, 0.170)
bb_ty <- st_bbox(ty_m)
W_M <- pad_until_clear(c(xmin = bb_ty[["xmin"]], xmax = bb_ty[["xmax"]],
                         ymin = bb_ty[["ymin"]], ymax = bb_ty[["ymax"]]),
                       ty_m, LEG_X, LEG_Y)

# ---------------- 版面：先定槽位，再撑窗口 ----------------
FIG_W <- 190; PAD_L <- 2; GAP_H <- 7; GAP_V <- 5.5
p_probe <- ggplot() + geom_sf(data = ty_m) +
  coord_sf(xlim = W_M[c("xmin","xmax")], ylim = W_M[c("ymin","ymax")], expand = FALSE) +
  scale_y_continuous(position = "right") + theme_map_pub()
mg <- with_font_device(panel_margins(p_probe))

col_w   <- 0.240 * FIG_W
panel_w <- FIG_W - PAD_L - col_w - GAP_H - mg$side
panel_h <- panel_w / win_aspect(W_M)
# 两个定位框的高度按各自窗口的长宽比分配，不硬性对半：对半会逼出上下留白，
# 而山西南北长，本来就需要更多高度。上下限防止任一框被压扁。
avail <- panel_h - GAP_V

# 国家窗口必须取「所有要进框的图层」的合并范围。中国_省line.shp 只有 8 条境界线段
# （含南海断续线），最北仅到 38.68 度，单取它的 bbox 会把东北、内蒙、新疆、台湾整片
# 裁掉，而且图面看不出异常。合并后南海断续线也在框内，不必另开角框。
# 角框版的主框只放陆域，取值时排除三沙市（460300）
bb0 <- if (SCS_INSET)
  bbox_union(st_transform(st_make_valid(
    shi[substr(as.character(shi$gb), 4, 9) != "460300", ]), CRS_C)) else
  bbox_union(prov_c, bnd_c)
dx <- bb0[["xmax"]] - bb0[["xmin"]]; dy <- bb0[["ymax"]] - bb0[["ymin"]]
bb <- c(xmin = bb0[["xmin"]] - 0.02 * dx, xmax = bb0[["xmax"]] + 0.02 * dx,
        ymin = bb0[["ymin"]] - 0.02 * dy, ymax = bb0[["ymax"]] + 0.02 * dy)
h_cn <- min(max(col_w / win_aspect(bb), 0.34 * avail), 0.55 * avail)
h_sx <- avail - h_cn
W_CN <- fit_aspect(bb, col_w / h_cn)

# 角框压不得陆地。窗口右下角此刻还在陆上，框放哪儿都会压，所以向东扩到太平洋，
# 再按新长宽比重定框高。扩窗改长宽比、fit_aspect 又可能补高把框挪回陆上，故迭代。
if (SCS_INSET) {
  for (i in 1:12) {
    W_CN <- widen_for_inset(W_CN, IX, IY, prov_c, side = "xmax")
    h_cn <- min(max(col_w / win_aspect(W_CN), 0.34 * avail), 0.55 * avail)
    W_CN <- fit_aspect(W_CN, col_w / h_cn)
    if (inset_is_clear(W_CN, IX, IY, prov_c)) break
  }
  assert_inset_clear(W_CN, IX, IY, prov_c)
  h_sx <- avail - h_cn
  fr_cn <- frac_fun(W_CN)
}
W_SX <- fit_aspect(st_bbox(st_transform(st_union(st_make_valid(sx_shi)), CRS_C)),
                   col_w / h_sx)
cat(sprintf("[layout] col %.1f mm; main %.1f x %.1f mm; locators %.1f / %.1f mm\n",
            col_w, panel_w, panel_h, h_cn, h_sx))

# ---------------- 地形 ----------------
tiles <- vsizip_tiles(DEM_DIR, "^ASTGTM_N3[78]E11[123][.]img[.]zip$")
dem_m <- load_dem(tiles, crs = CRS_M, win = W_M, fact = 4)
brk_m <- elev_breaks(dem_m, n = 6)
col_m <- pal_hypso("terrain", length(brk_m) - 1)
rel_m <- relief_rgb(dem_m, brk_m, col_m, strength = 0.42)

if (!requireNamespace("ggmapcn", quietly = TRUE)) stop("定位面板底图需要 ggmapcn")
ggmapcn::check_geodata(files = "gebco_2024_China.tif", quiet = TRUE)
geb <- system.file("extdata", "gebco_2024_China.tif", package = "ggmapcn")

# 国家面板：周边国家用中性灰蓝，中国境内掩膜后上分层设色。跨度大，分级手工给，
# 让高原、盆地、平原各占一档，比按分位推更贴合读图习惯。
BRK_CN <- c(-1e5, 200, 500, 1000, 2000, 3000, 4000, 5000, 1e5)
COL_CN <- pal_hypso("terrain", length(BRK_CN) - 1)
# 分级上界压到 5000：若把界线设在 4500，青藏高原绝大部分落进最深一档，整块压成
# 深红，既盖掉高原内部的起伏，也把视线从红色的山西上引开。
dem_cn <- load_dem(geb, crs = CRS_C, win = W_CN, fact = 1, res = 4500)
cn_mask <- terra::vect(st_union(prov_c))
rel_world <- relief_rgb(dem_cn, BRK_SURROUND, PAL_SURROUND, strength = 0.20)
rel_cn    <- relief_rgb(terra::mask(dem_cn, cn_mask), BRK_CN, COL_CN, strength = 0.38)

dem_sx <- load_dem(geb, crs = CRS_C, win = W_SX, fact = 1, res = 700)
brk_sx <- elev_breaks(dem_sx, n = 6)
rel_sx <- relief_rgb(dem_sx, brk_sx, pal_hypso("terrain", length(brk_sx) - 1),
                     strength = 0.32)
# 省界外罩白纱：地形仍可见，但山西是全饱和的那一块，省的轮廓因此读得出来。
# 两级版的定位面板用的是整体去饱和，两种手法各演示一次。
veil_sx <- st_difference(st_as_sfc(st_bbox(W_SX, crs = st_crs(CRS_C))),
                         st_union(st_make_valid(st_transform(sx_shi, CRS_C))))

# ---------------- 面板 ----------------
lab <- function(txt) annotate("label", x = -Inf, y = Inf, hjust = -0.10, vjust = 1.14,
                              label = txt, size = TXT_GG, family = "Arial",
                              fill = alpha("white", 0.85), label.r = unit(0, "mm"),
                              label.padding = unit(0.7, "mm"))
theme_loc <- function() theme_map_pub() +
  theme(axis.text = element_blank(), axis.ticks = element_blank(),
        plot.margin = margin(0, 0, 0, 0))

sx_box <- st_as_sfc(st_bbox(sx_c))
# 角框版把南海一带的境界线整体交给角框，主框不再画半截断续线。bnd_c 里还有西部
# 边境的线段，所以按位置分而不是按序号取。
sansha    <- st_transform(st_make_valid(
               shi[substr(as.character(shi$gb), 4, 9) == "460300", ]), CRS_C)
scs_zone  <- st_buffer(st_as_sfc(st_bbox(sansha)), 3e5)
in_scs    <- lengths(st_intersects(bnd_c, scs_zone)) > 0
bnd_cn    <- if (SCS_INSET) bnd_c[!in_scs, ] else bnd_c

# coord_sf 不放进图层列表：geom_sf 自带一个默认 coord_sf，排在其后就会把已设的
# 窗口替换掉，面板悄悄退回数据全域。coord_sf 一律最后加。
cn_layers <- function(dw, dc, bl = bnd_cn) list(
  geom_spatraster_rgb(data = dw, maxcell = 3e6),
  geom_spatraster_rgb(data = dc, maxcell = 3e6),
  geom_sf(data = prov_c, fill = NA, colour = alpha("white", 0.55), linewidth = LW * 0.3),
  geom_sf(data = bl, colour = "grey20", linewidth = LW * 0.5))

win_coord <- function(w) coord_sf(xlim = w[c("xmin","xmax")], ylim = w[c("ymin","ymax")],
                                  expand = FALSE)

p_cn <- ggplot() + cn_layers(rel_world, rel_cn) +
  geom_sf(data = sx_c, fill = alpha(ACC, 0.65), colour = ACC, linewidth = LW * 0.5) +
  lab("China") + win_coord(W_CN) + theme_loc()

if (SCS_INSET) {
  # 角框窗口先按角框的物理长宽比撑到位，否则 coord_sf 在框内留信箱边，右下两边对不齐
  scs_lines <- bnd_c[in_scs, ]
  W_SCS <- fit_aspect(bbox_union(sansha, scs_lines), inset_aspect(W_CN, IX, IY))
  dem_scs <- load_dem(geb, crs = CRS_C, win = W_SCS, fact = 1, res = 4500)
  p_scs <- ggplot() +
    cn_layers(relief_rgb(dem_scs, BRK_SURROUND, PAL_SURROUND, strength = 0.18),
              relief_rgb(terra::mask(dem_scs, cn_mask), BRK_CN, COL_CN, strength = 0.35),
              bl = scs_lines) +
    win_coord(W_SCS) + theme_loc() +
    theme(panel.border = element_rect(colour = "grey30", fill = NA, linewidth = LW * 0.8))
  assert_window(p_scs, W_SCS)
  p_cn <- p_cn + corner_inset(p_scs, W_CN, IX, IY)
  if (!is.null(INSET_LABEL))
    p_cn <- p_cn + annotate("text", x = fr_cn$fx(IX[2]), y = fr_cn$fy(IY[2] + 0.075),
                            hjust = 1, label = INSET_LABEL, size = TXT_GG * 0.86,
                            family = "Arial", colour = "black", lineheight = 0.95)
}
assert_window(p_cn, W_CN)

ty_c   <- st_transform(ty_m, CRS_C)
ty_box <- st_as_sfc(st_bbox(ty_c))
p_sx <- ggplot() +
  geom_spatraster_rgb(data = rel_sx, maxcell = 2e6) +
  geom_sf(data = veil_sx, fill = alpha("white", 0.45), colour = NA) +
  geom_sf(data = st_transform(st_make_valid(sx_shi), CRS_C), fill = NA,
          colour = alpha("white", 0.6), linewidth = LW * 0.45) +
  geom_sf(data = st_union(sx_c), fill = NA, colour = "grey15", linewidth = LW * 1.1) +
  geom_sf(data = ty_c, fill = alpha(ACC, 0.6), colour = ACC, linewidth = LW * 0.6) +
  geom_sf(data = ty_box, fill = NA, colour = ACC, linewidth = LW * 1.2) +
  lab("Shanxi") + win_coord(W_SX) + theme_loc()

p_main <- ggplot() +
  geom_spatraster_rgb(data = rel_m, maxcell = 4e6) +
  geom_sf(data = ty_xm, fill = NA, colour = alpha("white", 0.65), linewidth = LW * 0.5) +
  geom_sf(data = ty_m, fill = NA, colour = ACC, linewidth = LW_DAT * 1.3) +
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

cat("[content] 中国全图必备内容覆盖核查
")
if (SCS_INSET) check_cn_content(W_CN, W_SCS, crs = CRS_C) else check_cn_content(W_CN, crs = CRS_C)

assert_window(p_sx, W_SX)
assert_window(p_main, W_M)

# ---------------- 合成 ----------------
grobs <- with_font_device(list(
  main = pin_panel(p_main, panel_w, panel_h),
  cn   = pin_panel(p_cn,   col_w,   h_cn),
  sx   = pin_panel(p_sx,   col_w,   h_sx)))
FIG_H <- panel_h + mg$top + mg$bot

base <- arrangeGrob(
  nullGrob(),
  arrangeGrob(nullGrob(), grobs$cn, nullGrob(), grobs$sx, nullGrob(), ncol = 1,
              heights = unit(c(mg$top, h_cn, GAP_V, h_sx, mg$bot), "mm")),
  nullGrob(), grobs$main, ncol = 4,
  widths = unit(c(PAD_L, col_w, GAP_H, panel_w + mg$side), "mm"))

cn_rect   <- c(x0 = PAD_L, x1 = PAD_L + col_w, yt = mg$top, yb = mg$top + h_cn)
sx_rect   <- c(x0 = PAD_L, x1 = PAD_L + col_w,
               yt = mg$top + h_cn + GAP_V, yb = mg$top + h_cn + GAP_V + h_sx)
main_rect <- c(x0 = PAD_L + col_w + GAP_H + mg$left,
               x1 = PAD_L + col_w + GAP_H + mg$left + panel_w,
               yt = mg$top, yb = mg$top + panel_h)
b1 <- box_in(st_bbox(sx_box), W_CN, cn_rect)     # 中国框里的山西
b2 <- box_in(st_bbox(ty_box), W_SX, sx_rect)     # 山西框里的太原
segs <- rbind(
  data.frame(x1 = b2[["x1"]], y1 = b2[["yt"]], x2 = main_rect[["x0"]], y2 = main_rect[["yt"]]),
  data.frame(x1 = b2[["x1"]], y1 = b2[["yb"]], x2 = main_rect[["x0"]], y2 = main_rect[["yb"]]))
# 中国到山西这一段只在无角框时画：角框在国家面板右下，正压在引线锥的必经之路上
if (!SCS_INSET) segs <- rbind(
  data.frame(x1 = b1[["x0"]], y1 = b1[["yb"]], x2 = sx_rect[["x0"]], y2 = sx_rect[["yt"]]),
  data.frame(x1 = b1[["x1"]], y1 = b1[["yb"]], x2 = sx_rect[["x1"]], y2 = sx_rect[["yt"]]),
  segs)
fig <- add_leaders(base, segs, FIG_H)

STEM <- if (SCS_INSET) "taiyuan_three_level_inset" else "taiyuan_three_level"
for (v in list(list(paste0(STEM, ".png"), 300),
               list(paste0(STEM, "_preview.png"), 150))) {
  ggsave(v[[1]], fig, width = FIG_W, height = FIG_H, units = "mm",
         dpi = v[[2]], bg = "white", device = ragg::agg_png)
  cat(sprintf("WROTE %-34s %g x %.1f mm @ %d dpi  %.2f MB\n",
              v[[1]], FIG_W, FIG_H, v[[2]], file.info(v[[1]])$size / 1e6))
}
