# -*- coding: utf-8 -*-
"""页面定义 C：管理员端 10 个"""
from _lib import (tag, dot, card, table, pager, empty, stat_grid, filter_bar, inp, btn,
                  form_row, metric_detail, timeline, chips, chart_line, chart_bar,
                  chart_hbar, chart_ring, disclaimer)

ADM_CSS = """
.tree { font-size:14px; }
.tree-i { padding:9px 12px; border-radius:6px; color:#606266; display:flex; align-items:center; gap:8px; }
.tree-i.on { background:#ecf5ff; color:#409eff; font-weight:500; }
.tree-i.sub { padding-left:28px; }
.kv { display:grid; grid-template-columns:1fr 1fr; gap:14px 18px; }
.kv-l { font-size:13px; color:#909399; margin-bottom:6px; }
.kv-v { font-size:15px; color:#303133; }
.mod-card { border:1px solid #ebeef5; border-radius:10px; padding:16px 18px; background:#fff; }
.mod-card.on { border-color:#409eff; background:#f5faff; }
.mod-t { font-size:16px; font-weight:600; color:#303133; margin-bottom:6px; display:flex; align-items:center; gap:8px; }
.mod-d { font-size:13px; color:#909399; line-height:1.8; }
.code { font-family:Consolas,Monaco,monospace; font-size:13px; color:#303133; background:#fafafa;
  border:1px solid #ebeef5; border-radius:6px; padding:2px 8px; }
.screen-stat { background:#fff; border:1px solid #ebeef5; border-radius:12px; padding:20px 22px; }
.screen-v { font-size:40px; font-weight:600; color:#303133; line-height:1.15; }
.screen-l { font-size:15px; color:#909399; margin-bottom:10px; }
.screen-s { font-size:13px; color:#67c23a; margin-top:8px; }
"""


def _adm_users():
    rows = [
        ['130 0000 0001', '系统管理员', tag('管理员', 'primary'), 'ADMIN', tag('正常', 'success'), '2026-09-08 09:00', btn('编辑', False, True)],
        ['130 0000 0002', '张桂兰', tag('老年用户', 'info'), 'ELDER', tag('正常', 'success'), '2026-09-08 09:14', btn('编辑', False, True) + ' ' + btn('禁用', False, True)],
        ['130 0000 0003', '李强', tag('家属', 'warning'), 'FAMILY', tag('正常', 'success'), '2026-09-13 19:02', btn('编辑', False, True) + ' ' + btn('禁用', False, True)],
        ['130 0000 0004', '王护工', tag('护工', 'success'), 'CARE', tag('正常', 'success'), '2026-09-10 09:00', btn('编辑', False, True) + ' ' + btn('禁用', False, True)],
        ['130 0000 0007', '张敏', tag('家属', 'warning'), 'FAMILY', tag('已禁用', 'danger'), '2026-09-14 10:31', btn('启用', True, True)],
    ]
    body = f'<div class="crumb">用户与权限 / <b>用户管理</b></div>' \
           f'{stat_grid([("用户总数", "38", "人", "本月新增 12"), ("老年用户", "14", "人", "含 2 位未完善档案"), ("家属账号", "16", "人", "已生效绑定 21 条"), ("护工 / 管理员", "8", "人", "护工 6 · 管理员 2")])}' \
           f'{filter_bar([inp("手机号 / 姓名"), inp("全部角色", sel=True), inp("全部状态", sel=True), btn("查询", True), btn("重置"), btn("新增用户", True)])}' \
           f'{card("用户列表", table(["手机号", "姓名", "角色", "角色代码", "状态", "注册时间", "操作"], rows) + pager(1, 5, 38))}' \
           f'<div style="height:18px"></div><div class="grid-2">' \
           f'<div>{card("空结果状态", empty("没有符合条件的用户", "换个手机号或清空筛选条件再试", "空"))}</div>' \
           f'<div>{card("禁用与权限说明", """<div class="alert-warn" style="margin-bottom:12px"><b>禁用后立即不可登录</b>，已签发的令牌在下次校验时失效；禁用不影响其历史产生的健康数据与处理记录。</div><div class="alert-info" style="margin-bottom:10px">管理员账号不可自助注册，只能由既有管理员创建，且不允许禁用自己。</div><div class="alert-info">删除用户为高危操作，本期不提供硬删除，统一使用禁用。</div>""")}</div>' \
           f'</div>'
    return ('UI-ADMIN-01', '用户管理', '正常 / 筛选无结果 / 禁用后不可登录 / 新增校验失败 / 不允许禁用自己',
            'admin', '用户管理', False, body, ADM_CSS)


