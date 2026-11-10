<template>
  <main class="mango-requirement-detail mango-detail-workbench-page">
    <header class="mango-detail-toolbar mango-requirement-detail__header">
      <div class="mango-detail-heading">
        <div class="mango-detail-title" :title="suite?.form.requirement_name">
          需求详情 / {{ suiteId || '-' }} /
          {{ suite?.form.requirement_name || suite?.requirement?.name || '-' }}
        </div>
        <div class="mango-detail-subtitle">
          <a-tag :color="enumStore.colors[requirementForm.requirement_category]">{{
            categoryTitle
          }}</a-tag>
          {{ suite?.requirement?.requirement_key || '-' }} · V{{ suite?.version_no || '-' }} ·
          {{ suite?.product?.name || '-' }} · {{ suite?.iterationName || '-' }}
        </div>
      </div>
      <a-space class="mango-detail-actions" wrap>
        <span class="mango-requirement-detail__save" :class="'is-' + saveState">{{
          saveStateText
        }}</span>
        <a-button
          v-if="saver.failed.size"
          size="small"
          :loading="saver.writing.value"
          :disabled="controlsBlocked"
          @click="saver.retry"
          >重试保存</a-button
        >
        <a-button class="mango-back-button" size="small" @click="router.back()">返回</a-button>
        <a-button
          size="small"
          :loading="navigating === 'workspace'"
          :disabled="!loaded || navigating !== null"
          @click="openCaseWorkspace"
          >用例生成工作台</a-button
        >
        <a-button
          size="small"
          type="primary"
          :loading="navigating === 'create-plan'"
          :disabled="!loaded || navigating !== null"
          @click="createPlan"
          >新建测试计划</a-button
        >
      </a-space>
    </header>
    <a-alert v-if="suiteId === null" type="error">需求版本 ID 无效，请返回列表重新打开。</a-alert>
    
    <a-alert v-if="navigationError" type="error">跳转失败，请再次点击对应操作重试。</a-alert>
    <a-alert v-if="transitionError" type="error"
      >状态更新失败，请重试。<a-button
        size="mini"
        :loading="transitioning"
        :disabled="operationBlocked"
        @click="retryTransition"
        >重试</a-button
      ></a-alert
    >
    <section
      class="mango-section-card mango-requirement-detail__workflow mango-horizontal-scroll-region"
      aria-label="需求阶段"
    >
      <button
        v-for="item in workflowOptions"
        :key="item.key"
        type="button"
        class="mango-requirement-detail__stage"
        :class="{ 'is-current': suite?.status === item.key, 'is-passed': isPassed(item.key) }"
        :aria-current="suite?.status === item.key ? 'step' : undefined"
        :aria-busy="transitioning && requestedStatus === item.key"
        :disabled="operationBlocked || hasUnsaved"
        @click="changeStatus(item.key)"
      >
        <a-spin :loading="transitioning && requestedStatus === item.key">{{ item.title }}</a-spin>
      </button>
    </section>
    <section class="mango-detail-workbench">
      <a-tabs v-model:active-key="activeTab">
        <a-tab-pane key="detail" title="详细信息">
          <div class="mango-requirement-detail__options">
            
          </div>
          <MangoPanelSpin :loading="loading.suite" class="mango-requirement-detail__form-panel">
            <section class="mango-section-card">
              <div class="mango-section-title">基本信息</div>
              <a-form
                :model="form"
                :disabled="controlsBlocked"
                layout="horizontal"
                auto-label-width
              >
                <div class="mango-requirement-detail__fields">
                  <a-form-item label="需求概要" class="mango-requirement-detail__full"
                    ><a-input
                      v-model="form.requirement_name"
                      @blur="saveSuiteField('requirement_name')"
                  /></a-form-item>
                  <a-form-item label="需求分类"
                    ><a-select
                      v-model="requirementForm.requirement_category"
                      :disabled="controlsBlocked || !suite?.requirement"
                      :options="requirementCategoryOptions"
                      :field-names="fieldNames"
                      @change="saver.saveRequirement"
                  /></a-form-item>
                  <a-form-item label="问题类型"
                    ><a-select
                      v-model="requirementForm.issue_type"
                      :disabled="controlsBlocked || !suite?.requirement"
                      :options="issueTypeOptions"
                      :field-names="fieldNames"
                      @change="saver.saveRequirement"
                  /></a-form-item>
                  <a-form-item label="PM"
                    ><a-select
                      v-model="requirementForm.owner"
                      :disabled="controlsBlocked || !suite?.requirement"
                      :options="userOptions"
                      :loading="loading.users"
                      :field-names="fieldNames"
                      allow-search
                      @change="saver.saveRequirement"
                  /></a-form-item>
                  <a-form-item label="开发负责人"
                    ><a-select
                      v-model="form.development_owner"
                      :options="userOptions"
                      :loading="loading.users"
                      :field-names="fieldNames"
                      allow-search
                      allow-clear
                      @change="saveSuiteField('development_owner')"
                  /></a-form-item>
                  <a-form-item label="QA owner"
                    ><a-select
                      v-model="form.owner"
                      :options="userOptions"
                      :loading="loading.users"
                      :field-names="fieldNames"
                      allow-search
                      @change="saveSuiteField('owner')"
                  /></a-form-item>
                  <a-form-item label="Team"
                    ><a-select
                      v-model="form.delivery_team"
                      :options="departmentOptions"
                      :loading="loading.departments"
                      :field-names="departmentFieldNames"
                      allow-search
                      allow-clear
                      @change="saveSuiteField('delivery_team')"
                  /></a-form-item>
                  <a-form-item label="所属 Sprint" required
                    ><a-select
                      v-model="form.iteration_ref"
                      :options="iterationOptions"
                      :loading="loading.iterations"
                      allow-search
                      placeholder="请选择 Sprint"
                      @change="saveSuiteField('iteration_ref')"
                  /></a-form-item>
                  <a-form-item label="描述" class="mango-requirement-detail__full"
                    ><a-textarea
                      v-model="form.description"
                      :auto-size="{ minRows: 2, maxRows: 6 }"
                      @blur="saveSuiteField('description')"
                  /></a-form-item>
                  <a-form-item label="需要测试"
                    ><a-switch
                      :model-value="form.test_required"
                      :loading="saver.writing.value"
                      :before-change="() => saver.toggleFlag('test_required')"
                      size="small"
                  /></a-form-item>
                  <a-form-item label="建议自动化"
                    ><a-switch
                      :model-value="form.automation_recommended"
                      :loading="saver.writing.value"
                      :before-change="() => saver.toggleFlag('automation_recommended')"
                      size="small"
                  /></a-form-item>
                  <a-form-item label="效果测试"
                    ><a-switch
                      :model-value="form.effect_test_required"
                      :loading="saver.writing.value"
                      :before-change="() => saver.toggleFlag('effect_test_required')"
                      size="small"
                  /></a-form-item>
                </div>
              </a-form>
            </section>
          </MangoPanelSpin>
          <RequirementTasks
            ref="tasksRef"
            :context-key="contextKey"
            :requirement-id="suiteId"
            :enabled="loaded"
            :blocked="transitioning"
            :users="userOptions"
            :users-loading="loading.users"
          />
          <section class="mango-section-card">
            <div class="mango-section-title">排期与发布</div>
            <a-form :model="form" :disabled="controlsBlocked" layout="horizontal" auto-label-width>
              <div class="mango-requirement-detail__fields">
                <a-form-item v-for="field in dateFields" :key="field.key" :label="field.title">
                  <a-date-picker
                    v-model="form[field.key]"
                    value-format="YYYY-MM-DD"
                    @change="saveSuiteField(field.key)"
                  />
                </a-form-item>
                <a-form-item label="关联客户"
                  ><a-input v-model="form.customer_ref" @blur="saveSuiteField('customer_ref')"
                /></a-form-item>
              </div>
            </a-form>
          </section>
        </a-tab-pane>
        <a-tab-pane key="cases" :title="'用例（' + cases.length + '）'">
          <section class="mango-section-card">
            <div class="mango-section-title mango-requirement-detail__section-title">
              <span>关联用例</span>
              <a-space
                ><a-button
                  size="small"
                  :loading="navigating === 'workspace'"
                  :disabled="!loaded || navigating !== null"
                  @click="openCaseWorkspace"
                  >生成用例</a-button
                ><a-button
                  size="small"
                  type="primary"
                  :disabled="assetWriteBlocked || loading.cases"
                  @click="openCasePicker"
                  >从用例库关联</a-button
                ></a-space
              >
            </div>
            
            <a-alert v-if="unbindError" type="error"
              >取消关联失败，请再次点击对应操作重试。</a-alert
            >
            <a-table
              :data="cases"
              :columns="caseColumns"
              :pagination="false"
              :loading="loading.cases"
              :scroll="{ x: 1040 }"
              row-key="id"
              :selected-keys="selectedCaseIds"
              :row-selection="{ type: 'checkbox', showCheckedAll: true }"
              @selection-change="selectCases"
            >
              <template #case_no="{ record }"
                ><a-link
                  :loading="navigating === 'case-' + record.id"
                  :disabled="navigating !== null"
                  @click="openCase(record)"
                  >{{ record.case_no }}</a-link
                ></template
              >
              <template #case_priority="{ record }"
                ><a-tag :color="enumStore.colors[record.priority]">{{
                  enumTitle(priorityOptions, record.priority)
                }}</a-tag></template
              >
              <template #case_operations="{ record }"
                ><MangoTableActions
                  :actions="[
                    {
                      label: '取消关联',
                      danger: true,
                      loading: unbindingIds.includes(record.id),
                      disabled: assetWriteBlocked || loading.cases,
                      onClick: () => unbindCases([record.id]),
                    },
                  ]"
              /></template>
            </a-table>
          </section>
        </a-tab-pane>
        <a-tab-pane key="plans" :title="'测试计划（' + plans.length + '）'">
          <section class="mango-section-card">
            
            <a-table
              :data="plans"
              :columns="planColumns"
              :pagination="false"
              :loading="loading.plans"
              :scroll="{ x: 900 }"
              row-key="id"
            >
              <template #plan_name="{ record }"
                ><a-link
                  :loading="navigating === 'plan-' + record.id"
                  :disabled="navigating !== null"
                  @click="openPlan(record)"
                  >{{ record.name }}</a-link
                ></template
              >
              <template #plan_status="{ record }"
                ><a-tag :color="enumStore.colors[record.status]">{{
                  enumTitle(planStatusOptions, record.status)
                }}</a-tag></template
              >
              <template #plan_progress="{ record }">{{
                formatRate(record.execution_stats.progress)
              }}</template>
              <template #plan_pass_rate="{ record }">{{
                formatRate(record.execution_stats.pass_rate)
              }}</template>
            </a-table>
          </section>
        </a-tab-pane>
        <a-tab-pane key="defects" :title="'缺陷（' + defects.length + '）'">
          <section class="mango-section-card">
            <div class="mango-section-title mango-requirement-detail__section-title"
              ><span>需求缺陷</span
              ><a-button
                size="small"
                type="primary"
                :loading="navigating === 'create-defect'"
                :disabled="!loaded || navigating !== null"
                @click="createDefect"
                >新增缺陷</a-button
              ></div
            >
            
            <a-table
              :data="defects"
              :columns="defectColumns"
              :pagination="false"
              :loading="loading.defects"
              :scroll="{ x: 980 }"
              row-key="id"
            >
              <template #defect_status="{ record }"
                ><a-tag :color="enumStore.colors[record.status]">{{
                  enumTitle(defectStatusOptions, record.status)
                }}</a-tag></template
              >
              <template #defect_severity="{ record }"
                ><a-tag :color="enumStore.colors[record.severity]">{{
                  enumTitle(defectSeverityOptions, record.severity)
                }}</a-tag></template
              >
            </a-table>
          </section>
        </a-tab-pane>
        <a-tab-pane key="resources" :title="'相关文档（' + resources.length + '）'">
          <section class="mango-section-card">
            
            <a-list :data="resources" :loading="loading.resources">
              <template #item="{ item }"
                ><a-list-item
                  ><a-list-item-meta :title="item.title || item.context_key"
                    ><template #description
                      ><a-tooltip :content="item.content || item.file_name || '-'"
                        ><span class="mango-requirement-detail__document-text">{{
                          item.content || item.file_name || '-'
                        }}</span></a-tooltip
                      ></template
                    ></a-list-item-meta
                  ><template #extra>{{ item.update_time }}</template></a-list-item
                ></template
              >
            </a-list>
          </section>
        </a-tab-pane>
      </a-tabs>
    </section>
    <RequirementCasePicker
      ref="casePickerRef"
      :context-key="contextKey"
      :requirement-id="suiteId"
      :product-id="suite?.product?.id || null"
      :available="loaded"
      :bound-ids="cases.map((item) => item.id)"
      :priority-options="priorityOptions"
      :priority-colors="enumStore.colors"
      @changed="onCasesBound"
    />
  </main>
