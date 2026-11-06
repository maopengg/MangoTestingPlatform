# AGENTS.md

本文件是 `mango-console/` 前端开发约束。更完整规范见 `docs/前端统一规则规范.md`。

## 项目定位

- Vue 3 + TypeScript + Vite + Arco Design + Pinia。
- 后台测试平台，优先服务扫描、排查、配置和连续操作。
- 风格要求：企业级、数据密集、紧凑、干净统一。
- 不改接口、路由、权限和业务数据结构，除非任务明确要求。

## 页面规范化、状态与组件化

- 新增或整理页面状态、组件及 composable 时，遵循 [Vue 页面状态管理与组件化开发规范](../docs/架构设计/Vue页面状态管理与组件化开发规范.md)。
- 不新增 `reactive<any>`、`const data: any = reactive(...)` 等无类型的整页状态对象；按职责组织状态，使用明确类型，派生值使用 `computed`。
- 页面负责布局与协调，独立业务区域按需要拆组件；不按行数或文件数量机械拆分，不传递整个页面状态对象。
- 目录按上述规范组织：页面入口与真实配置放 `index.vue`、`config.ts`，类型、业务组件和有状态逻辑按需放 `types.ts`、`components/`、`composables/`；子路由保持独立目录，不建空壳文件。
- 已有代码随业务维护渐进整理，不仅为变量改名或统一语法全局重构；保留 API、权限及保存和执行语义。
- 逐页规范化时同步维护 [修复清单](../docs/架构设计/Vue页面规范化修复清单.md)：开始标记“修复中”，覆盖所属弹窗、抽屉及关联组件；记录问题、验证结果与提交依据，验收通过后标记“已完成”。

## 页面与权限交互

遵循根目录 `AGENTS.md` 的“页面与操作权限”：按钮统一展示，不使用 `v-permission`、操作权限字段或页面内角色判断控制显示、禁用和点击，只保留业务条件及加载/防重复限制。公共请求层不按角色或权限缓存预拦截请求，只展示后端权限错误；菜单路由权限仍保留。子页面归属业务菜单，角色切换清理旧状态、忽略迟到响应，保存固定快照，自身权限变化后刷新路由。

## 常用命令

```bash
npm run dev
npm run build:dev
npm run tsc
npm run theme:audit
npm run responsive:audit
```

- 未明确要求时，不启动或占用 `5173`。
- 样式/组件改造后优先跑 `npm run theme:audit`。
- 阶段验收或构建风险时跑 `npm run build:dev`。
- `npm run tsc` 可能有历史全量类型问题，需区分是否由本次改动引入。

## 屏幕与显示密度兼容

