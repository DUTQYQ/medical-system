# -*- coding: utf-8 -*-
"""03.概要设计 v2.0 生成器 · 正文
严格按老师《概要设计模板》的 5 章骨架输出 Markdown。
改内容 → 重跑本脚本 → 再跑 build_docx.py 转 Word。
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_modules import (MODULES, DOMAINS, CLIENTS, INFRA, slug,  # noqa: E402
                          TECH_MODULES, MODULE_FILES)
from data_funcs import (FUNCS, INTERNAL_FUNCS, NATURE_DEFAULT,  # noqa: E402
                        NATURE_OVERRIDE)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = os.path.join(os.path.dirname(BASE), "04.编码", "数据库", "schema.sql")
OUT_MD = os.path.join(BASE, "概要设计说明书_康养系统_v2.0.md")
FIGDIR = "图_v2"

FIGCAP = "\n\n![](%s/%s)\n\n"


def figure(path, caption):
    """图：图片独占一段，图题作为 pandoc 图注（Word 中为 Caption 样式）"""
    return "\n\n![%s](%s/%s)\n\n" % (caption, FIGDIR, path)


def cap(text):
    """图题作为段落，紧跟图片下方"""
    return "\n\n*%s*\n\n" % text


# ---------------------------------------------------------------- 封面 / 文控
COVER = """# 基于 AI 智能体的智能康养系统

## 概 要 设 计

| 项目 | 内容 |
|---|---|
| 密级 | 秘密 |
| 文档编号 | D0000-PPC-XXXX-2026-PPD-2026 |
| 项目名称 | 基于 AI 智能体的智能康养系统 |
| 项目编号 | 待学校 / 指导老师统一给定 |
| 文档名称 | 概要设计说明书 |
| 版本 | 0.8.0-0.0.0 |
| 编制日期 | 2026-09-24 |
| 编制单位 | 大连理工大学创新实践基地 |
| 总页数 | 见页脚域统计 |
| 正文页数 | 见页脚域统计 |
| 附录页数 | 见页脚域统计 |
| 生效日期 | 2026-09-24 |
| 编制 | 丘宇乾 |
| 批准 | 吴剑光 |

版权所有，翻版必究。

### 文件修改控制

| 修改编号 | 版本 | 修改条款及内容 | 修改日期 |
|---|---|---|---|
| 1 | 0.8.0-0.0.0 | 创建 | 2026-09-18 |
| 2 | 0.8.0-0.0.0 | 按指导老师下发的《概要设计模板》重构章节结构，补齐模块详细概述、全局变量、模块间接口函数设计与关键数据结构定义 | 2026-09-24 |
"""

# ---------------------------------------------------------------- 1 文档概述
CH1 = """## 1 文档概述

### 1.1 文档目的和范围

本文档是**基于 AI 智能体的智能康养系统**的概要设计说明书，用于描述系统总体结构、模块划分、数据库设计与接口约定，为后续详细设计、编码、测试与维护提供基准。

本系统的定位是**面向老年人的 AI 主动式健康管理平台**，而非"带聊天功能的养老系统"。其核心业务闭环为：

> 数据采集 → AI 分析 → 健康咨询 → 异常检测 → 预警 → 家属 / 护工处理 → 记录

**阅读对象**：项目指导老师、项目组全体成员（丘宇乾、梁霁鸣、周彦龙）、后续承接维护的开发与测试人员。

**范围界定**：本文档只覆盖系统的**总体结构、模块职责、数据库与接口设计**，不涉及界面视觉稿（见《原型设计说明书 v2.0》）、不涉及具体代码实现细节（见编码阶段交付物）。功能按【核心】与【选配】两级标注，【选配】功能本期不实现，交付文档中以文字标注，不使用图形符号。

**与其他文档的关系**：需求类问题以《需求分析说明书 v1.0》为准；设计层裁决以《设计决策记录 v1.0》为准；接口字段级细节以《API 接口契约 v0.2》为准；本文档与之冲突时，以《设计决策记录 v1.0》为最终依据。

### 1.2 术语/缩略语

| 序号 | 术语/缩略语 | 说明 |
|---|---|---|
| 1 | API | 应用程序编程接口（Application Programming Interface） |
| 2 | FR | 功能需求（Functional Requirement），编号形如 `FR-<前缀>-nnn` |
| 3 | Agent | 智能体，本项目中指由编排器调度的、承担特定意图处理职责的 AI 处理单元 |
| 4 | RAG | 检索增强生成（Retrieval-Augmented Generation） |
| 5 | LLM | 大语言模型（Large Language Model） |
| 6 | Prompt | 提交给大语言模型的提示词 |
| 7 | Embedding | 文本向量化，用于相似度检索 |
| 8 | 向量库 | 存放文本向量的数据库，本项目采用 Chroma 或 FAISS |
| 9 | E-R 图 | 实体—联系图（Entity-Relationship Diagram） |
| 10 | 三范式 | 关系数据库设计的第一、第二、第三范式（1NF / 2NF / 3NF） |
| 11 | DTO / VO | 数据传输对象 / 视图对象；本项目对应 Pydantic 的入参模型与出参模型 |
| 12 | JWT | JSON Web Token，本项目用于登录态鉴权 |
| 13 | 软删除 | 用标记字段代替物理删除，保留数据可追溯 |
| 14 | 预警接收人 | 一条预警推送到的每一个具体用户，各自持有独立的已读状态 |
| 15 | 风险等级 | 0 正常 / 1 轻度 / 2 较高 / 3 高风险，四级 |

### 1.3 参考文档

