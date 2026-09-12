# 数据库 · 设计说明

归属：**丘宇乾**（主，编写建表脚本）· **周彦龙**（审，评审表结构与索引）

> 表结构以 `03.概要设计/概要设计说明书_康养系统_v1.0.md` 第 4 章为唯一事实来源（Single Source of Truth）。
> 本文件如有出入，以概要设计说明书为准，并同步修订本文件。

---

## 环境

| 项 | 值 |
|---|---|
| 数据库 | MySQL 8.0 |
| 字符集 | utf8mb4 |
| 排序规则 | utf8mb4_general_ci |

---

## 表清单（15 张：核心 11 + 选配 4）

| 表名 | 用途 | 备注 |
|---|---|---|
| user | 用户主表（四类角色） | 核心 |
| elder_profile | 老人健康档案 | 核心 |
| family_bind | 家属与老人绑定关系（含申请确认状态机） | 核心 |
| care_relation | 护工与老人分配关系 | 核心 |
| health_record | 健康指标统一表（type 区分） | 核心 |
| health_warning | 预警记录（处理状态 + AI 摘要） | 核心 |
| alert_receiver | 预警接收人（每人一条，独立已读状态） | 核心 |
| warning_handle_record | 预警处理留痕 | 核心 |
| chat_session | 咨询会话 | 核心 |
| chat_message | 咨询消息 | 核心 |
| sys_config | 阈值与系统配置 | 核心，**配置化关键表** |
| medication | 用药信息 | 【选配】 |
| knowledge_document | 知识库文档 | 【选配】 |
| knowledge_chunk | 知识库分块向量 | 【选配】 |
| ai_log | AI 调用日志 | 【选配】 |

> `alert_receiver` 关键字段：`warning_id`、`user_id`、`read_status`、`read_time`。

---

## 设计约定

1. **配置入表**：预警阈值、指标范围、角色权限等一律存 `sys_config`，**代码中不得硬编码**——这是设计评审加分项
2. **统一指标表**：血压 / 血糖 / 心率 / 睡眠 / 步数共用 `health_record`，以 `type` 字段区分，避免建 5 张结构相似的表
3. **软删除**：档案等核心数据用 `deleted` 标记，不做物理删除
4. **时间字段**：统一 `create_time` / `update_time`，由数据库自动维护
5. **密码存储**：bcrypt 加密，禁止明文
6. **权限隔离落地**：家属只能查已绑定老人、护工只能查分配老人——查询条件在 SQL 层强制带关系表过滤，不依赖前端传参
7. **处理状态与已读状态分离**（D-05）：预警处理状态在 `health_warning.status`，每人已读状态在 `alert_receiver.read_status`，**严禁合并为一个字段**——否则会出现"家属 A 看过 → 家属 B 也显示已读"的缺陷

---

## 交付物

| 文件 | 说明 | 状态 |
|---|---|---|
| `schema.sql` | 建表脚本（15 张表 + 索引 + 外键） | 已完成 |
| `init_data.sql` | 初始化数据（预置管理员、阈值配置、指标配置、示例数据） | 已完成 |
| E-R 图 | 随概要设计文档提交评审 | 已完成（`03.概要设计/图/`） |

---

## 命名规范

- 表名：小写字母 + 下划线，单数形式
- 字段名：小写字母 + 下划线
- 主键：统一 `id`（BIGINT 自增）
- 外键字段：`xxx_id`
- 状态字段：用语义化字符串（如 `PENDING` / `APPROVED` / `REJECTED`）；有限枚举等级（如 `level`）用 TINYINT

> 本节与《概要设计说明书》4.2 节对齐。原"状态字段统一 `status`（TINYINT）"的旧口径已作废（对应概要设计 4.9 节勘误 **E-07**）。

---

## 表名口径（重要）

- 家属绑定表为 **`family_bind`**，**不再使用旧名 `family_relation`**
  （依据《设计决策记录 v1.0》D-02、API 契约 v0.2 §12；旧名残留见概要设计说明书 4.9 节勘误 **E-06**）
- 需求说明书 §6"数据需求概要"中若仍写 `family_relation`，以 `family_bind` 为准


---

## 索引与约束

| 表 | 索引 / 约束 | 用途 |
|---|---|---|
| user | UNIQUE(phone) | 登录名唯一 |
| elder_profile | INDEX(user_id) | 按账号查档案 |
| family_bind | INDEX(family_user_id), INDEX(profile_id) | 绑定查询 |
| care_relation | INDEX(care_user_id), INDEX(profile_id) | 护工范围隔离 |
| health_record | INDEX(profile_id, type, measured_at), INDEX(recorder_id) | 趋势 / 列表查询与录入人关联 |
| health_warning | INDEX(profile_id, status), INDEX(level) | 预警列表与筛选 |
| alert_receiver | UNIQUE(warning_id, user_id), INDEX(user_id, read_status) | 未读数统计 |
| chat_message | INDEX(session_id) | 会话消息拉取 |

> 本节与《概要设计说明书》4.7 节对齐。
