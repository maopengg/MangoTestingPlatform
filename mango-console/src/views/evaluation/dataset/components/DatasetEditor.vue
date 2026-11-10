<template>
  <a-modal
    modal-class="mango-simple-form-modal"
    v-model:visible="visible"
    :title="form.id === null ? '新建评测数据集' : '编辑评测数据集'"
    :width="560"
    :mask-closable="!savingDataset"
    :esc-to-close="!savingDataset"
    :closable="!savingDataset"
    @keydown.enter="onEnter"
  >
    <a-form class="mango-simple-form"
      :model="form"
      layout="horizontal"
      auto-label-width
      :disabled="savingDataset"
      :inert="savingDataset"
    >
      <a-form-item class="mango-simple-form-item" label="数据集名称" required><a-input v-model="form.name" /></a-form-item>
      <a-form-item class="mango-simple-form-item" label="任务类型" required>
        <a-input-tag
          :model-value="form.task_type"
          :unique-value="true"
          placeholder="自由输入，如：记忆，问答；回车确认"
          @update:model-value="updateTaskTypes"
        />
      </a-form-item>
      <a-form-item class="mango-simple-form-item" v-if="form.id !== null" label="状态"
        ><a-select v-model="form.status" :options="datasetStatusOptions"
      /></a-form-item>
      <a-form-item class="mango-simple-form-item" label="说明"><a-textarea v-model="form.description" /></a-form-item>
    </a-form>
    <a-alert v-if="saveError" type="error">{{ saveError }}</a-alert>
    <template #footer>
      <a-space class="mango-modal-dialog-footer-actions">
        <a-button :disabled="savingDataset" @click="close">取消</a-button>
        <a-button type="primary" :loading="savingDataset" @click="saveDataset">提交</a-button>
      </a-space>
    </template>
  </a-modal>
</template>

<script setup lang="ts">
  import { computed, onBeforeUnmount, onDeactivated, reactive, ref, watch } from 'vue'
  import { createEvaluationDataset, updateEvaluationDataset } from '@/api/evaluation'
  import { useEvaluationEnums } from '../../components/useEvaluationEnums'
  import type { EvaluationDatasetRecord } from '../types'
  import { createDatasetForm, datasetPayload, normalizeLabels } from '../form'
  const props = defineProps<{ contextKey: number }>()
  const emit = defineEmits<{ (event: 'saved'): void }>()
  const { options } = useEvaluationEnums()
  const datasetStatusOptions = computed(() => options('evaluation_case_status'))
  const form = reactive(createDatasetForm())
  const visible = ref(false),
    savingDataset = ref(false),
    saveError = ref('')
  let generation = 0,
    savingId: number | null = null
  function close() {
    ++generation
    visible.value = false
    saveError.value = ''
    Object.assign(form, createDatasetForm())
  }
  function open(record?: EvaluationDatasetRecord) {
    if (savingDataset.value) return
    ++generation
    Object.assign(form, createDatasetForm(record))
    saveError.value = ''
    visible.value = true
  }
  function updateTaskTypes(value: unknown) {
    if (!savingDataset.value) form.task_type = normalizeLabels(value)
  }
  async function saveDataset() {
    if (savingDataset.value || !visible.value) return false
    const payload = datasetPayload(form)
    saveError.value = !payload.name
      ? '请填写数据集名称'
      : !payload.task_type.length
      ? '请至少输入一个任务类型'
      : ''
    if (saveError.value) return false
    const current = generation
    savingDataset.value = true
    savingId = form.id
    try {
      if (form.id !== null) await updateEvaluationDataset(payload)
      else await createEvaluationDataset(payload)
      if (current !== generation || !visible.value) return false
      visible.value = false
      emit('saved')
      return true
    } catch {
      if (current === generation && visible.value)
        saveError.value = '数据集保存失败，草稿已保留，请重试'
      return false
    } finally {
      savingDataset.value = false
      savingId = null
    }
  }
  function onEnter(event: KeyboardEvent) {
    const target = event.target as HTMLElement | null
    if (
      event.isComposing ||
      event.keyCode === 229 ||
      target?.tagName === 'TEXTAREA' ||
      target?.closest?.('.arco-input-tag')
    )
      return
    event.preventDefault()
    void saveDataset()
  }
  watch(
    visible,
    (value) => {
      if (!value) close()
    },
    { flush: 'sync' }
  )
  watch(() => props.contextKey, close, { flush: 'sync' })
  onDeactivated(close)
  onBeforeUnmount(close)
  function isSaving(id: number) {
    return savingDataset.value && savingId === id
  }
  defineExpose({ open, close, isSaving })
</script>
