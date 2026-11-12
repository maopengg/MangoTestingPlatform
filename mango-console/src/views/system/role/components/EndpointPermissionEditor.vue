<template>
  <section class="mango-endpoint-editor">
    <div class="mango-endpoint-editor__filters">
      <a-radio-group v-if="protocols.length" v-model="protocol" type="button" size="small">
        <a-radio v-for="item in protocols" :key="item" :value="item">{{ item.toUpperCase() }}</a-radio>
      </a-radio-group>
      <a-input v-model="keyword" size="small" allow-clear placeholder="搜索名称、说明或 URL" aria-label="搜索接口" />
    </div>
    <a-table class="mango-native-scroll-table" :columns="columns" :data="filtered" row-key="id"
      :scroll="{ x: 520, y: 'var(--mango-endpoint-table-height)' }" :pagination="{ pageSize: 10, current: page, total: filtered.length, size: 'small' }"
      @page-change="page = $event" size="small">
      <template #endpoint="{ record }">
        <div class="mango-endpoint-editor__name mango-endpoint-editor__description" :title="record.description || record.name">
          {{ record.method }} · {{ record.description || record.name }}
        </div>
        <div v-for="url in record.urls" :key="url" class="mango-endpoint-editor__url">{{ url }}</div>
      </template>
      <template #effect="{ record }">
        <a-switch :model-value="record.fixed ? record.fixed_enabled : permissions[record.id] === 'endpoint_allow'"
          :disabled="readonly || record.fixed"
          checked-text="允许" unchecked-text="拒绝"
          :aria-label="`${record.description || record.name} 的接口权限`" @change="value => change(record.id, value === true)" />
      </template>
      <template #empty><div class="mango-empty-state">暂无匹配接口</div></template>
    </a-table>
  </section>
</template>
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { EndpointEffect, EndpointGroup, EndpointOverrides } from '../endpoint-permissions'
const props = defineProps<{ groups: EndpointGroup[]; menuKey: string; permissions: EndpointOverrides; readonly: boolean }>()
const emit = defineEmits<{ change: [id: string, effect: EndpointEffect] }>()
const protocol = ref('http'), keyword = ref(''), page = ref(1)
const group = computed(() => props.groups.find(item => item.menu_key === props.menuKey))
const protocols = computed(() => (['http', 'mcp'] as const).filter(
  value => group.value?.endpoints.some(item => item.protocol === value),
))
watch(protocols, values => {
  if (!values.some(value => value === protocol.value)) protocol.value = values[0] || 'http'
}, { immediate: true })
const columns = [
  { title: '功能 / 说明 / 地址', slotName: 'endpoint' },
  { title: '授权', slotName: 'effect', width: 120, align: 'center' as const },
]
const filtered = computed(() => {
  const term = keyword.value.trim().toLowerCase()
  return (group.value?.endpoints ?? []).filter(item => item.protocol === protocol.value &&
    (!term || [item.name, item.description, ...item.urls].join(' ').toLowerCase().includes(term)))
})
watch([() => props.menuKey, protocol, keyword, () => props.groups], () => { page.value = 1 })
function change(id: string, allowed: boolean) {
  const endpoint = group.value?.endpoints.find(item => item.id === id)
  if (!props.readonly && endpoint && !endpoint.fixed) emit('change', id, allowed ? 'endpoint_allow' : 'endpoint_deny')
}
</script>
<style scoped>
.mango-endpoint-editor { min-width: 0; padding: var(--m-card-padding); box-sizing: border-box; --mango-endpoint-table-height: max(200px, calc(100dvh - 440px)); }
.mango-endpoint-editor__filters { display: flex; flex-wrap: wrap; gap: var(--m-page-gap); margin: var(--m-page-gap) 0; }
.mango-endpoint-editor__filters :deep(.arco-input-wrapper) { min-width: 160px; flex: 1; }
.mango-endpoint-editor__name { color: var(--m-text); font-weight: 600; overflow-wrap: anywhere; }
.mango-endpoint-editor__description, .mango-endpoint-editor__url { white-space: pre-line; overflow-wrap: anywhere; }
.mango-endpoint-editor__description { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
</style>
