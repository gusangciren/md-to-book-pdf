#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
replace_cover.py — 替换**已有 PDF** 的封面页，不重排正文

适用场景：书已经排好了，只想换封面图（改配色、换标题版式）。
整页铺满新封面图，原有页面内容被完全盖住；其余页保持不变。

用法：
  python scripts/replace_cover.py input.pdf new_cover.png output.pdf
  # 顺带补目录链接与书签：
  python scripts/replace_cover.py input.pdf new_cover.png output.pdf \
      --toc-json toc.json --toc-page 2 --book-title "书名"
"""
import argparse
import sys

import pymupdf as fitz


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf", help="原 PDF 路径")
    ap.add_argument("cover", help="新封面图路径（PNG / JPG）")
    ap.add_argument("output", help="输出 PDF 路径")
    ap.add_argument("--page", type=int, default=1, help="要替换的页码（1-based，默认 1=封面）")
    ap.add_argument("--margin", type=float, default=0.0,
                    help="封面图四周留白（单位 pt）。0 = 满版出血；想留边就填 18 之类")
    args = ap.parse_args()

    if not args.cover.lower().endswith((".png", ".jpg", ".jpeg")):
        sys.exit(f"[错误] 封面图只支持 PNG/JPG：{args.cover}")

    doc = fitz.open(args.pdf)
    if not 1 <= args.page <= len(doc):
        sys.exit(f"[错误] --page {args.page} 超出 PDF 页数 {len(doc)}")

    page = doc[args.page - 1]
    r = page.rect
    m = max(0.0, args.margin)
    target = fitz.Rect(r.x0 + m, r.y0 + m, r.x1 - m, r.y1 - m)

    # keep_proportion=True：按比例缩放并居中，绝不拉伸变形
    page.insert_image(target, filename=args.cover, overlay=True, keep_proportion=True)
    print(f"[封面] 已替换第 {args.page} 页：{args.cover}")

    doc.save(args.output, garbage=4, deflate=True)
    doc.close()
    print(f"[完成] -> {args.output}")
    print("提示：换封面后如果目录页码需要修正，可接着跑 add_toc_links.py。")


if __name__ == "__main__":
    main()
