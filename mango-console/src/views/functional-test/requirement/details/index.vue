<template>
  <main class="mango-requirement-detail">
    <header class="mango-detail-toolbar mango-requirement-detail__header">
      <div class="mango-requirement-detail__identity">
        <a-space size="small">
          <a-tag color="arcoblue">{{ categoryTitle }}</a-tag>
          <strong>{{ suite.requirement_name || suite.requirement?.name || '需求详情' }}</strong>
        </a-space>
        <span class="mango-requirement-detail__meta">
          {{ suite.requirement?.requirement_key || '-' }} · V{{ suite.version_no || '-' }} ·
          {{ suite.project_product?.name || '-' }} · {{ suite.iteration_ref?.name || '-' }}
        </span>
      </div>
      <a-space>
        <span class="mango-requirement-detail__save" :class="`is-${saveState}`">{{ saveStateText }}</span>
        <a-button class="mango-back-button" size="small" @click="router.back()">返回</a-button>
        <a-button  size="small" @click="openCaseWorkspace">用例生成工作台</a-button>
        <a-button  size="small" type="primary" @click="createPlan">新建测试计划</a-button>
      </a-space>
    </header>

    <a-spin class="mango-requirement-detail__spin" :loading="initialLoading">
      <section class="mango-section-card mango-requirement-detail__workflow" aria-label="需求阶段">
        <button
          v-for="item in workflowOptions"
          :key="item.key"
          type="button"
          class="mango-requirement-detail__stage"
          :class="{ 'is-current': suite.status === item.key, 'is-passed': isPassed(item.key) }"
          :aria-current="suite.status === item.key ? 'step' : undefined"
          :disabled="transitioning"
          @click="changeStatus(item.key)"
        >
          <span>{{ item.title }}</span>
        </button>
      </section>

      <section class="mango-detail-workbench">
        <a-tabs v-model:active-key="activeTab" class="mango-tabs-nav-only">
          <a-tab-pane key="detail" title="详细信息">
            <section class="mango-section-card">
              <div class="mango-section-title">基本信息</div>
              <a-form :model="form" :disabled="false" layout="vertical" class="mango-requirement-detail__form">
                <a-grid :cols="4" :col-gap="12" :row-gap="2">
                  <a-grid-item :span="2"><a-form-item label="需求概要"><a-input v-model="form.requirement_name" @blur="saveSuiteField('requirement_name')" /></a-form-item></a-grid-item>
                  <a-grid-item><a-form-item label="需求分类"><a-select v-model="requirementForm.requirement_category" :options="requirementCategoryOptions" :field-names="fieldNames" @change="saveRequirement" /></a-form-item></a-grid-item>
                  <a-grid-item><a-form-item label="问题类型"><a-select v-model="requirementForm.issue_type" :options="issueTypeOptions" :field-names="fieldNames" @change="saveRequirement" /></a-form-item></a-grid-item>
                  <a-grid-item><a-form-item label="PM"><a-select v-model="requirementForm.owner" :options="userOptions" :field-names="fieldNames" allow-search @change="saveRequirement" /></a-form-item></a-grid-item>
                  <a-grid-item><a-form-item label="开发负责人"><a-select v-model="form.development_owner" :options="userOptions" :field-names="fieldNames" allow-search allow-clear @change="saveSuiteField('development_owner')" /></a-form-item></a-grid-item>
                  <a-grid-item><a-form-item label="QA owner"><a-select v-model="form.owner" :options="userOptions" :field-names="fieldNames" allow-search @change="saveSuiteField('owner')" /></a-form-item></a-grid-item>
                  <a-grid-item><a-form-item label="Team"><a-select v-model="form.delivery_team" :options="departmentOptions" :field-names="departmentFieldNames" allow-search allow-clear @change="saveSuiteField('delivery_team')" /></a-form-item></a-grid-item>
                  <a-grid-item><a-form-item label="所属 Sprint" required><a-select v-model="form.iteration_ref" :options="iterationOptions" allow-search :loading="iterationLoading" placeholder="请选择 Sprint" @change="saveSuiteField('iteration_ref')" /></a-form-item></a-grid-item>
                  <a-grid-item :span="4"><a-form-item label="描述"><a-textarea v-model="form.description" :auto-size="{ minRows: 2, maxRows: 6 }" @blur="saveSuiteField('description')" /></a-form-item></a-grid-item>
                  <a-grid-item><a-form-item label="需要测试"><a-switch v-model="form.test_required" size="small" @change="saveSuiteField('test_required')" /></a-form-item></a-grid-item>
                  <a-grid-item><a-form-item label="建议自动化"><a-switch v-model="form.automation_recommended" size="small" @change="saveSuiteField('automation_recommended')" /></a-form-item></a-grid-item>
                  <a-grid-item><a-form-item label="效果测试"><a-switch v-model="form.effect_test_required" size="small" @change="saveSuiteField('effect_test_required')" /></a-form-item></a-grid-item>
                </a-grid>
              </a-form>
            </section>

            <section class="mango-section-card">
              <div class="mango-section-title mango-requirement-detail__section-title">
                <span>子任务 <small>{{ suite.task_metrics?.completed || 0 }}/{{ suite.task_metrics?.total || tasks.length }}</small></span>
                <a-button  size="small" type="primary" @click="addTask">新增子任务</a-button>
              </div>
              <a-table :data="tasks" :columns="taskColumns" :pagination="false" :loading="!initialLoading && taskLoading" :scroll="{ x: 1480 }" row-key="id">
                <template #task_sort="{ record }"><a-input-number v-model="record.sort_order" :disabled="false" size="mini" :min="0" @change="saveTask(record)" /></template>
                <template #task_name="{ record }"><a-input v-model="record.name" :disabled="false" size="small" @blur="saveTask(record)" /></template>
                <template #task_type="{ record }"><a-select v-model="record.task_type" :disabled="false" size="small" :options="taskTypeOptions" :field-names="fieldNames" @change="saveTask(record)" /></template>
                <template #task_status="{ record }"><a-select v-model="record.status" :disabled="false" size="small" :options="taskStatusOptions" :field-names="fieldNames" @change="saveTask(record)" /></template>
                <template #task_owner="{ record }"><a-select v-model="record.owner_id" :disabled="false" size="small" :options="userOptions" :field-names="fieldNames" allow-search allow-clear @change="saveTask(record)" /></template>
                <template #task_start="{ record }"><a-date-picker v-model="record.planned_start_date" :disabled="false" size="small" value-format="YYYY-MM-DD" @change="saveTask(record)" /></template>
                <template #task_end="{ record }"><a-date-picker v-model="record.planned_end_date" :disabled="false" size="small" value-format="YYYY-MM-DD" @change="saveTask(record)" /></template>
                <template #task_estimated="{ record }"><a-input-number v-model="record.estimated_person_days" :disabled="false" size="small" :min="0" :precision="2" @change="saveTask(record)" /></template>
                <template #task_actual="{ record }"><a-input-number v-model="record.actual_person_days" :disabled="false" size="small" :min="0" :precision="2" @change="saveTask(record)" /></template>
                <template #task_self_test="{ record }"><a-select v-model="record.self_test_status" :disabled="false" size="small" :options="selfTestOptions" :field-names="fieldNames" @change="saveTask(record)" /></template>
                <template #task_operations="{ record }"><MangoTableActions :actions="[{ label: '删除', danger: true, onClick: () => removeTask(record) }]" /></template>
              </a-table>
            </section>

            <section class="mango-section-card">
              <div class="mango-section-title">排期与发布</div>
              <a-form :model="form" :disabled="false" layout="vertical" class="mango-requirement-detail__form">
                <a-grid :cols="4" :col-gap="12">
                  <a-grid-item v-for="field in dateFields" :key="field.key"><a-form-item :label="field.title"><a-date-picker v-model="form[field.key]" value-format="YYYY-MM-DD" @change="saveSuiteField(field.key)" /></a-form-item></a-grid-item>
                  <a-grid-item><a-form-item label="关联客户"><a-input v-model="form.customer_ref" @blur="saveSuiteField('customer_ref')" /></a-form-item></a-grid-item>
                </a-grid>
              </a-form>
            </section>
          </a-tab-pane>

          <a-tab-pane key="cases" :title="`用例（${cases.length}）`">
            <section class="mango-section-card">
              <div class="mango-section-title mango-requirement-detail__section-title">
                <span>关联用例</span>
                <a-space><a-button  size="small" @click="openCaseWorkspace">生成用例</a-button><a-button  size="small" type="primary" @click="openCasePicker">从用例库关联</a-button></a-space>
              </div>
              <a-table :data="cases" :columns="caseColumns" :pagination="false" :loading="!initialLoading && assetLoading" :scroll="{ x: 1040 }" row-key="id" :row-selection="{ type: 'checkbox', showCheckedAll: true }" @selection-change="selectedCaseIds = $event">
                <template #case_no="{ record }"><a-link  @click="openCase(record)">{{ record.case_no }}</a-link></template>
                <template #case_priority="{ record }">{{ enumTitle(priorityOptions, record.priority) }}</template>
                <template #case_operations="{ record }"><MangoTableActions :actions="[{ label: '取消关联', danger: true, onClick: () => unbindCases([record.id]) }]" /></template>
              </a-table>
            </section>
          </a-tab-pane>

          <a-tab-pane key="plans" :title="`测试计划（${plans.length}）`">
            <section class="mango-section-card"><a-table :data="plans" :columns="planColumns" :pagination="false" :loading="!initialLoading && assetLoading" :scroll="{ x: 900 }" row-key="id">
              <template #plan_name="{ record }"><a-link  @click="openPlan(record)">{{ record.name }}</a-link></template>
              <template #plan_status="{ record }"><a-tag>{{ enumTitle(planStatusOptions, record.status) }}</a-tag></template>
              <template #plan_progress="{ record }">{{ formatRate(record.execution_stats?.progress) }}</template>
              <template #plan_pass_rate="{ record }">{{ formatRate(record.execution_stats?.pass_rate) }}</template>
            </a-table></section>
          </a-tab-pane>

          <a-tab-pane key="defects" :title="`缺陷（${defects.length}）`">
            <section class="mango-section-card"><div class="mango-section-title mango-requirement-detail__section-title"><span>需求缺陷</span><a-button  size="small" type="primary" @click="createDefect">新增缺陷</a-button></div>
              <a-table :data="defects" :columns="defectColumns" :pagination="false" :loading="!initialLoading && assetLoading" :scroll="{ x: 980 }" row-key="id">
                <template #defect_status="{ record }"><a-tag>{{ enumTitle(defectStatusOptions, record.status) }}</a-tag></template>
                <template #defect_severity="{ record }">{{ enumTitle(defectSeverityOptions, record.severity) }}</template>
              </a-table>
            </section>
          </a-tab-pane>

          <a-tab-pane key="resources" :title="`相关文档（${resources.length}）`">
            <section class="mango-section-card"><a-list :data="resources" :loading="!initialLoading && assetLoading">
              <template #item="{ item }"><a-list-item><a-list-item-meta :title="item.title || item.context_key" :description="item.content || item.file_name || '-'" /><template #extra>{{ item.update_time }}</template></a-list-item></template>
            </a-list></section>
          </a-tab-pane>
        </a-tabs>
      </section>
    </a-spin>

    <a-modal v-model:visible="casePickerVisible" title="从用例库关联用例" width="760px" :ok-loading="bindingCases" :ok-button-props="{ disabled: false }" @ok="bindCases">
      <a-table :data="caseCandidates" :columns="casePickerColumns" :loading="casePickerLoading" :pagination="false" :scroll="{ x: 680, y: 460 }" row-key="id" :row-selection="{ type: 'checkbox', showCheckedAll: true }" @selection-change="candidateCaseIds = $event" />
    </a-modal>
  </main>
