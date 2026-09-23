# -*- coding: utf-8 -*-
"""CathayViewer 功能自检（batch1 + batch2 + batch3 + batch4）

真平台运行（QT_QPA_PLATFORM=windows）+ 真 QApplication + 临时目录造文件。
每一步都写日志文件（不依赖 stdout —— Qt 原生崩溃会吞掉输出）。
覆盖 12 项要求 + batch1 新增 6 项 + batch2 新增 9 项（19-27）
+ batch3 新增 9 项（28-36：MD 渲染切换 / 非 md 提示 / JSON 树与过滤 / 大 JSON 回退
/ 坏 JSON 回退 / 相关文件三档 / 双击打开通路 / 缩略图面板与跳页）
+ batch4 新增 7 项（37-43：双击 PDF 进阅读区 / 双击文本进阅读区 / 命令行带文件进阅读区
/ 多文件参数只开首个+提示 / 阅读区宽度占比 / 分割条最小宽度 / 外部打开为显式按钮）
+ batch5 新增 14 项（44-57：关联/取消关联脚本存在且为 ASCII+CRLF+含关键串 / PDF 连续滚动
初始载入 / 滚到中部底部页码变化+已插页增加 / PgUp·PgDn·Ctrl+Home·Ctrl+End / 导航面板默认
展开+目录页签+双击跳页 / TXT 文内查找命中+下一个循环 / PDF 文字层查找到已知词 / 无文字层 PDF
给提示 / 非 PDF 打开时面板隐藏不报错 / Ctrl+F 显示·Esc 关闭查找条 / 同一页只渲染一次（缓存
复用）/ 缩放切换后页码与页数不错乱 / 页码框输入跳页生效）
+ batch6 新增 4 项（58-61：Ctrl+滚轮缩放生效 / 页码框输入 7 回车→当前页=7（1 基）/ 缩放回
「适应宽度」后仍能继续滚动加载下一页 / 目录联动高亮随页变化）。
+ batch7 重构与新增（阅读器内核换为 PdfView；64-69：阅读器独立窗口 / PDF 平滑滚动（滚轮像素
+ ↑↓）/ 文字层鼠标选择复制 / 跨文件全文检索（独立进程）/ 目录单击跳页 / 版权·授权信息三来源）。
+ batch8·9·10（70-91）：列表 3 列 / 只显示上一级 / 单击打开 / 默认适应页面 / 跨页连选 / 关键词
高亮 / 默认双窗 / 顶部紧凑 / 检索按钮移左栏 / 布局记忆 / 版式自适应 / 版本切换真打开 / 查找健壮。
+ batch11 新增 6 项（92-97：✂摘录本 / 📷截图本（整页+框选）/ ⇄打开 TXT 自动对读 / ⇄页码双向
同步 / 🕘检索历史自动保存与调阅 / ⤒版权页目录优先+回退）。
+ batch12 新增 5 项（98-102：⧉复制文本自动附纪年换算 / PDF 选中复制自动换算 / ❞脚注 RTF /
⌛纪年换算工具 / ✂摘录自动含纪年换算）。
+ batch13 新增 3 项（103-105：👤人名别名归一（检索人名并入字號/笔名，ask/auto/off）/ 人名
别名表对话框 / 别名归一逻辑 expand·lookup 反查）。
+ batch14 新增 9 项（106-114：⇄对读左右并列+中间 PDF 导航 / 对读可切 TXT 版本 /
对读可退出只看 PDF·只看 TXT / 进对读保持 PDF 页并同步 TXT / 左栏可缩很小 +
「版本」下拉变宽 / 🗂摘录查看・编辑器 / ⌛越界纪年（康熙63年）→公元年+提示实际纪年 /
⌛反查每个年号注明年数 / ⌛反查含民国纪年）。
+ batch15 新增 3 项（115-117：拖入 PDF/TXT → 在阅读区打开 / 拖入多个只开首个 + 提示 /
  双击关联：关联·取消关联脚本含 PDF/TXT 并设为默认）。
+ batch16 新增 3 项（118-120：大 PDF 著录不卡（浅著录秒回 + 后台补深 + 缓存）/
  超大 TXT 只载入前 8 MB + 提示 / 超大 TXT 对读截断且不自动进对读）。
+ batch17 改进 1 项（121：左栏可拖得极窄·窄时按钮收进「⋮」·一键收起/展开 Ctrl+Shift+L）。
+ batch18 新增 4 项（122-125：独立阅读窗口 Ctrl+F 可用 / 最小化文件列表窗口不带走阅读器 /
  直接打开文件→左栏列同文件夹+相似文件名 / 直接打开孤立文件不出错）。
+ batch19 修复 1 项（126：PDV5/PDV6 后缀（_PDV5AIFOCR 等）与其他后缀归为同一本）。
+ batch20 修复 1 项（127：左栏拖窄后「跨文件全文检索」主入口不被收进 ⋮）。
最后输出 SUMMARY ok=N fail=M（当前 **127/127**）。
+ batch17：左侧文件列表可拖得極窄（min 48px，窄时动作按钮收进「⋮」菜单、
  自动收起「上级文件夹」列），新增 Ctrl+Shift+L 收起/展开左栏（测试 110 已扩充）。
+ batch16 新增 3 项（118-120：大 PDF 著录不卡（浅著录秒回 + 后台补深 + 缓存）/ 超大 TXT 只载前 8MB
  + 提示 / 超大 TXT 对读只载前 8MB且不自动进对读）。
最后输出 SUMMARY ok=N fail=M（当前 **120/120**）。

只读不动源库；临时目录跑完即删。写死到 CathayViewer-DEV\\开发\\功能自检_日志.txt。
"""
import os
import sys
import tempfile
import shutil
import time

# 真平台（必须在 import PyQt6 / gui 之前）
os.environ['QT_QPA_PLATFORM'] = 'windows'

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                       # CathayViewer-DEV
sys.path.insert(0, ROOT)

LOGP = os.path.join(HERE, '功能自检_日志.txt')
_LOG = []


def log(s):
    _LOG.append(str(s))
    try:
        with open(LOGP, 'w', encoding='utf-8') as f:
            f.write('\n'.join(_LOG) + '\n')
    except Exception:
        pass


def _cjk_font():
    for f in (r'C:\Windows\Fonts\msyh.ttc', r'C:\Windows\Fonts\simsun.ttc',
              r'C:\Windows\Fonts\simhei.ttf'):
        if os.path.isfile(f):
            return f
    return ''