| 序号 | 文档名 | 作者 | 时间 | 版本 |
|---|---|---|---|---|
| 1 | 项目企划书（康养系统） | 项目组 | 2026-09-08 | v2.0 |
| 2 | 需求分析说明书（康养系统） | 项目组 | 2026-09-14 | v1.0 |
| 3 | 界面清单（康养系统） | 项目组 | 2026-09-14 | v1.0 |
| 4 | 原型设计说明书（康养系统） | 项目组 | 2026-09-14 | v2.0 |
| 5 | 设计决策记录（康养系统） | 丘宇乾 | 2026-09-12 | v1.0 |
| 6 | API 接口契约（康养系统） | 丘宇乾 | 2026-09-08 | v0.2 |
| 7 | 数据库建表脚本 schema.sql | 丘宇乾 | 2026-09-12 | v1.0 |
| 8 | 概要设计模板（指导教师下发） | 吴剑光 | 2026-09-15 | — |
| 9 | 概要设计样例：苍穹外卖管理系统（指导教师下发） | 徐诺言 | 2025-11-27 | 0.8.0-0.0.0 |
"""

# ---------------------------------------------------------------- 2 系统结构图
CH2_HEAD = """## 2 系统结构图

本系统采用 **B/S 架构、前后端分离**的组织形式。按指导老师要求，模块划分区分 **业务模块** 与 **技术模块** 两类：业务模块直接实现项目业务目标，技术模块是被各业务模块共用、支撑业务实现的基础设施。

系统整体分为两层模块、五个层次：

1. **业务层（业务模块 9 个）**：AUTH 认证与权限、PROFILE 健康档案、HEALTH 健康指标、AI 健康咨询与智能体编排、ALERT 主动预警、FAMILY 家属绑定、CARE 护工端、ADMIN 后台管理、CONFIG 系统配置。它们直接实现对老年人的健康管理业务闭环。
2. **技术层（技术模块 6 个）**：T1 数据访问与事务管理、T2 鉴权与请求上下文、T3 统一响应与异常处理、T4 日志与审计、T5 配置与阈值缓存、T6 文件存储【选配】。它们被业务模块共用，不直接承载业务语义。
3. **界面层**：按角色划分为老人端、家属端、护工端、管理员端与公共认证界面，共 38 个界面（核心 29 + 选配 9）。
4. **数据与外部服务层**：MySQL 8.0 数据库、大语言模型服务、向量库与文件存储。
5. **横切机制**：鉴权、统一响应、异常处理与日志审计由技术模块以中间件或依赖注入的形式贯穿各层。

模块分解关系如图 2-1 所示；五层架构与横切机制的分布如图 2-2 所示。

"""

CH2_TAIL = """**模块划分依据**：模块按**业务职责**划分而非按技术分层划分，一个模块内部同时包含接口、服务与数据访问三部分，便于组内按模块并行开发与交付。9 个业务模块与《API 接口契约 v0.2》第 2~10 章一一对应，接口总数为 45 个。

**关于"一个文件一个模块"**：指导老师指出工程惯例是"一个文件一个模块"。本项目采取的是**同一惯例的分层落地**——每个模块对应一组同名前缀的文件（接口文件 `api/v1/<模块>.py`、服务文件 `services/<模块>_service.py`、数据访问文件 `repositories/<模块>_repo.py`），模块之间只通过接口调用，不直接引用对方的内部实现。3.0.3 节给出完整的"模块 ↔ 文件"对应表。

**关于 AI 能力的位置**：AI 能力不作为锦上添花的附属功能，而是独立成 **M4 AI 健康咨询与智能体编排模块**，承担意图识别、多 Agent 编排、RAG 检索增强与风险判定；其判定结果通过 M5 主动预警模块进入业务闭环。这一编排关系在 3.4 节展开。
"""


def ch3():
    out = ["""## 3 模块详细概述

### 3.0 模块总体说明

后端共 **15 个模块**（业务模块 9 个 + 技术模块 6 个），对外接口 **45 个**，模块间调用接口 **8 个**。按指导老师要求，模块区分业务与技术两类，下列两张表分别列出；每个模块在 3.1~3.13 节按"功能定义 → 模块结构 → 类图与接口说明"三部分展开。

#### 3.0.1 业务模块清单

业务模块直接实现项目业务目标，共 9 个：

表 3-1　业务模块清单

| 编号 | 模块 | 英文标识 | 主要职责 | 对应契约章 |
|---|---|---|---|---|"""]
    for m in MODULES:
        out.append("| %s | %s | %s | %s | %s |" % (
            m["code"], m["cn"], m["en"], m["duty"], m["chapter"]))

    out.append("""
#### 3.0.2 技术模块清单

技术模块是被各业务模块**共用**的基础设施，只支撑业务实现、不直接承载业务语义。其中 T1 / T2 / T4 承载的公共能力最关键，在本章 3.11~3.13 节按四件套展开；T3 / T5 / T6 的能力已在 5.1 与 5.3 节中说明，此处仅列清单。

表 3-2　技术模块清单

| 编号 | 模块 | 主要职责 | 被谁共用 | 本章展开方式 |
|---|---|---|---|---|""")
    for t in TECH_MODULES:
        out.append("| %s | %s | %s | %s | %s |" % (
            t["code"], t["cn"], t["duty"], t["shared_by"], t["chapter"]))

    out.append("""
**技术支撑业务的落地方式**：业务模块**只调用技术模块对外暴露的接口**，不自行实现数据库会话、鉴权判定与日志写入。例如 M3 录入指标时通过 T1 的 `UnitOfWork` 开事务、经 M2 的 `resolve_visible_profiles` 校验数据范围、异常时由 T2 统一转成 1002，全过程由 T4 留痕。这样做的收益是：口径唯一（阈值、可见范围、错误码只有一处定义）、便于排查（请求 ID 串联全部日志）、可替换（换数据库或日志方案只改技术模块）。

#### 3.0.3 模块与文件的对应关系

按"一个模块一组同名文件"的落法，模块与代码文件的对应关系如下表。模块之间只通过接口调用，不直接引用对方的内部实现。

表 3-3　模块与文件对应表

| 编号 | 模块 | 接口层 | 服务层 | 数据访问 / 其他 |
|---|---|---|---|---|""")
    for code, name, iface, svc, repo in MODULE_FILES:
        out.append("| %s | %s | %s | %s | %s |" % (code, name, iface, svc, repo))

    out.append("""
**统一的技术约定**（后文各模块不再重复说明）：

