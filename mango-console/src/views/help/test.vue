<template>
  <div class="theme-lab">
    <section class="lab-head">
      <div>
        <p class="eyebrow">MANGO CONSOLE DESIGN SYSTEM</p>
        <h1>企业级 SaaS 组件主题验收</h1>
        <p class="sub-title">抽取系统高频组件，预览统一后的后台产品风格。</p>
      </div>
      <div class="head-card">
        <span>视觉关键词</span>
        <strong>清晰 / 紧凑 / 可排查</strong>
        <em>Arco Design + Mango Console</em>
      </div>
    </section>

    <section class="mango-section-card">
      <div class="mango-section-title">
        <div>
          <h2>主题 Token</h2>
          <p>用于全局背景、卡片、状态、表格、按钮的基础配色。</p>
        </div>
        <a-tag color="blue" size="small">Preview</a-tag>
      </div>
      <div class="token-grid">
        <div v-for="item in colorTokens" :key="item.name" class="token-item">
          <i :style="{ background: item.value }"></i>
          <span>{{ item.name }}</span>
          <strong>{{ item.value }}</strong>
        </div>
      </div>
    </section>

    <section class="mango-section-card">
      <div class="mango-section-title">
        <div>
          <h2>标题与字体层级</h2>
          <p>统一列表页、配置页、详情页、卡片区块和说明文字，避免各页面标题大小不一致。</p>
        </div>
        <a-tag color="blue" size="small">Typography</a-tag>
      </div>
      <div class="type-grid">
        <div class="type-card page-title-sample">
          <span>页面标题 / Report Page</span>
          <strong>测试报告详情</strong>
          <p>22px / 700 / --m-text，用于详情页头部、报告页头部、一级业务页面标题。</p>
        </div>
        <div class="type-card detail-title-sample">
          <span>详情标题 / Detail Title</span>
          <strong>订单创建主流程校验</strong>
          <p>18px / 650 / --m-text，用于抽屉、详情卡片、被查看对象名称。</p>
        </div>
        <div class="type-card section-title-sample">
          <span>区块标题 / Section Title</span>
          <strong>测试套用例列表</strong>
          <p>16px / 600 / --m-text，用于表格区、配置分组、帮助页分类。</p>
        </div>
        <div class="type-card table-title-sample">
          <span>卡片标题 / Card Title</span>
          <strong>接口自动化配置</strong>
          <p>14px / 600 / --m-text-2，用于卡片、小面板、表格工具栏标题。</p>
        </div>
        <div class="type-card body-title-sample">
          <span>正文强调 / Body Strong</span>
          <strong>执行环境：测试环境</strong>
          <p>13px / 500 / --m-text-2，用于描述列表、列表项主文案。</p>
        </div>
        <div class="type-card meta-title-sample">
          <span>辅助信息 / Meta Text</span>
          <strong>2026-05-22 10:32:08</strong>
          <p>12px / 400-600 / --m-muted，用于时间、统计说明、面包屑非当前项。</p>
        </div>
      </div>
    </section>

    <section class="component-grid">
      <div class="mango-section-card">
        <div class="mango-section-title">
          <div>
            <h2>按钮与操作</h2>
            <p>系统里常见的新建、删除、执行、文本按钮、更多操作。</p>
          </div>
        </div>
        <div class="button-row">
          <a-button type="primary">主操作</a-button>
          <a-button class="success-action-btn" type="primary" status="success">执行</a-button>
          <a-button class="success-action-btn" type="primary" status="success">调试</a-button>
          <a-button status="danger">删除</a-button>
          <a-button>次要</a-button>
          <a-button type="text">文本按钮</a-button>
        </div>
        <div class="button-row compact">
          <AddButton />
          <DeleteButton />
          <a-dropdown trigger="hover">
            <a-button size="mini" type="text">更多</a-button>
            <template #content>
              <a-doption>复制</a-doption>
              <a-doption>导出</a-doption>
              <a-doption>查看日志</a-doption>
            </template>
          </a-dropdown>
        </div>
      </div>

      <div class="mango-section-card">
        <div class="mango-section-title">
          <div>
            <h2>状态与反馈</h2>
            <p>执行状态、通知结果、进度、提示信息。</p>
          </div>
        </div>
        <div class="tag-row">
          <a-tag color="green">成功</a-tag>
          <a-tag color="red">失败</a-tag>
          <a-tag color="orange">进行中</a-tag>
          <a-tag color="blue">待开始</a-tag>
          <a-badge status="processing" text="自动轮询" />
        </div>
        <a-alert type="info" class="semantic-alert"
          >建议：重要反馈用语义色，不用高饱和大面积底色。</a-alert
        >
        <div class="progress-list">
          <div v-for="item in progressItems" :key="item.label" class="progress-row">
            <span>{{ item.label }}</span>
            <a-progress :percent="item.percent" :show-text="false" :stroke-width="8" />
            <em>{{ Math.round(item.percent * 100) }}%</em>
          </div>
        </div>
      </div>
    </section>

    <section class="component-grid">
      <div class="mango-section-card custom-component-card">
        <div class="mango-section-title">
          <div>
            <h2>自定义组件 / 表格工具</h2>
            <p>来自 TableConfig、SortableTable，统一成小尺寸圆形工具按钮和轻量弹层。</p>
          </div>
        </div>
        <div class="custom-toolbar">
          <span>表格偏好</span>
          <TableConfig
            @refresh="tableConfigState = '已触发刷新'"
            @update-border="(value) => (tableConfigState = value ? '显示边框' : '隐藏边框')"
            @update-striped="(value) => (tableConfigState = value ? '显示斑马纹' : '关闭斑马纹')"
          />
          <SortableTable :columns="customColumns" @update="onCustomColumnsUpdate" />
          <em>{{ tableConfigState }}</em>
        </div>
        <div class="column-preview">
          <a-tag v-for="item in visibleCustomColumns" :key="item.key" color="blue" size="small">
            {{ item.title }}
          </a-tag>
        </div>
      </div>

      <div class="mango-section-card custom-component-card">
        <div class="mango-section-title">
          <div>
            <h2>自定义组件 / 表单反馈</h2>
            <p>来自 PasswordStrong、TipMessage，用低饱和语义色统一表单提示。</p>
          </div>
        </div>
        <TipMessage
          message="从响应 JSON 中提取字段时，请优先使用可读性更强的 jsonpath 表达式。"
          icon="i"
          icon-color="var(--m-primary)"
          text-color="var(--m-text-2)"
          background-color="var(--m-surface-soft)"
          border="1px solid var(--m-primary-border)"
          border-radius="8px"
          margin-bottom="12px"
        />
        <a-input-password v-model="passwordSample" placeholder="输入密码查看强度" allow-clear />
        <div class="password-preview">
          <PasswordStrong :input-value="passwordSample" />
        </div>
      </div>
    </section>

    <section class="component-grid">
      <div class="mango-section-card">
        <div class="mango-section-title">
          <div>
            <h2>业务组件 / 断言结果</h2>
            <p>对应 AssertionResult 的信息组织：实际值、期望值、结果和失败原因。</p>
          </div>
        </div>
        <AssertionResult :data="assertionResultItems" />
      </div>

      <div class="mango-section-card">
        <div class="mango-section-title">
          <div>
            <h2>业务组件 / 参数与 JSON</h2>
            <p>对应 KeyValueList、JsonDisplay 的轻量化主题：键值清晰、代码可读。</p>
          </div>
        </div>
        <div class="kv-preview">
          <div v-for="item in keyValueItems" :key="item.key" class="kv-row">
            <span>{{ item.key }}</span>
            <strong>{{ item.value }}</strong>
            <a-tag :color="item.color" size="small">{{ item.type }}</a-tag>
          </div>
        </div>
        <pre class="mini-json"><code v-html="miniJsonExample"></code></pre>
      </div>
    </section>

    <section class="mango-section-card">
      <div class="mango-section-title">
        <div>
          <h2>筛选表单</h2>
          <p>覆盖输入、级联、选择、日期、时间、数字、标签、开关等高频控件。</p>
        </div>
        <div class="title-actions">
          <a-button size="small">重置</a-button>
          <a-button size="small" type="primary">搜索</a-button>
        </div>
      </div>
      <a-form layout="inline" :model="formModel" class="filter-form">
        <a-form-item label="关键字">
          <a-input v-model="formModel.keyword" placeholder="请输入用例/接口名称" allow-clear />
        </a-form-item>
        <a-form-item label="项目产品">
          <a-cascader
            v-model="formModel.product"
            :options="productOptions"
            placeholder="请选择项目/产品"
            allow-clear
            allow-search
          />
        </a-form-item>
        <a-form-item label="状态">
          <a-select
            v-model="formModel.status"
            :options="statusOptions"
            placeholder="请选择"
            allow-clear
          />
        </a-form-item>
        <a-form-item label="日期">
          <a-date-picker v-model="formModel.date" />
        </a-form-item>
        <a-form-item label="时间">
          <a-time-picker v-model="formModel.time" />
        </a-form-item>
        <a-form-item label="重试">
          <a-input-number v-model="formModel.retry" :min="0" :max="10" />
        </a-form-item>
        <a-form-item label="标签">
          <a-input-tag v-model="formModel.tags" placeholder="输入后回车" allow-clear />
        </a-form-item>
        <a-form-item label="成员">
          <a-tree-select
            v-model="formModel.owner"
            :data="treeData"
            placeholder="请选择"
            allow-clear
            allow-search
          />
        </a-form-item>
        <a-form-item label="通知">
          <a-switch v-model="formModel.notice" />
        </a-form-item>
      </a-form>
    </section>

    <section class="mango-section-card table-section">
      <div class="table-toolbar">
        <div>
          <h2>表格与工具栏</h2>
          <p>
            <span>测试用例</span>
            <i></i>
            <span>已选择 2 项</span>
            <i></i>
            <span>共 128 条</span>
          </p>
        </div>
        <div class="title-actions">
          <a-radio-group v-model="tableFilter" type="button" size="small">
            <a-radio value="all">全部</a-radio>
            <a-radio value="fail">失败</a-radio>
            <a-radio value="success">成功</a-radio>
          </a-radio-group>
          <a-button size="small" status="danger">批量删除</a-button>
          <a-button size="small" type="primary">新增</a-button>
        </div>
      </div>
      <a-table
        :bordered="false"
        :columns="columns"
        :data="rows"
        :loading="false"
        :pagination="false"
        :row-selection="{ selectedRowKeys }"
        :scroll="{ x: 1160 }"
        row-key="id"
        class="theme-table"
      >
        <template #level="{ record }">
          <a-tag :color="record.levelColor" size="small">{{ record.level }}</a-tag>
        </template>
        <template #status="{ record }">
          <a-tag :color="record.statusColor" size="small">{{ record.status }}</a-tag>
        </template>
        <template #enabled="{ record }">
          <a-switch :model-value="record.enabled" size="small" />
        </template>
        <template #actions>
          <a-space :size="4">
            <a-button type="text" size="mini">编辑</a-button>
            <a-button type="text" size="mini">执行</a-button>
            <a-dropdown trigger="hover">
              <a-button type="text" size="mini">更多</a-button>
              <template #content>
                <a-doption>详情</a-doption>
                <a-doption>复制</a-doption>
                <a-doption>查看日志</a-doption>
              </template>
            </a-dropdown>
          </a-space>
        </template>
      </a-table>
      <div class="mango-table-footer-preview">
        <a-pagination :total="128" :page-size="10" size="small" show-total show-jumper />
      </div>
    </section>

    <section class="component-grid">
      <div class="mango-section-card">
        <div class="mango-section-title">
          <div>
            <h2>详情信息</h2>
            <p>详情页、抽屉、报告头部可以使用描述列表和状态摘要。</p>
          </div>
          <a-button size="small" type="primary" @click="drawerVisible = true">打开抽屉</a-button>
        </div>
        <a-descriptions :column="2" size="small" bordered>
          <a-descriptions-item label="任务名称">每日冒烟测试</a-descriptions-item>
          <a-descriptions-item label="执行环境">测试环境</a-descriptions-item>
          <a-descriptions-item label="执行人">admin</a-descriptions-item>
          <a-descriptions-item label="通知状态">
            <a-tag color="green" size="small">已发送</a-tag>
          </a-descriptions-item>
        </a-descriptions>
      </div>

      <div class="mango-section-card">
        <div class="mango-section-title">
          <div>
            <h2>流程与折叠</h2>
            <p>用于步骤、执行日志、参数化配置等层级内容。</p>
          </div>
        </div>
        <a-tabs default-active-key="log" size="small">
          <a-tab-pane key="log" title="执行日志">
            <a-timeline class="theme-timeline">
              <a-timeline-item label="10:32:08">开始执行测试套</a-timeline-item>
              <a-timeline-item label="10:32:11">完成接口鉴权</a-timeline-item>
              <a-timeline-item label="10:32:15" dot-color="red">订单断言失败</a-timeline-item>
            </a-timeline>
          </a-tab-pane>
          <a-tab-pane key="steps" title="步骤">
            <a-collapse :bordered="false" :default-active-key="[1]">
              <a-collapse-item :key="1" header="步骤 1：准备测试数据">
                <p class="mango-muted-text">生成用户、订单和支付参数。</p>
              </a-collapse-item>
              <a-collapse-item :key="2" header="步骤 2：执行接口请求">
                <p class="mango-muted-text">请求体、响应体和断言结果统一在详情里展示。</p>
              </a-collapse-item>
            </a-collapse>
          </a-tab-pane>
        </a-tabs>
      </div>
    </section>

    <section class="component-grid">
      <div class="mango-section-card">
        <div class="mango-section-title">
          <div>
            <h2>上传与空状态</h2>
            <p>文件上传、加载中、无数据状态，是平台配置页常见场景。</p>
          </div>
        </div>
        <a-upload draggable action="/" :auto-upload="false" class="theme-upload">
          <template #upload-button>
            <div class="upload-drop">
              <strong>拖拽文件到这里，或点击选择</strong>
              <span>支持 .py / .json / .xlsx / 图片附件</span>
            </div>
          </template>
        </a-upload>
        <div class="state-grid">
          <a-spin :loading="true" tip="加载配置中..." class="state-card">
            <div></div>
          </a-spin>
          <div class="state-card">
            <div class="mango-empty-state theme-empty-demo">暂无配置项</div>
          </div>
        </div>
      </div>

      <div class="mango-section-card">
        <div class="mango-section-title">
          <div>
            <h2>数据指标</h2>
            <p>首页统计、资源卡片和执行器状态可以用统一的数据卡表达。</p>
          </div>
        </div>
        <a-grid :cols="2" :col-gap="10" :row-gap="10">
          <a-grid-item v-for="item in statisticItems" :key="item.label">
            <div class="stat-card">
              <a-statistic :title="item.label" :value="item.value" :precision="item.precision" />
              <a-tag :color="item.color" size="small">{{ item.trend }}</a-tag>
            </div>
          </a-grid-item>
        </a-grid>
      </div>
    </section>

    <section class="mango-section-card">
      <div class="mango-section-title">
        <div>
          <h2>图表样式</h2>
          <p>覆盖首页和测试报告常见图表：占比、趋势、活跃度、状态分布。</p>
        </div>
        <a-tag color="blue" size="small">Charts</a-tag>
      </div>
      <div class="chart-grid">
        <div class="chart-card">
          <div class="chart-head">
            <div>
              <strong>测试用例占比</strong>
              <span>UI / API / Pytest</span>
            </div>
            <em>总计 1,286</em>
          </div>
          <div class="donut-chart" style="--p1: 0 48%; --p2: 48% 82%; --p3: 82% 100%">
            <div>
              <strong>48%</strong>
              <span>API</span>
            </div>
          </div>
          <div class="chart-legend">
            <span><i class="blue"></i>API 618</span>
            <span><i class="green"></i>UI 438</span>
            <span><i class="orange"></i>Pytest 230</span>
          </div>
        </div>

        <div class="chart-card chart-wide">
          <div class="chart-head">
            <div>
              <strong>近三个月执行趋势</strong>
              <span>成功 / 失败用例数</span>
            </div>
            <em>周维度</em>
          </div>
          <div class="bar-chart">
            <div v-for="item in trendItems" :key="item.week" class="bar-column">
              <div class="bar-stack">
                <i class="success" :style="{ height: `${item.success}px` }"></i>
                <i class="danger" :style="{ height: `${item.fail}px` }"></i>
              </div>
              <span>{{ item.week }}</span>
            </div>
          </div>
          <div class="chart-legend">
            <span><i class="green"></i>成功</span>
            <span><i class="red"></i>失败</span>
          </div>
        </div>

        <div class="chart-card">
          <div class="chart-head">
            <div>
              <strong>活跃度排行</strong>
              <span>产品 / 模块执行次数</span>
            </div>
            <em>Top 5</em>
          </div>
          <div class="rank-chart">
            <div v-for="item in rankItems" :key="item.name" class="rank-row">
              <span>{{ item.name }}</span>
              <div><i :style="{ width: `${item.value}%` }"></i></div>
              <em>{{ item.count }}</em>
            </div>
          </div>
        </div>

        <div class="chart-card">
          <div class="chart-head">
            <div>
              <strong>报告状态分布</strong>
              <span>成功 / 失败 / 进行中</span>
            </div>
            <em>实时</em>
          </div>
          <div class="status-summary">
            <div v-for="item in chartStatusItems" :key="item.label" :class="item.type">
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
              <i :style="{ width: `${item.percent}%` }"></i>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="component-grid">
      <div class="mango-section-card">
        <div class="mango-section-title">
          <div>
            <h2>列表与头像</h2>
            <p>通知中心、执行器、消息流可以统一成轻量列表。</p>
          </div>
        </div>
        <a-list :bordered="false" :split="false" class="theme-list">
          <a-list-item v-for="item in notificationItems" :key="item.title">
            <a-list-item-meta :description="item.description" :title="item.title">
              <template #avatar>
                <a-avatar :style="{ backgroundColor: item.color }" :size="30">{{
                  item.avatar
                }}</a-avatar>
              </template>
            </a-list-item-meta>
            <a-tag :color="item.tagColor" size="small">{{ item.status }}</a-tag>
          </a-list-item>
        </a-list>
      </div>

      <div class="mango-section-card">
        <div class="mango-section-title">
          <div>
            <h2>导航与轻提示</h2>
            <p>面包屑、分割线、Tooltip、Popover 用于降低复杂页的理解成本。</p>
          </div>
        </div>
        <a-breadcrumb class="theme-breadcrumb">
          <a-breadcrumb-item>接口自动化</a-breadcrumb-item>
          <a-breadcrumb-item>组合场景</a-breadcrumb-item>
          <a-breadcrumb-item>订单创建主流程</a-breadcrumb-item>
        </a-breadcrumb>
        <a-divider />
        <div class="button-row">
          <a-tooltip content="用于解释图标按钮或被截断字段" mini>
            <a-button size="small">Tooltip</a-button>
          </a-tooltip>
          <a-popover title="字段说明" trigger="click">
            <a-button size="small">Popover</a-button>
            <template #content>
              <p class="popover-copy">用于展示轻量帮助、字段解释和临时操作集合。</p>
            </template>
          </a-popover>
          <a-button size="small" type="outline">Outline</a-button>
          <a-button size="small" type="dashed">Dashed</a-button>
        </div>
      </div>
    </section>

    <section class="component-grid">
      <div class="mango-section-card">
        <div class="mango-section-title">
          <div>
            <h2>代码与 JSON 展示</h2>
            <p>JSON 与 Python 分开展示，模拟 PyCharm 深色编辑器的阅读体验。</p>
          </div>
        </div>
        <div class="editor-stack">
          <div class="editor-panel">
            <div class="editor-title">
              <span>response.json</span>
              <em>JSON</em>
            </div>
            <pre><code v-html="jsonExample"></code></pre>
          </div>
          <div class="editor-panel">
            <div class="editor-title">
              <span>test_order.py</span>
              <em>Python</em>
            </div>
            <pre><code v-html="pythonExample"></code></pre>
          </div>
        </div>
      </div>

      <div class="mango-section-card">
        <div class="mango-section-title">
          <div>
            <h2>消息与侧栏</h2>
            <p>通知、日志、帮助说明适合使用右侧抽屉和轻量提示。</p>
          </div>
          <a-button size="small" @click="modalVisible = true">打开弹窗</a-button>
        </div>
        <div class="message-list">
          <div v-for="item in messages" :key="item.title" class="message-item">
            <span :class="item.type"></span>
            <div>
              <strong>{{ item.title }}</strong>
              <p>{{ item.content }}</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="mango-section-card">
      <div class="mango-section-title">
        <div>
          <h2>主题工程验收</h2>
          <p>用于检查全局主题是否从视觉试验沉淀为可维护的工程规则。</p>
        </div>
        <a-tag color="green" size="small">Theme QA</a-tag>
      </div>
      <div class="audit-grid">
        <div v-for="group in auditGroups" :key="group.title" class="audit-card">
          <div class="audit-head">
            <span>{{ group.title }}</span>
            <a-tag :color="group.color" size="small">{{ group.status }}</a-tag>
          </div>
          <ul>
            <li v-for="item in group.items" :key="item">{{ item }}</li>
          </ul>
        </div>
      </div>
      <div class="audit-command">
        <span>扫描命令</span>
        <code>npm run theme:audit</code>
        <em>发现新增硬编码颜色时，优先改为 --m-* token。</em>
      </div>
    </section>

    <a-drawer v-model:visible="drawerVisible" :width="560" title="主题抽屉样式">
      <a-form :model="drawerForm" layout="vertical">
        <a-form-item label="任务名称">
          <a-input v-model="drawerForm.name" />
        </a-form-item>
        <a-form-item label="执行模式">
          <a-radio-group v-model="drawerForm.mode">
            <a-radio value="serial">串行</a-radio>
            <a-radio value="parallel">并行</a-radio>
          </a-radio-group>
        </a-form-item>
        <a-form-item label="失败通知">
          <a-checkbox v-model="drawerForm.failNotice">仅失败时通知</a-checkbox>
        </a-form-item>
      </a-form>
      <template #footer>
        <a-button @click="drawerVisible = false">取消</a-button>
        <a-button type="primary" @click="drawerVisible = false">保存</a-button>
      </template>
    </a-drawer>

    <a-modal v-model:visible="modalVisible" title="主题弹窗样式" width="420px">
      <p class="mango-muted-text"
        >弹窗用于确认、短表单和不可打断的重点提示。按钮、边框、标题和正文都沿用同一套 token。</p
      >
    </a-modal>
  </div>
