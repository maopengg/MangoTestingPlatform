# AGENTS.md

本文件是 `mango-console/` 前端开发约束。更完整规范见 `docs/前端统一规则规范.md`。

## 项目定位

- Vue 3 + TypeScript + Vite + Arco Design + Pinia。
- 后台测试平台，优先服务扫描、排查、配置和连续操作。
- 风格要求：企业级、数据密集、紧凑、干净统一。
- 不改接口、路由、权限和业务数据结构，除非任务明确要求。

## 常用命令

```bash
npm run dev
npm run build:dev
npm run tsc
npm run theme:audit
```

- 未明确要求时，不启动或占用 `5173`。
- 样式/组件改造后优先跑 `npm run theme:audit`。
- 阶段验收或构建风险时跑 `npm run build:dev`。
- `npm run tsc` 可能有历史全量类型问题，需区分是否由本次改动引入。

## 主题与样式

- 样式优先使用 `--m-*` token。
- 不新增硬编码颜色、`--color-*`、`--primary-*`。
- 全局自定义 class 必须使用 `mango-` 前缀。
- 第三方选择器可保留原名：`.arco-*`、`.cm-*`、`.el-*`。
- 状态色使用 `--m-success`、`--m-danger`、`--m-warning`。
- 避免高饱和大面积背景，状态背景使用弱化表达。
- 允许例外：代码高亮、图表 fallback、业务枚举色、图片/图标原色。

## 页面骨架

- 列表页优先使用 `TableBody + TableHeader + TableFooter`。
- 详情页优先使用 `mango-detail-toolbar + mango-detail-workbench`。
- 配置区优先使用 `mango-section-card + mango-section-title + mango-soft-panel`。
- 页面不要贴边，也不要做营销式大留白。
- 长文本必须省略、tooltip 或进入详情。
- 宽内容只允许在表格、代码面板、画布内部滚动。

## 表格

- 表格默认无重边框、紧凑行高、表头弱底色、hover 轻提示。
- 操作列固定右侧，宽度统一 `170`。
- 操作列统一使用 `MangoTableActions`。
- `MangoTableActions` 默认展示 2 个操作，超出进“更多”。
- 删除/移除/清理必须 `danger: true`。
- 表格内执行、调试保持文本按钮；表格外主执行按钮才用成功绿色。
- 长字段必须 `ellipsis: true`、`tooltip: true`。
- 固定操作列时必须设置 `scroll.x`。
- 除非明确需要，不固定名称列。

## 表单与搜索

- 搜索区由 `TableHeader` 控制。
- 搜索 label 固定宽度，保证多行对齐。
- 不在页面内散写控件宽度。
- 必填标识使用 `mango-form-item__require`。
- 说明文案用 `--m-muted`，错误提示用 `--m-danger`。

## 弹窗与抽屉

- 普通 `a-modal` footer 按钮统一靠右。
- `Modal.confirm` 的取消/删除按钮统一靠右。
- `ModalDialog` footer 使用 `mango-modal-dialog-footer-actions`。
- 页面局部样式不允许把 `.arco-modal-footer` 改成居中或靠左。
- 右侧抽屉 `a-drawer` 不跟随弹窗规则，footer 保持左下角。
- 抽屉内容区可滚动，footer 固定。
- 大 JSON/大文本编辑使用公共编辑抽屉。

## 详情、代码与图表

- 子详情页不要重复展示父列表已有基础信息块。
- 详情页标题使用轻量 toolbar 风格，可带 ID + 名称。
- JSON 展示默认只展开第一层；响应头等低价值内容可默认收起。
- Python/代码展示使用 PyCharm 风格 token。
- 日志、堆栈、代码块统一走 `mango-code-panel` 或现有代码组件。
- 图表使用 `--m-chart-1` 到 `--m-chart-5`。
- 流程图节点颜色必须有清晰含义，避免误导用户。

## 公共组件优先

- 新增公共组件按用途放入 `actions/display/editors/feedback/forms/overlays/reports/table` 等子目录。
- 表格操作列：`components/table/MangoTableActions.vue`。
- JSON 大编辑：`components/editors/MangoJsonEditDrawer.vue`。
- 侧边详情：`components/overlays/BaseSidePanel.vue`。
- 空状态：`mango-empty-state`，不要新增裸 `a-empty`。
- 断言、键值、提示、代码、滚动条优先复用现有组件。

## Loading 规则

- 所有接口请求必须有 loading 状态。
- 异步保存、删除、执行、调试、导入、导出必须绑定按钮 loading。
- 表格数据加载必须绑定表格 loading。
- 组件懒加载、耗时渲染、抽屉/弹窗内容加载必须有局部 loading。
- loading 只覆盖对应区域，不用全页遮罩替代局部反馈。
- 左中右、多面板、工作台类页面必须按区域拆分 loading；某一区域数据加载完成后应立即解除该区域 loading。
- 只有页面初始阶段所有关键区域都没有可展示数据时，才允许使用整页 loading。
- loading 结束必须在成功和失败分支都正确关闭。

## 代码约束

- 手工编辑优先使用 `apply_patch`。
- 不重构无关代码，不回滚用户已有改动。
- 注释只写复杂逻辑的必要说明。
- 新增全局样式必须 `mango-` 前缀。
- scoped 样式也优先使用 `--m-*` token。

## 验证清单

- `npm run theme:audit` 保持 `Needs review: 0`。
- 操作列是否为 `170`。
- 表格是否只在内部横向滚动。
- 长文本是否可查看完整内容。
- 弹窗 footer 是否靠右，抽屉 footer 是否左下角。
- 6 套主题下文字、表格、弹窗、抽屉、代码、图表是否可读。
