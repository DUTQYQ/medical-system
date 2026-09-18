-- ============================================================
-- 基于 AI 智能体的智能康养系统 · 建表脚本 schema.sql
-- ============================================================
-- 版本：v1.0　日期：2026-09-12
-- 数据库：MySQL 8.0　字符集：utf8mb4　排序：utf8mb4_general_ci
-- 事实来源：03.概要设计/概要设计说明书_康养系统_v1.0.md 第 4 章
-- 归属：丘宇乾（编写）· 周彦龙（评审）
--
-- 执行顺序：先建所有表，再补外键（避免建表时依赖顺序）
-- 使用方式：
--   mysql -u root -p < schema.sql
--   mysql -u root -p kangyang < init_data.sql
-- ============================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

CREATE DATABASE IF NOT EXISTS `kangyang`
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_general_ci;

USE `kangyang`;

-- 按依赖倒序清理（仅首次执行有效，重复执行安全）
DROP TABLE IF EXISTS `ai_log`;
DROP TABLE IF EXISTS `knowledge_chunk`;
DROP TABLE IF EXISTS `knowledge_document`;
DROP TABLE IF EXISTS `medication`;
DROP TABLE IF EXISTS `chat_message`;
DROP TABLE IF EXISTS `chat_session`;
DROP TABLE IF EXISTS `warning_handle_record`;
DROP TABLE IF EXISTS `alert_receiver`;
DROP TABLE IF EXISTS `health_warning`;
DROP TABLE IF EXISTS `health_record`;
DROP TABLE IF EXISTS `care_relation`;
DROP TABLE IF EXISTS `family_bind`;
DROP TABLE IF EXISTS `elder_profile`;
DROP TABLE IF EXISTS `sys_config`;
DROP TABLE IF EXISTS `user`;


-- ============================================================
-- 一、核心表（11 张）
-- ============================================================

