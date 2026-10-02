#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
md-to-book-pdf ｜ 一键成书编排脚本

把整套流程串成一条命令：
  构建 HTML → Edge 打印 raw.pdf → 探测真实页码 → 回填目录 → 再打印 → 后处理 → QA 自检

设计目标（对外开源，别人开箱即用、效果与作者一致）：
- 依赖全部走 pip（pymupdf / markdown），不依赖任何写死的环境路径
- 浏览器（Edge / Chrome）跨平台自动探测，也可 --browser 手动指定
- 所有子步骤用 sys.executable 运行，配合虚拟环境即用
- 霞鹜文楷（LXGW WenKai）字体需本机安装，缺失时给出明确指引

用法示例：
  python make_book.py --md-file 书稿.md --title "书名" --author "作者" \
      --subtitle "副标题" --cover-style navy --out 输出.pdf
"""
import argparse
import os
import shutil
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)


# ---------------------------------------------------------------------------
# 浏览器自动探测（跨平台：Edge / Chrome）
# ---------------------------------------------------------------------------

def _candidate_browsers():
    return [
        # Windows
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        # macOS
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        # Linux（PATH 上的命令名）
        "microsoft-edge", "microsoft-edge-stable",
        "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
    ]


def find_browser(explicit=None):
    if explicit:
        if shutil.which(explicit) or os.path.exists(explicit):
            return explicit
        raise SystemExit(f"[错误] 指定的浏览器不存在：{explicit}")
    for b in _candidate_browsers():
        if os.path.exists(b):
            return b
    # 再试一次 PATH 上的命令名
    for b in _candidate_browsers():
        found = shutil.which(b)
        if found:
            return found
    raise SystemExit(
        "找不到 Edge / Chrome。请先安装其一，或用 --browser 指定可执行文件路径。\n"
        "  Windows: 安装 Microsoft Edge 或 Google Chrome\n"
        "  macOS:   brew install --cask microsoft-edge   （或 Google Chrome）\n"
        "  Linux:   sudo apt install microsoft-edge-stable  或 google-chrome-stable"
    )


# ---------------------------------------------------------------------------
# 子步骤
# ---------------------------------------------------------------------------

def run_py(script_name, *args):
    cmd = [sys.executable, os.path.join(SCRIPT_DIR, script_name), *args]
    print(f"\n$ {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def print_pdf(browser, html_path, out_pdf):
    """无头浏览器打印成 PDF。

    每次用独立的临时 --user-data-dir：用户此时往往正开着 Edge/Chrome，
    共用默认配置目录会被占用，导致打印静默失败或串到已有实例。
    """
    import tempfile
    from pathlib import Path
    profile = tempfile.mkdtemp(prefix="md2pdf_edge_")
    # as_uri() 会把中文/空格路径正确百分号编码，直接传裸路径在部分系统上会失败
    file_url = Path(os.path.abspath(html_path)).as_uri()
    cmd = [
        browser, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
        f"--user-data-dir={profile}",
        f"--print-to-pdf={out_pdf}", file_url,
    ]
    print(f"\n$ {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        # 旧版 Edge/Chrome 不带 --headless=new 也能用，兜底重试
        fallback = [
            browser, "--headless", "--disable-gpu", "--no-pdf-header-footer",
            f"--user-data-dir={profile}",
            f"--print-to-pdf={out_pdf}", file_url,
        ]
        print("[提示] --headless=new 失败，改用 --headless 重试")
        subprocess.run(fallback, check=True)
    finally:
        shutil.rmtree(profile, ignore_errors=True)


def check_font():
    """软校验：霞鹜文楷缺失时给出明确指引（不阻断，避免误报）。"""
    import platform
    name = "LXGW WenKai"
    if platform.system() == "Windows":
        cand = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Fonts")
        windir = os.path.expandvars(r"%WINDIR%\Fonts")
        found = any(
            f.lower().startswith("lxgw") and f.lower().endswith((".ttf", ".otf", ".ttc"))
            for d in (cand, windir)
            if os.path.isdir(d)
            for f in os.listdir(d)
        )
    elif platform.system() == "Darwin":
        found = os.path.exists(os.path.expanduser("~/Library/Fonts/LXGW WenKai.ttf")) or \
                os.path.exists("/Library/Fonts/LXGW WenKai.ttf")
    else:
        found = bool(shutil.which("fc-list")) and bool(
            subprocess.run(["fc-list"], capture_output=True, text=True).stdout
            .lower().find("lxgw wenkai") >= 0
        )
    if not found:
        print(
            f"\n[警告] 未检测到「{name}」字体。封面与正文均依赖它，缺失会导致排版与作者不一致。\n"
            "  安装方法见 README.md 的「字体依赖」一节，装好后重跑即可。"
        )


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(
        description="md-to-book-pdf 一键成书：Markdown → 精装 PDF",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--md-file", help="单文件书稿 .md")
    src.add_argument("--md-dir", help="多章节 .md 文件夹（按文件名排序，每文件一章）")
    p.add_argument("--title", required=True, help="书名（可含 \\n 手动断行）")
    p.add_argument("--author", required=True, help="作者名")
    p.add_argument("--subtitle", default=None, help="副标题")
    p.add_argument("--kicker", default=None, help="封面左上角小字（默认「{作者} · 著」）")
    p.add_argument("--quote", default=None, help="封面底部引言（可含 \\n）")
    p.add_argument("--meta", default=None, help="页脚 meta，如「三篇 · 中文全译本」")
    p.add_argument("--desc", default=None, help="系列型封面描述段落")
    p.add_argument("--steps", type=int, default=0, help="系列型封面数字圆圈个数")
    p.add_argument("--motif", default=None, help="封面 motif：curve/path/stairs/rings/brush/constellation")
    p.add_argument("--series", default=None, help="章节扉页 kicker（默认用书名）")
    p.add_argument("--split-by", default="h1", choices=["h1", "h2"],
                   help="分章方式：h1 按一级标题（默认）；h2 按二级标题 `## 第 N 章`")
    p.add_argument("--cover-style", default="light",
                   choices=["light", "forest", "navy", "ink", "wine", "red", "red-bright", "red-deep"], help="封面配色主题")
    p.add_argument("--no-cover", action="store_true", help="不要封面")
    p.add_argument("--cover", default=None, help="用户明确指定的封面图（不自动用文件夹图）")
    p.add_argument("--back-cover", default=None, help="封底图")
    p.add_argument("--browser", default=None, help="手动指定 Edge/Chrome 可执行文件路径")
    p.add_argument("--build-dir", default="./build", help="中间产物目录（默认 ./build）")
    p.add_argument("--out", required=True, help="最终输出 PDF 路径")
    args = p.parse_args()

    browser = find_browser(args.browser)
    print(f"[浏览器] {browser}")
    check_font()

    os.makedirs(args.build_dir, exist_ok=True)
    build_dir = os.path.abspath(args.build_dir)
    book_html = os.path.join(build_dir, "book.html")
    raw_pdf = os.path.join(build_dir, "raw.pdf")
    raw_toc_pdf = os.path.join(build_dir, "raw_toc.pdf")
    toc_json = os.path.join(build_dir, "toc.json")
    chapters_json = os.path.join(build_dir, "chapters.json")
    qa_dir = os.path.join(build_dir, "qa_snap")
    os.makedirs(qa_dir, exist_ok=True)

    # 1) 首次构建（目录无页码）
    build_args = ["--md-file", args.md_file] if args.md_file else ["--md-dir", args.md_dir]
    build_args += ["--title", args.title, "--author", args.author,
                   "--cover-style", args.cover_style, "--split-by", args.split_by,
                   "--out-html", book_html]
    for flag, val in (("--subtitle", args.subtitle), ("--kicker", args.kicker),
                      ("--quote", args.quote), ("--meta", args.meta),
                      ("--desc", args.desc), ("--motif", args.motif),
                      ("--series", args.series), ("--cover", args.cover),
                      ("--back-cover", args.back_cover)):
        if val:
            build_args += [flag, val]
    if args.steps:
        build_args += ["--steps", str(args.steps)]
    if args.no_cover:
        build_args += ["--no-cover"]
    run_py("build_book.py", *build_args)

    # 2) 打印 raw.pdf
    print_pdf(browser, book_html, raw_pdf)

    # 3) 探测章节真实页码
    run_py("detect_chapters.py", "--raw-pdf", raw_pdf,
           "--out-toc", toc_json, "--chapters", chapters_json)

    # 4) 二次构建（回填真实页码）
    run_py("build_book.py", *build_args)

    # 5) 再打印
    print_pdf(browser, book_html, raw_toc_pdf)

    # 6) 后处理（背景 + 页脚 + PDF 书签）
    finalize_args = ["--input-pdf", raw_toc_pdf, "--title", args.title,
                     "--out-pdf", args.out, "--toc-json", toc_json]
    if not args.no_cover:
        finalize_args.append("--has-cover")
    # 目录页位置：有封面时是第 2 页，无封面时是第 1 页
    finalize_args += ["--toc-page", "2" if not args.no_cover else "1"]
    run_py("finalize_book.py", *finalize_args)

    # 7) QA 自检
    run_py("qa_check.py", "--pdf", args.out, "--out-snapshots", qa_dir)

    # 8) 封面满版校验（几何 + 像素双判，留白则非零退出 → 整条流水线报错）
    if args.no_cover:
        print("\n[满版校验] --no-cover，跳过")
    else:
        print("\n[满版校验] 检查封面是否铺满整页…")
        run_py("check_bleed.py", args.out)

    print(f"\n[完成] 成书已输出：{args.out}")
    print(f"[QA 截图目录] {qa_dir}（请人工核对封面/目录页码/字体/图片）")


if __name__ == "__main__":
    main()
