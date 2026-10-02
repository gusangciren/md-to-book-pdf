"""
qa_check.py
QA 自检脚本：抽取关键页面输出 PNG 截图，用于交付前校验排版问题。
"""

import _utf8_stdout  # noqa: F401  # 必须在其他 import 之前：保证中文输出不因终端编码崩溃
import argparse
import os

import pymupdf as fitz


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", required=True, help="待校验的最终 PDF")
    parser.add_argument("--out-snapshots", required=True, help="截图输出目录")
    args = parser.parse_args()

    os.makedirs(args.out_snapshots, exist_ok=True)

    doc = fitz.open(args.pdf)
    total = len(doc)
    sample_pages = [0, 1, 3, 6, 10]  # 封面/目录/正文/插图所在页视排版而定，取代表页
    count = 0
    for pno in sample_pages:
        if pno >= total:
            break
        pix = doc[pno].get_pixmap(dpi=150)
        out_path = os.path.join(args.out_snapshots, f"page_{pno + 1:02d}.png")
        pix.save(out_path)
        print(f"[截图] {out_path}")
        count += 1
    doc.close()
    print(f"[完成] 共输出 {count} 张校验截图（PDF 总页数 {total}）")


if __name__ == "__main__":
    main()