- 全站只使用 `src/hooks/useDisplayDensity.ts` 的显示密度方案。自动模式以 CSS 视口宽度为依据连续缩放：`1900px → 1`、`2560px → 1.15`、`3840px → 1.35`，超过 4K 保持 `1.35`；不得通过 `screen.width`、设备物理分辨率或 `devicePixelRatio` 再判断 2K/4K。
- 应用启动和视口变化时由全局逻辑调用 `applyDisplayDensity`，页面和组件不得各自监听窗口并修改根字号，也不得自行维护另一套屏幕档位。
- 普通 CSS/LESS 固定尺寸必须写在 `<style>`、公共样式或 class 中，交由 `scripts/postcss-fluid-rem.cjs` 自动从 `px` 转为 `rem`。模板中的 `style="width: 100px"`、`:style="{ width: '100px' }"` 等内联固定尺寸禁止使用，因为它们不会经过 PostCSS。
- 允许保留 `1px` 及以下的边框和像素级绘制尺寸；百分比、`fr`、`minmax()`、`clamp()`、容器查询等响应式尺寸按实际布局使用。
- JavaScript/TypeScript 中会影响 DOM 布局的数值尺寸必须使用 `scaleDensityPixels`；可能是数字或 `px` 字符串的通用属性使用 `scaleDensityLength`。典型场景包括动态网格最小宽度、时间轴单位宽度、树层级缩进、DOM 内画布尺寸和由代码生成的内联位置。
- `getBoundingClientRect()`、`clientWidth`、`scrollWidth`、指针坐标、服务端返回的实际截图坐标等已经处于当前 CSS 像素坐标系，禁止再次乘以显示密度。只有“设计尺寸常量”需要缩放，避免双重缩放。
- `a-table` / `a-table-column` 的 `columns[].width`、列 `width` 和 `scroll.x/scroll.y`，`a-modal`、`a-drawer` 的 `width`，以及 `a-avatar` 的数值 `size`，由 `src/layouts/index.ts` 的全局适配组件统一缩放。业务页面继续填写设计基准尺寸，不得手工乘 `displayDensityScale`，也不得绕开全局组件直接引入并渲染 Arco 原始组件。
- 表格表头字段名保持单行；长数据列使用 `ellipsis + tooltip`，通过 `scroll.x` 承接宽内容，不得为了塞进 4K 页面而缩窄列宽或让中文逐字换行。表格滚动仍遵守本文件“表格”章节的边界规则。
- Modal、Drawer、Popover、下拉面板和其他浮层的内容必须保留合理的视口边界；自定义浮层如果最终不经过全局 `a-modal` / `a-drawer`，其 JS 宽高必须显式使用密度工具，CSS 宽高必须放入样式块。
- 图表、SVG、Canvas、流程图和甘特图需要区分“DOM 展示尺寸”与“内部坐标系”：与字体、节点盒子和页面布局对齐的尺寸必须同步密度；纯数据坐标、缩放矩阵和导出原始分辨率不得盲目缩放。密度变化后需要重排的组件监听 `mango-density-change` 或复用现有 `resize` / `ResizeObserver` 链路。
- 多栏工作台继续使用 `mango-workbench-scroll-x`、准确的最小宽度和容器查询保证小屏可用；不得使用 `zoom` 或页面级 `transform: scale()` 做整页适配，这会破坏固定定位、弹层、鼠标坐标和滚动范围。
- 路由相关的页面高度、滚动模式和布局 class 不得在异步导航的 `beforeEach` 阶段提前切换，否则旧页面会在新页面加载期间发生瞬时拉伸。此类布局状态应直接派生自当前路由，或在导航成功后的 `afterEach` 中更新，确保与新页面同一轮渲染。
- 新增或修改页面布局、组件尺寸、表格、弹窗、抽屉、画布或图表后必须执行 `npm run responsive:audit`。该审计用于确认全局适配入口存在，并禁止内联固定 px、`zoom` 和页面级缩放；涉及表格时同时执行 `npm run table:audit`。
- 验收至少覆盖约 `1900px`、`2560px`、`3840px` 三档 CSS 视口，检查文字是否遮挡、控件是否重叠、表格固定列与滚动条是否正确、弹窗/抽屉是否溢出，以及路由切换是否出现布局拉伸。浏览器缩放比例应保持一致，避免把浏览器缩放差异误判为应用适配问题。

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
- 路由级列表页存在项目/产品或模块筛选时，统一使用 `ProjectProductNavigationWorkbench`；业务页面不得直接拼装 `ProjectProductNavigationSidebar` 和自定义右侧容器。项目/产品与模块条件由左侧导航承载，不在搜索区和表格中重复展示。
- 列表页的搜索项、表格列、静态下拉选项优先放同目录 `config.ts`，页面组件只保留业务状态、接口请求和交互逻辑。
- 每个业务页面 `index.vue` 必须搭配同目录 `config.ts`；`config.ts` 必须承载当前页面真实配置（列、搜索项、静态选项、滚动宽度等），不能只放 `tabKey` 之类的路由分支参数。
- 同一模块有多个菜单/路由页面时，每个路由必须有独立页面入口；公共逻辑下沉到 `components/`、hooks 或 service，避免多个路由都指向同一个 `index.vue` 后再靠 `tabKey` 分支渲染。
- 详情页优先使用 `mango-detail-toolbar + mango-detail-workbench`。
- 配置区优先使用 `mango-section-card + mango-section-title + mango-soft-panel`。
- 页面外边距、标题与主体间距、多区域工作台列间距统一使用 `--m-page-gap`（当前为 `8px`）；组件内部表单、标题和内容 padding 可按密度单独控制，不在页面级布局中散写 `8px/12px`。
- 页面不要贴边，也不要做营销式大留白。
- 长文本必须省略、tooltip 或进入详情。
- 宽内容只允许在表格、代码面板、画布内部滚动。
- 多列工作台、详情页、左树右表、左导航右内容、图表双栏/多栏等固定最小宽度布局，不能只依赖 `body` 的 `--m-app-min-width` 防压缩；当内部列宽之和可能超过主内容区时，必须在业务区域外层使用 `mango-workbench-scroll-x`，并通过 `--mango-workbench-min-width` 设置该区域真实最小宽度。
- `mango-workbench-scroll-x` 只解决横向不足导致的压缩/裁切；纵向滚动仍交给页面或指定业务区域，不要因为加横向边界而把整页纵向滚动塞进表格或基础组件。
- 新增或改造多栏页面时，至少检查 13 寸主内容区、1200px 应用最小宽度、侧边菜单展开状态下是否被压缩；如果需要保留多栏，就加区域横向滚动边界；如果业务上可以降级，优先在合理断点改为单栏。
- 横向字段组、断言参数、前置/后置变量等宽内容必须由页面/业务区域容器承接横向滚动，统一使用 `mango-horizontal-scroll-region`；不要把横向 scrollbar 写进 `KeyValueList` 等基础表单组件内部。

