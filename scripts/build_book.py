"""
build_book.py
CLI 工具：解析单文件/多文件 Markdown，生成用于 Edge headless 打印的 HTML。

- 封面三种来源（优先级从高到低）：
  1. --cover 用户本地图片（存在则直接嵌入）
  2. 默认自动生成排版封面（SVG data URI，「安静编辑感」版式：kicker + 大字标题 + 金色短线 +
     宽字距副标题 + 极简线条 motif + 金边引言 + 发丝线页脚；三种配色主题，不用 CSS 背景）
  3. --no-cover 不生成封面
- 自动切分章节并生成章节扉页（金色大编号 + 标题 + 金色分隔线）
- 同时写出 chapters.json（章节锚点与标题），供 detect_chapters.py 探测真实页码
- 第二次运行时自动读取输出目录下的 toc.json，把真实页码回填进目录
"""

import _utf8_stdout  # noqa: F401  # 必须在其他 import 之前：保证中文输出不因终端编码崩溃
import argparse
import base64
import json
import os
import xml.etree.ElementTree as ET

import markdown


# ---------------------------------------------------------------------------
# 章节切分
# ---------------------------------------------------------------------------

def split_by_h1(md_text):
    """模式 A：按一级标题 `# ` 切分章节，返回 [(章节标题, 正文md), ...]"""
    chapters = []
    title = None
    pre = []
    buf = []
    for line in md_text.split("\n"):
        if line.startswith("# "):
            if title is not None:
                chapters.append((title, "\n".join(buf)))
            elif "".join(pre).strip():
                chapters.append(("前言", "\n".join(pre)))
                pre = []
            title = line[2:].strip()
            buf = []
        else:
            if title is None:
                pre.append(line)
            else:
                buf.append(line)
    if title is not None:
        chapters.append((title, "\n".join(buf)))
    elif "".join(pre).strip():
        chapters.append(("前言", "\n".join(pre)))
    return chapters


def split_by_files(md_dir):
    """模式 B：文件夹内每个 md 文件为一章，按文件名排序合并"""
    files = sorted(f for f in os.listdir(md_dir) if f.lower().endswith(".md"))
    if not files:
        raise SystemExit(f"目录中没有找到 .md 文件: {md_dir}")
    chapters = []
    for fn in files:
        with open(os.path.join(md_dir, fn), "r", encoding="utf-8") as f:
            text = f.read()
        lines = text.split("\n")
        title = None
        for i, line in enumerate(lines):
            if line.startswith("# "):
                title = line[2:].strip()
                del lines[i]
                break
        if not title:
            title = os.path.splitext(fn)[0]
        chapters.append((title, "\n".join(lines)))
    return chapters


def split_by_h2(md_text):
    """模式 C：按二级标题 `## ` 切分章节（稿件里章节是 `## 第 N 章` 形式时使用）。

    对真实稿件做了容错：自动跳过「首个 `## ` 之前的所有块」（通常是 `# 书名`、
    YAML frontmatter、封面图引用、副标题），以及「`## 目录` + 目录列表」整段，
    只把 `## 第 N 章` 当作独立章节。这样别人拿原始 `## 第 N 章` 稿件就能直接成书，
    无需先手动预处理成 `# 第 N 章`。
    """
    chapters = []
    title = None
    buf = []
    in_toc = False
    for line in md_text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("## "):
            heading = stripped[3:].strip()
            # 跳过目录章及其后的列表，直到下一个 `## `
            if heading.replace(" ", "") in ("目录", "目录。", "目录:"):
                if title is not None:
                    chapters.append((title, "\n".join(buf)))
                    title = None
                    buf = []
                in_toc = True
                continue
            in_toc = False
            if title is not None:
                chapters.append((title, "\n".join(buf)))
            title = heading
            buf = []
        else:
            if in_toc:
                continue
            # 首个 `## ` 之前的块（书名 / frontmatter / 副标题）直接丢弃，不生成「前言」
            if title is None:
                continue
            buf.append(line)
    if title is not None:
        chapters.append((title, "\n".join(buf)))
    return chapters


