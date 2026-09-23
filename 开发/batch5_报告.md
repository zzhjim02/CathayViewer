# CathayViewer 批次5 报告

主题：① PDF 连续纵向滚动阅读（顺滑 / 预渲染 / 缓存）｜② 文件关联脚本（`关联.bat` / `取消关联.bat`）
③ 导航面板（目录 / 缩略图 / 查找，打开 PDF/EPUB 默认展开）｜④ 单文件全文检索（Ctrl+F）
补充要求：缩放三档 + Ctrl+滚轮、可输入页码框 N / M、目录自动高亮、O(log n) 查页、同一页只渲染一次。

平台：Windows（真平台 `QT_QPA_PLATFORM=windows`），未重新打包 exe，未动 `dev_dist / dev_build`。

---

## 1. 改动文件 + 字节数

| 文件 | 改前 | 改后 | 说明 |
|---|---:|---:|---|
| `gui.py` | 82,125 | **107,901** | 连续滚动引擎（预渲染 + QPixmap 缓存 + 二分查页）/ 缩放 / 页码框 / 导航面板 / 文内查找 |
| `开发\功能自检.py` | 31,349 | **42,523** | 新增 44–57 共 14 项断言 |
| `关联.bat`（新） | — | **2,544** | 纯 ASCII + CRLF，写 HKCU 关联（只生成不执行） |
| `取消关联.bat`（新） | — | **1,125** | 反向 `reg delete /f` |
| `README.md` | 4,736 | **7,275** | 连续滚动 / 缩放 / 页码框 / 导航 / 文内查找 / 文件关联说明 |
| `viewer_meta.py` | 37,018 | 37,018 | 未改（仅参与 py_compile） |
| `viewer_core.py` | 21,840 | 21,840 | 未改（仅参与 py_compile） |

辅助（诊断脚本，只读 / 不写注册表）：`开发\_mkbat.py`、`开发\_probe_bat.py`、`开发\_probe_bat2.py`、
`开发\_probe_batch5.py`、`开发\_probe_colo2.py`、`开发\_probe_txt.py`。

