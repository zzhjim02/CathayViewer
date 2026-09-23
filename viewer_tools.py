# -*- coding: utf-8 -*-
"""CathayViewer · 学术书库浏览与阅读 —— 记录与工具层  v0.1.0

本模块只做「纯逻辑」，不依赖 PyQt：
  * 截图本 / 摘录本：写到「系统文档\\Cathay文档记录」下，绝不碰源书库；
  * 对读页码索引（SyncIndex）：解析 TXT 里的页码标记（移植自 CathayReader）；
  * 目录（PDF 标签页）里找「版权页」；
  * 相关文献推荐：同丛书 / 同专题 / 同一本书的其他书 / 同一作者的其他著作；
  * 跨文件全文检索历史（增删去重）。

硬约束：源书库一个字节都不写。所有写入都落在用户「文档」下自己的记录目录。
"""
import ctypes
import os
import re
from ctypes import wintypes

import viewer_meta as META

# 测试/自定义用：指到别处（None = 用系统「文档」）
_DOCS_ROOT = None

# ----------------------------------------------------------------- 系统文档目录
# FOLDERID_Documents = {FDD39AD0-238F-46AF-ADB4-6C85480369C7}
class _GUID(ctypes.Structure):
    _fields_ = [('Data1', wintypes.DWORD), ('Data2', wintypes.WORD),
                ('Data3', wintypes.WORD), ('Data4', ctypes.c_byte * 8)]


def _known_documents():
    """用已知文件夹 API 拿「文档」（可能被重定向到 OneDrive）；失败返回 ''。"""
    try:
        g = _GUID(0xFDD39AD0, 0x238F, 0x46AF,
                  (ctypes.c_byte * 8)(0xAD, 0xB4, 0x6C, 0x85, 0x48, 0x03, 0x69, 0xC7))
        ptr = ctypes.c_wchar_p()
        r = ctypes.windll.shell32.SHGetKnownFolderPath(
            ctypes.byref(g), 0, None, ctypes.byref(ptr))
        if r == 0 and ptr.value:
            p = ptr.value
            try:
                ctypes.windll.ole32.CoTaskMemFree(ptr)
            except Exception:
                pass
            return p
    except Exception:
        pass
    return ''


def documents_dir():
    p = _known_documents()
    if p and os.path.isdir(p):
        return p
    return os.path.join(os.path.expanduser('~'), 'Documents')


def docs_root():
    """记录根目录：<文档>\\Cathay文档记录（可被 _DOCS_ROOT / 环境变量覆盖）。"""
    if _DOCS_ROOT:
        return _DOCS_ROOT
    env = os.environ.get('CATHAY_DOCS_DIR')
    if env:
        return env
    return os.path.join(documents_dir(), 'Cathay文档记录')


def record_dir(kind):
    """记录本目录（截图本 / 摘录本），不存在就建。"""
    d = os.path.join(docs_root(), kind)
    os.makedirs(d, exist_ok=True)
    return d


_SNAPSHOT_DIR = '截图本'
_EXCERPT_DIR = '摘录本'


# ----------------------------------------------------------------- 出处信息
def _safe_name(s, default='未命名'):
    s = re.sub(r'[\\/:*?"<>|\r\n\t]+', '_', str(s or '')).strip(' ._')
    s = re.sub(r'\s+', ' ', s)
    return (s or default)[:80]


def _version_label(meta, src_path):
    """版本描述：PDF原本 / 繁体TXT / 繁转简TXT / 其它。"""
    ext = os.path.splitext(src_path or '')[1].lower()
    if ext == '.pdf':
        return 'PDF原本'
    if ext in ('.txt', '.text'):
        if '繁转简' in os.path.basename(src_path or ''):
            return '繁转简TXT'
        if meta.get('trad'):
            return '繁体TXT'
        return 'TXT文本'
    return (ext.lstrip('.') or '文本').upper()


