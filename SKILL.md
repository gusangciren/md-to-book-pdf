---
name: md-to-book-pdf
description: 把 Markdown 书稿批量排版生成精装 PDF 书籍（霞鹜文楷、米白底、可点击目录 + PDF 侧边栏书签、章节扉页、QA 截图自检）。触发词：整理成PDF文件。封面一律由脚本自动生成（「安静编辑感」版式：8 套配色主题 + 线条 motif + 金边引言，换参数即可重新生成），不要自动使用书稿文件夹里的图片，仅当用户明确指定某张图时才通过 --cover 使用。已开源，附 check_env.py 环境自检与 replace_cover.py / add_toc_links.py 两个存量 PDF 修复工具。
---

# md-to-book-pdf ｜ Markdown 批量生成精装 PDF 书籍

触发词：整理成PDF文件

> 封面策略：**封面一律由脚本自动生成**（「安静编辑感」版式：左上 kicker → 霞鹜文楷大字标题居左 → 金色短线 → 宽字距副标题 → 极简线条 motif → 金边引言块 → 发丝线页脚）。⚠️ **不要自动使用书稿文件夹/素材里的图片当封面**——哪怕文件夹里有现成封面图也不用；只有用户明确说「用这张图做封面」时才传 `--cover`。⚠️ **自动生成的封面在视觉风格上必须与书稿文件夹内已有的封面图保持明显差异**，不得直接复刻其版式、配色或插图；当默认 `light` 主题与已有封面过于接近时，应主动切换 `forest`/`navy`/`ink`/`wine` 等差异明显的主题。可交付其他 AI 直接使用。

## 前置输入

用户必须提供：
1. 书稿：单份 md 文件 或 存放多个分章节 md 的文件夹
2. 书稿配套图片素材
3. 元数据：书名、作者

封面参数（可选）：
- **默认自动生成封面**（不传任何封面参数即可），按下面「封面参数速查」组织参数
- 用户明确指定图片时才传 `--cover cover.png`（⚠️ 不要自作主张用书稿文件夹里的图片，哪怕它是现成封面）
- `--no-cover`：明确不要封面
- 封底 `--back-cover back.png`：可选，不传不加

## 封面参数速查（自动生成时必读）

| 参数 | 作用 | 示例 |
| --- | --- | --- |
| `--cover-style` | 配色主题（8 套）：`light` 米白暖底·深绿大字·金点缀 / `forest` 深墨绿·奶油大字·金点缀 / `navy` 藏蓝·白大字·橙点缀 / `ink` 墨黑底·暖米白字·琥珀金笔触 / `wine` 深酒红底·米白字·金线星座 / `red` 中国红·暖白字·亮金 / `red-bright` 鲜亮红 / `red-deep` 深红 | `--cover-style ink` |
| `--title` | 书名，可含 `\n` 手动断行（参考图断法：`保罗·格雷厄姆\n文集`、`选择\n改变命运`） | `--title "选择\n改变命运"` |
| `--subtitle` | 标题下宽字距小字 | `--subtitle "靠学识赢得未来"` |
| `--kicker` | 左上角小字（默认「{作者} · 著」） | `--kicker "Y Combinator · 斯坦福 CS183B"` |
| `--quote` | 底部金边引言，最多两行（可含 `\n`，超长自动断） | `--quote "在重大选择面前做出最优选择，\n在微小选择面前养成好习惯。"` |
| `--meta` | 页脚 meta 文字 | `--meta "十八章 · 中文全译本"` |
| `--desc` / `--steps` | 系列/课程型封面：描述段落 + 数字步骤圆圈（配套 `--motif rings`） | `--desc "……" --steps 7 --motif rings` |
| `--motif` | 线条图案：`curve` J 型增长曲线 / `path` 抉择路径 / `stairs` 上行阶梯 / `rings` 同心圆底纹 / `brush` 书法飞白 / `constellation` 金线星座（默认按主题自动：light=curve, forest=path, navy=stairs, ink=brush, wine=constellation, red*=rings） | `--motif stairs` |
| `--series` | 章节扉页左上角 kicker 小字（默认用书名；系列书可传系列名，如「第一个 100 块」） | `--series "第一个 100 块"` |

> ⚠️ **暗底主题（navy / ink / wine / red 系列）必须走矢量 SVG 重新生成，禁止对已有位图做像素换色。**
> 像素换色（按颜色距离替换背景）会让圆圈编号等反白文字与重新着色的图形融在一起，文字彻底不可读。
> 用户拿旧封面图想换配色时，改 `PALETTES` 里的色值后重跑 `build_book.py`，不要走图像处理。

