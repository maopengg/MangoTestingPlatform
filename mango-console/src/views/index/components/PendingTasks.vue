<template>
  <div class="mango-upcoming-tasks">
    <mango-panel-spin :loading="loading" class="mango-upcoming-tasks__spin">
      <div
        v-if="dataList.length"
        class="mango-upcoming-tasks__list mango-native-scrollbar"
        @scroll.passive="handleScroll"
      >
        <HoverTaskDetail v-for="(task, index) in dataList" :key="task.id">
          <article
            class="mango-upcoming-task mango-hover-task-row"
            :class="{ 'mango-upcoming-task--nearest': index === 0 }"
            tabindex="0"
            :aria-label="`${task.name}，停留一秒查看完整任务信息`"
          >
            <div class="mango-upcoming-task__time">
              <span class="mango-upcoming-task__relative">{{ relativeTime(task) }}</span>
              <span class="mango-upcoming-task__absolute">{{ displayTime(task.next_run_at) }}</span>
            </div>

            <div class="mango-upcoming-task__content">
              <div class="mango-upcoming-task__title-row">
                <span class="mango-upcoming-task__name">{{ task.name }}</span>
              </div>
              <div class="mango-upcoming-task__meta">
                <span class="mango-upcoming-task__meta-text">
                  {{ formatProjectProductPath(task.project_product) }}
                </span>
                <span class="mango-upcoming-task__meta-text">
                  {{ timingStrategyNames(task.timing_strategies) }}
                </span>
              </div>
            </div>

            <div class="mango-upcoming-task__result">
              <a-tag :color="resultStatusColor(task.latest_result_status)" size="small">
                {{ resultStatusTitle(task.latest_result_status) }}
              </a-tag>
              <div class="mango-upcoming-task__result-tags">
                <a-tag
                  v-for="testEnv in task.test_envs || []"
                  :key="testEnv"
                  :color="environmentColor(testEnv)"
                  size="small"
                >
                  {{ environmentName(testEnv) }}
                </a-tag>
              </div>
            </div>
          </article>
          <template #content>
            <div class="mango-upcoming-task-detail">
              <div class="mango-upcoming-task-detail__header">
                <strong>{{ task.name }}</strong>
                <span>{{ resultStatusTitle(task.latest_result_status) }}</span>
              </div>
              <dl class="mango-upcoming-task-detail__fields">
                <template v-for="row in taskDetailRows(task)" :key="row.label">
                  <dt>{{ row.label }}</dt>
                  <dd>{{ row.value }}</dd>
                </template>
              </dl>
              <div class="mango-upcoming-task-detail__strategies">
                <span>定时策略</span>
                <div v-for="strategy in task.timing_strategies || []" :key="strategy.id">
                  <strong>{{ strategy.name || '未命名策略' }}</strong>
                  <code>{{ strategy.cron || '-' }}</code>
                </div>
                <small v-if="!task.timing_strategies?.length">-</small>
              </div>
            </div>
          </template>
        </HoverTaskDetail>
        <template v-if="loadingMore || loadMoreFailed"><a-button  size="mini" type="text" @click="loadNextPage"
            >重新加载</a-button></template>
      </div>
      <div v-else-if="!loading" class="mango-empty-state mango-upcoming-tasks__empty">
        <template v-if="loadFailed">
          <span></span>
          <a-button size="mini" type="text" @click="refresh">重新加载</a-button>
        </template>
        <span v-else>暂无即将执行的定时任务</span>
      </div>
    </mango-panel-spin>
  </div>
</template>

