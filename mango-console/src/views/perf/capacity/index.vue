<template>
  <TableBody plain class="mango-detail-workbench-page mango-perf-page">
    <template #header>
      <TableHeader title="性能测试 / 执行器容量">
        <template #header-extra>
          <a-space>
            <a-button size="small" :loading="loading" @click="load">刷新</a-button>
          </a-space>
        </template>
      </TableHeader>
    </template>

    <template #default>
      <div class="mango-perf-capacity-page">
        <a-alert type="info">
          发压能力用于保护执行器本身。开始性能测试前，平台会根据场景峰值、已选执行器和可用容量进行校验；容量不足时禁止执行，避免执行器过载导致结果失真。
        </a-alert>

        <div class="mango-metric-grid mango-perf-capacity-metrics">
          <div class="mango-metric-card"><span>在线性能执行器</span><strong>{{ summary.online_count || 0 }} / {{ summary.executor_count || 0 }}</strong></div>
          <div class="mango-metric-card"><span>容量策略</span><strong>安全默认值</strong></div>
          <div class="mango-metric-card"><span>默认可调度 VU</span><strong>{{ formatCapacity(summary.available_vus) }}</strong></div>
          <div class="mango-metric-card"><span>默认可调度 RPS</span><strong>{{ formatCapacity(summary.available_rps) }}</strong></div>
        </div>

        <section class="mango-section-card">
          <div class="mango-section-title">
            <div><h2>调度规则</h2><p>这里展示平台如何计算执行器可承接的压力，不影响场景中的负载模型。</p></div>
          </div>
          <div class="mango-perf-capacity-rules">
            <div class="mango-soft-panel">
              <strong>1. 获取安全容量</strong>
              <p>按 {{ defaults.safe_vus || 100 }} VU、{{ defaults.safe_rps || 20 }} RPS 的统一保守值计算，避免维护未落地的人工校准数据。</p>
            </div>
            <div class="mango-soft-panel">
              <strong>2. 保留安全余量</strong>
              <p>默认只使用安全容量的 {{ safetyFactorPercent }}%，发压前请先确认执行器容量。</p>
            </div>
            <div class="mango-soft-panel">
              <strong>3. 扣除运行中预留</strong>
              <p>扣除其他性能运行已经占用的容量，剩余值才是新任务当前可调度的容量。</p>
            </div>
          </div>
        </section>

        <section class="mango-section-card mango-perf-capacity-list">
          <div class="mango-section-title">
            <div><h2>执行器发压能力</h2><p>仅在线且支持性能测试的执行器可以被场景选择；离线记录仅用于识别历史校准状态。</p></div>
          </div>
          <a-table :columns="capacityColumns" :data="rows" :loading="loading" :pagination="false" :scroll="{ x: CAPACITY_TABLE_SCROLL_X }">
            <template #columns>
              <a-table-column v-for="column in capacityColumns" :key="column.key" v-bind="column">
                <template #cell="{ record }">
                  <template v-if="column.key === 'executor'">
                    <div class="mango-perf-capacity-executor"><strong>{{ record.executor_name }}</strong><span>{{ record.fingerprint }}</span></div>
                  </template>
                  <a-tag v-else-if="column.key === 'online'" :color="record.online ? 'green' : 'gray'" size="small">{{ record.online ? '在线' : '离线' }}</a-tag>
                  <template v-else-if="column.key === 'engine'">
                    <strong>{{ String(record.engine || 'k6').toUpperCase() }}</strong>
                    <span class="mango-perf-capacity-subtext">{{ record.engine_version || '运行时上报版本' }}</span>
                  </template>
                  <a-tag v-else-if="column.key === 'calibration'" color="blue" size="small">安全默认值</a-tag>
                  <div v-else-if="column.key === 'safe_capacity'" class="mango-perf-capacity-values">
                    <span><b>{{ formatCapacity(record.safe_vus) }}</b> VU</span><span><b>{{ formatCapacity(record.safe_rps) }}</b> RPS</span>
                  </div>
                  <div v-else-if="column.key === 'available_capacity'" class="mango-perf-capacity-values">
                    <span><b>{{ formatCapacity(record.available_vus) }}</b> VU <small>已占 {{ formatCapacity(record.reserved_vus) }}</small></span>
                    <span><b>{{ formatCapacity(record.available_rps) }}</b> RPS <small>已占 {{ formatCapacity(record.reserved_rps) }}</small></span>
                  </div>
                  <template v-else-if="column.key === 'valid_until'"><span class="mango-perf-capacity-subtext">长期有效</span></template>
                </template>
              </a-table-column>
            </template>
            <template #empty><div class="mango-empty-state">暂无性能执行器，请先启动启用了 performance 能力的执行器</div></template>
          </a-table>
        </section>
      </div>
    </template>
  </TableBody>

</template>

<script setup lang="ts">
  import { computed, onMounted, reactive, ref } from 'vue'
  import { get } from '@/api/http'
  import { CAPACITY_TABLE_SCROLL_X, capacityColumns } from './config'

  const rows = ref<any[]>([])
  const loading = ref(false)
  const summary = reactive<any>({})
  const defaults = reactive<any>({})
  const safetyFactorPercent = computed(() => Math.round(Number(defaults.safety_factor || 0.7) * 100))

  function formatCapacity(value: unknown) { return new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 2 }).format(Number(value || 0)) }

  async function load() {
    loading.value = true
    try {
      const response: any = await get({ url: '/perf/capacity/overview' })
      rows.value = response.data?.rows || []
      Object.assign(summary, response.data?.summary || {})
      Object.assign(defaults, response.data?.defaults || {})
    } finally { loading.value = false }
  }

  onMounted(load)
</script>

<style scoped lang="less">
  .mango-perf-capacity-page { display: flex; flex-direction: column; gap: var(--m-page-gap); }
  .mango-perf-capacity-metrics { margin: 0; }
  .mango-perf-capacity-rules { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--m-page-gap); }
  .mango-perf-capacity-rules strong { color: var(--m-text); }
  .mango-perf-capacity-rules p { margin: 6px 0 0; color: var(--m-muted); line-height: 1.6; }
  .mango-perf-capacity-list { min-width: 0; }
  .mango-perf-capacity-executor, .mango-perf-capacity-values { display: flex; min-width: 0; flex-direction: column; gap: 3px; }
  .mango-perf-capacity-executor strong, .mango-perf-capacity-executor span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .mango-perf-capacity-executor span, .mango-perf-capacity-subtext, .mango-perf-capacity-values small { display: block; color: var(--m-muted); font-size: 12px; }
  .mango-perf-capacity-values span { color: var(--m-text-2); }
  .mango-perf-capacity-values small { display: inline; margin-left: 4px; }
  .mango-perf-capacity-tip { margin-bottom: var(--m-page-gap); }
  @container (max-width: 1099px) { .mango-perf-capacity-rules { grid-template-columns: 1fr; } }
</style>
