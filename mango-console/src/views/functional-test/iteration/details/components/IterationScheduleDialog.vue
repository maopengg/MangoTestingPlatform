<template>
  <a-modal
    modal-class="mango-simple-form-modal"
    v-model:visible="visible"
    title="编辑需求排期"
    :width="560"
    :ok-loading="saving"
    :on-before-ok="save"
    :on-before-cancel="canCancel"
    @cancel="reset"
  >
    <a-alert class="mango-iteration-schedule__notice">{{ subjectLabel }}</a-alert>
    
    
    <MangoRequestFeedback v-if="saveError" :message="&quot;排期保存失败，输入已保留，请重试。&quot;" />
    <a-form class="mango-simple-form" :model="form" layout="horizontal" :disabled="saving" auto-label-width>
      <a-grid class="mango-simple-form-fields" :cols="2" :col-gap="16">
        <a-grid-item class="mango-simple-form-fields"
          ><a-form-item class="mango-simple-form-item" label="开发负责人"
            ><a-select
              v-model="form.development_owner"
              :options="ownerOptions"
              :loading="usersLoading"
              :field-names="fieldNames"
              allow-search
              allow-clear /></a-form-item
        ></a-grid-item>
        <a-grid-item class="mango-simple-form-fields"
          ><a-form-item class="mango-simple-form-item" label="优先级"
            ><a-select
              v-model="form.priority"
              :options="priorityOptions"
              :loading="enumsLoading"
              :field-names="fieldNames" /></a-form-item
        ></a-grid-item>
        <a-grid-item class="mango-simple-form-fields"
          ><a-form-item class="mango-simple-form-item" label="计划开始"
            ><a-date-picker
              v-model="form.planned_start_date"
              value-format="YYYY-MM-DD" /></a-form-item
        ></a-grid-item>
        <a-grid-item class="mango-simple-form-fields"
          ><a-form-item class="mango-simple-form-item" label="计划提测"
            ><a-date-picker
              v-model="form.planned_submit_date"
              value-format="YYYY-MM-DD" /></a-form-item
        ></a-grid-item>
        <a-grid-item class="mango-simple-form-fields"
          ><a-form-item class="mango-simple-form-item" label="交付状态"
            ><a-select
              v-model="form.status"
              :options="statusOptions"
              :loading="enumsLoading"
              :field-names="fieldNames" /></a-form-item
        ></a-grid-item>
      </a-grid>
    </a-form>
  </a-modal>
</template>

<script setup lang="ts">
import { requestFailureMessage } from '@/utils/load-error'

  import { computed, onActivated, onBeforeUnmount, onDeactivated, reactive, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { putManualSuite } from '@/api/functional-test'
  import { createIterationScheduleForm, iterationSchedulePayload } from '../form'
  import type {
    IterationScheduleForm,
    IterationScheduleSubject,
    IterationUserOption,
  } from '../types'

  const props = defineProps<{
    contextKey: string
    iterationId: number
    users: IterationUserOption[]
    priorityOptions: IterationUserOption[]
    statusOptions: IterationUserOption[]
    usersLoading?: boolean
    usersError?: boolean
    enumsLoading?: boolean
    enumsError?: boolean
  }>()
  const emit = defineEmits<{
    (event: 'saved', id: number): void
    (event: 'retry-users'): void
    (event: 'retry-enums'): void
  }>()
  const fieldNames = { value: 'key', label: 'title' }
  const visible = ref(false),
    saving = ref(false),
    saveError = ref(false)
  const subject = ref<{
    id: number
    iterationId: number
    ownerName: string
    ownerId: number | null
  } | null>(null)
  const subjectLabel = ref('')
  const form: IterationScheduleForm = reactive(createIterationScheduleForm())
  const ownerOptions = computed(() => {
    const selected = subject.value
    if (
      !selected ||
      selected.ownerId === null ||
      !selected.ownerName ||
      props.users.some((item) => Number(item.key) === selected.ownerId)
    )
      return props.users
    return [...props.users, { key: selected.ownerId, title: selected.ownerName }]
  })
  let active = true,
    generation = 0
  const savingId = ref<number | null>(null)
  const isSaving = (id: number) => saving.value && savingId.value === id
  const current = (version: number) => active && visible.value && generation === version
  const canCancel = () => !saving.value
  function reset() {
    ++generation
    visible.value = false
    subject.value = null
    subjectLabel.value = ''
    saveError.value = false
    Object.assign(form, createIterationScheduleForm())
  }
  function open(record: IterationScheduleSubject) {
    if (
      !active ||
      saving.value ||
      !Number.isSafeInteger(props.iterationId) ||
      props.iterationId <= 0
    )
      return
    const id = record.suite_id ?? record.id
    if (!Number.isSafeInteger(id) || id <= 0) return
    reset()
    Object.assign(form, createIterationScheduleForm(record))
    subject.value = {
      id,
      iterationId: props.iterationId,
      ownerId: form.development_owner,
      ownerName:
        typeof record.development_owner === 'object' ? record.development_owner?.name ?? '' : '',
    }
    subjectLabel.value = `${
      record.requirement_name || record.requirement?.name || '未命名需求'
    } · V${record.version_no ?? '-'}`
    visible.value = true
  }
  async function save() {
    if (!active || !visible.value || !subject.value || saving.value) return false
    const version = generation,
      id = subject.value.id
    const payload = iterationSchedulePayload(id, subject.value.iterationId, form)
    saving.value = true
    savingId.value = id
    saveError.value = false
    try {
      const data: unknown = (await putManualSuite(payload)).data
      if (!current(version)) return false
      if (
        !data ||
        typeof data !== 'object' ||
        Array.isArray(data) ||
        Reflect.get(data, 'id') !== id
      )
        throw Error('保存结果未确认')
      reset()
      Message.success('排期已保存')
      emit('saved', id)
    } catch (requestFailure) {
      if (current(version)) saveError.value = requestFailureMessage(requestFailure, true, "排期保存失败，输入已保留，请重试。")
    } finally {
      saving.value = false
      savingId.value = null
    }
    return false
  }
  watch(() => [props.contextKey, props.iterationId], reset, { flush: 'sync' })
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
  .mango-iteration-schedule__notice {
    margin-bottom: var(--m-page-gap);
  }
</style>