# ---------------------------------------------------------------------------
# 自动生成封面（SVG data URI，「安静编辑感」编辑排版风）
# 说明：不用 CSS 背景（打印会丢），整页封面画成一张 SVG 内嵌图片。
# SVG 里不能引用外部/网络资源，但本机系统字体（霞鹜文楷）可用。
# ---------------------------------------------------------------------------

W, H = 794, 1123  # A4 @96dpi
X = 92            # 统一左边距

PALETTES = {
    "light": dict(   # 米白暖底 · 深墨绿大字 · 金色点缀（参考：保罗·格雷厄姆文集）
        bg_top="#f7f1e4", bg_bot="#ede3cd", title="#2f4a3a", accent="#c08b33",
        kicker="#93897a", subtitle="#b8862b", quote="#55534a", quotebar="#c08b33",
        hairline="#a99d84", meta="#b8862b", muted="#6e675a",
        motif="#2f4a3a", motif2="#c9973f", grid="#8a7f68",
    ),
    "forest": dict(  # 深墨绿渐变底 · 奶油大字 · 金色点缀（参考：选择改变命运）
        bg_top="#33543f", bg_bot="#1a3125", title="#f2e8d5", accent="#cfa14a",
        kicker="#c7ba9c", subtitle="#cfa14a", quote="#d9cfba", quotebar="#cfa14a",
        hairline="#8f9a83", meta="#cfa14a", muted="#b5ab93",
        motif="#d4a94e", motif2="#d4a94e", grid="#d4a94e",
    ),
    "navy": dict(    # 藏蓝渐变底 · 白色大字 · 橙色点缀（参考：YC 创业课）
        bg_top="#26415f", bg_bot="#142741", title="#f5f2ea", accent="#e0763c",
        kicker="#e08a4f", subtitle="#e0955c", quote="#ccd6e4", quotebar="#e0763c",
        hairline="#6d84a0", meta="#e0955c", muted="#9fb0c4",
        motif="#e8804a", motif2="#e8804a", grid="#e8804a",
    ),
    "ink": dict(     # 墨黑底 · 暖米白字 · 琥珀金笔触（写作/文集气质，创意主题）
        bg_top="#26211c", bg_bot="#100c09", title="#f1e9da", accent="#c8922e",
        kicker="#b9a98e", subtitle="#d9a24e", quote="#e8dfce", quotebar="#c8922e",
        hairline="#6b5f4e", meta="#d9a24e", muted="#a99c84",
        motif="#c8922e", motif2="#c8922e", grid="#c8922e",
    ),
    "wine": dict(    # 深酒红底 · 米白字 · 金线星座（文学经典气质，创意主题）
        bg_top="#5a2230", bg_bot="#2c0f17", title="#f3e7d8", accent="#caa24b",
        kicker="#cdb0a0", subtitle="#caa24b", quote="#ecdcd0", quotebar="#caa24b",
        hairline="#8a6b63", meta="#caa24b", muted="#c2a596",
        motif="#e7c988", motif2="#e7c988", grid="#e7c988",
    ),
    "red": dict(     # 中国红底 · 暖白字 · 亮金点缀（系列/课程型封面，高辨识度）
        bg_top="#b32430", bg_bot="#6e0b14", title="#fffbf2", accent="#f2c14e",
        kicker="#f7d9a8", subtitle="#f2c14e", quote="#f0e6d8", quotebar="#f2c14e",
        hairline="#d9984a", meta="#f2c14e", muted="#e6c9a8",
        motif="#f2c14e", motif2="#f2c14e", grid="#f2c14e",
    ),
    "red-bright": dict(  # 鲜亮红底 · 暖白字 · 亮金点缀
        bg_top="#d62828", bg_bot="#9a1b1b", title="#fffbf2", accent="#f2c14e",
        kicker="#f7d9a8", subtitle="#f2c14e", quote="#f0e6d8", quotebar="#f2c14e",
        hairline="#e6a94a", meta="#f2c14e", muted="#f0d9b8",
        motif="#f2c14e", motif2="#f2c14e", grid="#f2c14e",
    ),
    "red-deep": dict(    # 深红底 · 暖白字 · 亮金点缀
        bg_top="#7a1018", bg_bot="#3d0509", title="#fffbf2", accent="#f2c14e",
        kicker="#f7d9a8", subtitle="#f2c14e", quote="#f0e6d8", quotebar="#f2c14e",
        hairline="#b87a3a", meta="#f2c14e", muted="#dcbfa0",
        motif="#f2c14e", motif2="#f2c14e", grid="#f2c14e",
    ),
}

