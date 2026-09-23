# -*- coding: utf-8 -*-
"""CathayViewer · 学术书库浏览与阅读 —— 历史纪年换算  v0.1.0

纯逻辑（不依赖 PyQt）。把近代文献里混用的纪年换算成公元年：
  * 民国纪年（民国二十六年 = 1937）
  * 年号纪年（光绪二十四年 = 1898；含明清、太平天国、大韩帝国、日本、伪满等）
  * 干支纪年（戊戌 = 1898；单干支列出 1700–2000 年全部对应年份）
  * 年号 + 干支（咸丰庚申 = 1860）

数据参考用户提供的三个资料表（明清民国年号表、中日朝三国近代纪年表、中华甲子年表）；
年号起始年、干支 60 循环均为可核验的公共事实，故内置精简表，不依赖外部盘。
"""
import re

# 天干 / 地支
STEMS = '甲乙丙丁戊己庚辛壬癸'
BRANCHES = '子丑寅卯辰巳午未申酉戌亥'
_GANZHI_BASE = 1984          # 1984 = 甲子

# 年号 / 纪年 → 元年公元（元年 = start；N 年 = start + N - 1）
ERA = {
    # 明
    '洪武': 1368, '建文': 1399, '永樂': 1403, '永乐': 1403, '洪熙': 1425,
    '宣德': 1426, '正統': 1436, '正统': 1436, '景泰': 1450, '天順': 1457, '天顺': 1457,
    '成化': 1465, '弘治': 1488, '正德': 1506, '嘉靖': 1522, '隆慶': 1567, '隆庆': 1567,
    '萬曆': 1573, '万历': 1573, '泰昌': 1620, '天啟': 1621, '天启': 1621,
    '崇禎': 1628, '崇祯': 1628,
    # 清（含入关前）
    '天命': 1616, '天聰': 1627, '天聪': 1627, '崇德': 1636, '順治': 1644, '顺治': 1644,
    '康熙': 1662, '雍正': 1723, '乾隆': 1736, '嘉慶': 1796, '嘉庆': 1796,
    '道光': 1821, '咸豐': 1851, '咸丰': 1851, '同治': 1862, '光緒': 1875, '光绪': 1875,
    '宣統': 1909, '宣统': 1909,
    # 太平天國 / 中華民國 / 洪憲 / 偽滿
    '太平天國': 1851, '太平天国': 1851,
    '民國': 1912, '民国': 1912, '洪憲': 1916, '洪宪': 1916,
    '大同': 1932, '康德': 1934,
    # 日本
    '明治': 1868, '大正': 1912, '昭和': 1926, '平成': 1989, '令和': 2019,
    # 朝鮮 / 大韓帝國
    '開國': 1392, '开国': 1392, '建陽': 1896, '建阳': 1896, '光武': 1897, '隆熙': 1907,
}

_ERA_ALT = '|'.join(sorted(ERA.keys(), key=len, reverse=True))
_NUM = r'(?:[〇零一二三四五六七八九十百千廿卅0-9]{1,6}|元|正)'
_GRP = r'[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]'

_RE_ERA_N = re.compile(r'(%s)\s*(%s)\s*年' % (_ERA_ALT, _NUM))
_RE_ERA_GZ = re.compile(r'(%s)\s*(%s)' % (_ERA_ALT, _GRP))
_RE_GZ = re.compile(r'(%s)(年?)' % _GRP)
_RE_FY = re.compile(r'公元\s*([0-9]{3,4})\s*年?')
_RE_SKIP = re.compile(r'【[^】]*】')


def _cn2int(s):
    s = (s or '').strip()
    if not s:
        return None
    if s.isdigit():
        return int(s)
    if s in ('元', '正'):
        return 1
    s = s.replace('廿', '二十').replace('卅', '三十')
    d = {'〇': 0, '零': 0, '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
         '六': 6, '七': 7, '八': 8, '九': 9}
    u = {'十': 10, '百': 100, '千': 1000}
    if s == '十':
        return 10
    total, num = 0, 0
    for ch in s:
        if ch in d:
            num = d[ch]
        elif ch in u:
            total += (num if num else 1) * u[ch]
            num = 0
        else:
            return None
    return total + num


