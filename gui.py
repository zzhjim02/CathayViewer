# -*- coding: utf-8 -*-
"""CathayViewer · 学术书库浏览与阅读 —— 界面（首启向导 + 主窗口）

只读原则：所有库都以 mode=ro 打开；源书库一个字节都不写。
"""
import io
import json
import os
import re
import sys
import time
import traceback
from bisect import bisect_right

_FULL_SCAN_MAX = 200      # batch16：PDF 深著录最多全文扫描的页数（超过则只用前后采样）

from PyQt6.QtCore import (Qt, QEvent, QPoint, QProcess, QRect, QSize, QThread, QTimer,
                         QUrl, pyqtSignal)
from PyQt6.QtGui import (QColor, QFont, QFontMetrics, QIcon, QImage, QKeySequence, QPainter,
                         QPalette, QPen, QPixmap, QShortcut, QTextBlockFormat, QTextCursor,
                         QTextDocument, QTextImageFormat)
from PyQt6.QtWidgets import (QApplication, QAbstractScrollArea, QCheckBox, QComboBox, QDialog,
                             QDockWidget, QFileDialog,
                             QGroupBox, QSpinBox, QScrollArea, QMenu, QStyle,
                             QStyledItemDelegate, QStyleOptionViewItem,
                             QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget,
                             QListWidgetItem,
                             QMainWindow, QMessageBox, QProgressBar, QPushButton,
                             QRadioButton, QSplitter, QStackedWidget, QTableWidget,
                             QTableWidgetItem, QTabWidget, QTextEdit, QTreeWidget, QTreeWidgetItem,
                             QVBoxLayout, QWidget)

JSON_MAX_BYTES = 20 * 1024 * 1024    # JSON 树：超过此大小回退纯文本（或 ijson 流式）
TEXT_MAX_BYTES = 64 * 1024 * 1024    # 文本阅读上限：超过只载入前 64 MB（状态栏提示，不静默丢弃）
TEXT_DISPLAY_MAX = 8 * 1024 * 1024   # batch16：普通文本阅读最多载入前 8 MB（大 TXT 不再卡界面）
DUAL_TXT_MAX = 8 * 1024 * 1024       # batch16：对读 TXT 最多载入前 8 MB
DUAL_AUTO_MAX = 64 * 1024 * 1024     # batch16：TXT 超过此大小不自动进对读（只提示）
# 可直接拖入 / 双击在阅读区打开的扩展名
READER_EXTS = ('.pdf', '.txt', '.text', '.md', '.epub', '.json', '.csv')

import viewer_core as C
import viewer_meta as META
import viewer_tools as TOOLS
import viewer_chrono as CHRONO
import viewer_alias as ALIAS

APP_TITLE = C.APP_TITLE
APP_VERSION = C.APP_VERSION
TIP_EXAMPLE = '（下面两行只是示例，可改成你自己的目录）'


def icon_path():
    for p in (os.path.join(getattr(sys, '_MEIPASS', ''), 'app.ico'),
              os.path.join(C.app_dir(), 'app.ico')):
        if p and os.path.isfile(p):
            return p
    return ''


class BuildWorker(QThread):
    prog = pyqtSignal(dict)
    done = pyqtSignal(dict)
    fail = pyqtSignal(str)

    def __init__(self, roots, db, copy_to, exts, fresh=True):
        super().__init__()
        self.roots, self.db, self.copy_to, self.exts = roots, db, copy_to, exts
        self.fresh = fresh
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        try:
            fn = C.build if self.fresh else C.refresh
            kw = {'exts': self.exts, 'cancel': lambda: self._stop,
                  'on_progress': lambda p: self.prog.emit(p), 'copy_to': self.copy_to}
            r = fn(self.roots, self.db, **kw) if self.fresh else fn(self.db, self.roots, **kw)
            self.done.emit(r)
        except Exception as e:
            self.fail.emit('%s: %s' % (type(e).__name__, e))


class MetaWorker(QThread):
    """batch16：深著录解析放后台线程（大 PDF 读文字层可达 10s，不能卡 UI）。"""
    done = pyqtSignal(str, float, object)     # path, mtime, meta

    def __init__(self, name, path, mtime, parent=None):
        super().__init__(parent)
        self._n, self._p, self._t = name, path, mtime

    def run(self):
        m = None
        try:
            m = META.parse(self._n or '', self._p)
        except Exception:
            m = None
        try:
            self.done.emit(self._p, float(self._t), m)
        except Exception:
            pass


class Wizard(QDialog):
    """首启向导：① 选目录 ② 选库（自建 / 用已有） ③ 建库进度"""

    def __init__(self, parent=None, settings=None, first_run=True):
        super().__init__(parent)
        self.setWindowTitle(('第一次使用 —— ' if first_run else '') + '建立文件名索引')
        self.resize(760, 520)
        self.st = settings or C.load_settings()
        self.result_info = None
        self.worker = None

        self.stack = QStackedWidget()
        self.stack.addWidget(self._page1())
        self.stack.addWidget(self._page2())
        self.stack.addWidget(self._page3())
        lay = QVBoxLayout(self)
        self.lb_head = QLabel('<b>① 选要索引的文件夹</b>')
        lay.addWidget(self.lb_head)
        lay.addWidget(self.stack)
        row = QHBoxLayout()
        self.b_back = QPushButton('← 上一步')
        self.b_next = QPushButton('下一步 →')
        self.b_back.clicked.connect(self._back)
        self.b_next.clicked.connect(self._next)
        row.addStretch(1)
        row.addWidget(self.b_back)
        row.addWidget(self.b_next)
        lay.addLayout(row)
        self._sync()
        if icon_path():
            from PyQt6.QtGui import QIcon
            self.setWindowIcon(QIcon(icon_path()))

    # ---- 页 1：目录
    def _page1(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(QLabel('要索引的书库目录（含子文件夹、孙文件夹）：\n'
                           '<span style="color:#b8860b">%s</span>' % TIP_EXAMPLE))
        self.lst = QListWidget()
        self.lst.setAcceptDrops(True)
        for r in (self.st.get('roots') or C.DEFAULT_ROOTS):
            self.lst.addItem(r)
        v.addWidget(self.lst, 1)
        row = QHBoxLayout()
        b1 = QPushButton('添加文件夹…')
        b2 = QPushButton('移除选中')
        b1.clicked.connect(self._add_dir)
        b2.clicked.connect(lambda: [self.lst.takeItem(i.row())
                                    for i in sorted(self.lst.selectedIndexes(),
                                                    key=lambda x: -x.row())])
        row.addWidget(b1)
        row.addWidget(b2)
        row.addStretch(1)
        v.addLayout(row)
        v.addWidget(QLabel('提示：本地盘 / 移动硬盘 / 网络盘都可以；移动盘换盘符也能认回来。'))
        return w

    def _add_dir(self):
        d = QFileDialog.getExistingDirectory(self, '选要索引的文件夹')
        if d:
            self.lst.addItem(d)

    # ---- 页 2：库
    def _page2(self):
        w = QWidget()
        v = QVBoxLayout(w)
        g = QGroupBox('索引库')
        gv = QVBoxLayout(g)
        self.rb_new = QRadioButton('自建新库（推荐）—— 扫描上面的目录，生成一份文件名索引')
        self.rb_use = QRadioButton('直接用已有的索引库（只读，不改它）'
                                   ' —— 比如别人给的 .db 或另一台机器建的')
        gv.addWidget(self.rb_new)
        gv.addWidget(self.rb_use)
        row = QHBoxLayout()
        self.ed_db = QLineEdit(self.st.get('primary_db') or '')
        b = QPushButton('浏览…')
        b.clicked.connect(self._pick_db)
        row.addWidget(QLabel('主库位置'))
        row.addWidget(self.ed_db, 1)
        row.addWidget(b)
        gv.addLayout(row)
        row2 = QHBoxLayout()
        self.ed_bk = QLineEdit(self.st.get('backup_db') or '')
        b2 = QPushButton('浏览…')
        b2.clicked.connect(self._pick_bk)
        row2.addWidget(QLabel('备查位置'))
        row2.addWidget(self.ed_bk, 1)
        row2.addWidget(b2)
        gv.addLayout(row2)
        gv.addWidget(QLabel('<span style="color:#666">备查位置留空也行；它只当副本，'
                            '主库不可用时自动改读它（比如移动硬盘没插）。</span>'))
        v.addWidget(g)
        v.addWidget(QLabel('<span style="color:#666">“直接用已有的库”支持：本软件的索引库、'
                           'CathayIndex 的 local_files.db。认不出的库会明确提示。</span>'))
        self.rb_new.setChecked(True)
        v.addStretch(1)
        return w

    def _pick_db(self):
        p, _ = QFileDialog.getSaveFileName(self, '索引库放哪儿（.db）',
                                           self.ed_db.text() or 'cathayviewer_index.db',
                                           '索引库 (*.db)')
        if p:
            self.ed_db.setText(p)

    def _pick_bk(self):
        p, _ = QFileDialog.getSaveFileName(self, '备查位置（可留空）',
                                           self.ed_bk.text() or 'index_backup.db',
                                           '索引库 (*.db)')
        if p:
            self.ed_bk.setText(p)

    # ---- 页 3：进度
    def _page3(self):
        w = QWidget()
        v = QVBoxLayout(w)
        self.lb_run = QLabel('准备好后点「开始建库」')
        self.pb = QProgressBar()
        self.pb.setRange(0, 0)
        self.pb.setVisible(False)
        self.tx = QTextEdit()
        self.tx.setReadOnly(True)
        v.addWidget(self.lb_run)
        v.addWidget(self.pb)
        v.addWidget(self.tx, 1)
        return w

    # ---- 导航
    def _sync(self):
        i = self.stack.currentIndex()
        self.lb_head.setText(['<b>① 选要索引的文件夹</b>',
                              '<b>② 选索引库放哪儿</b>',
                              '<b>③ 开始建库</b>'][i])
        self.b_back.setEnabled(i > 0 and not self._busy())
        self.b_next.setText('开始建库' if i == 2 else '下一步 →')
        self.b_next.setEnabled(not self._busy())

    def _busy(self):
        return bool(self.worker and self.worker.isRunning())

    def _back(self):
        if not self._busy():
            self.stack.setCurrentIndex(max(0, self.stack.currentIndex() - 1))
            self._sync()

    def _next(self):
        i = self.stack.currentIndex()
        if i < 2:
            self.stack.setCurrentIndex(i + 1)
            self._sync()
            return
        self._start()

    def _start(self):
        if self._busy():
            return
        roots = [self.lst.item(k).text() for k in range(self.lst.count())]
        db = self.ed_db.text().strip()
        if self.rb_use.isChecked():
            if not os.path.isfile(db):
                QMessageBox.warning(self, '提示', '这个索引库文件不存在：\n%s' % db)
                return
            kind = C.detect_db(db)
            if not kind:
                QMessageBox.warning(self, '提示',
                                    '这个库我读不了（不认识的库型）。\n'
                                    '支持：本软件的索引库、CathayIndex 的 local_files.db')
                return
            self.result_info = {'used_existing': True, 'db': db, 'kind': kind}
            self.accept()
            return
        if not roots:
            QMessageBox.warning(self, '提示', '至少加一个要索引的文件夹。')
            return
        self.pb.setVisible(True)
        self.lb_run.setText('正在扫描…（只读，不会改动源书库）')
        self._sync()
        self.worker = BuildWorker(roots, db, self.ed_bk.text().strip(),
                                  C.EXTS, fresh=True)
        self.worker.prog.connect(self._on_prog)
        self.worker.done.connect(self._on_done)
        self.worker.fail.connect(self._on_fail)
        self.worker.start()
        self.b_stop = QPushButton('停止')
        self.b_stop.clicked.connect(lambda: self.worker and self.worker.stop())
        self.layout().addWidget(self.b_stop)

    def _on_prog(self, p):
        if p.get('stage') == 'scan':
            self.tx.append('已扫 %s 个文件…  %s' % (p.get('n'), p.get('dir', '')[:70]))
        elif p.get('stage') == 'skip':
            self.tx.append('跳过（目录不存在）：%s' % p.get('root'))

    def _on_done(self, r):
        self.pb.setVisible(False)
        mb = r.get('files', 0) * 1.8 / 1024.0
        self.lb_run.setText('建库完成 ✓')
        self.tx.append('共 %s 个文件，索引约 %.1f MB，用时 %ss\n库：%s'
                       % (r.get('files'), mb, r.get('secs'), r.get('db')))
        st = C.load_settings()
        st.update({'primary_db': r.get('db'), 'backup_db': self.ed_bk.text().strip(),
                   'roots': [self.lst.item(k).text() for k in range(self.lst.count())],
                   'last_count': r.get('files', 0)})
        C.save_settings(st)
        self.result_info = {'used_existing': False, 'info': r, 'settings': st}
        self.accept()

    def _on_fail(self, msg):
        self.pb.setVisible(False)
        self.lb_run.setText('建库失败')
        self.tx.append('失败：%s' % msg)
        self._sync()


# ======================================================================
# batch7：全新 PDF 阅读内核（平滑滚动 + 文字层选择/复制）
#          + 阅读器独立窗口 + 跨文件全文检索（独立进程）
# ======================================================================

def _is_cjk(ch):
    o = ord(ch)
    return (0x4E00 <= o <= 0x9FFF or 0x3400 <= o <= 0x4DBF or 0xF900 <= o <= 0xFAFF
            or 0x3000 <= o <= 0x303F or 0xFF00 <= o <= 0xFFEF or 0x3040 <= o <= 0x30FF
            or 0x2018 <= o <= 0x201F)


def _join_words(words):
    """把 PyMuPDF 的词按阅读顺序拼回文本：拉丁词之间补空格，中日文不补。"""
    out = []
    prev = ''
    for w in words:
        if out and prev:
            a, b = prev[-1], w[0]
            if (not _is_cjk(a)) and (not _is_cjk(b)) and a.isalnum() and b.isalnum():
                out.append(' ')
        out.append(w)
        prev = w
    return ''.join(out)


def read_bytes(p, limit=0):
    """只读原始字节：limit=0 时大文件用 mmap 映射后整块取出；limit>0 只读前 N 字节。"""
    try:
        size = os.path.getsize(p)
    except OSError:
        size = 0
    if limit and size > limit:
        with open(p, 'rb') as f:
            return f.read(limit)
    if size >= 4 * 1024 * 1024:
        import mmap
        with open(p, 'rb') as f:
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                return bytes(mm)
    with open(p, 'rb') as f:
        return f.read()


def decode_bytes(b):
    """把字节解码为文本；chardet 优先，回退常见中文编码。"""
    if not b:
        return ''
    enc = ''
    try:
        import chardet
        enc = (chardet.detect(b[:262144]).get('encoding') or '').lower()
    except Exception:
        enc = ''
    if enc in ('gb2312', 'gbk', 'gb18030'):
        enc = 'gb18030'
    cands = []
    for e in ([enc] if enc else []) + ['utf-8-sig', 'utf-8', 'gb18030', 'big5']:
        if e and e not in cands:
            cands.append(e)
    for e in cands:
        try:
            return b.decode(e)
        except (UnicodeDecodeError, LookupError):
            continue
    return b.decode('utf-8', 'replace')


def _ctx_text(t, j, n, span=30):
    a = max(0, j - span)
    b = min(len(t), j + n + span)
    s = t[a:b].replace('\n', ' ').replace('\r', ' ').strip()
    return ('…' if a > 0 else '') + s + ('…' if b < len(t) else '')


class PdfPageItem(QWidget):
    """PDF 单页：画页图 + 文字层（鼠标选词/复制）+ 查找高亮。"""
    def __init__(self, view, index):
        super().__init__()
        self.view = view
        self.index = index
        self.pix = None
        self.words = []
        self.hl = []
        self.sel_a = -1
        self.sel_b = -1
        self._drag = False
        self._rr = None            # batch11：框选截图用的橡皮筋矩形
        self._r0 = None
        self.setCursor(Qt.CursorShape.IBeamCursor)

    def set_content(self, pix, words, hl):
        self.pix = pix
        self.words = words or []
        self.hl = hl or []
        self.update()

    def paintEvent(self, _ev):
        p = QPainter(self)
        if self.pix is not None:
            p.drawPixmap(0, 0, self.pix)
        if self._rr is not None:                # batch11：框选截图的选中框
            p.setPen(QPen(QColor(30, 120, 220), 2, Qt.PenStyle.DashLine))
            p.setBrush(QColor(30, 120, 220, 40))
            p.drawRect(self._rr)
        if self.hl:
            p.setPen(QPen(QColor(220, 140, 0), 2))
            p.setBrush(QColor(255, 235, 0, 80))
            for (x0, y0, x1, y1) in self.hl:
                p.drawRect(int(x0), int(y0), int(max(1, x1 - x0)), int(max(1, y1 - y0)))
        if self.sel_a >= 0 and self.sel_b >= 0 and self.words:
            a, b = sorted((self.sel_a, self.sel_b))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(51, 153, 255, 95))
            for k in range(a, min(b + 1, len(self.words))):
                x0, y0, x1, y1, _t = self.words[k][:5]
                p.drawRect(int(x0), int(y0), int(max(1, x1 - x0)), int(max(1, y1 - y0)))
        p.end()

    def _word_at(self, pt):
        x, y = pt.x(), pt.y()
        for k, w in enumerate(self.words):
            x0, y0, x1, y1 = w[0], w[1], w[2], w[3]
            if x0 - 2 <= x <= x1 + 2 and y0 - 2 <= y <= y1 + 2:
                return k
        best, bd = -1, 1e9
        for k, w in enumerate(self.words):
            x0, y0, x1, y1 = w[0], w[1], w[2], w[3]
            if y0 - 5 <= y <= y1 + 5:
                dd = 0 if x0 <= x <= x1 else min(abs(x - x0), abs(x - x1))
                if dd < bd:
                    bd, best = dd, k
        return best

    def mousePressEvent(self, ev):
        if ev.button() != Qt.MouseButton.LeftButton:
            return
        if self.view.region_active():          # batch11：框选截图模式
            self._r0 = ev.position().toPoint()
            self._rr = QRect(self._r0, self._r0)
            self.update()
            ev.accept()
            return
        if not self.words:
            return
        k = self._word_at(ev.position().toPoint())
        if k < 0:
            return
        self.view.begin_select(self.index, k, ev.globalPosition().toPoint())
        ev.accept()

    def mouseMoveEvent(self, ev):
        if self.view.region_active() and self._r0 is not None:
            self._rr = QRect(self._r0, ev.position().toPoint()).normalized()
            self.update()
            ev.accept()
            return
        if not self.view.is_dragging():
            return
        self.view.extend_select(ev.globalPosition().toPoint())
        ev.accept()

    def mouseReleaseEvent(self, ev):
        if self.view.region_active() and self._r0 is not None:
            rr = QRect(self._r0, ev.position().toPoint()).normalized()
            self._r0 = None
            self._rr = None
            self.update()
            self.view.finish_region(self.index, rr)
            ev.accept()
            return
        if not self.view.is_dragging():
            return
        self.view.end_select()
        ev.accept()

    def selected_text(self):
        if self.sel_a < 0 or self.sel_b < 0 or not self.words:
            return ''
        a, b = sorted((self.sel_a, self.sel_b))
        idxs = sorted(range(a, min(b + 1, len(self.words))),
                      key=lambda k: (round(self.words[k][1] / 4.0), self.words[k][0]))
        return _join_words([self.words[k][4] for k in idxs])

    def clear_sel(self):
        self.sel_a = self.sel_b = -1
        self.update()


class PdfView(QScrollArea):
    """连续纵向滚动 PDF 阅读器：按页懒渲染、像素级平滑滚动、文字层可选可复制。"""
    pageChanged = pyqtSignal(int)
    zoomRequested = pyqtSignal(float)
    fitZoom = pyqtSignal(float)          # batch10：窗口变化自动重排后的新缩放
    selectionMade = pyqtSignal(str)
    regionSelected = pyqtSignal(int, object)   # batch11：框选截图（页号, QRect）
    excerptRequested = pyqtSignal(str)          # batch11：右键「摘录选中文字」
    snapshotRequested = pyqtSignal(int)         # batch11：右键「截图本页」（页号）

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self._content = QWidget()
        self._lay = QVBoxLayout(self._content)
        self._lay.setContentsMargins(10, 10, 10, 10)
        self._lay.setSpacing(14)
        self._lay.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self.setWidget(self._content)
        self.doc = None
        self._zoom = 1.0
        self._invert = False
        self._hl_kw = ''
        self._items = []
        self._pix = {}
        self._words = {}
        self._hl = {}
        self._render_count = {}
        self._tops = []
        self._cur_page = 0
        self._active = None
        self._dragging = False
        self._anchor = None
        self._focus = None
        self._region = False          # batch11：框选截图模式
        self._vt = QTimer(self)
        self._vt.setSingleShot(True)
        self._vt.setInterval(30)
        self._vt.timeout.connect(self._render_visible)
        # batch10：适应窗口 —— 窗口/视口变化时自动重算缩放（去抖）
        self._fit_mode = None            # 'fitw' / 'fitp' / None
        self._ft = QTimer(self)
        self._ft.setSingleShot(True)
        self._ft.setInterval(60)
        self._ft.timeout.connect(self._refit_now)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.verticalScrollBar().setSingleStep(40)
        self.verticalScrollBar().valueChanged.connect(self._on_scroll)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._copyk = QShortcut(QKeySequence.StandardKey.Copy, self)
        self._copyk.activated.connect(self.copy_selection)
        self._copyak = QShortcut(QKeySequence('Ctrl+A'), self)
        self._copyak.activated.connect(self.select_all_page)

    # ---- 文档装载
    def clear(self):
        self._vt.stop()
        while self._lay.count():
            item = self._lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self.doc = None
        self._items = []
        self._pix = {}
        self._words = {}
        self._hl = {}
        self._render_count = {}
        self._tops = []
        self._cur_page = 0
        self._active = None
        self._content.adjustSize()

    def set_document(self, doc, page=0, zoom=1.0, invert=False, hl=''):
        self.clear()
        self.doc = doc
        self._zoom = float(zoom or 1.0)
        self._invert = bool(invert)
        self._hl_kw = hl or ''
        if doc is None:
            return
        n = int(getattr(doc, 'page_count', 0) or 0)
        for i in range(n):
            it = PdfPageItem(self, i)
            it.setFixedSize(self._page_size(i))
            self._lay.addWidget(it, 0, Qt.AlignmentFlag.AlignHCenter)
            self._items.append(it)
        self._content.adjustSize()
        self._build_tops()
        self.goto_page(max(0, min(n - 1, int(page))), emit=False)
        if self._fit_mode:
            self._refit_now()
        self._render_visible()

    def _page_size(self, i):
        try:
            r = self.doc[i].rect
            w = max(40, int(round(float(r.width) * self._zoom)))
            h = max(40, int(round(float(r.height) * self._zoom)))
        except Exception:
            w, h = int(612 * self._zoom), int(792 * self._zoom)
        return QSize(w, h)

    def _build_tops(self):
        tops = []
        y = int(self._lay.contentsMargins().top())
        sp = int(self._lay.spacing())
        for it in self._items:
            tops.append(y)
            y += it.height() + sp
        self._tops = tops

    def page_count(self):
        return len(self._items)

    def current_page(self):
        return int(self._cur_page)

    def render_counts(self):
        return dict(self._render_count)

    def _page_at_y(self, y):
        if not self._tops:
            return 0
        k = bisect_right(self._tops, y + 6) - 1
        return max(0, min(len(self._items) - 1, k))

    def _on_scroll(self, _v=None):
        p = self._page_at_y(self.verticalScrollBar().value())
        if p != self._cur_page:
            self._cur_page = p
            self.pageChanged.emit(p)
        self._vt.start()

    def goto_page(self, i, emit=True):
        if not self._items:
            return
        i = max(0, min(len(self._items) - 1, int(i)))
        self._cur_page = i
        y = self._tops[i] - int(self._lay.contentsMargins().top())
        self.verticalScrollBar().setValue(max(0, y))
        self._render_visible()
        if emit:
            self.pageChanged.emit(i)

    # ---- 渲染
    def _page_words(self, i):
        if i in self._words:
            return self._words[i]
        ws = []
        try:
            z = self._zoom
            for w in self.doc[i].get_text('words'):
                ws.append((float(w[0]) * z, float(w[1]) * z, float(w[2]) * z,
                           float(w[3]) * z, w[4]))
        except Exception:
            ws = []
        self._words[i] = ws
        return ws

    def _page_hl(self, i):
        if not self._hl_kw:
            return []
        if i in self._hl:
            return self._hl[i]
        rects = []
        try:
            z = self._zoom
            for r in (self.doc[i].search_for(self._hl_kw) or []):
                rects.append((float(r.x0) * z, float(r.y0) * z,
                              float(r.x1) * z, float(r.y1) * z))
        except Exception:
            rects = []
        self._hl[i] = rects
        return rects

    def _render_page(self, i):
        if i in self._pix:
            return self._pix[i]
        try:
            import fitz
            pm = self.doc[i].get_pixmap(matrix=fitz.Matrix(self._zoom, self._zoom))
            img = QImage(pm.samples, pm.width, pm.height, pm.stride,
                         QImage.Format.Format_RGB888).copy()
            if self._invert:
                img.invertPixels(QImage.InvertMode.InvertRgb)
            pix = QPixmap.fromImage(img)
        except Exception:
            pix = None
        self._pix[i] = pix
        self._render_count[i] = int(self._render_count.get(i, 0)) + 1
        return pix

    def _visible_range(self):
        if not self._items:
            return (0, -1)
        top = self.verticalScrollBar().value()
        h = max(1, self.viewport().height())
        a = self._page_at_y(top)
        b = self._page_at_y(top + h) + 1
        return (max(0, a - 1), min(len(self._items) - 1, b + 1))

    def _render_visible(self):
        if not self._items:
            return
        a, b = self._visible_range()
        for i in range(a, b + 1):
            self._render_page(i)
            self._items[i].set_content(self._pix.get(i),
                                       self._page_words(i), self._page_hl(i))

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._ft.start()             # batch10：适应宽度/页面时随窗口重排（去抖）
        self._vt.start()

    # ---- batch10：适应窗口（随视口大小自动缩放，保证整页左右都看得见）
    def fit_zoom(self, mode=None):
        """按当前视口算「适应宽度 / 适应页面」的缩放系数。"""
        mode = mode or self._fit_mode
        if self.doc is None or not self._items or not mode:
            return float(self._zoom)
        try:
            i = max(0, min(len(self._items) - 1, int(self._cur_page)))
            r = self.doc[i].rect
            pw, ph = max(1.0, float(r.width)), max(1.0, float(r.height))
        except Exception:
            pw, ph = 612.0, 792.0
        vp = self.viewport().size()
        vw, vh = max(60, vp.width() - 24), max(60, vp.height() - 24)
        z = (min(vw / pw, vh / ph) if mode == 'fitp' else (vw / pw))
        return max(0.2, min(5.0, z))

    def set_fit(self, mode):
        """mode: 'fitw' / 'fitp' / None（None＝用 set_zoom 的固定值）。"""
        self._fit_mode = mode
        if mode:
            self._refit_now()

    def _refit_now(self):
        if not self._fit_mode or self.doc is None or not self._items:
            return
        z = self.fit_zoom(self._fit_mode)
        if abs(z - self._zoom) > max(0.002, self._zoom * 0.002):
            keep = self._cur_page
            self.set_zoom(z)
            try:
                self.goto_page(keep, emit=False)
            except Exception:
                pass
            self.fitZoom.emit(z)

    # ---- 高亮 / 缩放 / 反色
    def set_highlight(self, kw):
        self._hl_kw = kw or ''
        self._hl = {}
        self._vt.start()

    def set_invert(self, b):
        b = bool(b)
        if b != self._invert:
            self._invert = b
            self._pix = {}
            self._render_count = {}
            self._render_visible()

    def set_zoom(self, z):
        z = max(0.2, min(6.0, float(z)))
        if abs(z - self._zoom) < 1e-4:
            return
        keep = self._cur_page
        self._zoom = z
        for i, it in enumerate(self._items):
            it.setFixedSize(self._page_size(i))
        self._content.adjustSize()
        self._pix = {}
        self._words = {}
        self._hl = {}
        self._render_count = {}
        self._build_tops()
        self.goto_page(keep, emit=False)
        self._render_visible()

    # ---- 选择 / 复制（batch8：支持跨页连选）
    def is_dragging(self):
        return bool(self._dragging)

    # ---- batch11：框选截图
    def region_active(self):
        return bool(getattr(self, '_region', False))

    def begin_region(self):
        """进入一次性框选模式：下一次在页面上拖拽即选定截图区域。"""
        self._region = True
        try:
            self.setCursor(Qt.CursorShape.CrossCursor)
        except Exception:
            pass

    def cancel_region(self):
        self._region = False
        try:
            self.unsetCursor()
        except Exception:
            pass

    def finish_region(self, page, rr):
        """框选结束：若框太小则忽略（当作整页），否则发 regionSelected。"""
        self._region = False
        try:
            self.unsetCursor()
        except Exception:
            pass
        if rr is not None and rr.width() >= 8 and rr.height() >= 8:
            self.regionSelected.emit(int(page), QRect(rr))

    def current_page_index(self):
        return int(self._cur_page)

    def grab_page_pixmap(self, i=None):
        """取第 i 页当前缩放下的位图（QPixmap）；i=None 用当前页。截图用。"""
        if not self._items:
            return None
        if i is None:
            i = self._cur_page
        i = max(0, min(len(self._items) - 1, int(i)))
        return self._render_page(i)

    def begin_select(self, page, k, gpos):
        self._dragging = True
        self._anchor = (int(page), int(k))
        self._focus = (int(page), int(k))
        self._apply_selection()

    def extend_select(self, gpos):
        if not self._dragging:
            return
        hit = self._hit_global(gpos)
        if hit is not None:
            self._focus = hit
            self._apply_selection()

    def end_select(self):
        self._dragging = False
        t = self.selected_text()
        if t:
            QApplication.clipboard().setText(t)
            self.selectionMade.emit(t)

    def _hit_global(self, gpos):
        """全局坐标 → (页号, 词序号)，超出页面时贴到最近的行/端。"""
        try:
            cp = self._content.mapFromGlobal(gpos)
        except Exception:
            return None
        if not self._items:
            return None
        page = self._page_at_y(cp.y())
        it = self._items[page]
        if not it.words:
            return (page, 0)
        local = QPoint(cp.x() - it.x(), cp.y() - it.y())
        k = it._word_at(local)
        if k < 0:
            best, bd = 0, 1e18
            for kk, w in enumerate(it.words):
                cy = (w[1] + w[3]) / 2.0
                dd = abs(cy - local.y())
                if dd < bd:
                    bd, best = dd, kk
            k = best
        return (page, k)

    def _apply_selection(self):
        a, b = self._anchor, self._focus
        if a is None or b is None:
            return
        if a > b:
            a, b = b, a
        for i, it in enumerate(self._items):
            n = len(it.words)
            if n == 0:
                continue
            if i < a[0] or i > b[0]:
                it.sel_a = it.sel_b = -1
            elif a[0] == b[0]:
                it.sel_a, it.sel_b = a[1], b[1]
            elif i == a[0]:
                it.sel_a, it.sel_b = a[1], n - 1
            elif i == b[0]:
                it.sel_a, it.sel_b = 0, b[1]
            else:
                it.sel_a, it.sel_b = 0, n - 1
            it.update()

    def _set_active(self, it):
        self._active = it

    def selected_text(self):
        parts = []
        for it in self._items:
            t = it.selected_text()
            if t:
                parts.append(t)
        return '\n'.join(parts).strip()

    def copy_selection(self):
        t = self.selected_text()
        if t:
            try:                                     # 复制选中文字 → 自动附纪年换算
                t2, hits = CHRONO.annotate_append(t)
                if hits:
                    t = t2
            except Exception:
                pass
            QApplication.clipboard().setText(t)
            self.selectionMade.emit(t)
        return t

    def select_all_page(self):
        if self._active is None and self._items:
            self._set_active(self._items[self._cur_page])
        if self._active is not None and self._active.words:
            self._active.sel_a = 0
            self._active.sel_b = len(self._active.words) - 1
            self._active.update()
            self.copy_selection()

    def page_text(self, i):
        try:
            return _join_words([w[4] for w in self._page_words(i)])
        except Exception:
            return ''

    # ---- 滚轮 / 键盘
    def wheelEvent(self, ev):
        if ev.modifiers() & Qt.KeyboardModifier.ControlModifier:
            dy = ev.angleDelta().y()
            if dy:
                self.zoomRequested.emit(1.1 if dy > 0 else 1.0 / 1.1)
            ev.accept()
            return
        sb = self.verticalScrollBar()
        pd = ev.pixelDelta()
        if pd.y() or pd.x():
            sb.setValue(sb.value() - pd.y())
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - pd.x())
        else:
            dy = ev.angleDelta().y()
            dx = ev.angleDelta().x()
            if dy:
                sb.setValue(sb.value() - int(dy / 120.0 * 66))
            if dx:
                self.horizontalScrollBar().setValue(
                    self.horizontalScrollBar().value() - int(dx / 120.0 * 66))
        ev.accept()

    def keyPressEvent(self, ev):
        k = ev.key()
        if k == Qt.Key.Key_Escape and self.region_active():
            self.cancel_region()
            ev.accept()
            return
        sb = self.verticalScrollBar()
        st = max(40, min(200, self.viewport().height() // 12))
        if k == Qt.Key.Key_Down:
            sb.setValue(sb.value() + st)
        elif k == Qt.Key.Key_Up:
            sb.setValue(sb.value() - st)
        elif k in (Qt.Key.Key_PageDown, Qt.Key.Key_Space):
            self.goto_page(self._cur_page + 1)
        elif k == Qt.Key.Key_PageUp:
            self.goto_page(self._cur_page - 1)
        elif k == Qt.Key.Key_Home:
            self.goto_page(0)
        elif k == Qt.Key.Key_End:
            self.goto_page(len(self._items) - 1)
        else:
            super().keyPressEvent(ev)
            return
        ev.accept()

    def contextMenuEvent(self, ev):
        m = QMenu(self)
        t = self.selected_text()
        a_c = m.addAction('复制选中文字' if t else '复制本页文字')
        a_a = m.addAction('全选本页')
        m.addSeparator()
        a_ex = m.addAction('✂ 摘录选中文字')
        a_sn = m.addAction('📷 截图本页')
        a_sr = m.addAction('▣ 框选截图')
        m.addSeparator()
        a_z1 = m.addAction('放大（Ctrl+滚轮）')
        a_z2 = m.addAction('缩小（Ctrl+滚轮）')
        chosen = m.exec(ev.globalPos())
        if chosen is a_c:
            if t:
                self.copy_selection()
            else:
                txt = self.page_text(self._cur_page)
                if txt:
                    try:                             # 复制本页文字 → 自动附纪年换算
                        txt, _ = CHRONO.annotate_append(txt)
                    except Exception:
                        pass
                    QApplication.clipboard().setText(txt)
                    self.selectionMade.emit(txt)
        elif chosen is a_ex:
            self.excerptRequested.emit(t)
        elif chosen is a_sn:
            self.snapshotRequested.emit(int(self._cur_page))
        elif chosen is a_sr:
            self.begin_region()
        elif chosen is a_a:
            self.select_all_page()
        elif chosen is a_z1:
            self.zoomRequested.emit(1.1)
        elif chosen is a_z2:
            self.zoomRequested.emit(1.0 / 1.1)


class ReaderWindow(QMainWindow):
    """阅读器独立窗口：关闭时自动收回主窗口。

    batch18：**不设父窗口**（独立顶层窗口）——这样最小化主窗口（文件列表）时，
    阅读器窗口不会被连带最小化。
    """
    def __init__(self, owner):
        super().__init__(None)
        self.owner = owner
        self.setWindowTitle('CathayViewer 阅读器')
        try:
            self.setWindowFlag(Qt.WindowType.Window, True)
            self.setWindowFlag(Qt.WindowType.WindowMinimizeButtonHint, True)
            self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, True)
            self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, True)
        except Exception:
            pass
        try:
            if icon_path():
                self.setWindowIcon(QIcon(icon_path()))
        except Exception:
            pass

    def closeEvent(self, ev):
        try:
            if not getattr(self, '_cv_no_attach', False):
                self.owner._attach_reader(from_close=True)
        except Exception:
            pass
        try:
            super().closeEvent(ev)
        except Exception:
            pass


