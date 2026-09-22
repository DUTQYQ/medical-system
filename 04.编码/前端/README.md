# 前端 · Vue 3 开发说明

归属：**梁霁鸣**（主）· 周彦龙（护工端 / 管理端页面）· 丘宇乾（api 接口层）

---

## 技术栈

| 项 | 选型 |
|---|---|
| 框架 | Vue 3（组合式 API） |
| UI 组件 | Element Plus |
| 图表 | ECharts（健康趋势图） |
| 构建 | Vite |
| HTTP | Axios（统一封装在 src/utils/request.js） |
| 语音 | Web Speech API（【选配】STT / TTS，浏览器原生零成本） |

---

## 启动方式

```bash
cd 04.编码/前端
npm install
npm run dev
```

> 依赖安装走国内镜像：`npm config set registry https://registry.npmmirror.com`

---

## 目录说明

```
src/
├── api/          接口定义（丘宇乾维护，他人只读）
├── router/       路由，分文件：index.js 只写 import
├── views/
│   ├── elder/    老人端页面（梁霁鸣）
│   ├── family/   家属端页面（梁霁鸣）
│   ├── care/     护工端页面（周彦龙）
│   └── admin/    管理员页面（周彦龙）
├── components/   公共组件，按端建子目录
├── utils/        工具函数（梁霁鸣维护）
└── styles/       全局样式（梁霁鸣维护）
```

详细归属见 `../OWNERS.md`。

---

## 开发约定（务必遵守）

1. **接口只走 api 层**：页面里不要手写 `axios.get(...)`，统一调用 `src/api/` 暴露的函数
2. **路由分文件**：只在自己的 `router/xxx.js` 里加路由，不要改 `router/index.js`
3. **不适老化不提交**：老人端页面字号 ≥18px、主按钮 ≥48px、主流程 ≤3 步
4. **免责声明**：AI 相关页面底部固定"内容仅供参考，不构成医疗诊断"
5. **阈值不写死**：健康指标正常范围一律调用后端接口获取，不在前端写死常量
6. **API Key 绝不出现在前端**：这是硬性红线，违规会被老师直接打回

---

## 与后端联调

后端接口契约见 `03.概要设计/API接口契约_康养系统_v0.2.md`。

后端尚未完成时，前端按契约用 mock 数据开发，不要停下来干等。

---

## 当前实现状态（2026-09-21）

- **老人端 + 家属端 + 公共/认证 共 22 个页面已完成**（含 3 个选配页），`npm run build` 通过。
- `src/api/` 当前为**内存态 mock 实现**（后端未完成）：数据源与逻辑集中在 `src/api/mock.js`，各域文件（auth/profile/health/ai/alert/family/config/notification）按契约暴露同名函数；约定「成功 resolve 出 `data`、失败 `throw { code, message }`」。后端完成后把各函数内部的 mock 调用替换为 `request.get/post` 即可，页面代码无需改动。

### 演示账号（mock 阶段密码任意）

| 角色 | 手机号 | 姓名 |
| --- | --- | --- |
| 老人端 | `13000000002` | 张桂兰 |
| 家属端 | `13000000003` | 李强 |

