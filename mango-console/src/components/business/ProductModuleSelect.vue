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
    @popup-visible-change="onPopupVisibleChange"
  >
    <template #empty>
      <div class="mango-empty-state">
        <template v-if="failed"><a-button size="small" :loading="loading" @click.stop="loadOptions">重试</a-button></template>
        <template v-else>暂无模块</template>
      </div>
    </template>
  </a-cascader>
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
  const moduleRequestScopes = new WeakMap<object, { identity: unknown[]; version: number }>()
  let nextModuleScope = 0
  function moduleRequestScope(store: object, identity: unknown[]): number {
    const scope = moduleRequestScopes.get(store)
    if (scope && scope.identity.every((value, index) => value === identity[index])) return scope.version
    const version = ++nextModuleScope
    moduleRequestScopes.set(store, { identity: [...identity], version })
    return version
  }
  function readModuleOptions(value: unknown): SharedModuleOption[] {
    if (!Array.isArray(value)) throw new Error('模块列表格式不正确')
    return value.map(value => {
      if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('模块格式不正确')
      const row = value as Record<string, unknown>
      if ((typeof row.key !== 'string' && (typeof row.key !== 'number' || !Number.isFinite(row.key))) || typeof row.title !== 'string') throw new Error('模块字段格式不正确')
      if (row.disabled !== undefined && typeof row.disabled !== 'boolean') throw new Error('模块状态格式不正确')
      const option: SharedModuleOption = { key: row.key, title: row.title }
      if (row.disabled !== undefined) option.disabled = row.disabled
      if (row.children !== undefined && row.children !== null) option.children = readModuleOptions(row.children)
      return option
    })
  }
</script>

<script lang="ts" setup>
import { reportLoadError } from '@/utils/load-error'

  import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from 'vue'
  import { fieldNames } from '@/setting'
  import { getUserModuleTree } from '@/api/system/module'
  import useUserStore from '@/store/modules/user'

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
  const user = useUserStore()
  const options = ref<ModuleOption[]>([])
  const loading = ref(false)
  const loadVersion = ref(0)
  const failed = ref(false)
  let active = true, disposed = false, mounted = false, needsLoad = true
  let sharedRequest: { key: string; promise: Promise<SharedModuleOption[]> } | null = null
  const identityScope = () => moduleRequestScope(user, [user.userId, user.roleId, user.token, user.selected_environment])
  function detachSharedRequest(): void {
    if (sharedRequest && pendingModuleRequests.get(sharedRequest.key) === sharedRequest.promise)
      pendingModuleRequests.delete(sharedRequest.key)
    sharedRequest = null
  }
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
    mounted = true
    void loadOptions()
  })

  watch(
    () => [getCacheKey(props.projectProductId), identityScope(), props.refreshToken],
    (value, oldValue) => {
      detachSharedRequest()
      if (props.autoClear && (value[0] !== oldValue[0] || value[1] !== oldValue[1])) {
        emit('update:modelValue', '')
      }
      options.value = []
      failed.value = false
      loadVersion.value++
      loading.value = false
      needsLoad = true
      if (mounted && active && !disposed) void loadOptions()
    },
    { flush: 'sync' }
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

  function fetchModuleOptions(projectProductId: unknown, key: string) {
    const pending = pendingModuleRequests.get(key)
    if (pending) {
      return pending
    }
    const request = getUserModuleTree(getLeafValue(projectProductId))
      .then((res) => {
        if (res.code !== 200) throw new Error('模块列表加载失败')
        return readModuleOptions(res.data)
      })
      .finally(() => {
        if (pendingModuleRequests.get(key) === request) pendingModuleRequests.delete(key)
      })
    pendingModuleRequests.set(key, request)
    return request
  }

  function loadOptions() {
    if (disposed || !active) return Promise.resolve()
    const version = loadVersion.value + 1
    loadVersion.value = version
    const scope = identityScope()
    const cacheKey = getCacheKey(props.projectProductId)
    const isCurrent = () => !disposed && active && loadVersion.value === version && identityScope() === scope && getCacheKey(props.projectProductId) === cacheKey
    loading.value = true
    failed.value = false
    needsLoad = true
    const key = `${scope}:${cacheKey}`, promise = fetchModuleOptions(props.projectProductId, key)
    sharedRequest = { key, promise }
    return promise
      .then((list) => {
        if (!isCurrent()) return
        options.value = list
        needsLoad = false
        emit('loaded', cascaderOptions.value)
      })
      .catch((loadFailure0) => { if (isCurrent()) (reportLoadError(loadFailure0, "加载失败，请重试", false), failed.value = true) })
      .finally(() => {
        if (isCurrent()) loading.value = false
        if (sharedRequest?.promise === promise) sharedRequest = null
      })
  }

  function onPopupVisibleChange(visible: boolean): void {
    if (visible && failed.value && !loading.value) void loadOptions()
  }
  onDeactivated(() => { active = false; detachSharedRequest(); loadVersion.value++; loading.value = false; needsLoad = true })
  onActivated(() => { active = true; if (mounted && needsLoad && !loading.value) void loadOptions() })
  onBeforeUnmount(() => { disposed = true; active = false; detachSharedRequest(); loadVersion.value++; loading.value = false })

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
