"""
make_cover.py
独立封面生成器：只出封面，不成书。

为什么需要独立入口：
- 迭代封面配色时不必跑整条成书流水线（build → print → detect → 回填 → 再 print），
  一轮要 1-2 分钟；这里只需 1 秒出图，改参数立刻看到效果。
- 网站书籍入口、公众号推头、社交卡片等场景只要封面图，不需要 PDF。
- 输出的 PNG 走Edge headless 截图（真实渐变/字体/字距），所见即所得；
  不要用 PyMuPDF 渲染 SVG 做预览——它不支持 SVG 渐变，背景会变纯黑。

用法：
    python scripts/make_cover.py --title "闭环" --author "古思" --style red-bright \\
        --subtitle "在你睡觉的时候赚钱" --quote "……" --out 封面.png

    # 一次出多套主题挑色
    python scripts/make_cover.py --title "闭环" --author "古思" --all-styles --out-dir previews/

    # 只出矢量 SVG（要交给设计师改）
    python scripts/make_cover.py --title "闭环" --author "古思" --style wine --format svg --out 封面.svg
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_book import PALETTES, DEFAULT_MOTIF, build_cover_svg  # noqa: E402


def _candidate_browsers():
    return [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
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
    for b in _candidate_browsers():
        found = shutil.which(b)
        if found:
            return found
    raise SystemExit(
        "找不到 Edge / Chrome。先安装其一，或用 --browser 指定可执行文件路径。\n"
        "  Windows: 安装 Microsoft Edge\n"
        "  macOS:   brew install --cask microsoft-edge\n"
        "  Linux:   sudo apt install microsoft-edge-stable"
    )


def svg_to_png(browser, svg, out_png, scale=2):
    """SVG → PNG：包一层最小 HTML 再截图。

    直接截图 .svg 文件在部分平台上会得到空白图（视口与 SVG 固有尺寸不匹配），
    所以写进一个把SVG 撑满视口的 HTML 里再截。

    scale=2 出 1588×2246 的2倍图，用作网站/推头足够清晰。
    """
    import base64
    from pathlib import Path

    b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    html = (
        '<!DOCTYPE html><html><head><meta charset="utf-8"><style>'
        "html,body{margin:0;padding:0;background:transparent;}"
        "img{display:block;width:794px;height:1123px;}"
        "</style></head><body>"
        f'<img src="data:image/svg+xml;base64,{b64}">'
        "</body></html>"
    )
    tmpdir = tempfile.mkdtemp(prefix="mkcover_")
    try:
        html_path = os.path.join(tmpdir, "cover.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        os.makedirs(os.path.dirname(os.path.abspath(out_png)) or ".", exist_ok=True)
        # 独立 profile：用户可能正开着浏览器，共用默认目录会因文件锁失败
        profile = tempfile.mkdtemp(prefix="mkcover_edge_")
        cmd = [
            browser, "--headless=new", "--disable-gpu",
            "--default-background-color=00000000",
            f"--force-device-scale-factor={scale}",
            f"--user-data-dir={profile}",
            f"--screenshot={os.path.abspath(out_png)}",
            "--window-size=794,1123",
            Path(html_path).as_uri(),
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except subprocess.CalledProcessError:
            cmd[1] = "--headless"          # 旧版 Edge 不认 --headless=new
            subprocess.run(cmd, check=True, capture_output=True)
        finally:
            shutil.rmtree(profile, ignore_errors=True)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    if not os.path.exists(out_png):
        raise SystemExit("[错误] 截图失败：浏览器没有产出 PNG（可手动用 Edge 打开 SVG 排查）")
    return out_png


def one_cover(args, style, out_path):
    svg = build_cover_svg(
        args.title, args.subtitle, args.author, style,
        kicker=args.kicker, quote=args.quote, meta=args.meta,
        desc=args.desc, steps=args.steps,
        motif=args.motif or DEFAULT_MOTIF.get(style),
    )
    motif = args.motif or DEFAULT_MOTIF.get(style)
    if args.format == "svg":
        # 也要建目录：--out build/cover.svg 这种路径在 CI 里很常见，
        # 只有 PNG 分支建目录会让 svg 分支抛 FileNotFoundError
        os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(svg)
        print(f"[封面] {style:<11} → {out_path}（矢量，可交给设计师改）")
        return out_path

    browser = find_browser(args.browser)
    svg_to_png(browser, svg, out_path, scale=args.scale)
    size = os.path.getsize(out_path)
    print(f"[封面] {style:<11} → {out_path}（{args.scale}x · {size // 1024} KB）")
    return out_path


def main():
    ap = argparse.ArgumentParser(
        description="独立封面生成器：只出封面图，不成书",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("用法：")[1] if "用法：" in __doc__ else None,
    )
    ap.add_argument("--title", required=True, help="书名，可含 \\n 手动断行")
    ap.add_argument("--author", required=True, help="作者名")
    ap.add_argument("--subtitle", default="", help="副标题")
    ap.add_argument("--kicker", default=None, help="左上角小字（默认「{作者} · 著」）")
    ap.add_argument("--quote", default="", help="底部金边引言，最多两行（可含 \\n）")
    ap.add_argument("--meta", default="", help="页脚 meta 文字")
    ap.add_argument("--desc", default="", help="系列/课程型封面：描述段落")
    ap.add_argument("--steps", type=int, default=0, help="系列/课程型封面：数字步骤圆圈个数")
    ap.add_argument("--motif", default=None,
                    choices=["curve", "path", "stairs", "rings", "brush", "constellation"],
                    help="线条图案（默认按主题自动）")
    ap.add_argument("--style", default=None, choices=list(PALETTES), help="配色主题")
    ap.add_argument("--all-styles", action="store_true", help="一次出全部 8 套主题用于挑色")
    ap.add_argument("--format", default="png", choices=["png", "svg"], help="输出位图或矢量")
    ap.add_argument("--scale", type=int, default=2, help="PNG 倍率（2 = 1588×2246）")
    ap.add_argument("--out", default=None, help="单张输出路径（配合 --style）")
    ap.add_argument("--out-dir", default="cover-previews", help="批量输出目录（配合 --all-styles）")
    ap.add_argument("--browser", default=None, help="手动指定浏览器可执行文件")
    args = ap.parse_args()

    if not args.all_styles and not args.style:
        raise SystemExit("请指定 --style（%s）或 --all-styles" % "/".join(PALETTES))

    if args.all_styles:
        os.makedirs(args.out_dir, exist_ok=True)
        ext = args.format
        for st in PALETTES:
            safe = args.title.replace("\\n", "").replace("/", "_")
            out = os.path.join(args.out_dir, f"cover-{st}-{safe}.{ext}")
            one_cover(args, st, out)
        print(f"\n[完成] {len(PALETTES)} 套封面已输出到 {os.path.abspath(args.out_dir)}")
        return

    out = args.out or os.path.join(args.out_dir, f"cover-{args.style}.{args.format}")
    one_cover(args, args.style, out)
    print("\n[提示] 封面比例与 A4 完全一致（794×1123 = 210×297mm），"
          "成书时会满版铺满整页，无需再裁。")


if __name__ == "__main__":
    main()