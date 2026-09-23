# batch14 报告 —— 对读重做 / 摘录本查看器 / 纪年换算增强

日期：2026-09-23
范围：`D:\我的软件创作库\CathayViewer-DEV\`（`0.1.0` 产物由 `make_release.py` 重新组装）
**未改动**源书库 / 其它盘；**未删除**任何用户文件。

---

## 1. 本批要解决的问题（用户逐条）

| # | 用户反馈 | 处理 |
|---|---|---|
| 1 | 对读是「一上一下」，应为 PDF/TXT 两个纵列、中间是 PDF 导航页 | `DualRead` 改为 `QSplitter(Horizontal)`：左 PDF、中导航列、右 TXT |
| 2 | 对读时不能选 TXT 的版本 | 中间新增「TXT 版本」下拉（同书各 TXT：繁简 / 不同 OCR），切换即重载并对齐当前页 |
| 3 | 左边文件列表要能缩得很小 | `tb.setMinimumWidth(90)`（原 260） |
| 4 | 「版本」选项显示不全 | `cb_ver` 最小 160 / 最大 360 |
| 5 | 进对读后 PDF 应留在原页、TXT 跳到该页 | `_enter_dual` 保持当前 PDF 页并把 TXT 同步过去（原固定第 1 页） |
| 6 | 缺摘录资料查看器和编辑器 | 新增 `excerpt_viewer`（`Ctrl+Shift+M`）：摘录本可查看/编辑/新增/删除/排序/保存；另含截图本页签 |
| 7 | 对读后如何单独打开 PDF / TXT | 中间「只看 PDF」「只看 TXT」按钮 → 退出对读、保持当前页 |
| 8 | 纪年转换器要支持民国 1–38 年 | `convert/annotate` 增 `allow_short_republic`；**工具里全支持**（复制/摘录自动注记仍按原规则不换 1–38） |
| 9 | 错误纪年（如康熙63年）要换算并提示该年各种纪年 | 新增 `ERA_END` 越界判定：康熙63年 → 1724 年，并提示「康熙共 61 年，无第 63 年；该年实为雍正二年」 |

另：反查公元年时**每个年号都注明是第几年**（1898 → 光绪二十四年、明治三十一年、光武二年）。

---

## 2. 改了哪些文件

| 文件 | 说明 |
|---|---|
| `gui.py` | `DualRead` 重写（左右并列 + 中间导航 + TXT 版本 + 只看 PDF/TXT + 信号 `txtChanged`/`exitRequested`）；`_enter_dual/_dual_txt_variants/_connect_dual/_on_dual_txt_changed/_dual_single`；`cb_ver`/`tb` 宽度；`excerpt_viewer` + 按钮 + `Ctrl+Shift+M`；`chrono_dialog` 用 `allow_short_republic=True` 且反查注明年数 |
| `viewer_tools.py` | 新增 `parse_excerpts/build_excerpts/read_excerpts/write_excerpts/list_snapshots`（摘录本读写 + 截图本清单） |
| `viewer_chrono.py` | 新增 `ERA_END`、`_cn_num/era_year_cn/eras_in_year/format_eras`、越界提示 `_overflow_note`；`allow_short_republic` 贯通 `convert/annotate/annotate_append` |
| `开发\功能自检.py` | 新增 106–114（9 项）；总数 105 → **114**；头部说明同步 |
| `README.md` / `使用说明.txt` / `开发日志.md` | batch14 功能 / 快捷键 `Ctrl+Shift+M` / 按钮 / 更新日志 |

调试脚本（未删，`_` 前缀，打包自动排除）：`_dbg_batch11.py`、`_dbg_chron.py`、`_dbg_xlsx.py`、`_dbg_cbdb.py`、`_dbg_alias2.py`。

---

## 3. 关键实现要点

### 3.1 对读重做（`DualRead`）
- 布局：`QSplitter(Qt.Horizontal)` = `[pdf][nav][txt]`，`setSizes([620,150,540])`，中间列 `setMinimum/MaximumWidth(118/196)`。
- 中间列（PDF 导航页）：标题、`同步翻页` 勾选、页码框 + `跳页`、`⏮◀▶⏭`、缩放下拉、**TXT 版本**下拉、`只看 PDF` / `只看 TXT`。
- 同步：原 `_guard` 双向同步逻辑保留；新增 `_first/_last/_step/_jump`。
- TXT 版本：`set_txt_list([(label,path)…])` + `_switch_txt` → `load_txt`（重载并 `goto_number(当前页)`）→ 发 `txtChanged(path)`，主窗更新 `_text_path`。

### 3.2 进对读保持页（需求 5）
`_enter_dual` 中：若 `self.pd` 存在且 `self._pd_path == pdf_path`（正在读这本 PDF），则 `first = self.pgno + 1`，否则 1；`dual.load(..., first=first)`；`self.pgno = first-1`。

### 3.3 只看 PDF / 只看 TXT（需求 7）
`DualRead.exitRequested(str)` → 主窗 `_dual_single(which)`：
- `pdf`：`pgno = dual.current_page()` → `_pdf_show()`；
- `text`：`_show_text_file(_text_path)`（带 `_suppress_dual` 防自动回对读）。

### 3.4 摘录本查看/编辑器（需求 6）
`viewer_tools` 纯逻辑：
- `parse_excerpts`：按 `### 摘录 · ` 切块，解析 `body`（`> ` 引文）与 `cite`（空 `>` 之后的 `> ` 行）。
- `build_excerpts` / `write_excerpts`：与 `add_excerpt` 同格式，先写 `.tmp` 再 `os.replace` 原子替换。
- `list_snapshots`：截图本图片清单（新在前）。
GUI `excerpt_viewer`：左侧列表（过滤）+ 右侧正文/出处编辑；新增/删除/上移/下移/保存本条/保存全部/重新载入/打开 md；截图本页签可预览与打开。

