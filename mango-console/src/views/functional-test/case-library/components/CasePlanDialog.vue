<template>
  <a-modal
    modal-class="mango-simple-form-modal"
    v-if="mode === 'join'"
    v-model:visible="visible"
    :width="560"
    :on-before-cancel="canCancel"
    @cancel="reset"
    title="加入测试计划"
    :ok-loading="saving"
    :on-before-ok="save"
  >
    <a-alert v-if="saveError" type="error" class="mango-case-plan__notice"
      >加入失败，选择已保留，请重试。</a-alert
    >

    <a-form auto-label-width class="mango-simple-form" :model="joinForm" layout="horizontal" :disabled="saving">
      <a-form-item class="mango-simple-form-item" label="测试计划" required>
        <a-select
          v-model="joinForm.plan_id"
          :options="planOptions"
          :loading="planLoading"
          allow-search
        />
      </a-form-item>
    </a-form>
  </a-modal>

  <a-modal
    modal-class="mango-simple-form-modal"
    v-else-if="mode === 'create'"
    v-model:visible="visible"
    :on-before-cancel="canCancel"
    @cancel="reset"
    :title="caseIds.length ? `新建测试计划并加入 ${caseIds.length} 条用例` : '新建测试计划'"
    :width="560"
    :ok-loading="saving"
    :on-before-ok="save"
    :ok-text="createdPlanId === null ? '确定' : '重试加入用例'"
  >
    <a-alert v-if="createdPlanId !== null && saveError" type="warning" class="mango-case-plan__notice"
      >计划已创建（ID {{ createdPlanId }}），用例尚未加入。再次提交只重试加入操作。</a-alert
    >
    <a-alert v-else-if="saveError" type="error" class="mango-case-plan__notice"
      >创建失败，输入已保留，请重试。</a-alert
    >


    <a-form auto-label-width class="mango-simple-form" :model="form" layout="horizontal" :disabled="saving || createdPlanId !== null">
      <div class="mango-case-plan__fields mango-simple-form-fields">
        <div class="mango-case-plan__wide mango-simple-form-fields">
          <a-form-item class="mango-simple-form-item" label="计划名称" required>
            <a-input v-model="form.name" placeholder="请输入计划名称" />
          </a-form-item>
        </div>
        <div class="mango-simple-form-fields">
          <a-form-item class="mango-simple-form-item" label="项目产品" required>
            <ProjectProductSelect
              v-model="form.project_product"
              :disabled="Boolean(caseIds.length) || saving || createdPlanId !== null"
              :allow-clear="!caseIds.length"
              @change="onProductChange"
            />
          </a-form-item>
        </div>
        <div class="mango-simple-form-fields">
          <a-form-item class="mango-simple-form-item" label="计划类型" required>
            <a-select
              v-model="form.scope_type"
              :options="enumStore.functional_test_plan_scope_type"
              :field-names="fieldNames"
              @change="onScopeChange"
            />
          </a-form-item>
        </div>
        <div class="mango-simple-form-fields" v-if="form.scope_type === 0">
          <a-form-item class="mango-simple-form-item" label="关联需求版本" required>
            <a-select
              v-model="form.requirement_version"
              :options="requirementOptions"
              :loading="requirementLoading"
              allow-search
              placeholder="请选择具体需求版本"
            />
          </a-form-item>
        </div>
        <div class="mango-simple-form-fields" v-else-if="form.scope_type === 1">
          <a-form-item class="mango-simple-form-item" label="关联 Sprint" required>
            <a-select
              v-model="form.iteration"
              :options="iterationOptions"
              :loading="iterationLoading"
              allow-search
              placeholder="请选择 Sprint"
            />
          </a-form-item>
        </div>
        <div class="mango-simple-form-fields" v-else>
          <a-form-item class="mango-simple-form-item" label="范围标识">
            <a-input v-model="form.scope_ref" placeholder="例如 Sprint 24 / v2.8.0" />
          </a-form-item>
        </div>
        <div class="mango-simple-form-fields">
          <a-form-item class="mango-simple-form-item" label="负责人" required>
            <a-select
              v-model="form.owner"
              :options="users"
              :field-names="fieldNames"
              allow-search
            />
          </a-form-item>
        </div>
        <div class="mango-simple-form-fields">
          <a-form-item class="mango-simple-form-item" label="计划开始">
            <a-date-picker
              v-model="form.planned_start_time"
              show-time
              value-format="YYYY-MM-DD HH:mm:ss"
            />
          </a-form-item>
        </div>
        <div class="mango-simple-form-fields">
          <a-form-item class="mango-simple-form-item" label="计划结束">
            <a-date-picker
              v-model="form.planned_end_time"
              show-time
              value-format="YYYY-MM-DD HH:mm:ss"
            />
          </a-form-item>
        </div>
        <div class="mango-simple-form-fields">
          <a-form-item class="mango-simple-form-item" label="状态">
            <a-select
              v-model="form.status"
              :options="enumStore.functional_test_plan_status"
              :field-names="fieldNames"
            />
          </a-form-item>
        </div>
        <div class="mango-case-plan__wide mango-simple-form-fields">
          <a-form-item class="mango-simple-form-item" label="备注">
            <a-textarea v-model="form.remark" />
          </a-form-item>
        </div>
      </div>
    </a-form>
  </a-modal>
