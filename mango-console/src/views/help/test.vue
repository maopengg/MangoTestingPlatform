<template>
  <div class="theme-lab mango-theme-lab">
    <section class="lab-head">
      <div>
        <p class="eyebrow">MANGO CONSOLE DESIGN SYSTEM</p>
        <h1>企业级 SaaS 组件主题验收</h1>
        <p class="sub-title">本地样式示例，业务按钮不提交数据；断言 AI 分析沿用公共组件。</p>
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
          <strong>API自动化配置</strong>
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
          <a-button type="primary" data-testid="qa-views-help-test-button-主操作">主操作</a-button>
          <a-button class="success-action-btn" type="primary" status="success" data-testid="qa-views-help-test-button-执行">执行</a-button>
          <a-button class="success-action-btn" type="primary" status="success" data-testid="qa-views-help-test-button-调试">调试</a-button>
          <a-button status="danger" data-testid="qa-views-help-test-button-删除">删除</a-button>
          <a-button data-testid="qa-views-help-test-button-次要">次要</a-button>
          <a-button
            class="mango-back-button"
            type="primary"
            status="warning"
            data-testid="qa-views-help-test-button-后退"
            :loading="navigationLoading"
            @click="goBack"
          >
            后退
          </a-button>
          <a-button type="text" data-testid="qa-views-help-test-button-文本按钮">文本按钮</a-button>
        </div>
        <div class="button-row compact">
          <AddButton />
          <DeleteButton />
          <a-dropdown trigger="hover">
            <a-button size="mini" type="text" data-testid="qa-views-help-test-button-更多">更多</a-button>
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
          border-radius="7px"
          margin-bottom="10px"
        />
        <a-input-password v-model="passwordSample" placeholder="输入密码查看强度" allow-clear data-testid="qa-views-help-test-input-password-输入密码查看强度" />
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
          <a-button size="small" @click="resetFilters" data-testid="qa-views-help-test-button-重置">重置</a-button>
          <a-button size="small" type="primary" data-testid="qa-views-help-test-button-搜索">搜索</a-button>
        </div>
      </div>
      <a-form layout="inline" :model="formModel" class="filter-form">
        <a-form-item label="关键字">
          <a-input v-model="formModel.keyword" placeholder="请输入用例/接口名称" allow-clear data-testid="qa-views-help-test-input-请输入用例-接口名称" />
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
            allow-clear data-testid="qa-views-help-test-select-请选择"
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
          <a-input-tag v-model="formModel.tags" placeholder="输入后回车" allow-clear data-testid="qa-views-help-test-input-tag-输入后回车" />
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
            <span>已选择 {{ selectedRowKeys.length }} 项</span>
            <i></i>
            <span>当前示例 {{ displayedRows.length }} 条</span>
          </p>
        </div>
        <div class="title-actions">
          <a-radio-group v-model="tableFilter" type="button" size="small">
            <a-radio value="all" data-testid="qa-views-help-test-radio-全部">全部</a-radio>
            <a-radio value="fail" data-testid="qa-views-help-test-radio-失败">失败</a-radio>
            <a-radio value="success" data-testid="qa-views-help-test-radio-成功">成功</a-radio>
          </a-radio-group>
          <a-button size="small" status="danger" data-testid="qa-views-help-test-button-批量删除">批量删除</a-button>
          <a-button size="small" type="primary" data-testid="qa-views-help-test-button-新增">新增</a-button>
        </div>
      </div>
      <a-table
        :bordered="false"
        :columns="columns"
        :data="displayedRows"
        :loading="false"
        :pagination="false"
        v-model:selected-keys="selectedRowKeys"
        :row-selection="{ type: 'checkbox', showCheckedAll: true }"
        :scroll="{ x: tableScrollX }"
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
          <a-switch v-model="record.enabled"  />
        </template>
        <template #actions>
          <MangoTableActions :actions="[
            { label: '编辑' }, { label: '执行' }, { label: '详情' },
            { label: '复制' }, { label: '查看日志' },
          ]" />
        </template>
      </a-table>
      <div class="mango-table-footer-preview">
        <a-pagination :total="displayedRows.length" :page-size="10" size="small" show-total show-jumper />
      </div>
    </section>

    <section class="component-grid">
      <div class="mango-section-card">
        <div class="mango-section-title">
          <div>
            <h2>详情信息</h2>
            <p>详情页、抽屉、报告头部可以使用描述列表和状态摘要。</p>
          </div>
          <a-button size="small" type="primary" @click="openDrawer" data-testid="qa-views-help-test-button-打开抽屉">打开抽屉</a-button>
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
          <a-tab-pane key="log" title="执行日志" data-testid="qa-views-help-test-tab-pane-执行日志">
            <a-timeline class="theme-timeline">
              <a-timeline-item label="10:32:08">开始执行测试套</a-timeline-item>
              <a-timeline-item label="10:32:11">完成接口鉴权</a-timeline-item>
              <a-timeline-item label="10:32:15" dot-color="red">订单断言失败</a-timeline-item>
            </a-timeline>
          </a-tab-pane>
          <a-tab-pane key="steps" title="步骤" data-testid="qa-views-help-test-tab-pane-步骤">
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
                <i class="success" :style="{ height: `${scaleDensityPixels(item.success)}px` }"></i>
                <i class="danger" :style="{ height: `${scaleDensityPixels(item.fail)}px` }"></i>
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
          <a-breadcrumb-item>API自动化</a-breadcrumb-item>
          <a-breadcrumb-item>组合场景</a-breadcrumb-item>
          <a-breadcrumb-item>订单创建主流程</a-breadcrumb-item>
        </a-breadcrumb>
        <a-divider />
        <div class="button-row">
          <a-tooltip content="用于解释图标按钮或被截断字段" mini>
            <a-button size="small" data-testid="qa-views-help-test-button-tooltip">Tooltip</a-button>
          </a-tooltip>
          <a-popover title="字段说明" trigger="click">
            <a-button size="small" data-testid="qa-views-help-test-button-popover">Popover</a-button>
            <template #content>
              <p class="popover-copy">用于展示轻量帮助、字段解释和临时操作集合。</p>
            </template>
          </a-popover>
          <a-button size="small" type="outline" data-testid="qa-views-help-test-button-outline">Outline</a-button>
          <a-button size="small" type="dashed" data-testid="qa-views-help-test-button-dashed">Dashed</a-button>
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
          <a-button size="small" @click="modalVisible = true" data-testid="qa-views-help-test-button-打开弹窗">打开弹窗</a-button>
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

    <a-drawer v-model:visible="drawerVisible" :width="560" title="主题抽屉样式" @cancel="cancelDrawer">
      <a-form :model="drawerForm" layout="horizontal">
        <a-form-item label="任务名称">
          <a-input v-model="drawerForm.name" />
        </a-form-item>
        <a-form-item label="执行模式">
          <a-radio-group v-model="drawerForm.mode">
            <a-radio value="serial" data-testid="qa-views-help-test-radio-串行">串行</a-radio>
            <a-radio value="parallel" data-testid="qa-views-help-test-radio-并行">并行</a-radio>
          </a-radio-group>
        </a-form-item>
        <a-form-item label="失败通知">
          <a-checkbox v-model="drawerForm.failNotice" data-testid="qa-views-help-test-checkbox-仅失败时通知">仅失败时通知</a-checkbox>
        </a-form-item>
      </a-form>
      <template #footer>
        <a-button @click="cancelDrawer" data-testid="qa-views-help-test-button-取消">取消</a-button>
        <a-button type="primary" @click="saveDrawer" data-testid="qa-views-help-test-button-保存">保存</a-button>
      </template>
    </a-drawer>

    <a-modal v-model:visible="modalVisible" title="主题弹窗样式" :width="540">
      <p class="mango-muted-text"
        >弹窗用于确认、短表单和不可打断的重点提示。按钮、边框、标题和正文都沿用同一套 token。</p
      >
    </a-modal>
  </div>
