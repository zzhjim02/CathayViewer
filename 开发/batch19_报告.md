# batch19 报告 —— 修复 `_PDV5AIFOCR` / `_PDV6AIFOCR` 后缀无法归到同一本

日期：2026-09-23 ｜ 用户报障（含实例目录）
范围：`CathayViewer-DEV`（**并同步修了 CathayShelf-DEV**）；只读源书库、不碰注册表。

---

## 1. 现象（用户给的实例）

```
Y:\...\中华民国史档案资料汇编 第3辑\
   第3辑外交_OCR.txt
   第3辑外交_OCR_【简转繁】.txt
   第3辑外交_OCR_PD5AIOCR.pdf
   第3辑外交_OCR_PD5AIOCR.txt
   第3辑外交_OCR_PD5AIOCR_【简转繁】.txt
   第3辑外交_PDV5AIFOCR.txt          ← 与上面几个「不是同一本」
   第3辑外交_PDV5AIFOCR_【简转繁】.txt ← 同上
```

**根因**：解析产物后缀的正则只认 `pd` / `pdl` / `pdN` 形状：

```python
(?:pd(?:vl)?\d*)?(?:ai)?f?ocr        # PD / PDL / PD6 OK；PDV5 / PDV6 ✗
```

`PDV5AIFOCR` 里 `PD(?:vl)?` 后面来的是 `V5`（字母+数字），正则匹配不上 → 只把尾巴的 `AIFOCR` 剥掉，**留下 `PDV5`**：

| 文件名 | 修复前 `book_core` | 修复后 |
|---|---|---|
| `第3辑外交_OCR.txt` | 第3辑外交 | 第3辑外交 |
| `第3辑外交_PDV5AIFOCR.txt` | **第3辑外交 PDV5** ✗ | 第3辑外交 ✅ |

于是：搜索时它们**各占一行**、版本下拉**分家**、PDF/TXT 也配不上对。

## 2. 修改

**CathayViewer / `viewer_meta.py`**
1. `NOISE_TOK`：`(?:pd(?:vl)?\d*)?` → **`(?:pd[a-z]{0,2}\d*)?`**（可吃掉 `PDV5 / PDV6 / PDVL5 / PD5 / PDL5 …`）；
2. `_ENG_TAG`（族键尾部）同样放宽；
3. 新增 `_ANY_OCR`：族键里**任意位置**的 OCR 引擎标记都剥（这样 `_OCR_PD5AIOCR` 与 `_OCR` 也归一族）；
4. `_TXT_SUFFIXES` 补齐 `_PDV5AIFOCR / _PDV5AIOCR / _PDV6AIFOCR / _PDV6AIOCR / _PD5AIFOCR / _PD5AIOCR / _PDL5*` 及其 `_【简转繁】/_【繁转简】` 组合；
5. `_sibling_texts` 的排序键改为同时认「繁转简 / 简转繁」。

**CathayShelf / `core.py`**：`NOISE_TOK` 同一处放宽（用户问的“是不是 SHELF 也有” → **是**，已同样修好）。

## 3. 效果（用用户给的目录实测）

- `family_key('第3辑外交_*')` 现在**全部相同** → 该辑 7 个文件**聚成 1 本**（修复前 4 + 3 两组）；
- `_sibling_texts` 能找出 6 个 TXT 变体、`_sibling_pdfs` 找到 PDF；
- 全量自检新增 **126**：搜索 `第3辑外交` → **1 行**、版本下拉 **7 项**；
- CathayShelf `core.py <目录> groups` 实测：`第3辑军事1` 7 个文件归为 1 个书 key ✓。

## 4. 自检

```
viewer_meta.py  =>  result = OK（新增 PDV5/PDV6 用例 3 条）
py -3 开发\功能自检.py  =>  SUMMARY ok=126 fail=0  RESULT = OK
```

## 5. 说明

- 规则没变：**不同 OCR 引擎的同名 TXT 仍然都保留**（不会被去重隐藏），只是现在会**归到同一本书**里，用「版本」下拉切换。
- CathayShelf 只改了源码（`core.py`）；其打包 exe 未重发（如需重发请说一声）。
