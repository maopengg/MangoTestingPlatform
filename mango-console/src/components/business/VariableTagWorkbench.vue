<template>
  <div class="mango-variable-tags-workbench" :class="{ 'mango-variable-tags-workbench--collapsed': collapsed }">
    <aside class="mango-variable-tags-panel mango-section-card" aria-label="变量分类">
      <div class="mango-variable-tags-head">
        <div v-if="!collapsed"><h3>变量分类</h3><p>按标签筛选变量</p></div>
        <a-tooltip :content="collapsed ? '展开变量分类' : '收起变量分类'">
          <a-button class="mango-variable-tags-collapse" size="small" type="text" :aria-label="collapsed ? '展开变量分类' : '收起变量分类'" @click="collapsed = !collapsed">
            <IconLeft v-if="!collapsed" /><IconRight v-else />
          </a-button>
        </a-tooltip>
      </div>
      <template v-if="!collapsed">
        <div class="mango-variable-tags-search"><a-input-search v-model="keyword" size="small" allow-clear placeholder="搜索分类" /></div>
        <MangoPanelSpin :loading="loading" class="mango-variable-tags-list">
          <a-button v-if="failed" size="small" :loading="loading" @click="refresh">重新加载</a-button>
          <button v-for="item in entries" :key="item.key" type="button" class="mango-variable-tags-entry"
            :class="{ 'mango-variable-tags-entry--active': modelValue === item.value }"
            :aria-pressed="modelValue === item.value" :title="item.name" @click="emit('update:modelValue', item.value)">
            <span>{{ item.name }}</span><small>{{ item.count }}</small>
          </button>
        </MangoPanelSpin>
      </template>
    </aside>
    <div class="mango-variable-tags-table"><slot /></div>
  </div>
</template>
<script setup lang="ts">
  import { computed, onBeforeUnmount, onDeactivated, onActivated, ref, watch } from 'vue'
  import { IconLeft, IconRight } from '@arco-design/web-vue/es/icon'
  import MangoPanelSpin from '@/components/feedback/MangoPanelSpin.vue'
  import { reportLoadError } from '@/utils/load-error'
  import useUserStore from '@/store/modules/user'
  import type { VariableTagReader, VariableTagSummary } from './variable-tags'
  const props = defineProps<{ modelValue: string | null; query: Record<string, unknown>; read: VariableTagReader }>()
  const emit = defineEmits<{ (event: 'update:modelValue', value: string | null): void }>()
  const collapsed = ref(false), keyword = ref(''), loading = ref(false), failed = ref(false)
  const summary = ref<VariableTagSummary>({ total: 0, untagged: 0, items: [] })
  let sequence = 0, active = true
  let pending: { token: number; key: string; promise: Promise<void> } | null = null
  let loadedKey: string | null = null
  const user = useUserStore()
  const summaryQuery = computed(() => Object.fromEntries(Object.entries(props.query)
    .filter(([key]) => !['tag', 'untagged', 'page', 'pageSize', 'tag_summary'].includes(key))
    .sort(([left], [right]) => left.localeCompare(right))))
  const queryKey = computed(() => JSON.stringify(summaryQuery.value))
  const identity = computed(() => [user.userId, user.roleId, user.token, user.selected_environment])
  const tagEntries = computed(() => props.modelValue && !summary.value.items.some(item => item.name === props.modelValue)
    ? [...summary.value.items, { name: props.modelValue, count: 0 }] : summary.value.items)
  const entries = computed(() => [
    { key: 'all', value: null, name: '全部', count: summary.value.total },
    { key: 'empty', value: '', name: '未分类', count: summary.value.untagged },
    ...tagEntries.value.filter(item => item.name.toLowerCase().includes(keyword.value.trim().toLowerCase()))
      .map(item => ({ ...item, key: `tag:${item.name}`, value: item.name })),
  ])
  const names = computed(() => summary.value.items.map(item => item.name))
  function refresh(): Promise<void> {
    if (!active) return Promise.resolve()
    const key = queryKey.value
    if (pending?.token === sequence && pending.key === key) return pending.promise
    const token = ++sequence
    loading.value = true; failed.value = false
    const promise = (async () => {
      try {
        const result = await props.read({ ...summaryQuery.value, tag_summary: true })
        if (token !== sequence || !active) return
        summary.value = result.data
        loadedKey = key
      } catch (error) {
        if (token === sequence && active) { failed.value = true; reportLoadError(error, '分类加载失败', false) }
      }
    })().finally(() => {
      if (token === sequence) loading.value = false
      if (pending?.token === token) pending = null
    })
    pending = { token, key, promise }
    return promise
  }
  function invalidate() { sequence++; pending = null; loadedKey = null; loading.value = false; summary.value = { total: 0, untagged: 0, items: [] } }
  function refreshAfterMutation() { invalidate(); return refresh() }
  watch([queryKey, identity], () => { invalidate(); void refresh() }, { immediate: true })
  watch(identity, () => {
    invalidate(); emit('update:modelValue', null)
  }, { flush: 'sync' })
  onDeactivated(() => { active = false; invalidate() })
  onActivated(() => { active = true; if (loadedKey !== queryKey.value) void refresh() })
  onBeforeUnmount(() => { active = false; invalidate() })
  defineExpose({ refresh, refreshAfterMutation, invalidate, names })
