# -*- coding: utf-8 -*-
"""页面定义 A：公共 / 认证 4 个 + 老人端 13 个"""
from _lib import (tag, dot, card, table, pager, empty, stat_grid, filter_bar, inp, btn,
                  form_row, metric_detail, timeline, chips, chart_line, chart_bar,
                  chart_hbar, chart_ring, disclaimer)

ELDER_CSS = """
.elder { font-size:19px; }
.elder .card-title { font-size:20px; }
.elder .tbl, .elder .tbl th { font-size:16px; }
.elder .form-label { font-size:18px; }
.elder .inp { height:50px; font-size:18px; min-width:200px; }
.elder .btn { font-size:17px; padding:13px 22px; min-height:48px; }
.elder .stat-label { font-size:17px; }
.elder .stat-val { font-size:34px; }
.elder .nav-item { font-size:20px; padding:19px 24px; }
.elder .crumb { font-size:16px; }
.elder .tl-t { font-size:17px; }
.elder .tl-d { font-size:15px; }
.elder .disclaimer { font-size:16px; padding:14px 20px; }
.elder .hint, .elder .hint-err { font-size:15px; }
.elder .note-bar { font-size:14px; }
"""

AUTH_CSS = """
.auth-wrap { min-height:830px; background:#f5f7fa; display:flex; align-items:center; justify-content:center; }
.auth-box { width:480px; }
.auth-logo { display:flex; align-items:center; gap:12px; font-size:25px; font-weight:600; color:#409eff;
  justify-content:center; margin-bottom:10px; }
.auth-slogan { text-align:center; font-size:14px; color:#909399; margin-bottom:24px; }
.auth-h { font-size:20px; font-weight:600; color:#303133; text-align:center; margin-bottom:20px; }
.fld { margin-bottom:18px; }
.fld-l { font-size:14px; color:#606266; margin-bottom:8px; display:block; }
.fld-inp { height:48px; border:1px solid #dcdfe6; border-radius:8px; padding:0 14px; display:flex;
  align-items:center; font-size:15px; color:#303133; background:#fff; }
.fld-inp.err { border-color:#f56c6c; }
.fld-inp.ph { color:#c0c4cc; }
.fld-inp .tail { margin-left:auto; font-size:14px; color:#409eff; }
.alert-warn { background:#fdf6ec; border:1px solid #faecd8; color:#b88230; font-size:13px;
  padding:10px 14px; border-radius:8px; margin-bottom:18px; }
.alert-info { background:#ecf5ff; border:1px solid #d9ecff; color:#3a6f9e; font-size:13px;
  padding:10px 14px; border-radius:8px; }
.btn-block { width:100%; height:48px; font-size:17px; border-radius:8px; margin-top:8px; }
.auth-foot { display:flex; justify-content:space-between; font-size:14px; margin-top:14px; }
.auth-foot span { color:#409eff; }
.auth-tip { margin-top:20px; background:#fff; border:1px solid #ebeef5; border-radius:8px;
  padding:14px 16px; font-size:13px; color:#909399; line-height:1.85; }
.auth-tip b { color:#606266; font-weight:500; }
"""


def _login():
    body = f"""
<div class="auth-wrap">
  <div class="auth-box">
    <div class="auth-logo"><span class="logo-mark" style="width:40px;height:40px;font-size:19px">康</span>智能康养系统</div>
    <div class="auth-slogan">面向老年人的 AI 主动式健康管理平台</div>
    <div class="card" style="padding:32px 38px">
      <div class="auth-h">登录</div>
      <div class="alert-warn">您的登录状态已过期，请重新登录</div>
      <div class="fld"><span class="fld-l">手机号</span><div class="fld-inp">130 0000 0002</div></div>
      <div class="fld"><span class="fld-l">密码</span><div class="fld-inp err">••••••••<span class="tail">显示</span></div>
        <div class="hint-err" style="margin-top:8px">手机号或密码不正确，请重新输入（今日还可尝试 4 次）</div></div>
      <button class="btn btn-primary btn-block">登 录</button>
      <div class="auth-foot"><span>忘记密码</span><span>还没有账号？立即注册</span></div>
    </div>
    <div class="auth-tip">
      <b>登录后按角色自动跳转</b>：老年用户 → 老人端首页；家属 → 家属端看板；护工 → 护工工作台；管理员 → 管理后台。<br>
      <b>连续 5 次密码错误将锁定 15 分钟</b>，锁定期间不区分手机号是否注册，避免账号探测。
    </div>
    {disclaimer('本系统提供健康管理辅助，不构成医疗诊断')}
  </div>
</div>"""
    return ('UI-AUTH-01', '登录页', '正常 / 登录失败提示 / 会话过期 / 账号锁定风险提示',
            'plain', None, False, body, AUTH_CSS)


def _register():
    body = f"""
<div class="auth-wrap">
  <div class="auth-box">
    <div class="auth-logo"><span class="logo-mark" style="width:40px;height:40px;font-size:19px">康</span>智能康养系统</div>
    <div class="auth-slogan">注册后需完成手机号校验，方可使用系统功能</div>
    <div class="card" style="padding:32px 38px">
      <div class="auth-h">注册账号</div>
      <div class="fld"><span class="fld-l">手机号</span><div class="fld-inp err">130000002</div>
        <div class="hint-err" style="margin-top:8px">请输入 11 位手机号</div></div>
      <div class="fld"><span class="fld-l">短信验证码</span><div class="fld-inp ph">请输入 6 位验证码<span class="tail">获取验证码</span></div></div>
      <div class="fld"><span class="fld-l">设置密码</span><div class="fld-inp ph">8~20 位，需含字母与数字</div>
        <div class="hint" style="margin-top:8px">密码强度：弱 · 建议加入大写字母提高强度</div></div>
      <div class="fld"><span class="fld-l">确认密码</span><div class="fld-inp ph">请再次输入密码</div></div>
      <div class="fld"><span class="fld-l">选择身份</span>
        <div class="chip-row">
          <span class="chip">我是老年用户</span>
          <span class="chip" style="border-color:#dcdfe6;background:#f4f4f5;color:#c0c4cc">我是家属</span>
          <span class="chip" style="border-color:#dcdfe6;background:#f4f4f5;color:#c0c4cc">护工（需管理员开通）</span>
          <span class="chip" style="border-color:#dcdfe6;background:#f4f4f5;color:#c0c4cc">管理员（不可自助注册）</span>
        </div>
        <div class="hint" style="margin-top:10px">护工与管理员账号由管理员统一创建，自助注册仅开放老年用户与家属两类角色</div>
      </div>
      <div style="margin-top:6px;font-size:14px;color:#606266"><span class="ck on" style="margin:0"></span>我已阅读并同意《用户协议》与《隐私政策》</div>
      <button class="btn btn-primary btn-block" style="margin-top:22px">注 册</button>
      <div class="auth-foot"><span></span><span>已有账号？返回登录</span></div>
    </div>
    {disclaimer('健康数据仅用于本人与已授权家属的健康管理，不对外提供')}
  </div>
</div>"""
    return ('UI-AUTH-02', '注册页', '正常 / 格式校验失败 / 角色白名单限制 / 隐私授权未勾选',
            'plain', None, False, body, AUTH_CSS)