</template>

<script lang="ts" setup>
  import { reactive, ref } from 'vue'
  import AddButton from '@/components/actions/AddButton.vue'
  import DeleteButton from '@/components/actions/DeleteButton.vue'
  import AssertionResult from '@/components/feedback/AssertionResult.vue'
  import PasswordStrong from '@/components/forms/PasswordStrong.vue'
  import SortableTable from '@/components/table/SortableTable.vue'
  import TableConfig from '@/components/table/TableConfig.vue'
  import TipMessage from '@/components/feedback/TipMessage.vue'

  const drawerVisible = ref(false)
  const modalVisible = ref(false)
  const tableFilter = ref('all')
  const selectedRowKeys = ref(['10421', '10423'])
  const tableConfigState = ref('等待操作')
  const passwordSample = ref('Mango2026')
  const visibleCustomColumns = ref<any[]>([])

  const formModel = reactive({
    keyword: '',
    product: '',
    status: '',
    date: '',
    time: '',
    retry: 2,
    tags: ['冒烟', 'P0'],
    owner: '',
    notice: true,
  })

  const drawerForm = reactive({
    name: '每日冒烟测试',
    mode: 'parallel',
    failNotice: true,
  })

  const colorTokens = [
    { name: 'Primary', value: 'var(--m-primary)' },
    { name: 'Primary Soft', value: 'var(--m-primary-soft)' },
    { name: 'Background', value: 'var(--m-bg)' },
    { name: 'Surface', value: 'var(--m-surface)' },
    { name: 'Border', value: 'var(--m-border)' },
    { name: 'Text', value: 'var(--m-text)' },
    { name: 'Success', value: 'var(--m-success)' },
    { name: 'Danger', value: 'var(--m-danger)' },
    { name: 'Warning', value: 'var(--m-warning)' },
    { name: 'Muted', value: 'var(--m-muted)' },
  ]

  const customColumns = [
    { title: '用例名称', key: 'name' },
    { title: '接口名称', key: 'apiName' },
    { title: '执行环境', key: 'env' },
    { title: '测试结果', key: 'status' },
    { title: '更新时间', key: 'updatedAt', width: 180 },
  ]

  visibleCustomColumns.value = [...customColumns]

  const onCustomColumnsUpdate = (columns: any[]) => {
    visibleCustomColumns.value = columns
    tableConfigState.value = `已显示 ${columns.length} 列`
  }

  const assertionResultItems = [
    {
      method: '状态码等于',
      actual: '500',
      expect: '200',
      ass_msg: '状态码断言失败，接口返回服务器异常，请检查订单服务日志',
      status: 0,
    },
    {
      method: '响应字段包含',
      actual: 'order_no, status, amount',
      expect: 'order_no',
      ass_msg: '响应字段存在',
      status: 1,
    },
  ]

  const keyValueItems = [
    { key: 'Authorization', value: 'Bearer ********', type: 'Header', color: 'blue' },
    { key: 'order_no', value: '${orderNo}', type: 'Param', color: 'green' },
    { key: 'cleanup', value: 'after_case', type: 'Config', color: 'orange' },
  ]

  const progressItems = [
    { label: 'UI 自动化', percent: 0.76 },
    { label: 'API 自动化', percent: 0.92 },
    { label: 'Pytest', percent: 0.58 },
  ]

  const statusOptions = [
    { label: '成功', value: 'success' },
    { label: '失败', value: 'fail' },
    { label: '进行中', value: 'running' },
  ]

  const productOptions = [
    {
      label: 'Mango 平台',
      value: 'mango',
      children: [
        { label: '控制台', value: 'console' },
        { label: '执行器', value: 'actuator' },
      ],
    },
  ]

  const treeData = [
    {
      key: 'team',
      title: '测试团队',
      children: [
        { key: 'admin', title: 'Admin' },
        { key: 'tester', title: 'Tester' },
      ],
    },
  ]

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 90 },
    {
      title: '用例名称',
      dataIndex: 'name',
      width: 220,
      ellipsis: true,
      tooltip: true,
      align: 'left',
    },
    {
      title: '模块',
      dataIndex: 'module',
      width: 150,
      ellipsis: true,
      tooltip: true,
      align: 'left',
    },
    { title: '等级', slotName: 'level', width: 100 },
    { title: '维护人', dataIndex: 'owner', width: 110 },
    { title: '状态', slotName: 'status', width: 110 },
    { title: '启用', slotName: 'enabled', width: 90 },
    { title: '更新时间', dataIndex: 'updatedAt', width: 180 },
    { title: '说明', dataIndex: 'description', ellipsis: true, tooltip: true, align: 'left' },
    { title: '操作', slotName: 'actions', fixed: 'right', width: 170 },
  ]

  const rows = [
    {
      id: '10421',
      name: '订单创建主流程校验',
      module: '订单中心',
      level: 'P0',
      levelColor: 'red',
      owner: 'Admin',
      status: '成功',
      statusColor: 'green',
      enabled: true,
      updatedAt: '2026-05-22 10:32:08',
      description: '覆盖创建订单、库存冻结、支付单生成等关键链路。',
    },
    {
      id: '10422',
      name: '支付回调签名异常场景',
      module: '支付中心',
      level: 'P1',
      levelColor: 'orange',
      owner: 'Mango',
      status: '失败',
      statusColor: 'red',
      enabled: true,
      updatedAt: '2026-05-22 10:34:19',
      description: '断言失败：response.code 期望为 200，实际为 500。',
    },
    {
      id: '10423',
      name: '用户权限边界校验',
      module: '用户权限',
      level: 'P1',
      levelColor: 'orange',
      owner: 'Tester',
      status: '进行中',
      statusColor: 'blue',
      enabled: false,
      updatedAt: '2026-05-22 10:38:01',
      description: '验证角色、菜单、接口权限的组合边界。',
    },
  ]

  const messages = [
    { type: 'info', title: '通知中心', content: '用于展示 WebSocket 消息、系统通知和执行提醒。' },
    { type: 'success', title: '执行完成', content: '成功反馈轻量出现，不打断用户继续排查。' },
    { type: 'danger', title: '异常提示', content: '失败信息保留红色语义，但避免大面积警告色。' },
  ]

  const statisticItems = [
    { label: '今日执行', value: 128, precision: 0, trend: '+12%', color: 'blue' },
    { label: '成功率', value: 96.8, precision: 1, trend: '稳定', color: 'green' },
    { label: '失败用例', value: 7, precision: 0, trend: '需关注', color: 'red' },
    { label: '平均耗时', value: 2.35, precision: 2, trend: '秒', color: 'orange' },
  ]

  const trendItems = [
    { week: 'W1', success: 82, fail: 14 },
    { week: 'W2', success: 104, fail: 18 },
    { week: 'W3', success: 76, fail: 10 },
    { week: 'W4', success: 118, fail: 16 },
    { week: 'W5', success: 94, fail: 20 },
    { week: 'W6', success: 126, fail: 12 },
    { week: 'W7', success: 108, fail: 8 },
    { week: 'W8', success: 132, fail: 15 },
  ]

  const rankItems = [
    { name: '订单中心', value: 96, count: 428 },
    { name: '支付中心', value: 78, count: 352 },
    { name: '用户权限', value: 62, count: 286 },
    { name: '数据工厂', value: 48, count: 214 },
    { name: '监控任务', value: 36, count: 168 },
  ]

  const chartStatusItems = [
    { label: '成功', value: 963, percent: 88, type: 'success' },
    { label: '失败', value: 42, percent: 28, type: 'danger' },
    { label: '进行中', value: 18, percent: 18, type: 'running' },
  ]

  const auditGroups = [
    {
      title: 'Token 使用',
      status: '必需',
      color: 'blue',
      items: ['页面背景使用 --m-bg', '卡片面板使用 --m-surface', '状态反馈使用语义 token'],
    },
    {
      title: '组件覆盖',
      status: '已覆盖',
      color: 'green',
      items: [
        'Arco 表格、表单、弹窗、抽屉读取主题',
        '自定义组件读取 --m-*',
        '图表监听主题变化刷新',
      ],
    },
    {
      title: '允许例外',
      status: '受控',
      color: 'orange',
      items: ['代码高亮保留 PyCharm 风格', '业务枚举色可保留', '图表 fallback 仅作兜底'],
    },
    {
      title: '验收页面',
      status: '建议',
      color: 'purple',
      items: ['登录页', '首页', '报告详情', 'API/UI 详情', '系统设置与数据工厂'],
    },
  ]

  const notificationItems = [
    {
      title: '执行器节点 online-runner-01',
      description: 'Windows / Chrome 126 / 空闲中',
      avatar: 'UI',
      color: 'var(--m-primary)',
      status: '在线',
      tagColor: 'green',
    },
    {
      title: '接口回归任务完成',
      description: '128 条用例，失败 7 条，耗时 18m 24s',
      avatar: 'API',
      color: 'var(--m-success)',
      status: '已通知',
      tagColor: 'blue',
    },
    {
      title: 'Pytest 环境依赖异常',
      description: 'requirements.txt 安装失败，等待处理',
      avatar: 'PY',
      color: 'var(--m-danger)',
      status: '异常',
      tagColor: 'red',
    },
  ]

  const jsonExample = `<span class="syntax-brace">{</span>
  <span class="syntax-key">"theme"</span>: <span class="syntax-string">"enterprise-data-dense"</span>,
  <span class="syntax-key">"primary"</span>: <span class="syntax-string">"#1E40AF"</span>,
  <span class="syntax-key">"surface"</span>: <span class="syntax-string">"#FFFFFF"</span>,
  <span class="syntax-key">"table"</span>: <span class="syntax-brace">{</span>
    <span class="syntax-key">"bordered"</span>: <span class="syntax-bool">false</span>,
    <span class="syntax-key">"hover"</span>: <span class="syntax-string">"#EFF6FF"</span>,
    <span class="syntax-key">"density"</span>: <span class="syntax-string">"compact"</span>
  <span class="syntax-brace">}</span>
<span class="syntax-brace">}</span>`

  const pythonExample = `<span class="syntax-keyword">import</span> <span class="syntax-module">pytest</span>


<span class="syntax-keyword">def</span> <span class="syntax-function">test_create_order</span><span class="syntax-brace">(</span>api_client, order_payload<span class="syntax-brace">)</span>:
    response = api_client.<span class="syntax-method">post</span><span class="syntax-brace">(</span><span class="syntax-string">"/api/orders"</span>, json=order_payload<span class="syntax-brace">)</span>
    body = response.<span class="syntax-method">json</span><span class="syntax-brace">()</span>

    <span class="syntax-keyword">assert</span> response.status_code == <span class="syntax-number">200</span>
    <span class="syntax-keyword">assert</span> body<span class="syntax-brace">[</span><span class="syntax-string">"code"</span><span class="syntax-brace">]</span> == <span class="syntax-number">0</span>
    <span class="syntax-keyword">assert</span> body<span class="syntax-brace">[</span><span class="syntax-string">"data"</span><span class="syntax-brace">][</span><span class="syntax-string">"order_no"</span><span class="syntax-brace">]</span>`

  const miniJsonExample = `<span class="syntax-brace">{</span>
  <span class="syntax-key">"code"</span>: <span class="syntax-number">0</span>,
  <span class="syntax-key">"message"</span>: <span class="syntax-string">"success"</span>,
  <span class="syntax-key">"trace_id"</span>: <span class="syntax-string">"mango-20260522"</span>
<span class="syntax-brace">}</span>`
</script>