def source_info(meta, page, src_path):
    """出处信息 dict + 单行文本。"""
    meta = meta or {}
    name = meta.get('name') or os.path.splitext(os.path.basename(src_path or ''))[0] or '未命名'
    vol = meta.get('volume') or ''
    pub = meta.get('publisher') or ''
    year = meta.get('year') or ''
    author = meta.get('author') or ''
    version = meta.get('version_label') or _version_label(meta, src_path)
    try:
        pg = int(page)
        pg_txt = '第%d页' % pg if pg > 0 else '页码未定'
    except Exception:
        pg_txt = '页码未定'
    bits = ['《%s》' % name]
    if vol:
        bits.append(vol)
    bits.append(pg_txt)
    line = ''.join(bits)
    tail = []
    if author:
        tail.append(author)
    if version:
        tail.append('版本：%s' % version)
    if pub or year:
        tail.append('%s%s' % (pub, ('·%s年' % year) if year else ''))
    if src_path:
        tail.append('文件：%s' % os.path.basename(src_path))
    return {'book': name, 'volume': vol, 'page': pg_txt, 'version': version,
            'author': author, 'publisher': pub, 'year': year, 'file': src_path,
            'headline': line, 'detail': '｜'.join(tail)}


# ----------------------------------------------------------------- 摘录本
def excerpt_target():
    d = record_dir(_EXCERPT_DIR)
    return os.path.join(d, '摘录本.md')


def add_excerpt(meta, text, page, src_path, ts=None):
    """把一段选中文字追加到「摘录本」。返回记录 dict（含写入路径）。

    text: 选中的正文；page: 页码（int 或 ''）；src_path: 出处文件。
    正文与出处写成可读的 Markdown 块。
    """
    text = (text or '').strip()
    if not text:
        return None
    if ts is None:
        import time as _t
        ts = _t.strftime('%Y-%m-%d %H:%M:%S')
    info = source_info(meta, page, src_path)
    path = excerpt_target()
    quoted = '\n'.join('> ' + ln for ln in text.splitlines())
    block = ('\n### 摘录 · %s\n%s\n>\n> —— %s\n> %s\n'
             % (ts, quoted, info['headline'], info['detail']))
    try:
        head = ''
        if not os.path.isfile(path):
            head = '# 摘录本\n\n> 本文件由 CathayViewer 自动维护（每条摘录附带出处）。\n'
        with open(path, 'a', encoding='utf-8') as f:
            f.write(head + block)
    except Exception as e:
        return {'error': str(e), 'path': path}
    return {'path': path, 'dir': os.path.dirname(path), 'ts': ts,
            'chars': len(text), 'info': info}


# ----------------------------------------------------------------- 摘录本：读取 / 编辑
_EXC_HEAD = '# 摘录本\n\n> 本文件由 CathayViewer 自动维护（每条摘录附带出处）。\n'
_EXC_SPLIT = re.compile(r'(?m)^###\s*摘录\s*·\s*')


def parse_excerpts(text=None, path=None):
    """把「摘录本.md」解析成记录列表 [{ts, body, cite}]，供查看/编辑。"""
    if text is None:
        text = _read_text(path or excerpt_target())
    text = text or ''
    recs = []
    for blk in _EXC_SPLIT.split(text)[1:]:
        lines = blk.split('\n')
        ts = (lines[0] or '').strip()
        body, cite, sep = [], [], False
        for ln in lines[1:]:
            if not sep:
                if ln.strip() == '>':
                    sep = True
                    continue
                if ln.startswith('> '):
                    body.append(ln[2:])
                elif ln.startswith('>'):
                    body.append(ln[1:])
                elif ln.strip() == '':
                    continue
                else:
                    body.append(ln)
            else:
                if ln.startswith('> '):
                    cite.append(ln[2:])
                elif ln.startswith('>'):
                    cite.append(ln[1:])
                elif ln.strip() == '':
                    continue
                else:
                    cite.append(ln)
        while body and not body[-1].strip():
            body.pop()
        while cite and not cite[-1].strip():
            cite.pop()
        if not body and not cite:
            continue
        recs.append({'ts': ts, 'body': '\n'.join(body).strip('\n'),
                     'cite': '\n'.join(cite).strip('\n')})
    return recs


