# -*- coding: utf-8 -*-
"""CathayViewer 阅读流畅度性能诊断（batch6）。

真平台（QT_QPA_PLATFORM=windows）+ 真 MainWindow + 合成 200 页 PDF，量化：
  1) 打开到首屏可看的耗时；
  2) 同一页渲染次数（滚动来回 3 次后是否仍为 1，验证缓存复用）；
  3) 连续滚动到底过程中的单步最大耗时（滚动回调里是否有 >100ms 长阻塞）；
  4) 已缓存页数（当前页 ±2 及以上，验证预取）。
结果写 开发\\性能诊断_结果.txt，同时在 stdout 打印。

只读不动源库；临时目录跑完即删。
"""
import io
import os
import shutil
import sys
import tempfile
import time

os.environ['QT_QPA_PLATFORM'] = 'windows'          # 必须在 import PyQt6 / gui 之前

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
OUT = os.path.join(HERE, '性能诊断_结果.txt')
_L = []

PAGES = 200
BUDGET_MS = 100.0                                   # 单步耗时预算


def log(s):
    _L.append(str(s))
    try:
        with open(OUT, 'w', encoding='utf-8') as f:
            f.write('\n'.join(_L) + '\n')
    except Exception:
        pass


def cjk_font():
    for f in (r'C:\Windows\Fonts\msyh.ttc', r'C:\Windows\Fonts\simsun.ttc',
              r'C:\Windows\Fonts\simhei.ttf'):
        if os.path.isfile(f):
            return f
    return ''


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    import viewer_core as C
    import fitz

    base = tempfile.mkdtemp(prefix='cv_perf_')
    cfg = os.path.join(base, 'cfg')
    os.makedirs(cfg, exist_ok=True)
    C.app_dir = lambda: cfg
    C.settings_path = lambda: os.path.join(cfg, 'cathayviewer_settings.json')

    src = os.path.join(base, '书库')
    os.makedirs(src, exist_ok=True)
    pdfp = os.path.join(src, '性能测试_%d页.pdf' % PAGES)
    FONT = cjk_font()
    doc = fitz.open()
    t_gen0 = time.perf_counter()
    for i in range(PAGES):
        pg = doc.new_page()
        if FONT:
            pg.insert_text((60, 90), '性能测试 第 %d 页' % (i + 1),
                           fontsize=20, fontname='cjk', fontfile=FONT)
            for k in range(18):
                pg.insert_text((60, 130 + k * 34),
                               '第 %d 页 第 %d 行：连续滚动、缓存复用与缩放记账的基准测试文本。'
                               % (i + 1, k + 1), fontsize=12, fontname='cjk', fontfile=FONT)
        else:
            pg.insert_text((60, 90), 'page %d' % (i + 1), fontsize=20)
    toc = [[1, '第 %d 节' % j, 1 + (j - 1) * (PAGES // 10)] for j in range(1, 11)]
    doc.set_toc(toc)
    doc.save(pdfp)
    doc.close()
    gen_ms = (time.perf_counter() - t_gen0) * 1000

    db = os.path.join(base, 'idx.db')
    C.build([src], db)
    C.save_settings({'primary_db': db, 'roots': [src]})

    import gui as G
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    w = G.MainWindow(C.load_settings())
    w.show()
    app.processEvents()

    log('== CathayViewer 阅读流畅度性能诊断 ==')
    log('合成 PDF：%d 页（生成耗时 %.0f ms）｜ 源：%s'
        % (PAGES, gen_ms, os.path.basename(pdfp)))

    # ---------- 打开到首屏可看 ----------
    w.ed_kw.setText('性能测试')
    w.do_search()
    app.processEvents()
    ti = next((i for i, r in enumerate(w.rows)
               if (r.get('name') or '').lower().endswith('.pdf')), -1)
    if ti < 0:
        log('FAIL：库里没找到合成 PDF')
        return 1
    w.tb.setCurrentCell(ti, 0)
    w.on_pick()
    app.processEvents()

    t0 = time.perf_counter()
    w.preview_here()
    # 首屏可看 = 已插入首页且首页位图已渲染进缓存
    app.processEvents()
    open_ms = (time.perf_counter() - t0) * 1000
    first_ok = (w.pd is not None and w._inserted >= 1 and len(w._page_pixmaps) >= 1)
    log('1) 打开到首屏可看：%.0f ms（首屏已渲染=%s，已载入 %d 页，缩放 %s %d%%）'
        % (open_ms, first_ok, w._inserted, w._zoom_label(),
           round(100 * w._zoom_factor())))

    # ---------- 同一页渲染次数（滚动来回 3 次） ----------
    sb = w.view.verticalScrollBar()
    before = dict(w._render_count)
    for _ in range(3):
        sb.setValue(0)
        app.processEvents()
        sb.setValue(sb.maximum() // 2)
        app.processEvents()
        sb.setValue(sb.maximum())
        app.processEvents()
    after = dict(w._render_count)
    reuse = all(after.get(k) == v for k, v in before.items())   # 已渲染页不被重复渲染
    max_once = max(after.values()) if after else 0
    log('2) 同一页渲染次数：滚动来回 3 次后 max=%d（已缓存页无重复渲染=%s，缓存页数=%d）'
        % (max_once, reuse, len(after)))

    # ---------- 连续滚动到底：单步最大耗时 ----------
    w.pdf_home()
    app.processEvents()
    total = int(w.pd.page_count)
    sb = w.view.verticalScrollBar()
    maxt = 0.0
    maxt_cb = 0.0
    steps = 0
    t_all0 = time.perf_counter()
    while steps < 400:
        # 仅测滚动回调（同步信号）本身的耗时
        t_cb = time.perf_counter()
        sb.setValue(sb.maximum())
        maxt_cb = max(maxt_cb, (time.perf_counter() - t_cb) * 1000)
        # 加上定时器里的续插/渲染（事件循环走一圈）
        t0 = time.perf_counter()
        app.processEvents()
        dt = (time.perf_counter() - t0) * 1000
        maxt = max(maxt, dt)
        steps += 1
        if w._inserted >= total and sb.value() >= sb.maximum() - 1:
            break
    scroll_ms = (time.perf_counter() - t_all0) * 1000
    log('3) 连续滚动到底：单步最大耗时 = %.0f ms（滚动回调本体最大 %.0f ms）'
        % (maxt, maxt_cb))
    log('     步数=%d，累计 %.0f ms，平均 %.0f ms/步；预算 %.0f ms → %s'
        % (steps, scroll_ms, scroll_ms / max(1, steps), BUDGET_MS,
           '达标' if maxt < BUDGET_MS else '超预算'))

    # ---------- 已缓存页数（预取 当前页 ±2） ----------
    app.processEvents()
    cur = int(w.pgno)
    keys = set(int(k) for k in w._page_pixmaps.keys())
    ring = [p for p in range(max(0, cur - 2), min(total, cur + 3))]
    ring_ok = all(p in keys for p in ring)
    log('4) 已缓存页数 = %d ｜ 当前页=%d（1 基）±2 命中=%s ｜ 覆盖 %s'
        % (len(keys), cur + 1, ring_ok,
           ('[%d..%d]' % (min(keys), max(keys))) if keys else '[]'))
    log('   预取结论：当前页 ±2 及以上%s' % ('已缓存' if ring_ok else '未完全缓存'))

    # ---------- 渲染总量核对 ----------
    log('   总渲染次数 = %d（已插页 %d / 总 %d）｜ 每页最多渲染 %d 次'
        % (sum(w._render_count.values()), w._inserted, total,
           max(w._render_count.values()) if w._render_count else 0))

    verdict = (first_ok and reuse and max_once <= 1
               and maxt < BUDGET_MS and ring_ok)
    log('SUMMARY %s ｜ 打开 %.0f ms ｜ 单步最大 %.0f ms ｜ 缓存 %d 页'
        % ('PASS' if verdict else 'CHECK', open_ms, maxt, len(keys)))

    try:
        w.close()
    except Exception:
        pass
    app.processEvents()
    shutil.rmtree(base, ignore_errors=True)
    print('\n'.join(_L))
    return 0 if verdict else 2


if __name__ == '__main__':
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException:
        import traceback
        log('FATAL: ' + traceback.format_exc().replace('\n', ' | ')[:1500])
        raise