DEFAULT_MOTIF = {"light": "curve", "forest": "path", "navy": "stairs", "ink": "brush", "wine": "constellation", "red": "rings", "red-bright": "rings", "red-deep": "rings"}


def _esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _wrap_title(title, per_line=7, max_lines=4):
    """书名换行：支持显式 \\n（含字面反斜杠 n）；超长按每行 per_line 字硬换行"""
    out = []
    for part in title.replace("\\n", "\n").split("\n"):
        part = part.strip()
        if not part:
            continue
        for i in range(0, len(part), per_line):
            out.append(part[i:i + per_line])
    return out[:max_lines]


def _wrap_plain(text, per_line, max_lines=2):
    out = []
    for part in text.replace("\\n", "\n").split("\n"):
        part = part.strip()
        if not part:
            continue
        for i in range(0, len(part), per_line):
            out.append(part[i:i + per_line])
    return out[:max_lines]


def _title_font(lines):
    n = max(len(l) for l in lines)
    if n <= 6:
        return 104, 6
    if n == 7:
        return 90, 2
    return 78, 2


# ----- 背景与 defs -----

def _bg(p, style):
    t = ["<defs>"]
    if style == "light":
        t.append(f'<linearGradient id="bg" x1="0" y1="0" x2="0.35" y2="1">'
                 f'<stop offset="0" stop-color="{p["bg_top"]}"/>'
                 f'<stop offset="1" stop-color="{p["bg_bot"]}"/></linearGradient>')
        t.append('<radialGradient id="blob1" cx="0.20" cy="0.10" r="0.55">'
                 '<stop offset="0" stop-color="#fffef7" stop-opacity="0.9"/>'
                 '<stop offset="1" stop-color="#fffef7" stop-opacity="0"/></radialGradient>')
        t.append('<radialGradient id="blob2" cx="0.90" cy="0.55" r="0.45">'
                 '<stop offset="0" stop-color="#fff8e8" stop-opacity="0.4"/>'
                 '<stop offset="1" stop-color="#fff8e8" stop-opacity="0"/></radialGradient>')
        # 纸纹颗粒（feTurbulence，极低透明度，不影响清晰度）
        t.append('<filter id="grain" x="0" y="0" width="100%" height="100%">'
                 '<feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" stitchTiles="stitch"/>'
                 '<feColorMatrix type="matrix" values="0 0 0 0 0.45 0 0 0 0 0.40 0 0 0 0 0.33 0 0 0 0.05 0"/>'
                 '</filter>')
    else:
        t.append(f'<linearGradient id="bg" x1="0" y1="0" x2="0.4" y2="1">'
                 f'<stop offset="0" stop-color="{p["bg_top"]}"/>'
                 f'<stop offset="1" stop-color="{p["bg_bot"]}"/></linearGradient>')
        t.append('<radialGradient id="blob1" cx="0.12" cy="0.08" r="0.55">'
                 '<stop offset="0" stop-color="#ffffff" stop-opacity="0.07"/>'
                 '<stop offset="1" stop-color="#ffffff" stop-opacity="0"/></radialGradient>')
        t.append('<radialGradient id="blob2" cx="0.9" cy="0.95" r="0.5">'
                 '<stop offset="0" stop-color="#000000" stop-opacity="0.18"/>'
                 '<stop offset="1" stop-color="#000000" stop-opacity="0"/></radialGradient>')
    t.append("</defs>")
    t.append(f'<rect width="{W}" height="{H}" fill="url(#bg)"/>')
    t.append(f'<rect width="{W}" height="{H}" fill="url(#blob1)"/>')
    t.append(f'<rect width="{W}" height="{H}" fill="url(#blob2)"/>')
    if style == "light":
        t.append(f'<rect width="{W}" height="{H}" filter="url(#grain)"/>')
    return "".join(t)


# ----- 极简线条 motif -----

