<template>
  <TableBody ref="tableBody" plain class="mango-detail-workbench-page">
    <template #header>
      <TableHeader title="python脚本运行器（预警监控&Mock服务）">
        <template #header-extra>
          <a-space>
            <a-button v-permission="'monitoring.task:create'"
              type="primary"
              size="small"
              @click="onAdd"
              data-testid="qa-views-monitoring-task-button-新增"
            >
              新增
            </a-button>
            <a-button size="small" @click="demoPanelVisible = true">Demo / 使用方法</a-button>
          </a-space>
        </template>
      </TableHeader>
    </template>
    <template #default>
      <ProjectProductNavigationWorkbench
        contained-body
        :model-value="projectProductCondition?.value"
        @filter-change="onSidebarFilterChange"
      >
        <div class="mango-monitoring-task-page__workbench">
          <aside class="mango-monitoring-task-page__task-panel">
            <div class="mango-monitoring-task-page__task-heading">
              <div>
                <strong>监控任务</strong>
                <span>共 {{ taskPaging.total }} 条</span>
              </div>
              <a-input-search
                v-if="taskNameCondition"
                v-model="taskNameCondition.value"
                size="small"
                allow-clear
                placeholder="搜索任务名称"
                @search="onTaskSearch"
                @clear="onTaskSearch"
              />
            </div>
            <mango-panel-spin
              :loading="table.tableLoading.value"
              class="mango-monitoring-task-page__list-spin"
            >
              <div
                class="mango-monitoring-task-page__task-list mango-native-scrollbar"
                @scroll.passive="onTaskListScroll"
              >
                <div
                  v-for="record of table.dataList"
                  :key="record.id"
                  role="button"
                  tabindex="0"
                  class="mango-monitoring-task-page__task-item"
                  :class="{
                    'mango-monitoring-task-page__task-item--selected': record.id === workspace.taskId,
                  }"
                  @click="selectWorkspaceTask(record)"
                  @keydown.enter="selectWorkspaceTask(record)"
                >
                  <span class="mango-monitoring-task-page__task-content">
                    <span class="mango-monitoring-task-page__task-title">
                      <strong :title="record.name">{{ record.name }}</strong>
                      <a-tag :color="monitoringTaskStatusColor(record)" size="small">
                        {{ monitoringTaskStatusText(record) }}
                      </a-tag>
                    </span>
                    <span class="mango-monitoring-task-page__task-description">
                      {{ record.description || '暂无任务描述' }}
                    </span>
                    <span class="mango-monitoring-task-page__task-meta">
                      <span>PID {{ record.pid || '-' }}</span>
                      <span>{{ record.test_env_display || '未配置环境' }}</span>
                      <span>{{ formatProjectProductPath(record.project_product) }}</span>
                    </span>
                  </span>
                </div>
                <div
                  v-if="!table.tableLoading.value && !table.dataList.length"
                  class="mango-empty-state"
                >
                  暂无监控任务
                </div>
                <div v-else-if="taskListLoadingMore" class="mango-monitoring-task-page__load-more">
                  <mango-panel-spin :size="18" />
                  <span>正在加载更多</span>
                </div>
              </div>
            </mango-panel-spin>
          </aside>

          <main class="mango-monitoring-task-page__detail">
            <mango-panel-spin :loading="workspaceLoading" class="mango-monitoring-workspace__loading">
              <div v-if="workspace.task" class="mango-monitoring-workspace">
                <div class="mango-monitoring-workspace__summary">
                  <div class="mango-monitoring-workspace__identity">
                    <div class="mango-monitoring-workspace__title-row">
                      <strong>{{ workspace.task.name }}</strong>
                      <a-tag :color="monitoringTaskStatusColor(workspace.task)" size="small">
                        {{ workspaceStatusText }}
                      </a-tag>
                      <span v-if="fileSaving" class="mango-monitoring-workspace__dirty">
                        自动保存中
                      </span>
                      <span v-else-if="workspaceDirty" class="mango-monitoring-workspace__dirty">
                        待自动保存
                      </span>
                    </div>
                    <div class="mango-monitoring-workspace__meta-row">
                      <span>PID：{{ workspace.task.pid || '-' }}</span>
                      <span>测试环境：{{ workspace.task.test_env_display || '未配置' }}</span>
                      <span>启动时间：{{ workspace.task.started_at || '-' }}</span>
                      <span>更新人：{{ workspace.task.update_user?.name || '-' }}</span>
                    </div>
                  </div>
                  <a-space wrap>
                    <a-button v-permission="'monitoring.task:edit'" size="small" @click="onUpdate(workspace.task)">编辑配置</a-button>
                    <a-button v-permission="'monitoring.task:detail'" size="small" @click="openLogPanel">实时日志</a-button>
                    <a-button v-permission="'monitoring.task:execute'"
                      v-if="!workspaceProcessActive"
                      type="primary"
                      size="small"
                      status="success"
                      :loading="workspaceActionLoading"
                      @click="runWorkspaceTask"
                    >
                      运行
                    </a-button>
                    <a-button v-permission="'monitoring.task:execute'"
                      v-else
                      size="small"
                      status="danger"
                      :loading="workspaceActionLoading"
                      :disabled="!workspaceCanStop"
                      @click="stopWorkspaceTask"
                    >
                      {{ workspaceCanStop ? '停止' : '停止中' }}
                    </a-button>
                    <a-button v-permission="'monitoring.task:delete'" size="small" status="danger" @click="onDelete(workspace.task)">
                      删除
                    </a-button>
                  </a-space>
                </div>

                <div class="mango-monitoring-workspace__panes">
                  <section class="mango-monitoring-workspace__pane">
                    <header class="mango-monitoring-workspace__pane-header">
                      <div>
                        <div class="mango-monitoring-workspace__pane-title">Python 代码</div>
                        <div class="mango-monitoring-workspace__pane-description">
                          鼠标移出编辑区后自动保存，通过上方运行按钮执行脚本。
                        </div>
                      </div>
                    </header>
                    <div
                      class="mango-monitoring-workspace__editor"
                      @mouseleave="saveWorkspaceCode(false)"
                    >
                      <CodeEditor
                        ref="fileEditorRef"
                        v-model="workspace.codeText"
                        language="python"
                        placeholder="请输入 Python 脚本"
                        :codeStyle="{ height: '100%' }"
                        :dark="true"
                      />
                    </div>
                  </section>
                </div>
              </div>
              <div v-else class="mango-monitoring-task-page__empty mango-empty-state">
                请选择或新建一个监控任务
              </div>
            </mango-panel-spin>
          </main>
        </div>
      </ProjectProductNavigationWorkbench>
    </template>
  </TableBody>

  <BaseSidePanel
    v-model:visible="demoPanelVisible"
    title="监控脚本使用说明"
    width="50vw"
    :show-footer="false"
  >
    <template #header-actions>
      <a-button size="small" type="primary" @click="copyMonitoringDemo">复制 Demo</a-button>
    </template>
    <div class="mango-monitoring-demo-panel">
      <a-tabs v-model:active-key="activeDemoType" class="mango-monitoring-demo-panel__tabs">
        <a-tab-pane key="basic" title="不带测试环境">
          <div class="mango-monitoring-demo-panel__tab-content">
            <a-alert type="info" :show-icon="true">
              适用于不依赖平台测试配置的 Python 监控任务，例如业务指标预警、独立接口巡检和 Mock
              服务。脚本自行管理所需配置，不会读取平台中的域名或数据库。
            </a-alert>

            <section class="mango-monitoring-demo-panel__section">
              <div class="mango-monitoring-demo-panel__title">使用条件</div>
              <div class="mango-monitoring-demo-panel__conditions">
                <span>监控执行服务必须在线，否则任务无法启动。</span>
                <span>任务无需选择测试环境，平台不会注入域名和数据库配置。</span>
                <span>任务启用通知并配置通知组后，self.send 才会真正发送消息。</span>
                <span>脚本只能使用平台后端环境中已安装的 Python 依赖。</span>
              </div>
            </section>

            <section class="mango-monitoring-demo-panel__section">
              <div class="mango-monitoring-demo-panel__title">编写要求</div>
              <div class="mango-monitoring-demo-panel__requirements">
                <span>继承 MonitorBase，并实现 run() 作为任务入口。</span>
                <span>保留 __main__ 入口，并调用 start_monitoring()。</span>
                <span>常驻循环必须设置 sleep 间隔，避免空循环占满 CPU。</span>
                <span>使用 self.log、self.log_warning、self.log_error 输出实时日志。</span>
                <span>检测到不满足监控条件的数据时调用 self.send，消息会发送给通知组人员。</span>
                <span>密码、Token 等敏感信息应从环境变量或平台配置读取，禁止硬编码。</span>
                <span>单次检查异常应自行捕获，避免常驻任务因一次失败直接退出。</span>
              </div>
            </section>

            <section
              class="mango-monitoring-demo-panel__section mango-monitoring-demo-panel__code-section"
            >
              <div class="mango-monitoring-demo-panel__title">完整 Demo</div>
              <div class="mango-monitoring-demo-panel__code">
                <CodeEditor
                  :model-value="basicMonitoringDemoCode"
                  language="python"
                  :codeStyle="{ height: '100%' }"
                  :dark="true"
                  readonly
                />
              </div>
            </section>
          </div>
        </a-tab-pane>

        <a-tab-pane key="environment" title="带测试环境">
          <div class="mango-monitoring-demo-panel__tab-content">
            <a-alert type="info" :show-icon="true">
              适用于需要复用平台测试配置的 Python 监控任务。选择测试环境后，可直接从 self
              获取当前项目/产品在该环境下的域名和逻辑数据库连接。
            </a-alert>

            <section class="mango-monitoring-demo-panel__section">
              <div class="mango-monitoring-demo-panel__title">使用条件</div>
              <div class="mango-monitoring-demo-panel__conditions">
                <span>监控执行服务必须在线，否则任务无法启动。</span>
                <span>任务必须选择测试环境，并归属到已配置测试对象的项目/产品。</span>
                <span>域名来自测试对象配置，数据库来自该产品与环境的逻辑数据库绑定。</span>
                <span>任务启用通知并配置通知组后，self.send 才会真正发送消息。</span>
                <span>脚本只能使用平台后端环境中已安装的 Python 依赖。</span>
              </div>
            </section>

            <section class="mango-monitoring-demo-panel__section">
              <div class="mango-monitoring-demo-panel__title">编写要求</div>
              <div class="mango-monitoring-demo-panel__requirements">
                <span>继承 MonitorBase，并实现 run() 作为任务入口。</span>
                <span>保留 __main__ 入口，并调用 start_monitoring()。</span>
                <span>常驻循环必须设置 sleep 间隔，避免空循环占满 CPU。</span>
                <span>使用 self.log、self.log_warning、self.log_error 输出实时日志。</span>
                <span>检测到不满足监控条件的数据时调用 self.send，消息会发送给通知组人员。</span>
                <span>密码、Token 等敏感信息应从环境变量或平台配置读取，禁止硬编码。</span>
                <span>单次检查异常应自行捕获，避免常驻任务因一次失败直接退出。</span>
              </div>
            </section>

            <section class="mango-monitoring-demo-panel__section">
              <div class="mango-monitoring-demo-panel__title">测试环境注入的 self 字段</div>
              <div class="mango-monitoring-demo-panel__injections">
                <div>
                  <code>self.test_config</code><span>当前环境、域名和数据库配置的汇总字典</span>
                </div>
                <div>
                  <code>self.test_env / self.test_env_name</code><span>环境值和中文名称</span>
                </div>
                <div>
                  <code>self.domain / self.domains</code><span>默认域名和不同自动化类型的域名</span>
                </div>
                <div>
                  <code>self.database_configs / self.databases</code
                  ><span>按逻辑数据库名称索引的配置</span>
                </div>
                <div>
                  <code>self.get_database_config(alias)</code
                  ><span>获取指定逻辑数据库；只有一个时可不传名称</span>
                </div>
                <div>
                  <code>self.get_database_connection(alias)</code
                  ><span>获取受平台查询和写入权限控制的数据库连接</span>
                </div>
              </div>
              <div class="mango-monitoring-demo-panel__security-tip">
                平台不会把数据库密码放入 test_config。请通过 get_database_connection()
                建立连接，并在使用后关闭。
              </div>
            </section>

            <section
              class="mango-monitoring-demo-panel__section mango-monitoring-demo-panel__code-section"
            >
              <div class="mango-monitoring-demo-panel__title">完整 Demo</div>
              <div class="mango-monitoring-demo-panel__code">
                <CodeEditor
                  :model-value="environmentMonitoringDemoCode"
                  language="python"
                  :codeStyle="{ height: '100%' }"
                  :dark="true"
                  readonly
                />
              </div>
            </section>
          </div>
        </a-tab-pane>
      </a-tabs>
    </div>
  </BaseSidePanel>

  <BaseSidePanel
    v-model:visible="logPanelVisible"
    :title="`实时日志${workspace.task?.name ? ` · ${workspace.task.name}` : ''}`"
    width="50vw"
    :show-footer="false"
    @cancel="closeLogPanel"
  >
    <template #header-actions>
      <a-space>
        <span class="mango-monitoring-workspace__auto-scroll">自动滚动</span>
        <a-switch v-model="workspace.autoScroll" size="small" />
        <a-button size="small" :loading="logRefreshLoading" @click="fetchWorkspaceLog(false)">
          刷新
        </a-button>
        <a-button v-permission="'monitoring.task:download'"
          size="small"
          status="success"
          :loading="logDownloadLoading"
          @click="handleDownloadLog"
        >
          下载日志
        </a-button>
        <a-button v-permission="'monitoring.task:execute'"
          v-if="workspaceProcessActive"
          size="small"
          status="danger"
          :loading="workspaceActionLoading"
          :disabled="!workspaceCanStop"
          @click="stopWorkspaceTask"
        >
          {{ workspaceCanStop ? '停止运行' : '停止中' }}
        </a-button>
      </a-space>
    </template>
    <div class="mango-monitoring-log-panel">
      <div class="mango-monitoring-log-panel__description">
        窗口打开期间每 2 秒自动刷新当前任务最近 500 行日志。
      </div>
      <div class="mango-monitoring-log-panel__editor">
        <CodeEditor
          ref="logEditorRef"
          v-model="workspace.logText"
          placeholder="任务运行后，日志会实时显示在这里"
          :codeStyle="{ height: '100%' }"
          :dark="true"
          readonly
        />
      </div>
    </div>
  </BaseSidePanel>

  <ModalDialog ref="modalDialogRef" :title="data.actionTitle" @confirm="onDataForm">
    <template #content>
      <a-form :model="formModel">
        <a-form-item
          :class="[item.required ? 'mango-form-item__require' : 'mango-form-item__no_require']"
          :label="item.label"
          v-for="item of filteredFormItems"
          :key="item.key"
        >
          <template v-if="item.type === 'input'">
            <a-input :placeholder="item.placeholder" v-model="item.value" />
          </template>
          <template v-else-if="item.type === 'textarea'">
            <a-textarea
              v-model="item.value"
              :placeholder="item.placeholder"
              :auto-size="{ minRows: 3, maxRows: 6 }"
            />
          </template>
          <template v-else-if="item.type === 'cascader'">
            <ProjectProductSelect
              v-model="item.value"
              :placeholder="item.placeholder"
              @change="onProjectChange(item.value)"
            />
          </template>
          <template v-else-if="item.type === 'switch'">
            <a-switch v-model="item.value" :checked-value="1" :unchecked-value="0" />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'test_env'">
            <a-select
              v-model="item.value"
              :options="enumStore.environment_type"
              :field-names="fieldNames"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              value-key="key"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'notice_group'">
            <a-select
              v-model="item.value"
              :multiple="item.multiple"
              :max-tag-count="item.multiple ? 1 : undefined"
              :options="data.noticeList"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              value-key="key"
            />
          </template>
        </a-form-item>
      </a-form>
    </template>
  </ModalDialog>