def _adm_roles():
    roles = ''
    for name, code, desc, n in [('系统管理员', 'ADMIN', '全部权限，含用户与配置管理', 2),
                                ('老年用户', 'ELDER', '本人健康数据、AI 咨询、预警通知', 14),
                                ('家属', 'FAMILY', '仅限已生效绑定老人的数据与预警', 16),
                                ('护工', 'CARE', '仅限被分配老人的档案查看与预警处理', 6)]:
        roles += f"""<div class="mod-card" style="margin-bottom:12px"><div class="mod-t">{name}
<span class="tag tag-info">{code}</span><span style="margin-left:auto;font-size:13px;color:#909399">{n} 人</span></div>
<div class="mod-d">{desc}</div></div>"""
    perms = [
        ('健康档案', ['查看', '编辑', '删除']),
        ('健康指标', ['查看', '录入', '代录', '导出']),
        ('预警通知', ['接收', '处理', '配置规则']),
        ('AI 健康咨询', ['发起', '查看历史', '查看他人']),
        ('用户与角色', ['查看', '新增', '禁用', '分配角色']),
        ('系统配置', ['查看', '修改阈值', '修改模型']),
    ]
    grid = ''
    for k, items in perms:
        cks = ''
        on_map = {
            '健康档案': ['查看', '编辑', '删除'],
            '健康指标': ['查看', '录入', '代录', '导出'],
            '预警通知': ['接收', '处理', '配置规则'],
            'AI 健康咨询': ['发起', '查看历史'],
            '用户与角色': [],
            '系统配置': [],
        }
        for it in items:
            cks += f'<span class="ck{" on" if it in on_map[k] else ""}">{it}</span>'
        grid += f'<div class="perm-k">{k}</div><div>{cks}</div>'
    body = f'<div class="crumb">用户与权限 / <b>角色管理</b></div>' \
           f'<div class="grid-1-2"><div>{card("系统内置角色", roles + "<div class=\'hint\'>内置角色不可删除，仅可调整权限项</div>")}</div>' \
           f'<div>{card("权限分配 · 当前角色：系统管理员", f"<div class=\'perm\'>{grid}</div>" + "<div style=\'height:16px\'></div>" + btn("保存权限", True) + "　" + btn("恢复默认"))}' \
           f'<div style="height:18px"></div>{card("权限模型说明", """<div class="alert-info" style="margin-bottom:10px">系统为固定四角色模型（ADMIN / ELDER / FAMILY / CARE），不开放自由建角色，避免权限组合失控。</div><div class="alert-warn">权限校验在接口层强制执行，界面隐藏仅作为体验优化，不作为安全边界。</div>""")}</div></div>' \
           f'<div style="height:18px"></div>{card("只读状态", """<div class="alert-info">老年用户与家属角色的核心权限由业务规则决定（如家属只能看已绑定老人），在界面上以置灰只读方式展示，不允许取消勾选。</div>""")}</div>'
    return ('UI-ADMIN-02', '角色管理', '正常 / 权限只读（业务规则锁定项）/ 保存失败 / 恢复默认',
            'admin', '角色管理', False, body, ADM_CSS)


