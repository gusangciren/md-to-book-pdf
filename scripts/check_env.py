#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_env.py — 环境自检：确认能不能跑 md-to-book-pdf

用法：
  python scripts/check_env.py

检查四项：Python 版本 / 依赖库 / 霞鹜文楷字体 / Edge 或 Chrome。
缺什么就打印可直接照做的安装指引，全部就绪时以退出码 0 结束。
"""
import glob
import os
import platform
import shutil
import subprocess
import sys

MIN_PY = (3, 8)

FONT_HINT = (
    "下载：https://github.com/lxgw/LxgwWenKai/releases\n"
    "   Windows：解压后双击 ttf →「为所有用户安装」\n"
    "   macOS  ：双击 ttf → 字体册「安装字体」\n"
    "   Linux  ：cp LXGWWenKai-Regular.ttf /usr/share/fonts/ && fc-cache -fv"
)


def check_python():
    ok = sys.version_info >= MIN_PY
    print(f"[{'OK' if ok else '!!'}] Python {platform.python_version()}"
          f"（需要 ≥ {'.'.join(map(str, MIN_PY))}）")
    return ok


def check_deps():
    ok = True
    # 用pymupdf 而非已废弃的 fitz 别名——探测 fitz 本身就会触发弃用警告，
    # 而警告出现在用户跑的第一条命令里，观感很差
    for mod, pkg, why in (
        ("pymupdf", "pymupdf", "PDF 后处理（背景/页脚/书签/满版校验）"),
        ("markdown", "markdown", "Markdown → HTML"),
    ):
        try:
            m = __import__(mod)
            ver = getattr(m, "__version__", getattr(m, "version", "?"))
            print(f"[OK] {pkg} {ver}")
        except ImportError:
            ok = False
            print(f"[!!] 缺少 {pkg} —— {why}")
    if not ok:
        print("     安装：pip install -r requirements.txt")
    return ok


def find_font():
    system = platform.system()
    cands = []
    if system == "Windows":
        local = os.environ.get("LOCALAPPDATA", "")
        if local:
            fonts_dir = os.path.join(local, "Microsoft", "Windows", "Fonts")
            cands += glob.glob(os.path.join(fonts_dir, "LXGW*.*tf"))
        cands += glob.glob(os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "LXGW*.*tf"))
    elif system == "Darwin":
        cands += glob.glob(os.path.expanduser("~/Library/Fonts/LXGW*.*tf"))
        cands += glob.glob("/Library/Fonts/LXGW*.*tf")
        cands += glob.glob("/System/Library/Fonts/**/LXGW*.*tf", recursive=True)
    else:
        cands += glob.glob("/usr/share/fonts/**/LXGW*.*tf", recursive=True)
        cands += glob.glob(os.path.expanduser("~/.local/share/fonts/**/LXGW*.*tf"), recursive=True)
        cands += glob.glob(os.path.expanduser("~/.fonts/**/LXGW*.*tf"), recursive=True)
    return cands[0] if cands else None


def check_font():
    path = find_font()
    print(f"[{'OK' if path else '!!'}] 霞鹜文楷：{path or '未找到'}")
    if not path:
        print("     缺字体不会报错，但 PDF 中文会回退成系统默认字体，版式与示例不一致。")
        print("     安装：")
        print("     " + FONT_HINT)
    return bool(path)


def find_browser():
    system = platform.system()
    if system == "Windows":
        cands = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ]
    elif system == "Darwin":
        cands = [
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        ]
    else:
        cands = ["microsoft-edge", "microsoft-edge-stable", "google-chrome",
                 "google-chrome-stable", "chromium", "chromium-browser"]
    for c in cands:
        if os.path.exists(c):
            return c
    for c in cands:
        found = shutil.which(c)
        if found:
            return found
    return None


def check_browser():
    path = find_browser()
    print(f"[{'OK' if path else '!!'}] 浏览器：{path or '未找到 Edge / Chrome'}")
    if not path:
        print("     本工具用无头浏览器打印 PDF，必须有 Edge 或 Chrome 其一。")
        print("     Windows：系统自带 Edge，一般无需安装；macOS：brew install --cask microsoft-edge")
    return bool(path)


def main():
    print("=" * 46)
    print("md-to-book-pdf 环境自检")
    print("=" * 46)
    results = [check_python(), check_deps(), check_font(), check_browser()]
    print("=" * 46)
    if all(results):
        print("全部就绪，可以出书：")
        print('  python scripts/make_book.py --md-file 书稿.md --title "书名" \\')
        print('      --author "作者" --out 书名.pdf')
        return 0
    print("有缺失项，见上方指引。字体缺失只影响美观，浏览器/依赖缺失则无法出书。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