</template>

<script lang="ts" setup>
  import { formatProjectProductPath } from '@/utils/business-format'
  import { Message, Modal } from '@arco-design/web-vue'
  import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
  import { ModalDialogType } from '@/types/components'
  import { useTable } from '@/hooks/table'
  import { useLatestRequest } from '@/hooks/use-latest-request'
  import { getFormItems } from '@/utils/datacleaning'
  import { conditionItems, formItems } from './config'
  import CodeEditor from '@/components/editors/CodeEditor.vue'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import {
    deleteMonitoringTask,
    downloadMonitoringTaskLog,
    getMonitoringTask,
    getMonitoringTaskDetail,
    getMonitoringTaskLogs,
    postMonitoringTask,
    postMonitoringTaskStart,
    postMonitoringTaskStop,
    putMonitoringTask,
  } from '@/api/monitoring/task'
  import { useEnum } from '@/store/modules/get-enum'
  import { getSystemNoticeName } from '@/api/system/notice_group'
  import { getStatusTagColor, MONITORING_TASK_STATUS_COLORS } from '@/utils/status-color'
  import { fieldNames } from '@/setting'

  const modalDialogRef = ref<ModalDialogType | null>(null)

  const fileEditorRef = ref<any>(null)
  const table = useTable()
  const { beginRequest, isLatestRequest } = useLatestRequest()
  const projectProductCondition = computed(() =>
    conditionItems.find((item) => item.key === 'project_product')
  )
  const taskNameCondition = computed(() => conditionItems.find((item) => item.key === 'name'))
  const formModel = ref({})
  const enumStore = useEnum()
  const monitoringTaskStatusColor = (task: any) => {
    if (task?.status === 1 && !task?.pid) return 'orange'
    return getStatusTagColor(MONITORING_TASK_STATUS_COLORS, task?.status)
  }
  const monitoringTaskStatusText = (task: any) => {
    if (task?.status === 1 && !task?.pid) return '等待执行服务'
    if (task?.status !== 1 && task?.pid) return '停止中'
    return enumStore.monitoring_task_status[task?.status]?.title || '未知状态'
  }
  const filteredFormItems = computed(() =>
    data.isAdd ? formItems : formItems.filter((it) => it.key !== 'script_content')
  )

  const data: any = reactive({
    isAdd: false,
    updateId: 0,
    actionTitle: '新增',
    noticeList: [],
  })

  const logEditorRef = ref<any>(null)
  const demoPanelVisible = ref(false)
  const activeDemoType = ref<'basic' | 'environment'>('basic')
  const basicMonitoringDemoCode = `# -*- coding: utf-8 -*-
"""监控脚本 Demo：展示循环检查、实时日志、异常捕获和通知写法。"""

import time

from mangotools.monitoring import MonitorBase


class DemoMonitor(MonitorBase):
    CHECK_INTERVAL_SECONDS = 10

    def run(self):
        self.log("Demo 监控任务启动成功")
        check_count = 0

        while True:
            try:
                # 在这里编写检查逻辑，例如查询接口、数据库或业务指标。
                check_count += 1
                self.log(f"第 {check_count} 次检查完成，当前未发现异常")

                has_problem = False
                if has_problem:
                    # 检测到不满足监控条件的数据后，发送给任务通知组中的对应人员。
                    self.send("发现不满足监控条件的数据，请及时处理", msg="Demo 监控告警")
            except Exception as error:
                # 单次检查失败不应让常驻任务直接退出。
                self.log_error(f"检查失败: {error}")

            time.sleep(self.CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    DemoMonitor().start_monitoring()
`
  const environmentMonitoringDemoCode = `# -*- coding: utf-8 -*-
"""测试环境 Demo：读取任务所选环境的域名和逻辑数据库配置。"""

import time

from mangotools.monitoring import MonitorBase


class EnvironmentMonitor(MonitorBase):
    CHECK_INTERVAL_SECONDS = 30

    def run(self):
        if self.test_config is None:
            self.log_warning("当前任务未选择测试环境，无法读取域名和数据库配置")
            return

        # self.domain 默认优先取API自动化域名，其次取通用、UI自动化配置。
        self.log(f"开始检查 {self.test_env_name}，目标域名：{self.domain or '未配置'}")
        self.log(f"可用逻辑数据库：{list(self.database_configs)}")

        # 多数据库时请传逻辑数据库名称，例如 self.get_database_config("订单库")。
        database = self.get_database_config()
        if database:
            self.log(
                f"使用数据库 {database['alias']}："
                f"{database['db_type_name']} {database['host']}:{database['port']}"
            )

        while True:
            try:
                # 可通过 self.domain、self.domains、self.database_configs 编写检查逻辑。
                has_problem = False
                if database is None:
                    self.log_warning("当前没有唯一可用的数据库，请按逻辑数据库名称获取连接")
                else:
                    connection = self.get_database_connection()
                    try:
                        database_result = connection.condition_execute("SELECT 1 AS health")
                    finally:
                        connection.close()
                    has_problem = not bool(database_result)

                if has_problem:
                    # 检测到不满足监控条件的数据后，发送给任务通知组中的对应人员。
                    self.send("发现不满足监控条件的数据，请及时处理", msg="环境监控告警")
                else:
                    self.log("本次环境检查完成，未发现异常")
            except Exception as error:
                self.log_error(f"环境检查失败: {error}")

            time.sleep(self.CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    EnvironmentMonitor().start_monitoring()
`
  const activeMonitoringDemoCode = computed(() =>
    activeDemoType.value === 'environment' ? environmentMonitoringDemoCode : basicMonitoringDemoCode
  )
  const logPanelVisible = ref(false)
  const logRefreshLoading = ref(false)
  const logDownloadLoading = ref(false)
  const fileSaving = ref(false)
  const workspaceLoading = ref(false)
  const workspaceActionLoading = ref(false)
  const logRequestPending = ref(false)
  const stateRequestPending = ref(false)
  const taskListRefreshing = ref(false)
  const taskListLoadingMore = ref(false)
  const taskListHasMore = ref(true)
  const taskPaging = reactive({
    page: 1,
    pageSize: 20,
    total: 0,
  })
  let workspacePollTimer: ReturnType<typeof setInterval> | null = null
  let workspaceLoadRequestId = 0
  let workspaceSavePromise: Promise<boolean> | null = null

  const workspace = reactive({
    codeText: '',
    originalCode: '',
    logText: '',
    autoScroll: true,
    taskId: 0,
    task: null as any,
  })
  const workspaceDirty = computed(() => workspace.codeText !== workspace.originalCode)
  const workspaceProcessActive = computed(
    () =>
      workspace.task?.status === 1 || workspace.task?.status === 5 || Boolean(workspace.task?.pid)
  )
  const workspaceCanStop = computed(
    () => workspace.task?.status === 1 || workspace.task?.status === 5
  )
  const workspaceStatusText = computed(() => monitoringTaskStatusText(workspace.task))

  async function copyMonitoringDemo() {
    try {
      await navigator.clipboard.writeText(activeMonitoringDemoCode.value)
      Message.success('Demo 代码已复制')
    } catch {
      Message.error('复制失败，请在代码区域中手动选择复制')
    }
  }

  function onAdd() {
    data.actionTitle = '新增'
    data.isAdd = true
    modalDialogRef.value?.toggle()
    formItems.forEach((it) => {
      if (it.reset) {
        it.reset()
      } else {
        it.value = it.multiple ? [] : ''
      }
    })
  }

  function onDelete(record: any) {
    Modal.confirm({
      title: '提示',
      content: '是否要删除此任务？',
      cancelText: '取消',
      okText: '删除',
      onBeforeOk: () => {
        return deleteMonitoringTask(record.id)
          .then((res) => {
            Message.success(res.msg)
            if (record.id === workspace.taskId) clearWorkspaceTask()
          })
          .catch(console.log)
          .finally(() => {
            doRefresh()
          })
      },
    })
  }

  function onDataForm() {
    // 编辑模式下跳过 script_content 的验证
    const itemsToValidate = data.isAdd
      ? formItems
      : formItems.filter((it) => it.key !== 'script_content')

    if (itemsToValidate.every((it) => (it.validator ? it.validator() : true))) {
      const value = getFormItems(formItems)
      if (value['test_env'] === '' || value['test_env'] === undefined) {
        value['test_env'] = null
      }
      if (data.isAdd) {
        postMonitoringTask(value)
          .then((res) => {
            modalDialogRef.value?.toggle()
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
          .finally(() => {
            modalDialogRef.value?.setConfirmLoading(false)
          })
      } else {
        value['id'] = data.updateId
        // 编辑时不包含 script_content 字段
        delete value['script_content']
        putMonitoringTask(value)
          .then((res) => {
            modalDialogRef.value?.toggle()
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
          .finally(() => {
            modalDialogRef.value?.setConfirmLoading(false)
          })
      }
    } else {
      modalDialogRef.value?.setConfirmLoading(false)
    }
  }

  function onUpdate(item: any) {
    data.actionTitle = '编辑'
    data.isAdd = false
    data.updateId = item.id
    // 先加载通知组列表
    if (item.project_product?.id) {
      onProjectChange(item.project_product.id)
    }
    modalDialogRef.value?.toggle()
    nextTick(() => {
      formItems.forEach((it) => {
        const propName = item[it.key]
        if (typeof propName === 'object' && propName !== null) {
          if (it.key === 'project_product') {
            it.value = propName.id
          } else if (it.key === 'notice_group') {
            it.value = propName?.id || ''
          } else {
            it.value = propName.id
          }
        } else {
          it.value = propName ?? ''
        }
      })
      // 更新时默认不覆盖脚本内容，需用户手动粘贴
      const scriptItem = formItems.find((it) => it.key === 'script_content')
      if (scriptItem) scriptItem.value = ''
    })
  }

  function onProjectChange(projectProductId: number | number[]) {
    // 获取项目产品ID（级联选择器可能返回数组）
    let id: number | null = null
    if (Array.isArray(projectProductId)) {
      id = projectProductId[projectProductId.length - 1] as number
    } else if (typeof projectProductId === 'number') {
      id = projectProductId
    }

    if (!id) {
      data.noticeList = []
      // 清空通知组选择
      const noticeGroupItem = formItems.find((it) => it.key === 'notice_group')
      if (noticeGroupItem) noticeGroupItem.value = ''
      return
    }

    getSystemNoticeName(id)
      .then((res) => {
        data.noticeList = (res.data || []).map((item: any) => ({
          key: item.value,
          label: item.label,
          value: item.value,
        }))
      })
      .catch(console.log)
  }

  function onTaskSearch() {
    doRefresh(true)
  }

  function onSidebarFilterChange(filter: { projectProduct: any }) {
    if (projectProductCondition.value) projectProductCondition.value.value = filter.projectProduct
    doRefresh(true)
  }

  function doRefresh(showLoading = false, append = false) {
    if (append && (taskListRefreshing.value || taskListLoadingMore.value || !taskListHasMore.value))
      return
    const requestId = beginRequest()
    const requestPage = append ? taskPaging.page + 1 : 1
    if (append) {
      taskListLoadingMore.value = true
    } else {
      taskListRefreshing.value = true
      if (showLoading) table.tableLoading.value = true
    }
    const value = getFormItems(conditionItems)
    value['page'] = requestPage
    value['pageSize'] = taskPaging.pageSize
    getMonitoringTask(value)
      .then((res) => {
        if (!isLatestRequest(requestId)) return
        const rows = Array.isArray(res.data) ? res.data : []
        if (append) {
          const existingIds = new Set(table.dataList.map((task: any) => task.id))
          table.dataList.push(...rows.filter((task: any) => !existingIds.has(task.id)))
        } else {
          table.handleSuccess(res)
        }
        taskPaging.page = requestPage
        taskPaging.total = Number((res as any).totalSize) || 0
        taskListHasMore.value = table.dataList.length < taskPaging.total
        const currentTask = table.dataList.find((task: any) => task.id === workspace.taskId)
        if (currentTask && workspace.task) {
          workspace.task = {
            ...workspace.task,
            ...currentTask,
          }
        } else if (workspaceDirty.value) {
          return
        } else if (table.dataList.length) {
          void loadWorkspaceTask(table.dataList[0])
        } else {
          clearWorkspaceTask()
        }
      })
      .catch((error) => {
        if (isLatestRequest(requestId)) console.log(error)
      })
      .finally(() => {
        if (append) taskListLoadingMore.value = false
        if (isLatestRequest(requestId)) {
          taskListRefreshing.value = false
          table.tableLoading.value = false
        }
      })
  }

  function onTaskListScroll(event: Event) {
    const target = event.currentTarget as HTMLElement
    const distanceToBottom = target.scrollHeight - target.scrollTop - target.clientHeight
    if (distanceToBottom <= 80) doRefresh(false, true)
  }

  function stopWorkspacePolling() {
    if (workspacePollTimer) {
      clearInterval(workspacePollTimer)
      workspacePollTimer = null
    }
  }

  function startWorkspacePolling() {
    if (workspacePollTimer || !workspace.taskId) return
    if (!logPanelVisible.value) return
    workspacePollTimer = setInterval(() => {
      if (!workspace.taskId || !logPanelVisible.value) {
        stopWorkspacePolling()
        return
      }
      void fetchWorkspaceLog(true)
      void refreshWorkspaceState()
    }, 2000)
  }

  function syncWorkspacePolling() {
    if (workspace.taskId && logPanelVisible.value) {
      startWorkspacePolling()
    } else {
      stopWorkspacePolling()
    }
  }

  async function selectWorkspaceTask(record: any) {
    if (record.id === workspace.taskId) return
    if (workspaceDirty.value) {
      const saved = await saveWorkspaceCode(false)
      if (!saved) return
    }
    void loadWorkspaceTask(record)
  }

  async function loadWorkspaceTask(record: any) {
    const requestId = ++workspaceLoadRequestId
    stopWorkspacePolling()
    workspace.taskId = record.id
    workspace.task = record
    workspace.codeText = ''
    workspace.originalCode = ''
    workspace.logText = ''
    workspaceLoading.value = true
    try {
      const res: any = await getMonitoringTaskDetail(record.id)
      if (requestId !== workspaceLoadRequestId) return
      const task = res.data || record
      workspace.task = task
      workspace.codeText = task.script_content || ''
      workspace.originalCode = workspace.codeText
      if (requestId !== workspaceLoadRequestId) return
      syncWorkspacePolling()
    } catch (error) {
      if (requestId === workspaceLoadRequestId) Message.error('加载脚本内容失败')
    } finally {
      if (requestId === workspaceLoadRequestId) workspaceLoading.value = false
    }
  }

  function clearWorkspaceTask() {
    workspaceLoadRequestId += 1
    stopWorkspacePolling()
    workspace.taskId = 0
    workspace.task = null
    workspace.codeText = ''
    workspace.originalCode = ''
    workspace.logText = ''
    workspaceLoading.value = false
    logPanelVisible.value = false
  }

  async function refreshWorkspaceState() {
    if (!workspace.taskId || stateRequestPending.value) return
    const taskId = workspace.taskId
    stateRequestPending.value = true
    try {
      const res: any = await getMonitoringTaskDetail(taskId)
      if (taskId !== workspace.taskId || !res.data) return
      workspace.task = {
        ...workspace.task,
        ...res.data,
      }
      const taskIndex = table.dataList.findIndex((task: any) => task.id === taskId)
      if (taskIndex >= 0) Object.assign(table.dataList[taskIndex], res.data)
    } catch (error) {
      console.log(error)
    } finally {
      stateRequestPending.value = false
      syncWorkspacePolling()
    }
  }

  async function saveWorkspaceCode(showSuccess = true) {
    if (!workspace.taskId || !workspace.task) {
      Message.warning('未选择任务')
      return false
    }
    if (!workspace.codeText.trim()) {
      Message.warning('脚本内容不能为空')
      return false
    }
    if (!workspaceDirty.value) return true
    if (workspaceSavePromise) return workspaceSavePromise
    const taskId = workspace.taskId
    const codeToSave = workspace.codeText
    fileSaving.value = true
    const payload: any = {
      id: taskId,
      script_content: codeToSave,
    }
    const request = (async () => {
      try {
        const res: any = await putMonitoringTask(payload)
        if (workspace.taskId === taskId) workspace.originalCode = codeToSave
        if (showSuccess) Message.success(res.msg || '代码保存成功')
        return true
      } catch (error) {
        Message.error('代码自动保存失败')
        return false
      }
    })()
    workspaceSavePromise = request
    try {
      return await request
    } finally {
      if (workspaceSavePromise === request) {
        workspaceSavePromise = null
        fileSaving.value = false
      }
    }
  }

  async function runWorkspaceTask() {
    if (!workspace.taskId || workspaceActionLoading.value) return
    if (workspaceProcessActive.value) {
      Message.warning('任务仍在运行或停止中，请等待进程完全停止后再运行')
      return
    }
    workspaceActionLoading.value = true
    try {
      const saved = await saveWorkspaceCode(false)
      if (!saved) return
      const res: any = await postMonitoringTaskStart(workspace.taskId)
      workspace.task = {
        ...workspace.task,
        ...(res.data || {}),
      }
      Message.success(res.msg || '任务已提交运行')
      logPanelVisible.value = true
      await fetchWorkspaceLog(true)
      await refreshWorkspaceState()
      syncWorkspacePolling()
    } catch (error) {
      console.log(error)
    } finally {
      workspaceActionLoading.value = false
    }
  }

  async function stopWorkspaceTask() {
    if (!workspace.taskId || workspaceActionLoading.value) return
    workspaceActionLoading.value = true
    try {
      const res: any = await postMonitoringTaskStop(workspace.taskId)
      workspace.task = {
        ...workspace.task,
        ...(res.data || {}),
      }
      Message.success(res.msg || '已提交停止请求')
      logPanelVisible.value = false
      await refreshWorkspaceState()
      syncWorkspacePolling()
    } catch (error) {
      console.log(error)
    } finally {
      workspaceActionLoading.value = false
    }
  }

  async function openLogPanel() {
    if (!workspace.taskId) {
      Message.warning('请先选择任务')
      return
    }
    logPanelVisible.value = true
    await fetchWorkspaceLog(true)
    syncWorkspacePolling()
    if (workspace.autoScroll) nextTick(() => logEditorRef.value?.scrollToBottom?.())
  }

  function closeLogPanel() {
    logPanelVisible.value = false
    syncWorkspacePolling()
  }

  // 工作台打开期间轮询最近日志，避免整份日志持续传输。
  async function fetchWorkspaceLog(silent = false) {
    if (!workspace.taskId || logRequestPending.value) return
    logRequestPending.value = true
    if (!silent) logRefreshLoading.value = true
    try {
      const res = await getMonitoringTaskLogs(workspace.taskId, 500)
      const nextLog = (res.data || []).join('')
      if (nextLog !== workspace.logText) {
        workspace.logText = nextLog
        if (workspace.autoScroll) {
          nextTick(() => logEditorRef.value?.scrollToBottom?.())
        }
      }
    } catch (error) {
      if (!silent) Message.error('日志刷新失败')
    } finally {
      logRequestPending.value = false
      if (!silent) logRefreshLoading.value = false
    }
  }

  async function handleDownloadLog() {
    if (!workspace.taskId) {
      Message.warning('请先选择任务')
      return
    }
    if (logDownloadLoading.value) return
    logDownloadLoading.value = true
    try {
      const res: any = await downloadMonitoringTaskLog(workspace.taskId)
      const blob = new Blob([res.data], { type: 'text/plain;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `任务日志_${workspace.taskId}_${new Date().getTime()}.log`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
      Message.success('日志下载成功')
    } catch (error) {
      Message.error('下载失败')
    } finally {
      logDownloadLoading.value = false
    }
  }

  onMounted(() => {
    doRefresh(true)
  })

  onBeforeUnmount(() => {
    stopWorkspacePolling()
  })
</script>

<style scoped lang="less">
  .mango-monitoring-task-page__workbench {
    display: grid;
    flex: 1;
    width: 100%;
    min-width: 0;
    min-height: 0;
    padding: var(--m-page-gap);
    grid-template-columns: minmax(240px, 280px) minmax(0, 1fr);
    gap: var(--m-page-gap);
    overflow: hidden;
    background: var(--m-bg);
  }

  .mango-monitoring-task-page__task-panel,
  .mango-monitoring-task-page__detail {
    display: flex;
    min-width: 0;
    min-height: 0;
    flex-direction: column;
    overflow: hidden;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-lg);
    background: var(--m-surface);
  }

  .mango-monitoring-task-page__task-heading {
    display: flex;
    min-height: 78px;
    padding: 8px 12px;
    flex-direction: column;
    justify-content: center;
    gap: 8px;
    border-bottom: 1px solid var(--m-border);

    > div {
      display: flex;
      min-width: 0;
      align-items: baseline;
      gap: 8px;
    }

    :deep(.arco-input-wrapper) {
      width: 100%;
    }

    strong {
      color: var(--m-text);
      font-size: 14px;
    }

    span {
      color: var(--m-muted);
      font-size: 12px;
    }
  }

  .mango-monitoring-task-page__list-spin {
    display: flex;
    flex: 1;
    min-height: 0;

    :deep(> .mango-panel-spin__content) {
      display: flex;
      width: 100%;
      min-height: 0;
      flex-direction: column;
    }
  }

  .mango-monitoring-task-page__task-list {
    flex: 1;
    min-height: 0;
    overflow: auto;
  }

  .mango-monitoring-task-page__task-item {
    box-sizing: border-box;
    display: flex;
    width: 100%;
    min-width: 0;
    min-height: 88px;
    padding: 10px 12px;
    align-items: flex-start;
    gap: 10px;
    border: 0;
    border-bottom: 1px solid var(--m-border);
    border-left: 3px solid transparent;
    background: var(--m-surface);
    color: var(--m-text-2);
    cursor: pointer;
    text-align: left;
    transition: background 0.16s ease, border-color 0.16s ease;

    &:hover,
    &:focus-visible {
      background: var(--m-surface-soft);
      outline: none;
    }
  }

  .mango-monitoring-task-page__task-item--selected {
    border-left-color: var(--m-primary);
    background: var(--m-primary-soft);
  }

  .mango-monitoring-task-page__task-content {
    display: flex;
    min-width: 0;
    flex: 1;
    flex-direction: column;
    gap: 5px;
  }

  .mango-monitoring-task-page__task-title,
  .mango-monitoring-task-page__task-meta {
    display: flex;
    min-width: 0;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .mango-monitoring-task-page__task-title strong,
  .mango-monitoring-task-page__task-description {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-monitoring-task-page__task-title strong {
    color: var(--m-text);
    font-size: 13px;
  }

  .mango-monitoring-task-page__task-description,
  .mango-monitoring-task-page__task-meta {
    color: var(--m-muted);
    font-size: 12px;
  }

  .mango-monitoring-task-page__task-meta span:last-child {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-monitoring-task-page__load-more {
    display: flex;
    min-height: 44px;
    padding: 6px 10px;
    align-items: center;
    justify-content: center;
    gap: 8px;
    color: var(--m-muted);
    font-size: 12px;
  }

  .mango-monitoring-task-page__empty {
    flex: 1;
  }

  .mango-monitoring-workspace__loading {
    display: flex;
    flex: 1;
    width: 100%;
    height: 100%;
    min-height: 0;

    :deep(> .mango-panel-spin__content) {
      height: 100%;
      min-height: 0;
    }
  }

  .mango-monitoring-workspace {
    box-sizing: border-box;
    display: flex;
    width: 100%;
    height: 100%;
    min-height: 0;
    flex-direction: column;
    overflow: hidden;
  }

  .mango-monitoring-workspace__summary {
    display: flex;
    min-height: 66px;
    padding: 10px 12px;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    border-bottom: 1px solid var(--m-border);
  }

  .mango-monitoring-workspace__identity {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 5px;
  }

  .mango-monitoring-workspace__title-row,
  .mango-monitoring-workspace__meta-row {
    display: flex;
    min-width: 0;
    align-items: center;
    gap: 10px;
  }

  .mango-monitoring-workspace__title-row strong {
    overflow: hidden;
    color: var(--m-text);
    font-size: 15px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-monitoring-workspace__meta-row,
  .mango-monitoring-workspace__auto-scroll {
    color: var(--m-muted);
    font-size: 12px;
  }

  .mango-monitoring-workspace__dirty {
    color: var(--m-warning);
    font-size: 12px;
  }

  .mango-monitoring-workspace__panes {
    display: grid;
    flex: 1;
    min-height: 0;
    grid-template-columns: minmax(0, 1fr);
    padding: var(--m-page-gap);
    gap: var(--m-page-gap);
    background: var(--m-bg);
  }

  .mango-monitoring-workspace__pane {
    display: flex;
    min-width: 0;
    min-height: 0;
    flex-direction: column;
    overflow: hidden;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius);
    background: var(--m-surface);
  }

  .mango-monitoring-workspace__pane-header {
    display: flex;
    min-height: 58px;
    padding: 8px 12px;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    border-bottom: 1px solid var(--m-border);
  }

  .mango-monitoring-workspace__pane-title {
    color: var(--m-text);
    font-size: 14px;
    font-weight: 600;
    line-height: 22px;
  }

  .mango-monitoring-workspace__pane-description {
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .mango-monitoring-workspace__editor {
    flex: 1;
    min-height: 0;
    overflow: hidden;

    :deep(.code-editor),
    :deep(.cm-editor) {
      height: 100%;
      min-height: 0;
    }

    :deep(.cm-scroller) {
      overflow: auto;
    }
  }

  .mango-monitoring-demo-panel {
    box-sizing: border-box;
    min-height: 100%;
    padding: 0;
    background: var(--m-bg);
  }

  .mango-monitoring-demo-panel__tabs {
    width: 100%;
  }

  .mango-monitoring-demo-panel__tab-content {
    display: flex;
    padding-top: var(--m-page-gap);
    flex-direction: column;
    gap: var(--m-page-gap);
  }

  .mango-monitoring-demo-panel__section {
    padding: 12px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius);
    background: var(--m-surface);
  }

  .mango-monitoring-demo-panel__title {
    margin-bottom: 8px;
    color: var(--m-text);
    font-size: 14px;
    font-weight: 600;
    line-height: 22px;
  }

  .mango-monitoring-demo-panel__conditions,
  .mango-monitoring-demo-panel__requirements {
    display: grid;
    gap: 6px 18px;
    color: var(--m-text-2);
    font-size: 12px;
    line-height: 20px;
  }

  .mango-monitoring-demo-panel__injections {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px 18px;

    div {
      display: flex;
      min-width: 0;
      flex-direction: column;
      gap: 2px;
    }

    code {
      color: var(--m-primary);
      font-size: 12px;
    }

    span {
      color: var(--m-muted);
      font-size: 12px;
      line-height: 18px;
    }
  }

  .mango-monitoring-demo-panel__security-tip {
    margin-top: 10px;
    color: var(--m-warning);
    font-size: 12px;
    line-height: 18px;
  }

  .mango-monitoring-demo-panel__requirements {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .mango-monitoring-demo-panel__conditions span::before,
  .mango-monitoring-demo-panel__requirements span::before {
    margin-right: 6px;
    color: var(--m-primary);
    content: '•';
  }

  .mango-monitoring-demo-panel__code-section {
    display: flex;
    min-height: 520px;
    flex-direction: column;
  }

  .mango-monitoring-demo-panel__code {
    min-height: 0;
    flex: 1;
    overflow: hidden;
    border: 1px solid var(--m-code-border);
    border-radius: var(--m-radius);

    :deep(.code-editor),
    :deep(.cm-editor) {
      height: 100%;
      min-height: 0;
    }

    :deep(.cm-scroller) {
      overflow: auto;
    }
  }

  .mango-monitoring-log-panel {
    box-sizing: border-box;
    display: flex;
    height: 100%;
    min-height: 0;
    padding: 0;
    flex-direction: column;
    gap: var(--m-page-gap);
    background: var(--m-bg);
  }

  .mango-monitoring-log-panel__description {
    flex: none;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .mango-monitoring-log-panel__editor {
    flex: 1;
    min-height: 0;
    overflow: hidden;
    border: 1px solid var(--m-code-border);
    border-radius: var(--m-radius);

    :deep(.code-editor),
    :deep(.cm-editor) {
      height: 100%;
      min-height: 0;
    }

    :deep(.cm-scroller) {
      overflow: auto;
    }
  }

  @media (max-width: 1100px) {
    .mango-monitoring-task-page__workbench {
      grid-template-rows: 240px minmax(0, 1fr);
      grid-template-columns: minmax(0, 1fr);
    }

    .mango-monitoring-workspace__summary {
      align-items: flex-start;
      flex-direction: column;
    }

    .mango-monitoring-demo-panel__requirements {
      grid-template-columns: minmax(0, 1fr);
    }

    .mango-monitoring-demo-panel__injections {
      grid-template-columns: minmax(0, 1fr);
    }
  }
</style>