def _adm_rules():
    def row(name, key, unit, normal, watch, high, src):
        return [f'<span class="strong">{name}</span><div style="font-size:12px;color:#909399;margin-top:2px"><span class="code">{key}</span></div>',
                f'<div class="inp" style="height:34px;color:#303133;min-width:96px">{normal}</div><span class="unit">{unit}</span>',
                f'<div class="inp" style="height:34px;color:#303133;min-width:96px">{watch}</div>',
                f'<div class="inp" style="height:34px;color:#303133;min-width:96px">{high}</div>',
                tag('< ' + unit, 'success') if False else src]
    rows = [
        row('收缩压（高压）', 'bp_systolic', 'mmHg', '≤139', '140~179', '≥180',
            tag('已生效', 'success')),
        row('舒张压（低压）', 'bp_diastolic', 'mmHg', '≤89', '90~109', '≥110',
            tag('已生效', 'success')),
        row('血糖（空腹）', 'glucose_fasting', 'mmol/L', '3.9~6.1', '6.2~11.0', '≥11.1',
            tag('已生效', 'success')),
        row('心率', 'heart_rate', '次/分', '60~100', '101~120', '<60 或 ≥121',
            tag('已生效', 'success')),
        row('睡眠时长', 'sleep_hours', '小时', '≥7', '5~6.9', '<5',
            tag('已生效', 'success')),
        row('每日步数', 'steps_daily', '步', '≥6000', '3000~5999', '<3000',
            tag('已生效', 'success')),
        row('预警冷却时间', 'alert_cooldown_min', '分钟', '—', '—', '30',
            tag('已生效', 'success')),
    ]
    tb = table(['指标 / 配置项', '正常区间', '关注（level 1-2）', '高风险（level 3）', '状态'], rows)
    body = f'<div class="crumb">健康与预警 / <b>预警规则配置</b></div>' \
           f'<div class="alert-info mb">阈值全部保存在 <span class="code">sys_config</span> 表，界面不硬编码任何数值；保存后<b>即时生效</b>，无需重启服务。</div>' \
           f'{card("阈值与风险等级", tb)}' \
           f'<div style="height:18px"></div><div class="grid-2-1">' \
           f'<div>{card("等级判定与通知策略", table(["等级", "判定条件", "通知范围", "通知方式"], [
               [tag('level 1 关注', 'info'), '连续 2 天处于关注区间', '已绑定家属', '站内通知'],
               [tag('level 2 偏高', 'warning'), '单次进入关注区间', '已绑定家属', '站内通知'],
               [tag('level 3 高风险', 'danger'), '任一指标达到高风险区间', '全部已绑定家属 + 责任护工', '站内通知（红点置顶）'],
           ]))}</div>' \
           f'<div>{card("变更与校验", """<div class="hint-err" style="margin-bottom:12px">高风险阈值必须大于关注上限，否则保存被拦截并提示“阈值区间冲突”。</div><div class="alert-info" style="margin-bottom:12px">每次修改记录变更人、时间与修改前后值，可在系统日志中追溯。</div>""" + btn("恢复默认值") + "　" + btn("导出配置") + "　" + btn("保存并生效", True) + "<div style=\'height:12px\'></div><div class=\'hint\'>冷却时间内同一老人的同类预警不重复创建，避免消息轰炸。</div>")}</div></div>' \
           f'<div style="height:18px"></div>{card("保存状态", """<div class="alert-info">保存成功：页面顶部出现“配置已保存并即时生效”提示条；保存失败：保留用户输入并提示“保存失败，请重试”，不回退为旧值。</div>""")}</div>'
    return ('UI-ADMIN-03', '预警规则配置', '正常 / 阈值区间冲突校验 / 保存失败回退保护 / 恢复默认 / 冷却时间生效',
            'admin', '预警规则配置', False, body, ADM_CSS)


