<!-- ============================================================
     基于 AI 智能体的康养系统 · API 接口契约 v0.2
     用途：前后端并行开发的对齐基准；前端据此 mock，后端据此实现
     维护：接口变更必须先改本文档，双方确认后再改代码
     责任人：丘宇乾（后端实现）· 梁霁鸣/周彦龙（前端使用）
     ============================================================ -->

# 基于 AI 智能体的康养系统 · API 接口契约

> 版本：v0.2（依据《设计决策记录 v1.0》修订，随概要设计评审细化）
> 编写日期：2026-09-08
> 用途：前后端并行开发对齐基准
> 配套文档：`03.概要设计/设计决策记录_康养系统_v1.0.md`（D-01~D-06 的设计依据）

---

## 0. 文档信息

| 项 | 内容 |
|---|---|
| 文档版本 | v0.2（待评审） |
| 编写日期 | 2026-09-08 |
| 上游文档 | 需求分析说明书 v1.0（125 条 FR：核心 101 + 选配 24）、设计决策记录 v1.0 |
| 接口总数 | 45 个（其中 1 个标注【选配】本期不实现） |
| 本次变更 | 见下方 v0.2 变更清单 |

### v0.2 变更清单（2026-09-08）

| 编号 | 变更 | 依据 |
|---|---|---|
| C-01 | 注册接口角色白名单收紧为 `ELDER` / `FAMILY`，`CARE` / `ADMIN` 拒绝自助注册；新增管理员建号接口 | D-01 |
| C-02 | 家属绑定改为"申请 → 确认 → 生效"三段式，新增待确认列表与确认 / 拒绝接口 | D-02 |
| C-03 | 明确通知范围为站内通知，新增未读数轮询接口；电话号码仅作档案展示 | D-03 |
| C-04 | 预警 `ai_summary` 允许为空，新增 `summary_status` 与摘要重试接口；AI 失败不阻断主流程 | D-04 |
| C-05 | 预警处理状态（四态）与接收人已读状态（二态）拆分为两个字段 / 两张表 | D-05 |
| C-06 | 新增 `alert_receiver` 接收人概念，预警列表返回 `my_read_status` | D-05 |
| C-07 | 修正 `agent` 字段示例值 `RISK_AGENT` → `RISK` | E-04 |
| C-08 | 知识库文档上传接口标注【选配】，本期不实现 | E-03 |

### 变更约定

接口如需调整，**必须先修改本文档并在群内同步**，双方确认后再改代码。
前端不得绕过 `src/api/` 层手写请求；后端不得单方面修改字段名。

---

## 1. 通用约定

### 1.1 基础信息

| 项 | 值 |
|---|---|
| Base URL | `/api` |
| 请求格式 | JSON（`application/json`） |
| 编码 | UTF-8 |
| 日期格式 | `YYYY-MM-DD HH:mm:ss` |

### 1.2 鉴权方式

除注册、登录外，所有接口需在请求头携带 JWT：

```
Authorization: Bearer <token>
```

Token 过期或无效时返回 `code: 1001`，前端收到后跳转登录页并提示"会话已过期"。

### 1.3 统一响应格式

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

分页响应在 `data` 中额外包含：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "list": [],
    "total": 100,
    "page": 1,
    "page_size": 20
  }
}
```

### 1.4 错误码

| code | 含义 | 前端处理 |
|---|---|---|
| 0 | 成功 | 正常渲染 |
| 1001 | 未登录或 Token 失效 | 跳登录页 |
| 1002 | 无权限（越权访问） | 提示无权限并返回上一页 |
| 1003 | 账号已被禁用 | 提示并退出登录 |
| 2001 | 参数校验失败 | 展示 `message` 中的具体错误 |
| 2002 | 资源不存在 | 提示记录不存在 |
| 3001 | AI 服务异常 | 提示"AI 助手暂时不可用，请稍后再试" |
| 3002 | AI 调用超频 | 提示"今日咨询次数已达上限" |
| 4001 | 绑定申请已存在，请勿重复提交 | 提示并展示当前状态 |
| 4002 | 绑定关系已达上限 | 提示"该老人绑定的家属数量已达上限" |
| 4003 | 该角色不允许自助注册 | 提示"护工与管理员账号由管理员创建"（见 D-01） |
| 4004 | 绑定关系未生效 | 提示"请先完成老人确认"（见 D-02） |
| 5001 | 服务器内部错误 | 通用错误提示 |

> 错误码 `3001` 出现时，**健康数据录入、预警生成、预警处理等主流程必须仍然可用**（见 D-04）。前端不得因为该错误码阻断用户操作。

---

## 2. 认证模块（AUTH）

### 2.1 用户注册

```
POST /api/auth/register
```

权限：公开

请求体：

```json
{
  "phone": "13800138000",
  "password": "Abc123456",
  "name": "张桂兰",
  "role": "ELDER"
}
```

**角色白名单（D-01）**：`role` 只能是 `ELDER` 或 `FAMILY`，不传时默认 `ELDER`。
**`CARE` 与 `ADMIN` 不允许自助注册**——传入时后端返回 `code: 4003`，**不做静默降级**。这两类账号由管理员通过 `POST /api/admin/users` 创建，初始管理员由数据库初始化脚本预置。

响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "user_id": 10001,
    "phone": "13800138000",
    "name": "张桂兰",
    "role": "ELDER"
  }
}
```