| 项 | 约定 |
|---|---|
| 接口层 | FastAPI `APIRouter`，位于 `app/api/v1/`，只做参数校验、鉴权注入与统一响应封装，**不写业务逻辑、不直接访问数据库** |
| 应用层 | Service 类，位于 `app/services/`，承载业务规则与事务边界 |
| 数据层 | Repository 类，位于 `app/repositories/`，继承 T1 的 `BaseRepository`，基于 SQLAlchemy 2.0 访问数据库 |
| 实体层 | ORM 模型 `app/models/`；出入参模型 `app/schemas/`（Pydantic v2，分 Create / Update / Out 三类） |
| 鉴权 | 由 T2 提供 `Depends(get_current_user)` 与 `require_role(...)`，替代 Java 方案的 ThreadLocal 上下文 |
| 统一响应 | 全部接口返回 T3 的 `ApiResponse[T]`（`code` / `message` / `data`） |
| 阈值来源 | 一律经 T5 读取 `sys_config` 表并走缓存，代码中不出现硬编码阈值 |
| 接口性质 | 对外接口（HTTP，供前端调用）与模块间内部调用接口分开列出，见 5.2 节 |
""")
    fig_no = 0
    tbl_no = 3
    figs, tbls = [], []
    for i, m in enumerate(MODULES, 1):
        out.append("### 3.%d %s模块（%s %s）\n" % (i, m["cn"], m["code"], m["en"]))
        out.append("本模块职责：%s。对应数据表：%s。\n" % (
            m["duty"], "、".join("`%s`" % t for t in m["tables"])))

        # 3.x.1 功能定义
        tbl_no += 1
        out.append("#### 3.%d.1 %s模块功能定义\n" % (i, m["cn"]))
        out.append("表 3-%d　%s模块功能定义\n" % (tbl_no, m["cn"]))
        tbls.append("表 3-%d　%s模块功能定义" % (tbl_no, m["cn"]))
        out.append("| 序号 | 功能点 | 功能点详细说明 | 需求编号 |")
        out.append("|---|---|---|---|")
        for j, (fp, desc, fr) in enumerate(m["features"], 1):
            out.append("| %d | %s | %s | %s |" % (j, fp, desc, fr))
        out.append("")

        # 3.x.2 模块结构
        fig_no += 1
        out.append("#### 3.%d.2 %s模块结构\n" % (i, m["cn"]))
        out.append("模块结构如图 3-%d 所示：接口层接收请求并完成鉴权与参数校验，"
                   "应用层实现本模块的业务规则，数据层负责表访问；虚线框为横切依赖与上游触发来源。\n" % fig_no)
        fname = "图3-%d_%s%s_模块结构图.png" % (fig_no, m["code"], slug(m["cn"]))
        out.append(figure(fname, "图 3-%d　%s模块结构图" % (fig_no, m["cn"])))
        figs.append("图 3-%d　%s模块结构图" % (fig_no, m["cn"]))

        # 3.x.3 类图 + 接口说明
        fig_no += 1
        out.append("#### 3.%d.3 %s模块类图与接口说明\n" % (i, m["cn"]))
        out.append("类图如图 3-%d 所示。类名与职责对应后文第 5 章的接口函数定义。\n" % fig_no)
        fname = "图3-%d_%s%s_类图.png" % (fig_no, m["code"], slug(m["cn"]))
        out.append(figure(fname, "图 3-%d　%s模块类图" % (fig_no, m["cn"])))
        figs.append("图 3-%d　%s模块类图" % (fig_no, m["cn"]))
        if m.get("agents"):
            out.append("")
            out.append("四类 Agent 的分工：")
            for a, d in m["agents"]:
                out.append("- `%s`：%s" % (a, d))
            out.append("")

        tbl_no += 1
        funcs = [f for f in FUNCS if f["m"] == m["code"]]
        out.append("表 3-%d　%s模块接口说明\n" % (tbl_no, m["cn"]))
        tbls.append("表 3-%d　%s模块接口说明" % (tbl_no, m["cn"]))
        out.append("| 序号 | 模块名称 | 接口函数 | 函数说明 |")
        out.append("|---|---|---|---|")
        for j, f in enumerate(funcs, 1):
            out.append("| %d | %s | `%s` | %s |" % (j, m["cn"], f["name"], f["summary"]))
        out.append("")

    # ---------- 3.10 ~ 3.12 技术模块（B 档出四件套）----------
    detail = [t for t in TECH_MODULES if "classes" in t]
    out.append("### 3.10 技术模块详细说明\n")
    out.append("技术模块不出现在接口层的 HTTP 端点里，它们的能力由业务模块在服务层直接调用。"
               "因此下列各节的接口说明表列出的是**供其他模块调用的函数**（按指导老师口径即「外部接口」），"
               "各模块内部不对外公开的私有方法属「内部接口」，已在类图中以 `_` 前缀体现，不逐个列出。\n")
    for i, t in enumerate(detail, len(MODULES) + 2):
        out.append("### 3.%d %s模块（%s %s，技术模块）\n" % (i, t["cn"], t["code"], t["en"]))
        out.append("本模块职责：%s。被谁共用：%s。对应数据对象：%s。\n" % (
            t["duty"], t["shared_by"], "、".join("`%s`" % x for x in t["tables"])))

        tbl_no += 1
        out.append("#### 3.%d.1 %s模块功能定义\n" % (i, t["cn"]))
        out.append("表 3-%d　%s模块功能定义\n" % (tbl_no, t["cn"]))
        tbls.append("表 3-%d　%s模块功能定义" % (tbl_no, t["cn"]))
        out.append("| 序号 | 功能点 | 功能点详细说明 | 需求编号 |")
        out.append("|---|---|---|---|")
        for j, (fp, desc, fr) in enumerate(t["features"], 1):
            out.append("| %d | %s | %s | %s |" % (j, fp, desc, fr))
        out.append("")

        fig_no += 1
        out.append("#### 3.%d.2 %s模块结构\n" % (i, t["cn"]))
        out.append("模块结构如图 3-%d 所示：本模块不暴露 HTTP 端点，"
                   "以中间件或依赖注入的形式被业务模块引用。\n" % fig_no)
        fname = "图3-%d_%s%s_模块结构图.png" % (fig_no, t["code"], slug(t["cn"]))
        out.append(figure(fname, "图 3-%d　%s模块结构图" % (fig_no, t["cn"])))
        figs.append("图 3-%d　%s模块结构图" % (fig_no, t["cn"]))

        fig_no += 1
        out.append("#### 3.%d.3 %s模块类图与接口说明\n" % (i, t["cn"]))
        out.append("类图如图 3-%d 所示。\n" % fig_no)
        fname = "图3-%d_%s%s_类图.png" % (fig_no, t["code"], slug(t["cn"]))
        out.append(figure(fname, "图 3-%d　%s模块类图" % (fig_no, t["cn"])))
        figs.append("图 3-%d　%s模块类图" % (fig_no, t["cn"]))

        tbl_no += 1
        out.append("表 3-%d　%s模块对外提供的函数\n" % (tbl_no, t["cn"]))
        tbls.append("表 3-%d　%s模块对外提供的函数" % (tbl_no, t["cn"]))
        out.append("| 序号 | 模块名称 | 调用函数 | 函数说明 |")
        out.append("|---|---|---|---|")
        for j, (fname, fdesc) in enumerate(t["public_funcs"], 1):
            out.append("| %d | %s | `%s` | %s |" % (j, t["cn"], fname, fdesc))
        out.append("")

    return "\n".join(out), figs, tbls


# ---------------------------------------------------------------- 4 数据库设计
CH4 = """## 4 数据库设计

