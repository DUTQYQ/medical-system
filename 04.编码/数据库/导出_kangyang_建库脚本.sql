-- MySQL dump 10.13  Distrib 8.0.42, for Win64 (x86_64)
--
-- Host: localhost    Database: kangyang
-- ------------------------------------------------------
-- Server version	8.0.42

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Current Database: `kangyang`
--

CREATE DATABASE /*!32312 IF NOT EXISTS*/ `kangyang` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;

USE `kangyang`;

--
-- Table structure for table `ai_log`
--

DROP TABLE IF EXISTS `ai_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ai_log` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `user_id` bigint DEFAULT NULL COMMENT '调用人 ID（FK → user.id）',
  `agent` varchar(20) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT 'Agent：HEALTH/HEALTH_DATA/RISK/EMERGENCY/ALERT',
  `model` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '模型标识（如 deepseek-chat）',
  `prompt_tokens` int DEFAULT NULL COMMENT '输入 token 数',
  `output_tokens` int DEFAULT NULL COMMENT '输出 token 数',
  `latency_ms` int DEFAULT NULL COMMENT '耗时（毫秒）',
  `success` tinyint NOT NULL DEFAULT '1' COMMENT '是否成功：1 是 / 0 否（失败可用于说明降级设计，D-04）',
  `error_msg` varchar(500) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '失败原因',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_ailog_user` (`user_id`),
  KEY `idx_ailog_create` (`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='【选配】AI 调用日志';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `alert_receiver`
--

DROP TABLE IF EXISTS `alert_receiver`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `alert_receiver` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `warning_id` bigint NOT NULL COMMENT '预警 ID（FK → health_warning.id）',
  `user_id` bigint NOT NULL COMMENT '接收人 ID（家属/护工/老人，FK → user.id）',
  `read_status` varchar(10) COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'UNREAD' COMMENT '已读状态（每人独立）：UNREAD/READ',
  `read_time` datetime DEFAULT NULL COMMENT '阅读时间',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_receiver_warning_user` (`warning_id`,`user_id`),
  KEY `idx_receiver_unread` (`user_id`,`read_status`),
  CONSTRAINT `fk_receiver_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_receiver_warning` FOREIGN KEY (`warning_id`) REFERENCES `health_warning` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=70005 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='预警接收人（每人一条，承载已读状态）';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `care_relation`
--

DROP TABLE IF EXISTS `care_relation`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `care_relation` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `care_user_id` bigint NOT NULL COMMENT '护工账号 ID（FK → user.id）',
  `profile_id` bigint NOT NULL COMMENT '老人档案 ID（FK → elder_profile.id）',
  `status` tinyint NOT NULL DEFAULT '1' COMMENT '状态：1 在管 / 0 已交接',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_care_user` (`care_user_id`),
  KEY `idx_care_profile` (`profile_id`),
  CONSTRAINT `fk_care_profile` FOREIGN KEY (`profile_id`) REFERENCES `elder_profile` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_care_user` FOREIGN KEY (`care_user_id`) REFERENCES `user` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=8002 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='护工—老人分配关系';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `chat_message`
--

DROP TABLE IF EXISTS `chat_message`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `chat_message` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键（message_id）',
  `session_id` bigint NOT NULL COMMENT '所属会话 ID（FK → chat_session.id）',
  `role` varchar(10) COLLATE utf8mb4_general_ci NOT NULL COMMENT '角色：user / assistant',
  `content` text COLLATE utf8mb4_general_ci NOT NULL COMMENT '消息内容',
  `intent` varchar(20) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '意图：NORMAL/DATA/ABNORMAL/EMERGENCY',
  `agent` varchar(20) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '执行 Agent：HEALTH/HEALTH_DATA/RISK/EMERGENCY',
  `safety_level` varchar(5) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '安全分级：L1~L4',
  `sources` text COLLATE utf8mb4_general_ci COMMENT 'RAG 命中来源（JSON 数组）',
  `warning_id` bigint DEFAULT NULL COMMENT '触发预警时关联的预警 ID（FK → health_warning.id）',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_message_session` (`session_id`),
  CONSTRAINT `fk_message_session` FOREIGN KEY (`session_id`) REFERENCES `chat_session` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='AI 咨询消息（含意图/Agent/安全分级）';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `chat_session`
--

