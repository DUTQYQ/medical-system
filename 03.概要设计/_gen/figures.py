# -*- coding: utf-8 -*-
"""03.概要设计 v2.0 生成器 · 出图
产出 19 张图到 03.概要设计/图_v2/：
  图2-1 系统结构图（模块分解树状图）
  图3-1 ~ 图3-18：9 个模块 ×（模块结构图 + UML 类图）
依赖：Graphviz dot（Anaconda Scripts/dot.BAT）。改内容后重跑本脚本即可重建全部图。
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_modules import (MODULES, DOMAINS, CLIENTS, INFRA, TECH_MODULES,  # noqa: E402
                          slug)

TECH_SHORT = {"T1": "T1 数据访问", "T2": "T2 鉴权上下文", "T3": "T3 统一响应",
              "T4": "T4 日志与审计", "T5": "T5 配置缓存", "T6": "T6 文件存储"}

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 03.概要设计
OUT = os.path.join(BASE, "图_v2")
DOT = r"C:\Users\qiuyu\QYQAnaconda\Library\bin\dot.exe"

GRAPH_HEAD = '''digraph G {{
  graph [fontname="Microsoft YaHei", bgcolor="white", rankdir=TB,
         nodesep={ns}, ranksep={rs}, dpi=200, pad=0.3, splines=spline, compound=true];
  node  [shape=box, style="rounded,filled", fontname="Microsoft YaHei", fontsize=15,
         penwidth=1.5, margin="0.20,0.12", fillcolor="#eff6ff", color="#3b82f6"];
  edge  [fontname="Microsoft YaHei", fontsize=12, color="#94a3b8", fontcolor="#475569",
         penwidth=1.1, arrowsize=0.7];
'''

CLUSTER = '''  subgraph cluster_{cid} {{
    label="{label}"; labeljust="l"; fontname="Microsoft YaHei";
    fontsize={fs}; fontcolor="{fc}"; style="rounded"; color="{cc}"; penwidth=1.4; margin=12;
{body}
  }}
'''


def esc(s):
    """HTML-like label 转义"""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def uml(name, resp, fill="#eff6ff", color="#3b82f6", fs=15):
    """UML 类框：类名（下划线）+ 职责，两个分隔栏"""
    return ('<<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="5" '
            f'BGCOLOR="{fill}" COLOR="{color}">'
            f'<TR><TD SIDES="B"><FONT POINT-SIZE="{fs}"><U>{esc(name)}</U></FONT></TD></TR>'
            f'<TR><TD><FONT POINT-SIZE="11">{esc(resp)}</FONT></TD></TR>'
            '</TABLE>>')


# ----------------------------------------------------------------------------
# 图2-1 系统结构图（模块分解树状图）
# ----------------------------------------------------------------------------
def fig_system():
    mod_of = {}
    for dom, codes in DOMAINS:
        mod_of[dom] = [m for m in MODULES if m["code"] in codes]

    body = []
    for i, (dom, codes) in enumerate(DOMAINS, 1):
        rows = []
        for m in mod_of[dom]:
            rows.append('    n_%s [label="%s %s\\n%s", fillcolor="#eff6ff", color="#3b82f6"];'
                        % (m["code"], m["code"], m["cn"], m["en"]))
        body.append(CLUSTER.format(cid="d%d" % i, label=dom, fs=15, fc="#0f172a",
                                   cc="#cbd5e1", body="\n".join(rows)))

    clients = "\n".join(
        '    c%d [label="%s\\n%s", fillcolor="#f0fdf4", color="#16a34a"];' % (i, n, d)
        for i, (n, d) in enumerate(CLIENTS, 1))
    tech = "\n".join(
        '    n_%s [label="%s", fillcolor="#fef9c3", color="#ca8a04"];' % (t["code"], TECH_SHORT[t["code"]])
        for t in TECH_MODULES)

    dot = GRAPH_HEAD.format(ns=0.4, rs=0.7)
    dot = dot.replace('pad=0.3, splines=spline, compound=true];',
                      'pad=0.3, splines=spline, compound=true, size="10,7"];')
    dot += '  root [label="基于 AI 智能体的智能康养系统\\nB/S 架构 · 前后端分离 · 38 个界面 / 45 个接口 / 15 张表",' \
           ' fillcolor="#1e293b", fontcolor="white", color="#0f172a", fontsize=17, margin="0.30,0.16"];\n'
    dot += CLUSTER.format(cid="client", label="界面层（用户端）", fs=15,
                          fc="#14532d", cc="#86efac", body=clients)
    dot += "\n".join(body) + "\n"
    dot += CLUSTER.format(cid="tech", label="技术层（被业务模块共用的公共基础设施）", fs=15,
                          fc="#854d0e", cc="#facc15", body=tech)

    # 层级：根 → 界面层 → 业务模块 → 技术模块
    dot += '  hub [shape=point, width=0.01, style=invis];\n'
    for i in range(1, 6):
        dot += '  root -> c%d [style=dashed];\n' % i
        dot += '  c%d -> hub [style=invis];\n' % i
    for m in MODULES:
        dot += '  hub -> n_%s [style=invis];\n' % m["code"]
    for code in ("M1", "M3", "M4"):
        dot += '  root -> n_%s [style=dashed];\n' % code
    # 业务模块依赖技术模块（技术支撑业务）
    for code in ("M1", "M3", "M4"):
        dot += '  n_%s -> n_T1 [style=dashed, color="#ca8a04", fontcolor="#854d0e"%s];\n' % (
            code, ', label="依赖技术模块"' if code == "M1" else '')
    dot += '  n_M5 -> n_T4 [style=dashed, color="#ca8a04"];\n'
    dot += '  n_M8 -> n_T4 [style=dashed, color="#ca8a04"];\n'
    dot += '}\n'
    return dot


# ----------------------------------------------------------------------------
# 图2-2 分层架构图
# ----------------------------------------------------------------------------
def fig_layers():
    dot = GRAPH_HEAD.format(ns=0.4, rs=0.62)
    dot = dot.replace('pad=0.3, splines=spline, compound=true];',
                      'pad=0.3, splines=spline, compound=true, size="9.5,7"];')
    layers = [
        ("L1", "表示层（前端）", "Vue3 + Element Plus · 38 个界面\\n老人端 13 / 家属端 5 / 护工端 6 / 管理员端 10 / 公共 4",
         "#f0fdf4", "#16a34a"),
        ("L2", "接口层", "FastAPI APIRouter · 45 个接口\\n参数校验（Pydantic v2）· 统一响应 ApiResponse[T]",
         "#dbeafe", "#3b82f6"),
        ("L3", "应用服务层", "9 个业务模块 Service\\nAI Agent 编排（意图识别 / RAG / 四类 Agent）· 事务边界（T1 UnitOfWork）",
         "#eff6ff", "#3b82f6"),
        ("L4", "数据访问层", "Repository / BaseRepository（T1）\\nSQLAlchemy 2.0 · 只读会话 · 软删除过滤",
         "#f8fafc", "#64748b"),
        ("L5", "数据与外部服务层", "MySQL 8.0（15 张表）· LLM 服务（DeepSeek / 千问 / GLM-4）· 向量库（Chroma / FAISS）· 文件存储",
         "#f1efE8", "#888780"),
    ]
    for i, (code, name, desc, fill, color) in enumerate(layers, 1):
        dot += ('  %s [label="%s　%s\\n%s", fillcolor="%s", color="%s", fontsize=14];\n'
                % (code, code, name, desc, fill, color))
    dot += '  subgraph cluster_cross {\n'
    dot += '    label="横切机制（技术模块，被各层共用）"; labeljust="l"; fontname="Microsoft YaHei";\n'
    dot += '    fontsize=14; fontcolor="#854d0e"; style="rounded,dashed"; color="#facc15"; margin=10;\n'
    dot += '    X1 [label="T2 鉴权与请求上下文\\nJWT · require_role · 请求 ID", fillcolor="#fef9c3", color="#ca8a04", fontsize=13];\n'
    dot += '    X2 [label="T3 统一响应与异常处理\\n错误码 · 全局异常处理器", fillcolor="#fef9c3", color="#ca8a04", fontsize=13];\n'
    dot += '    X3 [label="T4 日志与审计\\n请求日志 · AI 调用留痕 · 审计", fillcolor="#fef9c3", color="#ca8a04", fontsize=13];\n'
    dot += '    {rank=same; X1; X2; X3;}\n'
    dot += '  }\n'
    iface_edges = [("L1", "L2", "HTTP / JSON"), ("L2", "L3", "调用 Service"),
                   ("L3", "L4", "读写"), ("L4", "L5", "持久化 / 检索")]
    for a, b, lbl in iface_edges:
        dot += '  %s -> %s [label="%s", color="#3b82f6", fontcolor="#1d4ed8"];\n' % (a, b, lbl)
    # 由应用服务层牵出，令横切模块与数据访问层同层（rank=same 必须写在 cluster 内部）
    dot += '  L3 -> X1 [style=dashed, color="#ca8a04", fontcolor="#854d0e", label="依赖"];\n'
    dot += '}\n'
    return dot


# ----------------------------------------------------------------------------
# 3.x.2 模块结构图（单 cluster 分层：接口层 → 服务层 → 数据层 + 依赖/触发）
# ----------------------------------------------------------------------------
def fig_structure(m):
    s = m["structure"]
    iface = "\n".join(
        '    s%d [label="%s", fillcolor="#dbeafe", color="#3b82f6"];' % (i, t)
        for i, t in enumerate(s["iface"], 1))
    svc = "\n".join(
        '    v%d [label="%s", fillcolor="#eff6ff", color="#3b82f6"];' % (i, t)
        for i, t in enumerate(s["service"], 1))
    data = "\n".join(
        '    d%d [label="%s", fillcolor="#f8fafc", color="#64748b"];' % (i, t)
        for i, t in enumerate(s["data"], 1))
    side = "\n".join(
        '    x%d [label="%s", fillcolor="#fef9c3", color="#ca8a04", style="rounded,dashed"];'
        % (i, t) for i, t in enumerate(s["side"], 1))

    n_if, n_sv, n_da, n_sd = len(s["iface"]), len(s["service"]), len(s["data"]), len(s["side"])
    rank_lines = (
        "    {rank=same; %s}\n" % " ".join("s%d" % i for i in range(1, n_if + 1))
        + "    {rank=same; %s}\n" % " ".join("v%d" % i for i in range(1, n_sv + 1))
        + "    {rank=same; %s %s}\n" % (" ".join("d%d" % i for i in range(1, n_da + 1)),
                                       " ".join("x%d" % i for i in range(1, n_sd + 1))))

    dot = GRAPH_HEAD.format(ns=0.35, rs=0.5)
    dot = dot.replace('pad=0.3, splines=spline, compound=true];',
                      'pad=0.3, splines=spline, compound=true, size="9,4.6"];')
    dot += '  subgraph cluster_main {\n'
    dot += ('    label="%s %s　模块结构（%s）\\n实线箭头＝调用与读写；虚线箭头＝依赖与上游触发";'
            ' labeljust="l"; fontname="Microsoft YaHei";\n' % (m["code"], m["cn"], m["en"]))
    dot += '    fontsize=16; fontcolor="#0f172a"; style="rounded"; color="#cbd5e1"; penwidth=1.4; margin=14;\n'
    dot += iface + "\n" + svc + "\n" + data + "\n" + side + "\n"
    dot += rank_lines
    dot += "  }\n"

    for i in range(1, n_if + 1):
        dot += '  s%d -> v1 [label="调用", color="#3b82f6", fontcolor="#1d4ed8"];\n' % i
    for i in range(2, n_sv + 1):
        dot += '  v1 -> v%d [style=dashed, dir=both, arrowtail=none, constraint=false];\n' % i
    for i in range(1, n_da + 1):
        dot += '  v1 -> d%d [label="读写", color="#64748b", fontcolor="#475569"];\n' % i
    for i in range(1, n_sd + 1):
        dot += ('  v%d -> x%d [style=dashed, arrowhead=vee, color="#ca8a04", fontcolor="#854d0e", %s];\n'
                % ((i % n_sv) + 1, i, 'label="依赖 / 触发"' if i == 1 else 'constraint=false'))
    dot += "}\n"
    return dot


# ----------------------------------------------------------------------------
# 3.x.3 类图
# ----------------------------------------------------------------------------
def fig_class(m):
    dot = GRAPH_HEAD.format(ns=0.35, rs=0.5)
    dot = dot.replace('pad=0.3, splines=spline, compound=true];',
                      'pad=0.3, splines=spline, compound=true, size="9,6"];')
    dot += '  node [shape=plaintext, fillcolor="white", color="white", style=""];\n'
    dot += '  subgraph cluster_cls {\n'
    dot += '    label="%s %s　类图（%s）"; labeljust="l"; fontname="Microsoft YaHei";\n' % (
        m["code"], m["cn"], m["en"])
    dot += '    fontsize=16; fontcolor="#0f172a"; style="rounded"; color="#cbd5e1"; penwidth=1.4; margin=14;\n'
    for name, resp, fill, color in m["classes"]:
        dot += '    %s [label=%s];\n' % (name, uml(name, resp, fill, color))
    for name, resp in m.get("agents", []):
        dot += '    %s [label=%s];\n' % (name, uml(name, resp, "#f5f3ff", "#8b5cf6"))
    dot += "  }\n"
    for a, b, kind in m["class_edges"]:
        if kind == "泛化":
            dot += '  %s -> %s [arrowhead=onormal, color="#16a34a", penwidth=1.2];\n' % (a, b)
        else:
            dot += '  %s -> %s [label="%s", arrowhead=vee, color="#64748b"];\n' % (a, b, kind)
    dot += "}\n"
    return dot


def render(name, src):
    os.makedirs(OUT, exist_ok=True)
    dotp = os.path.join(OUT, name + ".dot")
    pngp = os.path.join(OUT, name + ".png")
    with open(dotp, "w", encoding="utf-8") as f:
        f.write(src)
    r = subprocess.run([DOT, "-Tpng", "-O", dotp], capture_output=True)
    # dot -O 生成 name.dot.png，统一改名
    gen = dotp + ".png"
    if os.path.exists(gen):
        if os.path.exists(pngp):
            os.remove(pngp)
        os.rename(gen, pngp)
    ok = os.path.exists(pngp)
    print(("OK  " if ok else "FAIL") , name, os.path.getsize(pngp) if ok else r.stderr[:200])
    return ok


def main():
    made = []
    made.append(("图2-1_模块分解图", fig_system()))
    made.append(("图2-2_分层架构图", fig_layers()))
    n = 0
    for m in MODULES:
        n += 1
        made.append(("图3-%d_%s%s_模块结构图" % (n, m["code"], slug(m["cn"])), fig_structure(m)))
        n += 1
        made.append(("图3-%d_%s%s_类图" % (n, m["code"], slug(m["cn"])), fig_class(m)))
    for t in TECH_MODULES:
        if "classes" not in t:      # T3 / T5 / T6 仅列清单，不出图
            continue
        n += 1
        made.append(("图3-%d_%s%s_模块结构图" % (n, t["code"], slug(t["cn"])), fig_structure(t)))
        n += 1
        made.append(("图3-%d_%s%s_类图" % (n, t["code"], slug(t["cn"])), fig_class(t)))
    allok = True
    for name, src in made:
        allok &= render(name, src)
    print("共 %d 张图，全部成功：%s" % (len(made), allok))


if __name__ == "__main__":
    main()
