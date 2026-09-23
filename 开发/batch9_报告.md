# CathayViewer 批次9 报告（单窗口+布局记忆 · 导航归位 · 双击防重 · 检索去重）

日期：2026-09-22
范围：`D:\我的软件创作库\CathayViewer-DEV\`
平台：Windows 真平台（`QT_QPA_PLATFORM=windows`）
结果：`开发\功能自检.py` **SUMMARY ok=84 fail=0**（batch1–8 无回归）

---

## 0. 本次需求与处理

| # | 需求 | 处理 | 自检 |
|---|---|---|---|
| 1 | 导航面板应在**阅读器窗口的右侧**，不在文件列表窗口 | 导航 dock 跟随阅读器容器：合并时停靠在主窗右侧（即阅读器右缘）；`_detach_reader` 时 `setParent(reader_win)` + 阅读器右侧停靠，收回时回到主窗 | 84 |
| 2 | **双击文件名后页面容易卡住** | 单击/双击合并到同一入口 + **防重入**（同一路径 0.6s 内重复触发直接忽略）+ 元数据**解析缓存**（同文件不重复深度解析）。双击 = 单击 + 双击两次事件，现在只处理一次 | 80 |
| 3 | PDF 显示清楚的前提下，**别把窗口弄那么大** | 默认窗口 1500×950 → **1200×820**（≤屏 80%）；拆窗阅读器 72%×96% → 62%×88% | 78 |
| 4 | **两窗合并**，更协调、可调、**记住** | 默认单窗口（左列表 ｜ 右阅读器，QSplitter 可拖，阅读器约 3/4，`setStretchFactor(0,1)/(1,3)`）；**记住窗口尺寸+位置、分隔条比例、是否拆窗**（写 `cathayviewer_settings.json`，不打包进发布包）；「🗗 独立窗口」保留 | 78/79 |
| 5 | 单文件/跨文件检索**纳入 PDF 及对应 TXT**，并按规则去重 | 见 §1 | 81–83 |

用户补充口径（已落实）：**不去流水线噪声、不去 6 位编号**；命中数「相同」= **真实总出现次数**；配对**只限同一目录**；「多 PDF 对一 TXT 则命中数相同即隐藏」**不适用于原版与繁简 TXT**。

---

## 1. 检索去重（batch9 核心）

**归一化键**（`viewer_meta.same_name_key`）：去扩展名 → 全角转半角 + 清私用区/零宽 → **只忽略 `_opt`**（关键词组 `opt`，带分隔符边界）→ 去首尾分隔符、小写。
⇒ `A_PD6AIFOCR_opt.pdf` ≡ `A_PD6AIFOCR.txt`；而 `A_PD6AIFOCR.txt` ≠ `A_PD6GJOCR.txt`、`A.txt` ≠ `A_【繁转简】.txt`。

**去重函数**（`viewer_meta.dedup_files(files)`，files = `[{name,path,count,hits}]`）：
- 分组：`(同目录)`；
- 对每个 TXT：找**同目录、同名（忽略 `_opt`）的 PDF**：
  - 无同名 PDF → 保留；
  - 是**繁转简/简转繁变体** → 保留（豁免，规则④）；
  - 有同名 PDF 且**命中数相同** → **隐藏该 TXT**（规则①）；
  - 有同名 PDF 且**命中数不同** → 保留并打 `txt_mark`（规则②）；
- 其余一律保留（不同引擎 TXT 名字不同 ⇒ 自动都显示，规则③）。

**检索范围扩样**（`MainWindow._expand_family`，族键 `viewer_meta.family_key`）：在同目录内按族键（再去掉 OCR 引擎标记与繁简标记）把同一本书的 **PDF/TXT 一起送入扫描**。跨文件全文检索与单文件文内查找都走这套。

**命中数**：`_fts_pdf/_fts_text` 改为返回 **(真实总次数, 前 N 条上下文)**；单文件用 `_scan_pdf/_scan_text` 同构。绝不因条数上限导致 ①② 误判。

**单文件**（Ctrl+F）：`find_run → _find_all` —— 当前文件 + 同书 PDF/TXT 一起找 → `dedup_files` → 展平为命中列表（每条带 `path/name/page/off/ctx/txt_mark`）；跳转时若命中在别的文件，先 `_open_path` 切过去；文本命中按字符偏移选中。导航「查找」页签与状态栏都会标出所属文件与「（TXT）」。

**跨文件**：worker 输出改为 `files:[{path,name,count,hits}]`；`_fts_done` 调 `dedup_files` 后再弹结果（结果标题显示「N 个文件 / M 处」）。

---

## 2. 其它改动

- **默认单窗口**：`main()` 不再无条件 `start_two_window_mode()`，改为 `_restore_layout()`（恢复布局；上次是拆窗才继续拆）。
- **布局记忆**：`_layout_dict/_save_layout/_restore_layout`；`closeEvent` 落盘。`_layout_track` 只有主程序设 → **自检/测试构造的窗口不会污染设置**。
- **防重入**：`open_here` 计算路径后判定 `_last_open_path/_last_open_t`（0.6s）。`_on_item_click` 去掉多余的一次 `on_pick()`。
- **元数据缓存**：`on_pick` 按 `(路径, mtime)` 缓存 `META.parse` 结果，重复点击同一文件不再深度解析（读版权页很重）。
- **无文字层提示**：`_find_all` 在无命中且当前是 PDF、其文字层为空时，恢复「这个 PDF 没有文字层，需要先做 OCR」提示。
- **文本偏移对齐**：`_scan_text` 把 `\r\n/\r` 归一为 `\n`，与 QTextEdit 的换行处理一致，避免选中错位。

---

## 3. 自检（84 项）

```
SUMMARY ok=84 fail=0
RESULT = OK
```
- 既有 1–77 无回归（77 改名「阅读器可拆成独立窗口」）。
- 新增 78–84：默认单窗口（阅读器占大头）· 布局记忆（尺寸/比例/拆窗）· 双击防重入 ·
  去重①②③④+`_opt` · 检索纳入对应 TXT · 单文件同套去重 · 导航面板跟随阅读器。
- `gui.py --selftest2` / `--selftest` / `viewer_core --selftest` / `viewer_meta --selftest` 全 OK。

---

## 4. 遗留 / 说明

1. 去重**只比对 PDF/TXT**，EPUB/MD/JSON 不参与配对（避免误伤）。
2. 单文件「对应 TXT」的纳入靠**同目录族键**（去掉 OCR 引擎标记/繁简标记/`_opt` 后同主干）；若你的引擎标记写法特殊，给一份清单可再收紧。
3. 跨页连选仍无「拖到边缘自动滚屏」。
4. **被去重项默认隐藏**：单文件「查找」页签底部与跨文件结果窗底部各有「▸ 显示被去重的 N 项」小按钮，可展开查看/复制（`_find_hidden` / `dedup_split`；自检 85/86）。
5. 窗口版 exe 无控制台（`sys.stdout is None`），跨文件检索 worker 已改用 `_emit()` 安全输出，避免 `AttributeError` 导致 worker 退出码 1。
6. 排障脚本 `_probe_b9.py` / `_patch_readme*.py` / `_probe*.py` 均 `_*`（`.gitignore` + 打包排除），不进发布包。
