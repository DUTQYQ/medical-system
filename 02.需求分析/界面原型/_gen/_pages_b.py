# -*- coding: utf-8 -*-
"""页面定义 B：家属端 5 个 + 护工端 6 个"""
from _lib import (tag, dot, card, table, pager, empty, stat_grid, filter_bar, inp, btn,
                  form_row, metric_detail, timeline, chips, chart_line, chart_bar,
                  chart_hbar, chart_ring, disclaimer)

EXTRA = """
.fam-elder-tabs { display:flex; gap:12px; margin-bottom:18px; }
.fam-elder { background:#fff; border:1px solid #ebeef5; border-radius:10px; padding:14px 20px;
  display:flex; align-items:center; gap:12px; font-size:15px; color:#606266; }
.fam-elder.on { border-color:#409eff; background:#ecf5ff; color:#409eff; font-weight:500; }
.fam-elder small { color:#909399; font-size:13px; }
.warn-card { border:1px solid #fde2e2; background:#fef0f0; border-radius:10px; padding:14px 18px; margin-bottom:12px; }
.warn-card.watch { border-color:#faecd8; background:#fdf6ec; }
.warn-h { display:flex; align-items:center; gap:10px; font-size:15px; font-weight:500; color:#303133; }
.warn-d { font-size:13px; color:#606266; margin-top:8px; line-height:1.8; }
.choice { border:1px solid #d9ecff; background:#ecf5ff; color:#409eff; border-radius:8px;
  padding:11px 16px; font-size:14px; }
.choice.on { background:#409eff; border-color:#409eff; color:#fff; }
"""


def _family_home():
    tabs = """<div class="fam-elder-tabs">
  <div class="fam-elder on">张桂兰　<small>母亲 · 72 岁 · 高风险</small></div>
  <div class="fam-elder">王秀英　<small>岳母 · 78 岁 · 正常</small></div>
  <div class="fam-elder" style="color:#c0c4cc">+ 绑定更多老人</div>
</div>"""
    warns = ''
    for lvl, cls, txt, meta in [
        ('高风险', 'danger', '血压 185/100 mmHg，超出高风险阈值 ≥180 mmHg', '2026-09-14 16:30 · 未读'),
        ('高风险', 'danger', '血压 178/102 mmHg，超出高风险阈值', '2026-09-13 20:10 · 已处理'),
        ('关注', 'warning', '收缩压连续 3 天偏高（165→170→178）', '2026-09-12 08:05 · 已读'),
    ]:
        wcls = 'warn-card' if cls == 'danger' else 'warn-card watch'
        warns += f"""<div class="{wcls}"><div class="warn-h">{tag(lvl, cls)}{txt}</div>
<div class="warn-d">{meta} · 张桂兰</div></div>"""
    body = f'<div style="padding:22px 26px 34px"><div class="crumb">家属端 / <b>健康看板</b></div>' \
           f'{tabs}' \
           f'{stat_grid([("今日血压", "185/100", "mmHg", "高风险 · 16:30 测量"), ("今日心率", "78", "次/分", "正常"), ("今日血糖", "6.8", "mmol/L", "偏高"), ("未读预警", "1", "条", "红点已亮")])}' \
           f'<div class="grid-2-1"><div>{card("最近预警（按风险等级置顶）", warns + "<div style=\'height:6px\'></div>" + btn("查看全部预警", False, True))}</div>' \
           f'<div>{card("快捷操作", """<div style="display:flex;flex-direction:column;gap:12px">