**章节扉页**：每章独占一页（前后强制分页），左对齐编辑风——小字 kicker（书名/系列名）→ 金色大数字 → 深墨绿章节标题 → 短金线；内容块从页面约 1/3 处开始（不要太靠顶）。**引用块**：朴素缩进式（仅左缩进 1.2em），**不要加竖线/底色/边框**（封面上的引言块除外，封面引言保留金竖线）。

各主题的成品效果见 `references/cover-style-*.png` 参考图（light-jcurve / forest-path / navy-stairs / ink-brush / wine-constellation / light-series）。

## 快速开始（make_book.py 一键成书，推荐）

把整套流程（构建 → Edge 打印 → 探测真实页码 → 回填目录 → 再打印 → 后处理+书签 → QA 自检）串成一条命令。浏览器（Edge / Chrome）跨平台自动探测，依赖全部走 pip，不写死任何环境路径。

```bash
# 0) 先自检环境（缺字体/浏览器会直接告诉你怎么装）
python scripts/check_env.py

# 1) 准备隔离环境（一次）
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt        # Windows
#   macOS / Linux: .venv/bin/pip install -r requirements.txt

# 2) 一键成书（章节用一级标题 `# `）
.venv/Scripts/python scripts/make_book.py \
  --md-file 书稿.md \
  --title "书名" --author "作者" \
  --subtitle "副标题" --cover-style navy \
  --out 输出.pdf

# 稿件章节是二级标题 `## 第 N 章` 形式时，加 --split-by h2
.venv/Scripts/python scripts/make_book.py --md-file 书稿.md --split-by h2 ...
```

`scripts/make_book.py` 已自动完成下面「完整执行流程」的步骤 2–7；如需逐环节微调（如只改封面参数），仍可手动按步骤 2–7 跑单脚本。

> 本 skill 已开源，任何人可自由使用、修改、再分发（见 `LICENSE` / `README.md`）。

支持图片语法：标准 markdown `![](xxx.png)`、Obsidian `![[xxx.png]]`。
> Obsidian 语法执行前先规范化成 `![](路径)`，并确认路径相对**输出 html 所在目录**可解析（不确定就用绝对路径）。

## 修已有 PDF（不必重排）

用户已经有成品 PDF，只想改封面或补目录链接时，**不要重跑整套流程**：

```bash
# 换封面：整页铺满新图并保持原比例（不拉伸），其余页不动
python scripts/replace_cover.py 原书.pdf 新封面.png 输出.pdf        # 满版出血
python scripts/replace_cover.py 原书.pdf 新封面.png 输出.pdf --margin 18   # 留边

# 目录点不动 / 缺侧边栏书签
python scripts/add_toc_links.py 原书.pdf 输出.pdf \
  --toc-json build/toc.json --toc-page 2 --book-title "书名"
# 若 toc.json 页码与手上这份 PDF 差几页，用 --page-offset 整体修正
```

`add_toc_links.py` 接受 `detect_chapters.py` 产出的 toc.json（列表格式），也接受简单映射 `{"3": 5, "后记": 49}`。

## 只做封面（不成书）

迭代封面配色时**不要跑整条成书流水线**（build → print → detect → 回填 → 再 print，一轮 1–2 分钟）。
用 `make_cover.py`，1 秒出图，改参数立刻看到效果；网站书籍入口、公众号推头、社交卡片等只要封面图的场景也用它。

```bash
# 单张 PNG（2 倍图1588×2246，网站/推头够用）
python scripts/make_cover.py --title "闭环" --author "古思" \
    --subtitle "在你睡觉的时候赚钱" --style red-bright \
    --quote "把赚钱变成一台\n不需要你盯着也会运转的机器。" \
    --meta "六章 · 商业系统" --out 封面.png

# 一次出全部 8 套主题挑色（最常用）
python scripts/make_cover.py --title "闭环" --author "古思" --all-styles --out-dir previews/

