<template>
  <div
    class="mango-product-module-level-select"
    :class="{ 'mango-product-module-level-select--without-labels': !showLabels }"
  >
    <div class="mango-product-module-level-select__field">
      <span v-if="showLabels">一级模块</span>
      <a-select
        aria-label="一级模块"
        :model-value="selectedPath[0]"
        :options="levelOneOptions"
        :field-names="fieldNames"
        :disabled="disabled"
        :loading="loading"
        :allow-clear="allowClear"
        allow-search
        placeholder="请选择一级模块"
        value-key="key"
        @update:model-value="(value) => onLevelChange(0, value)"
      />
    </div>
    <div class="mango-product-module-level-select__field">
      <span v-if="showLabels">二级模块</span>
      <a-select
        aria-label="二级模块"
        :model-value="selectedPath[1]"
        :options="levelTwoOptions"
        :field-names="fieldNames"
        :disabled="disabled || !selectedPath[0] || !levelTwoOptions.length"
        :loading="loading"
        :allow-clear="allowClear"
        allow-search
        :placeholder="levelTwoPlaceholder"
        value-key="key"
        @update:model-value="(value) => onLevelChange(1, value)"
      />
    </div>
    <div class="mango-product-module-level-select__field">
      <span v-if="showLabels">三级模块</span>
      <a-select
        aria-label="三级模块"
        :model-value="selectedPath[2]"
        :options="levelThreeOptions"
        :field-names="fieldNames"
        :disabled="disabled || !selectedPath[1] || !levelThreeOptions.length"
        :loading="loading"
        :allow-clear="allowClear"
        allow-search
        :placeholder="levelThreePlaceholder"
        value-key="key"
        @update:model-value="(value) => onLevelChange(2, value)"
      />
    </div>
  </div>
</template>

<script lang="ts" setup>
  import { computed, onMounted, ref, watch } from 'vue'
  import { getUserModuleTree } from '@/api/system/module'
  import { fieldNames } from '@/setting'

  type ModuleOption = {
    key: string | number
    title: string
    children?: ModuleOption[]
  }

  const props = defineProps({
    modelValue: {
      type: [String, Number],
      default: null,
    },
    projectProductId: {
      type: [String, Number, Array],
      default: null,
    },
    disabled: {
      type: Boolean,
      default: false,
    },
    allowClear: {
      type: Boolean,
      default: true,
    },
    autoClear: {
      type: Boolean,
      default: true,
    },
    showLabels: {
      type: Boolean,
      default: true,
    },
  })

  const emit = defineEmits(['update:modelValue', 'change', 'loaded'])
  const options = ref<ModuleOption[]>([])
  const selectedPath = ref<Array<string | number | undefined>>([])
  const loading = ref(false)
  const loadVersion = ref(0)

  const levelOneOptions = computed(() => toSelectOptions(options.value))
  const levelTwoOptions = computed(() =>
    toSelectOptions(findOption(options.value, selectedPath.value[0])?.children || [])
  )
  const levelThreeOptions = computed(() =>
    toSelectOptions(
      findOption(
        findOption(options.value, selectedPath.value[0])?.children || [],
        selectedPath.value[1]
      )?.children || []
    )
  )
  const levelTwoPlaceholder = computed(() => {
    if (!selectedPath.value[0]) return '请先选择一级模块'
    return levelTwoOptions.value.length ? '请选择二级模块（可不选）' : '当前无二级模块'
  })
  const levelThreePlaceholder = computed(() => {
    if (!selectedPath.value[1]) return '请先选择二级模块'
    return levelThreeOptions.value.length ? '请选择三级模块（可不选）' : '当前无三级模块'
  })

  onMounted(loadOptions)

  watch(
    () => props.projectProductId,
    (value, oldValue) => {
      if (value === oldValue) return
      selectedPath.value = []
      if (props.autoClear) emitValue(null)
      loadOptions()
    }
  )

  watch([() => props.modelValue, options], () => hydrateSelectedPath(), { deep: true })

  function getLeafValue(value: any) {
    return Array.isArray(value) ? value[value.length - 1] ?? null : value ?? null
  }

  function toSelectOptions(items: ModuleOption[]) {
    return items.map(({ key, title }) => ({ key, title }))
  }

  function findOption(items: ModuleOption[], key: any) {
    if (key === undefined || key === null || key === '') return undefined
    return items.find((item) => String(item.key) === String(key))
  }

  function findPath(items: ModuleOption[], target: any, path: Array<string | number> = []) {
    for (const item of items) {
      const currentPath = [...path, item.key]
      if (String(item.key) === String(target)) return currentPath
      const childPath = findPath(item.children || [], target, currentPath)
      if (childPath) return childPath
    }
    return null
  }

  function hydrateSelectedPath() {
    const value = getLeafValue(props.modelValue)
    if (value === null || value === '') {
      selectedPath.value = []
      return
    }
    selectedPath.value = findPath(options.value, value) || []
  }

  function onLevelChange(levelIndex: number, value: string | number | undefined) {
    const nextPath = selectedPath.value.slice(0, levelIndex)
    if (value !== undefined && value !== null && value !== '') nextPath[levelIndex] = value
    selectedPath.value = nextPath
    emitValue(nextPath[nextPath.length - 1] ?? null)
  }

  function emitValue(value: string | number | null) {
    emit('update:modelValue', value)
    emit('change', value)
  }

  async function loadOptions() {
    const projectProductId = getLeafValue(props.projectProductId)
    if (projectProductId === null || projectProductId === '') {
      options.value = []
      selectedPath.value = []
      return
    }
    const version = ++loadVersion.value
    loading.value = true
    try {
      const res = await getUserModuleTree(projectProductId)
      if (version !== loadVersion.value) return
      options.value = Array.isArray(res.data) ? res.data : []
      hydrateSelectedPath()
      emit('loaded', options.value)
    } catch (error) {
      console.log(error)
    } finally {
      if (version === loadVersion.value) loading.value = false
    }
  }
</script>

<style scoped>
  .mango-product-module-level-select {
    display: grid;
    grid-template-columns:
      max-content minmax(0, 1fr)
      max-content minmax(0, 1fr)
      max-content minmax(0, 1fr);
    align-items: center;
    gap: 8px 10px;
    width: 100%;
  }

  .mango-product-module-level-select__field {
    display: contents;
  }

  .mango-product-module-level-select--without-labels {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .mango-product-module-level-select__field > span {
    color: var(--m-muted);
    font-size: 13px;
    line-height: 32px;
    white-space: nowrap;
  }

  .mango-product-module-level-select__field :deep(.arco-select) {
    width: 100%;
    min-width: 0;
  }

  .mango-product-module-level-select__field :deep(.arco-select-view) {
    width: 100%;
  }

  @media (max-width: 720px) {
    .mango-product-module-level-select {
      grid-template-columns: max-content minmax(0, 1fr);
    }
  }
</style>
