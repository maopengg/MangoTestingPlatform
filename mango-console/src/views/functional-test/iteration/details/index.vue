<template>
  <TableBody plain class="mango-detail-workbench-page" :sticky-horizontal-scroll="false">
    <template #header>
      <TableHeader :title="headerTitle">
        <template #header-extra>
          <a-space><a-button class="mango-back-button" size="small" @click="router.back()">返回</a-button><a-button size="small" :loading="loading" @click="loadAll">刷新</a-button></a-space>
        </template>
      </TableHeader>
    </template>
    <template #default>
      <section class="mango-iteration-detail">
        <div class="mango-iteration-detail__summary">
          <a-space wrap>
            <a-tag>{{ enumTitle(iterationStatusOptions, iteration.status) }}</a-tag>
            <span>{{ iteration.start_date || '-' }} 至 {{ iteration.end_date || '-' }}</span>
            <span>负责人：{{ iteration.owner?.name || '-' }}</span>
            <span>需求 {{ ganttData.summary?.requirement_count || suites.length }} 条</span>
            <a-tag v-if="saveState === 'saving'" color="arcoblue">正在保存…</a-tag>
            <a-tag v-else-if="saveState === 'saved'" color="green">已保存</a-tag>
            <a-tag v-else-if="saveState === 'failed'" color="red">保存失败</a-tag>
            <a-tag v-if="ganttData.summary?.overdue_count" color="red">逾期 {{ ganttData.summary.overdue_count }}</a-tag>
            <a-tag v-if="ganttData.summary?.overlap_count" color="orangered">排期重叠 {{ ganttData.summary.overlap_count }}</a-tag>
          </a-space>
        </div>
        <a-tabs v-model:active-key="activeSection" class="mango-iteration-detail__tabs">
          <a-tab-pane key="board" title="需求看板">
            <RequirementKanban
              :columns="boardColumns"
              :loading="loading"
              :priority-options="priorityOptions"
              @open="openOverview"
              @move="moveRequirement"
              @cancel="cancelRequirement"
            />
          </a-tab-pane>
          <a-tab-pane key="schedule" title="需求排期">
            <a-tabs v-model:active-key="activeView" class="mango-iteration-detail__schedule-tabs">
              <a-tab-pane key="table" title="排期表格">
            <div class="mango-iteration-detail__table">
              <a-table class="mango-native-scroll-table" :data="suites" :columns="scheduleColumns" :loading="loading" :pagination="false" :scroll="{ x: 1420, y: '100%' }" row-key="id">
                <template #requirement_key="{ record }">{{ record.requirement?.requirement_key || '-' }}</template>
                <template #priority="{ record }">{{ enumTitle(priorityOptions, record.priority) }}</template>
                <template #development_owner="{ record }">{{ record.development_owner?.name || '未分配' }}</template>
                <template #status="{ record }"><a-tag>{{ enumTitle(suiteStatusOptions, record.status) }}</a-tag></template>
                <template #owner="{ record }">{{ record.owner?.name || '-' }}</template>
                <template #actions="{ record }"><MangoTableActions :actions="[
                  { permission: 'functional.iteration:edit', label: '编辑排期', onClick: () => openSchedule(record) },
                  { permission: 'functional.suite:edit', label: '确认提测', disabled: record.status >= 4, onClick: () => confirmSubmit(record) },
                ]" /></template>
              </a-table>
            </div>
              </a-tab-pane>
              <a-tab-pane key="gantt" title="用户甘特图">
                <UserScheduleGantt :data="ganttData" :loading="loading" :status-options="suiteStatusOptions" @edit="openGanttSchedule" />
              </a-tab-pane>
            </a-tabs>
          </a-tab-pane>
          <a-tab-pane key="cases" :title="`迭代用例（${iterationCaseTotal}）`">
            <FunctionalCaseGrid
              :rows="iterationCases"
              :columns="iterationCaseColumns"
              :loading="loading"
              :editable="false"
              :selectable="false"
              :show-hint="false"
            >
              <template #summary>共 {{ iterationCaseTotal }} 条，汇总需求来源与本迭代测试计划中的全部用例</template>
            </FunctionalCaseGrid>
          </a-tab-pane>
          <a-tab-pane key="plans" :title="`测试计划（${plans.length}）`">
            <div class="mango-iteration-detail__table">
              <a-table class="mango-native-scroll-table" :data="plans" :columns="iterationPlanColumns" :loading="loading" :pagination="false" :scroll="{ x: 1140, y: '100%' }" row-key="id">
                <template #name="{ record }"><a-link @click="goPlan(record)">{{ record.name }}</a-link></template>
                <template #scope_type="{ record }">{{ enumTitle(planScopeOptions, record.scope_type) }}</template>
                <template #plan_status="{ record }"><a-tag>{{ enumTitle(planStatusOptions, record.status) }}</a-tag></template>
                <template #execution_progress="{ record }">{{ record.execution_stats?.executed || 0 }}/{{ record.execution_stats?.total || 0 }}（{{ formatRate(record.execution_stats?.progress) }}）</template>
                <template #pass_rate="{ record }">{{ formatRate(record.execution_stats?.pass_rate) }}</template>
                <template #plan_owner="{ record }">{{ record.owner?.name || '-' }}</template>
              </a-table>
            </div>
          </a-tab-pane>
          <a-tab-pane key="defects" :title="`缺陷（${defects.length}）`">
            <div class="mango-iteration-detail__table">
              <a-table class="mango-native-scroll-table" :data="defects" :columns="iterationDefectColumns" :loading="loading" :pagination="false" :scroll="{ x: 1120, y: '100%' }" row-key="id">
                <template #defect_no="{ record }"><a-link @click="goDefect(record)">{{ record.defect_no }}</a-link></template>
                <template #defect_status="{ record }"><a-tag>{{ enumTitle(defectStatusOptions, record.status) }}</a-tag></template>
                <template #severity="{ record }">{{ enumTitle(defectSeverityOptions, record.severity) }}</template>
                <template #defect_priority="{ record }">{{ enumTitle(defectPriorityOptions, record.priority) }}</template>
                <template #assignee="{ record }">{{ record.assignee?.name || '未分配' }}</template>
              </a-table>
            </div>
          </a-tab-pane>
        </a-tabs>
      </section>
    </template>
  </TableBody>

  <a-modal v-model:visible="scheduleVisible" title="编辑需求排期" width="720px" :ok-loading="saving" @ok="saveSchedule">
    <a-form :model="scheduleForm" layout="vertical">
      <a-alert type="info">{{ scheduleForm.requirement_name }} · V{{ scheduleForm.version_no }}</a-alert>
      <a-grid :cols="2" :col-gap="16" class="mango-iteration-detail__form-grid">
        <a-grid-item><a-form-item label="开发负责人"><a-select v-model="scheduleForm.development_owner" :options="userOptions" :field-names="fieldNames" allow-search allow-clear /></a-form-item></a-grid-item>
        <a-grid-item><a-form-item label="优先级"><a-select v-model="scheduleForm.priority" :options="priorityOptions" :field-names="fieldNames" /></a-form-item></a-grid-item>
        <a-grid-item><a-form-item label="计划开始"><a-date-picker v-model="scheduleForm.planned_start_date" value-format="YYYY-MM-DD" /></a-form-item></a-grid-item>
        <a-grid-item><a-form-item label="计划提测"><a-date-picker v-model="scheduleForm.planned_submit_date" value-format="YYYY-MM-DD" /></a-form-item></a-grid-item>
        <a-grid-item><a-form-item label="交付状态"><a-select v-model="scheduleForm.status" :options="suiteStatusOptions" :field-names="fieldNames" /></a-form-item></a-grid-item>
      </a-grid>
    </a-form>
  </a-modal>

  <RequirementOverviewDrawer
    v-model:visible="overviewVisible"
    :suite-id="overviewSuiteId"
    :status-options="suiteStatusOptions"
    @edit-schedule="openSchedule"
    @changed="loadAll"
  />
