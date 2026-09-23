# batch20 报告 —— 「跨文件全文检索」按钮不见了的根因与修复

日期：2026-09-23 ｜ 用户报障：**左栏的跨文件搜索功能不见了**

---

## 1. 真实根因（比"被收进菜单"更严重）

batch17 为了让左栏能拖得极窄，我给左栏那排按钮设了横向尺寸策略
`QSizePolicy.Policy.Ignored`：

```python
for _b in (self.b_fts, self.b_fts_hist, self.b_alias, self.b_exc, self.b_more):
    _b.setMinimumWidth(0)
    _b.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
```

`Ignored` 的语义是「**忽略 sizeHint，给多少算多少**」；而这一行末尾还有一个
`addStretch(1)` 会把多余空间全吃掉 → 结果是**按钮实际宽高被压成 0**：

```
左栏 211px → b_fts[w=0, h=24]  b_more[w=0, h=22]     ← 整排按钮根本渲染不出来
左栏 600px → b_fts[w=0, h=26]  b_fts_hist[w=0, ...]  ← 宽了也一样看不见
```

所以**任何宽度下那排按钮都不可见**（用户保存的左栏宽度 211px 只是个巧合）。
自检 121/127 当时只查了 `isHidden()` 标志，查不出「宽高为 0」，漏过了这个 bug。

## 2. 修复

1. 尺寸策略改回 `QSizePolicy.Policy.Minimum`（按文字自然宽度显示）；
2. `_fit_left_buttons(width)` 重写为「**主入口永远留住**」：
   - `≥560px`：4 个按钮全显示（跨文件全文检索 / 检索历史 / 人名别名 / 摘录本）；
   - `≥380px`：只留「🔎 全文检索」+「⋮」（其余 3 个进菜单）；
   - `≥160px`：留「🔎 检索」+「⋮」；
   - 更窄：留「🔎」图标 +「⋮」；
   - 左栏窄于 220px 时收起「上级文件夹」列（沿用 batch17）。
3. 新增快捷键 **`Ctrl+Shift+S` = 跨文件全文检索**（左栏收起成 0 宽时也一定能用）；
4. `⋮` 菜单第一项仍是「跨文件全文检索」，任何宽度都可从菜单进入。

## 3. 验证

- **真几何断言**（新增，防止同类 bug 再漏）：自检 127 断言窄左栏下主按钮
  `width() > 20`、宽左栏下 3 个次要按钮 `width() > 20`；
- **目视验证**：按用户保存的 211px 布局渲染截图（`_shot/L211.png`、`L600.png`），
  211px 下确实能看到「🔎 检索」+「⋮」，600px 下 4 个按钮全展开；
- 左栏仍可拖到 ~110px（受「检索」按钮本身宽度限制），`Ctrl+Shift+L` 仍可一键收起/展开；
- 全量功能自检：**127/127 OK**（含把 110/127 两个旧断言按新语义更新）。

## 4. 经验（写进开发日志）

- 布局类 bug **必须查真实几何**（`width()/height()`），只查 `isHidden()`/`isVisible()` 会漏；
- `QSizePolicy.Ignored` + `addStretch` 组合会把控件压成 0 宽 —— 想「让控件可被压缩」应该用
  `Minimum` + 在窄时**隐藏**，而不是 `Ignored`。
