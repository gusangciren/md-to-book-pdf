"""
check_bleed.py
封面满版出血自动校验：判定 PDF 首页封面是否真的铺满整页。

为什么需要自动化：
- 「封面有没有留白边」用眼睛看会漏——PDF 阅读器的页面预览本身带背景色和缩放，
  几毫米的白边在截图里几乎看不出来（历史上就是这样漏掉的）。
- 判据是**几何法**：读首页图片 bbox，与页面矩形比对四边留白（mm）。
- 另有像素法（四边采样）仅作**参考输出**，不参与判定：浅色主题封面
  （light/forest）的渐变顶部本身接近页面底色，像素法无法区分「浅色封面」
  与「真留白」，强行判定会误报。

用法：
    python scripts/check_bleed.py 书.pdf            # 校验首页
    python scripts/check_bleed.py 书.pdf --tol 1.0  # 容差 1mm（默认 0.5mm）
    python scripts/check_bleed.py 书.pdf --no-cover # 无封面书，跳过
"""

import _utf8_stdout  # noqa: F401  # 必须在其他 import 之前：保证中文输出不因终端编码崩溃
import argparse
import os
import sys

import pymupdf

MM = 72 / 25.4  # pt per mm


def _is_page_bg(r, g, b):
    """判断是否为页面底色（真留白）。

    不能用「接近纯白」当判据 —— light/forest 等主题封面顶部就是米白浅色渐变
    （实测 RGB 246,242,230），会被误判成白边。
    页面上真正露出的空白只能是页面自身的米白底 #FBF7EE=(251,247,238)，
    因此按「与页面底色的距离」判定，比绝对白阈值可靠。
    """
    return abs(r - 251) <= 6 and abs(g - 247) <= 6 and abs(b - 238) <= 6


def check(path, tol=0.5):
    doc = pymupdf.open(path)
    try:
        total = len(doc)
        page = doc[0]
        W, H = page.rect.width, page.rect.height
        infos = page.get_image_info()
        if not infos:
            print("[失败] 首页没有图片 —— 封面没被嵌入（不是留白问题，是完全丢失）")
            return False

        ok = True
        # ---- ① 几何法：图片 bbox 四边留白 ----
        # 封面可能被 Edge 拆成多个 image tile（渐变分层），取能覆盖面积最大的那个
        info = max(infos, key=lambda i: (i["bbox"][2] - i["bbox"][0]) * (i["bbox"][3] - i["bbox"][1]))
        x0, y0, x1, y1 = info["bbox"]
        gaps = {
            "左": x0 / MM,
            "上": y0 / MM,
            "右": (W - x1) / MM,
            "下": (H - y1) / MM,
        }
        print(f"页面{ W / MM:.1f} × {H / MM:.1f} mm，共 {total} 页")
        print(f"首页图片 bbox：左{x0 / MM:.2f} 上{y0 / MM:.2f} "
              f"右{x1 / MM:.1f} 下{y1 / MM:.1f} mm")
        for side, v in gaps.items():
            # 负值代表溢出页面（object-fit:cover 的正常结果），按 0 处理
            flag = "OK" if v <= tol else "留白"
            if v > tol:
                ok = False
            print(f"  {side}边留白 {max(0.0, v):.2f} mm  [{flag}]")

        # ---- ② 像素法：四边采样（仅作参考，不参与判定） ----
        # 为什么只作参考：浅色主题封面（light/forest）的渐变顶部本身就接近页面底色
        # （实测 forest 左上角 RGB 249,245,235 vs 底色 251,247,238，仅差 2–3），
        # 像素法在这种主题下从原理上无法区分「浅色封面」与「真留白」，
        # 强行判定会误报。几何法（bbox）能精确判定，是唯一判据。
        # 用低 dpi 快速采样，避免为了几个像素渲染整页
        pix = page.get_pixmap(dpi=36)
        w, h, n = pix.width, pix.height, pix.n

        def sample(xs, ys, label):
            blanks = 0
            total_px = 0
            for x, y in zip(xs, ys):
                if 0 <= x < w and 0 <= y < h:
                    o = (y * w + x) * n
                    total_px += 1
                    if _is_page_bg(pix.samples[o], pix.samples[o + 1], pix.samples[o + 2]):
                        blanks += 1
            if total_px == 0:
                return
            print(f"  {label}采样：{blanks}/{total_px} 接近页面底色（{blanks / total_px:.0%}）[参考]")

        m = max(1, w // 20)
        sample(range(m, w - m, max(1, (w - 2 * m) // 12)), [0] * 12, "上边")
        sample(range(m, w - m, max(1, (w - 2 * m) // 12)), [h - 1] * 12, "下边")
        sample([0] * 12, range(m, h - m, max(1, (h - 2 * m) // 12)), "左边")
        sample([w - 1] * 12, range(m, h - m, max(1, (h - 2 * m) // 12)), "右边")

        print()
        if ok:
            print(f"[通过] 封面满版铺满整页（四边留白 ≤ {tol} mm），无白边。")
        else:
            print("[失败] 封面未满版，存在白边。修法见 SKILL.md 踩坑第 7 条：")
            print("  @page cover { margin: 0 } + .cover-page img { width:100%; height:100%; "
                  "object-fit:cover } + body { margin:0 }，三者缺一不可。")
        return ok
    finally:
        doc.close()


def main():
    ap = argparse.ArgumentParser(description="封面满版出血校验")
    ap.add_argument("pdf", help="待校验的 PDF")
    ap.add_argument("--tol", type=float, default=0.5, help="容差 mm（默认 0.5）")
    ap.add_argument("--no-cover", action="store_true", help="无封面书，检查后直接通过")
    args = ap.parse_args()

    if args.no_cover:
        print("[跳过] --no-cover，不校验封面")
        sys.exit(0)

    # 先判存在性：否则 pymupdf 会抛 FileNotFoundError traceback，
    # 新手看到一大段栈根本不知道只是路径打错了
    if not os.path.isfile(args.pdf):
        print(f"[错误] 找不到文件：{args.pdf}")
        print("请确认路径拼写（Windows 下若含中文或空格，注意用引号包住整个路径）。")
        sys.exit(2)

    sys.exit(0 if check(args.pdf, args.tol) else 1)


if __name__ == "__main__":
    main()