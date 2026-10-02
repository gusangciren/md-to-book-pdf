"""
finalize_book.py
PyMuPDF 后处理：
- 在每个页面的内容流**最底层**绘制米白背景 #FBF7EE（不遮挡文字；直接 draw_rect 会把正文盖住）
- 增加页脚：{书籍标题} · {页码}（页面底部居中，霞鹜缺失时用内置中文字体 china-s 兜底）
- 第 1 页是封面时传 --has-cover，跳过封面页页脚
- 传 --toc-json 时写入 PDF 侧边栏书签大纲（章节树），便于阅读器导航
"""
import argparse
import json
import os

import pymupdf as fitz

BG = (0xFB / 255.0, 0xF7 / 255.0, 0xEE / 255.0)  # #FBF7EE 米白


def add_background_under_content(page):
    """用 Shape.commit(overlay=False) 把米白背景画在所有已有内容的下层，不遮挡文字"""
    rect = page.rect
    shape = page.new_shape()
    shape.draw_rect(rect)
    shape.finish(fill=BG, color=None)
    shape.commit(overlay=False)


def build_outline(toc_json, title, toc_page):
    """由 detect_chapters.py 产出的 toc.json 生成 PDF 书签大纲。

    toc.json 结构：[{"anchor": "chap_001", "title": "第一章 …", "page": 3}, …]
    层级：书名 → 目录 → 各章节。目录页里的可点击链接供页内跳转，
    书签大纲供阅读器侧边栏与「跳转到章节」使用，两者互为补充。
    """
    with open(toc_json, "r", encoding="utf-8") as f:
        items = json.load(f)

    outline = []
    if title:
        outline.append([1, title, 1])
    if toc_page and toc_page > 0:
        outline.append([1, "目录", toc_page])
    for it in items:
        page_no = int(it.get("page") or 0)
        if page_no < 1:
            continue
        outline.append([1, it["title"], page_no])
    return outline


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-pdf", required=True, help="Edge 第二次打印出的 raw_toc.pdf")
    parser.add_argument("--title", required=True, help="书籍标题（用于页脚）")
    parser.add_argument("--out-pdf", required=True, help="最终输出 PDF 路径")
    parser.add_argument("--has-cover", action="store_true",
                        help="第 1 页是封面时传入，跳过封面页的页脚")
    parser.add_argument("--toc-json", default=None,
                        help="detect_chapters.py 产出的 toc.json；传入则写入 PDF 侧边栏书签")
    parser.add_argument("--toc-page", type=int, default=0,
                        help="目录页页码（1-based）；与 --toc-json 一起在书签里加「目录」节点")
    args = parser.parse_args()

    doc = fitz.open(args.input_pdf)
    total = len(doc)

    if args.toc_json and os.path.exists(args.toc_json):
        outline = build_outline(args.toc_json, args.title, args.toc_page)
        # 页码越界保护：丢弃指向不存在页面的条目，避免生成打不开的书签
        outline = [o for o in outline if 1 <= o[2] <= total]
        if outline:
            doc.set_toc(outline)
            print(f"[书签] 已写入 {len(outline)} 条 PDF 侧边栏书签")
    elif args.toc_json:
        print(f"[警告] 未找到 {args.toc_json}，跳过书签写入")

    for i, page in enumerate(doc):
        add_background_under_content(page)
        if args.has_cover and i == 0:
            continue
        rect = page.rect
        footer = f"{args.title} · {i + 1}"
        footer_rect = fitz.Rect(0, rect.height - 40, rect.width, rect.height - 18)
        page.insert_textbox(
            footer_rect,
            footer,
            fontsize=9,
            fontname="china-s",
            color=(0.25, 0.22, 0.18),
            align=fitz.TEXT_ALIGN_CENTER,
        )
    doc.save(args.out_pdf, garbage=3, deflate=True)
    doc.close()
    print(f"[完成] 已输出 {args.out_pdf}")


if __name__ == "__main__":
    main()
