# CathayViewer「文献著录信息」提取能力补齐 —— 报告

日期：2026-09-22
范围：`D:\我的软件创作库\CathayViewer-DEV\`（**未改动** CathayShelf-DEV、Y: 盘或任何其他目录；未删除任何用户文件）

---

## 1. 改了什么

| 文件 | 改动前 | 改动后 | 说明 |
|---|---|---|---|
| `viewer_meta.py` | — | **34653 字节** | 主体改动：新增深度著录引擎；`parse()` 变为分派入口 |
| `gui.py` | — | **39858 字节** | 仅 2 处最小改动：列表分组/同书判定的两处 `META.parse(...)` 显式加 `deep=False`，避免搜索时对每行读版权页拖慢界面 |

算法来源：只读参考 `CathayShelf-DEV\core.py`（`pdf_text / locate_colophon / parse_cip / find_pub / find_year / extract_title / author_from / nw / T2S_LIGHT` 等），**移植规则到 viewer_meta.py，不 import、不改动 CathayShelf**（避免打包耦合）。出版社→城市沿用原 `publisher_city()`（读 `CathayViewer-DEV\config\publishers.csv`，缺则只读兜底 `CathayShelf-DEV\config\publishers.csv`）。

## 2. 新增 / 修改的函数

**修改**
- `parse(name, path='', deep=None)` —— 分派入口：`deep` 省略时 `= bool(path)`；有 path 时走 `parse_deep`，异常自动退化回文件名解析；**签名兼容，`parse(name)` 行为与旧版逐字节一致**（已校验 `parse(name) == _parse_file(name)`）。
- `parse()` 原文件名逻辑整体移入私有函数 **`_parse_file(name, path='')`**（避免与 `parse_deep` 相互递归）。
- `publisher_city(pub, extra_csv='')` —— 拆出懒加载器 `_city_map()`，行为不变。
- `cite()` —— 城市优先取 `meta['city']`（深度著录结果），缺则回退 `publisher_city(pub)`。
- `selftest()` —— 增加一行 `_selftest_deep(ok)` 调用。

**新增（深度著录引擎）**
- `parse_deep(name, path='')` —— 四来源合并主函数，返回字段与 `parse()` 一致，另加 `'city'`（出版社→城市）与 `'src'`（各字段来源：`file`/`folder`/`txt`/`pdf`/`dict`）。
- 文本工具：`_nw()`（全角→半角＋清私用区乱码）、`_read_head()`（只读文件头解码）、`_detect_trad()`。
- 版权页规则（移植）：`_locate_colophon()`、`_parse_cip()`、`_valid_author()`、`_extract_title()`、`_find_pub()`、`_find_year()`、`_author_from()`。
- 四个来源采集：`_folder_names()` / `_folder_meta()` / `_strip_vol_tail()`、`_sibling_texts()`、`_sibling_pdfs()`、`_pdf_text()`、`_colophon_meta()`。
- 自检：`_selftest_deep(ok)`。

**合并优先级**（每个字段按序取第一个非空）：`文件名 > 文件夹链 > 同名TXT > PDF`。
- 满足需求⑤「folder 补 file 的空缺」：文件名已有的字段不被文件夹覆盖，文件名缺失的字段由文件夹补。
- 版权页内部再分优先级：`locate_colophon` 滑窗后 **优先 CIP「图书在版编目」行**，其次含 出版/发行/印张/定价/ISBN/第 N 版 的版权页窗口。
- 城市：CIP 里直接给出则用它，否则 `publisher_city(出版社)`（src 标为 `dict`）。

**同名文本变体**覆盖：`<stem>_result.txt`、`<stem>_PD6AIFOCR.txt`、`<stem>_PD6AIOCR.txt`、`<stem>_PDVL6AIFOCR.txt`、`<stem>_【繁转简】.txt` 等；此外同目录下 `book_core` 相同的任意 `.txt` 也纳入（非繁转简优先）；用户选中的若是 txt，则同时回找同书 PDF。

## 3. 自检输出

### `py -3 viewer_meta.py`（result = **OK**，15 项全绿）

```
OK   孙中山全集 第三册_10490188_PD6AIFOCR.pdf → 孙中山全集 第三册
OK   鲒埼亭集_PDVL6AIFOCR_【繁转简】.txt → 鲒埼亭集
OK   中国伪书综考（全1册）（邓瑞全 王冠英编著 合肥 黄山书社1998年 → 中国伪书综考（全1册）
OK   （可打印版）金翼英文版扫描版-全篇_unlocked_PD6AIOC → （可打印版）金翼英文版 全篇
OK   近代中国史料丛刊三辑 0427 冯宫保（子材）军牍集要（一）_PD6 → 近代中国史料丛刊三辑 0427 冯宫保（子材）军牍集要（一）
OK   布罗代尔：十五至十八世纪的物质文明 第1卷_14296873_lay → 十五至十八世纪的物质文明 第1卷
OK   续伪书通考_郑良树编著_台湾学生书局1984年.pdf → 续伪书通考 郑良树编著 台湾学生书局1984年
OK   多版本聚合：3 个文件聚成 1 本 → 1 组
OK   版本排序：PDF 原本排第一 → ['.pdf', '.pdf', '.txt']
OK   引用：布罗代尔：《十五至十八世纪的物质文明 第1卷》，第27页。
OK   ①只有文件夹名 → pub=文物出版社 year=1981 au=李泽厚 vol=全1册 city=北京
OK   ②只有文件名 → pub=台湾学生书局 year=1984 au=郑良树 city=台北
OK   ③同名_result.txt CIP → pub=文物出版社 year=1981 au=李泽厚著 city=北京
OK   ④合成PDF版权页 → pub=商务印书馆 year=1992 city=北京 name=十五至十八世纪的物质文明
OK   ⑤合并优先级 → name=十五至十八世纪的物质文明 第1卷 vol=第1卷 pub=商务印书馆 year=1992 src={'name': 'file', 'publisher': 'folder', 'year': 'folder', 'city': 'dict'}
result = OK
```

五个深度用例均自造临时文件（`tempfile`）验证、跑完 `shutil.rmtree` 删除：
1. **只有文件夹名** —— 目录 `李泽厚：美的历程（全1册）（北京 文物出版社1981年）`，文件名为纯编号；→ 作者/出版社/年/卷册/城市全部来自 **folder**。
2. **只有文件名** —— `续伪书通考_郑良树编著_台湾学生书局1984年.pdf`；→ 出版社/年/作者/城市来自 **file**。
3. **同名 `_result.txt` 有 CIP 行** —— CIP 行 `美的历程／李泽厚著．—北京：文物出版社，1981.3`；→ 出版社/年/作者/城市来自 **txt**。
4. **合成 PDF 文本层有版权页** —— 用 PyMuPDF 生成单页 PDF，写入 CIP 行；→ 出版社/年/城市/书名来自 **pdf**。
5. **合并优先级** —— 文件夹名 `旧书名（北京 商务印书馆1992年）` + 文件名 `十五至十八世纪的物质文明 第1卷_14296873_layered.pdf`；→ 书名/卷册取 **file**（不被 folder 覆盖），出版社/年由 **folder** 补空，城市由词典得。

### `py -3 -m py_compile viewer_meta.py gui.py` → **退出码 0**（界面文件语法/编译无恙）

### 兼容性
- `parse(name)` 返回结构与旧版**完全一致**（无新增 `city`/`src` 键）。
- `parse(name, path)`（如 GUI 的 `on_pick`）走深度著录，异常自动回退，不会中断界面。

## 4. 遗留问题

1. **GUI 离屏自检在本机（PyQt6 6.10.2 + Python 3.14 + offscreen）会在 `MainWindow.__init__` 处原生崩溃**（退出码 `0xC0000409`），**属预存在环境问题，与本次改动无关**：把本次对 `gui.py` 的两处 `deep=False` 改动还原成原样后崩溃依旧发生；崩溃点在任何 `META.parse` 调用之前。`py -3 -m py_compile gui.py` 通过。建议在有正常显示/匹配 Python 的机器上跑 `py -3 gui.py --selftest2` 复核界面。
   - 副作用：尝试运行该自检时，工具会把结果写进 `CathayViewer-DEV\_selftest_gui.txt`（该文件本就是自检每次运行的产物），因崩溃中断目前仅留下首行 `OK 建库 4 个文件 → 4`。它不是用户资料，待自检能正常跑完即可自动回填完整结果。
2. `_fill_versions` 用 `deep=False` 的名字做同书匹配；若某书文件名是纯编号、书名只能从文件夹/版权页得到，则深度书名与列表书名可能不一致，导致该书的版本串接匹配不到。当前库多为「文件名即书名」，影响面很小；如需彻底对齐，可让该处也走深度（代价是切书时逐候选读版权页，较慢）。
3. 文件夹链只对**最近一级**（或名字里含 `（`/`：`/`《` 的祖先目录）贡献「书名」，避免把 `历史` 之类的分类目录名误当书名；祖先目录仍可贡献作者/出版社/年/卷册（近的优先、只补空）。
4. 未重新打包 exe（按要求由你来做）。
