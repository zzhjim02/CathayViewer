# CathayViewer「batch1 低成本功能补齐 + 功能核验」报告

日期：2026-09-22
范围：`D:\我的软件创作库\CathayViewer-DEV\`（**未改动** CathayShelf-DEV、Y: 盘或其他目录；**未删除任何用户文件**；**未重新打包 exe**，未动 `dev_dist`/`dev_build`）

---

## 1. 改了什么文件（字节数）

| 文件 | 改动前 | 改动后 | 说明 |
|---|---|---|---|
| `gui.py` | 39858 | **46805** | 5 项新功能 + 1 处潜伏 bug 修复 |
| `viewer_meta.py` | 34653 | **37018** | 新增版权页逐页定位：`_colophon_score` / `find_colophon_page` |
| `viewer_core.py` | 21840 | 21840（未改） | 仅被自检 `import` |

新增/写入的文件（全在 `CathayViewer-DEV\开发\` 下）：
- `开发\功能自检.py`（12316 字节，真平台自检脚本）
- `开发\功能自检_日志.txt`（每次运行覆盖写）
- `开发\batch1_报告.md`（本报告）
- 诊断用临时脚本 `开发\_probe_epub.py` / `_probe_colo.py` 及各自 `*_out.txt`（保留下次可复用；未删）

---

## 2. 改动的函数清单

### viewer_meta.py（新增）
- **`find_colophon_page(path, front=20, back=15)`** —— 逐页定位版权页，**返回页码（1 起）**；找不到返回 `0`。默认只看「前 20 页 + 后 15 页」，逐页用 `_colophon_score` 计分（强特征行数 → 总分最优）；命中门槛：强特征 ≥1（ISBN/定价/统一书号/印张…）或总分 ≥6。只读打开，绝不改文件。
- **`_colophon_score(text)`** —— 给一页文本计「版权页」分，复用 `_locate_colophon` 的同一套关键词（CIP/ISBN/定价/版次/出版/印张…）。

### gui.py
- **`_ui()`**：顶部工具栏存 `self._top_widgets`；主题行新增「行距」`QSpinBox`(`sp_line`，100–250%，默认 150，步进 10) 与 `◐ PDF 反色` 复选框 `cb_invert`；按钮行新增 `⤒ 版权页`/`⧉ 复制文本`/`⧉ 复制带格式`，并把整排按钮存进 `self._btn_widgets`。
- **`__init__`**：新增 `_reader`（`'pdf'`/`'text'`）、`_top_widgets`、`_btn_widgets`；新增快捷键 `Ctrl+Shift+C → copy_text`。
- **`colophon_here()`**（新）—— `⤒ 版权页`：当前项若是 txt 自动找同书 PDF（`META._sibling_pdfs`），调 `META.find_colophon_page` 拿页码 → `fitz.open` → 复用 `self.pd/self.pgno/self._pdf_show()` 跳页；找不到 → 状态栏「没找到版权页」。
- **`copy_text()`**（新）—— `⧉ 复制文本`：PDF 走文字层 `pd[pgno].get_text()`，无文字层提示「这页没有文字层」；文本视图复制阅读区纯文本。
- **`copy_html()`**（新）—— `⧉ 复制带格式`：`QMimeData.setHtml(self.view.toHtml())` 保留 HTML；PDF 用文字层拼 `<p>` 段落。
- **`_apply_line_height(lh)`**（新）—— 用 `QTextBlockFormat.setLineHeight(lh, 1 /*ProportionalHeight*/)` 对整篇文档应用行距（保留滚动位置）。
- **`_on_invert()`**（新）—— 勾选反色时立即重画当前页。
- **`apply_theme()`** —— 主题色/字号之外，再调 `_apply_line_height()`；状态栏带上行距。
- **`_pdf_show()`** —— 渲染后按 `cb_invert` 做 `QImage.invertPixels(InvertRgb)` 像素反色；用 `insertImage(QImage)` + `addResource(ImageResource, QUrl('2'), pixmap)` 显示；置 `_reader='pdf'`。
- **`toggle_full()`** —— 进入全屏时隐藏 `_top_widgets + _btn_widgets`（先记录原可见性），退出时恢复；状态栏提示「按 F11 退出全屏」。
- **`preview_here()`** —— PDF 分支改为保留 `self.pd` 打开、统一走 `_pdf_show()`（**修复潜伏 bug**：原来这里 `d.close()` 后 `self.pd` 悬空，导致「在阅读区打开」后 PgUp/PgDn 翻页失效）；文本分支置 `_reader='text'`、清 `pd`、应用行距。
- **`on_ver()`** —— 切版本时置 `_reader='text'`、清 `pd`。

实修的一个真 bug：`QTextCursor.insertImage()` **不接受 `QPixmap`**（原 `preview_here` 用的就是这个，会抛 `arguments did not match any overload`）。改为传 `QImage`（自检第 5 项抓出并已修复）。

---

## 3. 5 项功能怎么用（按钮 / 快捷键）

| 功能 | 入口 | 行为 |
|---|---|---|
| ① 版权页跳转 | 详情区按钮 **`⤒ 版权页`** | 打开该书 PDF 并跳到版权页；找不到→状态栏「没找到版权页」 |
| ② 快速复制文本 | 按钮 **`⧉ 复制文本`** ＋快捷键 **`Ctrl+Shift+C`** | 复制阅读区纯文本；PDF 取文字层整页文本，无文字层→「这页没有文字层」 |
| ② 快速复制带格式 | 按钮 **`⧉ 复制带格式`** | 复制为 HTML 富文本（`text/html`），保留格式 |
| ③ 行距控制 | 主题/字号行 **「行距」`QSpinBox`**（100–250%，默认 150%） | 改即生效，作用于 `self.view` 全文 |
| ④ PDF 反色 | 主题行复选框 **`◐ PDF 反色`** | 勾选后 PDF 页像素反色（`QImage.invertPixels`），`_pdf_show()` 尊重该开关 |
| ⑤ 全屏隐藏工具栏 | **`F11`** | 进全屏自动隐藏顶部工具栏 + 详情按钮行（记录原状态），退出恢复；状态栏「按 F11 退出全屏」 |

---

## 4. 功能自检（真平台）结果

运行：`py -3 开发\功能自检.py`（`QT_QPA_PLATFORM=windows`，真 QApplication，临时目录造文件，**每步写日志文件**）
日志：`开发\功能自检_日志.txt`

```
== CathayViewer 功能自检 ==
 1. OK   建库 4 条                         files=4
 2. OK   搜索串接同书多版本                      raw=2 rows=1
 3. OK   版本下拉 >=2                       cb_ver.count=2
 4. OK   复制引用含书名                        '某某著：《甲书》，北京：文物出版社，1981年，第X页。'
 5. OK   PDF 打开+翻页+addResource          opened=True pgno=1 msg='第 2 / 3 页（PgUp / PgDn 翻页，F11 全屏）' addResource_ok=True
 6. OK   切 3 主题无异常                      styles=44/44/44
 7. OK   字号跟随 spinbox                   view.font().pointSize=20
 8. OK   F11 全屏翻转                       after1=True after2=False
 9. OK   Ctrl+T 目录不抛异常                  toc_here 未抛异常
