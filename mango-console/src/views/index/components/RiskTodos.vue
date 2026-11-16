<template>
  <div class="mango-risk-todos">
    <mango-panel-spin :loading="loading" class="mango-risk-todos__spin">
      <div
        v-if="items.length"
        class="mango-risk-todos__list mango-native-scrollbar"
        @scroll.passive="handleScroll"
      >
        <HoverTaskDetail v-for="item in items" :key="item.id">
          <article
            class="mango-risk-todo mango-hover-task-row"
            tabindex="0"
            :aria-label="`${item.title}，停留一秒查看完整待办信息`"
          >
            <span :class="['mango-risk-todo__marker', `is-${severityKey(item.severity)}`]">
              <IconExclamationCircleFill />
            </span>
            <div class="mango-risk-todo__content">
              <div class="mango-risk-todo__detail-trigger">
                <span class="mango-risk-todo__title-row">
                  <strong>{{ item.title }}</strong>
                  <a-tag
                    class="mango-risk-todo__type-tag"
                    :color="item.severity === 2 ? 'red' : 'orange'"
                    size="small"
                  >
                    {{ item.event_type_name }}
                  </a-tag>
                </span>
                <span class="mango-risk-todo__summary">
                  {{ item.summary }}
                </span>
              </div>
              <div class="mango-risk-todo__footer">
                <div class="mango-risk-todo__meta">
                  <span class="mango-risk-todo__project">
                    {{ projectProductPath(item) }}
                  </span>
                  <span class="mango-risk-todo__owner">
                    {{ ownerName(item) }}
                  </span>
                  <span class="mango-risk-todo__time">
                    {{ relativeTime(item) }}
                  </span>
                </div>
                <div class="mango-risk-todo__actions">
                  <a-button
                    v-if="item.can_mark_handled"
                    size="mini"
                    type="text"
                    :loading="handlingTodoId === item.id"
                    :disabled="handlingTodoId !== null"
                    @click="confirmHandled(item)"
                  >
                    已处理
                  </a-button>
                  <a-button
                    size="mini"
                    type="text"
                    :loading="navigatingTodoId === item.id"
                    :disabled="handlingTodoId !== null || navigatingTodoId !== null"
                    @click="goToSource(item)"
                  >
                    去处理
                  </a-button>
                </div>
              </div>
            </div>
          </article>
          <template #content>
            <div class="mango-risk-todo-detail">
              <div class="mango-risk-todo-detail__header">
                <strong>{{ item.title }}</strong>
                <a-tag :color="item.severity === 2 ? 'red' : 'orange'" size="small">
                  {{ item.event_type_name }}
                </a-tag>
              </div>
              <p class="mango-risk-todo-detail__summary">{{ item.summary }}</p>
              <dl class="mango-risk-todo-detail__fields">
                <template v-for="row in detailRows(item)" :key="row.label">
                  <dt>{{ row.label }}</dt>
                  <dd>{{ row.value }}</dd>
                </template>
              </dl>
              <div v-if="cleanupErrors(item).length" class="mango-risk-todo-detail__section">
                <span>失败明细</span>
                <div
                  v-for="(error, index) in cleanupErrors(item)"
                  :key="error.item_id ?? index"
                  class="mango-risk-todo-detail__error"
                >
                  <strong data-feedback-kind="execution-result">{{ error.alias || error.table_name || `失败项 ${index + 1}` }}</strong>
                  <small data-feedback-kind="execution-result">
                    {{
                      [error.environment_name, error.database_name, error.table_name]
                        .filter(Boolean)
                        .join(' · ')
                    }}
                  </small>
                  <p data-feedback-kind="execution-result">{{ error.error || '清理失败' }}</p>
                </div>
              </div>
              <div v-if="cleanupPendingItems(item).length" class="mango-risk-todo-detail__section">
                <span>待清理明细</span>
                <div
                  v-for="(cleanupItem, index) in cleanupPendingItems(item)"
                  :key="cleanupItem.item_id ?? index"
                  class="mango-risk-todo-detail__cleanup-item"
                >
                  <strong>{{
                    cleanupItem.alias || cleanupItem.table_name || `待清理项 ${index + 1}`
                  }}</strong>
                  <small>
                    {{
                      [
                        cleanupItem.environment_name,
                        cleanupItem.database_name,
                        cleanupItem.table_name,
                      ]
                        .filter(Boolean)
                        .join(' · ')
                    }}
                  </small>
                  <p>
                    {{ cleanupItem.primary_key || '主键' }} =
                    {{ cleanupItem.primary_value ?? '-' }}
                  </p>
                </div>
              </div>
              <div v-if="schemaDifferences(item).length" class="mango-risk-todo-detail__section">
                <span>结构变化</span>
                <pre>{{ formatDetailValue(schemaDifferences(item)) }}</pre>
              </div>
            </div>
          </template>
        </HoverTaskDetail>
        <template v-if="loadingMore || loadMoreFailed"><a-button  size="mini" type="text" @click="loadNextPage"
            >重新加载</a-button></template>
      </div>
      <div v-else-if="!loading" class="mango-empty-state mango-risk-todos__empty">
        <template v-if="loadFailed">
          <span></span>
          <a-button size="mini" type="text" @click="refresh">重新加载</a-button>
        </template>
        <template v-else>
          <IconCheckCircle />
          <span>当前没有待处理风险</span>
        </template>
      </div>
    </mango-panel-spin>
  </div>