</template>

<script lang="ts" setup>
  import { computed, onActivated, onDeactivated, reactive, ref } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import type { TablePropsType } from '@/types/components'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import { scaleDensityPixels } from '@/hooks/useDisplayDensity'
  import { colorTokens, customColumns, assertionResultItems, keyValueItems, progressItems, statusOptions, productOptions, treeData, columns, sampleRows, messages, statisticItems, trendItems, rankItems, chartStatusItems, auditGroups, notificationItems, jsonExample, pythonExample, miniJsonExample, tableScrollX } from './test/config'
  import { useRouter } from 'vue-router'
  import AddButton from '@/components/actions/AddButton.vue'
  import DeleteButton from '@/components/actions/DeleteButton.vue'
  import AssertionResult from '@/components/feedback/AssertionResult.vue'
  import PasswordStrong from '@/components/forms/PasswordStrong.vue'
  import SortableTable from '@/components/table/SortableTable.vue'
  import TableConfig from '@/components/table/TableConfig.vue'
  import TipMessage from '@/components/feedback/TipMessage.vue'

  const router = useRouter()
  const drawerVisible = ref(false)
  const modalVisible = ref(false)
  const tableFilter = ref<'all' | 'fail' | 'success'>('all')
  const rows = ref(sampleRows.map(row => ({ ...row })))
  const displayedRows = computed(() => rows.value.filter(row => tableFilter.value === 'all' || row.status === (tableFilter.value === 'fail' ? '失败' : '成功')))
  const selectedRowKeys = ref(['10421', '10423'])
  const tableConfigState = ref('等待操作')
  const passwordSample = ref('Mango2026')
  const visibleCustomColumns = ref<TablePropsType[]>([])

  const navigationLoading = ref(false)
  let active = true
  let navigationGeneration = 0
  async function goBack() {
    if (!active || navigationLoading.value) return
    const generation = navigationGeneration
    navigationLoading.value = true
    try {
      if (window.history.state?.back) router.back()
      else await router.push('/index/home')
    } catch {
      if (active && generation === navigationGeneration) Message.error('返回失败，请重试')
    } finally {
      navigationLoading.value = false
    }
  }

  const createFilterForm = () => ({
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
  const formModel = reactive(createFilterForm())
  function resetFilters() { Object.assign(formModel, createFilterForm()) }

  interface DrawerForm { name: string; mode: 'serial' | 'parallel'; failNotice: boolean }
  const drawerSaved = ref<DrawerForm>({
    name: '每日冒烟测试',
    mode: 'parallel',
    failNotice: true,
  })
  const drawerForm = reactive<DrawerForm>({ ...drawerSaved.value })
  function openDrawer() { Object.assign(drawerForm, drawerSaved.value); drawerVisible.value = true }
  function cancelDrawer() { drawerVisible.value = false; Object.assign(drawerForm, drawerSaved.value) }
  function saveDrawer() { drawerSaved.value = { name: drawerForm.name, mode: drawerForm.mode, failNotice: drawerForm.failNotice }; drawerVisible.value = false }
  onDeactivated(() => { active = false; navigationGeneration++; cancelDrawer(); modalVisible.value = false })
  onActivated(() => { active = true })

  visibleCustomColumns.value = [...customColumns]

  const onCustomColumnsUpdate = (columns: TablePropsType[]) => {
    visibleCustomColumns.value = columns.map(column => ({ ...column }))
    tableConfigState.value = `已显示 ${columns.length} 列`
  }

</script>

<style scoped lang="less">
  .theme-lab {
    box-sizing: border-box;
    min-width: 0;
    height: 100%;
    overflow: auto;
    padding: var(--m-page-gap);
    background: linear-gradient(
        180deg,
        var(--m-primary-soft),
        color-mix(in srgb, var(--m-surface) 0%, transparent) 234px
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
    border-radius: var(--m-radius-lg);
    background: var(--m-surface);
    box-shadow: var(--m-shadow);
  }

  .lab-head {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 252px;
    gap: 14px;
    align-items: stretch;
    padding: 16px;
  }

  .eyebrow {
    color: var(--m-primary);
    font-size: 10px;
    font-weight: 700;
  }

  .lab-head h1 {
    margin-top: 5px;
    font-size: 22px;
    line-height: 30px;
    font-weight: 700;
  }

  .sub-title,
  .mango-section-title p,
  .table-toolbar p,
  .mango-muted-text,
  .message-item p {
    color: var(--m-muted);
    font-size: 11px;
  }

  .head-card {
    display: grid;
    align-content: center;
    gap: 5px;
    padding: 12px;
    border: 1px solid var(--m-primary-border);
    border-radius: var(--m-radius-lg);
    background: linear-gradient(135deg, var(--m-primary-soft), var(--m-surface));
  }

  .head-card span,
  .head-card em {
    color: var(--m-muted);
    font-size: 10px;
    font-style: normal;
  }

  .head-card strong {
    color: var(--m-primary);
    font-size: 18px;
  }

  .mango-section-card {
    margin-top: var(--m-page-gap);
    padding: 12px;
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
    gap: 12px;
    margin-bottom: 10px;
  }

  .mango-section-title h2,
  .table-toolbar h2 {
    font-size: 16px;
  }

  .token-grid {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 9px;
  }

  .token-item {
    display: grid;
    grid-template-columns: 27px minmax(0, 1fr);
    gap: 2px 9px;
    align-items: center;
    padding: 9px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-lg);
    background: var(--m-surface);
  }

  .token-item i {
    grid-row: span 2;
    width: 27px;
    height: 27px;
    border: 1px solid var(--m-border);
    border-radius: 5px;
  }

  .token-item span,
  .token-item strong {
    font-size: 10px;
  }

  .token-item span {
    color: var(--m-muted);
  }

  .component-grid > *,
  .chart-grid > * {
    min-width: 0;
  }

  .component-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: var(--m-page-gap);
  }

  .type-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 9px;
  }

  .type-card {
    min-height: 118px;
    padding: 10px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-lg);
    background: var(--m-surface);
  }

  .type-card span {
    display: block;
    margin-bottom: 9px;
    color: var(--m-muted);
    font-size: 10px;
    line-height: 16px;
  }

  .type-card strong {
    display: block;
    margin-bottom: 7px;
    color: var(--m-text);
    line-height: 1.35;
  }

  .type-card p {
    color: var(--m-muted);
    font-size: 10px;
    line-height: 18px;
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
    gap: 7px;
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
      line-height: 18px;
    }
  }

  .custom-toolbar {
    display: flex;
    align-items: center;
    gap: 9px;
    min-height: 37px;
    padding: 9px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-lg);
    background: var(--m-surface);
  }

  .custom-toolbar > span {
    color: var(--m-text-2);
    font-size: 11px;
    font-weight: 600;
  }

  .custom-toolbar em {
    margin-left: auto;
    color: var(--m-muted);
    font-size: 10px;
    font-style: normal;
  }

  .column-preview {
    display: flex;
    flex-wrap: wrap;
    gap: 7px;
    margin-top: 9px;
  }

  .password-preview {
    max-width: 324px;
    margin-top: 9px;

    :deep(.mango-password-strength__bar) {
      height: 7px;
      border-radius: 899px;
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
      font-size: 10px;
    }
  }

  .kv-preview {
    display: grid;
    gap: 9px;
  }

  .kv-row span {
    display: block;
    color: var(--m-muted);
    font-size: 10px;
  }

  .kv-row strong {
    color: var(--m-text-2);
    font-size: 11px;
    font-weight: 600;
  }

  .kv-row {
    display: grid;
    grid-template-columns: 108px minmax(0, 1fr) max-content;
    gap: 9px;
    align-items: center;
    padding: 7px 9px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-lg);
    background: var(--m-surface);
  }

  .kv-row strong {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mini-json {
    margin: 9px 0 0;
    padding: 9px 10px;
    overflow: auto;
    border: 1px solid var(--m-code-border);
    border-radius: var(--m-radius-lg);
    background: var(--m-code-bg);
    color: var(--m-code-text);
    font-family: 'JetBrains Mono', Consolas, 'Courier New', monospace;
    font-size: 10px;
    line-height: 1.7;
  }

  .button-row + .button-row,
  .progress-list {
    margin-top: 10px;
  }

  .compact {
    padding-top: 9px;
    border-top: 1px dashed var(--m-border);
  }

  .progress-row {
    display: grid;
    grid-template-columns: 82px minmax(0, 1fr) 37px;
    gap: 9px;
    color: var(--m-text-2);
    font-size: 11px;
  }

  .semantic-alert {
    margin-top: 10px;
    border: 1px solid var(--m-primary-border);
    border-radius: var(--m-radius-lg);
    background: var(--m-surface-soft);

    :deep(.arco-alert-icon) {
      color: var(--m-primary);
    }

    :deep(.arco-alert-content) {
      color: var(--m-text-2);
    }
  }

  .progress-row + .progress-row {
    margin-top: 9px;
  }

  .progress-row em {
    color: var(--m-muted);
    font-style: normal;
    text-align: right;
  }

  .filter-form {
    :deep(.arco-form-item) {
      margin-bottom: 9px;
    }

    :deep(.arco-input-wrapper),
    :deep(.arco-select-view-single),
    :deep(.arco-picker),
    :deep(.arco-input-tag),
    :deep(.arco-input-number) {
      width: 171px;
      border-radius: 5px;
    }
  }

  .table-section {
    padding: 0;
    overflow: hidden;
  }

  .table-toolbar {
    margin-bottom: 0;
    padding: 10px 12px;
    border-bottom: 1px solid var(--m-border);
    background: var(--m-surface-soft);
  }

  .table-toolbar p {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-top: 3px;
  }

  .table-toolbar p i {
    width: 3px;
    height: 3px;
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
    padding: 9px 12px;
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
    min-height: 100px;
    border: 1px dashed var(--m-primary-border);
    border-radius: var(--m-radius-lg);
    background: var(--m-surface-soft);
    color: var(--m-primary);
    text-align: center;
  }

  .upload-drop span {
    margin-top: 3px;
    color: var(--m-muted);
    font-size: 10px;
  }

  .state-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 9px;
    margin-top: 9px;
  }

  .state-card {
    display: grid;
    place-items: center;
    min-height: 86px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-lg);
    background: var(--m-surface);
  }

  .theme-empty-demo {
    width: 100%;
    min-height: 64px;
    border: 0;
  }

  .stat-card {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    min-height: 77px;
    padding: 10px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-lg);
    background: var(--m-surface);
  }

  .stat-card :deep(.arco-statistic-title) {
    color: var(--m-muted);
    font-size: 10px;
  }

  .stat-card :deep(.arco-statistic-value) {
    color: var(--m-text);
    font-size: 21px;
    font-weight: 650;
  }

  .theme-list {
    :deep(.arco-list-item) {
      padding: 9px;
      border: 1px solid var(--m-border);
      border-radius: var(--m-radius-lg);
      background: var(--m-surface);
    }

    :deep(.arco-list-item + .arco-list-item) {
      margin-top: 9px;
    }

    :deep(.arco-list-item-meta-title) {
      color: var(--m-text);
      font-size: 11px;
      font-weight: 600;
    }

    :deep(.arco-list-item-meta-description) {
      color: var(--m-muted);
      font-size: 10px;
    }
  }

  .chart-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(min(100%, 300px), 1fr));
    gap: var(--m-page-gap);
  }

  .chart-card {
    min-height: 234px;
    padding: 10px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-lg);
    background: var(--m-surface);
  }

  .chart-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 9px;
    margin-bottom: 10px;
  }

  .chart-head strong {
    display: block;
    color: var(--m-text);
    font-size: 12px;
    font-weight: 600;
  }

  .chart-head span,
  .chart-head em {
    color: var(--m-muted);
    font-size: 10px;
    font-style: normal;
  }

  .donut-chart {
    display: grid;
    place-items: center;
    width: 133px;
    height: 133px;
    margin: 9px auto 12px;
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
    width: 84px;
    height: 84px;
    border-radius: 50%;
    background: var(--m-surface);
  }

  .donut-chart strong {
    color: var(--m-text);
    font-size: 21px;
    line-height: 25px;
  }

  .donut-chart span {
    color: var(--m-muted);
    font-size: 10px;
  }

  .chart-legend {
    display: flex;
    justify-content: center;
    gap: 10px;
    flex-wrap: wrap;
    color: var(--m-muted);
    font-size: 10px;
  }

  .chart-legend span {
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }

  .chart-legend i {
    width: 7px;
    height: 7px;
    border-radius: 899px;
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
    grid-template-columns: repeat(8, minmax(23px, 1fr));
    align-items: end;
    gap: 10px;
    height: 158px;
    padding: 16px 7px 0;
    border-bottom: 1px solid var(--m-border);
    background: linear-gradient(to top, var(--m-border) 1px, transparent 1px) 0 0 / 100% 39px,
      var(--m-surface);
  }

  .bar-column {
    display: grid;
    justify-items: center;
    gap: 7px;
  }

  .bar-stack {
    display: flex;
    align-items: end;
    gap: 3px;
    height: 124px;
  }

  .bar-stack i {
    width: 9px;
    min-height: 3px;
    border-radius: 899px 899px 1px 1px;
  }

  .bar-stack .success {
    background: var(--m-primary);
  }

  .bar-stack .danger {
    background: var(--m-danger);
  }

  .bar-column span {
    color: var(--m-muted);
    font-size: 9px;
  }

  .rank-chart,
  .status-summary {
    display: grid;
    gap: 10px;
    margin-top: 16px;
  }

  .rank-row {
    display: grid;
    grid-template-columns: 63px minmax(0, 1fr) 32px;
    align-items: center;
    gap: 7px;
    color: var(--m-text-2);
    font-size: 10px;
  }

  .rank-row div {
    height: 7px;
    overflow: hidden;
    border-radius: 899px;
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
    gap: 7px;
    padding-bottom: 10px;
    color: var(--m-text-2);
    font-size: 11px;
  }

  .status-summary strong {
    font-size: 16px;
    font-weight: 650;
  }

  .status-summary i {
    grid-column: 1 / -1;
    height: 7px;
    border-radius: 899px;
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
    gap: 9px;
  }

  .audit-card {
    padding: 10px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-lg);
    background: var(--m-surface-soft);
  }

  .audit-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 7px;
    margin-bottom: 7px;
  }

  .audit-head span {
    color: var(--m-text);
    font-size: 11px;
    font-weight: 650;
  }

  .audit-card ul {
    display: grid;
    gap: 5px;
    margin: 0;
    padding-left: 14px;
    color: var(--m-text-2);
    font-size: 10px;
    line-height: 16px;
  }

  .audit-command {
    display: grid;
    grid-template-columns: max-content max-content minmax(0, 1fr);
    align-items: center;
    gap: 9px;
    margin-top: 9px;
    padding: 9px 10px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-lg);
    background: var(--m-surface);
    color: var(--m-muted);
    font-size: 10px;
  }

  .audit-command code {
    padding: 2px 7px;
    border: 1px solid var(--m-code-border);
    border-radius: 5px;
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
    max-width: 198px;
    color: var(--m-text-2);
    font-size: 11px;
  }

  :deep(.arco-btn) {
    border-radius: 5px;
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
    margin-top: 5px;
  }

  .editor-stack {
    display: grid;
    gap: 9px;
  }

  .editor-panel {
    overflow: hidden;
    border: 1px solid var(--m-code-border);
    border-radius: var(--m-radius-lg);
    background: var(--m-code-bg);
    box-shadow: none;
  }

  .editor-title {
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 28px;
    padding: 0 10px;
    border-bottom: 1px solid var(--m-code-border);
    background: color-mix(in srgb, var(--m-code-bg) 88%, var(--m-code-text));
    color: var(--m-code-comment);
    font-size: 10px;
  }

  .editor-title span {
    color: var(--m-code-text);
  }

  .editor-title em {
    color: var(--m-code-comment);
    font-style: normal;
  }

  .editor-panel pre {
    min-height: 135px;
    margin: 0;
    padding: 10px 12px;
    overflow: auto;
    color: var(--m-code-text);
    font-family: 'JetBrains Mono', Consolas, 'Courier New', monospace;
    font-size: 11px;
    line-height: 1.68;
    tab-size: 2;
  }

  :deep(.syntax-key),
  :deep(.syntax-function) {
    color: var(--m-code-function);
    font-weight: 650;
  }

  :deep(.syntax-string) {
    color: var(--m-code-string);
  }

  :deep(.syntax-keyword),
  :deep(.syntax-bool) {
    color: var(--m-code-keyword);
    font-weight: 600;
  }

  :deep(.syntax-number) {
    color: var(--m-code-number);
    font-weight: 650;
  }

  :deep(.syntax-module),
  :deep(.syntax-method) {
    color: var(--m-code-function);
    font-weight: 600;
  }

  :deep(.syntax-brace) {
    color: var(--m-code-bracket);
  }

  .message-list {
    display: grid;
    gap: 9px;
  }

  .message-item {
    gap: 9px;
    padding: 9px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-lg);
    background: var(--m-surface);
  }

  .message-item > span {
    flex: none;
    width: 7px;
    height: 7px;
    border-radius: 899px;
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
    font-size: 11px;
  }

</style>
