# -*- coding: utf-8 -*-
"""驱动：生成 38 个界面原型 HTML 到 ../pages/"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _lib import build
import _pages_a
import _pages_b
import _pages_c

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, '..', 'pages'))

all_pages = _pages_a.pages() + _pages_b.pages() + _pages_c.pages()
os.makedirs(OUT, exist_ok=True)

seen = set()
manifest = []
for uid, name, states, shell, active, elder, body, css in all_pages:
    assert uid not in seen, 'duplicate uid: ' + uid
    seen.add(uid)
    html = build(uid, name, states, body, shell, active, elder, css)
    fn = f'{uid}_{name.replace(" ", "")}.html'
    with open(os.path.join(OUT, fn), 'w', encoding='utf-8') as f:
        f.write(html)
    manifest.append((uid, name, fn, shell, states))

print(f'generated {len(manifest)} pages -> {OUT}')
for uid, name, fn, shell, states in manifest:
    print(f'  {uid:14s} {name:10s} [{shell}] {os.path.getsize(os.path.join(OUT, fn))//1024}KB')

groups = {}
for uid, *_ in manifest:
    k = uid.split('-')[1]
    groups[k] = groups.get(k, 0) + 1
print('by group:', groups, 'total', sum(groups.values()))
