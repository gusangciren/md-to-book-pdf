# md-to-book-pdf

[![CI](https://github.com/gusangciren/md-to-book-pdf/actions/workflows/ci.yml/badge.svg)](https://github.com/gusangciren/md-to-book-pdf/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

把 Markdown 书稿一键排版成「出版级」PDF 电子书：自动生成封面、章节扉页、可点击目录、PDF 侧边栏书签、页码页脚，**中文逐字保真、版式固定**。

> 本工具的设计语言来自「像企业家一样写作」站点：安静编辑感（米白底 + 真实封面 + 克制留白）、霞鹜文楷字体、金色强调。任何人用本工具，得到的效果与作者一致。

## 效果预览

**点击封面直接在 GitHub 里翻看完整 PDF，无需下载**（左边是验证用的最小示例，右边是同一条流水线跑出的 55 页真实书稿）：

| 最小示例 | 真实书稿《闭环》 |
|:---:|:---:|
| [![sample 封面](examples/preview-sample.png)](examples/sample.pdf) | [![闭环 封面](examples/preview-闭环.png)](examples/闭环.pdf) |
| 5 页 · 2 章 · 无图 · 491 KB | 55 页 · 7 章 · 20 张配图 · 9.2 MB |

更多对比说明见 [examples/README.md](examples/README.md)。

```bash
git clone https://github.com/gusangciren/md-to-book-pdf.git
cd md-to-book-pdf
pip install -r requirements.txt
python scripts/check_env.py        # 确认环境
python scripts/make_book.py --md-file 你的书稿.md --title "书名" --author "作者" --out 书名.pdf
```

---

## 特性

- **一键生成**：`python scripts/make_book.py` 自动完成「Markdown → HTML → 无头浏览器打印 → PDF 后处理 → 质检」，无需手动拼步骤。
- **自动封面**：纯代码绘制的矢量 SVG 封面（不依赖 AI 出图），8 套配色主题 + 6 种线条 motif，差异显著，不会「看起来像把原封面复制上去」。**封面满版出血铺满整页，四边 0mm 白边**。
- **章节自动识别**：`--split-by h1` 或 `--split-by h2`。书稿用 `## 第 N 章` 也能直接处理——会自动跳过书名行、`## 目录` 与封面图引用，无需手工预处理。
- **可点击目录 + 侧边栏书签**：目录页链接供页内 Ctrl+点击跳转，同时写入 PDF 章节大纲，阅读器侧边栏可直接跳章。
- **固定排版**：正文 12pt、行距 1.95、两端对齐、A4 页边距统一；引用块朴素缩进式（无竖线/底色）；链接蓝 + 跳转提示。
- **跨平台**：自动探测 Windows / macOS / Linux 上的 Edge / Chrome 可执行文件。
- **存量 PDF 修复工具**：目录点不动、想换封面，不必重新排版——用 `add_toc_links.py` / `replace_cover.py` 直接修。

---

## 先自检环境

新用户第一步跑这个，缺什么会直接告诉你怎么装：

```bash
python scripts/check_env.py
```

检查 Python 版本、`pymupdf` / `markdown` 依赖、霞鹜文楷字体、Edge/Chrome 四项，全部就绪时以退出码 0 结束。

---

## 环境依赖

| 依赖 | 说明 | 安装 |
| --- | --- | --- |
| Python | ≥ 3.8 | 系统自带或官网安装 |
| 依赖库 | `pymupdf` + `markdown` | `pip install -r requirements.txt` |
| 字体 | **LXGW WenKai（霞鹜文楷）** | 必须本机安装，否则中文会回退成系统默认字体、效果不一致 |
| 浏览器 | **Edge 或 Chrome**（用于无头打印） | 已安装其一即可；可用 `--browser` 手动指定路径 |

### 安装霞鹜文楷

- **Windows**：下载 `LXGWWenKai-Regular.ttf` 后右键「为所有用户安装」，或放进 `%LOCALAPPDATA%\Microsoft\Windows\Fonts\`。
- **macOS**：双击字体文件 → 字体册「安装字体」，或放进 `~/Library/Fonts/`。
- **Linux**：`sudo cp LXGWWenKai-Regular.ttf /usr/share/fonts/`，再 `fc-cache -fv`。
- 下载地址：<https://github.com/lxgw/LxgwWenKai/releases> （或搜「霞鹜文楷」）。

> 字体是本工具「效果对齐」的关键。作者用的就是霞鹜文楷；对方装了同样的字体，才能拿到一样的版式。

---

## 快速开始

### 1. 安装依赖

```bash
cd md-to-book-pdf
pip install -r requirements.txt
python scripts/check_env.py      # 建议先自检
```

### 2. 单文件书稿 → PDF

```bash
python scripts/make_book.py \
  --md-file 我的书稿.md \
  --title "我的书" \
  --author "作者名" \
  --out 我的书.pdf
```

### 3. 多章节文件夹 → PDF

每篇文章一个 `.md`，按文件名排序，每文件一章：

```bash
python scripts/make_book.py \
  --md-dir 书稿文件夹/ \
  --title "我的书" \
  --author "作者名" \
  --out 我的书.pdf
```

### 4. 书稿用 `## 第 N 章` 分级（推荐中文书稿写法）

```bash
python scripts/make_book.py \
  --md-file 书稿.md \
  --split-by h2 \
  --title "我的书" \
  --author "作者名" \
  --out 我的书.pdf
```

`--split-by h2` 会自动跳过：
- 顶部 `# 书名`、封面图引用、frontmatter；
- `## 目录` 及其列表；
- 只把 `## 第 N 章` 当作正式章节。

---

## 封面参数

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `--title` | 必填 | 书名（可用 `\n` 手动断行） |
| `--author` | 必填 | 作者名 |
| `--subtitle` | 无 | 副标题（封面标题下方宽字距小字） |
| `--kicker` | `{作者} · 著` | 封面左上角小字 |
| `--quote` | 无 | 封面底部引言（最多两行，可含 `\n`） |
| `--meta` | 无 | 页脚 meta，如「三篇 · 中文全译本」 |
| `--desc` | 无 | 系列/课程型封面描述段落 |
| `--steps` | 0 | 系列型封面数字圆圈个数 |
| `--motif` | 见下表 | 线条 motif：curve/path/stairs/rings/brush/constellation |
| `--series` | 书名 | 章节扉页左上角 kicker |
| `--cover-style` | `light` | 配色主题（见下表） |
| `--cover` | 无 | 指定封面图（默认自动生成，不自动用文件夹里的图） |
| `--back-cover` | 无 | 封底图 |
| `--no-cover` | 关 | 不生成封面 |

### 8 套配色主题（`--cover-style`）

| 主题 | 配色 | 默认 motif |
| --- | --- | --- |
| `light`（默认） | 米白暖底 #f7f1e4→#ede3cd，标题深绿，金线 | `curve` J 型增长曲线 |
| `forest` | 深墨绿 #33543f→#1a3125，米白字，金线 | `path` 抉择路径 |
| `navy` | 藏蓝 #26415f→#142741，白字，橙线 | `stairs` 上行阶梯 |
| `ink` | 墨黑 #26211c→#100c09，暖米白字，琥珀金 | `brush` 书法飞白笔触 |
| `wine` | 深酒红 #5a2230→#2c0f17，米白字，金线 | `constellation` 金线星座 |
| `red` | 中国红 #b32430→#6e0b14，暖白字，亮金 | `rings` 同心圆 |
| `red-bright` | 鲜亮红 #d62828→#9a1b1b，暖白字，亮金 | `rings` |
| `red-deep` | 深红 #7a1018→#3d0509，暖白字，亮金 | `rings` |

参考图见 `references/cover-style-*.png`。

> 暗底主题（navy / ink / wine / red 系列）一律由矢量 SVG 生成。
> 若你已有位图封面想换配色，请改 `PALETTES` 后重跑，**不要**对图片做像素换色——
> 反白文字会与重新着色的图形融在一起而彻底不可读。

### 系列 / 课程型封面

```bash
python scripts/make_book.py \
  --md-file 课程.md \
  --title "我的课程" --author "作者名" \
  --cover-style red-bright \
  --desc "一套关于……的方法论" \
  --steps 7 --motif rings \
  --out 课程.pdf
```

---

## 只要封面，不要书

试配色、出封面图（网站书籍入口 / 公众号推头 / 社交卡片）时不用跑整条成书流水线：

```bash
# 单张 PNG（2 倍图 1588×2246）
python scripts/make_cover.py --title "闭环" --author "古思" \
  --subtitle "在你睡觉的时候赚钱" --style red-bright \
  --quote "把赚钱变成一台\n不需要你盯着也会运转的机器。" \
  --meta "六章 · 商业系统" --out 封面.png

# 一次出全部 8 套主题挑色
python scripts/make_cover.py --title "闭环" --author "古思" --all-styles --out-dir previews/

# 只出矢量 SVG，交给设计师改
python scripts/make_cover.py --title "闭环" --author "古思" --style wine --format svg --out 封面.svg
```

封面参数与 `make_book.py` 完全一致，生成逻辑同一份代码——**这里看到的就是成书后的效果**。
输出比例 794×1123 = A4，与成书满版铺开的比例一致，不用再裁。

---

## 校验封面满版

「封面有没有留白边」靠肉眼看会漏：阅读器的页面预览自带背景和缩放，几毫米白边在截图里几乎看不出来。

```bash
python scripts/check_bleed.py 书.pdf          # 容差 0.5mm
python scripts/check_bleed.py 书.pdf --tol 1.0
```

**判据是几何法**：读首页图片 bbox，与页面矩形比对四边留白，报出精确 mm 数，
通过退 0 / 失败退 1。`make_book.py` 成书后会自动跑这一步，留白会让流水线
非零退出，CI 里可直接用返回值卡质量。

输出里还有一行「四边采样」，那是**像素法，仅作参考、不参与判定**。
之所以不拿它当判据：light / forest 等浅色主题封面的渐变顶部本身
（实测 RGB 249,245,235）与页面底色（251,247,238）只差 2–3，像素法在原理上
分不清「浅色封面」和「真留白」，强行判定会对浅色主题误报。

---

## 修已有 PDF（不用重排）

### 换封面

```bash
python scripts/replace_cover.py 原书.pdf 新封面.png 输出.pdf
# 想留边而不是满版出血：--margin 18
```

整页铺满新封面图并保持原比例（不拉伸），其余页完全不动。

### 目录点不动 / 缺书签

先用 `detect_chapters.py` 生成 `toc.json`，再补链接：

```bash
python scripts/detect_chapters.py --raw-pdf 原书.pdf --out-toc toc.json --chapters chapters.json
python scripts/add_toc_links.py 原书.pdf 输出.pdf --toc-json toc.json --toc-page 2 --book-title "书名"
```

- `--toc-page`：目录页在第几页（1-based）
- `--page-offset`：若 `toc.json` 的页码和你手上这份 PDF 差几页，用它整体修正

---

## 作为 WorkBuddy Skill 使用

本仓库自带 `SKILL.md`。把它整个文件夹放进：

- 用户级：`~/.workbuddy/skills/md-to-book-pdf/`
- 项目级：`<项目>/.workbuddy/skills/md-to-book-pdf/`

WorkBuddy 即可在对话中调用本工具排版你的书稿。

---

## 工作原理（简述）

1. `build_book.py`：Markdown → 内嵌封面 SVG 的 HTML。
2. 无头 Edge/Chrome `--print-to-pdf`：HTML → 原始 PDF。
   每次使用独立的临时 `--user-data-dir`，避免与用户正在运行的浏览器抢占配置目录。
3. `detect_chapters.py`：识别章节起始页，产出 `toc.json`。
4. `build_book.py` 二次运行：把真实页码回填进目录。
5. `finalize_book.py`：PyMuPDF 在最底层绘制米白底、写入页脚、生成可点击目录链接，并用 `set_toc()` 写入 PDF 侧边栏书签。
6. `qa_check.py`：质检（章节数、页码、断图等），输出代表页截图。
7. `check_bleed.py`：校验封面是否满版铺满整页（以几何法为唯一判据，像素采样仅作参考输出）。

`make_book.py` 把以上串成一步，并自动探测浏览器。

`make_cover.py` 是旁路：只复用第1 步的封面生成能力单独出图，不进成书流水线。

---

## 常见问题

**Q：中文显示成方块 / 字体不对？**
A：没装霞鹜文楷。装好字体再跑，或先跑 `python scripts/check_env.py` 看诊断。

**Q：提示找不到浏览器？**
A：用 `--browser "C:/路径/msedge.exe"` 手动指定 Edge/Chrome。

**Q：Edge 正开着，会不会冲突？**
A：不会。脚本每次用独立的临时用户配置目录打印。

**Q：想改封面配色但不想重排正文？**
A：用 `make_cover.py` 单独出图挑色最快（1 秒一张，不用跑整条流水线）：
`python scripts/make_cover.py --title "书名" --author "作者" --all-styles --out-dir previews/`
选定后改 `--cover-style` 重跑 `make_book.py`，页码不变。
若整本书重跑太慢，用 `replace_cover.py` 直接换已有 PDF 的封面。

**Q：封面有白边 / 不满版？**
A：跑 `python scripts/check_bleed.py 书.pdf`，它会报出四边留白的精确 mm 数并给出修法。
`make_book.py` 成书后会自动跑这一步。白边在阅读器预览里几乎看不出来，别靠肉眼判断。

**Q：章节被拆错 / 目录被当成章节？**
A：中文书稿用 `--split-by h2`，工具会自动跳过书名行与 `## 目录`。

**Q：`--out 输出/我的书.pdf` 这样带目录的路径可以吗？**
A：可以，输出目录会自动创建（含多层新目录）。不用先 `mkdir`。
反过来，`输入`路径不存在则会直接报错并提示你检查拼写，不会等到流水线跑一半才崩。

**Q：书名里的 `\n` 漏进了章节页 kicker？**
A：已归一化，标题里的 `\n` 不会漏到扉页。

---

## 贡献

欢迎提 Issue 和 PR，尤其这几类：

- **新的封面主题 / motif**：加进 `scripts/build_book.py` 的 `PALETTES` 与 motif 函数，
  记得在 `make_book.py --cover-style` 的choices 里同步。
- **踩坑修复**：`SKILL.md` 末尾的「踩坑清单」是这个项目最有价值的部分，
  如果你在别的系统上发现了新的坑，欢迎补进去。
- **平台适配**：目前只在 Windows 上完整验证过；macOS / Linux 的路径与字体安装若有问题，欢迎 PR。

改完请跑一遍自检与端到端：

```bash
python scripts/check_env.py
python scripts/make_book.py --md-file examples/sample.md --split-by h2 \
  --title "像企业家一样写作" --author "示例作者" --cover-style forest --out examples/sample.pdf
python scripts/check_bleed.py examples/sample.pdf    # 必须通过（退出码 0）
```

推送后GitHub Actions 会自动在 Windows + Ubuntu 上跑这套流程（`.github/workflows/ci.yml`），
另有独立任务验证 `make_cover.py` 出矢量封面。徽章见仓库顶部。

---

## License

MIT —— 随意使用、修改、再分发。详见 `LICENSE`。
