# 前端真实浏览器联调记录

2026-10-08，在实际 Chrome 无头浏览器中访问 Vite 5174，代理到 FastAPI 8002。后端仅连接隔离 SQLite；没有写入用户 MySQL，没有调用真实模型。四角色分别使用演示初始化工具创建的独立账号。图片、JSON记录为实际执行结果。

| 脚本 | 已通过检查 | 验证内容 |
|---|---:|---|
| full-browser-smoke.cjs | 21 | 四角色页面、隐私授权、老人血压录入触发预警、家属通知/处理和记录、AI不可用保留输入、跨角色与过期登录 |
| mutation-smoke.cjs | 12 | 创建/启禁/角色维护、知识增改删与重建、阈值错误拒绝/保存、指标保存、网络失败提示 |
| multi-profile-smoke.cjs | 5 | 老人多档案、家属和护工授权代建、关系隔离403、管理员代建 |
| final-fields-smoke.cjs | 4 | 七类知识下拉及真实保存、护工测量区间筛选、统计canvas渲染 |
| status-tags-smoke.cjs | 3 | 护工异常与已处理标签、中文已读状态，更新当前截图 |
| anonymous-smoke.cjs / chart-smoke.cjs | 独立验证 | 匿名路由保护、登录页、实际图表与控制台 |

所有结果中的 `page_errors` 均须为空。管理写入测试的控制台记录包含特意触发的400与网络中断，属于预期错误；没有以空数据或成功提示掩盖失败。构建通过不能替代上述浏览器验证，也不证明真实模型的回答质量或生产MySQL业务写入。

## 复现

需要先安装后端依赖和前端依赖。下面路径在本项目根目录执行；端口8002与5174只用于隔离测试。所有测试账户的演示密码由后端 `scripts.seed --demo` 产生，不能使用在生产部署中。

先开终端一，仅给当前进程设置环境：

```powershell
$env:DATABASE_URL = 'sqlite:///D:/Desktop/康养系统实训项目/04.编码/前端/qa/config.local.browser-test.db'
$env:JWT_SECRET = 'browser-only-test-secret-over-32-characters'
$env:CHROMA_PATH = 'D:/Desktop/康养系统实训项目/04.编码/前端/qa/config.local.vector-test'
$env:VECTOR_STORE_PATH = $env:CHROMA_PATH
$env:DEEPSEEK_API_KEY = ''
$env:QWEN_API_KEY = ''
$env:GLM_API_KEY = ''
$env:LLM_API_KEY = ''
$env:DASHSCOPE_API_KEY = ''
$env:ZHIPU_API_KEY = ''
cd 04.编码/后端
.venv/Scripts/python.exe -m scripts.seed --demo
.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8002
```

终端二在项目根目录执行：

```powershell
$env:VITE_BACKEND_URL = 'http://127.0.0.1:8002'
npm.cmd --prefix 04.编码/前端 run dev -- --host 127.0.0.1 --port 5174 --strictPort
```

测试使用Playwright及本机Chrome。当前Codex运行时已自带Playwright，终端三可执行：

```powershell
$env:NODE_PATH = 'C:/Users/qiuyu/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules'
node.exe 05.集成测试/前端浏览器/anonymous-smoke.cjs
node.exe 05.集成测试/前端浏览器/full-browser-smoke.cjs
node.exe 05.集成测试/前端浏览器/mutation-smoke.cjs
node.exe 05.集成测试/前端浏览器/multi-profile-smoke.cjs
node.exe 05.集成测试/前端浏览器/final-fields-smoke.cjs
node.exe 05.集成测试/前端浏览器/status-tags-smoke.cjs
```

脚本以自身目录为输出目录，可从项目根运行。重新执行会对隔离测试库增加记录；结果截图数值随测试记录变化。SQLite和向量缓存均按仓库已有 `config.local.*` 规则忽略，无需修改 `.gitignore`。本版未对短信、语音、PDF等选配能力做接入验收。