## 表格

- 表格默认无重边框、紧凑行高、表头弱底色、hover 轻提示。
- 列表页、工作台页表格的滚动方向必须拆分：上下滚动交给外层页面/区域容器，左右滚动才交给表格。
- 列表页的横向滚动必须严格限制在 Arco 表格内容区；搜索区、`TableTabs`、工具栏和 `TableFooter` 不得跟随表格横向移动。
- 列表页存在业务分类 Tabs 时，必须放入 `ProjectProductNavigationWorkbench` 的 `tabs` 插槽等固定区域；仅作为导航或工具栏的 Tabs 使用 `mango-tabs-nav-only`，其内容区上内边距统一为 `1px`。
- `ProjectProductNavigationWorkbench` 不使用页面级横向滚动或强制右侧最小宽度；右侧使用 `minmax(0, 1fr)`，宽表由 `a-table` 的 `scroll.x` 提供横向滚动。
- 不得在表格外壳重复设置 `overflow-x: auto`，不得用页面级 `wheel` 事件代理表格横向滚动；表格滚动条统一由全局 `.arco-table` 样式控制。
- 常规列表表格只配置 `scroll.x`，不要配置 `scroll.y`，不要让表格内部承担纵向滚动。
- 需要固定左侧筛选/模块导航时，左侧使用 `position: sticky` 固定在外层滚动容器内；右侧搜索区和表格随外层上下滚动。
- 若 Arco 表格因横向滚动显示不可拖动的内部竖向 scrollbar，只隐藏表格内部竖向轨道和 thumb，保留横向 scrollbar。
- 只有弹窗、抽屉、代码面板、画布、有限高度嵌入区等明确固定高度场景，才允许使用表格内部 `scroll.y`。
- 操作列固定右侧，宽度全局统一 `160`。
- 操作列统一使用 `MangoTableActions`。
- `MangoTableActions` 操作数小于等于 3 时全部外显；大于等于 4 时外显 2 个，其余进“更多”。
- 删除/移除/清理必须 `danger: true`。
- 表格内执行、调试保持文本按钮；表格外主执行按钮才用成功绿色。
- 表格中的启用/停用、默认开启、是否生效等二元状态优先使用 `a-switch size="small"`，通过 `beforeChange` 等机制确保接口成功后再切换；只读状态才使用 tag。
- 枚举类 tag 颜色优先使用 `useEnum()` 提供的 `enumStore.colors[value]`，展示文案从对应枚举项的 `title` 获取，例如测试对象列表的部署环境、自动化类型。
- 表格列对齐统一：ID、序号、数字、短枚举、状态 tag、开关、操作列等固定/短字段居中；名称、路径、说明、地址、错误信息、绑定关系等业务文本字段左对齐。
- 长字段必须 `ellipsis: true`、`tooltip: true`。
- 表格和详情中的项目产品只展示产品名称时使用 `record.project_product.name`；模块完整路径统一使用后端 `full_path` 或 `formatModulePath(record.module)`，不得读取 `superior_module_1/2` 自行拼接。
- 使用 `ProjectProductNavigationWorkbench` 的列表必须展示导航归属列，且位置不得由业务页自由调整：只有项目/产品导航时，固定为“业务数据列 → 项目/产品 → 操作”；启用 `show-modules` 的模块导航时，固定为“业务数据列 → 项目/产品 → 模块 → 操作”。“项目/产品、模块”必须连续，中间不得插入其他列。新增或修改导航列表后执行 `npm run navigation:audit`。
- 表格默认允许用户拖拽调整列宽；确有交互冲突的小型嵌入表格才允许显式设置 `:column-resizable="false"`。
- 表格的原生滚动条和 Arco 自绘滚动条统一由 `src/styles/index.css` 全局控制，业务页面不得重复定义表格滚动条宽度、轨道或滑块颜色；存在横向溢出时，由全局同步轨道常驻在表格当前可视区域底部，页面不得自行实现浮动横向滚动条。
- 只要表格或业务区域能够横向/纵向滚动，对应滚动条就必须显示在当前可视区域的底部/右侧。优先使用 `a-table` 自身的滚动条：父级设置有限高度，表格同时配置 `scroll.x`、`scroll.y` 并使用 `mango-native-scroll-table`，让横向条位于表格底边、纵向条位于表格右侧；不得额外复制代理滚动条。位于 `ProjectProductNavigationWorkbench` 内时必须启用 `contained-body`，并关闭外层滚动条接管。
- 固定操作列时必须设置 `scroll.x`。
- 新增或修改表格后必须执行 `npm run table:audit`，确认常规表格没有遗漏 `scroll.x`、没有关闭固定横向条且缺少公共替代组件、项目导航工作台内的固定滚动表格已启用 `contained-body`。
- 除非明确需要，不固定名称列。

