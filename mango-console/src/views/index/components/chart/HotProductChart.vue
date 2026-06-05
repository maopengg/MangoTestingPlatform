<template>
  <div class="mango-activity-rank">
    <a-spin :loading="loading" class="mango-activity-rank__spin">
      <div v-if="rankItems.length" class="mango-activity-rank__list mango-custom-scrollbar">
        <div v-for="item in rankItems" :key="item.name" class="mango-activity-rank__row">
          <span class="mango-activity-rank__name" :title="item.name">{{ item.name }}</span>
          <div class="mango-activity-rank__track">
            <i class="mango-activity-rank__bar" :style="{ width: `${item.percent}%` }"></i>
          </div>
          <em class="mango-activity-rank__count">{{ item.count }}</em>
        </div>
      </div>
      <div v-else-if="!loading" class="mango-empty-state mango-activity-rank__empty">
        暂无活跃度数据
      </div>
    </a-spin>
  </div>
</template>

<script lang="ts" setup>
  import { computed, onMounted, ref } from 'vue'
  import { getSystemActivityLevel } from '@/api/system'

  interface ActivityRankItem {
    name: string
    count: number
    percent: number
  }

  const loading = ref(false)
  const rawNames = ref<string[]>([])
  const rawCounts = ref<number[]>([])

  const rankItems = computed<ActivityRankItem[]>(() => {
    const max = Math.max(...rawCounts.value, 0)
    return rawNames.value
      .map((name, index) => {
        const count = Number(rawCounts.value[index] || 0)
        return {
          name,
          count,
          percent: max > 0 ? Math.max(4, Math.round((count / max) * 100)) : 0,
        }
      })
      .sort((prev, next) => next.count - prev.count)
  })

  function normalizeActivityData(payload: any) {
    const names = Array.isArray(payload?.name) ? payload.name : []
    const counts = Array.isArray(payload?.total_logins) ? payload.total_logins : []
    rawNames.value = names.map((item: any) => String(item || '-'))
    rawCounts.value = counts.map((item: any) => Number(item || 0))
  }

  function activityLevel() {
    loading.value = true
    getSystemActivityLevel()
      .then((res) => {
        normalizeActivityData(res.data)
      })
      .catch(console.log)
      .finally(() => {
        loading.value = false
      })
  }

  onMounted(() => {
    activityLevel()
  })
</script>

<style lang="less" scoped>
  .mango-activity-rank {
    flex: 1;
    width: 100%;
    min-height: 0;
  }

  .mango-activity-rank__spin,
  :deep(.mango-activity-rank__spin .arco-spin-children) {
    display: flex;
    width: 100%;
    height: 100%;
    min-height: 0;
    flex-direction: column;
  }

  .mango-activity-rank__list {
    display: grid;
    gap: 12px;
    min-height: 0;
    padding: 12px 2px 4px;
    overflow-y: auto;
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

  .mango-activity-rank__empty {
    flex: 1;
    min-height: 120px;
  }

  @media (max-width: 1280px) {
    .mango-activity-rank__row {
      grid-template-columns: 3.75em minmax(0, 1fr) 34px;
      gap: 6px;
    }
  }
</style>