def _adm_metrics():
    rows = [
        ['血压', 'BLOOD_PRESSURE', 'mmHg', '收缩压 / 舒张压', '1 次 / 天建议', tag('启用', 'success')],
        ['血糖', 'BLOOD_GLUCOSE', 'mmol/L', '空腹 / 餐后', '按医嘱', tag('启用', 'success')],
        ['心率', 'HEART_RATE', '次/分', '静息心率', '按需', tag('启用', 'success')],
        ['睡眠', 'SLEEP', '小时', '每日总时长', '1 次 / 天', tag('启用', 'success')],
        ['步数', 'STEPS', '步', '每日累计', '1 次 / 天', tag('启用', 'success')],
        ['体重', 'WEIGHT', 'kg', '晨起空腹', '每周 2~3 次', tag('停用', 'info')],
    ]
    body = f'<div class="crumb">健康与预警 / <b>健康指标配置</b></div>' \
           f'{filter_bar([inp("全部指标类型", sel=True), btn("查询", True), btn("新增指标类型", True)])}' \
           f'{card("指标类型与单位", table(["指标名称", "类型代码", "单位", "取值范围说明", "建议频次", "状态"], rows))}' \
           f'<div style="height:18px"></div><div class="grid-2">' \
           f'<div>{card("新增 / 编辑指标类型", form_row('指标名称', '<div class="inp ph" style="min-width:200px">如：血氧饱和度</div>', req=True) +
                                        form_row('类型代码', '<div class="inp" style="color:#303133;min-width:200px">OXYGEN_SAT</div><span class="unit">大写英文，唯一不可重复</span>') +
                                        form_row('单位', '<div class="inp" style="color:#303133;min-width:130px">%</div>') +
                                        form_row('合理范围', '<div class="inp" style="color:#303133;min-width:110px">95</div><span class="unit">~</span><div class="inp" style="color:#303133;min-width:110px">100</div>') +
                                        form_row('状态', '<div class="inp inp-sel" style="color:#303133">启用</div>') +
                                        "<div style=\'height:12px\'></div>" + btn("保存", True) + "　" + btn("取消"))}</div>' \
           f'<div>{card("约束与说明", """<div class="alert-info" style="margin-bottom:12px">指标类型与 <span class="code">health_record.type</span> 一一对应；停用后新建记录不再出现该类型，历史数据仍可查询。</div><div class="alert-warn" style="margin-bottom:12px">类型代码一旦产生数据不可修改，只能停用后新建，避免历史数据语义漂移。</div><div class="alert-info">单位为展示与录入用，换算规则不做自动处理，避免误判。</div>""")}' \
           f'<div style="height:18px"></div>{card("空数据状态", empty("还没有配置指标类型", "至少需要配置血压与心率两类，才能启用预警规则", "空"))}</div></div>' \
           f'<div style="height:18px"></div>{card("停用二次确认（弹窗形态示意）", """<div style="border:1px solid #ebeef5;border-radius:10px;overflow:hidden"><div style="background:#fafafa;padding:11px 15px;font-size:13px;color:#909399">停用“体重”指标类型？</div><div style="padding:18px"><div style="font-size:14px;color:#606266;line-height:1.8;margin-bottom:16px">停用后老人端不再显示体重的录入入口，已有的体重历史记录仍保留可查。</div><div style="display:flex;gap:10px;justify-content:flex-end"><button class="btn btn-sm">取消</button><button class="btn btn-sm btn-primary">确认停用</button></div></div></div>""")}</div>'
    return ('UI-ADMIN-04', '健康指标配置', '正常 / 空数据 / 代码重复校验 / 停用二次确认 / 有数据时禁止改代码',
            'admin', '健康指标配置', False, body, ADM_CSS)


def _adm_kb():
    tree = """<div class="tree">
  <div class="tree-i on">全部条目</div>
  <div class="tree-i sub">高血压</div>
  <div class="tree-i sub">糖尿病</div>
  <div class="tree-i sub">睡眠与情绪</div>
  <div class="tree-i sub">用药常识</div>
  <div class="tree-i sub">紧急处理</div>
  <div class="tree-i"><span style="color:#409eff">+</span> 新建分类</div>
</div>"""
    rows = [
        ['高血压老人能吃鸡蛋吗', '高血压', '128 字', '2026-09-06 14:20', tag('已索引', 'success'), btn('编辑', False, True) + ' ' + btn('删除', False, True)],
        ['家庭自测血压的正确方法', '高血压', '236 字', '2026-09-05 10:02', tag('已索引', 'success'), btn('编辑', False, True) + ' ' + btn('删除', False, True)],
        ['血压多高需要立即就医', '高血压', '184 字', '2026-09-05 09:48', tag('已索引', 'success'), btn('编辑', False, True) + ' ' + btn('删除', False, True)],
        ['夜间失眠的非药物调节方法', '睡眠与情绪', '310 字', '2026-09-04 16:31', tag('待重建索引', 'warning'), btn('编辑', False, True) + ' ' + btn('删除', False, True)],
        ['低血糖的识别与应急处理', '紧急处理', '152 字', '2026-09-04 11:15', tag('已索引', 'success'), btn('编辑', False, True) + ' ' + btn('删除', False, True)],
    ]
    body = f'<div class="crumb">健康与预警 / <b>知识库管理</b></div>' \
           f'{stat_grid([("知识条目", "46", "条", "本期已录入"), ("分类", "5", "个", "高血压条目最多"), ("向量分片", "312", "片", "平均每条 6.8 片"), ("待重建索引", "1", "条", "修改后未重建")])}' \
           f'{filter_bar([inp("按标题搜索"), inp("全部分类", sel=True), btn("查询", True), btn("重建全部索引"), btn("新增条目", True)])}' \
           f'<div class="grid-1-2"><div>{card("分类", tree)}</div>' \
           f'<div>{card("知识条目", table(["标题", "分类", "字数", "更新时间", "索引状态", "操作"], rows) + pager(1, 3, 46))}</div></div>' \
           f'<div style="height:18px"></div><div class="grid-2">' \
           f'<div>{card("新增 / 编辑条目", form_row('标题', '<div class="inp ph" style="min-width:300px">如：高血压老人能吃鸡蛋吗</div>', req=True) +
                                          form_row('分类', '<div class="inp inp-sel" style="color:#303133">高血压</div>') +
                                          form_row('正文', '<div class="inp ph" style="min-width:320px;height:90px;align-items:flex-start;padding-top:10px">录入健康科普正文，保存后自动分片并写入向量库</div>') +
                                          "<div style=\'height:12px\'></div>" + btn("保存并重建索引", True) + "　" + btn("仅保存"))}</div>' \
           f'<div>{card("状态与选配说明", """<div class="alert-warn" style="margin-bottom:12px"><b>【选配】文档上传解析</b>（PDF / Word 自动切分入库）本期不实现，界面保留入口但标注“即将支持”。</div><div class="alert-info" style="margin-bottom:10px"><b>索引重建中：</b>条目状态显示“重建中”，期间 AI 咨询仍可用旧索引作答，不阻断服务。</div><div class="alert-info" style="margin-bottom:10px"><b>空分类：</b>该分类下暂无条目时展示空状态并提供“新增条目”按钮。</div><div class="alert-warn">AI 只能基于本知识库与老人档案作答，知识库不得出现诊断结论类表述。</div>""")}</div>' \
           f'</div>'
    return ('UI-ADMIN-05', '知识库管理', '正常 / 空分类 / 索引重建中 / 上传解析（选配未实现）/ 删除二次确认',
            'admin', '知识库管理', False, body, ADM_CSS)


