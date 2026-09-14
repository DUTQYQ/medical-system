# -*- coding: utf-8 -*-
"""康养系统界面原型 v2.0 · 生成器公共库
外壳：elder / family / care / admin / plain / screen
组件：卡片、表格、分页、空态、统计卡、表单行、聊天气泡、时间轴、折线/条形图
"""

CSS = '<link rel="stylesheet" href="../prototype.css">'

# ---------------- 基础小件 ----------------

def tag(text, kind='info'):
    return f'<span class="tag tag-{kind}">{text}</span>'


def dot(kind):
    return f'<span class="dot dot-{kind}"></span>'


def disclaimer(text='本页健康数据与建议仅供参考，不构成医疗诊断，身体不适请及时就医'):
    return f'<div class="disclaimer">{text}</div>'


def card(title, inner, extra=''):
    t = f'<div class="card-title">{title}</div>' if title else ''
    return f'<div class="card">{t}{inner}{extra}</div>'


def table(headers, rows, cls=''):
    th = ''.join(f'<th>{h}</th>' for h in headers)
    trs = ''
    for r in rows:
        tds = ''.join(f'<td>{c}</td>' for c in r)
        trs += f'<tr>{tds}</tr>'
    return f'<table class="tbl {cls}"><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table>'


def pager(cur=1, pages=5, total=0):
    ps = ''
    for i in range(1, pages + 1):
        ps += f'<span class="pg{" on" if i == cur else ""}">{i}</span>'
    tot = f'<span style="margin-right:auto;color:#909399">共 {total} 条</span>' if total else ''
    return (f'<div class="pager">{tot}<span class="pg">上一页</span>{ps}'
            f'<span class="pg">下一页</span></div>')


def empty(title, desc='', ico='空'):
    d = f'<div class="empty-d">{desc}</div>' if desc else ''
    return (f'<div class="empty"><div class="empty-ico">{ico}</div>'
            f'<div class="empty-t">{title}</div>{d}</div>')


def stat_grid(items, cols=4):
    """items: [(label, value, unit, foot)]"""
    g = '' if cols == 4 else f' stat-grid-{cols}'
    inner = ''
    for label, val, unit, foot in items:
        u = f'<small>{unit}</small>' if unit else ''
        f = f'<div class="stat-foot">{foot}</div>' if foot else ''
        inner += (f'<div class="stat"><div class="stat-label">{label}</div>'
                  f'<div class="stat-val">{val}{u}</div>{f}</div>')
    return f'<div class="stat-grid{g}">{inner}</div>'


def filter_bar(parts):
    return '<div class="filter-bar">' + ''.join(parts) + '</div>'


def inp(ph, sel=False, cls=''):
    c = 'inp ph inp-sel' if sel else f'inp ph {cls}'.strip()
    return f'<div class="{c}">{ph}</div>'


def btn(text, primary=False, sm=False):
    c = 'btn' + (' btn-primary' if primary else '') + (' btn-sm' if sm else '')
    return f'<button class="{c}">{text}</button>'


def form_row(label, ctrl, hint='', req=False):
    r = '<i>*</i>' if req else ''
    h = ''
    if hint:
        h = f'<div class="{"hint-err" if hint.startswith("!") else "hint"}">{hint.lstrip("!")}</div>'
    return (f'<div class="form-row"><div class="form-label">{r}{label}</div>'
            f'<div class="form-ctrl">{ctrl}{h}</div></div>')


def metric_detail(items):
    """items: [(k, v, cls)]"""
    inner = ''
    for k, v, c in items:
        inner += f'<div><div class="md-k">{k}</div><div class="md-v {c}">{v}</div></div>'
    return f'<div class="metric-detail">{inner}</div>'


def timeline(items):
    inner = ''
    for t, d in items:
        inner += f'<div class="tl-item"><div class="tl-t">{t}</div><div class="tl-d">{d}</div></div>'
    return f'<div class="tl">{inner}</div>'


def chips(items):
    return '<div class="chip-row">' + ''.join(f'<span class="chip">{i}</span>' for i in items) + '</div>'


# ---------------- 图表（纯 SVG，离线可截） ----------------