def _profile():
    rows = [
        ('姓名', '张桂兰'), ('性别', '女'), ('年龄', '72 岁（1954-03-12）'),
        ('手机号', '130 0000 0002 <span class="tag tag-success" style="margin-left:10px">已实名校验</span>'),
        ('当前角色', '老年用户'), ('注册时间', '2026-09-08 09:14'),
    ]
    info = ''.join(f'<div class="elder-row"><div class="elder-k">{k}</div><div class="elder-v">{v}</div></div>'
                   for k, v in rows)
    sec = card('账号信息', info) + '<div class="mb"></div>'
    ops = card('安全设置', f"""
<div class="elder-row"><div class="elder-k">登录密码</div><div class="elder-v">已设置 · 上次修改 2026-09-08</div>
  <span style="margin-left:auto">{btn('修改密码')}</span></div>
<div class="elder-row"><div class="elder-k">绑定手机号</div><div class="elder-v">130 0000 0002</div>
  <span style="margin-left:auto">{btn('更换手机号')}</span></div>
<div class="elder-row"><div class="elder-k">登录设备</div><div class="elder-v">本机 Chrome · 2026-09-14 16:20 登录</div></div>
<div class="elder-row"><div class="elder-k">退出登录</div><div class="elder-v" style="color:#909399">退出后需重新输入手机号与密码</div>
  <span style="margin-left:auto">{btn('退出登录')}</span></div>
""")
    body = f'<div class="main" style="padding:22px 26px 34px">' \
           f'<div class="crumb">我的 / <b>个人中心</b></div>' \
           f'<div class="grid-2-1"><div>{sec}{ops}</div><div>' \
           f'{card("状态提示", """<div class="alert-info">修改手机号需通过新手机号短信验证码校验；更换成功后，已生效的家属绑定关系不受影响。</div><div style="height:14px"></div><div class="alert-warn">本账号同时可在老人端、家属端、护工端、管理后台登录，界面按角色自动切换。</div>""")}' \
           f'</div></div>{disclaimer()}</div>'
    return ('UI-AUTH-03', '个人中心', '正常 / 修改密码成功 / 手机号已被占用 / 未登录跳转',
            'elder', '我的', True, body, ELDER_CSS)


def _forgot():
    step = """<div class="wizard">
  <div class="wizard-step on"><span class="wizard-num">1</span>验证手机号</div><div class="wizard-line"></div>
  <div class="wizard-step on"><span class="wizard-num">2</span>输入验证码</div><div class="wizard-line"></div>
  <div class="wizard-step on"><span class="wizard-num">3</span>设置新密码</div><div class="wizard-line"></div>
  <div class="wizard-step"><span class="wizard-num">4</span>完成</div>
</div>"""
    body = f"""
<div class="auth-wrap">
  <div class="auth-box">
    <div class="card" style="padding:32px 38px">
      <div class="auth-h">找回密码</div>
      {step}
      <div class="alert-warn">验证码已发送至 130****0002，5 分钟内有效；今日剩余获取次数 2 次</div>
      <div class="fld"><span class="fld-l">手机号</span><div class="fld-inp">130 0000 0002</div></div>
      <div class="fld"><span class="fld-l">验证码</span><div class="fld-inp err">9 3 2 1</div>
        <div class="hint-err" style="margin-top:8px">验证码不正确或已过期，请重新获取</div></div>
      <div class="fld"><span class="fld-l">新密码</span><div class="fld-inp ph">8~20 位，需含字母与数字</div></div>
      <div class="fld"><span class="fld-l">确认新密码</span><div class="fld-inp ph">请再次输入新密码</div></div>
      <button class="btn btn-primary btn-block" style="margin-top:18px">提交并返回登录</button>
      <div class="auth-foot"><span>返回登录</span><span></span></div>
    </div>
    <div class="auth-tip">
      <b>【选配】</b>本功能为可裁剪项，本期仅在原型层面确认交互；若工期不足，登录页保留“请联系管理员重置”的兜底文案。<br>
      <b>安全约束</b>：校验失败不区分“手机号未注册”与“验证码错误”，避免手机号枚举。
    </div>
  </div>
</div>"""
    return ('UI-AUTH-04', '忘记密码', '正常 / 验证码错误 / 手机号未注册（不区分提示）/ 次数超限',
            'plain', None, False, body, AUTH_CSS)


# ---------------- 老人端 ----------------

