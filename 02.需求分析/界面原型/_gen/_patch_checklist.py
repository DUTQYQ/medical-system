# -*- coding: utf-8 -*-
"""把「界面—效果图对照表」插入《界面清单》，并补充文档信息中的原型交付状态。"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import _pages_a
import _pages_b
import _pages_c

ALL = _pages_a.pages() + _pages_b.pages() + _pages_c.pages()

FILE = os.path.normpath(os.path.join(HERE, '..', '..', '界面清单_康养系统_v1.0.md'))
GROUP = {'AUTH': '公共 / 认证', 'ELDER': '老人端', 'FAMILY': '家属端', 'CARE': '护工端', 'ADMIN': '管理员端'}
PRI = {}


def load_pri():
    import re
    src = open(os.path.join(HERE, '_make_doc.py'), encoding='utf-8').read()
    ns = {}
    start = src.index('PRI = {')
    end = src.index('}\n', start) + 1
    exec(src[start:end], ns)
    return ns['PRI']


PRI = load_pri()

rows = []
for i, (uid, name, states, shell, active, elder, body, css) in enumerate(ALL, 1):
    g = GROUP[uid.split('-')[1]]
    p = PRI[uid]
    level = '【核心】' if p.startswith('【核心】') else '【选配】'
    status = '已完成' if level == '【核心】' else '已完成（可裁剪）'
    fn = f'{uid}_{name.replace(" ", "")}.png'
    rows.append(f'| {i} | {uid} | {name} | {g} | {level} | `界面原型/效果图/{fn}` | {status} |')

section = """
---

## 8. 界面—效果图对照表（原型完成状态）

> 原型交付状态：**38 个界面全部完成效果图**，一界面一图，与上表编号逐条对应。
> 效果图源文件与出图管线见 `界面原型/`（`pages/` 为 HTML 源、`效果图/` 为 PNG、`_gen/` 为生成器）。
> 详细设计说明见《原型设计说明书_康养系统_v2.0.md》。

| 序号 | 界面编号 | 界面名称 | 分组 | 分级 | 效果图 | 状态 |
|---|---|---|---|---|---|---|
""" + '\n'.join(rows) + """

**统计核对**：核心 29 个 + 选配 9 个 = 38 个，与第 0 节「界面总数」一致。

> 说明：v1.0 评审版的 P1~P9（覆盖 12 个界面编号）已归档至 `界面原型/_v1_评审版/`，
> 编号映射关系见《原型设计说明书 v2.0》第 4 章。

---

## 9. 待确认事项
"""


def main():
    text = open(FILE, encoding='utf-8').read()

    old_head = '| 界面总数 | 38 个（核心 29 + 选配 9） |'
    new_head = ('| 界面总数 | 38 个（核心 29 + 选配 9） |\n'
                '| 原型交付 | 38 个界面已全部出图，见 `界面原型/效果图/`；说明书见《原型设计说明书_康养系统_v2.0.md》 |')
    if '| 原型交付 |' not in text:
        assert old_head in text, '未找到界面总数行'
        text = text.replace(old_head, new_head, 1)

    marker = '\n## 8. 待确认事项'
    assert marker in text, '未找到第 8 章'
    text = text.replace(marker, section, 1)

    open(FILE, 'w', encoding='utf-8').write(text)
    print(f'updated {FILE}')
    print(f'  inserted {len(rows)} rows, size {os.path.getsize(FILE)//1024} KB')


if __name__ == '__main__':
    main()
