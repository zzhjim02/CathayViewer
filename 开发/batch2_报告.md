# CathayViewer「batch2 功能补齐」报告

日期：2026-09-22
范围：`D:\我的软件创作库\CathayViewer-DEV\`（**未改动** CathayShelf-DEV、Y: 盘或其他目录；**未删除任何用户文件**；**未重新打包 exe**，未动 `dev_dist`/`dev_build`）

---

## 1. 改了哪些文件（字节数）

| 文件 | 改动前 | 改动后 | 说明 |
|---|---|---|---|
| `gui.py` | 46805 | **58707** | 4 项功能 + 1 处列表结构升级（几乎全部改动都在此文件） |
| `viewer_meta.py` | 37018 | 37018（未改） | 复用现成的 `parse(..., deep=False)`，无需新增函数 |
| `viewer_core.py` | 21840 | 21840（未改） | 仅被 `import`；settings 读写沿用 `load_settings/save_settings` |
| `开发\功能自检.py` | 12316 | **17879** | 新增第 19–27 项断言（真平台） |

新增/写入（全在 `CathayViewer-DEV\开发\` 下）：
- `开发\_probe_epub_toc.py` / `_probe_epub_toc_out.txt`（探测 fitz EPUB 大纲行为，留下次复用，未删）
- `开发\batch2_报告.md`（本报告）
- `开发\功能自检_日志.txt`（每次运行覆盖写）

**未新增任何依赖**（继续只用 PyQt6 + PyMuPDF）。

---

## 2. 改动的函数清单（`gui.py`）

### ① 搜索结果 5 列（著录）
- **`_ui()`**：`self.tb = QTableWidget(0, 5)`，表头 `['文件名', '著录', '大小', '修改时间', '所在文件夹']`；列宽：0 文件名 Interactive(240)、1 著录 Stretch、2 大小 ResizeToContents、3 时间 ResizeToContents、4 目录 Interactive(260)；`setWordWrap(False)`。
- **`_meta_brief(name, path)`**（新）—— 用 `META.parse(name, path, deep=False)` 拼「作者 · 出版社 · 年 · SSID」。**坚持 deep=False**：只解析文件名，绝不在列表里读 PDF/版权页。
- **`do_search()`** —— 填表改为 5 列；著录列文本 + tooltip 全文（空则提示「（文件名里没有著录信息）」），大小/目录也带 tooltip。`self.rows` 与表格行的对应关系不变（先按同书串接生成 `self.rows`，再逐行填表）。

### ② 搜索历史 + 保存的搜索
- **`_search_hist_add(kw)`**（新）—— 写 `settings['search_hist']`（去重、新的在前、上限 50）；`do_search()` 里在拿到非空关键词后自动调用（Enter 搜索即记一条）。
- **`_rerun_search(kw)`**（新）—— 设关键词并重跑 `do_search()`。
- **`save_search()`**（新，**Ctrl+D**）—— 当前关键词存入 `settings['saved_searches']`（去重、上限 50），状态栏提示「已保存搜索：…」。
- **`search_history_dialog()`**（新，**Ctrl+K**）—— 一个对话框分两组：`QListWidget` 历史（最近 N 条）+ 已保存；双击任一即重搜；「删除选中」同时从两组（及 settings）删除。

### ③ 阅读统计（打开次数 / 累计时长 / 最常阅读）
- **`_stat_open(path)`**（新）—— 打开文件时：先 `_stat_flush()` 结算上一个，再给本文件 `opens+1`、写 `last='MM-DD HH:MM'`、起 `t0`。
- **`_stat_flush()`**（新）—— 切换文件 / 关窗时把 `now - t0` 累加进 `settings['stats'][path]['secs']`。
- **`closeEvent(ev)`**（新）—— 关窗时结算最后一次时长（异常静默），再 `super().closeEvent`。
- **`_stats_text()`**（新）—— 生成统计文本：总累计时长 + 「最近读的 20 本」+「最常阅读 Top 20（按打开次数 / 时长）」。
- **`read_stats_dialog()`**（新，**Ctrl+Shift+H**）—— 弹出只读「阅读统计」对话框。
- 接线：`preview_here()`（txt / pdf 两支）、`epub_here()`、`open_cli_arg()`、`colophon_here()` 成功后调 `_stat_open(path)`；`on_ver()` 切版本时 `_stat_flush()`。同时新增 `self._pd_path` 记录当前打开文档路径。

### ④ EPUB 目录树
- **`toc_here()`（Ctrl+T）** —— 扩展为 PDF **和 EPUB** 通用：当前选中项若是可渲染电子书（`.pdf/.epub/.xps/.cbz/.mobi/.fb2/.svg`）且不是已打开的那本，则就地 `fitz.open(path)` 并 `get_toc()`；无大纲回退「按页列」。双击/「跳转」复用 `self.pd/self.pgno/self._pdf_show()`（EPUB 也用 fitz 渲染）。同时把结果写进 `self._last_toc`（便于自检）。

### 其它
- `__init__`：新增 `Ctrl+K`/`Ctrl+D`/`Ctrl+Shift+H` 三个 `QShortcut`；新增属性 `_pd_path`/`_stat_path`/`_stat_t0`/`_last_toc`。
- `gui.py` 自带 offscreen `selftest()`：把「列表 4 列」断言改为「5 列」（保持与本批一致）。

---

## 3. 新列 / 新快捷键

| 项 | 内容 |
|---|---|
| 新列 | 列表由 4 列 → **5 列**：`文件名 | 著录 | 大小 | 修改时间 | 所在文件夹`；「著录」= 作者 · 出版社 · 年 · SSID，长文本 tooltip 全文 |
| **Ctrl+K** | 搜索历史 / 已保存的搜索（分两组、双击重搜、可删除） |
| **Ctrl+D** | 把当前关键词存入 `settings['saved_searches']`（状态栏提示） |
| **Ctrl+Shift+H** | 阅读统计（最近 20 本 + 最常阅读 Top 20 + 总累计时长） |
| Ctrl+T | 保持不变，**现在 PDF/EPUB 通用**（EPUB 取 fitz 大纲，无大纲列页码） |

数据只写 `cathayviewer_settings.json`（`search_hist` / `saved_searches` / `stats` 三个新键）；所有异常静默/状态栏提示，绝不改源书库、不写其它文件。

---

## 4. 功能自检（真平台）结果

运行：`py -3 开发\功能自检.py`（`QT_QPA_PLATFORM=windows`，真 QApplication，临时目录造文件，每步写日志）
日志：`开发\功能自检_日志.txt`

```
SUMMARY ok=27 fail=0
RESULT = OK
```

<details><summary>明细（27 项）</summary>

```
 1. OK   建库 4 条                         files=4
 2. OK   搜索串接同书多版本                      raw=2 rows=1
 3. OK   版本下拉 >=2                       cb_ver.count=2
 4. OK   复制引用含书名                        '某某著：《甲书》，北京：文物出版社，1981年，第X页。'
 5. OK   PDF 打开+翻页+addResource          opened=True pgno=1 addResource_ok=True
 6. OK   切 3 主题无异常                      styles=44/44/44
 7. OK   字号跟随 spinbox                   view.font().pointSize=20
 8. OK   F11 全屏翻转                       after1=True after2=False
 9. OK   Ctrl+T 目录不抛异常                  toc_here 未抛异常