def _elder_home():
    metrics = [
        ('血压', '128/82', 'mmHg', '08:20　<span class="tag tag-success">正常</span>'),
        ('心率', '76', '次/分', '08:20　<span class="tag tag-success">正常</span>'),
        ('血糖', '6.8', 'mmol/L', '07:10　<span class="tag tag-warning">偏高</span>'),
        ('睡眠', '5.5', '小时', '昨日　<span class="tag tag-warning">偏少</span>'),
    ]
    m = ''
    for n, v, u, f in metrics:
        m += f'<div class="stat"><div class="stat-label">{n}</div><div class="stat-val">{v}<small>{u}</small></div><div class="stat-foot">{f}</div></div>'
    body = f"""
<div style="padding:24px 32px 36px">
  <div class="card" style="background:#ecf5ff;border-color:#d9ecff;display:flex;align-items:center;justify-content:space-between;margin-bottom:22px">
    <div><div style="font-size:29px;font-weight:600;color:#303133">张桂兰 您好</div>
    <div style="font-size:18px;color:#606266;margin-top:6px">72 岁 · 高血压 · 今日已测量 2 项指标</div></div>
    <div style="font-size:17px;color:#909399;text-align:right;line-height:1.8">2026年9月14日 星期一<br>晴 24℃</div>
  </div>
  <div class="card-title" style="font-size:22px">今日健康</div>
  <div class="stat-grid">{m}</div>
  <div class="card-title" style="font-size:22px;margin-top:24px">快捷服务（最多三步完成）</div>
  <div class="grid-3 mb">
    <button class="big-btn" style="background:#409eff;color:#fff;text-align:left">
      <span style="display:block;font-size:24px;font-weight:600">问 AI 健康助手</span>
      <span style="display:block;font-size:16px;opacity:.88;margin-top:6px">不舒服？点这里说出来</span></button>
    <button class="big-btn" style="background:#67c23a;color:#fff;text-align:left">
      <span style="display:block;font-size:24px;font-weight:600">录入健康指标</span>
      <span style="display:block;font-size:16px;opacity:.88;margin-top:6px">血压 血糖 心率</span></button>
    <button class="big-btn" style="background:#e6a23c;color:#fff;text-align:left;position:relative">
      <span style="position:absolute;top:-10px;right:14px;background:#f56c6c;color:#fff;border-radius:18px;
        padding:2px 12px;font-size:17px">2 条待处理</span>
      <span style="display:block;font-size:24px;font-weight:600">查看我的预警</span>
      <span style="display:block;font-size:16px;opacity:.88;margin-top:6px">由系统自动发现，无须自己判断</span></button>
  </div>
  <div class="grid-2-1">
    <div>{card('今日提醒', '''<div class="tl">''' + timeline([
        ('下午 15:00 服用苯磺酸氨氯地平片 5mg', '来自用药信息 · 已提醒 1 次'),
        ('今晚睡前测量一次血压', '来自健康打卡计划'),
        ('今日已走 3200 步，建议再走动 20 分钟', '来自健康打卡计划'),
    ]) + '</div>')}</div>
    <div>{card('空数据与异常状态', empty('今天还没有健康数据', '点击“录入健康指标”，3 秒即可完成', '空') + '<div style="height:12px"></div><div class="alert-info">数据不足 2 条时，趋势图显示“数据积累中”，不绘制曲线</div>')}</div>
  </div>
  <div style="margin-top:20px">{disclaimer()}</div>
</div>"""
    return ('UI-ELDER-01', '老人首页', '正常 / 空数据（今日未测量）/ 未读预警红点 / 数据不足时趋势占位',
            'elder', '首页', True, body, ELDER_CSS)


def _elder_record():
    info = ''.join(f'<div class="elder-row"><div class="elder-k">{k}</div><div class="elder-v">{v}</div></div>'
                   for k, v in [
                       ('姓名', '张桂兰'), ('性别 / 年龄', '女 · 72 岁'),
                       ('身高 / 体重', '158 cm · 62 kg'), ('血型', 'A 型'),
                       ('慢病标签', tag('高血压', 'danger') + ' ' + tag('2 型糖尿病', 'warning') + ' ' + tag('失眠', 'info')),
                       ('过敏史', '青霉素过敏（皮肤试验阳性）'),
                       ('既往病史', '2018 年脑梗，恢复良好，无肢体功能障碍'),
                   ])
    contacts = ''.join(f'<div class="elder-row"><div class="elder-k">{k}</div><div class="elder-v">{v}</div></div>'
                       for k, v in [
                           ('紧急联系人', '李强（儿子）· 130 0000 0003'),
                           ('备用联系人', '张伟（侄子）· 130 0000 0009'),
                           ('责任护工', '王护工 · 130 0000 0004'),
                       ])
    family = table(['姓名', '关系', '手机号', '状态', '可查看范围'],
                   [['李强', '儿子', '130 0000 0003', tag('已生效', 'success'), '健康档案 · 指标 · 预警'],
                    ['张敏', '女儿', '130 0000 0007', tag('待老人确认', 'warning'), '（未生效，不可见任何数据）']])
    body = f'<div style="padding:22px 32px 36px"><div class="crumb">健康档案 / <b>我的健康档案</b></div>' \
           f'<div class="grid-2-1 mb"><div>{card("基本信息 <span style=\'font-size:15px;color:#909399\'>（点击“编辑”修改）</span>", info, "")}</div>' \
           f'<div>{card("紧急联系人与责任护工", contacts)}</div></div>' \
           f'<div class="mb">{card("已授权的家属", family)}</div>' \
           f'<div class="grid-2 mb">' \
           f'<div>{card("空档案状态", empty("尚未填写健康档案", "完善档案后，AI 咨询才能结合您的实际情况作答", "空") + "<div style=\'height:12px\'></div>" + btn("立即完善档案", True))}</div>' \
           f'<div>{card("权限边界", """<div class="alert-info" style="margin-bottom:12px">档案数据仅本人、已生效绑定的家属、责任护工与管理员可见。</div><div class="alert-warn">家属绑定处于“待老人确认”状态时，其请求一律返回 1002 无权限，界面不展示任何数据，而不是显示空白卡片。</div>""")}</div>' \
           f'</div>{disclaimer()}</div>'
    return ('UI-ELDER-02', '健康档案', '正常 / 空档案（引导完善）/ 未确认家属无权限 / 慢病标签空',
            'elder', '健康档案', True, body, ELDER_CSS)


