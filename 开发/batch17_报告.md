# batch17 报告 —— 左侧文件列表可手动缩小（batch17）

日期：2026-09-23
范围：`D:\我的软件创作库\CathayViewer-DEV\`；**未改动**源书库、不碰注册表；**未删除**用户文件。

---

## 1. 需求

「左侧文件列表需要能够手动缩小宽度，现在的最小宽度太大了，太占地方。」

## 2. 定位

左栏看似已把 `tb.setMinimumWidth(90)`（batch14），但**实际拖不动**，因为左栏顶部还放了一排动作按钮：

- 🔎 跨文件全文检索 / 🕘 检索历史 / 👤 人名别名 / 🗂 摘录本

四个按钮的文字把左栏的 **minimumSizeHint 撑到约 400px**，QSplitter 拖到该值就停下——所以「最小宽度太大」。

## 3. 修改

| 项 | 改法 |
|---|---|
| 列表最小宽度 | `90 → 48 px`（`tb.setMinimumWidth(48)`） |
| 按钮不再撑宽 | 4 个按钮 + 「⋮」按钮设 `QSizePolicy.Ignored/Fixed`、`minimumWidth(0)` |
| 窄时收纳 | 左栏宽度 **< 420px** 时，4 个按钮隐藏，改用 **「⋮」菜单**（菜单里含同样 4 项动作）；再窄（< 220px）自动收起「上级文件夹」列 |
| 完全收起 | `sp.setCollapsible(0, True)`：拖到 0 可完全收起左栏（右侧保底 ≥200px） |
| 一键收起/展开 | 新增 `Ctrl+Shift+L`（`toggle_list`），收起后记住原宽，再按恢复 |
| 「上级文件夹」列 | `ResizeToContents → Interactive`（初宽 150），可手动拖宽窄，不再被长路径撑死 |
| 自适应时机 | `splitterMoved` 信号 + `resizeEvent` 都调用 `_fit_left_buttons()` |

## 4. 改了哪些文件

- `gui.py`：`_ui`（表头/按钮/分割条）、新增 `_fit_left_buttons/_on_split_moved/toggle_list`、`Ctrl+Shift+L` 快捷键、`resizeEvent` 接入。
- `开发\功能自检.py`：测试 42/87/110 适配（左栏可收起、列模式改 Interactive、极窄可拖到 48）+ 新增 **121**（一键收起/展开）。总数 **120 → 121**。
- `README.md` / `使用说明.txt` / `开发日志.md`：batch17 说明。

## 5. 自检

```
viewer_core / viewer_meta / viewer_tools / viewer_chrono / viewer_alias / gui --selftest(2)  => result = OK
py -3 开发\功能自检.py  =>  SUMMARY ok=121 fail=0  RESULT = OK
```

新增/调整用例：
- 42 分割条最小宽度约束（左栏可收起、阅读区保底 ≥200）
- 87 文件列表列模式（文件名 Stretch + 上级文件夹 Interactive）
- 110 左栏可拖得极窄（tb.min=48；窄时按钮收进 ⋮；宽时恢复）
- 121 一键收起/展开（Ctrl+Shift+L；collapsed=0）

## 6. 说明

- 左栏在 **420–880px** 区间显示完整按钮；**<420px** 只显示「⋮」；**<220px** 收起「上级文件夹」列。
- 想彻底腾地方：`Ctrl+Shift+L` 或把分割条拖到最左。