拒绝示例（传入 `ADMIN`）：

```json
{
  "code": 4003,
  "message": "该角色不允许自助注册，护工与管理员账号由管理员创建",
  "data": null
}
```

### 2.2 用户登录

```
POST /api/auth/login
```

权限：公开

请求体：

```json
{ "phone": "13800138000", "password": "Abc123456" }
```

响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIs...",
    "expires_in": 86400,
    "user": {
      "user_id": 10001,
      "name": "张桂兰",
      "role": "ELDER",
      "avatar": ""
    }
  }
}
```

> 后端按 `role` 决定前端跳转目标页，前端不自行判断角色含义。

### 2.3 退出登录

```
POST /api/auth/logout
```

权限：登录用户。服务端将 Token 加入失效列表。

### 2.4 获取当前用户信息

```
GET /api/auth/me
```

权限：登录用户。返回同 2.2 中的 `user` 结构。

---

## 3. 健康档案（PROFILE）

### 3.1 档案列表

```
GET /api/profiles
```

权限：登录用户。老人返回本人档案，家属返回已绑定老人档案，护工返回负责老人档案，管理员返回全部。

> **数据隔离在后端强制实现**，前端无需传过滤参数。

### 3.2 创建档案

```
POST /api/profiles
```

请求体：

```json
{
  "name": "张桂兰",
  "gender": "F",
  "birthday": "1954-03-12",
  "height": 158,
  "weight": 62,
  "blood_type": "A",
  "allergy": "青霉素",
  "medical_history": "高血压 8 年",
  "chronic_tags": ["高血压"],
  "emergency_contact": "李强",
  "emergency_phone": "13900139000"
}
```

### 3.3 档案详情 / 更新 / 删除

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/profiles/{id}` | 详情 |
| PUT | `/api/profiles/{id}` | 更新（字段同 3.2） |
| DELETE | `/api/profiles/{id}` | 删除（二次确认，软删除） |

---

## 4. 健康指标（HEALTH）

### 4.1 录入指标

```
POST /api/health/records
```

权限：老人（本人）/ 家属（代管老人）/ 护工（负责老人）

请求体：

```json
{
  "profile_id": 2001,
  "type": "BLOOD_PRESSURE",
  "values": { "systolic": 128, "diastolic": 82 },
  "measured_at": "2026-09-08 08:20:00",
  "remark": ""
}
```

`type` 取值与 `values` 结构：

| type | 含义 | values 结构 |
|---|---|---|
| BLOOD_PRESSURE | 血压 | `{ "systolic": 128, "diastolic": 82 }` |
| BLOOD_SUGAR | 血糖 | `{ "value": 6.8 }` |
| HEART_RATE | 心率 | `{ "value": 76 }` |
| SLEEP | 睡眠 | `{ "hours": 7.5, "quality": 3 }` |
| STEP | 步数 | `{ "count": 5200 }` |

