<template>
  <div class="mango-activity-rank">
    <mango-panel-spin :loading="loading" class="mango-activity-rank__spin">
      <div class="mango-activity-rank__metrics">
        <div>
          <span>活跃用户</span>
          <strong>{{ activeUsers }}</strong>
        </div>
        <div>
          <span>用户使用率</span>
          <strong>{{ activityRate.toFixed(2) }}%</strong>
        </div>
        <div>
          <span>平台访问</span>
          <strong>{{ visitCount }}</strong>
        </div>
      </div>
      
      <div
        v-if="dailyActivity.length"
        class="mango-activity-rank__trend"
        aria-label="近 7 天每日活跃用户趋势"
      >
        <div
          v-for="item in dailyActivity"
          :key="item.date"
          class="mango-activity-rank__trend-item"
          :title="`${formatActivityDate(item.date)}：${item.active_users} 人活跃`"
        >
          <span>{{ item.active_users }} 人</span>
          <i :style="{ height: `${dailyBarHeight(item.active_users)}%` }"></i>
          <em>{{ formatActivityDate(item.date) }}</em>
        </div>
      </div>
      <div v-if="rankItems.length" class="mango-activity-rank__section-title"> 用户活跃排行 </div>
      <div
        v-if="rankItems.length"
        class="mango-activity-rank__list mango-custom-scrollbar"
        @scroll.passive="handleRankScroll"
      >
        <div v-for="item in rankItems" :key="item.id" class="mango-activity-rank__row">
          <span class="mango-activity-rank__name" :title="item.name">{{ item.name }}</span>
          <div class="mango-activity-rank__track">
            <i class="mango-activity-rank__bar" :style="{ width: `${item.percent}%` }"></i>
          </div>
          <em class="mango-activity-rank__count">{{ item.count }}</em>
        </div>
        <div v-if="loadingMore" class="mango-activity-rank__load-state">正在加载更多...</div>
        <button
          v-else-if="loadMoreFailed"
          type="button"
          class="mango-activity-rank__retry"
          @click="loadNextPage"
        ></button>
        <div v-else-if="!hasMore" class="mango-activity-rank__load-state">已加载全部用户</div>
      </div>
      
    </mango-panel-spin>
  </div>
</template>

<script lang="ts" setup>
import { reportLoadError } from '@/utils/load-error'

  import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from 'vue'
  import { useRoute } from 'vue-router'
  import useUserStore from '@/store/modules/user'
  import { scaleDensityPixels } from '@/hooks/useDisplayDensity'
  import { emptyHomeActivity, readHomeActivity } from '../../records'
  import { homeActivityPageSize as pageSize } from '../../config'
  import { getSystemActivityLevel } from '@/api/system'

  interface ActivityRankItem {
    id: string
    name: string
    count: number
    percent: number
  }

  const loading = ref(false)
  const loadingMore = ref(false)
  const loadMoreFailed = ref(false)
  const loadFailed = ref(false)
  const currentPage = ref(1)
  const activity = ref(emptyHomeActivity())
  const rankTotal = computed(() => activity.value.total)
  const activeUsers = computed(() => activity.value.activeUsers)
  const activityRate = computed(() => activity.value.activityRate)
  const visitCount = computed(() => activity.value.visitCount)
  const dailyActivity = computed(() => activity.value.daily)
  const route = useRoute(), user = useUserStore(), entryPath = route.path
  const contextKey = computed(() => JSON.stringify([
    route.fullPath, user.userId, user.roleId, user.token, user.selected_environment,
  ]))
  let requestSequence = 0, active = true, mounted = false
  const available = () => active && route.path === entryPath
  function invalidate() { requestSequence++; loading.value = false; loadingMore.value = false }
  const maxDailyActivity = computed(() =>
    Math.max(...dailyActivity.value.map((item) => item.active_users), 0)
  )

  const rankItems = computed<ActivityRankItem[]>(() => {
    const max = Math.max(...activity.value.rows.map(row => row.count), 0)
    return activity.value.rows.map(row => ({
      ...row, percent: max > 0 ? Math.max(4, Math.round(row.count / max * 100)) : 0,
    })).sort((prev, next) => next.count - prev.count)
  })
  const hasMore = computed(() => rankItems.value.length < rankTotal.value)

  function dailyBarHeight(value: number) {
    if (!maxDailyActivity.value) return 4
    return Math.max(8, Math.round((value / maxDailyActivity.value) * 100))
  }

  function formatActivityDate(value: string) {
    return value.replace('-', '/')
  }

  async function activityLevel(reset = false) {
    if (!available() || loading.value || loadingMore.value || (!reset && !hasMore.value)) return
    const targetPage = reset ? 1 : currentPage.value + 1
    const sequence = ++requestSequence, context = contextKey.value
    const current = () => available() && sequence === requestSequence && context === contextKey.value
    loadMoreFailed.value = false
    if (reset) { loading.value = true; loadFailed.value = false }
    else loadingMore.value = true
    try {
      const next = readHomeActivity(await getSystemActivityLevel({ page: targetPage, pageSize }))
      if (!current()) return
      const rows = reset ? next.rows : [...activity.value.rows, ...next.rows]
      activity.value = { ...next, rows: next.total === 0 ? [] : [...new Map(rows.map(row => [row.id, row])).values()].slice(0, next.total) }
      currentPage.value = targetPage
      loadFailed.value = false
    } catch (loadFailure0) {
      if (!current()) return
      if (reset) (reportLoadError(loadFailure0, "加载失败，请重试", false), loadFailed.value = true)
      else (reportLoadError(loadFailure0, "加载失败，请重试", false), loadMoreFailed.value = true)
    } finally {
      if (current()) { loading.value = false; loadingMore.value = false }
    }
  }

  function loadNextPage() {
    return activityLevel(false)
  }

  function handleRankScroll(event: Event) {
    const target = event.currentTarget as HTMLElement
    if (target.scrollTop + target.clientHeight >= target.scrollHeight - scaleDensityPixels(48)) loadNextPage()
  }

  watch(contextKey, () => {
    invalidate()
    activity.value = emptyHomeActivity()
    currentPage.value = 1
    loadFailed.value = false
    loadMoreFailed.value = false
    if (mounted) void activityLevel(true)
  }, { flush: 'sync' })
  onMounted(() => { mounted = true; void activityLevel(true) })
  onDeactivated(() => { active = false; invalidate() })
  onActivated(() => {
    if (mounted && !active) { active = true; void activityLevel(true) }
  })
  onBeforeUnmount(() => { active = false; mounted = false; invalidate() })