def _elder_record_edit():
    f = ''
    f += form_row('姓名', '<div class="inp" style="color:#303133">张桂兰</div>', req=True)
    f += form_row('性别', '<div class="inp inp-sel" style="color:#303133">女</div>' + '<span class="unit">与身份证一致</span>')
    f += form_row('出生日期', '<div class="inp" style="color:#303133">1954-03-12</div>' + '<span class="unit">自动计算 72 岁</span>')
    f += form_row('身高', '<div class="inp" style="color:#303133;min-width:130px">158</div><span class="unit">cm</span>')
    f += form_row('体重', '<div class="inp inp-err" style="color:#303133;min-width:130px">6</div><span class="unit">kg</span>',
                  '!体重需在 20~200 kg 之间，请重新输入')
    f += form_row('慢病标签', tag('高血压', 'danger') + ' ' + tag('2 型糖尿病', 'warning') + ' ' +
                  '<span class="tag tag-info">+ 添加标签</span>', '可多选，用于 AI 咨询时的个性化提示')
    f += form_row('过敏史', '<div class="inp ph" style="min-width:380px">如：青霉素过敏</div>')
    f += form_row('紧急联系人姓名', '<div class="inp" style="color:#303133;min-width:200px">李强</div>'
                  '<div class="inp inp-sel" style="color:#303133">儿子</div>')
    f += form_row('紧急联系人手机号', '<div class="inp" style="color:#303133;min-width:220px">130 0000 0003</div>')
    f += form_row('备注', '<div class="inp ph" style="min-width:380px">其他需要记录的情况</div>')

    dialog = """<div style="border:1px solid #ebeef5;border-radius:10px;overflow:hidden">
  <div style="background:#fafafa;padding:12px 16px;font-size:13px;color:#909399">弹窗形态示意：删除档案二次确认</div>
  <div style="padding:20px 18px">
    <div style="font-size:16px;font-weight:500;color:#303133;margin-bottom:10px">确认删除健康档案？</div>
    <div style="font-size:14px;color:#606266;line-height:1.8;margin-bottom:18px">删除后，档案下的健康指标与趋势数据将一并不可访问，已产生的预警记录仍会保留以便追溯。此操作不可撤销。</div>
    <div style="display:flex;gap:10px;justify-content:flex-end"><button class="btn">取消</button><button class="btn" style="background:#f56c6c;border-color:#f56c6c;color:#fff">确认删除</button></div>
  </div>
</div>"""
    body = f'<div style="padding:22px 32px 36px"><div class="crumb">健康档案 / <b>编辑档案</b></div>' \
           f'<div class="grid-2-1"><div>{card("档案信息（带 * 为必填）", f)}' \
           f'<div style="margin-top:18px;display:flex;gap:12px">{btn("保存档案", True)}{btn("取消")}' \
           f'<span style="margin-left:auto">{btn("新增档案")}</span></div></div>' \
           f'<div class="mb">{card("状态示意", """<div class="hint-err" style="margin-bottom:14px">体重填写 6 kg，超出合理范围，保存被拦截并在字段下方提示</div>""")}</div>' \
           f'<div>{card("危险操作", """<div style="margin-bottom:14px;font-size:14px;color:#909399">档案删除需二次确认，避免误触</div>""" + dialog)}</div>' \
           f'</div></div>{disclaimer()}</div>'
    return ('UI-ELDER-03', '档案编辑', '正常 / 字段越界校验 / 保存成功提示 / 删除二次确认 / 未登录',
            'elder', '健康档案', True, body, ELDER_CSS)


def _elder_input():
    chips_html = chips(['血压', '血糖', '心率', '睡眠', '步数'])
    rows = ''
    rows += form_row('测量时间', '<div class="inp" style="color:#303133">2026-09-14 16:30</div><span class="unit">默认当前时间</span>')
    rows += form_row('收缩压（高压）', '<div class="inp inp-err" style="color:#303133;min-width:170px;font-size:24px">185</div>'
                     '<span class="unit">mmHg</span>', '!收缩压 ≥180 mmHg 属高风险，保存后将立即生成预警并通知家属')
    rows += form_row('舒张压（低压）', '<div class="inp" style="color:#303133;min-width:170px;font-size:24px">100</div><span class="unit">mmHg</span>')
    rows += form_row('测量姿势', '<div class="inp inp-sel" style="color:#303133">坐姿 · 静息 5 分钟后</div>')
    rows += form_row('备注', '<div class="inp ph" style="min-width:330px">如：服药后测量 / 感觉头晕</div>')

    cfg = table(['配置项', '当前值（来自 sys_config）', '来源'],
                [['收缩压正常上限', '139 mmHg', 'sys_config'],
                 ['level 3 高风险阈值', '≥180 mmHg', 'sys_config'],
                 ['预警接收人', '已绑定的全部家属 + 责任护工', 'family_bind / care_relation']])

    body = f'<div style="padding:22px 32px 36px"><div class="crumb">健康指标 / <b>录入指标</b></div>' \
           f'<div class="grid-2-1"><div>{card("选择要录入的指标", chips_html + "<div style=\'height:6px\'></div><div style=\'font-size:15px;color:#909399\'>当前：血压（本图为老人端适老化大字号表单）</div>")}' \
           f'<div style="height:18px"></div>{card("填写测量结果", rows)}' \
           f'<div style="margin-top:20px;display:flex;gap:14px;align-items:center">' \
           f'<button class="btn btn-primary" style="height:56px;font-size:20px;padding:0 34px">保存并检测</button>' \
           f'<button class="btn" style="height:56px;font-size:18px">取消</button>' \
           f'<span style="font-size:16px;color:#909399">保存后自动判定，异常时会立刻通知家属</span></div></div>' \
           f'<div class="mb">{card("判定依据（配置化，不硬编码）", cfg + "<div style=\'height:12px\'></div><div class=\'alert-info\'>阈值改动在管理端“预警规则配置”完成后即时生效，界面只展示、不写死。</div>")}</div>' \
           f'<div>{card("校验与失败状态", """<div class="alert-warn" style="margin-bottom:12px">舒张压大于收缩压时不允许保存，提示“低压不应高于高压”。</div><div class="alert-info">保存失败（网络异常）时保留已填内容，并在按钮上方给出“保存失败，请重试”，不清空表单。</div>""")}</div>' \
           f'</div>{disclaimer()}</div>'
    return ('UI-ELDER-04', '指标录入', '正常 / 范围校验拦截 / 保存失败重试 / 录入即触发判定',
            'elder', '指标录入', True, body, ELDER_CSS)