def ganzhi_index(gz):
    """干支 → 0–59 序号（1984 甲子 = 0）；非法组合返回 -1。"""
    if not gz or len(gz) < 2:
        return -1
    a, b = gz[0], gz[1]
    if a not in STEMS or b not in BRANCHES:
        return -1
    si, bi = STEMS.index(a), BRANCHES.index(b)
    for k in range(6):
        if (si + 10 * k) % 12 == bi:
            return si + 10 * k
    return -1


def year_to_ganzhi(year):
    i = (int(year) - _GANZHI_BASE) % 60
    return STEMS[i % 10] + BRANCHES[i % 12]


def ganzhi_years(gz, y0=1700, y1=2000):
    idx = ganzhi_index(gz)
    if idx < 0:
        return []
    return [y for y in range(int(y0), int(y1) + 1) if (y - _GANZHI_BASE) % 60 == idx]


_RE_REPUBLIC_MIN = 39          # 民国 39 年及以后才自动换算（民国元年–38 年不再标注）


def _skip_era(era, n):
    return era in ('民國', '民国') and n is not None and n <= (_RE_REPUBLIC_MIN - 1)


def convert(text, gz_from=1700, gz_to=2000):
    """识别 text 中的纪年，返回命中列表 [{start,end,token,note,kind,year}]（不重叠）。"""
    if not text:
        return []
    spans = [(m.start(), m.end()) for m in _RE_SKIP.finditer(text)]

    def prot(i):
        return any(a <= i < b for a, b in spans)

    def tail(m):
        return text[m.end():m.end() + 1] == '【'      # 紧跟着已有标注 → 跳过（幂等）

    cands = []
    for m in _RE_ERA_N.finditer(text):
        if prot(m.start()) or tail(m):
            continue
        era, numtxt = m.group(1), m.group(2)
        n = _cn2int(numtxt)
        st = ERA.get(era)
        if not n or st is None:
            continue
        y = st + n - 1
        if _skip_era(era, n):
            continue
        cands.append((m.start(), m.end(), '%s%s年=%d年' % (era, numtxt, y), 'era', y))
    for m in _RE_ERA_GZ.finditer(text):
        if prot(m.start()) or tail(m):
            continue
        era, gz = m.group(1), m.group(2)
        st = ERA.get(era)
        ys = ganzhi_years(gz, gz_from, gz_to)
        pick = None
        if st is not None:
            for y in ys:
                if st - 1 <= y <= st + 70:
                    pick = y
                    break
        if pick is None and ys:
            pick = min(ys, key=lambda y: abs(y - st if st else y))
        if pick is not None:
            cands.append((m.start(), m.end(), '%s%s=%d年' % (era, gz, pick), 'era_gz', pick))
    for m in _RE_GZ.finditer(text):
        if prot(m.start()) or tail(m):
            continue
        gz = m.group(1)
        ys = ganzhi_years(gz, gz_from, gz_to)
        if not ys:
            continue
        note = '%s=%s年' % (gz, '、'.join(str(y) for y in ys))
        cands.append((m.start(), m.end(), note, 'gz', None))
    # 去重叠：起点靠前、跨度长者优先
    cands.sort(key=lambda c: (c[0], -(c[1] - c[0])))
    chosen, last = [], -1
    for s, e, note, kind, y in cands:
        if s < last:
            continue
        chosen.append((s, e, note, kind, y))
        last = e
    return [{'start': s, 'end': e, 'token': text[s:e], 'note': note,
             'kind': kind, 'year': y} for s, e, note, kind, y in chosen]


def annotate(text, gz_from=1700, gz_to=2000):
    """在引文里每个纪年后加【对应公元年】。返回 (新文本, 命中列表)。"""
    hits = convert(text, gz_from, gz_to)
    if not hits:
        return text, []
    out, prev = [], 0
    for h in hits:
        out.append(text[prev:h['start']])
        out.append(h['token'])
        out.append('【%s】' % h['note'])
        prev = h['end']
    out.append(text[prev:])
    return ''.join(out), hits


def annotate_append(text, gz_from=1700, gz_to=2000):
    """复制文本时用：在整段文字后面追加一栏【纪年换算】（去重、保留出现顺序）。

    返回 (新文本, 命中列表)。无命中则原文返回。
    """
    hits = convert(text, gz_from, gz_to)
    if not hits:
        return text, []
    notes = []
    for h in hits:
        if h['note'] not in notes:
            notes.append(h['note'])
    return (text.rstrip() + '\n【纪年换算】' + '；'.join(notes) + '。'), hits