DROP TABLE IF EXISTS `chat_session`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `chat_session` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键（session_id）',
  `user_id` bigint NOT NULL COMMENT '发起人 ID（FK → user.id）',
  `profile_id` bigint DEFAULT NULL COMMENT '针对档案 ID（FK → elder_profile.id）',
  `title` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '会话标题（可由首问生成）',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_session_user` (`user_id`),
  KEY `idx_session_profile` (`profile_id`),
  CONSTRAINT `fk_session_profile` FOREIGN KEY (`profile_id`) REFERENCES `elder_profile` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_session_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='AI 咨询会话';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `elder_profile`
--

DROP TABLE IF EXISTS `elder_profile`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `elder_profile` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `user_id` bigint NOT NULL COMMENT '归属账号 ID（FK → user.id）',
  `name` varchar(50) COLLATE utf8mb4_general_ci NOT NULL COMMENT '姓名',
  `gender` char(1) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '性别：M 男 / F 女',
  `birthday` date DEFAULT NULL COMMENT '出生日期',
  `height` decimal(5,1) DEFAULT NULL COMMENT '身高 cm',
  `weight` decimal(5,1) DEFAULT NULL COMMENT '体重 kg',
  `blood_type` varchar(5) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '血型',
  `allergy` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '过敏史',
  `medical_history` varchar(500) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '既往病史',
  `chronic_tags` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '慢病标签（JSON 数组，如 ["高血压","糖尿病"]）',
  `emergency_contact` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '紧急联系人姓名（仅展示/人工联系依据，D-03）',
  `emergency_phone` varchar(20) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '紧急联系人电话（仅展示/人工联系依据，D-03）',
  `deleted` tinyint NOT NULL DEFAULT '0' COMMENT '软删除：0 正常 / 1 已删除',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_profile_user` (`user_id`),
  KEY `idx_profile_deleted` (`deleted`),
  CONSTRAINT `fk_profile_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=2002 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='老人健康档案';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `family_bind`
--

DROP TABLE IF EXISTS `family_bind`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `family_bind` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键（bind_id）',
  `family_user_id` bigint NOT NULL COMMENT '家属账号 ID（FK → user.id）',
  `profile_id` bigint NOT NULL COMMENT '老人档案 ID（FK → elder_profile.id）',
  `relation` varchar(20) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '亲属关系：儿子/女儿/配偶…',
  `note` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '申请备注',
  `status` varchar(10) COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'PENDING' COMMENT '状态：PENDING/APPROVED/REJECTED/REVOKED',
  `approved_by` bigint DEFAULT NULL COMMENT '确认人 ID（代确认时记录操作人，本人确认为本人）',
  `approve_note` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '代确认原因（留痕）',
  `approve_time` datetime DEFAULT NULL COMMENT '确认时间',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_bind_family` (`family_user_id`),
  KEY `idx_bind_profile` (`profile_id`),
  KEY `idx_bind_status` (`status`),
  CONSTRAINT `fk_bind_family` FOREIGN KEY (`family_user_id`) REFERENCES `user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_bind_profile` FOREIGN KEY (`profile_id`) REFERENCES `elder_profile` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=9002 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='家属—老人绑定关系（申请确认状态机）';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `health_record`
--

DROP TABLE IF EXISTS `health_record`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `health_record` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `profile_id` bigint NOT NULL COMMENT '归属档案 ID（FK → elder_profile.id）',
  `type` varchar(20) COLLATE utf8mb4_general_ci NOT NULL COMMENT '指标类型：BLOOD_PRESSURE/BLOOD_SUGAR/HEART_RATE/SLEEP/STEP',
  `val1` decimal(10,2) DEFAULT NULL COMMENT '主值（收缩压/血糖/心率/睡眠时长/步数）',
  `val2` decimal(10,2) DEFAULT NULL COMMENT '次值（舒张压/睡眠质量）',
  `measured_at` datetime NOT NULL COMMENT '测量时间',
  `is_abnormal` tinyint NOT NULL DEFAULT '0' COMMENT '是否触发异常：0 否 / 1 是',
  `remark` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `recorder_id` bigint DEFAULT NULL COMMENT '录入人 ID（本人/家属代录/护工，FK → user.id）',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_record_trend` (`profile_id`,`type`,`measured_at`),
  KEY `idx_record_measured` (`measured_at`),
  KEY `fk_record_recorder` (`recorder_id`),
  CONSTRAINT `fk_record_profile` FOREIGN KEY (`profile_id`) REFERENCES `elder_profile` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_record_recorder` FOREIGN KEY (`recorder_id`) REFERENCES `user` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=30009 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='健康指标统一记录表（type 区分指标）';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `health_warning`
--

DROP TABLE IF EXISTS `health_warning`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `health_warning` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `profile_id` bigint NOT NULL COMMENT '归属档案 ID（FK → elder_profile.id）',
  `record_id` bigint DEFAULT NULL COMMENT '触发记录 ID（FK → health_record.id）',
  `type` varchar(20) COLLATE utf8mb4_general_ci NOT NULL COMMENT '指标类型',
  `value_text` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '展示值（如 "178/102"）',
  `level` tinyint NOT NULL COMMENT '风险等级：0 正常 / 1 轻度 / 2 较高 / 3 高风险',
  `status` varchar(15) COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'PENDING' COMMENT '处理状态（全局唯一）：PENDING/PROCESSING/RESOLVED/IGNORED',
  `trigger_source` varchar(20) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '触发来源：DATA_INPUT 录入 / AI_CHAT 咨询 / MANUAL 人工',
  `ai_summary` text COLLATE utf8mb4_general_ci COMMENT 'AI 摘要（异步生成，允许为 NULL，D-04）',
  `summary_status` varchar(10) COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'PENDING' COMMENT '摘要状态：PENDING/SUCCESS/FAILED/SKIPPED',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_warning_profile_status` (`profile_id`,`status`),
  KEY `idx_warning_level` (`level`),
  KEY `idx_warning_record` (`record_id`),
  KEY `idx_warning_create` (`create_time`),
  CONSTRAINT `fk_warning_profile` FOREIGN KEY (`profile_id`) REFERENCES `elder_profile` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_warning_record` FOREIGN KEY (`record_id`) REFERENCES `health_record` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=40002 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='健康预警记录（处理状态 + AI 摘要）';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `knowledge_chunk`