def _adm_report():
    bar = chart_bar([('第 1 周', 24), ('第 2 周', 38), ('第 3 周', 52), ('第 4 周', 61), ('第 5 周', 47), ('第 6 周', 66)],
                    w=620, h=210, unit=' 次')
    line = chart_line([{'name': '预警条数', 'color': '#e6a23c', 'vals': [8, 12, 15, 22, 18, 26]}],
                      ['第 1 周', '第 2 周', '第 3 周', '第 4 周', '第 5 周', '第 6 周'], ymin=0, ymax=30, w=620, h=200)
    hb = chart_hbar([('高血压', 46), ('糖尿病', 24), ('睡眠问题', 16), ('用药咨询', 9), ('紧急处理', 5)], w=600)
    body = f'<div class="crumb">健康与预警 / <b>统计报表</b></div>' \
           f'{filter_bar([inp("最近 6 周", sel=True), inp("全部角色", sel=True), btn("查询", True), btn("导出 Excel"), btn("导出 PDF")])}' \
           f'{stat_grid([("注册用户", "38", "人", "本周 +12"), ("AI 咨询次数", "288", "次", "本周 66 次"), ("生成预警", "101", "条", "高风险 26 条"), ("预警处理率", "86", "%", "平均响应 11 分钟")])}' \
           f'<div class="grid-2 mb">{card("每周 AI 咨询次数", bar)}{card("每周预警条数", line)}</div>' \
           f'<div class="grid-2-1"><div>{card("咨询意图分布", hb + "<div class=\'hint\'>意图分布由 rule-based 分类统计，不依赖大模型输出，保证口径稳定。</div>")}</div>' \
           f'<div>{card("处理闭环指标", table(["指标", "数值", "说明"], [
               ['预警总数', '101 条', '近 6 周累计'],
               ['已处理', '87 条', '占 86%'],
               ['平均响应时长', '11 分钟', '从生成到首次处理'],
               ['高风险处理率', '100%', 'level 3 全部有处理记录'],
               ['重复预警抑制', '34 条', '冷却时间内未重复创建'],
           ])) + "<div style=\'height:12px\'></div>" + chart_ring(86, "预警处理率", "近 6 周", color="#67c23a")}</div></div>' \
           f'<div style="height:18px"></div><div class="grid-2">' \
           f'<div>{card("空数据状态", empty("所选周期内暂无统计数据", "换个时间范围，或确认系统已有用户与指标数据", "空"))}</div>' \
           f'<div>{card("统计口径与导出", """<div class="alert-info" style="margin-bottom:12px">注册用户按账号创建时间统计；AI 咨询按 chat_message 中用户提问条数统计；预警按 health_warning 生成时间统计，不含被冷却拦下的重复预警。</div><div class="alert-warn">导出失败（文件过大或网络异常）时提示“导出失败，请缩小时间范围后重试”，已渲染的图表不清空。</div>""")}</div></div>'
    return ('UI-ADMIN-06', '统计报表', '正常 / 空数据 / 周期切换 / 导出失败重试 / 大数据量分页',
            'admin', '统计报表', False, body, ADM_CSS)