# 只出矢量 SVG，交给设计师改
python scripts/make_cover.py --title "闭环" --author "古思" --style wine --format svg --out 封面.svg
```

参数与 `make_book.py` 的封面参数完全一致（`--subtitle` / `--kicker` / `--quote` / `--meta` / `--desc` / `--steps` / `--motif`），生成逻辑复用 `build_cover_svg()`，所以**这里看到的效果就是成书后的效果**。输出比例 794×1123 = A4，与成书满版铺开的比例一致，无需再裁。

## 校验封面满版（不要靠肉眼）

「封面有没有留白边」用眼睛看会漏——PDF 阅读器的页面预览本身带背景和缩放，几毫米白边在截图里几乎看不出来。跑：

```bash
python scripts/check_bleed.py 书.pdf           # 容差 0.5mm，通过退0 / 失败退 1
python scripts/check_bleed.py 书.pdf --tol 1.0  # 放宽到1mm
```

**几何法是唯一判据**：读首页图片 bbox 与页面矩形比对，报出四边留白精确 mm 数。

输出里的「四边采样」是像素法，**仅作参考、不参与判定**——light / forest 等浅色主题封面的渐变顶部本身（实测 RGB 249,245,235）与页面底色（251,247,238）只差 2–3，像素法在原理上分不清「浅色封面」与「真留白」，强行判定会对浅色主题误报。

`make_book.py` 已在成书后自动跑这一步（步骤 8），留白会让整条流水线非零退出——CI 里可直接用返回值卡质量。

## 依赖环境

- Python（3.8+）+ `pymupdf`、`markdown` 两个库。**安装到隔离环境/虚拟环境，不要全局 pip install**：
  ```bash
  python -m venv .venv && .venv/Scripts/pip install pymupdf markdown   # Windows
  ```
- Edge 浏览器（完整路径通常为 `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`，PATH 里没有就用全路径）
- 本机已安装「霞鹜文楷 LXGW WenKai」字体（封面和正文都用它）
- 跑 `python scripts/check_env.py` 可一次性确认以上各项，缺什么会给可执行指引

## 完整执行流程（顺序不可乱，步骤不可跳过）

1. 素材校验
   - 模式 A 单文件：`--md-file 书稿.md`，脚本通过一级标题 `# ` 自动切分章节（无标题则整册作为「前言」一章）
   - 模式 B 多章节：`--md-dir ./src`，按文件名排序，每个 md 文件为一章（取文件内首个 `# ` 当章节标题，没有则用文件名）
   - 封面按上面「前置输入」的优先级处理

2. build_book.py 输出中间 html（第一次运行，目录暂无页码）

   ```bash
   python scripts/build_book.py ^
     --md-file "书稿.md" ^
     --title "书籍标题" ^
     --subtitle "副标题" ^
     --author "作者名" ^
     --quote "封面引言" ^
     --meta "N 讲 · 中文全译本" ^
     --cover-style light ^
     --out-html "./build/book.html"
   ```

   同时会在输出目录写出 `chapters.json`（章节锚点+标题）和 `cover.svg`（自动封面预览文件）。

3. Edge headless 打印 html 得到 raw.pdf（**必须带 --no-pdf-header-footer**，否则 Edge 会加 URL/日期页眉页脚；**必须带独立 `--user-data-dir`**，否则用户正开着 Edge 时会抢占配置目录导致静默失败）

   ```bash
   msedge --headless=new --disable-gpu --no-pdf-header-footer \
     --user-data-dir="$TEMP/edge_$(date +%s)" \
     --print-to-pdf=./build/raw.pdf ./build/book.html
   ```

4. 【强制】探测章节真实页码，生成 toc.json

   > ⚠️ 只要改动字号、边距、图片，**必须重新运行，禁止复用旧 toc.json，否则目录页码错乱**

   ```bash
   python scripts/detect_chapters.py ^
     --raw-pdf ./build/raw.pdf ^
     --out-toc ./build/toc.json ^
     --chapters ./build/chapters.json
   ```

5. 再次运行 build_book.py（命令同步骤 2，会自动读取 build/toc.json 回填真实页码），再次 Edge 打印得到 raw_toc.pdf（同样带 --no-pdf-header-footer）

6. finalize_book.py PDF 后处理

   ```bash
   python scripts/finalize_book.py ^
     --input-pdf ./build/raw_toc.pdf ^
     --title "书籍标题" ^
     --has-cover ^
     --toc-json ./build/toc.json ^
     --toc-page 2 ^
     --out-pdf "C:\Users\Administrator\Desktop\【输出】书籍名称.pdf"
   ```

   `--has-cover`：第 1 页是封面时传入（跳过封面页脚）——**自动生成封面和用户图片封面都要传**；`--no-cover` 时不要加。

   `--toc-json` + `--toc-page`：写入 PDF **侧边栏书签大纲**（书名 → 目录 → 各章节），阅读器可直接跳章。
   目录页里的蓝色链接供页内 Ctrl+点击跳转，书签供侧边栏导航，两者并存互为补充。
   页码越界的条目会被自动丢弃，避免生成打不开的书签。

