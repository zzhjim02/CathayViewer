# -*- coding: utf-8 -*-
"""组装发布包（exe + config + 开发源码 + README/使用说明 + app.ico），
自动排除索引库/设置/构建缓存/调试脚本，并压 zip。

用法：py -3 make_release.py [版本号]      （默认 0.1.0）
产物：上级目录 `CathayViewer 学术书库浏览与阅读 <版本>` 目录，及同名（含源码）zip。
旧的同名目录/zip 会被「改名归档」为 .OLD-<时间戳>，不删除。
"""
import hashlib
import os
import shutil
import sys
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))          # ...\CathayViewer-DEV\开发
DEV = os.path.dirname(HERE)                                # ...\CathayViewer-DEV
ROOT = os.path.dirname(DEV)                                # ...\我的软件创作库
NAME = 'CathayViewer 学术书库浏览与阅读'
VER = sys.argv[1] if len(sys.argv) > 1 else '0.1.0'

# 不进包：目录名（小写比较）
EXCLUDE_DIRS = {'dev_dist', 'dev_build', 'dist', 'build', '__pycache__',
                '.git', '.svn', 'runtime', '.idea'}
# 不进包：扩展名
EXCLUDE_EXT = {'.db', '.pyc', '.pyo', '.pdb'}
# 不进包：文件名
EXCLUDE_FILES = {'cathayviewer_index.db', 'cathayviewer_settings.json',
                 '_selftest.txt', '_selftest_gui.txt', 'cathayviewer_index.db.building'}
# 不进包：文件名前缀（调试/探针脚本）
EXCLUDE_PREFIX = ('_',)          # 所有 _*.py/_*.txt 排障脚本都不进发布包
# 不进包：包根（顶层）下的本地用户数据（config\ 下的随包发布，见 batch13）
EXCLUDE_ROOT = {'person_alias.csv'}


def _skip(rel):
    name = os.path.basename(rel)
    low = name.lower()
    if low in EXCLUDE_DIRS or low in EXCLUDE_FILES:
        return True
    if os.path.splitext(low)[1] in EXCLUDE_EXT:
        return True
    if low.startswith(EXCLUDE_PREFIX):
        return True
    if low in EXCLUDE_ROOT and ('/' not in rel and '\\' not in rel):
        return True          # 顶层：运行时生成的本地别名表不发布（config\ 下的随包发布）
    return False


def copy_tree(src, dst, rel=''):
    os.makedirs(dst, exist_ok=True)
    for e in os.scandir(src):
        r = os.path.join(rel, e.name) if rel else e.name
        if _skip(r):
            continue
        s, d = e.path, os.path.join(dst, e.name)
        if e.is_dir():
            copy_tree(s, d, r)
        else:
            shutil.copy2(s, d)


def archive_old(path, ts):
    """存在的旧产物改名归档（不删除）。被占用时返回 'locked'，由调用方改为原地刷新。"""
    if not os.path.exists(path):
        return 'none'
    dst = '%s.OLD-%s' % (path, ts)
    n = 1
    while os.path.exists(dst):
        dst = '%s.OLD-%s-%d' % (path, ts, n)
        n += 1
    try:
        os.rename(path, dst)
        print('旧产物已归档：', os.path.basename(dst))
        return 'renamed'
    except OSError as e:
        print('旧产物被占用，无法改名（%s）→ 改为原地覆盖刷新：%s'
              % (e, os.path.basename(path)))
        return 'locked'


