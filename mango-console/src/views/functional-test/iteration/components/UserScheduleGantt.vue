<template>
  <div class="mango-user-gantt" :class="{ 'mango-user-gantt--loading': loading }">
    <div class="mango-user-gantt__toolbar">
      <a-space>
        <a-radio-group v-model="zoom" type="button" size="small">
          <a-radio value="day">按日</a-radio><a-radio value="week">按周</a-radio>
        </a-radio-group>
        <span>排期负责人 {{ summary.owner_count || 0 }} 人</span>
        <span>需求 {{ summary.requirement_count || 0 }} 条</span>
        <a-tag v-if="summary.overlap_count" color="orangered">排期重叠 {{ summary.overlap_count }}</a-tag>
        <a-tag v-if="summary.overdue_count" color="red">已逾期 {{ summary.overdue_count }}</a-tag>
      </a-space>
      <a-space>
        <a-input v-model="keyword" size="small" allow-clear placeholder="搜索需求" />
        <a-select v-model="ownerFilter" size="small" :options="ownerOptions" allow-clear placeholder="全部负责人" />
        <a-select v-model="statusFilter" size="small" :options="normalizedStatusOptions" allow-clear placeholder="全部状态" />
      </a-space>
      <span class="mango-user-gantt__hint">颜色表示交付状态；红色边框表示逾期，警示图标表示排期重叠</span>
    </div>
    <mango-panel-spin :loading="loading" class="mango-user-gantt__spin">
      <a-empty v-if="!groups.length" description="当前 Sprint 暂无需求排期" />
      <div v-else class="mango-user-gantt__viewport">
        <div ref="leftRef" class="mango-user-gantt__left" @scroll="syncVertical('left')">
          <div class="mango-user-gantt__header-cell">负责人 / 需求与子任务</div>
          <template v-for="group in groups" :key="group.owner_id || 'unassigned'">
            <div class="mango-user-gantt__owner">{{ group.owner_name }}<span>{{ group.items.length }} 条 · 重叠 {{ group.items.filter((item: any) => item.overlap).length }} · 逾期 {{ group.items.filter((item: any) => item.overdue).length }}</span></div>
            <div v-for="item in group.items" :key="item.id" class="mango-user-gantt__requirement">
              <strong>{{ item.requirement_key }}</strong>
              <span>{{ item.requirement_name }} · V{{ item.version_no }}</span>
            </div>
          </template>
        </div>
        <div ref="timelineRef" class="mango-user-gantt__timeline-scroll" @scroll="syncVertical('timeline')">
          <div class="mango-user-gantt__timeline" :style="{ width: `${timelineWidth}px` }">
            <div class="mango-user-gantt__axis" :style="gridStyle">
              <div v-for="unit in units" :key="unit.key" :class="['mango-user-gantt__axis-unit', { 'is-weekend': unit.weekend }]">{{ unit.label }}</div>
            </div>
            <template v-for="group in groups" :key="`timeline-${group.owner_id || 'unassigned'}`">
              <div class="mango-user-gantt__owner-track"></div>
              <div v-for="item in group.items" :key="`bar-${item.id}`" class="mango-user-gantt__track" :style="trackStyle">
                <template v-if="item.planned_start_date && item.planned_submit_date">
                  <a-tooltip :content="tooltip(item)">
                    <div
                      class="mango-user-gantt__bar"
                      :class="[`mango-user-gantt__bar--status-${item.status}`, { 'is-overdue': item.overdue }]"
                      :style="barStyle(item)"
                      @click="emit('edit', item)"
                    >
                      <span>{{ statusTitle(item.status) }}</span><span>{{ item.time_progress }}%</span>
                      <icon-exclamation-circle-fill v-if="item.overlap" />
                    </div>
                  </a-tooltip>
                </template>
                <span v-else class="mango-user-gantt__unscheduled">未完成排期</span>
              </div>
            </template>
            <div v-if="todayOffset !== null" class="mango-user-gantt__today" :style="{ left: `${todayOffset}px` }"><span>今天</span></div>
          </div>
        </div>
      </div>
    </mango-panel-spin>
  </div>
</template>