7. 【强制 QA 自检，交付前必跑】qa_check.py

   ```bash
   python scripts/qa_check.py --pdf "输出.pdf" --out-snapshots ./build/qa_snap
   ```

   输出最多 5 张校验截图（第 1/2/4/7/11 页，不足则跳过）。

   QA 人工校验要点：
   1. **封面**：书名/副标题/引言/meta 无误、断行位置美观（禁止单字成行，可用 `\n` 手动调）、配色协调；不满意 → 改封面参数重新生成（只影响第 1 页，页码不变，无需重跑 detect）
   2. 文字不贴页面四边，边距充足
   3. 图片完整等比例缩小，无裁切，带圆角
   4. 可点击链接：蓝色粗体下划线+↗；目录底部存在提示：`按住 Ctrl 键，同时点击文中蓝色链接即可跳转阅读`
   5. 霞鹜文楷字体生效，字号稳定
   6. 目录页码与实际页面一致
   7. **PDF 侧边栏书签存在且跳转页码正确**（用 `doc.get_toc()` 可快速验证）

   > 只要任意一项异常，返回修改参数，完整重跑整套流程，不能直接交付用户。

## 重新生成封面（低成本迭代）

- 封面是独立整页 SVG，**替换封面不影响正文页码**，toc.json 可复用——改任何封面参数重跑 build 即可
- 常用迭代：换主题 `--cover-style`；调断行 `--title "A\nB"`；换引言 `--quote`；换图案 `--motif`；系列型加 `--desc/--steps`
- 预览封面用 Edge 截图（真实渐变/字体/字距）：
  ```bash
  msedge --headless=new --disable-gpu --screenshot="preview.png" --window-size=794,1123 "file:///……/cover.svg"
  ```
  ⚠️ 不要用 PyMuPDF 渲染 cover.svg 做预览——它不支持 SVG 渐变，背景会变纯黑，产生误导

## 踩坑清单（必须阅读）

1. Edge headless 打印自带缩放；CSS 字号不等于 PDF 实际字号，严格遵守 design_spec.md 参数，禁止凭感觉修改字号。
2. Markdown 图片不一定被包裹；CSS 必须同时处理 `img` 和 `figure img`；图片必须 `object-fit: contain`，严禁 cover（会裁切图片）。
3. 修改字号、边距、图片大小一定会改变总页数，必须重跑 detect_chapters.py，不能沿用旧 toc.json（**换封面参数除外**，见上）。
4. CSS 页面背景在打印时会丢失；正文背景由 PyMuPDF 在**内容流最底层**绘制 #FBF7EE（直接 draw_rect 会盖住正文）；**自动封面同理不能用 CSS 背景，必须画成 SVG data URI 内嵌图片**（build_book.py 已实现）。
5. 链接固定样式：蓝色 #1a5fb4、粗体、下划线，后缀 ↗ 图标；目录底部固定 Ctrl 点击提示文字。
6. 自动封面 SVG 内**不能引用外部图片/网络资源**（img 标签里的 SVG 是隔离文档），只能用矢量图形 + 本机系统字体；需要照片级封面时让用户提供图片走 `--cover`。
7. **封面满版出血唯一可靠方案 = 命名页 + 百分比尺寸 + `body{margin:0}`**（四边实测 0.00mm）：
   ```css
   @page cover { size: A4; margin: 0; }
   .cover-page { page: cover; page-break-after: always; }
   .cover-page img { width: 100%; height: 100%; max-width: none; max-height: none;
                     object-fit: cover; border-radius: 0; display: block; margin: 0; }
   body { margin: 0; padding: 0; }   /* ← 少了这行四边会留 ~2mm 米白缝 */
   ```
   三个必须同时满足的点：① `body` 默认外边距 8px（≈2.12mm）必须清零，否则封面被往里推；② 用 `width/height:100%` 而非固定 `210mm/297mm`——Edge 打印缩放取整会给固定尺寸留约 1.8mm 缝；③ `object-fit:cover` 而非 `fill`（防变形）。
   **已废弃的方案（不要再试）**：负 margin 补偿（`margin:-24mm -26mm`）只能消掉左/上，右/下消不掉，实测左 3.6mm / 右余 25.8mm / 上 3.4mm / 下余 38.1mm；`position:absolute; left:-26mm` 会导致图片完全丢失。
   ⚠️ **调试陷阱**：用「只有纯色块的简单测试 SVG」验证这套方案会得到假阴性——Edge 打印不把简单 SVG 当图片嵌入（`page.get_image_info()` 返回 0），看起来像方案失效。必须用 `build_book.py` 生成的**真实复杂 cover.svg**（含渐变 + 文字）测试，或直接跑 `check_bleed.py` 让机器判。
