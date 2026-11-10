<template>
  <div class="mango-report-delivery">
    <a-spin :loading="metadataLoading">
      <template v-if="metadataError"></template>
      <template v-else-if="draft">
        <div v-for="field in REPORT_DELIVERY_FIELDS" :key="field.key" class="mango-system-settings__row">
          <div class="mango-system-settings__label-wrap"><span class="mango-system-settings__label">{{ field.label }}</span></div>
          <div class="mango-system-settings__type"><a-tag v-if="field.type !== 'text'" size="small">普通配置</a-tag></div>
          <div class="mango-system-settings__control">
            <a-switch v-if="field.type === 'switch'"  v-model="draft[field.key]" :loading="loading" :disabled="loading" :aria-label="field.label" size="medium" @change="save" />
            <a-input-number v-else-if="field.type === 'number'"  v-model="draft[field.key]" class="mango-system-settings__input mango-system-settings__input--number" :disabled="loading" :aria-label="field.label" :min="300" :max="604800" :precision="0" size="medium" @blur="save" @press-enter="save" />
            <span v-else>{{ field.text }}</span>
          </div>
        </div>
        <div class="mango-system-settings__row">
          <div class="mango-system-settings__control">
            <a-button size="small" :loading="sampling" @click="sample">下载 HTML</a-button>
            <span v-if="loading" role="status">正在保存…</span>
          </div>
        </div>
      </template>
    </a-spin>
  </div>
</template>

<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { onMounted, onActivated, onDeactivated, onBeforeUnmount, ref, watch } from 'vue'
  import { useRoute } from 'vue-router'
  import { Message } from '@arco-design/web-vue'
  import useUserStore from '@/store/modules/user'
  import usePermissionStore from '@/store/modules/permission'
  import { downloadSampleReport, getReportDeliveryMetadata } from '@/api/system/offline_report'
  import { REPORT_DELIVERY_FIELDS } from '../config'
  import { parseReportDeliveryConfig, parseReportDeliveryMetadata } from '../report-delivery'
  import type { ReportDeliveryConfig } from '../report-delivery'

  const props = defineProps<{ modelValue: unknown; loading: boolean }>()
  const emit = defineEmits<{ (event: 'update:modelValue', value: ReportDeliveryConfig): void; (event: 'save'): void }>()
  const route = useRoute(), user = useUserStore(), permission = usePermissionStore(), pagePath = route.path
  const draft = ref<ReportDeliveryConfig | null>(null)
  const defaults = ref<ReportDeliveryConfig | null>(null)
  const metadataLoading = ref(true)
  const metadataError = ref('')
  const sampling = ref(false)
  let mounted = false, active = true, disposed = false, needsMetadata = true
  let contextVersion = 0, requestVersion = 0
  let pendingMetadata: Promise<void> | null = null
  let sampleController: AbortController | null = null
  const available = () => mounted && active && !disposed && route.path === pagePath && document.visibilityState === 'visible'
  const identity = () => JSON.stringify([route.fullPath, user.userId, user.roleId, user.token, user.selected_environment, permission.permissionKeys])
  const current = (version: number, key: string) => available() && version === contextVersion && key === identity()
  function syncDraft(value: unknown) {
    if (!defaults.value) return
    try { draft.value = parseReportDeliveryConfig(value, defaults.value); metadataError.value = '' }
    catch (loadFailure0) { draft.value = null; (reportLoadError(loadFailure0, "加载失败，请重试", false), metadataError.value = '报告配置格式异常，请重新读取系统配置') }
  }
  watch(() => props.modelValue, syncDraft)
  function loadMetadata(): Promise<void> {
    if (!available()) { needsMetadata = true; return Promise.resolve() }
    if (pendingMetadata) return pendingMetadata
    const version = ++requestVersion, context = contextVersion, key = identity()
    const valid = () => version === requestVersion && current(context, key)
    metadataLoading.value = true; metadataError.value = ''; needsMetadata = false
    const promise = Promise.resolve().then(async () => {
      try {
        if (!valid()) return
        const result = parseReportDeliveryMetadata(await getReportDeliveryMetadata())
        if (!valid()) return
        defaults.value = result; syncDraft(props.modelValue)
      } catch (loadFailure1) { if (valid()) { defaults.value = null; draft.value = null; (reportLoadError(loadFailure1, "配置选项加载失败，请重试", false), metadataError.value = '配置选项加载失败，请重试') } }
      finally { if (valid()) { metadataLoading.value = false; pendingMetadata = null } }
    })
    pendingMetadata = promise
    return promise
  }
  function save() {
    if (!available() || props.loading || metadataLoading.value || metadataError.value || !draft.value) return
    try {
      const payload = parseReportDeliveryConfig(draft.value)
      emit('update:modelValue', payload); emit('save')
    } catch { Message.warning('链接有效期必须是300～604800秒的整数，请检查报告配置') }
  }
  async function sample() {
    if (!available() || sampling.value || metadataLoading.value || metadataError.value || !draft.value) return
    const context = contextVersion, key = identity(), controller = new AbortController()
    sampleController = controller
    sampling.value = true
    try { await downloadSampleReport(controller.signal) }
    catch { if (current(context, key) && !controller.signal.aborted) Message.error('下载失败，请重试') }
    finally { sampling.value = false; if (sampleController === controller) sampleController = null }
  }
  function pause() {
    contextVersion++; requestVersion++; pendingMetadata = null; needsMetadata = true
    defaults.value = null; draft.value = null; metadataLoading.value = false
    sampleController?.abort()
  }
  function resume() { if (available() && needsMetadata) void loadMetadata() }
  function visibilityChanged() { if (document.visibilityState === 'visible') resume(); else pause() }
  watch(identity, () => { pause(); metadataError.value = ''; resume() }, { flush: 'sync' })
  onMounted(() => { mounted = true; document.addEventListener('visibilitychange', visibilityChanged); resume() })
  onActivated(() => { active = true; resume() })
  onDeactivated(() => { active = false; pause() })
  onBeforeUnmount(() => { disposed = true; pause(); document.removeEventListener('visibilitychange', visibilityChanged) })
</script>

<style scoped>
  .mango-report-delivery { width: 100%; min-width: 0; }
  .mango-report-delivery :deep(.arco-spin) { display: block; width: 100%; min-height: var(--m-control-height-medium); }
</style>