<button class="btn btn-primary" style="height:46px;font-size:15px">代老人录入指标</button>
<button class="btn" style="height:46px;font-size:15px">代老人发起 AI 咨询</button>
<button class="btn" style="height:46px;font-size:15px">查看健康趋势</button>
<button class="btn" style="height:46px;font-size:15px">联系责任护工 王护工</button></div>""")}' \
           f'<div style="height:18px"></div>{card("数据归属", """<div class="alert-info" style="margin-bottom:10px">看板只展示你已生效绑定的老人数据，切换老人时上下文与 AI 会话会同步重置。</div><div class="alert-warn">未绑定的老人不会出现在上方选择器中，直接访问其地址返回 1002 无权限。</div>""")}</div></div>' \
           f'<div style="height:18px"></div><div class="grid-2">' \
           f'<div>{card("无绑定老人（空态）", empty("你还没有绑定任何老人", "绑定并得到老人确认后，这里会显示他的健康看板", "空") + "<div style=\'height:12px\'></div>" + btn("去绑定老人", True))}</div>' \
           f'<div>{card("权限隔离边界", """<div class="alert-info" style="margin-bottom:12px">家属只能看到已生效绑定的老人；绑定处于待确认时，接口返回 1002，界面提示“该老人尚未授权你查看数据”。</div><div class="alert-warn">多位家属绑定同一老人时，各自的处理记录互相可见，但已读状态彼此独立，避免出现“我看到了但没处理”的责任真空。</div>""")}</div></div>' \
           f'<div style="margin-top:18px">{disclaimer()}</div></div>'
    return ('UI-FAMILY-01', '家属首页', '正常 / 多老人切换 / 无绑定老人（空态）/ 未读红点',
            'family', '首页', False, body, EXTRA)


def _family_bind():
    form = ''
    form += form_row('老人手机号', '<div class="inp" style="color:#303133;min-width:230px">130 0000 0002</div><span class="unit">系统按手机号定位老人账号</span>', req=True)
    form += form_row('与老人的关系', '<div class="inp inp-sel" style="color:#303133">儿子</div>')
    form += form_row('真实姓名', '<div class="inp" style="color:#303133;min-width:200px">李强</div>')
    form += form_row('申请说明', '<div class="inp ph" style="min-width:340px">选填，如：我是长子，负责日常照护</div>')
    status = table(['老人', '关系', '申请时间', '状态', '可见数据', '操作'],
                   [['张桂兰', '儿子', '2026-09-13 19:02', tag('已生效', 'success'), '全部可见', btn('解除绑定', False, True)],
                    ['王秀英', '女婿', '2026-09-14 15:48', tag('待老人确认', 'warning'), '<span style="color:#c0c4cc">不可见</span>', btn('撤回申请', False, True)],
                    ['刘建国', '侄子', '2026-09-10 11:20', tag('已被拒绝', 'danger'), '<span style="color:#c0c4cc">不可见</span>', btn('重新申请', False, True)]])
    body = f'<div style="padding:22px 26px 34px"><div class="crumb">家属端 / <b>绑定老人</b></div>' \
           f'<div class="grid-1-2"><div>{card("提交绑定申请", form + "<div style=\'height:14px\'></div>" + btn("提交申请", True))}</div>' \
           f'<div>{card("我的绑定关系", status)}' \
           f'<div style="height:18px"></div>{card("绑定授权规则（关键）", """<div class="alert-warn" style="margin-bottom:12px"><b>申请提交后必须由老人本人在老人端同意，绑定才生效。</b>在待确认期间，家属端看不到该老人的任何数据，包括档案、指标、预警与 AI 咨询上下文。</div><div class="alert-info" style="margin-bottom:10px">解绑后权限立即失效，但历史处理记录仍保留可追溯，不会被删除。</div><div class="alert-info">同一老人最多可绑定 5 名家属，上限取自 sys_config（family_bind_max），不写死在代码里。</div>""")}</div></div>' \
           f'<div style="height:18px"></div><div class="grid-2">' \
           f'<div>{card("无申请记录（空态）", empty("还没有绑定任何老人", "提交申请后需要老人确认，确认通过才可查看数据", "空"))}</div>' \
           f'<div>{card("解绑二次确认（弹窗形态示意）", """<div style="border:1px solid #ebeef5;border-radius:10px;overflow:hidden"><div style="background:#fafafa;padding:11px 15px;font-size:13px;color:#909399">解除与张桂兰的绑定？</div><div style="padding:18px"><div style="font-size:14px;color:#606266;line-height:1.8;margin-bottom:16px">解除后你将立即无法查看该老人的健康数据与预警通知。此操作可重新申请，但需老人再次确认。</div><div style="display:flex;gap:10px;justify-content:flex-end"><button class="btn btn-sm">取消</button><button class="btn btn-sm" style="background:#f56c6c;border-color:#f56c6c;color:#fff">确认解除</button></div></div></div>""")}</div>' \
           f'</div>{disclaimer()}</div>'
    return ('UI-FAMILY-02', '绑定老人', '正常 / 待确认（数据不可见）/ 已被拒绝 / 解绑二次确认 / 超出绑定上限',
            'family', '绑定老人', False, body, EXTRA)


def _family_overview():
    chart = chart_line(
        [{'name': '收缩压', 'color': '#409eff', 'vals': [165, 170, 178, 185]},
         {'name': '舒张压', 'color': '#67c23a', 'vals': [95, 98, 102, 100]}],
        ['9/11', '9/12', '9/13', '9/14'], ymin=80, ymax=200, w=600, h=210, abn=[(0, 3)])
    prof = ''.join(f'<div class="form-row" style="padding:13px 0"><div class="form-label" style="width:120px">{k}</div>'
                   f'<div class="form-ctrl" style="font-size:15px;color:#303133">{v}</div></div>'
                   for k, v in [('姓名', '张桂兰'), ('年龄', '72 岁'), ('慢病', '高血压、2 型糖尿病'),
                                ('过敏史', '青霉素过敏'), ('紧急联系人', '李强（本人）· 130 0000 0003'),
                                ('责任护工', '王护工 · 130 0000 0004')])
    body = f'<div style="padding:22px 26px 34px"><div class="crumb">家属端 / <b>张桂兰 · 老人健康概况</b></div>' \
           f'{stat_grid([("最近血压", "185/100", "mmHg", "高风险 · 09-14 16:30"), ("最近心率", "78", "次/分", "正常"), ("最近血糖", "6.8", "mmol/L", "偏高"), ("近 7 天预警", "3", "条", "高风险 2 条")])}' \
           f'<div class="grid-2-1"><div>{card("近 7 天血压趋势", chart)}' \
           f'<div style="height:18px"></div>{card("健康档案摘要", prof)}</div>' \
           f'<div>{card("代管操作", """<div style="display:flex;flex-direction:column;gap:12px">