def _elder_history():
    rows = [
        ['2026-09-14 16:30', '血压', '185/100 mmHg', tag('高风险 level 3', 'danger')],
        ['2026-09-13 20:10', '血压', '178/102 mmHg', tag('高风险 level 3', 'danger')],
        ['2026-09-12 08:05', '血压', '170/98 mmHg', tag('偏高 level 2', 'warning')],
        ['2026-09-11 08:12', '血压', '165/95 mmHg', tag('偏高 level 1', 'warning')],
        ['2026-09-12 07:10', '血糖', '6.8 mmol/L', tag('偏高', 'warning')],
        ['2026-09-12 08:20', '心率', '76 次/分', tag('正常', 'success')],
        ['2026-09-11 22:30', '睡眠', '5.5 小时', tag('偏少', 'warning')],
    ]
    body = f'<div style="padding:22px 32px 36px"><div class="crumb">健康指标 / <b>指标历史</b></div>' \
           f'{filter_bar([inp("开始日期"), inp("结束日期"), inp("全部指标类型", sel=True), btn("查询", True), btn("重置")])}' \
           f'{card("指标记录", table(["测量时间", "指标类型", "数值", "判定结果"], rows) + pager(1, 5, 46))}' \
           f'<div style="height:18px"></div><div class="grid-2">' \
           f'<div>{card("空数据状态", empty("还没有任何指标记录", "完成第一次录入后，这里会按时间倒序展示", "空") + "<div style=\'height:12px\'></div>" + btn("去录入指标", True))}</div>' \
           f'<div>{card("异常与权限状态", """<div class="alert-info" style="margin-bottom:12px">异常记录可点击进入预警详情，查看阈值对比与近 7 天趋势。</div><div class="alert-warn">查看非本人档案的历史记录时返回 1002 无权限，界面提示“你无权查看该档案”，不展示分页空表。</div>""")}</div>' \
           f'</div>{disclaimer()}</div>'
    return ('UI-ELDER-05', '指标历史', '正常 / 空数据 / 筛选无结果 / 无权限',
            'elder', '指标录入', True, body, ELDER_CSS)


def _elder_trend():
    chart = chart_line(
        [{'name': '收缩压', 'color': '#409eff', 'vals': [128, 132, 130, 136, 141, 138, 145, 152, 148, 155, 160, 158, 165, 162, 170, 168, 175, 178, 172, 185]},
         {'name': '舒张压', 'color': '#67c23a', 'vals': [82, 84, 83, 85, 88, 86, 90, 92, 90, 94, 96, 95, 98, 96, 100, 99, 102, 104, 100, 100]}],
        ['8/26', '8/28', '8/30', '9/1', '9/3', '9/5', '9/7', '9/9', '9/11', '9/13'],
        ymin=60, ymax=200, abn=[(0, 18), (0, 19)])
    body = f'<div style="padding:22px 32px 36px"><div class="crumb">健康指标 / <b>健康趋势图</b></div>' \
           f'{filter_bar([inp("指标：血压", sel=True), inp("最近 30 天", sel=True), btn("切换为柱状图"), btn("导出图片")])}' \
           f'{card("血压趋势（收缩压 / 舒张压，异常点高亮）", chart + "<div style=\'font-size:15px;color:#909399;margin-top:8px\'>红点为超出风险等级的异常测量，点击可跳转对应预警详情</div>")}' \
           f'<div style="height:18px"></div>' \
           f'{stat_grid([("近 30 天测量次数", "20", "次", "平均 1.4 天一次"), ("收缩压均值", "154", "mmHg", "较上月 +12"), ("最高收缩压", "185", "mmHg", "2026-09-14"), ("异常次数", "8", "次", "其中高风险 2 次")])}' \
           f'<div class="grid-2">' \
           f'<div>{card("数据不足状态", empty("数据积累中", "该指标少于 2 条记录，暂不绘制趋势曲线", "空"))}</div>' \
           f'<div>{card("AI 参与方式", """<div class="alert-info" style="margin-bottom:12px">趋势图本身由规则与统计生成，不依赖大模型；大模型仅用于生成自然语言解读。</div><div class="alert-warn">当模型不可用时，趋势图与数值照常展示，解读区域显示“AI 解读暂不可用”。</div>""")}</div>' \
           f'</div>{disclaimer()}</div>'
    return ('UI-ELDER-06', '健康趋势图', '正常 / 数据不足（<2 条占位）/ 异常点高亮 / AI 解读降级',
            'elder', '指标录入', True, body, ELDER_CSS)


