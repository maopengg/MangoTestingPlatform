<template>
  <a-modal
    modal-class="mango-simple-form-modal"
    v-model:visible="visible"
    :title="recordId === null ? '新建 Sprint' : '编辑 Sprint'"
    :width="560"
    :ok-loading="saving"
    :on-before-ok="save"
    :on-before-cancel="canCancel"
    @cancel="reset"
  >
    <MangoRequestFeedback v-if="saveError" :message="&quot;保存失败，输入已保留，请重试。&quot;" />
    
    
    <a-form class="mango-simple-form" :model="form" layout="horizontal" auto-label-width :disabled="saving">
      <a-grid class="mango-simple-form-fields" :cols="2" :col-gap="16">
        <a-grid-item class="mango-simple-form-fields"
          ><a-form-item class="mango-simple-form-item" label="Sprint 编号" required
            ><a-input v-model="form.iteration_no" :max-length="64" /></a-form-item
        ></a-grid-item>
        <a-grid-item class="mango-simple-form-fields"
          ><a-form-item class="mango-simple-form-item" label="Sprint 名称" required
            ><a-input v-model="form.name" :max-length="128" /></a-form-item
        ></a-grid-item>
        <a-grid-item class="mango-simple-form-fields"
          ><a-form-item class="mango-simple-form-item" label="项目产品" required
            ><ProjectProductSelect v-model="form.project_product" :disabled="saving" /></a-form-item
        ></a-grid-item>
        <a-grid-item class="mango-simple-form-fields"
          ><a-form-item class="mango-simple-form-item" label="负责人" required
            ><a-select
              v-model="form.owner"
              :options="ownerOptions"
              :field-names="fieldNames"
              :loading="usersLoading"
              allow-search /></a-form-item
        ></a-grid-item>
        <a-grid-item class="mango-simple-form-fields"
          ><a-form-item class="mango-simple-form-item" label="开始日期" required
            ><a-date-picker v-model="form.start_date" value-format="YYYY-MM-DD" /></a-form-item
        ></a-grid-item>
        <a-grid-item class="mango-simple-form-fields"
          ><a-form-item class="mango-simple-form-item" label="结束日期" required
            ><a-date-picker v-model="form.end_date" value-format="YYYY-MM-DD" /></a-form-item
        ></a-grid-item>
        <a-grid-item class="mango-simple-form-fields"
          ><a-form-item class="mango-simple-form-item" label="状态" required
            ><a-select
              v-model="form.status"
              :options="statusOptions"
              :field-names="fieldNames"
              :loading="enumsLoading" /></a-form-item
        ></a-grid-item>
        <a-grid-item class="mango-simple-form-fields" :span="2"
          ><a-form-item class="mango-simple-form-item" label="备注"
            ><a-textarea
              v-model="form.remark"
              :auto-size="{ minRows: 3, maxRows: 6 }" /></a-form-item
        ></a-grid-item>
      </a-grid>
    </a-form>
  </a-modal>
</template>
<script setup lang="ts">
import { requestFailureMessage } from '@/utils/load-error'

  import { computed, onActivated, onBeforeUnmount, onDeactivated, reactive, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import { postFunctionalIteration, putFunctionalIteration } from '@/api/functional-test'
  import { iterationObject, iterationRecordId } from '../presentation'
  import { createIterationForm, iterationSavePayload } from '../list-form'
  import type { IterationForm, IterationOption, IterationRow } from '../types'
  const props = defineProps<{
    contextKey: string
    users: IterationOption[]
    statusOptions: IterationOption[]
    busyIds?: number[]
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
  const recordId = ref<number | null>(null),
    savingId = ref<number | null>(null)
  const originalOwner = ref<IterationOption | null>(null)
  const form: IterationForm = reactive(createIterationForm())
  const ownerOptions = computed(() =>
    originalOwner.value &&
    !props.users.some((item) => String(item.key) === String(originalOwner.value?.key))
      ? [...props.users, originalOwner.value]
      : props.users
  )
  let active = true,
    generation = 0
  const current = (version: number) => active && visible.value && generation === version
  const canCancel = () => !saving.value
  const isSaving = (id: number) => saving.value && savingId.value === id
  function reset() {
    ++generation
    visible.value = false
    recordId.value = null
    originalOwner.value = null
    saveError.value = false
    Object.assign(form, createIterationForm())
  }
  function open(record: IterationRow | null, productId: number | null = null) {
    if (!active || saving.value) return
    reset()
    recordId.value = record?.id ?? null
    originalOwner.value = record?.owner ? { key: record.owner.id, title: record.owner.name } : null
    Object.assign(form, createIterationForm(record, productId))
    visible.value = true
  }
  async function save() {
    if (!active || !visible.value || saving.value) return false
    const version = generation,
      id = recordId.value,
      payload = iterationSavePayload(form, id)
    if (id !== null && props.busyIds?.includes(id)) {
      Message.warning('该 Sprint 正在删除确认或处理中，请稍后重试')
      return false
    }
    if (
      !payload.iteration_no ||
      !payload.name ||
      !payload.project_product ||
      !payload.owner ||
      !payload.start_date ||
      !payload.end_date ||
      payload.status === null ||
      !Number.isFinite(payload.status)
    ) {
      Message.warning('请填写必填字段')
      return false
    }
    saving.value = true
    savingId.value = id
    saveError.value = false
    try {
      const response = await (id === null
        ? postFunctionalIteration(payload)
        : putFunctionalIteration(payload))
      if (!current(version)) return false
      const savedId = iterationRecordId(iterationObject(response.data).id)
      if (id !== null && savedId !== id) throw Error('保存结果未确认')
      reset()
      Message.success('保存成功')
      emit('saved', savedId)
    } catch (requestFailure) {
      if (current(version)) saveError.value = requestFailureMessage(requestFailure, true, "保存失败，输入已保留，请重试。")
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
  .mango-iteration-editor__notice {
    margin-bottom: var(--m-page-gap);
  }
</style>
