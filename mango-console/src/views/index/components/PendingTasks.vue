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
        <div v-if="loadingMore || loadMoreFailed" class="mango-upcoming-tasks__load-more">
          <mango-panel-spin v-if="loadingMore" :size="16" />
          <a-button v-else size="mini" type="text" @click="loadNextPage"
            >加载失败，点击重试</a-button
          >
        </div>
      </div>
      <div v-else-if="!loading" class="mango-empty-state mango-upcoming-tasks__empty">
        <template v-if="loadFailed">
          <span>任务队列加载失败</span>
          <a-button size="mini" type="text" @click="fetchData">重新加载</a-button>
        </template>
        <span v-else>暂无即将执行的定时任务</span>
      </div>
    </mango-panel-spin>
  </div>
</template>

<script lang="ts" setup>
  import { onBeforeUnmount, onMounted, ref } from 'vue'
  import { getSystemIndexPendingTasks } from '@/api/system/tasks'
  import { useEnum } from '@/store/modules/get-enum'
  import { formatProjectProductPath, getEnumTagColor } from '@/utils/business-format'
  import HoverTaskDetail from './HoverTaskDetail.vue'

  interface UpcomingTaskRecord {
    id: number
    name: string
    test_envs: number[]
    execution_scenes: string[]
    execution_scope: string | null
    latest_result_status: number | null
    next_run_at: string
    next_run_time?: string
    seconds_until_run: number
    project_product?: { name?: string; project?: { name?: string } }
    timing_strategies?: Array<{ id: number; name?: string; cron?: string }>
    case_people?: { id?: number; name?: string }
  }

  const enumStore = useEnum()
  const dataList = ref<UpcomingTaskRecord[]>([])
  const loading = ref(true)
  const loadingMore = ref(false)
  const loadFailed = ref(false)
  const loadMoreFailed = ref(false)
  const page = ref(1)
  const total = ref(0)
  const pageSize = 20
  const now = ref(Date.now())
  let clockTimer: ReturnType<typeof setInterval> | undefined
  let refreshTimer: ReturnType<typeof setInterval> | undefined
  let requestSequence = 0

  function optionTitle(value: string) {
    const options = enumStore.automation_execution_scene || []
    return options.find((item: any) => String(item.key) === String(value))?.title || '未分类'
  }

  function environmentName(value: number | null) {
    if (value === null || value === undefined) return '-'
    const options = enumStore.environment_type || []
    return options.find((item: any) => Number(item.key) === Number(value))?.title || '-'
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
    return options.find((item: any) => String(item.key) === String(value))?.title || value
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

  async function fetchData(reset = true) {
    if (!reset && (loading.value || loadingMore.value || dataList.value.length >= total.value))
      return
    const sequence = ++requestSequence
    const targetPage = reset ? 1 : page.value + 1
    if (reset) {
      loading.value = dataList.value.length === 0
      loadFailed.value = false
    } else {
      loadingMore.value = true
      loadMoreFailed.value = false
    }
    try {
      const res = await getSystemIndexPendingTasks({ page: targetPage, pageSize })
      if (sequence !== requestSequence) return
      const rows = Array.isArray(res.data) ? res.data : []
      if (reset) {
        dataList.value = rows
      } else {
        const existingIds = new Set(dataList.value.map((item) => item.id))
        dataList.value.push(...rows.filter((item) => !existingIds.has(item.id)))
      }
      page.value = targetPage
      total.value = Number(res.totalSize || rows.length)
      now.value = Date.now()
    } catch {
      if (sequence !== requestSequence) return
      if (reset) {
        dataList.value = []
        loadFailed.value = true
      } else {
        loadMoreFailed.value = true
      }
    } finally {
      if (sequence === requestSequence) {
        loading.value = false
        loadingMore.value = false
      }
    }
  }

  function loadNextPage() {
    fetchData(false)
  }

  function handleScroll(event: Event) {
    const target = event.currentTarget as HTMLElement
    if (target.scrollHeight - target.scrollTop - target.clientHeight <= 64) {
      loadNextPage()
    }
  }

  onMounted(() => {
    fetchData()
    clockTimer = setInterval(() => {
      now.value = Date.now()
    }, 30_000)
    refreshTimer = setInterval(() => fetchData(true), 60_000)
  })

  onBeforeUnmount(() => {
    requestSequence += 1
    if (clockTimer) clearInterval(clockTimer)
    if (refreshTimer) clearInterval(refreshTimer)
  })

  defineExpose({ refresh: fetchData })
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