15. 改动封面相关 CSS 后**必须跑 `check_bleed.py` 验证**，不要凭截图判断——白边在阅读器预览里几乎看不出来。改完`make_book.py` 会自动跑这一步。
16. 只改封面配色/文案时用 `make_cover.py` 单独出图迭代，别为试一个配色重跑整条流水线。
17. **输出目录要自动创建，别让用户先 `mkdir`**。`--out "输出/我的书.pdf"` 是很自然的写法，若目录不存在，`pymupdf.save()` 会抛 `FileNotFoundError`，而 `make_book.py` 用 `subprocess.run(check=True)` 调脚本，用户看到的是一整段 `CalledProcessError` traceback，完全不知道只是「目录不存在」。修法：调用前先 `os.makedirs(out_dir, exist_ok=True)` 并在失败时给中文提示；`finalize_book.py` / `replace_cover.py` 独立调用时也要自建。
18. **输入文件不存在也要拦在入口**。同理，`pymupdf.open()` 抛的 `FileNotFoundError` 对新手是噪音，脚本入口统一先 `os.path.isfile()` 判断，打印「找不到文件：xxx」+ 检查拼写的提示，退 2（与「校验不通过」的退 1 区分开）。
19. **拿不到 stdout 就别猜**。Windows runner 默认 PowerShell、非 UTF-8 终端（cp1252/cp936）会让 `print` 中文直接 `UnicodeEncodeError`；容器里 Chromium 缺沙箱会 `SIGABRT` + `Broken pipe`。症状是「CI 红了但日志看不懂」。正确做法是**第一时间让 CI 把输出写进产物**（`2>&1 | tee build/x.log` + `if: always()` 上传），而不是猜原因——本次就是这样猜错三轮才对上。
20. **`--split-by h2` 会吞掉正文图片（真 bug，已修）**。`split_by_h2()` 原本有一句 `if stripped.startswith("!") and ")" in stripped: continue`，本意是跳过封面图引用，但封面图引用在首个 `## ` 之前，本就会被「`title is None` 阶段」统一丢弃；这句判断是多余的，且会**误删正文里所有以 `!` 开头的图片行**（书稿用 `## 第 N 章` 分章时，全部走这个分支）。表现为：PDF 里正文图 0 张、目录/封面正常。修法：删掉那句 `startswith("!")` 判断。验证：改完用书稿（20 图）跑，`get_images()` 应从 0 变 21（封面光栅化 1 + 正文 20）。CI 用无图 `sample.md` 测不出这个 bug，带图书稿才暴露。
8. 图片相对路径按**输出 html 所在目录**解析（如 `./build/book.html` 引用 `./build/` 下的图）；书稿里的相对路径对不上时改用绝对路径或把图片拷进 build 目录。
9. 章节极多导致目录跨页时，回填页码可能使目录多占一页、页码整体偏移——回填后复查目录页数，如有偏移再迭代一轮 detect → build → print。
10. Obsidian `![[xxx.png]]` 语法 markdown 库不认识，执行前先替换成 `![](xxx.png)` 并核对路径。
11. 命令行传入的 `\n` 是字面反斜杠+n，脚本已做归一化（标题/引言里的 `\n` 都按换行处理）。
12. **不要用像素重着色改封面配色**（按颜色距离替换背景区域）。反白文字（圆圈编号、暗底上的标题）会与重新着色的图形融在一起，文字彻底不可读。改配色一律改 `PALETTES` 色值后重跑 `build_book.py`。
13. Edge 打印必须用**独立临时 `--user-data-dir`**：用户大概率正开着 Edge，共用默认配置目录会因文件锁而静默失败或串到已有实例。html 路径含中文/空格时用 `Path().as_uri()` 转 `file:///` URI，不要传裸路径。
14. 生成 PDF 后若源 PDF 正在被阅读器打开，`doc.save()` 会报 `Permission denied` / `Device or resource busy`。对策：先输出到 `build/final.pdf`，再 `cp` 覆盖目标；仍失败就是用户正开着预览，等关闭后替换。