</template>
<script setup lang="ts">
  import {
    computed,
    onActivated,
    onBeforeUnmount,
    onDeactivated,
    onMounted,
    reactive,
    ref,
    shallowRef,
    watch,
  } from 'vue'
  import type { ShallowRef } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { useRoute, useRouter } from 'vue-router'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import MangoPanelSpin from '@/components/feedback/MangoPanelSpin.vue'
  import { useEnum } from '@/store/modules/get-enum'
  import useUserStore from '@/store/modules/user'
  import { getUserName } from '@/api/user/user'
  import { getUserDepartment } from '@/api/user/department'
  import {
    getFunctionalContextResource,
    getFunctionalIterations,
    getFunctionalRequirementCases,
    getManualSuite,
    getRelatedFunctionalDefects,
    getRelatedFunctionalPlans,
    transitionManualSuiteStatus,
    unbindFunctionalRequirementCases,
  } from '@/api/functional-test'
  import RequirementCasePicker from './components/RequirementCasePicker.vue'
  import RequirementTasks from './components/RequirementTasks.vue'
  import { useRequirementSave } from './composables/useRequirementSave'
  import {
    caseColumns,
    dateFields,
    defectColumns,
    issueTypeOptions,
    planColumns,
    requirementCategoryOptions,
    workflowOptions,
  } from './config'
  import {
    createRequirementForm,
    createVersionForm,
    parseRequirementCase,
    parseRequirementDefect,
    parseRequirementPlan,
    parseRequirementResource,
    parseRequirementVersion,
    requirementId,
    requirementList,
    requirementObject,
  } from './presentation'
  import type {
    RequirementCasePickerHandle,
    RequirementTasksHandle,
    RequirementCaseRow,
    RequirementDefect,
    RequirementForm,
    RequirementPlan,
    RequirementResource,
    RequirementVersion,
    RequirementVersionField,
    RequirementVersionForm,
  } from './types'

  const route = useRoute(),
    router = useRouter(),
    enumStore = useEnum(),
    user = useUserStore()
  const suiteId = computed(() => requirementId(route.query.id))
  const contextKey = computed(() =>
    JSON.stringify([
      route.fullPath,
      user.userId,
      user.roleId,
      user.token,
      user.selected_environment,
    ])
  )
  const suite = shallowRef<RequirementVersion | null>(null)
  const form: RequirementVersionForm = reactive(createVersionForm())
  const requirementForm: RequirementForm = reactive(createRequirementForm())
  const cases = shallowRef<RequirementCaseRow[]>([]),
    plans = shallowRef<RequirementPlan[]>([]),
    defects = shallowRef<RequirementDefect[]>([]),
    resources = shallowRef<RequirementResource[]>([])
  const users = shallowRef<Array<{ key: number | string; title: string }>>([])
  const departments = shallowRef<Array<{ id: number; name: string }>>([])
  const iterations = shallowRef<Array<{ value: number; label: string }>>([])
  type Region =
    | 'suite'
    | 'cases'
    | 'plans'
    | 'defects'
    | 'resources'
    | 'users'
    | 'departments'
    | 'iterations'
    | 'enums'
  const emptyRegions = () => ({
    suite: false,
    cases: false,
    plans: false,
    defects: false,
    resources: false,
    users: false,
    departments: false,
    iterations: false,
    enums: false,
  })
  const loading = reactive(emptyRegions()),
    errors = reactive(emptyRegions())
  const sequences: Record<Region, number> = {
    suite: 0,
    cases: 0,
    plans: 0,
    defects: 0,
    resources: 0,
    users: 0,
    departments: 0,
    iterations: 0,
    enums: 0,
  }
  const casePickerRef = ref<RequirementCasePickerHandle | null>(null),
    tasksRef = ref<RequirementTasksHandle | null>(null)
  const activeTab = ref('detail'),
    selectedCaseIds = ref<number[]>([])
  const transitioning = ref(false),
    requestedStatus = ref<number | null>(null),
    transitionError = ref(false)
  const unbindingIds = ref<number[]>([]),
    unbindError = ref(false)
  const navigating = ref<string | null>(null),
    navigationError = ref(false)
  const wantedSuite = ref(false),
    wantedCases = ref(false),
    wantedAll = ref(false)
  let active = true,
    mounted = false,
    epoch = 0
  const available = () =>
    active && route.path === '/functional-test/requirement/details' && suiteId.value !== null
  const current = (version: number) => available() && epoch === version
  const loaded = computed(() => suite.value !== null && suite.value.id === suiteId.value)
  const externalBusy = computed(
    () => transitioning.value || unbindingIds.value.length > 0 || !!casePickerRef.value?.isOpen()
  )
  const controlsBlocked = computed(() => !loaded.value || loading.suite || externalBusy.value)
  const saver = useRequirementSave({
    suite,
    form,
    requirementForm,
    getEpoch: () => epoch,
    isCurrent: current,
    canSave: () => available() && !controlsBlocked.value,
    invalidateRead: () => {
      ++sequences.suite
      loading.suite = false
    },
    iterationLabel: (id) =>
      iterations.value.find((item) => item.value === id)?.label || (id === null ? '' : 'ID ' + id),
  })
  const physicalBusy = computed(
    () =>
      saver.writing.value ||
      transitioning.value ||
      unbindingIds.value.length > 0 ||
      !!casePickerRef.value?.isSaving() ||
      !!tasksRef.value?.isSaving()
  )
  const operationBlocked = computed(
    () => !loaded.value || loading.suite || physicalBusy.value || !!casePickerRef.value?.isOpen()
  )
  const assetWriteBlocked = computed(() => operationBlocked.value)
  const hasUnsaved = computed(
    () =>
      loaded.value &&
      (JSON.stringify(createVersionForm(form)) !== JSON.stringify(suite.value?.form) ||
        (!!suite.value?.requirement &&
          JSON.stringify(createRequirementForm(requirementForm)) !==
            JSON.stringify(suite.value.requirement.form)))
  )
  const saveState = computed(() =>
    saver.writing.value
      ? 'saving'
      : saver.failed.size
      ? 'failed'
      : hasUnsaved.value
      ? 'pending'
      : 'saved'
  )
  const saveStateText = computed(() =>
    !loaded.value
      ? ''
      : { saving: '正在保存…', failed: '保存失败', pending: '待保存', saved: '已保存' }[
          saveState.value
        ]
  )
  const fieldNames = { value: 'key', label: 'title' },
    departmentFieldNames = { value: 'id', label: 'name' }
  const priorityOptions = computed(() => enumStore.case_level || []),
    planStatusOptions = computed(() => enumStore.functional_test_plan_status || [])
  const defectStatusOptions = computed(() => enumStore.functional_test_defect_status || []),
    defectSeverityOptions = computed(() => enumStore.functional_test_defect_severity || [])
  const enumTitle = (
    options: Array<{ key: number | string; title: string }>,
    value: number | null
  ) => options.find((item) => Number(item.key) === value)?.title || '-'
  const categoryTitle = computed(() =>
    enumTitle(requirementCategoryOptions, requirementForm.requirement_category)
  )
  const formatRate = (value: number) => value.toFixed(0) + '%'
  const isPassed = (status: number) => {
    const index = workflowOptions.findIndex((item) => item.key === status),
      currentIndex = workflowOptions.findIndex((item) => item.key === suite.value?.status)
    return index >= 0 && currentIndex > index
  }
  const optionTitles = {
    users: '用户选项',
    departments: '部门选项',
    iterations: 'Sprint',
    enums: '枚举',
  }
  type OptionKey = 'users' | 'departments' | 'iterations' | 'enums'
  const failedOptions = computed(() =>
    (Object.keys(optionTitles) as OptionKey[]).filter((key) => errors[key])
  )
  const userOptions = computed(() => {
    const next = [...users.value]
    const fallback = [
      [suite.value?.form.owner, suite.value?.ownerName],
      [suite.value?.form.development_owner, suite.value?.developerName],
      [suite.value?.requirement?.form.owner, ''],
    ] as const
    for (const [id, name] of fallback)
      if (id && !next.some((item) => Number(item.key) === id))
        next.push({ key: id, title: name || 'ID ' + id })
    return next
  })
  const departmentOptions = computed(() => {
    const id = suite.value?.form.delivery_team
    return id && !departments.value.some((item) => item.id === id)
      ? [...departments.value, { id, name: suite.value?.teamName || 'ID ' + id }]
      : departments.value
  })
  const iterationOptions = computed(() => {
    const id = suite.value?.form.iteration_ref
    return id && !iterations.value.some((item) => item.value === id)
      ? [...iterations.value, { value: id, label: suite.value?.iterationName || 'ID ' + id }]
      : iterations.value
  })
  async function readRegion(
    key: Region,
    request: () => Promise<unknown>,
    apply: (data: unknown) => void
  ) {
    if (!available()) return false
    const version = epoch,
      sequence = ++sequences[key]
    const valid = () => current(version) && sequences[key] === sequence
    loading[key] = true
    errors[key] = false
    try {
      const response = requirementObject(await request())
      if (!valid()) return false
      apply(response.data)
      return true
    } catch {
      if (valid()) errors[key] = true
      return false
    } finally {
      if (valid()) loading[key] = false
    }
  }
  function applySuite(next: RequirementVersion) {
    const previous = suite.value
    for (const key of Object.keys(form) as RequirementVersionField[]) {
      if (!previous || form[key] === previous.form[key])
        Object.assign(form, { [key]: next.form[key] })
    }
    for (const key of Object.keys(requirementForm) as Array<keyof RequirementForm>) {
      if (
        !previous?.requirement ||
        previous.requirement.id !== next.requirement?.id ||
        requirementForm[key] === previous.requirement.form[key]
      )
        Object.assign(requirementForm, {
          [key]: next.requirement?.form[key] ?? createRequirementForm()[key],
        })
    }
    suite.value = next
  }
  async function loadSuite() {
    if (!available()) return false
    if (physicalBusy.value) {
      wantedSuite.value = true
      return false
    }
    const target = suiteId.value!
    wantedSuite.value = false
    return readRegion(
      'suite',
      () => getManualSuite({ id: target }),
      (data) => {
        const records = requirementList(data)
        if (records.length !== 1) throw Error('需求详情未确认')
        applySuite(parseRequirementVersion(records[0], target))
        void loadIterations()
      }
    )
  }
  function readList<T>(
    key: Region,
    request: () => Promise<unknown>,
    parse: (row: unknown) => T,
    rows: ShallowRef<T[]>
  ) {
    return readRegion(key, request, (data) => {
      const next = requirementList(data).map(parse)
      rows.value = next
    })
  }
  function loadCases() {
    if (unbindingIds.value.length || casePickerRef.value?.isSaving()) {
      wantedCases.value = true
      return Promise.resolve(false)
    }
    const target = suiteId.value
    wantedCases.value = false
    return readList(
      'cases',
      () => getFunctionalRequirementCases(target!),
      parseRequirementCase,
      cases
    ).then((success) => {
      if (success)
        selectedCaseIds.value = selectedCaseIds.value.filter((id) =>
          cases.value.some((row) => row.id === id)
        )
      return success
    })
  }
  const loadPlans = () => {
    const target = suiteId.value
    return readList(
      'plans',
      () => getRelatedFunctionalPlans({ requirement_version_id: target }),
      parseRequirementPlan,
      plans
    )
  }
  const loadDefects = () => {
    const target = suiteId.value
    return readList(
      'defects',
      () => getRelatedFunctionalDefects({ requirement_version_id: target }),
      parseRequirementDefect,
      defects
    )
  }
  const loadResources = () => {
    const target = suiteId.value
    return readList(
      'resources',
      () => getFunctionalContextResource({ suite: target, page: 1, pageSize: 200 }),
      parseRequirementResource,
      resources
    )
  }
  const loadUsers = () =>
    readList(
      'users',
      getUserName,
      (value) => {
        const row = requirementObject(value)
        if (
          (typeof row.key !== 'number' && typeof row.key !== 'string') ||
          typeof row.title !== 'string'
        )
          throw Error('用户选项格式错误')
        return { key: row.key, title: row.title }
      },
      users
    )
  const loadDepartments = () =>
    readList(
      'departments',
      () => getUserDepartment({ page: 1, pageSize: 500 }),
      (value) => {
        const row = requirementObject(value),
          id = requirementId(row.id)
        if (!id || typeof row.name !== 'string') throw Error('部门选项格式错误')
        return { id, name: row.name }
      },
      departments
    )
  function loadIterations() {
    const product = suite.value?.product?.id
    if (!product) return Promise.resolve(false)
    return readList(
      'iterations',
      () => getFunctionalIterations({ project_product: product, page: 1, pageSize: 500 }),
      (value) => {
        const row = requirementObject(value),
          id = requirementId(row.id)
        if (!id || typeof row.name !== 'string') throw Error('Sprint 选项格式错误')
        return {
          value: id,
          label: (typeof row.iteration_no === 'string' ? row.iteration_no : '') + ' ' + row.name,
        }
      },
      iterations
    )
  }
  async function loadEnums() {
    if (!available()) return false
    const version = epoch,
      sequence = ++sequences.enums
    loading.enums = true
    errors.enums = false
    try {
      await enumStore.getEnum()
      return current(version) && sequences.enums === sequence
    } catch {
      if (current(version) && sequences.enums === sequence) errors.enums = true
      return false
    } finally {
      if (current(version) && sequences.enums === sequence) loading.enums = false
    }
  }
  const retryOptions = (key: OptionKey) =>
    ({
      users: loadUsers,
      departments: loadDepartments,
      iterations: loadIterations,
      enums: loadEnums,
    }[key]())
  function loadAll() {
    if (!available()) return Promise.resolve([])
    if (physicalBusy.value) {
      wantedAll.value = true
      return Promise.allSettled([loadUsers(), loadDepartments(), loadEnums()])
    }
    wantedAll.value = false
    return Promise.allSettled([
      loadSuite(),
      loadCases(),
      loadPlans(),
      loadDefects(),
      loadResources(),
      loadUsers(),
      loadDepartments(),
      loadEnums(),
    ])
  }
  function saveSuiteField(field: RequirementVersionField) {
    return saver.saveField(field)
  }
  async function changeStatus(status: number) {
    if (
      !available() ||
      operationBlocked.value ||
      hasUnsaved.value ||
      !suite.value ||
      status === suite.value.status
    )
      return false
    if (!suite.value.form.iteration_ref) {
      Message.warning('请先绑定迭代')
      return false
    }
    const version = epoch,
      target = suite.value.id,
      expectedTime = suite.value.update_time
    ++sequences.suite
    loading.suite = false
    transitioning.value = true
    transitionError.value = false
    requestedStatus.value = status
    try {
      const data = requirementObject(
        (
          await transitionManualSuiteStatus({
            id: target,
            status,
            expected_update_time: expectedTime,
          })
        ).data
      )
      if (!current(version)) return false
      const next = parseRequirementVersion(data.suite, target)
      if (next.status !== status) throw Error('状态结果未确认')
      applySuite(next)
      Message.success('需求状态已更新')
      return true
    } catch {
      if (current(version)) transitionError.value = true
      return false
    } finally {
      transitioning.value = false
    }
  }
  const retryTransition = () =>
    requestedStatus.value === null ? Promise.resolve(false) : changeStatus(requestedStatus.value)
  function selectCases(keys: Array<number | string>) {
    if (!available() || loading.cases || assetWriteBlocked.value) return
    selectedCaseIds.value = [...new Set(keys.map(Number))].filter((id) =>
      cases.value.some((row) => row.id === id)
    )
  }
  function openCasePicker() {
    if (available() && !assetWriteBlocked.value && !loading.cases) casePickerRef.value?.open()
  }
  function onCasesBound(id: number) {
    if (!available() || id !== suiteId.value) return
    ++sequences.cases
    wantedCases.value = true
    wantedSuite.value = true
  }
  async function unbindCases(ids: number[]) {
    if (!available() || assetWriteBlocked.value || loading.cases || !suite.value) return false
    const selected = [...new Set(ids)].filter((id) => cases.value.some((row) => row.id === id))
    if (!selected.length) return false
    const version = epoch,
      target = suite.value.id
    ++sequences.cases
    unbindError.value = false
    unbindingIds.value = selected
    try {
      const data = requirementObject(
        (await unbindFunctionalRequirementCases(target, [...selected])).data
      )
      if (!current(version)) return false
      if (
        typeof data.unbound_count !== 'number' ||
        !Number.isSafeInteger(data.unbound_count) ||
        data.unbound_count < 0
      )
        throw Error('取消结果未确认')
      cases.value = cases.value.filter((row) => !selected.includes(row.id))
      selectedCaseIds.value = selectedCaseIds.value.filter((id) => !selected.includes(id))
      Message.success('已取消关联')
      wantedCases.value = true
      wantedSuite.value = true
      return true
    } catch {
      if (current(version)) unbindError.value = true
      return false
    } finally {
      unbindingIds.value = []
    }
  }
  async function navigate(key: string, path: string, query: Record<string, string | number>) {
    if (!available() || !loaded.value || navigating.value !== null) return false
    const version = epoch
    navigating.value = key
    navigationError.value = false
    try {
      const failure = await router.push({ path, query })
      if (current(version) && failure) navigationError.value = true
      return !failure
    } catch {
      if (current(version)) navigationError.value = true
      return false
    } finally {
      navigating.value = null
    }
  }
  const openCaseWorkspace = () =>
    navigate('workspace', '/functional-test/suite/details', { id: suiteId.value! })
  const createPlan = () =>
    navigate('create-plan', '/functional-test/plan/index', {
      requirement_version: suiteId.value!,
      project_product: suite.value?.product?.id || '',
      create: 1,
    })
  const createDefect = () =>
    navigate('create-defect', '/functional-test/defect/index', {
      requirement_version: suiteId.value!,
      project_product: suite.value?.product?.id || '',
      create: 1,
    })
  function openPlan(row: RequirementPlan) {
    if (plans.value.includes(row))
      return navigate('plan-' + row.id, '/functional-test/plan/details', { id: row.id })
  }
  function openCase(row: RequirementCaseRow) {
    if (cases.value.includes(row))
      return navigate('case-' + row.id, '/functional-test/case/details', { id: row.id })
  }
  function invalidate() {
    ++epoch
    for (const key of Object.keys(sequences) as Region[]) ++sequences[key]
    suite.value = null
    cases.value = []
    plans.value = []
    defects.value = []
    resources.value = []
    users.value = []
    departments.value = []
    iterations.value = []
    Object.assign(form, createVersionForm())
    Object.assign(requirementForm, createRequirementForm())
    Object.assign(loading, emptyRegions())
    Object.assign(errors, emptyRegions())
    saver.reset()
    selectedCaseIds.value = []
    activeTab.value = 'detail'
    wantedSuite.value = false
    wantedCases.value = false
    wantedAll.value = false
    transitionError.value = false
    unbindError.value = false
    navigationError.value = false
    requestedStatus.value = null
  }
  watch([physicalBusy, wantedSuite, wantedCases, wantedAll], () => {
    if (!available() || physicalBusy.value) return
    if (wantedAll.value) {
      void loadAll()
      return
    }
    if (wantedSuite.value) void loadSuite()
    if (wantedCases.value) void loadCases()
  })
  watch(
    contextKey,
    () => {
      invalidate()
      if (mounted) void loadAll()
    },
    { flush: 'sync' }
  )
  onMounted(() => {
    mounted = true
    void loadAll()
  })
  onDeactivated(() => {
    active = false
    invalidate()
  })
  onActivated(() => {
    if (active) return
    active = true
    if (mounted) void loadAll()
  })
  onBeforeUnmount(() => {
    active = false
    mounted = false
    invalidate()
  })