def _adm_screen():
    def sc(label, val, unit, sub):
        return (f'<div class="screen-stat"><div class="screen-l">{label}</div>'
                f'<div class="screen-v">{val}<small style="font-size:16px;color:#909399">{unit}</small></div>'
                f'<div class="screen-s">{sub}</div></div>')
    bar = chart_bar([('09-08', 3), ('09-09', 2), ('09-10', 4), ('09-11', 5), ('09-12', 3), ('09-13', 6), ('09-14', 4)],
                    w=620, h=200, unit=' 条')
    line = chart_line([{'name': '活跃用户', 'color': '#409eff', 'vals': [6, 9, 11, 14, 13, 18, 21]}],
                      ['09-08', '09-09', '09-10', '09-11', '09-12', '09-13', '09-14'], ymin=0, ymax=24, w=620, h=190)
    body = f'<div class="crumb">系统 / <b>运营概览大屏</b>　<span style="color:#67c23a">数据每 60 秒自动刷新 · 最近刷新 16:32</span></div>' \
           f'<div class="stat-grid">{sc("在册老人", "14", " 人", "本周新增 3")}{sc("今日活跃", "21", " 人", "较昨日 +4")}{sc("今日预警", "4", " 条", "高风险 1 条")}{sc("待处理预警", "2", " 条", "均已超过 15 分钟")}</div>' \
           f'<div class="grid-2 mb">{card("近 7 天预警趋势", bar)}{card("近 7 天活跃用户", line)}</div>' \
           f'<div class="grid-2-1"><div>{card("高风险老人实时看板", table(["老人", "年龄", "最近异常", "风险等级", "状态"], [
               [dot('danger') + '<span class="strong">张桂兰</span>', '72', '血压 185/100 mmHg', tag('level 3', 'danger'), '处理中'],
               [dot('danger') + '<span class="strong">王秀英</span>', '78', '睡眠 4.0 小时', tag('level 3', 'danger'), '待处理'],
               [dot('watch') + '<span class="strong">刘建国</span>', '69', '收缩压 152 mmHg', tag('level 2', 'warning'), '观察中'],
           ]))}</div>' \
           f'<div>{card("系统运行状态", """<div class="form-row" style="padding:11px 0"><div class="form-label" style="width:118px">大模型服务</div><div class="form-ctrl"><span class="tag tag-success">可用</span><span class="hint" style="width:auto">平均响应 1.8s</span></div></div>
<div class="form-row" style="padding:11px 0"><div class="form-label" style="width:118px">向量库</div><div class="form-ctrl"><span class="tag tag-success">可用</span><span class="hint" style="width:auto">312 个分片</span></div></div>
<div class="form-row" style="padding:11px 0"><div class="form-label" style="width:118px">数据库</div><div class="form-ctrl"><span class="tag tag-success">可用</span><span class="hint" style="width:auto">15 张表 · 720 KB</span></div></div>
<div class="form-row" style="padding:11px 0"><div class="form-label" style="width:118px">预警巡检</div><div class="form-ctrl"><span class="tag tag-success">运行中</span><span class="hint" style="width:auto">30 秒轮询</span></div></div>
<div class="alert-warn" style="margin-top:12px">大屏为【选配】项；模型不可用时此处显示“降级运行”，预警巡检不受影响。</div>""")}</div></div>'
    return ('UI-ADMIN-07', '概览大屏', '正常 / 自动刷新 / 待处理告警 / 模型不可用（降级运行）/ 空数据',
            'admin', '概览大屏', False, body, ADM_CSS)