</template>

<script lang="ts" setup>
  import { computed, onMounted, reactive, ref } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import { useRoute, useRouter } from 'vue-router'
  import TableBody from '@/components/table/TableBody.vue'
  import TableHeader from '@/components/table/TableHeader.vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import FunctionalCaseGrid from '@/components/table/FunctionalCaseGrid.vue'
  import type { FunctionalGridColumn } from '@/components/table/functional-case-grid'
  import { useEnum } from '@/store/modules/get-enum'
  import { getUserName } from '@/api/user/user'
  import { formatModulePath, formatProjectProductPath } from '@/utils/business-format'
  import {
    confirmManualSuiteSubmit, getFunctionalIterationDetail, getFunctionalIterationGantt,
    getFunctionalIterationBoard, getFunctionalIterationCases, getManualSuite,
    getRelatedFunctionalDefects, getRelatedFunctionalPlans, putManualSuite,
    transitionManualSuiteStatus,
  } from '@/api/functional-test'
  import UserScheduleGantt from '../components/UserScheduleGantt.vue'
  import RequirementKanban from '../components/RequirementKanban.vue'
  import RequirementOverviewDrawer from '../components/RequirementOverviewDrawer.vue'
  import { createCaseLibraryColumns, formatAutomationBindings } from '../../case-library/config'
  import { iterationDefectColumns, iterationPlanColumns, scheduleColumns } from './config'

  const route = useRoute()
  const router = useRouter()
  const enumStore = useEnum()
  const fieldNames = { value: 'key', label: 'title' }
  const iterationId = computed(() => Number(route.query.id))
  const iteration = reactive<any>({})
  const ganttData = reactive<any>({ summary: {}, groups: [] })
  const suites = ref<any[]>([])
  const plans = ref<any[]>([])
  const defects = ref<any[]>([])
  const boardColumns = ref<any[]>([])
  const iterationCases = ref<any[]>([])
  const iterationCaseTotal = ref(0)
  const iterationCaseColumns = ref<FunctionalGridColumn[]>([])
  const userOptions = ref<any[]>([])
  const activeView = ref('table')
  const activeSection = ref('board')
  const loading = ref(false)
  const saving = ref(false)
  const scheduleVisible = ref(false)
  const overviewVisible = ref(false)
  const overviewSuiteId = ref<number>()
  const saveState = ref<'idle' | 'saving' | 'saved' | 'failed'>('idle')
  const scheduleForm = reactive<any>({})
  const iterationStatusOptions = computed(() => (enumStore as any).functional_test_iteration_status || [])
  const suiteStatusOptions = computed(() => (enumStore as any).manual_test_suite_status || [])
  const priorityOptions = computed(() => (enumStore as any).case_level || [])
  const planScopeOptions = computed(() => (enumStore as any).functional_test_plan_scope_type || [])
  const planStatusOptions = computed(() => (enumStore as any).functional_test_plan_status || [])
  const defectStatusOptions = computed(() => (enumStore as any).functional_test_defect_status || [])
  const defectSeverityOptions = computed(() => (enumStore as any).functional_test_defect_severity || [])
  const defectPriorityOptions = computed(() => (enumStore as any).functional_test_defect_priority || [])
  const headerTitle = computed(() => `研发协同 / 迭代管理 / ${iteration.name || '迭代详情'}`)
  const enumTitle = (options: any[], value: any) => options.find((item) => item.key === value)?.title || '-'
  const formatRate = (value: any) => `${Number(value || 0).toFixed(2).replace(/\.00$/, '')}%`

  async function loadAll() {
    if (!iterationId.value) return
    loading.value = true
    try {
      const [detailRes, suitesRes, ganttRes, plansRes, defectsRes, boardRes, casesRes] = await Promise.all([
        getFunctionalIterationDetail(iterationId.value),
        getManualSuite({ iteration_ref: iterationId.value }),
        getFunctionalIterationGantt({ iteration_id: iterationId.value }),
        getRelatedFunctionalPlans({ iteration_id: iterationId.value }),
        getRelatedFunctionalDefects({ iteration_id: iterationId.value }),
        getFunctionalIterationBoard(iterationId.value),
        getFunctionalIterationCases({ iteration_id: iterationId.value, page: 1, pageSize: 500 }),
      ])
      Object.assign(iteration, detailRes.data || {})
      suites.value = (suitesRes.data || []).map((item: any) => ({
        ...item,
        requirement_name: item.requirement_name || item.requirement?.name || '未命名需求',
      }))
      Object.assign(ganttData, ganttRes.data || { summary: {}, groups: [] })
      plans.value = plansRes.data || []
      defects.value = defectsRes.data || []
      boardColumns.value = boardRes.data?.columns || []
      iterationCases.value = (casesRes.data || []).map((record: any) => ({
        ...record,
        project_product_id: record.project_product?.id || record.project_product_id,
        project_product_path: formatProjectProductPath(record.project_product),
        module_id: record.module?.id || record.module_id,
        module_path: formatModulePath(record.module),
        owner_id: record.owner?.id || record.owner_id,
        automation_bindings: formatAutomationBindings(record.bindings),
        source_requirement: record.suite
          ? `${record.suite.requirement?.requirement_key || 'REQ'} · ${record.suite.requirement_name || record.suite.requirement?.name || '-'} V${record.suite.version_no || '-'}`
          : '-',
      }))
      iterationCaseTotal.value = casesRes.totalSize || iterationCases.value.length
    } finally { loading.value = false }
  }
  function openSchedule(row: any) {
    Object.assign(scheduleForm, {
      id: row.suite_id || row.id,
      requirement_name: row.requirement_name,
      version_no: row.version_no,
      iteration_ref: iterationId.value,
      development_owner: row.development_owner?.id,
      priority: row.priority,
      planned_start_date: row.planned_start_date,
      planned_submit_date: row.planned_submit_date,
      status: row.status,
    })
    scheduleVisible.value = true
  }
  function openOverview(row: any) {
    overviewSuiteId.value = row.id
    overviewVisible.value = true
  }
  function moveRequirement(payload: { item: any; status: number }) {
    if (payload.status === 6) {
      Modal.confirm({
        title: '确认测试完成',
        content: '系统将检查执行中计划，并提示未执行用例和未关闭缺陷。确定继续吗？',
        hideCancel: false,
        onBeforeOk: () => persistRequirementMove(payload),
      })
      return
    }
    persistRequirementMove(payload)
  }
  function cancelRequirement(item: any) {
    Modal.warning({
      title: '确认取消需求',
      content: `取消后需求将从当前看板中隐藏，但不会删除业务数据。确定取消「${item.requirement_name || item.requirement?.name || item.id}」吗？`,
      hideCancel: false,
      onBeforeOk: () => persistRequirementMove({ item, status: 7 }),
    })
  }
  async function persistRequirementMove(payload: { item: any; status: number }) {
    const { item, status } = payload
    const previous = item.status
    item.status = status
    boardColumns.value = boardColumns.value.map((column: any) => ({
      ...column,
      items: boardColumns.value.flatMap((current: any) => current.items).filter((row: any) => row.status === column.status),
    }))
    saveState.value = 'saving'
    try {
      const response = await transitionManualSuiteStatus({
        id: item.id,
        status,
        expected_update_time: item.update_time,
      })
      const saved = response.data?.suite
      if (saved) Object.assign(item, saved)
      saveState.value = 'saved'
      const warnings = response.data?.warnings || []
      if (warnings.length) Message.warning(warnings.join('；'))
      else Message.success('需求状态已更新')
      await loadAll()
      return true
    } catch (error) {
      item.status = previous
      saveState.value = 'failed'
      await loadAll()
      return false
    }
  }
  function openGanttSchedule(item: any) {
    const row = suites.value.find((suite: any) => suite.id === item.id)
    if (row) openSchedule(row)
  }
  async function saveSchedule() {
    saving.value = true
    saveState.value = 'saving'
    try {
      await putManualSuite({ ...scheduleForm })
      const [suiteRes, ganttRes] = await Promise.all([
        getManualSuite({ id: scheduleForm.id }),
        getFunctionalIterationGantt({ iteration_id: iterationId.value }),
      ])
      const saved = (suiteRes.data || [])[0]
      const index = suites.value.findIndex((item: any) => item.id === scheduleForm.id)
      if (saved && index >= 0) suites.value[index] = saved
      Object.assign(ganttData, ganttRes.data || { summary: {}, groups: [] })
      scheduleVisible.value = false
      saveState.value = 'saved'
      Message.success('排期已保存')
      return true
    } catch (error) {
      saveState.value = 'failed'
      throw error
    } finally { saving.value = false }
  }
  async function confirmSubmit(row: any) {
    saving.value = true
    try {
      await confirmManualSuiteSubmit(row.id)
      const [suiteRes, ganttRes] = await Promise.all([
        getManualSuite({ id: row.id }),
        getFunctionalIterationGantt({ iteration_id: iterationId.value }),
      ])
      const saved = (suiteRes.data || [])[0]
      const index = suites.value.findIndex((item: any) => item.id === row.id)
      if (saved && index >= 0) suites.value[index] = saved
      Object.assign(ganttData, ganttRes.data || { summary: {}, groups: [] })
      Message.success('已确认提测')
    } finally { saving.value = false }
  }
  function goPlan(row: any) { router.push({ path: '/functional-test/plan/details', query: { id: row.id } }) }
  function goDefect(row: any) { router.push({ path: '/functional-test/defect/index', query: { defect_id: row.id } }) }
  onMounted(async () => {
    await enumStore.getEnum()
    userOptions.value = (await getUserName()).data || []
    const baseColumns = createCaseLibraryColumns(enumStore, userOptions.value)
    const relationColumns = baseColumns.filter((item) => ['project_product_id', 'module_id'].includes(item.field))
    iterationCaseColumns.value = [
      ...baseColumns.filter((item) => !['project_product_id', 'module_id'].includes(item.field)),
      { field: 'source_requirement', title: '来源需求', width: 260, editable: false },
      { field: 'iteration_plan_count', title: '关联计划数', width: 100, editable: false },
      {
        field: 'iteration_recent_result', title: '最近结果', width: 100, editable: false,
        options: (enumStore.functional_test_result || []).map((item: any) => ({
          label: item.title,
          value: item.key,
          colorToken: item.key === 1 ? '--m-success' : item.key === 2 ? '--m-danger' : '--m-muted',
        })),
      },
      { field: 'iteration_open_defect_count', title: '未关闭缺陷', width: 100, editable: false },
      ...relationColumns,
    ]
    await loadAll()
  })
