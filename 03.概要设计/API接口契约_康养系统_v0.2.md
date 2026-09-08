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

### 4.3 删除指标

```
DELETE /api/health/records/{id}
```

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

权限：老人 / 家属（代管老人）

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
- 任一人提交处理结果 → `status = RESOLVED`，写入 `warning_handle_record`，其余人界面显示"已由 XXX 于 XX 时间处理"
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

处理后 `status` 流转为 `RESOLVED`，并写入 `warning_handle_record`（记录处理人、方式、说明、时间）。

处理过程中可先置为中间态（护工已接单但尚未完成）：

```
PUT /api/alerts/{id}/status
```

请求体 `{ "status": "PROCESSING" }`；取值 `PROCESSING` / `IGNORED`。

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

`status`：`NORMAL` / `WATCH` / `ABNORMAL`

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