def chart_line(series, xlabels, ymin=0, ymax=200, abn=(), w=620, h=220):
    """series: [{'name','color','vals'}]; abn: [(series_idx, point_idx)]"""
    L, R, T, B = 50, 14, 14, 30
    pw, ph = w - L - R, h - T - B
    n = max(len(s['vals']) for s in series)
    xs = [L + (pw * i / (n - 1) if n > 1 else 0) for i in range(n)]

    def yv(v):
        return T + ph * (ymax - v) / (ymax - ymin)

    g = ''
    for k in range(5):
        v = ymin + (ymax - ymin) * k / 4
        y = yv(v)
        g += (f'<line x1="{L}" y1="{y:.1f}" x2="{w-R}" y2="{y:.1f}" stroke="#ebeef5" stroke-width="1"/>'
              f'<text x="{L-8}" y="{y+4:.1f}" font-size="11" fill="#a8abb2" text-anchor="end">{int(v)}</text>')
    for i, lb in enumerate(xlabels):
        g += (f'<text x="{xs[i]:.1f}" y="{h-9}" font-size="11" fill="#a8abb2" '
              f'text-anchor="middle">{lb}</text>')
    lines = ''
    for si, s in enumerate(series):
        pts = ' '.join(f'{xs[i]:.1f},{yv(v):.1f}' for i, v in enumerate(s['vals']))
        lines += (f'<polyline points="{pts}" fill="none" stroke="{s["color"]}" '
                  f'stroke-width="2" stroke-linejoin="round"/>')
        do = ' opacity="0"' if s.get('hide_dots') else ''
        for i, v in enumerate(s['vals']):
            lines += (f'<circle cx="{xs[i]:.1f}" cy="{yv(v):.1f}" r="3.2" fill="#fff" '
                      f'stroke="{s["color"]}" stroke-width="2"{do}/>')
    for si, pi in abn:
        s = series[si]
        v = s['vals'][pi]
        lines += (f'<circle cx="{xs[pi]:.1f}" cy="{yv(v):.1f}" r="6" fill="#f56c6c" opacity="0.22"/>'
                  f'<circle cx="{xs[pi]:.1f}" cy="{yv(v):.1f}" r="4" fill="#f56c6c"/>'
                  f'<text x="{xs[pi]:.1f}" y="{yv(v)-12:.1f}" font-size="12" fill="#f56c6c" '
                  f'text-anchor="middle" font-weight="500">{v}</text>')
    lg = ''
    if len(series) > 1:
        x = L + 4
        for s in series:
            lg += (f'<rect x="{x}" y="2" width="10" height="10" rx="2" fill="{s["color"]}"/>'
                   f'<text x="{x+15}" y="11" font-size="12" fill="#606266">{s["name"]}</text>')
            x += 15 + len(s['name']) * 13 + 26
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" height="{h}" role="img">'
            f'{g}{lg}<g>{lines}</g></svg>')


def chart_bar(items, w=620, h=220, color='#409eff', unit=''):
    """items: [(label, value)]"""
    L, R, T, B = 50, 14, 14, 30
    pw, ph = w - L - R, h - T - B
    mx = max(v for _, v in items) * 1.18 or 1
    n = len(items)
    gap = pw / n
    bw = min(46, gap * 0.5)
    g = ''
    for k in range(5):
        v = mx * k / 4
        y = T + ph * (1 - k / 4)
        g += (f'<line x1="{L}" y1="{y:.1f}" x2="{w-R}" y2="{y:.1f}" stroke="#ebeef5" stroke-width="1"/>'
              f'<text x="{L-8}" y="{y+4:.1f}" font-size="11" fill="#a8abb2" text-anchor="end">{int(v)}</text>')
    bars = ''
    for i, (lb, v) in enumerate(items):
        cx = L + gap * i + gap / 2
        bh = ph * v / mx
        bars += (f'<rect x="{cx-bw/2:.1f}" y="{T+ph-bh:.1f}" width="{bw:.1f}" height="{bh:.1f}" '
                 f'rx="4" fill="{color}"/>'
                 f'<text x="{cx:.1f}" y="{T+ph-bh-7:.1f}" font-size="12" fill="#606266" '
                 f'text-anchor="middle">{v}{unit}</text>'
                 f'<text x="{cx:.1f}" y="{h-9}" font-size="11" fill="#a8abb2" '
                 f'text-anchor="middle">{lb}</text>')
    return f'<svg viewBox="0 0 {w} {h}" width="100%" height="{h}" role="img">{g}{bars}</svg>'


def chart_hbar(items, w=620, color='#409eff', unit='%', row_h=34):
    """items: [(label, value)]  value 0-100"""
    mx = max(v for _, v in items) or 1
    h = row_h * len(items) + 14
    L = 118
    pw = w - L - 62
    out = ''
    for i, (lb, v) in enumerate(items):
        y = 10 + i * row_h
        bl = pw * v / mx
        out += (f'<text x="{L-12}" y="{y+13}" font-size="12.5" fill="#606266" text-anchor="end">{lb}</text>'
                f'<rect x="{L}" y="{y+3}" width="{pw}" height="14" rx="7" fill="#f4f4f5"/>'
                f'<rect x="{L}" y="{y+3}" width="{bl:.1f}" height="14" rx="7" fill="{color}"/>'
                f'<text x="{L+pw+10}" y="{y+14}" font-size="12.5" fill="#303133">{v}{unit}</text>')
    return f'<svg viewBox="0 0 {w} {h}" width="100%" height="{h}" role="img">{out}</svg>'


