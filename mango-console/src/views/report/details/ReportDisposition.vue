<template>
  <slot :open="open" :eligible="eligible" />
  <a-modal modal-class="mango-simple-form-modal" v-model:visible="visible" title="排查与排除" :width="560" :mask-closable="false"
    :closable="!saving" :cancel-button-props="{ disabled: saving }" :ok-loading="saving"
    ok-text="保存" @before-ok="save">
    <a-alert v-if="errorText" type="error">{{ errorText }}</a-alert>
    <a-descriptions :column="1" size="small">
      <a-descriptions-item label="执行项">{{ snapshot?.name || snapshot?.id || '-' }}</a-descriptions-item>
      <a-descriptions-item label="影响范围">整条执行项，共 {{ snapshot?.case_sum ?? 1 }} 个用例；原始结果保留</a-descriptions-item>
    </a-descriptions>
    <a-form auto-label-width :model="form" layout="horizontal" class="mango-disposition-form mango-simple-form">
      <a-form-item class="mango-simple-form-item" label="排除统计"><a-switch v-model="form.is_excluded" size="small" :disabled="saving" /></a-form-item>
      <a-form-item class="mango-simple-form-item" label="原因分类" :required="form.is_excluded">
        <a-select v-model="form.failure_reason" :options="reasonOptions" :disabled="saving" allow-clear placeholder="请选择失败原因" />
      </a-form-item>
      <a-form-item class="mango-simple-form-item" label="排查说明" :required="form.is_excluded">
        <a-textarea v-model="form.failure_description" :disabled="saving" :max-length="1000" show-word-limit placeholder="填写排查结论；也可不排除，仅保存原因和说明" />
      </a-form-item>
    </a-form>
  </a-modal>
</template>

<script setup lang="ts">
  import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, reactive, ref, watch } from 'vue'
  import { useRoute } from 'vue-router'
  import { Message } from '@arco-design/web-vue'
  import { useEnum } from '@/store/modules/get-enum'
  import { useUserStoreContext } from '@/store/modules/user'
  import { reportPayload } from './report-overview'
  import { useReportDispositionWrite } from './composables/useReportDispositionWrite'
  import { dispositionDraft, dispositionPayload, emptyDispositionDraft, reportDispositionRecord, type ReportDispositionDraft, type ReportDispositionRecord } from './report-disposition'

  import { updateReportDisposition } from '@/api/system/test_sute_details'

  const props = defineProps<{ record: unknown; editable?: boolean }>()
  const emit = defineEmits<{ (event: 'saved'): void }>()
  const enumStore = useEnum(), userStore = useUserStoreContext(), route = useRoute()

  const visible = ref(false)
  const writePending = ref(false)
  const errorText = ref('')
  const snapshot = ref<ReportDispositionRecord | null>(null)
  const record = computed(() => reportDispositionRecord(props.record))
  const writes = useReportDispositionWrite()
  const saving = computed(() => writePending.value || (record.value?.id != null && writes.busyIds.has(record.value.id)))
  const eligible = computed(() => Boolean(props.editable && record.value?.id !== null && record.value && (
    record.value.status === 0 || record.value.fail > 0 || record.value.is_excluded || record.value.failure_reason || record.value.failure_description
  )))
  const form: ReportDispositionDraft = reactive(emptyDispositionDraft())
  const reasonOptions = computed(() => enumStore.report_failure_reason.map(item => ({ value: item.key, label: item.title })))
  let version = 0, active = true, disposed = false
  const available = () => !disposed && active && document.visibilityState === 'visible'

  function close() {
    version += 1
    snapshot.value = null
    visible.value = false
    errorText.value = ''
    Object.assign(form, emptyDispositionDraft())
  }

  function open() {
    if (saving.value || !available() || !eligible.value || !record.value) return
    version += 1
    snapshot.value = { ...record.value }
    Object.assign(form, dispositionDraft(record.value))
    errorText.value = ''
    visible.value = true
  }
  async function save() {
    const target = snapshot.value
    if (saving.value || !visible.value || !available() || !eligible.value || !target || target.id === null) return false
    // 分类与说明独立保存；手工提交排除时由界面要求补全结论。
    if (form.is_excluded && (!form.failure_reason || !form.failure_description.trim())) {
      Message.warning('排除统计时，请填写原因分类和排查说明')
      return false
    }
    const payload = dispositionPayload(form), currentVersion = version
    const current = () => available() && visible.value && version === currentVersion && snapshot.value?.id === target.id
    const release = writes.acquire(target.id)
    if (!release) return false
    writePending.value = true
    errorText.value = ''
    try {
      reportPayload(await updateReportDisposition(target.id, payload))
      if (!current()) return false
      Message.success('排查结论已保存')
      close()
      emit('saved')
      return true
    } catch {
      if (current()) errorText.value = '排查结论保存失败，请重试'
      return false
    } finally {
      writePending.value = false
      release()
    }
  }
  function visibilityChanged() { if (document.visibilityState !== 'visible') close() }
  watch(() => visible.value, value => { if (!value && snapshot.value) close() }, { flush: 'sync' })
  watch([() => record.value?.id, () => props.editable, () => route.fullPath,
    () => userStore.userId, () => userStore.roleId, () => userStore.token, () => userStore.selected_environment,
  ], close, { flush: 'sync' })
  onMounted(() => document.addEventListener('visibilitychange', visibilityChanged))
  onDeactivated(() => { active = false; close() })
  onActivated(() => { active = true })
  onBeforeUnmount(() => { disposed = true; active = false; close(); document.removeEventListener('visibilitychange', visibilityChanged) })
</script>

<style scoped>
  .mango-disposition-form { margin-top: var(--m-space-md); }
</style>