</script>
<style scoped>
  .mango-requirement-detail {
    display: flex;
    flex-direction: column;
    gap: var(--m-page-gap);
    min-height: 100%;
    min-width: 0;
    padding: var(--m-page-gap);
  }
  .mango-requirement-detail__header {
    gap: var(--m-page-gap);
  }
  .mango-requirement-detail__save {
    min-width: 72px;
    color: var(--m-muted);
    font-size: 12px;
  }
  .mango-requirement-detail__save.is-saved {
    color: var(--m-success);
  }
  .mango-requirement-detail__save.is-failed {
    color: var(--m-danger);
  }
  .mango-requirement-detail__workflow {
    display: flex;
    align-items: center;
    overflow-x: auto;
    padding: 10px 12px;
  }
  .mango-requirement-detail__stage {
    position: relative;
    flex: 1 0 112px;
    border: 0;
    border-bottom: 2px solid var(--m-border);
    padding: 5px 8px 9px;
    background: transparent;
    color: var(--m-muted);
    cursor: pointer;
  }
  .mango-requirement-detail__stage.is-passed {
    border-bottom-color: var(--m-success);
    color: var(--m-text-2);
  }
  .mango-requirement-detail__stage.is-current {
    border-bottom-color: var(--m-primary);
    color: var(--m-primary);
    font-weight: 600;
  }
  .mango-requirement-detail__stage:focus-visible {
    outline: 2px solid var(--m-primary);
    outline-offset: 2px;
  }
  .mango-requirement-detail__stage:disabled {
    cursor: default;
  }
  .mango-requirement-detail__fields {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    column-gap: 16px;
  }
  .mango-requirement-detail__full {
    grid-column: 1 / -1;
  }
  .mango-requirement-detail__fields :deep(.arco-picker) {
    width: 100%;
  }
  .mango-requirement-detail__section-title {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .mango-requirement-detail__options {
    display: grid;
    gap: var(--m-page-gap);
  }
  .mango-requirement-detail__options:empty {
    display: none;
  }
  .mango-requirement-detail__form-panel {
    display: block;
  }
  .mango-requirement-detail__document-text {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .mango-section-card + .mango-section-card {
    margin-top: var(--m-page-gap);
  }
</style>
