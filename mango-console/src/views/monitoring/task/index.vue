<template>
  <TableBody ref="tableBody" plain class="mango-detail-workbench-page">
    <template #header>
      <TableHeader title="python脚本运行器（预警监控&Mock服务）">
        <template #header-extra>
          <a-space>
            <a-button
              type="primary"
              size="small"
              :disabled="operationBusy"
              @click="onAdd"
              data-testid="qa-views-monitoring-task-button-新增"
            >
              新增
            </a-button>
            <a-button size="small" @click="demoRef?.open()">Demo / 使用方法</a-button>
          </a-space>
        </template>
      </TableHeader>
    </template>
    <template #default>
      <ProjectProductNavigationWorkbench
        ref="navigationCreateRef"
        contained-body
        data-navigation-layout="explorer"
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
              <span class="mango-monitoring-task-page__scope" :title="currentProjectProductLabel">{{ currentProjectProductLabel }}</span>
              <a-input-search
                v-model="taskName"
                size="small"
                allow-clear
                placeholder="搜索任务名称"
                @search="onTaskSearch"
                @clear="onTaskSearch"
              />
            </div>
            
            <mango-panel-spin
              :loading="taskListLoading"
              class="mango-monitoring-task-page__list-spin"
            >
              <div
                class="mango-monitoring-task-page__task-list mango-native-scrollbar"
                @scroll.passive="onTaskListScroll"
              >
                <div
                  v-for="record of taskRows"
                  :key="record.id"
                  role="button"
                  tabindex="0"
                  class="mango-monitoring-task-page__task-item"
                  :class="{
                    'mango-monitoring-task-page__task-item--selected': record.id === workspaceTaskId,
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
                    <span class="mango-monitoring-task-page__task-description" :title="record.description ?? undefined">
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
                  v-if="!taskListLoading && !taskRows.length"
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
              <div v-if="workspaceTask" class="mango-monitoring-workspace">
                
                <MangoRequestFeedback v-if="saveFailed" :message="&quot;代码保存失败，当前草稿已保留。&quot;"><template #action><a-button size="small" :loading="fileSaving" @click="saveWorkspaceCode(false)">重试</a-button></template></MangoRequestFeedback>
                
                <div class="mango-monitoring-workspace__summary">
                  <div class="mango-monitoring-workspace__identity">
                    <div class="mango-monitoring-workspace__title-row">
                      <strong>{{ workspaceTask.name }}</strong>
                      <a-tag :color="monitoringTaskStatusColor(workspaceTask)" size="small">
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
                      <span>PID：{{ workspaceTask.pid || '-' }}</span>
                      <span>测试环境：{{ workspaceTask.test_env_display || '未配置' }}</span>
                      <span>启动时间：{{ workspaceTask.started_at || '-' }}</span>
                      <span>更新人：{{ workspaceTask.update_user?.name || '-' }}</span>
                    </div>
                  </div>
                  <a-space wrap>
                    <a-button size="small" :disabled="operationBusy" @click="onUpdate(workspaceTask)">编辑配置</a-button>
                    <a-button  size="small" @click="openLogPanel">实时日志</a-button>
                    <a-button
                      v-if="!workspaceProcessActive"
                      type="primary"
                      size="small"
                      status="success"
                      :loading="workspaceActionLoading"
                      :disabled="!workspaceReady || configSaving || deletingIds.size > 0"
                      @click="runWorkspaceTask"
                    >
                      运行
                    </a-button>
                    <a-button
                      v-else
                      size="small"
                      status="danger"
                      :loading="workspaceActionLoading"
                      :disabled="!workspaceCanStop || fileSaving || configSaving || deletingIds.size > 0"
                      @click="stopWorkspaceTask"
                    >
                      {{ workspaceCanStop ? '停止' : '停止中' }}
                    </a-button>
                    <a-button size="small" status="danger" :loading="deletingIds.has(workspaceTask.id)" :disabled="operationBusy" @click="onDelete(workspaceTask)">
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
                        v-model="workspaceCodeText"
                        language="python"
                        placeholder="请输入 Python 脚本"
                        :codeStyle="{ height: '100%' }"
                        :dark="true"
                        :readonly="!workspaceReady || workspaceActionLoading || deletingIds.size > 0"
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

  <MonitoringTaskDemo ref="demoRef" />

  <BaseSidePanel
    v-model:visible="logPanelVisible"
    :title="`实时日志${workspaceTask?.name ? ` · ${workspaceTask.name}` : ''}`"
    width="50vw"
    :show-footer="false"
    @cancel="closeLogPanel"
  >
    <template #header-actions>
      <a-space>
        <span class="mango-monitoring-workspace__auto-scroll">自动滚动</span>
        <a-switch v-model="autoScroll" size="small" />
        <a-button size="small" :loading="logRefreshLoading" @click="fetchWorkspaceLog(false)">
          刷新
        </a-button>
        <a-button
          size="small"
          status="success"
          :loading="logDownloadLoading"
          @click="handleDownloadLog"
        >
          下载日志
        </a-button>
        <a-button
          v-if="workspaceProcessActive"
          size="small"
          status="danger"
          :loading="workspaceActionLoading"
          :disabled="!workspaceCanStop || fileSaving || configSaving || deletingIds.size > 0"
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
          v-model="logText"
          placeholder="任务运行后，日志会实时显示在这里"
          :codeStyle="{ height: '100%' }"
          :dark="true"
          readonly
        />
      </div>
    </div>
  </BaseSidePanel>

  <MonitoringTaskEditor ref="taskEditorRef" @saved="onEditorSaved" @saving-change="onConfigSavingChange" />
