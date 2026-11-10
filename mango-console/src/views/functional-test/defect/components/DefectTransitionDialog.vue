<template>
  <a-modal
    modal-class="mango-simple-form-modal"
    v-model:visible="visible"
    title="流转缺陷"
    :width="560"
    :ok-loading="saving"
    :on-before-ok="save"
    :on-before-cancel="canCancel"
    @cancel="reset"
  >
    
    
    <a-alert v-if="saveError" type="error" class="mango-defect-transition__error"
      >流转失败，输入已保留，请重试。</a-alert
    >
    <a-form auto-label-width class="mango-simple-form" :model="form" layout="horizontal" :disabled="saving">
      <a-form-item class="mango-simple-form-item" label="目标状态" required
        ><a-select v-model="form.status" :loading="enumsLoading" :options="transitionOptions"
      /></a-form-item>
      <a-form-item class="mango-simple-form-item" v-if="form.status === 2" label="经办人" required
        ><a-select
          v-model="form.assignee"
          :options="users"
          :loading="usersLoading"
          :field-names="fieldNames"
          allow-search
      /></a-form-item>
      <template v-if="form.status === 3 || form.status === 4">
        <a-form-item class="mango-simple-form-item" label="解决方式" required
          ><a-select
            v-model="form.resolution"
            :loading="enumsLoading"
            :options="resolutionOptions"
            :field-names="fieldNames"
        /></a-form-item>
        <a-form-item class="mango-simple-form-item" label="解决说明"><a-textarea v-model="form.resolution_note" /></a-form-item>
      </template>
    </a-form>
  </a-modal>
</template>

<script setup lang="ts">
  import { computed, onActivated, onBeforeUnmount, onDeactivated, reactive, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { useEnum } from '@/store/modules/get-enum'
  import { transitionFunctionalDefect } from '@/api/functional-test'
  import { defectStatusTransitions } from '../config'
  import type {
    DefectActionSubject,
    DefectMutationResult,
    DefectTransitionForm,
    DefectTransitionSubject,
    DefectUserOption,
  } from '../types'

  const props = defineProps<{
    users: DefectUserOption[]
    contextKey: string
    usersLoading?: boolean
    usersError?: boolean
    enumsLoading?: boolean
    enumsError?: boolean
  }>()
  const emit = defineEmits<{
    (event: 'saved', record: DefectMutationResult): void
    (event: 'retry-users'): void
    (event: 'retry-enums'): void
  }>()
  const enumStore = useEnum()
  const fieldNames = { value: 'key', label: 'title' }
  const visible = ref(false),
    saving = ref(false),
    saveError = ref(false)
  const subject = ref<DefectTransitionSubject | null>(null)
  const form: DefectTransitionForm = reactive({
    status: null,
    assignee: null,
    resolution: null,
    resolution_note: '',
  })
  const resolutionOptions = computed(() => enumStore.functional_test_defect_resolution ?? [])
  const transitionOptions = computed(() =>
    (subject.value ? defectStatusTransitions[subject.value.currentStatus] ?? [] : []).map(
      (value) => ({
        value,
        label:
          enumStore.functional_test_defect_status?.find((item) => item.key === value)?.title ?? '-',
      })
    )
  )
  let active = true,
    generation = 0
  const current = (version: number) => active && visible.value && version === generation
  const savingId = ref<number | null>(null)
  const isSaving = (id: number) => saving.value && savingId.value === id
  const canCancel = () => !saving.value
  function reset() {
    ++generation
    visible.value = false
    subject.value = null
    saveError.value = false
    Object.assign(form, { status: null, assignee: null, resolution: null, resolution_note: '' })
  }
  function open(record: DefectActionSubject, target?: number) {
    if (!active || saving.value) return
    reset()
    subject.value = {
      id: record.id,
      currentStatus: record.status,
      assignee: record.assignee?.id ?? null,
      resolution: record.resolution ?? null,
      resolution_note: record.resolution_note ?? '',
    }
    Object.assign(form, {
      status: target ?? null,
      assignee: subject.value.assignee,
      resolution: subject.value.resolution,
      resolution_note: subject.value.resolution_note,
    })
    visible.value = true
  }
  async function save() {
    if (!active || !visible.value || !subject.value || saving.value) return false
    if (
      form.status === null ||
      !transitionOptions.value.some((option) => option.value === form.status)
    ) {
      Message.warning('请选择目标状态')
      return false
    }
    if (
      (form.status === 2 && form.assignee === null) ||
      ((form.status === 3 || form.status === 4) && form.resolution === null)
    ) {
      Message.warning('请填写必填字段')
      return false
    }
    const version = generation,
      id = subject.value.id
    const payload = {
      id,
      status: form.status,
      assignee: form.assignee,
      resolution: form.resolution,
      resolution_note: form.resolution_note,
    }
    savingId.value = id
    saving.value = true
    saveError.value = false
    try {
      const data: unknown = (await transitionFunctionalDefect(payload)).data
      if (!current(version)) return false
      if (
        !data ||
        typeof data !== 'object' ||
        Array.isArray(data) ||
        Reflect.get(data, 'id') !== id
      )
        throw Error('流转结果未确认')
      reset()
      Message.success('状态已更新')
      emit('saved', { ...data, id })
    } catch {
      if (current(version)) saveError.value = true
    } finally {
      saving.value = false
      savingId.value = null
    }
    return false
  }
  watch(() => props.contextKey, reset, { flush: 'sync' })
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
  defineExpose({ open, isSaving })
</script>

<style scoped>
  .mango-defect-transition__error {
    margin-bottom: var(--m-page-gap);
  }
</style>
