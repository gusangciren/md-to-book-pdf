
import _utf8_stdout  # noqa: F401  # 必须在其他 import 之前：保证中文输出不因终端编码崩溃
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
add_toc_links.py — 给**已有 PDF** 补加可点击目录 + 侧边栏书签（不重新排版）

适用场景：PDF 已经做好了，但目录点不动 / 没有章节书签。
本脚本只在目录页扫描文字行、按 y 坐标聚行，给每一行加内部跳转链接，并写入 PDF 大纲。

用法：
  python scripts/add_toc_links.py input.pdf output.pdf \
      --toc-json toc.json --toc-page 2 --book-title "书名"

toc.json 由 detect_chapters.py 产出，结构：
  [{"anchor": "chap_001", "title": "第一章 …", "page": 3}, …]
也接受简单映射 {"3": 5, "后记": 49}。
"""
import argparse
import json
import re
import sys

import pymupdf as fitz


def norm(s):
    return "".join(s.split())


def load_toc(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # 统一成 [(匹配键列表, 页码, 标题)]，兼容两种格式
    out = []
    if isinstance(data, list):
        for it in data:
            out.append(([it.get("title", ""), it.get("anchor", "")], int(it["page"]), it.get("title", "")))
    else:
        for k, v in data.items():
            out.append(([k], int(v), k))
    return out


def collect_rows(page):
    """把目录页的文本 span 按 y 坐标聚成行"""
    spans = []
    for b in page.get_text("dict")["blocks"]:
        for line in b.get("lines", []):
            for s in line["spans"]:
                if s["text"].strip():
                    spans.append({"text": s["text"], "bbox": s["bbox"]})
    spans.sort(key=lambda s: (s["bbox"][1], s["bbox"][0]))

    rows = []
    for s in spans:
        cy = (s["bbox"][1] + s["bbox"][3]) / 2
        for row in rows:
            if abs(row["cy"] - cy) < 5:
                row["spans"].append(s)
                row["cy"] = (row["cy"] + cy) / 2
                break
        else:
            rows.append({"cy": cy, "spans": [s]})
    for row in rows:
        row["spans"].sort(key=lambda s: s["bbox"][0])
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf", help="原 PDF 路径")
    ap.add_argument("output", help="输出 PDF 路径")
    ap.add_argument("--toc-json", required=True, help="detect_chapters.py 产出的 toc.json")
    ap.add_argument("--toc-page", type=int, default=2, help="目录页页码（1-based），默认 2")
    ap.add_argument("--book-title", default="", help="书名，用作书签根节点")
    ap.add_argument("--page-offset", type=int, default=0,
                    help="页码整体偏移。toc.json 记录的页码与你手上这份 PDF 差几页时用它修正")
    args = ap.parse_args()

    toc = load_toc(args.toc_json)
    doc = fitz.open(args.pdf)
    if not 1 <= args.toc_page <= len(doc):
        sys.exit(f"[错误] --toc-page {args.toc_page} 超出 PDF 页数 {len(doc)}")
    page = doc[args.toc_page - 1]
    total = len(doc)
    bottom_limit = page.rect.height - 40  # 页脚区域不参与匹配

    added = 0
    outline = []
    if args.book_title:
        outline.append([1, args.book_title, 1])
    outline.append([1, "目录", args.toc_page])

    for row in collect_rows(page):
        if row["cy"] > bottom_limit:
            continue
        line = "".join(s["text"] for s in row["spans"])
        if any(k in line for k in ("Ctrl", "提示", "阅读")):
            continue
        line_norm = norm(line)

        hit = None
        for keys, page_no, title in toc:
            for k in keys:
                if k and norm(k) and norm(k) in line_norm:
                    hit = (page_no, title or line.strip())
                    break
            if hit:
                break
        if not hit:
            continue

        target = hit[0] + args.page_offset
        if not 1 <= target <= total:
            continue

        y0 = min(s["bbox"][1] for s in row["spans"]) - 2
        y1 = max(s["bbox"][3] for s in row["spans"]) + 2
        x0 = min(s["bbox"][0] for s in row["spans"]) - 5
        x1 = max(s["bbox"][2] for s in row["spans"]) + 5
        page.insert_link({
            "kind": fitz.LINK_GOTO,
            "from": fitz.Rect(x0, y0, x1, y1),
            "page": target - 1,
            "to": fitz.Point(0, 0),
            "zoom": 0,
        })
        outline.append([1, hit[1], target])
        added += 1
        print(f"  + {line.strip()[:40]} -> p{target}")

    if outline:
        doc.set_toc(outline)
    doc.save(args.output, garbage=4, deflate=True)
    doc.close()
    print(f"[完成] {added} 个目录链接 + {len(outline)} 条书签 -> {args.output}")


if __name__ == "__main__":
    main()