def _motif_curve(p):
    """J 型增长曲线：浅色网格 + 深色曲线 + 金色端点（占满中部留白区）"""
    t = []
    for gy in (650, 710, 770):
        t.append(f'<line x1="118" y1="{gy}" x2="672" y2="{gy}" '
                 f'stroke="{p["grid"]}" stroke-opacity="0.22" stroke-width="1"/>')
    t.append(f'<line x1="118" y1="620" x2="118" y2="880" stroke="{p["grid"]}" stroke-opacity="0.35" stroke-width="1.5"/>')
    t.append(f'<line x1="118" y1="880" x2="672" y2="880" stroke="{p["grid"]}" stroke-opacity="0.35" stroke-width="1.5"/>')
    t.append(f'<path d="M 126 872 L 450 862 C 570 852 615 750 658 598" fill="none" '
             f'stroke="{p["motif"]}" stroke-width="4.5" stroke-linecap="round"/>')
    t.append(f'<circle cx="126" cy="872" r="6" fill="{p["motif"]}"/>')
    t.append(f'<circle cx="658" cy="598" r="20" fill="none" stroke="{p["motif2"]}" stroke-width="1.5" stroke-opacity="0.9"/>')
    t.append(f'<circle cx="658" cy="598" r="9.5" fill="{p["motif2"]}"/>')
    return "".join(t)


def _motif_path(p):
    """抉择路径：金色节点连线 + 同心圆底纹"""
    t = []
    for r in (60, 105, 150):
        t.append(f'<circle cx="640" cy="640" r="{r}" fill="none" '
                 f'stroke="{p["motif"]}" stroke-opacity="0.16" stroke-width="1.2"/>')
    t.append(f'<circle cx="455" cy="640" r="7" fill="none" stroke="{p["motif"]}" stroke-width="2"/>')
    t.append(f'<line x1="472" y1="652" x2="520" y2="688" stroke="{p["motif"]}" '
             f'stroke-opacity="0.8" stroke-width="2.5" stroke-dasharray="2 8" stroke-linecap="round"/>')
    t.append(f'<path d="M 618 566 L 618 655 C 618 685 602 692 586 694 L 545 697 L 545 845" '
             f'fill="none" stroke="{p["motif"]}" stroke-width="4" stroke-linecap="round"/>')
    t.append(f'<circle cx="618" cy="566" r="9" fill="{p["motif"]}"/>')
    t.append(f'<circle cx="545" cy="697" r="8" fill="none" stroke="{p["motif"]}" stroke-width="4"/>')
    t.append(f'<circle cx="545" cy="845" r="9" fill="{p["motif"]}"/>')
    return "".join(t)


def _motif_stairs(p):
    """上行阶梯：逐级点标 + 顶端圆环"""
    t = [f'<line x1="320" y1="894" x2="660" y2="894" stroke="{p["muted"]}" stroke-opacity="0.3" stroke-width="1"/>']
    d = "M 330 878"
    for _ in range(10):
        d += " h 31 v -27"
    t.append(f'<path d="{d}" fill="none" stroke="{p["motif"]}" stroke-width="4" stroke-linecap="round"/>')
    for i in range(11):
        t.append(f'<circle cx="{330 + i * 31}" cy="{878 - i * 27}" r="4.5" fill="{p["motif"]}"/>')
    t.append(f'<circle cx="640" cy="608" r="15" fill="none" stroke="{p["motif"]}" stroke-width="2"/>')
    t.append(f'<circle cx="640" cy="608" r="5.5" fill="{p["motif"]}"/>')
    t.append(f'<circle cx="330" cy="878" r="6" fill="{p["motif"]}"/>')
    return "".join(t)


def _motif_rings(p):
    """同心圆底纹（右上 + 左下）"""
    t = []
    for r in (70, 115, 160, 205):
        t.append(f'<circle cx="{W - 30}" cy="40" r="{r}" fill="none" '
                 f'stroke="{p["motif2"]}" stroke-opacity="0.3" stroke-width="1.3"/>')
    for r in (60, 100, 140):
        t.append(f'<circle cx="20" cy="{H - 250}" r="{r}" fill="none" '
                 f'stroke="{p["motif2"]}" stroke-opacity="0.26" stroke-width="1.3"/>')
    return "".join(t)