<button class="btn btn-primary" style="height:44px">代录健康指标</button>
<button class="btn" style="height:44px">代发起 AI 咨询</button>
<button class="btn" style="height:44px">查看完整档案</button>
<button class="btn" style="height:44px">导出近 30 天记录</button></div>
<div class="hint" style="margin-top:14px">代录的数据会标注录入人，与老人自录的数据区分记录，便于追溯。</div>""")}' \
           f'<div style="height:18px"></div>{card("权限与空数据", """<div class="alert-warn" style="margin-bottom:10px"><b>无权限：</b>未生效绑定的老人，任何请求返回 1002，界面直接提示“你无权查看该老人数据”，而不是显示空卡片。</div><div class="alert-info" style="margin-bottom:10px"><b>空数据：</b>老人尚无指标时，趋势区显示“数据积累中”，其余信息正常展示。</div><div class="alert-info">AI 咨询上下文按老人切换，切回后不会串到另一位老人的档案。</div>""")}</div></div>' \
           f'<div style="margin-top:18px">{disclaimer()}</div></div>'
    return ('UI-FAMILY-03', '老人健康概况', '正常 / 无权限（未绑定）/ 空数据（无指标）/ 代录数据',
            'family', '健康概况', False, body, EXTRA)


def _family_notice():
    rows = [
        [tag('未读', 'danger'), tag('高风险', 'danger'), '张桂兰', '血压 185/100 mmHg 超阈值', '09-14 16:30', tag('处理中', 'warning'), btn('处理', True, True)],
        [tag('已读', 'info'), tag('高风险', 'danger'), '张桂兰', '血压 178/102 mmHg 超阈值', '09-13 20:10', tag('已处理', 'success'), btn('查看', False, True)],
        [tag('已读', 'info'), tag('关注', 'warning'), '张桂兰', '收缩压连续 3 天偏高', '09-12 08:05', tag('已处理', 'success'), btn('查看', False, True)],
        [tag('未读', 'danger'), tag('关注', 'warning'), '王秀英', '睡眠 4.0 小时，连续 2 天偏少', '09-14 07:30', tag('待处理', 'danger'), btn('处理', True, True)],
    ]
    choices = ''.join(f'<span class="choice{" on" if i == 0 else ""}">{t}</span>'
                      for i, t in enumerate(['已电话联系老人', '已上门查看', '已协助就医', '稍后处理']))
    body = f'<div style="padding:22px 26px 34px"><div class="crumb">家属端 / <b>通知中心</b></div>' \
           f'{stat_grid([("未读通知", "2", "条", "家属端红点已亮"), ("待我处理", "2", "条", "按风险等级排序"), ("本周已处理", "3", "条", "平均响应 12 分钟"), ("接收方式", "站内通知", "", "无短信 / 电话")])}' \
           f'{filter_bar([inp("全部老人", sel=True), inp("全部状态", sel=True), inp("全部级别", sel=True), btn("只看未读", True), btn("批量标为已读")])}' \
           f'{card("预警通知", table(["我的状态", "级别", "老人", "预警内容", "时间", "处理状态", "操作"], rows) + pager(1, 2, 14))}' \
           f'<div style="height:18px"></div><div class="grid-2-1">' \
           f'<div>{card("登记处理结果", f"<div style=\'font-size:14px;color:#606266;margin-bottom:12px\'>预警 #40001 · 张桂兰 · 血压 185/100 mmHg</div>{choices}<div style=\'height:14px\'></div>" + form_row('处理说明', '<div class="inp ph" style="min-width:330px">如：已电话联系，安排傍晚复测</div>') + form_row('是否已联系老人', '<div class="inp inp-sel" style="color:#303133">已联系</div>') + "<div style=\'height:12px\'></div>" + btn("提交处理结果", True) + "　" + btn("稍后处理"))}</div>' \
           f'<div>{card("状态正交说明", """<div class="alert-info" style="margin-bottom:12px">“我的状态”只表示我是否已读；“处理状态”是全局共享的。我先读了但没处理，另一位家属处理后，我这条仍显示未读，列表里会提示“已由李强于 16:41 处理”。</div><div class="alert-warn">30 秒轮询未读数；网络中断时保留上一次结果并提示“数据可能不是最新”。</div>""")}' \
           f'</div></div><div style="margin-top:18px">{disclaimer()}</div></div>'
    return ('UI-FAMILY-04', '通知中心', '正常 / 未读红点 / 已被他人处理 / 提交失败重试 / 已读与处理状态正交',
            'family', '通知中心', False, body, EXTRA)


def _family_report():
    bars = chart_bar([('9/8', 3), ('9/9', 2), ('9/10', 4), ('9/11', 5), ('9/12', 3), ('9/13', 6), ('9/14', 4)],
                     w=600, h=210, unit=' 次')
    avg = chart_line([{'name': '收缩压均值', 'color': '#409eff', 'vals': [148, 152, 150, 156, 160, 158, 165]}],
                     ['9/8', '9/9', '9/10', '9/11', '9/12', '9/13', '9/14'], ymin=120, ymax=180, w=600, h=200)
    body = f'<div style="padding:22px 26px 34px"><div class="crumb">家属端 / <b>健康日报周报</b></div>' \
           f'{filter_bar([inp("张桂兰", sel=True), inp("本周（09-08 ~ 09-14）", sel=True), btn("查询", True), btn("导出 PDF"), btn("发送到邮箱")])}' \
           f'{stat_grid([("本周测量次数", "27", "次", "较上周 +6"), ("平均收缩压", "165", "mmHg", "较上周 +9"), ("高风险预警", "2", "次", "均为血压"), ("打卡完成率", "78", "%", "较上周 +9%")])}' \
           f'<div class="grid-2 mb">{card("每日测量次数", bars)}{card("收缩压均值走势", avg)}</div>' \
           f'<div class="grid-2-1"><div>{card("本周小结（自动生成，可编辑）", """<div style="font-size:14px;color:#606266;line-height:1.95">
