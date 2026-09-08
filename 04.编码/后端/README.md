# 后端 · 开发说明

归属：**丘宇乾**（全部后端代码，另两人不提交此目录任何改动）

---

## 技术栈（待确认）

| 项 | 选型 | 状态 |
|---|---|---|
| 主选 | Python 3.11 + FastAPI | 文档倾向方案，AI 生态友好 |
| 备选 | Java + SSM（Spring + SpringMVC + MyBatis） | ⚠️ 需老师确认是否强制 |
| 数据库 | MySQL 8 | 已定 |
| AI 编排 | LangChain / LangGraph | 已定 |
| 大模型 | DeepSeek / 通义千问 / GLM-4（三选一） | ⚠️ 待定 |
| 向量库 | Chroma 或 FAISS | 已定方向 |

> **重要**：若老师要求改用 Java SSM，本目录结构需整体调整，请在编码开始前（9/28 前）确认。
> 前端不受影响——前后端通过 HTTP 接口解耦，前端代码无需改动。

---

## 目录说明（按 FastAPI 规划）

```
app/
├── main.py       应用入口
├── core/         配置、安全、数据库连接
├── models/       数据模型（ORM）
├── api/          路由层（对应前端 api/ 的接口）
├── services/     业务逻辑（档案、指标、预警、通知）
└── agent/        LangGraph Agent 编排
    ├── intent.py      意图识别路由
    ├── health.py      Health Agent（RAG 检索）
    ├── health_data.py Health Data Agent（查库 + 趋势）
    ├── risk.py        Risk Agent（风险分级 + 预警）
    ├── emergency.py   Emergency Agent（紧急处理）
    └── alert.py       Alert Agent（后台守护检测）
```

---

## 环境配置（红线）

1. **API Key 只存 `.env`，绝不进代码、绝不进前端**
2. `.env` 已在 `.gitignore` 中，不会被提交
3. 提交代码前务必 `git status` 确认 `.env` 未被追踪
4. 仓库内提供 `.env.example` 作为模板，只写变量名不写值

```bash
cp .env.example .env   # 复制后填入自己的 Key
```

---

## 本地启动（FastAPI）

```bash
cd 04.编码/后端
python -m venv .venv
.venv/Scripts/activate        # Windows
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
uvicorn app.main:app --reload
```

接口文档自动生成：<http://127.0.0.1:8000/docs>

---

## 开发约定

1. 接口实现严格对齐 `03.概要设计/API接口契约_康养系统_v0.1.md`，变更先改契约文档
2. 预警阈值等配置项一律从 `sys_config` 表读取，**不在代码中硬编码**
3. 所有 AI 调用必须带安全分级（L1~L4）处理与敏感词兜底
4. 涉及他人接口变更时，在群里同步，避免前端白等