### 4.1 数据库引擎概述

| 项 | 选型与配置 |
|---|---|
| 数据库 | MySQL 8.0 |
| 存储引擎 | InnoDB（支持事务、行级锁与外键） |
| 字符集 / 排序规则 | `utf8mb4` / `utf8mb4_general_ci`（支持完整中文与特殊符号） |
| 事务隔离级别 | REPEATABLE READ（MySQL 默认；预警生成与处理走显式事务保证一致性） |
| 主键策略 | `BIGINT AUTO_INCREMENT` 代理主键，业务编号不参与主键 |
| 时间字段 | `DATETIME`，通用审计字段 `create_time` / `update_time` 全表统一 |
| 连接与池化 | SQLAlchemy 2.0 连接池，慢查询阈值由 `sys_config` 下发 |
| 备份策略 | 交付演示环境为单实例，采用"每日全量 `mysqldump` + 关键表脚本化重建"；正式部署建议追加 binlog 增量备份，RPO ≤ 5 分钟 |
| 高可用 | **本期为单机单实例**，不做读写分离与主从切换；正式部署规划为一主一从、从库承担报表读，切换目标 30 秒内 |

> 说明：备份与高可用部分按实际情况描述，未实现的能力明确标注为"规划"，不做虚假陈述。

### 4.2 数据库概要设计

#### 4.2.1 数据库表清单

本系统共设计 **15 张表 = 核心表 11 张 + 选配表 4 张**，覆盖用户与角色、健康档案、指标与预警、家属绑定、护工分配、AI 咨询与知识库等实体。表清单如下。

表 4-1　数据库表清单
"""


def ch4_tables():
    """从 schema.sql 解析表名与中文注释，保证与建表脚本一致"""
    txt = open(SCHEMA, encoding="utf-8").read()
    rows = []
    for m in re.finditer(r"CREATE TABLE `(\w+)` \((.*?)ENGINE=InnoDB", txt, re.S):
        name, body = m.group(1), m.group(2)
        cm = re.search(r"COMMENT='([^']+)'\s*;?\s*$", body.strip())
        comment = cm.group(1) if cm else ""
        opt = "选配" if "选配" in comment else "核心"
        rows.append((name, comment.replace("【选配】", ""), opt))
    return rows


def ch4():
    rows = ch4_tables()
    core = [r for r in rows if r[2] == "核心"]
    opt = [r for r in rows if r[2] == "选配"]

    LAYER = {
        "user": "基础表", "elder_profile": "基础表", "family_bind": "基础表",
        "care_relation": "基础表", "sys_config": "配置表",
        "health_record": "业务表", "health_warning": "业务表",
        "alert_receiver": "业务表", "warning_handle_record": "业务表",
        "chat_session": "业务表", "chat_message": "业务表",
        "medication": "选配表", "knowledge_document": "选配表",
        "knowledge_chunk": "选配表", "ai_log": "选配表",
    }
    SCALE = {
        "user": "小", "elder_profile": "小", "family_bind": "小", "care_relation": "小",
        "sys_config": "极小", "health_record": "大（增长最快）", "health_warning": "中",
        "alert_receiver": "中", "warning_handle_record": "小", "chat_session": "小",
        "chat_message": "中", "medication": "小", "knowledge_document": "小",
        "knowledge_chunk": "中", "ai_log": "中",
    }
    out = [CH4]
    out.append("| 序号 | 表名 | 用途 | 分层 | 分层依据 | 预估规模 |")
    out.append("|---|---|---|---|---|---|")
    for i, (n, c, k) in enumerate(rows, 1):
        lay = LAYER.get(n, "业务表")
        why = {"基础表": "主体与关系，被业务表引用",
               "配置表": "系统级参数，全局唯一来源",
               "业务表": "随业务过程产生，随主体增长",
               "选配表": "【选配】本期不实现"}[lay]
        out.append("| %d | `%s` | %s | %s | %s | %s |" % (
            i, n, c, ("%s%s" % (lay, "【选配】" if k == "选配" else "")), why, SCALE.get(n, "小")))
    out.append("")

    out.append("""#### 4.2.2 基础表与业务表的划分

按照"**先确定基础表，再确定业务表**"的原则，15 张表分为四层，建表顺序与依赖方向一致：