响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "record_id": 30001,
    "is_abnormal": true,
    "risk_level": 1,
    "warning_id": 40001
  }
}
```

> 录入后由 Alert Agent 同步执行阈值检测；`is_abnormal` 为 true 时返回预警 ID，前端可提示"已触发健康预警"。

### 4.2 指标列表

```
GET /api/health/records?profile_id=2001&type=BLOOD_PRESSURE&page=1&page_size=20
```

### 4.3 作废误录指标并保留审计

```
DELETE /api/health/records/{id}
```

请求体为 `{ "reason": "复核发现误录" }`，原因必填。老人、家属和护工只能作废本人录入的记录；管理员可核验后作废其他记录。接口追加 `health_record_void`，保留原始测量及预警、检测证据关联；重复操作不重复写审计。默认历史列表、趋势、护工最新指标和 AI 数据上下文排除作废记录。历史列表传 `include_voided=true` 可查看原始数值、作废人及原因，返回 `is_voided`、`void_audit`、`can_void`。作废不会关闭原预警。

### 4.4 趋势数据（供 ECharts）

```
GET /api/health/trend?profile_id=2001&type=BLOOD_PRESSURE&days=30
```

响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "dates": ["2026-08-09", "2026-08-10"],
    "series": [
      { "name": "收缩压", "values": [126, 130] },
      { "name": "舒张压", "values": [80, 84] }
    ],
    "normal_range": { "min": 90, "max": 139 },
    "abnormal_points": [
      { "date": "2026-08-10", "value": 148, "level": 2 }
    ]
  }
}
```

> `normal_range` 由后端从 `sys_config` 读取，**前端不得写死正常范围**。

---

## 5. AI 健康咨询（AI）

### 5.1 发起咨询

```
POST /api/ai/chat
```

权限：老人（本人档案）/ 家属（已批准绑定的老人档案）/ 护工（当前负责的老人档案）

请求体：

```json
{
  "profile_id": 2001,
  "question": "我最近血压有点高，早上起来头有点晕，要紧吗？",
  "session_id": null
}
```

`session_id` 为空时自动创建新会话。

响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "session_id": 50001,
    "message_id": 60001,
    "answer": "我查了您近 7 天的记录，血压平均 142/90 mmHg……",
    "intent": "ABNORMAL",
    "agent": "RISK",
    "safety_level": "L3",
    "risk_level": 2,
    "sources": ["高血压日常管理指南", "老年晨起头晕处理建议"],
    "warning_id": 40002,
    "disclaimer": "AI 回答内容仅供参考，不构成医疗诊断"
  }
}
```

字段说明：

| 字段 | 说明 |
|---|---|
| intent | `NORMAL` / `DATA` / `ABNORMAL` / `EMERGENCY` |
| agent | 实际执行的 Agent：`HEALTH` / `HEALTH_DATA` / `RISK` / `EMERGENCY` |
| safety_level | L1~L4 安全分级 |
| sources | RAG 命中的知识来源，前端可展示以增强可信度 |
| warning_id | 触发预警时返回，否则为 null |

> 前端需展示 `intent` 与 `agent`，这是本项目"多 Agent 编排"的直观体现。

### 5.2 会话列表 / 消息 / 删除

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/ai/sessions?profile_id=2001` | 会话列表 |
| GET | `/api/ai/sessions/{id}/messages` | 会话内消息 |
| DELETE | `/api/ai/sessions/{id}` | 删除会话 |

### 5.3 角色范围

- 老人只能以本人档案发起咨询；家属只能使用已批准绑定的老人档案；护工只能使用当前负责的老人档案。
- 老人、家属、护工的会话列表仅返回本人发起的会话；读取消息和删除会话也必须是本人会话。角色生成的建议历史同样仅返回当前生成者的记录。即使其他用户有权访问同一老人档案，也不能查看这段私密咨询或他人的角色建议。
- 管理员维护知识库和系统配置，不使用老人健康咨询入口。护工使用护理工作助手；老人和家属分别使用本人健康生活助手、家属照护助手。
- 家属可对本人有权查看的预警登记联系、探访或送医结论；预警状态推进或忽略由护工、管理员执行。

---

## 6. 主动预警（ALERT）

> 本章按《设计决策记录 v1.0》D-04、D-05 重写。核心变化两点：
> 1. **AI 摘要是异步增强**，`ai_summary` 可能为空，前端必须能处理（D-04）
> 2. **处理状态与已读状态分离**，处理状态属预警本身，已读状态属当前用户（D-05）

### 6.0 两套状态的定义