<script lang="ts" setup>
  import { computed, ref } from 'vue'
  import { scaleDensityPixels } from '@/hooks/useDisplayDensity'

  const props = withDefaults(defineProps<{ data?: any; loading?: boolean; statusOptions?: any[] }>(), {
    data: () => ({}), loading: false, statusOptions: () => [],
  })
  const emit = defineEmits<{ (event: 'edit', item: any): void }>()
  const zoom = ref<'day' | 'week'>('day')
  const keyword = ref('')
  const ownerFilter = ref<number>()
  const statusFilter = ref<number>()
  const leftRef = ref<HTMLElement>()
  const timelineRef = ref<HTMLElement>()
  let syncing = false
  const fallbackStatusOptions = [
    { value: 1, label: '需求池' },
    { value: 2, label: '需求就绪' },
    { value: 3, label: '开发中' },
    { value: 4, label: '待提测' },
    { value: 5, label: '测试中' },
    { value: 6, label: 'PM验收' },
    { value: 7, label: '已取消' },
    { value: 8, label: '待开发' },
    { value: 9, label: '待发布' },
    { value: 10, label: '已发布' },
  ]
  const sourceGroups = computed(() => props.data?.groups || [])
  const groups = computed(() => sourceGroups.value
    .filter((group: any) => ownerFilter.value === undefined || group.owner_id === ownerFilter.value)
    .map((group: any) => ({ ...group, items: group.items.filter((item: any) => {
      const matchesKeyword = !keyword.value || `${item.requirement_key} ${item.requirement_name}`.toLowerCase().includes(keyword.value.toLowerCase())
      return matchesKeyword && (statusFilter.value === undefined || Number(item.status) === Number(statusFilter.value))
    }) }))
    .filter((group: any) => group.items.length))
  const summary = computed(() => ({
    owner_count: groups.value.filter((item: any) => item.owner_id).length,
    requirement_count: groups.value.reduce((total: number, item: any) => total + item.items.length, 0),
    overlap_count: groups.value.reduce((total: number, item: any) => total + item.items.filter((row: any) => row.overlap).length, 0),
    overdue_count: groups.value.reduce((total: number, item: any) => total + item.items.filter((row: any) => row.overdue).length, 0),
  }))
  const ownerOptions = computed(() => sourceGroups.value.map((item: any) => ({ value: item.owner_id, label: item.owner_name })))
  const normalizedStatusOptions = computed(() => {
    const options = props.statusOptions.map((item: any) => ({
      value: Number(item.key ?? item.value),
      label: item.title ?? item.label,
    })).filter((item: any) => Number.isFinite(item.value) && item.label)
    return options.length ? options : fallbackStatusOptions
  })
  const parseDate = (value: string) => {
    const [year, month, day] = String(value || '').slice(0, 10).split('-').map(Number)
    return new Date(year, month - 1, day)
  }
  const addDays = (date: Date, days: number) => new Date(date.getFullYear(), date.getMonth(), date.getDate() + days)
  const diffDays = (start: Date, end: Date) => Math.round((end.getTime() - start.getTime()) / 86400000)
  const startDate = computed(() => parseDate(props.data?.iteration?.start_date))
  const endDate = computed(() => parseDate(props.data?.iteration?.end_date))
  const dayCount = computed(() => Math.max(1, diffDays(startDate.value, endDate.value) + 1))
  const unitDays = computed(() => zoom.value === 'day' ? 1 : 7)
  const unitWidth = computed(() => scaleDensityPixels(zoom.value === 'day' ? 72 : 112))
  const unitCount = computed(() => Math.ceil(dayCount.value / unitDays.value))
  const timelineWidth = computed(() => Math.max(scaleDensityPixels(720), unitCount.value * unitWidth.value))
  const units = computed(() => Array.from({ length: unitCount.value }, (_, index) => {
    const current = addDays(startDate.value, index * unitDays.value)
    return {
      key: current.toISOString(),
      label: zoom.value === 'day' ? `${current.getMonth() + 1}/${current.getDate()}` : `${current.getMonth() + 1}/${current.getDate()} 起`,
      weekend: zoom.value === 'day' && [0, 6].includes(current.getDay()),
    }
  }))
  const gridStyle = computed(() => ({ gridTemplateColumns: `repeat(${unitCount.value}, ${unitWidth.value}px)` }))
  const trackStyle = computed(() => ({ backgroundSize: `${unitWidth.value}px 100%` }))
  const pixelsPerDay = computed(() => timelineWidth.value / dayCount.value)
  const todayOffset = computed(() => {
    if (!props.data?.today) return null
    const offset = diffDays(startDate.value, parseDate(props.data.today))
    return offset >= 0 && offset < dayCount.value ? (offset + 0.5) * pixelsPerDay.value : null
  })
  function barStyle(item: any) {
    const start = Math.max(0, diffDays(startDate.value, parseDate(item.planned_start_date)))
    const end = Math.min(dayCount.value - 1, diffDays(startDate.value, parseDate(item.planned_submit_date)))
    const inset = scaleDensityPixels(4)
    return {
      left: `${start * pixelsPerDay.value + inset}px`,
      width: `${Math.max(scaleDensityPixels(28), (end - start + 1) * pixelsPerDay.value - inset * 2)}px`,
    }
  }
  function statusTitle(value: any) {
    return normalizedStatusOptions.value.find((item) => item.value === Number(value))?.label || `状态 ${value}`
  }
  function tooltip(item: any) {
    const overlapText = item.overlap ? `与 ${item.overlap_with?.join('、') || '同负责人其他需求'} 重叠` : ''
    const flags = [item.overdue ? '已逾期' : '', overlapText].filter(Boolean).join('；')
    return `${item.planned_start_date} 至 ${item.planned_submit_date}｜${statusTitle(item.status)}｜时间进度 ${item.time_progress}%${flags ? `｜${flags}` : ''}`
  }
  function syncVertical(source: 'left' | 'timeline') {
    if (syncing) return
    syncing = true
    const from = source === 'left' ? leftRef.value : timelineRef.value
    const target = source === 'left' ? timelineRef.value : leftRef.value
    if (from && target) target.scrollTop = from.scrollTop
    requestAnimationFrame(() => { syncing = false })
  }
