<template>
  <a-modal
    modal-class="mango-simple-form-modal"
    :visible="visible"
    :title="mode === 'version' ? '新建需求版本' : mode === 'edit' ? '编辑需求' : '新增需求'"
    :width="560"
    :ok-loading="saving"
    :on-before-ok="save"
    :on-before-cancel="canCancel"
    :mask-closable="!saving"
    :esc-to-close="!saving"
    @update:visible="onVisibleChange"
  >
    <a-alert v-if="saveError" type="error" class="mango-suite-editor__notice"
      >保存失败，输入已保留，请重试。</a-alert
    >
    
    
    <a-form auto-label-width class="mango-simple-form" :model="form" layout="horizontal" :disabled="saving">
      <a-grid class="mango-simple-form-fields" :cols="2" :col-gap="16">
        <a-grid-item class="mango-simple-form-fields" :span="2"
          ><a-form-item class="mango-simple-form-item" label="需求名称" required
            ><a-input v-model="form.requirement_name" /></a-form-item
        ></a-grid-item>
        <a-grid-item class="mango-simple-form-fields"
          ><a-form-item class="mango-simple-form-item" label="项目产品" required
            ><ProjectProductSelect
              v-model="form.project_product"
              :disabled="saving"
              @change="onProductChange" /></a-form-item
        ></a-grid-item>
        <a-grid-item class="mango-simple-form-fields"
          ><a-form-item class="mango-simple-form-item" label="模块名称" required
            ><ProductModuleSelect
              v-model="form.module"
              :project-product-id="form.project_product"
              :auto-clear="false"
              :disabled="saving" /></a-form-item
        ></a-grid-item>
        <a-grid-item class="mango-simple-form-fields"
          ><a-form-item class="mango-simple-form-item" label="所属 Sprint" required
            ><a-select
              v-model="form.iteration_ref"
              :options="sprintOptions"
              allow-search
              :loading="iterationLoading"
              placeholder="请选择 Sprint" /></a-form-item
        ></a-grid-item>
        <a-grid-item class="mango-simple-form-fields"
          ><a-form-item class="mango-simple-form-item" label="优先级"
            ><a-select
              v-model="form.priority"
              :options="priorityOptions"
              :field-names="fieldNames" /></a-form-item
        ></a-grid-item>
        <a-grid-item class="mango-simple-form-fields"
          ><a-form-item class="mango-simple-form-item" label="开发负责人"
            ><a-select
              v-model="form.development_owner"
              :options="userOptions"
              :field-names="fieldNames"
              allow-search
              allow-clear /></a-form-item
        ></a-grid-item>
        <a-grid-item class="mango-simple-form-fields"
          ><a-form-item class="mango-simple-form-item" label="测试负责人" required
            ><a-select
              v-model="form.owner"
              :options="userOptions"
              :field-names="fieldNames"
              allow-search
              placeholder="请选择测试负责人" /></a-form-item
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
              :field-names="fieldNames" /></a-form-item
        ></a-grid-item>
      </a-grid>
    </a-form>
  </a-modal>