--

DROP TABLE IF EXISTS `knowledge_chunk`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `knowledge_chunk` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `doc_id` bigint NOT NULL COMMENT '所属文档 ID（FK → knowledge_document.id）',
  `chunk_index` int NOT NULL DEFAULT '0' COMMENT '分块序号',
  `chunk_text` text COLLATE utf8mb4_general_ci NOT NULL COMMENT '文本块内容',
  `embedding` json DEFAULT NULL COMMENT '向量（JSON 数组；生产环境建议用向量库 Chroma/FAISS 存储）',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_kchunk_doc` (`doc_id`),
  CONSTRAINT `fk_kchunk_doc` FOREIGN KEY (`doc_id`) REFERENCES `knowledge_document` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='【选配】知识库分块与向量';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `knowledge_document`
--

DROP TABLE IF EXISTS `knowledge_document`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `knowledge_document` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `title` varchar(200) COLLATE utf8mb4_general_ci NOT NULL COMMENT '标题',
  `category` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '分类：高血压/糖尿病/心率异常/睡眠/老年运动/老年饮食/常见问题',
  `content` mediumtext COLLATE utf8mb4_general_ci COMMENT '正文内容',
  `enabled` tinyint NOT NULL DEFAULT '1' COMMENT '是否启用：1 是 / 0 否',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_kdoc_category` (`category`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='【选配】知识库文档';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `medication`
--

DROP TABLE IF EXISTS `medication`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `medication` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `profile_id` bigint NOT NULL COMMENT '归属档案 ID（FK → elder_profile.id）',
  `drug_name` varchar(100) COLLATE utf8mb4_general_ci NOT NULL COMMENT '药品名称',
  `dosage` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '剂量（如 "5mg 每日一次"）',
  `take_time` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '服药时间（如 "08:00,20:00"）',
  `remark` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_med_profile` (`profile_id`),
  CONSTRAINT `fk_med_profile` FOREIGN KEY (`profile_id`) REFERENCES `elder_profile` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='【选配】用药信息';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sys_config`
--

DROP TABLE IF EXISTS `sys_config`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sys_config` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键（config_id）',
  `config_key` varchar(50) COLLATE utf8mb4_general_ci NOT NULL COMMENT '配置键（唯一）',
  `config_value` varchar(500) COLLATE utf8mb4_general_ci NOT NULL COMMENT '配置值（阈值存 JSON）',
  `config_type` varchar(20) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '类型：threshold/number/string/json',
  `group_name` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '分组：threshold/system/notify…',
  `description` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '说明',
  `enabled` tinyint NOT NULL DEFAULT '1' COMMENT '是否启用：1 是 / 0 否',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_config_key` (`config_key`),
  KEY `idx_config_group` (`group_name`)
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='系统配置与预警阈值（禁止硬编码）';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user`
--

DROP TABLE IF EXISTS `user`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `phone` varchar(20) COLLATE utf8mb4_general_ci NOT NULL COMMENT '手机号（登录名）',
  `password_hash` varchar(100) COLLATE utf8mb4_general_ci NOT NULL COMMENT '密码（bcrypt 加密，禁明文）',
  `name` varchar(50) COLLATE utf8mb4_general_ci NOT NULL COMMENT '姓名',
  `role` varchar(10) COLLATE utf8mb4_general_ci NOT NULL COMMENT '角色：ELDER/FAMILY/CARE/ADMIN',
  `status` tinyint NOT NULL DEFAULT '1' COMMENT '状态：1 启用 / 0 禁用（禁用后 Token 立即失效）',
  `avatar` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '头像 URL（本期不做上传）',
  `last_login_time` datetime DEFAULT NULL COMMENT '最近登录时间',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_phone` (`phone`),
  KEY `idx_user_role` (`role`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='用户主表（四类角色）';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `warning_handle_record`
--

DROP TABLE IF EXISTS `warning_handle_record`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `warning_handle_record` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `warning_id` bigint NOT NULL COMMENT '预警 ID（FK → health_warning.id）',
  `handler_id` bigint NOT NULL COMMENT '处理人 ID（FK → user.id）',
  `action` varchar(20) COLLATE utf8mb4_general_ci NOT NULL COMMENT '处理方式：CONTACTED/ARRANGED_VISIT/SENT_HOSPITAL/OBSERVE',
  `result` varchar(500) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '处理说明',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间（处理时间）',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_handle_warning` (`warning_id`),
  KEY `idx_handle_handler` (`handler_id`),
  CONSTRAINT `fk_handle_handler` FOREIGN KEY (`handler_id`) REFERENCES `user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_handle_warning` FOREIGN KEY (`warning_id`) REFERENCES `health_warning` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='预警处理留痕';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping routines for database 'kangyang'
--
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-09-15 10:19:51