</template>

<script lang="ts" setup>
import { reportLoadError } from '@/utils/load-error'

  import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import useUserStore from '@/store/modules/user'
  import { usePagePolling, type PollingContext } from '@/hooks/use-page-polling'
  import { scaleDensityPixels } from '@/hooks/useDisplayDensity'
  import { Message, Modal } from '@arco-design/web-vue'
  import { IconCheckCircle, IconExclamationCircleFill } from '@arco-design/web-vue/es/icon'
  import { getSystemWorkbenchTodos, postSystemWorkbenchTodoHandled } from '@/api/system'
  import { useNotificationMessage } from '@/store/modules/notification-message'
  import HoverTaskDetail from './HoverTaskDetail.vue'
  import { homeFeedPageSize as pageSize } from '../config'
  import { readRiskTodos, readHandledTodo, riskCleanupDetails } from '../records'
  import type { RiskTodoItem } from '../types'

  const emit = defineEmits<{
    (event: 'pending-change', hasPending: boolean): void
    (event: 'pending-count-change', count: number): void
  }>()
  const router = useRouter(), route = useRoute(), user = useUserStore()
  const notificationMessage = useNotificationMessage()
  const items = ref<RiskTodoItem[]>([])
  const loading = ref(true)
  const loadingMore = ref(false)
  const loadFailed = ref(false)
  const loadMoreFailed = ref(false)
  const page = ref(1)
  const total = ref(0)
  const handlingTodoId = ref<number | null>(null)
  const navigatingTodoId = ref<number | null>(null)
  const identityKey = computed(() => JSON.stringify([user.userId, user.roleId, user.token, user.selected_environment]))
  const contextKey = computed(() => JSON.stringify([identityKey.value, route.fullPath]))
  let mounted = false, requestPending = false, actionGeneration = 0
  let requestSequence = 0
  let confirmation: ReturnType<typeof Modal.confirm> | null = null
  const polling = usePagePolling(context => fetchData('quiet', context), pause)

  function invalidateRead() {
    requestSequence++
    requestPending = false
    loading.value = false
    loadingMore.value = false
  }
  function pause() {
    invalidateRead()
    actionGeneration++
    confirmation?.close()
    confirmation = null
  }
  function publishCount(count: number) {
    notificationMessage.setTodoPendingCount(count)
    emit('pending-change', count > 0)
    emit('pending-count-change', count)
  }

  function severityKey(value: number) {
    return value === 2 ? 'danger' : 'warning'
  }

  function projectProductPath(item: RiskTodoItem) {
    const project = item.project_product?.project?.name || '-'
    return `${project} / ${item.project_product?.name || '-'}`
  }

  function ownerName(item: RiskTodoItem) {
    const names = (item.owners || []).map((owner) => owner.name || owner.username).filter(Boolean)
    return names.length ? names.join('、') : '未配置'
  }

  const detailLabels: Record<string, string> = {
    source_name: '数据来源',
    auth_name: '授权名称',
    test_env_name: '测试环境',
    refresh_mode: '刷新方式',
    expires_at: '授权到期时间',
    last_refresh_time: '最后刷新时间',
    last_refresh_error: '刷新失败原因',
    entity_name: '数据模型',
    table_name: '数据表',
    datasource_alias_id: '数据源别名 ID',
    invalidated_template_count: '受影响模板',
    execution_no: '执行编号',
    template_name: '数据模板',
    failed_count: '清理失败',
    pending_count: '待手动清理',
    success_count: '清理成功',
    skipped_count: '跳过',
    total_count: '清理总数',
    prepublication_count: '待审核 Case',
  }

  const hiddenDetailKeys = new Set([
    'test_env',
    'differences',
    'difference_fingerprint',
    'errors',
    'cleanup_items',
    'cases',
    'case_preview_truncated',
  ])
  const dateTimeDetailKeys = new Set(['expires_at', 'last_refresh_time'])

  function formatDateTime(value: unknown) {
    const matched = String(value).match(/^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})/)
    return matched ? `${matched[1]} ${matched[2]}` : String(value)
  }

  function formatDetailValue(value: unknown, key?: string) {
    if (key && dateTimeDetailKeys.has(key)) return formatDateTime(value)
    if (value === true) return '是'
    if (value === false) return '否'
    if (typeof value === 'object') return JSON.stringify(value, null, 2)
    return String(value)
  }

  function detailRows(item: RiskTodoItem) {
    const rows = [
      { label: '项目 / 产品', value: projectProductPath(item) },
      { label: '所属模块', value: item.module?.name || '-' },
      { label: '负责人', value: ownerName(item) },
      { label: '发生时间', value: formatDateTime(item.occurred_at || '-') },
      { label: '风险时间', value: formatDateTime(item.due_at || '-') },
      { label: '当前状态', value: relativeTime(item) },
    ]
    Object.entries(item.details || {}).forEach(([key, value]) => {
      if (hiddenDetailKeys.has(key) || value === null || value === undefined || value === '') return
      rows.push({
        label: detailLabels[key] || key,
        value: formatDetailValue(value, key),
      })
    })
    return rows
  }

  function cleanupErrors(item: RiskTodoItem) {
    return riskCleanupDetails(item.details.errors)
  }

  function cleanupPendingItems(item: RiskTodoItem) {
    return riskCleanupDetails(item.details.cleanup_items)
  }

  function schemaDifferences(item: RiskTodoItem) {
    return Array.isArray(item.details?.differences) ? item.details.differences : []
  }

  function relativeTime(item: RiskTodoItem) {
    const target = new Date(item.due_at || item.occurred_at).getTime()
    if (!Number.isFinite(target)) return '-'
    const minutes = Math.round((target - Date.now()) / 60_000)
    if (item.source_type === 6 || item.source_type === 7) {
      const waiting = Math.abs(Math.min(minutes, 0))
      if (waiting < 60) return `已等待 ${waiting} 分钟`
      if (waiting < 1440) return `已等待 ${Math.floor(waiting / 60)} 小时`
      return `已等待 ${Math.floor(waiting / 1440)} 天`
    }
    if (minutes < 0) {
      const overdue = Math.abs(minutes)
      if (overdue < 60) return `已超时 ${overdue} 分钟`
      if (overdue < 1440) return `已超时 ${Math.floor(overdue / 60)} 小时`
      return `已超时 ${Math.floor(overdue / 1440)} 天`
    }
    if (minutes < 60) return `${minutes} 分钟后到期`
    if (minutes < 1440) return `${Math.floor(minutes / 60)} 小时后到期`
    return `${Math.floor(minutes / 1440)} 天后到期`
  }

  async function fetchData(mode: 'reset' | 'append' | 'quiet', pollContext?: PollingContext) {
    if (!polling.isAvailable() || requestPending || handlingTodoId.value !== null) return
    if (mode === 'append' && items.value.length >= total.value) return
    const sequence = ++requestSequence
    const context = contextKey.value
    const current = () => polling.isAvailable() && sequence === requestSequence
      && context === contextKey.value && (!pollContext || pollContext.isCurrent())
    requestPending = true
    const targetPage = mode === 'append' ? page.value + 1 : mode === 'quiet' ? page.value : 1
    if (mode !== 'append') {
      loading.value = mode === 'reset' || items.value.length === 0
      loadFailed.value = false
    } else {
      loadingMore.value = true
      loadMoreFailed.value = false
    }
    try {
      const rows = mode === 'append' ? [...items.value] : []
      let nextTotal = 0, pendingCount = 0, lastPage = 1
      for (let nextPage = mode === 'append' ? targetPage : 1; nextPage <= targetPage; nextPage++) {
        const result = readRiskTodos(await getSystemWorkbenchTodos({ page: nextPage, pageSize, status: 'pending' }))
        if (!current()) return
        rows.push(...result.rows)
        nextTotal = result.total
        pendingCount = result.pending
        lastPage = nextPage
        if (nextPage * pageSize >= nextTotal || !result.rows.length) break
      }
      items.value = nextTotal === 0 ? [] : [...new Map(rows.map(row => [row.id, row])).values()].slice(0, nextTotal)
      page.value = lastPage
      total.value = nextTotal
      publishCount(pendingCount)
      loadFailed.value = false
      loadMoreFailed.value = false
    } catch (loadFailure0) {
      if (!current()) return
      if (mode === 'append') (reportLoadError(loadFailure0, "加载失败，请重试", false), loadMoreFailed.value = true)
      else (reportLoadError(loadFailure0, "加载失败，请重试", false), loadFailed.value = true)
    } finally {
      if (sequence === requestSequence) {
        requestPending = false
        loading.value = false
        loadingMore.value = false
      }
    }
  }

  function refresh() { return fetchData('reset') }
  function loadNextPage() { return fetchData('append') }

  function handleScroll(event: Event) {
    const target = event.currentTarget as HTMLElement
    if (target.scrollHeight - target.scrollTop - target.clientHeight <= scaleDensityPixels(64)) void loadNextPage()
  }

  async function goToSource(item: RiskTodoItem) {
    if (!polling.isAvailable() || handlingTodoId.value !== null || navigatingTodoId.value !== null) return
    const generation = actionGeneration, context = contextKey.value
    const path =
      item.source_type === 7 ? '/report/system/details' : item.source_type === 6 ? '/apitest/case/index' : item.source_type === 1
        ? '/uitest/auth-config/index'
        : item.source_type === 2
        ? '/apitest/auth-config/index'
        : item.source_type === 4
        ? '/data-factory/execution/index'
        : '/data-factory/entity/index'
    const query =
      item.source_type === 6 ? { publication_status: 'prepublished', project_product: String(item.source_id) } : item.source_type === 4
        ? { execution_no: String(item.details.execution_no ?? '') }
        : { id: String(item.source_id) }
    navigatingTodoId.value = item.id
    try { await router.push({ path, query }) }
    catch {
      if (polling.isAvailable() && generation === actionGeneration && context === contextKey.value) Message.error('页面打开失败，请重试')
    } finally { navigatingTodoId.value = null }
  }

  function confirmHandled(item: RiskTodoItem) {
    if (!polling.isAvailable() || !item.can_mark_handled || handlingTodoId.value !== null || confirmation) return
    const id = item.id, generation = actionGeneration, context = contextKey.value
    let dialog: ReturnType<typeof Modal.confirm> | null = null
    const current = () => polling.isAvailable() && generation === actionGeneration && context === contextKey.value && confirmation === dialog
    const isCleanupFailure = item.event_type === 6
    dialog = Modal.confirm({
      title: '确认标记为已处理？',
      content: item.event_type === 10
        ? '请确认平台已恢复，相关请求结果及清理状态已经核查。此操作只关闭待办，不会重试或修改原报告结果。'
        : isCleanupFailure
        ? '请确认已在线下完成清理。该操作只关闭当前清理失败待办，不会再次执行数据清理。'
        : '该操作只关闭当前结构待确认事件，不会修改数据模型或数据库表结构。',
      okText: '已处理',
      cancelText: '取消',
      onBeforeCancel: () => handlingTodoId.value === null,
      onClose: () => { if (confirmation === dialog) confirmation = null },
      onBeforeOk: async () => {
        if (!current() || handlingTodoId.value !== null) return false
        if (!items.value.some(row => row.id === id && row.can_mark_handled)) return true
        handlingTodoId.value = id
        invalidateRead()
        let acknowledged = false
        try {
          const message = readHandledTodo(await postSystemWorkbenchTodoHandled(item.event_type === 10
            ? { id, handle_note: '已确认平台恢复，并核查相关请求结果及清理状态。' } : { id }), id)
          if (!current()) return false
          acknowledged = true
          items.value = items.value.filter(row => row.id !== id)
          Message.success(message)
        } catch {
          if (current()) Message.error('标记处理失败，请重试')
        } finally {
          handlingTodoId.value = null
        }
        if (acknowledged && current()) await fetchData('quiet')
        return acknowledged
      },
    })
    confirmation = dialog
  }

  watch(contextKey, (value, previous) => {
    pause()
    items.value = []
    page.value = 1
    total.value = 0
    loadFailed.value = false
    loadMoreFailed.value = false
    if (JSON.parse(value)[0] !== JSON.parse(previous)[0]) publishCount(0)
    if (mounted) void refresh()
  }, { flush: 'sync' })
  onMounted(() => { mounted = true; polling.start(); void refresh() })
  onBeforeUnmount(() => { mounted = false; pause() })
