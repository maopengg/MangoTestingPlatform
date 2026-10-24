<template>
  <a-cascader
    :model-value="modelValue"
    :field-names="fieldNames"
    :options="cascaderOptions"
    :placeholder="placeholder"
    :disabled="disabled"
    :allow-clear="allowClear"
    :allow-search="allowSearch"
    :loading="loading"
    :check-strictly="checkStrictly"
    value-key="key"
    @update:model-value="onUpdate"
    @change="onChange"
  />
</template>

<script lang="ts">
  type SharedModuleOption = {
    key: string | number
    title: string
    level?: number
    disabled?: boolean
    selectionDisabledByLevel?: boolean
    children?: SharedModuleOption[]
  }

  const pendingModuleRequests = new Map<string, Promise<SharedModuleOption[]>>()
</script>

<script lang="ts" setup>
  import { computed, onMounted, ref, watch } from 'vue'
  import { fieldNames } from '@/setting'
  import { getUserModuleTree } from '@/api/system/module'

  type ModuleOption = SharedModuleOption

  const props = defineProps({
    modelValue: {
      type: [String, Number],
      default: null,
    },
    projectProductId: {
      type: [String, Number, Array],
      default: null,
    },
    placeholder: {
      type: String,
      default: '请选择模块名称',
    },
    disabled: {
      type: Boolean,
      default: false,
    },
    allowClear: {
      type: Boolean,
      default: true,
    },
    allowSearch: {
      type: Boolean,
      default: true,
    },
    autoClear: {
      type: Boolean,
      default: true,
    },
    checkStrictly: {
      type: Boolean,
      default: false,
    },
    refreshToken: {
      type: [String, Number],
      default: 0,
    },
    maxSelectableLevel: {
      type: Number,
      default: undefined,
    },
    selectableLevel: {
      type: Number,
      default: 3,
    },
    maxDisplayLevel: {
      type: Number,
      default: 3,
    },
    excludedKeys: {
      type: Array,
      default: () => [],
    },
    showAllOption: {
      type: Boolean,
      default: false,
    },
    allOptionLabel: {
      type: String,
      default: '全部模块',
    },
  })

  const emit = defineEmits(['update:modelValue', 'change', 'loaded'])
  const options = ref<ModuleOption[]>([])
  const loading = ref(false)
  const loadVersion = ref(0)
  const cascaderOptions = computed(() => {
    const excludedKeys = new Set(props.excludedKeys.map((item) => String(item)))
    const hasMaxLevel =
      props.maxSelectableLevel !== undefined &&
      props.maxSelectableLevel !== null &&
      Number.isFinite(Number(props.maxSelectableLevel))
    const maxSelectableLevel = hasMaxLevel
      ? Number(props.maxSelectableLevel)
      : Number.POSITIVE_INFINITY
    const selectableLevel = Number(props.selectableLevel || 0)
    const hasMaxDisplayLevel =
      props.maxDisplayLevel !== undefined &&
      props.maxDisplayLevel !== null &&
      Number.isFinite(Number(props.maxDisplayLevel))
    const maxDisplayLevel = hasMaxDisplayLevel
      ? Number(props.maxDisplayLevel)
      : Number.POSITIVE_INFINITY

    function normalize(items: ModuleOption[], depth: number): ModuleOption[] {
      if (depth > maxDisplayLevel) return []
      return (items || []).reduce<ModuleOption[]>((result, item) => {
        if (excludedKeys.has(String(item.key))) return result
        const { children: rawChildren, ...option } = item
        const level = depth
        if (level > maxDisplayLevel) return result
        const children = level < maxDisplayLevel ? normalize(rawChildren || [], depth + 1) : []
        if (selectableLevel > 0 && level < selectableLevel && children.length === 0) {
          return result
        }
        const selectionDisabledByLevel =
          level > maxSelectableLevel || (selectableLevel > 0 && level !== selectableLevel)
        const normalizedOption = selectionDisabledByLevel
          ? {
              ...option,
              level,
              selectionDisabledByLevel: true,
              disabled: children.length === 0,
            }
          : { ...option, level }
        result.push(children.length ? { ...normalizedOption, children } : normalizedOption)
        return result
      }, [])
    }

    const normalizedOptions = normalize(options.value, 1)
    return props.showAllOption
      ? [{ key: '__all__', title: props.allOptionLabel, level: 0 }, ...normalizedOptions]
      : normalizedOptions
  })

  onMounted(() => {
    loadOptions()
  })

  watch(
    () => props.projectProductId,
    (value, oldValue) => {
      if (value === oldValue) {
        return
      }
      if (props.autoClear) {
        emit('update:modelValue', '')
      }
      loadOptions()
    }
  )

  watch(
    () => props.refreshToken,
    (value, oldValue) => {
      if (value === oldValue) return
      loadOptions()
    }
  )

  function getLeafValue(value: any) {
    if (Array.isArray(value)) {
      return value[value.length - 1] ?? null
    }
    return value ?? null
  }

  function getCacheKey(value: any) {
    const leafValue = getLeafValue(value)
    return leafValue === undefined || leafValue === null || leafValue === ''
      ? '__all__'
      : String(leafValue)
  }

  function fetchModuleOptions(projectProductId: any) {
    const key = getCacheKey(projectProductId)
    const pending = pendingModuleRequests.get(key)
    if (pending) {
      return pending
    }
    const request = getUserModuleTree(getLeafValue(projectProductId))
      .then((res) => {
        return Array.isArray(res.data) ? res.data : []
      })
      .finally(() => {
        pendingModuleRequests.delete(key)
      })
    pendingModuleRequests.set(key, request)
    return request
  }

  function loadOptions() {
    const version = loadVersion.value + 1
    loadVersion.value = version
    const cacheKey = getCacheKey(props.projectProductId)
    loading.value = true
    return fetchModuleOptions(props.projectProductId)
      .then((list) => {
        if (loadVersion.value !== version || getCacheKey(props.projectProductId) !== cacheKey) {
          return
        }
        options.value = list
        emit('loaded', cascaderOptions.value)
      })
      .catch(console.log)
      .finally(() => {
        if (loadVersion.value === version) {
          loading.value = false
        }
      })
  }

  function onUpdate(value: any) {
    if (!isSelectableValue(value)) return
    emit('update:modelValue', value)
  }

  function onChange(value: any) {
    if (!isSelectableValue(value)) return
    emit('change', value)
  }

  function isSelectableValue(value: any) {
    const key = getLeafValue(value)
    if (key === undefined || key === null || key === '') return true
    const queue = [...cascaderOptions.value]
    while (queue.length) {
      const option = queue.shift()
      if (!option) continue
      if (String(option.key) === String(key)) return !option.selectionDisabledByLevel
      if (option.children?.length) queue.push(...option.children)
    }
    return false
  }
</script>