def _motif_brush(p):
    """书法飞白笔触：粗→细的琥珀金一笔，左下起笔、向右上挑锋，落笔处一个墨点"""
    t = []
    # 笔触主体（填充路径，左粗右尖）
    t.append(f'<path d="M 132 832 '
             f'C 280 800, 446 742, 606 648 '
             f'C 624 636, 634 626, 642 612 '
             f'L 624 628 '
             f'C 470 718, 322 778, 150 846 Z" '
             f'fill="{p["motif"]}"/>')
    # 落笔墨点
    t.append(f'<circle cx="150" cy="846" r="11" fill="{p["motif"]}"/>')
    # 挑锋末端小点
    t.append(f'<circle cx="642" cy="612" r="5" fill="{p["motif"]}"/>')
    return "".join(t)


def _motif_constellation(p):
    """金线星座：若干星点（小圆）用细线连成松散星图，落在中部留白"""
    stars = [(180, 700), (300, 640), (430, 690), (540, 610), (600, 720), (470, 770)]
    t = []
    for i in range(len(stars) - 1):
        x1, y1 = stars[i]
        x2, y2 = stars[i + 1]
        t.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
                 f'stroke="{p["motif"]}" stroke-opacity="0.5" stroke-width="1.2"/>')
    for x, y in stars:
        t.append(f'<circle cx="{x}" cy="{y}" r="9" fill="none" '
                 f'stroke="{p["motif"]}" stroke-opacity="0.35" stroke-width="1"/>')
        t.append(f'<circle cx="{x}" cy="{y}" r="3.2" fill="{p["motif"]}"/>')
    return "".join(t)


MOTIFS = {"curve": _motif_curve, "path": _motif_path, "stairs": _motif_stairs,
          "rings": _motif_rings, "brush": _motif_brush, "constellation": _motif_constellation}


def _cover_editorial(lines, subtitle, kicker, quote, meta, desc, steps, motif, p):
    """「安静编辑感」版式：kicker / 大字标题 / 短线 / 宽字距副标题 / motif / 引言 / 页脚"""
    t = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}">', _bg(p, CURRENT_STYLE[0])]
    fs, ls = _title_font(lines)

    # 标题（居左）
    y0 = 318
    for i, line in enumerate(lines):
        t.append(f'<text x="{X}" y="{y0 + i * (fs + 30)}" font-family="LXGW WenKai" '
                 f'font-size="{fs}" letter-spacing="{ls}" fill="{p["title"]}">{_esc(line)}</text>')
    last_y = y0 + (len(lines) - 1) * (fs + 30)
    bar_y = last_y + 54
    sub_y = bar_y + 56

    # motif（副标题之后空间够才画）
    motif_y_ok = sub_y < 600
    if motif and motif_y_ok:
        t.append(MOTIFS[motif](p))

    # 短金线 + 副标题
    t.append(f'<rect x="{X}" y="{bar_y}" width="88" height="6" fill="{p["accent"]}"/>')
    if subtitle:
        t.append(f'<text x="{X}" y="{sub_y}" font-family="LXGW WenKai" font-size="29" '
                 f'letter-spacing="8" fill="{p["subtitle"]}">{_esc(subtitle)}</text>')

    # 描述段落 + 数字步骤（系列/课程型封面，参考「闭环」版式）
    cursor = sub_y
    if desc:
        d_lines = _wrap_plain(desc, 26, max_lines=4)
        dy = sub_y + 64
        for i, line in enumerate(d_lines):
            t.append(f'<text x="{X}" y="{dy + i * 40}" font-family="LXGW WenKai" '
                     f'font-size="24" letter-spacing="1" fill="{p["muted"]}">{_esc(line)}</text>')
        cursor = dy + len(d_lines) * 40
    if steps and steps > 0:
        cy = cursor + 66 if desc else sub_y + 120
        if cy < 940:
            for i in range(min(steps, 10)):
                cx = X + 17 + i * 54
                t.append(f'<circle cx="{cx}" cy="{cy}" r="17" fill="{p["accent"]}"/>')
                t.append(f'<text x="{cx}" y="{cy + 7}" text-anchor="middle" font-family="LXGW WenKai" '
                         f'font-size="19" fill="#ffffff">{i + 1}</text>')

    # 金边引言块
    if quote:
        q_lines = _wrap_plain(quote, 20, max_lines=2)
        qy = 966
        t.append(f'<rect x="{X}" y="{qy - 26}" width="4" height="{len(q_lines) * 42 + 12}" fill="{p["quotebar"]}"/>')
        for i, line in enumerate(q_lines):
            t.append(f'<text x="{X + 26}" y="{qy + i * 42}" font-family="LXGW WenKai" '
                     f'font-size="27" letter-spacing="2" fill="{p["quote"]}">{_esc(line)}</text>')

    # 发丝线页脚 + meta + 圆环饰件
    t.append(f'<line x1="{X}" y1="1048" x2="{W - X}" y2="1048" '
             f'stroke="{p["hairline"]}" stroke-opacity="0.45" stroke-width="1"/>')
    if meta:
        t.append(f'<text x="{X}" y="1092" font-family="LXGW WenKai" font-size="24" '
                 f'letter-spacing="6" fill="{p["meta"]}">{_esc(meta)}</text>')
    t.append(f'<circle cx="{W - 104}" cy="1084" r="9" fill="none" stroke="{p["accent"]}" stroke-width="2"/>')

    # kicker（左上角）
    if kicker:
        t.append(f'<text x="{X}" y="120" font-family="LXGW WenKai" font-size="26" '
                 f'letter-spacing="6" fill="{p["kicker"]}">{_esc(kicker)}</text>')
    t.append("</svg>")
    return "".join(t)


