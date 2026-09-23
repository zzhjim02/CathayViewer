# CathayViewer 批次7 报告（阅读器重构 + 5 项新功能 + 版权信息）

日期：2026-09-22
范围：`D:\我的软件创作库\CathayViewer-DEV\`
平台：Windows 真平台（`QT_QPA_PLATFORM=windows`）
结果：`开发\功能自检.py` **SUMMARY ok=69 fail=0**

---

## 0. 本次解决的 6 个问题

| # | 需求 | 处理 | 自检 |
|---|---|---|---|
| 1 | 文件选择器与阅读器拆成两个窗口，阅读器尽量占满屏 | 新增「🗗 独立窗口」：把阅读区整体拆到独立窗口并最大化；关窗自动收回 | 64 |
| 2 | PDF 不支持滚轮/上下键滚动，段落感强、卡顿 | **重建 PDF 内核**（`PdfView`：QScrollArea + 分页控件），滚轮**像素级平滑**、`↑`/`↓` 小步、PgUp/PgDn 整页；仅渲染可见页 ±1 并缓存 | 46/47/55/56/60/65 |
| 3 | PDF 无法鼠标选择/复制隐藏文字层 | 每页叠加**词级文字层**，鼠标拖选即高亮并自动复制；右键「复制本页文字/全选本页」 | 66 |
| 4 | 对搜索结果里的 PDF 做跨文件全文检索，放独立进程 | 新增「🔎 全文检索」：把当前结果写 job.json，`QProcess` 另起进程跑 `--fts-worker`，进度回报，完成后弹出结果列表（双击跳页/全部复制） | 67 |
| 5 | 单击（而非双击）PDF 目录即跳转到指定页 | 目录页签 `itemClicked` 也接 `_nav_toc_go` | 49/68 |
| 6 | 文件名 / 版权页 / 上级目录名里的版权信息尽量找全 | `viewer_meta` 新增 `_rights_meta/_rights_scan`：三来源合并 授权/版权/出版发行/ISBN/版次/印次/出版年月，并标注来源；详情面板显示 | 69 |

---

## 1. 阅读器架构：从「QTextEdit 贴图」到「专用 PdfView」

旧实现把每页图片作为独立块插进一个只读 `QTextEdit`。这样：
- 滚轮/方向键是**按文本行**滚动的，图片块一整块一整块跳 → 「段落感太强」；
- 每次续插都要重排整篇文档 → 卡；
- 图片没有文字层 → 不能选、不能复制。

新实现 `PdfView(QScrollArea)`：
- 一个纵排的 `PdfPageItem` 列表（每页固定尺寸 = 页矩形 × 缩放）；
- **懒渲染**：只渲染视口 ±1 页，`QTimer` 去抖；`QPixmap` 按页缓存，同一页只渲染一次（自检 55：`render_counts` 全为 1）；
- **像素级平滑滚动**：`wheelEvent` 优先用 `pixelDelta`（触控板），否则按 `angleDelta` 换算像素滚动；滚动条 `singleStep=40`；
- **键盘**：`↑/↓` 小步滚动、`PgUp/PgDn`/空格 整页、`Home/End` 首末页；
- **文字层**：`page.get_text('words')` 缩放后随页保存；`mousePress/Move/Release` 做词级选择（同一页内），选中即画蓝色高亮并入剪贴板；`Ctrl+C`/右键可复制；`Ctrl+A` 全选本页；
- **查找高亮**：`page.search_for(kw)` 的矩形在 `paintEvent` 里画（不烘焙进位图 → 改高亮不必重渲染位图）；
- `Ctrl+滚轮` 发 `zoomRequested` 信号，由主窗口统一改缩放系数（`set_zoom` 重排页尺寸并保当前页）。

主窗口右栏改为 `QStackedWidget`：0=文本框（TXT/MD/JSON），1=`PdfView`。文本类代码继续用 `self.view`（别名到文本框），PDF 类代码走 `self.pdf_view`。

---

## 2. 阅读器独立窗口

- `_ui` 把右栏整体记为 `self.reader_panel`；
- `_detach_reader()`：`reader_panel` 重新 `setCentralWidget` 到一个新的 `ReaderWindow`（`QMainWindow`，`showMaximized()`），并把「导航」`QDockWidget` 一并搬过去；
- `_attach_reader()`：搬回 `QSplitter`（恢复原分割比例），关掉独立窗口；
- `ReaderWindow.closeEvent` → 自动收回，避免窗口关了阅读区丢失。

---

## 3. 跨文件全文检索（独立进程）

- 主窗口 `fulltext_search()`：取当前结果去重路径 → 写 `job.json` → `QProcess` 启动
  `--fts-worker job`（冻结时用 `sys.executable`，开发时用 `python gui.py --fts-worker`）。
- `fts_run(job)`（独立进程入口）：逐文件——PDF 走 `page.get_text()` 逐页找、文本走 `read_bytes/decode_bytes`；stdout 打 `PROGRESS\t已扫\t总数\t命中`，结果写 `out.json`。
- 主窗口按进度更新状态栏；结束后弹结果列表（文件名｜页｜上下文），双击 `_open_fts_hit` 打开并跳页；「全部复制」。
- **界面不卡**：繁重的取文/搜索全在子进程。

> 注：PDF 逐页 `get_text` + 每页 `search_for` 在独立进程里跑；无文字层的 PDF 无命中（会照常提示需 OCR）。

---

## 4. 版权 / 授权信息（第 6 项）

`viewer_meta.py` 新增：
- `_RIGHTS_PATS` + `_rights_meta(text)`：从一段文本抽
  `authorization`（据X授权 / X授权重印…）、`copyright_holder`（版权所有：X）、
  `copyright_line`（© X）、`rights_holder`（出版发行：X）、`isbn`、`edition`（第N版）、
  `printing`（第N次印刷）、`pub_date`（年份/年月）。
- `_rights_scan(name, path, colophon)`：**文件名 → 上级目录链 → 版权页** 三来源合并，逐字段记录来源（file/folder/colophon）。
- `parse_deep()` 结果新增 `rights` / `rights_src` 与平铺字段；`gui.MainWindow` 详情面板显示「版权/授权：…（来源）」。

实测：`史记_中华书局授权影印本` → 授权=中华书局；版权页文本 → ISBN/版次/印次/出版年月/版权所有 主体；`文件+目录+版权页` 三来源可同时命中。

---

## 5. 自检（69 项，全绿）

```
SUMMARY ok=69 fail=0
RESULT = OK
```
- 既有 1–63 项**无回归**；其中 46/47/55/56/58/60 已改写为新内核断言，49 标签改为「单击跳页」。
- 新增 64–69：独立窗口拆/收 · PDF 平滑滚动（滚轮像素 + ↑↓）· 文字层选择/复制 ·
  跨文件全文检索（独立进程 worker，真跑一次）· 目录单击跳页 · 版权/授权信息三来源。

内置自检：`--selftest` / `--selftest2` / `viewer_core --selftest` / `viewer_meta` 均 `OK`。

---

## 6. 遗留 / 说明

1. 文字层选择目前**限单页内**（跨页选择未做；已够「选一段复制」）。
2. 大文档（数千页）建 `PdfPageItem` 会创建等量轻量控件；已懒渲染，控件本身开销很小，暂不虚拟化。
3. 全文检索对**无文字层** PDF 无结果；建议先用 CathayOCR 生成文字层。
4. 排障临时脚本 `_probe_pdf7.py` 属 `_*.py`（`.gitignore` + 打包排除），不影响发布。
