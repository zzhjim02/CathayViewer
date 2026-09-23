# CathayViewer 批次13 报告（人名别名归一）

日期：2026-09-23
范围：`D:\我的软件创作库\CathayViewer 学术书库浏览与阅读 0.1.0\开发\`（+ 沙箱副本）
平台：Windows 真平台（`QT_QPA_PLATFORM=windows`）
结果：`开发\功能自检.py` **SUMMARY ok=105 fail=0**（batch1–12 无回归）

---

## 0. 需求 → 处理（对应清单 12）

| 需求 | 处理 | 自检 |
|---|---|---|
| 检索「吴佩孚」→ 询问是否自动检索「子玉、吴玉帅、玉帅、孚威将军、孚威」 | `do_search` 先做别名归一，`_alias_extra` 弹框询问（可设 auto/off）；并入的别名一起检索 | 103 |
| 输入「孙中山」→ 自动关联「孙文、逸仙、中山樵」 | 同上；`alias_mode='auto'` 时直接并入 | 103/105 |
| 尽量覆盖近代甚至中国古代人物 | 内置表 + **CBDB 离线导入**（实测 9.9 万人 / 15.7 万别名） | 104/105 |
| 网上数据可否用 | 见下「数据源与发布」 | — |

---

## 1. 新增纯逻辑模块 `viewer_alias.py`

- **别名表**：`DEFAULT_ALIASES`（84 人 / 391 别名：先秦—清 + 晚清民国）——事实性 字号/号/谥号/笔名/化名/绰号。
- **索引**：别名 / 正名 → {正名}（带缓存 `_idx`，`reload()` 失效）；`lookup` 支持一个字号对应多人。
- **`expand(kw, limit=16)`**：要一并检索的其它名字（含正名反查），保序去重、封顶 16（CBDB 里大量同名号）。
- **维护**：`add_person / remove_person / write_csv / import_csv`（用户表 = `app_dir()/person_alias.csv`，多种分隔符）。
- **CBDB 离线导入** `import_cbdb_dir(folder, merge=True, min_len=2, max_aliases=40, year_from, year_to, on_progress)`：
  - 读 `BIOG_MAIN.xlsx`（c_personid → c_name_chn，正名）与 `ALTNAME_DATA.xlsx`（c_personid → c_alt_name_chn，别名）；
  - 只留 2 字以上且含 CJK 的别名，去重、封顶；可按时段过滤；
  - 写入本地 `person_alias.csv`，不发布。
- 自检：`py -3 viewer_alias.py` → 12/12 OK。

## 2. 主窗接入（gui.py）

- `do_search()`：`extras = self._alias_extra(kw)` → `kws = [kw] + extras`，逐个 `C.search` 后合并去重（同书各版本仍串成一条）；状态栏显示「已并入别名：…」。
- `_alias_extra()`：按 `st['alias_mode']`（**ask 默认 / auto / off**）决定；ask 用 `QMessageBox.question` 列出别名询问。
- `_HiDelegate` 改为**多关键词高亮**（长词优先匹配、逐字绘制黄底），`_hl_kws` 保存本轮关键词。
- **👤 人名别名** 对话框（`Ctrl+Shift+A` + 左栏按钮）：模式选择；人员列表（正名：别名…）；新增/编辑、删除、导入 CSV、导出 CSV、**从 CBDB 导入…**、按人名/字号反查。
- 按钮行/左栏已含：📷截图 · ✂摘录 · ⇄对读 · ❞脚注 · ⌛纪年换算 · 👤人名别名。

## 3. 数据源与发布

| 数据源 | 内容 | 获取 | 许可 |
|---|---|---|---|
| **本地 CBDB 导出**（已并入、随包发） | 正名 + 字/号/别名（以古代为主，6.4 万人物 19.7 万别名行） | `F:\...\CBDB主数据库-直接导出-20240820` | CBDB（Harvard/北大/中研院），学术免费、需引用 |
| Wikidata | 别名 + 字/号 属性 | SPARQL/API 或 dump | CC0 |
| 中研院人名权威档 | 明清人物 字号 | 站点 | 学术使用 |
| CN-DBpedia / 维基百科 | 别称/别名 | dump | 视来源 |

> 随包数据落位 `config\person_alias.csv`（内置精简表 + CBDB 衍生，约 9.9 万人 / 15.7 万条），启动自动加载；用户自己增补的写本地 `person_alias.csv`（不覆盖随包那份）。程序**不联网**。
> **致谢**：别名数据含 CBDB 衍生内容，版权归 CBDB，学术免费需引用。

## 4. 实测

```
CBDB 导入：...\中国历代人物传记数据库（CBDB）主数据库-直接导出-20240820
DONE people=98586 aliases=156844        # 合并内置后 98649 / 157208
OUT ...\开发\person_alias.csv  (2.2 MB)
```
- 苏轼 → 苏东坡/苏子瞻/子瞻/东坡居士/和仲/铁冠道人；王安石 → 半山/介甫/临川先生/荆公…
- 反查：子瞻→苏轼、东坡居士→苏轼、半山→王安石、醉翁→欧阳修、孙文→孙中山、周树人→鲁迅。

## 5. 自检

- `功能自检.py` 新增 step 103–105（别名归一检索 / 别名表对话框 / expand·lookup 反查）。
- 全部：`viewer_core --selftest` / `viewer_meta` / `viewer_tools` / `viewer_chrono` / `viewer_alias` / `gui --selftest` / `gui --selftest2` / `功能自检.py` **全 OK（105/105）**。
- `make_release.py`：把 `config\person_alias.csv` **随包发布**（需求：人名数据要随软件发布）；仅排除**顶层**运行时本地用户表 `person_alias.csv`。