### 3.5 纪年换算增强（需求 8、9）
- `allow_short_republic=True` → `_skip_era` 不再跳过民国 1–38；工具侧始终传 True，复制/摘录侧保持默认 False。
- `ERA_END`：各年号实际末年（康熙 1722 等）；`_overflow_note(era,n,y)`：`n > end-start+1` 时给出「存疑：X 共 N 年，无第 n 年；该年实为 …」。
- `eras_in_year/format_eras`：按**实际起讫年**判定该年在用的年号，并写成「光绪二十四年」；民国含在内（不做越界）。
- 自检新增：`康熙六十三年 → 1724 且含「雍正」`、`光绪三十五年 → 1909 且含「宣统」`、`format_eras(1898) 含 光绪二十四年/明治三十一年 且不含 同治`。

---

## 4. 自检结果

```
py -3 viewer_core.py --selftest   => result = OK
py -3 viewer_meta.py              => result = OK
py -3 viewer_tools.py             => result = OK
py -3 viewer_chrono.py            => result = OK
py -3 viewer_alias.py             => result = OK
py -3 gui.py --selftest           => result = OK
py -3 gui.py --selftest2          => result = OK
py -3 开发\功能自检.py             => SUMMARY ok=114 fail=0  RESULT = OK
```

新增用例（106–114）：
106 对读左右并列 + 中间 PDF 导航；107 对读可切 TXT 版本；108 只看 PDF / 只看 TXT；
109 进对读保持 PDF 页并同步 TXT；110 左栏可缩很小 + 版本下拉变宽；111 摘录查看/编辑器；
112 越界纪年 → 公元年 + 提示实际纪年；113 反查每个年号注明年数；114 反查含民国纪年。

---

## 5. 遗留 / 说明

1. `DualRead` 的 TXT 版本列表用**同目录扫描**（`META.family_key`）得到，不依赖索引库，改完书库文件无需重建库即可见新 TXT。
2. 「只看 PDF」在主窗用的是同一份已打开的 PDF 文档对象（`self.pd`），不重复解析。
3. 拆窗/导航面板逻辑未改；对读态仍 `_hide_nav()`（导航在中间列）。
4. 本批**未重新打包 exe**（需 `打包EXE.bat` 或 `fab.py` → `make_release.py`）。
