<template>
  <ModalDialog modal-class="mango-simple-form-modal" ref="dialog" title="编辑任务精细化配置" :width="560" confirm-text="保存" @confirm="save" @cancel="close">
    <template #content>
      <div class="mango-task-fine-summary">
        <strong>{{ task?.name }}</strong>
        <span>任务组：{{ task?.task_group_name || '—' }}。以下配置独立保存，任务组同步不会覆盖。</span>
      </div>
      <a-alert v-if="saveError" type="error">{{ saveError }}</a-alert>
      <a-form auto-label-width :model="form" layout="horizontal" class="mango-task-fine-form mango-simple-form">
        <a-form-item class="mango-simple-form-item" label="API 并发">
          <a-input-number v-model="form.api_concurrency_limit" :min="1" :max="platformLimit" :precision="0" allow-clear
            :disabled="saving || !supportsApi" placeholder="留空使用平台默认并发" />
          <template #extra>{{ supportsApi ? `每份报告的上限；当前平台容量 ${platformLimit}` : '当前类型不包含API，此配置暂不生效' }}</template>
        </a-form-item>
        <a-form-item class="mango-simple-form-item" label="负责人" required>
          <a-select v-model="form.case_people" :options="availableUsers" :field-names="fieldNames" allow-search :disabled="saving" />
        </a-form-item>
        <a-form-item class="mango-simple-form-item" label="报告保留策略">
          <a-select v-model="form.report_retention_policy" :options="retentionOptions" :field-names="fieldNames" :disabled="saving" />
        </a-form-item>
      </a-form>
    </template>
  </ModalDialog>
</template>

<script setup lang="ts">
import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, reactive, ref, watch } from 'vue'
import { Message } from '@arco-design/web-vue'
import { useRoute } from 'vue-router'
import useUserStore from '@/store/modules/user'
import usePermissionStore from '@/store/modules/permission'
import type { ModalDialogType } from '@/types/components'
import ModalDialog from '@/components/overlays/ModalDialog.vue'
import { putSystemTasks } from '@/api/system/tasks'
import { assertFineTuningSaved, fineTuningPatch, readFineTuning, readFineTuningTask, validateFineTuning, type FineTuningTask, type FineTuningOption } from '../fine-tuning'

const props = defineProps<{ userOptions: FineTuningOption[]; retentionOptions: FineTuningOption[]; platformLimit: number }>()
const emit = defineEmits<{ (event: 'saved'): void }>()
const fieldNames = { value: 'key', label: 'title' }
const dialog = ref<Pick<ModalDialogType, 'show' | 'close' | 'setConfirmLoading'> | null>(null)
const task = ref<FineTuningTask | null>(null), saving = ref(false), saveError = ref('')
const form = reactive(readFineTuning({}))
let original = readFineTuning({})
const route = useRoute(), user = useUserStore(), permission = usePermissionStore(), pagePath = route.path
let editorVersion = 0, active = true, disposed = false
const identity = () => JSON.stringify([route.path, route.fullPath, user.userId, user.roleId, user.token, user.selected_environment, permission.permissionKeys])
const available = () => active && !disposed && route.path === pagePath && document.visibilityState === 'visible'
const supportsApi = computed(() => !task.value?.case_types?.length || task.value.case_types.includes(1))
const availableUsers = computed(() => {
  const owner = form.case_people
  const options = props.userOptions.map(option => ({ ...option, key: owner !== null && String(option.key) === String(owner) ? owner : option.key }))
  if (owner !== null && !options.some(option => String(option.key) === String(owner))) options.unshift({ key: owner, title: (String(owner) === String(original.case_people) ? task.value?.owner_name : '') || `用户 ID ${owner}` })
  return options
})
function close() {
  editorVersion++; task.value = null; saveError.value = ''
  original = readFineTuning({}); Object.assign(form, readFineTuning({}))
  void dialog.value?.close()
}
function open(record: unknown) {
  if (!available() || saving.value) return
  close()
  try {
    task.value = readFineTuningTask(record)
    original = readFineTuning(record)
    Object.assign(form, readFineTuning(record))
    void dialog.value?.show()
  } catch { close(); Message.error('任务数据格式异常，请刷新后重试') }
}
async function save() {
  if (!available() || saving.value || !task.value) return
  const version = editorVersion, key = identity(), target = { ...task.value }
  const current = () => available() && version === editorVersion && key === identity()
  saveError.value = ''
  try {
    const patch = fineTuningPatch(original, form)
    const error = validateFineTuning(readFineTuning(form), props.platformLimit, supportsApi.value && patch.api_concurrency_limit !== undefined)
    if (error) { saveError.value = error; return }
    if (!Object.keys(patch).length) { close(); return }
    saving.value = true
    const response = await putSystemTasks({ id: target.id, ...patch })
    assertFineTuningSaved(response)
    if (key === identity() && available()) emit('saved')
    if (current()) { close(); Message.success('精细化配置已保存，下次执行生效') }
  } catch {
    if (current()) saveError.value = '精细化配置保存失败，请重试'
  } finally { saving.value = false; if (version === editorVersion) dialog.value?.setConfirmLoading(false) }
}
function visibilityChanged() { if (document.visibilityState !== 'visible') close() }
watch(identity, close, { flush: 'sync' })
onMounted(() => document.addEventListener('visibilitychange', visibilityChanged))
onActivated(() => { active = true })
onDeactivated(() => { active = false; close() })
onBeforeUnmount(() => { disposed = true; close(); document.removeEventListener('visibilitychange', visibilityChanged) })
defineExpose({ open, close })
</script>

<style scoped>
.mango-task-fine-summary { display: flex; flex-direction: column; gap: 6px; margin-bottom: 16px; }
.mango-task-fine-summary strong { color: var(--m-text); overflow-wrap: anywhere; }
.mango-task-fine-summary span { color: var(--m-muted); font-size: 12px; }
.mango-task-fine-form { width: 100%; }
</style>
