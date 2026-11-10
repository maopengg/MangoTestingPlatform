<template>
  <a-modal
    modal-class="mango-simple-form-modal"
    v-model:visible="visible"
    :title="recordId === null ? '新建测试计划' : '编辑测试计划'"
    :width="560"
    :ok-loading="saving"
    :on-before-ok="save"
    :on-before-cancel="canCancel"
    @cancel="reset"
  >
    <a-alert v-if="saveError" type="error" class="mango-plan-editor__notice"
      >保存失败，草稿已保留，请重试。</a-alert
    >



    <a-form class="mango-simple-form" :model="form" layout="horizontal" auto-label-width :disabled="saving">
      <a-grid class="mango-simple-form-fields" :cols="2" :col-gap="scaleDensityPixels(16)">
        <a-grid-item class="mango-simple-form-fields" :span="2"
          ><a-form-item class="mango-simple-form-item" label="计划名称" required
            ><a-input v-model="form.name" :max-length="256" /></a-form-item
        ></a-grid-item>
        <a-grid-item class="mango-simple-form-fields"
          ><a-form-item class="mango-simple-form-item" label="项目产品" required
            ><ProjectProductSelect v-model="form.project_product" :disabled="saving" /></a-form-item
        ></a-grid-item>
        <a-grid-item class="mango-simple-form-fields"
          ><a-form-item class="mango-simple-form-item" label="计划类型" required
            ><a-select
              v-model="form.scope_type"
              :options="scopeOptions"
              :field-names="fieldNames"
              :loading="enumsLoading"
              @change="onScopeTypeChange" /></a-form-item
        ></a-grid-item>
        <a-grid-item class="mango-simple-form-fields" v-if="form.scope_type === 0"
          ><a-form-item class="mango-simple-form-item" label="关联需求版本" required
            ><a-select
              v-model="form.requirement_version"
              :options="requirementOptions"
              allow-search
              :loading="requirements.loading" /></a-form-item
        ></a-grid-item>
        <a-grid-item class="mango-simple-form-fields" v-else-if="form.scope_type === 1"
          ><a-form-item class="mango-simple-form-item" label="关联 Sprint" required
            ><a-select
              v-model="form.iteration"
              :options="iterationOptions"
              allow-search
              :loading="iterations.loading" /></a-form-item
        ></a-grid-item>
        <a-grid-item class="mango-simple-form-fields" v-else
          ><a-form-item class="mango-simple-form-item" label="范围标识"
            ><a-input
              v-model="form.scope_ref"
              :max-length="128"
              placeholder="例如 v2.8.0 / 核心回归" /></a-form-item
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
          ><a-form-item class="mango-simple-form-item" label="测试环境"
            ><a-input v-model="form.environment" :max-length="128" /></a-form-item
        ></a-grid-item>
        <a-grid-item class="mango-simple-form-fields"
          ><a-form-item class="mango-simple-form-item" label="构建版本"
            ><a-input v-model="form.build_version" :max-length="128" /></a-form-item
        ></a-grid-item>
        <a-grid-item class="mango-simple-form-fields"
          ><a-form-item class="mango-simple-form-item" label="计划开始"
            ><a-date-picker
              v-model="form.planned_start_time"
              show-time
              value-format="YYYY-MM-DD HH:mm:ss" /></a-form-item
        ></a-grid-item>
        <a-grid-item class="mango-simple-form-fields"
          ><a-form-item class="mango-simple-form-item" label="计划结束"
            ><a-date-picker
              v-model="form.planned_end_time"
              show-time
              value-format="YYYY-MM-DD HH:mm:ss" /></a-form-item
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
import { reportLoadError } from '@/utils/load-error'

  import {
    computed,
    onActivated,
    onBeforeUnmount,
    onDeactivated,
    reactive,
    ref,
    shallowRef,
    watch,
  } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import { scaleDensityPixels } from '@/hooks/useDisplayDensity'
  import {
    getFunctionalRequirements,
    getFunctionalIterations,
    postFunctionalPlan,
    putFunctionalPlan,
  } from '@/api/functional-test'
  import { planIdValue, planList, planObject } from '../presentation'
  import { createPlanEditorForm, planEditorPayload, planSelectionId } from '../list-form'
  import type { PlanEditorForm, PlanEditorDefaults, PlanListRow } from '../types'

  const props = defineProps<{
    contextKey: string
    users: Array<{ key: number | string; title: string }>
    scopeOptions: Array<{ key: number | string; title: string }>
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
  const form: PlanEditorForm = reactive(createPlanEditorForm())
  type Choice = { value: number; label: string }
  const requirements = reactive({ options: [] as Choice[], loading: false, error: false })
  const iterations = reactive({ options: [] as Choice[], loading: false, error: false })
  const originalOwner = shallowRef<{ key: number; title: string } | null>(null)
  const originalRequirement = shallowRef<Choice | null>(null),
    originalIteration = shallowRef<Choice | null>(null)
  const ownerOptions = computed(() =>
    originalOwner.value &&
    !props.users.some((item) => String(item.key) === String(originalOwner.value?.key))
      ? [...props.users, originalOwner.value]
      : props.users
  )
  const withSelected = (options: Choice[], selected: Choice | null) =>
    selected && !options.some((item) => item.value === selected.value)
      ? [...options, selected]
      : options
  const requirementOptions = computed(() =>
    withSelected(requirements.options, originalRequirement.value)
  )
  const iterationOptions = computed(() => withSelected(iterations.options, originalIteration.value))
  let active = true,
    generation = 0
  const sequences = { requirement: 0, iteration: 0 }
  const current = (version: number) => active && visible.value && generation === version
  const canCancel = () => !saving.value
  const isSaving = (id?: number) => saving.value && (id === undefined || savingId.value === id)
  function clearOptions() {
    ++sequences.requirement
    ++sequences.iteration
    Object.assign(requirements, { options: [], loading: false, error: false })
    Object.assign(iterations, { options: [], loading: false, error: false })
  }
  function reset() {
    ++generation
    visible.value = false
    recordId.value = null
    saveError.value = false
    originalOwner.value = null
    originalRequirement.value = null
    originalIteration.value = null
    clearOptions()
    Object.assign(form, createPlanEditorForm())
  }
  function open(record: PlanListRow | null, defaults?: PlanEditorDefaults) {
    if (!active || saving.value) return
    reset()
    recordId.value = record?.id ?? null
    Object.assign(form, createPlanEditorForm(record, defaults))
    originalOwner.value = record?.owner ? { key: record.owner.id, title: record.owner.name } : null
    const version = record?.requirement_version,
      iteration = record?.iteration
    originalRequirement.value = version
      ? {
          value: version.id,
          label: `${version.requirement_name || version.requirement?.name || '需求'} · V${
            version.version_no || '-'
          }`,
        }
      : defaults?.requirementId
      ? { value: defaults.requirementId, label: `需求版本 ID ${defaults.requirementId}` }
      : null
    originalIteration.value = iteration
      ? { value: iteration.id, label: `${iteration.iteration_no} ${iteration.name}` }
      : null
    visible.value = true
    void Promise.allSettled([loadOptions('requirement'), loadOptions('iteration')])
  }
  async function loadOptions(kind: 'requirement' | 'iteration') {
    const product = planSelectionId(form.project_product)
    if (!active || !visible.value || saving.value || product === null) return false
    const version = generation,
      sequence = ++sequences[kind],
      state = kind === 'requirement' ? requirements : iterations
    const valid = () =>
      current(version) &&
      sequences[kind] === sequence &&
      planSelectionId(form.project_product) === product
    state.loading = true
    state.error = false
    try {
      const query = { project_product: product, page: 1, pageSize: 500 }
      const data = (
        await (kind === 'requirement'
          ? getFunctionalRequirements(query)
          : getFunctionalIterations(query))
      ).data
      if (!valid()) return false
      state.options = planList(data).map((value) => {
        const item = planObject(value),
          id = planIdValue(item.id)
        if (typeof item.name !== 'string') throw Error('选项格式错误')
        return {
          value: id,
          label:
            kind === 'requirement'
              ? `${item.name} · V${item.version_no || '-'}`
              : `${typeof item.iteration_no === 'string' ? item.iteration_no : ''} ${item.name}`,
        }
      })
      return true
    } catch (loadFailure0) {
      if (valid()) (reportLoadError(loadFailure0, "加载失败，请重试", false), state.error = true)
      return false
    } finally {
      if (valid()) state.loading = false
    }
  }
  function onScopeTypeChange() {
    form.scope_ref = ''
    if (form.scope_type !== 0) form.requirement_version = null
    if (form.scope_type !== 1) form.iteration = null
  }
  watch(
    () => planSelectionId(form.project_product),
    () => {
      if (!visible.value || saving.value) return
      form.requirement_version = null
      form.iteration = null
      originalRequirement.value = null
      originalIteration.value = null
      clearOptions()
      void Promise.allSettled([loadOptions('requirement'), loadOptions('iteration')])
    },
    { flush: 'sync' }
  )
  async function save() {
    if (!active || !visible.value || saving.value) return false
    const id = recordId.value,
      version = generation,
      payload = planEditorPayload(form, id)
    if (id !== null && props.busyIds?.includes(id)) {
      Message.warning('该计划正在删除确认或处理中')
      return false
    }
    if (
      !payload.name ||
      !payload.project_product ||
      !payload.owner ||
      !Number.isInteger(payload.scope_type) ||
      (payload.scope_type === 0 && !payload.requirement_version) ||
      (payload.scope_type === 1 && !payload.iteration)
    ) {
      Message.warning('请填写必填字段')
      return false
    }
    saving.value = true
    savingId.value = id
    saveError.value = false
    try {
      const response = await (id === null
        ? postFunctionalPlan(payload)
        : putFunctionalPlan(payload))
      if (!current(version)) return false
      const savedId = planIdValue(planObject(response.data).id)
      if (id !== null && savedId !== id) throw Error('保存结果未确认')
      reset()
      Message.success('保存成功')
      emit('saved', savedId)
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
  .mango-plan-editor__notice {
    margin-bottom: var(--m-page-gap);
  }
</style>