10. OK   Ctrl+B 记位置+重开跳回                pgno=1
11. OK   Ctrl+H 历史含该文件                  history=1
12. OK   Ctrl+E EPUB                    pd_pages=1 msg='已用 PDF 引擎打开（.epub，共 1 页）｜PgUp/PgDn 翻页'
13. OK   ⤒ 版权页跳转                        pgno=2（期望 2）msg='版权页在第 3 / 3 页'
14. OK   ⧉ 复制文本（文字层）                    '图书在版编目（CIP）数据\n甲书／某某著．—北京：文物出版社，1981.3\nISBN 7-5010-...'
15. OK   ⧉ 复制带格式（HTML）                  hasHtml=True text='图书在版编目（CIP）数据...'
16. OK   行距控制生效                         第一块 lineHeight=180.0（期望 180）
17. OK   ◐ PDF 反色                       pixel_flip=True msg='第 3 / 3 页...'
18. OK   全屏隐藏工具栏+恢复                     full=True hidden=True restored=True
SUMMARY ok=18 fail=0
RESULT = OK
```

- 第 1–12 项 = 任务要求的 12 项，**全部 OK**。
- 第 13–18 项 = 本次新增功能核验（版权页跳转 / 复制文本 / 复制带格式 / 行距 / 反色 / 全屏隐藏），**全部 OK**。
- 第 5 项显式复现刚修的 `addResource` 调用（`add_ok=True`），并验 `pdf_goto(1)` 后 `pgno==1`。
- 造数细节：真 3 页 PDF（`fitz` 生成，含大纲 + 第 3 页 CIP 版权页文本）；`甲书.pdf` 与 `甲书_【繁转简】.txt` 同书两版本；真 epub（`fitz.save(.epub)`）。
- 自检把 `C.app_dir()/settings_path()` 临时改写到临时目录，**没有污染** `CathayViewer-DEV\cathayviewer_settings.json`（已核对，内容与走查前一致）。

编译：`py -3 -m py_compile gui.py viewer_meta.py viewer_core.py` → 退出码 0。
`py -3 viewer_meta.py`（既有深度著录自检）→ `result = OK`。

---

## 5. 遗留问题

1. **`find_colophon_page` 只扫「前 20 + 后 15 页」**。版权页落在此范围外的书会返回 0（提示「没找到版权页」）。如需更全，可加「全文兜底扫描」（仅强特征命中才算），代价是大部头 PDF 变慢。
2. **`_fill_versions` 仍用纯文件名判定同书**（`deep=False`，沿用上批改动）。若某书书名只能从文件夹/版权页得到，深度书名与列表书名可能不一致，导致其多版本串接不中；影响面小（现有库多为「文件名即书名」）。
3. **`preview_here` 行为变化**：PDF 分支不再 `d.close()`，`self.pd` 会保持打开直到被下一次打开替换（与 `open_cli_arg`/`epub_here` 一致）。这是修「翻页失效」的必要改动，但会多持有一个 fitz 文档句柄。
4. **行距对 PDF 图片页无视觉效果**（只对角标文本/HTML 有意义）；这是预期行为（PDF 页是整张位图）。
5. **反色用 Qt 内置 `QImage.invertPixels`**，未引入 PIL，无新依赖。
6. `gui.py` 自带的 `selftest()`/`selftest2()` 在本机（PyQt6 + Python 3.14 + offscreen）仍会在 `MainWindow.__init__` 处**预存在地原生崩溃**，与本批改动无关；本批改用真平台（`windows`）自检脚本，已全绿。
7. 按要求**未重新打包 exe**，未动 `dev_dist`/`dev_build`。