| 维度 | 存储位置 | 取值 | 说明 |
|---|---|---|---|
| 处理状态 `status` | `health_warning`（全局唯一） | `PENDING` → `PROCESSING` → `RESOLVED` / `IGNORED` | 这条预警处理到哪一步 |
| 已读状态 `my_read_status` | `alert_receiver`（每人一条） | `UNREAD` / `READ` | 当前登录用户看没看过 |

补充规则：

- 任一人点开详情 → 只更新自己那条 `alert_receiver`，**不影响其他接收人**
- 家属提交跟进反馈 → 保持 `PENDING` 或 `PROCESSING`，追加 `warning_handle_record`，返回 `record_type=FOLLOW_UP`。
- 负责护工或管理员确认处理完成 → `status = RESOLVED`，追加 `record_type=RESOLUTION` 的处理记录。管理员统计的已处理次数不包含家属反馈。
- **已处理不等于已读**：未读的接收人仍应看到该预警及其处理结果

### 6.1 预警列表

```
GET /api/alerts?status=PENDING&level=3&page=1&page_size=20
```

`status`：`PENDING` / `PROCESSING` / `RESOLVED` / `IGNORED`；`level`：0~3

响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "list": [
      {
        "warning_id": 40001,
        "profile_id": 2001,
        "elder_name": "李凤英",
        "elder_age": 78,
        "type": "BLOOD_PRESSURE",
        "value_text": "178/102",
        "unit": "mmHg",
        "level": 3,
        "level_text": "高风险",
        "ai_summary": "该老人近 3 天血压持续在 165~178 区间，呈上升趋势……",
        "summary_status": "SUCCESS",
        "status": "PENDING",
        "my_read_status": "UNREAD",
        "trigger_source": "DATA_INPUT",
        "created_at": "2026-09-08 07:42:00",
        "handler_name": null,
        "handle_result": null
      }
    ],
    "total": 4,
    "page": 1,
    "page_size": 20
  }
}
```

字段说明：

| 字段 | 说明 |
|---|---|
| `ai_summary` | **可空**。为 `null` 时前端显示"AI 摘要生成中"或"生成失败，可查看原始数据"，不得隐藏整条预警 |
| `summary_status` | `PENDING`（生成中）/ `SUCCESS` / `FAILED` / `SKIPPED`（低级别预警不生成） |
| `my_read_status` | 当前登录用户对该预警的已读状态，用于列表红点 |
| `trigger_source` | `DATA_INPUT`（录入触发）/ `AI_CHAT`（咨询识别触发）/ `MANUAL`（人工创建） |

### 6.2 预警详情

```
GET /api/alerts/{id}
```

在列表字段基础上增加 `history_trend`（近 7 天该指标数据，供详情图表）与 `handles`（处理记录数组）。

访问详情时，后端自动将**当前用户**的 `alert_receiver.read_status` 置为 `READ`。

### 6.3 处理预警

```
POST /api/alerts/{id}/handle
```

请求体：

```json
{
  "result": "已电话联系老人，确认今日服药，安排明日复诊",
  "action": "CONTACTED"
}
```

`action`：`CONTACTED` / `ARRANGED_VISIT` / `SENT_HOSPITAL` / `OBSERVE`

负责护工或管理员提交结论后 `status` 流转为 `RESOLVED`；家属提交反馈时保持原状态。两者均写入 `warning_handle_record`，返回处理人角色和记录类型。家属只能登记已批准绑定档案的实际跟进情况，不能关闭、推进或忽略预警。

处理过程中可先置为中间态（护工已接单但尚未完成）：

```
PUT /api/alerts/{id}/status
```

请求体 `{ "status": "PROCESSING" }`；取值 `PROCESSING` / `IGNORED`。
仅护工和管理员可推进或忽略预警；家属使用上述处理结论接口登记跟进，不可改变预警处理阶段。

### 6.4 标记已读（作用于当前用户）

```
POST /api/alerts/{id}/read
```

只更新**当前登录用户**的 `alert_receiver.read_status`，不影响其他接收人，也不改变预警的 `status`。

### 6.5 AI 摘要重试（D-04）

```
POST /api/alerts/{id}/summary/retry
```

`summary_status = FAILED` 时，由用户或管理员手动触发重新生成。
返回 `3001` 时前端提示"AI 助手暂时不可用"，**预警本身保持可见可用**。

### 6.6 预警统计

```
GET /api/alerts/statistics
```

响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "pending": 3,
    "high_risk": 1,
    "today_new": 7,
    "handled": 12,
    "unread": 5
  }
}
```