## 表单与搜索

- 搜索区由 `TableHeader` 控制。
- 项目导航工作台的搜索区统一由 `TableSearchPanel` 承载，搜索和重置由 `TableSearchActions` 固定在动态网格第一行最后一格；页面不得重复渲染搜索按钮或嵌套第二个 `TableHeader`。
- `TableSearchPanel` 使用右侧容器完整宽度，通过 `ResizeObserver` 按 `210-250px` 字段块范围和 `8px` 基础间距动态计算列数与单格宽度，优先消除右侧剩余空白。
- 搜索 label 固定宽度，保证多行对齐。
- 普通搜索区域的 label 固定为 `70px`、控件固定为 `160px`、字段块固定为 `230px`；业务页面不得散写搜索控件宽度。
- 后端支持 `__in`、数组或逗号分隔集合查询的搜索下拉框必须支持多选。`FormItem` 搜索配置统一调用 `enableMultiSelectSearch`，选择器绑定 `:multiple="item.multiple"` 和折叠标签，多值通过 `searchOperator: 'in'` 提交为 `key__in=value1,value2`，重置时恢复为空数组。
- 项目/产品、模块等上下级依赖选择器，以及后端仅支持精确单值的专用接口可以保持单选；例外必须登记在 `scripts/search-multiselect-audit.mjs` 并写明接口限制，不得仅因前端实现方便保留单选。
- 不在页面内散写控件宽度。
- 列表页表格外的新增、创建、导入等主按钮优先使用 `size="small"`，与既有管理页保持紧凑一致。
- 必填标识使用 `mango-form-item__require`。
- 说明文案用 `--m-muted`，错误提示用 `--m-danger`。

## 弹窗与抽屉

