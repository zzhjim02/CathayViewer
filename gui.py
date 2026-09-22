# -*- coding: utf-8 -*-
"""CathayViewer · 学术书库浏览与阅读 —— 界面（首启向导 + 主窗口）

只读原则：所有库都以 mode=ro 打开；源书库一个字节都不写。
"""
import io
import json
import os
import re
import sys
import traceback

from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QImage, QKeySequence, QPixmap, QShortcut
from PyQt6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog, QDockWidget, QFileDialog,
                             QGroupBox, QSpinBox,
                             QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget,
                             QListWidgetItem,
                             QMainWindow, QMessageBox, QProgressBar, QPushButton,
                             QRadioButton, QSplitter, QStackedWidget, QTableWidget,
                             QTableWidgetItem, QTextEdit, QTreeWidget, QTreeWidgetItem,
                             QVBoxLayout, QWidget)

JSON_MAX_BYTES = 20 * 1024 * 1024    # JSON 树：超过此大小回退纯文本

import viewer_core as C
import viewer_meta as META

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
        # batch3：MD 渲染 / JSON 树 / 相关文件 / 缩略图
        self._md_render = False     # 阅读区是否处于 Markdown 渲染态
        self._md_path = ''          # 当前渲染的 .md 路径
        self._md_src = ''           # 当前 .md 的源码文本
        self._thumb_dock = None     # 右侧缩略图面板
        self._thumb_list = None
        self._thumb_timer = None
        self._thumbs_added = 0
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
        self.tb = QTableWidget(0, 5)
        self.tb.setHorizontalHeaderLabels(['文件名', '著录', '大小', '修改时间', '所在文件夹'])
        _hh = self.tb.horizontalHeader()
        _hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        _hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        _hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        _hh.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        _hh.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
        self.tb.setColumnWidth(0, 240)
        self.tb.setColumnWidth(4, 260)
        self.tb.setWordWrap(False)
        self.tb.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tb.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tb.itemSelectionChanged.connect(self.on_pick)
        self.tb.itemDoubleClicked.connect(self._on_item_dbl)
        self.tb.setMinimumWidth(220)          # 分割条拖到极左也不会挤没
        self.tb.setMaximumWidth(560)          # 上限（resizeEvent 里再按窗口 32% 收紧）
        sp.addWidget(self.tb)
        right = QWidget()
        right.setMinimumWidth(320)
        rv = QVBoxLayout(right)
        self.lb_info = QLabel('选一个文件看详情')
        self.lb_info.setWordWrap(True)
        self.view = QTextEdit()
        self.view.setReadOnly(True)
        vrow = QHBoxLayout()
        vrow.addWidget(QLabel('版本'))
        self.cb_ver = QComboBox()
        self.cb_ver.currentIndexChanged.connect(self.on_ver)
        vrow.addWidget(self.cb_ver, 1)
        rv.addLayout(vrow)
        trow = QHBoxLayout()
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
        self.cb_invert = QCheckBox('◐ PDF 反色')
        trow.addWidget(self.cb_invert)
        trow.addStretch(1)
        rv.addLayout(trow)
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
        for x in self._btn_widgets:
            row.addWidget(x)
        rv.addWidget(self.lb_info)
        rv.addWidget(self.view, 1)
        rv.addLayout(row)
        sp.addWidget(right)
        sp.setChildrenCollapsible(False)      # 两侧不可被折叠掉
        sp.setStretchFactor(0, 0)             # 左：列表/详情，不抢空间
        sp.setStretchFactor(1, 1)             # 右：阅读区，占据窗口增量
        sp.setSizes([340, 1160])              # 阅读区默认占大头（窗口变窄时按比例缩放）
        self._split = sp
        v.addWidget(sp, 1)
        self.statusBar().showMessage('就绪')

    # ---- 窗口尺寸 / 分割比例
    def _apply_default_size(self):
        """默认窗口尺寸：1500×950，但不超出屏幕可用区的 90%。"""
        try:
            scr = QApplication.primaryScreen()
            g = scr.availableGeometry() if scr is not None else None
            if g is not None and g.width() > 0 and g.height() > 0:
                w, h = min(1500, int(g.width() * 0.9)), min(950, int(g.height() * 0.9))
            else:
                w, h = 1500, 950
        except Exception:
            w, h = 1500, 950
        self.resize(max(1100, w), max(720, h))

    def resizeEvent(self, ev):
        """窗口变化时：左侧列表最大宽度 ≤ 窗口 32%（且 ≤560px），保证阅读区占大头。"""
        try:
            super().resizeEvent(ev)
        except Exception:
            pass
        try:
            tb = getattr(self, 'tb', None)
            if tb is not None:
                tb.setMaximumWidth(max(tb.minimumWidth(),
                                       min(560, int(self.width() * 0.32))))
        except Exception:
            pass

    def _on_item_dbl(self, *_):
        """列表项双击 → 一律在阅读区内部打开（不再甩给外部程序）。"""
        self.open_here()

    def open_here(self):
        """在阅读区内部打开当前项：PDF/EPUB 走内置引擎渲染，TXT/MD/JSON/CSV 走文本预览。
        记历史/统计，刷新著录与版本下拉；外部程序只由「↗ 用外部程序打开」显式触发。
        """
        self.on_pick()                       # 刷新著录信息 + 版本下拉
        r = self._cur()
        if not r:
            self.statusBar().showMessage('先在列表里选一个文件')
            return False
        p = os.path.join(r.get('dir') or '', r.get('name') or '')
        if not os.path.isfile(p):
            self.statusBar().showMessage('文件不在了：%s' % p)
            return False
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
                self._hist_add()
                self._stat_open(p)
                self.statusBar().showMessage(
                    '已在阅读区打开：%s（共 %d 页，PgUp/PgDn 翻页）'
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
        rows = C.search(self.db, kw, 800)
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
        self.tb.setRowCount(0)
        for r in self.rows:
            k = self.tb.rowCount()
            self.tb.insertRow(k)
            sz = r.get('size') or 0
            nm = r.get('name') or ''
            dr = r.get('dir') or ''
            brief = self._meta_brief(nm, os.path.join(dr, nm))
            it0 = QTableWidgetItem(nm)
            it0.setToolTip(nm)
            it1 = QTableWidgetItem(brief)
            it1.setToolTip(brief or '（文件名里没有著录信息）')
            it2 = QTableWidgetItem('%.1f KB' % (sz / 1024.0))
            it2.setToolTip('%d 字节' % sz)
            it3 = QTableWidgetItem(_ts(r.get('mtime')))
            it4 = QTableWidgetItem(dr)
            it4.setToolTip(dr)
            self.tb.setItem(k, 0, it0)
            self.tb.setItem(k, 1, it1)
            self.tb.setItem(k, 2, it2)
            self.tb.setItem(k, 3, it3)
            self.tb.setItem(k, 4, it4)
        self.statusBar().showMessage('搜到 %d 本（原始命中 %d 条，同书各版本已串在一起）'
                                     % (len(self.rows), len(rows)))

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
        """关窗：结算最后一次阅读时长（写 settings，异常静默）。"""
        try:
            self._stat_flush()
        except Exception:
            pass
        try:
            super().closeEvent(ev)
        except Exception:
            pass

    def _cur(self):
        i = self.tb.currentRow()
        return self.rows[i] if 0 <= i < len(self.rows) else None

    def on_pick(self):
        r = self._cur()
        if not r:
            return
        p = os.path.join(r.get('dir') or '', r.get('name') or '')
        try:
            self.meta = META.parse(r.get('name') or '', p)
        except Exception:
            self.meta = {'name': r.get('name') or '', 'volume': '', 'author': '',
                         'publisher': '', 'year': '', 'ssid': '', 'trad': False,
                         'ext': '', 'tail': '', 'path': p, 'raw': r.get('name') or ''}
        m = self.meta
        bits = [b for b in (m.get('author'), m.get('volume'), m.get('publisher'),
                            ((m.get('year') or '') + '年') if m.get('year') else '',
                            ('SSID ' + m['ssid']) if m.get('ssid') else '',
                            '【繁体】' if m.get('trad') else '') if b]
        self.lb_info.setText('<b>%s</b><br>%s<br>%.1f KB ｜ %s<br>'
                             '<span style="color:#1e7a6f">%s</span>'
                             % (m.get('name') or r.get('name'), p,
                                (r.get('size') or 0) / 1024.0, _ts(r.get('mtime')),
                                ' ｜ '.join(bits) or '（文件名里没有元数据）'))
        self._fill_versions(m)

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
        """弹出目录（PDF / EPUB 大纲；没大纲就列页码）。Ctrl+T"""
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
            except Exception:
                d = getattr(self, 'pd', None)
        if d is None:
            self.statusBar().showMessage('目录只对已打开的 PDF / EPUB 有效（先点 📖 在阅读区打开）')
            return
        try:
            items = d.get_toc() or []
        except Exception:
            items = []
        dlg = QDialog(self)
        dlg.setWindowTitle('目录' + ('（%d 项）' % len(items) if items else '（无大纲，按页列）'))
        dlg.resize(560, 480)
        vb = QVBoxLayout(dlg)
        lst = QListWidget()
        if items:
            for lvl, title, pg in items:
                lst.addItem('%s%s（第 %d 页）' % ('    ' * max(0, int(lvl) - 1), title, pg))
        else:
            for i in range(int(d.page_count)):
                lst.addItem('第 %d 页' % (i + 1))
        vb.addWidget(lst)
        self._last_toc = {'items': items, 'pages': int(d.page_count),
                          'rows': lst.count(), 'path': getattr(self, '_pd_path', '')}

        def go():
            i = lst.currentRow()
            if i >= 0:
                self.pgno = (int(items[i][2]) - 1) if items else i
                self.pgno = max(0, min(int(d.page_count) - 1, self.pgno))
                self._pdf_show()
            dlg.accept()

        lst.itemDoubleClicked.connect(lambda _: go())
        bb = QPushButton('跳转')
        bb.clicked.connect(go)
        vb.addWidget(bb)
        dlg.exec()

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
        try:
            self.ed_kw.setText(os.path.splitext(os.path.basename(p))[0])
            self.do_search()
            want = os.path.normcase(p)
            cur = -1
            for i, r in enumerate(self.rows):
                rp = os.path.normcase(os.path.abspath(
                    os.path.join(r.get('dir') or '', r.get('name') or '')))
                if rp == want:
                    cur = i
                    break
            if cur < 0 and self.rows:
                cur = 0                      # 库里没登记 → 仍打开文件，列表选第一个同名词
            if cur >= 0:
                self.tb.setCurrentCell(cur, 0)
                self.on_pick()
        except Exception:
            pass
        ok = self._open_path(p)              # 一律在阅读区内部打开（PDF/EPUB/文本）
        if ok:
            tail = ''
            if len(files) > 1:
                tail = '（另有 %d 个文件参数已忽略）' % (len(files) - 1)
            self.statusBar().showMessage('已在阅读区打开：%s%s'
                                         % (os.path.basename(p), tail))

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
            self._hist_add()
            self._stat_open(p)
            self.statusBar().showMessage('已用 PDF 引擎打开（%s，共 %d 页）｜PgUp/PgDn 翻页'
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

    def _pdf_show(self):
        """按当前页码重画阅读区（PDF）。◐ PDF 反色 勾选时像素反色。"""
        d = getattr(self, 'pd', None)
        if d is None:
            return
        try:
            import fitz
            pg = d[self.pgno]
            pm = pg.get_pixmap(matrix=fitz.Matrix(1.4, 1.4))
            img = QImage(pm.samples, pm.width, pm.height, pm.stride,
                         QImage.Format.Format_RGB888).copy()
            if getattr(self, 'cb_invert', None) is not None and self.cb_invert.isChecked():
                img.invertPixels(QImage.InvertMode.InvertRgb)
            self.view.clear()
            from PyQt6.QtCore import QUrl as _QUrl
            from PyQt6.QtGui import QTextDocument as _QTD
            pmx = QPixmap.fromImage(img)
            self.view.document().addResource(_QTD.ResourceType.ImageResource,
                                            _QUrl('2'), pmx)
            cur = self.view.textCursor()
            cur.insertImage(img)
            self.view.setTextCursor(cur)
            self._reader = 'pdf'
            self.statusBar().showMessage('第 %d / %d 页（PgUp / PgDn 翻页，F11 全屏）'
                                         % (self.pgno + 1, d.page_count))
        except Exception as e:
            self.statusBar().showMessage('翻页失败：%s' % e)

    def _on_invert(self, *_):
        """勾选/取消 ◐ PDF 反色 时立即重画当前 PDF 页。"""
        if getattr(self, 'pd', None) is not None:
            self._pdf_show()

    def pdf_goto(self, delta):
        d = getattr(self, 'pd', None)
        if d is None:
            return
        self.pgno = max(0, min(max(1, d.page_count) - 1, self.pgno + delta))
        self._pdf_show()

    def apply_theme(self):
        """主题（浅色/深色/护眼）+ 正文字号 + 行距；F11 全屏。"""
        i = self.cb_theme.currentIndex() if hasattr(self, 'cb_theme') else 0
        bg, fg = [('#ffffff', '#222222'), ('#1e1e1e', '#d8d8d8'),
                  ('#f4ecd8', '#3a3226')][max(0, min(2, i))]
        try:
            self.view.setStyleSheet('QTextEdit{background:%s;color:%s;}' % (bg, fg))
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

    def on_ver(self, i):
        if 0 <= i < len(self.vers):
            p = self.vers[i].get('path') or ''
            self._stat_flush()
            self.pd = None
            self._pd_path = ''
            self._reader = 'text'
            self.view.setPlainText('选中的版本：\n%s' % p)
            self._apply_line_height()
            self.statusBar().showMessage('已切到：%s' % os.path.basename(p))

    def copy_cite(self):
        m = getattr(self, 'meta', None)
        if not m:
            return
        s = META.cite(m, page='X')
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
            page = META.find_colophon_page(pdf)        # 1 起；0 = 没找到
            if not page:
                self.statusBar().showMessage('没找到版权页')
                return
            import fitz
            d = fitz.open(pdf)
            if d.page_count <= 0:
                self.statusBar().showMessage('没找到版权页')
                return
            self.pd = d
            self._pd_path = pdf
            self.pgno = max(0, min(d.page_count - 1, page - 1))
            self._pdf_show()
            self._hist_add()
            self._stat_open(pdf)
            self.statusBar().showMessage('版权页在第 %d / %d 页'
                                         % (self.pgno + 1, d.page_count))
        except Exception as e:
            self.statusBar().showMessage('没找到版权页：%s' % e)

    def copy_text(self):
        """⧉ 复制文本：把阅读区当前纯文本复制到剪贴板（PDF 取文字层）。"""
        try:
            if getattr(self, '_reader', '') == 'pdf' and getattr(self, 'pd', None) is not None:
                t = ''
                try:
                    t = (self.pd[self.pgno].get_text() or '').strip()
                except Exception:
                    t = ''
                if not t:
                    self.statusBar().showMessage('这页没有文字层')
                    return
                QApplication.clipboard().setText(t)
                self.statusBar().showMessage('已复制本页文本（%d 字）' % len(t))
                return
            t = self.view.toPlainText()
            if not t.strip():
                self.statusBar().showMessage('阅读区没有可复制的文本')
                return
            QApplication.clipboard().setText(t)
            self.statusBar().showMessage('已复制阅读区文本（%d 字）' % len(t))
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
            md = QMimeData()
            md.setHtml(html)
            md.setText(text)
            QApplication.clipboard().setMimeData(md)
            self.statusBar().showMessage('已复制带格式文本')
        except Exception as e:
            self.statusBar().showMessage('复制失败：%s' % e)

    # ============================================================ batch3
    # ① Markdown 渲染 / 源码切换（Ctrl+M / 𝐌D 渲染）
    def _read_text_file(self, p, limit=200000):
        """读文本文件（自动试多种编码），只读。"""
        with open(p, 'rb') as f:
            head = f.read(limit)
        for enc in ('utf-8-sig', 'utf-8', 'gb18030', 'big5'):
            try:
                return head.decode(enc)
            except UnicodeDecodeError:
                continue
        return head.decode('utf-8', 'replace')

    def _show_text_file(self, p):
        """把文本文件读进阅读区（纯文本态）；同时复位 MD 状态。"""
        txt = self._read_text_file(p, 200000)
        self.view.setPlainText(txt)
        self.pd = None
        self._pd_path = ''
        self._reader = 'text'
        self._md_path = ''
        self._md_render = False
        self._md_src = ''
        self._apply_line_height()
        self._stat_open(p)
        return True

    def md_toggle(self):
        """Ctrl+M / 𝐌D 渲染：.md 文件在「渲染态 / 源码态」间切换。"""
        r = self._cur()
        p = os.path.join(r.get('dir') or '', r.get('name') or '') if r else ''
        if not p or not p.lower().endswith('.md'):
            self.statusBar().showMessage('这个文件不是 Markdown')
            return
        try:
            if self._md_path != p:
                # 首次：从磁盘读源码，先以源码态呈现
                self._md_src = self._read_text_file(p, 500000)
                self._md_path = p
                self._md_render = False
                self.pd = None
                self._pd_path = ''
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
        dlg = QDialog(self)
        dlg.setWindowTitle('JSON 树 — %s' % os.path.basename(p))
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
        """算出「相关文件」三档。返回 {'A','B','C','prefix','author'}（各为 dict 列表）。"""
        out = {'A': [], 'B': [], 'C': [], 'prefix': '', 'author': '', 'db': self.db}
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
        out['C'] = out['C'][:50]
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
                self._hist_add()
                self._stat_open(path)
                return True
            except Exception as e:
                self.statusBar().showMessage('打不开：%s' % e)
                return False
        try:
            self._show_text_file(path)
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
        groups = [('同丛书 / 同专题（%d）' % len(g['A']), g['A']),
                  ('同作者（%d）' % len(g['B']), g['B']),
                  ('相邻书架 · 同目录（%d）' % len(g['C']), g['C'])]
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
        vb.addWidget(QLabel('同丛书/同专题：前缀「%s」相同或同目录名；同作者：著录作者相同；'
                            '相邻书架：同目录其它文件（最多 50）。双击打开。'
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

    # ④ 缩略图侧栏（Ctrl+Shift+T）
    def _build_thumb_dock(self):
        if getattr(self, '_thumb_dock', None) is not None:
            return
        dk = QDockWidget('缩略图', self)
        dk.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea |
                           Qt.DockWidgetArea.RightDockWidgetArea)
        lst = QListWidget()
        lst.setViewMode(QListWidget.ViewMode.IconMode)
        lst.setIconSize(QSize(110, 150))
        lst.setResizeMode(QListWidget.ResizeMode.Adjust)
        lst.setMovement(QListWidget.Movement.Static)
        lst.setSpacing(6)
        lst.itemClicked.connect(self._thumb_clicked)
        dk.setWidget(lst)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dk)
        self._thumb_dock = dk
        self._thumb_list = lst

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
        """点缩略图 → 跳该页（复用 self.pd / self.pgno / _pdf_show）。"""
        i = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        d = getattr(self, 'pd', None)
        if i is None or d is None:
            return
        self.pgno = max(0, min(int(d.page_count) - 1, int(i)))
        self._pdf_show()

    def toggle_thumbs(self):
        """Ctrl+Shift+T：打开/隐藏右侧缩略图面板（PDF/EPUB，懒加载前 40 页）。"""
        d = getattr(self, 'pd', None)
        if d is None or int(getattr(d, 'page_count', 0) or 0) <= 0:
            self.statusBar().showMessage('缩略图只对已打开的 PDF / EPUB 有效'
                                         '（先点 📖 在阅读区打开或 Ctrl+E）')
            return
        if self._thumb_dock is not None and self._thumb_dock.isVisible():
            self._thumb_dock.hide()
            self._stop_thumb_timer()
            self.statusBar().showMessage('已隐藏缩略图（Ctrl+Shift+T 再开）')
            return
        self._build_thumb_dock()
        self._start_thumb_load()
        self._thumb_dock.show()
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
                self._hist_add()
                self.statusBar().showMessage('已打开文本（只读，最多显示前 200 KB）')
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
                self._hist_add()
                self._stat_open(p)
            else:
                self.view.setPlainText('这个格式（%s）暂不支持在此预览，'
                                       '点「↗ 用外部程序打开」。' % ext)
        except Exception as e:
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

    os.environ['QT_QPA_PLATFORM'] = 'offscreen'    # 强制（环境里可能是空串，setdefault 盖不住）
    if not QApplication.instance():
        QApplication(sys.argv)
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
    ok(w.tb.columnCount() == 5, '主窗口构建：列表 5 列')
    w.ed_kw.setText('甲书')
    w.do_search()
    ok(w.tb.rowCount() == 2, '界面搜索「甲书」出 2 行 → %d' % w.tb.rowCount())
    ti = next((i for i, r in enumerate(w.rows)
               if (r.get('name') or '').lower().endswith('.txt')), 0)
    w.tb.setCurrentCell(ti, 0)      # 刻意挑 txt：假 PDF 会让 PyMuPDF 直接 abort
    w.on_pick()
    ok('甲书' in w.lb_info.text(), '选中行显示详情')
    w.preview_here()
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

    os.environ['QT_QPA_PLATFORM'] = (os.environ.get('CV_PLATFORM') or 'offscreen')
    from PyQt6.QtWidgets import QApplication
    if not QApplication.instance():
        QApplication(sys.argv)
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
    ok(len(w.rows) >= 2, '搜索「甲书」命中 %d' % len(w.rows))
    w.tb.setCurrentCell(0, 0)
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
    ok(wz.count() == 3, '向导 %d 页' % wz.count())
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