def _adm_logs():
    logs = [
        ('16:30:12', 'WARN', '预警生成', '老人张桂兰 血压 185/100 mmHg，判定 level 3，已通知 2 位接收人'),
        ('16:30:12', 'INFO', '指标录入', 'profile_id=1 录入 BLOOD_PRESSURE，规则引擎耗时 12 ms'),
        ('16:25:07', 'INFO', 'AI 咨询', '意图 EMERGENCY → 强制写预警 #40002，Agent 耗时 1.7 s'),
        ('16:21:33', 'INFO', 'AI 咨询', '意图 DATA → 查询 health_record 20 条 + health_warning 2 条'),
        ('16:20:05', 'INFO', '登录', '手机号 1300000002 登录成功，角色 ELDER，IP 192.168.1.23'),
        ('16:11:48', 'ERROR', '登录失败', '手机号 1300000002 密码错误，第 2 次失败'),
        ('15:58:20', 'INFO', '配置变更', '管理员修改 bp_systolic 高风险阈值 180 → 180（无变化）'),
        ('15:40:02', 'WARN', 'AI 降级', '模型调用超时 8.2 s，已回退为规则摘要，预警不受影响'),
        ('15:12:44', 'INFO', '权限拦截', '家属 user_id=5 请求未绑定老人档案，返回 1002'),
    ]
    lines = ''
    for t, lv, act, d in logs:
        c = {'WARN': '#e6a23c', 'ERROR': '#f56c6c', 'INFO': '#909399'}[lv]
        lines += (f'<div class="log-line"><b>{t}</b>　<span style="color:{c};width:52px;display:inline-block">{lv}</span>　'
                  f'<b>{act}</b>　{d}</div>')
    body = f'<div class="crumb">系统 / <b>系统日志</b></div>' \
           f'{stat_grid([("今日日志", "412", "条", "INFO 占 91%"), ("警告", "9", "条", "含 3 条 AI 降级"), ("错误", "2", "条", "均为登录失败"), ("权限拦截", "4", "条", "越权访问尝试")])}' \
           f'{filter_bar([inp("全部类型", sel=True), inp("全部级别", sel=True), inp("开始日期"), inp("结束日期"), btn("查询", True), btn("导出日志")])}' \
           f'{card("日志明细（按时间倒序）", lines + pager(1, 5, 412))}' \
           f'<div style="height:18px"></div><div class="grid-2">' \
           f'<div>{card("空数据状态", empty("所选条件内暂无日志", "调整时间范围或清空筛选条件", "空"))}</div>' \
           f'<div>{card("记录范围与说明", """<div class="alert-info" style="margin-bottom:12px">记录登录、操作、配置变更、预警生成与权限拦截五类事件；日志只追加，不提供界面删除。</div><div class="alert-warn" style="margin-bottom:12px">日志中的手机号做脱敏展示，完整值仅管理员在授权场景可查，避免隐私外泄。</div><div class="alert-info">【选配】系统日志为可裁剪项，若工期不足可先只保留预警与登录两类。</div>""")}</div>' \
           f'</div>'
    return ('UI-ADMIN-08', '系统日志', '正常 / 空结果 / 脱敏展示 / 导出 / 只追加不可删',
            'admin', '系统日志', False, body, ADM_CSS)


def _adm_notice():
    rows = [
        ['系统上线试运行通知', '全站', '2026-09-08 09:00', tag('已发布', 'success'), '2026-12-31', btn('编辑', False, True) + ' ' + btn('下架', False, True)],
        ['血压阈值调整说明', '全部家属与护工', '2026-09-12 10:20', tag('已发布', 'success'), '2026-10-31', btn('编辑', False, True) + ' ' + btn('下架', False, True)],
        ['国庆期间值班安排', '全部护工', '2026-09-20 08:00', tag('待发布', 'warning'), '2026-10-08', btn('编辑', False, True) + ' ' + btn('发布', True, True)],
    ]
    body = f'<div class="crumb">系统 / <b>系统公告</b></div>' \
           f'<div class="grid-2-1"><div>{card("公告列表", table(["标题", "可见范围", "发布时间", "状态", "失效时间", "操作"], rows) + pager(1, 1, 3))}</div>' \
           f'<div>{card("发布公告", form_row('标题', '<div class="inp ph" style="min-width:250px">如：系统维护通知</div>', req=True) +
                                      form_row('可见范围', '<div class="inp inp-sel" style="color:#303133">全部用户</div>') +
                                      form_row('生效时间', '<div class="inp" style="color:#303133">2026-09-15 09:00</div>') +
                                      form_row('失效时间', '<div class="inp" style="color:#303133">2026-09-30 23:59</div>') +
                                      form_row('公告正文', '<div class="inp ph" style="min-width:280px;height:100px;align-items:flex-start;padding-top:10px">支持纯文本，不解析 HTML</div>') +
                                      "<div style=\'height:12px\'></div>" + btn("保存草稿") + "　" + btn("立即发布", True))}</div></div>' \
           f'<div style="height:18px"></div><div class="grid-2">' \
           f'<div>{card("空数据状态", empty("还没有发布任何公告", "发布后会在对应用户端的通知中心顶部展示", "空"))}</div>' \
           f'<div>{card("说明", """<div class="alert-info" style="margin-bottom:12px">公告与预警通知共用站内通知通道，但优先级低于预警，不会覆盖或顶掉预警红点。</div><div class="alert-warn" style="margin-bottom:12px">正文不支持富文本与脚本，避免注入风险；下架后用户端立即不可见。</div><div class="alert-info">【选配】系统公告为可裁剪项，若工期不足可整体下线，不影响核心预警闭环。</div>""")}</div>' \
           f'</div>'
    return ('UI-ADMIN-09', '系统公告', '正常 / 空数据 / 草稿与发布 / 下架 / 脚本注入拦截',
            'admin', '系统公告', False, body, ADM_CSS)