class TxtSyncView(QTextEdit):
    """对读用 TXT 视图：带页码索引，滚动/跳页与 PDF 同步（算法移植自 CathayReader）。"""
    pageChanged = pyqtSignal(int)          # 印刷页码（1 起）

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(QFont('Microsoft YaHei', 12))
        self.idx = None
        self._syncing = False
        self._cur = 0
        self.truncated = False      # batch16：TXT 过大时只载入前 DUAL_TXT_MAX
        self.verticalScrollBar().valueChanged.connect(self._on_scroll)

    def load(self, path):
        try:
            _sz = os.path.getsize(path)
        except OSError:
            _sz = 0
        lim = DUAL_TXT_MAX if _sz > DUAL_TXT_MAX else 0
        txt = TOOLS._read_text(path, lim)
        self.truncated = bool(lim)
        self.setPlainText(txt)
        self.idx = TOOLS.SyncIndex(txt)
        self._cur = 0
        return bool(txt)

    def goto_number(self, number):
        """跳到印刷页码 number（1 起）；没有页码标记就按比例。"""
        if not self.idx or self.idx.page_count == 0:
            return
        off, hit = self.idx.offset_for_page(int(number))
        doc = self.document()
        pos = min(int(off), max(0, doc.characterCount() - 1))
        c = QTextCursor(doc)
        c.setPosition(max(0, pos))
        self._syncing = True
        try:
            self.setTextCursor(c)
            cr = self.cursorRect(c)
            sb = self.verticalScrollBar()
            sb.setValue(max(0, sb.value() + cr.top() - 12))
            self._cur = int(hit)
        finally:
            self._syncing = False

    def _on_scroll(self, _v):
        if self._syncing or not self.idx or self.idx.page_count == 0:
            return
        cur = self.cursorForPosition(QPoint(0, 0))
        n = self.idx.page_at_position(cur.position())
        if n and n != self._cur:
            self._cur = int(n)
            self.pageChanged.emit(int(n))


class TextView(QTextEdit):
    """文本阅读框：复制（右键 / Ctrl+C）时自动在文末追加历史纪年换算。"""

    def _annot(self, sel):
        try:
            t, hits = CHRONO.annotate_append(sel)
            return t
        except Exception:
            return sel

    def _sel_text(self):
        return self.textCursor().selectedText().replace('\u2029', '\n')

    def _copy_annotated(self):
        sel = self._sel_text()
        if not (sel or '').strip():
            super().copy()
            return
        QApplication.clipboard().setText(self._annot(sel))

    def keyPressEvent(self, ev):
        if ev.matches(QKeySequence.StandardKey.Copy):
            self._copy_annotated()
            ev.accept()
            return
        super().keyPressEvent(ev)

    def contextMenuEvent(self, ev):
        m = QMenu(self)
        a1 = m.addAction('复制（含纪年换算）')
        a2 = m.addAction('复制原文')
        a3 = m.addAction('全选')
        chosen = m.exec(ev.globalPos())
        if chosen is a1:
            self._copy_annotated()
        elif chosen is a2:
            super().copy()
        elif chosen is a3:
            self.selectAll()


class DualRead(QWidget):
    """PDF（左）+ TXT（右）左右并列对读，中间纵列是 PDF 导航；页码双向同步。

    batch11 新增；batch14 改为左右两纵列 + 中间 PDF 导航页，并支持切换 TXT 版本与单独打开。
    """
    pageChanged = pyqtSignal(int)          # PDF 页号（0 起），供主窗状态栏联动
    txtChanged = pyqtSignal(str)           # 用户切换了 TXT 版本 → 主窗更新 _text_path
    exitRequested = pyqtSignal(str)        # 点「只看 PDF / 只看 TXT」→ 'pdf' / 'text'

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pdf = PdfView()
        self.txt = TxtSyncView()
        self._guard = False
        self._pdf_count = 0
        self._txt_path = ''
        # 中间纵列（PDF 导航页）：页码 / 翻页 / 同步 / 缩放 / TXT 版本 / 单独打开
        nav = QWidget()
        nv = QVBoxLayout(nav)
        nv.setContentsMargins(4, 4, 4, 4)
        nv.setSpacing(5)
        self.lb = QLabel('对读')
        self.lb.setWordWrap(True)
        nv.addWidget(self.lb)
        nv.addWidget(QLabel('PDF 导航'))
        self.cb_sync = QCheckBox('同步翻页')
        self.cb_sync.setChecked(True)
        nv.addWidget(self.cb_sync)
        nv.addWidget(QLabel('页'))
        self.ed = QLineEdit()
        self.ed.setFixedWidth(56)
        self.ed.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ed.returnPressed.connect(self._jump)
        nv.addWidget(self.ed)
        b_go = QPushButton('跳页')
        b_go.clicked.connect(self._jump)
        nv.addWidget(b_go)
        pn = QHBoxLayout()
        pn.setSpacing(2)
        self.b_first = QPushButton('⏮')
        self.b_prev = QPushButton('◀')
        self.b_next = QPushButton('▶')
        self.b_last = QPushButton('⏭')
        for _b in (self.b_first, self.b_prev, self.b_next, self.b_last):
            _b.setMaximumWidth(30)
            pn.addWidget(_b)
        self.b_first.clicked.connect(self._first)
        self.b_prev.clicked.connect(lambda: self._step(-1))
        self.b_next.clicked.connect(lambda: self._step(1))
        self.b_last.clicked.connect(self._last)
        nv.addLayout(pn)
        self.cb_fit = QComboBox()
        self.cb_fit.addItems(['适应宽度', '适应页面', '100%'])
        self.cb_fit.setCurrentIndex(1)
        self.cb_fit.currentIndexChanged.connect(self._fit)
        nv.addWidget(self.cb_fit)
        nv.addWidget(QLabel('TXT 版本'))
        self.cb_txt = QComboBox()
        self.cb_txt.setToolTip('切换对读用的 TXT（不同 OCR / 繁简版本）')
        self.cb_txt.currentIndexChanged.connect(self._switch_txt)
        nv.addWidget(self.cb_txt)
        self.b_pdf_only = QPushButton('只看 PDF')
        self.b_pdf_only.setToolTip('退出对读，只显示 PDF（保持当前页）')
        self.b_pdf_only.clicked.connect(lambda: self._single('pdf'))
        self.b_txt_only = QPushButton('只看 TXT')
        self.b_txt_only.setToolTip('退出对读，只显示 TXT')
        self.b_txt_only.clicked.connect(lambda: self._single('text'))
        nv.addWidget(self.b_pdf_only)
        nv.addWidget(self.b_txt_only)
        nv.addStretch(1)
        nav.setMinimumWidth(118)
        nav.setMaximumWidth(196)
        sp = QSplitter(Qt.Orientation.Horizontal)
        sp.addWidget(self.pdf)
        sp.addWidget(nav)
        sp.addWidget(self.txt)
        sp.setSizes([620, 150, 540])
        sp.setStretchFactor(0, 3)
        sp.setStretchFactor(1, 0)
        sp.setStretchFactor(2, 3)
        sp.setChildrenCollapsible(False)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        lay.addWidget(sp, 1)
        self.pdf.pageChanged.connect(self._on_pdf_page)
        self.txt.pageChanged.connect(self._on_txt_page)

    # ---- 装载
    def load(self, doc, txt_path, first=1, fit='fitp'):
        self._guard = True
        try:
            self.pdf.set_document(doc, max(0, int(first) - 1), 1.0)
            self._pdf_count = int(getattr(doc, 'page_count', 0) or 0)
            self.txt.load(txt_path)
            self._txt_path = txt_path
            self._set_fit(fit)
            self.txt.goto_number(int(first))
            try:
                self.ed.setText(str(int(first)))
            except Exception:
                pass
            try:
                import os as _os
                _tail = '｜TXT 过大，仅前 %d MB' % (DUAL_TXT_MAX // 1048576) \
                    if getattr(self.txt, 'truncated', False) else ''
                self.lb.setText('对读：《%s》 ｜ PDF %d 页 / TXT %d 页%s（按页码标记同步）'
                                % (_os.path.basename(txt_path),
                                   self._pdf_count, self.txt.idx.page_count if self.txt.idx else 0,
                                   _tail))
            except Exception:
                self.lb.setText('对读：已加载')
        finally:
            self._guard = False

    def _set_fit(self, fit):
        m = {'fitw': 0, 'fitp': 1, '100': 2}.get(fit or 'fitp', 1)
        self.cb_fit.blockSignals(True)
        self.cb_fit.setCurrentIndex(m)
        self.cb_fit.blockSignals(False)
        if fit in ('fitw', 'fitp'):
            self.pdf.set_fit(fit)
        else:
            self.pdf.set_fit(None)
            self.pdf.set_zoom(1.0)

    def _fit(self, i):
        if i == 0:
            self.pdf.set_fit('fitw')
        elif i == 1:
            self.pdf.set_fit('fitp')
        else:
            self.pdf.set_fit(None)
            self.pdf.set_zoom(1.0)

    # ---- batch14：TXT 版本切换 / 单独打开 / 跳页面控
    def set_txt_list(self, items):
        """items: [(标签, 路径), …] —— 对读时可切换的 TXT 版本。"""
        self.cb_txt.blockSignals(True)
        self.cb_txt.clear()
        for label, path in (items or []):
            self.cb_txt.addItem(str(label), path)
        if items:
            i = self.cb_txt.findData(self._txt_path)
            self.cb_txt.setCurrentIndex(i if i >= 0 else 0)
        self.cb_txt.blockSignals(False)
        self.cb_txt.setEnabled(self.cb_txt.count() > 1)

    def _switch_txt(self, i):
        p = self.cb_txt.itemData(i)
        if not p or p == self._txt_path:
            return
        if self.load_txt(p):
            self.txtChanged.emit(p)

    def load_txt(self, path):
        """换一个 TXT 并重新对齐到当前页。"""
        try:
            if not self.txt.load(path):
                return False
        except Exception:
            return False
        self._txt_path = path
        try:
            n = int(re.sub(r'\D', '', self.ed.text()) or '1')
        except Exception:
            n = 1
        self._guard = True
        try:
            self.txt.goto_number(n)
        finally:
            self._guard = False
        return True

    def _first(self):
        self.ed.setText('1')
        self._jump()

    def _last(self):
        self.ed.setText(str(max(1, int(self._pdf_count or 1))))
        self._jump()

    def _step(self, d):
        try:
            n = int(re.sub(r'\D', '', self.ed.text()) or '1') + int(d)
        except Exception:
            n = 1
        self.ed.setText(str(max(1, n)))
        self._jump()

    def _single(self, which):
        self.exitRequested.emit(str(which))

    # ---- 同步
    def _on_pdf_page(self, i):
        if self._guard:
            return
        try:
            self.ed.setText(str(int(i) + 1))
        except Exception:
            pass
        if self.cb_sync.isChecked():
            self._guard = True
            try:
                self.txt.goto_number(int(i) + 1)
            finally:
                self._guard = False
        self.pageChanged.emit(int(i))

    def _on_txt_page(self, n):
        if self._guard:
            return
        try:
            self.ed.setText(str(int(n)))
        except Exception:
            pass
        if self.cb_sync.isChecked():
            self._guard = True
            try:
                self.pdf.goto_page(int(n) - 1)
            finally:
                self._guard = False
        self.pageChanged.emit(int(n) - 1)

    def _jump(self):
        try:
            n = int(re.sub(r'\D', '', self.ed.text()) or '1')
        except Exception:
            n = 1
        self._guard = True
        try:
            self.pdf.goto_page(int(n) - 1)
            self.txt.goto_number(int(n))
        finally:
            self._guard = False
        self.pageChanged.emit(int(n) - 1)

    def goto_page(self, n):
        self.ed.setText(str(int(n) + 1))
        self._guard = True
        try:
            self.pdf.goto_page(int(n))
            self.txt.goto_number(int(n) + 1)
        finally:
            self._guard = False

    def current_page(self):
        return int(self.pdf.current_page())

    def clear(self):
        try:
            self.pdf.clear()
            self.txt.clear()
            self.txt.idx = None
        except Exception:
            pass


# ---- 跨文件全文检索（独立进程 worker）
def _fts_pdf(path, kw, per_file):
    """返回 (总命中次数, 前 per_file 条上下文)。"""
    hits = []
    count = 0
    import fitz
    d = fitz.open(path)
    try:
        for i in range(int(d.page_count)):
            try:
                t = (d[i].get_text() or '').replace('\xa0', ' ')
            except Exception:
                t = ''
            j = t.find(kw)
            while j >= 0:
                count += 1
                if len(hits) < per_file:
                    hits.append({'page': i, 'ctx': _ctx_text(t, j, len(kw))})
                j = t.find(kw, j + len(kw))
    finally:
        try:
            d.close()
        except Exception:
            pass
    return count, hits


def _fts_text(path, kw, per_file):
    """返回 (总命中次数, 前 per_file 条上下文)。"""
    t = decode_bytes(read_bytes(path, TEXT_MAX_BYTES)).replace('\xa0', ' ')
    hits = []
    count = 0
    start = 0
    while True:
        j = t.find(kw, start)
        if j < 0:
            break
        count += 1
        if len(hits) < per_file:
            hits.append({'page': None, 'ctx': _ctx_text(t, j, len(kw))})
        start = j + len(kw)
    return count, hits


def _emit(s):
    """向 stdout 写进度；窗口版 exe 没有控制台（stdout 可能为 None），静默忽略。"""
    try:
        if sys.stdout is not None:
            sys.stdout.write(s)
            sys.stdout.flush()
    except Exception:
        pass


def fts_run(job_path):
    """在独立进程里执行跨文件全文检索：读 job.json，进度写 stdout，结果写 out.json。"""
    with open(job_path, 'r', encoding='utf-8') as f:
        job = json.load(f)
    kw = job.get('kw') or ''
    files = job.get('files') or []
    out = job.get('out') or ''
    budget = int(job.get('max_hits') or 500)
    files_rep = []
    errors = []
    scanned = 0
    total = 0
    per_file = int(job.get('max_per_file') or 50)
    if kw:
        for p in files:
            scanned += 1
            cnt, hh = 0, []
            try:
                ext = os.path.splitext(p)[1].lower()
                if ext == '.pdf':
                    cnt, hh = _fts_pdf(p, kw, per_file)
                elif ext in ('.txt', '.md', '.json', '.csv', '.log', '.htm', '.html'):
                    cnt, hh = _fts_text(p, kw, per_file)
            except Exception as e:
                errors.append('%s: %s' % (os.path.basename(p), e))
            if cnt:
                files_rep.append({'path': p, 'name': os.path.basename(p),
                                  'count': cnt, 'hits': hh})
                total += cnt
            _emit('PROGRESS\t%d\t%d\t%d\n' % (scanned, len(files), total))
    flat = []
    for fr in files_rep:
        for h in fr.get('hits') or []:
            flat.append({'path': fr['path'], 'name': fr['name'],
                         'page': h.get('page'), 'ctx': h.get('ctx')})
    try:
        with open(out, 'w', encoding='utf-8') as f:
            json.dump({'kw': kw, 'files': files_rep, 'hits': flat, 'errors': errors,
                       'scanned': scanned, 'total': len(files)}, f, ensure_ascii=False)
    except Exception:
        pass
    _emit('DONE\n')
    return 0


class _HiDelegate(QStyledItemDelegate):
    """列表里把命中的关键词用黄底画出来（支持多个关键词，超长自动裁剪）。"""
    def __init__(self, kw_getter, parent=None):
        super().__init__(parent)
        self._kw = kw_getter

    def _kws(self):
        try:
            v = self._kw() if callable(self._kw) else ''
        except Exception:
            v = ''
        if isinstance(v, (list, tuple, set)):
            out = [str(x) for x in v if x]
        else:
            out = [str(v)] if v else []
        return sorted(set(out), key=len, reverse=True)     # 长的优先，避免短词切碎

    def paint(self, painter, option, index):
        kws = self._kws()
        text = str(index.data(Qt.ItemDataRole.DisplayRole) or '')
        if not kws or not any(k in text for k in kws):
            super().paint(painter, option, index)
            return
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        style = opt.widget.style() if opt.widget is not None else QApplication.style()
        opt.text = ''
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, opt.widget)
        painter.save()
        fm = painter.fontMetrics()
        rect = option.rect.adjusted(4, 0, -4, 0)
        x = rect.left()
        baseline = rect.top() + (rect.height() - fm.height()) // 2 + fm.ascent()
        sel = bool(opt.state & QStyle.StateFlag.State_Selected)
        fg = opt.palette.color(QPalette.ColorRole.HighlightedText if sel
                               else QPalette.ColorRole.Text)

        def _hot(i):
            for k in kws:
                if text.startswith(k, i):
                    return k
            return ''

        i, stop = 0, False
        while i < len(text) and not stop:
            k = _hot(i)
            if k:
                seg, hot = k, True
                i += len(k)
            else:
                seg, hot = text[i], False
                i += 1
            w = fm.horizontalAdvance(seg)
            if x + w > rect.right() + 2:
                stop = True
                break
            if hot:
                painter.fillRect(QRect(x, rect.top() + 2, w, rect.height() - 4),
                                 QColor(255, 221, 0, 175))
            painter.setPen(fg)
            painter.drawText(x, baseline, seg)
            x += w
        painter.restore()


