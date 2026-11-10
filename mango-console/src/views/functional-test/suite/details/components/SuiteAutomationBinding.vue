<template>
  <a-modal
    modal-class="mango-simple-form-modal"
    :visible="visible"
    title="手动绑定自动化用例"
    :width="560"
    :ok-loading="saving"
    :on-before-ok="save"
    :on-before-cancel="canCancel"
    :mask-closable="!saving"
    :esc-to-close="!saving"
    @update:visible="onVisibleChange"
  >
    <a-alert v-if="saveError" type="error" class="mango-suite-binding__error"
      >绑定失败，输入已保留，请重试。</a-alert
    >
    <a-form auto-label-width class="mango-simple-form" :model="form" layout="horizontal" :disabled="saving">
      <a-form-item class="mango-simple-form-item" label="自动化类型"
        ><a-select v-model="form.automation_type" :options="typeOptions" :field-names="fieldNames"
      /></a-form-item>
      <a-form-item class="mango-simple-form-item" label="自动化用例 ID" required
        ><a-input-number v-model="form.automation_case_id" :min="1" :precision="0"
      /></a-form-item>
    </a-form>
  </a-modal>
</template>
<script setup lang="ts">
  import { onActivated, onBeforeUnmount, onDeactivated, reactive, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { postManualAutomationBind } from '@/api/functional-test'
  import { relationId } from '../case-form'
  import type { SuiteCaseRecord } from '../case-form'
  import { resourceId, objectValue } from '../resource-form'
  const props = defineProps<{
    suiteId: number | null
    contextKey: string
    available: boolean
    blocked: boolean
    typeOptions: Array<{ key: number | string; title: string }>
  }>()
  const emit = defineEmits<{
    (event: 'changed', suiteId: number): void
    (event: 'busy', value: boolean): void
  }>()
  const fieldNames = { value: 'key', label: 'title' }
  const visible = ref(false),
    saving = ref(false),
    saveError = ref(false)
  const form = reactive<{ automation_type: number; automation_case_id: number | null }>({
    automation_type: 1,
    automation_case_id: null,
  })
  let subject: { id: number; suiteId: number; contextKey: string } | null = null
  let active = true,
    generation = 0
  const current = (version: number) =>
    active &&
    visible.value &&
    props.available &&
    generation === version &&
    subject?.suiteId === props.suiteId &&
    subject?.contextKey === props.contextKey
  const canCancel = () => !saving.value
  function reset() {
    ++generation
    visible.value = false
    saveError.value = false
    subject = null
    form.automation_type = 1
    form.automation_case_id = null
  }
  function onVisibleChange(value: boolean) {
    if (!value && canCancel()) reset()
  }
  function open(record: SuiteCaseRecord, type: number) {
    if (
      !active ||
      saving.value ||
      props.blocked ||
      !props.available ||
      !resourceId(props.suiteId) ||
      !resourceId(record.id) ||
      relationId(record.suite) !== props.suiteId ||
      ![0, 1].includes(type)
    )
      return
    reset()
    subject = { id: record.id, suiteId: props.suiteId!, contextKey: props.contextKey }
    form.automation_type = type
    visible.value = true
  }
  async function save() {
    if (saving.value || props.blocked || !subject || !current(generation)) return false
    if (![0, 1].includes(form.automation_type) || !resourceId(form.automation_case_id)) {
      Message.error('请选择自动化类型并填写正整数用例 ID')
      return false
    }
    const version = generation,
      target = { ...subject }
    const payload = {
      case_id: target.id,
      automation_type: form.automation_type,
      automation_case_id: form.automation_case_id,
    }
    saving.value = true
    emit('busy', true)
    saveError.value = false
    try {
      const response = await postManualAutomationBind(payload)
      if (!current(version)) return false
      const result = objectValue(response.data)
      if (
        !resourceId(result.id) ||
        resourceId(result.manual_case) !== target.id ||
        Number(result.automation_type) !== payload.automation_type ||
        resourceId(result.automation_case_id) !== payload.automation_case_id
      )
        throw new Error('Invalid binding response')
      reset()
      Message.success('绑定成功')
      emit('changed', target.suiteId)
    } catch {
      if (current(version)) saveError.value = true
    } finally {
      saving.value = false
      emit('busy', false)
    }
    return false
  }
  watch(() => [props.contextKey, props.suiteId, props.available], reset, { flush: 'sync' })
  onDeactivated(() => {
    active = false
    reset()
  })
  onActivated(() => {
    active = true
  })
  onBeforeUnmount(() => {
    active = false
    reset()
  })
  defineExpose({ open })
</script>
<style scoped>
  .mango-suite-binding__error {
    margin-bottom: var(--m-page-gap);
  }
</style>