仅改 `CathayViewer-DEV\` 下文件；未触碰 CathayShelf-DEV / Y: 盘 / 其它目录；未删任何用户文件。
真实 `cathayviewer_settings.json` 未污染（自检重定向 settings 到临时目录，mtime 保持 20:24，size=178）。

编译校验：

```
py -3 -m py_compile gui.py viewer_meta.py viewer_core.py   →  rc=0
py -3 -m py_compile 开发\功能自检.py                          →  rc=0
```

---

## 2. 四条要求怎么实现的

### ① PDF 连续纵向滚动（顺滑 / 预渲染 / 缓存 / O(log n) 查页）
- **连续滚动 + 懒加载**：`_pdf_show()` 把页图作为独立块连续排入 `QTextEdit`（页间留 10px 间距）；
  打开时先排入**当前页 ±2 的预渲染窗口**（最多 5 页，秒开）；滚动接近底部时 `QTimer`（单发）→
  `_cont_more()` **每次续插 2 页**，其余按需补齐，**不一次渲染整本**、不阻塞界面。
- **缓存为 QPixmap，同一页只渲染一次**：`_render_page_pixmap(i)` 命中 `self._page_pixmaps`（QPixmap 字典）
  直接复用；未命中才 `fitz` 渲染，并用 `self._render_count[i]` 计数（缓存复用不计，命中即不再渲染）。
  回滚/翻页不重复渲染。
- **算当前页：y 偏移累计表 + 二分查页（O(log n)）**：`_insert_one_page` 记录每页在文档中的 y 偏移
  `self._page_tops`（`documentLayout().blockBoundingRect` 增量取，不重排）；滚动回调 `_on_view_scroll`
  只做 `bisect_right(_page_tops, v+8)-1`（+ 兜底 `cursorForPosition`），**滚动回调绝不重排/重渲染**。
- **状态栏 + 可输入页码框**：状态栏「第 N / M 页（…已载入 K 页，缩放 X%）」；工具栏有页码框「N / M」，
  输入回车跳页（`page_jump`，越界自动夹到首/末页）。
- **跳页**：保留 PgUp/PgDn（`pdf_goto`），新增 Ctrl+Home/Ctrl+End（`pdf_home`/`pdf_end`）；任一跳页从目标页重建窗口。
- 文档切换 `_pdf_stop()` 清缓存与记账；文本/MD/JSON 打开时隐藏导航面板，不破坏文本阅读。

### ② 缩放 + Ctrl+滚轮
- 工具栏「缩放」下拉：**适应宽度 / 适应页面 / 100% + 自定义**；`_zoom_factor()` 按模式与视口尺寸算系数，
  `_pdf_show()` 以 `fitz.Matrix(zoom, zoom)` 渲染。
- **Ctrl+滚轮**：`eventFilter(self.view, …)` 拦截带 Ctrl 的 Wheel，系数 ×1.1 / ÷1.1（夹 0.25–4.0），下拉切到「自定义」并重建。
- 缩放后 `_pdf_show()` 重建页图与 `_page_tops`，**页码与页数记账不串**（pgno 保留、`len(_page_tops)==_inserted`）。

### ③ 文件关联脚本（只生成，不执行）
新增 `关联.bat` / `取消关联.bat`，**纯 ASCII + CRLF**（`开发\_mkbat.py` 用 `encode('ascii')` 强校验）。
对 `.pdf/.epub/.txt/.md` 写 **HKCU**：`HKCU\Software\Classes\CathayViewer.<ext>`（默认值 = `CathayViewer Reader`，
含 `DefaultIcon` 与 `shell\open\command = "\"<exe>\" \"%1\""`）＋ `HKCU\Software\Classes\.<ext>\OpenWithProgids`
加值名 `CathayViewer.<ext>`（`REG_NONE`）。exe 默认 `%~dp0CathayViewer.exe`（注释示例可改）。
`取消关联.bat` 反向 `reg delete /f`。已用「把 `reg` 回显化」在真 cmd 验证展开正确（16 条 add / 8 条 delete）。
**脚本只生成不执行、不写 HKLM、不装服务**；README 说明 Win10/11 需在「设置 → 应用 → 默认应用」选一次。
程序内双击/带文件启动仍走阅读区（沿用 batch4，未改）。

### ④ 导航面板（目录 / 缩略图 / 查找，默认打开 + 自动高亮）
`QDockWidget('导航') + QTabWidget`：目录（`fitz get_toc()`，双击跳页）、缩略图（按需渲染）、查找（PDF 结果列表）。
**打开 PDF/EPUB 后 `_after_pdf_open()` 自动展开**（可手动关，下次仍展开）。`Ctrl+T` 聚焦目录页签、
`Ctrl+Shift+T` 聚焦缩略图页签；非 PDF 打开时隐藏、不报错。滚动时 `_sync_toc_highlight()` 用**二分**在目录项里
找当前章节并高亮（仅面板可见时做，O(log n)）。

### ⑤ 单文件全文检索（Ctrl+F，常驻查找条）
阅读区上方查找条：输入框 +「上一个 / 下一个」+「第 n / m 处」+ 关闭（`✕`）；`Ctrl+F` 聚焦、`Esc` 关闭。
- **TXT/MD/JSON/CSV**：`QTextDocument.find()` 高亮循环 + `toPlainText().count(kw)` 计数。
- **PDF（有文字层）**：`fitz page.get_text()` 建**页级文本缓存**（归一空白、按文档 id 失效），单文件内搜索，
  结果进「查找」页签（页码 + 上下文 30 字，双击跳页），跳页后在页图用 `search_for(kw)` 矩形画黄色高亮框。
- **PDF 无文字层**：提示「…需要先做 OCR（可以交给 CathayOCR）」。**不搜索引库**。

---

## 3. 自检 SUMMARY + FAIL 明细

```
SUMMARY ok=57 fail=0
RESULT = OK
```

- 原有 43 项（1–43）**全部不回归**，全 OK。
- 新增 14 项（44–57）：

| # | 断言 | 实测 |
|---|---|---|
| 44 | 关联.bat 存在+ASCII+CRLF+含关键串 | `size=2544 ascii=True crlf=True pdf=True exe=True` |
| 45 | 取消关联.bat 存在+ASCII+CRLF+含关键串 | `size=1125 ascii=True crlf=True pdf=True exe=True` |
| 46 | PDF 连续滚动：初始载入若干页 | `reader=pdf inserted=5 total=12` |
| 47 | 滚到中部/底部：页码变化+已插页增加 | `pg 0->3->6 inserted 7->7->9` |
| 48 | PgDn/PgUp/Ctrl+Home/Ctrl+End 可用 | `home=0 pgdn=1 pgup=0 end=11 ctrlhome=0 total=12` |
| 49 | 导航面板默认展开+目录页签+双击跳页 | `visible=True toc_rows=3 tab=0 jump_pgno=5` |
| 50 | TXT 文内查找命中+下一个循环 | `total=50 idx 0->0 sel='正文' label='第 1 / 50 处'` |
| 51 | PDF 文字层查找到已知词+跳页+结果列表 | `total=1 pgno=5 tab=1 hl='第 6 页'` |
| 52 | 无文字层 PDF 给出 OCR 提示 | `msg='…没有文字层，需要先做 OCR…' total=0` |
| 53 | 非 PDF 打开时导航面板隐藏不报错 | `reader=text nav_hidden=True` |
| 54 | Ctrl+F 显示 / Esc 关闭查找条 | `vis=True->False` |
| 55 | 同一页只渲染一次（缓存复用） | `reuse=True counts=[1] cached=5` |
| 56 | 缩放切换后页码与页数不错乱 | `total=12 [(适应宽度,0,7,True),(适应页面,0,7,True),(100%,0,7,True)]` |
| 57 | 页码框输入跳页生效 | `set5->pgno=4 clamp99->pgno=11 total=12` |

**FAIL 明细：无（fail=0）。**

说明：46/47/55/56/57 造 `滚动测试.pdf`（12 页，带 TOC）；51 用已知词「第 6 页」命中第 6 页；
52 造 `无文字层.pdf`（只放图片、无文字层）。测试期间 `os.startfile/subprocess.Popen` 打桩，
证明打开动作不调外部程序。**自检只读取 `关联.bat` 文本校验，绝不执行 `reg`、绝不写真实注册表。**

> 附带修复：`view.clear()` 会在空文档上发出一次假的 `valueChanged`，曾导致续插定时器误排、
> 覆盖版权页状态栏提示（step13）。已在 `_pdf_show` 重建前后断开/重连滚动信号，并让 `_cont_more`
> 仅在真插入了页时才刷新状态。

运行命令：`$env:QT_QPA_PLATFORM='windows'; py -3 '开发\功能自检.py'`（rc=0），日志见 `开发\功能自检_日志.txt`。

---

## 4. 报告路径

`D:\我的软件创作库\CathayViewer-DEV\开发\batch5_报告.md`
