<template>
  <ModalDialog ref="dialog" title="编辑任务精细化配置" :width="560" confirm-text="保存" @confirm="save">
    <template #content>
      <div class="mango-task-fine-summary">
        <strong>{{ task?.name }}</strong>
        <span>任务组：{{ task?.task_group_name || '—' }}。以下配置独立保存，任务组同步不会覆盖。</span>
      </div>
      <a-form :model="form" layout="horizontal" class="mango-task-fine-form">
        <a-form-item label="API 并发">
          <a-input-number v-model="form.api_concurrency_limit" :min="1" allow-clear
            :disabled="saving || !supportsApi" placeholder="留空使用平台默认并发" />
          <template #extra>{{ supportsApi ? `每份报告的上限；当前平台容量 ${platformLimit}` : '当前类型不包含API，此配置暂不生效' }}</template>
        </a-form-item>
        <a-form-item label="负责人" required>
          <a-select v-model="form.case_people" :options="userOptions" :field-names="fieldNames" allow-search :disabled="saving" />
        </a-form-item>
        <a-form-item label="报告保留策略">
          <a-select v-model="form.report_retention_policy" :options="retentionOptions" :field-names="fieldNames" :disabled="saving" />
        </a-form-item>
      </a-form>
    </template>
  </ModalDialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import ModalDialog from '@/components/overlays/ModalDialog.vue'
import { putSystemTasks } from '@/api/system/tasks'
import { fineTuningPatch, readFineTuning } from '../fine-tuning'

defineProps<{ userOptions: any[]; retentionOptions: any[]; platformLimit: number }>()
const emit = defineEmits<{ (event: 'saved'): void }>()
const fieldNames = { value: 'key', label: 'title' }
const dialog = ref<InstanceType<typeof ModalDialog> | null>(null)
const task = ref<any>(null), saving = ref(false)
const form = reactive(readFineTuning({}))
let original = readFineTuning({})
const supportsApi = computed(() => !task.value?.case_types?.length || task.value.case_types.includes(1))
function open(record: any) {
  if (saving.value) return
  task.value = { ...record }
  original = readFineTuning(record)
  Object.assign(form, readFineTuning(record))
  dialog.value?.show()
}
async function save() {
  if (saving.value || !task.value) return
  try {
    if (!form.case_people) { Message.error('请选择负责人'); return }
    const patch = fineTuningPatch(original, form)
    if (!Object.keys(patch).length) { dialog.value?.close(); return }
    saving.value = true
    await putSystemTasks({ id: task.value.id, ...patch })
    dialog.value?.close()
    Message.success('精细化配置已保存，下次执行生效')
    emit('saved')
  } catch {
    // 公共请求层提示错误，保留当前编辑内容供重试。
  } finally { saving.value = false; dialog.value?.setConfirmLoading(false) }
}
defineExpose({ open })
</script>

<style scoped>
.mango-task-fine-summary { display: flex; flex-direction: column; gap: 6px; margin-bottom: 16px; }
.mango-task-fine-summary strong { color: var(--m-text); overflow-wrap: anywhere; }
.mango-task-fine-summary span { color: var(--m-muted); font-size: 12px; }
.mango-task-fine-form { width: 100%; }
</style>
