# CathayViewer 批次6 报告（修复发布落差 + 大文件能力 + 自检崩溃）

日期：2026-09-22
范围：`D:\我的软件创作库\CathayViewer-DEV\`（并重做发布包，剔除误带的索引库）
平台：Windows 真平台（`QT_QPA_PLATFORM=windows`）

---

## 0. 本批解决的四类问题

| # | 问题（来自评审） | 处理 |
|---|---|---|
| 1 | 发布包落后 DEV 一整批（第 5 批没进包） | 用当前源码**重新打包**，发布包与 DEV 对齐 |
| 2 | 发布包误带 508 MB `cathayviewer_index.db` | 打包/组装阶段**排除全部 `*.db`**，并加进 `.gitignore` |
| 3 | 大 TXT 只读前 200 KB（静默截断，与计划书 mmap 方案不符） | 改 **mmap 全文读取 + chardet 编码识别**，上限 64 MB 且状态栏提示 |
| 4 | JSON 未按计划书用 ijson 流式 | >20 MB 时 **ijson 流式看顶层**（无 ijson 则回退纯文本） |
| 5 | `gui.py --selftest2` 原生死锁（0xC0000409） | **找到真因并修复**（见 §3），连带修掉 `selftest2` 自身两个旧 bug |

---

## 1. 改动文件 + 字节数

| 文件 | 改前 | 改后 | 说明 |
|---|---:|---:|---|
| `gui.py` | 112,355 | **114,xxx** | 大 TXT / 大 JSON / 自检修复 / 文案 |
| `开发\功能自检.py` | 42,523 | **~47,000** | 新增 62–63；更新 32（流式/回退） |
| `requirements.txt` | 4 行 | 5 行 | + `ijson>=3.2` |
| `.gitignore` | — | — | + `dev_dist/ dev_build/ *.db cathayviewer_settings.json` |
| `使用说明.txt`（新） | — | — | 补第 5 批功能介绍（连续滚动/缩放/查找等） |
| `开发\batch6_报告.md`（新） | — | — | 本报告 |

未改动 `viewer_core.py` / `viewer_meta.py` 主体；未动 CathayShelf-DEV、Y: 盘或其它目录。

---

## 2. 功能实现要点

### ① 大 TXT：mmap 全文读取 + chardet（去 200KB 截断）
- `_read_bytes(p, limit=0)`：`limit=0` 读全文；文件 ≥4 MB 时用 **`mmap`** 映射后整块取出，避免额外缓冲；`limit>0` 只读前 N 字节。
- `_decode_text(b)`：**chardet 优先**（`gb2312/gbk → gb18030` 归一），失败再依次试 `utf-8-sig / utf-8 / gb18030 / big5`。
- `_show_text_file`：按 `TEXT_MAX_BYTES`（**64 MB**）决定是否截断；一旦截断**状态栏明确提示**「文件很大…只载入前 64 MB（不静默丢弃）」，不再无声丢内容。
- `md_toggle` 的源码读取同样走该通路。

### ② 大 JSON：ijson 流式顶层浏览
- `_json_load_stream(p)`：用 `ijson.parse` **流式**读顶层（不整份载入），object 列顶层键、array 列元素，最多 5000 项。
- `json_tree_dialog`：>20 MB 时优先走流式；**无 ijson 时**仍回退纯文本（行为与旧版一致）。
- 小文件仍用 `json.load` + `QTreeWidget`；对话框逻辑抽成 `_json_show_dialog()` 复用。

### ③ 自检崩溃修复（见 §3）
### ④ 文案：把「已打开文本（最多显示前 200 KB）」改为「只读，全文；超大文件最多前 64 MB」。

---

## 3. 关键根因：为什么 `--selftest2` 会原生崩溃

**不是 offscreen 平台问题，而是 QApplication 被 GC 回收。**

原代码：
```python
if not QApplication.instance():
    QApplication(sys.argv)      # 返回值被丢弃
app = QApplication.instance()   # 这里拿到的可能已是 None（上一步已被回收）
```
`QApplication(sys.argv)` 的 **Python 包装对象**没有被任何变量持有 → 引用计数归零 → 被 GC → 之后构造 `MainWindow` 时底层 `qApp` 已失效 → Windows 直接 **fail-fast `0xC0000409`**（连 Python traceback 都没有，`faulthandler` 也抓不到）。

**修复**：`app = QApplication.instance() or QApplication(sys.argv)` —— 创建即持引用。`selftest()` 与 `selftest2()` 两处都改。

> 这一条同时解释了历史报告里「offscreen 崩溃、真机正常」的迷惑现象：真机 `main()` 里 `app = QApplication(sys.argv)` 是有引用的，所以不崩。

顺带修掉 `selftest2` 自身的**两个旧 bug**（因长期崩溃而从未暴露）：
- `wz.count()` → `wz.stack.count()`（`Wizard` 没有 `count`）。
- 「搜索命中」断言 `len(w.rows) >= 2` → 兼容多版本聚合后的 `1 行（原始 2 条）`；预览改为直接走文本读取通路（聚合后不再单独列 txt 行）。

---

## 4. 功能自检（真平台）结果

```
SUMMARY ok=63 fail=0
RESULT = OK
```

- 原有 61 项**无回归**；新增/更新：
  - **32** 大 JSON 流式/回退 → `stream=map top=1 err=too_big`
  - **62** 大 TXT mmap 全文读取+chardet → `size=8.4MB len=4400000 tail=True enc=True bom=True`
    （末行读得到＝没被截到 200KB；GB18030 中文解对；带 BOM 的 UTF-8 解干净）
  - **63** 大 JSON ijson 流式顶层浏览 → `size=27.6MB err=too_big stream=map top=5000`

内置自检（本批修复后）也全绿：
```
py -3 gui.py --selftest2   → result = OK   （rc=0，不再 0xC0000409）
py -3 gui.py --selftest    → result = OK
py -3 viewer_core.py --selftest → result = OK
py -3 viewer_meta.py       → result = OK
```

编译：`py -3 -m py_compile gui.py viewer_meta.py viewer_core.py 开发\功能自检.py` → rc=0。

---

## 5. 发布包重做

- 用当前源码重新 PyInstaller 打包（含 `ijson`），产物写入 `dev_dist\CathayViewer.exe`。
- 组装发布脚本 `开发\make_release.py`：拷 exe + `config\` + `开发\`（源码）+ README/使用说明/app.ico，
  **自动跳过** `*.db / *_settings.json / dev_dist / dev_build / dist / __pycache__ / _dbg* / _probe*`。
- 生成 `校验值.txt`（字节数 + SHA256）。
- 发布目录与 zip（含源码）均**不再包含任何 `.db`**；索引库由用户首次运行时自建。

**新 exe**：`CathayViewer.exe` 96,692,670 字节
**SHA256**：`8ade106259aa49fad72bcc2c099067fc2050f4ccd28b03a7a4d99916856b008f`

---

## 6. 遗留 / 说明

1. 旧发布包（含 508 MB db 的那份）**改名归档**为 `.OLD-<时间戳>`，未删除（磁盘可自行清理）。
2. `ijson` 已装入环境并写进 `requirements.txt`；无 ijson 时大 JSON 行为回退为「纯文本」，不影响运行。
3. 自检里的大文件用例（8 MB TXT / 24 MB JSON）跑完即删（临时目录），不留垃圾。
4. `_dbg*.py` / `_probe_json.py` 为本次排障临时脚本，已在 `.gitignore` 的 `_*.py` 覆盖范围内，打包时一并跳过。