def _elder_ai():
    chat = f"""
<div class="bubble-row me"><div class="bubble-av">张</div><div>
  <div class="bubble">我最近的血压怎么样？</div><div class="bubble-meta" style="text-align:right">16:21</div></div></div>
<div class="bubble-row"><div class="bubble-av">AI</div><div>
  <div class="bubble">您最近 4 次血压测量结果分别是 <b>185/100、178/102、170/98、165/95 mmHg</b>（9月14日、13日、12日、11日），整体呈上升趋势，均高于您的正常上限 139/89 mmHg。<br><br>其中 9 月 13 日与 14 日两次已触发高风险预警。建议尽快联系家属或责任护工，并在安静状态下复测一次；若同时出现头痛、胸闷、视物模糊，请立即就医。
    <div class="bubble-src">依据来源：<b>本人健康指标（health_record）</b> · 近 30 天记录 20 条 · 预警记录 2 条</div>
  </div>
  <div class="bubble-meta">16:21　意图：DATA　Agent：HEALTH_DATA　安全等级：L2</div></div></div>
<div class="bubble-row me"><div class="bubble-av">张</div><div>
  <div class="bubble">高血压的人能吃鸡蛋吗？</div><div class="bubble-meta" style="text-align:right">16:23</div></div></div>
<div class="bubble-row"><div class="bubble-av">AI</div><div>
  <div class="bubble">可以吃，建议每天不超过 1 个全蛋。鸡蛋本身不升高血压，但油炸、腌制的做法（如咸蛋、煎蛋配咸菜）会明显增加钠摄入，不利于血压控制。对高血压人群，更关键的是把每日食盐控制在 5 g 以内。
    <div class="bubble-src">依据来源：<b>知识库（knowledge_chunk）</b> · 《中国高血压防治指南》科普条目 · 未读取您的个人指标</div>
  </div>
  <div class="bubble-meta">16:23　意图：NORMAL　Agent：HEALTH　安全等级：L1</div></div></div>
<div class="bubble-row me"><div class="bubble-av">张</div><div>
  <div class="bubble">我胸口很痛，喘不上气</div><div class="bubble-meta" style="text-align:right">16:25</div></div></div>
<div class="bubble-row"><div class="bubble-av">AI</div><div>
  <div class="bubble" style="border-color:#f56c6c;background:#fef0f0">这可能是需要立即处理的紧急情况。<b>请马上拨打 120</b>，并通知家属；不要自行驾车前往医院。在等待期间请保持坐位或半卧位，不要剧烈活动。<br><br>系统已同时为这次咨询<b>生成紧急预警</b>，并已通知您的家属李强与责任护工王护工（16:25:07）。
    <div class="bubble-src">系统动作：<b>写入 health_warning（level 3）+ 立即通知</b> · 不仅给出文字建议</div>
  </div>
  <div class="bubble-meta">16:25　意图：EMERGENCY　Agent：EMERGENCY　安全等级：L4</div></div></div>"""
    side = card('本次会话信息', f"""
<div class="elder-row"><div class="elder-k">当前档案</div><div class="elder-v">张桂兰（本人）</div></div>
<div class="elder-row"><div class="elder-k">意图路由</div><div class="elder-v">{tag('DATA', 'primary')} {tag('NORMAL', 'info')} {tag('EMERGENCY', 'danger')}</div></div>
<div class="elder-row"><div class="elder-k">调用 Agent</div><div class="elder-v">HEALTH_DATA · HEALTH · EMERGENCY</div></div>
<div class="elder-row"><div class="elder-k">今日剩余次数</div><div class="elder-v">17 / 20 次</div></div>
""") + '<div style="height:18px"></div>' + card('状态与降级', """
<div class="alert-warn" style="margin-bottom:12px">模型不可用：返回“AI 助手暂时不可用，请稍后再试”，<b>不影响</b>指标录入与预警功能。</div>
<div class="alert-warn" style="margin-bottom:12px">今日次数用尽：提示“今日咨询次数已达上限”，其余功能照常。</div>
<div class="alert-info">AI 回答仅作健康参考，不构成医疗诊断；紧急症状一律引导就医并落预警。</div>
""")
    body = f'<div style="padding:22px 32px 36px"><div class="crumb">AI 健康咨询 / <b>与健康助手对话</b></div>' \
           f'<div class="grid-2-1"><div>{card("对话", chat + "<div style=\'height:6px\'></div>" + chips(["我最近的血压怎么样？", "高血压能吃鸡蛋吗？", "我的预警是怎么回事？", "睡不好怎么办？"]))}' \
           f'</div><div>{side}</div></div>' \
           f'<div style="margin-top:18px">{disclaimer("本页内容由 AI 生成，仅供健康参考，不构成医疗诊断；紧急情况请立即拨打 120")}</div></div>'
    return ('UI-ELDER-07', 'AI 健康咨询', '正常（多意图路由）/ 紧急症状升级并落预警 / 模型不可用降级 / 超频限流 / 敏感词兜底',
            'elder', 'AI 健康咨询', True, body, ELDER_CSS)


def _elder_ai_history():
    rows = [
        ['2026-09-14 16:25', '我胸口很痛，喘不上气', tag('EMERGENCY', 'danger'), '已落预警 #40002'],
        ['2026-09-14 16:23', '高血压的人能吃鸡蛋吗？', tag('NORMAL', 'info'), '知识库 3 条'],
        ['2026-09-14 16:21', '我最近的血压怎么样？', tag('DATA', 'primary'), '指标 20 条 + 预警 2 条'],
        ['2026-09-13 09:02', '我这个预警是怎么回事？', tag('ABNORMAL', 'warning'), '预警 #40001 + 趋势'],
        ['2026-09-11 20:14', '晚上总是睡不着', tag('NORMAL', 'info'), '知识库 2 条'],
    ]
    detail = """<div class="bubble-row"><div class="bubble-av">AI</div><div><div class="bubble" style="font-size:14px">
您 9 月 13 日的预警（#40001）是因为收缩压达到 178 mmHg，超过高风险阈值 180 附近的警戒区间，规则判定为 level 3 高风险。当时的处理结果是“已电话联系，安排复诊”。
<div class="bubble-src">依据来源：<b>预警记录 #40001</b> · <b>近 7 天血压趋势</b></div></div></div></div>"""
    body = f'<div style="padding:22px 32px 36px"><div class="crumb">AI 健康咨询 / <b>咨询历史</b></div>' \
           f'{filter_bar([inp("按档案：张桂兰（本人）", sel=True), inp("意图：全部", sel=True), inp("开始日期"), btn("查询", True)])}' \
           f'<div class="grid-2-1"><div>{card("历史会话", table(["时间", "提问摘要", "意图", "依据"], rows) + pager(1, 3, 28))}</div>' \
           f'<div>{card("会话回看", detail + "<div style=\'height:8px\'></div><div class=\'alert-info\'>回看历史会话不消耗当日咨询次数，也不会重新生成回答。</div>")}</div></div>' \
           f'<div style="height:18px"></div>' \
           f'<div style="height:18px"></div><div class="grid-2">' \
           f'<div>{card("空数据状态", empty("还没有咨询记录", "到 AI 健康咨询页提第一个问题吧", "空") + "<div style=\'height:12px\'></div>" + btn("去咨询", True))}</div>' \
           f'<div>{card("保留与权限", """<div class="alert-info" style="margin-bottom:12px">会话按老人档案隔离：家属切换代管老人后，只能看到该老人的咨询记录，不串档。</div><div class="alert-warn">咨询历史默认保留 12 个月，超期自动清理；清理仅删除问答文本，不影响健康指标与预警记录。</div>""")}</div></div>' \
           f'<div style="margin-top:18px">{disclaimer()}</div></div>'
    return ('UI-ELDER-08', '咨询历史', '正常 / 空数据 / 按档案筛选 / 权限隔离（仅本人与已绑定家属）',
            'elder', 'AI 健康咨询', True, body, ELDER_CSS)


