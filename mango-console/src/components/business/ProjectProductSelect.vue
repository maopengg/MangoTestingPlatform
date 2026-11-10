<template>
  <a-cascader
    :model-value="modelValue"
    :options="productOptions"
    :placeholder="placeholder"
    :disabled="disabled"
    :allow-clear="allowClear"
    :allow-search="allowSearch"
    :loading="loading"
    value-key="key"
    @update:model-value="onUpdate"
    @change="onChange"
    @popup-visible-change="onPopupVisibleChange"
  >
    <template #empty>
      <div class="mango-empty-state">
        <template v-if="failed"><a-button size="small" :loading="loading" @click.stop="loadOptions">重试</a-button></template>
        <template v-else>暂无项目或产品</template>
      </div>
    </template>
  </a-cascader>
</template>

<script lang="ts" setup>
import { reportLoadError } from '@/utils/load-error'

  import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from 'vue'
  import { useProject } from '@/store/modules/get-project'
  import useUserStore from '@/store/modules/user'

  const props = defineProps({
    modelValue: {
      type: [String, Number, Array],
      default: null,
    },
    placeholder: {
      type: String,
      default: '请选择项目/产品',
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
    currentProjectOnly: {
      type: Boolean,
      default: false,
    },
  })

  const emit = defineEmits(['update:modelValue', 'change'])
  const projectInfo = useProject()
  const user = useUserStore()
  const loading = ref(false)
  const failed = ref(false)
  let active = true, mounted = false, disposed = false, version = 0, needsLoad = true
  let pending: { version: number; promise: Promise<void> } | null = null
  const available = () => mounted && active && !disposed && (typeof document === 'undefined' || !document.hidden)
  const productOptions = computed(() => {
    const selectedProject = 'selectValue' in projectInfo ? projectInfo.selectValue : null
    if (!props.currentProjectOnly || !selectedProject) {
      return projectInfo.projectProduct
    }
    return projectInfo.projectProduct.filter(
      item => String(item.value) === String(selectedProject)
    )
  })

  function invalidate() {
    version++
    pending = null
    needsLoad = true
    loading.value = false
    failed.value = false
  }
  function loadOptions(): Promise<void> {
    if (!available()) return Promise.resolve()
    if (pending?.version === version) return pending.promise
    const requestVersion = version
    const current = () => available() && requestVersion === version
    loading.value = true
    failed.value = false
    const promise = projectInfo.projectProductName().then(() => {
      if (current()) {
        failed.value = projectInfo.optionErrors.products
        needsLoad = failed.value
      }
    }).catch((loadFailure0) => {
      if (current()) { (reportLoadError(loadFailure0, "加载失败，请重试", false), failed.value = true); needsLoad = true }
    }).finally(() => {
      if (current()) { loading.value = false; pending = null }
    })
    pending = { version, promise }
    return promise
  }
  function onPopupVisibleChange(visible: boolean) {
    if (visible && failed.value) void loadOptions()
  }
  watch(() => [user.userId, user.roleId, user.token, user.selected_environment], () => {
    invalidate()
    const currentVersion = version
    void Promise.resolve().then(() => { if (currentVersion === version) void loadOptions() })
  }, { flush: 'sync' })
  function onVisibilityChange() {
    if (document.hidden) invalidate()
    else if (active && needsLoad) void loadOptions()
  }
  onMounted(() => {
    mounted = true
    if (typeof document !== 'undefined') document.addEventListener('visibilitychange', onVisibilityChange)
    void loadOptions()
  })
  onActivated(() => { active = true; if (needsLoad) void loadOptions() })
  onDeactivated(() => { active = false; invalidate() })
  onBeforeUnmount(() => {
    disposed = true
    invalidate()
    if (typeof document !== 'undefined') document.removeEventListener('visibilitychange', onVisibilityChange)
  })

  function onUpdate(value: unknown) {
    emit('update:modelValue', value)
  }

  function onChange(value: unknown) {
    emit('change', value)
  }
</script>
