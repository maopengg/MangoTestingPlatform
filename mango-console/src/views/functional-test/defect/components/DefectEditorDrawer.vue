<template>
  <a-drawer
    v-model:visible="visible"
    :title="form.id === null && detailId === null ? '新建缺陷' : `编辑缺陷 ${metadata.defect_no}`"
    :width="760"
    :ok-loading="saving"
    :on-before-ok="save"
    :on-before-cancel="canCancel"
    :mask-closable="!saving"
    :esc-to-close="!saving"
    @cancel="reset"
  >



    <a-alert v-if="saveError" type="error" class="mango-defect-editor__error"
      >保存失败，输入及已上传附件已保留，请重试。</a-alert
    >
    <MangoPanelSpin :loading="detailLoading">
      <a-form :model="form" layout="horizontal" :disabled="saving || detailLoading || detailError">
        <a-grid :cols="2" :col-gap="16">
          <a-grid-item :span="2"><div class="mango-section-title">基本信息</div></a-grid-item>
          <a-grid-item v-if="form.id !== null" :span="2">
            <div class="mango-defect-page__readonly-meta">
              <span>状态：{{ enumTitle(statusOptions, metadata.status) }}</span>
              <span>报告人：{{ metadata.reporter_name || '-' }}</span>
              <span>创建：{{ metadata.create_time || '-' }}</span>
              <span>更新：{{ metadata.update_time || '-' }}</span>
            </div>
          </a-grid-item>
          <a-grid-item :span="2"
            ><a-form-item label="缺陷标题" required><a-input v-model="form.title" /></a-form-item
          ></a-grid-item>
          <a-grid-item
            ><a-form-item label="项目产品" required
              ><ProjectProductSelect
                v-model="form.project_product"
                @change="onFormProductChange" /></a-form-item
          ></a-grid-item>
          <a-grid-item
            ><a-form-item label="模块"
              ><ProductModuleSelect
                v-model="form.module"
                :project-product-id="form.project_product"
                :auto-clear="false" /></a-form-item
          ></a-grid-item>
          <a-grid-item
            ><a-form-item label="缺陷来源" required
              ><a-select
                v-model="form.source_type"
                :loading="enumsLoading"
                :options="sourceOptions"
                :field-names="fieldNames" /></a-form-item
          ></a-grid-item>
          <a-grid-item
            ><a-form-item label="缺陷类型" required
              ><a-select
                v-model="form.defect_type"
                :loading="enumsLoading"
                :options="typeOptions"
                :field-names="fieldNames" /></a-form-item
          ></a-grid-item>
          <a-grid-item
            ><a-form-item label="严重程度" required
              ><a-select
                v-model="form.severity"
                :loading="enumsLoading"
                :options="severityOptions"
                :field-names="fieldNames" /></a-form-item
          ></a-grid-item>
          <a-grid-item
            ><a-form-item label="优先级" required
              ><a-select
                v-model="form.priority"
                :loading="enumsLoading"
                :options="priorityOptions"
                :field-names="fieldNames" /></a-form-item
          ></a-grid-item>
          <a-grid-item
            ><a-form-item label="经办人"
              ><a-select
                v-model="form.assignee"
                :options="users"
                :loading="usersLoading"
                :field-names="fieldNames"
                allow-search
                allow-clear /></a-form-item
          ></a-grid-item>
          <a-grid-item v-if="form.id"
            ><a-form-item label="解决方式"
              ><span>{{ enumTitle(resolutionOptions, metadata.resolution) }}</span></a-form-item
            ></a-grid-item
          >
          <a-grid-item v-if="form.id" :span="2"
            ><a-form-item label="解决说明"
              ><span>{{ metadata.resolution_note || '-' }}</span></a-form-item
            ></a-grid-item
          >
          <a-grid-item v-if="form.id" :span="2"
            ><div class="mango-defect-page__readonly-meta"
              ><span>解决时间：{{ metadata.resolved_at || '-' }}</span
              ><span>关闭时间：{{ metadata.closed_at || '-' }}</span></div
            ></a-grid-item
          >
          <a-grid-item :span="2"><div class="mango-section-title">问题内容</div></a-grid-item>
          <a-grid-item :span="2"
            ><a-form-item label="问题描述"
              ><a-textarea
                v-model="form.description"
                :auto-size="{ minRows: 2, maxRows: 5 }" /></a-form-item
          ></a-grid-item>
          <a-grid-item :span="2"
            ><a-form-item label="前置条件"
              ><a-textarea
                v-model="form.precondition"
                :auto-size="{ minRows: 2, maxRows: 4 }" /></a-form-item
          ></a-grid-item>
          <a-grid-item :span="2">
            <a-form-item label="复现步骤">
              <div class="mango-defect-page__steps">
                <div
                  v-for="(step, index) in form.reproduce_steps"
                  :key="index"
                  class="mango-defect-page__step"
                >
                  <span>{{ index + 1 }}</span
                  ><a-input v-model="step.action" placeholder="操作" /><a-input
                    v-model="step.expected"
                    placeholder="预期"
                  /><a-input v-model="step.actual" placeholder="实际" />
                  <a-button
                    size="mini"
                    status="danger"
                    @click="form.reproduce_steps.splice(index, 1)"
                    >删除</a-button
                  >
                </div>
                <a-button size="small" @click="addStep">添加步骤</a-button>
              </div>
            </a-form-item>
          </a-grid-item>
          <a-grid-item :span="2"
            ><a-form-item label="预期结果"
              ><a-textarea
                v-model="form.expected_result"
                :auto-size="{ minRows: 2, maxRows: 4 }" /></a-form-item
          ></a-grid-item>
          <a-grid-item :span="2"
            ><a-form-item label="实际结果" required
              ><a-textarea
                v-model="form.actual_result"
                :auto-size="{ minRows: 2, maxRows: 5 }" /></a-form-item
          ></a-grid-item>
          <a-grid-item :span="2"
            ><a-form-item label="环境信息"
              ><a-textarea
                v-model="form.environment"
                :auto-size="{ minRows: 2, maxRows: 4 }" /></a-form-item
          ></a-grid-item>
          <a-grid-item :span="2">
            <a-form-item label="附件">
              <div class="mango-defect-page__attachments">
                <a-space v-if="form.attachment_file_ids?.length" wrap>
                  <a-tag
                    v-for="fileId in form.attachment_file_ids"
                    :key="fileId"
                    :closable="!saving"
                    @close="removeAttachment(fileId)"
                    >File #{{ fileId }}</a-tag
                  >
                </a-space>
                <a-upload
                  :file-list="attachmentFileList"
                  multiple
                  :auto-upload="false"
                  :disabled="saving || detailLoading"
                  @change="onAttachmentChange"
                />
              </div>
            </a-form-item>
          </a-grid-item>
          <a-grid-item :span="2"><div class="mango-section-title">关联信息</div></a-grid-item>
          <a-grid-item :span="2"
            ><a-form-item label="关联用例库用例"
              ><a-select
                v-model="form.case_ids"
                :options="caseOptions"
                multiple
                allow-search
                allow-clear
                :loading="caseLoading"
              /><a-button v-if="caseError" size="mini" :loading="caseLoading" @click="loadCases"
                >重试用例</a-button
              ></a-form-item
            ></a-grid-item
          >
          <a-grid-item
            ><a-form-item label="发现于测试计划"
              ><a-select
                v-model="form.source_plan_id"
                :options="planOptions"
                allow-search
                allow-clear
                :loading="plansLoading"
                @change="changePlan"
              /><a-button v-if="plansError" size="mini" :loading="plansLoading" @click="loadPlans"
                >重试计划</a-button
              ></a-form-item
            ></a-grid-item
          >
          <a-grid-item
            ><a-form-item label="关联计划用例"
              ><a-select
                v-model="form.plan_case_ids"
                :options="planCaseOptions"
                multiple
                allow-search
                allow-clear
                :loading="planCaseLoading"
              /><a-button
                v-if="planCaseError"
                size="mini"
                :loading="planCaseLoading"
                @click="loadPlanCases(false)"
                >重试计划用例</a-button
              ></a-form-item
            ></a-grid-item
          >
          <a-grid-item v-if="metadata.relations?.length" :span="2">
            <div class="mango-defect-page__relation-list">
              <div
                v-for="relation in metadata.relations"
                :key="relation.id"
                class="mango-defect-page__relation-item"
              >
                <div
                  ><strong>{{ relation.case_no || '-' }}</strong>
                  {{ relation.case_title || '-' }}</div
                >
                <small v-if="relation.plan_case"
                  >发现于 {{ relation.plan_name || `计划 #${relation.plan_id}` }}，结果
                  {{ enumTitle(enumStore.functional_test_result || [], relation.result) }}，执行人
                  {{ relation.executor_name || '-' }}，{{ relation.execute_time || '-' }}</small
                >
                <small v-else>来自用例库</small>
              </div>
            </div>
          </a-grid-item>
        </a-grid>
      </a-form>
    </MangoPanelSpin>
  </a-drawer>