10. OK   Ctrl+B 记位置+重开跳回                pgno=1
11. OK   Ctrl+H 历史含该文件                  history=1
12. OK   Ctrl+E EPUB                    pd_pages=1
13. OK   ⤒ 版权页跳转                        pgno=2（期望 2）
14. OK   ⧉ 复制文本（文字层）                    '…ISBN…'
15. OK   ⧉ 复制带格式（HTML）                  hasHtml=True
16. OK   行距控制生效                         第一块 lineHeight=180.0
17. OK   ◐ PDF 反色                       pixel_flip=True
18. OK   全屏隐藏工具栏+恢复                     full=True hidden=True restored=True
19. OK   列表 5 列 + 「著录」列表头               columns=5 head1='著录'
20. OK   著录列非空且有内容                      rows=1 brief=['文物出版社 · 1981年'] tip=['文物出版社 · 1981年']
21. OK   Ctrl+K 历史写入+去重                 hist=['甲书', '丙书']
22. OK   Ctrl+K 历史重跑                    hist=['甲书', '丙书'] ed='甲书' rows=1
23. OK   Ctrl+D 保存搜索                    saved=['甲书'] msg='已保存搜索：甲书（Ctrl+K 查看/删除）'
24. OK   打开两次 stats.opens==2            opens=2 secs=0.652 甲书.pdf
25. OK   stats.secs>0 累加                max_secs=0.652 n=1
26. OK   Ctrl+Shift+H 统计列出 Top          len=194 has_top=True has_total=True
27. OK   Ctrl+T EPUB 目录(大纲/页码)          items=1 pages=1 rows=1
```
</details>

- 第 1–18 项 = batch1 全部旧断言，**无回归**（全 OK）。
- 第 19–27 项 = 本批新增 9 项断言（≥8 项要求），**全 OK**：
  - 19 列表 5 列 + 表头「著录」；20 著录列非空且带全文 tooltip（造数 `丙书_某某编著_文物出版社1981年.epub` → `文物出版社 · 1981年`）；
  - 21 历史写入 + 去重 + 新的在前；22 Ctrl+K 对话框可列历史并重跑；
  - 23 Ctrl+D 保存搜索；24 同一文件打开两次 → `opens==2`；25 `secs>0` 累加；26 统计文本含「总累计阅读时长 / 最常阅读 Top 20」且列出该书；
  - 27 EPUB 用 `fitz.open(path).get_toc()` 取到大纲（`items=1`），退路页码可用（`pages=1`）。

- 造数：真 3 页 PDF（含大纲 + 第 3 页 CIP 版权页）；`甲书.pdf` 与 `甲书_【繁转简】.txt` 同书两版本；真 epub（`fitz` 生成并 `set_toc`，故大纲可读回）。
- **settings 已重定向到临时目录**（`C.app_dir()/settings_path()` 被自检改写）：临时目录跑完即删，**没有污染** `CathayViewer-DEV\cathayviewer_settings.json`（已核对：178 字节、LastWriteTime 20:24，均为自检前状态）。
- 编译：`py -3 -m py_compile gui.py viewer_meta.py viewer_core.py` → 退出码 **0**（`开发\功能自检.py` 同 rc=0）。

---

## 5. 遗留问题

1. **著录列 deep=False 只看文件名**：文件名里没有作者/出版社/年的书，著录列为空（tooltip 提示「（文件名里没有著录信息）」）。这是刻意的——列表里若跑 `parse_deep`（读版权页/PDF）会拖垮搜索。需要完整著录可在右侧详情面板（`on_pick` 走 deep）查看。
2. **阅读统计以「文件路径」为键**：移动盘换盘符后，同一本书会按新路径另记一条（与 `history`/`marks` 现状一致）。换盘符重认可沿用 `viewer_core.volume_key`，本批未做。
3. **`secs` 为墙钟时长**：窗口失焦/挂机时也在计时；不是「实际阅读」时长。若需精确可加焦点/空闲判定，本批未做。
4. **统计「最近 20 本」按 `last` 字符串排序**：跨年时 `MM-DD HH:MM` 的字典序不等于时间序（同一自然年内正确）。如需跨年精确，应改成时间戳。
5. **Ctrl+T 会「跟随当前选中项」**：若列表里选中的是另一本书而阅读区正开着甲书，Ctrl+T 会把 `self.pd` 切到选中那本再列目录（这是为让 EPUB 无需先 Ctrl+E 即可看目录）。只想看「当前正在读的」这本时，保持选中项与阅读区一致即可。
6. **`toc_here` 无大纲时按页列**：EPUB 无大纲时会列出全部页码（大部头 EPUB 会很长）；未做「按 spine 章节列」的精细回退。
7. `gui.py` 自带的 offscreen `selftest()/selftest2()` 在本机（PyQt6 + Python 3.14 + offscreen）仍会在 `MainWindow.__init__` 处**预存在地原生崩溃**（与 batch1 同，与本批改动无关）；本批沿用真平台（`windows`）自检脚本，已全绿。
8. 按要求**未重新打包 exe**，未动 `dist`/`dev_build`/`dev_dist`。
