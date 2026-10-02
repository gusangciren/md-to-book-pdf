"""
detect_chapters.py
在 raw.pdf 中探测每个章节扉页的真实页码，输出 toc.json（供 build_book.py 第二次运行回填目录）。
排版（字号/边距/图片）改动后必须重跑，禁止复用旧 toc.json。
"""
import argparse
import json
import os

import pymupdf as fitz


def norm(s):
    """去掉所有空白，避免 PDF 文本提取断行导致标题匹配失败"""
    return "".join(s.split())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-pdf", required=True, help="Edge 第一次打印出的 raw.pdf")
    parser.add_argument("--out-toc", required=True, help="输出 toc.json 路径")
    parser.add_argument("--chapters", required=True, help="build_book.py 生成的 chapters.json")
    args = parser.parse_args()

    with open(args.chapters, "r", encoding="utf-8") as f:
        chapters = json.load(f)

    doc = fitz.open(args.raw_pdf)
    page_texts = [doc[i].get_text() for i in range(len(doc))]
    doc.close()
    normalized = [norm(t) for t in page_texts]

    # 目录页自身也包含全部章节标题，必须从目录页之后开始找，否则第一章会匹配到目录页
    toc_page_idx = 0
    for i, t in enumerate(normalized):
        if "目录" in t:
            toc_page_idx = i
            break

    toc_list = []
    search_from = toc_page_idx + 1
    for meta in chapters:
        key = norm(meta["title"])
        page_no = None
        for i in range(search_from, len(normalized)):
            if key and key in normalized[i]:
                page_no = i + 1
                search_from = i + 1  # 章节顺序单调递增
                break
        if page_no is None:
            # 兜底：全书搜索
            for i in range(len(normalized)):
                if key and key in normalized[i]:
                    page_no = i + 1
                    break
        if page_no is None:
            print(f"[警告] 未在 PDF 中找到章节「{meta['title']}」，页码沿用上一章")
            page_no = toc_list[-1]["page"] if toc_list else 1
        toc_list.append({"anchor": meta["anchor"], "title": meta["title"], "page": page_no})

    out_dir = os.path.dirname(os.path.abspath(args.out_toc))
    os.makedirs(out_dir, exist_ok=True)
    with open(args.out_toc, "w", encoding="utf-8") as f:
        json.dump(toc_list, f, ensure_ascii=False, indent=2)
    print(f"[完成] 已写出 {args.out_toc}（{len(toc_list)} 章）")
    for item in toc_list:
        print(f"  第 {item['page']} 页  {item['title']}")


if __name__ == "__main__":
    main()