</template>

<script lang="ts" setup>
  import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import { formatProjectProductPath } from '@/utils/business-format'
  import { getStatusTagColor, MONITORING_TASK_STATUS_COLORS } from '@/utils/status-color'
  import { useEnum } from '@/store/modules/get-enum'
  import { scaleDensityPixels } from '@/hooks/useDisplayDensity'
  import { deleteMonitoringTask } from '@/api/monitoring/task'
  import type { NavigationCreateSource } from '@/utils/navigation-create-defaults'
  import CodeEditor from '@/components/editors/CodeEditor.vue'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import MonitoringTaskEditor from './components/MonitoringTaskEditor.vue'
  import MonitoringTaskDemo from './components/MonitoringTaskDemo.vue'
  import { createConditionItems } from './config'
  import { productId } from './editor-draft'
  import { useMonitoringTaskList } from './composables/useMonitoringTaskList'
  import { useMonitoringTaskWorkspace } from './composables/useMonitoringTaskWorkspace'
  import { useMonitoringTaskLogs } from './composables/useMonitoringTaskLogs'
  import { useMonitoringTaskScope } from './composables/useMonitoringTaskScope'
  import type { CodeEditorHandle, MonitoringTaskSnapshot, ProductSelection, TaskDemoHandle, TaskEditorHandle } from './types'

  const navigationCreateRef = ref<NavigationCreateSource | null>(null)
  const taskEditorRef = ref<TaskEditorHandle | null>(null), demoRef = ref<TaskDemoHandle | null>(null)
  const logEditorRef = ref<CodeEditorHandle | null>(null)
  const configSaving = ref(false), deletingIds = reactive(new Set<number>())
  const conditionItems = createConditionItems(), enumStore = useEnum()
  const projectProductCondition = computed(() => conditionItems.find(item => item.key === 'project_product'))
  const taskName = computed({
    get: () => { const value = conditionItems.find(item => item.key === 'name')?.value; return typeof value === 'string' ? value : '' },
    set: value => { const item = conditionItems.find(item => item.key === 'name'); if (item) item.value = value },
  })
  const tasks = useMonitoringTaskList(conditionItems)
  const { rows: taskRows, loading: taskListLoading, loadingMore: taskListLoadingMore, failed: taskListFailed, paging: taskPaging } = tasks
  const currentProjectProductLabel = computed(() => {
    const id = productId(projectProductCondition.value?.value ?? null)
    if (id === null) return '全部产品'
    const product = taskRows.value.find(task => task.project_product.id === id)?.project_product
    return product ? formatProjectProductPath(product) : `产品 ID ${id}`
  })
  const workspace = useMonitoringTaskWorkspace({
    blocked: () => configSaving.value || (workspaceTaskId.value !== null && deletingIds.has(workspaceTaskId.value)),
    changed: (task, write) => tasks.updateTask(task, write),
    reset: () => logs.close(true),
    started: () => logs.open(),
    stopped: () => { logs.close(); void workspace.refreshState() },
  })
  const {
    task: workspaceTask, taskId: workspaceTaskId, codeText: workspaceCodeText, dirty: workspaceDirty,
    loading: workspaceLoading, loadFailed: workspaceLoadFailed, ready: workspaceReady,
    saving: fileSaving, actionLoading: workspaceActionLoading, processActive: workspaceProcessActive,
    canStop: workspaceCanStop, stateLoading, stateFailed, saveFailed,
  } = workspace
  const logs = useMonitoringTaskLogs({
    taskId: () => workspaceTaskId.value, snapshot: workspace.snapshot, current: workspace.current,
    refreshState: workspace.refreshState, pauseState: workspace.pauseStateRequests,
    scroll: () => logEditorRef.value?.scrollToBottom(),
  })
  const { visible: logPanelVisible, text: logText, autoScroll, loading: logRefreshLoading, failed: logFailed, downloading: logDownloadLoading } = logs
  const saveWorkspaceCode = workspace.saveCode, runWorkspaceTask = workspace.run, stopWorkspaceTask = workspace.stop
  const openLogPanel = logs.open, fetchWorkspaceLog = logs.refresh, handleDownloadLog = logs.download
  function closeLogPanel() { logs.close() }
  const monitoringTaskStatusColor = (task: MonitoringTaskSnapshot | null) => {
    if (task?.status === 1 && !task.pid) return 'orange'
    return getStatusTagColor(MONITORING_TASK_STATUS_COLORS, task?.status)
  }
  const monitoringTaskStatusText = (task: MonitoringTaskSnapshot | null) => {
    if (!task) return '-'
    if (task.status === 1 && !task.pid) return '等待执行服务'
    if (task.status !== 1 && task.status !== 5 && task.pid) return '停止中'
    return enumStore.monitoring_task_status.find(item => Number(item.key) === task.status)?.title || task.status_display || '未知状态'
  }
  const workspaceStatusText = computed(() => monitoringTaskStatusText(workspaceTask.value))
  const operationBusy = computed(() => configSaving.value || fileSaving.value || workspaceActionLoading.value || deletingIds.size > 0)
  let confirmation: ReturnType<typeof Modal.confirm> | null = null, confirmationVersion = 0, searchVersion = 0
  const scope = useMonitoringTaskScope(() => {
    ++searchVersion; ++confirmationVersion
    confirmation?.close(); confirmation = null
    taskEditorRef.value?.close(); demoRef.value?.close()
  })
  watch(taskRows, records => workspace.reconcile(records, tasks.lastChange.value === 'replace'), { flush: 'sync' })
  function onConfigSavingChange(pending: boolean) { configSaving.value = pending }
  function onEditorSaved() { void tasks.load(false, true) }
  function onAdd() {
    if (!scope.available() || operationBusy.value) return
    taskEditorRef.value?.openCreate(navigationCreateRef.value?.getCreateDefaults().projectProduct ?? null)
  }
  function onUpdate(record: MonitoringTaskSnapshot) {
    if (!scope.available() || operationBusy.value) return
    taskEditorRef.value?.openEdit(record)
  }
  function onDelete(record: MonitoringTaskSnapshot) {
    if (!scope.available() || operationBusy.value || confirmation) return
    const id = record.id, version = scope.snapshot(), window = ++confirmationVersion
    const valid = () => scope.current(version) && window === confirmationVersion
    const dialog = Modal.confirm({
      title: '提示', content: '是否要删除此任务？', cancelText: '取消', okText: '删除',
      onBeforeCancel: () => !deletingIds.has(id),
      onBeforeOk: async () => {
        if (!valid() || operationBusy.value) return false
        deletingIds.add(id)
        try {
          const response = await deleteMonitoringTask(id)
          if (!valid()) return false
          if (response.code !== 200) throw new Error('Task deletion failed')
          Message.success(response.msg)
          if (workspaceTaskId.value === id) workspace.clear(false)
          await tasks.load(false, true)
          return true
        } catch { if (valid()) Message.error('任务删除失败，请重试'); return false }
        finally { deletingIds.delete(id) }
      },
      onClose: () => { if (confirmation === dialog) confirmation = null },
    })
    confirmation = dialog
  }
  async function applySearch(product?: ProductSelection) {
    if (!scope.available() || workspaceActionLoading.value || configSaving.value) return
    const search = ++searchVersion, version = scope.snapshot(), selected = workspace.snapshot()
    if (workspaceDirty.value || fileSaving.value) { if (!await saveWorkspaceCode(false)) return }
    if (search !== searchVersion || !scope.current(version) || !workspace.current(selected) || workspaceActionLoading.value || configSaving.value || deletingIds.size > 0) return
    if (product !== undefined && projectProductCondition.value) projectProductCondition.value.value = product
    await tasks.load()
  }
  function onTaskSearch() { return applySearch() }
  function onSidebarFilterChange(filter: { projectProduct: ProductSelection }) { return applySearch(filter.projectProduct) }
  function doRefresh(_showLoading = true, append = false) { return tasks.load(append) }
  function onTaskListScroll(event: Event) {
    const target = event.currentTarget as HTMLElement
    if (target.scrollHeight - target.scrollTop - target.clientHeight <= scaleDensityPixels(80)) void tasks.load(true)
  }
  function selectWorkspaceTask(record: MonitoringTaskSnapshot) { return workspace.select(record) }
  onBeforeUnmount(() => { confirmation?.close(); confirmation = null })
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

  .mango-monitoring-task-page__scope {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
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
    flex-wrap: wrap;
    gap: 12px;
    border-bottom: 1px solid var(--m-border);
  }

  .mango-monitoring-workspace__identity {
    display: flex;
    min-width: 0;
    flex-direction: column;
    flex: 1 1 280px;
    gap: 5px;
  }

  .mango-monitoring-workspace__title-row,
  .mango-monitoring-workspace__meta-row {
    display: flex;
    min-width: 0;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
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


  }
</style>
