# batch18 报告 —— 独立窗口的查找/最小化 与「直接打开文件」的邻居列表

日期：2026-09-23
范围：`D:\我的软件创作库\CathayViewer-DEV\`；**未改动**源书库、不碰注册表；**未删除**用户文件。

---

## 用户需求

2. 独立窗口模式下，按 **Ctrl+F 无反应**，PDF 阅读器的单文件搜索功能没法用。
3. **直接打开特定文件**（不是先搜文件名再打开）时，左侧文件栏应自动显示**同文件夹的其他文件** + **与之文件名相似的其他文件**。
4. 独立窗口模式下，**只最小化文件列表窗口**时，**阅读器窗口不应被连带最小化**。

## 1. 需求 2：独立阅读窗口的 Ctrl+F

**原因**：所有快捷键都是 `QShortcut(..., self)` 挂在**主窗口**上的；阅读器拆成独立窗口后焦点在独立窗口里，主窗口的带焦点快捷键不触发 → Ctrl+F 没反应。

**改法**：新增 `_bind_reader_shortcuts(win)`，在 `_detach_reader()` 里给独立窗口挂**窗口级**快捷键：`Ctrl+F`（打开查找条）、`Esc`（关查找条）、`F11`（该窗口全屏，新增 `_reader_full`）。快捷键对象挂到 `win._cv_sc` 持引用防 GC。

## 2. 需求 4：最小化列表窗口不带走阅读器

**原因**：`ReaderWindow(self)` 以主窗口为父窗口；Windows 下最小化父窗口会连带最小化子窗口。

**改法**：`ReaderWindow.__init__` 改为 `super().__init__(None)`（**顶层窗口，无父**）并显式 `setWindowFlag(Qt.Window, True)` 等；`owner` 仅作回调引用（关闭时仍 `_attach_reader` 收回）。主窗口 `closeEvent` 里主动把独立窗口一并关掉（并置 `_closing/_cv_no_attach`，避免关机时把阅读面板搬回正在销毁的窗口）。

## 3. 需求 3：直接打开文件 → 左栏列「同文件夹 + 相似文件名」

`open_path_in_reader()`（拖入 / 命令行 / 双击关联 共用入口）改为调用新增的 `_list_neighbors(p)`：

1. **同文件夹**：先 `viewer_core.by_dir(db, 目录)`（新增，`COLLATE NOCASE` 只读查询），再用 `os.scandir` 把**没进索引**的同目录文件补齐；
2. **文件名相似**：`viewer_core.like_stem(db, 主干)`（新增，`stem LIKE '主干%'`），两份键——
   - `META.book_core(文件名)`，
   - `_similar_key()`（新增：再去掉「续编/补遗/外编/外编/补编…」尾缀，让「甲书续编」也能带出「甲书」系列）；
3. 填充时 **不去重**（新增 `_fill_rows(rows, dedup=False)`）——邻居列表里**每个文件各占一行**（搜索结果的「同书串一条」规则不适用于这里）；
4. 自动**选中被打开的那个文件**，状态栏给出「左侧：同文件夹 N 个 ｜ 相似文件名 M 个（共 K 个）」。

## 4. 改了哪些文件

| 文件 | 说明 |
|---|---|
| `gui.py` | `ReaderWindow`（无父顶层窗口）；`_bind_reader_shortcuts/_reader_full`；`_attach_reader/closeEvent` 关机保护；`do_search` 抽出 `_fill_rows(rows, dedup=True)`；新增 `_similar_key/_list_neighbors`；`open_path_in_reader` 改走邻居列表 |
| `viewer_core.py` | 新增 `by_dir()` / `like_stem()`（均只读、限额） |
| `开发\功能自检.py` | 新增 122-125；总数 121 → **125** |
| `README.md` / `使用说明.txt` / `开发日志.md` | batch18 说明 |

## 5. 自检

```
viewer_core / viewer_meta / viewer_tools / viewer_chrono / viewer_alias / gui --selftest(2)  => result = OK
py -3 开发\功能自检.py  =>  SUMMARY ok=125 fail=0  RESULT = OK
```

新增用例：
- 122 独立阅读窗口 Ctrl+F 可打开查找条（窗口级快捷键 + 实际弹条）
- 123 最小化文件列表窗口不带走独立阅读器（`win.parent() is None`、`isMinimized()` 仍 False、能收回）
- 124 直接打开文件 → 左栏列出同文件夹 + 相似文件名（n=5，选中被打开文件）
- 125 直接打开孤立文件不报错（左栏至少含它自己）

## 6. 说明

- 邻居列表用的是**索引库**（快）+ 磁盘目录补齐；若某书从未入库也会出现在“同文件夹”里。
- 「相似文件名」按**书名主干前缀**判定（同文件夹的先列在前）。
