"""
check_bleed.py
封面满版出血自动校验：判定 PDF 首页封面是否真的铺满整页。

为什么需要自动化：
- 「封面有没有留白边」用眼睛看会漏——PDF 阅读器的页面预览本身带背景色和缩放，
  几毫米的白边在截图里几乎看不出来（历史上就是这样漏掉的）。
- 本脚本用两种独立手段交叉判定，任何一种判定为「有白边」即报错退出码 1：
  ① 几何法：读首页图片 bbox，与页面矩形比对的四边留白（mm）
  ② 像素法：直接采样页面四边像素，看是否与封面主色系一致（能抓到 bbox 正确但图像本身留白的边界情况）

用法：
    python scripts/check_bleed.py 书.pdf            # 校验首页
    python scripts/check_bleed.py 书.pdf --tol 1.0  # 容差 1mm（默认 0.5mm）
    python scripts/check_bleed.py 书.pdf --no-cover # 无封面书，跳过
"""

import _utf8_stdout  # noqa: F401  # 必须在其他 import 之前：保证中文输出不因终端编码崩溃
import argparse
import sys

import pymupdf

MM = 72 / 25.4  # pt per mm


def _is_blank(r, g, b):
    """接近米白/纯白即视为白边。正文底色是 #FBF7EE=(251,247,238)"""
    return r > 236 and g > 232 and b > 222


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

        # ---- ② 像素法：四边采样 ----
        # 用低 dpi 快速采样，避免为了几个像素渲染整页
        pix = page.get_pixmap(dpi=36)
        w, h, n = pix.width, pix.height, pix.n

        def sample(xs, ys, label):
            nonlocal ok
            blanks = 0
            total_px = 0
            for x, y in zip(xs, ys):
                if 0 <= x < w and 0 <= y < h:
                    o = (y * w + x) * n
                    total_px += 1
                    if _is_blank(pix.samples[o], pix.samples[o + 1], pix.samples[o + 2]):
                        blanks += 1
            if total_px == 0:
                return
            ratio = blanks / total_px
            flag = "OK" if ratio <= 0.25 else "疑似白边"
            if ratio > 0.25:
                ok = False
            print(f"  {label}采样：{blanks}/{total_px} 像素发白（{ratio:.0%}）[{flag}]")

        m = max(1, w // 20)
        sample(range(m, w - m, max(1, (w - 2 * m) // 12)), [0] * 12, "上边")
        sample(range(m, w - m, max(1, (w - 2 * m) // 12)), [h - 1] * 12, "下边")
        sample([0] * 12, range(m, h - m, max(1, (h - 2 * m) // 12)), "左边")
        sample([w - 1] * 12, range(m, h - m, max(1, (h - 2 * m) // 12)), "右边")

        print()
        if ok:
            print(f"[通过] 封面满版铺满整页（四边留白 ≤ {tol} mm），无白边。")
        else:
            print(f"[失败] 封面未满版，存在白边。修法见 SKILL.md 踩坑第7 条：")
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
    sys.exit(0 if check(args.pdf, args.tol) else 1)


if __name__ == "__main__":
    main()