</script>

<style lang="less" scoped>
  .mango-iteration-detail { display: flex; height: 100%; min-height: 0; flex-direction: column; gap: var(--m-page-gap); padding-top: var(--m-page-gap); }
  .mango-iteration-detail__summary { padding: 8px 12px; border: 1px solid var(--m-border); border-radius: var(--m-radius-md); background: var(--m-surface); color: var(--m-text-2); }
  .mango-iteration-detail__tabs { display: flex; flex: 1; min-height: 0; flex-direction: column; border: 1px solid var(--m-border); border-radius: var(--m-radius-md); background: var(--m-surface); }
  .mango-iteration-detail__tabs :deep(.arco-tabs-content), .mango-iteration-detail__tabs :deep(.arco-tabs-content-list), .mango-iteration-detail__tabs :deep(.arco-tabs-pane) { height: 100%; min-height: 0; }
  .mango-iteration-detail__tabs :deep(.arco-tabs-content) { flex: 1; min-height: 0; padding: 0; }
  .mango-iteration-detail__schedule-tabs { display: flex; height: 100%; min-height: 0; flex-direction: column; }
  .mango-iteration-detail__schedule-tabs :deep(.arco-tabs-content), .mango-iteration-detail__schedule-tabs :deep(.arco-tabs-content-list), .mango-iteration-detail__schedule-tabs :deep(.arco-tabs-pane) { height: 100%; min-height: 0; }
  .mango-iteration-detail__schedule-tabs :deep(.arco-tabs-content) { flex: 1; min-height: 0; padding: 0; }
  .mango-iteration-detail__table { display: flex; height: 100%; min-height: 0; flex-direction: column; overflow: hidden; }
  .mango-iteration-detail__form-grid { margin-top: 12px; }
</style>