class MainWindow(QMainWindow):
    def __init__(self, settings=None):
        super().__init__()
        self.st = settings or C.load_settings()
        self.db = self.st.get('primary_db') or ''
        self.rows = []
        self.vers = []
        self.meta = None
        self._reader = ''        # 'pdf' / 'text'：当前阅读区内容类型
        self._top_widgets = []   # 顶部工具栏（全屏时隐藏）
        self._btn_widgets = []   # 详情区按钮行（全屏时隐藏）
        self._f11 = QShortcut(QKeySequence('F11'), self) if QShortcut else None
        if self._f11:
            self._f11.activated.connect(self.toggle_full)
        self.pd = None      # 当前 PDF 文档
        self.pgno = 0       # 当前页（0 起）
        self._pd_path = ''  # 当前打开文档的路径（目录跟随它）
        self._stat_path = ''  # 阅读统计：当前计时的文件
        self._stat_t0 = 0.0
        self._last_toc = None
        self._pgdn = QShortcut(QKeySequence('PgDown'), self)
        self._pgdn.activated.connect(lambda: self.pdf_goto(1))
        self._pgup = QShortcut(QKeySequence('PgUp'), self)
        self._pgup.activated.connect(lambda: self.pdf_goto(-1))
        self._toc = QShortcut(QKeySequence('Ctrl+T'), self)
        self._toc.activated.connect(self.toc_here)
        self._mark = QShortcut(QKeySequence('Ctrl+B'), self)
        self._mark.activated.connect(self.bookmark_here)
        self._hist = QShortcut(QKeySequence('Ctrl+H'), self)
        self._hist.activated.connect(self.hist_here)
        self._sk = QShortcut(QKeySequence('Ctrl+K'), self)
        self._sk.activated.connect(self.search_history_dialog)
        self._sd = QShortcut(QKeySequence('Ctrl+D'), self)
        self._sd.activated.connect(self.save_search)
        self._rstat = QShortcut(QKeySequence('Ctrl+Shift+H'), self)
        self._rstat.activated.connect(self.read_stats_dialog)
        self._epub = QShortcut(QKeySequence('Ctrl+E'), self)
        self._epub.activated.connect(self.epub_here)
        self._cpy = QShortcut(QKeySequence('Ctrl+Shift+C'), self)
        self._cpy.activated.connect(self.copy_text)
        # batch11：截图本 / 摘录本 / 对读 / 跨文件检索历史
        self.dual = None                 # PDF+TXT 对读面板（_ui 里创建）
        self._exk = QShortcut(QKeySequence('Ctrl+Shift+E'), self)
        self._exk.activated.connect(self.excerpt_here)
        self._snk = QShortcut(QKeySequence('Ctrl+Shift+X'), self)
        self._snk.activated.connect(self.snapshot_here)
        self._dualk = QShortcut(QKeySequence('Ctrl+Shift+D'), self)
        self._dualk.activated.connect(self.toggle_dual)
        self._ftshistk = QShortcut(QKeySequence('Ctrl+Shift+F'), self)
        self._ftshistk.activated.connect(self.fts_history_dialog)
        self._footk = QShortcut(QKeySequence('Ctrl+Shift+I'), self)
        self._footk.activated.connect(self.footnote_here)
        self._listk = QShortcut(QKeySequence('Ctrl+Shift+L'), self)      # batch17：收起/展开左栏
        self._listk.activated.connect(self.toggle_list)
        self._chronok = QShortcut(QKeySequence('Ctrl+Shift+Y'), self)
        self._chronok.activated.connect(self.chrono_dialog)
        self._aliask = QShortcut(QKeySequence('Ctrl+Shift+A'), self)
        self._aliask.activated.connect(self.alias_dialog)
        self._excvk = QShortcut(QKeySequence('Ctrl+Shift+M'), self)
        self._excvk.activated.connect(self.excerpt_viewer)
        self.st.setdefault('auto_dual', True)     # 打开 TXT 且有同名 PDF → 自动对读
        self._suppress_dual = False               # 版本切换等场景临时禁用自动对读
        # batch3：MD 渲染 / JSON 树 / 相关文件 / 缩略图
        self._md_render = False     # 阅读区是否处于 Markdown 渲染态
        self._md_path = ''          # 当前渲染的 .md 路径
        self._md_src = ''           # 当前 .md 的源码文本
        self._thumb_dock = None     # 右侧缩略图面板
        self._thumb_list = None
        self._thumb_timer = None
        self._thumbs_added = 0
        # batch5：连续滚动 / 导航面板 / 文内查找
        self._nav_dock = None       # 导航面板（QDockWidget：目录 / 缩略图 / 查找）
        self._nav_tabs = None
        self._nav_toc = None
        self._nav_find = None
        # batch7：PDF 渲染缓存/滚动记账已移入 PdfView（阅读器内核）
        self._fts_proc = None       # 跨文件全文检索进程
        self._fts_kw = ''
        self._fts_total = 0
        self._msg_hold_until = 0.0  # 显式提示的保护期（避免被滚动状态栏覆盖）
        self._zoom = 1.0            # 自定义缩放系数
        self._zoom_mode = 'fitp'    # batch8：默认「适应页面」；fitp/fitw/100/custom
        self._pd_texts = None       # PDF 页级文本缓存
        self._pd_texts_doc = None   # 缓存归属的文档 id（换文件时重建）
        self._hl_kw = ''            # 当前 PDF 高亮关键词
        self._find_kw = ''
        self._find_total = 0
        self._find_idx = -1
        self._find_hits = []        # batch9: [{path,name,page,off,ctx,txt_mark}]
        self._find_kept = []        # 保留（默认展示）的命中
        self._find_hidden = []      # 被去重、默认隐藏的命中
        self._find_view = []        # 实际展示（kept + 可选的 hidden）
        self._find_show_hidden = False
        self._text_path = ''        # 当前文本视图打开的文件路径
        self._last_json = None
        self._last_related = None
        self._mdk = QShortcut(QKeySequence('Ctrl+M'), self)
        self._mdk.activated.connect(self.md_toggle)
        self._jsk = QShortcut(QKeySequence('Ctrl+J'), self)
        self._jsk.activated.connect(self.json_tree_dialog)
        self._relk = QShortcut(QKeySequence('Ctrl+R'), self)
        self._relk.activated.connect(self.related_dialog)
        self._thk = QShortcut(QKeySequence('Ctrl+Shift+T'), self)
        self._thk.activated.connect(self.toggle_thumbs)
        # batch5：Ctrl+Home/End 首/末页、Ctrl+F 文内查找、Esc 关闭查找条
        self._homek = QShortcut(QKeySequence('Ctrl+Home'), self)
        self._homek.activated.connect(self.pdf_home)
        self._endk = QShortcut(QKeySequence('Ctrl+End'), self)
        self._endk.activated.connect(self.pdf_end)
        self._findk = QShortcut(QKeySequence('Ctrl+F'), self)
        self._findk.activated.connect(self.find_focus)
        self._esck = QShortcut(QKeySequence('Esc'), self)
        self._esck.activated.connect(self.find_close)
        # batch20：跨文件全文检索的快捷键（左栏收窄/收起时也一定能用）
        self._ftsk = QShortcut(QKeySequence('Ctrl+Shift+S'), self)
        self._ftsk.activated.connect(self.fulltext_search)
        try:
            from PyQt6.QtCore import QTimer as _QT
            _QT.singleShot(300, self.open_cli_arg)   # 双击 / 命令行带路径 → 直接打开
        except Exception:
            pass
        self.setWindowTitle('%s %s' % (APP_TITLE, APP_VERSION))
        self._apply_default_size()
        self.setFont(QFont('Microsoft YaHei', 9))
        if icon_path():
            from PyQt6.QtGui import QIcon
            self.setWindowIcon(QIcon(icon_path()))
        self._ui()
        self._refresh_status()
        try:
            self.setAcceptDrops(True)         # batch15：支持把 PDF / TXT 拖进来打开
        except Exception:
            pass

    def _ui(self):
        cen = QWidget()
        self.setCentralWidget(cen)
        v = QVBoxLayout(cen)
        # 顶部：搜索
        top = QHBoxLayout()
        self.ed_kw = QLineEdit()
        self.ed_kw.setPlaceholderText('搜文件名 / 书名（逐字精准匹配；回车搜索）')
        self.ed_kw.returnPressed.connect(self.do_search)
        b = QPushButton('🔍 搜索')
        b.clicked.connect(self.do_search)
        self.b_build = QPushButton('📚 建库 / 刷新')
        self.b_build.clicked.connect(self.do_build)
        top.addWidget(self.ed_kw, 1)
        top.addWidget(b)
        top.addWidget(self.b_build)
        v.addLayout(top)
        self._top_widgets = [self.ed_kw, b, self.b_build]
        # 主体
        sp = QSplitter(Qt.Orientation.Horizontal)
        self.tb = QTableWidget(0, 3)
        self.tb.setHorizontalHeaderLabels(['序号', '文件名', '上级文件夹'])
        self.tb.verticalHeader().setVisible(False)     # batch10：去掉行号列（序号只留一列）
        self.tb.verticalHeader().setDefaultSectionSize(22)
        _hh = self.tb.horizontalHeader()
        _hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        _hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        _hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)   # batch17：可缩（不再被内容撑宽）
        _hh.resizeSection(2, 150)
        _hh.setMinimumSectionSize(24)
        self.tb.setWordWrap(False)
        self.tb.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tb.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tb.itemSelectionChanged.connect(self.on_pick)
        self.tb.itemDoubleClicked.connect(self._on_item_dbl)
        self.tb.itemClicked.connect(self._on_item_click)      # 单击文件名即打开
        self.tb.setMinimumWidth(48)           # batch17：可以拖得非常窄（原先 90 仍嫌占位）
        self.tb.setMaximumWidth(880)          # 上限（resizeEvent 里再按窗口比例收紧）
        # 命中关键词在文件名列黄底高亮
        self._last_kw = ''
        self.st.setdefault('alias_mode', 'ask')      # 人名别名：ask / auto / off
        self._hl_kws = []
        self._hi = _HiDelegate(lambda: (getattr(self, '_hl_kws', None)
                                        or ([self._last_kw] if getattr(self, '_last_kw', '') else [])),
                               self.tb)
        self.tb.setItemDelegate(self._hi)
        # 左栏：文件列表 + 「跨文件全文检索」按钮
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lh = QHBoxLayout()
        self.b_fts = QPushButton('🔎 跨文件全文检索')
        self.b_fts.setToolTip('对当前搜索结果的 PDF/文本做跨文件全文检索（另开进程，不卡界面）—— Ctrl+Shift+S')
        self.b_fts.clicked.connect(self.fulltext_search)
        self.b_fts_hist = QPushButton('🕘 检索历史')
        self.b_fts_hist.setToolTip('调阅历次跨文件全文检索结果（自动保存，Ctrl+Shift+F）')
        self.b_fts_hist.clicked.connect(self.fts_history_dialog)
        self.b_alias = QPushButton('👤 人名别名')
        self.b_alias.setToolTip('近代人物字号/笔名/化名归一：检索人物名时可一并检索其别名（Ctrl+Shift+A）')
        self.b_alias.clicked.connect(self.alias_dialog)
        self.b_exc = QPushButton('🗂 摘录本')
        self.b_exc.setToolTip('查看 / 编辑已摘录的资料（Ctrl+Shift+M）')
        self.b_exc.clicked.connect(self.excerpt_viewer)
        # batch17：左栏变窄时，上面 4 个按钮收进「⋮」菜单，让文件列表能缩到極小
        from PyQt6.QtWidgets import QToolButton
        self.b_more = QToolButton()
        self.b_more.setText('⋮')
        self.b_more.setToolTip('更多：跨文件全文检索 / 检索历史 / 人名别名 / 摘录本')
        try:
            self.b_more.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        except Exception:
            pass
        _mmenu = QMenu(self.b_more)
        _mmenu.addAction('🔎 跨文件全文检索', self.fulltext_search)
        _mmenu.addAction('🕘 检索历史', self.fts_history_dialog)
        _mmenu.addAction('👤 人名别名', self.alias_dialog)
        _mmenu.addAction('🗂 摘录本', self.excerpt_viewer)
        self.b_more.setMenu(_mmenu)
        lh.addWidget(self.b_fts)
        lh.addWidget(self.b_fts_hist)
        lh.addWidget(self.b_alias)
        lh.addWidget(self.b_exc)
        lh.addWidget(self.b_more)
        self.b_more.setVisible(False)
        lh.addStretch(1)
        # batch20：这排按钮按自然宽度显示（batch17 设的 Ignored 策略会把它们压成 0 宽、整排看不见 —— 已修）；
        # 拖窄时靠 _fit_left_buttons 把次要按钮收进 ⋮，主入口「检索」始终保留
        from PyQt6.QtWidgets import QSizePolicy
        for _b in (self.b_fts, self.b_fts_hist, self.b_alias, self.b_exc, self.b_more):
            _b.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
            _b.setMinimumHeight(24)
        lv.addLayout(lh)
        lv.addWidget(self.tb, 1)
        sp.addWidget(left)
        self._left = left
        right = QWidget()
        right.setMinimumWidth(320)
        rv = QVBoxLayout(right)
        rv.setContentsMargins(2, 1, 2, 1)
        rv.setSpacing(2)
        self.lb_info = QLabel('选一个文件看详情')
        self.lb_info.setWordWrap(True)
        self.lb_info.setVisible(False)      # 默认隐藏（正文进 tooltip），点「ⓘ」展开
        self.text_view = TextView()
        self.pdf_view = PdfView()
        self.pdf_view.pageChanged.connect(self._on_pdf_page)
        self.pdf_view.zoomRequested.connect(self._pdf_zoom_step)
        self.pdf_view.fitZoom.connect(self._on_fit_zoom)
        self.pdf_view.selectionMade.connect(self._on_pdf_selection)
        self.pdf_view.regionSelected.connect(self._on_pdf_region)
        self.pdf_view.excerptRequested.connect(self._excerpt_from_pdf)
        self.pdf_view.snapshotRequested.connect(self._snapshot_from_pdf)
        self.stack = QStackedWidget()
        self.stack.addWidget(self.text_view)      # 0：文本 / MD / JSON
        self.stack.addWidget(self.pdf_view)       # 1：PDF 连续滚动
        self.dual = DualRead()                     # 2：PDF + TXT 对读
        self.dual.pageChanged.connect(self._on_dual_page)
        self.dual.pdf.regionSelected.connect(self._on_pdf_region)
        self.dual.pdf.excerptRequested.connect(self._excerpt_from_pdf)
        self.dual.pdf.snapshotRequested.connect(self._snapshot_from_pdf)
        self.stack.addWidget(self.dual)
        self.view = self.text_view                # 兼容：文本类代码继续用 self.view
        self.view.setReadOnly(True)
        self.view.installEventFilter(self)      # Ctrl+滚轮缩放（滚轮事件发给 viewport）
        try:
            self.view.viewport().installEventFilter(self)
        except Exception:
            pass
        trow = QHBoxLayout()
        trow.setContentsMargins(0, 0, 0, 0)
        trow.setSpacing(4)
        trow.addWidget(QLabel('版本'))
        self.cb_ver = QComboBox()
        self.cb_ver.setMinimumWidth(160)          # batch14：不再把「版本」显示不全
        self.cb_ver.setMaximumWidth(360)
        self.cb_ver.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.cb_ver.currentIndexChanged.connect(self.on_ver)
        trow.addWidget(self.cb_ver)
        self.b_info = QPushButton('ⓘ 详情')
        self.b_info.setCheckable(True)
        self.b_info.setMaximumWidth(70)
        self.b_info.setToolTip('显示/隐藏 文件详情（默认隐藏，为阅读让出空间）')
        self.b_info.toggled.connect(self.lb_info.setVisible)
        trow.addWidget(self.b_info)
        trow.addWidget(QLabel('主题'))
        self.cb_theme = QComboBox()
        self.cb_theme.addItems(['浅色', '深色', '护眼'])
        trow.addWidget(self.cb_theme)
        trow.addWidget(QLabel('字号'))
        self.sp_font = QSpinBox()
        self.sp_font.setRange(8, 30)
        self.sp_font.setValue(13)
        trow.addWidget(self.sp_font)
        trow.addWidget(QLabel('行距'))
        self.sp_line = QSpinBox()
        self.sp_line.setRange(100, 250)
        self.sp_line.setValue(150)
        self.sp_line.setSingleStep(10)
        self.sp_line.setSuffix('%')
        trow.addWidget(self.sp_line)
        trow.addWidget(QLabel('缩放'))
        self.cb_zoom = QComboBox()
        self.cb_zoom.addItems(['适应宽度', '适应页面', '100%', '自定义'])
        self.cb_zoom.setCurrentIndex(1)
        self.cb_zoom.setToolTip('PDF 缩放：适应宽度 / 适应页面 / 100% / 自定义（Ctrl+滚轮）')
        self.cb_zoom.currentIndexChanged.connect(self._zoom_changed)
        trow.addWidget(self.cb_zoom)
        self.sp_zoom = QSpinBox()
        self.sp_zoom.setRange(50, 400)
        self.sp_zoom.setValue(100)
        self.sp_zoom.setSuffix('%')
        self.sp_zoom.setKeyboardTracking(False)
        self.sp_zoom.setToolTip('自定义缩放 50%–400%（回车 / 失焦生效）')
        self.sp_zoom.valueChanged.connect(self._zoom_pct_changed)
        trow.addWidget(self.sp_zoom)
        self.cb_invert = QCheckBox('◐ PDF 反色')
        trow.addWidget(self.cb_invert)
        trow.addStretch(1)
        trow.addWidget(QLabel('页'))
        self.ed_page = QLineEdit()
        self.ed_page.setFixedWidth(52)
        self.ed_page.setToolTip('输入页码后回车跳转（N / M）')
        self.ed_page.setText('0')
        self.ed_page.returnPressed.connect(self.page_jump)
        trow.addWidget(self.ed_page)
        self.lb_pg_total = QLabel('/ 0')
        trow.addWidget(self.lb_pg_total)
        self.b_pg_first = QPushButton('⏮')
        self.b_pg_first.setToolTip('首页（Ctrl+Home）')
        self.b_pg_first.clicked.connect(self.pdf_home)
        self.b_pg_prev = QPushButton('◀')
        self.b_pg_prev.setToolTip('上一页（PgUp）')
        self.b_pg_prev.clicked.connect(lambda: self.pdf_goto(-1))
        self.b_pg_next = QPushButton('▶')
        self.b_pg_next.setToolTip('下一页（PgDn）')
        self.b_pg_next.clicked.connect(lambda: self.pdf_goto(1))
        self.b_pg_last = QPushButton('⏭')
        self.b_pg_last.setToolTip('末页（Ctrl+End）')
        self.b_pg_last.clicked.connect(self.pdf_end)
        for _pb in (self.b_pg_first, self.b_pg_prev, self.b_pg_next, self.b_pg_last):
            _pb.setMaximumWidth(34)
            trow.addWidget(_pb)
        rv.addLayout(trow)
        for _w in (self.cb_ver, self.cb_theme, self.sp_font, self.sp_line,
                   self.cb_zoom, self.sp_zoom, self.ed_page, self.b_info):
            try:
                _w.setFixedHeight(22)
            except Exception:
                pass
        self.cb_theme.currentIndexChanged.connect(self.apply_theme)
        self.sp_font.valueChanged.connect(self.apply_theme)
        self.sp_line.valueChanged.connect(self.apply_theme)
        self.cb_invert.stateChanged.connect(self._on_invert)
        row = QHBoxLayout()
        b1 = QPushButton('📖 在阅读区打开')
        b1.clicked.connect(self.preview_here)
        b2 = QPushButton('↗ 用外部程序打开')
        b2.setToolTip('用系统默认程序打开当前文件（双击不再走这里）')
        b2.clicked.connect(self.open_external)
        b3 = QPushButton('📂 打开所在文件夹')
        b3.clicked.connect(self.open_folder)
        b4 = QPushButton('📋 复制引用')
        b4.clicked.connect(self.copy_cite)
        b5 = QPushButton('⤒ 版权页')
        b5.clicked.connect(self.colophon_here)
        b6 = QPushButton('⧉ 复制文本')
        b6.clicked.connect(self.copy_text)
        b7 = QPushButton('⧉ 复制带格式')
        b7.clicked.connect(self.copy_html)
        b8 = QPushButton('𝐌D 渲染')
        b8.setToolTip('Markdown 渲染 / 源码切换（Ctrl+M）')
        b8.clicked.connect(self.md_toggle)
        self._btn_widgets = [b1, b2, b3, b4, b5, b6, b7, b8]
        _b9 = QPushButton('🗗 独立窗口')
        _b9.setToolTip('把阅读器拆成独立窗口（可最大化占据全屏）；再点一次收回')
        _b9.clicked.connect(self.toggle_reader_window)
        self._btn_widgets += [_b9]
        _bsnap = QPushButton('📷 截图')
        _bsnap.setToolTip('把当前 PDF 页面（或框选区域）存入「文档\\Cathay文档记录\\截图本」（Ctrl+Shift+X）')
        _bsnap.clicked.connect(self.snapshot_here)
        _bexc = QPushButton('✂ 摘录')
        _bexc.setToolTip('把选中文字存入「文档\\Cathay文档记录\\摘录本」，自动附出处（Ctrl+Shift+E）')
        _bexc.clicked.connect(self.excerpt_here)
        _bdual = QPushButton('⇄ 对读')
        _bdual.setToolTip('PDF 与 TXT 对照阅读、按页码同步（Ctrl+Shift+D）')
        _bdual.clicked.connect(self.toggle_dual)
        _bfoot = QPushButton('❞ 脚注')
        _bfoot.setToolTip('把选中引文做成带出处的脚注，粘贴到 Word 即成真脚注（Ctrl+Shift+I）')
        _bfoot.clicked.connect(self.footnote_here)
        _bchrono = QPushButton('⌛ 纪年换算')
        _bchrono.setToolTip('民国 / 年号 / 干支纪年 ⇄ 公元年（含民国 1–38 年）（Ctrl+Shift+Y）')
        _bchrono.clicked.connect(self.chrono_dialog)
        _bexcv = QPushButton('🗂 摘录本')
        _bexcv.setToolTip('查看 / 编辑已摘录的资料（Ctrl+Shift+M）')
        _bexcv.clicked.connect(self.excerpt_viewer)
        self._btn_widgets += [_bsnap, _bexc, _bdual, _bfoot, _bchrono, _bexcv]
        for x in self._btn_widgets:
            row.addWidget(x)
        rv.addWidget(self.lb_info)
        rv.addWidget(self._build_find_bar())
        rv.addWidget(self.stack, 1)
        rv.addLayout(row)
        self.reader_panel = right               # 阅读区（可整体拆到独立窗口）
        self._reader_win = None
        self._split_sizes = None
        sp.addWidget(right)
        sp.setChildrenCollapsible(False)      # 两侧不可被折叠掉
        sp.setCollapsible(0, True)            # batch17：左栏可完全收起（拖到 0 或 Ctrl+Shift+L）
        sp.setCollapsible(1, False)
        sp.setStretchFactor(0, 0)             # 左：列表/详情，不抢空间
        sp.setStretchFactor(1, 1)             # 右：阅读区，占据窗口增量
        sp.setSizes([340, 1160])              # 阅读区默认占大头（窗口变窄时按比例缩放）
        self._split = sp
        self._split.splitterMoved.connect(self._on_split_moved)   # batch17：拖分割条时自适应左栏按钮
        v.addWidget(sp, 1)
        self.statusBar().showMessage('就绪')
        try:
            self._fit_left_buttons(340)
        except Exception:
            pass

    # ---- batch17：左栏宽度自适应／可缩到極小
    def _on_split_moved(self, *_):
        try:
            self._fit_left_buttons(self._split.sizes()[0])
        except Exception:
            pass

    def _fit_left_buttons(self, w):
        """左栏窄 → 次要按钮（检索历史/人名别名/摘录本）收进「⋮」；
        「跨文件全文检索」是本栏主入口，**尽量留住**（窄了换短标签，再窄只留图标）。"""
        try:
            w = int(w)
        except Exception:
            w = 340
        primary = getattr(self, 'b_fts', None)
        others = [x for x in (getattr(self, 'b_fts_hist', None),
                              getattr(self, 'b_alias', None),
                              getattr(self, 'b_exc', None)) if x is not None]
        more = getattr(self, 'b_more', None)
        if w >= 560:
            if primary is not None:
                primary.setText('🔎 跨文件全文检索')
            for b in others:
                b.setVisible(True)
            if more is not None:
                more.setVisible(False)
        elif w >= 380:
            if primary is not None:
                primary.setText('🔎 全文检索')
            for b in others:
                b.setVisible(False)
            if more is not None:
                more.setVisible(True)
        elif w >= 160:
            if primary is not None:
                primary.setText('🔎 检索')
            for b in others:
                b.setVisible(False)
            if more is not None:
                more.setVisible(True)
        else:
            if primary is not None:
                primary.setText('🔎')
            for b in others:
                b.setVisible(False)
            if more is not None:
                more.setVisible(True)
        tb = getattr(self, 'tb', None)
        if tb is not None:
            tb.setColumnHidden(2, w < 220)     # 太窄时收起「上级文件夹」列

    def toggle_list(self):
        """收起/展开左侧文件列表（Ctrl+Shift+L）。"""
        sp = getattr(self, '_split', None)
        if sp is None:
            return
        try:
            sz = sp.sizes()
        except Exception:
            return
        if sz and sz[0] > 40:
            self._list_prev = int(sz[0])
            sp.setSizes([0, int(sz[1]) + int(sz[0])])
            self.statusBar().showMessage('已收起文件列表（Ctrl+Shift+L 恢复）')
        else:
            w0 = int(getattr(self, '_list_prev', 360) or 360)
            right_w = int(sz[1]) if len(sz) > 1 else 900
            sp.setSizes([w0, max(200, right_w - w0)])
            self.statusBar().showMessage('已展开文件列表')
        try:
            self._fit_left_buttons(sp.sizes()[0])
        except Exception:
            pass

    # ---- 窗口尺寸 / 分割比例
    def _apply_default_size(self):
        """默认窗口尺寸：1200×820（不超过屏幕可用区 80%）——只要能看清 PDF 就好，不占满屏。"""
        try:
            scr = QApplication.primaryScreen()
            g = scr.availableGeometry() if scr is not None else None
            if g is not None and g.width() > 0 and g.height() > 0:
                w, h = min(1200, int(g.width() * 0.8)), min(820, int(g.height() * 0.8))
            else:
                w, h = 1200, 820
        except Exception:
            w, h = 1200, 820
        self.resize(max(1000, w), max(680, h))
        try:
            self._split.setSizes([260, max(700, w - 260)])   # 阅读器约占 3/4
            self._split.setStretchFactor(0, 1)              # 窗口拉伸时阅读器拿大头
            self._split.setStretchFactor(1, 3)
        except Exception:
            pass

    def resizeEvent(self, ev):
        """窗口变化时：左侧列表最大宽度 ≤ 窗口 32%（且 ≤560px），保证阅读区占大头。"""
        try:
            super().resizeEvent(ev)
        except Exception:
            pass
        try:
            tb = getattr(self, 'tb', None)
            if tb is not None:
                if getattr(self, '_reader_win', None) is not None:
                    tb.setMaximumWidth(16777215)      # 阅读器已独立 → 列表可占满
                else:
                    tb.setMaximumWidth(max(tb.minimumWidth(),
                                           min(880, int(self.width() * 0.46))))
            self._fit_left_buttons(self._split.sizes()[0])   # batch17：窗口变化时左栏按钮自适应
        except Exception:
            pass

    def _on_item_dbl(self, *_):
        """列表项双击 → 一律在阅读区内部打开（不再甩给外部程序）。"""
        self.open_here()

    def _on_item_click(self, item):
        """单击「文件名」列 → 即打开该文件（单击序号/上级文件夹列不打开）。"""
        if item is None or item.column() != 1:
            return
        r = item.row()
        if self.tb.currentRow() != r:
            self.tb.setCurrentCell(r, 1)
        self.open_here()

    def open_here(self):
        """在阅读区内部打开当前项：PDF/EPUB 走内置引擎渲染，TXT/MD/JSON/CSV 走文本预览。
        记历史/统计，刷新著录与版本下拉；外部程序只由「↗ 用外部程序打开」显式触发。
        batch9：防重入 —— 双击 = 单击 + 双击两次触发，这里只处理一次，避免重复加载卡顿。
        """
        r = self._cur()
        if not r:
            self.statusBar().showMessage('先在列表里选一个文件')
            return False
        p = os.path.join(r.get('dir') or '', r.get('name') or '')
        if not os.path.isfile(p):
            self.statusBar().showMessage('文件不在了：%s' % p)
            return False
        import time
        _now = time.time()
        if getattr(self, '_last_open_path', '') == p \
                and _now - getattr(self, '_last_open_t', 0.0) < 0.6:
            return False                      # 单击后紧跟的双击 → 忽略
        self._last_open_path, self._last_open_t = p, _now
        self.on_pick()                       # 刷新著录信息 + 版本下拉
        ext = ((r.get('ext') or os.path.splitext(p)[1]) or '').lower()
        if ext in ('.pdf', '.epub', '.xps', '.cbz', '.mobi', '.fb2', '.svg'):
            try:
                import fitz
                if ext == '.pdf':
                    with open(p, 'rb') as f:
                        if not f.read(5).startswith(b'%PDF'):
                            raise ValueError('PDF 结构不完整（可先用 CathayRepair 修一下）')
                d = fitz.open(p)
                if int(getattr(d, 'page_count', 0) or 0) <= 0:
                    self.statusBar().showMessage('这个文件没有可显示的页面')
                    return False
                self.pd = d
                self._pd_path = p
                self.pgno = 0
                try:
                    _mk = (C.load_settings().get('marks') or {}).get(p) or {}
                    self.pgno = max(0, min(int(d.page_count) - 1, int(_mk.get('page') or 0)))
                except Exception:
                    pass
                self._pdf_show()
                self._after_pdf_open()
                self._hist_add()
                self._stat_open(p)
                self.statusBar().showMessage(
                    '已在阅读区打开：%s（共 %d 页，连续滚动，PgUp/PgDn 翻页）'
                    % (os.path.basename(p), int(d.page_count)))
                return True
            except Exception as e:
                self.statusBar().showMessage(
                    '阅读区打开失败：%s（可点「↗ 用外部程序打开」）' % e)
                return False
        if ext in ('.txt', '.md', '.json', '.csv'):
            try:
                self._show_text_file(p)      # 内部已记统计
                self._hist_add()
                self.statusBar().showMessage('已在阅读区打开：%s' % os.path.basename(p))
                return True
            except Exception as e:
                self.statusBar().showMessage('阅读区打开失败：%s' % e)
                return False
        self.view.setPlainText('这个格式（%s）暂不支持在此预览，'
                               '点「↗ 用外部程序打开」。' % ext)
        self._pdf_stop()
        self._hide_nav()
        self.pd = None
        self._pd_path = ''
        self._reader = 'text'
        return False

    # ---- 状态
    def _refresh_status(self):
        if not self.db or not os.path.isfile(self.db):
            self.statusBar().showMessage('还没建索引 —— 点「建库 / 刷新」开始（只读扫描，不改源库）')
            return
        s = C.stats(self.db)
        self.statusBar().showMessage(
            '索引：%s 个文件 ｜ 库 %.1f MB ｜ %s ｜ 建于 %s%s'
            % (s.get('files'), s.get('db_size', 0) / 1048576.0, self.db,
               s.get('built_at', ''), ' ｜ 缺失 %s' % s.get('missing') if s.get('missing') else ''))

    # ---- 动作
    def do_build(self):
        w = Wizard(self, self.st, first_run=not os.path.isfile(self.db or ''))
        if w.exec() and w.result_info and not w.result_info.get('used_existing'):
            self.st = w.result_info.get('settings', self.st)
            self.db = self.st.get('primary_db', self.db)
            self._refresh_status()
        elif w.result_info and w.result_info.get('used_existing'):
            self.db = w.result_info['db']
            self._refresh_status()

    def do_search(self):
        if not self.db or not os.path.isfile(self.db):
            QMessageBox.information(self, '提示', '还没有索引库，先点「建库 / 刷新」。')
            return
        kw = self.ed_kw.text().strip()
        if not kw:
            return
        self._search_hist_add(kw)      # 记一条搜索历史（去重、新的在前）
        extras = self._alias_extra(kw)         # 人名别名归一：一并检索字号/笔名/化名
        kws = [kw] + extras
        self._hl_kws = list(kws)               # 多关键词黄底高亮
        rows = []
        for _k in kws:
            try:
                rows += C.search(self.db, _k, 800)
            except Exception:
                pass
        # 同一个文件的多种后缀（PDF/TXT/繁转简…）串成一条，不在列表里并列显示
        seen = {}
        self.rows = []
        for r in rows:
            try:
                q = META.parse(r.get('name') or '',
                               os.path.join(r.get('dir') or '', r.get('name') or ''),
                               deep=False)   # 列表只按文件名分组，不读版权页（快）
                key = (r.get('dir') or '', q.get('name') or r.get('name'), q.get('volume') or '')
            except Exception:
                key = (r.get('dir') or '', r.get('name') or '', '')
            hit = seen.get(key)
            if hit is None:
                seen[key] = r
                self.rows.append(r)
            else:
                hn, rn = (hit.get('name') or '').lower(), (r.get('name') or '').lower()
                if rn.endswith('.pdf') and not hn.endswith('.pdf'):   # PDF 原本优先
                    self.rows[self.rows.index(hit)] = r
                    seen[key] = r
        self._last_kw = kw            # 供文件名列黄底高亮
        self._fill_rows(rows)
        _msg = '搜到 %d 本（原始命中 %d 条，同书各版本已串在一起）' % (len(self.rows), len(rows))
        if len(kws) > 1:
            _msg += '；已并入别名：%s' % '、'.join(extras[:10])
        self.statusBar().showMessage(_msg)

    def _fill_rows(self, rows, dedup=True):
        """填充左栏表格。dedup=True 时把「同书同版本」串一条（PDF 原本优先）；
        dedup=False（直接打开文件时的邻居列表）则**每个文件都保留**。"""
        seen = {}
        self.rows = []
        for r in rows:
            if not dedup:
                self.rows.append(r)
                continue
            try:
                q = META.parse(r.get('name') or '',
                               os.path.join(r.get('dir') or '', r.get('name') or ''),
                               deep=False)   # 列表只按文件名分组，不读版权页（快）
                key = (r.get('dir') or '', q.get('name') or r.get('name'), q.get('volume') or '')
            except Exception:
                key = (r.get('dir') or '', r.get('name') or '', '')
            hit = seen.get(key)
            if hit is None:
                seen[key] = r
                self.rows.append(r)
            else:
                hn, rn = (hit.get('name') or '').lower(), (r.get('name') or '').lower()
                if rn.endswith('.pdf') and not hn.endswith('.pdf'):   # PDF 原本优先
                    self.rows[self.rows.index(hit)] = r
                    seen[key] = r
        self.tb.setRowCount(0)
        for r in self.rows:
            k = self.tb.rowCount()
            self.tb.insertRow(k)
            nm = r.get('name') or ''
            dr = r.get('dir') or ''
            parent = os.path.basename(dr.rstrip('\\/')) or dr      # 只显示上一级
            it0 = QTableWidgetItem(str(k + 1))
            it0.setToolTip('序号')
            it1 = QTableWidgetItem(nm)
            it1.setToolTip(nm)
            it2 = QTableWidgetItem(parent)
            it2.setToolTip(dr)
            self.tb.setItem(k, 0, it0)
            self.tb.setItem(k, 1, it1)
            self.tb.setItem(k, 2, it2)
        try:
            self.tb.viewport().update()
        except Exception:
            pass
        return len(self.rows)

    # ---- batch18：直接打开某文件 → 左栏列出「同文件夹 + 文件名相似」的文件
    def _similar_key(self, name):
        """相似文件名的检索键：书名主干，再去掉「续编 / 补遗 / 外编」这类尾缀。"""
        try:
            s = META.book_core(name or '')
        except Exception:
            s = name or ''
        s2 = re.sub(r'(续编|续集|续录|补遗|补编|外编|附编|新编|前编|后编|别编|二编|三编|再编)$', '', s)
        s2 = s2.strip(' _-—+·、.')
        return s2 or s

    def _list_neighbors(self, p, limit_same=300, limit_like=300):
        """把 p 所在文件夹的文件 + 与 p 书名主干相似的文件填到左栏（并尽量选中 p）。"""
        p = os.path.abspath(p)
        d = os.path.dirname(p)
        base = os.path.basename(p)
        _stem = os.path.splitext(base)[0]
        try:
            self.ed_kw.setText(_stem)
        except Exception:
            pass
        self._last_kw = ''
        self._hl_kws = []
        rows, seen = [], set()

        def _add(rs):
            for r in rs:
                try:
                    k = (os.path.normcase(r.get('dir') or ''),
                         (r.get('name') or '').lower())
                except Exception:
                    continue
                if k in seen:
                    continue
                seen.add(k)
                rows.append(r)

        n_same = 0
        # ① 同文件夹（先查索引库，再把磁盘上没进库的也补上）
        try:
            same = C.by_dir(self.db, d, limit_same) if self.db else []
        except Exception:
            same = []
        n_same = len(same)
        _add(same)
        try:
            for e in os.scandir(d):
                if not e.is_file():
                    continue
                if os.path.splitext(e.name)[1].lower() not in C.EXTS:
                    continue
                try:
                    stt = e.stat()
                except OSError:
                    continue
                _add([{'dir': d, 'name': e.name, 'size': stt.st_size,
                       'mtime': stt.st_mtime}])
        except OSError:
            pass
        # ② 书名主干相似（不限文件夹）：主干 + 去掉「续编/补遗」等尾缀的更宽键
        try:
            core = META.book_core(base) or _stem
        except Exception:
            core = _stem
        try:
            core2 = self._similar_key(base)
        except Exception:
            core2 = core
        keys = []
        for k in (core, core2):
            if k and k not in keys:
                keys.append(k)
        n_like = 0
        for k in keys:
            try:
                like = C.like_stem(self.db, k, limit_like) if self.db else []
                n_like += len(like)
                _add(like)
            except Exception:
                pass
        n = self._fill_rows(rows, dedup=False)          # 邻居列表：每个文件都列出来
        # 选中打开的那一个
        want = os.path.normcase(p)
        for i, r in enumerate(self.rows):
            if os.path.normcase(os.path.abspath(
                    os.path.join(r.get('dir') or '', r.get('name') or ''))) == want:
                try:
                    self.tb.setCurrentCell(i, 0)
                except Exception:
                    pass
                break
        self.statusBar().showMessage(
            '左侧：同文件夹 %d 个 ｜ 相似文件名 %d 个（共 %d 个）' % (n_same, n_like, n))
        return n

    def _meta_brief(self, name, path):
        """著录列文本：作者 · 出版社 · 年 · SSID（只解析文件名，deep=False，快）。"""
        try:
            q = META.parse(name or '', path or '', deep=False)
        except Exception:
            return ''
        bits = []
        try:
            for b in (q.get('author'), q.get('publisher'),
                      ((q.get('year') or '') + '年') if q.get('year') else '',
                      ('SSID ' + q.get('ssid')) if q.get('ssid') else ''):
                if b:
                    bits.append(b)
        except Exception:
            pass
        return ' · '.join(bits)

    # ---- 搜索历史 / 已保存的搜索（Ctrl+K / Ctrl+D）----
    # ---- 人名别名归一（👤 / Ctrl+Shift+A）
    def _alias_extra(self, kw):
        """kw 是收录的人物时，返回要一并检索的字号/笔名/化名（按设置询问/自动/关闭）。"""
        try:
            extra = ALIAS.expand(kw)
        except Exception:
            extra = []
        if not extra:
            return []
        mode = self.st.get('alias_mode', 'ask')
        if mode == 'off' or getattr(self, '_alias_silent', False):
            return []
        if mode == 'auto':
            return extra
        try:
            r = QMessageBox.question(
                self, '人名别名',
                '「%s」还有其他字号 / 笔名 / 化名：\n\n%s\n\n是否连同这些名字一起检索？'
                % (kw, '、'.join(extra[:20]) + ('…等 %d 个' % len(extra) if len(extra) > 20 else '')),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes)
            return extra if r == QMessageBox.StandardButton.Yes else []
        except Exception:
            return []

    def _refresh_alias_count(self, lbl):
        try:
            c = ALIAS.count()
            lbl.setText('已收录 %d 人 / %d 个字号·笔名·化名；检索到人物名时按设置处理。'
                        % (c['people'], c['aliases']))
        except Exception:
            pass

    def alias_dialog(self):
        """👤 人名别名表：查看/增删/导入导出，并设置检索时的处理方式。"""
        from PyQt6.QtWidgets import QListWidget, QListWidgetItem, QFileDialog, QInputDialog
        dlg = QDialog(self)
        dlg.setWindowTitle('人名别名表')
        dlg.resize(780, 640)
        vb = QVBoxLayout(dlg)
        head = QLabel('')
        head.setWordWrap(True)
        vb.addWidget(head)
        row = QHBoxLayout()
        row.addWidget(QLabel('检索时：'))
        cb = QComboBox()
        cb.addItems(['询问我（默认）', '自动并入别名', '关闭别名归一'])
        cb.setCurrentIndex({'ask': 0, 'auto': 1, 'off': 2}.get(self.st.get('alias_mode', 'ask'), 0))

        def _mode(i):
            self.st['alias_mode'] = {0: 'ask', 1: 'auto', 2: 'off'}[i]
            try:
                C.save_settings(self.st)
            except Exception:
                pass
            self.statusBar().showMessage('人名别名：%s' % cb.currentText())
        cb.currentIndexChanged.connect(_mode)
        row.addWidget(cb)
        row.addStretch(1)
        vb.addLayout(row)
        lst = QListWidget()
        vb.addWidget(lst, 1)

        def _fill():
            lst.clear()
            g = ALIAS.groups()
            for canon in sorted(g.keys(), key=lambda x: (len(x), x)):
                als = g.get(canon) or []
                it = QListWidgetItem('%s：%s' % (canon, '、'.join(als[:12]) + ('…' if len(als) > 12 else '')))
                it.setData(Qt.ItemDataRole.UserRole, canon)
                it.setToolTip(canon + '：' + '、'.join(als))
                lst.addItem(it)
        _fill()
        self._refresh_alias_count(head)
        brow = QHBoxLayout()
        b_add = QPushButton('新增/编辑')
        b_del = QPushButton('删除')
        b_imp = QPushButton('导入 CSV')
        b_exp = QPushButton('导出 CSV')
        b_cbdb = QPushButton('从 CBDB 导入…')
        b_find = QPushButton('查一个人')
        b_close = QPushButton('关闭')
        for w in (b_add, b_del, b_imp, b_exp, b_cbdb, b_find):
            brow.addWidget(w)
        brow.addStretch(1)
        brow.addWidget(b_close)
        vb.addLayout(brow)

        def do_add():
            canon, okk = QInputDialog.getText(dlg, '新增/编辑', '正名（如 吴佩孚）：')
            if not okk or not (canon or '').strip():
                return
            als, ok2 = QInputDialog.getText(dlg, '别名', '该人的字/号/笔名/化名（顿号或逗号分隔）：')
            if not ok2:
                return
            ALIAS.add_person(canon.strip(), als)
            _fill()
            self._refresh_alias_count(head)

        def do_del():
            it = lst.currentItem()
            if not it:
                return
            canon = it.data(Qt.ItemDataRole.UserRole)
            if QMessageBox.question(dlg, '删除', '从本地表里删除「%s」？' % canon) \
                    == QMessageBox.StandardButton.Yes:
                ALIAS.remove_person(canon)
                _fill()
                self._refresh_alias_count(head)

        def do_imp():
            p, _ = QFileDialog.getOpenFileName(dlg, '导入别名 CSV', '', 'CSV (*.csv);;所有文件 (*)')
            if not p:
                return
            n = ALIAS.import_csv(p)
            _fill()
            self._refresh_alias_count(head)
            self.statusBar().showMessage('导入完成：新增 %d 人 / %d 别名' % (n[0], n[1]))

        def do_exp():
            p, _ = QFileDialog.getSaveFileName(dlg, '导出别名 CSV', 'person_alias.csv', 'CSV (*.csv)')
            if p:
                ALIAS.write_csv(p)
                self.statusBar().showMessage('已导出：%s' % p)

        def do_cbdb():
            d = QFileDialog.getExistingDirectory(
                dlg, '选 CBDB 导出目录（含 ALTNAME_DATA.xlsx / BIOG_MAIN.xlsx）')
            if not d:
                return
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            try:
                n = ALIAS.import_cbdb_dir(d)
                _fill()
                self._refresh_alias_count(head)
                self.statusBar().showMessage('CBDB 导入完成：%d 人 / %d 别名' % (n[0], n[1]))
            except Exception as e:
                QMessageBox.warning(dlg, '导入失败', str(e))
            finally:
                QApplication.restoreOverrideCursor()

        def do_find():
            k, okk = QInputDialog.getText(dlg, '查一个人', '输入人名或字号：')
            if not okk or not (k or '').strip():
                return
            hits = ALIAS.lookup(k.strip())
            if not hits:
                self.statusBar().showMessage('未收录：%s' % k.strip())
                return
            QMessageBox.information(dlg, '查询结果', '\n\n'.join(
                '正名：%s\n别名：%s' % (h['canonical'], '、'.join(h['aliases'])) for h in hits))

        b_add.clicked.connect(do_add)
        b_del.clicked.connect(do_del)
        b_imp.clicked.connect(do_imp)
        b_exp.clicked.connect(do_exp)
        b_cbdb.clicked.connect(do_cbdb)
        b_find.clicked.connect(do_find)
        b_close.clicked.connect(dlg.accept)
        self._last_alias_dlg = {'dlg': dlg, 'list': lst, 'combo': cb}
        dlg.exec()

    def _search_hist_add(self, kw):
        """Enter 搜索时自动记一条（去重、新的在前、最多 50 条）。"""
        kw = (kw or '').strip()
        if not kw:
            return
        try:
            st = C.load_settings()
            h = [x for x in (st.get('search_hist') or []) if x != kw]
            h.insert(0, kw)
            st['search_hist'] = h[:50]
            C.save_settings(st)
        except Exception:
            pass

    def _rerun_search(self, kw):
        """用给定关键词重跑一次搜索（历史/已保存双击用）。"""
        try:
            self.ed_kw.setText(kw or '')
            self.do_search()
            self.statusBar().showMessage('已重搜：%s' % kw)
        except Exception as e:
            self.statusBar().showMessage('重搜失败：%s' % e)

    def save_search(self):
        """Ctrl+D：把当前关键词存入 settings['saved_searches']。"""
        kw = self.ed_kw.text().strip()
        if not kw:
            self.statusBar().showMessage('搜索框是空的，先输入关键词再按 Ctrl+D')
            return
        try:
            st = C.load_settings()
            s = [x for x in (st.get('saved_searches') or []) if x != kw]
            s.insert(0, kw)
            st['saved_searches'] = s[:50]
            C.save_settings(st)
            self.statusBar().showMessage('已保存搜索：%s（Ctrl+K 查看/删除）' % kw)
        except Exception as e:
            self.statusBar().showMessage('保存失败：%s' % e)

    def search_history_dialog(self):
        """Ctrl+K：搜索历史 + 已保存的搜索（双击重搜，可删除）。"""
        try:
            st = C.load_settings()
            hist = list(st.get('search_hist') or [])
            saved = list(st.get('saved_searches') or [])
        except Exception:
            hist, saved = [], []
        dlg = QDialog(self)
        dlg.setWindowTitle('搜索历史 / 已保存的搜索')
        dlg.resize(640, 540)
        vb = QVBoxLayout(dlg)
        vb.addWidget(QLabel('历史（最近 %d 条，双击重搜）：' % len(hist)))
        lh = QListWidget()
        for k in hist:
            lh.addItem(k)
        vb.addWidget(lh, 1)
        vb.addWidget(QLabel('已保存（Ctrl+D 添加，双击重搜）：'))
        ls = QListWidget()
        for k in saved:
            ls.addItem(k)
        vb.addWidget(ls, 1)

        def go(kw):
            self._rerun_search(kw)
            dlg.accept()

        def go_h():
            i = lh.currentRow()
            if 0 <= i < len(hist):
                go(hist[i])

        def go_s():
            i = ls.currentRow()
            if 0 <= i < len(saved):
                go(saved[i])

        def dele():
            kill = set()
            for it in lh.selectedItems():
                kill.add(it.text())
            for it in ls.selectedItems():
                kill.add(it.text())
            if not kill:
                self.statusBar().showMessage('先选中要删除的条目')
                return
            try:
                stt = C.load_settings()
                stt['search_hist'] = [x for x in (stt.get('search_hist') or [])
                                      if x not in kill]
                stt['saved_searches'] = [x for x in (stt.get('saved_searches') or [])
                                         if x not in kill]
                C.save_settings(stt)
            except Exception as e:
                self.statusBar().showMessage('删除失败：%s' % e)
                return
            for lst, items in ((lh, list(lh.selectedItems())),
                               (ls, list(ls.selectedItems()))):
                for it in items:
                    lst.takeItem(lst.row(it))
            self.statusBar().showMessage('已删除 %d 条（历史/已保存）' % len(kill))

        lh.itemDoubleClicked.connect(lambda _: go_h())
        ls.itemDoubleClicked.connect(lambda _: go_s())
        self._last_hist = {'hist': hist, 'saved': saved}
        row = QHBoxLayout()
        bd = QPushButton('删除选中')
        bd.clicked.connect(dele)
        bf = QPushButton('关闭')
        bf.clicked.connect(dlg.accept)
        row.addWidget(bd)
        row.addStretch(1)
        row.addWidget(bf)
        vb.addLayout(row)
        dlg.exec()

    # ---- 阅读统计（打开次数 / 累计时长 / 最常阅读）----
    def _stat_open(self, path):
        """打开文件时调用：先结算上一个文件，再给这个文件记一次打开。"""
        try:
            import time
            self._stat_flush()            # 结算上一个文件
            if not path:
                return
            st = C.load_settings()
            stats = st.get('stats') or {}
            e = stats.get(path) or {}
            e['opens'] = int(e.get('opens') or 0) + 1
            e['secs'] = float(e.get('secs') or 0.0)
            e['last'] = time.strftime('%m-%d %H:%M')
            stats[path] = e
            st['stats'] = stats
            C.save_settings(st)
            self._stat_path = path
            self._stat_t0 = time.time()
        except Exception as ex:
            self._stat_path = ''
            self._stat_t0 = 0.0
            self.statusBar().showMessage('统计记录失败：%s' % ex)

    def _stat_flush(self):
        """把当前文件的阅读时长累加进 settings['stats']（切换文件/关窗时）。"""
        p = getattr(self, '_stat_path', '') or ''
        t0 = getattr(self, '_stat_t0', 0.0) or 0.0
        self._stat_path = ''
        self._stat_t0 = 0.0
        if not p or not t0:
            return
        try:
            import time
            secs = max(0.0, time.time() - t0)
            st = C.load_settings()
            stats = st.get('stats') or {}
            e = stats.get(p) or {}
            e['secs'] = float(e.get('secs') or 0.0) + secs
            e['opens'] = int(e.get('opens') or 0)
            e['last'] = time.strftime('%m-%d %H:%M')
            stats[p] = e
            st['stats'] = stats
            C.save_settings(st)
        except Exception as ex:
            self.statusBar().showMessage('统计写入失败：%s' % ex)

    def _stats_text(self):
        """阅读统计文本：总累计时长 + 最近 20 本 + 最常阅读 Top 20。"""
        def fmt(s):
            s = float(s or 0)
            if s < 60:
                return '%.0f 秒' % s
            if s < 3600:
                return '%.1f 分钟' % (s / 60.0)
            return '%.1f 小时' % (s / 3600.0)

        try:
            st = C.load_settings()
            stats = {p: e for p, e in (st.get('stats') or {}).items()
                     if isinstance(e, dict)}
        except Exception:
            stats = {}
        total = sum(float(e.get('secs') or 0) for e in stats.values())

        def line(p, e):
            return '%-30s  打开 %d 次 · 累计 %s · 最后 %s' % (
                os.path.basename(p), int(e.get('opens') or 0),
                fmt(e.get('secs')), e.get('last') or '')

        recent = sorted(stats.items(), key=lambda x: str(x[1].get('last') or ''),
                        reverse=True)[:20]
        top = sorted(stats.items(),
                     key=lambda x: (int(x[1].get('opens') or 0),
                                    float(x[1].get('secs') or 0)),
                     reverse=True)[:20]
        L = ['总累计阅读时长：%s（共 %d 本有记录）' % (fmt(total), len(stats)), '',
             '— 最近读的 20 本 —']
        L += [line(p, e) for p, e in recent] or ['（暂无）']
        L += ['', '— 最常阅读 Top 20（按打开次数 / 时长）—']
        L += [line(p, e) for p, e in top] or ['（暂无）']
        return '\n'.join(L)

    def read_stats_dialog(self):
        """Ctrl+Shift+H：阅读统计对话框。"""
        txt = self._stats_text()
        self._last_stats_text = txt
        dlg = QDialog(self)
        dlg.setWindowTitle('阅读统计')
        dlg.resize(680, 540)
        vb = QVBoxLayout(dlg)
        te = QTextEdit()
        te.setReadOnly(True)
        te.setPlainText(txt)
        vb.addWidget(te, 1)
        bb = QPushButton('好')
        bb.clicked.connect(dlg.accept)
        vb.addWidget(bb)
        dlg.exec()

    def closeEvent(self, ev):
        """关窗：停后台深著录线程 + 结算阅读时长 + 记住布局 + 一并关掉独立阅读窗口。"""
        try:
            self._stop_meta_worker()
        except Exception:
            pass
        try:
            self._stat_flush()
        except Exception:
            pass
        self._save_layout()
        # batch18：阅读器是独立顶层窗口，主窗口退出时把它一并关掉（否则程序不会退出）
        try:
            win = getattr(self, '_reader_win', None)
            if win is not None:
                self._closing = True
                win._cv_no_attach = True
                win.close()
                self._reader_win = None
        except Exception:
            pass
        try:
            super().closeEvent(ev)
        except Exception:
            pass

    # ---- batch9：窗口布局记忆（尺寸/位置、分割比例、是否拆窗）
    def _layout_dict(self):
        d = {'win_geom': [self.x(), self.y(), self.width(), self.height()],
             'reader_detached': getattr(self, '_reader_win', None) is not None}
        try:
            d['split_sizes'] = list(self._split.sizes())
        except Exception:
            pass
        w = getattr(self, '_reader_win', None)
        if w is not None:
            try:
                d['reader_geom'] = [w.x(), w.y(), w.width(), w.height()]
            except Exception:
                pass
        return d

    def _save_layout(self):
        if not getattr(self, '_layout_track', False):
            return
        try:
            st = C.load_settings()
            st.update(self._layout_dict())
            C.save_settings(st)
        except Exception:
            pass

    def _restore_layout(self):
        """启动时恢复上次的窗口布局；返回是否应拆成双窗口。"""
        try:
            st = C.load_settings()
        except Exception:
            return False
        g = st.get('win_geom')
        if isinstance(g, (list, tuple)) and len(g) == 4:
            try:
                self.setGeometry(int(g[0]), int(g[1]),
                                 max(1000, int(g[2])), max(680, int(g[3])))
            except Exception:
                pass
        sz = st.get('split_sizes')
        if isinstance(sz, (list, tuple)) and len(sz) == 2:
            try:
                self._split.setSizes([max(160, int(sz[0])), max(300, int(sz[1]))])
            except Exception:
                pass
        self._layout_track = True
        return bool(st.get('reader_detached'))

    def _cur(self):
        i = self.tb.currentRow()
        return self.rows[i] if 0 <= i < len(self.rows) else None

    def on_pick(self):
        """选中一项 → 立即用「浅著录」显示详情（不阻塞），深著录（读 PDF 文字层）放后台线程。 batch16"""
        r = self._cur()
        if not r:
            return
        p = os.path.join(r.get('dir') or '', r.get('name') or '')
        try:
            mtime = os.path.getmtime(p)
        except OSError:
            mtime = 0.0
        try:
            nkey = os.path.normcase(os.path.abspath(p))
        except Exception:
            nkey = p
        key = (nkey, round(float(mtime), 3))
        cache = getattr(self, '_meta_map', None)
        if cache is None:
            cache = self._meta_map = {}
        m = cache.get(key)
        deep = bool(m is not None and m.get('_deep'))
        if m is None:
            try:
                m = META.parse(r.get('name') or '', p, deep=False)
            except Exception:
                m = {'name': r.get('name') or '', 'volume': '', 'author': '',
                     'publisher': '', 'year': '', 'ssid': '', 'trad': False,
                     'ext': '', 'tail': '', 'path': p, 'raw': r.get('name') or ''}
            if len(cache) > 400:
                cache.clear()
            cache[key] = m
        self.meta = m
        self._meta_cache = {'_k': (p, mtime), '_m': m}      # 兼容旧引用
        self._render_info(r, m)
        self._fill_versions(m)
        if not deep:
            self._request_deep_meta(r.get('name') or '', p, mtime, key)

    def _render_info(self, r, m):
        """把著录信息写进详情条（浅/深著录共用）。"""
        try:
            p = os.path.join(r.get('dir') or '', r.get('name') or '')
            bits = [b for b in (m.get('author'), m.get('volume'), m.get('publisher'),
                                ((m.get('year') or '') + '年') if m.get('year') else '',
                                ('SSID ' + m['ssid']) if m.get('ssid') else '',
                                '【繁体】' if m.get('trad') else '') if b]
            info = ('<b>%s</b><br>%s<br>%.1f KB ｜ %s<br>'
                    '<span style="color:#1e7a6f">%s</span>'
                    % (m.get('name') or r.get('name'), p,
                       (r.get('size') or 0) / 1024.0, _ts(r.get('mtime')),
                       ' ｜ '.join(bits) or '（文件名里没有元数据）'))
            _rb = self._rights_text(m)
            if _rb:
                info += '<br><span style="color:#8a5a00">版权/授权：%s</span>' % _rb
            if not m.get('_deep'):
                info += '<br><span style="color:#888">（正在后台深度著录…）</span>'
            self.lb_info.setText(info)
            _tip = (re.sub(r'<br\s*/?>', '\n', info).replace('&nbsp;', ' ')
                    .replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&'))
            self.lb_info.setToolTip(_tip)
            self.b_info.setToolTip('文件详情（默认隐藏）：\n' + _tip)
        except Exception:
            pass

    # ---- batch16：后台深著录（不卡界面）
    def _stop_meta_worker(self, ms=4000):
        """关窗/退出前等后台线程结束（QThread 运行中被销毁会触发原生 fail-fast）。"""
        self._meta_closing = True
        self._meta_pending = None
        w = getattr(self, '_meta_worker', None)
        try:
            if w is not None and w.isRunning():
                w.wait(int(ms))
        except Exception:
            pass

    def _request_deep_meta(self, name, path, mtime, key):
        if getattr(self, '_meta_closing', False):
            return
        cur = getattr(self, '_meta_worker', None)
        if cur is not None and cur.isRunning():
            self._meta_pending = (name, path, mtime, key)
            return
        try:
            w = MetaWorker(name, path, mtime, self)
        except Exception:
            return
        w.done.connect(self._on_deep_meta)
        self._meta_worker = w
        self._meta_pending = None
        try:
            w.start()
        except Exception:
            pass

    def _on_deep_meta(self, path, mtime, m):
        try:
            if m:
                m['_deep'] = True
                try:
                    nkey = os.path.normcase(os.path.abspath(path))
                except Exception:
                    nkey = path
                key = (nkey, round(float(mtime), 3))
                if getattr(self, '_meta_map', None) is None:
                    self._meta_map = {}
                self._meta_map[key] = m
                r = self._cur()
                cp = os.path.join(r.get('dir') or '', r.get('name') or '') if r else ''
                if r and os.path.normcase(os.path.abspath(cp)) == nkey:
                    self.meta = m
                    self._meta_cache = {'_k': (cp, mtime), '_m': m}
                    self._render_info(r, m)
        except Exception:
            pass
        finally:
            pend = getattr(self, '_meta_pending', None)
            self._meta_pending = None
            if pend:
                self._request_deep_meta(*pend)
            else:
                # 当前项仍是浅著录 → 继续补深著录
                try:
                    r = self._cur()
                    if r:
                        p = os.path.join(r.get('dir') or '', r.get('name') or '')
                        mm = self._meta_map.get((os.path.normcase(os.path.abspath(p)),
                                                 round(float(os.path.getmtime(p)), 3)))
                        if mm is not None and not mm.get('_deep'):
                            self._request_deep_meta(r.get('name') or '', p,
                                                    os.path.getmtime(p),
                                                    (os.path.normcase(os.path.abspath(p)),
                                                     round(float(os.path.getmtime(p)), 3)))
                except Exception:
                    pass

    def _rights_text(self, m):
        """把版权/授权信息拼成一行（标注来源：文件名 / 上级目录 / 版权页）。"""
        rr = (m.get('rights') or {}) if isinstance(m, dict) else {}
        src = (m.get('rights_src') or {}) if isinstance(m, dict) else {}
        labels = [('authorization', '授权'), ('copyright_holder', '版权'),
                  ('copyright_line', '版权'), ('rights_holder', '出版发行'),
                  ('isbn', 'ISBN'), ('edition', '版次'), ('printing', '印次'),
                  ('pub_date', '出版年月')]
        srcname = {'file': '文件名', 'folder': '上级目录', 'colophon': '版权页'}
        out = []
        for k, lab in labels:
            v = rr.get(k)
            if v:
                tag = srcname.get(src.get(k), '')
                out.append('%s %s%s' % (lab, v, ('（%s）' % tag) if tag else ''))
        return ' ｜ '.join(out)

    def _fill_versions(self, m):
        """按书名把同一本书的各版本都找出来（PDF 原本 / 繁转简 TXT / 其它）。"""
        self.vers = []
        self.cb_ver.blockSignals(True)
        self.cb_ver.clear()
        try:
            cand = C.search(self.db, m.get('name') or '', 200) if m.get('name') else []
            for r in cand:
                q = META.parse(r.get('name') or '',
                               os.path.join(r.get('dir') or '', r.get('name') or ''),
                               deep=False)   # 同书判定用文件名即可
                if q.get('name') == m.get('name') and q.get('volume') == m.get('volume'):
                    self.vers.append(q)
            self.vers = META.versions_of(self.vers, m.get('name'), m.get('volume'))
        except Exception:
            pass
        for v in self.vers:
            tag = 'PDF 原本' if (v.get('ext') == '.pdf' and not v.get('tail')) else \
                (v.get('ext', '').lstrip('.').upper() + (v.get('tail') or ''))
            self.cb_ver.addItem('%s ｜ %s' % (tag, os.path.basename(v.get('path') or '')))
        self.cb_ver.blockSignals(False)
        if self.vers:
            self.statusBar().showMessage('这本书有 %d 个版本（下拉可切）' % len(self.vers))

    def bookmark_here(self):
        """记住当前位置（写进设置；下次打开同一文件自动跳回）。Ctrl+B"""
        r = self._cur()
        if not r:
            return
        import time
        p = os.path.join(r.get('dir') or '', r.get('name') or '')
        try:
            st = C.load_settings()
            bm = st.get('marks') or {}
            bm[p] = {'page': int(getattr(self, 'pgno', 0)),
                     'at': time.strftime('%Y-%m-%d %H:%M')}
            st['marks'] = bm
            C.save_settings(st)
            self._hist_add()
            self.statusBar().showMessage('已记住位置：第 %d 页'
                                         % (int(getattr(self, 'pgno', 0)) + 1))
        except Exception as e:
            self.statusBar().showMessage('记忆失败：%s' % e)

    def toc_here(self):
        """Ctrl+T：显示导航面板的「目录」页签（PDF / EPUB 大纲；没大纲就列页码）。"""
        cur = self._path()
        ext = os.path.splitext(cur)[1].lower()
        openable = ext in ('.pdf', '.epub', '.xps', '.cbz', '.mobi', '.fb2', '.svg')
        d = getattr(self, 'pd', None)
        # 当前选中项是可渲染的电子书（含 EPUB），且不是已打开的那本 → 就地打开它
        if cur and os.path.isfile(cur) and openable and \
                (d is None or getattr(self, '_pd_path', '') != cur):
            try:
                import fitz
                d = fitz.open(cur)
                self.pd = d
                self._pd_path = cur
                self.pgno = 0
                self._pdf_show()
                self._after_pdf_open()
            except Exception:
                d = getattr(self, 'pd', None)
        if d is None:
            self.statusBar().showMessage('目录只对已打开的 PDF / EPUB 有效（先点 📖 在阅读区打开）')
            return
        n = self._fill_nav_toc()
        self._show_nav(0)
        self.statusBar().showMessage('目录：%d 项（Ctrl+T 显示/隐藏）' % n)

    def open_path_in_reader(self, p, note=''):
        """把某个文件在阅读区内部打开；左栏自动列出同文件夹 + 文件名相似的文件（batch18）。"""
        try:
            if self.db and os.path.isfile(self.db):
                self._list_neighbors(p)          # batch18：直接打开 → 自动列邻居（含选中）
            else:                                # 没索引库：退回按文件名搜
                self.ed_kw.setText(os.path.splitext(os.path.basename(p))[0])
                self.do_search()
            want = os.path.normcase(os.path.abspath(p))
            cur = -1
            for i, r in enumerate(self.rows):
                rp = os.path.normcase(os.path.abspath(
                    os.path.join(r.get('dir') or '', r.get('name') or '')))
                if rp == want:
                    cur = i
                    break
            if cur < 0 and self.rows:
                cur = 0                          # 库里没登记 → 仍打开文件，列表选第一个
            if cur >= 0:
                self.tb.setCurrentCell(cur, 0)
                self.on_pick()
        except Exception:
            pass
        ok = self._open_path(p)              # 一律在阅读区内部打开（PDF/EPUB/文本）
        if ok:
            self._say('已在阅读区打开：%s%s' % (os.path.basename(p), note or ''), hold=1.5)
        return ok

    # ---- batch15：拖入文件即打开（PDF / TXT 等）
    def _url_reader_ok(self, u):
        try:
            p = u.toLocalFile()
            return bool(p) and os.path.isfile(p) and \
                os.path.splitext(p)[1].lower() in READER_EXTS
        except Exception:
            return False

    def dragEnterEvent(self, ev):
        try:
            md = ev.mimeData()
            if md is not None and md.hasUrls() and any(self._url_reader_ok(u) for u in md.urls()):
                ev.acceptProposedAction()
                return
        except Exception:
            pass
        try:
            ev.ignore()
        except Exception:
            pass

    def dragMoveEvent(self, ev):
        try:
            ev.acceptProposedAction()
        except Exception:
            pass

    def dropEvent(self, ev):
        """把拖入的 PDF / TXT（可多选）在阅读区打开；多个时只开第一个并提示。"""
        paths = []
        try:
            for u in ev.mimeData().urls():
                p = u.toLocalFile()
                if p and os.path.isfile(p):
                    paths.append(os.path.abspath(p))
        except Exception:
            paths = []
        try:
            ev.acceptProposedAction()
        except Exception:
            pass
        if not paths:
            self.statusBar().showMessage('拖入的内容不是文件（支持把 PDF / TXT 等文件拖进来）')
            return
        p = paths[0]
        ext = os.path.splitext(p)[1].lower()
        if ext not in READER_EXTS:
            self.statusBar().showMessage('这个格式暂不支持在阅读区打开：%s' % os.path.basename(p))
            return
        note = ('（另有 %d 个拖入文件已忽略）' % (len(paths) - 1)) if len(paths) > 1 else ''
        self.open_path_in_reader(p, note)
        self._hist_add()

    def open_cli_arg(self):
        """双击关联 / 命令行带文件启动：一律先在阅读区内部打开（不甩给外部程序）。
        多个文件参数时打开第一个，其余在状态栏提示（未入列表）。
        """
        try:
            cand = [a for a in sys.argv[1:] if not a.startswith('-')]
        except Exception:
            cand = []
        files = []
        for a in cand:
            try:
                if os.path.isfile(a):
                    files.append(os.path.abspath(a))
            except Exception:
                continue
        if not files:
            return
        p = files[0]
        tail = ''
        if len(files) > 1:
            tail = '（另有 %d 个文件参数已忽略）' % (len(files) - 1)
        self.open_path_in_reader(p, tail)

    def epub_here(self):
        """用 PDF 引擎直接打开当前项（支持 EPUB；也可以打开 PDF）。Ctrl+E"""
        r = self._cur()
        if not r:
            return
        p = os.path.join(r.get('dir') or '', r.get('name') or '')
        if not os.path.isfile(p):
            self.statusBar().showMessage('文件不在了：%s' % p)
            return
        try:
            import fitz
            d = fitz.open(p)
            if d.page_count <= 0:
                self.statusBar().showMessage('这个文件没有可显示的页面')
                return
            self.pd = d
            self._pd_path = p
            self.pgno = 0
            self._pdf_show()
            self._after_pdf_open()
            self._hist_add()
            self._stat_open(p)
            self.statusBar().showMessage('已用 PDF 引擎打开（%s，共 %d 页）｜连续滚动，PgUp/PgDn 翻页'
                                         % (os.path.splitext(p)[1].lower() or 'file',
                                            d.page_count))
        except Exception as e:
            self.statusBar().showMessage('打不开：%s' % e)

    def hist_here(self):
        """最近打开（Ctrl+H；双击重开）。"""
        from PyQt6.QtWidgets import QListWidget
        st = C.load_settings()
        hs = list(st.get('history') or [])
        dlg = QDialog(self)
        dlg.setWindowTitle('最近打开（%d 条）' % len(hs))
        dlg.resize(640, 460)
        vb = QVBoxLayout(dlg)
        lst = QListWidget()
        for h in hs[:200]:
            lst.addItem('%s   %s' % (h.get('at', ''), h.get('path', '')))
        vb.addWidget(lst)

        def go():
            i = lst.currentRow()
            if 0 <= i < len(hs):
                p = hs[i].get('path', '')
                if os.path.isfile(p):
                    try:
                        self.ed_kw.setText(os.path.splitext(os.path.basename(p))[0])
                        self.do_search()
                        if self.rows:
                            self.tb.setCurrentCell(0, 0)
                            self.on_pick()
                            self.preview_here()
                    except Exception as e:
                        self.statusBar().showMessage('重开失败：%s' % e)
                else:
                    self.statusBar().showMessage('文件不在了：%s' % p)
            dlg.accept()

        lst.itemDoubleClicked.connect(lambda _: go())
        vb.addWidget(QPushButton('好'))
        dlg.exec()

    def _hist_add(self):
        """把当前项追加进阅读历史（不重复，最多 300 条）。"""
        r = self._cur()
        import time
        if not r:
            return
        p = os.path.join(r.get('dir') or '', r.get('name') or '')
        try:
            st = C.load_settings()
            hs = [h for h in (st.get('history') or []) if h.get('path') != p]
            hs.insert(0, {'path': p, 'at': time.strftime('%m-%d %H:%M')})
            st['history'] = hs[:300]
            C.save_settings(st)
        except Exception:
            pass

    # ============================================================ batch5
    # ① PDF 连续纵向滚动（懒加载 + 预渲染 + QPixmap 缓存）＋ O(log n) 二分查页
    def _pdf_stop(self):
        """关掉 PDF 阅读态：清空 PdfView，复位查找/文本缓存。"""
        try:
            self.pdf_view.clear()
        except Exception:
            pass
        self._pd_texts = None
        self._pd_texts_doc = None
        self._hl_kw = ''

    def _zoom_factor(self):
        """当前缩放系数：适应宽度 / 适应页面 / 100% / 自定义。"""
        d = getattr(self, 'pd', None)
        mode = getattr(self, '_zoom_mode', 'fitp')
        if mode == 'custom':
            return max(0.2, min(5.0, float(getattr(self, '_zoom', 1.0))))
        if mode == '100' or d is None:
            return 1.0
        try:                                  # batch10：适应宽度/页面交给 PdfView 按视口算
            if getattr(self.pdf_view, 'doc', None) is not None:
                return float(self.pdf_view.fit_zoom(mode))
        except Exception:
            pass
        try:
            r = d[int(getattr(self, 'pgno', 0))].rect
            pw, ph = max(1.0, float(r.width)), max(1.0, float(r.height))
        except Exception:
            pw, ph = 612.0, 792.0
        try:
            vp = self.pdf_view.viewport().size()
            vw, vh = max(60, vp.width() - 26), max(60, vp.height() - 26)
        except Exception:
            vw, vh = 800, 1000
        if mode == 'fitp':
            return max(0.2, min(5.0, min(vw / pw, vh / ph)))
        return max(0.2, min(5.0, vw / pw))        # fitw

    def _pdf_show(self):
        """把当前文档交给 PdfView 显示（首次装入 / 换文件 / 重建）；跳页请用 pdf_goto。"""
        d = getattr(self, 'pd', None)
        if d is None:
            return
        self.stack.setCurrentWidget(self.pdf_view)
        self._reader = 'pdf'
        self._text_path = ''
        inv = bool(self.cb_invert.isChecked()) if hasattr(self, 'cb_invert') else False
        self.pdf_view.set_document(d, int(getattr(self, 'pgno', 0)),
                                   self._zoom_factor(), invert=inv,
                                   hl=getattr(self, '_hl_kw', ''))
        _m = getattr(self, '_zoom_mode', 'fitp')      # batch10：装完记下适应模式
        self.pdf_view.set_fit(_m if _m in ('fitw', 'fitp') else None)
        self._sync_zoom_ui()
        self._sync_page_box()
        self._upd_status_pdf()
        try:
            self.pdf_view.setFocus()
        except Exception:
            pass

    def _on_pdf_page(self, i):
        """PdfView 滚动/跳页 → 同步页码框、目录高亮、状态栏。"""
        d = getattr(self, 'pd', None)
        if d is None:
            return
        self.pgno = max(0, min(int(d.page_count) - 1, int(i)))
        self._sync_page_box()
        self._sync_toc_highlight()
        self._upd_status_pdf()

    def _on_fit_zoom(self, _z):
        """batch10：适应窗口自动重排后，同步缩放 UI 与状态栏。"""
        try:
            self._sync_zoom_ui()
            self._upd_status_pdf()
        except Exception:
            pass

    def _pdf_zoom_step(self, factor):
        """Ctrl+滚轮 / 右键菜单 → 自定义缩放步进。"""
        if getattr(self, 'pd', None) is None:
            return
        cur = (float(self._zoom) if self._zoom_mode == 'custom' else self._zoom_factor())
        self._zoom = max(0.25, min(4.0, cur * float(factor)))
        self._zoom_mode = 'custom'
        if getattr(self, 'cb_zoom', None) is not None:
            self.cb_zoom.blockSignals(True)
            self.cb_zoom.setCurrentIndex(3)
            self.cb_zoom.blockSignals(False)
        self._pdf_view_active().set_zoom(self._zoom)
        self._sync_zoom_ui()
        self._upd_status_pdf()

    def _on_pdf_selection(self, t):
        if t:
            self.statusBar().showMessage(
                '已选中 %d 字（已复制到剪贴板；Ctrl+C 可再复制）' % len(t))

    def _sync_page_box(self):
        """页码框与滚动实时双向同步：滚动 → 框里数字跟着变（非法输入会被纠正回当前页）。"""
        try:
            self.ed_page.setText(str(int(self.pgno) + 1))
        except Exception:
            pass

    def _sync_toc_highlight(self):
        """目录页签自动高亮当前章节（O(log n)，仅面板可见时做）。"""
        try:
            dk = getattr(self, '_nav_dock', None)
            lt = getattr(self, '_last_toc', None)
            if dk is None or not dk.isVisible() or not lt or self._nav_toc is None:
                return
            pages = lt.get('row_pages')
            if not pages:
                return
            k = bisect_right(pages, int(self.pgno)) - 1
            if k < 0:
                k = 0
            k = max(0, min(int(self._nav_toc.count()) - 1, int(k)))
            if self._nav_toc.currentRow() != k:
                self._nav_toc.setCurrentRow(k)
                it = self._nav_toc.item(k)
                if it is not None:
                    self._nav_toc.scrollToItem(it)
        except Exception:
            pass

    def _upd_status_pdf(self):
        d = getattr(self, 'pd', None)
        if d is None:
            return
        try:
            self.lb_pg_total.setText('/ %d' % int(d.page_count))
        except Exception:
            pass
        self._sync_page_box()
        try:
            if time.time() < float(getattr(self, '_msg_hold_until', 0.0) or 0.0):
                return                      # 显式提示保护期内，不用滚动状态覆盖它
        except Exception:
            pass
        self.statusBar().showMessage(
            '第 %d / %d 页（滚轮/↑↓ 平滑滚动，PgUp/PgDn 翻页；缩放 %d%%）'
            % (int(self.pgno) + 1, int(d.page_count), round(100 * self._zoom_factor())))

    def pdf_goto(self, delta):
        d = getattr(self, 'pd', None)
        if d is None:
            return
        self.pgno = max(0, min(max(1, int(d.page_count)) - 1, int(self.pgno) + int(delta)))
        self._pdf_view_active().goto_page(self.pgno)

    def pdf_home(self):
        """Ctrl+Home：回到首页。"""
        if getattr(self, 'pd', None) is None:
            return
        self.pgno = 0
        self._pdf_view_active().goto_page(0)

    def pdf_end(self):
        """Ctrl+End：跳到末页。"""
        d = getattr(self, 'pd', None)
        if d is None:
            return
        self.pgno = max(0, int(d.page_count) - 1)
        self._pdf_view_active().goto_page(self.pgno)

    def page_jump(self):
        """页码框（N / M）回车跳页。"""
        d = getattr(self, 'pd', None)
        if d is None:
            return
        try:
            n = int(re.sub(r'\D', '', self.ed_page.text()) or (int(self.pgno) + 1))
        except Exception:
            n = int(self.pgno) + 1
        self.pgno = max(0, min(int(d.page_count) - 1, n - 1))
        self._pdf_view_active().goto_page(self.pgno)
        self._upd_status_pdf()

    def _zoom_changed(self, i):
        """缩放三档 + 自定义（适应宽度 / 适应页面 / 100% / 自定义百分比）。"""
        i = max(0, min(3, int(i)))
        self._zoom_mode = ['fitw', 'fitp', '100', 'custom'][i]
        if i == 3:
            try:
                self._zoom = max(0.5, min(4.0, float(self.sp_zoom.value()) / 100.0))
            except Exception:
                self._zoom = 1.0
        if getattr(self, 'pd', None) is not None:
            if self._zoom_mode in ('fitw', 'fitp'):
                self._pdf_view_active().set_fit(self._zoom_mode)
            else:
                self._pdf_view_active().set_fit(None)
                self._pdf_view_active().set_zoom(self._zoom_factor())
            self.statusBar().showMessage('缩放：%d%%（%s）'
                                         % (round(100 * self._zoom_factor()),
                                            self._zoom_label()))
        self._sync_zoom_ui()

    def _zoom_pct_changed(self, v):
        """百分比框（50–400）回车/失焦 → 切到自定义缩放并重建。"""
        try:
            self._zoom = max(0.5, min(4.0, float(v) / 100.0))
        except Exception:
            return
        self._zoom_mode = 'custom'
        if getattr(self, 'pd', None) is not None:
            self._pdf_view_active().set_fit(None)
            self._pdf_view_active().set_zoom(self._zoom)
            self.statusBar().showMessage('缩放：%d%%（自定义）' % int(round(100 * self._zoom)))
        self._sync_zoom_ui()

    def _zoom_label(self):
        return {'fitw': '适应宽度', 'fitp': '适应页面', '100': '100%'}.get(
            getattr(self, '_zoom_mode', 'fitp'), '自定义')

    def _sync_zoom_ui(self):
        """把当前有效缩放回填到下拉框 / 百分比框（阻断信号，避免递归）。"""
        try:
            pct = int(round(100 * self._zoom_factor()))
            self.sp_zoom.blockSignals(True)
            self.sp_zoom.setValue(max(50, min(400, pct)))
            self.sp_zoom.blockSignals(False)
        except Exception:
            pass
        try:
            idx = {'fitw': 0, 'fitp': 1, '100': 2, 'custom': 3}.get(
                getattr(self, '_zoom_mode', 'fitp'), 1)
            self.cb_zoom.blockSignals(True)
            self.cb_zoom.setCurrentIndex(idx)
            self.cb_zoom.blockSignals(False)
        except Exception:
            pass

    def _say(self, msg, hold=0.0):
        """状态栏提示；hold>0 时在保护期内不被滚动状态覆盖。"""
        try:
            self.statusBar().showMessage(msg)
            if hold:
                self._msg_hold_until = time.time() + float(hold)
        except Exception:
            pass

    def eventFilter(self, obj, ev):
        # PDF 的 Ctrl+滚轮缩放已由 PdfView 自己处理（zoomRequested 信号）
        return super().eventFilter(obj, ev)

    def _on_invert(self, *_):
        """勾选/取消 ◐ PDF 反色 时清缓存并立即重画。"""
        if getattr(self, 'pd', None) is not None:
            self._pdf_view_active().set_invert(bool(self.cb_invert.isChecked()))

    def apply_theme(self):
        """主题（浅色/深色/护眼）+ 正文字号 + 行距；F11 全屏。"""
        i = self.cb_theme.currentIndex() if hasattr(self, 'cb_theme') else 0
        bg, fg = [('#ffffff', '#222222'), ('#1e1e1e', '#d8d8d8'),
                  ('#f4ecd8', '#3a3226')][max(0, min(2, i))]
        try:
            self.view.setStyleSheet('QTextEdit{background:%s;color:%s;}' % (bg, fg))
            try:
                self.pdf_view.setStyleSheet('QScrollArea{background:%s;}' % bg)
                self.pdf_view.viewport().setStyleSheet('background:%s;' % bg)
            except Exception:
                pass
            sz = self.sp_font.value() if hasattr(self, 'sp_font') else 13
            self.view.setFont(QFont('Microsoft YaHei', sz))
            lh = self.sp_line.value() if hasattr(self, 'sp_line') else 150
            self._apply_line_height(lh)
            self.statusBar().showMessage('主题：%s（字号 %d，行距 %d%%，F11 全屏）'
                                         % (self.cb_theme.currentText(), sz, lh))
        except Exception:
            pass

    def _apply_line_height(self, lh=None):
        """把行距（百分比）作用到阅读区：整篇按比例块格式。"""
        try:
            if lh is None:
                lh = self.sp_line.value() if hasattr(self, 'sp_line') else 150
            from PyQt6.QtGui import QTextBlockFormat, QTextCursor
            vs = self.view.verticalScrollBar().value()
            cur = self.view.textCursor()
            cur.select(QTextCursor.SelectionType.Document)
            bf = QTextBlockFormat()
            bf.setLineHeight(float(lh), 1)      # 1 = ProportionalHeight（比例）
            cur.mergeBlockFormat(bf)
            cur.setPosition(0)                  # 收掉选区，避免高亮
            self.view.setTextCursor(cur)
            self.view.verticalScrollBar().setValue(vs)
        except Exception:
            pass

    def toggle_full(self):
        """F11：全屏时自动隐藏工具栏/按钮行（退出时恢复）。"""
        try:
            if self.isFullScreen():
                self.showNormal()
                for w, vis in getattr(self, '_full_prev', []):
                    try:
                        w.setVisible(vis)
                    except Exception:
                        pass
                self.statusBar().showMessage('已退出全屏')
            else:
                widgets = list(getattr(self, '_top_widgets', [])) + \
                    list(getattr(self, '_btn_widgets', []))
                self._full_prev = [(w, w.isVisible()) for w in widgets]
                for w in widgets:
                    w.setVisible(False)
                self.showFullScreen()
                self.statusBar().showMessage('按 F11 退出全屏')
        except Exception as e:
            self.statusBar().showMessage('全屏切换失败：%s' % e)

    # ---- batch7：阅读器独立窗口
    def _detach_reader(self):
        if getattr(self, '_reader_win', None) is not None:
            return
        try:
            self._split_sizes = self._split.sizes()
        except Exception:
            self._split_sizes = [340, 1160]
        win = ReaderWindow(self)
        self.reader_panel.setParent(win)
        win.setCentralWidget(self.reader_panel)
        dk = getattr(self, '_nav_dock', None)
        if dk is not None:
            try:
                self.removeDockWidget(dk)
                dk.setParent(win)
                win.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dk)
                dk.show()
            except Exception:
                pass
        self._reader_win = win
        win.resize(1200, 900)
        win.showMaximized()
        self._bind_reader_shortcuts(win)      # batch18：独立窗口也要能用 Ctrl+F 查找
        self.statusBar().showMessage('阅读器已独立成窗口（可最大化 · F11 全屏）')

    def _bind_reader_shortcuts(self, win):
        """batch18：给独立阅读窗口挂上窗口级快捷键（Ctrl+F/Esc/F11）——
        主窗口上的 QShortcut 在焦点落到独立窗口时不会触发。"""
        try:
            scs = []

            def _mk(seq, slot):
                sc = QShortcut(QKeySequence(seq), win)
                try:
                    sc.setContext(Qt.ShortcutContext.WindowShortcut)
                except Exception:
                    pass
                sc.activated.connect(slot)
                scs.append(sc)

            _mk('Ctrl+F', self.find_focus)
            _mk('Esc', self.find_close)
            _mk('F11', lambda: self._reader_full(win))
            try:
                win._cv_sc = scs          # 持引用，避免被 GC
            except Exception:
                pass
        except Exception:
            pass

    def _reader_full(self, win):
        """独立阅读窗口的 F11 全屏切换。"""
        try:
            if win.isFullScreen():
                win.showMaximized()
            else:
                win.showFullScreen()
        except Exception:
            pass

    def _attach_reader(self, from_close=False):
        win = getattr(self, '_reader_win', None)
        if win is None:
            return
        self._reader_win = None
        if getattr(self, '_closing', False):      # batch18：主窗口正在关闭 → 只清掉独立窗口
            try:
                win.hide()
                win.deleteLater()
            except Exception:
                pass
            return
        dk = getattr(self, '_nav_dock', None)
        if dk is not None:
            try:
                win.removeDockWidget(dk)
                dk.setParent(self)
                self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dk)
                dk.hide()
            except Exception:
                pass
        try:
            self.reader_panel.setParent(None)
            self._split.addWidget(self.reader_panel)
            self._split.setSizes(getattr(self, '_split_sizes', None) or [340, 1160])
        except Exception:
            pass
        try:
            win.hide()
            win.deleteLater()
        except Exception:
            pass
        self.statusBar().showMessage('阅读器已收回主窗口（🗗 可再独立）')

    def toggle_reader_window(self):
        if getattr(self, '_reader_win', None) is not None:
            self._attach_reader()
        else:
            self._detach_reader()

    def start_two_window_mode(self):
        """默认双窗口：主窗口放文件列表（靠左），阅读器独立成窗口（尽量大，靠右）。"""
        try:
            if getattr(self, '_reader_win', None) is not None:
                return
            self._detach_reader()
            win = getattr(self, '_reader_win', None)
            scr = QApplication.primaryScreen()
            g = scr.availableGeometry() if scr is not None else None
            if win is None or g is None or g.width() <= 0:
                return
            win.showNormal()
            st = C.load_settings()
            rg = st.get('reader_geom')
            if isinstance(rg, (list, tuple)) and len(rg) == 4 and int(rg[2]) > 400:
                win.setGeometry(int(rg[0]), int(rg[1]), int(rg[2]), int(rg[3]))
            else:
                w = max(640, int(g.width() * 0.62))
                h = max(480, int(g.height() * 0.88))
                top = g.top() + int(g.height() * 0.06)
                win.setGeometry(g.right() - w + 1, top, w, h)
                self.resize(min(560, max(400, int(g.width() * 0.25))), h)
                self.move(g.left() + 8, top)                        # 靠左
            self.statusBar().showMessage('双窗口：左侧文件列表 ｜ 右侧阅读器（可最大化 · 🗗 收回）')
        except Exception as e:
            try:
                self.statusBar().showMessage('双窗口模式失败：%s' % e)
            except Exception:
                pass

    # ---- batch7：跨文件全文检索（独立进程）
    _FTS_EXTS = ('.pdf', '.txt', '.md', '.json', '.csv')

    def _expand_family(self, files):
        """batch9：把每本书的 PDF 与对应 TXT（含不同 OCR 引擎 / 繁简变体 / _opt）都纳入检索范围。"""
        out, seen = [], set()

        def add(p):
            k = os.path.normcase(os.path.abspath(p))
            if p and k not in seen and os.path.isfile(p):
                seen.add(k)
                out.append(p)

        for p in files:
            add(p)
            try:
                d = os.path.dirname(os.path.abspath(p))
                key = META.family_key(os.path.basename(p))
                if not key:
                    continue
                for fn in os.listdir(d):
                    if os.path.splitext(fn)[1].lower() in self._FTS_EXTS \
                            and META.family_key(fn) == key:
                        add(os.path.join(d, fn))
            except OSError:
                pass
        return out

    def fulltext_search(self):
        if getattr(self, '_fts_proc', None) is not None:
            self.statusBar().showMessage('全文检索进行中…（完成后自动弹出结果）')
            return
        rows = getattr(self, 'rows', []) or []
        files = []
        seen = set()
        for r in rows:
            p = os.path.join(r.get('dir') or '', r.get('name') or '')
            if p and p not in seen and os.path.isfile(p):
                seen.add(p)
                files.append(p)
        files = self._expand_family(files)      # batch9：把对应的 TXT 也纳入检索范围
        if not files:
            self.statusBar().showMessage('当前搜索结果为空：先搜出一些文件再全文检索')
            return
        from PyQt6.QtWidgets import QInputDialog
        kw, ok = QInputDialog.getText(
            self, '跨文件全文检索',
            '关键词（在 %d 个文件里全文查找，PDF 取文字层）：' % len(files))
        if not ok or not kw.strip():
            return
        kw = kw.strip()
        import tempfile
        jobdir = tempfile.mkdtemp(prefix='cvfts_')
        job = os.path.join(jobdir, 'job.json')
        out = os.path.join(jobdir, 'out.json')
        try:
            with open(job, 'w', encoding='utf-8') as f:
                json.dump({'kw': kw, 'files': files, 'out': out}, f, ensure_ascii=False)
        except Exception as e:
            self.statusBar().showMessage('无法创建检索任务：%s' % e)
            return
        if getattr(sys, 'frozen', False):
            prog, args = sys.executable, ['--fts-worker', job]
        else:
            prog = sys.executable
            args = [os.path.abspath(__file__), '--fts-worker', job]
        proc = QProcess(self)
        proc.setProgram(prog)
        proc.setArguments(args)
        proc.readyReadStandardOutput.connect(lambda: self._fts_progress(proc))
        proc.finished.connect(lambda code, st: self._fts_done(code, out, jobdir, kw))
        self._fts_proc = proc
        self._fts_total = len(files)
        self._fts_kw = kw
        try:
            proc.start()
        except Exception as e:
            self._fts_proc = None
            self.statusBar().showMessage('启动检索进程失败：%s' % e)
            return
        self.statusBar().showMessage(
            '已在独立进程开始全文检索：%d 个文件，关键词「%s」…' % (len(files), kw))

    def _fts_progress(self, proc):
        try:
            data = bytes(proc.readAllStandardOutput()).decode('utf-8', 'replace')
        except Exception:
            return
        for line in data.splitlines():
            if line.startswith('PROGRESS\t'):
                parts = line.split('\t')
                if len(parts) >= 4:
                    self.statusBar().showMessage(
                        '全文检索中… %s / %s 个文件，已命中 %s 处（关键词 %s）'
                        % (parts[1], parts[2], parts[3], getattr(self, '_fts_kw', '')))

    def _fts_done(self, code, out, jobdir, kw):
        self._fts_proc = None
        try:
            with open(out, 'r', encoding='utf-8') as f:
                res = json.load(f)
        except Exception:
            self.statusBar().showMessage('全文检索失败（进程返回 %s）' % code)
            return
        files = res.get('files') or []
        if not files and res.get('hits'):                 # 兼容旧输出
            agg = {}
            for h in res['hits']:
                p = h.get('path')
                a = agg.setdefault(p, {'path': p,
                                       'name': os.path.basename(p or ''),
                                       'count': 0, 'hits': []})
                a['count'] += 1
                a['hits'].append({'page': h.get('page'), 'ctx': h.get('ctx')})
            files = list(agg.values())
        kept, hidden = META.dedup_split(files)             # batch9 去重（被去重项默认隐藏）
        total = sum(int(f.get('count') or 0) for f in kept)
        self.statusBar().showMessage(
            '全文检索完成：扫描 %s 个文件，命中 %d 处（去重后 %d 个文件%s）'
            % (res.get('scanned'), total, len(kept),
               ('，另有 %d 个被去重隐藏' % len(hidden)) if hidden else ''))
        # batch11：跨文件检索历史自动保存（随时可在「🕘 检索历史」调阅）
        try:
            stt = C.load_settings()
            rec = {'kw': kw, 'at': time.strftime('%Y-%m-%d %H:%M'),
                   'scanned': res.get('scanned'), 'files': len(kept),
                   'hidden': len(hidden), 'total': total,
                   'kept': kept, 'kept_hidden': hidden,
                   'errors': res.get('errors') or []}
            stt['fts_hist'] = TOOLS.fts_hist_add(stt.get('fts_hist') or [], rec)
            C.save_settings(stt)
        except Exception:
            pass
        self._show_fts_dialog(kw, kept, hidden, res.get('errors') or [])

    def _show_fts_dialog(self, kw, files, hidden, errors):
        def _rows(fs, mark_hidden=False):
            out = []
            for f in fs:
                mark = '（TXT）' if f.get('txt_mark') else ''
                if mark_hidden:
                    mark += '（已去重）'
                for h in f.get('hits') or []:
                    out.append((f.get('path'), h.get('page'),
                                '%s%s' % (f.get('name') or '', mark), h.get('ctx') or ''))
            return out

        kept_rows = _rows(files)
        hid_rows = _rows(hidden, mark_hidden=True)
        dlg = QDialog(self)
        dlg.setWindowTitle('跨文件全文检索「%s」— %d 个文件 / %d 处'
                           % (kw, len(files), len(kept_rows)))
        dlg.resize(900, 620)
        vb = QVBoxLayout(dlg)
        lst = QListWidget()
        info = QLabel()
        info.setWordWrap(True)
        shown = {'hidden': False}

        def _fill():
            lst.clear()
            rows = kept_rows + (hid_rows if shown['hidden'] else [])
            for path, pg, name, ctx in rows:
                tag = ('第 %d 页' % (int(pg) + 1)) if pg is not None else '—'
                it = QListWidgetItem('%s ｜ %s ｜ %s' % (name, tag, ctx))
                it.setData(Qt.ItemDataRole.UserRole, (path, pg))
                lst.addItem(it)
            info.setText('双击一条结果 → 在阅读区打开并跳到该页。共 %d 个文件 / %d 处。%s'
                         % (len(files), len(kept_rows),
                            ('已展开 %d 个被去重项。' % len(hid_rows)) if shown['hidden']
                            else ('' if not hid_rows else '另有 %d 个被去重项，默认隐藏。'
                                  % len(hid_rows))))

        _fill()
        vb.addWidget(info)
        vb.addWidget(lst, 1)
        if errors:
            lb = QLabel('有 %d 个文件读取失败：%s' % (len(errors), '；'.join(errors[:3])))
            lb.setWordWrap(True)
            vb.addWidget(lb)
        bb = QHBoxLayout()
        b1 = QPushButton('全部复制')
        b3 = QPushButton('▸ 显示被去重的 %d 项' % len(hid_rows))
        b3.setVisible(bool(hid_rows))
        b2 = QPushButton('关闭')
        bb.addWidget(b1)
        bb.addWidget(b3)
        bb.addStretch(1)
        bb.addWidget(b2)
        vb.addLayout(bb)

        def _toggle_hidden():
            shown['hidden'] = not shown['hidden']
            b3.setText(('▾ 收起被去重的 %d 项' if shown['hidden']
                        else '▸ 显示被去重的 %d 项') % len(hid_rows))
            _fill()

        def _copy_all():
            lines = []
            for path, pg, name, ctx in (kept_rows + (hid_rows if shown['hidden'] else [])):
                lines.append('%s%s\n%s' % (
                    name, ('（第 %d 页）' % (int(pg) + 1)) if pg is not None else '', ctx))
            QApplication.clipboard().setText('\n\n'.join(lines))
            self.statusBar().showMessage('已复制全部检索结果')

        def _open(it):
            d = it.data(Qt.ItemDataRole.UserRole)
            if d:
                self._open_fts_hit(d[0], d[1])

        b1.clicked.connect(_copy_all)
        b3.clicked.connect(_toggle_hidden)
        b2.clicked.connect(dlg.accept)
        lst.itemDoubleClicked.connect(_open)
        dlg.exec()

    def _open_fts_hit(self, path, page):
        for i, r in enumerate(getattr(self, 'rows', []) or []):
            p = os.path.join(r.get('dir') or '', r.get('name') or '')
            if os.path.normcase(p) == os.path.normcase(path or ''):
                self.tb.setCurrentCell(i, 0)
                self.on_pick()
                break
        self.preview_here()
        if page is not None and getattr(self, 'pd', None) is not None:
            try:
                self.pgno = max(0, min(int(self.pd.page_count) - 1, int(page)))
                self.pdf_view.goto_page(self.pgno)
            except Exception:
                pass

    # ---- batch11：跨文件全文检索历史（自动保存，Ctrl+Shift+F）
    def fts_history_dialog(self):
        """调阅历次跨文件全文检索结果：双击重开该次结果，可删除/清空。"""
        try:
            st = C.load_settings()
            hist = list(st.get('fts_hist') or [])
        except Exception:
            hist = []
        self._last_fts_hist = hist
        dlg = QDialog(self)
        dlg.setWindowTitle('跨文件检索历史')
        dlg.resize(720, 520)
        vb = QVBoxLayout(dlg)
        vb.addWidget(QLabel('历次全文检索（最近 %d 次，双击重开该次结果）：' % len(hist)))
        lst = QListWidget()
        for h in hist:
            lst.addItem('%s ｜ 「%s」 ｜ %s 个文件 / %s 处%s'
                        % (h.get('at') or '', h.get('kw') or '',
                           h.get('files') or 0, h.get('total') or 0,
                           ('，另有 %s 个被去重' % h.get('hidden')) if h.get('hidden') else ''))
        vb.addWidget(lst, 1)

        def _open():
            i = lst.currentRow()
            if 0 <= i < len(hist):
                h = hist[i]
                dlg.accept()
                self._show_fts_dialog(h.get('kw') or '', h.get('kept') or [],
                                     h.get('kept_hidden') or [], h.get('errors') or [])

        def _del():
            i = lst.currentRow()
            if not (0 <= i < len(hist)):
                self.statusBar().showMessage('先选中一条历史')
                return
            try:
                stt = C.load_settings()
                hh = list(stt.get('fts_hist') or [])
                del hh[i]
                stt['fts_hist'] = hh
                C.save_settings(stt)
            except Exception as e:
                self.statusBar().showMessage('删除失败：%s' % e)
                return
            lst.takeItem(i)
            hist.pop(i)
            self.statusBar().showMessage('已删除该条检索历史')

        def _clear():
            try:
                stt = C.load_settings()
                stt['fts_hist'] = []
                C.save_settings(stt)
            except Exception:
                pass
            hist[:] = []
            lst.clear()
            self.statusBar().showMessage('已清空检索历史')

        lst.itemDoubleClicked.connect(lambda _: _open())
        row = QHBoxLayout()
        bd = QPushButton('删除选中')
        bd.clicked.connect(_del)
        bc = QPushButton('清空')
        bc.clicked.connect(_clear)
        bf = QPushButton('关闭')
        bf.clicked.connect(dlg.accept)
        row.addWidget(bd)
        row.addWidget(bc)
        row.addStretch(1)
        row.addWidget(bf)
        vb.addLayout(row)
        dlg.exec()

    def on_ver(self, i):
        """版本下拉切换 → 真正打开该版本（PDF 原本 / 繁转简 TXT / 其它）。batch10 修正：以前只显示路径文字。"""
        if not (0 <= i < len(self.vers)):
            return
        p = self.vers[i].get('path') or ''
        if not p or not os.path.isfile(p):
            self.statusBar().showMessage('这个版本的文件不在了：%s' % p)
            return
        self._stat_flush()
        self._suppress_dual = True          # 切版本不强制对读，保持当前阅读方式
        try:
            opened = self._open_path(p)
        finally:
            self._suppress_dual = False
        if opened:
            try:
                self.cb_ver.blockSignals(True)
                self.cb_ver.setCurrentIndex(i)
                self.cb_ver.blockSignals(False)
            except Exception:
                pass
            self.statusBar().showMessage('已切到：%s' % os.path.basename(p))

    def copy_cite(self):
        m = getattr(self, 'meta', None)
        if not m:
            return
        s = META.cite(m, page='X')
        try:                                     # 引文里含纪年就自动换算
            s, _hits = CHRONO.annotate(s)
        except Exception:
            pass
        QApplication.clipboard().setText(s)
        self.statusBar().showMessage('已复制引用：%s' % s)

    def colophon_here(self):
        """跳到当前这本书的版权页（PDF；当前项是 txt 时自动找同书 PDF）。找不到就提示。"""
        r = self._cur()
        if not r:
            self.statusBar().showMessage('先在列表里选一本书')
            return
        p = os.path.join(r.get('dir') or '', r.get('name') or '')
        try:
            pdf = p if p.lower().endswith('.pdf') else ''
            if not pdf:
                cands = META._sibling_pdfs(p) if hasattr(META, '_sibling_pdfs') else []
                pdf = cands[0] if cands else ''
            if not pdf or not os.path.isfile(pdf):
                self.statusBar().showMessage('没找到版权页')
                return
            import fitz
            d = fitz.open(pdf)
            if d.page_count <= 0:
                self.statusBar().showMessage('没找到版权页')
                return
            # batch11：先查 PDF 目录（标签页/书签）里有没有「版权页 / 版权」
            try:
                toc = d.get_toc() or []
            except Exception:
                toc = []
            page = TOOLS.find_colophon_in_toc(toc)
            src = '目录' if page else ''
            if not page:
                page = META.find_colophon_page(pdf)        # 1 起；0 = 没找到
                src = '文字层' if page else ''
            if not page:
                try:
                    d.close()
                except Exception:
                    pass
                self.statusBar().showMessage('没找到版权页')
                return
            self.pd = d
            self._pd_path = pdf
            self.pgno = max(0, min(d.page_count - 1, page - 1))
            self._pdf_show()
            self._hist_add()
            self._stat_open(pdf)
            self._say('版权页在第 %d / %d 页（来源：%s）'
                      % (self.pgno + 1, d.page_count, src or '文字层'), hold=2.0)
        except Exception as e:
            self.statusBar().showMessage('没找到版权页：%s' % e)

    def copy_text(self):
        """⧉ 复制文本：把阅读区当前纯文本复制到剪贴板（自动附纪年换算）。"""
        def _ann(x):
            try:
                y, hits = CHRONO.annotate_append(x)
                return y, len(hits)
            except Exception:
                return x, 0
        try:
            if getattr(self, '_reader', '') == 'pdf' and getattr(self, 'pd', None) is not None:
                try:
                    _sel = self.pdf_view.selected_text()
                except Exception:
                    _sel = ''
                if _sel:
                    _sel, _n = _ann(_sel)
                    QApplication.clipboard().setText(_sel)
                    self.statusBar().showMessage('已复制选中文本（%d 字%s）'
                                                 % (len(_sel), ('，含纪年换算 %d 处' % _n) if _n else ''))
                    return
                t = ''
                try:
                    t = (self.pd[self.pgno].get_text() or '').strip()
                except Exception:
                    t = ''
                if not t:
                    self.statusBar().showMessage('这页没有文字层')
                    return
                t, _n = _ann(t)
                QApplication.clipboard().setText(t)
                self.statusBar().showMessage('已复制本页文本（%d 字%s）'
                                             % (len(t), ('，含纪年换算 %d 处' % _n) if _n else ''))
                return
            t = self.view.toPlainText()
            if not t.strip():
                self.statusBar().showMessage('阅读区没有可复制的文本')
                return
            t, _n = _ann(t)
            QApplication.clipboard().setText(t)
            self.statusBar().showMessage('已复制阅读区文本（%d 字%s）'
                                         % (len(t), ('，含纪年换算 %d 处' % _n) if _n else ''))
        except Exception as e:
            self.statusBar().showMessage('复制失败：%s' % e)

    def copy_html(self):
        """⧉ 复制带格式：保留 HTML 格式复制（PDF 用文字层拼段落）。"""
        try:
            from PyQt6.QtCore import QMimeData
            html = self.view.toHtml() or ''
            text = self.view.toPlainText() or ''
            if getattr(self, '_reader', '') == 'pdf' and getattr(self, 'pd', None) is not None:
                try:
                    t = (self.pd[self.pgno].get_text() or '').strip()
                except Exception:
                    t = ''
                if not t:
                    self.statusBar().showMessage('这页没有文字层')
                    return
                import html as _h
                text = t
                html = ('<p>' + '</p><p>'.join(
                    _h.escape(x) for x in t.splitlines() if x.strip()) + '</p>')
            if not text.strip():
                self.statusBar().showMessage('阅读区没有可复制的文本')
                return
            try:                                     # 复制带格式 → 文本部分附纪年换算
                t2, hits = CHRONO.annotate_append(text)
                if hits:
                    import html as _h2
                    extra = t2[len(text):].strip()
                    html = (html or '') + '<p>' + _h2.escape(extra) + '</p>'
                    text = t2
            except Exception:
                pass
            md = QMimeData()
            md.setHtml(html)
            md.setText(text)
            QApplication.clipboard().setMimeData(md)
            self.statusBar().showMessage('已复制带格式文本')
        except Exception as e:
            self.statusBar().showMessage('复制失败：%s' % e)

    # ============================================================ batch11
    # ① 截图本（📷）／② 摘录本（✂）／③ PDF+TXT 对读（⇄）
    def _record_meta(self):
        """当前阅读对象的著录（书名/卷/作者/出版社/年），供截图/摘录出处用。"""
        path = getattr(self, '_pd_path', '') or getattr(self, '_text_path', '') or self._path()
        m = getattr(self, 'meta', None)
        if not m or not isinstance(m, dict):
            try:
                m = META.parse(os.path.basename(path or ''), path or '', deep=False)
            except Exception:
                m = {}
        return m or {}

    def _pdf_view_active(self):
        """当前有效的 PDF 视图：对读时用对读里的 PDF，否则用主阅读器的。"""
        if getattr(self, '_reader', '') == 'dual' and getattr(self, 'dual', None) is not None:
            return self.dual.pdf
        return self.pdf_view

    def _txt_widget(self):
        """当前有效的文本框：对读时用对读里的 TXT，否则用主文本框。"""
        if getattr(self, '_reader', '') == 'dual' and getattr(self, 'dual', None) is not None:
            return self.dual.txt
        return self.view

    # ---- ① 截图本
    def snapshot_here(self):
        """📷 截图：把当前 PDF 页存入「文档\\Cathay文档记录\\截图本」，提示输入页码。"""
        rd = getattr(self, '_reader', '')
        if rd == 'dual':
            self._snapshot_from_pdf(self.dual.current_page())
            return
        if rd == 'pdf' and getattr(self, 'pd', None) is not None:
            self._snapshot_from_pdf(int(self.pgno))
            return
        r = self._cur()
        p = os.path.join(r.get('dir') or '', r.get('name') or '') if r else ''
        if p.lower().endswith('.pdf') and os.path.isfile(p):
            self.preview_here()
            if getattr(self, 'pd', None) is not None:
                self._snapshot_from_pdf(int(self.pgno))
                return
        self.statusBar().showMessage('截图需要先在阅读区打开一个 PDF（右键菜单里还有「框选截图」）')

    def _snapshot_from_pdf(self, page):
        """截当前页 → 提示页码 → 存入截图本。"""
        try:
            v = self._pdf_view_active()
            pm = v.grab_page_pixmap(int(page))
            if pm is None or pm.isNull():
                self.statusBar().showMessage('这一页还没渲染好，稍等一下再截')
                return
            from PyQt6.QtWidgets import QInputDialog
            num, ok = QInputDialog.getInt(
                self, '截图页码', '这张图对应书里的第几页？（可修改）',
                int(page) + 1, 0, 100000, 1)
            if not ok:
                return
            self._save_snapshot(pm, num)
        except Exception as e:
            self.statusBar().showMessage('截图失败：%s' % e)

    def _on_pdf_region(self, page, rect):
        """右键「框选截图」拖出的矩形 → 裁剪 → 提示页码 → 存入截图本。"""
        try:
            v = self._pdf_view_active()
            pm = v.grab_page_pixmap(int(page))
            if pm is None or pm.isNull():
                self.statusBar().showMessage('框选失败：页面未渲染')
                return
            r = QRect(rect).intersected(QRect(0, 0, pm.width(), pm.height()))
            if r.width() < 8 or r.height() < 8:
                return
            crop = pm.copy(r)
            from PyQt6.QtWidgets import QInputDialog
            num, ok = QInputDialog.getInt(
                self, '截图页码', '选中区域对应书里的第几页？',
                int(page) + 1, 0, 100000, 1)
            if not ok:
                return
            self._save_snapshot(crop, num)
        except Exception as e:
            self.statusBar().showMessage('框选截图失败：%s' % e)

    def _save_snapshot(self, pm, page):
        try:
            from PyQt6.QtCore import QBuffer, QIODevice, QByteArray
            ba = QByteArray()
            buf = QBuffer(ba)
            buf.open(QIODevice.OpenModeFlag.WriteOnly)
            pm.save(buf, 'PNG')
            buf.close()
            meta = self._record_meta()
            src = getattr(self, '_pd_path', '') or self._path()
            r = TOOLS.add_snapshot(bytes(ba), meta, page, src)
            if not r or r.get('error'):
                self.statusBar().showMessage('截图保存失败：%s' % ((r or {}).get('error') or '未知'))
                return False
            self._say('已存入截图本：%s' % (r.get('name') or ''), hold=3.0)
            return True
        except Exception as e:
            self.statusBar().showMessage('截图保存失败：%s' % e)
            return False

    # ---- ② 摘录本
    def _current_selection(self):
        """当前阅读区选中的文字（PDF 文字层 / 文本 / 对读），无则空串。"""
        sel = ''
        if getattr(self, '_reader', '') in ('pdf', 'dual'):
            try:
                sel = self._pdf_view_active().selected_text()
            except Exception:
                sel = ''
        if not (sel or '').strip():
            try:
                sel = self._txt_widget().textCursor().selectedText().replace('\u2029', '\n')
            except Exception:
                sel = ''
        return sel or ''

    def excerpt_here(self):
        """✂ 摘录：把选中文字存入摘录本（自动附出处 + 纪年换算）。"""
        sel = self._current_selection()
        if not (sel or '').strip():
            self.statusBar().showMessage('先在正文里选中一段文字再摘录（Ctrl+Shift+E）')
            return
        self._excerpt_from_text(sel)

    def _excerpt_from_pdf(self, sel):
        if not (sel or '').strip():
            self.statusBar().showMessage('先选中一段文字再摘录')
            return
        self._excerpt_from_text(sel)

    def _excerpt_from_text(self, text):
        meta = self._record_meta()
        rd = getattr(self, '_reader', '')
        if rd in ('pdf', 'dual') and getattr(self, 'pd', None) is not None:
            page = int(self.pgno) + 1
            src = getattr(self, '_pd_path', '') or self._path()
        else:
            page = ''
            src = getattr(self, '_text_path', '') or self._path()
        try:                                     # 摘录也是「引文」：自动做纪年换算
            text, _hits = CHRONO.annotate(text)
            _n = len(_hits)
        except Exception:
            _n = 0
        r = TOOLS.add_excerpt(meta, text, page, src)
        if not r or r.get('error'):
            self.statusBar().showMessage('摘录失败：%s' % ((r or {}).get('error') or '未知'))
            return
        self._say('已摘录 %d 字 → 摘录本%s'
                  % (r.get('chars') or 0,
                     ('（含纪年换算 %d 处）' % _n) if _n else ''), hold=2.5)

    # ---- ④ 历史纪年换算（⌛ / Ctrl+Shift+Y）
    def chrono_dialog(self):
        """随时可开的「历史纪年换算」工具：民国/年号/干支 ⇄ 公元年。"""
        dlg = QDialog(self)
        dlg.setWindowTitle('历史纪年换算')
        dlg.resize(780, 640)
        vb = QVBoxLayout(dlg)
        vb.addWidget(QLabel('把带纪年的文字（民国 / 年号 / 干支）粘到下面，点「换算」：'
                            '每个纪年后会加【=公元年】；民国 1～38 年也会换算；'
                            '越界纪年（如康熙63年）会算出公元年并提示该年实际纪年；'
                            '干支会列出 1700–2000 年全部对应年份。'))
        ed_in = QTextEdit()
        vb.addWidget(ed_in, 1)
        row = QHBoxLayout()
        b_conv = QPushButton('换算')
        b_copy = QPushButton('复制结果')
        b_ins = QPushButton('取当前选区')
        b_look = QPushButton('反查公元年')
        b_close = QPushButton('关闭')
        row.addWidget(b_conv)
        row.addWidget(b_copy)
        row.addWidget(b_ins)
        row.addWidget(b_look)
        row.addStretch(1)
        row.addWidget(b_close)
        vb.addLayout(row)
        vb.addWidget(QLabel('结果：'))
        ed_out = QTextEdit()
        ed_out.setReadOnly(True)
        vb.addWidget(ed_out, 1)
        pre = self._current_selection()
        if not (pre or '').strip():
            try:
                pre = QApplication.clipboard().text() or ''
            except Exception:
                pre = ''
        ed_in.setPlainText(pre or '')

        def do_conv():
            ann, hits = CHRONO.annotate(ed_in.toPlainText(), allow_short_republic=True)
            ed_out.setPlainText(ann)
            self.statusBar().showMessage('纪年换算：命中 %d 处' % len(hits))

        def do_copy():
            QApplication.clipboard().setText(ed_out.toPlainText())
            self.statusBar().showMessage('已复制换算结果')

        def do_ins():
            s = self._current_selection()
            if (s or '').strip():
                ed_in.setPlainText(s)
                do_conv()
            else:
                self.statusBar().showMessage('阅读区没有选中文字')

        def do_look():
            from PyQt6.QtWidgets import QInputDialog
            y, okk = QInputDialog.getInt(self, '反查公元年', '输入公元年（1000–2100）：',
                                         1898, 1000, 2100, 1)
            if not okk:
                return
            eras = CHRONO.format_eras(y)          # 每个年号都注明「是第几年」
            gz_note = ''
            try:
                gz_note = CHRONO.year_to_ganzhi(y)
            except Exception:
                pass
            lines = ['公元 %d 年：' % y,
                     '干支：%s' % gz_note,
                     '在用的年号：%s' % (eras or '—'),
                     ('民国纪年：民国 %s年' % CHRONO.era_year_cn(y - 1911))
                     if y >= 1912 else '（无民国纪年）']
            ed_out.setPlainText('\n'.join(lines))

        b_conv.clicked.connect(do_conv)
        b_copy.clicked.connect(do_copy)
        b_ins.clicked.connect(do_ins)
        b_look.clicked.connect(do_look)
        b_close.clicked.connect(dlg.accept)
        self._last_chrono = {'in': ed_in, 'out': ed_out, 'dlg': dlg}
        if (pre or '').strip():
            do_conv()
        dlg.exec()

    # ---- ⑥ 摘录资料 查看 / 编辑（🗂 / Ctrl+Shift+M）
    def excerpt_viewer(self):
        """查看 + 编辑「摘录本」；另有「截图本」页签（可预览 / 打开图片）。"""
        from PyQt6.QtWidgets import (QTabWidget, QListWidget, QListWidgetItem,
                                     QPlainTextEdit)
        from PyQt6.QtGui import QPixmap
        dlg = QDialog(self)
        dlg.setWindowTitle('摘录资料（摘录本 / 截图本）')
        dlg.resize(960, 660)
        vb = QVBoxLayout(dlg)
        tabs = QTabWidget()
        vb.addWidget(tabs, 1)

        # ---------- 摘录本（可编辑）
        page = QWidget()
        pv = QHBoxLayout(page)
        lcol = QVBoxLayout()
        self._exc_filter = QLineEdit()
        self._exc_filter.setPlaceholderText('过滤：书名 / 关键词')
        lcol.addWidget(self._exc_filter)
        lst = QListWidget()
        lcol.addWidget(lst, 1)
        lrow = QHBoxLayout()
        b_new = QPushButton('＋ 新增')
        b_del = QPushButton('－ 删除')
        b_up = QPushButton('↑ 上移')
        b_dn = QPushButton('↓ 下移')
        for x in (b_new, b_del, b_up, b_dn):
            lrow.addWidget(x)
        lcol.addLayout(lrow)
        rcol = QVBoxLayout()
        rcol.addWidget(QLabel('正文（可编辑）：'))
        ed_body = QPlainTextEdit()
        rcol.addWidget(ed_body, 3)
        rcol.addWidget(QLabel('出处（书名 / 页码 / 版本 …，可编辑）：'))
        ed_cite = QPlainTextEdit()
        ed_cite.setMaximumHeight(90)
        rcol.addWidget(ed_cite, 1)
        brow = QHBoxLayout()
        b_save = QPushButton('保存本条')
        b_save_all = QPushButton('保存全部')
        b_open = QPushButton('打开摘录本.md')
        b_reload = QPushButton('重新载入')
        b_close = QPushButton('关闭')
        for x in (b_save, b_save_all, b_open, b_reload):
            brow.addWidget(x)
        brow.addStretch(1)
        brow.addWidget(b_close)
        rcol.addLayout(brow)
        pv.addLayout(lcol, 1)
        pv.addLayout(rcol, 1)
        tabs.addTab(page, '摘录本')

        # ---------- 截图本（可预览）
        sp = QWidget()
        sv = QHBoxLayout(sp)
        slist = QListWidget()
        sprev = QLabel('选一张截图预览')
        sprev.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sprev.setMinimumWidth(380)
        sbtn = QVBoxLayout()
        b_sopen = QPushButton('用系统看图打开')
        b_sdir = QPushButton('打开截图本文件夹')
        b_srefresh = QPushButton('刷新')
        for x in (b_sopen, b_sdir, b_srefresh):
            sbtn.addWidget(x)
        sbtn.addStretch(1)
        sv.addWidget(slist, 1)
        sv.addWidget(sprev, 2)
        sv.addLayout(sbtn)
        tabs.addTab(sp, '截图本')

        state = {'recs': [], 'cur': -1}

        def open_any(p):
            try:
                os.startfile(p)
            except Exception:
                try:
                    self._open_path(p)
                except Exception:
                    self.statusBar().showMessage('打不开：%s' % p)

        def refresh_snaps():
            slist.clear()
            for s in TOOLS.list_snapshots():
                it = QListWidgetItem(s['name'])
                it.setData(Qt.ItemDataRole.UserRole, s['path'])
                slist.addItem(it)

        def show_snap(*_):
            it = slist.currentItem()
            if not it:
                return
            pm = QPixmap(it.data(Qt.ItemDataRole.UserRole))
            if pm.isNull():
                sprev.setText('打不开图片')
            else:
                sprev.setPixmap(pm.scaled(max(380, sprev.width() - 10), 520,
                                          Qt.AspectRatioMode.KeepAspectRatio,
                                          Qt.TransformationMode.SmoothTransformation))

        def row_of(idx, widget):
            for k in range(widget.count()):
                if int(widget.item(k).data(Qt.ItemDataRole.UserRole)) == idx:
                    return k
            return 0

        def refresh_list(keep=-1):
            lst.blockSignals(True)
            lst.clear()
            kw = (self._exc_filter.text() or '').strip().lower()
            for i, r in enumerate(state['recs']):
                line = (r.get('body') or '').splitlines()
                line = line[0] if line else ''
                txt = '%s ｜ %s' % (r.get('ts') or '（无时间）', line[:40])
                hay = (txt + (r.get('body') or '') + (r.get('cite') or '')).lower()
                if kw and kw not in hay:
                    continue
                it = QListWidgetItem(txt)
                it.setData(Qt.ItemDataRole.UserRole, i)
                lst.addItem(it)
            lst.blockSignals(False)
            if lst.count() and keep >= 0:
                lst.setCurrentRow(row_of(keep, lst))
            elif lst.count():
                lst.setCurrentRow(0)
            else:
                ed_body.setPlainText('')
                ed_cite.setPlainText('')
                state['cur'] = -1

        def load_cur(*_):
            it = lst.currentItem()
            if not it:
                return
            i = int(it.data(Qt.ItemDataRole.UserRole))
            if not (0 <= i < len(state['recs'])):
                return
            state['cur'] = i
            ed_body.setPlainText(state['recs'][i].get('body') or '')
            ed_cite.setPlainText(state['recs'][i].get('cite') or '')

        def push_cur():
            i = state['cur']
            if i < 0:
                return False
            state['recs'][i]['body'] = ed_body.toPlainText().strip('\n')
            state['recs'][i]['cite'] = ed_cite.toPlainText().strip('\n')
            return True

        def do_save_cur():
            if push_cur():
                refresh_list(state['cur'])
                self.statusBar().showMessage('已更新本条（记得「保存全部」写回文件）')

        def do_save_all():
            push_cur()
            try:
                p = TOOLS.write_excerpts(state['recs'])
                self.statusBar().showMessage('已保存摘录本：%s（共 %d 条）'
                                             % (os.path.basename(p), len(state['recs'])))
            except Exception as e:
                self.statusBar().showMessage('保存失败：%s' % e)

        def do_new():
            push_cur()
            import time as _t
            state['recs'].insert(0, {'ts': _t.strftime('%Y-%m-%d %H:%M:%S'),
                                     'body': '', 'cite': ''})
            refresh_list(0)
            lst.setCurrentRow(0)
            ed_body.setFocus()

        def do_del():
            it = lst.currentItem()
            if not it:
                return
            i = int(it.data(Qt.ItemDataRole.UserRole))
            if QMessageBox.question(dlg, '删除摘录',
                                    '确定删除这一条摘录？') != QMessageBox.StandardButton.Yes:
                return
            if not (0 <= i < len(state['recs'])):
                return
            state['recs'].pop(i)
            state['cur'] = -1
            refresh_list(min(i, len(state['recs']) - 1) if state['recs'] else -1)

        def do_move(d):
            it = lst.currentItem()
            if not it:
                return
            i = int(it.data(Qt.ItemDataRole.UserRole))
            j = i + d
            if not (0 <= j < len(state['recs'])):
                return
            push_cur()
            state['recs'][i], state['recs'][j] = state['recs'][j], state['recs'][i]
            refresh_list(j)

        def do_reload():
            try:
                state['recs'] = TOOLS.read_excerpts()
            except Exception:
                state['recs'] = []
            state['cur'] = -1
            refresh_list()

        lst.currentItemChanged.connect(load_cur)
        self._exc_filter.textChanged.connect(lambda *_: refresh_list(state['cur']))
        b_new.clicked.connect(do_new)
        b_del.clicked.connect(do_del)
        b_up.clicked.connect(lambda: do_move(-1))
        b_dn.clicked.connect(lambda: do_move(1))
        b_save.clicked.connect(do_save_cur)
        b_save_all.clicked.connect(do_save_all)
        b_reload.clicked.connect(do_reload)
        b_open.clicked.connect(lambda: open_any(TOOLS.excerpt_target_path()))
        b_close.clicked.connect(dlg.accept)
        slist.currentItemChanged.connect(show_snap)
        b_srefresh.clicked.connect(refresh_snaps)
        b_sopen.clicked.connect(lambda: (slist.currentItem() and
                                         open_any(slist.currentItem().data(Qt.ItemDataRole.UserRole))))
        b_sdir.clicked.connect(lambda: open_any(TOOLS.record_dir(TOOLS._SNAPSHOT_DIR)))
        refresh_snaps()
        do_reload()
        self._last_excerpt_dlg = {'dlg': dlg, 'list': lst, 'body': ed_body,
                                  'cite': ed_cite, 'tabs': tabs, 'recs': state}
        dlg.exec()

    # ---- ⑤ 注释一键插入（脚注，❞ / Ctrl+Shift+I）
    def footnote_here(self):
        """把引文（当前选区 / 剪贴板）做成带出处的「脚注」；粘到 Word 即成真脚注。"""
        body = self._current_selection()
        if not (body or '').strip():
            try:
                body = QApplication.clipboard().text() or ''
            except Exception:
                body = ''
        meta = self._record_meta()
        rd = getattr(self, '_reader', '')
        if rd in ('pdf', 'dual') and getattr(self, 'pd', None) is not None:
            page = int(self.pgno) + 1
        else:
            page = 'X'
        try:
            src = META.cite(meta, page=page)
        except Exception:
            src = ''
        if not src:
            src = self._path()
        try:
            src, _ = CHRONO.annotate(src)
        except Exception:
            pass
        try:
            from PyQt6.QtCore import QMimeData
            rtf = TOOLS.footnote_rtf(body, src).encode('ascii', 'replace')
            md = QMimeData()
            md.setData('text/rtf', bytes(rtf))
            md.setHtml(TOOLS.footnote_html(body, src))
            md.setText(('%s  %s' % (body or '', src or '')).strip())
            QApplication.clipboard().setMimeData(md)
        except Exception as e:
            self.statusBar().showMessage('生成脚注失败：%s' % e)
            return
        self._say('已生成脚注（正文 %d 字 ｜ 脚注「%s」）——到 Word 里 Ctrl+V 即成脚注'
                  % (len(body or ''), (src or '')[:24]), hold=3.5)

    # ---- ③ PDF + TXT 对读（⇄）
    def toggle_dual(self):
        """开/关 PDF 与 TXT 的对照阅读（按页码同步）。"""
        if getattr(self, '_reader', '') == 'dual':
            tp = getattr(self, '_text_path', '')
            self._reader = 'text'
            if tp and os.path.isfile(tp):
                self._show_text_file(tp)
            else:
                self.stack.setCurrentWidget(self.text_view)
            self._say('已退出对读')
            return
        r = self._cur()
        p = os.path.join(r.get('dir') or '', r.get('name') or '') if r else ''
        if not p or not os.path.isfile(p):
            self.statusBar().showMessage('先在列表里选一本书')
            return
        ext = os.path.splitext(p)[1].lower()
        if ext in ('.txt', '.text'):
            if not self._enter_dual(p):
                self.statusBar().showMessage('这本书没有同名 PDF，无法对读')
        elif ext == '.pdf':
            txts = []
            if hasattr(META, '_sibling_texts'):
                try:
                    txts = [x for x in META._sibling_texts(p) if os.path.isfile(x)]
                except Exception:
                    txts = []
            if txts:
                self._enter_dual(txts[0], p)
            else:
                self.statusBar().showMessage('这本 PDF 没有同名 TXT，无法对读')
        else:
            self.statusBar().showMessage('对读只支持 PDF / TXT')

    def _maybe_auto_dual(self, txt_path):
        """打开 TXT 时：若有同名 PDF，则自动进入对读（可在设置里关）。"""
        try:
            if getattr(self, '_suppress_dual', False):
                return False
            if not (txt_path or '').lower().endswith(('.txt', '.text')):
                return False
            if not self.st.get('auto_dual', True):
                return False
            try:                                  # batch16：过大 TXT 不自动进对读（会很卡 / 且只能截断）
                if os.path.getsize(txt_path) > DUAL_TXT_MAX:
                    self.statusBar().showMessage(
                        '这个 TXT 较大（%.0f MB）：未自动进入对读'
                        '（对读只载入前 %d MB）；可点「⇄ 对读」手动打开'
                        % (os.path.getsize(txt_path) / 1048576.0, DUAL_TXT_MAX // 1048576))
                    return False
            except OSError:
                pass
            pdfs = []
            if hasattr(META, '_sibling_pdfs'):
                pdfs = [x for x in META._sibling_pdfs(txt_path) if x.lower().endswith('.pdf')]
            if not pdfs:
                return False
            return self._enter_dual(txt_path, pdfs[0])
        except Exception:
            return False

    def _dual_txt_variants(self, txt_path, pdf_path=''):
        """同一本书可用的 TXT 版本：[(标签, 路径)]（含繁简 / 不同 OCR 版本）。"""
        items, seen = [], set()

        def add(p):
            if not p or not os.path.isfile(p):
                return
            k = os.path.normcase(os.path.abspath(p))
            if k in seen:
                return
            seen.add(k)
            base = os.path.basename(p)
            items.append(('当前：%s' % base if p == txt_path else base, p))

        add(txt_path)
        try:
            for fn in (META._sibling_texts(txt_path) if hasattr(META, '_sibling_texts') else []):
                add(fn)
        except Exception:
            pass
        if pdf_path:
            try:
                d = os.path.dirname(os.path.abspath(pdf_path))
                key = META.family_key(os.path.basename(pdf_path))
                for fn in os.listdir(d):
                    if fn.lower().endswith(('.txt', '.text')) and META.family_key(fn) == key:
                        add(os.path.join(d, fn))
            except OSError:
                pass
        return items

    def _connect_dual(self):
        if getattr(self, '_dual_wired', False):
            return
        try:
            self.dual.txtChanged.connect(self._on_dual_txt_changed)
            self.dual.exitRequested.connect(self._dual_single)
        except Exception:
            pass
        self._dual_wired = True

    def _on_dual_txt_changed(self, path):
        self._text_path = path
        self.statusBar().showMessage('已切换对读 TXT：%s' % os.path.basename(path))

    def _dual_single(self, which):
        """退出对读，只留 PDF 或只留 TXT（保持当前位置）。"""
        try:
            page = int(self.dual.current_page()) + 1
        except Exception:
            page = int(getattr(self, 'pgno', 0)) + 1
        if which == 'pdf':
            if getattr(self, 'pd', None) is None:
                self.statusBar().showMessage('没有 PDF 可单独打开')
                return
            self.pgno = max(0, page - 1)
            self._pdf_show()
            self._say('已退出对读，只显示 PDF（第 %d 页）' % page, hold=2.5)
            return
        tp = getattr(self, '_text_path', '')
        self._reader = 'text'
        if tp and os.path.isfile(tp):
            self._suppress_dual = True
            try:
                self._show_text_file(tp)
            finally:
                self._suppress_dual = False
            self._say('已退出对读，只显示 TXT', hold=2.5)
        else:
            self.stack.setCurrentWidget(self.text_view)
            self._say('已退出对读', hold=2.5)

    def _enter_dual(self, txt_path, pdf_path=None):
        try:
            import fitz
            if not pdf_path and hasattr(META, '_sibling_pdfs'):
                cands = [x for x in META._sibling_pdfs(txt_path) if x.lower().endswith('.pdf')]
                pdf_path = cands[0] if cands else ''
            if not pdf_path or not os.path.isfile(pdf_path):
                return False
            d = fitz.open(pdf_path)
            if int(d.page_count) <= 0:
                return False
            # batch14：进入对读时 PDF 停在第几页——若当前读的就是这本 PDF，就保持在原页
            first = 1
            same = (getattr(self, 'pd', None) is not None
                    and getattr(self, '_pd_path', '') == pdf_path)
            if same:
                try:
                    first = int(getattr(self, 'pgno', 0)) + 1
                except Exception:
                    first = 1
            first = max(1, min(int(d.page_count), first))
            self._connect_dual()
            self.pd = d
            self._pd_path = pdf_path
            self.pgno = first - 1
            fit = getattr(self, '_zoom_mode', 'fitp')
            if fit not in ('fitw', 'fitp', '100'):
                fit = 'fitp'
            self.dual.load(d, txt_path, first=first, fit=fit)
            self.dual.set_txt_list(self._dual_txt_variants(txt_path, pdf_path))
            self._text_path = txt_path
            self._reader = 'dual'
            self.stack.setCurrentWidget(self.dual)
            self._hide_nav()
            self._sync_page_box()
            self._upd_status_pdf()
            self._stat_open(txt_path)
            self._say('已进入 PDF + TXT 对读（左右并列），PDF 停在第 %d 页、TXT 已同步' % first,
                      hold=3.0)
            return True
        except Exception as e:
            self.statusBar().showMessage('对读打开失败：%s' % e)
            return False

    def _on_dual_page(self, i):
        if getattr(self, 'pd', None) is None:
            return
        try:
            self.pgno = max(0, min(int(self.pd.page_count) - 1, int(i)))
        except Exception:
            self.pgno = 0
        self._sync_page_box()
        self._upd_status_pdf()

    # ============================================================ batch3
    # ① Markdown 渲染 / 源码切换（Ctrl+M / 𝐌D 渲染）
    def _read_text_file(self, p, limit=0):
        """只读文本文件：limit=0 读全文（大文件走 mmap，避免额外缓冲）；limit>0 只读前 limit 字节。
        编码：chardet 优先，失败再依次试 utf-8-sig / utf-8 / gb18030 / big5。"""
        try:
            return self._decode_text(self._read_bytes(p, limit))
        except Exception:
            return ''

    def _read_bytes(self, p, limit=0):
        """只读原始字节：limit=0 时大文件用 mmap 映射后整块取出；limit>0 只读前 N 字节。"""
        try:
            size = os.path.getsize(p)
        except OSError:
            size = 0
        if limit and size > limit:
            with open(p, 'rb') as f:
                return f.read(limit)
        if size >= 4 * 1024 * 1024:
            import mmap
            with open(p, 'rb') as f:
                with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                    return bytes(mm)
        with open(p, 'rb') as f:
            return f.read()

    def _decode_text(self, b):
        """把字节解码为文本；chardet 优先，回退常见中文编码。"""
        if not b:
            return ''
        enc = ''
        try:
            import chardet
            enc = (chardet.detect(b[:262144]).get('encoding') or '').lower()
        except Exception:
            enc = ''
        if enc in ('gb2312', 'gbk', 'gb18030'):
            enc = 'gb18030'
        cands = []
        for e in ([enc] if enc else []) + ['utf-8-sig', 'utf-8', 'gb18030', 'big5']:
            if e and e not in cands:
                cands.append(e)
        for e in cands:
            try:
                return b.decode(e)
            except (UnicodeDecodeError, LookupError):
                continue
        return b.decode('utf-8', 'replace')

    def _show_text_file(self, p):
        """把文本文件读进阅读区（纯文本态）；同时复位 MD 状态。"""
        try:
            _sz = os.path.getsize(p)
        except OSError:
            _sz = 0
        _capped = _sz > TEXT_DISPLAY_MAX
        txt = self._read_text_file(p, TEXT_DISPLAY_MAX if _capped else 0)
        self._pdf_stop()
        self._hide_nav()
        self.stack.setCurrentWidget(self.text_view)
        self.view.setPlainText(txt)
        self.pd = None
        self._pd_path = ''
        self._text_path = p
        self._reader = 'text'
        # batch10：不再清空查找结果状态（否则跳转到其它命中文件后列表/计数就废了）
        try:
            self.lb_pg_total.setText('/ 0')
            self.ed_page.setText('0')
        except Exception:
            pass
        self._md_path = ''
        self._md_render = False
        self._md_src = ''
        self._apply_line_height()
        self._stat_open(p)
        if _capped:
            self._say('文件很大（%.0f MB）：为不卡界面，只载入前 %d MB（不静默丢弃）'
                      % (_sz / 1048576.0, TEXT_DISPLAY_MAX // 1048576))
        return True

    def md_toggle(self):
        """Ctrl+M / 𝐌D 渲染：.md 文件在「渲染态 / 源码态」间切换。"""
        r = self._cur()
        p = os.path.join(r.get('dir') or '', r.get('name') or '') if r else ''
        if not p or not p.lower().endswith('.md'):
            self.statusBar().showMessage('这个文件不是 Markdown')
            return
        try:
            self.stack.setCurrentWidget(self.text_view)
            if self._md_path != p:
                # 首次：从磁盘读源码，先以源码态呈现
                try:
                    _sz = os.path.getsize(p)
                except OSError:
                    _sz = 0
                self._md_src = self._read_text_file(
                    p, TEXT_MAX_BYTES if _sz > TEXT_MAX_BYTES else 0)
                self._md_path = p
                self._md_render = False
                self.pd = None
                self._pd_path = ''
                self._text_path = p
                self._reader = 'text'
                self.view.setPlainText(self._md_src)
                self._apply_line_height()
                self._stat_open(p)
            self._md_render = not self._md_render
            if self._md_render:
                self.view.document().setMarkdown(self._md_src or '')
                st = '渲染'
            else:
                self.view.setPlainText(self._md_src or '')
                self._apply_line_height()
                st = '源码'
            self.statusBar().showMessage('Markdown %s态（Ctrl+M 切换）' % st)
        except Exception as e:
            self.statusBar().showMessage('Markdown 切换失败：%s' % e)

    # ② JSON 树形浏览（Ctrl+J）
    def _json_load(self, p):
        """读 + 解析 JSON。返回 (data, err)：err='' 成功；'too_big' 超限；否则异常串。"""
        try:
            if os.path.getsize(p) > JSON_MAX_BYTES:
                return None, 'too_big'
            with open(p, 'rb') as f:
                raw = f.read()
            return json.loads(raw.decode('utf-8-sig')), ''
        except Exception as e:
            return None, str(e)

    def _json_load_stream(self, p, max_items=5000):
        """大 JSON 流式：用 ijson 只读顶层结构（不整份载入）。
        返回 (tree, tag)：tree=None 表示失败（tag 为 'no_ijson' 或异常串）。"""
        try:
            import ijson
        except Exception:
            return None, 'no_ijson'
        tw = QTreeWidget()
        tw.setHeaderLabels(['键 / 索引', '说明'])
        tw.setColumnWidth(0, 280)
        top = ''
        cnt = 0
        try:
            with open(p, 'rb') as f:
                for prefix, event, value in ijson.parse(f):
                    if prefix == '' and event == 'start_map':
                        top = 'map'
                    elif prefix == '' and event == 'start_array':
                        top = 'array'
                    elif top == 'map' and prefix == '' and event == 'map_key':
                        QTreeWidgetItem(tw, [str(value), '顶层键'])
                        cnt += 1
                    elif top == 'array' and prefix == 'item' and event in (
                            'start_map', 'start_array', 'number', 'string', 'boolean', 'null'):
                        QTreeWidgetItem(tw, ['[%d]' % cnt, '元素'])
                        cnt += 1
                    if cnt >= max_items:
                        break
        except Exception as e:
            return None, str(e)
        tw.expandToDepth(0)
        return tw, ('array' if top == 'array' else 'map')

    def _json_show_dialog(self, p, tree, note=''):
        """弹出 JSON 树对话框（可过滤）。"""
        dlg = QDialog(self)
        title = 'JSON 树 — %s' % os.path.basename(p)
        if note:
            title += '｜' + note
        dlg.setWindowTitle(title)
        dlg.resize(760, 620)
        vb = QVBoxLayout(dlg)
        ed = QLineEdit()
        ed.setPlaceholderText('按 key 过滤（输入即筛）')
        vb.addWidget(ed)
        vb.addWidget(tree, 1)
        ed.textChanged.connect(lambda s: self._json_filter(tree, s))
        bb = QPushButton('关闭')
        bb.clicked.connect(dlg.accept)
        vb.addWidget(bb)
        dlg.exec()

    def _json_build_tree(self, data):
        """把 JSON 数据建成 QTreeWidget。dict/list 可展开；值显示类型与内容。"""
        tw = QTreeWidget()
        tw.setHeaderLabels(['键', '值 / 类型'])
        tw.setColumnWidth(0, 240)

        def add(parent, key, val):
            if isinstance(val, dict):
                it = QTreeWidgetItem(parent, [str(key), 'object(%d)' % len(val)])
                for k, v in val.items():
                    add(it, k, v)
            elif isinstance(val, list):
                it = QTreeWidgetItem(parent, [str(key), 'array(%d)' % len(val)])
                for i, v in enumerate(val):
                    add(it, '[%d]' % i, v)
            else:
                QTreeWidgetItem(parent, [str(key), _json_val_str(val)])

        if isinstance(data, dict):
            for k, v in data.items():
                add(tw, k, v)
        elif isinstance(data, list):
            add(tw, '(root array)', data)
        else:
            QTreeWidgetItem(tw, ['(root)', _json_val_str(data)])
        tw.expandToDepth(0)
        return tw

    def _json_filter(self, tree, txt):
        """按 key 过滤：命中项及其祖先显示，否则隐藏。返回可见顶层数。"""
        txt = (txt or '').strip().lower()

        def walk(it):
            hit = (not txt) or (txt in it.text(0).lower())
            child_hit = False
            for i in range(it.childCount()):
                if walk(it.child(i)):
                    child_hit = True
            show = hit or child_hit
            it.setHidden(not show)
            return show

        n = 0
        for i in range(tree.topLevelItemCount()):
            if walk(tree.topLevelItem(i)):
                n += 1
        if txt:
            tree.expandAll()
        return n

    def json_tree_dialog(self):
        """Ctrl+J：.json 文件键值树（可展开、可过滤）。大文件/坏文件回退纯文本。"""
        r = self._cur()
        p = os.path.join(r.get('dir') or '', r.get('name') or '') if r else ''
        if not p or not p.lower().endswith('.json'):
            self.statusBar().showMessage('这个文件不是 JSON')
            return
        if not os.path.isfile(p):
            self.statusBar().showMessage('文件不在了：%s' % p)
            return
        data, err = self._json_load(p)
        if err == 'too_big':
            tree, tag = self._json_load_stream(p)
            if tree is not None:
                self._last_json = {'tree': tree, 'path': p, 'top': tree.topLevelItemCount()}
                self._json_show_dialog(p, tree, '大文件·流式（仅顶层）')
                return
            self.statusBar().showMessage('这个 JSON 超过 20 MB，改用纯文本显示')
            try:
                self._show_text_file(p)
            except Exception as e:
                self.statusBar().showMessage('回退纯文本失败：%s' % e)
            return
        if err:
            self.statusBar().showMessage('JSON 解析失败（%s），改用纯文本显示' % err)
            try:
                self._show_text_file(p)
            except Exception as e:
                self.statusBar().showMessage('回退纯文本失败：%s' % e)
            return
        tree = self._json_build_tree(data)
        self._last_json = {'tree': tree, 'path': p, 'top': tree.topLevelItemCount()}
        self._json_show_dialog(p, tree)

    # ③ 相关文件推荐（Ctrl+R）
    def _series_prefix(self, name):
        """书名去除卷册/括注后，取开头连续中文作为「丛书/专题」前缀。"""
        try:
            s = META.book_core(name or '')
        except Exception:
            s = name or ''
        s = re.sub(r'[（(][^（）()]*[)）]', '', s)          # 去所有括注
        s = re.sub(r'第\s*[0-9一二三四五六七八九十百千]{1,4}\s*[册卷集部编篇辑期]', '', s)
        s = re.sub(r'全\s*[0-9一二三四五六七八九十]{1,3}\s*册', '', s)
        s = re.sub(r'[\s_\-—+·、.]+', ' ', s).strip(' _-—+·、.')
        m = re.match(r'[\u4e00-\u9fa5]{2,}', s)
        return (m.group(0) if m else s).strip()

    def related_groups(self):
        """相关文献推荐。返回多档：
        A=同丛书/同专题(兼容) B=同作者(兼容) C=同目录(兼容)；
        另加 batch11 四档细分：series / topic / same_book / same_author。
        """
        out = {'A': [], 'B': [], 'C': [], 'prefix': '', 'author': '', 'db': self.db,
               'series': [], 'topic': [], 'same_book': [], 'same_author': []}
        r = self._cur()
        if not r:
            return out
        p = os.path.join(r.get('dir') or '', r.get('name') or '')
        folder = r.get('dir') or ''
        try:
            cm = META.parse(r.get('name') or '', p, deep=False)
        except Exception:
            cm = {}
        prefix = self._series_prefix(cm.get('name') or r.get('name') or '')
        author = cm.get('author') or ''
        out['prefix'], out['author'] = prefix, author
        folder_base = os.path.basename(os.path.normpath(folder)) if folder else ''

        cands = {}
        # 相邻书架：直接读当前目录（最快，不查库）
        try:
            for fn in sorted(os.listdir(folder)):
                fp = os.path.join(folder, fn)
                if os.path.isfile(fp) and fp != p:
                    cands[fp] = {'name': fn, 'dir': folder, 'path': fp,
                                 'ext': os.path.splitext(fn)[1].lower()}
        except OSError:
            pass
        # 同丛书 / 同作者：search 关键词（限制 200 条候选）
        for kw in (prefix, author):
            if not kw:
                continue
            try:
                for rr in C.search(self.db, kw, 200):
                    fp = os.path.join(rr.get('dir') or '', rr.get('name') or '')
                    if fp and fp != p and fp not in cands:
                        cands[fp] = rr
            except Exception:
                pass
        cands = dict(list(cands.items())[:200])

        cand_list = []
        for fp, c in cands.items():
            nm = c.get('name') or os.path.basename(fp)
            d = c.get('dir') or os.path.dirname(fp)
            try:
                xm = META.parse(nm, fp, deep=False)
            except Exception:
                xm = {}
            xp = self._series_prefix(xm.get('name') or nm)
            same_folder = bool(folder_base) and \
                os.path.basename(os.path.normpath(d)) == folder_base
            item = {'name': nm, 'dir': d, 'path': fp}
            if (prefix and xp and xp == prefix) or same_folder:
                out['A'].append(item)
            if author and (xm.get('author') or '') == author:
                out['B'].append(item)
            if os.path.normpath(d) == os.path.normpath(folder):
                out['C'].append(item)
            cand_list.append({'name': nm, 'dir': d, 'path': fp,
                              'author': (xm.get('author') or '')})
        out['C'] = out['C'][:50]
        # batch11：四档细分（同丛书 / 同专题 / 同一本书的其他书 / 同一作者的其他著作）
        cur = {'name': cm.get('name') or r.get('name') or '', 'dir': folder,
               'path': p, 'author': author}
        try:
            out.update(TOOLS.classify_related(cur, cand_list))
        except Exception:
            pass
        return out

    def _open_path(self, path):
        """在阅读区打开一个路径（PDF/EPUB 走 fitz；文本走纯文本）。"""
        if not path or not os.path.isfile(path):
            self.statusBar().showMessage('文件不在了：%s' % path)
            return False
        ext = os.path.splitext(path)[1].lower()
        if ext in ('.pdf', '.epub', '.xps', '.cbz', '.mobi', '.fb2', '.svg'):
            try:
                import fitz
                d = fitz.open(path)
                if d.page_count <= 0:
                    self.statusBar().showMessage('这个文件没有可显示的页面')
                    return False
                self.pd = d
                self._pd_path = path
                self.pgno = 0
                self._pdf_show()
                self._after_pdf_open()
                self._hist_add()
                self._stat_open(path)
                return True
            except Exception as e:
                self.statusBar().showMessage('打不开：%s' % e)
                return False
        try:
            self._show_text_file(path)
            self._maybe_auto_dual(path)
            self.statusBar().showMessage('已打开：%s' % os.path.basename(path))
            return True
        except Exception as e:
            self.statusBar().showMessage('打不开：%s' % e)
            return False

    def related_dialog(self):
        """Ctrl+R：相关文件（同丛书/同作者/相邻书架，三档分组，双击打开）。"""
        r = self._cur()
        if not r:
            self.statusBar().showMessage('先在列表里选一本书')
            return
        g = self.related_groups()
        self._last_related = g
        tree = QTreeWidget()
        tree.setHeaderLabels(['相关文件', '所在文件夹'])
        tree.setColumnWidth(0, 300)
        series = g.get('series') or g.get('A') or []
        topic = g.get('topic') or []
        same_book = g.get('same_book') or []
        same_author = g.get('same_author') or g.get('B') or []
        groups = [('同丛书（%d）' % len(series), series),
                  ('同专题（同目录，%d）' % len(topic), topic),
                  ('同一本书的其他书（%d）' % len(same_book), same_book),
                  ('同一作者的其他著作（%d）' % len(same_author), same_author)]
        for title, lst in groups:
            gi = QTreeWidgetItem(tree, [title, ''])
            for it in lst:
                ci = QTreeWidgetItem(gi, [it['name'], it['dir']])
                ci.setData(0, Qt.ItemDataRole.UserRole, it['path'])
            gi.setExpanded(True)
        g['tree'] = tree
        dlg = QDialog(self)
        dlg.setWindowTitle('相关文件 — %s' % (r.get('name') or ''))
        dlg.resize(760, 600)
        vb = QVBoxLayout(dlg)
        vb.addWidget(QLabel('四档推荐：同丛书（前缀「%s」）／ 同专题（同目录）／'
                            '同一本书的其他书（同名）／ 同一作者的其他著作。双击打开。'
                            % (g['prefix'] or '—')))
        vb.addWidget(tree, 1)
        bb = QPushButton('关闭')
        bb.clicked.connect(dlg.accept)
        vb.addWidget(bb)
        g['dialog'] = dlg

        def go(item):
            if item is None:
                return
            path = item.data(0, Qt.ItemDataRole.UserRole)
            if path:
                self._open_path(path)
                dlg.accept()

        tree.itemDoubleClicked.connect(go)
        dlg.exec()

    # ④ 导航面板（目录 / 缩略图 / 查找）—— Ctrl+T · Ctrl+Shift+T 聚焦对应页签
    def _build_nav_dock(self):
        """构建导航面板（右侧 QDockWidget，含 目录 / 缩略图 / 查找 三个页签）。"""
        if getattr(self, '_nav_dock', None) is not None:
            return
        dk = QDockWidget('导航', self)
        dk.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea |
                           Qt.DockWidgetArea.RightDockWidgetArea)
        tabs = QTabWidget()
        toc = QListWidget()
        toc.itemDoubleClicked.connect(self._nav_toc_go)
        toc.itemClicked.connect(self._nav_toc_go)     # 单击即跳页（batch7）
        lst = QListWidget()
        lst.setViewMode(QListWidget.ViewMode.IconMode)
        lst.setIconSize(QSize(110, 150))
        lst.setResizeMode(QListWidget.ResizeMode.Adjust)
        lst.setMovement(QListWidget.Movement.Static)
        lst.setSpacing(6)
        lst.itemClicked.connect(self._thumb_clicked)
        fnd = QListWidget()
        fnd.itemDoubleClicked.connect(self._nav_find_go)
        fnd.itemClicked.connect(self._nav_find_go)
        fnd_box = QWidget()
        _fv = QVBoxLayout(fnd_box)
        _fv.setContentsMargins(0, 0, 0, 0)
        _fv.setSpacing(2)
        _fv.addWidget(fnd, 1)
        self._btn_find_hidden = QPushButton('显示被去重的项')
        self._btn_find_hidden.setToolTip('被去重（同名且命中数相同的 TXT）默认隐藏；点此展开/收起')
        self._btn_find_hidden.setVisible(False)
        self._btn_find_hidden.clicked.connect(self.toggle_find_hidden)
        _fv.addWidget(self._btn_find_hidden)
        tabs.addTab(toc, '目录')
        tabs.addTab(lst, '缩略图')
        tabs.addTab(fnd_box, '查找')
        # batch10：窗口小的时候页签字不显示不全 —— 不拉伸、缩小内边距/字号、带滚动按钮
        try:
            tabs.setDocumentMode(True)
            tabs.setUsesScrollButtons(True)
            tabs.tabBar().setExpanding(False)
            tabs.tabBar().setElideMode(Qt.TextElideMode.ElideNone)
            _tf = tabs.font()
            _tf.setPointSize(max(7, _tf.pointSize() - 1))
            tabs.setFont(_tf)
            tabs.setStyleSheet('QTabBar::tab{padding:2px 7px;}')
            for _k, _t in enumerate(('目录', '缩略图', '查找')):
                tabs.setTabToolTip(_k, _t)
        except Exception:
            pass
        tabs.currentChanged.connect(self._nav_tab_changed)
        dk.setWidget(tabs)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dk)
        self._nav_dock = dk
        self._nav_tabs = tabs
        self._nav_toc = toc
        self._nav_find = fnd
        self._thumb_dock = dk            # 兼容旧断言/旧叫法
        self._thumb_list = lst

    def _build_thumb_dock(self):        # 兼容旧名
        self._build_nav_dock()

    def _nav_tab_changed(self, i):
        if i == 1 and getattr(self, 'pd', None) is not None:
            self._start_thumb_load()

    def _show_nav(self, tab=0):
        self._build_nav_dock()
        try:
            self._nav_tabs.setCurrentIndex(int(tab))
        except Exception:
            pass
        if int(tab) == 1:
            self._start_thumb_load()
        self._nav_dock.show()

    def _hide_nav(self):
        dk = getattr(self, '_nav_dock', None)
        if dk is not None:
            dk.hide()
        self._stop_thumb_timer()

    def _nav_toc_go(self, item):
        """单击/双击目录项 → 跳页。"""
        if item is None:
            return
        pg = item.data(Qt.ItemDataRole.UserRole)
        d = getattr(self, 'pd', None)
        if pg is None or d is None:
            return
        self.pgno = max(0, min(int(d.page_count) - 1, int(pg)))
        self.pdf_view.goto_page(self.pgno)
        self.statusBar().showMessage('已跳到第 %d 页' % (int(self.pgno) + 1))

    def _nav_find_go(self, item):
        """双击查找结果 → 跳该页并高亮。"""
        if item is None:
            return
        k = item.data(Qt.ItemDataRole.UserRole)
        if k is None:
            return
        self._find_idx = int(k)
        self._find_jump(int(k))
        self._upd_find_label()

    def _fill_nav_toc(self):
        """把当前文档的大纲（无大纲则页码）填进「目录」页签，返回条目数。"""
        d = getattr(self, 'pd', None)
        if d is None:
            return 0
        try:
            items = d.get_toc() or []
        except Exception:
            items = []
        self._build_nav_dock()
        toc = self._nav_toc
        toc.clear()
        row_pages = []
        if items:
            for lvl, title, pg in items:
                it = QListWidgetItem('%s%s（第 %d 页）'
                                     % ('    ' * max(0, int(lvl) - 1), title, int(pg)))
                it.setData(Qt.ItemDataRole.UserRole, int(pg) - 1)
                toc.addItem(it)
                row_pages.append(max(0, int(pg) - 1))
        else:
            for i in range(int(d.page_count)):
                it = QListWidgetItem('第 %d 页' % (i + 1))
                it.setData(Qt.ItemDataRole.UserRole, i)
                toc.addItem(it)
                row_pages.append(i)
        self._last_toc = {'items': items, 'pages': int(d.page_count),
                          'rows': toc.count(), 'row_pages': row_pages,
                          'path': getattr(self, '_pd_path', '')}
        return toc.count()

    def _after_pdf_open(self):
        """打开 PDF/EPUB 后：清掉上一份文档的查找状态，填目录并默认展开导航面板。"""
        self._pd_texts = None
        self._pd_texts_doc = None
        self._hl_kw = ''
        self._find_kw = ''
        self._find_total = 0
        self._find_idx = -1
        self._find_hits = []
        try:
            self._fill_nav_toc()
        except Exception:
            pass
        self._show_nav(0)

    # ④ 文内查找条（Ctrl+F）
    def _build_find_bar(self):
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        self.ed_find = QLineEdit()
        self.ed_find.setPlaceholderText('文内查找（Ctrl+F；回车查找）—— PDF 需有文字层')
        self.ed_find.returnPressed.connect(self.find_run)
        self.b_find_prev = QPushButton('上一个')
        self.b_find_prev.clicked.connect(self.find_prev)
        self.b_find_next = QPushButton('下一个')
        self.b_find_next.clicked.connect(self.find_next)
        self.lb_find = QLabel('第 0 / 0 处')
        self.b_find_close = QPushButton('✕')
        self.b_find_close.setToolTip('关闭查找条（Esc）')
        self.b_find_close.clicked.connect(self.find_close)
        h.addWidget(QLabel('查找'))
        h.addWidget(self.ed_find, 1)
        for _b in (self.b_find_prev, self.b_find_next, self.b_find_close):
            try:
                _b.setFixedHeight(24)
            except Exception:
                pass
        h.addWidget(self.b_find_prev)
        h.addWidget(self.b_find_next)
        h.addWidget(self.lb_find)
        h.addWidget(self.b_find_close)
        self._find_bar_widget = w
        w.setVisible(False)          # 初始隐藏，Ctrl+F 才出现（给阅读让空间）
        return w

    def find_focus(self):
        """Ctrl+F：显示并聚焦查找条。"""
        try:
            self._find_bar_widget.setVisible(True)
            self.ed_find.setFocus()
            self.ed_find.selectAll()
        except Exception:
            pass

    def find_close(self):
        """Esc / ✕：关闭查找条，清掉 PDF 高亮。"""
        try:
            self._find_bar_widget.setVisible(False)
        except Exception:
            pass
        if getattr(self, '_hl_kw', ''):
            self._hl_kw = ''
            try:
                self.pdf_view.set_highlight('')
            except Exception:
                pass
        self._find_total = 0
        self._find_idx = -1
        self._upd_find_label()

    def _upd_find_label(self):
        try:
            self.lb_find.setText('第 %d / %d 处'
                                 % ((self._find_idx + 1) if self._find_total > 0 else 0,
                                    self._find_total))
        except Exception:
            pass

    def find_run(self):
        """执行查找（当前文件内）。"""
        kw = self.ed_find.text()
        if not kw:
            self._find_total = 0
            self._find_idx = -1
            self._upd_find_label()
            return
        self._find_all(kw)

    @staticmethod
    def _hit(f, h):
        """一条命中 —— 统一成可跳转的结构。"""
        return {'path': f.get('path'), 'name': f.get('name'), 'page': h.get('page'),
                'off': h.get('off'), 'ctx': h.get('ctx') or '',
                'txt_mark': f.get('txt_mark')}

    def _rebuild_find_view(self):
        """当前展示的命中列表 = 保留项 (+ 被去重项，若用户打开了开关)。"""
        self._find_view = list(getattr(self, '_find_kept', []))
        if getattr(self, '_find_show_hidden', False):
            self._find_view += list(getattr(self, '_find_hidden', []))
        self._find_hits = list(getattr(self, '_find_kept', []))   # 兼容旧引用
        self._find_total = len(self._find_view)
        if not self._find_view:
            self._find_idx = -1
        elif self._find_idx < 0 or self._find_idx >= self._find_total:
            self._find_idx = 0

    def toggle_find_hidden(self):
        """展开/收起「被去重」的命中（默认隐藏）。"""
        self._find_show_hidden = not getattr(self, '_find_show_hidden', False)
        self._rebuild_find_view()
        self._populate_find_tab()
        self._upd_find_label()
        if self._find_view:
            self._find_jump(self._find_idx if self._find_idx >= 0 else 0)
        self.statusBar().showMessage(
            '%s被去重项（共 %d 处）' % ('已展开' if self._find_show_hidden else '已收起',
                                      len(getattr(self, '_find_hidden', []))))

    def _find_targets(self):
        """batch9：单文件范围 = 当前打开的文件 + 同目录「同一本书」的 PDF/TXT 变体。"""
        cur = self._find_current_path()
        if not cur:
            return []
        files, seen = [], set()

        def add(p):
            k = os.path.normcase(os.path.abspath(p))
            if p and k not in seen and os.path.isfile(p):
                seen.add(k)
                files.append(p)

        add(cur)
        try:
            d = os.path.dirname(os.path.abspath(cur))
            key = META.family_key(os.path.basename(cur))
            if key:
                for fn in os.listdir(d):
                    if os.path.splitext(fn)[1].lower() in ('.pdf', '.txt') \
                            and META.family_key(fn) == key:
                        add(os.path.join(d, fn))
        except OSError:
            pass
        return files

    def _find_current_path(self):
        if getattr(self, '_reader', '') == 'pdf':
            return getattr(self, '_pd_path', '')
        return getattr(self, '_text_path', '')

    def _find_all(self, kw):
        """batch9 统一入口：当前文件 + 同书 PDF/TXT 一起找，按规则去重后列表展示。"""
        self._find_kw = kw
        rep = []
        for p in self._find_targets():
            try:
                ext = os.path.splitext(p)[1].lower()
                cnt, hh = self._scan_pdf(p, kw) if ext == '.pdf' else self._scan_text(p, kw)
            except Exception:
                continue
            rep.append({'path': p, 'name': os.path.basename(p), 'count': cnt, 'hits': hh})
        kept, hidden = META.dedup_split(rep)          # batch9：被去重项默认隐藏
        self._find_kept = [self._hit(f, h)
                           for f in kept for h in (f.get('hits') or [])]
        self._find_hidden = [dict(self._hit(f, h), hidden=True)
                             for f in hidden for h in (f.get('hits') or [])]
        self._find_show_hidden = False
        self._rebuild_find_view()
        self._hl_kw = kw if self._find_view else ''
        try:
            if getattr(self, 'pd', None) is not None and getattr(self, '_reader', '') in ('pdf', 'dual'):
                self._pdf_view_active().set_highlight(self._hl_kw)
        except Exception:
            pass
        self._populate_find_tab()
        self._upd_find_label()
        if self._find_view:
            self._find_jump(0)
            self._show_nav(2)
            _msg = '文内查找：命中 %d 处（%d 个文件）' % (len(self._find_kept), len(kept))
            if self._find_hidden:
                _msg += '，另有 %d 处被去重隐藏（点「显示被去重的项」查看）' % len(self._find_hidden)
            self.statusBar().showMessage(_msg)
        else:
            cur = self._find_current_path()
            _notxt = False
            if (cur or '').lower().endswith('.pdf'):
                d = getattr(self, 'pd', None)
                if d is not None and getattr(self, '_pd_texts_doc', None) == id(d):
                    _notxt = not any((x or '').strip() for x in (self._pd_texts or []))
            if _notxt:
                self.statusBar().showMessage(
                    '这个 PDF 没有文字层，需要先做 OCR（可以交给 CathayOCR）')
            else:
                self.statusBar().showMessage('没找到：%s' % kw)

    def _scan_text(self, p, kw):
        """扫描一个文本文件：返回 (总次数, 命中[{off,ctx}])。"""
        try:
            _sz = os.path.getsize(p)
        except OSError:
            _sz = 0
        t = self._norm_ws(self._read_text_file(
            p, TEXT_MAX_BYTES if _sz > TEXT_MAX_BYTES else 0))
        t = t.replace('\r\n', '\n').replace('\r', '\n')   # 对齐 QTextEdit 的换行处理
        count, hits, start = 0, [], 0
        while True:
            j = t.find(kw, start)
            if j < 0:
                break
            count += 1
            if len(hits) < 500:
                hits.append({'off': j, 'ctx': self._ctx(t, j, len(kw))})
            start = j + len(kw)
        return count, hits

    def _find_jump(self, i):
        """跳到展示列表的第 i 处；命中在别的文件里就先切过去。"""
        view = getattr(self, '_find_view', None) or getattr(self, '_find_hits', [])
        if not (0 <= i < len(view)):
            return
        h = view[i]
        _cur = self._find_current_path() or ''
        if h.get('path') and os.path.normcase(h['path']) != os.path.normcase(_cur):
            if not self._open_path(h['path']):            # batch10：打不开就明确提示
                self.statusBar().showMessage('打不开这条结果：%s' % (h.get('path') or ''))
                return
            QTimer.singleShot(0, self._populate_find_tab)   # 延后刷新，避免在信号里清表
        self._find_idx = i
        if h.get('page') is not None and getattr(self, 'pd', None) is not None:
            self.pgno = max(0, min(int(self.pd.page_count) - 1, int(h['page'])))
            try:
                self._pdf_view_active().set_highlight(self._hl_kw)
                self._pdf_view_active().goto_page(self.pgno)
            except Exception:
                pass
        elif h.get('off') is not None:
            try:
                tw = self._txt_widget()
                if tw is self.view:
                    self.stack.setCurrentWidget(self.text_view)
                doc = tw.document()
                c = tw.textCursor()
                c.setPosition(min(int(h['off']), max(0, doc.characterCount() - 1)))
                c.setPosition(min(c.position() + len(self._hl_kw),
                                  max(0, doc.characterCount() - 1)),
                              QTextCursor.MoveMode.KeepAnchor)
                tw.setTextCursor(c)
                tw.centerCursor()
            except Exception:
                pass
        mark = '（TXT）' if h.get('txt_mark') else ''
        pg = ('第 %d 页' % (int(h['page']) + 1)) if h.get('page') is not None else '文本'
        self.statusBar().showMessage('第 %d / %d 处 ｜ %s%s ｜ %s：%s'
                                     % (i + 1, self._find_total, h.get('name') or '',
                                        mark, pg, h.get('ctx') or ''))

    def _text_step(self, forward):
        tw = self._txt_widget()
        if forward:
            found = tw.find(self._find_kw)
        else:
            found = tw.find(self._find_kw, QTextDocument.FindFlag.FindBackward)
        if not found:                       # 循环：回到头/尾再找
            cur = tw.textCursor()
            cur.movePosition(QTextCursor.MoveOperation.Start if forward
                             else QTextCursor.MoveOperation.End)
            tw.setTextCursor(cur)
            if forward:
                found = tw.find(self._find_kw)
            else:
                found = tw.find(self._find_kw, QTextDocument.FindFlag.FindBackward)
        return found

    def find_next(self):
        if self._find_total <= 0:
            if self.ed_find.text():
                self.find_run()
            return
        self._find_idx = (self._find_idx + 1) % self._find_total
        self._find_jump(self._find_idx)
        self._upd_find_label()

    def find_prev(self):
        if self._find_total <= 0:
            if self.ed_find.text():
                self.find_run()
            return
        self._find_idx = (self._find_idx - 1) % self._find_total
        self._find_jump(self._find_idx)
        self._upd_find_label()

    def _norm_ws(self, s):
        """把 PDF 取文里常见的非断行空格/全角空格归一为普通空格，便于检索。"""
        return (s or '').replace('\xa0', ' ').replace('\u3000', ' ').replace('\ufffd', ' ')

    def _ctx(self, t, j, n, span=30):
        a = max(0, j - span)
        b = min(len(t), j + n + span)
        s = t[a:b].replace('\n', ' ').replace('\r', ' ').strip()
        return ('…' if a > 0 else '') + s + ('…' if b < len(t) else '')

    def _scan_pdf(self, p, kw):
        """扫描一个 PDF 的文字层：返回 (总次数, 命中[{page,ctx}])。"""
        d = getattr(self, 'pd', None)
        if d is not None and os.path.normcase(getattr(self, '_pd_path', '')) == os.path.normcase(p):
            if self._pd_texts is None or getattr(self, '_pd_texts_doc', None) != id(d):
                try:
                    self._pd_texts = [self._norm_ws(d[i].get_text() or '')
                                      for i in range(int(d.page_count))]
                except Exception:
                    self._pd_texts = []
                self._pd_texts_doc = id(d)
            texts = self._pd_texts
        else:
            import fitz
            doc = fitz.open(p)
            try:
                texts = [self._norm_ws(doc[i].get_text() or '')
                         for i in range(int(doc.page_count))]
            finally:
                doc.close()
        count, hits = 0, []
        for i, t in enumerate(texts):
            j = t.find(kw)
            while j >= 0:
                count += 1
                if len(hits) < 500:
                    hits.append({'page': i, 'ctx': self._ctx(t, j, len(kw))})
                j = t.find(kw, j + len(kw))
        return count, hits

    def _find_pdf_jump(self, i):
        """兼容旧接口：跳到第 i 处。"""
        self._find_jump(int(i))

    def _populate_find_tab(self):
        self._build_nav_dock()
        lst = self._nav_find
        lst.clear()
        cur = self._find_current_path()
        for k, h in enumerate(getattr(self, '_find_view', [])):
            same = os.path.normcase(h.get('path') or '') == os.path.normcase(cur or '')
            head = ('第 %d 页' % (int(h['page']) + 1)) if h.get('page') is not None else '文本'
            if not same:
                head = '%s%s ｜ %s' % (h.get('name') or '',
                                       '（TXT）' if h.get('txt_mark') else '', head)
            if h.get('hidden'):
                head += '（已去重）'
            it = QListWidgetItem('%s ｜ %s' % (head, h.get('ctx') or ''))
            it.setData(Qt.ItemDataRole.UserRole, k)
            lst.addItem(it)
        b = getattr(self, '_btn_find_hidden', None)
        if b is not None:
            nh = len(getattr(self, '_find_hidden', []))
            b.setVisible(nh > 0)
            b.setText(('▾ 收起被去重的 %d 项' if getattr(self, '_find_show_hidden', False)
                       else '▸ 显示被去重的 %d 项') % nh)

    def _thumb_add_one(self):
        """渲染下一页缩略图（懒加载，最多 40 页）。成功返回 True。"""
        d = getattr(self, 'pd', None)
        lst = getattr(self, '_thumb_list', None)
        if d is None or lst is None:
            return False
        total = int(getattr(d, 'page_count', 0) or 0)
        i = self._thumbs_added
        if i >= 40 or i >= total:
            return False
        try:
            import fitz
            pm = d[i].get_pixmap(matrix=fitz.Matrix(0.15, 0.15))
            img = QImage(pm.samples, pm.width, pm.height, pm.stride,
                         QImage.Format.Format_RGB888).copy()
            it = QListWidgetItem(QIcon(QPixmap.fromImage(img)), '第 %d 页' % (i + 1))
            it.setData(Qt.ItemDataRole.UserRole, i)
            lst.addItem(it)
        except Exception:
            pass
        self._thumbs_added = i + 1
        return True

    def _thumb_step(self):
        if not self._thumb_add_one():
            self._stop_thumb_timer()
            lst = getattr(self, '_thumb_list', None)
            if lst is not None and lst.count():
                self.statusBar().showMessage('缩略图已就绪：%d 页' % lst.count())

    def _stop_thumb_timer(self):
        t = getattr(self, '_thumb_timer', None)
        if t is not None:
            t.stop()

    def _start_thumb_load(self):
        lst = getattr(self, '_thumb_list', None)
        if lst is None:
            return
        lst.clear()
        self._thumbs_added = 0
        if getattr(self, '_thumb_timer', None) is None:
            from PyQt6.QtCore import QTimer as _QT
            self._thumb_timer = _QT(self)
            self._thumb_timer.setInterval(0)
            self._thumb_timer.timeout.connect(self._thumb_step)
        self._thumb_timer.start()

    def _thumb_clicked(self, item):
        """点缩略图 → 跳该页。"""
        i = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        d = getattr(self, 'pd', None)
        if i is None or d is None:
            return
        self.pgno = max(0, min(int(d.page_count) - 1, int(i)))
        self.pdf_view.goto_page(self.pgno)

    def toggle_thumbs(self):
        """Ctrl+Shift+T：打开/隐藏右侧缩略图面板（PDF/EPUB，懒加载前 40 页）。"""
        d = getattr(self, 'pd', None)
        if d is None or int(getattr(d, 'page_count', 0) or 0) <= 0:
            self.statusBar().showMessage('缩略图只对已打开的 PDF / EPUB 有效'
                                         '（先点 📖 在阅读区打开或 Ctrl+E）')
            return
        if (self._nav_dock is not None and self._nav_dock.isVisible()
                and self._nav_tabs is not None and self._nav_tabs.currentIndex() == 1):
            self._nav_dock.hide()
            self._stop_thumb_timer()
            self.statusBar().showMessage('已隐藏缩略图（Ctrl+Shift+T 再开）')
            return
        self._show_nav(1)
        self.statusBar().showMessage('缩略图加载中…（Ctrl+Shift+T 隐藏）')

    def preview_here(self):
        r = self._cur()
        if not r:
            return
        p = os.path.join(r.get('dir') or '', r.get('name') or '')
        ext = (r.get('ext') or '').lower()
        try:
            if ext in ('.txt', '.md', '.json', '.csv'):
                self._show_text_file(p)
                if ext == '.txt':
                    self._maybe_auto_dual(p)
                self._hist_add()
                self.statusBar().showMessage('已打开文本（只读，全文；超大文件最多前 64 MB）')
            elif ext in ('.pdf', '.epub', '.xps', '.cbz', '.mobi', '.fb2', '.svg'):
                if ext == '.pdf':
                    # 先验文件头/结尾：坏 PDF 会让 PyMuPDF 直接 abort（连异常都不抛）
                    with open(p, 'rb') as f:
                        head = f.read(5)
                        f.seek(max(0, os.path.getsize(p) - 2048))
                        tail = f.read()
                    if not head.startswith(b'%PDF') or b'%%EOF' not in tail:
                        raise ValueError('PDF 结构不完整（可先用 CathayRepair 修一下）')
                import fitz
                d = fitz.open(p)
                self.pd = d
                self._pd_path = p
                self.pgno = 0
                try:
                    _mk = (C.load_settings().get('marks') or {}).get(p) or {}
                    self.pgno = max(0, min(d.page_count - 1, int(_mk.get('page') or 0)))
                except Exception:
                    pass
                self._pdf_show()
                self._after_pdf_open()
                self._hist_add()
                self._stat_open(p)
            else:
                self.stack.setCurrentWidget(self.text_view)
                self.view.setPlainText('这个格式（%s）暂不支持在此预览，'
                                       '点「↗ 用外部程序打开」。' % ext)
                self._pdf_stop()
                self._hide_nav()
        except Exception as e:
            self.stack.setCurrentWidget(self.text_view)
            self.view.setPlainText('打不开：%s: %s' % (type(e).__name__, e))

    def _path(self):
        r = self._cur()
        return os.path.join(r.get('dir') or '', r.get('name') or '') if r else ''

    def open_external(self):
        p = self._path()
        if p and os.path.isfile(p):
            try:
                os.startfile(p)
            except Exception as e:
                QMessageBox.warning(self, '提示', '打开失败：%s' % e)
        else:
            QMessageBox.information(self, '提示', '文件不在（盘没插？）')

    def open_folder(self):
        p = self._path()
        d = os.path.dirname(p)
        if d and os.path.isdir(d):
            try:
                os.startfile(d)
            except Exception as e:
                QMessageBox.warning(self, '提示', '打开失败：%s' % e)
        else:
            QMessageBox.information(self, '提示', '文件夹不在（盘没插？）')


def _json_val_str(v):
    """JSON 叶子值 → 显示文本（字符串截断 200 字，附带类型）。"""
    if isinstance(v, str):
        s = v if len(v) <= 200 else v[:200] + '…（共 %d 字）' % len(v)
        return 'str: ' + s
    if v is None:
        return 'null'
    if isinstance(v, bool):
        return 'bool: ' + ('true' if v else 'false')
    if isinstance(v, int):
        return 'int: %d' % v
    if isinstance(v, float):
        return 'float: %g' % v
    return str(v)


def _ts(t):
    try:
        import time
        return time.strftime('%Y-%m-%d %H:%M', time.localtime(float(t)))
    except Exception:
        return ''


# ---------------------------------------------------------------- 自检
def selftest():
    import shutil
    import tempfile
    log = []

    def ok(c, m):
        log.append(('OK  ' if c else 'FAIL') + ' ' + m)
        return bool(c)

    _plat = os.environ.get('CV_PLATFORM')
    if _plat is None:
        # Windows 用原生平台；offscreen 在本机 PyQt6 6.10 + Python 3.14 下会在 MainWindow 构造处原生崩溃
        _plat = '' if sys.platform.startswith('win') else 'offscreen'
    if _plat:
        os.environ['QT_QPA_PLATFORM'] = _plat
    else:
        os.environ.pop('QT_QPA_PLATFORM', None)
    app = QApplication.instance() or QApplication(sys.argv)   # 必须持引用，否则被 GC → 原生崩溃
    base = tempfile.mkdtemp(prefix='cv_gui_')
    src = os.path.join(base, '书库')
    os.makedirs(os.path.join(src, '子', '孙'), exist_ok=True)
    for n in ('甲书.pdf', '甲书_【繁转简】.txt', '乙书.epub'):
        open(os.path.join(src, n), 'wb').write(b'x' * 64)
    open(os.path.join(src, '子', '孙', '丙书.txt'), 'wb').write(b'y' * 64)
    db = os.path.join(base, 'idx.db')
    r = C.build([src], db)
    ok(r['files'] == 4, '建库 4 个文件 → %d' % r['files'])
    st = C.load_settings()
    st.update({'primary_db': db, 'roots': [src]})
    w = MainWindow(st)
    ok(w.tb.columnCount() == 3, '主窗口构建：列表 3 列')
    _hd = [w.tb.horizontalHeaderItem(i).text() for i in range(w.tb.columnCount())]
    ok(_hd == ['序号', '文件名', '上级文件夹'], '列表表头：%s' % _hd)
    w.ed_kw.setText('甲书')
    w.do_search()
    ok(w.tb.rowCount() >= 1 and len(C.search(db, '甲书')) >= 2,
       '界面搜索「甲书」→ %d 行（原始 %d 条）' % (w.tb.rowCount(), len(C.search(db, '甲书'))))
    w.tb.setCurrentCell(0, 0)
    w.on_pick()
    ok('甲书' in w.lb_info.text(), '选中行显示详情')
    w._show_text_file(os.path.join(src, '甲书_【繁转简】.txt'))   # 直接走文本读取通路
    ok('x' * 10 in w.view.toPlainText(), '文本预览能读出内容')
    wz = Wizard(None, st, first_run=True)
    ok(wz.lst.count() >= 1 and wz.stack.count() == 3, '向导：目录列表 + 3 页')
    ok(hasattr(wz, 'rb_new') and hasattr(wz, 'rb_use'), '向导：自建 / 用已有 两种模式')
    wz.close()
    w.close()
    shutil.rmtree(base, ignore_errors=True)
    txt = '\n'.join(log) + '\nresult = %s\n' % ('OK' if all(l.startswith('OK') for l in log) else 'FAIL')
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    print('%s %s' % (APP_TITLE, APP_VERSION))
    print(txt)
    try:
        open(os.path.join(C.app_dir(), '_selftest_gui.txt'), 'w', encoding='utf-8').write(txt)
    except Exception:
        pass


def main():
    os.environ.setdefault('QT_QPA_PLATFORM', os.environ.get('QT_QPA_PLATFORM', ''))
    if '--fts-worker' in sys.argv:
        try:
            i = sys.argv.index('--fts-worker')
            job = sys.argv[i + 1]
        except Exception:
            return 2
        try:
            return fts_run(job)
        except Exception:
            return 3
    app = QApplication(sys.argv)
    st = C.load_settings()
    win = MainWindow(st)
    win.show()
    if not os.path.isfile(st.get('primary_db') or ''):
        wz = Wizard(win, st, first_run=True)
        if wz.exec() and wz.result_info:
            if wz.result_info.get('used_existing'):
                win.db = wz.result_info['db']
                win._refresh_status()
            else:
                win.st = wz.result_info.get('settings', st)
                win.db = win.st.get('primary_db', win.db)
                win._refresh_status()
    try:
        if win._restore_layout():        # batch9：恢复上次布局；上次拆窗则继续拆
            win.start_two_window_mode()
    except Exception:
        pass
    sys.exit(app.exec())


def selftest2():
    """稳当版自检：每步先落盘（offscreen 下旧自检会原生死锁，故另起一套）。"""
    import shutil
    import tempfile
    log = []
    REP = os.path.join(C.app_dir(), '_selftest_gui.txt')

    def ok(c, m):
        log.append(('OK  ' if c else 'FAIL') + ' ' + m)
        try:
            with open(REP, 'w', encoding='utf-8') as f:
                f.write('\n'.join(log) + '\n')
        except Exception:
            pass
        return bool(c)

    _plat = os.environ.get('CV_PLATFORM')
    if _plat is None:
        _plat = '' if sys.platform.startswith('win') else 'offscreen'
    if _plat:
        os.environ['QT_QPA_PLATFORM'] = _plat
    else:
        os.environ.pop('QT_QPA_PLATFORM', None)
    from PyQt6.QtWidgets import QApplication
    # app 必须立即持引用（QApplication(app) 的返回值被丢弃 → Python 包装对象被 GC → 原生死锁）
    app = QApplication.instance() or QApplication(sys.argv)
    base = tempfile.mkdtemp(prefix='cv2_')
    src = os.path.join(base, '书库')
    os.makedirs(os.path.join(src, '子', '孙'), exist_ok=True)
    for n in ('甲书.pdf', '甲书_【繁转简】.txt', '乙书.epub'):
        open(os.path.join(src, n), 'wb').write(b'x' * 64)
    open(os.path.join(src, '子', '孙', '丙书.txt'), 'wb').write(b'y' * 64)
    db = os.path.join(base, 'idx.db')
    r = C.build([src], db)
    ok(r['files'] == 4, '建库 4 个文件 → %d' % r['files'])
    C.save_settings({'primary_db': db, 'roots': [src]})
    st = C.load_settings()
    w = MainWindow(st)
    ok(True, '主窗口')
    w.ed_kw.setText('甲书')
    w.do_search()
    ok(len(w.rows) >= 1 and len(C.search(db, '甲书')) >= 2,
       '搜索「甲书」→ %d 行（原始 %d 条）' % (len(w.rows), len(C.search(db, '甲书'))))
    ti = next((i for i, r in enumerate(w.rows)
               if (r.get('name') or '').lower().endswith('.txt')), 0)
    w.tb.setCurrentCell(ti, 0)      # 挑 txt：假 PDF 会让 PyMuPDF 直接 abort
    w.on_pick()
    ok(bool(getattr(w, 'meta', None)), '元数据面板')
    ok(w.cb_ver.count() >= 1, '版本下拉 %d 项' % w.cb_ver.count())
    w.copy_cite()
    ok(bool(QApplication.clipboard().text()), '复制引用')
    w.cb_theme.setCurrentIndex(2)
    w.sp_font.setValue(16)
    w.apply_theme()
    ok(True, '主题/字号')
    w.preview_here()
    ok(len(w.view.toPlainText()) > 0, '预览')
    wz = Wizard(w, st)
    ok(wz.stack.count() == 3, '向导 %d 页' % wz.stack.count())
    wz.close()
    w.close()
    shutil.rmtree(base, ignore_errors=True)
    good = all(x.startswith('OK') for x in log)
    ok(good, 'result')
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    print('%s %s' % (APP_TITLE, APP_VERSION))
    print('\n'.join(log))
    print('result = %s' % ('OK' if good else 'FAIL'))
    sys.exit(0 if good else 1)


if __name__ == '__main__':
    if '--selftest2' in sys.argv:
        selftest2()
    elif '--selftest' in sys.argv:
        selftest()
    else:
        main()