COVER_STYLES = {name: None for name in PALETTES}  # 兼容旧接口占位
CURRENT_STYLE = ["light"]


def build_cover_svg(title, subtitle, author, style, kicker=None, quote=None,
                    meta=None, desc=None, steps=0, motif=None):
    if style not in PALETTES:
        raise SystemExit(f"未知封面风格: {style}（可选: {'/'.join(PALETTES)}）")
    CURRENT_STYLE[0] = style
    p = PALETTES[style]
    lines = _wrap_title(title)
    motif = motif or DEFAULT_MOTIF[style]
    kicker = kicker or f"{author} · 著"
    svg = _cover_editorial(lines, subtitle, kicker, quote, meta, desc, steps, motif, p)
    ET.fromstring(svg)  # 结构自检，畸形直接报错
    return svg


def cover_block(svg):
    b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f'<div class="cover-page"><img src="data:image/svg+xml;base64,{b64}"></div>'


def _file_uri(path):
    """本地图片转 file:/// URI（html 在 build/ 子目录，相对路径会失效；中文名自动百分号编码）"""
    from pathlib import Path
    return Path(path).resolve().as_uri()


# ---------------------------------------------------------------------------
# 页面 CSS
# 封面满版出血：靠命名页 @page cover { margin: 0 } 把封面页边距清零，
# 再让图片按整页尺寸 210mm×297mm 铺开。正文页仍走默认 @page 的 24mm 26mm。
# ⚠️ 不要再用「负 margin 补偿」方案：Edge 打印存在缩放，负 margin 只能消掉左/上边距，
#    右边距始终残留约 26mm（实测左 3.6mm / 右余 25.8mm），封面不满版。
# ⚠️ 封面 SVG 不能直接用 <img src="data:image/svg+xml">：Edge 打印不把内嵌 SVG
#    当作图片嵌入，PDF 里会整页丢失。必须先把 SVG 光栅化成 PNG/JPG 再内嵌。
# ---------------------------------------------------------------------------