</script>
<style scoped>
  .mango-variable-tags-workbench { display: grid; grid-template-columns: 160px minmax(0, 1fr); gap: var(--m-page-gap); flex: 1; min-height: 0; min-width: 0; overflow: hidden; }
  .mango-variable-tags-workbench--collapsed { grid-template-columns: 36px minmax(0, 1fr); }
  .mango-variable-tags-workbench--collapsed .mango-variable-tags-panel { align-items: center; padding: 8px 4px; }
  .mango-variable-tags-panel { display: flex; flex-direction: column; gap: var(--m-page-gap); min-height: 0; min-width: 0; border-color: var(--m-border-strong); background: var(--m-surface); overflow: hidden; }
  .mango-variable-tags-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; padding-bottom: 2px; }
  .mango-variable-tags-head h3 { margin: 0; color: var(--m-text); font-size: 14px; font-weight: 600; line-height: 20px; white-space: nowrap; }
  .mango-variable-tags-head p { margin: 2px 0 0; color: var(--m-muted); font-size: 11px; line-height: 16px; }
  .mango-variable-tags-collapse { width: 28px; height: 28px; flex: 0 0 28px; padding: 0; color: var(--m-text-2); }
  .mango-variable-tags-collapse:hover { color: var(--m-primary); background: var(--m-fill-2); }
  .mango-variable-tags-search { padding: 8px; border: 1px solid var(--m-border); border-radius: var(--m-radius-md); background: var(--m-surface-soft); }
  .mango-variable-tags-list { flex: 1; min-height: 0; overflow-y: scroll; }
  .mango-variable-tags-entry { display: flex; align-items: center; justify-content: space-between; gap: var(--m-page-gap); width: 100%; padding: 6px; border: 0; border-radius: var(--m-radius-sm); background: transparent; color: var(--m-text); cursor: pointer; text-align: left; font-size: 13px; line-height: 20px; }
  .mango-variable-tags-entry span { overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
  .mango-variable-tags-entry small { color: var(--m-muted); font-variant-numeric: tabular-nums; }
  .mango-variable-tags-entry:hover { background: var(--m-surface-soft); }
  .mango-variable-tags-entry--active { background: var(--m-primary-soft); color: var(--m-primary); font-weight: 600; }
  .mango-variable-tags-entry:focus-visible { outline: 2px solid var(--m-primary); outline-offset: -2px; }
  .mango-variable-tags-table { display: flex; flex-direction: column; min-width: 0; min-height: 0; overflow: hidden; }
</style>
