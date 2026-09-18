# -*- coding: utf-8 -*-
"""数据字典生成器：解析 04.编码/数据库/schema.sql，输出与指导老师样例同款的 xlsx。
列结构完全对齐 shengyadb.xls：类型/大小/名称/非空/默认值/补充/描述/扩展/左/类型/右/List显示/特殊取值描述/追加日期/追加原因
每张表一个工作表，另加首张「说明」页。
"""
import os
import re
import datetime

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

ROOT = r"D:\Desktop\康养系统实训项目"
SCHEMA = os.path.join(ROOT, "04.编码", "数据库", "schema.sql")
OUT = os.path.join(ROOT, "04.编码", "数据库", "数据字典_康养系统_v1.0.xlsx")

HEADERS = ["类型", "大小", "名称", "非空", "默认值", "补充", "描述", "扩展",
           "左", "类型", "右", "List显示", "特殊取值描述", "追加日期", "追加原因"]

# 枚举字段的取值说明（人工校订，来源：概要设计 v2.0 表 5-1）
ENUM_DESC = {
    "role": "ELDER 老年用户 / FAMILY 家属 / CARE 护工 / ADMIN 管理员",
    "gender": "M 男 / F 女",
    "type": "指标：BLOOD_PRESSURE 血压 / BLOOD_SUGAR 血糖 / HEART_RATE 心率 / SLEEP 睡眠 / STEP 步数",
    "level": "0 正常 / 1 轻度 / 2 较高 / 3 高风险",
    "trigger_source": "DATA_INPUT 录入触发 / AI_CHAT 咨询触发 / MANUAL 人工创建",
    "summary_status": "PENDING 生成中 / SUCCESS 成功 / FAILED 失败 / SKIPPED 低级别不生成",
    "read_status": "UNREAD 未读 / READ 已读",
    "action": "CONTACTED 已联系 / ARRANGED_VISIT 安排上门 / SENT_HOSPITAL 送医 / OBSERVE 继续观察",
    "role_chat": "user 用户提问 / assistant 模型回答",
    "intent": "NORMAL 普通咨询 / DATA 数据类 / ABNORMAL 异常 / EMERGENCY 紧急",
    "agent": "HEALTH / HEALTH_DATA / RISK / EMERGENCY 四类智能体",
    "safety_level": "L1 / L2 / L3 / L4 安全分级，L3 以上须附就医引导",
    "blood_type": "A / B / AB / O / 其他",
    "config_type": "threshold 阈值 / number 数值 / string 字符串 / json 结构化",
    "group_name": "threshold 阈值 / system 系统参数 / notify 通知参数",
    "category": "高血压 / 糖尿病 / 心率异常 / 睡眠 / 老年运动 / 老年饮食 / 常见问题",
    "enabled": "1 启用 / 0 停用",
    "deleted": "0 正常 / 1 已删除（软删除）",
    "is_abnormal": "0 未触发异常 / 1 已触发异常",
    "success": "1 调用成功 / 0 调用失败（用于说明 AI 降级设计，D-04）",
}

# 补充列：主键 / 外键 / 索引 / 唯一
FORM_CTRL = {
    "VARCHAR": "input", "CHAR": "select", "TEXT": "textarea", "MEDIUMTEXT": "textarea",
    "INT": "number", "BIGINT": "number", "TINYINT": "select", "DECIMAL": "number",
    "DATE": "datepicker", "DATETIME": "datetimepicker", "JSON": "textarea",
}

# 同名 status 在不同表语义不同，按「表.字段」精确给出
PAIR_DESC = {
    ("user", "status"): "1 启用 / 0 禁用（禁用后 Token 立即失效）",
    ("family_bind", "status"): "PENDING 待确认 / APPROVED 已生效 / REJECTED 已拒绝 / REVOKED 已解绑",
    ("health_warning", "status"): "PENDING 待处理 / PROCESSING 处理中 / RESOLVED 已处理 / IGNORED 已忽略",
    ("care_relation", "status"): "1 在管 / 0 已交接",
    ("family_bind", "relation"): "儿子 / 女儿 / 配偶 等，自由文本",
    ("chat_message", "role"): "user 用户提问 / assistant 模型回答",
    ("alert_receiver", "read_status"): "UNREAD 未读 / READ 已读（每个接收人独立）",
    ("health_warning", "summary_status"): "PENDING 生成中 / SUCCESS 成功 / FAILED 失败 / SKIPPED 低级别不生成",
    ("warning_handle_record", "action"): "CONTACTED 已联系 / ARRANGED_VISIT 安排上门 / SENT_HOSPITAL 送医 / OBSERVE 继续观察",
    ("health_record", "type"): "BLOOD_PRESSURE 血压 / BLOOD_SUGAR 血糖 / HEART_RATE 心率 / SLEEP 睡眠 / STEP 步数",
    ("sys_config", "config_type"): "threshold 阈值 / number 数值 / string 字符串 / json 结构化",
    ("sys_config", "group_name"): "threshold 阈值 / system 系统参数 / notify 通知参数",
    ("knowledge_document", "category"): "高血压 / 糖尿病 / 心率异常 / 睡眠 / 老年运动 / 老年饮食 / 常见问题",
}