> 口径说明：`pending` 为全局未处理条数；`unread` 为**当前用户**未读条数（D-05）。

### 6.7 通知未读数（D-03）

```
GET /api/notifications/unread
```

响应：

```json
{ "code": 0, "message": "success", "data": { "unread": 5, "latest_level": 3 } }
```

前端以 30 秒周期轮询本接口（数据量极小），用于红点提示。
**本期通知范围 = 站内通知**。短信 / 电话外呼需第三方通道与资质，列为【选配】，本期不实现；档案中的紧急联系人电话仅作展示与人工联系依据。

---

## 7. 家属绑定（FAMILY）

> 本章按 D-02 重写：绑定必须经老人确认，未确认前不产生任何数据访问权限。

### 7.1 绑定状态机

```
（家属提交）PENDING ──确认──> APPROVED ──任一方解绑──> REVOKED
                  └──拒绝──> REJECTED
```

| 状态 | 含义 | 数据权限 |
|---|---|---|
| `PENDING` | 待老人（或管理员 / 护工代）确认 | 无 |
| `APPROVED` | 已生效 | 可查看该老人档案、指标、预警、咨询记录 |
| `REJECTED` | 已拒绝 | 无 |
| `REVOKED` | 已解绑 | 立即收回 |

### 7.2 接口清单

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/family/bind` | **提交绑定申请**（家属端），请求体 `{ "phone": "13800138000", "relation": "儿子", "note": "" }` |
| GET | `/api/family/bind-requests` | **待我确认的申请**（老人端 / 管理员端） |
| PUT | `/api/family/bind/{id}/confirm` | 确认或拒绝，请求体 `{ "action": "APPROVE", "note": "" }` |
| GET | `/api/family/elders` | 已生效（APPROVED）的代管老人列表 |
| DELETE | `/api/family/bind/{id}` | 解绑，任一方发起即时生效 |

请求 / 响应要点：

- 提交申请时，后端校验老人手机号是否存在；不存在返回 `2002`
- 同一对"家属-老人"已存在 `PENDING` 或 `APPROVED` 记录时，返回 `4001`
- 老人绑定家属数达上限（默认 5，入 `sys_config` 的 `family_bind_max`）时返回 `4002`
- 解绑（`REVOKED`）为状态变更而非物理删除，历史处理记录保留用于追溯
- 代确认时写入 `approved_by`（操作人）与 `approve_note`（原因）；老人本人确认时 `approved_by` 为其本人

绑定申请对象：

```json
{
  "bind_id": 9001,
  "profile_id": 2001,
  "elder_name": "李凤英",
  "elder_phone_masked": "138****8000",
  "family_name": "李强",
  "relation": "儿子",
  "note": "我是李凤英的儿子",
  "status": "PENDING",
  "created_at": "2026-09-08 10:12:00"
}
```

---

## 8. 护工端（CARE）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/care/elders?status=ABNORMAL` | 负责老人列表，异常优先排序 |
| GET | `/api/care/elders/{profile_id}` | 老人详情（档案 + 最近指标 + 预警） |
| GET | `/api/care/handles` | 本人处理记录 |

`/api/care/elders` 单条结构：

```json
{
  "profile_id": 2001,
  "elder_name": "李凤英",
  "age": 78,
  "gender": "F",
  "address": "3 号楼 201",
  "status": "ABNORMAL",
  "latest_bp": "178/102",
  "latest_sugar": 6.4,
  "sleep_hours": 5.1,
  "pending_warnings": 1,
  "updated_at": "2026-09-08 07:42:00"
}
```

`status`：`UNKNOWN`（暂无健康数据）/ `STALE`（数据待更新）/ `NO_PENDING_ALERT`（暂无待处理预警）/ `WATCH` / `ABNORMAL`。待处理异常优先；没有预警不表示健康正常。数据新鲜度按 `sys_config.care_health_data_fresh_hours` 判定，默认 72 小时，仅用于提示记录待更新。旧 `NORMAL` 查询参数兼容映射至 `NO_PENDING_ALERT`。

---