def _elder_notice():
    rows = [
        [dot('danger') + '<b>高风险</b>', '血压 185/100 mmHg 超出高风险阈值', '2026-09-14 16:30', tag('未读', 'danger'), '查看详情'],
        [dot('danger') + '<b>高风险</b>', '血压 178/102 mmHg 超出高风险阈值', '2026-09-13 20:10', tag('已读', 'info'), '查看详情'],
        [dot('watch') + '<b>关注</b>', '收缩压 170 mmHg 连续 3 天偏高', '2026-09-12 08:05', tag('已读', 'info'), '查看详情'],
        [dot('watch') + '<b>关注</b>', '血糖 6.8 mmol/L 高于目标区间', '2026-09-12 07:10', tag('已读', 'info'), '查看详情'],
    ]
    tb = table(['级别', '预警内容', '时间', '我的状态', '操作'], rows)
    body = f'<div style="padding:22px 32px 36px"><div class="crumb">通知中心 / <b>我的预警通知</b></div>' \
           f'{stat_grid([("未读通知", "1", "条", "页面顶部红点同步显示"), ("本周新增预警", "3", "条", "高风险 2 条"), ("已处理", "1", "条", "由家属李强登记"), ("接收方式", "站内通知", "", "无短信 / 电话通道")])}' \
           f'{filter_bar([inp("全部状态", sel=True), inp("全部级别", sel=True), btn("只看未读"), btn("全部标为已读")])}' \
           f'{card("预警通知列表", tb + pager(1, 2, 12))}' \
           f'<div style="height:18px"></div><div class="grid-2">' \
           f'<div>{card("空数据状态", empty("暂无预警通知", "系统会持续监测您的指标，有异常会第一时间通知", "空"))}</div>' \
           f'<div>{card("状态说明", """<div class="alert-info" style="margin-bottom:12px">“我的状态”只表示本人是否已读；预警是否已处理是全局状态，由处理人决定，两者互不影响。</div><div class="alert-warn">通知范围仅限站内通知，不发送短信、不拨打语音电话；未读数量由客户端每 30 秒轮询一次。</div>""")}</div>' \
           f'</div>{disclaimer()}</div>'
    return ('UI-ELDER-09', '通知中心', '正常 / 未读红点 / 全部已读（空态）/ 已读与已处理状态正交',
            'elder', '通知中心', True, body, ELDER_CSS)


def _elder_warn_detail():
    chart = chart_line([{'name': '收缩压', 'color': '#409eff', 'vals': [165, 170, 178, 185]}],
                       ['9/11', '9/12', '9/13', '9/14'], ymin=140, ymax=200, w=580, h=200, abn=[(0, 3)])
    md = metric_detail([('本次收缩压', '185 mmHg', 'danger'), ('本次舒张压', '100 mmHg', 'danger'),
                        ('高风险阈值', '≥180 mmHg', ''), ('判定风险等级', 'level 3 高风险', 'danger'),
                        ('测量时间', '2026-09-14 16:30', ''), ('测量方式', '坐姿 · 静息后', '')])
    body = f'<div style="padding:22px 32px 36px"><div class="crumb">通知中心 / <b>预警详情</b></div>' \
           f'<div class="grid-2-1"><div>' \
           f'{card("预警 #40001 · 高风险", md + "<div style=\'height:16px\'></div>" + chart + "<div style=\'font-size:15px;color:#909399\'>近 7 天血压趋势（同类型指标对比）</div>")}' \
           f'<div style="height:18px"></div>' \
           f'{card("AI 预警摘要", """<div class="alert-warn">AI 摘要生成中或生成失败时，本区域显示：“AI 摘要暂不可用，可先查看下方原始数据与阈值对比”，<b>预警本身照常展示，不被隐藏</b>。</div><div style="height:12px"></div><div class="alert-info">摘要正常时展示：连续 4 天收缩压上升，今日 185 mmHg 为最高值，建议复测并尽快联系家属或就医。</div>""")}' \
           f'</div><div>' \
           f'{card("处理情况", timeline([("2026-09-14 16:41　李强（家属）登记处理", "方式：已电话联系老人　说明：已答应傍晚复测，若仍高于 180 立即送医"), ("2026-09-14 16:30　系统生成预警", "规则判定 level 3，接收人：家属李强、家属张敏（待确认，未接收）、护工王护工")]) + "<div style=\'height:10px\'></div>" + tag("当前全局状态：处理中", "warning"))}' \
           f'<div style="height:18px"></div>' \
           f'{card("我的操作", """<div style="font-size:14px;color:#606266;line-height:1.9;margin-bottom:14px">作为接收人，你可以登记处理结果。处理状态为全局共享，但“已读”状态仅代表你个人。</div>""" + btn("我已看到，稍后处理") + "　" + btn("填写处理结果", True) + "<div style=\'height:12px\'></div><div class=\'hint\'>多人接收时，他人处理的记录会展示在此页，避免重复联系。</div>")}' \
           f'</div></div><div style="margin-top:18px">{disclaimer()}</div></div>'
    return ('UI-ELDER-10', '预警详情', '正常（含 AI 摘要）/ AI 摘要失败降级不阻断 / 已被他人处理 / 已读未读独立',
            'elder', '通知中心', True, body, ELDER_CSS)


def _elder_checkin():
    items = [('血压', '已打卡　08:20 · 128/82 mmHg', 'success'), ('睡眠', '已打卡　昨晚 5.5 小时', 'success'),
             ('运动', '未打卡　今日 3200 步', 'warning'), ('服药', '未打卡　待 15:00 提醒', 'info')]
    rows = ''
    for k, v, t in items:
        rows += (f'<div class="elder-row"><div class="elder-k">{k}</div>'
                 f'<div class="elder-v" style="flex:1">{v}</div>'
                 f'<div>{tag("已完成" if t == "success" else ("待完成" if t == "warning" else "未开始"), t)}</div>'
                 f'<span style="margin-left:14px">{btn("一键打卡" if t != "success" else "重新打卡")}</span></div>')
    body = f'<div style="padding:22px 32px 36px"><div class="crumb">健康打卡 / <b>今日打卡</b></div>' \
           f'{stat_grid([("今日完成", "2 / 4", "项", "血压、睡眠已完成"), ("连续打卡", "6", "天", "最长记录 12 天"), ("本月打卡率", "78", "%", "较上月 +9%")], 3)}' \
           f'{card("今日打卡项目", rows)}' \
           f'<div style="height:18px"></div><div class="grid-2">' \
           f'<div>{card("全部完成状态", """<div class="alert-info" style="margin-bottom:12px">4 项全部完成时，页面顶部出现“今日打卡已完成”的绿条，并同步给已绑定家属。</div><div style="height:10px"></div><div class="empty-ico" style="width:52px;height:52px;font-size:18px;background:#f0f9eb;color:#67c23a;margin-bottom:10px">✓</div><div style="text-align:center;font-size:16px;color:#67c23a">今日打卡已完成，做得很好</div>""")}</div>' \
           f'<div>{card("说明", """<div class="alert-warn">【选配】健康打卡为可裁剪项，本期用于增强“主动式健康管理”的完整度，若工期不足可整体下线，不影响核心闭环。</div><div style="height:12px"></div><div class="alert-info">打卡数据写入 health_record（type=STEP / SLEEP），与人工录入共用同一张指标表，不额外建表。</div>""")}</div>' \
           f'</div>{disclaimer()}</div>'
    return ('UI-ELDER-11', '健康打卡', '正常 / 部分未打卡 / 全部完成 / 重复打卡覆盖提示',
            'elder', '首页', True, body, ELDER_CSS)