def parse_schema(path):
    txt = open(path, encoding="utf-8").read()
    tables = {}
    order = []
    # 建表语句（把 ENGINE 之后的尾部一起纳入，才能取到表注释）
    for m in re.finditer(r"CREATE TABLE `(\w+)` \((.*?)\n\) ENGINE=InnoDB(.*?);", txt, re.S):
        name, body, tail = m.group(1), m.group(2), m.group(3)
        cm = re.search(r"COMMENT='([^']*)'", tail)
        raw_comment = cm.group(1) if cm else ""
        comment = raw_comment.replace("【选配】", "")
        opt = "选配" if "【选配】" in raw_comment else "核心"
        cols, keys = [], []
        for line in body.split("\n"):
            line = line.strip().rstrip(",")
            if not line:
                continue
            if line.upper().startswith(("PRIMARY KEY", "UNIQUE KEY", "KEY ", "CONSTRAINT")):
                keys.append(line)
                continue
            cm2 = re.match(
                r"`(\w+)`\s+([A-Za-z]+)(?:\(([^)]*)\))?\s*(NOT NULL)?\s*(?:DEFAULT\s+('?[^ ,]+'?))?",
                line)
            if not cm2:
                continue
            col, typ, size, notnull, default = cm2.groups()
            dc = re.search(r"COMMENT '([^']*)'", line)
            desc = dc.group(1) if dc else ""
            cols.append(dict(name=col, type=typ.upper(), size=size or "",
                             notnull="Y" if notnull else "", default=(default or "").strip("'"),
                             desc=desc))
        tables[name] = dict(comment=comment, opt=opt, cols=cols, keys=keys)
        order.append(name)
    # 外键（注意对齐中的多空格）
    fks = {}
    for m in re.finditer(r"ALTER TABLE `(\w+)`(.*?);", txt, re.S):
        tbl, seg = m.group(1), m.group(2)
        for f in re.finditer(
                r"FOREIGN KEY\s*\(`(\w+)`\)\s+REFERENCES\s+`(\w+)`\s*\(`(\w+)`\)"
                r"(?:\s+ON DELETE\s+(CASCADE|SET NULL|RESTRICT))?",
                seg):
            rule = f.group(4) or "RESTRICT"
            fks.setdefault(tbl, {})[f.group(1)] = (f.group(2), f.group(3), rule)
    return tables, order, fks