| 层次 | 表 | 说明 |
|---|---|---|
| 基础表（4） | `user`、`elder_profile`、`family_bind`、`care_relation` | 描述"人"与"人与人的关系"，不随业务过程增长，被上层表通过外键引用 |
| 配置表（1） | `sys_config` | 系统级参数与健康阈值，全局唯一来源，**阈值不写死在代码里** |
| 业务表（6） | `health_record`、`health_warning`、`alert_receiver`、`warning_handle_record`、`chat_session`、`chat_message` | 随业务过程产生，数据量随基础表规模增长，是系统的主要写入对象 |
| 选配表（4） | `medication`、`knowledge_document`、`knowledge_chunk`、`ai_log` | 标注【选配】，本期不实现，表结构先行设计以保证扩展性 |

**主表与从表的划分**：以"被引用者为主表、引用者为从表"判定。例如 `elder_profile` 为主表，`health_record`、`health_warning`、`family_bind`、`care_relation` 均为其从表；`health_warning` 为主表，`alert_receiver` 与 `warning_handle_record` 为其从表。全部主外键关系共 **12 个**，均在建表语句之后以 `ALTER TABLE` 统一补充，避免建表时的依赖顺序问题。

#### 4.2.3 实体关系要点

- `user` 与 `elder_profile` 为 **1 : N**（一个账号可管理本人及代管的多份档案）；
- `user`（家属）与 `elder_profile`（老人）通过 `family_bind` 形成 **M : N**，绑定本身带状态机：`PENDING → APPROVED → REVOKED`；
- `user`（护工）与 `elder_profile`（老人）通过 `care_relation` 形成 **M : N**，`status` 区分在管与已交接；
- `elder_profile` 与 `health_record` 为 **1 : N**，指标通过 `type` 字段在同一张表内区分五类，避免五张同构表；
- `health_record` 与 `health_warning` 为 **1 : 0..1**（异常记录触发预警，正常记录不触发）；
- `health_warning` 与 `user` 通过 `alert_receiver` 形成 **M : N**，每人一条记录、各自持有独立的 `read_status`，这是"处理状态与已读状态分离"（决策 D-05）的落地方式；
- `health_warning` 与 `warning_handle_record` 为 **1 : N**，记录每一次处理动作以形成留痕；
- `chat_session` 与 `chat_message` 为 **1 : N**；消息上冗余保存 `intent`、`agent`、`safety_level` 与 `sources`，用于还原一次多 Agent 编排的完整决策过程。

#### 4.2.4 三范式与反规范化说明

**总体结论：本设计满足第三范式。** 各表均已满足第一范式（字段原子性）、第二范式（非主属性完全依赖主键，本系统统一使用 `BIGINT` 代理主键，不存在部分依赖）、第三范式（非主属性不传递依赖于主键）。

出于工程原因，存在三处**有意的反规范化**，均不影响上述结论，现逐条说明：

| 序号 | 位置 | 做法 | 理由 |
|---|---|---|---|
| 1 | `elder_profile.chronic_tags` | 以 JSON 数组文本存储慢病标签，未拆独立子表 | 慢病标签为低频变更、低基数（每档案通常 1~3 个）、且不参与关联查询与统计；拆表会引入一次额外的连接，收益小于成本。若后续需要按标签做人群统计，再迁移为 `elder_chronic_tag` 子表 |
| 2 | `chat_message.intent` / `agent` / `safety_level` / `sources` | 将一次编排的判定结果随消息落库 | 这些字段是**历史事实的快照**而非可推导的派生值：知识库与意图模型都会更新，事后重算无法还原当时的判定结果 |
| 3 | `health_warning.value_text` | 冗余保存触发时的展示值（如 `178/102`） | 触发记录可能被删除（`health_record` 允许删除），若不冗余则预警将失去触发依据；此为审计需求而非查询优化 |

> 上述反规范化均在文档与建表脚本注释中显式标注，避免后续维护者误判为设计疏漏。

#### 4.2.5 索引与约束策略

| 类别 | 内容 |
|---|---|
| 主键索引 | 全部 15 张表均使用 `BIGINT AUTO_INCREMENT` 代理主键 |
| 唯一约束 | `user.phone`（登录名唯一）、`sys_config.config_key`（配置键唯一）、`alert_receiver(warning_id, user_id)`（同一预警对同一人仅一条接收记录） |
| 高频查询索引 | `health_record(profile_id, type, measured_at)` 支撑趋势查询；`health_warning(profile_id, status)` 支撑预警列表；`alert_receiver(user_id, read_status)` 支撑未读数统计；`family_bind` 与 `care_relation` 按关系双方各建索引 |
| 时间索引 | `health_record.measured_at`、`health_warning.create_time`，支撑按周期统计 |
| 外键约束 | 12 个，统一在 `ALTER TABLE` 阶段补充；删除规则按语义选择：档案删除级联清理指标（`CASCADE`），录入人删除置空（`SET NULL`），处理人存在则禁止删除（`RESTRICT`） |
| 一致性兜底 | "同一对家属—老人不得存在两条 PENDING / APPROVED 记录"因 MySQL 无部分唯一索引，改由应用层校验实现，已在脚本注释中注明 |

#### 4.2.6 表间关系图

核心表（11 张）之间的实体关系如图 4-1 所示；【选配】表（4 张）的扩展关系如图 4-2 所示。

""")
    return "\n".join(out)


def ch4_tail():
    return """
#### 4.2.7 数据字典

逐表数据字典以 Excel 形式单独交付，文件为 `04.编码/数据库/数据字典_康养系统_v1.0.xlsx`，**每张表一个工作表（共 15 个）**，列结构与指导老师下发的样例一致：

| 列 | 含义 |
|---|---|
| 类型 / 大小 | MySQL 字段类型与长度 |
| 名称 | 字段名 |
| 非空 | Y 表示 NOT NULL |
| 默认值 | 建表语句中的默认值 |
| 补充 / 描述 | 字段中文含义与补充说明 |
| 扩展 | 前端表单控件类型 |
| 左 / 右 | 外键关系：左表（子表）字段 ← 右表（父表）字段 |
| List显示 | 是否在列表页展示 |
| 特殊取值描述 | 枚举字段的取值含义 |
| 追加日期 / 追加原因 | 需求追加时的留痕列，本期无追加 |