</template>
<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { computed, onActivated, onBeforeUnmount, onDeactivated, reactive, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import { getFunctionalIterations, postManualSuite, putManualSuite } from '@/api/functional-test'
  import {
    createSuiteEditorForm,
    suiteSelectionId,
    suiteEditorPayload,
    suiteEditorValidation,
  } from '../editor-form'
  import type {
    SuiteEditorDefaults,
    SuiteEditorMode,
    SuiteEditorForm,
    SuiteEditRecord,
    SuiteProductSelection,
  } from '../editor-form'
  const props = defineProps<{
    contextKey: string
    blocked: boolean
    users: Array<{ key: number | string; title: string }>
    usersLoading: boolean
    usersError: boolean
    priorityOptions: Array<{ key: number | string; title: string }>
    statusOptions: Array<{ key: number | string; title: string }>
  }>()
  const emit = defineEmits<{
    (event: 'saved', id: number): void
    (event: 'busy', value: boolean): void
    (event: 'visible', value: boolean): void
    (event: 'retry-users'): void
  }>()
  const fieldNames = { value: 'key', label: 'title' }
  const visible = ref(false),
    saving = ref(false),
    saveError = ref(false)
  const mode = ref<SuiteEditorMode>('create')
  const form: SuiteEditorForm = reactive(createSuiteEditorForm('create'))
  const iterationOptions = ref<Array<{ value: number; label: string }>>([])
  const iterationLoading = ref(false),
    iterationError = ref(false)
  const original = ref<SuiteEditRecord | null>(null)
  let active = true,
    generation = 0,
    iterationSequence = 0,
    previousProduct: number | null = null
  const current = (version: number) => active && visible.value && generation === version
  const canCancel = () => !saving.value
  const userOptions = computed(() => {
    const options = [...props.users]
    for (const relation of [original.value?.owner, original.value?.development_owner]) {
      const id = suiteSelectionId(relation)
      if (id !== null && !options.some((option) => String(option.key) === String(id))) {
        const label =
          relation && typeof relation === 'object' ? relation.name || relation.username : ''
        options.push({ key: id, title: label || `ID ${id}` })
      }
    }
    return options
  })
  const sprintOptions = computed(() => {
    const id = suiteSelectionId(form.iteration_ref)
    return id !== null && !iterationOptions.value.some((option) => option.value === id)
      ? [
          ...iterationOptions.value,
          {
            value: id,
            label:
              original.value?.iteration_ref && typeof original.value.iteration_ref === 'object'
                ? original.value.iteration_ref.name || `ID ${id}`
                : `ID ${id}`,
          },
        ]
      : iterationOptions.value
  })
  function reset() {
    ++generation
    ++iterationSequence
    visible.value = false
    saveError.value = false
    iterationOptions.value = []
    iterationLoading.value = false
    iterationError.value = false
    original.value = null
    previousProduct = null
    Object.assign(form, createSuiteEditorForm('create'))
  }
  function onVisibleChange(value: boolean) {
    if (!value && canCancel()) reset()
  }
  function open(
    nextMode: SuiteEditorMode,
    record?: SuiteEditRecord,
    defaults?: SuiteEditorDefaults
  ) {
    if (!active || saving.value || props.blocked) return
    if (nextMode !== 'create' && (!record || !suiteSelectionId(record.id))) return
    if (nextMode === 'version' && !suiteSelectionId(record?.requirement)) {
      Message.error('需求来源不完整，请刷新后重试')
      return
    }
    reset()
    mode.value = nextMode
    // Copy the small finite source so edits to a row cannot change this window's write target.
    original.value = record
      ? {
          id: record.id,
          requirement: suiteSelectionId(record.requirement),
          owner:
            typeof record.owner === 'object' && record.owner ? { ...record.owner } : record.owner,
          development_owner:
            typeof record.development_owner === 'object' && record.development_owner
              ? { ...record.development_owner }
              : record.development_owner,
          iteration_ref:
            typeof record.iteration_ref === 'object' && record.iteration_ref
              ? { ...record.iteration_ref }
              : record.iteration_ref,
        }
      : null
    Object.assign(form, createSuiteEditorForm(nextMode, record, defaults))
    previousProduct = suiteSelectionId(form.project_product)
    visible.value = true
    void loadIterations()
  }
  async function loadIterations() {
    if (!current(generation) || saving.value) return
    const productId = suiteSelectionId(form.project_product),
      version = generation,
      sequence = ++iterationSequence
    iterationOptions.value = []
    iterationError.value = false
    if (productId === null) {
      iterationLoading.value = false
      return
    }
    iterationLoading.value = true
    try {
      const response = await getFunctionalIterations({
        project_product: productId,
        page: 1,
        pageSize: 500,
      })
      if (
        !current(version) ||
        sequence !== iterationSequence ||
        suiteSelectionId(form.project_product) !== productId
      )
        return
      if (!Array.isArray(response.data)) throw Error('Invalid Sprint response')
      const options: Array<{ value: number; label: string }> = []
      for (const item of response.data as unknown[]) {
        if (!item || typeof item !== 'object' || Array.isArray(item)) throw Error('Invalid Sprint')
        const row = item as Record<string, unknown>,
          id = suiteSelectionId(
            typeof row.id === 'number' || typeof row.id === 'string' ? row.id : null
          )
        if (!id || typeof row.name !== 'string') throw Error('Invalid Sprint')
        options.push({
          value: id,
          label: `${typeof row.iteration_no === 'string' ? row.iteration_no : ''} ${
            row.name
          }`.trim(),
        })
      }
      iterationOptions.value = options
    } catch (loadFailure0) {
      if (current(version) && sequence === iterationSequence) (reportLoadError(loadFailure0, "加载失败，请重试", false), iterationError.value = true)
    } finally {
      if (current(version) && sequence === iterationSequence) iterationLoading.value = false
    }
  }
  function onProductChange(value: SuiteProductSelection) {
    const id = suiteSelectionId(value)
    if (id === previousProduct) return
    previousProduct = id
    form.module = null
    form.iteration_ref = null
    void loadIterations()
  }
  async function save() {
    if (!current(generation) || saving.value || props.blocked) return false
    const message = suiteEditorValidation(form)
    if (message) {
      Message.error(message)
      return false
    }
    const version = generation,
      payload = suiteEditorPayload(form, mode.value, original.value)
    saving.value = true
    emit('busy', true)
    saveError.value = false
    try {
      const response = await (mode.value === 'edit'
        ? putManualSuite(payload)
        : postManualSuite(payload))
      if (!current(version)) return false
      const result: unknown = response.data
      if (!result || typeof result !== 'object' || Array.isArray(result))
        throw Error('Invalid saved suite')
      const row = result as Record<string, unknown>
      const id = suiteSelectionId(
        typeof row.id === 'number' || typeof row.id === 'string' ? row.id : null
      )
      if (
        !id ||
        ('id' in payload && payload.id !== id) ||
        row.project_product !== payload.project_product
      )
        throw Error('Invalid saved suite')
      reset()
      Message.success('保存成功')
      emit('saved', id)
    } catch {
      if (current(version)) saveError.value = true
    } finally {
      saving.value = false
      emit('busy', false)
    }
    return false
  }
  watch(() => props.contextKey, reset, { flush: 'sync' })
  watch(visible, (value) => emit('visible', value), { flush: 'sync' })
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
  .mango-suite-editor__notice {
    margin-bottom: var(--m-page-gap);
  }
</style>