def _clean_in_place(root):
    """原地刷新时，清掉不该在发布包里的文件/目录（缓存/调试脚本）。

    注意：**绝不删除运行期文件**（索引库、设置、自检日志）——那是用户的数据，
    它们本来就不会被拷进包，不必删。
    """
    for dp, dns, fns in os.walk(root, topdown=False):
        rel_dir = os.path.relpath(dp, root)
        rel_dir = '' if rel_dir == '.' else rel_dir
        for fn in fns:
            rel = os.path.join(rel_dir, fn) if rel_dir else fn
            if os.path.basename(fn).lower() in EXCLUDE_FILES:
                continue                     # 索引库/设置/自检日志：保留
            if _skip(rel):
                try:
                    os.remove(os.path.join(dp, fn))
                except OSError:
                    pass
        for dn in dns:
            if dn.lower() in EXCLUDE_DIRS:
                try:
                    shutil.rmtree(os.path.join(dp, dn), ignore_errors=True)
                except OSError:
                    pass


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    ts = time.strftime('%Y%m%d-%H%M%S')
    exe_src = os.path.join(DEV, 'dev_dist', 'CathayViewer.exe')
    if not os.path.isfile(exe_src):
        print('缺 exe，请先打包：', exe_src)
        return 1

    rel_dir = os.path.join(ROOT, '%s %s' % (NAME, VER))
    zip_path = os.path.join(ROOT, '%s %s （含源码）%s.zip'
                            % (NAME, VER, time.strftime('%Y%m%d')))
    st_dir = archive_old(rel_dir, ts)
    archive_old(zip_path, ts)
    if st_dir == 'locked':
        _clean_in_place(rel_dir)

    os.makedirs(rel_dir, exist_ok=True)
    exe_dst = os.path.join(rel_dir, '%s %s.exe' % (NAME, VER))
    shutil.copy2(exe_src, exe_dst)

    copy_tree(os.path.join(DEV, 'config'), os.path.join(rel_dir, 'config'), rel='config')
    copy_tree(DEV, os.path.join(rel_dir, '开发'), rel='开发')          # 源码（自动跳过 db/缓存/调试）
    for f in ('app.ico', 'README.md', '使用说明.txt'):
        p = os.path.join(DEV, f)
        if os.path.isfile(p):
            try:
                shutil.copy2(p, os.path.join(rel_dir, f))
            except OSError as e:
                print('  ⚠ 文件被占用，跳过更新：%s（%s）' % (f, e))
    try:
        with open(os.path.join(rel_dir, '校验值.txt'), 'w', encoding='utf-8') as _f:
            _f.write('%s v%s\n\n主程序：%s\n字节数：%d\nSHA256：%s\n'
                     % (NAME, VER, os.path.basename(exe_dst),
                        os.path.getsize(exe_dst), sha256(exe_dst)))
    except OSError as e:
        print('  ⚠ 校验值.txt 写入失败：%s' % e)

    size = os.path.getsize(exe_dst)
    h = sha256(exe_dst)

    # 自检：确认「真止要进包的内容」里没有 .db / 索引 / 设置 / 调试脚本
    # （注意：发布目录本身允许存运行期文件——那是在“原地刷新”时保留的用户数据，不进 zip）
    bad = []
    for sub in ('config', '开发'):
        for dp, _dn, fns in os.walk(os.path.join(rel_dir, sub)):
            for fn in fns:
                rel = os.path.relpath(os.path.join(dp, fn), rel_dir)
                if _skip(rel) or os.path.splitext(fn.lower())[1] in EXCLUDE_EXT:
                    bad.append(rel)
    if bad:
        print('打包校验失败：要进包的内容里仍有被排除的文件：')
        for b in bad[:20]:
            print('  ', b)
        return 2

    # 压 zip（跳过运行期文件：索引库/设置/自检日志/调试脚本——它们允许留在发布目录里，但不进包）
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
        base = os.path.basename(rel_dir)
        for dp, _dn, fns in os.walk(rel_dir):
            for fn in fns:
                full = os.path.join(dp, fn)
                rel = os.path.relpath(full, rel_dir)
                if _skip(rel):
                    continue
                z.write(full, os.path.join(base, rel))

    # 再校一次 zip 里没混进运行期文件
    with zipfile.ZipFile(zip_path) as z:
        badz = [n for n in z.namelist()
                if os.path.splitext(n.lower())[1] in EXCLUDE_EXT
                or os.path.basename(n).lower() in EXCLUDE_FILES
                or os.path.basename(n).startswith(EXCLUDE_PREFIX)]
    if badz:
        print('打包校验失败：zip 里仍有被排除的文件：')
        for b in badz[:20]:
            print('  ', b)
        return 2
    print('发布包已生成：')
    print('  目录：', rel_dir)
    print('  zip ：', zip_path, '（%.1f MB）' % (os.path.getsize(zip_path) / 1048576.0))
    print('  exe ：%d 字节  SHA256 %s' % (size, h))
    return 0


if __name__ == '__main__':
    sys.exit(main())