本周血压整体呈上升趋势，平均收缩压 165 mmHg，高于上周的 156 mmHg。9 月 13 日、14 日连续两天达到高风险等级，已触发预警并由家属李强登记处理。<br>
睡眠时长 5.5 小时，低于建议值；日均步数 3200 步。建议下周保持每日一次晨间血压测量，并关注睡眠情况。</div>
<div class="hint" style="margin-top:14px">小结由规则统计生成，AI 仅负责自然语言表达；模型不可用时回退为纯数据表格。</div>""")}</div>' \
           f'<div>{card("状态说明", """<div class="alert-warn" style="margin-bottom:12px">【选配】健康日报 / 周报为可裁剪项，若工期不足可整体下线，不影响核心预警闭环。</div><div class="alert-info" style="margin-bottom:10px"><b>数据不足：</b>本周记录少于 3 条时，提示“数据量不足，暂不生成周报”，仅给出原始记录清单。</div><div class="alert-info">导出内容不含 AI 建议，仅含客观测量数据，避免被当作诊断依据。</div>""")}</div></div></div>'
    return ('UI-FAMILY-05', '健康日报周报', '正常 / 数据不足（<3 条）/ 导出失败 / AI 不可用时回退表格',
            'family', '健康概况', False, body, EXTRA)


# ---------------- 护工端 ----------------

def _care_workbench():
    todo = ''
    for lvl, cls, who, txt, t in [
        ('高风险', 'danger', '张桂兰', '血压 185/100 mmHg，家属已登记处理，待护工确认', '16:30'),
        ('高风险', 'danger', '王秀英', '睡眠 4.0 小时连续 2 天，指标异常', '07:30'),
        ('关注', 'warning', '刘建国', '收缩压 152 mmHg 连续 3 天偏高', '09:10'),
    ]:
        wcls = 'warn-card' if cls == 'danger' else 'warn-card watch'
        todo += f"""<div class="{wcls}"><div class="warn-h">{tag(lvl, cls)}{who}　{txt}</div>
