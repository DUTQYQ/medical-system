-- ============================================================
-- 基于 AI 智能体的智能康养系统 · 初始化数据 init_data.sql
-- ============================================================
-- 版本：v1.0　日期：2026-09-12
-- 前置：先执行 schema.sql 建库建表
--       mysql -u root -p < schema.sql
--       mysql -u root -p kangyang < init_data.sql
-- 归属：丘宇乾（编写）· 周彦龙（评审）
--
-- 本脚本内容：
--   1. 预置 1 个管理员账号（D-01：不依赖注册接口，也不依赖"第一个注册的人是管理员"）
--   2. 阈值配置（sys_config，DB-1 配置化的核心，代码不得硬编码）
--   3. 系统参数与指标配置
--   4. 演示用数据：1 老人 + 1 家属 + 1 护工 + 绑定关系 + 指标记录 + 1 条预警
--
-- 演示账号密码统一为：Abc123456
-- password_hash 为 bcrypt 加密串（cost=12），下方哈希已实测可通过 bcrypt.checkpw 校验。
-- 若需重新生成：python -c "import bcrypt;print(bcrypt.hashpw(b'Abc123456',bcrypt.gensalt(rounds=12)).decode())"
-- 首次部署后请务必修改管理员密码。
-- ============================================================

SET NAMES utf8mb4;
USE `kangyang`;

SET FOREIGN_KEY_CHECKS = 0;

-- 清空既有数据（幂等，可重复执行）
TRUNCATE TABLE `ai_log`;
TRUNCATE TABLE `knowledge_chunk`;
TRUNCATE TABLE `knowledge_document`;
TRUNCATE TABLE `medication`;
TRUNCATE TABLE `chat_message`;
TRUNCATE TABLE `chat_session`;
TRUNCATE TABLE `warning_handle_record`;
TRUNCATE TABLE `alert_receiver`;
TRUNCATE TABLE `health_warning`;
TRUNCATE TABLE `health_record`;
TRUNCATE TABLE `care_relation`;
TRUNCATE TABLE `family_bind`;
TRUNCATE TABLE `elder_profile`;
TRUNCATE TABLE `sys_config`;
TRUNCATE TABLE `user`;

SET FOREIGN_KEY_CHECKS = 1;


-- ============================================================
-- 一、用户（预置管理员 + 演示账号）
-- ============================================================
-- 角色：ELDER 老人 / FAMILY 家属 / CARE 护工 / ADMIN 管理员
-- 管理员为预置（D-01）；其余账号亦预置，便于答辩直接登录演示。

INSERT INTO `user` (`id`, `phone`, `password_hash`, `name`, `role`, `status`) VALUES
(1, '13000000001', '$2b$12$KLC3i9QqsCforZFtVXnun.FUS8gmBPIDuRJ5XjKmlcljDKAd3DdUW', '系统管理员', 'ADMIN', 1),
(2, '13000000002', '$2b$12$KLC3i9QqsCforZFtVXnun.FUS8gmBPIDuRJ5XjKmlcljDKAd3DdUW', '张桂兰',     'ELDER', 1),
(3, '13000000003', '$2b$12$KLC3i9QqsCforZFtVXnun.FUS8gmBPIDuRJ5XjKmlcljDKAd3DdUW', '李强',       'FAMILY',1),
(4, '13000000004', '$2b$12$KLC3i9QqsCforZFtVXnun.FUS8gmBPIDuRJ5XjKmlcljDKAd3DdUW', '王护工',     'CARE',  1);


-- ============================================================
-- 二、阈值配置 sys_config（DB-1：配置化，代码不硬编码）
-- ============================================================
-- 说明：level0 正常 / level1 轻度 / level2 较高 / level3 高风险
--       前端"正常范围"由后端读此表返回，界面不得写死。

INSERT INTO `sys_config` (`config_key`, `config_value`, `config_type`, `group_name`, `description`, `enabled`) VALUES
-- ---------------- 血压（收缩压，mmHg） ----------------
('BLOOD_PRESSURE_SYSTOLIC', '{"level0":"90~139","level1":"140~159","level2":"160~179","level3":">=180"}',
 'threshold', 'threshold', '血压·收缩压阈值（mmHg）', 1),
-- ---------------- 血压（舒张压，mmHg） ----------------
('BLOOD_PRESSURE_DIASTOLIC', '{"level0":"60~89","level1":"90~99","level2":"100~109","level3":">=110"}',
 'threshold', 'threshold', '血压·舒张压阈值（mmHg）', 1),
-- ---------------- 血糖（mmol/L） ----------------
('BLOOD_SUGAR', '{"level0":"3.9~6.1","level1":"6.2~7.0","level2":"7.1~11.1","level3":">=11.2"}',
 'threshold', 'threshold', '血糖阈值（mmol/L，空腹参考）', 1),
-- ---------------- 心率（次/分） ----------------
('HEART_RATE', '{"level0":"60~100","level1":"50~59,101~110","level2":"40~49,111~130","level3":"<40 或 >130"}',
 'threshold', 'threshold', '心率阈值（次/分）', 1),
-- ---------------- 睡眠（小时） ----------------
('SLEEP_HOURS', '{"level0":">=7","level1":"6~7","level2":"5~6","level3":"<5"}',
 'threshold', 'threshold', '睡眠时长阈值（小时）', 1),
-- ---------------- 步数（步/日） ----------------
('STEP_COUNT', '{"level0":">=6000","level1":"4000~5999","level2":"2000~3999","level3":"<2000"}',
 'threshold', 'threshold', '日常步数阈值（步/日）', 1),
