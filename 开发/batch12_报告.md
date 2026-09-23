# CathayViewer 批次12 报告（注释一键插入 · 历史纪年换算 · 复制自动换算）

日期：2026-09-23
范围：`D:\我的软件创作库\CathayViewer 学术书库浏览与阅读 0.1.0\开发\`（+ 沙箱副本）
平台：Windows 真平台（`QT_QPA_PLATFORM=windows`）
结果：`开发\功能自检.py` **SUMMARY ok=102 fail=0**（batch1–11 无回归）

---

## 0. 需求 → 处理（对应清单 10/11）

| # | 需求 | 处理 | 自检 |
|---|---|---|---|
| 10 | 复制的引文直接生成脚注格式，粘贴到 Word 即成脚注 | `TOOLS.footnote_rtf(body, source)` 生成带 `{\footnote …}` 的 RTF（汉字转 `\uN?`）+ HTML 回退，写入剪贴板多格式；Word 粘贴即成**真脚注** | 100 |
| 11 | 引文中民国/年号/干支纪年自动加【=公元年】，多个都标；干支列 1700–2000 全部年份 | 新增 `viewer_chrono.py`：`annotate / annotate_append / convert`；干支 60 循环 → 列出 1700–2000 全部年份 | 98/99/101/102 |
| 11+ | **复制 PDF/TXT/其它文件文字时**（含「复制本页文字」、拖选后右键复制）也自动加换算 | `TextView`（文本右键/Ctrl+C）+ `PdfView.copy_selection` / 「复制本页文字」 + `copy_text` / `copy_html` 文末自动附【纪年换算】 | 98/99 |
| 11++ | **民国元年–38 年不换算，39 年起自动换算** | `viewer_chrono._skip_era`：民国 n≤38 跳过；民国四十年 = 1951 | 98/99 + chrono 自检 |
| 11+++ | 新增**随时可开的历史纪年换算工具** | 主窗 `chrono_dialog()`（换算 + 反查公元年）；按钮「⌛ 纪年换算」+ `Ctrl+Shift+Y` | 101 |

---

## 1. 新增纯逻辑模块 `viewer_chrono.py`（不依赖 PyQt）

- **年号表 `ERA`**：明清 + 太平天国 + 洪宪 + 伪满（大同/康德）+ 中华民国 + 日本（明治/大正/昭和/平成/令和）+ 大韩帝国（开国/建阳/光武/隆熙），繁简双键。元年 = start，N 年 = start + N − 1。
- **干支**：天干地支 60 循环，锚点 1984=甲子；`ganzhi_index` 校验合法组合；`ganzhi_years(gz,1700,2000)` 列出全部对应年份（如 甲子 = 1744/1804/1864/1924/1984）。
- **汉语数字** `_cn2int`：一二三…十百千 + 元/正（=1）+ 廿/卅 + 阿拉伯数字。
- **`convert(text)`**：识别 ① 年号+N年 ② 年号+干支（如 咸丰庚申=1860）③ 单干支（列 1700–2000 全部年份）；**跳过【…】已标注区（幂等）**、跳过 民国≤38。
- **`annotate(text)`**：在每个纪年后加【XX=公元年】；**`annotate_append(text)`**：复制用——在**文末**追加一栏【纪年换算】（去重保序）。
- **`year_eras(year)`**：反查某公元年对应的年号（粗略，供速查）；`year_to_ganzhi`。
- 参考用户三份资料（明清民国年号表 / 中日朝三国近代纪年表 / 中华甲子年表）；年号起始年与干支循环均为可核验公共事实，内置精简表，**不依赖外部盘**。
- 自检：`py -3 viewer_chrono.py` → 21/21 OK。

## 2. 脚注（gui.py · footnote_here）

- `_current_selection()` 取当前选区（PDF 文字层 / 文本 / 对读），无则用剪贴板文本作为「正文」。
- 出处 = `META.cite(meta, page=当前页)`（缺则文件路径）；出处内也做纪年换算。
- `QApplication.clipboard().setMimeData`：同时放 `text/rtf`（含真脚注）+ `text/html` + 纯文本；**到 Word 里 Ctrl+V 即成脚注**。
- 按钮「❞ 脚注」+ `Ctrl+Shift+I`。

## 3. 复制自动换算（gui.py）

- 新增 `class TextView(QTextEdit)`：重写 `keyPressEvent`（Ctrl+C）与 `contextMenuEvent`（右键菜单「复制（含纪年换算）/ 复制原文/全选」），复制时经 `CHRONO.annotate_append`。
- `PdfView.copy_selection()`（拖选松手复制 / Ctrl+C / 右键复制选中）与右键「复制本页文字」分支都在文末附换算。
- `copy_text`（⧉ 复制文本）与 `copy_html`（复制带格式，HTML 追加一段）同样附换算；状态栏提示「含纪年换算 N 处」。

## 4. 纪年换算工具（主窗 · chrono_dialog）

- 输入框 + 「换算」→ 输出框显示标注结果；「取当前选区」「复制结果」；「反查公元年」输入年份 → 干支 / 在用年号 / 民国纪年。
- 打开时预填当前选区或剪贴板并自动换算；按钮「⌛ 纪年换算」+ `Ctrl+Shift+Y`。

## 5. 自检

- `功能自检.py` 新增 step 98–102（复制换算 / PDF 拖选换算 / 脚注 RTF / 换算工具 / 摘录换算）。
- 全部：`viewer_core --selftest` / `viewer_meta` / `viewer_tools` / `viewer_chrono` / `gui --selftest` / `gui --selftest2` / `功能自检.py` **全 OK（102/102）**。
