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
        >
          加载失败，点击重试
        </button>
        <div v-else-if="!hasMore" class="mango-activity-rank__load-state">已加载全部用户</div>
      </div>
      <div v-else-if="!loading" class="mango-empty-state mango-activity-rank__empty">
        暂无活跃度数据
      </div>
    </mango-panel-spin>
  </div>
</template>

<script lang="ts" setup>
  import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
  import { getSystemActivityLevel } from '@/api/system'

  interface ActivityRankItem {
    id: string
    name: string
    count: number
    percent: number
  }

  interface DailyActivityItem {
    date: string
    active_users: number
  }

  const loading = ref(false)
  const loadingMore = ref(false)
  const loadMoreFailed = ref(false)
  const currentPage = ref(1)
  const rankTotal = ref(0)
  const pageSize = 30
  let requestSequence = 0
  const rawUserIds = ref<string[]>([])
  const rawNames = ref<string[]>([])
  const rawCounts = ref<number[]>([])
  const activeUsers = ref(0)
  const activityRate = ref(0)
  const visitCount = ref(0)
  const dailyActivity = ref<DailyActivityItem[]>([])
  const maxDailyActivity = computed(() =>
    Math.max(...dailyActivity.value.map((item) => item.active_users), 0)
  )

  const rankItems = computed<ActivityRankItem[]>(() => {
    const max = Math.max(...rawCounts.value, 0)
    return rawNames.value
      .map((name, index) => {
        const count = Number(rawCounts.value[index] || 0)
        return {
          id: rawUserIds.value[index] || name,
          name,
          count,
          percent: max > 0 ? Math.max(4, Math.round((count / max) * 100)) : 0,
        }
      })
      .sort((prev, next) => next.count - prev.count)
  })
  const hasMore = computed(() => rankItems.value.length < rankTotal.value)

  function normalizeActivityData(payload: any, append = false) {
    const userIds = Array.isArray(payload?.user_ids) ? payload.user_ids : []
    const names = Array.isArray(payload?.name) ? payload.name : []
    const counts = Array.isArray(payload?.total_logins) ? payload.total_logins : []
    const incoming = names.map((item: any, index: number) => ({
      id: String(userIds[index] ?? item ?? index),
      name: String(item || '-'),
      count: Number(counts[index] || 0),
    }))
    const merged = append
      ? [
          ...rawNames.value.map((name, index) => ({
            id: rawUserIds.value[index],
            name,
            count: rawCounts.value[index],
          })),
          ...incoming,
        ]
      : incoming
    const unique = Array.from(new Map(merged.map((item) => [item.id, item])).values())
    rawUserIds.value = unique.map((item) => item.id)
    rawNames.value = unique.map((item) => item.name)
    rawCounts.value = unique.map((item) => item.count)
    rankTotal.value = Number(payload?.rank_total ?? payload?.active_users ?? unique.length)
    activeUsers.value = Number(payload?.active_users || 0)
    activityRate.value = Number(payload?.activity_rate || 0)
    visitCount.value = Number(payload?.visit_count || 0)
    dailyActivity.value = Array.isArray(payload?.daily_activity)
      ? payload.daily_activity.map((item: any) => ({
          date: String(item?.date || ''),
          active_users: Number(item?.active_users || 0),
        }))
      : []
  }

  function dailyBarHeight(value: number) {
    if (!maxDailyActivity.value) return 4
    return Math.max(8, Math.round((value / maxDailyActivity.value) * 100))
  }

  function formatActivityDate(value: string) {
    return value.replace('-', '/')
  }

  function activityLevel(reset = false) {
    if (loading.value || loadingMore.value || (!reset && !hasMore.value)) return
    const targetPage = reset ? 1 : currentPage.value + 1
    const sequence = ++requestSequence
    loadMoreFailed.value = false
    if (reset) loading.value = true
    else loadingMore.value = true
    getSystemActivityLevel({ page: targetPage, pageSize })
      .then((res) => {
        if (sequence !== requestSequence) return
        normalizeActivityData(res.data, !reset)
        currentPage.value = targetPage
      })
      .catch((error) => {
        if (sequence !== requestSequence) return
        console.log(error)
        if (!reset) loadMoreFailed.value = true
      })
      .finally(() => {
        if (sequence !== requestSequence) return
        loading.value = false
        loadingMore.value = false
      })
  }

  function loadNextPage() {
    activityLevel(false)
  }

  function handleRankScroll(event: Event) {
    const target = event.currentTarget as HTMLElement
    if (target.scrollTop + target.clientHeight >= target.scrollHeight - 48) loadNextPage()
  }

  onMounted(() => {
    activityLevel(true)
  })

  onBeforeUnmount(() => {
    requestSequence += 1
  })
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
