# batch15 报告 —— 拖入打开 / 双击关联

日期：2026-09-23
范围：`D:\我的软件创作库\CathayViewer-DEV\`（`0.1.0` 产物由 `make_release.py` 重新组装）
**未改动**源书库 / 其它盘；**未删除**任何用户文件。

---

## 1. 本批要解决的问题

| # | 用户反馈 | 处理 |
|---|---|---|
| 10 | 新增支持拖入 PDF / TXT 打开 | `MainWindow` 开启拖放：`dragEnterEvent/dragMoveEvent/dropEvent`，拖入即在阅读区打开 |
| 11 | 双击 PDF / TXT 后用本软件打开 | `关联.bat` 增加「设为默认」（HKCU）行；`取消关联.bat` 同步回退 |

---

## 2. 改了哪些文件

| 文件 | 说明 |
|---|---|
| `gui.py` | 模块常量 `READER_EXTS`；`__init__` 加 `setAcceptDrops(True)`；新增 `open_path_in_reader(p, note)`、`_url_reader_ok`、`dragEnterEvent`、`dragMoveEvent`、`dropEvent`；`open_cli_arg` 改用 `open_path_in_reader` |
| `关联.bat` / `取消关联.bat` | 每个扩展名后新增一条默认关联/取消行（HKCU）；保持 **ASCII + CRLF** |
| `开发\功能自检.py` | 新增 115-117（3 项）；总数 114 → **117** |
| `README.md` / `使用说明.txt` / `开发日志.md` | batch15 说明 |

辅助脚本（`_` 前缀，打包自动排除）：`_assoc_patch.py`（一次性补丁，幂等）。

---

## 3. 关键实现

### 3.1 拖入打开
- `READER_EXTS = ('.pdf', '.txt', '.text', '.md', '.epub', '.json', '.csv')`。
- `dragEnterEvent`：只当 MIME 里有**本地文件且扩展名在 READER_EXTS** 时才 `acceptProposedAction`，否则 `ignore`。
- `dropEvent`：收集本地文件路径；取第一个（不在支持列表则提示）；多个时提示「另有 N 个拖入文件已忽略」；调 `open_path_in_reader(p, note)` 并 `_hist_add()`。

### 3.2 双击关联（PDF / TXT）
`关联.bat`（用户级，需用户双击运行，不改系统级、不装服务）在原有 `OpenWithProgids` 之外，新增：
```
reg add "HKCU\Software\Classes\.pdf" /ve /d "CathayViewer.pdf" /f
```
（.epub / .txt / .md 同）——写入**用户级默认**，双击即可用本软件打开。
`取消关联.bat` 对应新增 `reg delete "HKCU\Software\Classes\.pdf" /ve /f`。
> 注：Win10/11 若已存在 UserChoice，仍可能需在「默认应用」里手选一次（系统保护机制）。

---

## 4. 自检结果

```
py -3 gui.py --selftest   => result = OK
py -3 gui.py --selftest2  => result = OK
py -3 开发\功能自检.py     => SUMMARY ok=117 fail=0  RESULT = OK
```

新增用例：
- 115 拖入 PDF/TXT → 在阅读区打开（含 `dragEnter` 接受）
- 116 拖入多个 → 只开首个 + 提示其余忽略
- 117 关联/取消关联脚本：ASCII + CRLF + 含 PDF/TXT + 含设为默认行

---

## 5. 遗留 / 说明

1. 拖放已用假事件对象（`_FakeDrop`）在自检中验证核心分支；真实拖动行为与原 `open_cli_arg` 共用同一路径。
2. 关联脚本仍为**用户级**（HKCU），不写 HKLM、不写服务；需用户自行双击运行。
3. 本批**未重新打包 exe**。