def build_excerpts(records):
    """把记录列表写回「摘录本.md」文本（与 add_excerpt 同一格式）。"""
    buf = [_EXC_HEAD]
    for r in (records or []):
        ts = (r.get('ts') or '').strip()
        body = (r.get('body') or '').rstrip('\n')
        cite = (r.get('cite') or '').rstrip('\n')
        if not (body or cite):
            continue
        quoted = '\n'.join('> ' + ln if ln.strip() else '>' for ln in body.splitlines())
        clines = '\n'.join('> ' + ln if ln.strip() else '>' for ln in cite.splitlines())
        buf.append('\n### 摘录 · %s\n%s\n>\n%s\n' % (ts, quoted, clines))
    return ''.join(buf)


def read_excerpts():
    """读取「摘录本」（返回记录列表）。"""
    return parse_excerpts(path=excerpt_target())


def write_excerpts(records):
    """整体重写「摘录本」（先写临时文件再原子替换）。返回写入路径。"""
    p = excerpt_target()
    tmp = p + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(build_excerpts(records))
    os.replace(tmp, p)
    return p


def excerpt_target_path():
    return excerpt_target()


# ----------------------------------------------------------------- 截图本：清单
_IMG_EXT = ('.png', '.jpg', '.jpeg', '.bmp', '.webp')


def list_snapshots():
    """列出截图本目录里的图片（新在前）：[{name, path, mtime}]。"""
    d = record_dir(_SNAPSHOT_DIR)
    out = []
    try:
        for fn in os.listdir(d):
            if fn.lower().endswith(_IMG_EXT):
                p = os.path.join(d, fn)
                try:
                    mt = os.path.getmtime(p)
                except OSError:
                    mt = 0
                out.append({'name': fn, 'path': p, 'mtime': mt})
    except OSError:
        pass
    out.sort(key=lambda x: x['mtime'], reverse=True)
    return out


# ----------------------------------------------------------------- 截图本
def snapshot_target():
    return record_dir(_SNAPSHOT_DIR)


def add_snapshot(png_bytes, meta, page, src_path, ts=None, ext='png'):
    """保存一张截图 → 截图本目录，并把「图 + 出处」追加进截图本.md。返回记录 dict。

    png_bytes: 图片字节（Qt 侧用 QBuffer 导出 PNG/JPEG）。
    """
    if not png_bytes:
        return None
    if ts is None:
        import time as _t
        ts = _t.strftime('%Y-%m-%d %H:%M:%S')
    info = source_info(meta, page, src_path)
    d = snapshot_target()
    stamp = re.sub(r'[^0-9]', '', ts)[:14] or 'snap'
    pg = re.sub(r'[^0-9]', '', info['page']) or 'x'
    fn = '%s_第%s页_%s.%s' % (_safe_name(info['book']), pg, stamp, ext)
    fp = os.path.join(d, fn)
    if os.path.exists(fp):              # 同一秒内多次截图 → 自动加序号，不覆盖
        stem, ext2 = os.path.splitext(fn)
        k = 2
        while os.path.exists(os.path.join(d, '%s_%d%s' % (stem, k, ext2))):
            k += 1
        fn = '%s_%d%s' % (stem, k, ext2)
        fp = os.path.join(d, fn)
    try:
        with open(fp, 'wb') as f:
            f.write(png_bytes)
    except Exception as e:
        return {'error': str(e), 'path': fp}
    md = os.path.join(d, '截图本.md')
    rel = fn
    block = ('\n### %s · %s\n\n![%s](%s)\n\n> %s\n> 截图时间：%s\n'
             % (info['headline'], ts[:10], info['headline'], rel,
                info['detail'], ts))
    try:
        head = ''
        if not os.path.isfile(md):
            head = '# 截图本\n\n> 本文件由 CathayViewer 自动维护（每张截图附出处）。\n'
        with open(md, 'a', encoding='utf-8') as f:
            f.write(head + block)
    except Exception as e:
        return {'error': str(e), 'path': fp, 'png': fp}
    return {'png': fp, 'md': md, 'dir': d, 'name': fn, 'ts': ts, 'info': info}