CSS = """
@page { size: A4; margin: 24mm 26mm; }
@page cover { size: A4; margin: 0; }
@page backcover { size: A4; margin: 0; }
/* body 必须 margin:0 —— 浏览器默认 body 外边距是 8px（≈2.12mm），
   不清零会把封面往里推，四边出现米白缝；正文边距也会比 design_spec 多 2mm。
   页面边距完全由 @page 的 24mm 26mm 控制。 */
body { margin: 0; padding: 0; font-family: "LXGW WenKai", "楷体", serif; font-size: 14pt; line-height: 1.95; text-align: justify; color: #2b2b26; }
p { margin: 0.6em 0; orphans: 2; widows: 2; }
img { max-width: 88%; max-height: 130mm; object-fit: contain; border-radius: 10px; display: block; margin: 1rem auto; }
figure img { max-width: 88%; max-height: 130mm; object-fit: contain; border-radius: 10px; display: block; margin: 1rem auto; }
a { color: #1a5fb4; font-weight: bold; text-decoration: underline; }
a::after { content: " ↗"; }
blockquote { margin: 1.2em 0; padding: 0 0 0 1.2em; }
.toc-title { text-align: center; font-size: 20pt; margin: 1.5rem 0; }
.toc-line { margin: 0.35em 0; }
.cover-page { page: cover; page-break-after: always; }
/* width/height 100% + object-fit: cover：按封面页整版尺寸铺开并等比填满，
   四边精确 0mm，无白边。若用固定 210mm/297mm + object-fit: fill，
   Edge 打印缩放取整会在上/左各留约 1.8mm 米白缝（实测）。 */
.cover-page img { width: 100%; height: 100%; max-width: none; max-height: none; object-fit: cover; border-radius: 0; display: block; margin: 0; }
.back-cover-page { page: backcover; page-break-before: always; }
.back-cover-page img { width: 100%; height: 100%; max-width: none; max-height: none; object-fit: cover; border-radius: 0; display: block; margin: 0; }
.chapter-title-page { page-break-before: always; page-break-after: always; text-align: left; padding: 66mm 0 3rem; }
.chapter-kicker { font-size: 12pt; letter-spacing: 0.4em; color: #c08b33; margin: 0 0 1.4rem; }
.chapter-num { font-size: 76pt; font-weight: bold; color: #c08b33; line-height: 1; margin: 0; }
.chapter-heading { font-size: 21pt; color: #1f3d2b; margin: 1.4rem 0 0; letter-spacing: 0.06em; }
.chapter-divider { width: 110px; height: 2px; background: #c08b33; margin: 1.8rem 0 0; }
.toc-tip { margin-top: 2rem; border: 1px dashed #c44; padding: 0.6rem 1rem; color: #c44; text-align: center; font-size: 11pt; }
"""


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--md-file", help="单 markdown 书稿文件路径")
    group.add_argument("--md-dir", help="多章节 md 文件夹路径")
    parser.add_argument("--split-by", default="h1", choices=["h1", "h2"],
                        help="分章方式：h1 按一级标题 `# ` 切分（默认）；"
                             "h2 按二级标题 `## ` 切分（稿件用 `## 第 N 章` 形式时）")
    parser.add_argument("--title", required=True, help="书籍标题（可含 \\n 手动断行）")
    parser.add_argument("--subtitle", default=None, help="副标题（封面标题下方的宽字距小字）")
    parser.add_argument("--author", required=True, help="作者名")
    parser.add_argument("--kicker", default=None, help="封面左上角小字（默认「{作者} · 著」）")
    parser.add_argument("--quote", default=None, help="封面底部引言（最多两行，可含 \\n）")
    parser.add_argument("--meta", default=None, help="页脚 meta 文字（如「三篇 · 中文全译本」）")
    parser.add_argument("--desc", default=None, help="封面描述段落（系列/课程型封面用）")
    parser.add_argument("--steps", type=int, default=0, help="封面数字步骤圆圈个数（0=不画）")
    parser.add_argument("--motif", default=None, choices=sorted(MOTIFS),
                        help="封面线条 motif（默认按风格自动：light=curve / forest=path / navy=stairs）")
    parser.add_argument("--series", default=None, help="章节扉页左上角 kicker 文字（默认用书名，如系列名「第一个 100 块」）")
    parser.add_argument("--cover", default=None, help="用户明确指定的封面图；封面默认自动生成，不自动使用书稿文件夹里的图片")
    parser.add_argument("--cover-style", default="light", choices=sorted(PALETTES),
                        help="自动生成封面配色主题：light 米白暖底 / forest 深墨绿 / navy 藏蓝")
    parser.add_argument("--no-cover", action="store_true", help="不生成任何封面")
    parser.add_argument("--back-cover", default=None, help="用户提供封底图，不传不加封底")
    parser.add_argument("--out-html", required=True, help="输出 html 路径")
    args = parser.parse_args()

    out_dir = os.path.dirname(os.path.abspath(args.out_html))
    os.makedirs(out_dir, exist_ok=True)

    # 读取 md 并切分章节
    if args.md_file:
        with open(args.md_file, "r", encoding="utf-8") as f:
            md_text = f.read()
        chapters = split_by_h1(md_text) if args.split_by == "h1" else split_by_h2(md_text)
    else:
        chapters = split_by_files(args.md_dir)
    if not chapters:
        raise SystemExit("书稿为空或没有解析到任何章节")

    # 章节扉页 + 章节元数据（锚点 + 标题），写出 chapters.json
    series_kicker = (args.series or args.title).replace("\\n", "").strip()
    chapters_meta = []
    parts = []
    for idx, (ch_title, ch_body) in enumerate(chapters, start=1):
        anchor = f"chap_{idx:03d}"
        chapters_meta.append({"anchor": anchor, "title": ch_title})
        body_html = markdown.markdown(ch_body, extensions=["fenced_code", "toc"])
        parts.append(
            '<section class="chapter">\n'
            f'<div class="chapter-title-page" id="{anchor}">\n'
            f'<div class="chapter-kicker">{series_kicker}</div>\n'
            f'<div class="chapter-num">{idx}</div>\n'
            f'<h1 class="chapter-heading">{ch_title}</h1>\n'
            '<div class="chapter-divider"></div>\n'
            f'</div>\n{body_html}\n</section>'
        )
    html_body = "\n".join(parts)
    with open(os.path.join(out_dir, "chapters.json"), "w", encoding="utf-8") as f:
        json.dump(chapters_meta, f, ensure_ascii=False, indent=2)

    # 目录：第二次运行时读取 toc.json 回填真实页码
    toc_data = None
    toc_path = os.path.join(out_dir, "toc.json")
    if os.path.exists(toc_path):
        with open(toc_path, "r", encoding="utf-8") as f:
            toc_data = json.load(f)
    pages = {}
    if toc_data:
        pages = {item["anchor"]: item.get("page", "") for item in toc_data}

    toc_html = '<h2 class="toc-title">目录</h2>'
    for meta_item in chapters_meta:
        page = pages.get(meta_item["anchor"], "")
        t = meta_item["title"]
        a = meta_item["anchor"]
        if page != "":
            toc_html += f'<p class="toc-line"><a href="#{a}">{t} ……… {page}</a></p>'
        else:
            toc_html += f'<p class="toc-line"><a href="#{a}">{t}</a></p>'
    toc_html += '<div class="toc-tip">按住 Ctrl 键，同时点击文中蓝色链接即可跳转阅读</div>'

    # 封面：用户图片 > 自动生成 > 无
    has_cover = False
    cover_html = ""
    if args.cover:
        if os.path.exists(args.cover):
            cover_html = f'<div class="cover-page"><img src="{_file_uri(args.cover)}"></div>'
            has_cover = True
            print(f"[封面] 使用用户图片: {args.cover}")
        else:
            print(f"[警告] 封面文件不存在: {args.cover}，改用自动生成封面")
    if not has_cover and not args.no_cover:
        svg = build_cover_svg(args.title, args.subtitle, args.author, args.cover_style,
                              kicker=args.kicker, quote=args.quote, meta=args.meta,
                              desc=args.desc, steps=args.steps, motif=args.motif)
        cover_html = cover_block(svg)
        has_cover = True
        svg_path = os.path.join(out_dir, "cover.svg")
        with open(svg_path, "w", encoding="utf-8") as f:
            f.write(svg)
        print(f"[封面] 已自动生成（主题 {args.cover_style}），预览文件 {svg_path}")
    if args.no_cover:
        print("[封面] 已按 --no-cover 跳过")

    backcover_html = ""
    if args.back_cover:
        if os.path.exists(args.back_cover):
            backcover_html = f'<div class="back-cover-page"><img src="{_file_uri(args.back_cover)}"></div>'
        else:
            print(f"[警告] 封底文件不存在，已跳过封底页: {args.back_cover}")

    full_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>{args.title}</title>
<style>{CSS}</style>
</head>
<body>
{cover_html}
{toc_html}
{html_body}
{backcover_html}
</body>
</html>
"""
    with open(args.out_html, "w", encoding="utf-8") as f:
        f.write(full_html)
    tip = "传 --has-cover" if has_cover else "不要传 --has-cover"
    print(f"[完成] 已写出 {args.out_html}（章节 {len(chapters_meta)} 个；finalize_book.py {tip}）")


if __name__ == "__main__":
    main()
