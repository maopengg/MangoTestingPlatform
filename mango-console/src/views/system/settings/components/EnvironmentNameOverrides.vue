<template>
  <div class="mango-environment-overrides">
    <a-alert data-feedback-kind="validation" v-if="modelError" type="error">{{ modelError }}</a-alert>
    <div v-for="row in rows" :key="row.id" class="mango-environment-overrides__row">
      <a-select
        v-model="row.environment"
        :options="optionsFor(row)"
        placeholder="选择环境"
        :disabled="loading"
        aria-label="部署环境"
        @change="commit"
      />
      <a-input
        v-model="row.name"
        placeholder="实际显示名称"
        :max-length="32"
        :disabled="loading"
        aria-label="环境显示名称"
        @blur="commit"
        @press-enter="commit"
      />
      <a-button size="small" status="danger" :disabled="loading" @click="removeRow(row.id)">
        删除
      </a-button>
    </div>
    <a-button
      size="small"
      :loading="loading"
      :disabled="loading || Boolean(modelError) || rows.length >= options.length"
      @click="addRow"
    >增加</a-button>
  </div>
</template>

<script setup lang="ts">
  import { ref, toRaw, watch } from 'vue'

  interface EnvironmentOption {
    key: number | string
    title: string
  }
  interface OverrideRow {
    id: number
    environment?: number | string
    name: string
  }
  const props = defineProps<{
    modelValue: unknown
    options: EnvironmentOption[]
    loading: boolean
  }>()
  const emit = defineEmits<{
    (event: 'update:modelValue', value: Record<string, string>): void
    (event: 'save'): void
  }>()
  const rows = ref<OverrideRow[]>([])
  const modelError = ref('')
  let nextId = 0
  let lastEmission: Record<string, string> | undefined

  watch(
    () => props.modelValue,
    (value) => {
      // Own updates must not rebuild inputs or discard incomplete local rows.
      if (lastEmission !== undefined && toRaw(value) === lastEmission) return
      if (!value || typeof value !== 'object' || Array.isArray(value) || Object.values(value).some(name => typeof name !== 'string')) {
        rows.value = []; modelError.value = '环境名称配置格式异常，请重新读取系统配置'; return
      }
      modelError.value = ''
      rows.value = Object.entries(value as Record<string, string>).map(([environment, name]) => ({
        id: nextId++, environment: props.options.find(option => String(option.key) === environment)?.key ?? environment, name,
      }))
    },
    { immediate: true }
  )
  watch(() => props.options, options => {
    for (const row of rows.value) {
      row.environment = options.find(option => String(option.key) === String(row.environment))?.key ?? row.environment
    }
  })

  const optionsFor = (row: OverrideRow) => props.options.map((option) => ({
    value: option.key,
    label: option.title,
    disabled: rows.value.some((other) =>
      other.id !== row.id && String(other.environment) === String(option.key)
    ),
  }))
  const addRow = () => {
    if (props.loading || modelError.value || rows.value.length >= props.options.length) return
    rows.value.push({ id: nextId++, name: '' })
  }
  const hasValue = (row: OverrideRow) =>
    row.environment !== undefined && row.environment !== null &&
    String(row.environment) !== '' &&
    Boolean(row.name.trim()) && row.name.trim().length <= 32
  const isComplete = (row: OverrideRow) => hasValue(row) &&
    props.options.some(option => String(option.key) === String(row.environment))
  const publish = (completeRows: OverrideRow[]) => {
    if (new Set(completeRows.map(row => String(row.environment))).size !== completeRows.length) return
    const value = Object.fromEntries(completeRows.map((row) => [String(row.environment), row.name.trim()]))
    lastEmission = value
    emit('update:modelValue', value)
    emit('save')
  }
  const commit = () => {
    if (props.loading || modelError.value || rows.value.some((row) => !isComplete(row))) return
    publish(rows.value)
  }
  const removeRow = (id: number) => {
    if (props.loading || modelError.value) return
    rows.value = rows.value.filter((row) => row.id !== id)
    // Deleting a saved override also works while another row is still a draft.
    publish(rows.value.filter(hasValue))
  }
</script>

<style scoped>
  .mango-environment-overrides {
    display: grid;
    gap: var(--m-space-sm);
    min-width: 0;
    justify-items: start;
  }
  .mango-environment-overrides__row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1.2fr) auto;
    gap: var(--m-space-sm);
    align-items: center;
    width: 100%;
    min-width: 0;
  }
  @media (max-width: 640px) {
    .mango-environment-overrides__row {
      grid-template-columns: minmax(0, 1fr) auto;
    }
    .mango-environment-overrides__row > :first-child {
      grid-column: 1 / -1;
    }
  }
</style>