-- ---------------- 系统参数 ----------------
('family_bind_max',        '5',  'number', 'system', '单个老人可绑定的家属上限（D-02）', 1),
('alert_unread_poll_sec',  '30', 'number', 'system', '通知未读数前端轮询周期（秒，D-03）', 1),
('ai_summary_timeout_sec', '8',  'number', 'system', 'AI 摘要生成超时（秒），超时判失败并降级（D-04）', 1),
('ai_summary_retry',       '1',  'number', 'system', 'AI 摘要失败重试次数（D-04）', 1),
('emergency_keywords',     '["胸痛","呼吸困难","意识丧失","昏厥","无法起身","大量出血","言语不清"]',
 'json', 'system', '紧急关键词：即使模型未判紧急，命中即由代码强制升级为 L4（R-01）', 1),
('llm_provider',           'deepseek', 'string', 'system', '大模型提供方（代码读取，切换模型只改此项 + .env 的 Key）', 1);


-- ============================================================
-- 三、演示数据：档案 / 绑定 / 指标 / 预警
-- ============================================================

-- ---------- 老人档案 ----------
INSERT INTO `elder_profile`
  (`id`, `user_id`, `name`, `gender`, `birthday`, `height`, `weight`, `blood_type`,
   `allergy`, `medical_history`, `chronic_tags`, `emergency_contact`, `emergency_phone`, `deleted`)
VALUES
(2001, 2, '张桂兰', 'F', '1948-03-12', 158.0, 62.0, 'A',
 '青霉素', '高血压 8 年，长期服用氨氯地平', '["高血压"]', '李强', '13000000003', 0);

-- ---------- 家属绑定（已生效，便于直接演示闭环） ----------
-- 本脚本只预置一条 APPROVED 关系以便直接演示主闭环；如需演示待确认流程，
-- 应通过绑定申请接口创建 PENDING 记录，再验证确认前不可访问（TC-A-03）。
INSERT INTO `family_bind`
  (`id`, `family_user_id`, `profile_id`, `relation`, `note`, `status`, `approved_by`, `approve_note`, `approve_time`)
VALUES
(9001, 3, 2001, '儿子', '我是张桂兰的儿子', 'APPROVED', 2, NULL, '2026-09-10 10:00:00');

-- ---------- 护工分配 ----------
INSERT INTO `care_relation` (`id`, `care_user_id`, `profile_id`, `status`) VALUES
(8001, 4, 2001, 1);

-- ---------- 健康指标记录（近 7 天血压 + 今日血糖/睡眠） ----------
INSERT INTO `health_record`
  (`id`, `profile_id`, `type`, `val1`, `val2`, `measured_at`, `is_abnormal`, `remark`, `recorder_id`)
VALUES
(30001, 2001, 'BLOOD_PRESSURE', 128.00, 82.00,  '2026-09-05 07:30:00', 0, '', 2),
(30002, 2001, 'BLOOD_PRESSURE', 165.00, 98.00,  '2026-09-06 07:35:00', 1, '早上起床后测量', 2),
(30003, 2001, 'BLOOD_PRESSURE', 170.00, 100.00, '2026-09-07 07:40:00', 1, '', 2),
(30004, 2001, 'BLOOD_PRESSURE', 178.00, 102.00, '2026-09-08 07:42:00', 1, '感觉头晕', 2),
(30005, 2001, 'BLOOD_SUGAR',    6.40,  NULL,     '2026-09-08 07:45:00', 0, '空腹', 2),
(30006, 2001, 'HEART_RATE',     82.00, NULL,     '2026-09-08 07:46:00', 0, '', 2),
(30007, 2001, 'SLEEP',          5.50,  3.00,     '2026-09-08 06:30:00', 0, '夜间易醒', 2);

-- ---------- 预警（D-04：主流程同步生成，AI 摘要异步补；此处预置为已成功） ----------
-- 用途：演示"异常数据自动变成家属待办"这一核心卖点。
INSERT INTO `health_warning`
  (`id`, `profile_id`, `record_id`, `type`, `value_text`, `level`, `status`,
   `trigger_source`, `ai_summary`, `summary_status`, `create_time`)
VALUES
(40001, 2001, 30004, 'BLOOD_PRESSURE', '178/102', 3, 'PENDING',
 'DATA_INPUT',
 '该老人近 3 天血压持续处于 165~178 mmHg 区间，呈明显上升趋势，今日收缩压达 178 mmHg（高风险）。结合主诉头晕，建议尽快安排复诊，切勿自行加量服药。',
 'SUCCESS', '2026-09-08 07:42:00');

-- ---------- 预警接收人（D-05：处理状态与已读状态分离，每人一条） ----------
INSERT INTO `alert_receiver` (`id`, `warning_id`, `user_id`, `read_status`, `read_time`) VALUES
(70001, 40001, 3, 'UNREAD', NULL),
(70002, 40001, 4, 'UNREAD', NULL),
(70003, 40001, 2, 'UNREAD', NULL);

-- ============================================================
-- 四、初始化完成
-- ============================================================
-- 演示账号（密码统一 Abc123456）：
--   管理员  13000000001 / 王护工 13000000004 / 老人 张桂兰 13000000002 / 家属 李强 13000000003
--
-- 验证要点：
--   1. 用家属账号登录，通知中心应显示 1 条未读预警（红点）——验证 TC-A-03/08
--   2. 用管理员登录，预警规则配置页应能读到上方阈值——验证 FR-ADMIN-004/010
--   3. 把 ai_summary 置空再查预警列表，界面应显示"AI 摘要生成中"而非崩溃——验证 D-04 / TC-A-06
-- ============================================================