> 数据字典由 `schema.sql` 解析生成，**与建表脚本同源**，任何字段改动只需改脚本并重新生成，避免文档与代码不一致。
"""


# ---------------------------------------------------------------- 5 接口设计
CH5_HEAD = """## 5 接口设计

### 5.1 全局变量

#### 5.1.1 状态与枚举常量

本系统的状态取值集中定义在 `app/core/constants.py`（`IntEnum` / `StrEnum`），供接口层、服务层与数据库共用，**不允许在业务代码中散落字面量**。

表 5-1　全局状态与枚举常量
"""

CH5_ENUMS = """| 枚举 | 取值 | 含义 | 主要使用位置 |
|---|---|---|---|
| 角色 `Role` | `ELDER` / `FAMILY` / `CARE` / `ADMIN` | 老年用户 / 家属 / 护工 / 管理员 | `user.role`、鉴权、数据范围计算 |
| 账号状态 | `1` / `0` | 启用 / 禁用（禁用后 Token 立即失效） | `user.status` |
| 家属绑定状态 `BindStatus` | `PENDING` / `APPROVED` / `REJECTED` / `REVOKED` | 待确认 / 已生效 / 已拒绝 / 已解绑 | `family_bind.status` |
| 护工分配状态 | `1` / `0` | 在管 / 已交接 | `care_relation.status` |
| 指标类型 `IndicatorType` | `BLOOD_PRESSURE` / `BLOOD_SUGAR` / `HEART_RATE` / `SLEEP` / `STEP` | 血压 / 血糖 / 心率 / 睡眠 / 步数 | `health_record.type` |
| 预警处理状态 `WarningStatus` | `PENDING` / `PROCESSING` / `RESOLVED` / `IGNORED` | 待处理 / 处理中 / 已处理 / 已忽略（全局唯一） | `health_warning.status` |
| 接收人已读状态 `ReadStatus` | `UNREAD` / `READ` | 未读 / 已读（每人独立） | `alert_receiver.read_status` |
| AI 摘要状态 `SummaryStatus` | `PENDING` / `SUCCESS` / `FAILED` / `SKIPPED` | 生成中 / 成功 / 失败 / 低级别不生成 | `health_warning.summary_status` |
| 风险等级 `RiskLevel` | `0` / `1` / `2` / `3` | 正常 / 轻度 / 较高 / 高风险 | 预警判定与展示 |
| 咨询意图 `Intent` | `NORMAL` / `DATA` / `ABNORMAL` / `EMERGENCY` | 普通咨询 / 数据类 / 异常 / 紧急 | 咨询请求路由 |
| 执行 Agent `AgentType` | `HEALTH` / `HEALTH_DATA` / `RISK` / `EMERGENCY` | 四类智能体 | 咨询编排与消息留痕 |
| 安全分级 `SafetyLevel` | `L1` / `L2` / `L3` / `L4` | 安全等级，L3 以上必须附带就医引导 | 回答安全兜底 |
| 处理方式 `HandleAction` | `CONTACTED` / `ARRANGED_VISIT` / `SENT_HOSPITAL` / `OBSERVE` | 已联系 / 安排上门 / 送医 / 继续观察 | 预警处理留痕 |
| 触发来源 `TriggerSource` | `DATA_INPUT` / `AI_CHAT` / `MANUAL` | 指标录入触发 / 咨询识别触发 / 人工创建 | `health_warning.trigger_source` |
| 护工端老人状态 `ElderStatus` | `NORMAL` / `WATCH` / `ABNORMAL` | 正常 / 关注 / 异常 | 护工工作台分色标识 |
| 错误码 `ErrorCode` | `0` / `1001`~`1003` / `2001`~`2002` / `3001`~`3002` / `4001`~`4004` / `5001` | 成功 / 鉴权类 / 参数类 / AI 类 / 业务类 / 系统类 | 统一响应 `code`，详见契约 1.4 节 |

> 错误码 `3001`（AI 服务异常）出现时，健康数据录入、预警生成与预警处理等主流程必须仍然可用，前端不得因此阻断用户操作（决策 D-04）。
"""

CH5_MID = """
#### 5.1.2 全局配置项

固定不变的运行参数通过 `.env` 与 `app/core/config.py`（pydantic-settings）管理，**API Key 只存在于后端 `.env`，绝不进入前端代码**。

表 5-2　全局配置项

| 配置项 | 取值 / 默认值 | 说明 |
|---|---|---|
| `LLM_PROVIDER` | `deepseek` / `qwen` / `glm` | 大模型选型开关，**换模型只改此配置，不改代码** |
| `LLM_API_KEY` | 后端 `.env` 注入 | 模型密钥，禁止写入前端与代码仓库 |
| `JWT_SECRET` | 后端 `.env` 注入 | JWT 签名密钥 |
| `JWT_TTL` | 86400（秒） | Token 有效期，与登录响应的 `expires_in` 一致 |
| `DB_URL` | `mysql+pymysql://...` | 数据库连接串 |
| `VECTOR_STORE` | `chroma` / `faiss` | 向量库实现选择 |
| `AI_TIMEOUT_SECONDS` | 8 | 模型调用超时阈值，超时即降级，不阻塞业务主流程 |

#### 5.1.3 配置化声明（重要）

**本系统不存在硬编码的健康阈值。** 预警阈值（各指标的四档区间）与业务参数（家属绑定上限 `family_bind_max`、登录失败限次等）全部存放于 `sys_config` 表，由 M8 后台管理模块维护、M3 指标模块与 M5 预警模块实时读取，前端通过 M9 系统配置模块获取展示用的正常范围。

这样设计的目的是：调整阈值无需改代码、无需重启，保存后即时生效（对应需求 `FR-ADMIN-009` 与 `FR-ADMIN-010`）。
"""

CH5_53 = """### 5.3 关键数据结构定义

