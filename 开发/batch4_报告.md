# CathayViewer 批次4 报告

主题：① 双击 / 带文件启动一律在「阅读区」内部打开（外部程序改为显式按钮）
② 阅读区默认更大（分割比例 + 左侧最大宽度约束）

平台：Windows（真平台 `QT_QPA_PLATFORM=windows`），未重新打包 exe，未动 `dev_dist / dev_build`。

---

## 1. 改动文件 + 字节数

| 文件 | 改前 | 改后 | 说明 |
|---|---|---|---|
| `gui.py` | 76,710 | **82,125** | 新增「阅读区内部打开」通路 + 分割比例/窗口尺寸 |
| `开发\功能自检.py` | 25,989 | **31,349** | 新增 37–43 共 7 项断言 |
| `viewer_meta.py` | 37,018 | 37,018 | 未改（仅参与 py_compile） |
| `viewer_core.py` | 21,840 | 21,840 | 未改（仅参与 py_compile） |

仅改 `CathayViewer-DEV\` 下文件；未触碰 CathayShelf-DEV / Y: 盘 / 其它目录；未删任何用户文件。
真实 `cathayviewer_settings.json` 未被污染（自检把 settings 重定向到临时目录，mtime 保持 20:24）。

编译校验：

```
py -3 -m py_compile gui.py viewer_meta.py viewer_core.py   →  rc=0
py -3 -m py_compile 开发\功能自检.py                          →  rc=0
```

---

## 2. 双击 / 启动行为与新按钮

**核心变化：任何「打开」动作默认都在右侧阅读区内部完成，不再甩给外部程序。**

- 列表项 **双击**：`itemDoubleClicked` 由原来的 `open_external()` 改为新的 `_on_item_dbl()` → `open_here()`。
  - PDF / EPUB / XPS / CBZ / MOBI / FB2 / SVG → `fitz` 渲染，走 `_pdf_show()`（含 ◐ 反色、记忆页跳回）。
  - TXT / MD / JSON / CSV → `_show_text_file()` 文本预览。
  - 其它格式 → 阅读区给出提示「暂不支持在此预览，点『↗ 用外部程序打开』」。
  - 打开时一并执行：刷新著录信息 + 版本下拉（`on_pick()`）、记历史（`_hist_add()`）、记统计（`_stat_open()`）。
- **命令行 / 双击关联带文件启动** `open_cli_arg()`：重写为——先在库里定位并选中该文件（找不到则选同名词的第一行，仍照常打开文件），随后统一走 `_open_path()` **在阅读区内部打开**（PDF/EPUB 渲染、文本预览）。
  - **多文件参数**：打开第一个，其余在状态栏提示「（另有 N 个文件参数已忽略）」。
- **外部程序打开** 保留为**显式按钮**：`b2` 文案由「🖼 用系统默认程序打开」改为 **「↗ 用外部程序打开」**（`open_external()` 仍用 `os.startfile`，只有点它才调外部）。
- `preview_here()`（「📖 在阅读区打开」按钮）同步增强：新增 **EPUB 渲染**分支 + 记历史；不支持格式的提示文案同步改为「↗ 用外部程序打开」。

---

## 3. 阅读区比例（实测）

窗口默认尺寸：**1500×950**，且不超过屏幕可用区的 90%（`_apply_default_size()`）。
分割器：`setChildrenCollapsible(False)`；左 `stretchFactor=0`、右 `stretchFactor=1`；默认 `setSizes([340, 1160])`。
左侧列表：`minimumWidth=220`、`maximumWidth = max(220, min(560, 窗口宽×32%))`（`resizeEvent` 内随窗口自适应，上限 560px）。

实测（真平台 1500 宽窗口）：

```
win=1500  left=340  right=1137  right% = 76%
```

- 阅读区宽（1137）> 左侧（340）✔
- 阅读区 ≥ 窗口 55%（76% ≫ 55%）✔
- `setSizes([0, 9999])` 后左侧被最小宽度兜住：`left_after_zero=220  min=220` ✔
- 状态栏 / 界面无裁切重叠（原有 8 项 UI 断言含全屏切换全部通过）。

---

## 4. 自检 SUMMARY

```
SUMMARY ok=43 fail=0
RESULT = OK
```

- 原有 36 项（1–36）**全部不回归**，全 OK。
- 新增 7 项（37–43）：

| # | 断言 | 实测 |
|---|---|---|
| 37 | 双击 PDF → 阅读区内部打开 | `loaded=True reader=pdf pgno=1 ext_calls=0` |
| 38 | 双击文本 → 阅读区有内容且不调外部 | `len=8 reader=text ext_calls=0` |
| 39 | 命令行带文件启动 → 阅读区 | `loaded=True pd_path=甲书.pdf ext_calls=0` |
| 40 | 多文件参数只开首个 + 状态栏提示 | `reader=text msg='已在阅读区打开：甲书_【繁转简】.txt（另有 1 个文件参数已忽略）'` |
| 41 | 阅读区宽 > 左且 ≥ 窗口 55% | `win=1500 left=340 right=1137 right%=76%` |
| 42 | 分割条最小宽度约束生效 | `left_after_zero=220 min=220` |
| 43 | 外部打开保留为显式按钮 | `btn_has_ext=True ext_calls=1` |

**FAIL 明细：无（fail=0）。**

打桩说明：37/38/39 运行期间把 `os.startfile` 与 `subprocess.Popen` 换成计数器，`ext_calls=0` 证明双击/命令行启动**没有**调用外部程序；43 证明显式按钮仍能触发外部打开（`ext_calls=1`）。

运行命令：`$env:QT_QPA_PLATFORM='windows'; py -3 '开发\功能自检.py'`（rc=0），日志见 `开发\功能自检_日志.txt`。

---

## 5. 报告路径

`D:\我的软件创作库\CathayViewer-DEV\开发\batch4_报告.md`
