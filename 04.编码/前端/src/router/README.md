# 路由分文件规则（必读）

本目录是**冲突最高发**的区域，请务必按规则操作。

## 问题

三个人各做各的页面，如果都往 `index.js` 里加路由，那么**每新增一个页面就会冲突一次**。
因为 Git 判断冲突的单位是"文件的同一处"，三人同时改同一个文件的末尾，必然撞车。

## 规则

`index.js` **只准写 import，不准写任何具体路由配置**。

每人只在自己的路由文件里添加路由：

| 文件 | 归属人 | 内容 |
|---|---|---|
| elder.js | 梁霁鸣 | 老人端路由 |
| family.js | 梁霁鸣 | 家属端路由 |
| care.js | 周彦龙 | 护工端路由 |
| admin.js | 周彦龙 | 管理端路由 |
| index.js | 梁霁鸣（初始化一次后基本不再改） | 仅做汇总 import |

## index.js 应当长成这样

```js
import { createRouter, createWebHistory } from 'vue-router'
import elderRoutes from './elder'
import familyRoutes from './family'
import careRoutes from './care'
import adminRoutes from './admin'

const routes = [
  ...elderRoutes,
  ...familyRoutes,
  ...careRoutes,
  ...adminRoutes,
]

const router = createRouter({ history: createWebHistory(), routes })
export default router
```

**注意**：上面这个文件建好之后，正常情况下三个人都不需要再改它。

## 自己的路由文件示例（elder.js）

```js
export default [
  { path: '/elder', name: 'ElderHome', component: () => import('../views/elder/Home.vue') },
  { path: '/elder/ai', name: 'ElderAI', component: () => import('../views/elder/AIConsult.vue') },
]
```

这样梁霁鸣改 elder.js、周彦龙改 care.js，两人同时提交也不会冲突。