本节列出贯穿各模块的公共数据结构，具体出入参模型在 5.2 各函数的参数与返回值中引用。实现上使用 Pydantic v2 模型，对应 Java 方案中的 DTO / VO / 统一响应类。

#### 5.3.1 统一响应结构

```python
class ApiResponse(BaseModel, Generic[T]):
    code: int = 0            # 0 成功；错误码见《API 接口契约 v0.2》1.4 节
    message: str = "success" # 提示信息，失败时为具体原因
    data: T | None = None    # 业务数据，失败时为 None
```

#### 5.3.2 分页结构

```python
class PageResult(BaseModel, Generic[T]):
    list: list[T]      # 当前页数据
    total: int         # 记录总数
    page: int          # 当前页码，从 1 开始
    page_size: int     # 每页条数，默认 20，上限 100
```

#### 5.3.3 核心入参模型

```python
class RegisterIn(BaseModel):          # 注册
    phone: str
    password: str
    name: str
    role: Literal["ELDER", "FAMILY"] = "ELDER"

class LoginIn(BaseModel):             # 登录
    phone: str
    password: str

class ProfileIn(BaseModel):           # 健康档案
    name: str
    gender: Literal["M", "F"] | None = None
    birthday: date | None = None
    height: float | None = None
    weight: float | None = None
    blood_type: str | None = None
    allergy: str | None = None
    medical_history: str | None = None
    chronic_tags: list[str] = []
    emergency_contact: str | None = None
    emergency_phone: str | None = None

class RecordIn(BaseModel):            # 指标录入（判别联合，按 type 校验 values 结构）
    profile_id: int
    type: Literal["BLOOD_PRESSURE", "BLOOD_SUGAR", "HEART_RATE", "SLEEP", "STEP"]
    values: dict[str, float]
    measured_at: datetime
    remark: str | None = None

class ChatIn(BaseModel):              # 发起咨询
    profile_id: int
    question: str
    session_id: int | None = None

class HandleIn(BaseModel):            # 预警处理
    result: str
    action: Literal["CONTACTED", "ARRANGED_VISIT", "SENT_HOSPITAL", "OBSERVE"]

class BindIn(BaseModel):              # 家属绑定申请
    phone: str
    relation: str | None = None
    note: str | None = None
```

#### 5.3.4 核心出参模型

