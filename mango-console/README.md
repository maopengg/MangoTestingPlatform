## 芒果测试平台前端（mango-console）

`mango-console` 是芒果测试平台的 Web 管理控制台，基于 **Vue 3 + TypeScript** 构建，使用 **Arco Design** 等组件库，提供接口测试、UI 测试、Pytest、性能测试、定时任务、预警监控等模块的可视化管理能力。

### 核心功能

- **首页与概览**：平台运行数据总览、统计图表。
- **接口测试（apitest）**：接口信息管理、用例配置、参数化、断言、执行记录等。
- **UI 测试（uitest）**：页面 / 元素管理、用例步骤编排、执行记录查看。
- **Pytest 管理（pytest）**：Pytest 用例、执行记录、报告展示。
- **性能测试（perf）**：性能任务配置与结果查看。
- **系统配置（system / config）**：项目 / 产品、模块、计划任务、通知组等基础配置。
- **预警监控（monitoring）**：
  - 监控任务管理（脚本运行器）：创建 / 编辑 / 启停 / 实时查看日志。
  - 预警监控报告：报告列表、状态筛选、统计卡片、详情查看。
- **用户与权限**：登录、角色、用户管理、操作日志等。

### 技术栈与结构

- **主要技术**：
  - Vue 3 + TypeScript
  - Vite 构建工具
  - Arco Design Vue 组件库
  - Pinia 状态管理
  - Axios 请求封装
  - ECharts 图表展示

- **目录结构（部分）**：
  - `src/`
    - `api/`：后端接口封装（按业务模块拆分，如 `monitoring/task.ts`、`monitoring/report.ts`、`system/*` 等）。
    - `components/`：通用组件（表格封装、弹窗、代码编辑器、图表组件等）。
    - `views/`：业务页面：
      - `monitoring/`：脚本运行器 & 预警监控报告页面。
      - `apitest/`、`uitest/`、`pytest/`、`perf/` 等。
    - `router/`：路由与守卫（权限、页面重载、缓存等）。
    - `store/`：Pinia 状态管理（枚举、项目、用户信息等）。
    - `styles/`：全局样式与主题配置。
    - `setting/`：前端配置（如枚举字段名映射等）。
  - `vite.config.ts`：Vite 配置。
  - `package.json` / `package-lock.json`：前端依赖与脚本。
  - `Dockerfile`：前端构建与部署容器配置。

### 部署与安装文档

前端 `mango-console` 的 Node 版本要求、依赖安装、环境配置、启动命令、构建与部署流程等内容，请统一参考官方部署教程：

- [Windows 部署教程（包含前端部署）](http://43.142.161.61:8002/pages/%E9%83%A8%E7%BD%B2%E6%95%99%E7%A8%8B/windows.html)


