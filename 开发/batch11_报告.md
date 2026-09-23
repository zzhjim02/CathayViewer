# CathayViewer 批次11 报告（截图本 · 摘录本 · PDF/TXT 对读 · 检索历史 · 版权页目录优先 · 相关文献四档）

日期：2026-09-23
范围：`D:\我的软件创作库\CathayViewer 学术书库浏览与阅读 0.1.0\开发\`（+ 沙箱副本）
平台：Windows 真平台（`QT_QPA_PLATFORM=windows`）
结果：`开发\功能自检.py` **SUMMARY ok=97 fail=0**（batch1–10 无回归）

---

## 0. 需求 → 处理（对应清单 1/2/3/7/8/9）

| # | 需求 | 处理 | 自检 |
|---|---|---|---|
| 1 | PDF 截图存入「截图本」，附出处，保存时提示页码；位于「文档\Cathay文档记录」 | `viewer_tools.add_snapshot`：整页 / 右键「▣ 框选截图」拖框 → 提示页码 → 存 PNG + `截图本.md`（书名·页码·版本·文件） | 93 |
| 2 | 选中文字一键摘录到「摘录本」，自动附出处 | `viewer_tools.add_excerpt` → `摘录本.md`（书名·卷册·页码·版本·出版社年·文件） | 92 |
| 3 | PDF 与 TXT 对读（同步）；打开 TXT 有同名 PDF 则自动对读 | 新增 `TxtSyncView`（页码索引 SyncIndex）+ `DualRead`（上 PDF 下 TXT，双向同步）；打开 TXT 自动进入（`st['auto_dual']` 默认 True） | 94/95 |
| 7 | 跨文件搜索结果历史自动保存、可调阅 | `_fts_done` 存 `settings['fts_hist']`（按 kw 去重，≤30）；新增「🕘 检索历史」对话框（重开/删除/清空） | 96 |
| 8 | 打开版权页先查 PDF 目录（标签页）有无「版权页/版权」 | `colophon_here` 先 `get_toc()` 找，找不到再读文字层 | 97 |
| 9 | 相关文献推荐：同丛书/同专题/同一本书的其他书/同一作者 | `related_groups` 新增 `series/topic/same_book/same_author`（保留 A/B/C 兼容）；对话框改四档 | 34 |

---

## 1. 新增纯逻辑模块 `viewer_tools.py`（不依赖 PyQt）

- **记录目录**：`documents_dir()` 用 `SHGetKnownFolderPath(FOLDERID_Documents)` 拿系统「文档」（兼容 OneDrive 重定向），下建 `Cathay文档记录\{截图本,摘录本}`；`_DOCS_ROOT` 可覆盖（供自检定向）。
- **出处信息** `source_info()`：书名/卷册/页码/版本/作者/出版社/年/文件；版本自动判定 PDF原本 / 繁转简TXT / 繁体TXT / TXT文本。
- **摘录/截图**：追加写 Markdown（首行带说明头）；截图文件名带页码+时间戳，**同秒重复自动加序号**不覆盖。
- **`SyncIndex`**：解析 TXT 页码标记（`≦N≧` / `第 N 页`，可选装饰线），<3 处按约 500 字/页兜底；提供 `page_range / page_at_position / offset_for_page`（移植自 CathayReader）。
- **`find_colophon_in_toc`**：目录里先找「版权页/版權頁」再找「版权/版權」，按目录顺序取第一个。
- **`classify_related`**：四档分类（prefix 丛书 / 同目录专题 / book_core 同书 / author 同作者）。
- **`fts_hist_add`**：检索历史插入去重（≤30）。
- 自检：`py -3 viewer_tools.py` → 15/15 OK。

## 2. 对读（gui.py · TxtSyncView / DualRead）

- `TxtSyncView(QTextEdit)`：`SyncIndex` 定位，`_syncing` 锁；滚动 → 发 `pageChanged(印刷页码)`。
- `DualRead(QWidget)`：`QSplitter(Vertical)` 上 `PdfView` 下 `TxtSyncView`；`_guard` 防回环；`_on_pdf_page` → 页码框 + `txt.goto_number(i+1)`；`_on_txt_page` → `pdf.goto_page(n-1)`；小工具条含「同步翻页 / 跳页 / 缩放」。
- 主窗：`_enter_dual / _maybe_auto_dual / toggle_dual / _on_dual_page`；`_pdf_view_active()` / `_txt_widget()` 把页码/缩放/查找路由到对读视图。
- **打开 TXT 遇同名 PDF 自动对读**；**版本下拉切换不强制对读**（`_suppress_dual`）。

## 3. 截图 / 摘录

- PdfView 新增 `regionSelected / excerptRequested / snapshotRequested` 信号 + 框选橡皮筋（`PdfPageItem` 支持 `_region` 拖框）。
- 主窗 `snapshot_here / _snapshot_from_pdf / _on_pdf_region / _save_snapshot`；`excerpt_here / _excerpt_from_pdf / _excerpt_from_text / _current_selection`。
- 按钮：**📷 截图 · ✂ 摘录 · ⇄ 对读**；快捷键 `Ctrl+Shift+X / E / D`。

## 4. 检索历史

- `_fts_done` 保存 `{kw, at, scanned, files, total, hidden, kept, kept_hidden, errors}`。
- 「🕘 检索历史」（`Ctrl+Shift+F`）+ 左侧按钮：列最近 30 次，双击重开该次结果。

## 5. 版权页 & 相关文献

- `colophon_here`：目录优先 → 文字层回退；状态栏标注来源（目录 / 文字层）。
- `related_dialog` 四档分组树（同丛书 / 同专题 / 同一本书的其他书 / 同一作者的其他著作）。

## 6. 自检

- `功能自检.py` 新增 step 92–97；原 step 34 由「三档」改「四档」。
- 全部：`viewer_core --selftest` / `viewer_meta` / `viewer_tools` / `gui --selftest` / `gui --selftest2` / `功能自检.py` **全 OK**。

> 写入位置仅限用户「文档」下自己的记录目录；**源书库一字节不改**。