# ----------------------------------------------------------------- 对读页码索引
#  移植自 CathayReader / page_parser.py：自动识别多种页码标记。
_PAGE_PATTERNS = [
    re.compile(r'≦\s*(\d+)\s*≧', re.MULTILINE),
    re.compile(r'(?:={6,}\s*\n\s*)?第\s*(\d+)\s*页(?:\s*\n\s*={6,})?', re.MULTILINE),
    re.compile(r'(?:-{6,}\s*\n\s*)?第\s*(\d+)\s*页(?:\s*\n\s*-{6,})?', re.MULTILINE),
]


def _read_text(path, limit=0):
    try:
        with open(path, 'rb') as f:
            raw = f.read(limit) if limit else f.read()
    except Exception:
        return ''
    b = raw
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


class SyncIndex(object):
    """TXT 页码索引：把 OCR 文本切成「页码 → 字符区间」，供 PDF/TXT 对读同步。"""

    def __init__(self, content='', path=''):
        self.content = ''
        self.pages = []          # [{'number','start','end'}, ...]
        self.pattern = None
        self._header_end = 0
        if path and not content:
            content = _read_text(path)
        if content:
            self.build(content)

    def build(self, content):
        content = (content or '').replace('\r\n', '\n').replace('\r', '\n')
        self.content = content
        self._detect_header()
        self._detect_pattern()
        self._parse_pages()
        return len(self.pages) > 0

    def _detect_header(self):
        lines = self.content.split('\n')
        end = 0
        for i, ln in enumerate(lines):
            s = ln.strip()
            if not s:
                continue
            if re.match(r'^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}', s):
                end = sum(len(x) + 1 for x in lines[:i + 1])
                continue
            if 'http' in s or '\\\\' in s:
                end = sum(len(x) + 1 for x in lines[:i + 1])
                continue
            break
        self._header_end = end

    def _detect_pattern(self):
        best, best_n = None, -1
        for pat in _PAGE_PATTERNS:
            n = len(list(pat.finditer(self.content)))
            if n > best_n:
                best_n, best = n, pat
        self.pattern = best if best_n >= 3 else None

    def _parse_pages(self):
        self.pages = []
        if not self.pattern:
            return self._fallback()
        ms = list(self.pattern.finditer(self.content))
        if len(ms) < 3:
            return self._fallback()
        for i, m in enumerate(ms):
            try:
                num = int(m.group(1))
            except (IndexError, ValueError):
                continue
            start = m.end()
            end = ms[i + 1].start() if i + 1 < len(ms) else len(self.content)
            self.pages.append({'number': num, 'start': start, 'end': end})
        self.pages = [p for p in self.pages if self.content[p['start']:p['end']].strip()]
        if not self.pages:
            self._fallback()

    def _fallback(self):
        self.pages = []
        cpp = 500
        pos = self._header_end
        num = 1
        while pos < len(self.content):
            end = min(pos + cpp, len(self.content))
            self.pages.append({'number': num, 'start': pos, 'end': end})
            pos, num = end, num + 1

    @property
    def page_count(self):
        return len(self.pages)

    def numbers(self):
        return [p['number'] for p in self.pages]

    def page_range(self, number):
        for p in self.pages:
            if p['number'] == number:
                return (p['start'], p['end'])
        return (0, 0)

    def page_at_position(self, pos):
        if not self.pages:
            return 0
        for p in self.pages:
            if p['start'] <= pos < p['end']:
                return p['number']
            if pos < p['start']:
                return p['number']
        return self.pages[-1]['number']

    def offset_for_page(self, number):
        """把「印刷页码」映射到字符偏移；没有该页则按比例就近。返回 (offset, 命中页码)。"""
        if not self.pages:
            return (0, 0)
        for p in self.pages:
            if p['number'] == number:
                return (p['start'], p['number'])
        nums = [p['number'] for p in self.pages]
        # 找最接近的页
        near = min(nums, key=lambda n: abs(n - number))
        for p in self.pages:
            if p['number'] == near:
                return (p['start'], near)
        return (self.pages[0]['start'], self.pages[0]['number'])


# ----------------------------------------------------------------- 版权页（目录优先）
_TOC_KW_STRONG = ('版权页', '版權頁')
_TOC_KW_WEAK = ('版权', '版權')


