<!-- ============================================================
     基于 AI 智能体的康养系统 · API 接口契约 v0.1
     用途：前后端并行开发的对齐基准；前端据此 mock，后端据此实现
     维护：接口变更必须先改本文档，双方确认后再改代码
     责任人：丘宇乾（后端实现）· 梁霁鸣/周彦龙（前端使用）
     ============================================================ -->

# 基于 AI 智能体的康养系统 · API 接口契约

> 版本：v0.1（初稿，随概要设计评审细化）
> 编写日期：2026-09-08
> 用途：前后端并行开发对齐基准

---

## 0. 文档信息

| 项 | 内容 |
|---|---|
| 文档版本 | v0.1（待评审） |
| 编写日期 | 2026-09-08 |
| 上游文档 | 需求分析说明书 v1.0（122 条 FR） |
| 接口总数 | 36 个 |

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
| 5001 | 服务器内部错误 | 通用错误提示 |

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

`role` 取值：`ELDER` / `FAMILY` / `CARE` / `ADMIN`

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
    "agent": "RISK_AGENT",
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

### 6.1 预警列表

```
GET /api/alerts?status=PENDING&level=3&page=1&page_size=20
```

`status`：`PENDING` / `VIEWED` / `HANDLED`；`level`：0~3

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
        "status": "PENDING",
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

`trigger_source`：`DATA_INPUT`（录入触发）/ `AI_CHAT`（咨询识别触发）

### 6.2 预警详情

```
GET /api/alerts/{id}
```

在列表字段基础上增加 `history_trend`（近 7 天该指标数据，供详情图表）。

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

处理后状态自动流转为 `HANDLED`，并写入 `warning_handle_record`。

### 6.4 标记已读

```
POST /api/alerts/{id}/read
```

### 6.5 预警统计

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
    "handled": 12
  }
}
```

---

## 7. 家属绑定（FAMILY）

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/family/bind` | 绑定老人，请求体 `{ "phone": "13800138000", "relation": "儿子" }` |
| GET | `/api/family/elders` | 代管老人列表 |
| DELETE | `/api/family/bind/{profile_id}` | 解绑 |

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
| PUT | `/api/admin/users/{id}/status` | 禁用 / 启用，请求体 `{ "enabled": false }` |
| GET | `/api/admin/thresholds` | 预警阈值配置列表 |
| PUT | `/api/admin/thresholds/{id}` | 更新阈值，保存后即时生效 |
| GET | `/api/admin/indicators` | 健康指标配置（类型、单位、范围） |
| GET | `/api/admin/knowledge` | 知识库条目列表 |
| POST | `/api/admin/knowledge` | 新增知识条目 |
| GET | `/api/admin/statistics?range=7d` | 统计（用户数、咨询数、预警数） |

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

1. AI 咨询是否需要**流式输出**（SSE）？当前契约按一次性返回设计，【选配】项可后补
2. 预警通知是否需要**服务端推送**（WebSocket）？当前按前端轮询设计，演示规模足够
3. 文件上传（知识库文档、头像）接口未在 v0.1 中定义，待【选配】项确认后补充
4. 后端技术栈若确定为 Java SSM，路径与响应结构保持不变，仅实现语言不同

---

> 本契约是前后端并行的基础。接口有变，先改文档，再改代码。
