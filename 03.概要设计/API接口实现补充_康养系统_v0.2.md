# API 接口实现补充 v0.2

日期：2026-10-08。本文补齐需求分析说明书中已有的核心功能和页面联调所需接口，沿用 v0.2 的认证、权限、错误码和统一响应 `{ code, message, data }`，不改变既定方案。未在本文重述的接口以原契约为准。

## 核心功能补充

| 方法 | 路径 | 请求 / 行为 | 对应需求 |
|---|---|---|---|
| PUT | `/api/auth/me` | 修改本人 `name`、`phone`；唯一性、格式由后端校验 | FR-AUTH-010 |
| POST | `/api/auth/privacy-consent` | `{ "accepted": true }`，记录当前用户授权版本与时间；不接受则不给健康数据访问权限 | FR-AUTH-011 |
| GET | `/api/family/binds` | 当前家属的申请历史，含 PENDING、APPROVED、REJECTED、REVOKED；申请不授予老人数据权限 | FR-FAMILY-001/003 |
| GET | `/api/notifications` | 当前用户站内预警通知，`page`、`page_size`；返回列表及总数，只取当前有效关系可见的数据 | FR-ALERT-011、FR-FAMILY-012 |
| POST | `/api/notifications/{id}/read` | `id` 为预警 ID；仅更新当前用户对应接收记录 | FR-ALERT-011 |
| POST | `/api/notifications/read-all` | 仅标记当前用户有权限访问的通知；不改变任何预警处理状态 | FR-ALERT-011 |
| PUT | `/api/admin/users/{id}/role` | `{ "role": "CARE" }` 或 `ADMIN`；仅管理员，限制在 CARE/ADMIN 间变更，令该用户旧 Token 失效；保留最后一个启用管理员 | FR-ADMIN-003 |
| PUT | `/api/admin/indicators/{type}` | 更新配置化的 `enabled`、`unit`、字段合法范围；写入 `sys_config`，即时生效 | FR-ADMIN-005 |
| PUT | `/api/admin/knowledge/{id}` | `{ "title", "category", "content", "enabled" }`；仅管理员；索引更新后查询不得返回旧正文 | FR-KB-002/006/008 |
| DELETE | `/api/admin/knowledge/{id}` | 仅管理员；删除/禁用条目并使其退出有效索引 | FR-KB-002/006/008 |
| POST | `/api/admin/knowledge/reindex` | 重建所有启用条目的向量索引；失败明确返回错误 | FR-KB-008 |

`GET /api/admin/statistics?range=1d|7d|30d` 返回周期起止时间、注册用户/活跃用户、咨询次数、预警发生/待处理/已处理次数、各模块实际数据总量及按日期聚合的图表数组。统计与明细使用一致的时间范围，页面展示统计口径。

`GET /api/care/elders` 另支持 `start_at`、`end_at` 日期时间，与 `status` 同时过滤。填写时间范围时，仅返回在该时间段内存在测量记录的负责老人；记录时间使用 `measured_at`，状态仍为当前状态，页面说明筛选口径。起始时间不得晚于结束时间。对应 FR-CARE-009。

## 运行质量补充

档案创建遵循 FR-HEALTH-001 的 1~N 份要求。老人创建的档案均归本人；管理员可额外传 `user_id` 指定已有老人账号。家属或护工代建必须传 `source_profile_id`，后端先确认其当前有权访问该来源档案，再在同一老人账号下创建新档案，仅为当前创建者建立对应生效绑定/在管关系。其他家属和护工不会自动获得新档案权限。家属通过手机号申请绑定时，可选 `profile_id` 必须属于该手机号对应老人；不传时选择该老人首份有效档案。档案详情及修改删除仍按每份档案的实时授权判断。

| 方法 | 路径 | 行为 |
|---|---|---|
| PUT | `/api/auth/password` | `{ "old_password", "new_password" }`；本人修改密码，校验旧密码并撤销旧 Token |
| GET | `/api/healthz` | 不泄露连接配置或密钥的健康检查；数据库不可用时明确失败 |

## 【选配】护工分配

管理员可通过 `/api/admin/care-relations` 查询/创建分配，通过 `DELETE /api/admin/care-relations/{id}` 交接/撤销。请求使用 `{ "care_user_id", "profile_id" }`，双方必须存在且护工账号启用。撤销后护工对该老人权限立即失效，历史处理记录保留。对应 FR-CARE-011，不列为核心验收前提。

## 实现边界

短信验证码、电话外呼、知识文件上传、流式输出和 PDF 导出仍为【选配】。无真实模型 Key 时返回 AI 不可用，不能伪装为模型成功；异常录入、站内通知和处理留痕仍可独立运行。模型仅接收经代码鉴权的上下文，不执行 SQL、权限判定或数据库写入。

测试使用独立临时数据库。既有 `schema.sql`、`init_data.sql` 含清空操作，应用启动不得执行它们，也不得自动覆盖已有 MySQL 数据。