def _adm_model():
    cards = ''
    for name, code, desc, on in [
        ('DeepSeek', 'deepseek-chat', '中文健康科普场景表现稳定，价格低，作为默认候选', True),
        ('通义千问', 'qwen-plus', '长文本与结构化输出稳定，适合摘要生成', False),
        ('GLM-4', 'glm-4-flash', '响应快、成本低，适合高频问答', False),
    ]:
        cards += (f'<div class="mod-card {"on" if on else ""}" style="margin-bottom:12px">'
                  f'<div class="mod-t">{name}{"<span class=\'tag tag-primary\'>当前使用</span>" if on else ""}</div>'
                  f'<div class="mod-d"><span class="code">{code}</span><br>{desc}</div>'
                  f'<div style="margin-top:12px">{btn("设为当前模型" if not on else "已选中", not on, True)} {btn("测试连接", False, True)}</div></div>')
    body = f'<div class="crumb">系统 / <b>AI 模型配置</b></div>' \
           f'<div class="alert-warn mb">API Key 只保存在后端 <span class="code">.env</span> 中，<b>绝不下发到前端</b>，界面仅展示脱敏后的尾部 4 位。</div>' \
           f'<div class="grid-1-2"><div>{card("可选模型", cards + "<div class=\'hint\'>切换模型只需修改 <span class=\'code\'>LLM_PROVIDER</span>，业务代码不变。</div>")}</div>' \
           f'<div>{card("当前配置", form_row('模型提供方', '<div class="inp inp-sel" style="color:#303133;min-width:190px">DeepSeek</div>') +
                                      form_row('模型名称', '<div class="inp" style="color:#303133;min-width:220px">deepseek-chat</div>') +
                                      form_row('API Key', '<div class="inp" style="color:#303133;min-width:240px">••••••••••••••••3f7a</div><span class="unit">仅后端可见</span>') +
                                      form_row('API 地址', '<div class="inp" style="color:#303133;min-width:260px">https://api.deepseek.com/v1</div>') +
                                      form_row('温度 / 最大长度', '<div class="inp" style="color:#303133;min-width:80px">0.3</div><div class="inp" style="color:#303133;min-width:110px">1024</div>') +
                                      form_row('摘要超时', '<div class="inp" style="color:#303133;min-width:90px">8</div><span class="unit">秒（超时回退规则摘要，不阻断预警）</span>') +
                                      form_row('每日咨询上限', '<div class="inp" style="color:#303133;min-width:80px">20</div><span class="unit">次 / 人 · 存 sys_config</span>') +
                                      "<div style=\'height:14px\'></div>" + btn("测试连接", True) + "　" + btn("保存配置") + "　" + btn("恢复默认"))}' \
           f'<div style="height:18px"></div>{card("连接测试与失败状态", """<div class="alert-info" style="margin-bottom:10px">测试成功：显示“连接正常，平均响应 1.8 s”。</div><div class="alert-warn" style="margin-bottom:10px">Key 未配置：提示“未检测到 API Key，请在后端 .env 中配置”，保存按钮置灰。</div><div class="alert-warn" style="margin-bottom:10px">测试失败：显示错误原因（超时 / 401 鉴权失败），但<b>不阻断</b>其他功能，预警与指标录入照常运行。</div><div class="alert-info">【选配】AI 模型配置为可裁剪项，本期亦可通过直接修改 .env 完成切换。</div>""")}</div></div>'
    return ('UI-ADMIN-10', 'AI 模型配置', '正常 / Key 未配置 / 测试连接失败 / 切换模型即时生效 / 超时降级',
            'admin', 'AI 模型配置', False, body, ADM_CSS)


def pages():
    return [_adm_users(), _adm_roles(), _adm_rules(), _adm_metrics(), _adm_kb(),
            _adm_report(), _adm_screen(), _adm_logs(), _adm_notice(), _adm_model()]