</template>

<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { computed, onActivated, onBeforeUnmount, onDeactivated, reactive, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import type { FileItem } from '@arco-design/web-vue/es/upload/interfaces'
  import MangoPanelSpin from '@/components/feedback/MangoPanelSpin.vue'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import { useEnum } from '@/store/modules/get-enum'
  import { postUserFile } from '@/api/system/file_data'
  import {
    getFunctionalDefectDetail,
    getFunctionalPlanCases,
    getFunctionalPlans,
    getManualCase,
    postFunctionalDefect,
    putFunctionalDefect,
  } from '@/api/functional-test'
  import {
    createDefectForm,
    defectCaseChoices,
    defectFields,
    defectId,
    defectMetadata,
    defectPayload,
    defectPlanChoices,
  } from '../form'
  import type {
    DefectCaseChoice,
    DefectMutationResult,
    DefectPlanChoice,
    DefectRouteSeed,
    DefectSelection,
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
    (event: 'saved', result: { record: DefectMutationResult; created: boolean }): void
    (event: 'retry-users'): void
    (event: 'retry-enums'): void
  }>()
  const enumStore = useEnum()
  const fieldNames = { value: 'key', label: 'title' }
  const visible = ref(false),
    saving = ref(false),
    saveError = ref(false)
  const detailLoading = ref(false),
    detailError = ref(false),
    detailId = ref<number | null>(null)
  const caseLoading = ref(false),
    caseError = ref(false),
    plansLoading = ref(false),
    plansError = ref(false),
    planCaseLoading = ref(false),
    planCaseError = ref(false)
  const form = reactive(createDefectForm()),
    metadata = ref(defectMetadata())
  const attachmentFileList = ref<FileItem[]>([])
  const libraryCaseRows = ref<DefectCaseChoice[]>([]),
    planCaseRows = ref<DefectCaseChoice[]>([]),
    loadedPlans = ref<DefectPlanChoice[]>([])
  const sourceOptions = computed(() => enumStore.functional_test_defect_source ?? [])
  const typeOptions = computed(() => enumStore.functional_test_defect_type ?? [])
  const severityOptions = computed(() => enumStore.functional_test_defect_severity ?? [])
  const priorityOptions = computed(() => enumStore.functional_test_defect_priority ?? [])
  const statusOptions = computed(() => enumStore.functional_test_defect_status ?? [])
  const resolutionOptions = computed(() => enumStore.functional_test_defect_resolution ?? [])
  const enumTitle = (options: Array<{ key: string | number; title: string }>, value: unknown) =>
    options.find((item) => item.key === value)?.title ?? '-'
  const caseOptions = computed(() => mergeCaseOptions(libraryCaseRows.value, false))
  const planCaseOptions = computed(() => mergeCaseOptions(planCaseRows.value, true))
  const planOptions = computed(() => {
    const options = new Map(loadedPlans.value.map((item) => [item.value, item]))
    for (const relation of metadata.value.relations)
      if (
        relation.plan_id !== null &&
        !options.has(relation.plan_id) &&
        relation.plan_id === defectId(form.source_plan_id)
      )
        options.set(relation.plan_id, {
          value: relation.plan_id,
          label: relation.plan_name || `计划 ${relation.plan_id}`,
          environment: '',
        })
    return [...options.values()]
  })
  let active = true,
    generation = 0,
    caseSequence = 0,
    plansSequence = 0,
    planCaseSequence = 0,
    detailSequence = 0
  let lastProduct: number | null = null,
    lastPlan: number | null = null,
    prefillSeed: DefectRouteSeed | null = null
  let applyingSeed = false
  const seedFields = [
    'module',
    'title',
    'precondition',
    'reproduce_steps',
    'expected_result',
    'actual_result',
    'environment',
  ] as const
  const seedTouched = new Set<(typeof seedFields)[number]>()
  watch(
    () =>
      seedFields.map((field) =>
        field === 'reproduce_steps' ? JSON.stringify(form.reproduce_steps) : form[field]
      ),
    (next, previous) => {
      if (!prefillSeed || applyingSeed) return
      next.forEach((value, index) => {
        if (value !== previous[index]) seedTouched.add(seedFields[index])
      })
    },
    { flush: 'sync' }
  )
  const current = (version: number) => active && visible.value && generation === version
  const savingId = ref<number | null>(null)
  const isSaving = (id: number) => saving.value && savingId.value === id
  const canCancel = () => !saving.value
  function mergeCaseOptions(records: DefectCaseChoice[], fromPlan: boolean) {
    const options = new Map(
      records.map((item) => [item.id, { value: item.id, label: `${item.case_no} ${item.title}` }])
    )
    for (const relation of metadata.value.relations) {
      const id = fromPlan ? relation.plan_case : relation.case
      const selectedIds = fromPlan ? form.plan_case_ids : form.case_ids
      if (id !== null && selectedIds.includes(id) && !options.has(id))
        options.set(id, { value: id, label: `${relation.case_no} ${relation.case_title}` })
    }
    return [...options.values()]
  }
  function reset() {
    ++generation
    ++caseSequence
    ++plansSequence
    ++planCaseSequence
    ++detailSequence
    visible.value = false
    saveError.value = false
    detailId.value = null
    detailLoading.value = false
    detailError.value = false
    caseLoading.value = false
    caseError.value = false
    plansLoading.value = false
    plansError.value = false
    planCaseLoading.value = false
    planCaseError.value = false
    Object.assign(form, createDefectForm())
    metadata.value = defectMetadata()
    attachmentFileList.value = []
    libraryCaseRows.value = []
    planCaseRows.value = []
    loadedPlans.value = []
    lastProduct = null
    lastPlan = null
    prefillSeed = null
    seedTouched.clear()
  }
  function begin() {
    if (!active || saving.value) return false
    reset()
    visible.value = true
    return true
  }
  function assignRecord(value: unknown) {
    Object.assign(form, createDefectForm(value))
    metadata.value = defectMetadata(value)
    lastProduct = defectId(form.project_product)
    lastPlan = defectId(form.source_plan_id)
  }
  async function open(
    record?: unknown,
    defaults?: { projectProduct: DefectSelection; module: DefectSelection }
  ) {
    if (!begin()) return
    assignRecord(record)
    if (form.id === null && defaults) {
      form.project_product = defaults.projectProduct
      form.module = defaults.module
      lastProduct = defectId(form.project_product)
    }
    await Promise.all([loadCases(), loadPlans(), loadPlanCases(false)])
  }
  async function openById(id: number) {
    if (!begin()) return
    detailId.value = id
    await loadDetail()
  }
  async function loadDetail() {
    if (!visible.value || !active || detailId.value === null || saving.value) return
    const id = detailId.value,
      version = generation,
      request = ++detailSequence
    detailLoading.value = true
    detailError.value = false
    try {
      const data: unknown = (await getFunctionalDefectDetail(id)).data
      if (!current(version) || request !== detailSequence) return
      if (defectId(defectFields(data).id) !== id) throw Error('缺陷详情未确认')
      assignRecord(data)
      void Promise.all([loadCases(), loadPlans(), loadPlanCases(false)])
    } catch (loadFailure0) {
      if (current(version) && request === detailSequence) (reportLoadError(loadFailure0, "加载失败，请重试", false), detailError.value = true)
    } finally {
      if (current(version) && request === detailSequence) detailLoading.value = false
    }
  }
  async function openFromRoute(seed: DefectRouteSeed) {
    if (!begin()) return
    Object.assign(form, {
      project_product: seed.projectProduct,
      requirement_version: seed.requirementVersion,
      source_type: seed.caseIds.length ? 1 : 0,
      source_plan_id: seed.planId,
      case_ids: [...seed.caseIds],
      plan_case_ids: [...seed.planCaseIds],
    })
    prefillSeed = { ...seed, caseIds: [...seed.caseIds], planCaseIds: [...seed.planCaseIds] }
    lastProduct = seed.projectProduct
    lastPlan = seed.planId
    await Promise.all([loadCases(), loadPlans(), loadPlanCases(false)])
  }
  function fillFromSeed() {
    if (!prefillSeed) return
    const fromPlan = prefillSeed.planId !== null && prefillSeed.planCaseIds.length > 0
    const id = fromPlan ? prefillSeed.planCaseIds[0] : prefillSeed.caseIds[0]
    const item = (fromPlan ? planCaseRows.value : libraryCaseRows.value).find(
      (row) => row.id === id
    )
    if (!item) return
    applyingSeed = true
    try {
      if (!seedTouched.has('module') && form.module === null) form.module = item.module_id
      if (!seedTouched.has('title')) form.title ||= `[缺陷] ${item.title || item.case_no}`
      if (!seedTouched.has('precondition')) form.precondition ||= item.precondition
      if (!seedTouched.has('reproduce_steps') && !form.reproduce_steps.length)
        form.reproduce_steps = item.test_steps.map((step, index) => ({
          sort: index + 1,
          action: step.action,
          expected: step.expected,
          actual: '',
        }))
      if (!seedTouched.has('expected_result')) form.expected_result ||= item.expected_result
      if (fromPlan) {
        if (!seedTouched.has('actual_result')) form.actual_result ||= item.actual_result
        if (!seedTouched.has('environment'))
          form.environment ||=
            loadedPlans.value.find((plan) => plan.value === defectId(form.source_plan_id))
              ?.environment ?? ''
      }
    } finally {
      applyingSeed = false
    }
  }
  async function loadCases() {
    const product = defectId(form.project_product),
      version = generation,
      request = ++caseSequence
    if (!current(version) || product === null) {
      caseLoading.value = false
      return
    }
    caseLoading.value = true
    caseError.value = false
    const valid = () =>
      current(version) && request === caseSequence && defectId(form.project_product) === product
    try {
      const data: unknown = (
        await getManualCase({ project_product: product, page: 1, pageSize: 500 })
      ).data
      if (!valid()) return
      libraryCaseRows.value = defectCaseChoices(data)
      fillFromSeed()
    } catch (loadFailure0) {
      if (valid()) (reportLoadError(loadFailure0, "加载失败，请重试", false), caseError.value = true)
    } finally {
      if (valid()) caseLoading.value = false
    }
  }
  async function loadPlans() {
    const product = defectId(form.project_product),
      version = generation,
      request = ++plansSequence
    if (!current(version) || product === null) {
      plansLoading.value = false
      return
    }
    plansLoading.value = true
    plansError.value = false
    const valid = () =>
      current(version) && request === plansSequence && defectId(form.project_product) === product
    try {
      const data: unknown = (
        await getFunctionalPlans({ project_product: product, page: 1, pageSize: 500 })
      ).data
      if (!valid()) return
      loadedPlans.value = defectPlanChoices(data)
      fillFromSeed()
    } catch (loadFailure1) {
      if (valid()) (reportLoadError(loadFailure1, "加载失败，请重试", false), plansError.value = true)
    } finally {
      if (valid()) plansLoading.value = false
    }
  }
  async function loadPlanCases(clear = true) {
    const plan = defectId(form.source_plan_id),
      product = defectId(form.project_product),
      version = generation,
      request = ++planCaseSequence
    if (clear) form.plan_case_ids = []
    planCaseRows.value = []
    planCaseError.value = false
    if (!current(version) || plan === null) {
      planCaseLoading.value = false
      return
    }
    planCaseLoading.value = true
    const valid = () =>
      current(version) &&
      request === planCaseSequence &&
      defectId(form.source_plan_id) === plan &&
      defectId(form.project_product) === product
    try {
      const data: unknown = (await getFunctionalPlanCases(plan)).data
      if (!valid()) return
      planCaseRows.value = defectCaseChoices(data)
      fillFromSeed()
    } catch (loadFailure2) {
      if (valid()) (reportLoadError(loadFailure2, "加载失败，请重试", false), planCaseError.value = true)
    } finally {
      if (valid()) planCaseLoading.value = false
    }
  }
  async function onFormProductChange() {
    if (saving.value || detailLoading.value) return
    const product = defectId(form.project_product)
    if (product === lastProduct) return
    lastProduct = product
    lastPlan = null
    prefillSeed = null
    form.module = null
    form.requirement_version = null
    form.case_ids = []
    form.source_plan_id = null
    form.plan_case_ids = []
    metadata.value.relations = []
    libraryCaseRows.value = []
    loadedPlans.value = []
    await Promise.all([loadCases(), loadPlans(), loadPlanCases(false)])
  }
  async function changePlan() {
    if (saving.value || detailLoading.value) return
    const plan = defectId(form.source_plan_id)
    if (plan === lastPlan) return
    lastPlan = plan
    prefillSeed = null
    await loadPlanCases()
  }
  function addStep() {
    if (!saving.value)
      form.reproduce_steps.push({
        sort: form.reproduce_steps.length + 1,
        action: '',
        expected: '',
        actual: '',
      })
  }
  function onAttachmentChange(files: FileItem[]) {
    if (!saving.value) attachmentFileList.value = [...files]
  }
  function removeAttachment(id: number) {
    if (!saving.value)
      form.attachment_file_ids = form.attachment_file_ids.filter((item) => item !== id)
  }
  async function save() {
    if (!active || !visible.value || saving.value || detailLoading.value || detailError.value)
      return false
    if (!form.title || defectId(form.project_product) === null || !form.actual_result) {
      Message.warning('请填写必填字段')
      return false
    }
    const version = generation,
      payload = defectPayload(form),
      created = form.id === null
    const files = attachmentFileList.value.flatMap((item) =>
      item.file ? [{ uid: item.uid, file: item.file }] : []
    )
    savingId.value = form.id
    saving.value = true
    saveError.value = false
    try {
      const uploads = await Promise.allSettled(
        files.map(async (item) => {
          const body = new FormData()
          body.append('test_file', item.file)
          body.append('type', '0')
          body.append('name', `${Date.now()}-${item.file.name}`)
          if (payload.project_product !== null)
            body.append('project_product', String(payload.project_product))
          const data: unknown = (await postUserFile(body)).data,
            id = defectId(defectFields(data).id)
          if (id === null || id <= 0) throw Error('附件上传未确认')
          if (current(version)) {
            form.attachment_file_ids = [...new Set([...form.attachment_file_ids, id])]
            attachmentFileList.value = attachmentFileList.value.filter(
              (file) => file.uid !== item.uid
            )
          }
          return id
        })
      )
      if (!current(version)) return false
      if (uploads.some((item) => item.status === 'rejected')) throw Error('附件上传失败')
      payload.attachment_file_ids = [
        ...new Set([
          ...payload.attachment_file_ids,
          ...uploads.flatMap((item) => (item.status === 'fulfilled' ? [item.value] : [])),
        ]),
      ]
      const data: unknown = (
        await (created ? postFunctionalDefect(payload) : putFunctionalDefect(payload))
      ).data
      if (!current(version)) return false
      const id = defectId(defectFields(data).id)
      if (id === null || id <= 0 || (!created && id !== payload.id)) throw Error('缺陷保存未确认')
      reset()
      Message.success('保存成功')
      emit('saved', { record: { ...defectFields(data), id }, created })
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
  defineExpose({ open, openById, openFromRoute, isSaving })
</script>

<style scoped lang="less">
  .mango-defect-editor__error {
    margin-bottom: var(--m-page-gap);
  }
  .mango-defect-page__steps {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .mango-defect-page__attachments {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .mango-defect-page__readonly-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 8px 20px;
    padding: 8px 12px;
    border-radius: var(--m-radius-md);
    background: var(--m-surface-soft);
    color: var(--m-muted);
  }
  .mango-defect-page__relation-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .mango-defect-page__relation-item {
    padding: 8px 12px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface-soft);
  }
  .mango-defect-page__relation-item small {
    display: block;
    margin-top: 4px;
    color: var(--m-muted);
  }
  .mango-defect-page__step {
    display: grid;
    grid-template-columns: 28px 1fr 1fr 1fr auto;
    align-items: center;
    gap: 8px;
  }
  .mango-defect-page__step > span {
    color: var(--m-muted);
    text-align: center;
  }
</style>