```python
class UserOut(BaseModel):             # 用户信息（不含密码）
    user_id: int
    phone: str
    name: str
    role: str
    avatar: str | None = None

class LoginOut(BaseModel):            # 登录结果
    token: str
    expires_in: int
    user: UserOut

class RecordOut(BaseModel):           # 指标录入结果
    record_id: int
    is_abnormal: bool
    risk_level: int
    warning_id: int | None = None

class TrendOut(BaseModel):            # 趋势数据（供 ECharts）
    dates: list[str]
    series: list[dict]
    normal_range: dict                # 来自 sys_config，前端不写死
    abnormal_points: list[dict]

class ChatOut(BaseModel):             # 咨询结果
    session_id: int
    message_id: int
    answer: str
    intent: str                       # NORMAL / DATA / ABNORMAL / EMERGENCY
    agent: str                        # HEALTH / HEALTH_DATA / RISK / EMERGENCY
    safety_level: str                 # L1~L4
    risk_level: int | None = None
    sources: list[str] = []           # RAG 命中来源
    warning_id: int | None = None
    disclaimer: str                   # 固定免责声明

class AlertOut(BaseModel):            # 预警列表项
    warning_id: int
    profile_id: int
    elder_name: str
    type: str
    value_text: str
    level: int
    level_text: str
    ai_summary: str | None = None     # 异步生成，允许为空（D-04）
    summary_status: str               # PENDING / SUCCESS / FAILED / SKIPPED
    status: str                       # 处理状态（全局唯一）
    my_read_status: str               # 当前用户已读状态
    trigger_source: str | None = None
    created_at: datetime
    handler_name: str | None = None
    handle_result: str | None = None

class ThresholdOut(BaseModel):        # 阈值配置
    config_id: int
    indicator: str
    indicator_name: str
    unit: str
    level0_range: str
    level1_range: str
    level2_range: str
    level3_range: str
    enabled: bool
```
"""


def ch5_funcs():
    """5.2 模块间接口函数设计：45 个对外接口 + 8 个模块间调用接口"""
    out = ["### 5.2 模块间接口函数设计\n",
           "本节按模块列出**全部 45 个对外接口函数**的详细信息，编号与《API 接口契约 v0.2》一一对应。\n",
           "按指导老师对接口的两分口径，本系统的接口分三类，本章分别处理：\n",
           "| 类别 | 定义 | 数量 | 本章位置 |",
           "|---|---|---|---|",
           "| 对外接口 | 面向系统外部（前端与其他端）提供的 HTTP 端点 | 45 | 5.2.1 ~ 5.2.9 |",
           "| 模块间调用接口 | 一个模块在进程内调用另一模块的函数；相对调用方模块而言亦属对外公开 | 8 | 5.2.10 |",
           "| 内部接口 | 模块或类内部使用、不对外暴露的私有方法（Python 以 `_` 前缀命名） | — | 不逐个列出，见各模块类图 |",
           "",
           "函数表格式遵循模板要求：**函数名、文件名、功能概要、参数、返回值、详细说明、使用注意事项**；"
           "并额外增加「接口性质」一项以体现上述分类。\n"]
    n = 0
    for i, m in enumerate(MODULES, 1):
        funcs = [f for f in FUNCS if f["m"] == m["code"]]
        out.append("#### 5.2.%d %s模块（%s %s，%d 个函数）\n" % (
            i, m["cn"], m["code"], m["en"], len(funcs)))
        for f in funcs:
            n += 1
            nature = NATURE_OVERRIDE.get((f["m"], f["name"]), NATURE_DEFAULT)
            out.append("**函数 %d／45　`%s`**　（%s）\n" % (n, f["name"], f["api"]))
            out.append("| 项 | 内容 |")
            out.append("|---|---|")
            out.append("| 函数名 | `%s` |" % f["name"])
            out.append("| 文件名 | `%s` |" % f["file"])
            out.append("| 接口性质 | %s |" % nature)
            out.append("| 功能概要 | %s |" % f["summary"])
            out.append("| 参数 | 见下表 |")
            out.append("| 返回值 | 类型 `%s`；%s |" % (f["ret"][0], f["ret"][1]))
            out.append("| 详细说明 | %s |" % f["detail"])
            out.append("| 使用注意事项 | %s |" % f["note"])
            out.append("")
            out.append("| 参数类型 | 变量名 | I/O | 说明 |")
            out.append("|---|---|---|---|")
            for t, v, io, d in f["params"]:
                out.append("| `%s` | `%s` | %s | %s |" % (t, v, io, d))
            out.append("")

    # ---------- 5.2.10 模块间调用接口 ----------
    out.append("#### 5.2.10 模块间调用接口（进程内，供其他模块调用）\n")
    out.append("下列 **8 个函数**是一个模块调用另一个模块时使用的入口。它们**不经过 HTTP**，"
               "由服务层直接调用，因此在数据隔离、阈值来源与错误码上与对外接口共用同一套实现，"
               "避免出现「网页上是一个口径、模块间调用却是另一个口径」的不一致。\n")
    for k, f in enumerate(INTERNAL_FUNCS, 1):
        out.append("**模块间函数 %d／8　`%s`**　（提供方：%s）\n" % (k, f["name"], f["m"]))
        out.append("| 项 | 内容 |")
        out.append("|---|---|")
        out.append("| 函数名 | `%s` |" % f["name"])
        out.append("| 文件名 | `%s` |" % f["file"])
        out.append("| 接口性质 | %s |" % f["api"])
        out.append("| 调用方 | %s |" % f["caller"])
        out.append("| 功能概要 | %s |" % f["summary"])
        out.append("| 参数 | 见下表 |")
        out.append("| 返回值 | 类型 `%s`；%s |" % (f["ret"][0], f["ret"][1]))
        out.append("| 详细说明 | %s |" % f["detail"])
        out.append("| 使用注意事项 | %s |" % f["note"])
        out.append("")
        out.append("| 参数类型 | 变量名 | I/O | 说明 |")
        out.append("|---|---|---|---|")
        for t, v, io, d in f["params"]:
            out.append("| `%s` | `%s` | %s | %s |" % (t, v, io, d))
        out.append("")
    return "\n".join(out), n


def copy_er():
    """把已有的 E-R 图纳入图_v2，统一由本目录管理"""
    import shutil
    for src, dst in (("ER图_核心.png", "图4-1_表间关系图_核心.png"),
                     ("ER图_选配.png", "图4-2_表间关系图_选配.png")):
        s = os.path.join(BASE, "图", src)
        d = os.path.join(BASE, FIGDIR, dst)
        if os.path.exists(s):
            shutil.copyfile(s, d)


def main():
    copy_er()
    parts = [COVER, CH1, CH2_HEAD]
    parts.append(figure("图2-1_模块分解图.png", "图 2-1　模块分解图（业务层 / 技术层）"))
    parts.append(figure("图2-2_分层架构图.png", "图 2-2　系统分层架构与横切机制"))
    parts.append(CH2_TAIL)
    figs = ["图 2-1　模块分解图（业务层 / 技术层）", "图 2-2　系统分层架构与横切机制"]

    ch3_txt, ch3_figs, ch3_tbls = ch3()
    parts.append(ch3_txt)
    figs += ch3_figs

    parts.append(ch4())
    parts.append(figure("图4-1_表间关系图_核心.png", "图 4-1　核心表实体关系图（11 张）"))
    parts.append(figure("图4-2_表间关系图_选配.png", "图 4-2　选配表实体关系图（4 张，本期不实现）"))
    figs += ["图 4-1　核心表实体关系图（11 张）", "图 4-2　选配表实体关系图（4 张）"]
    parts.append(ch4_tail())

    parts.append(CH5_HEAD)
    parts.append(CH5_ENUMS)
    parts.append(CH5_MID)
    funcs_txt, nfun = ch5_funcs()
    parts.append(funcs_txt)
    parts.append(CH5_53)

    # 附录：图表索引
    parts.append("## 附录 A　图表索引\n")
    parts.append("**图索引**\n")
    parts.append("| 编号 | 图题 |")
    parts.append("|---|---|")
    for f in figs:
        no, t = f.split("　", 1)
        parts.append("| %s | %s |" % (no, t))
    parts.append("")
    parts.append("**表索引**\n")
    parts.append("表 1-1　术语与缩略语 · 表 1-2　参考文档")
    parts.append("")
    parts.append("| 编号 | 表题 |")
    parts.append("|---|---|")
    for t in ch3_tbls:
        no, tt = t.split("　", 1)
        parts.append("| %s | %s |" % (no, tt))
    parts.append("| 表 4-1 | 数据库表清单 |")
    parts.append("| 表 5-1 | 全局状态与枚举常量 |")
    parts.append("| 表 5-2 | 全局配置项 |")
    parts.append("")
    parts.append("> 5.2 节另含 **45 张对外接口函数表** 与 **8 张模块间调用接口表**（每个函数一张，"
                 "格式统一为函数名 / 文件名 / 接口性质 / 功能概要 / 参数 / 返回值 / 详细说明 / 使用注意事项），"
                 "因数量较多未逐条列入上表。")
    parts.append("")
    parts.append("---\n")
    parts.append("> 本文档由 `03.概要设计/_gen/build_md.py` 生成，正文内容与配图、数据字典同源，"
                 "修改请改生成器后重新生成，不要直接编辑本文件。\n")

    txt = "\n".join(parts)
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(txt)
    print("已生成 %s" % OUT_MD)
    print("字数 %d，图 %d 张，表 %d 张，接口函数 %d 个" % (
        len(txt), len(figs), len(ch3_tbls) + 1, nfun))


if __name__ == "__main__":
    main()
