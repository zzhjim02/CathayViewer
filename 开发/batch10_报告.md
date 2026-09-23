# CathayViewer 批次10 报告（窗口自适应 · 列表列 · 版本切换 · 查找健壮性）

日期：2026-09-23
范围：`D:\我的软件创作库\CathayViewer-DEV\`
平台：Windows 真平台（`QT_QPA_PLATFORM=windows`）
结果：`开发\功能自检.py` **SUMMARY ok=91 fail=0**（batch1–9 无回归）

---

## 0. 用户报的 6 条 → 处理

| # | 现象 | 根因 | 处理 | 自检 |
|---|---|---|---|---|
| 1 | 窗口小，导航**页签字显示不全** | `QTabWidget` 默认 `expanding=True`：3 个页签平分宽度，窄了就被截 | `tabBar().setExpanding(False)` + `ElideNone` + 缩小字号/内边距 + 滚动按钮 + 悬停提示 | 88 |
| 2 | PDF **缩放僵化，不随窗口** | 只在「切缩放档位」时算一次；窗口变化不重算 | PdfView 新增 `_fit_mode` + 60ms 去抖 `_refit_now()`：`resizeEvent`/`set_document` 自动按视口重算（适应页面/适应宽度） | 89 |
| 3 | 列表里**文件名/上级文件夹显示不全**（有空间也不全） | 上级文件夹列写死 `Interactive 200px`；列表最大宽仅 560px | 上级文件夹列改 `ResizeToContents`、文件名列 `Stretch`；列表最大宽放宽到 `min(880, 窗口 46%)` | 87 |
| 4 | 文件列表**序号有两列** | 既有序号列、又有行号列（vertical header） | `verticalHeader().setVisible(False)` | 87 |
| 5 | 单文件查到 TXT，**部分结果点不开**；**版本切不回 PDF** | ①`on_ver` 只把路径当文字显示，根本不打开文件；②`_open_path` 失败时静默；③`_show_text_file` 把 `_find_total/_find_idx` 清零，跳转后计数/列表就废了 | `on_ver` 改为真正 `_open_path()` 并回填下拉；`_find_jump` 打不开时报状态栏并返回；`_show_text_file` 不再清空查找状态；跳转后延后刷新列表 | 90/91 |
| 6 | 拖动窗口变窄，PDF **整体右移、被导航栏遮住**，左侧空隙变大 | 同 ②：窗口变窄后仍按旧缩放渲染 → 页面宽度 > 视口，横向溢出 | 适应模式随视口重排（2 的改动）⇒ 页面宽度始终 ≤ 视口、无横向滚动条、左右完整可见 | 89 |

---

## 1. PDF 自适应（gui.py · PdfView）

- `PdfView.fit_zoom(mode)`：按**当前视口**算系数（`fitp` 取 `min(vw/pw, vh/ph)`，`fitw` 取 `vw/pw`）。
- `PdfView.set_fit(mode)` / `_refit_now()`：模式为适应时，视口或文档变化后自动 `set_zoom()`；`resizeEvent` 里 60ms 去抖，避免拖动时反复重渲染。
- 重排后发 `fitZoom` 信号（**与 Ctrl+滚轮的 `zoomRequested` 分开**，否则会误步进缩放），主窗口据此刷新缩放 UI/状态栏。
- `_zoom_factor()` 适应档改为委托 `PdfView.fit_zoom()`，`_pdf_show()` 装完文档即 `set_fit(当前档位)`。
- 效果：窗口拉窄/拉宽，页面始终整页（含左右边缘）可见；切「100%/自定义」则是固定倍数、可横向滚动查看。

## 2. 列表与页签

- 列表：`QTableWidget(0,3)` + 隐藏行号列；列模式 `ResizeToContents / Stretch / ResizeToContents`；最大宽 `min(880, 46%)`（阅读器独立时可占满）。
- 导航页签：不拉伸、ElideNone、字号 -1、`padding 2px 7px`、`documentMode`、悬停提示。

## 3. 版本下拉 = 真正换文件

以前 `on_ver` 只把 `路径` 写进文本框。现在：取该版本路径 → `_open_path()`（PDF 走内置引擎、TXT 走文本态）→ 回填下拉索引 + 状态栏提示；文件不在了会有明确提示。

## 4. 查找健壮性

- `_find_jump(i)`：命中在别的文件里 → `_open_path()`；**失败就报「打不开这条结果：…」并返回**（不再默默无反应）；成功则延后 `_populate_find_tab()` 刷新（避免在信号处理里清表）。
- `_show_text_file()`：删掉 `_find_total=0 / _find_idx=-1`，跳到 TXT 后查找结果与「第 i / N 处」仍在。
- `_find_idx` 在 `_find_jump` 内同步。

## 5. 顺带修复（打包版）

- 窗口版 exe（无控制台）`sys.stdout is None` → 跨文件检索 worker 里 `sys.stdout.write` 抛 `AttributeError`、退出码 1、**结果文件都不生成**。统一改 `_emit()` 守卫；`main()` 的 worker 分支加 try/except。
- 实测：打包 exe `--fts-worker` → **退出码 0，out.json 正常**。

## 6. 自检（91 项）

```
SUMMARY ok=91 fail=0
RESULT = OK
```
- 新增 87 列表列（无行号列 + 列自适应）· 88 页签不拉伸 · 89 PDF 适应窗口（真 PDF，窗口 1250→980 后缩放 1.005→0.731、页宽 ≤ 视口宽、横向滚动条=0）· 90 版本下拉逐个打开成功 · 91 查找打不开有提示不崩 + 开 TXT 不清计数。
- `gui.py --selftest2` / `--selftest` / `viewer_core --selftest` / `viewer_meta --selftest` 全 OK。

## 7. 遗留

1. 「适应宽度」目前也随窗口重排；若希望它固定不重排，可再提供开关。
2. 排障脚本 `_probe_b10.py` / `_patch_readme3.py` 等 `_*` 不进发布包。