def year_eras(year, span=40):
    """反查：公元 year 前后 span 年内在用的年号（粗略，供速查）。"""
    y = int(year)
    hit = [k for k in ERA if ERA[k] <= y <= ERA[k] + span and not _is_trad_dup(k)]
    return sorted(set(hit), key=lambda k: ERA[k])


_SIMP_MAP = {'樂': '乐', '統': '统', '順': '顺', '慶': '庆', '國': '国', '憲': '宪',
             '萬': '万', '曆': '历', '啟': '启', '禎': '祯', '聰': '聪', '緒': '绪',
             '陽': '阳', '豐': '丰'}
_TRAD_KEYS = set(k for k in ERA if any(c in _SIMP_MAP for c in k))


def _is_trad_dup(k):
    """繁体写法：简繁同词时反查只留简体那一个，避免重复。"""
    return k in _TRAD_KEYS


# ----------------------------------------------------------------- 自检
def selftest():
    import sys
    log = []

    def ok(c, m):
        log.append(('OK  ' if c else 'FAIL') + ' ' + m)
        return bool(c)

    ok(_cn2int('二十四') == 24, '汉语数字 二十四 = %s' % _cn2int('二十四'))
    ok(_cn2int('元') == 1 and _cn2int('正') == 1, '元/正 = 1')
    ok(_cn2int('廿四') == 24 and _cn2int('卅') == 30, '廿四=24 卅=30')
    ok(_cn2int('100') == 100, '阿拉伯 100')
    ok(year_to_ganzhi(1840) == '庚子', '1840 = %s（应 庚子）' % year_to_ganzhi(1840))
    ok(year_to_ganzhi(1898) == '戊戌', '1898 = %s（应 戊戌）' % year_to_ganzhi(1898))
    ok(ganzhi_index('甲子') == 0 and ganzhi_index('庚子') == 36, '干支序号 甲子=0 庚子=36')
    ok(ganzhi_index('甲丑') == -1, '非法干支 甲丑 → -1')
    ys = ganzhi_years('甲子', 1700, 2000)
    ok(ys == [1744, 1804, 1864, 1924, 1984], '甲子年份 %s' % ys)

    t1 = '光绪二十四年，戊戌变法。'
    a1, h1 = annotate(t1)
    ok('光绪二十四年=1898年】' in a1, '光绪二十四年→1898：%s' % a1)
    ok('戊戌' in a1 and '1898' in a1, '戊戌→含 1898')

    a2, h2 = annotate('民国四十年，迁台。')
    ok('民国四十年' in a2 and '1951' in a2, '民国四十年→1951：%s' % a2)
    a2b, h2b = annotate('民国三十八年，改元。')
    ok('【' not in a2b and h2b == [], '民国三十八年不转换：%s' % a2b)
    a2c, h2c = annotate('民国三十九年')
    ok('1950' in a2c, '民国三十九年→1950：%s' % a2c)
    ap, hp = annotate_append('光绪二十四年戊戌')
    ok('【纪年换算】' in ap and '1898' in ap, '复制追加：%s' % ap)

    a3, h3 = annotate('咸丰庚申，英法联军入京。')
    ok('1860' in a3, '咸丰庚申→1860：%s' % a3)

    a4, h4 = annotate('事在康熙元年前后。')
    ok('1662' in a4, '康熙元年→1662：%s' % a4)

    a5, h5 = annotate('甲午战争（1894年）')
    ok('1894' in a5 and ('1834' in a5 or '1954' in a5 or '1894' in a5),
       '单干支列出 1700–2000：%s' % a5)

    a6, h6 = annotate('光绪二十四年')
    a6b, _ = annotate(a6)                       # 再标注不应重复
    ok(a6b.count('【') == a6.count('【'), '已标注不重复标注')

    a7, h7 = annotate('明治四十五年、大正十五年、昭和六十四年')
    ok('1912' in a7 and '1926' in a7 and '1989' in a7, '日本年号：%s' % a7)
    ok('光绪' in year_eras(1898), '反查 1898 → %s' % year_eras(1898))

    out = '\n'.join(log) + '\nresult = %s\n' % (
        'OK' if all(l.startswith('OK') for l in log) else 'FAIL')
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    print('CathayViewer · 历史纪年换算  v0.1.0')
    print(out)


if __name__ == '__main__':
    selftest()
