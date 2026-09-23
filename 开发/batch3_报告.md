# CathayViewer「batch3 功能补齐（计划书最后 4 项）」报告

日期：2026-09-22
范围：`D:\我的软件创作库\CathayViewer-DEV\`（**未改动** CathayShelf-DEV / Y: 盘 / 其它目录；**未删除任何用户文件**；**未重新打包 exe**，未动 `dev_dist`/`dev_build`）

本批完成项目计划书最后 4 项：**Markdown 渲染切换（17）**、**JSON 树形浏览（18）**、**相关文件推荐（15）**、**缩略图侧栏（16）**。

---

## 1. 改了哪些文件（字节数）

| 文件 | 改动前 | 改动后 | 说明 |
|---|---|---|---|
| `gui.py` | 58707 | **76710** | 4 项新功能 + 4 个快捷键 + 1 个按钮（改动全在此文件） |
| `viewer_meta.py` | 37018 | 37018（未改） | 复用现成 `book_core` / `parse(..., deep=False)`；**无新增函数** |
| `viewer_core.py` | 21840 | 21840（未改） | 复用现成 `search`；本批未改 |
| `开发\功能自检.py` | 17879 | **25989** | 新增第 28–36 项断言（真平台） |

新增/写入（全在 `CathayViewer-DEV\开发\` 下）：
- `开发\_probe_md.py` / `_probe_md_out.txt`（验证 `setMarkdown` / `QTreeWidget` / `QListWidget` IconMode 行为，留下次复用）
- `开发\batch3_报告.md`（本报告）
- `开发\功能自检_日志.txt`（每次运行覆盖写）

**未新增任何依赖**（继续只用 PyQt6 + PyMuPDF）。

---

## 2. 新快捷键 / 面板清单

| 快捷键 | 功能 | 位置 |
|---|---|---|
| **Ctrl+M** | Markdown「渲染态 ⇄ 源码态」切换（另设按钮 `𝐌D 渲染`） | 阅读区 |
| **Ctrl+J** | JSON 键值树对话框（可展开、按 key 过滤） | 弹出对话框 |
| **Ctrl+R** | 「相关文件」对话框（三档分组，双击打开） | 弹出对话框 |
| **Ctrl+Shift+T** | 右侧缩略图面板开 / 隐藏（PDF/EPUB，懒加载前 40 页） | 右侧 QDockWidget |

新增按钮：`𝐌D 渲染`（加入 `self._btn_widgets`，随全屏一起隐藏/恢复）。

---

## 3. 各功能实现要点（均在 `gui.py`）

### ① Markdown 渲染 / 源码切换（Ctrl+M）
- `md_toggle()`：当前项是 `.md` 时切换；否则状态栏提示「这个文件不是 Markdown」。
- 首次按键：从磁盘读源码（`_read_text_file`），先以**源码态**呈现；随后每次切换：
  - 渲染态：`self.view.document().setMarkdown(self._md_src)`（Qt 原生 Markdown 渲染）；
  - 源码态：`self.view.setPlainText(self._md_src)`（回原始 md 文本，**不是**渲染后的纯文本）。
- 状态栏提示「Markdown 渲染态」/「Markdown 源码态」。
- 新增 `_md_render` / `_md_path` / `_md_src` 状态；`_show_text_file()` 统一处理文本读取并复位 MD 状态；`preview_here()` 的文本分支改为复用它。

### ② JSON 树形浏览（Ctrl+J）
- `json_tree_dialog()`：当前项是 `.json` 时打开；否则提示「这个文件不是 JSON」。
- 大文件（> `JSON_MAX_BYTES` = 20 MB）或解析失败 → 状态栏提示并 `_show_text_file()` 回退纯文本（**不弹窗**）。
- `_json_load()` 读 + 解析；`_json_build_tree()` 用 `QTreeWidget` 展示：dict/list 可展开（显示 `object(n)` / `array(n)`），叶子值显示**类型 + 内容**（字符串截断 200 字，`_json_val_str()`）。
- 顶部过滤输入框：`_json_filter()` 按 key 大小写不敏感匹配，命中项及其祖先保留、其余隐藏。
- 对话框关闭**不影响阅读区**（纯弹出，不写阅读区）。

### ③ 相关文件推荐（Ctrl+R）
- `related_groups()`：`META.parse(deep=False)` 取当前项著录，结合 `C.search(db, 关键词)`（前缀 / 作者，各限 200）+ 当前目录 `os.listdir`，候选去重后 **限制 200 条**（不做全库扫描）。
- 三档：
  - **A 同丛书 / 同专题**：`_series_prefix(书名)`（`book_core` 后剥括注 / 卷册，取开头连续中文）相同，**或**所在文件夹名相同；
  - **B 同作者**：`parse(deep=False)` 作者相同且非空；
  - **C 相邻书架**：同目录其它文件（**最多 50 条**）。
- `related_dialog()`：`QTreeWidget` 三个分组节点，子项存路径（`UserRole`），**双击 → `_open_path()` 打开**（PDF/EPUB 走 fitz，文本走纯文本）。

### ④ 缩略图侧栏（Ctrl+Shift+T）
- `toggle_thumbs()`：PDF/EPUB 已打开时切换；否则提示「缩略图只对已打开的 PDF / EPUB 有效」。
- `_build_thumb_dock()`：右侧 `QDockWidget` + `QListWidget`（`IconMode`，图标 110×150）。
- **懒加载**：`QTimer`（interval 0）逐页追加，`_thumb_add_one()` 每次渲染一页（`fitz`，缩放 0.15），最多 **40 页**——分页进行，不卡界面；全部就绪后停表并提示「缩略图已就绪：N 页」。
- `_thumb_clicked()`：点缩略图 → `self.pgno = i` → **复用 `_pdf_show()`** 跳页。
- 再按一次隐藏（不停留在首次自动可见的坑：先判存在且可见才隐藏，见 §5-2）。

### 其它
- `__init__`：新增 4 个 `QShortcut`（Ctrl+M / Ctrl+J / Ctrl+R / Ctrl+Shift+T）与状态属性（`_md_render`/`_md_path`/`_md_src`/`_thumb_dock`/`_thumb_list`/`_thumb_timer`/`_thumbs_added`/`_last_json`/`_last_related`）。
- 模块级新增：`JSON_MAX_BYTES`（20 MB 阈值）、`_json_val_str()`。
- 只写「自己的」`cathayviewer_settings.json`（本批功能本身不新增键）；不改源书库、不写其它文件。

---

## 4. 功能自检（真平台）结果

运行：`py -3 开发\功能自检.py`（`QT_QPA_PLATFORM=windows`，真 QApplication，临时目录造文件，每步写日志）
日志：`开发\功能自检_日志.txt`

```
SUMMARY ok=36 fail=0
RESULT = OK
```

**FAIL 明细：无（fail=0）。**

<details><summary>明细（36 项）</summary>

```
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
14. OK   ⧉ 复制文本（文字层）                    '…ISBN…'
15. OK   ⧉ 复制带格式（HTML）                  hasHtml=True
16. OK   行距控制生效                         第一块 lineHeight=180.0（期望 180）
17. OK   ◐ PDF 反色                       pixel_flip=True
18. OK   全屏隐藏工具栏+恢复                     full=True hidden=True restored=True
19. OK   列表 5 列 + 「著录」列表头               columns=5 head1='著录'
20. OK   著录列非空且有内容                      rows=1 brief=['文物出版社 · 1981年'] tip=['文物出版社 · 1981年']
21. OK   Ctrl+K 历史写入+去重                 hist=['甲书', '丙书']
22. OK   Ctrl+K 历史重跑                    hist=['甲书', '丙书'] ed='甲书' rows=1
23. OK   Ctrl+D 保存搜索                    saved=['甲书'] msg='已保存搜索：甲书（Ctrl+K 查看/删除）'
24. OK   打开两次 stats.opens==2            opens=2 secs=0.654 甲书.pdf
25. OK   stats.secs>0 累加                max_secs=0.654 n=1
26. OK   Ctrl+Shift+H 统计列出 Top          len=194 has_top=True has_total=True
27. OK   Ctrl+T EPUB 目录(大纲/页码)          items=1 pages=1 rows=1
batch3 追加文件 + 增量刷新：add=7 files=11
28. OK   Ctrl+M MD渲染⇄源码                 render=True/False h1=True bold=True back_same=True
29. OK   非 .md 提示                       msg='这个文件不是 Markdown'
30. OK   Ctrl+J JSON树节点+过滤              nodes=3 vis_all=3 vis_nested=1 nested_kids=True name_hidden=True
31. OK   Ctrl+J 对话框可开                   top=3 path=测试数据.json
32. OK   大 JSON 回退提示                    msg='这个 JSON 超过 20 MB，改用纯文本显示' reader=text
33. OK   坏 JSON 回退提示                    msg='JSON 解析失败（Expecting property name enclosed in double quotes: line 1 column 2 (char 1)），改用纯文本显示'
34. OK   Ctrl+R 相关文件三档                  prefix='近代中国史料丛刊' A=10 B=1 C=10 groups=3
35. OK   相关文件双击打开通路                     txt_ok=True reader=text pdf_ok=True reader=pdf
36. OK   Ctrl+Shift+T 缩略图+跳页            thumbs=3 pgno=1 vis=True->False
```
</details>

- 第 1–18 项 = batch1 全部旧断言；第 19–27 项 = batch2 断言。**全部无回归（OK）**。
- 第 28–36 项 = 本批新增 **9 项**断言（≥8 项要求），**全 OK**：
  - 28 MD 渲染态 `setMarkdown` 生效（`<h1>` + `font-weight`）且能切回源码（文本与原始 md 完全一致）；
  - 29 非 `.md` 文件按 Ctrl+M → 提示「这个文件不是 Markdown」；
  - 30 JSON 树顶层节点 3、`nested` 有 2 个子节点、按 `nested` 过滤后仅该支可见（`name` 被隐藏）；
  - 31 Ctrl+J 对话框可打开（`_last_json.top=3`）；
  - 32 > 20 MB JSON → 状态栏提示 + 阅读区回退纯文本（`reader=text`）；
  - 33 非法 JSON → 解析失败提示 + 回退纯文本；
  - 34 相关文件三档：前缀识别为「近代中国史料丛刊」，A/B/C 三组均非空（A=10, B=1, C=10）、分组节点=3；
  - 35 相关文件双击打开通路（txt → reader=text，pdf → reader=pdf）；
  - 36 缩略图面板建出 3 项、点击第 2 页 `pgno` 0→1、再按一次面板隐藏（vis True→False）。

- 造数：真 3 页 PDF（含大纲 + 第 3 页 CIP 版权页）；`甲书.pdf` 与 `甲书_【繁转简】.txt` 同书两版本；真 epub；batch3 追加 `测试笔记.md` / `测试数据.json` / 坏数据.json / 21 MB 大 JSON / 系列与同作者 pdf（建库后 `refresh` 增量入库，故不影响「建库 4 条」断言）。
- **settings 已重定向到临时目录**（`C.app_dir()/settings_path()` 被自检改写）：临时目录跑完即删，**没有污染** `CathayViewer-DEV\cathayviewer_settings.json`（跑完后仍为 178 字节、LastWriteTime 20:24，未变）。
- 编译：`py -3 -m py_compile gui.py viewer_meta.py viewer_core.py` → 退出码 **0**（`开发\功能自检.py` 同 rc=0）。

---

## 5. 遗留问题 / 说明

1. **MD 渲染用 Qt 原生 `setMarkdown`**：只覆盖 CommonMark + 部分扩展（表格、任务列表因 Qt 版本而异）；不支持的语法按纯文本呈现。渲染态下「回源码」重新读原始 md，不做双向编辑（阅读器只读，符合定位）。
2. **缩略图首次可见性**：`addDockWidget` 后 dock 默认可见，故 `toggle_thumbs()` 先判「已存在且可见」才走隐藏分支——避免首次按下反而隐藏。面板关窗不保存可见状态（每次会话默认关闭）。
3. **缩略图只做前 40 页且单线程分页**：`QTimer` 逐页追加避免卡界面；40 页上限是刻意（大部头全量渲染太重）。点缩略图复用 `_pdf_show()`，与 PgUp/PgDn 同一通路。
4. **相关文件三档可能重叠**：同一文件可同时出现在「同丛书」与「相邻书架」（若同目录）。这是刻意的（两档语义不同，A 是丛书聚合、C 是物理同目录）。「同目录名」判据在同目录退化时会让 A 含较多项，属预期。
5. **相关文件候选上限 200**：`C.search` 各关键词限 200 + 同目录直读，合并后截 200；不做全库扫描，故超大库也不慢。「同作者」用 `deep=False`（只看文件名），文件名为空作者的书不进 B 档。
6. **JSON 树不是编辑器**：只读展示；超大数组（如十几万项 list）仍会构建出对应节点，树会较长——本项目按「学术库 JSON 多为元数据」设计，未做虚拟化。>20 MB 已整体回退纯文本。
7. 按要求**未重新打包 exe**，未动 `dist`/`dev_build`/`dev_dist`。