def main():
    tables, order, fks = parse_schema(SCHEMA)
    wb = Workbook()

    # ---------------- 说明页 ----------------
    ws = wb.active
    ws.title = "说明"
    lines = [
        ("基于 AI 智能体的智能康养系统 · 数据字典", True),
        ("", False),
        ("数据库：MySQL 8.0 ／ 存储引擎：InnoDB ／ 字符集：utf8mb4 ／ 排序规则：utf8mb4_general_ci", False),
        ("版本：v1.0　日期：2026-09-24　编制：丘宇乾　来源：04.编码/数据库/schema.sql（本文件由脚本解析生成，与建表脚本同源）", False),
        ("", False),
        ("【指导老师对数据库设计的四条要求及本设计的落实】", True),
        ("1. 划分主表和从表确定主外键关系，不能所有数据一张表 —— 已划分 15 张表，共 12 个外键，主从关系见各表「左 / 右」列。", False),
        ("2. 首先确定基础表，再确认业务表 —— 基础表 4 张（user、elder_profile、family_bind、care_relation）→ 配置表 1 张（sys_config）→ 业务表 6 张 → 选配表 4 张，建表顺序与依赖一致。", False),
        ("3. 数据库设计满足三个范式 —— 满足 1NF / 2NF / 3NF；三处有意的反规范化（chronic_tags 的 JSON 存储、chat_message 的编排快照字段、health_warning 的 value_text）已在《概要设计说明书 v2.0》4.2.4 节逐条说明理由。", False),
        ("4. 数据字典按固定列结构给出 —— 本文件每张表一个工作表，列结构与指导老师下发样例一致。", False),
        ("", False),
        ("【列含义说明】", True),
        ("类型 / 大小：MySQL 字段类型与长度（DECIMAL 记为 精度,小数位）。", False),
        ("名称：字段名。", False),
        ("非空：Y 表示 NOT NULL。", False),
        ("默认值：建表语句中的 DEFAULT 值。", False),
        ("补充：主键 PK / 外键 FK / 唯一 UK / 索引 IDX / 业务约束。", False),
        ("描述：字段中文含义，取自建表语句 COMMENT。", False),
        ("扩展：前端表单控件类型。", False),
        ("左 / 类型 / 右：外键关系三列，读法为「左表（子表）字段 → 类型 → 右表（父表）字段」。", False),
        ("List显示：Y 表示列表页需要展示该字段。", False),
        ("特殊取值描述：枚举型字段的取值含义。", False),
        ("追加日期 / 追加原因：需求追加时的留痕列，本版本无追加项，留空。", False),
        ("", False),
        ("【表清单】", True),
    ]
    r = 1
    for text, bold in lines:
        c = ws.cell(row=r, column=1, value=text)
        if bold:
            c.font = Font(bold=True, size=12)
        c.alignment = Alignment(vertical="center")
        r += 1
    for i, t in enumerate(order, 1):
        ws.cell(row=r, column=1, value="%d. %s —— %s（%s）" % (
            i, t, tables[t]["comment"], tables[t]["opt"]))
        r += 1
    ws.column_dimensions["A"].width = 150

    # ---------------- 每表一页 ----------------
    thin = Side(style="thin", color="BFBFBF")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    head_fill = PatternFill("solid", fgColor="DDEBF7")
    key_fill = PatternFill("solid", fgColor="FFF2CC")

    for tname in order:
        t = tables[tname]
        s = wb.create_sheet(tname[:31])
        s["A1"] = tname
        s["B2"], s["C2"] = "表描述", t["comment"]
        s["E2"], s["H2"] = "做成日期", datetime.date(2026, 9, 12)
        s["B3"], s["C3"] = "表名称", tname
        s["E3"], s["F3"] = "备注", "【选配】表，本期不实现" if t["opt"] == "选配" else ""

        # 表头
        for i, h in enumerate(HEADERS):
            c = s.cell(row=4, column=i + 2, value=h)
            c.font = Font(bold=True)
            c.fill = head_fill
            c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            c.border = border

        # 主键 / 唯一 / 索引
        pk = ""
        for k in t["keys"]:
            if k.upper().startswith("PRIMARY KEY"):
                pk = re.search(r"`(\w+)`", k).group(1)
        uk_cols, idx_cols = set(), set()
        for k in t["keys"]:
            cols = re.findall(r"`(\w+)`", k)
            if k.upper().startswith("UNIQUE KEY"):
                uk_cols.add(cols[-1] if len(cols) > 1 else cols[0])
            elif k.upper().startswith("KEY "):
                for c2 in cols:
                    idx_cols.add(c2)

        row = 5
        for col in t["cols"]:
            n = col["name"]
            extra = []
            if n == pk:
                extra.append("PK 主键")
            if n in fks.get(tname, {}):
                extra.append("FK 外键")
            if n in uk_cols:
                extra.append("UK 唯一")
            elif n in idx_cols:
                extra.append("IDX 索引")
            if tname == "user" and n == "status":
                extra.append("1 启用 / 0 禁用")
            if tname == "family_bind" and n == "status":
                extra.append("PENDING/APPROVED/REJECTED/REVOKED；同一对家属—老人不得重复，由应用层校验")
            if tname == "health_warning" and n == "status":
                extra.append("PENDING/PROCESSING/RESOLVED/IGNORED；与已读状态正交（D-05）")
            if tname == "care_relation" and n == "status":
                extra.append("1 在管 / 0 已交接")
            if tname == "chat_message" and n == "role":
                extra.append("role=user / assistant")

            left = right = rel = ""
            if n in fks.get(tname, {}):
                pt, pc, rule = fks[tname][n]
                left, rel, right = "%s.%s" % (tname, n), "N : 1", "%s.%s" % (pt, pc)
                extra.append({"CASCADE": "级联删除", "SET NULL": "删除置空",
                              "RESTRICT": "存在则禁删"}[rule])

            size = col["size"]
            if col["type"] == "DECIMAL" and size:
                size = size.replace(",", ",")

            vals = [
                col["type"], size, n, col["notnull"], col["default"],
                "；".join(extra), col["desc"],
                FORM_CTRL.get(col["type"], "input"),
                left, rel, right,
                "" if col["type"] in ("TEXT", "MEDIUMTEXT", "JSON") else "Y",
                PAIR_DESC.get((tname, n)) or ENUM_DESC.get(n, ""),
                "", "",
            ]
            for i, v in enumerate(vals):
                c = s.cell(row=row, column=i + 2, value=v)
                c.border = border
                c.alignment = Alignment(vertical="center", wrap_text=True)
                if extra and i == 4:
                    c.fill = key_fill
            row += 1

        s.cell(row=row, column=1, value="END")
        ws_widths = [8, 10, 22, 6, 12, 22, 34, 12, 20, 7, 22, 9, 40, 11, 11]
        for i, w in enumerate(ws_widths):
            s.column_dimensions[get_column_letter(i + 2)].width = w
        s.freeze_panes = "C5"

    wb.save(OUT)
    print("已生成", OUT)
    print("工作表 %d 个：说明 + %d 张表" % (len(wb.sheetnames), len(order)))
    print("表清单：", "、".join(order))


if __name__ == "__main__":
    main()