def find_colophon_in_toc(toc, strong=None, weak=None):
    """在 PDF 目录（标签页/书签）里找版权页页码（1 起；找不到返回 0）。

    先找强关键词（版权页/版權頁），再退回弱关键词（版权/版權），按目录顺序取第一个。
    """
    strong = strong or _TOC_KW_STRONG
    weak = weak or _TOC_KW_WEAK
    if not toc:
        return 0
    rows = []
    for item in toc:
        try:
            title = str(item[1] or '')
            page = int(item[2] or 0)
        except Exception:
            continue
        if page > 0:
            rows.append((title, page))
    for kws in (strong, weak):
        for title, page in rows:
            t = title.strip()
            if any(k in t for k in kws):
                return page
    return 0


# ----------------------------------------------------------------- 相关文献推荐
def series_prefix(name):
    """书名去卷册/括注后，取开头连续中文，作为「丛书/专题」前缀。"""
    try:
        s = META.book_core(name or '')
    except Exception:
        s = name or ''
    s = re.sub(r'[（(][^（）()]*[)）]', '', s)
    s = re.sub(r'第\s*[0-9一二三四五六七八九十百千]{1,4}\s*[册卷集部编篇辑期]', '', s)
    s = re.sub(r'全\s*[0-9一二三四五六七八九十]{1,3}\s*册', '', s)
    s = re.sub(r'[\s_\-—+·、.]+', ' ', s).strip(' _-—+·、.')
    m = re.match(r'[\u4e00-\u9fa5]{2,}', s)
    return (m.group(0) if m else s).strip()


def classify_related(cur, cands):
    """把候选书分成四档：同丛书 / 同专题 / 同一本书的其他书 / 同一作者的其他著作。

    cur:   {'name','dir','path','author'}
    cands: 同上结构（去掉当前书），各自已有解析好的 author（可空）。
    返回 {组名: [{'name','dir','path'}]}。
    """
    res = {'series': [], 'topic': [], 'same_book': [], 'same_author': []}
    ccur = cur or {}
    cpre = series_prefix(ccur.get('name') or '')
    cauth = ccur.get('author') or ''
    ccore = META.book_core(ccur.get('name') or '')
    cpath = ccur.get('path') or ''
    cdir = os.path.normpath(ccur.get('dir') or '') if ccur.get('dir') else ''
    cfolder = os.path.basename(cdir) if cdir else ''
    for c in (cands or []):
        nm = c.get('name') or os.path.basename(c.get('path') or '')
        p = c.get('path') or ''
        if p and cpath and p == cpath:
            continue
        xdir = c.get('dir') or os.path.dirname(p)
        xnorm = os.path.normpath(xdir) if xdir else ''
        xfolder = os.path.basename(xnorm) if xnorm else ''
        xpre = series_prefix(nm)
        xcore = META.book_core(nm)
        xauth = c.get('author') or ''
        item = {'name': nm, 'dir': xdir, 'path': p}
        if cpre and len(cpre) >= 3 and xpre == cpre:
            res['series'].append(item)
        if cfolder and xfolder == cfolder:
            res['topic'].append(item)
        if ccore and xcore == ccore:
            res['same_book'].append(item)
        if cauth and xauth and xauth == cauth:
            res['same_author'].append(item)
    for k in res:
        res[k] = res[k][:50]
    return res


# ----------------------------------------------------------------- 跨文件检索历史
def fts_hist_add(hist, record, cap=30):
    """把一次跨文件全文检索记录插到最前（按 kw 去重，最多 cap 条）。返回新列表。"""
    hist = list(hist or [])
    kw = (record or {}).get('kw') or ''
    hist = [h for h in hist if (h.get('kw') or '') != kw]
    hist.insert(0, record)
    return hist[:cap]


# ----------------------------------------------------------------- 脚注（Word 可直贴）
def rtf_escape(s):
    """转义为 RTF：ASCII 直出，汉字转 \\uN?（Word 能识别）。"""
    out = []
    for ch in (s or ''):
        o = ord(ch)
        if ch == '\\':
            out.append('\\\\')
        elif ch == '{':
            out.append('\\{')
        elif ch == '}':
            out.append('\\}')
        elif ch == '\n':
            out.append('\\par\n')
        elif ch == '\t':
            out.append('\\tab ')
        elif o < 128:
            out.append(ch)
        else:
            if o > 32767:
                o -= 65536
            out.append('\\u%d?' % o)
    return ''.join(out)


