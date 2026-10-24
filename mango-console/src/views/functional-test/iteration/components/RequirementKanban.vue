<template>
  <a-spin class="mango-requirement-kanban__spin" :loading="loading">
    <div class="mango-requirement-kanban">
      <section
        v-for="column in columns"
        :key="column.status"
        class="mango-requirement-kanban__column"
        @dragover.prevent
        @drop="drop(column.status)"
      >
        <header class="mango-requirement-kanban__column-header">
          <span class="mango-requirement-kanban__status-dot" :data-status="column.status" />
          <strong>{{ column.title }}</strong>
          <a-badge :count="column.items.length" :max-count="999" />
        </header>
        <div class="mango-requirement-kanban__cards">
          <article
            v-for="item in column.items"
            :key="item.id"
            class="mango-requirement-kanban__card"
            draggable="true"
            @dragstart="dragStart(item)"
            @dragend="dragging = undefined"
            @click="emit('open', item)"
          >
            <div class="mango-requirement-kanban__card-key">
              <span>{{ item.requirement?.requirement_key || `REQ-${item.id}` }}</span>
              <a-space size="mini">
                <a-tag size="small">V{{ item.version_no }}</a-tag>
                <a-dropdown trigger="click" @click.stop>
                  <a-button size="mini" type="text"><icon-more /></a-button>
                  <template #content><a-doption @click="emit('cancel', item)">取消需求</a-doption></template>
                </a-dropdown>
              </a-space>
            </div>
            <div class="mango-requirement-kanban__card-title">
              {{ item.requirement_name || item.requirement?.name || '未命名需求' }}
            </div>
            <div class="mango-requirement-kanban__card-meta">
              <span>{{ priorityTitle(item.priority) }}</span>
              <span>{{ item.development_owner?.name || '未分配开发' }}</span>
              <span>{{ item.owner?.name || '未分配测试' }}</span>
            </div>
            <div class="mango-requirement-kanban__card-dates">
              {{ item.planned_start_date || '-' }} → {{ item.planned_submit_date || '-' }}
            </div>
            <div class="mango-requirement-kanban__metrics">
              <span>用例 {{ item.case_count || 0 }}</span>
              <span>进度 {{ formatRate(item.test_metrics?.progress) }}</span>
              <span>通过 {{ formatRate(item.test_metrics?.pass_rate) }}</span>
              <a-tag v-if="item.open_defect_count" size="small" color="red">缺陷 {{ item.open_defect_count }}</a-tag>
            </div>
          </article>
          <a-empty v-if="!column.items.length" description="暂无需求" />
        </div>
      </section>
    </div>
  </a-spin>
</template>

<script lang="ts" setup>
  import { ref } from 'vue'

  const emit = defineEmits<{
    (event: 'open', item: any): void
    (event: 'move', payload: { item: any; status: number }): void
    (event: 'cancel', item: any): void
  }>()
  const props = defineProps<{ columns: any[]; loading?: boolean; priorityOptions?: any[] }>()
  const dragging = ref<any>()
  const priorityTitle = (value: number) => props.priorityOptions?.find((item) => item.key === value)?.title || '-'
  const formatRate = (value: any) => `${Number(value || 0).toFixed(0)}%`
  const dragStart = (item: any) => { dragging.value = item }
  const drop = (status: number) => {
    if (!dragging.value || dragging.value.status === status) return
    emit('move', { item: dragging.value, status })
    dragging.value = undefined
  }
</script>

<style lang="less" scoped>
  .mango-requirement-kanban__spin { display: block; height: 100%; min-height: 0; }
  .mango-requirement-kanban { display: grid; height: 100%; min-height: 0; grid-template-columns: repeat(6, minmax(240px, 1fr)); gap: 10px; overflow: auto; padding: 10px; background: var(--m-surface); }
  .mango-requirement-kanban__column { display: flex; min-height: 100%; flex-direction: column; border: 1px solid var(--m-border); border-radius: var(--m-radius-md); background: var(--m-surface); }
  .mango-requirement-kanban__column-header { display: flex; align-items: center; gap: 8px; padding: 10px 12px; border-bottom: 1px solid var(--m-border); color: var(--m-text-1); }
  .mango-requirement-kanban__status-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--m-muted); }
  .mango-requirement-kanban__status-dot[data-status='3'], .mango-requirement-kanban__status-dot[data-status='5'] { background: var(--m-primary); }
  .mango-requirement-kanban__status-dot[data-status='4'] { background: var(--m-warning); }
  .mango-requirement-kanban__status-dot[data-status='6'] { background: var(--m-success); }
  .mango-requirement-kanban__cards { display: flex; min-height: 120px; flex: 1; flex-direction: column; gap: 8px; padding: 8px; overflow: auto; }
  .mango-requirement-kanban__card { cursor: grab; border: 1px solid var(--m-border); border-radius: var(--m-radius-md); background: var(--m-surface); padding: 10px; box-shadow: var(--m-shadow-sm); }
  .mango-requirement-kanban__card:hover { border-color: var(--m-primary); }
  .mango-requirement-kanban__card-key, .mango-requirement-kanban__metrics { display: flex; align-items: center; justify-content: space-between; gap: 6px; color: var(--m-text-3); font-size: 12px; }
  .mango-requirement-kanban__card-title { margin: 8px 0; color: var(--m-text-1); font-weight: 600; line-height: 1.5; }
  .mango-requirement-kanban__card-meta { display: flex; flex-wrap: wrap; gap: 4px 10px; color: var(--m-text-2); font-size: 12px; }
  .mango-requirement-kanban__card-dates { margin: 8px 0; color: var(--m-text-3); font-size: 12px; }
</style>