<div class="warn-d">{t} · 待我处理　{btn('立即处理', True, True)} {btn('标记已查看', False, True)}</div></div>"""
    body = f'<div style="padding:22px 26px 34px"><div class="crumb">护工端 / <b>今日工作台</b></div>' \
           f'{stat_grid([("负责老人", "6", "位", "其中高风险 2 位"), ("待处理预警", "3", "条", "高风险 2 条"), ("今日打卡异常", "1", "位", "王秀英 睡眠偏少"), ("我今日已处理", "4", "条", "平均响应 9 分钟")])}' \
           f'<div class="grid-2-1"><div>{card("待办事项（高风险置顶）", todo)}</div>' \
           f'<div>{card("快捷入口", """<div style="display:flex;flex-direction:column;gap:12px">
<button class="btn btn-primary" style="height:44px">查看负责老人列表</button>
<button class="btn" style="height:44px">进入预警处理</button>
<button class="btn" style="height:44px">查看我的处理记录</button></div>""")}' \
           f'<div style="height:18px"></div>{card("待办清零（空态）", empty("今日待办已全部处理", "如有新预警，会在 30 秒内出现在这里", "空"))}</div></div>' \
           f'<div style="height:18px"></div>{card("职责与权限边界", """<div class="alert-info" style="margin-bottom:10px">护工只能看到管理员分配给自己的老人；未分配的老人不出现在列表中，直接访问其档案返回 1002 无权限。</div><div class="alert-warn">护工不参与家属绑定审批，也不能修改老人档案，只做指标查看、预警处理与记录留痕。</div>""")}</div>' \
           f'<div style="margin-top:18px">{disclaimer()}</div></div>'
    return ('UI-CARE-01', '护工工作台', '正常 / 待办清零（空态）/ 高风险置顶 / 无负责老人',
            'care', '工作台', False, body, EXTRA)


def _care_elders():
    rows = [
        [dot('danger') + '<span class="strong">张桂兰</span>', '72 岁', '高血压 2 级（很高危）', '185/100', tag('高风险', 'danger'), '16:30 血压预警待处理'],
        [dot('danger') + '<span class="strong">王秀英</span>', '78 岁', '冠心病、失眠', '138/86', tag('高风险', 'danger'), '今日睡眠 4.0 小时'],
        [dot('watch') + '<span class="strong">刘建国</span>', '69 岁', '高血压 1 级', '152/94', tag('关注', 'warning'), '连续 3 天收缩压偏高'],
        [dot('normal') + '<span class="strong">陈淑芬</span>', '81 岁', '骨质疏松', '128/80', tag('正常', 'success'), '指标平稳'],
        [dot('normal') + '<span class="strong">赵德海</span>', '75 岁', '2 型糖尿病', '132/84', tag('正常', 'success'), '指标平稳'],
        [dot('normal') + '<span class="strong">孙玉兰</span>', '77 岁', '高血压 1 级', '130/82', tag('正常', 'success'), '指标平稳'],
    ]
    body = f'<div style="padding:22px 26px 34px"><div class="crumb">护工端 / <b>负责老人列表</b></div>' \
           f'{filter_bar([inp("姓名 / 手机号"), inp("全部状态", sel=True), inp("全部慢病", sel=True), btn("查询", True), btn("重置")])}' \
           f'{card("我负责的老人（按状态分色，高风险置顶）", table(["姓名", "年龄", "主要慢病", "最近血压", "状态", "最近异常"], rows) + pager(1, 2, 6))}' \
           f'<div style="height:18px"></div><div class="grid-2">' \
           f'<div>{card("状态分色规则", """<div class="form-row" style="padding:12px 0"><div class="form-label" style="width:110px">正常</div><div class="form-ctrl">""" + dot('normal') + """近 3 天无异常指标</div></div>