<script lang="ts" setup>
import { reportLoadError } from '@/utils/load-error'

  import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
  import { useRoute } from 'vue-router'
  import useUserStore from '@/store/modules/user'
  import { usePagePolling, type PollingContext } from '@/hooks/use-page-polling'
  import { scaleDensityPixels } from '@/hooks/useDisplayDensity'
  import { getSystemIndexPendingTasks } from '@/api/system/tasks'
  import { useEnum } from '@/store/modules/get-enum'
  import { formatProjectProductPath, getEnumTagColor } from '@/utils/business-format'
  import HoverTaskDetail from './HoverTaskDetail.vue'
  import { homeFeedPageSize as pageSize } from '../config'
  import { readUpcomingTasks } from '../records'
  import type { UpcomingTaskRecord } from '../types'

  const enumStore = useEnum()
  const dataList = ref<UpcomingTaskRecord[]>([])
  const loading = ref(true)
  const loadingMore = ref(false)
  const loadFailed = ref(false)
  const loadMoreFailed = ref(false)
  const page = ref(1)
  const total = ref(0)
  const now = ref(Date.now())
  const route = useRoute(), user = useUserStore()
  const contextKey = computed(() => JSON.stringify([
    route.fullPath, user.userId, user.roleId, user.token, user.selected_environment,
  ]))
  let mounted = false
  let requestPending = false
  let requestSequence = 0
  const polling = usePagePolling(context => fetchData('quiet', context), invalidateRequest)

  function invalidateRequest() {
    requestSequence++
    requestPending = false
    loading.value = false
    loadingMore.value = false
  }

  function optionTitle(value: string) {
    const options = enumStore.automation_execution_scene || []
    return options.find(item => String(item.key) === String(value))?.title || '未分类'
  }

  function environmentName(value: number | null) {
    if (value === null || value === undefined) return '-'
    const options = enumStore.environment_type || []
    return options.find(item => Number(item.key) === Number(value))?.title || '-'
  }

  function environmentColor(value: number | null) {
    if (value === null || value === undefined) return 'gray'
    return getEnumTagColor(enumStore.environment_type, value, enumStore.colors)
  }

  function timingStrategyNames(values?: Array<{ name?: string }>) {
    return (
      values
        ?.map((item) => item.name)
        .filter(Boolean)
        .join('、') || '-'
    )
  }

  function resultStatusTitle(value: number | null) {
    if (value === null || value === undefined) return '暂无执行结果'
    const title = enumStore.task_status?.[value]?.title || '未知'
    return `最近一次 · ${title}`
  }

  function resultStatusColor(value: number | null) {
    if (value === null || value === undefined) return 'gray'
    return enumStore.status_colors?.[value] || 'gray'
  }

  function executionScopeName(value: string | null) {
    if (!value) return '-'
    const options = enumStore.automation_execution_scope || []
    return options.find(item => String(item.key) === String(value))?.title || value
  }

  function taskDetailRows(task: UpcomingTaskRecord) {
    return [
      { label: '任务 ID', value: String(task.id) },
      { label: '项目 / 产品', value: formatProjectProductPath(task.project_product) },
      { label: '负责人', value: task.case_people?.name || '-' },
      { label: '下次执行', value: task.next_run_time || displayFullTime(task.next_run_at) },
      { label: '距离执行', value: relativeTime(task) },
      { label: '最近结果', value: resultStatusTitle(task.latest_result_status) },
      { label: '执行范围', value: executionScopeName(task.execution_scope) },
      {
        label: '测试环境',
        value: task.test_envs?.map((item) => environmentName(item)).join('、') || '-',
      },
      {
        label: '执行场景',
        value: task.execution_scenes?.map((item) => optionTitle(item)).join('、') || '-',
      },
    ]
  }

  function relativeTime(task: UpcomingTaskRecord) {
    const target = new Date(task.next_run_at).getTime()
    const seconds = Number.isFinite(target)
      ? Math.max(0, Math.floor((target - now.value) / 1000))
      : Math.max(0, task.seconds_until_run || 0)
    if (seconds <= 10) return '即将执行'
    if (seconds < 60) return `${seconds} 秒后`
    const minutes = Math.floor(seconds / 60)
    if (minutes < 60) return `${minutes} 分钟后`
    const hours = Math.floor(minutes / 60)
    if (hours < 24) return `${hours} 小时后`
    return `${Math.floor(hours / 24)} 天后`
  }

  function displayTime(value: string) {
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return '-'
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const hour = String(date.getHours()).padStart(2, '0')
    const minute = String(date.getMinutes()).padStart(2, '0')
    return `${month}-${day} ${hour}:${minute}`
  }

  function displayFullTime(value: string) {
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return '-'
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const hour = String(date.getHours()).padStart(2, '0')
    const minute = String(date.getMinutes()).padStart(2, '0')
    const second = String(date.getSeconds()).padStart(2, '0')
    return `${year}-${month}-${day} ${hour}:${minute}:${second}`
  }

  async function fetchData(mode: 'reset' | 'append' | 'quiet', pollContext?: PollingContext) {
    if (!polling.isAvailable() || requestPending) return
    if (mode === 'append' && dataList.value.length >= total.value) return
    const sequence = ++requestSequence
    const context = contextKey.value
    const current = () => polling.isAvailable() && sequence === requestSequence
      && context === contextKey.value && (!pollContext || pollContext.isCurrent())
    requestPending = true
    const targetPage = mode === 'append' ? page.value + 1 : mode === 'quiet' ? page.value : 1
    if (mode !== 'append') {
      loading.value = mode === 'reset' || dataList.value.length === 0
      loadFailed.value = false
    } else {
      loadingMore.value = true
      loadMoreFailed.value = false
    }
    try {
      const rows = mode === 'append' ? [...dataList.value] : []
      let nextTotal = 0, lastPage = 1
      // 队列排序随调度变化，静默刷新重读已加载页后一次替换，避免丢失滚动分页内容。
      for (let nextPage = mode === 'append' ? targetPage : 1; nextPage <= targetPage; nextPage++) {
        const result = readUpcomingTasks(await getSystemIndexPendingTasks({ page: nextPage, pageSize }))
        if (!current()) return
        rows.push(...result.rows)
        nextTotal = result.total
        lastPage = nextPage
        if (nextPage * pageSize >= nextTotal || !result.rows.length) break
      }
      const unique = new Map(rows.map(row => [row.id, row]))
      dataList.value = nextTotal === 0 ? [] : [...unique.values()].slice(0, nextTotal)
      page.value = lastPage
      total.value = nextTotal
      loadFailed.value = false
      loadMoreFailed.value = false
      now.value = Date.now()
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

  function loadNextPage() {
    return fetchData('append')
  }

  function handleScroll(event: Event) {
    const target = event.currentTarget as HTMLElement
    if (target.scrollHeight - target.scrollTop - target.clientHeight <= scaleDensityPixels(64)) {
      void loadNextPage()
    }
  }

  watch(contextKey, () => {
    invalidateRequest()
    dataList.value = []
    page.value = 1
    total.value = 0
    loadFailed.value = false
    loadMoreFailed.value = false
    if (mounted) void refresh()
  }, { flush: 'sync' })
  onMounted(() => { mounted = true; polling.start(); void refresh() })
  onBeforeUnmount(() => { mounted = false; invalidateRequest() })

  defineExpose({ refresh })
</script>

<style lang="less" scoped>
  .mango-upcoming-tasks {
    height: 100%;
    min-height: 0;
  }

  .mango-upcoming-tasks__spin {
    display: block;
    height: 100%;

    :deep(> .mango-panel-spin__content) {
      height: 100%;
    }
  }

  .mango-upcoming-tasks__list {
    height: 100%;
    overflow-y: auto;
  }

  .mango-upcoming-task {
    display: grid;
    grid-template-columns: 86px minmax(0, 1fr) auto;
    min-height: 55px;
    align-items: center;
    gap: 10px;
    padding: 8px 10px;
    border-bottom: 1px solid var(--m-border);
    background: var(--m-surface);
  }

  .mango-upcoming-task--nearest {
    background: color-mix(in srgb, var(--m-primary) 6%, var(--m-surface));
    box-shadow: inset 3px 0 0 var(--m-primary);
  }

  .mango-upcoming-task__time,
  .mango-upcoming-task__content {
    display: flex;
    min-width: 0;
    flex-direction: column;
  }

  .mango-upcoming-task__time {
    gap: 2px;
  }

  .mango-upcoming-task__relative {
    color: var(--m-primary);
    font-size: 14px;
    font-weight: 700;
    white-space: nowrap;
  }

  .mango-upcoming-task__absolute,
  .mango-upcoming-task__meta {
    color: var(--m-muted);
    font-size: 11px;
  }

  .mango-upcoming-task__result-tags,
  .mango-upcoming-task__result {
    display: flex;
    gap: 5px;
    white-space: nowrap;
  }

  .mango-upcoming-task__result-tags {
    align-items: center;
    justify-content: flex-end;
  }

  .mango-upcoming-task__result {
    align-items: flex-end;
    align-self: start;
    flex-direction: column;
  }

  .mango-upcoming-task__title-row,
  .mango-upcoming-task__meta {
    display: flex;
    min-width: 0;
    align-items: center;
  }

  .mango-upcoming-task__title-row {
    gap: 5px;
  }

  .mango-upcoming-task__name {
    overflow: hidden;
    color: var(--m-text);
    font-size: 13px;
    font-weight: 600;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-upcoming-task__meta {
    margin-top: 4px;
    overflow: hidden;
    white-space: nowrap;

    .mango-upcoming-task__meta-text {
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .mango-upcoming-task__meta-text + .mango-upcoming-task__meta-text::before {
      margin: 0 5px;
      color: var(--m-border-strong);
      content: '·';
    }
  }

  .mango-upcoming-task-detail__header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
    padding-bottom: 10px;
    border-bottom: 1px solid var(--m-border-soft);

    strong {
      min-width: 0;
      font-size: 16px;
      line-height: 20px;
      overflow-wrap: anywhere;
    }

    span {
      flex: none;
      color: var(--m-text-2);
      font-size: 13px;
      line-height: 20px;
    }
  }

  .mango-upcoming-task-detail__fields {
    display: grid;
    margin: 10px 0 0;
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
    }
  }

  .mango-upcoming-task-detail__strategies {
    margin-top: 12px;
    padding-top: 10px;
    border-top: 1px solid var(--m-border-soft);

    > span {
      display: block;
      margin-bottom: 6px;
      color: var(--m-muted);
      font-size: 14px;
    }

    > div {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 10px;
      padding: 5px 0;
      font-size: 14px;

      strong {
        min-width: 0;
        overflow-wrap: anywhere;
      }

      code {
        color: var(--m-text-2);
      }
    }

    small {
      color: var(--m-muted);
    }
  }

  .mango-upcoming-tasks__empty {
    display: flex;
    height: 100%;
    align-items: center;
    flex-direction: column;
    gap: 4px;
    justify-content: center;
  }

  .mango-upcoming-tasks__load-more {
    display: flex;
    min-height: 30px;
    align-items: center;
    justify-content: center;
    color: var(--m-muted);
  }

  @container mango-home (max-width: 1280px) {
    .mango-upcoming-task {
      grid-template-columns: 84px minmax(0, 1fr) auto;
      gap: 8px;
    }
  }
</style>