## 9. 管理员（ADMIN）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/admin/users?role=&keyword=` | 用户列表 |
| POST | `/api/admin/users` | **创建护工 / 管理员账号**（D-01），见下方 |
| PUT | `/api/admin/users/{id}/status` | 禁用 / 启用，请求体 `{ "enabled": false }` |
| GET | `/api/admin/thresholds` | 预警阈值配置列表 |
| PUT | `/api/admin/thresholds/{id}` | 更新阈值，保存后即时生效 |
| GET | `/api/admin/indicators` | 健康指标配置（类型、单位、范围） |
| GET | `/api/admin/knowledge` | 知识库条目列表 |
| POST | `/api/admin/knowledge` | 新增知识条目 |
| POST | `/api/admin/knowledge/upload` | 【选配】上传文档自动解析建索引（FR-KB-005，本期不实现） |
| GET | `/api/admin/statistics?range=7d` | 统计（用户数、咨询数、预警数） |

### 9.1 创建护工 / 管理员账号（D-01）

```
POST /api/admin/users
```

权限：仅 `ADMIN`。

请求体：

```json
{
  "phone": "13700137000",
  "password": "Init@2026",
  "name": "王护工",
  "role": "CARE"
}
```

`role` 仅允许 `CARE` 或 `ADMIN`；传 `ELDER` / `FAMILY` 时返回 `2001`（这两类走公开注册）。
响应返回新建用户基本信息，密码由后端 bcrypt 加密存储，不回显。

> 初始管理员账号由数据库初始化脚本 `init_data.sql` 预置，不依赖本接口。

阈值对象结构：

```json
{
  "config_id": 1,
  "indicator": "BLOOD_PRESSURE_SYSTOLIC",
  "indicator_name": "收缩压",
  "unit": "mmHg",
  "level0_range": "90~139",
  "level1_range": "140~159",
  "level2_range": "160~179",
  "level3_range": ">=180",
  "enabled": true
}
```

---

## 10. 系统配置（CONFIG）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/config/indicators` | 可录入指标类型与单位（前端表单用） |
| GET | `/api/config/thresholds` | 当前生效阈值（前端展示正常范围用，不写死） |

---

## 11. 待确认事项

| 编号 | 事项 | 当前状态 |
|---|---|---|
| 1 | AI 咨询是否需要**流式输出**（SSE） | 【选配】。v0.2 按一次性返回设计，主闭环跑通后再议 |
| 2 | 预警通知是否需要**服务端推送**（WebSocket） | 【选配】。v0.2 按 30 秒轮询未读数实现（D-03），已满足演示 |
| 3 | 文件上传（知识库文档、头像）接口 | 【选配】。知识库上传已标【选配】并列入 9 章但不实现（FR-KB-005）；头像本期不做 |
| 4 | 大模型选型（DeepSeek / 通义千问 / GLM-4） | **仍未定**。代码层按"换模型只改 `.env` 的 `LLM_PROVIDER`"设计，不影响本契约 |
| 5 | 短信 / 电话外呼通知 | 【选配】。需第三方通道与资质，本期明确不实现，需求端已同步降级（D-03） |
| 6 | 后端技术栈 | 已确认为 **Python FastAPI**，本契约的 URL 与响应结构即为最终形态（FastAPI 原生支持自动生成 /docs，联调时可直接对照） |

---

## 12. 数据模型补充（v0.2 新增，供 9/24 数据库设计参考）

D-05 引入的接收人概念需要新增一张表，v0.1 契约未体现：

| 表 | 作用 | 关键字段 |
|---|---|---|
| `alert_receiver` | 预警接收人（每条预警 × 每个接收人一条） | `warning_id`、`user_id`、`read_status`、`created_at` |
| `family_bind` | 家属绑定关系（含申请确认过程） | `bind_id`、`family_user_id`、`profile_id`、`relation`、`status`、`approved_by`、`approve_note` |

`health_warning` 表需增加 `summary_status` 字段；`ai_summary` 字段允许为 NULL。

---

> 本契约是前后端并行的基础。接口有变，先改文档，再改代码。
> 设计层面的裁决见 `03.概要设计/设计决策记录_康养系统_v1.0.md`。

## 2026-10-14 功能边界修复补充

本节记录当前代码的安全修复，原有接口路径保留。