<div class="form-row" style="padding:12px 0"><div class="form-label" style="width:110px">关注</div><div class="form-ctrl">""" + dot('watch') + """存在偏高记录或连续异常趋势</div></div>
<div class="form-row" style="padding:12px 0"><div class="form-label" style="width:110px">异常</div><div class="form-ctrl">""" + dot('danger') + """存在未处理的 level 3 高风险预警</div></div>""")}</div>' \
           f'<div>{card("空数据状态", empty("当前没有分配给你的老人", "请联系管理员在“管理交接”中分配负责老人", "空"))}</div>' \
           f'</div><div style="margin-top:18px">{disclaimer()}</div></div>'
    return ('UI-CARE-02', '负责老人列表', '正常 / 状态分色 / 高风险置顶 / 筛选无结果 / 未分配老人（空态）',
            'care', '老人列表', False, body, EXTRA)


def _care_profile():
    prof = ''.join(f'<div class="form-row" style="padding:13px 0"><div class="form-label" style="width:120px">{k}</div>'
                   f'<div class="form-ctrl" style="font-size:15px;color:#303133">{v}</div></div>'
                   for k, v in [('姓名', '张桂兰'), ('性别 / 年龄', '女 · 72 岁'), ('身高 / 体重', '158 cm · 62 kg'),
                                ('慢病标签', '高血压、2 型糖尿病'), ('过敏史', '青霉素过敏'),
                                ('既往病史', '2018 年脑梗，恢复良好'),
                                ('紧急联系人', '李强（儿子）· 130 0000 0003')])
    rows = [
        ['2026-09-14 16:30', '血压', '185/100', tag('高风险', 'danger')],
        ['2026-09-13 20:10', '血压', '178/102', tag('高风险', 'danger')],
        ['2026-09-12 08:05', '血压', '170/98', tag('偏高', 'warning')],
        ['2026-09-12 08:20', '心率', '76', tag('正常', 'success')],
    ]
    body = f'<div style="padding:22px 26px 34px"><div class="crumb">护工端 / <b>老人档案查看（只读）</b></div>' \
           f'<div class="grid-2-1"><div>{card("健康档案", prof)}' \
           f'<div style="height:18px"></div>{card("最近指标", table(["时间", "指标", "数值", "判定"], rows) + "<div style=\'height:10px\'></div>" + btn("查看全部记录", False, True))}</div>' \
           f'<div>{card("只读说明", """<div class="alert-info" style="margin-bottom:12px">护工对档案为只读权限：可查看档案与指标、可处理预警、可查看处理记录，<b>不可修改</b>任何健康数据。</div><div class="alert-warn" style="margin-bottom:12px">需要修正数据时，应由老人本人或已绑定家属操作，避免责任不清。</div><div class="alert-info">档案变更时间线可追溯到具体操作人与时间。</div>""")}' \
           f'<div style="height:18px"></div>{card("无权限状态", """<div class="alert-warn">查看未分配给自己的老人档案时返回 1002 无权限，界面提示“该老人不在你的负责范围内”，不展示任何字段。</div>""")}</div>' \
           f'</div></div><div style="margin-top:18px">{disclaimer()}</div></div>'
    return ('UI-CARE-03', '老人档案查看', '正常（只读）/ 无权限（非负责老人）/ 空数据 / 字段脱敏',
            'care', '老人列表', False, body, EXTRA)


def _care_handle():
    rows = [
        [tag('高风险', 'danger'), '张桂兰', '血压 185/100 mmHg', '09-14 16:30', tag('处理中', 'warning'), btn('处理', True, True)],
        [tag('高风险', 'danger'), '王秀英', '睡眠 4.0 小时', '09-14 07:30', tag('待处理', 'danger'), btn('处理', True, True)],
        [tag('关注', 'warning'), '刘建国', '收缩压 152 mmHg', '09-14 09:10', tag('已处理', 'success'), btn('查看', False, True)],
    ]
    choices = ''.join(f'<span class="choice{" on" if i == 0 else ""}">{t}</span>'
                      for i, t in enumerate(['已上门查看', '已电话联系', '已协助就医', '已转交家属']))
    form = f"""<div style="font-size:14px;color:#606266;margin-bottom:12px">预警 #40002 · 王秀英 · 睡眠 4.0 小时</div>
{choices}
<div style="height:14px"></div>
{form_row('处理说明', '<div class="inp ph" style="min-width:320px">如：已上门查看，老人状态平稳</div>', req=True)}
{form_row('处理时间', '<div class="inp" style="color:#303133">2026-09-14 17:05</div><span class="unit">默认当前时间，可修改</span>')}
<div style="height:14px"></div>{btn("提交处理结果", True)}　{btn("暂不处理")}"""
    body = f'<div style="padding:22px 26px 34px"><div class="crumb">护工端 / <b>预警处理</b></div>' \
           f'{filter_bar([inp("全部老人", sel=True), inp("待处理", sel=True), inp("全部级别", sel=True), btn("查询", True)])}' \
           f'{card("待处理预警", table(["级别", "老人", "预警内容", "时间", "状态", "操作"], rows) + pager(1, 2, 9))}' \
           f'<div style="height:18px"></div><div class="grid-2-1">' \
           f'<div>{card("登记处理结果", form)}</div>' \
           f'<div>{card("并发与失败状态", """<div class="alert-warn" style="margin-bottom:12px"><b>已被他人处理：</b>提交时若该预警已被家属或其他护工处理，提示“该预警已由李强于 16:41 处理”，并展示对方的处理结果，不覆盖他人记录。</div><div class="alert-warn" style="margin-bottom:12px"><b>提交失败：</b>网络异常时按钮变为“提交失败，点击重试”，已填内容不丢失。</div><div class="alert-info">处理状态为全局状态，一次处理即对所有接收人可见，避免重复上门。</div>""")}</div></div>' \
           f'<div style="margin-top:18px">{disclaimer()}</div></div>'
    return ('UI-CARE-04', '预警处理', '正常 / 已被他人处理（并发）/ 提交失败重试 / 必填校验 / 无待处理（空态）',
            'care', '预警处理', False, body, EXTRA)


def _care_records():
    rows = [
        ['2026-09-14 17:05', '王秀英', '睡眠 4.0 小时', '已上门查看', '已上门查看，老人状态平稳，已提醒早睡', '王护工'],
        ['2026-09-14 14:20', '刘建国', '收缩压 152 mmHg', '已电话联系', '已电话联系，建议傍晚复测，老人同意', '王护工'],
        ['2026-09-13 20:35', '张桂兰', '血压 178/102 mmHg', '已电话联系', '家属已到场，陪同复测 168/98，暂不需送医', '王护工'],
        ['2026-09-12 09:00', '陈淑芬', '心率 105 次/分', '已协助就医', '陪同前往社区医院，诊断为窦性心动过速', '王护工'],
    ]
    body = f'<div style="padding:22px 26px 34px"><div class="crumb">护工端 / <b>处理记录</b></div>' \
           f'{stat_grid([("我处理的预警", "18", "条", "本月累计"), ("平均响应时长", "9", "分钟", "较上月 -3 分钟"), ("协助就医", "2", "次", "本月"), ("被家属先行处理", "5", "条", "未重复上门")])}' \
           f'{filter_bar([inp("开始日期"), inp("结束日期"), inp("全部老人", sel=True), inp("全部处理方式", sel=True), btn("查询", True), btn("导出记录")])}' \
           f'{card("我的处理记录（可追溯）", table(["处理时间", "老人", "预警内容", "处理方式", "处理说明", "处理人"], rows) + pager(1, 5, 18))}' \
           f'<div style="height:18px"></div><div class="grid-2">' \
           f'<div>{card("空数据状态", empty("还没有处理记录", "处理预警后，这里会留下完整痕迹", "空"))}</div>' \
           f'<div>{card("可追溯要求", """<div class="alert-info" style="margin-bottom:12px">每条记录至少包含：处理人、处理方式、处理说明、处理时间，四项缺一不可。</div><div class="alert-warn">记录一经提交不可修改，如需补充说明应新增一条记录，保证留痕真实。</div>""")}</div>' \
           f'</div><div style="margin-top:18px">{disclaimer()}</div></div>'
    return ('UI-CARE-05', '处理记录', '正常 / 空数据 / 按时间与老人筛选 / 导出',
            'care', '处理记录', False, body, EXTRA)


def _care_handover():
    form = ''
    form += form_row('选择老人', '<div class="inp inp-sel" style="color:#303133;min-width:220px">张桂兰（72 岁 · 高血压）</div>', req=True)
    form += form_row('交接类型', '<div class="inp inp-sel" style="color:#303133;min-width:180px">转交他人</div>')
    form += form_row('接收护工', '<div class="inp inp-sel" style="color:#303133;min-width:200px">刘护工（当前负责 4 位老人）</div>')
    form += form_row('生效时间', '<div class="inp" style="color:#303133">2026-09-15 08:00</div>')
    form += form_row('交接说明', '<div class="inp ph" style="min-width:330px">如：我下周休假，张桂兰近期血压不稳，需重点关注</div>')
    rows = [
        ['2026-09-10 09:00', '张桂兰', '管理员 → 王护工', '初始分配', tag('已生效', 'success')],
        ['2026-08-28 15:30', '陈淑芬', '李护工 → 王护工', '休假交接', tag('已生效', 'success')],
    ]
    body = f'<div style="padding:22px 26px 34px"><div class="crumb">护工端 / <b>管理交接</b></div>' \
           f'<div class="grid-2-1"><div>{card("发起交接", form + "<div style=\'height:14px\'></div>" + btn("提交交接", True))}' \
           f'<div style="height:18px"></div>{card("交接记录", table(["时间", "老人", "交接路径", "类型", "状态"], rows))}</div>' \
           f'<div>{card("说明", """<div class="alert-warn" style="margin-bottom:12px">【选配】管理交接为可裁剪项，对应表 care_relation；本期核心流程中，老人由管理员在后台直接分配。</div><div class="alert-info" style="margin-bottom:10px">交接生效后，原护工立即失去该老人的查看与处理权限，未处理预警自动转给接收护工。</div><div class="alert-info">交接不会删除历史处理记录，接收护工可查到前任的全部处理痕迹，避免照护断层。</div>""")}' \
           f'<div style="height:18px"></div>{card("空数据状态", empty("还没有交接记录", "需要休假或调整负责范围时，可在此发起交接", "空"))}</div></div></div>' \
           f'<div style="margin-top:18px">{disclaimer()}</div></div>'
    return ('UI-CARE-06', '管理交接', '正常 / 空数据 / 交接后权限立即切换 / 未处理预警转移',
            'care', '老人列表', False, body, EXTRA)


def pages():
    return [_family_home(), _family_bind(), _family_overview(), _family_notice(), _family_report(),
            _care_workbench(), _care_elders(), _care_profile(), _care_handle(), _care_records(), _care_handover()]