<style scoped lang="less">
  .theme-lab {
    height: 100%;
    overflow: auto;
    padding: 14px;
    background: linear-gradient(
        180deg,
        var(--m-primary-soft),
        color-mix(in srgb, var(--m-surface) 0%, transparent) 260px
      ),
      var(--m-bg);
    color: var(--m-text);
  }

  h1,
  h2,
  p {
    margin: 0;
  }

  .lab-head,
  .mango-section-card {
    border: 1px solid var(--m-border);
    border-radius: 8px;
    background: var(--m-surface);
    box-shadow: var(--m-shadow);
  }

  .lab-head {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 280px;
    gap: 16px;
    align-items: stretch;
    padding: 18px;
  }

  .eyebrow {
    color: var(--m-primary);
    font-size: 12px;
    font-weight: 700;
  }

  .lab-head h1 {
    margin-top: 6px;
    font-size: 26px;
    line-height: 34px;
    font-weight: 750;
  }

  .sub-title,
  .mango-section-title p,
  .table-toolbar p,
  .mango-muted-text,
  .message-item p {
    color: var(--m-muted);
    font-size: 13px;
  }

  .head-card {
    display: grid;
    align-content: center;
    gap: 6px;
    padding: 14px;
    border: 1px solid var(--m-primary-border);
    border-radius: 8px;
    background: linear-gradient(135deg, var(--m-primary-soft), var(--m-surface));
  }

  .head-card span,
  .head-card em {
    color: var(--m-muted);
    font-size: 12px;
    font-style: normal;
  }

  .head-card strong {
    color: var(--m-primary);
    font-size: 20px;
  }

  .mango-section-card {
    margin-top: 10px;
    padding: 14px;
  }

  .mango-section-title,
  .table-toolbar,
  .title-actions,
  .button-row,
  .tag-row,
  .progress-row,
  .message-item {
    display: flex;
    align-items: center;
  }

  .mango-section-title,
  .table-toolbar {
    justify-content: space-between;
    gap: 14px;
    margin-bottom: 12px;
  }

  .mango-section-title h2,
  .table-toolbar h2 {
    font-size: 16px;
  }

  .token-grid {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 10px;
  }

  .token-item {
    display: grid;
    grid-template-columns: 30px minmax(0, 1fr);
    gap: 3px 10px;
    align-items: center;
    padding: 10px;
    border: 1px solid var(--m-border);
    border-radius: 8px;
    background: var(--m-surface);
  }

  .token-item i {
    grid-row: span 2;
    width: 30px;
    height: 30px;
    border: 1px solid var(--m-border);
    border-radius: 6px;
  }

  .token-item span,
  .token-item strong {
    font-size: 12px;
  }

  .token-item span {
    color: var(--m-muted);
  }

  .component-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
  }

  .type-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 10px;
  }

  .type-card {
    min-height: 132px;
    padding: 12px;
    border: 1px solid var(--m-border);
    border-radius: 8px;
    background: var(--m-surface);
  }

  .type-card span {
    display: block;
    margin-bottom: 10px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .type-card strong {
    display: block;
    margin-bottom: 8px;
    color: var(--m-text);
    line-height: 1.35;
  }

  .type-card p {
    color: var(--m-muted);
    font-size: 12px;
    line-height: 20px;
  }

  .page-title-sample strong {
    font-size: 22px;
    font-weight: 700;
  }

  .detail-title-sample strong {
    font-size: 18px;
    font-weight: 650;
  }

  .section-title-sample strong {
    font-size: 16px;
    font-weight: 600;
  }

  .table-title-sample strong {
    color: var(--m-text-2);
    font-size: 14px;
    font-weight: 600;
  }

  .body-title-sample strong {
    color: var(--m-text-2);
    font-size: 13px;
    font-weight: 500;
  }

  .meta-title-sample strong {
    color: var(--m-muted);
    font-size: 12px;
    font-weight: 600;
  }

  .button-row,
  .tag-row,
  .title-actions {
    gap: 8px;
    flex-wrap: wrap;
  }

  .success-action-btn {
    border-color: var(--m-success) !important;
    background: var(--m-success) !important;
    color: var(--m-on-primary) !important;
  }

  .success-action-btn:hover,
  .success-action-btn:focus {
    border-color: color-mix(in srgb, var(--m-success) 86%, var(--m-text)) !important;
    background: color-mix(in srgb, var(--m-success) 86%, var(--m-text)) !important;
    color: var(--m-on-primary) !important;
  }

  .custom-component-card {
    :deep(.arco-btn-circle) {
      border-color: var(--m-border-strong);
      color: var(--m-text-2);
      background: var(--m-surface);
    }

    :deep(.arco-btn-status-success) {
      border-color: var(--m-primary-border);
      color: var(--m-primary);
      background: var(--m-primary-soft);
    }

    :deep(.mango-tip-message) {
      align-items: center;
      line-height: 20px;
    }
  }

  .custom-toolbar {
    display: flex;
    align-items: center;
    gap: 10px;
    min-height: 42px;
    padding: 10px;
    border: 1px solid var(--m-border);
    border-radius: 8px;
    background: var(--m-surface);
  }

  .custom-toolbar > span {
    color: var(--m-text-2);
    font-size: 13px;
    font-weight: 600;
  }

  .custom-toolbar em {
    margin-left: auto;
    color: var(--m-muted);
    font-size: 12px;
    font-style: normal;
  }

  .column-preview {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 10px;
  }

  .password-preview {
    max-width: 360px;
    margin-top: 10px;

    :deep(.tip) {
      height: 8px;
      border-radius: 999px;
    }

    :deep(.normal) {
      background: var(--m-border);
    }

    :deep(.low) {
      background: color-mix(in srgb, var(--m-danger) 22%, transparent);
    }

    :deep(.middle) {
      background: color-mix(in srgb, var(--m-warning) 28%, transparent);
    }

    :deep(.strong) {
      background: var(--m-primary-border);
    }

    :deep(span:last-child) {
      color: var(--m-muted);
      font-size: 12px;
    }
  }

  .kv-preview {
    display: grid;
    gap: 10px;
  }

  .kv-row span {
    display: block;
    color: var(--m-muted);
    font-size: 12px;
  }

  .kv-row strong {
    color: var(--m-text-2);
    font-size: 13px;
    font-weight: 600;
  }

  .kv-row {
    display: grid;
    grid-template-columns: 120px minmax(0, 1fr) max-content;
    gap: 10px;
    align-items: center;
    padding: 8px 10px;
    border: 1px solid var(--m-border);
    border-radius: 8px;
    background: var(--m-surface);
  }

  .kv-row strong {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mini-json {
    margin: 10px 0 0;
    padding: 10px 12px;
    overflow: auto;
    border: 1px solid var(--m-code-border);
    border-radius: 8px;
    background: var(--m-code-bg);
    color: var(--m-code-text);
    font-family: 'JetBrains Mono', Consolas, 'Courier New', monospace;
    font-size: 12px;
    line-height: 1.7;
  }

  .button-row + .button-row,
  .progress-list {
    margin-top: 12px;
  }

  .compact {
    padding-top: 10px;
    border-top: 1px dashed var(--m-border);
  }

  .progress-row {
    display: grid;
    grid-template-columns: 92px minmax(0, 1fr) 42px;
    gap: 10px;
    color: var(--m-text-2);
    font-size: 13px;
  }

  .semantic-alert {
    margin-top: 12px;
    border: 1px solid var(--m-primary-border);
    border-radius: 8px;
    background: var(--m-surface-soft);

    :deep(.arco-alert-icon) {
      color: var(--m-primary);
    }

    :deep(.arco-alert-content) {
      color: var(--m-text-2);
    }
  }

  .progress-row + .progress-row {
    margin-top: 10px;
  }

  .progress-row em {
    color: var(--m-muted);
    font-style: normal;
    text-align: right;
  }

  .filter-form {
    :deep(.arco-form-item) {
      margin-bottom: 10px;
    }

    :deep(.arco-input-wrapper),
    :deep(.arco-select-view-single),
    :deep(.arco-picker),
    :deep(.arco-input-tag),
    :deep(.arco-input-number) {
      width: 190px;
      border-radius: 6px;
    }
  }

  .table-section {
    padding: 0;
    overflow: hidden;
  }

  .table-toolbar {
    margin-bottom: 0;
    padding: 12px 14px;
    border-bottom: 1px solid var(--m-border);
    background: var(--m-surface-soft);
  }

  .table-toolbar p {
    display: flex;
    align-items: center;
    gap: 7px;
    margin-top: 4px;
  }

  .table-toolbar p i {
    width: 4px;
    height: 4px;
    border-radius: 50%;
    background: var(--m-border-strong);
  }

  .theme-table {
    :deep(.arco-table-container) {
      border: 0;
    }

    :deep(.arco-table-th) {
      background: var(--m-surface-soft);
      color: var(--m-muted);
      font-weight: 600;
      border-right: 0;
    }

    :deep(.arco-table-td) {
      color: var(--m-text-2);
      border-right: 0;
      transition: background-color 0.2s ease;
    }

    :deep(.arco-table-tr:hover .arco-table-td) {
      background: var(--m-primary-soft);
    }

    :deep(.arco-table-cell) {
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .mango-table-footer-preview {
    display: flex;
    justify-content: flex-end;
    padding: 10px 14px;
    border-top: 1px solid var(--m-border);
    background: var(--m-surface);
  }

  .theme-upload {
    display: block;

    :deep(.arco-upload) {
      width: 100%;
    }
  }

  .upload-drop {
    display: grid;
    place-items: center;
    min-height: 112px;
    border: 1px dashed var(--m-primary-border);
    border-radius: 8px;
    background: var(--m-surface-soft);
    color: var(--m-primary);
    text-align: center;
  }

  .upload-drop span {
    margin-top: 4px;
    color: var(--m-muted);
    font-size: 12px;
  }

  .state-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
    margin-top: 10px;
  }

  .state-card {
    display: grid;
    place-items: center;
    min-height: 96px;
    border: 1px solid var(--m-border);
    border-radius: 8px;
    background: var(--m-surface);
  }

  .theme-empty-demo {
    width: 100%;
    min-height: 72px;
    border: 0;
  }

  .stat-card {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    min-height: 86px;
    padding: 12px;
    border: 1px solid var(--m-border);
    border-radius: 8px;
    background: var(--m-surface);
  }

  .stat-card :deep(.arco-statistic-title) {
    color: var(--m-muted);
    font-size: 12px;
  }

  .stat-card :deep(.arco-statistic-value) {
    color: var(--m-text);
    font-size: 24px;
    font-weight: 650;
  }

  .theme-list {
    :deep(.arco-list-item) {
      padding: 10px;
      border: 1px solid var(--m-border);
      border-radius: 8px;
      background: var(--m-surface);
    }

    :deep(.arco-list-item + .arco-list-item) {
      margin-top: 10px;
    }

    :deep(.arco-list-item-meta-title) {
      color: var(--m-text);
      font-size: 13px;
      font-weight: 600;
    }

    :deep(.arco-list-item-meta-description) {
      color: var(--m-muted);
      font-size: 12px;
    }
  }

  .chart-grid {
    display: grid;
    grid-template-columns: minmax(260px, 0.9fr) minmax(420px, 1.35fr) minmax(260px, 1fr) minmax(
        260px,
        1fr
      );
    gap: 10px;
  }

  .chart-card {
    min-height: 260px;
    padding: 12px;
    border: 1px solid var(--m-border);
    border-radius: 8px;
    background: var(--m-surface);
  }

  .chart-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 10px;
    margin-bottom: 12px;
  }

  .chart-head strong {
    display: block;
    color: var(--m-text);
    font-size: 14px;
    font-weight: 600;
  }

  .chart-head span,
  .chart-head em {
    color: var(--m-muted);
    font-size: 12px;
    font-style: normal;
  }

  .donut-chart {
    display: grid;
    place-items: center;
    width: 148px;
    height: 148px;
    margin: 10px auto 14px;
    border-radius: 50%;
    background: conic-gradient(
      var(--m-primary) var(--p1),
      var(--m-success) var(--p2),
      var(--m-warning) var(--p3)
    );
  }

  .donut-chart > div {
    display: grid;
    place-items: center;
    width: 94px;
    height: 94px;
    border-radius: 50%;
    background: var(--m-surface);
  }

  .donut-chart strong {
    color: var(--m-text);
    font-size: 24px;
    line-height: 28px;
  }

  .donut-chart span {
    color: var(--m-muted);
    font-size: 12px;
  }

  .chart-legend {
    display: flex;
    justify-content: center;
    gap: 12px;
    flex-wrap: wrap;
    color: var(--m-muted);
    font-size: 12px;
  }

  .chart-legend span {
    display: inline-flex;
    align-items: center;
    gap: 5px;
  }

  .chart-legend i {
    width: 8px;
    height: 8px;
    border-radius: 999px;
  }

  .chart-legend .blue {
    background: var(--m-primary);
  }

  .chart-legend .green {
    background: var(--m-success);
  }

  .chart-legend .orange {
    background: var(--m-warning);
  }

  .chart-legend .red {
    background: var(--m-danger);
  }

  .bar-chart {
    display: grid;
    grid-template-columns: repeat(8, minmax(26px, 1fr));
    align-items: end;
    gap: 12px;
    height: 176px;
    padding: 18px 8px 0;
    border-bottom: 1px solid var(--m-border);
    background: linear-gradient(to top, var(--m-border) 1px, transparent 1px) 0 0 / 100% 44px,
      var(--m-surface);
  }

  .bar-column {
    display: grid;
    justify-items: center;
    gap: 8px;
  }

  .bar-stack {
    display: flex;
    align-items: end;
    gap: 4px;
    height: 138px;
  }

  .bar-stack i {
    width: 10px;
    min-height: 4px;
    border-radius: 999px 999px 2px 2px;
  }

  .bar-stack .success {
    background: var(--m-primary);
  }

  .bar-stack .danger {
    background: var(--m-danger);
  }

  .bar-column span {
    color: var(--m-muted);
    font-size: 11px;
  }

  .rank-chart,
  .status-summary {
    display: grid;
    gap: 12px;
    margin-top: 18px;
  }

  .rank-row {
    display: grid;
    grid-template-columns: 70px minmax(0, 1fr) 36px;
    align-items: center;
    gap: 8px;
    color: var(--m-text-2);
    font-size: 12px;
  }

  .rank-row div {
    height: 8px;
    overflow: hidden;
    border-radius: 999px;
    background: var(--m-border);
  }

  .rank-row i {
    display: block;
    height: 100%;
    border-radius: inherit;
    background: linear-gradient(90deg, var(--m-primary-border), var(--m-primary));
  }

  .rank-row em {
    color: var(--m-muted);
    font-style: normal;
    text-align: right;
  }

  .status-summary > div {
    position: relative;
    display: grid;
    grid-template-columns: 1fr max-content;
    gap: 8px;
    padding-bottom: 12px;
    color: var(--m-text-2);
    font-size: 13px;
  }

  .status-summary strong {
    font-size: 18px;
    font-weight: 650;
  }

  .status-summary i {
    grid-column: 1 / -1;
    height: 8px;
    border-radius: 999px;
  }

  .status-summary .success i {
    background: var(--m-success);
  }

  .status-summary .danger i {
    background: var(--m-danger);
  }

  .status-summary .running i {
    background: var(--m-warning);
  }

  .audit-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 10px;
  }

  .audit-card {
    padding: 12px;
    border: 1px solid var(--m-border);
    border-radius: 8px;
    background: var(--m-surface-soft);
  }

  .audit-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 8px;
  }

  .audit-head span {
    color: var(--m-text);
    font-size: 13px;
    font-weight: 650;
  }

  .audit-card ul {
    display: grid;
    gap: 6px;
    margin: 0;
    padding-left: 16px;
    color: var(--m-text-2);
    font-size: 12px;
    line-height: 18px;
  }

  .audit-command {
    display: grid;
    grid-template-columns: max-content max-content minmax(0, 1fr);
    align-items: center;
    gap: 10px;
    margin-top: 10px;
    padding: 10px 12px;
    border: 1px solid var(--m-border);
    border-radius: 8px;
    background: var(--m-surface);
    color: var(--m-muted);
    font-size: 12px;
  }

  .audit-command code {
    padding: 3px 8px;
    border: 1px solid var(--m-code-border);
    border-radius: 6px;
    background: var(--m-code-bg);
    color: var(--m-code-text);
    font-family: 'JetBrains Mono', Consolas, 'Courier New', monospace;
  }

  .theme-breadcrumb {
    :deep(.arco-breadcrumb-item) {
      color: var(--m-muted);
    }

    :deep(.arco-breadcrumb-item:last-child) {
      color: var(--m-text);
      font-weight: 600;
    }
  }

  .popover-copy {
    max-width: 220px;
    color: var(--m-text-2);
    font-size: 13px;
  }

  :deep(.arco-btn) {
    border-radius: 6px;
  }

  :deep(.arco-btn-primary) {
    background: var(--m-primary);
  }

  :deep(.arco-btn-primary:hover) {
    background: var(--m-primary-hover);
  }

  :deep(.arco-radio-button.arco-radio-checked) {
    color: var(--m-primary);
    background: var(--m-primary-soft);
  }

  :deep(.arco-tabs-tab-active) {
    color: var(--m-primary);
  }

  :deep(.arco-descriptions-bordered .arco-descriptions-item-label) {
    background: var(--m-surface-soft);
    color: var(--m-muted);
  }

  .theme-timeline {
    margin-top: 6px;
  }

  .editor-stack {
    display: grid;
    gap: 10px;
  }

  .editor-panel {
    overflow: hidden;
    border: 1px solid var(--m-code-border);
    border-radius: 8px;
    background: var(--m-code-bg);
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
  }

  .editor-title {
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 32px;
    padding: 0 12px;
    border-bottom: 1px solid var(--m-code-border);
    background: color-mix(in srgb, var(--m-code-bg) 88%, #ffffff);
    color: var(--m-code-comment);
    font-size: 12px;
  }

  .editor-title span {
    color: var(--m-code-text);
  }

  .editor-title em {
    color: var(--m-code-comment);
    font-style: normal;
  }

  .editor-panel pre {
    min-height: 150px;
    margin: 0;
    padding: 12px 14px;
    overflow: auto;
    color: var(--m-code-text);
    font-family: 'JetBrains Mono', Consolas, 'Courier New', monospace;
    font-size: 13px;
    line-height: 1.68;
    tab-size: 2;
  }

  .syntax-key,
  .syntax-function {
    color: var(--m-code-function);
    font-weight: 650;
  }

  .syntax-string {
    color: var(--m-code-string);
  }

  .syntax-keyword,
  .syntax-bool {
    color: var(--m-code-keyword);
    font-weight: 600;
  }

  .syntax-number {
    color: var(--m-code-number);
    font-weight: 650;
  }

  .syntax-module,
  .syntax-method {
    color: var(--m-code-function);
    font-weight: 600;
  }

  .syntax-brace {
    color: var(--m-code-bracket);
  }

  .message-list {
    display: grid;
    gap: 10px;
  }

  .message-item {
    gap: 10px;
    padding: 10px;
    border: 1px solid var(--m-border);
    border-radius: 8px;
    background: var(--m-surface);
  }

  .message-item > span {
    flex: none;
    width: 8px;
    height: 8px;
    border-radius: 999px;
  }

  .message-item .info {
    background: var(--m-primary);
  }

  .message-item .success {
    background: var(--m-success);
  }

  .message-item .danger {
    background: var(--m-danger);
  }

  .message-item strong {
    font-size: 13px;
  }

  @media (max-width: 1px) {
    .token-grid {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }

    .type-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .component-grid {
      grid-template-columns: 1fr;
    }

    .chart-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .audit-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 1px) {
    .theme-lab {
      padding: 8px;
    }

    .lab-head,
    .token-grid,
    .type-grid {
      grid-template-columns: 1fr;
    }

    .mango-section-title,
    .table-toolbar {
      align-items: flex-start;
      flex-direction: column;
    }

    .chart-grid {
      grid-template-columns: 1fr;
    }

    .audit-grid,
    .audit-command {
      grid-template-columns: 1fr;
    }
  }
</style>
