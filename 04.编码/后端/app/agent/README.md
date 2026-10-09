# AI 实现与验证边界

咨询请求字段为 `question`。LangGraph 按四类意图选择独立数据路径，模型只接收文本；认证、权限、阈值、预警和写库由 Python 代码完成。

`NORMAL` 仅检索知识库；`DATA` 读取当前授权档案的真实指标；`ABNORMAL` 读取具体预警与近 7 天指标；紧急关键词命中后直接落预警、写接收人并显示求助提示，不等待模型。原有 MySQL 配置中的“胸痛”“呼吸困难”等词会匹配对应日常说法。

## 【核心】RAG 向量链路

默认 `EMBEDDING_PROVIDER=hash` 使用 512 维字形 n-gram 哈希向量，再以 Chroma 余弦距离取 Top-K。此模式可离线运行，无模型下载；属于词形检索，不能作为中文语义召回效果已验收的证据。接口明确返回 `semantic_embedding=false`。

Chroma 默认目录 `config.local.chroma` 被现有 Git 忽略规则覆盖。可用 `VECTOR_STORE_PATH` 或 `CHROMA_PATH` 指定目录，用 `RAG_TOP_K` 控制召回数量。知识修改、删除和禁用均触发重建；检索前校验当前启用文档的指纹，避免返回已撤下正文。

## 【核心】本地语义向量配置路径

系统提供 `sentence-transformers` 适配器，只有在可选依赖及完整本地模型已经存在时才加载。当前项目虚拟环境没有安装该依赖，也没有验证真实语义模型；不会自动安装依赖、下载模型或调用付费 API。

准备好本地模型后，可在后端 `.env` 设置：

```dotenv
EMBEDDING_PROVIDER=sentence-transformers
EMBEDDING_MODEL_PATH=D:/local-models/bge-small-zh-v1.5
```

路径必须是已存在的 SentenceTransformer 模型目录，并包含 `modules.json`。加载固定采用 `device=cpu`、`local_files_only=true`、`trust_remote_code=false`；依赖或文件不足时明确返回 `3001`，不会切回哈希向量并假装语义检索成功。不同模型使用独立 Chroma 集合，避免向量维度混用。启用后应执行管理员索引重建，再使用真实健康语料测试语义近义表达的召回效果。

使用方式依据 [SentenceTransformer 官方 API 文档](https://sbert.net/docs/package_reference/sentence_transformer/model.html)。

## 测试边界

测试中的模型回复由单测显式注入 stub，前端默认没有 mock 或伪造模型回答。缺 Key 返回 `3001`；外部模型未进行在线验收。语义模型适配器通过离线假模块验证加载参数和隔离逻辑，不能视为真实模型质量验证。

`data/knowledge_seed.json` 提供七个既定分类各一条基础科普，正文为 WHO、NHS 官方原始资料的短改写，带官方链接、来源日期、2026-10-08 检索日期与免责声明。内容覆盖血压测量、血糖管理、心悸求助信号、睡眠习惯、身体活动、均衡饮食及单次血压读数的解释边界；不提供诊断、个体运动处方或调整药物剂量。

在后端目录运行 `python -m scripts.import_knowledge` 仅预览当前数据库缺少哪些条目。明确需要追加时运行 `python -m scripts.import_knowledge --apply`，使用 `.env` 的 `DATABASE_URL` 已有表，追加缺失条目并重建索引；不会建表、执行数据库 SQL 文件、覆盖管理员编辑内容或重新启用已禁用条目。`python -m scripts.seed --demo` 只允许独立 SQLite 演示库，并自动导入此语料。当前已有 MySQL 的知识库是否完成导入需要另行核实，提供文件不能视作已写入当前数据库。

检索测试以该真实来源语料验证七类具体问题的 Top-3 词形召回，并验证重复导入保留原文、禁用状态与默认预览不写库。七条起始语料不代表完整疾病知识库，词形测试也不代表中文近义表达的语义召回已经验收。