</template>

<script lang="ts" setup>
  import { computed, onMounted, reactive, ref } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import { useRoute, useRouter } from 'vue-router'

  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import { useEnum } from '@/store/modules/get-enum'
  import { getUserName } from '@/api/user/user'
  import { getUserDepartment } from '@/api/user/department'
  import {
    bindFunctionalRequirementCases, deleteFunctionalRequirementTask, getFunctionalContextResource,
    getFunctionalIterations,
    getFunctionalRequirementCases, getFunctionalRequirementTasks, getManualCase, getManualSuite,
    getRelatedFunctionalDefects, getRelatedFunctionalPlans, postFunctionalRequirementTask,
    putFunctionalRequirement, putFunctionalRequirementTask, putManualSuite,
    transitionManualSuiteStatus, unbindFunctionalRequirementCases,
  } from '@/api/functional-test'
  import {
    defectColumns, issueTypeOptions, planColumns, requirementCategoryOptions, selfTestOptions,
    taskColumns, taskStatusOptions, taskTypeOptions,
  } from './config'

  const route = useRoute()
  const router = useRouter()

  const enumStore = useEnum()
  const suiteId = computed(() => Number(route.query.id))
  const suite = reactive<any>({})
  const form = reactive<any>({})
  const requirementForm = reactive<any>({})
  const tasks = ref<any[]>([])
  const cases = ref<any[]>([])
  const plans = ref<any[]>([])
  const defects = ref<any[]>([])
  const resources = ref<any[]>([])
  const userOptions = ref<any[]>([])
  const departmentOptions = ref<any[]>([])
  const iterationOptions = ref<any[]>([])
  const iterationLoading = ref(false)
  const initialLoading = ref(false)
  const taskLoading = ref(false)
  const assetLoading = ref(false)
  const transitioning = ref(false)
  const activeTab = ref('detail')
  const saveState = ref<'idle' | 'pending' | 'saving' | 'saved' | 'failed'>('idle')
  const casePickerVisible = ref(false)
  const casePickerLoading = ref(false)
  const bindingCases = ref(false)
  const caseCandidates = ref<any[]>([])
  const candidateCaseIds = ref<number[]>([])
  const selectedCaseIds = ref<number[]>([])
  const fieldNames = { value: 'key', label: 'title' }
  const departmentFieldNames = { value: 'id', label: 'name' }
  const workflowOptions = [
    { key: 1, title: '需求池' }, { key: 2, title: '需求就绪' }, { key: 8, title: '待开发' },
    { key: 3, title: '开发中' }, { key: 4, title: '待提测' }, { key: 5, title: '测试中' },
    { key: 6, title: 'PM验收' }, { key: 9, title: '待发布' }, { key: 10, title: '已发布' },
  ]
  const dateFields = [
    { key: 'planned_start_date', title: '计划开始' }, { key: 'planned_submit_date', title: '计划提测' },
    { key: 'planned_release_date', title: '计划上线' }, { key: 'customer_deadline_date', title: 'DDL（客户要求上线）' },
    { key: 'committed_release_date', title: '承诺上线' },
  ]
  const caseColumns = [
    { title: '用例编号', dataIndex: 'case_no', slotName: 'case_no', width: 140 },
    { title: '用例标题', dataIndex: 'title', width: 360, ellipsis: true, tooltip: true },
    { title: '优先级', dataIndex: 'priority', slotName: 'case_priority', width: 100, align: 'center' },
    { title: '负责人', dataIndex: 'owner.name', width: 140 },
    { title: '操作', dataIndex: 'operations', slotName: 'case_operations', width: 160, fixed: 'right', align: 'center' },
  ]
  const casePickerColumns = caseColumns.filter((item) => item.dataIndex !== 'operations').map((item) => ({ ...item, slotName: undefined }))
  const priorityOptions = computed(() => (enumStore as any).case_level || [])
  const planStatusOptions = computed(() => (enumStore as any).functional_test_plan_status || [])
  const defectStatusOptions = computed(() => (enumStore as any).functional_test_defect_status || [])
  const defectSeverityOptions = computed(() => (enumStore as any).functional_test_defect_severity || [])
  const categoryTitle = computed(() => enumTitle(requirementCategoryOptions, requirementForm.requirement_category))
  const saveStateText = computed(() => ({ idle: '', pending: '待保存', saving: '正在保存…', saved: '已保存', failed: '保存失败' }[saveState.value]))
  const workflowIndex = computed(() => workflowOptions.findIndex((item) => item.key === suite.status))
  const enumTitle = (options: any[] = [], value: any) => options.find((item) => item.key === value)?.title || '-'
  const formatRate = (value: any) => `${Number(value || 0).toFixed(0)}%`
  const isPassed = (status: number) => workflowOptions.findIndex((item) => item.key === status) < workflowIndex.value

  function normalizeSuite(item: any) {
    Object.assign(suite, item || {})
    Object.assign(form, item || {}, {
      owner: item?.owner?.id, development_owner: item?.development_owner?.id,
      delivery_team: item?.delivery_team?.id,
      iteration_ref: item?.iteration_ref?.id || item?.iteration_ref,
    })
    Object.assign(requirementForm, item?.requirement || {}, { owner: item?.requirement?.owner?.id })
  }
  async function loadSuite() {
    const res = await getManualSuite({ id: suiteId.value })
    normalizeSuite((res.data || [])[0] || {})
    await loadIterations()
  }
  async function loadIterations() {
    const projectProductId = suite.project_product?.id || suite.project_product
    iterationOptions.value = []
    if (!projectProductId) return
    iterationLoading.value = true
    try {
      const res = await getFunctionalIterations({ project_product: projectProductId, page: 1, pageSize: 500 })
      iterationOptions.value = (res.data || []).map((item: any) => ({
        label: `${item.iteration_no} ${item.name}`,
        value: item.id,
      }))
    } finally {
      iterationLoading.value = false
    }
  }
  async function loadTasks() {
    taskLoading.value = true
    try {
      const res = await getFunctionalRequirementTasks(suiteId.value)
      tasks.value = (res.data || []).map((item: any) => ({ ...item, owner_id: item.owner?.id }))
    } finally { taskLoading.value = false }
  }
  async function loadAssets() {
    assetLoading.value = true
    try {
      const [caseRes, planRes, defectRes, resourceRes] = await Promise.all([
        getFunctionalRequirementCases(suiteId.value),
        getRelatedFunctionalPlans({ requirement_version_id: suiteId.value }),
        getRelatedFunctionalDefects({ requirement_version_id: suiteId.value }),
        getFunctionalContextResource({ suite: suiteId.value, page: 1, pageSize: 200 }),
      ])
      cases.value = caseRes.data || []; plans.value = planRes.data || []; defects.value = defectRes.data || []; resources.value = resourceRes.data || []
    } finally { assetLoading.value = false }
  }
  async function loadAll() {
    if (!suiteId.value) return
    initialLoading.value = true
    try { await Promise.all([loadSuite(), loadTasks(), loadAssets()]) } finally { initialLoading.value = false }
  }
  async function withSave(action: () => Promise<any>) {
    saveState.value = 'saving'
    try { const result = await action(); saveState.value = 'saved'; return result } catch (error) { saveState.value = 'failed'; throw error }
  }
  async function saveSuiteField(field: string) {

    saveState.value = 'pending'
    const res = await withSave(() => putManualSuite({ id: suiteId.value, [field]: form[field] }))
    if (field === 'iteration_ref') {
      await loadSuite()
      return
    }
    const returned = res.data || {}
    if (returned.update_time) suite.update_time = returned.update_time
  }
  async function saveRequirement() {

    if (!requirementForm.id) return
    await withSave(() => putFunctionalRequirement({ id: requirementForm.id, owner: requirementForm.owner, issue_type: requirementForm.issue_type, requirement_category: requirementForm.requirement_category }))
  }
  async function saveTask(record: any) {

    saveState.value = 'pending'
    const payload = { ...record, owner: record.owner_id, requirement_version: suiteId.value }
    const res = await withSave(() => record.id ? putFunctionalRequirementTask(payload) : postFunctionalRequirementTask(payload))
    Object.assign(record, res.data || {}, { owner_id: res.data?.owner?.id })
    const completed = tasks.value.filter((item) => item.status === 2).length
    suite.task_metrics = { ...(suite.task_metrics || {}), total: tasks.value.length, completed }
  }
  function addTask() { if (true) tasks.value.push({ name: '新建子任务', task_type: 8, status: 0, self_test_status: 0, sort_order: tasks.value.length + 1 }) }
  function removeTask(record: any) {

    if (!record.id) { tasks.value = tasks.value.filter((item) => item !== record); return }
    Modal.warning({ title: '确认删除子任务', content: `确定删除「${record.name}」吗？`, hideCancel: false, onBeforeOk: async () => { if (false) return false; await deleteFunctionalRequirementTask(record.id); await Promise.all([loadTasks(), loadSuite()]); Message.success('已删除') } })
  }
  async function changeStatus(status: number) {

    if (status === suite.status) return
    if (!suite.iteration_ref?.id && !suite.iteration_ref) {
      Message.warning('请先绑定迭代')
      return
    }
    transitioning.value = true
    try { const res = await transitionManualSuiteStatus({ id: suiteId.value, status, expected_update_time: suite.update_time }); normalizeSuite(res.data?.suite || res.data); Message.success('需求状态已更新') } finally { transitioning.value = false }
  }
  async function openCasePicker() {

    casePickerVisible.value = true; casePickerLoading.value = true; candidateCaseIds.value = []
    try { const res = await getManualCase({ project_product: suite.project_product?.id, page: 1, pageSize: 500 }); const bound = new Set(cases.value.map((item) => item.id)); caseCandidates.value = (res.data || []).filter((item: any) => !bound.has(item.id)) } finally { casePickerLoading.value = false }
  }
  async function bindCases() { if (false) return; bindingCases.value = true; try { await bindFunctionalRequirementCases(suiteId.value, candidateCaseIds.value); casePickerVisible.value = false; await Promise.all([loadAssets(), loadSuite()]); Message.success('用例已关联') } finally { bindingCases.value = false } }
  async function unbindCases(ids: number[]) { if (false) return; await unbindFunctionalRequirementCases(suiteId.value, ids); await Promise.all([loadAssets(), loadSuite()]); Message.success('已取消关联') }
  function openCaseWorkspace() { router.push({ path: '/functional-test/suite/details', query: { id: suiteId.value } }) }
  function createPlan() { router.push({ path: '/functional-test/plan/index', query: { requirement_version: suiteId.value } }) }
  function createDefect() { router.push({ path: '/functional-test/defect/index', query: { requirement_version: suiteId.value, project_product: suite.project_product?.id, create: 1 } }) }
  function openPlan(row: any) { router.push({ path: '/functional-test/plan/details', query: { id: row.id } }) }
  function openCase(row: any) { router.push({ path: '/functional-test/case/details', query: { id: row.id } }) }

  onMounted(async () => {
    const [users, departments] = await Promise.all([getUserName(), getUserDepartment({ page: 1, pageSize: 500 })])
    userOptions.value = users.data || []; departmentOptions.value = departments.data || []
    await loadAll()
  })