</script>

<style lang="less" scoped>
  .mango-risk-todos {
    display: flex;
    height: 100%;
    min-height: 0;
    flex-direction: column;
  }

  .mango-risk-todos__spin {
    display: block;
    min-height: 0;
    flex: 1;

    :deep(> .mango-panel-spin__content) {
      height: 100%;
    }
  }

  .mango-risk-todos__list {
    height: 100%;
    overflow-y: auto;
  }

  .mango-risk-todo {
    display: grid;
    min-height: 68px;
    padding: 7px 9px;
    grid-template-columns: 14px minmax(0, 1fr);
    gap: 7px;
    border-bottom: 1px solid var(--m-border);
    background: var(--m-surface);
  }

  .mango-risk-todo__marker {
    padding-top: 1px;
    color: var(--m-warning);

    &.is-danger {
      color: var(--m-danger);
    }
  }

  .mango-risk-todo__content {
    min-width: 0;
  }

  .mango-risk-todo__title-row,
  .mango-risk-todo__footer,
  .mango-risk-todo__meta,
  .mango-risk-todo__actions {
    display: flex;
    min-width: 0;
    align-items: center;
  }

  .mango-risk-todo__detail-trigger {
    display: block;
    width: 100%;
    min-width: 0;
    text-align: left;
  }

  .mango-risk-todo__summary {
    display: block;
    overflow: hidden;
    margin: 2px 0;
    color: var(--m-text-2);
    font-size: 11px;
    line-height: 14px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-risk-todo__title-row {
    justify-content: space-between;
    gap: 5px;

    strong {
      min-width: 0;
      flex: 1;
      overflow: hidden;
      color: var(--m-text);
      font-size: 13px;
      font-weight: 600;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .mango-risk-todo__type-tag {
    display: inline-block;
    max-width: 93px;
    flex: none;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-risk-todo__meta {
    min-width: 0;
    flex: 1;
    overflow: hidden;
    gap: 0;
    color: var(--m-muted);
    font-size: 11px;
    white-space: nowrap;

    span {
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    span + span::before {
      margin: 0 4px;
      color: var(--m-border-strong);
      content: '·';
    }
  }

  .mango-risk-todo__project {
    flex: 1;
  }

  .mango-risk-todo__owner {
    max-width: 64px;
    flex: 0 1 64px;
  }

  .mango-risk-todo__time {
    max-width: 73px;
    flex: 0 1 73px;
  }

  .mango-risk-todo__footer {
    justify-content: space-between;
    gap: 3px;
  }

  .mango-risk-todo__actions {
    flex: none;
    gap: 3px;
  }

  .mango-risk-todos__empty,
  .mango-risk-todos__load-more {
    display: flex;
    height: 100%;
    min-height: 43px;
    align-items: center;
    justify-content: center;
    gap: 4px;
    color: var(--m-muted);
  }

  .mango-risk-todo-detail {
    color: var(--m-text);
  }

  .mango-risk-todo-detail__header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;

    strong {
      min-width: 0;
      font-size: 16px;
      line-height: 20px;
      overflow-wrap: anywhere;
    }
  }

  .mango-risk-todo-detail__summary {
    margin: 8px 0 10px;
    padding-bottom: 10px;
    border-bottom: 1px solid var(--m-border-soft);
    color: var(--m-text-2);
    font-size: 14px;
    line-height: 18px;
  }

  .mango-risk-todo-detail__fields {
    display: grid;
    margin: 0;
    grid-template-columns: 88px minmax(0, 1fr);
    gap: 7px 10px;
    font-size: 14px;
    line-height: 18px;

    dt {
      color: var(--m-muted);
    }

    dd {
      min-width: 0;
      margin: 0;
      color: var(--m-text-2);
      overflow-wrap: anywhere;
      white-space: pre-wrap;
    }
  }

  .mango-risk-todo-detail__section {
    margin-top: 12px;
    padding-top: 10px;
    border-top: 1px solid var(--m-border-soft);

    > span {
      display: block;
      margin-bottom: 6px;
      font-size: 14px;
      font-weight: 600;
    }

    pre {
      max-height: 180px;
      margin: 0;
      padding: 8px;
      overflow: auto;
      border-radius: 4px;
      background: var(--m-surface-soft);
      color: var(--m-text-2);
      font-size: 13px;
      line-height: 16px;
      white-space: pre-wrap;
    }
  }

  .mango-risk-todo-detail__error,
  .mango-risk-todo-detail__cleanup-item {
    padding: 7px 0;
    border-bottom: 1px solid var(--m-border-soft);

    &:last-child {
      border-bottom: 0;
    }

    strong,
    small,
    p {
      display: block;
    }

    strong {
      font-size: 14px;
      line-height: 18px;
    }

    small {
      margin-top: 2px;
      color: var(--m-muted);
      line-height: 16px;
    }

    p {
      margin: 4px 0 0;
      font-size: 13px;
      line-height: 16px;
      overflow-wrap: anywhere;
    }
  }

  .mango-risk-todo-detail__error p {
    color: var(--m-danger);
  }

  .mango-risk-todo-detail__cleanup-item p {
    color: var(--m-warning);
  }
</style>