</script>

<style lang="less" scoped>
  .mango-user-gantt { display: flex; height: 100%; min-height: 0; flex-direction: column; color: var(--m-text); }
  .mango-user-gantt__toolbar { display: flex; min-height: 40px; align-items: center; justify-content: space-between; gap: 8px; padding: 4px 12px; border-bottom: 1px solid var(--m-border); background: var(--m-surface); }
  .mango-user-gantt__hint { color: var(--m-muted); font-size: 12px; }
  .mango-user-gantt__spin, .mango-user-gantt__spin :deep(> .mango-panel-spin__content) { display: flex; flex: 1; min-height: 0; flex-direction: column; }
  .mango-user-gantt__viewport { display: grid; flex: 1; min-height: 0; grid-template-columns: 280px minmax(0, 1fr); overflow: hidden; }
  .mango-user-gantt__left { z-index: 2; overflow-y: auto; border-right: 1px solid var(--m-border); background: var(--m-surface); }
  .mango-user-gantt__header-cell, .mango-user-gantt__axis { position: sticky; top: 0; z-index: 3; height: 38px; box-sizing: border-box; border-bottom: 1px solid var(--m-border); background: var(--m-surface-soft); font-weight: 600; }
  .mango-user-gantt__header-cell { display: flex; align-items: center; padding: 0 12px; }
  .mango-user-gantt__owner, .mango-user-gantt__owner-track { height: 34px; box-sizing: border-box; border-bottom: 1px solid var(--m-border); background: var(--m-surface-soft); }
  .mango-user-gantt__owner { display: flex; align-items: center; justify-content: space-between; padding: 0 12px; font-weight: 600; }
  .mango-user-gantt__owner span { color: var(--m-muted); font-size: 12px; font-weight: 400; }
  .mango-user-gantt__requirement, .mango-user-gantt__track { height: 48px; box-sizing: border-box; border-bottom: 1px solid var(--m-border); }
  .mango-user-gantt__requirement { display: flex; flex-direction: column; justify-content: center; padding: 0 12px; overflow: hidden; }
  .mango-user-gantt__requirement strong, .mango-user-gantt__requirement span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .mango-user-gantt__requirement span { color: var(--m-muted); font-size: 12px; }
  .mango-user-gantt__timeline-scroll { min-width: 0; overflow: auto; }
  .mango-user-gantt__timeline { position: relative; min-height: 100%; }
  .mango-user-gantt__axis { display: grid; }
  .mango-user-gantt__axis-unit { display: flex; align-items: center; justify-content: center; border-right: 1px solid var(--m-border); color: var(--m-text-2); font-size: 12px; }
  .mango-user-gantt__axis-unit.is-weekend { background: color-mix(in srgb, var(--m-warning) 8%, var(--m-surface)); color: var(--m-muted); }
  .mango-user-gantt__track { position: relative; background-image: linear-gradient(to right, var(--m-border) 1px, transparent 1px); }
  .mango-user-gantt__bar { position: absolute; top: 8px; display: flex; height: 32px; align-items: center; justify-content: space-between; gap: 6px; overflow: hidden; padding: 0 9px; box-sizing: border-box; border: 1px solid var(--m-primary-border); border-radius: var(--m-radius-md); background: var(--m-primary-soft); color: var(--m-primary); cursor: pointer; font-size: 12px; white-space: nowrap; }
  .mango-user-gantt__bar--status-1 { border-color: var(--m-border-strong); background: var(--m-surface-soft); color: var(--m-muted); }
  .mango-user-gantt__bar--status-2 { border-color: color-mix(in srgb, var(--m-chart-5) 35%, var(--m-border)); background: color-mix(in srgb, var(--m-chart-5) 14%, var(--m-surface)); color: var(--m-chart-5); }
  .mango-user-gantt__bar--status-3 { border-color: var(--m-primary-border); background: var(--m-primary-soft); color: var(--m-primary); }
  .mango-user-gantt__bar--status-4 { border-color: color-mix(in srgb, var(--m-warning) 35%, var(--m-border)); background: color-mix(in srgb, var(--m-warning) 14%, var(--m-surface)); color: var(--m-warning); }
  .mango-user-gantt__bar--status-5 { border-color: color-mix(in srgb, var(--m-chart-2) 35%, var(--m-border)); background: color-mix(in srgb, var(--m-chart-2) 14%, var(--m-surface)); color: var(--m-chart-2); }
  .mango-user-gantt__bar--status-6 { border-color: color-mix(in srgb, var(--m-success) 35%, var(--m-border)); background: color-mix(in srgb, var(--m-success) 14%, var(--m-surface)); color: var(--m-success); }
  .mango-user-gantt__bar--status-7 { border-color: var(--m-border-strong); background: var(--m-surface-soft); color: var(--m-muted); }
  .mango-user-gantt__bar--status-8 { border-color: color-mix(in srgb, var(--m-chart-5) 35%, var(--m-border)); background: color-mix(in srgb, var(--m-chart-5) 12%, var(--m-surface)); color: var(--m-chart-5); }
  .mango-user-gantt__bar--status-9 { border-color: color-mix(in srgb, var(--m-warning) 35%, var(--m-border)); background: color-mix(in srgb, var(--m-warning) 12%, var(--m-surface)); color: var(--m-warning); }
  .mango-user-gantt__bar--status-10 { border-color: color-mix(in srgb, var(--m-success) 35%, var(--m-border)); background: color-mix(in srgb, var(--m-success) 12%, var(--m-surface)); color: var(--m-success); }
  .mango-user-gantt__bar.is-overdue { border-color: var(--m-danger); box-shadow: inset 0 0 0 1px var(--m-danger); }
  .mango-user-gantt__unscheduled { position: absolute; top: 15px; left: 12px; color: var(--m-muted); font-size: 12px; }
  .mango-user-gantt__today { position: absolute; z-index: 2; top: 38px; bottom: 0; width: 1px; background: var(--m-danger); pointer-events: none; }
  .mango-user-gantt__today span { position: sticky; top: 42px; display: inline-block; transform: translateX(-50%); padding: 1px 4px; border-radius: var(--m-radius-sm); background: var(--m-danger); color: var(--m-on-danger); font-size: 11px; }
</style>