</script>

<style lang="less" scoped>
  .mango-requirement-detail { display: flex; flex-direction: column; gap: var(--m-page-gap); min-height: 100%; }
  .mango-requirement-detail__header { display: flex; align-items: center; justify-content: space-between; gap: var(--m-page-gap); }
  .mango-requirement-detail__identity { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
  .mango-requirement-detail__meta { color: var(--m-muted); font-size: 12px; }
  .mango-requirement-detail__save { min-width: 72px; color: var(--m-muted); font-size: 12px; text-align: right; }
  .mango-requirement-detail__save.is-saved { color: var(--m-success); }
  .mango-requirement-detail__save.is-failed { color: var(--m-danger); }
  .mango-requirement-detail__spin { display: block; min-height: 520px; }
  .mango-requirement-detail__workflow { display: flex; align-items: center; overflow-x: auto; padding: 10px 12px; }
  .mango-requirement-detail__stage { position: relative; flex: 1 0 112px; border: 0; border-bottom: 2px solid var(--m-border); padding: 5px 8px 9px; background: transparent; color: var(--m-muted); cursor: pointer; }
  .mango-requirement-detail__stage::after { position: absolute; right: -3px; bottom: -4px; width: 6px; height: 6px; border-radius: 50%; background: var(--m-border); content: ''; }
  .mango-requirement-detail__stage.is-passed { border-bottom-color: var(--m-success); color: var(--m-text-2); }
  .mango-requirement-detail__stage.is-current { border-bottom-color: var(--m-primary); color: var(--m-primary); font-weight: 600; }
  .mango-requirement-detail__stage:focus-visible { outline: 2px solid var(--m-primary); outline-offset: 2px; }
  .mango-requirement-detail__form { padding-top: 4px; }
  .mango-requirement-detail__section-title { display: flex; align-items: center; justify-content: space-between; }
  .mango-requirement-detail__section-title small { color: var(--m-muted); font-weight: 400; }
  .mango-section-card + .mango-section-card { margin-top: var(--m-page-gap); }
  @media (prefers-reduced-motion: reduce) { .mango-requirement-detail__stage { transition: none; } }
</style>