def footnote_rtf(body, source):
    """生成带真脚注的 RTF：粘贴到 Word 即插入脚注（引用标记 + 脚注正文）。"""
    return ('{\\rtf1\\ansi\\ansicpg936\\deff0'
            '{\\fonttbl{\\f0\\fnil\\fcharset134 SimSun;}}'
            '\\f0\\fs21 %s{\\footnote\\fs18 %s}}'
            % (rtf_escape(body or ''), rtf_escape(source or '')))


def footnote_html(body, source):
    """HTML 回退（某些编辑器不认 RTF 时用）。"""
    import html as _h
    return ('<p>%s<a href="#_ftn1" name="_ftnref1"><sup>[1]</sup></a></p>'
            '<div id="_ftn1"><p><sup>[1]</sup> %s</p></div>'
            % (_h.escape(body or ''), _h.escape(source or '')))


# ----------------------------------------------------------------- 自检
def selftest():
    import shutil
    import tempfile
    import sys
    log = []

    def ok(c, m):
        log.append(('OK  ' if c else 'FAIL') + ' ' + m)
        return bool(c)

    base = tempfile.mkdtemp(prefix='vt_')
    global _DOCS_ROOT
    old = _DOCS_ROOT
    _DOCS_ROOT = os.path.join(base, 'Cathay文档记录')
    try:
        meta = {'name': '美的历程', 'volume': '第1册', 'author': '李泽厚',
                'publisher': '文物出版社', 'year': '1981'}
        # 摘录
        r1 = add_excerpt(meta, '人的觉醒是魏晋时期的一大特征。', 27, 'D:\\书库\\美的历程.pdf')
        ok(r1 and os.path.isfile(r1['path']) and '第27页' in open(r1['path'], encoding='utf-8').read(),
           '摘录本写入 + 出处：%s' % (r1 or {}).get('path'))
        r1b = add_excerpt(meta, '第二条摘录。', 28, 'D:\\书库\\美的历程.pdf')
        body = open(r1['path'], encoding='utf-8').read()
        ok(body.count('### 摘录') == 2 and '文物出版社' in body,
           '摘录本追加多条 + 出版社出处')
        # 截图
        r2 = add_snapshot(b'\x89PNG\r\n\x1a\nFAKE', meta, 27, 'D:\\书库\\美的历程.pdf')
        ok(r2 and os.path.isfile(r2['png']) and r2['name'].endswith('.png'),
           '截图本写入图片：%s' % (r2 or {}).get('name'))
        md = open(r2['md'], encoding='utf-8').read()
        ok((' ' not in r2['name'][:0]) and r2['name'] in md and '美的历程' in md,
           '截图本.md 含图片链接 + 出处')
        # 出处信息
        si = source_info(meta, 27, 'D:\\书库\\美的历程_【繁转简】.txt')
        ok('第27页' in si['headline'] and '繁转简TXT' in si['detail'],
           '出处信息：%s / %s' % (si['headline'], si['detail']))
        # 对读页码索引
        txt = ('元数据头\n2016-07-02 04:08:54\nhttp://x\n'
               '======\n第 1 页\n第一页正文甲。\n======\n第 2 页\n第二页正文乙。\n'
               '======\n第 3 页\n第三页正文丙丙丙。\n======\n第 4 页\n第四页正文丁。\n')
        idx = SyncIndex(txt)
        ok(idx.page_count == 4 and idx.page_range(2)[0] > 0,
           'SyncIndex 解析「第N页」→ %d 页' % idx.page_count)
        off2, num2 = idx.offset_for_page(2)
        ok(num2 == 2 and idx.page_at_position(off2) == 2,
           '页码→偏移→页码 一致（第2页）')
        idx2 = SyncIndex('≦1≧\n甲\n≦2≧\n乙\n≦3≧\n丙\n')
        ok(idx2.page_count == 3, 'SyncIndex 解析「≦N≧」→ %d 页' % idx2.page_count)
        # 版权页（目录优先）
        toc = [[1, '序', 1], [1, '正文', 5], [1, '版权页', 9]]
        ok(find_colophon_in_toc(toc) == 9, '目录里找「版权页」→ 第 %d 页'
           % find_colophon_in_toc(toc))
        toc2 = [[1, '前言', 1], [1, '版权', 3]]
        ok(find_colophon_in_toc(toc2) == 3, '目录里找「版权」→ 第 %d 页'
           % find_colophon_in_toc(toc2))
        ok(find_colophon_in_toc([[1, '序', 1]]) == 0, '目录里没有版权条目 → 0')
        # 相关推荐四档
        cur = {'name': '近代中国史料丛刊 001 甲篇', 'dir': 'D:\\库\\近代史料',
               'path': 'D:\\库\\近代史料\\a.pdf', 'author': '邓瑞全'}
        cands = [
            {'name': '近代中国史料丛刊 002 乙篇', 'dir': 'D:\\库\\近代史料',
             'path': 'D:\\库\\近代史料\\b.pdf', 'author': '王某'},
            {'name': '别史', 'dir': 'D:\\库\\别处', 'path': 'D:\\库\\别处\\c.pdf',
             'author': '邓瑞全'},
            {'name': '近代中国史料丛刊 001 甲篇', 'dir': 'D:\\库\\近代史料',
             'path': 'D:\\库\\近代史料\\a2.txt', 'author': '邓瑞全'},
        ]
        g = classify_related(cur, cands)
        ok(any('002' in x['name'] for x in g['series']), '同丛书命中 002')
        ok(any(x['name'] == '别史' for x in g['same_author']), '同作者命中 别史')
        ok(any(x['path'].endswith('.txt') for x in g['same_book']), '同一本书的其他书命中 txt')
        # 检索历史
        h = []
        h = fts_hist_add(h, {'kw': '甲', 'at': '1'})
        h = fts_hist_add(h, {'kw': '乙', 'at': '2'})
        h = fts_hist_add(h, {'kw': '甲', 'at': '3'})
        ok([x['kw'] for x in h] == ['甲', '乙'], '检索历史去重且新的在前：%s' % [x['kw'] for x in h])
        # 脚注 RTF
        rt = footnote_rtf('引文一句', '李泽厚：《美的历程》，1981年，第27页。')
        ok(rt.startswith('{\\rtf1') and '\\footnote' in rt and '\\u' in rt,
           '脚注 RTF 含 \\footnote 与 Unicode 转义')
        ok('<sup>' in footnote_html('正文', '出处') and '出处' in footnote_html('正文', '出处'),
           '脚注 HTML 回退')
        # 摘录本解析 / 回写（查看器 / 编辑器）
        recs = parse_excerpts(path=r1['path'])
        ok(len(recs) == 2 and '人的觉醒' in recs[0]['body']
           and '美的历程' in recs[0]['cite'],
           '解析摘录本 → %d 条，正文/出处正确' % len(recs))
        recs[0]['body'] = '（改过的）人的觉醒是魏晋时期的一大特征。'
        recs.append({'ts': '2026-01-01 00:00:00', 'body': '手工新增一条。',
                     'cite': '《测试书》第1页'})
        p2 = write_excerpts(recs)
        recs2 = parse_excerpts(path=p2)
        ok(len(recs2) == 3 and '（改过的）' in recs2[0]['body']
           and '手工新增' in recs2[2]['body'],
           '编辑后回写 → %d 条，改动与新增都在' % len(recs2))
        ok(build_excerpts(parse_excerpts(path=p2)).count('### 摘录') == 3,
           '回写→再解析仍为 3 条（格式自洽）')
        # 截图本清单
        snaps = list_snapshots()
        ok(any(s['name'] == r2['name'] for s in snaps),
           '截图本清单含刚存的图（%d 张）' % len(snaps))
    finally:
        _DOCS_ROOT = old
        shutil.rmtree(base, ignore_errors=True)
    out = '\n'.join(log) + '\nresult = %s\n' % (
        'OK' if all(l.startswith('OK') for l in log) else 'FAIL')
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    print('CathayViewer · 记录工具  v0.1.0')
    print(out)


if __name__ == '__main__':
    selftest()