def _elder_medication():
    rows = [
        ['苯磺酸氨氯地平片', '5 mg', '每日 1 次 · 15:00', '2026-08-01 起', tag('服用中', 'success')],
        ['阿卡波糖片', '50 mg', '每日 3 次 · 随餐', '2026-06-15 起', tag('服用中', 'success')],
        ['阿司匹林肠溶片', '100 mg', '每日 1 次 · 20:00', '2026-08-01 起', tag('服用中', 'success')],
    ]
    form = ''
    form += form_row('药品名称', '<div class="inp ph" style="min-width:280px">如：苯磺酸氨氯地平片</div>', req=True)
    form += form_row('单次剂量', '<div class="inp" style="color:#303133;min-width:130px">5</div><div class="inp inp-sel" style="color:#303133">mg</div>')
    form += form_row('服用频次', '<div class="inp inp-sel" style="color:#303133">每日 1 次</div><div class="inp" style="color:#303133">15:00</div>')
    form += form_row('开始日期', '<div class="inp" style="color:#303133">2026-08-01</div>')
    body = f'<div style="padding:22px 32px 36px"><div class="crumb">健康档案 / <b>用药信息</b></div>' \
           f'<div class="grid-2-1"><div>{card("在用药品", table(["药品名称", "剂量", "服用时间", "开始时间", "状态"], rows) + pager(1, 1, 3))}' \
           f'<div style="height:18px"></div>{card("空数据状态", empty("还没有添加用药信息", "添加后可在首页“今日提醒”中按时提示", "空") + "<div style=\'height:12px\'></div>" + btn("添加药品", True))}</div>' \
           f'<div>{card("新增用药", form + "<div style=\'height:14px\'></div>" + btn("保存", True) + "　" + btn("取消"))}' \
           f'<div style="height:18px"></div>{card("说明", """<div class="alert-warn">【选配】用药信息为可裁剪项，对应 data 表 medication，本期仅记录与提醒，不做用药冲突校验。</div><div style="height:12px"></div><div class="alert-info">药品与剂量为用户自行录入，系统不提供用药建议，仅按时间提醒。</div>""")}</div>' \
           f'</div>{disclaimer()}</div>'
    return ('UI-ELDER-12', '用药信息', '正常 / 空数据 / 新增校验失败 / 停用药品',
            'elder', '健康档案', True, body, ELDER_CSS)


def _elder_bind():
    pending = table(['申请人', '与我的关系', '申请时间', '操作'],
                    [['李强', '儿子', '2026-09-13 19:02', btn('同意', True, True) + ' ' + btn('拒绝', False, True)],
                     ['张敏', '女儿', '2026-09-14 10:31', btn('同意', True, True) + ' ' + btn('拒绝', False, True)]])
    active = table(['姓名', '关系', '手机号', '生效时间', '操作'],
                   [['李强', '儿子', '130 0000 0003', '2026-09-13 19:20', btn('解除绑定', False, True)],
                    ['王护工', '责任护工（由管理员分配）', '130 0000 0004', '2026-09-10 09:00', '<span style="color:#c0c4cc">不可解绑</span>']])
    detail = f"""<div class="elder-row"><div class="elder-k">申请人</div><div class="elder-v">张敏</div></div>
<div class="elder-row"><div class="elder-k">关系</div><div class="elder-v">女儿</div></div>
<div class="elder-row"><div class="elder-k">申请手机号</div><div class="elder-v">130 0000 0007</div></div>
<div class="elder-row"><div class="elder-k">申请时间</div><div class="elder-v">2026-09-14 10:31</div></div>
<div class="elder-row"><div class="elder-k">可见范围（同意后）</div><div class="elder-v">健康档案 · 指标与趋势 · 预警通知 · 代录数据</div></div>
<div style="margin-top:16px;display:flex;gap:12px">{btn('同意绑定', True)}{btn('拒绝')}</div>"""
    body = f'<div style="padding:22px 32px 36px"><div class="crumb">我的 / <b>家属绑定确认</b></div>' \
           f'{card("待我确认的绑定申请（同意后才生效）", pending)}' \
           f'<div style="height:18px"></div>' \
           f'{card("已生效的绑定关系", active)}' \
           f'<div style="height:18px"></div><div class="grid-2">' \
           f'<div>{card("无待确认申请（空态）", empty("暂无绑定申请", "家属提交申请后，会出现在上方列表并给出提醒", "空"))}</div>' \
           f'<div>{card("当前申请详情 / 解绑确认", detail + "<div style=\'height:16px\'></div><div class=\'alert-warn\'>解除绑定后，该家属立即无法查看任何数据；历史处理记录仍保留可追溯。</div>")}</div>' \
           f'</div><div style="margin-top:18px">{disclaimer()}</div></div>'
    return ('UI-ELDER-13', '绑定确认', '正常 / 无待确认申请（空态）/ 拒绝后不可见数据 / 解绑二次确认',
            'elder', '我的', True, body, ELDER_CSS)


def pages():
    return [_login(), _register(), _profile(), _forgot(),
            _elder_home(), _elder_record(), _elder_record_edit(), _elder_input(), _elder_history(),
            _elder_trend(), _elder_ai(), _elder_ai_history(), _elder_notice(), _elder_warn_detail(),
            _elder_checkin(), _elder_medication(), _elder_bind()]