</template>

<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { onActivated, onBeforeUnmount, onDeactivated, reactive, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import { useEnum } from '@/store/modules/get-enum'
  import {
    addFunctionalPlanCases,
    getFunctionalPlans,
    getFunctionalRequirements,
    getFunctionalIterations,
    postFunctionalPlan,
  } from '@/api/functional-test'
  import type { NavigationCreateSelection } from '@/utils/navigation-create-defaults'
  import { caseProductId } from '../form'
  import { createLibraryPlanForm, libraryPlanPayload } from '../plan-form'
  import type { CasePlanSubject, CaseUserOption, PlanChoice, PlanChoiceRecord } from '../types'

  const props = defineProps<{
    contextKey: string
    users: CaseUserOption[]
    defaults: NavigationCreateSelection
  }>()
  const enumStore = useEnum()
  const fieldNames = { value: 'key', label: 'title' }
  const mode = ref<'create' | 'join' | null>(null)
  const visible = ref(false),
    saving = ref(false),
    saveError = ref(false)
  const form = reactive(createLibraryPlanForm())
  const joinForm = reactive<{ plan_id: number | null }>({ plan_id: null })
  const caseIds = ref<number[]>([])
  const createdPlanId = ref<number | null>(null)
  const planOptions = ref<PlanChoice[]>([]),
    requirementOptions = ref<PlanChoice[]>([]),
    iterationOptions = ref<PlanChoice[]>([])
  const planLoading = ref(false),
    requirementLoading = ref(false),
    iterationLoading = ref(false)
  const planError = ref(false),
    requirementError = ref(false),
    iterationError = ref(false)
  let active = true,
    generation = 0
  let planRequest = 0,
    requirementRequest = 0,
    iterationRequest = 0
  const current = (version: number) => active && visible.value && version === generation
  const canCancel = () => !saving.value

  function reset() {
    ++generation
    ++planRequest
    ++requirementRequest
    ++iterationRequest
    visible.value = false
    mode.value = null
    caseIds.value = []
    createdPlanId.value = null
    Object.assign(form, createLibraryPlanForm())
    joinForm.plan_id = null
    planOptions.value = []
    requirementOptions.value = []
    iterationOptions.value = []
    planLoading.value = false
    requirementLoading.value = false
    iterationLoading.value = false
    planError.value = false
    requirementError.value = false
    iterationError.value = false
    saveError.value = false
  }

  function products(selection: CasePlanSubject[]) {
    const result: NonNullable<CasePlanSubject['productId']>[] = []
    const seen = new Set<string>()
    for (const item of selection) {
      if (item.productId === null || seen.has(String(item.productId))) continue
      seen.add(String(item.productId))
      result.push(item.productId)
    }
    return result
  }

  async function openJoin(selection: CasePlanSubject[]) {
    if (!active || saving.value) return
    const productIds = products(selection)
    if (!selection.length || productIds.length !== 1) {
      Message.warning('请选择同一项目产品下的用例')
      return
    }
    reset()
    mode.value = 'join'
    form.project_product = productIds[0]
    caseIds.value = selection.map((item) => item.id)
    visible.value = true
    await loadPlans()
  }

  async function openCreate(selection: CasePlanSubject[]) {
    if (!active || saving.value) return
    const productIds = products(selection)
    if (productIds.length > 1) {
      Message.warning('创建计划并加入用例时，请选择同一项目产品下的用例')
      return
    }
    reset()
    mode.value = 'create'
    caseIds.value = selection.map((item) => item.id)
    form.project_product = productIds[0] ?? props.defaults.projectProduct
    form.owner = selection[0]?.ownerId ?? null
    visible.value = true
    await Promise.all([loadRequirements(), loadIterations()])
  }

  async function loadPlans() {
    if (!active || !visible.value || mode.value !== 'join') return
    const version = generation,
      request = ++planRequest
    const owns = () => current(version) && request === planRequest
    planLoading.value = true
    planError.value = false
    try {
      const response = await getFunctionalPlans({
        project_product: caseProductId(form.project_product),
        page: 1,
        pageSize: 500,
      })
      const records: PlanChoiceRecord[] = response.data ?? []
      if (owns()) planOptions.value = records.map((item) => ({ label: item.name, value: item.id }))
    } catch (loadFailure0) {
      if (owns()) (reportLoadError(loadFailure0, "加载失败，请重试", false), planError.value = true)
    } finally {
      if (owns()) planLoading.value = false
    }
  }

  async function loadRequirements() {
    const productId = caseProductId(form.project_product)
    if (!active || !visible.value || mode.value !== 'create') return
    const version = generation,
      request = ++requirementRequest
    const owns = () => current(version) && request === requirementRequest
    requirementOptions.value = []
    requirementError.value = false
    requirementLoading.value = Boolean(productId)
    if (!productId) return
    try {
      const response = await getFunctionalRequirements({
        project_product: productId,
        page: 1,
        pageSize: 500,
      })
      const records: PlanChoiceRecord[] = response.data ?? []
      if (owns())
        requirementOptions.value = records.map((item) => ({
          label: `${item.name} · V${item.version_no ?? '-'}`,
          value: item.id,
        }))
    } catch (loadFailure1) {
      if (owns()) (reportLoadError(loadFailure1, "加载失败，请重试", false), requirementError.value = true)
    } finally {
      if (owns()) requirementLoading.value = false
    }
  }

  async function loadIterations() {
    const productId = caseProductId(form.project_product)
    if (!active || !visible.value || mode.value !== 'create') return
    const version = generation,
      request = ++iterationRequest
    const owns = () => current(version) && request === iterationRequest
    iterationOptions.value = []
    iterationError.value = false
    iterationLoading.value = Boolean(productId)
    if (!productId) return
    try {
      const response = await getFunctionalIterations({
        project_product: productId,
        page: 1,
        pageSize: 500,
      })
      const records: PlanChoiceRecord[] = response.data ?? []
      if (owns())
        iterationOptions.value = records.map((item) => ({
          label: `${item.iteration_no ?? ''} ${item.name}`,
          value: item.id,
        }))
    } catch (loadFailure2) {
      if (owns()) (reportLoadError(loadFailure2, "加载失败，请重试", false), iterationError.value = true)
    } finally {
      if (owns()) iterationLoading.value = false
    }
  }

  async function onProductChange() {
    form.requirement_version = null
    form.iteration = null
    await Promise.all([loadRequirements(), loadIterations()])
  }

  function onScopeChange() {
    form.scope_ref = ''
    if (form.scope_type !== 0) form.requirement_version = null
    if (form.scope_type !== 1) form.iteration = null
  }

  async function save() {
    if (!active || !visible.value || saving.value) return false
    const joining = mode.value === 'join'
    if (joining && !joinForm.plan_id) return false
    if (
      !joining &&
      createdPlanId.value === null &&
      (!form.name ||
        !caseProductId(form.project_product) ||
        !form.owner ||
        (form.scope_type === 0 && !form.requirement_version) ||
        (form.scope_type === 1 && !form.iteration))
    ) {
      Message.warning('请填写所有必填字段')
      return false
    }
    const version = generation
    const ids = [...caseIds.value]
    const payload = libraryPlanPayload(form)
    let targetId = joining ? joinForm.plan_id : createdPlanId.value
    saving.value = true
    saveError.value = false
    try {
      if (!joining && targetId === null) {
        const response = await postFunctionalPlan(payload)
        if (!current(version)) return false
        targetId = response.data.id
        // Keep the acknowledged plan when association fails; retry must not create another plan.
        createdPlanId.value = targetId
      }
      if (!current(version)) return false
      if (ids.length) await addFunctionalPlanCases({ plan_id: targetId, case_ids: ids })
      if (current(version)) {
        reset()
        Message.success(
          joining
            ? '已加入测试计划'
            : ids.length
            ? '测试计划创建成功，所选用例已加入'
            : '测试计划创建成功'
        )
      }
    } catch {
      if (current(version)) saveError.value = true
    } finally {
      saving.value = false
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
  defineExpose({ openCreate, openJoin })
</script>

<style scoped>
  .mango-case-plan__notice {
    margin-bottom: var(--m-page-gap);
  }
  .mango-case-plan__fields {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    column-gap: 16px;
  }
  .mango-case-plan__fields > div {
    min-width: 0;
  }
  .mango-case-plan__wide {
    grid-column: 1 / -1;
  }
</style>
