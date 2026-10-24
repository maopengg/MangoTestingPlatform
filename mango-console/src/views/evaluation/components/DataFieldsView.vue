<template>
  <div class="mango-data-fields-view">
    <dl v-if="kind === 'object' && entries.length" class="mango-data-fields-view__object">
      <div v-for="[key, value] in entries" :key="key" class="mango-data-fields-view__row">
        <dt :title="key">{{ label(key) }}</dt>
        <dd><DataFieldsView :data="value" :schema="schema?.properties?.[key]" /></dd>
      </div>
    </dl>
    <ol v-else-if="kind === 'array' && data.length" class="mango-data-fields-view__list">
      <li v-for="(value, index) in data" :key="index"><DataFieldsView :data="value" :schema="schema?.items" /></li>
    </ol>
    <span v-else class="mango-data-fields-view__value">{{ text }}</span>
  </div>
</template>
<script setup lang="ts">
  import { computed } from 'vue'
  import { fieldTitle } from './presentation'
  const props = defineProps<{ data: any; schema?: any }>()
  const kind = computed(() => Array.isArray(props.data) ? 'array' : props.data !== null && typeof props.data === 'object' ? 'object' : 'value')
  const entries = computed(() => kind.value === 'object' ? Object.entries(props.data) : [])
  const label = (key: string) => props.schema?.properties?.[key]?.title || fieldTitle(key)
  const text = computed(() => props.data === null ? '空值' : props.data === undefined ? '—' : props.data === '' ? '空文本' : typeof props.data === 'boolean' ? props.data ? '是' : '否' : kind.value !== 'value' ? '无' : String(props.data))
</script>
<style scoped>
  .mango-data-fields-view { min-width: 0; container-type: inline-size; }
  .mango-data-fields-view__object { margin: 0; }
  .mango-data-fields-view__row { display: grid; grid-template-columns: minmax(90px, 140px) minmax(0, 1fr); gap: var(--m-page-gap); padding-block: var(--m-space-sm); }
  .mango-data-fields-view__row dt { color: var(--m-text-2); overflow-wrap: anywhere; }
  .mango-data-fields-view__row dd { min-width: 0; margin: 0; }
  .mango-data-fields-view__list { margin: 0; padding-left: var(--m-card-padding); }
  .mango-data-fields-view__list > li + li { margin-top: var(--m-space-sm); }
  .mango-data-fields-view__value { white-space: pre-wrap; overflow-wrap: anywhere; }
  @container (max-width: 360px) { .mango-data-fields-view__row { grid-template-columns: minmax(0, 1fr); gap: var(--m-space-xs); } }
</style>