</script>

<style lang="less" scoped>
  .mango-activity-rank {
    flex: 1;
    width: 100%;
    min-height: 0;
  }

  .mango-activity-rank__spin,
  :deep(.mango-activity-rank__spin > .mango-panel-spin__content) {
    display: flex;
    width: 100%;
    height: 100%;
    min-height: 0;
    flex-direction: column;
  }

  .mango-activity-rank__list {
    display: grid;
    flex: 1;
    gap: 8px;
    align-content: start;
    min-height: 0;
    padding: 5px 1px 3px;
    overflow-y: auto;
  }

  .mango-activity-rank__metrics {
    display: grid;
    padding: 5px 1px;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 5px;

    div {
      min-width: 0;
      padding: 5px;
      border: 1px solid var(--m-border);
      border-radius: var(--m-radius-md);
      background: var(--m-surface-soft);
    }

    span,
    strong {
      display: block;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    span {
      color: var(--m-muted);
      font-size: 11px;
    }

    strong {
      margin-top: 1px;
      color: var(--m-text);
      font-size: 14px;
      line-height: 18px;
    }
  }

  .mango-activity-rank__trend {
    display: grid;
    height: 66px;
    padding: 1px 3px 0;
    grid-template-columns: repeat(7, minmax(0, 1fr));
    align-items: end;
    gap: 3px;
  }

  .mango-activity-rank__trend-item {
    display: grid;
    height: 100%;
    min-width: 0;
    grid-template-rows: 14px minmax(12px, 1fr) 14px;
    justify-items: center;
    align-items: end;

    span,
    em {
      color: var(--m-muted);
      font-size: 11px;
      font-style: normal;
      line-height: 12px;
      white-space: nowrap;
    }

    i {
      display: block;
      width: 8px;
      min-height: 2px;
      border-radius: 3px 3px 1px 1px;
      background: var(--m-primary);
    }
  }

  .mango-activity-rank__section-title {
    padding: 4px 1px 0;
    border-top: 1px solid var(--m-border);
    color: var(--m-text-2);
    font-size: 11px;
    font-weight: 600;
  }

  .mango-activity-rank__row {
    display: grid;
    grid-template-columns: 4.25em minmax(0, 1fr) 38px;
    align-items: center;
    gap: 8px;
    color: var(--m-text-2);
    font-size: 12px;
  }

  .mango-activity-rank__name {
    min-width: 0;
    overflow: hidden;
    color: var(--m-text-2);
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-activity-rank__track {
    height: 8px;
    overflow: hidden;
    border-radius: 999px;
    background: var(--m-border);
  }

  .mango-activity-rank__bar {
    display: block;
    height: 100%;
    border-radius: inherit;
    background: linear-gradient(90deg, var(--m-primary-border), var(--m-primary));
  }

  .mango-activity-rank__count {
    color: var(--m-muted);
    font-style: normal;
    text-align: right;
  }

  .mango-activity-rank__load-state,
  .mango-activity-rank__retry {
    padding: 3px 0;
    border: 0;
    background: transparent;
    color: var(--m-muted);
    font-size: 11px;
    line-height: 16px;
    text-align: center;
  }

  .mango-activity-rank__retry {
    color: var(--m-primary);
    cursor: pointer;
  }

  .mango-activity-rank__empty {
    flex: 1;
    min-height: 120px;
  }

  @container mango-home (max-width: 1280px) {
    .mango-activity-rank__row {
      grid-template-columns: 3.75em minmax(0, 1fr) 34px;
      gap: 6px;
    }
  }
</style>
