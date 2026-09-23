# batch16 报告 —— 修复「双击文件列表后程序很卡」

日期：2026-09-23
范围：`D:\我的软件创作库\CathayViewer-DEV\`
**未改动**源书库 / 其它盘；**未删除**任何用户文件。

---

## 1. 现象与定位

用户反馈：**双击文件列表后程序很卡**。

用真实 508 MB 索引库（447,102 条）+ `_dbg_lag2.py` 实测「选中/双击」链路上最重的一步：

| 文件 | 大小 | 浅著录 `deep=False` | 深著录 `deep=True` | `C.search(200)` |
|---|---|---|---|---|
| 辞海（第六版彩图本）_OCR_opt.pdf | 2207 MB | 0.000s | 0.279s → **修后 0.154s** | 0.009s |
| 汉语国学辞典.txt | 2051 MB | 0.000s | 0.085s → **0.035s** | 0.008s |
| 中华人民共和国药典…中药饮片卷_OCR.pdf | 1818 MB | 0.000s | **10.671s** → **0.137s** | 0.019s |
| 中华人民共和国药典…中药成方制剂卷.pdf | 1436 MB | 0.000s | **8.425s** → **0.130s** | 0.004s |
| 中华人民共和国药典 2020年版：二部.pdf | 1307 MB | 0.000s | **8.171s** → **0.109s** | 0.015s |

**根因**：`on_pick()` 在 **UI 线程同步**调用 `META.parse(..., deep=True)`；大 PDF 找不到版权页特征时会**逐页读取整本文字层**（`viewer_meta._pdf_text` 的全文回退），1.8 GB 的书要 **8–10 秒**；而且旧的元数据缓存只保留**最后一个**文件，翻列表会反复解析。

另外两处大文件卡顿：普通文本阅读上限 64 MB、对读 TXT **无上限**（`TOOLS._read_text` 读整文件）——遇到 2 GB 级 TXT 会直接卡死界面。

---

## 2. 修复

1. **深著录移入后台线程**：新增 `MetaWorker(QThread)`；`on_pick()` 先做**浅著录（deep=False，毫秒级）**立即显示详情，深著录放后台，完成后**只刷新详情条**。
2. **持久元数据缓存**：`self._meta_map`（`(路径, mtime)` 键，上限 400 条，超出清空），同一文件第二次选中**直接命中**，不再解析。
3. **大书不全量扫文字层**：`viewer_meta._pdf_text` 增加 `_FULL_SCAN_MAX = 200`：页数 ≤200 才全文回退，>200 只用「前 16+后 16」→ 无特征时扩到「前 60+后 30」，**不再全文**。（深著录 8–10s → 约 0.1–0.5s）
4. **文本阅读上限降到 8 MB**：`TEXT_DISPLAY_MAX = 8 MB`（超过只显示前 8 MB + 提示「为不卡界面」）。
5. **对读 TXT 上限 8 MB**：`TxtSyncView.load` 只读前 8 MB（`truncated` 标记，对读条注明）；`_maybe_auto_dual` 对 **>8 MB 的 TXT 不自动进对读**（提示可手动点「⇄ 对读」）。

---

## 3. 改了哪些文件

| 文件 | 说明 |
|---|---|
| `gui.py` | `MetaWorker`；`on_pick` 重写为「浅著录 + 后台深著录 + 缓存」（拆出 `_render_info`、新增 `_request_deep_meta/_on_deep_meta`）；常量 `TEXT_DISPLAY_MAX/DUAL_TXT_MAX/DUAL_AUTO_MAX`；`_show_text_file` 用 8 MB 上限；`TxtSyncView.load` 截断；`_maybe_auto_dual` 大 TXT 跳过 |
| `viewer_meta.py` | `_pdf_text` 大书不全量扫描（`_FULL_SCAN_MAX=200`） |
| `开发\功能自检.py` | 新增 118-120（3 项）；总数 117 → **120** |
| `README.md` / `使用说明.txt` / `开发日志.md` | batch16 说明 |

调试脚本（`_` 前缀，打包自动排除）：`_dbg_lag.py`、`_dbg_lag2.py`、`_assoc_patch.py`、`_dbg_*`。

---

## 4. 自检结果

```
viewer_core / viewer_meta / viewer_tools / viewer_chrono / viewer_alias  => result = OK
gui.py --selftest / --selftest2                                        => result = OK
py -3 开发\功能自检.py  => SUMMARY ok=120 fail=0  RESULT = OK
```

新增用例：
- 118 大 PDF 著录不卡：`on_pick` 秒回（实测 0.001s）+ 后台补深著录 + 缓存命中
- 119 超大 TXT（9 MB）只载入前 8 MB + 提示
- 120 超大 TXT：对读只载入前 8 MB，且不自动进对读

---

## 5. 效果与说明

- 双击/选中大 PDF：详情**立即**出现（浅著录），深著录几百毫秒内在后台补上；重复选中**零成本**。
- 深著录不再全文扫描：对**极少数把 CIP 放在中间**的超大书，可能识别不到版权页——属权衡（可再用 `Copyright/CIP` 关键词手查或全文检索）。
- 超大 TXT：阅读/对读最多前 8 MB（可搜索仍走 64 MB 上限的查找通道）。
- 本批**未重新打包 exe**。