- 普通 `a-modal` footer 按钮统一靠右。
- `Modal.confirm` 的取消/删除按钮统一靠右。
- `ModalDialog` footer 使用 `mango-modal-dialog-footer-actions`。
- `ModalDialog` 只负责统一外壳，页面仍需按内容控制宽度和密度：短表单优先约 `520-560px`，字段较多但可并排的表单优先约 `700-760px` 并使用紧凑双列；长文本、SQL、代码、说明字段独占整行。
- 弹窗表单优先左右布局；短字段不要在宽弹窗里单列铺满，避免出现大片空白。
- 页面局部样式不允许把 `.arco-modal-footer` 改成居中或靠左。
- 右侧抽屉 `a-drawer` 不跟随弹窗规则，footer 保持左下角。
- `BaseSidePanel` 分为 `action` 和 `page` 两种模式：表单、配置、日志等业务操作使用默认 `action` 模式并保留操作 footer；嵌入已有路由页面或完整工作台时必须使用 `mode="page"`，统一采用“来源标题与说明 + 弹性铺满的页面内容 + 全局版权栏”三段式结构，页面自身标题和操作保持完整，不再渲染取消、确认等操作 footer。
- 抽屉内容区可滚动，footer 固定。
- 创建、编辑和普通操作抽屉的四周边距统一由外壳承载，使用 `--m-page-gap`；header/footer 的水平边距与内容区保持一致。`BaseSidePanel` 的 action 内容容器提供边距，page 模式继续由页面外壳提供一次边距，业务根容器不得重复补 padding。内部卡片使用 `--m-card-padding`，无边距画布/工作台须明确由哪一层提供边距。修改后执行 `npm run drawer:audit`。
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

- 首次加载和用户主动发起的接口请求必须有对应 loading 状态；页面级自动轮询复用 `usePagePolling`，统一 5 秒静默更新，不反复触发页面或表格 loading，局部任务轮询按所属协议维护。
- 异步保存、删除、执行、调试、导入、导出必须绑定按钮 loading。
- 表格数据加载必须绑定表格 loading。
- 组件懒加载、耗时渲染、抽屉/弹窗内容加载必须有局部 loading。
- loading 只覆盖对应区域，不用全页遮罩替代局部反馈。
- 左中右、多面板、工作台类页面必须按区域拆分 loading；某一区域数据加载完成后应立即解除该区域 loading。
- 只有页面初始阶段所有关键区域都没有可展示数据时，才允许使用整页 loading。
- loading 结束必须在成功和失败分支都正确关闭。
- 同一内容区域的父子遮罩必须互斥；父级 loading 生效时，子级表格/面板遮罩使用 `!parentLoading && childLoading`，不同区域与按钮的 loading 保持独立。修改后执行 `npm run loading:audit`，分支互斥例外须在审计脚本中说明。
- 需要内容层承载高度、padding、Flex 或滚动的 loading 面板使用 `MangoPanelSpin`；布局只作用于自身或直接内容层，例如 `.mango-panel-spin :deep(> .mango-panel-spin__content)`。当前 Arco Spin 没有 `.arco-spin-children` 节点，不得依赖该选择器，也不得无差别修改后代内容层，避免影响内部表格、编辑器及浮层。

## 代码约束

- 手工编辑优先使用 `apply_patch`。
- 不重构无关代码，不回滚用户已有改动。
- 注释只写复杂逻辑的必要说明。
- 新增全局样式必须 `mango-` 前缀。
- scoped 样式也优先使用 `--m-*` token。

## 验证清单

- `npm run responsive:audit` 必须为 `Issues: 0`；涉及表格时 `npm run table:audit` 的各问题项必须为 `0`。
- `npm run search:audit` 必须为 `Issues: 0`，且新增例外必须有明确的后端协议原因。
- 约 `1900px`、`2560px`、`3840px` 三档 CSS 视口下，文字、表格、弹窗、抽屉、工作台和路由切换是否保持一致且无重叠、裁切或异常拉伸。
- 新增的固定尺寸是否位于样式块；JS 设计尺寸是否使用密度工具；实测 DOM/指针坐标是否避免了二次缩放。
- `npm run theme:audit` 保持 `Needs review: 0`。
- 操作列宽度是否统一为 `160`。
- 新增、创建、导入等列表主按钮是否使用小号紧凑尺寸。
- 二元状态列是否使用小号开关，并确保接口成功后再切换。
- 弹窗宽度、单双列布局是否匹配内容密度。
- 表格是否只在内部横向滚动。
- 多栏工作台/左树右表/图表多栏是否不会在 13 寸屏幕下被压缩；必要时是否使用 `mango-workbench-scroll-x` 和准确的 `--mango-workbench-min-width`。
- 长文本是否可查看完整内容。
- 弹窗 footer 是否靠右，抽屉 footer 是否左下角。
- 6 套主题下文字、表格、弹窗、抽屉、代码、图表是否可读。