def chart_ring(pct, label, sub='', size=150, color='#409eff'):
    r = 54
    c = 2 * 3.14159 * r
    off = c * (1 - pct / 100)
    return (f'<svg viewBox="0 0 {size} {size}" width="{size}" height="{size}" role="img">'
            f'<circle cx="{size/2}" cy="{size/2}" r="{r}" fill="none" stroke="#f4f4f5" stroke-width="14"/>'
            f'<circle cx="{size/2}" cy="{size/2}" r="{r}" fill="none" stroke="{color}" stroke-width="14" '
            f'stroke-dasharray="{c:.1f}" stroke-dashoffset="{off:.1f}" stroke-linecap="round" '
            f'transform="rotate(-90 {size/2} {size/2})"/>'
            f'<text x="{size/2}" y="{size/2-2}" font-size="24" font-weight="600" fill="#303133" '
            f'text-anchor="middle">{pct}%</text>'
            f'<text x="{size/2}" y="{size/2+20}" font-size="12" fill="#909399" text-anchor="middle">{sub}</text>'
            f'<text x="{size/2}" y="{size+14}" font-size="13" fill="#606266" text-anchor="middle">{label}</text>'
            f'</svg>')


# ---------------- 外壳 ----------------

def note(uid, name, states):
    return f'<div class="note-bar"><b>{uid}　{name}</b><span>覆盖状态：{states}</span></div>'


def topbar(role_label, who, avatar):
    return (f'<div class="topbar"><div class="logo"><span class="logo-mark">康</span>智能康养系统</div>'
            f'<div class="topbar-title">{role_label}</div>'
            f'<div class="topbar-right"><span>字体放大 A+</span><span>帮助</span>'
            f'<span>{who}</span><div class="avatar">{avatar}</div></div></div>')


def nav(items, active):
    out = ''
    for it in items:
        out += f'<div class="nav-item{" active" if it == active else ""}">{it}</div>'
    return f'<div class="nav">{out}</div>'


def aside_menu(groups, active):
    out = ''
    for gname, items in groups:
        if gname:
            out += f'<div class="aside-group">{gname}</div>'
        for label, ico in items:
            c = 'active' if label == active else ''
            out += (f'<div class="aside-item {c}"><span class="aside-ico">{ico}</span>{label}</div>')
    return f'<aside class="aside">{out}</aside>'


def build(uid, name, states, body, shell, active=None, elder=False, extra_css=''):
    """生成完整页面 HTML"""
    page_cls = 'page elder' if elder else 'page'
    el_css = ''
    if elder and shell == 'nav':
        el_css = '.nav-item{font-size:20px;padding:19px 24px}'

    if shell == 'plain':
        content = body
    elif shell == 'admin':
        content = (topbar('管理后台', '系统管理员', '管') +
                   f'<div class="shell-body">{aside_menu(ADMIN_MENU, active)}'
                   f'<main class="main">{body}</main></div>')
    else:
        content = topbar(ROLE_LABEL[shell], ROLE_WHO[shell], ROLE_AV[shell]) + nav(NAV[shell], active) + body

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>{uid} {name} - 康养系统</title>
{CSS}
<style>
{el_css}
{extra_css}
</style>
</head>
<body>
<div class="{page_cls}">
{note(uid, name, states)}
{content}
</div>
</body>
</html>
'''


ADMIN_MENU = [
    ('用户与权限', [('用户管理', '用'), ('角色管理', '角')]),
    ('健康与预警', [('预警规则配置', '警'), ('健康指标配置', '指'), ('知识库管理', '库'), ('统计报表', '统')]),
    ('系统', [('概览大屏', '览'), ('系统日志', '志'), ('系统公告', '告'), ('AI 模型配置', '模')]),
]

ROLE_LABEL = {'elder': '老人端', 'family': '家属端', 'care': '护工端', 'admin': '管理后台'}
ROLE_WHO = {'elder': '张桂兰', 'family': '李强', 'care': '王护工', 'admin': '系统管理员'}
ROLE_AV = {'elder': '张', 'family': '李', 'care': '王', 'admin': '管'}

NAV = {
    'elder': ['首页', '健康档案', '指标录入', 'AI 健康咨询', '通知中心', '我的'],
    'family': ['首页', '绑定老人', '健康概况', '通知中心', '我的'],
    'care': ['工作台', '老人列表', '预警处理', '处理记录', '我的'],
}
NAV_ACTIVE = {
    'elder': {'UI-ELDER-01': '首页', 'UI-ELDER-02': '健康档案', 'UI-ELDER-03': '健康档案',
              'UI-ELDER-04': '指标录入', 'UI-ELDER-05': '指标录入', 'UI-ELDER-06': '指标录入',
              'UI-ELDER-07': 'AI 健康咨询', 'UI-ELDER-08': 'AI 健康咨询',
              'UI-ELDER-09': '通知中心', 'UI-ELDER-10': '通知中心', 'UI-ELDER-11': '首页',
              'UI-ELDER-12': '健康档案', 'UI-ELDER-13': '我的', 'UI-AUTH-03': '我的'},
    'family': {'UI-FAMILY-01': '首页', 'UI-FAMILY-02': '绑定老人', 'UI-FAMILY-03': '健康概况',
               'UI-FAMILY-04': '通知中心', 'UI-FAMILY-05': '健康概况', 'UI-AUTH-03': '我的'},
    'care': {'UI-CARE-01': '工作台', 'UI-CARE-02': '老人列表', 'UI-CARE-03': '老人列表',
             'UI-CARE-04': '预警处理', 'UI-CARE-05': '处理记录', 'UI-CARE-06': '老人列表',
             'UI-AUTH-03': '我的'},
}