-- ---------- 1. user 用户主表 ----------
-- 四类角色：ELDER 老年用户 / FAMILY 家属 / CARE 护工 / ADMIN 管理员
-- 公开注册仅允许 ELDER、FAMILY；CARE、ADMIN 由管理员创建（D-01）
CREATE TABLE `user` (
  `id`              BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键',
  `phone`           VARCHAR(20)  NOT NULL                COMMENT '手机号（登录名）',
  `password_hash`   VARCHAR(100) NOT NULL                COMMENT '密码（bcrypt 加密，禁明文）',
  `name`            VARCHAR(50)  NOT NULL                COMMENT '姓名',
  `role`            VARCHAR(10)  NOT NULL                COMMENT '角色：ELDER/FAMILY/CARE/ADMIN',
  `status`          TINYINT      NOT NULL DEFAULT 1      COMMENT '状态：1 启用 / 0 禁用（禁用后 Token 立即失效）',
  `avatar`          VARCHAR(255)     NULL                COMMENT '头像 URL（本期不做上传）',
  `last_login_time` DATETIME         NULL                COMMENT '最近登录时间',
  `create_time`     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time`     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_phone` (`phone`),
  KEY `idx_user_role` (`role`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='用户主表（四类角色）';


-- ---------- 2. elder_profile 老人健康档案 ----------
CREATE TABLE `elder_profile` (
  `id`                BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键',
  `user_id`           BIGINT       NOT NULL                COMMENT '归属账号 ID（FK → user.id）',
  `name`              VARCHAR(50)  NOT NULL                COMMENT '姓名',
  `gender`            CHAR(1)          NULL                COMMENT '性别：M 男 / F 女',
  `birthday`          DATE             NULL                COMMENT '出生日期',
  `height`            DECIMAL(5,1)     NULL                COMMENT '身高 cm',
  `weight`            DECIMAL(5,1)     NULL                COMMENT '体重 kg',
  `blood_type`        VARCHAR(5)       NULL                COMMENT '血型',
  `allergy`           VARCHAR(255)     NULL                COMMENT '过敏史',
  `medical_history`   VARCHAR(500)     NULL                COMMENT '既往病史',
  `chronic_tags`      VARCHAR(255)     NULL                COMMENT '慢病标签（JSON 数组，如 ["高血压","糖尿病"]）',
  `emergency_contact` VARCHAR(50)      NULL                COMMENT '紧急联系人姓名（仅展示/人工联系依据，D-03）',
  `emergency_phone`   VARCHAR(20)      NULL                COMMENT '紧急联系人电话（仅展示/人工联系依据，D-03）',
  `deleted`           TINYINT      NOT NULL DEFAULT 0      COMMENT '软删除：0 正常 / 1 已删除',
  `create_time`       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time`       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_profile_user` (`user_id`),
  KEY `idx_profile_deleted` (`deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='老人健康档案';


-- ---------- 3. family_bind 家属绑定（D-02，状态机） ----------
-- 流程：PENDING --确认--> APPROVED --解绑--> REVOKED ；PENDING --拒绝--> REJECTED
-- 注意：表名为 family_bind，不是旧名 family_relation（见概要设计 4.9 节 E-06）
CREATE TABLE `family_bind` (
  `id`             BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键（bind_id）',
  `family_user_id` BIGINT       NOT NULL                COMMENT '家属账号 ID（FK → user.id）',
  `profile_id`     BIGINT       NOT NULL                COMMENT '老人档案 ID（FK → elder_profile.id）',
  `relation`       VARCHAR(20)      NULL                COMMENT '亲属关系：儿子/女儿/配偶…',
  `note`           VARCHAR(255)     NULL                COMMENT '申请备注',
  `status`         VARCHAR(10)  NOT NULL DEFAULT 'PENDING' COMMENT '状态：PENDING/APPROVED/REJECTED/REVOKED',
  `approved_by`    BIGINT           NULL                COMMENT '确认人 ID（代确认时记录操作人，本人确认为本人）',
  `approve_note`   VARCHAR(255)     NULL                COMMENT '代确认原因（留痕）',
  `approve_time`   DATETIME         NULL                COMMENT '确认时间',
  `create_time`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_bind_family` (`family_user_id`),
  KEY `idx_bind_profile` (`profile_id`),
  KEY `idx_bind_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='家属—老人绑定关系（申请确认状态机）';
-- 说明：同一对"家属-老人"不得存在两条 PENDING 或 APPROVED 记录，由业务层校验
--      （MySQL 无部分唯一索引；绑定上限 family_bind_max 存 sys_config，默认 5）


-- ---------- 4. care_relation 护工分配 ----------
CREATE TABLE `care_relation` (
  `id`           BIGINT   NOT NULL AUTO_INCREMENT COMMENT '主键',
  `care_user_id` BIGINT   NOT NULL                COMMENT '护工账号 ID（FK → user.id）',
  `profile_id`   BIGINT   NOT NULL                COMMENT '老人档案 ID（FK → elder_profile.id）',
  `status`       TINYINT  NOT NULL DEFAULT 1      COMMENT '状态：1 在管 / 0 已交接',
  `create_time`  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time`  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_care_user` (`care_user_id`),
  KEY `idx_care_profile` (`profile_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='护工—老人分配关系';


-- ---------- 5. health_record 健康指标统一表（DB-2） ----------
-- type 与 val1/val2 对应关系：
--   BLOOD_PRESSURE 血压  → val1=收缩压, val2=舒张压
--   BLOOD_SUGAR    血糖  → val1=血糖值
--   HEART_RATE     心率  → val1=心率
--   SLEEP          睡眠  → val1=时长(小时), val2=质量(1~5)
--   STEP           步数  → val1=步数
CREATE TABLE `health_record` (
  `id`          BIGINT        NOT NULL AUTO_INCREMENT COMMENT '主键',
  `profile_id`  BIGINT        NOT NULL                COMMENT '归属档案 ID（FK → elder_profile.id）',
  `type`        VARCHAR(20)   NOT NULL                COMMENT '指标类型：BLOOD_PRESSURE/BLOOD_SUGAR/HEART_RATE/SLEEP/STEP',
  `val1`        DECIMAL(10,2)     NULL                COMMENT '主值（收缩压/血糖/心率/睡眠时长/步数）',
  `val2`        DECIMAL(10,2)     NULL                COMMENT '次值（舒张压/睡眠质量）',
  `measured_at` DATETIME      NOT NULL                COMMENT '测量时间',
  `is_abnormal` TINYINT       NOT NULL DEFAULT 0      COMMENT '是否触发异常：0 否 / 1 是',
  `remark`      VARCHAR(255)      NULL                COMMENT '备注',
  `recorder_id` BIGINT            NULL                COMMENT '录入人 ID（本人/家属代录/护工，FK → user.id）',
  `create_time` DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_record_trend` (`profile_id`, `type`, `measured_at`),
  KEY `idx_record_measured` (`measured_at`),
  KEY `idx_record_recorder` (`recorder_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='健康指标统一记录表（type 区分指标）';


-- ---------- 6. health_warning 预警记录（D-04 / D-05） ----------
CREATE TABLE `health_warning` (
  `id`             BIGINT      NOT NULL AUTO_INCREMENT COMMENT '主键',
  `profile_id`     BIGINT      NOT NULL                COMMENT '归属档案 ID（FK → elder_profile.id）',
  `record_id`      BIGINT          NULL                COMMENT '触发记录 ID（FK → health_record.id）',
  `type`           VARCHAR(20) NOT NULL                COMMENT '指标类型',
  `value_text`     VARCHAR(50)     NULL                COMMENT '展示值（如 "178/102"）',
  `level`          TINYINT     NOT NULL                COMMENT '风险等级：0 正常 / 1 轻度 / 2 较高 / 3 高风险',
  `status`         VARCHAR(15) NOT NULL DEFAULT 'PENDING' COMMENT '处理状态（全局唯一）：PENDING/PROCESSING/RESOLVED/IGNORED',
  `trigger_source` VARCHAR(20)     NULL                COMMENT '触发来源：DATA_INPUT 录入 / AI_CHAT 咨询 / MANUAL 人工',
  `ai_summary`     TEXT            NULL                COMMENT 'AI 摘要（异步生成，允许为 NULL，D-04）',
  `summary_status` VARCHAR(10) NOT NULL DEFAULT 'PENDING' COMMENT '摘要状态：PENDING/SUCCESS/FAILED/SKIPPED',
  `create_time`    DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time`    DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_warning_profile_status` (`profile_id`, `status`),
  KEY `idx_warning_level` (`level`),
  KEY `idx_warning_record` (`record_id`),
  KEY `idx_warning_create` (`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='健康预警记录（处理状态 + AI 摘要）';


-- ---------- 7. alert_receiver 预警接收人（D-05 新增） ----------
-- 已读状态与预警处理状态正交：任一人点开只更新自己那条，不影响他人
CREATE TABLE `alert_receiver` (
  `id`          BIGINT      NOT NULL AUTO_INCREMENT COMMENT '主键',
  `warning_id`  BIGINT      NOT NULL                COMMENT '预警 ID（FK → health_warning.id）',
  `user_id`     BIGINT      NOT NULL                COMMENT '接收人 ID（家属/护工/老人，FK → user.id）',
  `read_status` VARCHAR(10) NOT NULL DEFAULT 'UNREAD' COMMENT '已读状态（每人独立）：UNREAD/READ',
  `read_time`   DATETIME        NULL                COMMENT '阅读时间',
  `create_time` DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_receiver_warning_user` (`warning_id`, `user_id`),
  KEY `idx_receiver_unread` (`user_id`, `read_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='预警接收人（每人一条，承载已读状态）';


-- ---------- 8. warning_handle_record 预警处理留痕 ----------
CREATE TABLE `warning_handle_record` (
  `id`          BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键',
  `warning_id`  BIGINT       NOT NULL                COMMENT '预警 ID（FK → health_warning.id）',
  `handler_id`  BIGINT       NOT NULL                COMMENT '处理人 ID（FK → user.id）',
  `action`      VARCHAR(20)  NOT NULL                COMMENT '处理方式：CONTACTED/ARRANGED_VISIT/SENT_HOSPITAL/OBSERVE',
  `result`      VARCHAR(500)     NULL                COMMENT '处理说明',
  `create_time` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间（处理时间）',
  `update_time` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_handle_warning` (`warning_id`),
  KEY `idx_handle_handler` (`handler_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='预警处理留痕';


-- ---------- 9. chat_session 咨询会话 ----------
CREATE TABLE `chat_session` (
  `id`          BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键（session_id）',
  `user_id`     BIGINT       NOT NULL                COMMENT '发起人 ID（FK → user.id）',
  `profile_id`  BIGINT           NULL                COMMENT '针对档案 ID（FK → elder_profile.id）',
  `title`       VARCHAR(100)     NULL                COMMENT '会话标题（可由首问生成）',
  `create_time` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_session_user` (`user_id`),
  KEY `idx_session_profile` (`profile_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='AI 咨询会话';


-- ---------- 10. chat_message 咨询消息 ----------
CREATE TABLE `chat_message` (
  `id`           BIGINT      NOT NULL AUTO_INCREMENT COMMENT '主键（message_id）',
  `session_id`   BIGINT      NOT NULL                COMMENT '所属会话 ID（FK → chat_session.id）',
  `role`         VARCHAR(10) NOT NULL                COMMENT '角色：user / assistant',
  `content`      TEXT        NOT NULL                COMMENT '消息内容',
  `intent`       VARCHAR(20)     NULL                COMMENT '意图：NORMAL/DATA/ABNORMAL/EMERGENCY',
  `agent`        VARCHAR(20)     NULL                COMMENT '执行 Agent：HEALTH/HEALTH_DATA/RISK/EMERGENCY',
  `safety_level` VARCHAR(5)      NULL                COMMENT '安全分级：L1~L4',
  `sources`      TEXT            NULL                COMMENT 'RAG 命中来源（JSON 数组）',
  `warning_id`   BIGINT          NULL                COMMENT '触发预警时关联的预警 ID（FK → health_warning.id）',
  `create_time`  DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time`  DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_message_session` (`session_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='AI 咨询消息（含意图/Agent/安全分级）';


-- ---------- 11. sys_config 系统配置 / 阈值（DB-1 配置化关键表） ----------
-- 阈值示例：config_key='BLOOD_PRESSURE_SYSTOLIC'
--          config_value='{"level0":"90~139","level1":"140~159","level2":"160~179","level3":">=180"}'
CREATE TABLE `sys_config` (
  `id`           BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键（config_id）',
  `config_key`   VARCHAR(50)  NOT NULL                COMMENT '配置键（唯一）',
  `config_value` VARCHAR(500) NOT NULL                COMMENT '配置值（阈值存 JSON）',
  `config_type`  VARCHAR(20)      NULL                COMMENT '类型：threshold/number/string/json',
  `group_name`   VARCHAR(50)      NULL                COMMENT '分组：threshold/system/notify…',
  `description`  VARCHAR(255)     NULL                COMMENT '说明',
  `enabled`      TINYINT      NOT NULL DEFAULT 1      COMMENT '是否启用：1 是 / 0 否',
  `create_time`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_config_key` (`config_key`),
  KEY `idx_config_group` (`group_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='系统配置与预警阈值（禁止硬编码）';


-- ============================================================
-- 二、选配表（4 张，本期可不实现）
-- ============================================================

-- ---------- 12. medication 用药信息【选配】 ----------
CREATE TABLE `medication` (
  `id`          BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键',
  `profile_id`  BIGINT       NOT NULL                COMMENT '归属档案 ID（FK → elder_profile.id）',
  `drug_name`   VARCHAR(100) NOT NULL                COMMENT '药品名称',
  `dosage`      VARCHAR(50)      NULL                COMMENT '剂量（如 "5mg 每日一次"）',
  `take_time`   VARCHAR(100)     NULL                COMMENT '服药时间（如 "08:00,20:00"）',
  `remark`      VARCHAR(255)     NULL                COMMENT '备注',
  `create_time` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_med_profile` (`profile_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='【选配】用药信息';


-- ---------- 13. knowledge_document 知识库文档【选配】 ----------
CREATE TABLE `knowledge_document` (
  `id`          BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键',
  `title`       VARCHAR(200) NOT NULL                COMMENT '标题',
  `category`    VARCHAR(50)      NULL                COMMENT '分类：高血压/糖尿病/心率异常/睡眠/老年运动/老年饮食/常见问题',
  `content`     MEDIUMTEXT       NULL                COMMENT '正文内容',
  `enabled`     TINYINT      NOT NULL DEFAULT 1      COMMENT '是否启用：1 是 / 0 否',
  `create_time` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_kdoc_category` (`category`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='【选配】知识库文档';


-- ---------- 14. knowledge_chunk 知识分块向量【选配】 ----------
CREATE TABLE `knowledge_chunk` (
  `id`          BIGINT   NOT NULL AUTO_INCREMENT COMMENT '主键',
  `doc_id`      BIGINT   NOT NULL                COMMENT '所属文档 ID（FK → knowledge_document.id）',
  `chunk_index` INT      NOT NULL DEFAULT 0      COMMENT '分块序号',
  `chunk_text`  TEXT     NOT NULL                COMMENT '文本块内容',
  `embedding`   JSON         NULL                COMMENT '向量（JSON 数组；生产环境建议用向量库 Chroma/FAISS 存储）',
  `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_kchunk_doc` (`doc_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='【选配】知识库分块与向量';


-- ---------- 15. ai_log AI 调用日志【选配】 ----------
CREATE TABLE `ai_log` (
  `id`          BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键',
  `user_id`     BIGINT           NULL                COMMENT '调用人 ID（可空；日志表不设外键以保留审计记录）',
  `agent`       VARCHAR(20)      NULL                COMMENT 'Agent：HEALTH/HEALTH_DATA/RISK/EMERGENCY/ALERT',
  `model`       VARCHAR(50)      NULL                COMMENT '模型标识（如 deepseek-chat）',
  `prompt_tokens`  INT           NULL                COMMENT '输入 token 数',
  `output_tokens`  INT           NULL                COMMENT '输出 token 数',
  `latency_ms`  INT              NULL                COMMENT '耗时（毫秒）',
  `success`     TINYINT      NOT NULL DEFAULT 1      COMMENT '是否成功：1 是 / 0 否（失败可用于说明降级设计，D-04）',
  `error_msg`   VARCHAR(500)     NULL                COMMENT '失败原因',
  `create_time` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_ailog_user` (`user_id`),
  KEY `idx_ailog_create` (`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='【选配】AI 调用日志';


-- ============================================================
-- 三、外键约束（建表后统一补充）
-- ============================================================
-- 说明：外键用于保证引用完整性；若后续分库或追求写入性能，可按需移除并改为应用层校验。

SET FOREIGN_KEY_CHECKS = 1;

ALTER TABLE `elder_profile`
  ADD CONSTRAINT `fk_profile_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE RESTRICT;

ALTER TABLE `family_bind`
  ADD CONSTRAINT `fk_bind_family`  FOREIGN KEY (`family_user_id`) REFERENCES `user` (`id`) ON DELETE RESTRICT,
  ADD CONSTRAINT `fk_bind_profile` FOREIGN KEY (`profile_id`)     REFERENCES `elder_profile` (`id`) ON DELETE RESTRICT;

ALTER TABLE `care_relation`
  ADD CONSTRAINT `fk_care_user`    FOREIGN KEY (`care_user_id`) REFERENCES `user` (`id`) ON DELETE RESTRICT,
  ADD CONSTRAINT `fk_care_profile` FOREIGN KEY (`profile_id`)   REFERENCES `elder_profile` (`id`) ON DELETE RESTRICT;

ALTER TABLE `health_record`
  ADD CONSTRAINT `fk_record_profile`  FOREIGN KEY (`profile_id`)  REFERENCES `elder_profile` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `fk_record_recorder` FOREIGN KEY (`recorder_id`) REFERENCES `user` (`id`) ON DELETE SET NULL;

ALTER TABLE `health_warning`
  ADD CONSTRAINT `fk_warning_profile` FOREIGN KEY (`profile_id`) REFERENCES `elder_profile` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `fk_warning_record`  FOREIGN KEY (`record_id`)  REFERENCES `health_record` (`id`) ON DELETE SET NULL;

ALTER TABLE `alert_receiver`
  ADD CONSTRAINT `fk_receiver_warning` FOREIGN KEY (`warning_id`) REFERENCES `health_warning` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `fk_receiver_user`    FOREIGN KEY (`user_id`)    REFERENCES `user` (`id`) ON DELETE CASCADE;

ALTER TABLE `warning_handle_record`
  ADD CONSTRAINT `fk_handle_warning` FOREIGN KEY (`warning_id`) REFERENCES `health_warning` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `fk_handle_handler` FOREIGN KEY (`handler_id`) REFERENCES `user` (`id`) ON DELETE RESTRICT;

ALTER TABLE `chat_session`
  ADD CONSTRAINT `fk_session_user`    FOREIGN KEY (`user_id`)    REFERENCES `user` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `fk_session_profile` FOREIGN KEY (`profile_id`) REFERENCES `elder_profile` (`id`) ON DELETE SET NULL;

ALTER TABLE `chat_message`
  ADD CONSTRAINT `fk_message_session` FOREIGN KEY (`session_id`) REFERENCES `chat_session` (`id`) ON DELETE CASCADE;

-- 【选配】表外键
ALTER TABLE `medication`
  ADD CONSTRAINT `fk_med_profile` FOREIGN KEY (`profile_id`) REFERENCES `elder_profile` (`id`) ON DELETE CASCADE;

ALTER TABLE `knowledge_chunk`
  ADD CONSTRAINT `fk_kchunk_doc` FOREIGN KEY (`doc_id`) REFERENCES `knowledge_document` (`id`) ON DELETE CASCADE;

-- ============================================================
-- 建表完成：15 张表（核心 11 + 选配 4）
-- 下一步：执行 init_data.sql 写入阈值配置、预置管理员与演示数据
-- ============================================================