| 接口 | 补充行为 |
|---|---|
| `PUT /api/auth/me` | 修改登录手机号或密码时要求 `current_password`。可选 `new_password` 为 8 至 72 字符且 UTF-8 不超过 72 字节；姓名、手机号和密码在同一事务更新。成功返回 `reauth_required`，为真时所有旧会话失效，前端清除登录状态并返回登录页。仅改姓名无需二次验证。原 `PUT /api/auth/password` 保留。 |
| `DELETE /api/profiles/{id}` | 存在未完成服务、借出设备、未结束报名或待处理预警时返回 HTTP 409，并提示各项数量；不会删除业务记录。 |
| `POST /api/ai/chat` | 紧急信息先确定症状对象。本人、其他人或对象不清时仍给即时求助提示，但 `warning_id` 为 null，不给所选老人误建预警。只有指向当前档案的当前症状才创建该老人紧急预警；软件分流不能替代现场急救。 |
| 异常咨询 | 已解决、已忽略及关联测量已作废的历史预警保留来源说明，但不加入返回的当前未处理有效预警等级。此等级不等于临床健康诊断。 |
| 预警详情和列表 | 新增 `summary_message`，说明摘要预算不足、模型失败或关联测量作废；只有真正生成的内容进入 `ai_summary`。 |
| `POST /api/alerts/{id}/summary/retry` | 非失败摘要返回 409；每日额度、单条次数或冷却限制触发时返回 429。失败请求的额度预留持久保存，不能通过删除咨询记录绕过。 |

可选摘要使用 `sys_config.ai_summary_daily_limit`（全院每日默认 100 次）、`ai_summary_warning_daily_limit`（单条每日默认 3 次）及 `ai_summary_cooldown_seconds`（手动重试间隔默认 60 秒）。每次上游请求都占一次额度，包括自动重试和失败请求；上限不限制测量、确定性预警、通知或处理。已作废测量跳过摘要；模型生成期间作废则丢弃返回分析，原预警仍需人工核验。

生活服务、健康录入和个人阈值页面在切换档案时清空原表单并忽略旧响应。服务、设备申请及阈值提案始终使用打开表单时的档案编号；借还列表按所选档案筛选，工作人员可切回全部授权任务。

## 2026-10-16 梁霁鸣提交整合

`GET /api/health/status?profile_id={id}` 返回当前授权档案的五类指标参考。当前比较使用院内默认或已审核个体阈值；原始检测证据单独保存在 `recorded_assessment`，不重算历史预警。`data_status` 为 `NO_DATA`、`STALE` 或 `FRESH`；无数据、数据待更新或检测停用时 `risk_level` 可为 null，不能视作健康正常。

基线排除本次、后续、未来及已作废测量，使用本次之前七天内最多五百条有效历史样本，至少两条才计算均值。血压两个分量分别给出 `baseline_components`，不足或分母为零时波动比例为 null，不能显示为平稳。波动提醒参数位于 `sys_config.FLUCTUATION_THRESHOLD`，缺失则不作波动提醒；不新增自动医疗预警，也不替代健康诊断。

活动建议接口为 `GET /api/activities`、`GET /api/activities/recommend?profile_id={id}`，及管理员专用 `POST /api/activities`、`PUT /api/activities/{id}`、`DELETE /api/activities/{id}`。建议读取按档案权限校验；停用条目只在管理员列表显示。DELETE 表示停用建议，不影响已排期活动和报名。

规则字段 `rules.suitable` 与 `rules.avoid` 支持 `min_age`、`max_age`、`chronic_in`、`seasons_in`、`seasons_not_in`，同组条件全部满足才命中；年龄上下限须有序，季节仅可选 spring、summer、autumn、winter。`caution.max_risk_level` 为 1 至 3 的整数。未知字段、错误类型或矛盾条件返回 422；不能直接保存任意 JSON。历史规则损坏时返回需确认且禁止通过该卡申请。

建议返回 `profile_id`、`suitability`、`reasons`、`can_request` 及 `service_category`。无近期有效记录返回需确认，有高风险记录或待处理高风险预警时暂缓参与；“可了解”不等于医学适宜性或已报名。前端只预填现有服务申请，用户确认地点与需求后才能提交，工作人员继续接单处理。

不启用分支中的独立 `profile_threshold` 直写体系和年龄自动放宽。管理员旧页面入口 `/admin/profile-thresholds` 复用当前 `PersonalThresholds`，继续使用 `/api/profiles/{id}/threshold-proposals` 与审核接口。