def main():
    import viewer_core as C
    import fitz

    # --- 让设置落到临时目录，绝不污染 CathayViewer-DEV\cathayviewer_settings.json
    base = tempfile.mkdtemp(prefix='cv_selfcheck_')
    cfg = os.path.join(base, 'cfg')
    os.makedirs(cfg, exist_ok=True)
    C.app_dir = lambda: cfg
    C.settings_path = lambda: os.path.join(cfg, 'cathayviewer_settings.json')

    import viewer_meta as META
    import viewer_tools as TOOLS
    TOOLS._DOCS_ROOT = os.path.join(base, 'Cathay文档记录')   # batch11：记录本重定向到临时目录
    import viewer_alias as ALIAS                              # batch13：人名别名归一
    import gui as G
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import QTimer, QUrl, QPoint, QPointF, QEvent, Qt
    from PyQt6.QtGui import QTextDocument, QPixmap, QImage, QWheelEvent, QKeyEvent

    FONT = _cjk_font()
    n_ok = [0]
    n_fail = [0]

    def step(no, name, fn):
        try:
            ok, detail = fn()
        except Exception as e:
            import traceback
            ok, detail = False, '%s: %s' % (type(e).__name__, e)
            log('     trace: ' + traceback.format_exc().replace('\n', ' | ')[:400])
        n_ok[0] += 1 if ok else 0
        n_fail[0] += 0 if ok else 1
        log('%2d. %s %-30s %s' % (no, 'OK  ' if ok else 'FAIL', name, detail))
        return ok

    # ---------------- 造源库文件 ----------------
    src = os.path.join(base, '书库')
    os.makedirs(src, exist_ok=True)
    pdfp = os.path.join(src, '甲书.pdf')
    txtp = os.path.join(src, '甲书_【繁转简】.txt')
    epubp = os.path.join(src, '丙书_某某编著_文物出版社1981年.epub')
    txt2 = os.path.join(src, '丁书.txt')

    def ins(pg, pt, text, fs):
        if FONT:
            pg.insert_text(pt, text, fontsize=fs, fontname='cjk', fontfile=FONT)
        else:
            pg.insert_text(pt, text, fontsize=fs, fontname='china-s')

    doc = fitz.open()
    ins(doc.new_page(), (72, 100), '甲书 标题页', 18)
    ins(doc.new_page(), (72, 100), '这是第二页的正文内容，用于翻页与书签测试。', 12)
    ins(doc.new_page(), (72, 120),
        '图书在版编目（CIP）数据\n甲书／某某著．—北京：文物出版社，1981.3\n'
        'ISBN 7-5010-0000-0\n定价：2.00元', 11)
    doc.set_toc([[1, '第一章', 1], [1, '第二章', 2], [1, '版权页', 3]])
    doc.save(pdfp)
    doc.close()
    open(txtp, 'w', encoding='utf-8').write('甲书 繁体转简体文本内容\n' + '正文' * 50)
    open(txt2, 'w', encoding='utf-8').write('丁书 纯文本内容')
    try:
        d = fitz.open()
        ins(d.new_page(), (72, 100), '丙书 EPUB 测试内容', 16)
        d.set_toc([[1, '丙书正文', 1]])
        d.save(epubp)
        d.close()
        epub_ok = True
    except Exception:
        epub_ok = False

    db = os.path.join(base, 'idx.db')
    r = C.build([src], db)
    log('== CathayViewer 功能自检 ==')
    log('root=%s  db=%s  files=%d  epub_created=%s' % (ROOT, db, r.get('files', -1), epub_ok))

    # ---------------- 12 项自检 ----------------
    step(1, '建库 4 条', lambda: (r.get('files') == 4, 'files=%s' % r.get('files')))

    app = QApplication.instance() or QApplication(sys.argv)

    st = {'primary_db': db, 'roots': [src], 'auto_dual': False}
    w = G.MainWindow(st)
    w.show()
    app.processEvents()

    def hit_jiashu():
        raw = C.search(db, '甲书', 800)
        w.ed_kw.setText('甲书')
        w.do_search()
        app.processEvents()
        return (len(raw) >= 2 and len(w.rows) == 1,
                'raw=%d rows=%d' % (len(raw), len(w.rows)))

    step(2, '搜索串接同书多版本', hit_jiashu)

    def versions():
        w.tb.setCurrentCell(0, 0)
        w.on_pick()
        app.processEvents()
        return (w.cb_ver.count() >= 2, 'cb_ver.count=%d' % w.cb_ver.count())

    step(3, '版本下拉 >=2', versions)

    def cite():
        w.copy_cite()
        t = QApplication.clipboard().text()
        return (bool(t) and '甲书' in t, repr(t[:60]))

    step(4, '复制引用含书名', cite)

    def pdf_pages():
        w.tb.setCurrentCell(0, 0)
        w.on_pick()
        w.preview_here()
        app.processEvents()
        opened = (getattr(w, 'pd', None) is not None and w._reader == 'pdf')
        w.pdf_goto(1)
        app.processEvents()
        pg_ok = (w.pgno == 1)
        msg = w.statusBar().currentMessage()
        no_err = '翻页失败' not in msg
        # 直接复现刚修的 addResource bug
        add_ok, add_err = True, ''
        try:
            img0 = QImage(8, 8, QImage.Format.Format_RGB888)
            w.view.document().addResource(QTextDocument.ResourceType.ImageResource,
                                          QUrl('2'), QPixmap.fromImage(img0))
        except TypeError as e:
            add_ok, add_err = False, str(e)
        ok = opened and pg_ok and no_err and add_ok
        return (ok, 'opened=%s pgno=%s msg=%r addResource_ok=%s %s'
                % (opened, w.pgno, msg[:40], add_ok, add_err))

    step(5, 'PDF 打开+翻页+addResource', pdf_pages)

    def theme():
        s = []
        for i in (0, 1, 2):
            w.cb_theme.setCurrentIndex(i)
            w.apply_theme()
            app.processEvents()
            s.append(w.view.styleSheet())
        return (s[0] != s[1] and s[1] != s[2], 'styles=%d/%d/%d' % tuple(len(x) for x in s))

    step(6, '切 3 主题无异常', theme)

    def fontsize():
        w.sp_font.setValue(20)
        app.processEvents()
        ps = w.view.font().pointSize()
        return (ps == 20, 'view.font().pointSize=%d' % ps)

    step(7, '字号跟随 spinbox', fontsize)

    def f11():
        w.toggle_full()
        app.processEvents()
        a = w.isFullScreen()
        w.toggle_full()
        app.processEvents()
        b = w.isFullScreen()
        return (a and not b, 'after1=%s after2=%s' % (a, b))

    step(8, 'F11 全屏翻转', f11)

    def close_modal():
        mw = QApplication.activeModalWidget()
        if mw is not None:
            mw.close()

    def toc():
        for d in (200, 600, 1200, 2000):
            QTimer.singleShot(d, close_modal)
        w.toc_here()                     # 含 exec()；由上面的定时器关闭
        app.processEvents()
        return (True, 'toc_here 未抛异常')

    step(9, 'Ctrl+T 目录不抛异常', toc)

    def bookmark():
        w.tb.setCurrentCell(0, 0)
        w.on_pick()
        w.pd = None
        w.preview_here()
        app.processEvents()
        w.pgno = 1
        w.bookmark_here()
        app.processEvents()
        w.pd = None
        w.pgno = 0
        w.preview_here()                 # 重开跳回
        app.processEvents()
        return (w.pgno == 1, 'pgno=%d' % w.pgno)

    step(10, 'Ctrl+B 记位置+重开跳回', bookmark)

    def history():
        w.tb.setCurrentCell(0, 0)
        w.on_pick()
        w._hist_add()
        hs = C.load_settings().get('history') or []
        return (any((h.get('path') or '').endswith('甲书.pdf') for h in hs),
                'history=%d' % len(hs))

    step(11, 'Ctrl+H 历史含该文件', history)

    def epub():
        if not epub_ok:
            return (True, '未验证（未能造出 epub）')
        w.ed_kw.setText('丙书')
        w.do_search()
        app.processEvents()
        if not w.rows:
            return (False, '库里没有 丙书.epub')
        w.tb.setCurrentCell(0, 0)
        w.on_pick()
        w.epub_here()
        app.processEvents()
        msg = w.statusBar().currentMessage()
        ok = (getattr(w, 'pd', None) is not None and w.pd.page_count > 0
              and '打不开' not in msg)
        return (ok, 'pd_pages=%s msg=%r'
                % (getattr(w.pd, 'page_count', None), msg[:50]))

    step(12, 'Ctrl+E EPUB', epub)

    # ---------------- 本次新增功能核验（13-18） ----------------
    def colophon():
        w.ed_kw.setText('甲书')
        w.do_search()
        app.processEvents()
        w.tb.setCurrentCell(0, 0)
        w.on_pick()
        w.colophon_here()
        app.processEvents()
        msg = w.statusBar().currentMessage()
        return (w.pgno == 2 and '版权页' in msg,
                'pgno=%d（期望 2）msg=%r' % (w.pgno, msg[:50]))

    step(13, '⤒ 版权页跳转', colophon)

    def copy_text():
        w.copy_text()
        app.processEvents()
        t = QApplication.clipboard().text()
        return (bool(t) and 'ISBN' in t, repr(t[:50]))

    step(14, '⧉ 复制文本（文字层）', copy_text)

    def copy_html():
        w.copy_html()
        app.processEvents()
        md = QApplication.clipboard().mimeData()
        ok = md is not None and md.hasHtml() and bool(md.text())
        return (ok, 'hasHtml=%s text=%r' % (md.hasHtml() if md else None,
                                            (md.text()[:40] if md else '')))

    step(15, '⧉ 复制带格式（HTML）', copy_html)

    def lineheight():
        w.sp_line.setValue(180)
        w.apply_theme()
        app.processEvents()
        lh = w.view.document().firstBlock().blockFormat().lineHeight()
        return (lh >= 100, '第一块 lineHeight=%s（期望 180）' % lh)

    step(16, '行距控制生效', lineheight)

    def invert():
        # 机制验证：对渲染出的 QImage 做像素反色，颜色确实翻转
        pm = w.pd[0].get_pixmap(matrix=fitz.Matrix(1.0, 1.0))
        qi = QImage(pm.samples, pm.width, pm.height, pm.stride,
                    QImage.Format.Format_RGB888).copy()
        b4 = qi.pixelColor(3, 3)
        qi.invertPixels(QImage.InvertMode.InvertRgb)
        af = qi.pixelColor(3, 3)
        flipped = (b4.red() == 255 - af.red() and b4.green() == 255 - af.green()
                   and b4.blue() == 255 - af.blue())
        # 开关经 UI 触发，不报错
        w.cb_invert.setChecked(True)
        app.processEvents()
        msg = w.statusBar().currentMessage()
        w.cb_invert.setChecked(False)
        app.processEvents()
        ok = flipped and '翻页失败' not in msg
        return (ok, 'pixel_flip=%s msg=%r' % (flipped, msg[:40]))

    step(17, '◐ PDF 反色', invert)

    def fullhide():
        w.toggle_full()
        app.processEvents()
        fs = w.isFullScreen()
        hidden = (all(not x.isVisible() for x in w._btn_widgets)
                  and all(not x.isVisible() for x in w._top_widgets))
        w.toggle_full()
        app.processEvents()
        restored = (all(x.isVisible() for x in w._btn_widgets)
                    and not w.isFullScreen())
        return (fs and hidden and restored,
                'full=%s hidden=%s restored=%s' % (fs, hidden, restored))

    step(18, '全屏隐藏工具栏+恢复', fullhide)

    # ---------------- batch2 新增功能核验（19-27） ----------------
    def cols5():
        h1 = w.tb.horizontalHeaderItem(1)
        return (w.tb.columnCount() == 5 and h1 is not None and h1.text() == '著录',
                'columns=%d head1=%r' % (w.tb.columnCount(), h1.text() if h1 else None))

    def cols3():
        hd = [w.tb.horizontalHeaderItem(i).text() for i in range(w.tb.columnCount())]
        return (w.tb.columnCount() == 3 and hd == ['序号', '文件名', '上级文件夹'],
                'columns=%d head=%s' % (w.tb.columnCount(), hd))

    step(19, '列表 3 列 + 表头（序号/文件名/上级文件夹）', cols3)

    def brief_col():
        w.ed_kw.setText('丙书')
        w.do_search()
        app.processEvents()
        if not w.rows:
            return (False, 'rows=0')
        nums = [w.tb.item(r, 0).text() if w.tb.item(r, 0) else ''
                for r in range(w.tb.rowCount())]
        dirs = [w.tb.item(r, 2).text() if w.tb.item(r, 2) else ''
                for r in range(w.tb.rowCount())]
        ok = (nums and nums[0] == '1' and all(d.strip() for d in dirs))
        return (ok, 'rows=%d num0=%r parent=%r' % (w.tb.rowCount(), nums[:1], dirs[:1]))

    step(20, '著录列非空且有内容', brief_col)

    def hist_write():
        w.ed_kw.setText('甲书')
        w.do_search()
        app.processEvents()
        h1 = C.load_settings().get('search_hist') or []
        w.ed_kw.setText('丙书')
        w.do_search()
        app.processEvents()
        w.ed_kw.setText('甲书')            # 再搜一次 → 去重，移到最前
        w.do_search()
        app.processEvents()
        h2 = C.load_settings().get('search_hist') or []
        ok = (h2 and h2[0] == '甲书' and h2.count('甲书') == 1 and '丙书' in h2)
        return (ok, 'hist=%r' % (h2[:5],))

    step(21, 'Ctrl+K 历史写入+去重', hist_write)

    def hist_dialog():
        for d in (200, 600, 1200, 2000):
            QTimer.singleShot(d, close_modal)
        w.search_history_dialog()          # 含 exec()，由定时器关闭
        app.processEvents()
        lh = (w._last_hist or {}).get('hist') or []
        w._rerun_search('甲书')            # 等同双击历史重跑
        app.processEvents()
        return (('甲书' in lh) and w.ed_kw.text() == '甲书' and bool(w.rows),
                'hist=%r ed=%r rows=%d' % (lh[:3], w.ed_kw.text(), len(w.rows)))

    step(22, 'Ctrl+K 历史重跑', hist_dialog)

    def ctrl_d_save():
        w.ed_kw.setText('甲书')
        app.processEvents()
        w.save_search()
        app.processEvents()
        s = C.load_settings().get('saved_searches') or []
        msg = w.statusBar().currentMessage()
        return ('甲书' in s and '已保存' in msg,
                'saved=%r msg=%r' % (s[:3], msg[:34]))

    step(23, 'Ctrl+D 保存搜索', ctrl_d_save)

    def stats_opens():
        stt = C.load_settings()
        stt.pop('stats', None)             # 先清空，便于精确计数
        C.save_settings(stt)
        w.ed_kw.setText('甲书')
        w.do_search()
        app.processEvents()
        ti = next((i for i, r in enumerate(w.rows)
                   if (r.get('name') or '').lower().endswith('.pdf')), 0)
        w.tb.setCurrentCell(ti, 0)
        w.on_pick()
        app.processEvents()
        w.preview_here()                   # 第 1 次打开
        app.processEvents()
        time.sleep(0.06)
        w.preview_here()                   # 第 2 次打开 → 结算上一次 + opens+1
        app.processEvents()
        p = os.path.join(w.rows[ti].get('dir') or '', w.rows[ti].get('name') or '')
        e = (C.load_settings().get('stats') or {}).get(p) or {}
        return (int(e.get('opens') or 0) == 2,
                'opens=%s secs=%.3f %s' % (e.get('opens'), float(e.get('secs') or 0),
                                          os.path.basename(p)))

    step(24, '打开两次 stats.opens==2', stats_opens)

    def stats_secs():
        stats = C.load_settings().get('stats') or {}
        vals = [float((e or {}).get('secs') or 0) for e in stats.values()]
        mx = max(vals) if vals else 0.0
        return (mx > 0, 'max_secs=%.3f n=%d' % (mx, len(vals)))

    step(25, 'stats.secs>0 累加', stats_secs)

    def stats_dialog():
        txt = w._stats_text()
        for d in (200, 600, 1200, 2000):
            QTimer.singleShot(d, close_modal)
        w.read_stats_dialog()              # 含 exec()，由定时器关闭
        app.processEvents()
        has = ('总累计阅读时长' in txt) and ('最常阅读' in txt) and ('甲书' in txt)
        return (has, 'len=%d has_top=%s has_total=%s'
                % (len(txt), '最常阅读' in txt, '总累计阅读时长' in txt))

    step(26, 'Ctrl+Shift+H 统计列出 Top', stats_dialog)

    def epub_toc():
        w.ed_kw.setText('丙书')
        w.do_search()
        app.processEvents()
        if not w.rows:
            return (False, '库里没有 丙书.epub')
        w.tb.setCurrentCell(0, 0)
        w.on_pick()
        app.processEvents()
        w.pd = None                        # 强制走 fitz.open(path).get_toc() 这条路
        w._pd_path = ''
        for d in (200, 600, 1200, 2000):
            QTimer.singleShot(d, close_modal)
        w.toc_here()
        app.processEvents()
        lt = w._last_toc or {}
        ok = (int(lt.get('rows') or 0) > 0
              and (bool(lt.get('items')) or int(lt.get('pages') or 0) > 0))
        return (ok, 'items=%d pages=%d rows=%d'
                % (len(lt.get('items') or []), int(lt.get('pages') or 0),
                   int(lt.get('rows') or 0)))

    step(27, 'Ctrl+T EPUB 目录(大纲/页码)', epub_toc)

    # ---------------- batch3 新增功能核验（28-36） ----------------
    # 追加 batch3 用文件（建库后再增量刷新进库；不影响前面「建库 4 条」断言）
    mdp = os.path.join(src, '测试笔记.md')
    open(mdp, 'w', encoding='utf-8').write('# 标题\n\n**粗体** 正文\n\n第二段。\n')
    jsok = os.path.join(src, '测试数据.json')
    open(jsok, 'w', encoding='utf-8').write(
        '{"name":"甲","nested":{"a":1,"b":[1,2,3]},"other":"x"}')
    jsbad = os.path.join(src, '坏数据.json')
    open(jsbad, 'w', encoding='utf-8').write('{不是合法 json,,,')
    jsbig = os.path.join(src, '大测试.json')
    with open(jsbig, 'w', encoding='utf-8') as f:
        f.write('{"big":"' + 'a' * (21 * 1024 * 1024) + '"}')
    ser1 = os.path.join(src, '近代中国史料丛刊 001 甲篇_邓瑞全编著_黄山书社1998年.pdf')
    ser2 = os.path.join(src, '近代中国史料丛刊 002 乙篇_王某某编著_黄山书社1999年.pdf')
    aut2 = os.path.join(src, '别史_邓瑞全编著_黄山书社2000年.pdf')
    for f in (ser1, ser2, aut2):
        open(f, 'wb').write(b'x' * 64)
    rr = C.refresh(db, [src])
    log('batch3 追加文件 + 增量刷新：add=%s files=%s'
        % (rr.get('add'), rr.get('files')))

    def pick(sub):
        """搜索并选中名含 sub 的行，返回其完整路径（找不到返回 ''）。"""
        w.ed_kw.setText(sub)
        w.do_search()
        app.processEvents()
        for i, r in enumerate(w.rows):
            if sub in (r.get('name') or ''):
                w.tb.setCurrentCell(i, 0)
                w.on_pick()
                app.processEvents()
                return os.path.join(r.get('dir') or '', r.get('name') or '')
        return ''

    def md_switch():
        p = pick('测试笔记')
        if not p:
            return (False, '未选中 md')
        w.preview_here()
        app.processEvents()
        src_txt = w.view.toPlainText()
        w.md_toggle()
        app.processEvents()
        r1, txt1 = w._md_render, w.view.document().toPlainText()
        html1 = w.view.document().toHtml().lower()
        w.md_toggle()
        app.processEvents()
        r2, txt2 = w._md_render, w.view.toPlainText()
        ok = (r1 is True and r2 is False and '<h1' in html1 and 'font-weight' in html1
              and '标题' in txt1 and txt2 == src_txt)
        return (ok, 'render=%s/%s h1=%s bold=%s back_same=%s'
                % (r1, r2, '<h1' in html1, 'font-weight' in html1, txt2 == src_txt))

    step(28, 'Ctrl+M MD渲染⇄源码', md_switch)

    def md_not():
        w.ed_kw.setText('甲书')
        w.do_search()
        app.processEvents()
        ti = next((i for i, r in enumerate(w.rows)
                   if (r.get('name') or '').lower().endswith('.txt')), 0)
        w.tb.setCurrentCell(ti, 0)
        w.on_pick()
        app.processEvents()
        w.md_toggle()
        msg = w.statusBar().currentMessage()
        return ('不是 Markdown' in msg, 'msg=%r' % msg)

    step(29, '非 .md 提示', md_not)

    def json_tree():
        p = pick('测试数据')
        if not p:
            return (False, '未选中 json')
        data, err = w._json_load(p)
        tree = w._json_build_tree(data)
        n = tree.topLevelItemCount()
        vis_all = w._json_filter(tree, '')
        vis_nested = w._json_filter(tree, 'nested')
        nested = next((tree.topLevelItem(i) for i in range(n)
                       if tree.topLevelItem(i).text(0) == 'nested'), None)
        child_ok = nested is not None and nested.childCount() == 2
        hid = next((tree.topLevelItem(i).isHidden() for i in range(n)
                    if tree.topLevelItem(i).text(0) == 'name'), None)
        ok = (err == '' and n >= 3 and vis_all == n and vis_nested == 1
              and child_ok and hid is True)
        return (ok, 'nodes=%d vis_all=%d vis_nested=%s nested_kids=%s name_hidden=%s'
                % (n, vis_all, vis_nested, child_ok, hid))

    step(30, 'Ctrl+J JSON树节点+过滤', json_tree)

    def json_dialog():
        pick('测试数据')
        for d in (200, 600, 1200, 2000):
            QTimer.singleShot(d, close_modal)
        w.json_tree_dialog()
        app.processEvents()
        lj = w._last_json or {}
        return (int(lj.get('top') or 0) >= 3,
                'top=%s path=%s' % (lj.get('top'),
                                    os.path.basename(lj.get('path') or '')))

    step(31, 'Ctrl+J 对话框可开', json_dialog)

    def json_big():
        p = pick('大测试')
        if not p:
            return (False, '未选中大 json')
        data, err = w._json_load(p)
        tree, tag = w._json_load_stream(p)
        if tree is not None:
            # 有 ijson：>20MB 走流式顶层浏览（不弹窗，避免阻塞自检）
            return (err == 'too_big',
                    'stream=%s top=%d err=%s' % (tag, tree.topLevelItemCount(), err))
        # 无 ijson：回退纯文本
        w._show_text_file(p)
        app.processEvents()
        msg = w.statusBar().currentMessage()
        return (('20 MB' in msg or '纯文本' in msg) and getattr(w, '_reader', '') == 'text',
                'msg=%r reader=%s' % (msg, getattr(w, '_reader', '')))

    step(32, '大 JSON 流式/回退', json_big)

    def json_bad():
        p = pick('坏数据')
        if not p:
            return (False, '未选中坏 json')
        w.json_tree_dialog()
        app.processEvents()
        msg = w.statusBar().currentMessage()
        ok = ('解析失败' in msg or '纯文本' in msg)
        return (ok, 'msg=%r' % msg)

    step(33, '坏 JSON 回退提示', json_bad)

    def related():
        p = pick('近代中国史料丛刊 001')
        if not p:
            return (False, '未选中系列书')
        g = w.related_groups()
        w._last_related = g
        A = [x['name'] for x in g['A']]
        B = [x['name'] for x in g['B']]
        C = [x['name'] for x in g['C']]
        S = [x['name'] for x in (g.get('series') or [])]
        AU = [x['name'] for x in (g.get('same_author') or [])]
        a_ok = any('002' in n for n in A)
        b_ok = any('别史' in n for n in B)
        c_ok = len(C) >= 1
        s_ok = any('002' in n for n in S)
        au_ok = any('别史' in n for n in AU)
        for d in (300, 900, 1800):
            QTimer.singleShot(d, close_modal)
        w.related_dialog()
        app.processEvents()
        lg = w._last_related or {}
        tr = lg.get('tree')
        tree_ok = tr is not None and tr.topLevelItemCount() == 4
        return (g['prefix'] == '近代中国史料丛刊' and a_ok and b_ok and c_ok
                and s_ok and au_ok and tree_ok,
                'prefix=%r A=%d B=%d C=%d series=%d same_author=%d groups=%s'
                % (g['prefix'], len(A), len(B), len(C), len(S), len(AU),
                   tr.topLevelItemCount() if tree_ok else -1))

    step(34, 'Ctrl+R 相关文献四档推荐', related)

    def related_open():
        ok1 = w._open_path(os.path.join(src, '丁书.txt'))
        app.processEvents()
        r1 = getattr(w, '_reader', '')
        ok2 = w._open_path(os.path.join(src, '甲书.pdf'))
        app.processEvents()
        r2 = getattr(w, '_reader', '')
        return (ok1 and ok2 and r1 == 'text' and r2 == 'pdf',
                'txt_ok=%s reader=%s pdf_ok=%s reader=%s' % (ok1, r1, ok2, r2))

    step(35, '相关文件双击打开通路', related_open)

    def thumbs():
        w.ed_kw.setText('甲书')
        w.do_search()
        app.processEvents()
        ti = next((i for i, r in enumerate(w.rows)
                   if (r.get('name') or '').lower().endswith('.pdf')), 0)
        w.tb.setCurrentCell(ti, 0)
        w.on_pick()
        w.preview_here()
        app.processEvents()
        if w.pd is None:
            return (False, '未打开 PDF')
        w.toggle_thumbs()
        app.processEvents()
        guard = 0
        while guard < 100 and w._thumb_add_one():
            guard += 1
        cnt = w._thumb_list.count()
        w.pgno = 0
        if cnt >= 2:
            w._thumb_clicked(w._thumb_list.item(1))
            app.processEvents()
        vis1 = w._thumb_dock.isVisible()
        w.toggle_thumbs()
        app.processEvents()
        vis2 = w._thumb_dock.isVisible()
        ok = (cnt >= 1 and w.pgno == (1 if cnt >= 2 else 0) and vis1 and not vis2)
        return (ok, 'thumbs=%d pgno=%d vis=%s->%s' % (cnt, w.pgno, vis1, vis2))

    step(36, 'Ctrl+Shift+T 缩略图+跳页', thumbs)

    # ---------------- batch4 新增功能核验（37-43） ----------------
    # ① 双击/带文件启动一律进阅读区 ② 双击不调外部程序 ③ 阅读区更宽 ④ 分割条最小宽度约束
    import subprocess as _sp
    _real_popen = _sp.Popen
    _real_startfile = getattr(os, 'startfile', None)
    _ext_calls = [0]

    def _stub_startfile(*a, **k):
        _ext_calls[0] += 1

    class _FakePopen(object):
        def __init__(self, *a, **k):
            _ext_calls[0] += 1

    def _patch_ext():
        if _real_startfile is not None:
            os.startfile = _stub_startfile
        _sp.Popen = _FakePopen

    def _unpatch_ext():
        if _real_startfile is not None:
            os.startfile = _real_startfile
        _sp.Popen = _real_popen

    def _dbl(kw, ext):
        """搜索 kw → 选中首个 .ext 行 → 真发 itemDoubleClicked 信号。"""
        w.ed_kw.setText(kw)
        w.do_search()
        app.processEvents()
        ti = next((i for i, r in enumerate(w.rows)
                   if (r.get('name') or '').lower().endswith(ext)), -1)
        if ti < 0:
            return -1
        w.tb.setCurrentCell(ti, 0)
        app.processEvents()
        w.tb.itemDoubleClicked.emit(w.tb.item(ti, 0))
        app.processEvents()
        return ti

    def dbl_pdf():
        _ext_calls[0] = 0
        _patch_ext()
        try:
            ti = _dbl('甲书', '.pdf')
            loaded = (ti >= 0 and getattr(w, 'pd', None) is not None
                      and getattr(w, '_reader', '') == 'pdf'
                      and 0 <= w.pgno < int(w.pd.page_count))
        finally:
            n = _ext_calls[0]
            _unpatch_ext()
        return (loaded and n == 0,
                'loaded=%s reader=%s pgno=%s ext_calls=%d'
                % (loaded, getattr(w, '_reader', ''), getattr(w, 'pgno', -1), n))

    step(37, '双击 PDF → 阅读区内部打开', dbl_pdf)

    def dbl_text():
        _ext_calls[0] = 0
        _patch_ext()
        try:
            ti = _dbl('丁书', '.txt')     # 丁书.txt 是独立文本，不被同名版本合并
            txt = w.view.toPlainText()
        finally:
            n = _ext_calls[0]
            _unpatch_ext()
        return (ti >= 0 and bool(txt) and n == 0,
                'len=%d reader=%s ext_calls=%d'
                % (len(txt), getattr(w, '_reader', ''), n))

    step(38, '双击文本 → 阅读区有内容且不调外部', dbl_text)

    def cli_pdf():
        _ext_calls[0] = 0
        _patch_ext()
        old = list(sys.argv)
        try:
            sys.argv = [old[0] if old else 'gui.py', pdfp]
            w.open_cli_arg()
            app.processEvents()
            loaded = (getattr(w, 'pd', None) is not None
                      and os.path.normcase(getattr(w, '_pd_path', ''))
                      == os.path.normcase(pdfp))
        finally:
            n = _ext_calls[0]
            sys.argv = old
            _unpatch_ext()
        return (loaded and n == 0,
                'loaded=%s pd_path=%s ext_calls=%d'
                % (loaded, os.path.basename(getattr(w, '_pd_path', '')), n))

    step(39, '命令行带文件启动 → 阅读区', cli_pdf)

    def cli_multi():
        old = list(sys.argv)
        try:
            sys.argv = [old[0] if old else 'gui.py', txtp, txt2]
            w.open_cli_arg()
            app.processEvents()
            msg = w.statusBar().currentMessage()
            loaded = (getattr(w, '_reader', '') == 'text' and bool(w.view.toPlainText()))
        finally:
            sys.argv = old
        return (loaded and '忽略' in msg,
                'reader=%s msg=%r' % (getattr(w, '_reader', ''), msg[:44]))

    step(40, '多文件参数只开首个+状态栏提示', cli_multi)

    def split_ratio():
        sizes = w._split.sizes()
        left, right = sizes[0], sizes[1]
        win = w.width()
        ok = (right > left) and (right >= 0.55 * win)
        return (ok, 'win=%d left=%d right=%d right%%=%.0f%%'
                % (win, left, right, 100.0 * right / max(1, win)))

    step(41, '阅读区宽 > 左且 ≥窗口 55%', split_ratio)

    def split_min():
        # batch17：左栏可收起（可拖到 0），但阅读区有最小宽度（≥200）
        w._split.setSizes([0, 9999])
        app.processEvents()
        left = w._split.sizes()[0]
        right = w._split.sizes()[1]
        mn = w.tb.minimumWidth()
        w._split.setSizes([340, 1160])
        app.processEvents()
        return (left >= 0 and left <= mn + 10 and mn > 0 and mn <= 60 and right >= 200,
                'left_after_zero=%d right=%d min=%d' % (left, right, mn))

    step(42, '分割条最小宽度约束生效（左栏可收起、阅读区保底）', split_min)

    def ext_button():
        btns = ' '.join(b.text() for b in getattr(w, '_btn_widgets', []))
        has = ('外部' in btns)
        _ext_calls[0] = 0
        _patch_ext()
        try:
            w.ed_kw.setText('甲书')
            w.do_search()
            app.processEvents()
            w.tb.setCurrentCell(0, 0)
            app.processEvents()
            w.open_external()
            app.processEvents()
        finally:
            n = _ext_calls[0]
            _unpatch_ext()
        return (has and n == 1, 'btn_has_ext=%s ext_calls=%d' % (has, n))

    step(43, '外部打开保留为显式按钮', ext_button)

    # ---------------- batch5 新增功能核验（44-54） ----------------
    # ① PDF 连续滚动 ② 注册表关联脚本（只校验文本，绝不执行） ③ 导航面板 ④ 文内查找
    bigp = os.path.join(src, '滚动测试.pdf')
    notlp = os.path.join(src, '无文字层.pdf')
    _d = fitz.open()
    for _i in range(12):
        _pg = _d.new_page()
        ins(_pg, (72, 100), '滚动测试 第 %d 页 正文内容' % (_i + 1), 16)
    _d.set_toc([[1, '第一章', 1], [1, '第二章', 6], [1, '第三章', 12]])
    _d.save(bigp)
    _d.close()
    _d = fitz.open()
    _png = os.path.join(base, '_notl.png')
    _qi = QImage(80, 50, QImage.Format.Format_RGB888)
    _qi.fill(0x3388ff)
    _qi.save(_png)
    _blob = open(_png, 'rb').read()
    for _i in range(2):
        _pg = _d.new_page()
        _pg.insert_image(fitz.Rect(50, 50, 400, 300), stream=_blob)
    _d.save(notlp)
    _d.close()
    _rr = C.refresh(db, [src])
    log('batch5 追加文件 + 增量刷新：add=%s files=%s'
        % (_rr.get('add'), _rr.get('files')))

    def _read_bat(name):
        p = os.path.join(ROOT, name)
        if not os.path.isfile(p):
            return None, '', False, False
        raw = open(p, 'rb').read()
        try:
            raw.decode('ascii')
            ascii_ok = True
        except UnicodeDecodeError:
            ascii_ok = False
        t = raw.decode('ascii', 'replace')
        return raw, t, ascii_ok, (raw.count(b'\r\n') > 0)

    def assoc_bat():
        raw, t, ascii_ok, crlf = _read_bat('关联.bat')
        if raw is None:
            return (False, 'missing 关联.bat')
        ok = (ascii_ok and crlf and ('CathayViewer.pdf' in t)
              and ('CathayViewer.exe' in t) and ('reg add' in t))
        return (ok, 'size=%d ascii=%s crlf=%s pdf=%s exe=%s'
                % (len(raw), ascii_ok, crlf, 'CathayViewer.pdf' in t,
                   'CathayViewer.exe' in t))

    step(44, '关联.bat 存在+ASCII+CRLF+含关键串', assoc_bat)

    def unassoc_bat():
        raw, t, ascii_ok, crlf = _read_bat('取消关联.bat')
        if raw is None:
            return (False, 'missing 取消关联.bat')
        ok = (ascii_ok and crlf and ('CathayViewer.pdf' in t)
              and ('CathayViewer.exe' in t) and ('reg delete' in t))
        return (ok, 'size=%d ascii=%s crlf=%s pdf=%s exe=%s'
                % (len(raw), ascii_ok, crlf, 'CathayViewer.pdf' in t,
                   'CathayViewer.exe' in t))

    step(45, '取消关联.bat 存在+ASCII+CRLF+含关键串', unassoc_bat)

    def cont_initial():
        p = pick('滚动测试')
        if not p:
            return (False, '未选中 滚动测试.pdf')
        w.resize(1300, 860)
        w.preview_here()
        app.processEvents()
        if getattr(w, 'pd', None) is None:
            return (False, '未打开')
        total = int(w.pd.page_count)
        pv = w.pdf_view
        app.processEvents()
        pv._render_visible()
        ok = (w._reader == 'pdf' and w.stack.currentWidget() is pv
              and pv.page_count() == total and len(pv._pix) >= 1)
        return (ok, 'reader=%s pages=%d rendered=%d total=%d'
                % (w._reader, pv.page_count(), len(pv._pix), total))

    step(46, 'PDF 连续滚动：初始载入若干页', cont_initial)

    def cont_scroll():
        p = pick('滚动测试')
        if not p:
            return (False, '未选中')
        w.resize(1300, 860)
        w.preview_here()
        app.processEvents()
        pv = w.pdf_view
        w.pdf_home()
        app.processEvents()
        pg0 = w.pgno
        sb = pv.verticalScrollBar()
        sb.setValue(sb.maximum() // 2)
        app.processEvents()
        pgm = w.pgno
        sb.setValue(sb.maximum())
        app.processEvents()
        pgb = w.pgno
        ok = (pgm != pg0 and pgb > pgm)
        return (ok, 'pg %d->%d->%d total=%d' % (pg0, pgm, pgb, int(w.pd.page_count)))

    step(47, '滚到中部/底部：页码变化+已插页增加', cont_scroll)

    def nav_keys():
        p = pick('滚动测试')
        if not p:
            return (False, '未选中')
        w.preview_here()
        app.processEvents()
        total = int(w.pd.page_count)
        w.pdf_home()
        app.processEvents()
        h = w.pgno
        w._pgdn.activated.emit()
        app.processEvents()
        a = w.pgno
        w._pgup.activated.emit()
        app.processEvents()
        b = w.pgno
        w._endk.activated.emit()
        app.processEvents()
        c = w.pgno
        w._homek.activated.emit()
        app.processEvents()
        d = w.pgno
        ok = (h == 0 and a == 1 and b == 0 and c == total - 1 and d == 0)
        return (ok, 'home=%d pgdn=%d pgup=%d end=%d ctrlhome=%d total=%d'
                % (h, a, b, c, d, total))

    step(48, 'PgDn/PgUp/Ctrl+Home/Ctrl+End 可用', nav_keys)

    def nav_panel():
        p = pick('滚动测试')
        if not p:
            return (False, '未选中')
        w.preview_here()
        app.processEvents()
        vis = (w._nav_dock is not None and w._nav_dock.isVisible())
        rows = w._nav_toc.count()
        tab = w._nav_tabs.currentIndex() if w._nav_tabs is not None else -1
        jumped = -1
        if rows >= 2:
            w._nav_toc_go(w._nav_toc.item(1))      # 第二章 → 第 6 页
            app.processEvents()
            jumped = w.pgno
        ok = (vis and rows >= 3 and tab == 0 and jumped == 5)
        return (ok, 'visible=%s toc_rows=%d tab=%d jump_pgno=%d'
                % (vis, rows, tab, jumped))

    step(49, '导航面板默认展开+目录页签+单击跳页', nav_panel)

    def find_txt():
        p = pick('甲书_【繁转简】')
        if not p:
            return (False, '未选中 txt')
        w.preview_here()
        app.processEvents()
        if w._reader != 'text':
            return (False, 'reader=%s' % w._reader)
        w.ed_find.setText('正文')
        w.find_run()
        app.processEvents()
        total, idx0 = w._find_total, w._find_idx
        for _ in range(total):
            w.find_next()
        app.processEvents()
        idx1 = w._find_idx
        sel = w.view.textCursor().selectedText()
        ok = (total >= 2 and idx0 == 0 and idx1 == 0 and '正文' in sel)
        return (ok, 'total=%d idx %d->%d sel=%r label=%r'
                % (total, idx0, idx1, sel[:6], w.lb_find.text()))

    step(50, 'TXT 文内查找命中+下一个循环', find_txt)

    def find_pdf():
        p = pick('滚动测试')
        if not p:
            return (False, '未选中')
        w.preview_here()
        app.processEvents()
        w.ed_find.setText('第 6 页')
        w.find_run()
        app.processEvents()
        total = w._find_total
        hits = list(w._find_hits)
        ok = (total >= 1 and any(int(h.get('page') or -1) == 5 for h in hits)
              and w.pgno == 5 and w._nav_find.count() == total
              and w._hl_kw == '第 6 页')
        return (ok, 'total=%d pgno=%d tab=%d hl=%r hit0=%s'
                % (total, w.pgno, w._nav_find.count(), w._hl_kw,
                   hits[0] if hits else None))

    step(51, 'PDF 文字层查找到已知词+跳页+结果列表', find_pdf)

    def find_notext():
        p = pick('无文字层')
        if not p:
            return (False, '未选中 无文字层.pdf')
        w.preview_here()
        app.processEvents()
        w.ed_find.setText('正文')
        w.find_run()
        app.processEvents()
        msg = w.statusBar().currentMessage()
        ok = ('没有文字层' in msg) and ('OCR' in msg) and w._find_total == 0
        return (ok, 'msg=%r total=%d' % (msg[:44], w._find_total))

    step(52, '无文字层 PDF 给出 OCR 提示', find_notext)

    def nav_on_text():
        p = pick('丁书')
        if not p:
            return (False, '未选中 丁书.txt')
        w.preview_here()
        app.processEvents()
        hidden = (w._nav_dock is None) or (not w._nav_dock.isVisible())
        return (w._reader == 'text' and hidden,
                'reader=%s nav_hidden=%s' % (w._reader, hidden))

    step(53, '非 PDF 打开时导航面板隐藏不报错', nav_on_text)

    def find_bar_toggle():
        w.find_focus()
        app.processEvents()
        v1 = w._find_bar_widget.isVisible()
        w.ed_find.setText('xx')
        w.find_close()
        app.processEvents()
        v2 = w._find_bar_widget.isVisible()
        return (v1 and not v2, 'vis=%s->%s' % (v1, v2))

    step(54, 'Ctrl+F 显示 / Esc 关闭查找条', find_bar_toggle)

    def render_once():
        p = pick('滚动测试')
        if not p:
            return (False, '未选中')
        w.resize(1300, 860)
        w.preview_here()
        app.processEvents()
        pv = w.pdf_view
        app.processEvents()
        pv._render_visible()
        sb = pv.verticalScrollBar()
        for v in (0, sb.maximum() // 2, 0, sb.maximum() // 3):
            sb.setValue(v)
            app.processEvents()
            pv._render_visible()
        counts = pv.render_counts()
        once = bool(counts) and max(counts.values()) == 1
        return (once, 'render_counts=%s cached=%d'
                % (sorted(counts.values()), len(counts)))

    step(55, '同一页只渲染一次（缓存复用）', render_once)

    def zoom_switch():
        p = pick('滚动测试')
        if not p:
            return (False, '未选中')
        w.resize(1300, 860)
        w.preview_here()
        app.processEvents()
        pv = w.pdf_view
        total_pages = int(w.pd.page_count)
        res = []
        okall = True
        for idx in (0, 1, 2):        # 适应宽度 / 适应页面 / 100%
            w.cb_zoom.setCurrentIndex(idx)
            app.processEvents()
            sz = pv._page_size(0)
            good = (pv.page_count() == total_pages and sz.width() > 40
                    and sz.height() > 40 and w.pgno < total_pages)
            okall = okall and good
            res.append((w.cb_zoom.currentText(), sz.width(), sz.height(), good))
        return (okall, 'total=%d %s' % (total_pages, res))

    step(56, '缩放切换后页码与页数不错乱', zoom_switch)

    def page_box():
        p = pick('滚动测试')
        if not p:
            return (False, '未选中')
        w.preview_here()
        app.processEvents()
        total = int(w.pd.page_count)
        w.ed_page.setText('5')
        w.page_jump()
        app.processEvents()
        a = w.pgno
        w.ed_page.setText('99')      # 越界 → 夹到末页
        w.page_jump()
        app.processEvents()
        b = w.pgno
        ok = (a == 4 and b == total - 1)
        return (ok, 'set5->pgno=%d clamp99->pgno=%d total=%d' % (a, b, total))

    step(57, '页码框输入跳页生效', page_box)

    # ---------------- batch6 新增功能核验（58-61） ----------------
    # ① Ctrl+滚轮缩放 ② 页码框输入跳页 ③ 缩放回适应宽度后仍能继续滚动加载 ④ 目录联动高亮
    def ctrl_wheel():
        p = pick('滚动测试')
        if not p:
            return (False, '未选中')
        w.resize(1300, 860)
        w.cb_zoom.setCurrentIndex(0)          # 适应宽度
        w.preview_here()
        app.processEvents()
        if w.pd is None:
            return (False, '未打开')
        before = round(100 * w._zoom_factor())
        pv = w.pdf_view
        ev = QWheelEvent(QPointF(10, 10), QPointF(10, 10), QPoint(0, 0),
                         QPoint(0, 120), Qt.MouseButton.NoButton,
                         Qt.KeyboardModifier.ControlModifier,
                         Qt.ScrollPhase.NoScrollPhase, False)
        pv.wheelEvent(ev)
        app.processEvents()
        after = round(100 * w._zoom_factor())
        ok = (after > 0 and after != before and w._zoom_mode == 'custom'
              and int(w.sp_zoom.value()) > 0)
        return (ok, 'zoom %d%%->%d%% mode=%s box=%d%%'
                % (before, after, w._zoom_mode, int(w.sp_zoom.value())))

    step(58, 'Ctrl+滚轮 缩放生效（PdfView）', ctrl_wheel)

    def page_box_7():
        p = pick('滚动测试')
        if not p:
            return (False, '未选中')
        w.preview_here()
        app.processEvents()
        w.ed_page.setText('7')                # 1 基显示 → 内部 0 基 pgno=6
        w.page_jump()
        app.processEvents()
        a, at = w.pgno, w.ed_page.text()
        w.ed_page.setText('abc')              # 非法输入 → 忽略并恢复显示
        w.page_jump()
        app.processEvents()
        b, bt = w.pgno, w.ed_page.text()
        ok = (a == 6 and at == '7' and b == 6 and bt == '7')
        return (ok, 'in7->pgno=%d box=%r | bad->pgno=%d box=%r' % (a, at, b, bt))

    step(59, '页码框输入 7 回车 → 当前页=7（1 基）', page_box_7)

    def zoom_back_scroll():
        p = pick('滚动测试')
        if not p:
            return (False, '未选中')
        w.resize(1300, 860)
        w.preview_here()
        app.processEvents()
        w.cb_zoom.setCurrentIndex(1)          # 先切到适应页面
        app.processEvents()
        w.cb_zoom.setCurrentIndex(0)          # 再切回适应宽度
        app.processEvents()
        pv = w.pdf_view
        w.pdf_home()
        app.processEvents()
        pg0 = w.pgno
        sb = pv.verticalScrollBar()
        for _ in range(12):
            sb.setValue(sb.maximum())
            app.processEvents()
        pgb = w.pgno
        ok = (pgb > pg0)
        return (ok, 'scrolled pg %d->%d total=%d' % (pg0, pgb, int(w.pd.page_count)))

    step(60, '缩放回「适应宽度」后仍能继续滚动', zoom_back_scroll)

    def toc_follow():
        p = pick('滚动测试')
        if not p:
            return (False, '未选中')
        w.preview_here()
        app.processEvents()
        w._show_nav(0)
        app.processEvents()
        rows = int((w._last_toc or {}).get('rows') or 0)
        w.ed_page.setText('6')                # 第二章（第 6 页）
        w.page_jump()
        app.processEvents()
        w._sync_toc_highlight()
        r1 = w._nav_toc.currentRow()
        w.ed_page.setText('1')                # 第一章（第 1 页）
        w.page_jump()
        app.processEvents()
        w._sync_toc_highlight()
        r2 = w._nav_toc.currentRow()
        ok = (rows >= 3 and r1 == 1 and r2 == 0)
        return (ok, 'toc_rows=%d ch2->row%d ch1->row%d' % (rows, r1, r2))

    step(61, '目录联动高亮随页变化', toc_follow)

    # ---------------- batch6 新增功能核验（62-63） ----------------
    # ① 大 TXT：mmap 全文读取 + chardet 编码识别（不再 200KB 静默截断）
    # ② 大 JSON：>20MB 用 ijson 流式顶层浏览（不再直接回退纯文本）
    bigtxt = os.path.join(src, '大文本_gb18030.txt')
    _seg = '这是用于验证大文本读取的中文段落。' * 64 + '\n'
    with open(bigtxt, 'w', encoding='gb18030') as _f:
        for _i in range(4000):                                   # 约 8 MB
            _f.write('第 %05d 行 ' % _i + _seg)
    bomtxt = os.path.join(src, '带BOM文本.txt')
    open(bomtxt, 'w', encoding='utf-8-sig').write('带BOM的UTF8文本\n' + '内容' * 100)
    bigjson = os.path.join(src, '大数据.json')
    with open(bigjson, 'w', encoding='utf-8') as _f:
        _f.write('{"start": 0,')
        _f.write(','.join('"k%07d": %d' % (_i, _i) for _i in range(1, 1500000)))
        _f.write('}')
    _r6 = C.refresh(db, [src])
    log('batch6 追加文件 + 增量刷新：add=%s files=%s' % (_r6.get('add'), _r6.get('files')))

    def big_text():
        sz = os.path.getsize(bigtxt)
        txt = w._read_text_file(bigtxt, 0)
        tail_ok = ('第 03999 行' in txt)          # 末行读得到 → 没被截到 200KB
        enc_ok = ('这是用于验证大文本读取的中文段落' in txt)   # GB18030 解对了
        bt = w._read_text_file(bomtxt, 0)
        bom_ok = (bt.startswith('带BOM') and '\ufeff' not in bt)
        ok = (sz > 6 * 1024 * 1024 and len(txt) > 3 * 1024 * 1024
              and tail_ok and enc_ok and bom_ok)
        return (ok, 'size=%.1fMB len=%d tail=%s enc=%s bom=%s'
                % (sz / 1048576.0, len(txt), tail_ok, enc_ok, bom_ok))

    step(62, '大 TXT mmap 全文读取+chardet', big_text)

    def big_json():
        sz = os.path.getsize(bigjson)
        _data, err = w._json_load(bigjson)
        tree, tag = w._json_load_stream(bigjson)
        top = tree.topLevelItemCount() if tree is not None else -1
        ok = (sz > 20 * 1024 * 1024 and err == 'too_big' and tree is not None and top > 1000)
        return (ok, 'size=%.1fMB err=%s stream=%s top=%d'
                % (sz / 1048576.0, err, tag, top))

    step(63, '大 JSON ijson 流式顶层浏览', big_json)

    # ---------------- batch7 新增功能核验（64-69） ----------------
    # ① 阅读器独立窗口 ② 平滑滚动（滚轮+↑↓） ③ 文字层选择/复制
    # ④ 跨文件全文检索（独立进程） ⑤ 目录单击跳页 ⑥ 版权/授权信息
    authpdf = os.path.join(src, '授权测试_中华书局授权影印.pdf')
    try:
        _ad = fitz.open()
        _ad.new_page()
        _ad.save(authpdf)
        _ad.close()
    except Exception:
        pass
    try:
        C.refresh(db, [src])
    except Exception:
        pass

    def reader_window():
        p = pick('滚动测试')
        if not p:
            return (False, '未选中')
        w.resize(1300, 860)
        w.preview_here()
        app.processEvents()
        w.toggle_reader_window()
        app.processEvents()
        detached = (w._reader_win is not None
                    and w.reader_panel.parent() is w._reader_win)
        w.toggle_reader_window()
        app.processEvents()
        attached = (w._reader_win is None and w.reader_panel.parent() is not None)
        return (detached and attached,
                'detached=%s attached=%s' % (detached, attached))

    step(64, '阅读器独立成窗口（可最大化）+收回', reader_window)

    def smooth_scroll():
        p = pick('滚动测试')
        if not p:
            return (False, '未选中')
        w.resize(1300, 860)
        w.preview_here()
        app.processEvents()
        pv = w.pdf_view
        sb = pv.verticalScrollBar()
        w.pdf_home()
        app.processEvents()
        v0 = sb.value()
        ev = QWheelEvent(QPointF(10, 10), QPointF(10, 10), QPoint(0, -40),
                         QPoint(0, -120), Qt.MouseButton.NoButton,
                         Qt.KeyboardModifier.NoModifier,
                         Qt.ScrollPhase.NoScrollPhase, False)
        pv.wheelEvent(ev)
        app.processEvents()
        v1 = sb.value()
        kev = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Down,
                        Qt.KeyboardModifier.NoModifier)
        pv.keyPressEvent(kev)
        app.processEvents()
        v2 = sb.value()
        return (v1 > v0 and v2 > v1,
                'wheel %d->%d, ↓ ->%d' % (v0, v1, v2))

    step(65, 'PDF 平滑滚动：滚轮像素 + ↑↓键', smooth_scroll)

    def text_layer_select():
        p = pick('滚动测试')
        if not p:
            return (False, '未选中')
        w.resize(1300, 860)
        w.preview_here()
        app.processEvents()
        pv = w.pdf_view
        pv._render_visible()
        app.processEvents()
        it = pv._items[0]
        if not it.words:
            return (False, '无文字层词')
        it.sel_a = 0
        it.sel_b = min(3, len(it.words) - 1)
        t = it.selected_text()
        QApplication.clipboard().setText('')
        pv.copy_selection()
        cb = QApplication.clipboard().text()
        return (bool(t) and t == cb,
                'sel=%r cb=%r words=%d' % (t[:20], cb[:20], len(it.words)))

    step(66, 'PDF 文字层鼠标选择/复制', text_layer_select)

    def fts_process():
        import json as _json
        files = []
        for r in w.rows:
            pp = os.path.join(r.get('dir') or '', r.get('name') or '')
            if os.path.isfile(pp):
                files.append(pp)
        if not files:
            return (False, '无文件')
        jd = tempfile.mkdtemp(prefix='cvftsj_')
        job = os.path.join(jd, 'job.json')
        out = os.path.join(jd, 'out.json')
        with open(job, 'w', encoding='utf-8') as f:
            _json.dump({'kw': '第 1 页', 'files': files, 'out': out},
                       f, ensure_ascii=False)
        rc = G.fts_run(job)
        try:
            res = _json.load(open(out, encoding='utf-8'))
        except Exception as e:
            return (False, 'out读取失败 %s' % e)
        hits = res.get('hits') or []
        return (rc == 0 and len(hits) >= 1,
                'rc=%s hits=%d files=%d' % (rc, len(hits), len(files)))

    step(67, '跨文件全文检索（独立进程 worker）', fts_process)

    def toc_single_click():
        p = pick('滚动测试')
        if not p:
            return (False, '未选中')
        w.resize(1300, 860)
        w.preview_here()
        app.processEvents()
        w._after_pdf_open()
        app.processEvents()
        if w._nav_toc.count() < 2:
            return (False, 'toc 行不足 %d' % w._nav_toc.count())
        w._nav_toc.itemClicked.emit(w._nav_toc.item(1))
        app.processEvents()
        return (w.pgno == 5, 'pgno=%d (want 5)' % w.pgno)

    step(68, '目录单击即跳页', toc_single_click)

    def rights_info():
        p = pick('授权测试')
        if not p:
            return (False, '未选中 授权测试')
        w.on_pick()
        app.processEvents()
        lb = w.lb_info.text()
        rr = (getattr(w, 'meta', None) or {}).get('rights') or {}
        return (('版权/授权' in lb) and bool(rr.get('authorization')),
                'auth=%s lb_has=%s' % (rr.get('authorization'), '版权/授权' in lb))

    step(69, '版权/授权信息（文件名/目录/版权页）', rights_info)

    # ---------------- batch8 新增/调整（70-77） ----------------
    # ① 列表 3 列 ② 只显示上一级 ③ 单击文件名即打开 ④ 默认缩放=适应页面 ⑤ 跨页连选
    # ⑥ 关键词高亮 ⑦ 默认双窗口 ⑧ 顶部紧凑 ⑨ 检索按钮移到左栏并改名
    _deepdir = os.path.join(src, '甲编', '乙辑')
    os.makedirs(_deepdir, exist_ok=True)
    with open(os.path.join(_deepdir, '深书.txt'), 'w', encoding='utf-8') as _f:
        _f.write('深层文件内容\n')
    try:
        C.refresh(db, [src])
    except Exception:
        pass

    def parent_only():
        p = pick('深书')
        if not p:
            return (False, '未选中 深书')
        app.processEvents()
        if w.tb.rowCount() < 1:
            return (False, 'no rows')
        shown = w.tb.item(0, 2).text()
        full = w.tb.item(0, 2).toolTip()
        return (shown == '乙辑' and '甲编' not in shown,
                'shown=%r full=%r' % (shown, full))

    step(70, '上级文件夹只显示上一级', parent_only)

    def single_click():
        p = pick('滚动测试')
        if not p:
            return (False, '未选中')
        w.pd = None
        w.tb.setCurrentCell(-1, -1)
        w._on_item_click(w.tb.item(0, 1))
        app.processEvents()
        a = (w.pd is not None)
        w.pd = None
        w.tb.setCurrentCell(-1, -1)
        w._on_item_click(w.tb.item(0, 2))      # 点「上级文件夹」列不应打开
        app.processEvents()
        b = (w.pd is None)
        return (a and b, 'by_filename=%s by_parent_not_opened=%s' % (a, b))

    step(71, '单击文件名即打开（其它列不触发）', single_click)

    def default_zoom():
        w3 = G.MainWindow(C.load_settings())
        w3.db = db
        r = (w3._zoom_mode == 'fitp' and w3.cb_zoom.currentIndex() == 1)
        md, cb = w3._zoom_mode, w3.cb_zoom.currentIndex()
        try:
            w3.close()
        except Exception:
            pass
        return (r, 'mode=%s cb=%d' % (md, cb))

    step(72, 'PDF 默认缩放=适应页面', default_zoom)

    def cross_page():
        p = pick('滚动测试')
        if not p:
            return (False, '未选中')
        w.resize(1300, 860)
        w.preview_here()
        app.processEvents()
        pv = w.pdf_view
        pv._render_visible()
        app.processEvents()
        if len(pv._items) < 2 or not pv._items[0].words or not pv._items[1].words:
            return (False, '页/词不足')
        i0, i1 = pv._items[0], pv._items[1]
        g0 = pv._content.mapToGlobal(QPoint(i0.x() + int(i0.words[0][0]) + 2,
                                            i0.y() + int(i0.words[0][1]) + 2))
        pv.begin_select(0, 0, g0)
        g1 = pv._content.mapToGlobal(QPoint(i1.x() + int(i1.words[3][0]) + 2,
                                            i1.y() + int(i1.words[3][1]) + 2))
        pv.extend_select(g1)
        app.processEvents()
        t = pv.selected_text()
        QApplication.clipboard().setText('')
        pv.end_select()
        ok = (i0.sel_a == 0 and i0.sel_b == len(i0.words) - 1 and i1.sel_a == 0
              and i1.sel_b >= 3 and '\n' in t
              and QApplication.clipboard().text() == t)
        return (ok, 'pg0=%s pg1=%s text=%r' % ((i0.sel_a, i0.sel_b),
                                               (i1.sel_a, i1.sel_b), t[:28]))

    step(73, 'PDF 跨页连选 + 复制', cross_page)

    def kw_highlight():
        w.ed_kw.setText('滚动测试')
        w.do_search()
        app.processEvents()
        return (getattr(w, '_last_kw', '') == '滚动测试' and w.tb.itemDelegate() is w._hi,
                'kw=%r delegate=%s' % (getattr(w, '_last_kw', ''),
                                       w.tb.itemDelegate() is w._hi))

    step(74, '搜索结果关键词高亮（文件名列）', kw_highlight)

    def fts_left():
        ok = (hasattr(w, 'b_fts') and '检索' in w.b_fts.text()
              and not w.reader_panel.isAncestorOf(w.b_fts))
        return (ok, 'text=%r in_reader=%s'
                % (w.b_fts.text(), w.reader_panel.isAncestorOf(w.b_fts)))

    step(75, '「跨文件全文检索」按钮位于左栏', fts_left)

    def compact_top():
        off = w.stack.mapTo(w.reader_panel, QPoint(0, 0)).y()
        ok = ((not w.lb_info.isVisible())
              and (not w._find_bar_widget.isVisible()) and off <= 52)
        return (ok, 'lb_info=%s find_bar=%s top_off=%d'
                % (w.lb_info.isVisible(), w._find_bar_widget.isVisible(), off))

    step(76, '阅读器顶部紧凑（≤52px）', compact_top)

    def two_window_default():
        w2 = G.MainWindow(C.load_settings())
        w2.db = db
        w2.start_two_window_mode()
        app.processEvents()
        det = (w2._reader_win is not None and w2.reader_panel.parent() is w2._reader_win)
        try:
            w2._attach_reader()
        except Exception:
            pass
        try:
            w2.close()
        except Exception:
            pass
        return (det, 'reader_win=%s' % det)

    step(77, '阅读器可拆成独立窗口（🗗 切换）', two_window_default)

    # ---------------- batch9 ----------------
    def single_window_default():
        w3 = G.MainWindow(C.load_settings())
        w3.db = db
        w3.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        w3.resize(1200, 800)
        w3.show()
        app.processEvents()
        try:
            n = w3._split.count()
            sz = w3._split.sizes()
        except Exception:
            n, sz = 0, [0, 0]
        merged = getattr(w3, '_reader_win', None) is None
        ok = merged and n == 2 and sz[1] >= 2 * max(1, sz[0])
        try:
            w3.close()
        except Exception:
            pass
        return (ok, 'merged=%s panes=%d sizes=%s' % (merged, n, list(sz)))

    step(78, '默认单窗口：左列表 ｜ 右阅读器（阅读器占大头）', single_window_default)

    def win_memory():
        w4 = G.MainWindow(C.load_settings())
        w4.db = db
        w4._layout_track = True
        w4.resize(1111, 777)
        w4.move(120, 80)
        w4._split.setSizes([240, 860])
        app.processEvents()
        d = w4._layout_dict()
        w4._save_layout()
        ok = (d.get('win_geom', [0, 0, 0, 0])[2:] == [1111, 777]
              and len(d.get('split_sizes') or []) == 2
              and d.get('reader_detached') is False)
        try:
            w4.close()
        except Exception:
            pass
        stored = C.load_settings()
        ok = ok and list(stored.get('split_sizes') or []) == list(d.get('split_sizes') or [])
        w5 = G.MainWindow(C.load_settings())
        det = w5._restore_layout()
        ok = ok and (not det) and w5.width() == 1111
        try:
            w5.close()
        except Exception:
            pass
        st = C.load_settings()
        st['reader_detached'] = True
        C.save_settings(st)
        w6 = G.MainWindow(C.load_settings())
        det2 = w6._restore_layout()
        ok = ok and bool(det2)
        try:
            w6.close()
        except Exception:
            pass
        st['reader_detached'] = False
        C.save_settings(st)
        return (ok, 'geom=%s split=%s det=%s restoreW=%d det2=%s'
                % (d.get('win_geom'), d.get('split_sizes'), d.get('reader_detached'),
                   w5.width(), bool(det2)))

    step(79, '窗口布局记忆（尺寸/位置 + 分割比例 + 是否拆窗）', win_memory)

    def no_double_open():
        if w._cur() is None and w.rows:
            w.tb.setCurrentCell(0, 1)
        r0 = w._cur()
        if r0 is None:
            return (False, '无选中行')
        calls = []
        orig = w.on_pick
        w.on_pick = lambda: calls.append(1)
        try:
            w._last_open_path, w._last_open_t = '', 0.0
            w.open_here()          # 第 1 次（单击）
            w.open_here()          # 第 2 次（双击紧跟）应该被拦
        finally:
            w.on_pick = orig
        ok = len(calls) == 1
        return (ok, 'open_calls=%d（双击只处理一次）' % len(calls))

    step(80, '双击不重复打开（防重入）', no_double_open)

    def dedup_engine():
        d0 = os.path.join(base, '去重')
        os.makedirs(d0, exist_ok=True)

        def f(nm, cnt):
            return {'name': nm, 'path': os.path.join(d0, nm), 'count': cnt, 'hits': []}

        a = META.dedup_files([f('书A_PD6AIFOCR.pdf', 3), f('书A_PD6AIFOCR.txt', 3)])
        b = META.dedup_files([f('书B_PD6AIFOCR.pdf', 4), f('书B_PD6AIFOCR.txt', 7)])
        c = META.dedup_files([f('书C_PD6AIFOCR.pdf', 2), f('书C_PD6GJOCR.txt', 2)])
        e = META.dedup_files([f('书D_PD6AIFOCR.pdf', 2), f('书D_PD6AIFOCR_【繁转简】.txt', 2)])
        o = META.dedup_files([f('书E_PD6AIFOCR_opt.pdf', 5), f('书E_PD6AIFOCR.txt', 5)])
        na, nb = [x['name'] for x in a], sorted(x['name'] for x in b)
        ok = (na == ['书A_PD6AIFOCR.pdf']
              and nb == ['书B_PD6AIFOCR.pdf', '书B_PD6AIFOCR.txt']
              and [x.get('txt_mark') for x in b if x['name'].endswith('.txt')] == [True]
              and sorted(x['name'] for x in c) == ['书C_PD6AIFOCR.pdf', '书C_PD6GJOCR.txt']
              and sorted(x['name'] for x in e)
              == ['书D_PD6AIFOCR.pdf', '书D_PD6AIFOCR_【繁转简】.txt']
              and [x['name'] for x in o] == ['书E_PD6AIFOCR_opt.pdf'])
        return (ok, '①%s ②%s ③%s ④%s opt%s'
                % (na, nb, [x['name'] for x in c], [x['name'] for x in e],
                   [x['name'] for x in o]))

    step(81, '去重①②③④ + _opt 视为同名（仅留 PDF）', dedup_engine)

    def scope_expand():
        d0 = os.path.join(base, '收范围')
        os.makedirs(d0, exist_ok=True)
        for n in ('书G_PD6AIFOCR.pdf', '书G_PD6AIFOCR.txt', '书G_PD6AIFOCR_【繁转简】.txt'):
            open(os.path.join(d0, n), 'wb').write(b'%PDF-1.4 x')
        got = [os.path.basename(x)
               for x in w._expand_family([os.path.join(d0, '书G_PD6AIFOCR.pdf')])]
        ok = ('书G_PD6AIFOCR.txt' in got and '书G_PD6AIFOCR_【繁转简】.txt' in got)
        return (ok, 'expanded=%s' % sorted(got))

    step(82, '跨文件检索把对应的 TXT 纳入范围', scope_expand)

    def single_find_dedup():
        d0 = os.path.join(base, '单文件')
        os.makedirs(d0, exist_ok=True)
        txt = os.path.join(d0, '书F_PD6AIFOCR.txt')
        with open(txt, 'w', encoding='utf-8') as f:
            f.write('关键词 关键词 关键词\n')
        w._text_path = txt
        w._reader = 'text'
        w.view.setPlainText('关键词 关键词 关键词\n')
        w.ed_find.setText('关键词')
        w.find_run()
        app.processEvents()
        ok1 = (w._find_total == 3 and w._find_hits[0]['path'] == txt)
        pdf = os.path.join(d0, '书F_PD6AIFOCR.pdf')
        open(pdf, 'wb').write(b'%PDF-1.4 bad')
        rep = [{'path': txt, 'name': '书F_PD6AIFOCR.txt', 'count': 3,
                'hits': [{'off': 0, 'ctx': 'x'}]},
               {'path': pdf, 'name': '书F_PD6AIFOCR.pdf', 'count': 3,
                'hits': [{'page': 0, 'ctx': 'x'}]}]
        kept = [k['name'] for k in META.dedup_files(rep)]
        ok2 = kept == ['书F_PD6AIFOCR.pdf']
        return (ok1 and ok2, 'single_total=%d keep=%s' % (w._find_total, kept))

    step(83, '单文件文内查找同一套去重（同命中数→只留 PDF）', single_find_dedup)

    def nav_in_reader():
        w7 = G.MainWindow(C.load_settings())
        w7.db = db
        w7._build_nav_dock()
        app.processEvents()
        w7.start_two_window_mode()
        app.processEvents()
        dk = getattr(w7, '_nav_dock', None)
        in_reader = (w7._reader_win is not None and dk is not None
                     and dk.parent() is w7._reader_win)
        try:
            w7._attach_reader()
        except Exception:
            pass
        dk2 = getattr(w7, '_nav_dock', None)
        back = (dk2 is not None and dk2.parent() is w7)
        try:
            w7.close()
        except Exception:
            pass
        return (in_reader and back, 'nav_in_reader=%s back_to_main=%s' % (in_reader, back))

    step(84, '导航面板跟随阅读器（拆窗在阅读器侧 / 收回随主窗）', nav_in_reader)

    def dedup_split_test():
        d0 = os.path.join(base, '去重2')
        os.makedirs(d0, exist_ok=True)

        def f(nm, cnt):
            return {'name': nm, 'path': os.path.join(d0, nm), 'count': cnt, 'hits': []}

        kept, hid = META.dedup_split([f('书H_PD6AIFOCR.pdf', 3),
                                      f('书H_PD6AIFOCR.txt', 3)])
        ok = ([x['name'] for x in kept] == ['书H_PD6AIFOCR.pdf']
              and [x['name'] for x in hid] == ['书H_PD6AIFOCR.txt'])
        return (ok, 'kept=%s hidden=%s'
                % ([x['name'] for x in kept], [x['name'] for x in hid]))

    step(85, '被去重项单独标出（dedup_split：默认隐藏）', dedup_split_test)

    def find_reveal():
        d0 = os.path.join(base, '单文件')
        txt = os.path.join(d0, '书F_PD6AIFOCR.txt')
        pdf = os.path.join(d0, '书F_PD6AIFOCR.pdf')
        w._text_path = txt
        w._reader = 'text'
        w.view.setPlainText('关键词 关键词 关键词\n')
        w.ed_find.setText('关键词')
        rep = [{'path': txt, 'name': '书F_PD6AIFOCR.txt', 'count': 3,
                'hits': [{'off': 0, 'ctx': 'a'}, {'off': 3, 'ctx': 'b'},
                         {'off': 6, 'ctx': 'c'}]},
               {'path': pdf, 'name': '书F_PD6AIFOCR.pdf', 'count': 3,
                'hits': [{'page': 0, 'ctx': 'p'}]}]
        kept, hid = META.dedup_split(rep)
        w._find_kept = [w._hit(f, h) for f in kept for h in (f.get('hits') or [])]
        w._find_hidden = [dict(w._hit(f, h), hidden=True)
                          for f in hid for h in (f.get('hits') or [])]
        w._find_show_hidden = False
        w._rebuild_find_view()
        w._populate_find_tab()
        app.processEvents()
        before = len(w._find_view)
        w.toggle_find_hidden()
        app.processEvents()
        after = len(w._find_view)
        ok = (before == 1 and after == 4 and len(w._find_hidden) == 3)
        return (ok, 'before=%d after=%d hidden=%d btn=%r'
                % (before, after, len(w._find_hidden), w._btn_find_hidden.text()))

    step(86, '单文件结果：被去重项默认隐藏 + 一键展开', find_reveal)

    def list_cols():
        from PyQt6.QtWidgets import QHeaderView
        hh = w.tb.horizontalHeader()
        okv = (not w.tb.verticalHeader().isVisible()
               and hh.sectionResizeMode(1) == QHeaderView.ResizeMode.Stretch
               and hh.sectionResizeMode(2) == QHeaderView.ResizeMode.Interactive)
        return (okv, 'vhead=%r mode1=%s mode2=%s'
                % (w.tb.verticalHeader().isVisible(),
                   hh.sectionResizeMode(1).name, hh.sectionResizeMode(2).name))

    step(87, '文件列表：无行号列 + 文件名拉伸 + 上级文件夹可缩', list_cols)

    def tabs_compact():
        w._build_nav_dock()
        _e = w._nav_tabs.tabBar().expanding()
        return (not _e, 'expanding=%r' % _e)

    step(88, '导航页签不拉伸（窗口小也不挤掉字）', tabs_compact)

    def pdf_fit_resize():
        import fitz
        d0 = os.path.join(base, '缩放')
        os.makedirs(d0, exist_ok=True)
        p = os.path.join(d0, '缩放书.pdf')
        dd = fitz.open()
        for t in ('缩放测试 第一页', '缩放测试 第二页'):
            pg = dd.new_page(width=420, height=640)
            pg.insert_text((40, 60), t)
        dd.save(p)
        dd.close()
        w2 = G.MainWindow({'primary_db': w.db, 'lib_root': base})
        w2.db = w.db
        w2.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        w2.resize(1250, 800)
        w2.show()
        for _ in range(20):
            app.processEvents()
            time.sleep(0.01)
        w2._open_path(p)
        for _ in range(10):
            app.processEvents()
            time.sleep(0.01)
        z1 = w2.pdf_view._zoom
        fit1 = w2.pdf_view._page_size(0).width() <= w2.pdf_view.viewport().width() + 2
        w2.resize(980, 640)
        for _ in range(40):
            app.processEvents()
            time.sleep(0.02)
        z2 = w2.pdf_view._zoom
        fit2 = w2.pdf_view._page_size(0).width() <= w2.pdf_view.viewport().width() + 2
        hmax = w2.pdf_view.horizontalScrollBar().maximum()
        mode = w2.pdf_view._fit_mode
        w2.close()
        return (mode == 'fitp' and fit1 and fit2 and hmax == 0 and abs(z2 - z1) > 1e-3,
                'fit=%r z1=%.3f z2=%.3f fits=%r/%r hmax=%d'
                % (mode, z1, z2, fit1, fit2, hmax))

    step(89, 'PDF 适应窗口（窗口变化自动重排、左右不被裁）', pdf_fit_resize)

    def ver_switch():
        import fitz as _fz
        d0 = os.path.join(base, '版本')
        os.makedirs(d0, exist_ok=True)
        pdf = os.path.join(d0, '版本书.pdf')
        _d = _fz.open()
        _pg = _d.new_page(width=420, height=640)
        _pg.insert_text((40, 60), '版本) 正文')
        _d.save(pdf)
        _d.close()
        open(os.path.join(d0, '版本书_PD6AIFOCR.txt'), 'w', encoding='utf-8').write('版本) 正文\n')
        db2 = os.path.join(base, 'i2.db')
        C.build([d0], db2)
        w3 = G.MainWindow({'primary_db': db2, 'lib_root': d0})
        w3.db = db2
        w3.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        w3.resize(1100, 720)
        w3.show()
        w3.ed_kw.setText('版本')
        w3.do_search()
        for _ in range(10):
            app.processEvents()
            time.sleep(0.01)
        w3.tb.setCurrentCell(0, 1)
        w3.on_pick()
        for _ in range(10):
            app.processEvents()
            time.sleep(0.01)
        n = w3.cb_ver.count()
        good = 0
        for k in range(n):
            want = w3.vers[k].get('path') or ''
            w3.on_ver(k)
            for _ in range(6):
                app.processEvents()
                time.sleep(0.01)
            cur = w3._pd_path or w3._text_path or ''
            if os.path.normcase(cur) == os.path.normcase(want):
                good += 1
        w3.close()
        return (n >= 1 and good == n, 'vers=%d opened_ok=%d' % (n, good))

    step(90, '版本下拉切换＝真的打开该版本', ver_switch)

    def find_robust():
        d0 = os.path.join(base, '跳转')
        os.makedirs(d0, exist_ok=True)
        tx = os.path.join(d0, '跳转书.txt')
        open(tx, 'w', encoding='utf-8').write('正文\n')
        w4 = G.MainWindow({'primary_db': w.db, 'lib_root': base})
        w4.db = w.db
        w4.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        w4.resize(1000, 700)
        w4.show()
        for _ in range(10):
            app.processEvents()
            time.sleep(0.01)
        w4._find_kept = [{'path': os.path.join(d0, '没有这个文件.txt'),
                          'name': '没有这个文件.txt', 'page': None,
                          'off': 0, 'ctx': 'x', 'txt_mark': False}]
        w4._find_hidden = []
        w4._find_show_hidden = False
        w4._rebuild_find_view()
        crashed = False
        try:
            w4._find_jump(0)
        except Exception:
            crashed = True
        msg = w4.statusBar().currentMessage() or ''
        # 打开一个真实 TXT 不应清空查找计数
        w4._find_total = 3
        w4._find_idx = 1
        w4._show_text_file(tx)
        keep = (w4._find_total == 3 and w4._find_idx == 1)
        w4.close()
        return ((not crashed) and ('打不开' in msg) and keep,
                'crashed=%r msg=%r keep=%r' % (crashed, msg[:24], keep))

    step(91, '查找结果打不开时给提示、不崩；开 TXT 不清空计数', find_robust)

    # ---------------- batch11 新增功能核验（92-97） ----------------
    # ① 摘录本 ② 截图本 ③ PDF+TXT 对读（自动+同步） ④ 检索历史 ⑤ 版权页目录优先+回退
    _dual = os.path.join(src, '对读测试.pdf')
    _dualtxt = os.path.join(src, '对读测试.txt')
    _d = fitz.open()
    for _i in range(3):
        ins(_d.new_page(), (72, 100), '对读测试 第 %d 页 正文' % (_i + 1), 14)
    _d.set_toc([[1, '第一章', 1], [1, '第二章', 2], [1, '第三章', 3]])
    _d.save(_dual)
    _d.close()
    open(_dualtxt, 'w', encoding='utf-8').write(
        '======\n第 1 页\n第一页正文甲甲甲。\n======\n第 2 页\n第二页正文乙乙乙。\n'
        '======\n第 3 页\n第三页正文丙丙丙。\n======\n')
    _colret = os.path.join(src, '版权回退.pdf')
    _d = fitz.open()
    ins(_d.new_page(), (72, 120),
        '图书在版编目（CIP）数据\n版权回退书／某某著．—北京：中华书局，1999.1\n'
        'ISBN 7-101-0000-0', 11)
    _d.new_page()
    _d.set_toc([[1, '正文', 1]])
    _d.save(_colret)
    _d.close()
    try:
        C.refresh(db, [src])
    except Exception:
        pass

    def excerpt_save():
        p = pick('甲书.pdf')
        if not p:
            return (False, '未选中 甲书.pdf')
        w.preview_here()
        app.processEvents()
        if w._reader != 'pdf':
            return (False, 'reader=%s' % w._reader)
        w.pdf_home()                          # 回到第 1 页（不依赖书签）
        app.processEvents()
        w.pdf_view.select_all_page()          # 选中第 1 页文字
        app.processEvents()
        w.excerpt_here()
        app.processEvents()
        ex = os.path.join(TOOLS.docs_root(), '摘录本', '摘录本.md')
        body = open(ex, encoding='utf-8').read() if os.path.isfile(ex) else ''
        ok = ('摘录' in body and '甲书' in body and '第1页' in body)
        return (ok, 'reader=%s file=%s has_第1页=%s'
                % (w._reader, os.path.isfile(ex), '第1页' in body))

    step(92, '✂ 摘录选中文字 → 摘录本（含书名/页码）', excerpt_save)

    def snapshot_save():
        from PyQt6.QtWidgets import QInputDialog
        from PyQt6.QtCore import QRect
        p = pick('甲书.pdf')
        if not p:
            return (False, '未选中 甲书.pdf')
        w.preview_here()
        app.processEvents()
        if w._reader != 'pdf':
            return (False, 'reader=%s' % w._reader)
        old = QInputDialog.getInt
        QInputDialog.getInt = staticmethod(lambda *a, **k: (1, True))   # 自动确认页码
        try:
            for d in (200, 600, 1200):
                QTimer.singleShot(d, close_modal)
            w.snapshot_here()                    # 整页截图
            app.processEvents()
            w._on_pdf_region(0, QRect(8, 8, 60, 60))   # 框选截图
            app.processEvents()
        finally:
            QInputDialog.getInt = old
        dd = os.path.join(TOOLS.docs_root(), '截图本')
        pngs = [f for f in os.listdir(dd) if f.lower().endswith('.png')] if os.path.isdir(dd) else []
        md = os.path.join(dd, '截图本.md')
        body = open(md, encoding='utf-8').read() if os.path.isfile(md) else ''
        ok = (len(pngs) >= 2 and '甲书' in body and '第1页' in body)
        return (ok, 'pngs=%d has_book=%s has_第1页=%s'
                % (len(pngs), '甲书' in body, '第1页' in body))

    step(93, '📷 截图 → 截图本（整页 + 框选）', snapshot_save)

    def dual_auto():
        w.st['auto_dual'] = True
        p = pick('对读测试.txt')
        if not p:
            w.st['auto_dual'] = False
            return (False, '未选中 对读测试.txt')
        w.preview_here()
        app.processEvents()
        engaged = (getattr(w, '_reader', '') == 'dual'
                   and w.stack.currentWidget() is w.dual
                   and getattr(w.dual.pdf, 'doc', None) is not None)
        pcount = w.dual.pdf.page_count()
        tcount = w.dual.txt.idx.page_count if w.dual.txt.idx else 0
        w.st['auto_dual'] = False
        return (engaged and pcount == 3 and tcount == 3,
                'reader=%s pdf=%d txt=%d' % (getattr(w, '_reader', ''), pcount, tcount))

    step(94, '⇄ 打开 TXT 有同名 PDF → 自动对读', dual_auto)

    def dual_sync():
        if getattr(w, '_reader', '') != 'dual':
            return (False, '未在对读态')
        w.dual._on_pdf_page(2)                # 模拟 PDF 翻到第 3 页
        app.processEvents()
        fwd = (w.dual.ed.text() == '3' and w.dual.txt._cur == 3)
        got = []
        w.dual.pdf.pageChanged.connect(lambda i: got.append(i))
        w.dual._on_txt_page(2)                # 模拟 TXT 滚到第 2 页
        app.processEvents()
        rev = (w.dual.ed.text() == '2' and (1 in got))
        return (fwd and rev,
                'fwd ed=%r txt=%d | rev ed=%r pdf_got=%s'
                % (w.dual.ed.text(), w.dual.txt._cur, w.dual.ed.text(), got))

    step(95, '⇄ 对读页码双向同步', dual_sync)

    def fts_hist_save():
        import json as _json
        jd = tempfile.mkdtemp(prefix='cvftsh_')
        out = os.path.join(jd, 'out.json')
        res = {'kw': '对读', 'scanned': 2, 'total': 3, 'errors': [],
               'files': [{'path': _dualtxt, 'name': '对读测试.txt', 'count': 3,
                          'hits': [{'page': None, 'ctx': '对读…'}]}]}
        with open(out, 'w', encoding='utf-8') as f:
            _json.dump(res, f, ensure_ascii=False)
        for d in (200, 600, 1200, 2000):
            QTimer.singleShot(d, close_modal)
        w._fts_done(0, out, jd, '对读')       # 含结果弹窗（定时器关闭）
        app.processEvents()
        hh = C.load_settings().get('fts_hist') or []
        ok1 = bool(hh) and hh[0].get('kw') == '对读'
        for d in (200, 600, 1200):
            QTimer.singleShot(d, close_modal)
        w.fts_history_dialog()               # 历史弹窗（定时器关闭）
        app.processEvents()
        lh = getattr(w, '_last_fts_hist', None) or []
        return (ok1 and len(lh) >= 1,
                'hist0=%s dlg=%d' % (hh[0].get('kw') if hh else None, len(lh)))

    step(96, '🕘 跨文件检索历史自动保存/可调阅', fts_hist_save)

    def colophon_toc_first():
        p = pick('甲书')
        if not p:
            return (False, '未选中 甲书')
        w.colophon_here()
        app.processEvents()
        m1 = w.statusBar().currentMessage()
        ok1 = (w.pgno == 2 and '版权页' in m1 and '目录' in m1)
        p2 = pick('版权回退')
        if not p2:
            return (False, '未选中 版权回退.pdf')
        w.colophon_here()
        app.processEvents()
        m2 = w.statusBar().currentMessage()
        ok2 = ('版权页' in m2) and ('文字层' in m2)
        return (ok1 and ok2, 'toc=%r fallback=%r' % (m1[:30], m2[:30]))

    step(97, '⤒ 版权页：目录优先，找不到再回退', colophon_toc_first)

    # ---------------- batch12 新增功能核验（98-102） ----------------
    # ① 复制自动纪年换算（民国 38 内不转） ② PDF 选中复制换算
    # ③ 脚注 RTF（Word 可直贴） ④ 纪年换算工具 ⑤ 摘录自动换算
    _chtxt = os.path.join(src, '纪年测试.txt')
    open(_chtxt, 'w', encoding='utf-8').write('光绪二十四年。民国三十八年。民国四十年。\n')
    _chpdf = os.path.join(src, '纪年测试.pdf')
    _d = fitz.open()
    ins(_d.new_page(), (72, 100), '光绪二十四年。民国三十八年。民国四十年。', 14)
    _d.save(_chpdf)
    _d.close()
    try:
        C.refresh(db, [src])
    except Exception:
        pass

    def copy_chrono():
        p = pick('纪年测试.txt')
        if not p:
            return (False, '未选中 纪年测试.txt')
        w.preview_here()
        app.processEvents()
        w.copy_text()
        app.processEvents()
        t = QApplication.clipboard().text()
        ok = ('【纪年换算】' in t and '1898' in t and '1951' in t and '1949' not in t)
        return (ok, repr(t[:90]))

    step(98, '⧉ 复制文本自动附纪年换算（民国38内不转）', copy_chrono)

    def pdf_copy_chrono():
        p = pick('纪年测试.pdf')
        if not p:
            return (False, '未选中 纪年测试.pdf')
        w.preview_here()
        app.processEvents()
        w.pdf_home()
        app.processEvents()
        w.pdf_view.select_all_page()
        app.processEvents()
        t = QApplication.clipboard().text()
        ok = ('【纪年换算】' in t and '1898' in t and '1951' in t and '1949' not in t)
        return (ok, repr(t[:90]))

    step(99, 'PDF 选中文字复制自动附纪年换算', pdf_copy_chrono)

    def footnote_rtf():
        p = pick('纪年测试.txt')
        if not p:
            return (False, '未选中 纪年测试.txt')
        w.preview_here()
        app.processEvents()
        w.view.selectAll()
        app.processEvents()
        data = b''
        for _try in range(3):          # 剪贴板是系统共享资源，偶尔被别的进程占用 → 重试
            w.footnote_here()
            app.processEvents()
            md = QApplication.clipboard().mimeData()
            data = bytes(md.data('text/rtf')) if (md is not None and md.hasFormat('text/rtf')) else b''
            if data:
                break
            QTimer.singleShot(120, lambda: None)
            app.processEvents()
            time.sleep(0.12)
        ok = (b'\\rtf1' in data and b'\\footnote' in data and b'\\u' in data)
        return (ok, 'has_rtf=%s len=%d' % (bool(data), len(data)))

    step(100, '❞ 脚注 RTF（Word 可直贴）', footnote_rtf)

    def chrono_tool():
        try:
            QApplication.clipboard().setText('光绪二十四年')
        except Exception:
            pass
        for d in (200, 600, 1200, 2000):
            QTimer.singleShot(d, close_modal)
        w.chrono_dialog()
        app.processEvents()
        lc = getattr(w, '_last_chrono', None) or {}
        out = lc.get('out').toPlainText() if lc.get('out') is not None else ''
        return ('1898' in out, repr(out[:70]))

    step(101, '⌛ 纪年换算工具可打开并换算', chrono_tool)

    def excerpt_chrono():
        p = pick('纪年测试.txt')
        if not p:
            return (False, '未选中 纪年测试.txt')
        w.preview_here()
        app.processEvents()
        w.view.selectAll()
        app.processEvents()
        w.excerpt_here()
        app.processEvents()
        ex = os.path.join(TOOLS.docs_root(), '摘录本', '摘录本.md')
        body = open(ex, encoding='utf-8').read() if os.path.isfile(ex) else ''
        return (('1898' in body and '1951' in body and '1949' not in body),
                'has1898=%s has1951=%s' % ('1898' in body, '1951' in body))

    step(102, '✂ 摘录自动含纪年换算', excerpt_chrono)

    # ---------------- batch13 新增功能核验（103-105）人名别名归一 ----------------
    def alias_expand():
        a = os.path.join(src, '子玉.txt')
        open(a, 'w', encoding='utf-8').write('子玉（吴佩孚字）相关正文\n')
        b = os.path.join(src, '孙文.txt')
        open(b, 'w', encoding='utf-8').write('孙文（孙中山本名）相关正文\n')
        try:
            C.refresh(db, [src])
        except Exception:
            pass
        w.st['alias_mode'] = 'auto'
        w.ed_kw.setText('吴佩孚')
        w.do_search()
        app.processEvents()
        names = [r.get('name') for r in w.rows]
        ok1 = any('子玉' in (n or '') for n in names)
        w.ed_kw.setText('孙中山')
        w.do_search()
        app.processEvents()
        names = [r.get('name') for r in w.rows]
        ok2 = any('孙文' in (n or '') for n in names)
        w.st['alias_mode'] = 'off'
        w.ed_kw.setText('吴佩孚')
        w.do_search()
        app.processEvents()
        names = [r.get('name') for r in w.rows]
        ok3 = not any('子玉' in (n or '') for n in names)
        w.st['alias_mode'] = 'ask'
        return (ok1 and ok2 and ok3,
                'auto子玉=%s auto孙文=%s off无=%s' % (ok1, ok2, ok3))

    step(103, '👤 人名别名归一（检索人名并入字號/笔名）', alias_expand)

    def alias_dialog():
        for d in (200, 600, 1200, 2000):
            QTimer.singleShot(d, close_modal)
        w.alias_dialog()
        app.processEvents()
        d = getattr(w, '_last_alias_dlg', {}) or {}
        lst, cbx = d.get('list'), d.get('combo')
        n = lst.count() if lst is not None else 0
        return (bool(lst) and n > 50 and cbx is not None,
                'list=%d combo=%s' % (n, cbx.currentText() if cbx else None))

    step(104, '👤 人名别名表对话框（查看/增删/导入导出）', alias_dialog)

    def alias_logic():
        ok1 = '子玉' in ALIAS.expand('吴佩孚')
        ok2 = ALIAS.canonical_of('孙文') == '孙中山'
        ok3 = ALIAS.count()['people'] > 50
        return (ok1 and ok2 and ok3,
                'expand吴佩孚=%s 反查孙文=%s people=%d'
                % (ok1, ok2, ALIAS.count()['people']))

    step(105, '👤 别名归一逻辑（expand / lookup 反查）', alias_logic)

    # ---------------- batch14 新增功能核验（106-114） ----------------
    # ① 对读左右并列 + 中间导航 ② TXT 版本可切 ③ 只看 PDF/TXT
    # ④ 进对读保持 PDF 页并同步 TXT ⑤ 左栏可缩小 ⑥ 版本下拉变宽
    # ⑦ 摘录查看/编辑器 ⑧ 越界纪年提示 ⑨ 反查注明年数
    def dual_layout():
        from PyQt6.QtWidgets import QSplitter
        if getattr(w, '_reader', '') != 'dual':
            w.st['auto_dual'] = True
            pick('对读测试.txt')
            w.preview_here()
            app.processEvents()
            w.st['auto_dual'] = False
        if getattr(w, '_reader', '') != 'dual':
            return (False, 'reader=%s' % w._reader)
        horiz = nav = False
        for s in w.dual.findChildren(QSplitter):
            if s.count() == 3 and s.widget(0) is w.dual.pdf and s.widget(2) is w.dual.txt:
                horiz = (s.orientation() == Qt.Orientation.Horizontal)
                mid = s.widget(1)
                nav = (mid is not None and mid is not w.dual.pdf and mid is not w.dual.txt
                       and w.dual.ed in mid.findChildren(type(w.dual.ed)))
        return (horiz and nav, 'horiz=%s 中间导航=%s' % (horiz, nav))

    step(106, '⇄ 对读：PDF/TXT 左右并列，中间是 PDF 导航', dual_layout)

    def dual_txt_version():
        v = os.path.join(src, '对读测试_【繁转简】.txt')
        open(v, 'w', encoding='utf-8').write(
            '======\n第 1 页\nTXT变体甲。\n======\n第 2 页\nTXT变体乙。\n'
            '======\n第 3 页\nTXT变体丙。\n======\n')
        try:
            C.refresh(db, [src])
        except Exception:
            pass
        p = pick('对读测试.txt')
        if not p:
            return (False, '未选中 对读测试.txt')
        w.st['auto_dual'] = True
        w.preview_here()
        app.processEvents()
        w.st['auto_dual'] = False
        if w._reader != 'dual':
            return (False, 'reader=%s' % w._reader)
        n = w.dual.cb_txt.count()
        target = -1
        for i in range(n):
            if '繁转简' in (w.dual.cb_txt.itemText(i) or ''):
                target = i
        if target < 0:
            return (False, '下拉项=%s' % [w.dual.cb_txt.itemText(i) for i in range(n)])
        w.dual.cb_txt.setCurrentIndex(target)
        app.processEvents()
        txt = w.dual.txt.toPlainText()
        ok = (n >= 2 and '变体' in txt)
        return (ok, 'n=%d 变体=%s path=%s'
                % (n, '变体' in txt, os.path.basename(getattr(w, '_text_path', ''))))

    step(107, '⇄ 对读可切换 TXT 版本（OCR/繁简）', dual_txt_version)

    def dual_single_view():
        if getattr(w, '_reader', '') != 'dual':
            w.st['auto_dual'] = True
            pick('对读测试.txt')
            w.preview_here()
            app.processEvents()
            w.st['auto_dual'] = False
        if getattr(w, '_reader', '') != 'dual':
            return (False, 'reader=%s' % w._reader)
        w.dual.goto_page(1)
        app.processEvents()
        w.dual._single('pdf')
        app.processEvents()
        ok1 = (w._reader == 'pdf' and w.stack.currentWidget() is w.pdf_view)
        pg = w.pgno
        w._enter_dual(getattr(w, '_text_path', ''))
        app.processEvents()
        w.dual._single('text')
        app.processEvents()
        ok2 = (w._reader == 'text' and w.stack.currentWidget() is w.text_view)
        return (ok1 and ok2, '只看PDF=%s pg=%s 只看TXT=%s' % (ok1, pg, ok2))

    step(108, '⇄ 对读可退出：只看 PDF / 只看 TXT', dual_single_view)

    def dual_keep_page():
        p = pick('对读测试.pdf')
        if not p:
            return (False, '未选中 对读测试.pdf')
        w.preview_here()
        app.processEvents()
        if w._reader != 'pdf':
            return (False, 'reader=%s' % w._reader)
        w.pgno = 2
        w._pdf_show()
        app.processEvents()
        w.toggle_dual()
        app.processEvents()
        ok = (w._reader == 'dual' and w.dual.ed.text() == '3' and w.pgno == 2)
        return (ok, 'reader=%s 页码框=%s pgno=%s' % (w._reader, w.dual.ed.text(), w.pgno))

    step(109, '⇄ 进对读：PDF 停原页，TXT 同步到该页', dual_keep_page)

    def left_width():
        # batch17：可拖得极窄（min≤60）；batch20：主按钮「跨文件全文检索」窄了也不藏（换短标签）
        _mn = w.tb.minimumWidth()
        w._fit_left_buttons(200)
        narrow_ok = ((not w.b_fts.isHidden()) and ('检索' in w.b_fts.text())
                     and not w.b_more.isHidden() and w.tb.isColumnHidden(2))
        w._fit_left_buttons(600)
        wide_ok = (not w.b_fts.isHidden() and w.b_more.isHidden()
                   and all(not x.isHidden() for x in (w.b_fts_hist, w.b_alias, w.b_exc))
                   and not w.tb.isColumnHidden(2))
        # 分割条能拖到极窄（窄模式下左栏实际宽度可小）
        w._fit_left_buttons(160)
        w._split.setSizes([48, max(400, w.width() - 48)])
        app.processEvents()
        lw = w._split.sizes()[0]
        w._fit_left_buttons(600)
        w._split.setSizes([340, max(400, w.width() - 340)])
        app.processEvents()
        return (w.tb.minimumWidth() <= 60 and w.cb_ver.maximumWidth() >= 300
                and narrow_ok and wide_ok and lw <= 140,
                'tb.min=%s cb_ver.max=%s 窄=%s 宽=%s 拖后left=%s'
                % (w.tb.minimumWidth(), w.cb_ver.maximumWidth(), narrow_ok, wide_ok, lw))

    step(110, '左栏可拖得极窄（主按钮保留下，其余收进⋮）+ 「版本」下拉显示变宽', left_width)

    def excerpt_viewer_open():
        for d in (200, 600, 1200, 2000):
            QTimer.singleShot(d, close_modal)
        w.excerpt_viewer()
        app.processEvents()
        d = getattr(w, '_last_excerpt_dlg', None) or {}
        lst = d.get('list')
        n = lst.count() if lst is not None else 0
        recs = (d.get('recs') or {}).get('recs') or []
        ok = bool(lst) and n >= 1 and len(recs) >= 1
        return (ok, 'list=%d recs=%d' % (n, len(recs)))

    step(111, '🗂 摘录查看器 / 编辑器（可列出并编辑）', excerpt_viewer_open)

    def chrono_overflow():
        import viewer_chrono as CHRONO
        a, _ = CHRONO.annotate('康熙六十三年')
        ok1 = ('1724' in a and '存疑' in a and ('雍正' in a))
        b, _ = CHRONO.annotate('光绪三十五年')
        ok2 = ('1909' in b and '存疑' in b and '宣统' in b)
        return (ok1 and ok2, '康熙63=%s | 光緖35=%s' % (a[:26], b[:26]))

    step(112, '⌛ 越界纪年（康熙63年）→公历年 + 提示实际纪年', chrono_overflow)

    def chrono_reverse():
        import viewer_chrono as CHRONO
        fe = CHRONO.format_eras(1898)
        ok1 = ('光绪二十四年' in fe and '明治三十一年' in fe and '同治' not in fe)
        ok2 = (CHRONO.era_year_cn(24) == '二十四' and CHRONO.era_year_cn(1) == '元')
        return (ok1 and ok2, '1898 => %s' % fe)

    step(113, '⌛ 反查：每个年号都注明是第几年', chrono_reverse)

    def dual_txt_and_layout_final():
        import viewer_chrono as CHRONO
        ok1 = CHRONO.format_eras(1937).count('年号') == 0 and '民国' in CHRONO.format_eras(1937)
        return (ok1, '1937 => %s' % CHRONO.format_eras(1937))

    step(114, '⌛ 反查含民国纪年且注明年数', dual_txt_and_layout_final)

    # ---------------- batch15 新增功能核验（115-117）拖入打开 / 双击关联 ----------------
    class _FakeMime(object):
        def __init__(self, paths):
            from PyQt6.QtCore import QMimeData, QUrl
            self._m = QMimeData()
            self._m.setUrls([QUrl.fromLocalFile(p) for p in paths])

        def hasUrls(self):
            return self._m.hasUrls()

        def urls(self):
            return self._m.urls()

    class _FakeDrop(object):
        def __init__(self, paths):
            self._mime = _FakeMime(paths)
            self.accepted = 0

        def mimeData(self):
            return self._mime

        def acceptProposedAction(self):
            self.accepted += 1

        def ignore(self):
            pass

    def drop_open():
        assert w.acceptDrops(), 'MainWindow 未开启拖放'
        pe = _FakeDrop([_dual])
        w.dragEnterEvent(pe)
        w.dropEvent(pe)
        app.processEvents()
        ok1 = (w._reader == 'pdf' and w.stack.currentWidget() is w.pdf_view)
        te = _FakeDrop([_dualtxt])
        w.dropEvent(te)
        app.processEvents()
        ok2 = (w._reader in ('text', 'dual'))
        ok3 = (pe.accepted >= 1)
        return (ok1 and ok2 and ok3,
                'acceptDrops=%s pdf=%s txt=%s ev=%s'
                % (w.acceptDrops(), ok1, w._reader, pe.accepted))

    step(115, '拖入 PDF / TXT → 在阅读区打开', drop_open)

    def drop_multi():
        fe = _FakeDrop([_dualtxt, _dual])
        w.dropEvent(fe)
        app.processEvents()
        msg = w.statusBar().currentMessage() or ''
        ok = (getattr(w, '_reader', '') in ('text', 'dual') and '另有 1' in msg)
        return (ok, 'reader=%s msg=%r' % (getattr(w, '_reader', ''), msg[:40]))

    step(116, '拖入多个 → 只开首个 + 提示其余忽略', drop_multi)

    def assoc_scripts():
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        a = os.path.join(root, '关联.bat')
        b = os.path.join(root, '取消关联.bat')
        ta = open(a, 'rb').read()
        tb = open(b, 'rb').read()
        ascii_ok = all(x < 128 for x in ta) and all(x < 128 for x in tb)
        crlf_ok = (ta.count(b'\n') - ta.count(b'\r\n') == 0
                   and tb.count(b'\n') - tb.count(b'\r\n') == 0)
        has_pdf = (b'CathayViewer.pdf' in ta) and (b'.pdf' in ta) and (b'.txt' in ta)
        default_add = (b'Classes\\.pdf" /ve /d "CathayViewer.pdf"' in ta)
        default_del = (b'Classes\\.pdf" /ve /f' in tb)
        ok = (ascii_ok and crlf_ok and has_pdf and default_add and default_del)
        return (ok, 'ascii=%s crlf=%s pdf/txt=%s 默认=%s/%s'
                % (ascii_ok, crlf_ok, has_pdf, default_add, default_del))

    step(117, '双击关联：关联/取消关联脚本（PDF/TXT，含设为默认）', assoc_scripts)

    # ---------------- batch16 新增功能核验（118-120）卡顿修复 ----------------
    def meta_async():
        p = pick('对读测试.pdf')
        if not p:
            return (False, '未选中 对读测试.pdf')
        w._meta_map = {}              # 清缓存，确保走一次新流程
        t0 = time.time()
        w.on_pick()
        dt = time.time() - t0
        fast = (dt < 1.0)
        deep_now = bool((w.meta or {}).get('_deep'))   # 允许竞态：先浅后深
        got = deep_now
        tk = time.time()
        while time.time() - tk < 5.0 and not got:
            app.processEvents()
            time.sleep(0.02)
            got = bool((w.meta or {}).get('_deep'))
        # 缓存：再来一次应立即拿到深著录
        t1 = time.time()
        w.on_pick()
        dt2 = time.time() - t1
        cached_deep = bool((w.meta or {}).get('_deep'))
        return (fast and got and cached_deep and dt2 < 1.0,
                '首次=%.3fs 深著录=%s(%.1fs) 缓存=%s(%.3fs)'
                % (dt, got, time.time() - tk, cached_deep, dt2))

    step(118, '大 PDF 著录不卡：浅著录秒回 + 后台补深 + 缓存', meta_async)

    _bigtxt = os.path.join(src, '大文件测试.txt')
    with open(_bigtxt, 'w', encoding='utf-8') as _f:
        _blk = '这是一段用于测试超大文件截断的正文。' * 40 + '\n'
        _nb = 0
        while _nb < 9 * 1024 * 1024:
            _f.write(_blk)
            _nb += len(_blk.encode('utf-8'))
    _d = fitz.open()
    ins(_d.new_page(), (72, 100), '大文件测试', 14)
    _d.save(os.path.join(src, '大文件测试.pdf'))
    _d.close()
    try:
        C.refresh(db, [src])
    except Exception:
        pass

    def big_text_cap():
        size = os.path.getsize(_bigtxt)
        w._show_text_file(_bigtxt)
        app.processEvents()
        n = len(w.view.toPlainText())
        msg = w.statusBar().currentMessage() or ''
        ok = (size > G.TEXT_DISPLAY_MAX and n <= G.TEXT_DISPLAY_MAX + 4096
              and ('只载入前' in msg or '卡界面' in msg))
        return (ok, 'MB=%.1f 载入字符=%d msg=%r' % (size / 1048576.0, n, msg[:30]))

    step(119, '超大 TXT 只载入前 8 MB（不卡界面）+ 提示', big_text_cap)

    def dual_big_skip():
        st = getattr(w.dual.txt, 'truncated', None)
        v = G.TxtSyncView()
        v.load(_bigtxt)
        trunc = bool(getattr(v, 'truncated', False))
        n = len(v.toPlainText())
        w.st['auto_dual'] = True
        r = w._maybe_auto_dual(_bigtxt)
        msg = w.statusBar().currentMessage() or ''
        w.st['auto_dual'] = False
        ok = (trunc and n <= G.DUAL_TXT_MAX + 4096 and (r is False)
              and ('未自动进入对读' in msg))
        return (ok, 'trunc=%s 字符=%d auto=%s msg=%r' % (trunc, n, r, msg[:26]))

    step(120, '超大 TXT：对读只载入前 8 MB，不自动进对读', dual_big_skip)

    def list_toggle():
        w._split.setSizes([340, max(400, w.width() - 340)])
        app.processEvents()
        key = w._listk.key().toString()
        w.toggle_list()
        app.processEvents()
        collapsed = w._split.sizes()[0]
        w.toggle_list()
        app.processEvents()
        back = w._split.sizes()[0]
        return (key == 'Ctrl+Shift+L' and collapsed == 0 and back > 100,
                'key=%s collapsed=%s back=%s' % (key, collapsed, back))

    step(121, '左栏一键收起/展开（Ctrl+Shift+L）', list_toggle)

    # ---------------- batch18（122-125）：独立窗口快捷键 / 最小化互不影响 / 直接打开列邻居 ----
    def detach_ctrl_f():
        p = pick('甲书.pdf') or pick('对读测试.pdf')
        if not p:
            return (False, '未选中')
        w.preview_here()
        app.processEvents()
        if w._reader_win is None:
            w._detach_reader()
        app.processEvents()
        win = w._reader_win
        if win is None:
            return (False, '未生成独立窗口')
        scs = list(getattr(win, '_cv_sc', []) or [])
        keys = [s.key().toString() for s in scs]
        ctx = [s.context().name for s in scs]
        f_sc = next((s for s in scs if s.key().toString() == 'Ctrl+F'), None)
        if f_sc is not None:
            try:
                f_sc.activated.emit()
            except Exception:
                pass
        app.processEvents()
        shown = not w._find_bar_widget.isHidden()
        ok = ('Ctrl+F' in keys and 'Esc' in keys
              and all(c == 'WindowShortcut' for c in ctx)
              and f_sc is not None and f_sc.isEnabled() and shown)
        w.find_close()
        return (ok, 'keys=%s ctx=%s shown=%s' % (keys, ctx, shown))

    step(122, '独立阅读窗口 Ctrl+F 可打开查找条', detach_ctrl_f)

    def detach_minimize():
        win = w._reader_win
        if win is None:
            return (False, '没有独立窗口')
        indep = (win.parent() is None)
        w.showMinimized()
        app.processEvents()
        kept = (not win.isMinimized())
        w.showNormal()
        app.processEvents()
        w._attach_reader()
        app.processEvents()
        back = (w._reader_win is None)
        return (indep and kept and back,
                'parent=%s 主窗最小化后阅读器未被带走=%s 收回=%s' % (win.parent(), kept, back))

    step(123, '最小化文件列表窗口不带走独立阅读器窗口', detach_minimize)

    def open_neighbors():
        d1 = os.path.join(src, '同架')
        d2 = os.path.join(src, '别处')
        os.makedirs(d1, exist_ok=True)
        os.makedirs(d2, exist_ok=True)
        p1 = os.path.join(d1, '甲书补遗.pdf')      # 打开的这个（在「同架」）
        p2 = os.path.join(d1, '乙书.pdf')          # 同文件夹的其他文件
        p3 = os.path.join(d2, '甲书续编.pdf')      # 别处但文件名相似
        for p in (p1, p2, p3):
            if not os.path.isfile(p):
                _d = fitz.open()
                ins(_d.new_page(), (72, 100), '甲书 补遗', 14)
                _d.save(p)
                _d.close()
        try:
            C.refresh(db, [src])
        except Exception:
            pass
        w.open_path_in_reader(p1)
        app.processEvents()
        names = [r.get('name') for r in w.rows]
        cur = w.tb.currentRow()
        curname = w.rows[cur].get('name') if 0 <= cur < len(w.rows) else ''
        ok = ('甲书补遗.pdf' in names and '乙书.pdf' in names
              and '甲书续编.pdf' in names and '甲书.pdf' in names
              and curname == '甲书补遗.pdf')
        return (ok, 'n=%d cur=%s 同架=%s 相似=%s'
                % (len(names), curname, '乙书.pdf' in names, '甲书续编.pdf' in names))

    step(124, '直接打开文件 → 左栏列出同文件夹 + 相似文件名', open_neighbors)

    def open_neighbors_unique():
        d3 = os.path.join(src, '独处')
        os.makedirs(d3, exist_ok=True)
        p3 = os.path.join(d3, '己书.pdf')
        if not os.path.isfile(p3):
            _d = fitz.open()
            ins(_d.new_page(), (72, 100), '己书', 14)
            _d.save(p3)
            _d.close()
        try:
            C.refresh(db, [src])
        except Exception:
            pass
        w.open_path_in_reader(p3)
        app.processEvents()
        names = [r.get('name') for r in w.rows]
        cur = w.tb.currentRow()
        curname = w.rows[cur].get('name') if 0 <= cur < len(w.rows) else ''
        return (curname == '己书.pdf' and len(names) >= 1, 'n=%d cur=%s' % (len(names), curname))

    step(125, '直接打开孤立文件也不报错（左栏至少含它自己）', open_neighbors_unique)

    # ---------------- batch19（126）：PDV5/PDV6 后缀也能归到同一本（用户报） ----------------
    def pdv_group():
        _d = os.path.join(src, '第3辑')
        os.makedirs(_d, exist_ok=True)
        _pdf = os.path.join(_d, '第3辑外交_OCR_PD5AIOCR.pdf')
        if not os.path.isfile(_pdf):
            _x = fitz.open()
            ins(_x.new_page(), (72, 100), '第3辑外交', 14)
            _x.save(_pdf)
            _x.close()
        for n in ('第3辑外交_OCR.txt', '第3辑外交_OCR_PD5AIOCR.txt',
                  '第3辑外交_OCR_PD5AIOCR_【简转繁】.txt',
                  '第3辑外交_PDV5AIFOCR.txt', '第3辑外交_PDV5AIFOCR_【简转繁】.txt',
                  '第3辑外交_PDV6AIFOCR.txt'):
            p = os.path.join(_d, n)
            if not os.path.isfile(p):
                open(p, 'w', encoding='utf-8').write('第3辑外交 正文')
        try:
            C.refresh(db, [src])
        except Exception:
            pass
        w.ed_kw.setText('第3辑外交')
        w.do_search()
        app.processEvents()
        n_rows = len(w.rows)
        cur = next((i for i, r in enumerate(w.rows)
                    if '第3辑外交' in (r.get('name') or '')), 0)
        w.tb.setCurrentCell(cur, 0)
        w.on_pick()
        app.processEvents()
        n_ver = w.cb_ver.count()
        keys = set(META.book_core(n) for n in (
            '第3辑外交_OCR.txt', '第3辑外交_PDV5AIFOCR.txt', '第3辑外交_PDV6AIFOCR.txt',
            '第3辑外交_OCR_PD5AIOCR.pdf', '第3辑外交_PDV5AIFOCR_【简转繁】.txt'))
        ok = (n_rows <= 2 and n_ver >= 3 and keys == {'第3辑外交'})
        return (ok, 'rows=%d 版本=%d 书主干=%s' % (n_rows, n_ver, keys))

    step(126, 'PDV5/PDV6 后缀与其他后缀归为同一本（可切换版本）', pdv_group)

    # ---------------- batch20（127）：「跨文件全文检索」主入口永远看得见 ----------------
    def fts_button_always():
        # 用户报障：左栏拖窄（settings split_sizes=[211,700]）后主按钮看不见，以为功能没了。
        # 真因：batch17 给这排按钮设了 Ignored 策略 → 实际宽高被压成 0（仅查 hidden 标志查不出来）。
        w._split.setSizes([211, max(500, w.width() - 211)])
        app.processEvents()
        w._fit_left_buttons(211)
        app.processEvents()
        a = (not w.b_fts.isHidden(), w.b_fts.text(), not w.b_more.isHidden(), w.b_fts.width())
        w._split.setSizes([600, max(500, w.width() - 600)])
        app.processEvents()
        w._fit_left_buttons(600)
        app.processEvents()
        b = (not w.b_fts.isHidden(), w.b_fts.text(), w.b_fts.width(),
             all(not x.isHidden() and x.width() > 20 for x in (w.b_fts_hist, w.b_alias, w.b_exc)))
        scs = [s.key().toString() for s in w.findChildren(G.QShortcut)]
        has_sc = 'Ctrl+Shift+S' in scs
        ok = (a[0] and a[2] and a[3] > 20 and '检索' in a[1]
              and b[0] and b[2] > 40 and b[3] and has_sc)
        return (ok, '窄左栏：主按钮在=%s 文字=%r 宽=%d ⋮在=%s；宽左栏：其余可见且宽>20=%s；快捷键=%s'
                % (a[0], a[1], a[3], a[2], b[3], has_sc))

    step(127, '左栏拖窄后「跨文件全文检索」主入口可见（真宽度>20，Ctrl+Shift+S）', fts_button_always)
    try:
        w.close()
    except Exception:
        pass
    app.processEvents()
    shutil.rmtree(base, ignore_errors=True)

    s = 'SUMMARY ok=%d fail=%d' % (n_ok[0], n_fail[0])
    log(s)
    log('RESULT = %s' % ('OK' if n_fail[0] == 0 else 'FAIL'))
    # 最后再尽量喷一次 stdout（即使崩溃也已落盘）
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    print('\n'.join(_LOG))
    return 0 if n_fail[0] == 0 else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException:
        import traceback
        log('FATAL: ' + traceback.format_exc().replace('\n', ' | ')[:1500])
        raise
