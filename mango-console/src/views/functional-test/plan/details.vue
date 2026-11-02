<template>
  <TableBody plain class="mango-detail-workbench-page">
    <template #header>
      <TableHeader :title="`研发协同 / 测试计划 / ${plan.name || '详情'}`">
        <template #header-extra>
          <a-space>
            <a-button class="mango-back-button" size="small" @click="router.back()">返回</a-button>
            <a-button size="small" :loading="loading" @click="loadDetail">刷新</a-button>
            <a-button
              size="small"
              :disabled="plan.status >= 2"
              @click="openCasePicker"
            >从用例库选用例</a-button>
            <a-button
              v-if="plan.status === 0 || plan.status === 1"
              size="small"
              type="primary"
              :loading="actionLoading"
              :disabled="!plan.cases?.length"
              @click="openStartPlan"
            >开始执行</a-button>
            <a-button
              v-if="plan.status === 2"
              size="small"
              type="primary"
              status="success"
              :loading="actionLoading"
              @click="finishPlan"
            >完成计划</a-button>
          </a-space>
        </template>
      </TableHeader>
    </template>
    <template #default>
      <div class="mango-plan-detail__workbench">
        <div class="mango-plan-detail__meta">
          <a-tag>{{ enumTitle(enumStore.functional_test_plan_status, plan.status) }}</a-tag>
          <span>{{ enumTitle(enumStore.functional_test_plan_scope_type, plan.scope_type) }}</span>
          <span>{{ scopeLabel }}</span>
          <span v-if="plan.environment">环境 {{ plan.environment }}</span>
          <span v-if="plan.build_version">构建 {{ plan.build_version }}</span>
          <span>进度 {{ plan.execution_stats?.executed || 0 }}/{{ plan.execution_stats?.total || 0 }}</span>
          <span>通过率 {{ formatRate(plan.execution_stats?.pass_rate) }}</span>
          <span>缺陷 {{ plan.defect_count || 0 }}（未关闭 {{ plan.open_defect_count || 0 }}）</span>
          <span v-if="plan.started_at">开始 {{ plan.started_at }}</span>
          <span v-if="plan.finished_at">完成 {{ plan.finished_at }}</span>
        </div>
        <FunctionalCaseGrid
          class="mango-plan-detail__grid"
          :rows="plan.cases || []"
          :columns="columns"
          :loading="loading"
          :editable="plan.status < 3"
          :show-hint="false"
          @cell-change="savePlanCase"
          @selection-change="selectedPlanCases = $event"
        >
          <template #summary>
            <span>已选择 {{ selectedPlanCases.length }} 条　共 {{ plan.cases?.length || 0 }} 条</span>
            <a-tag v-if="caseSaving" size="small" color="arcoblue">正在保存…</a-tag>
            <a-tag v-else-if="saveFailed" size="small" color="red">保存失败</a-tag>
            <a-tag v-else-if="savedOnce" size="small" color="green">已保存</a-tag>
          </template>
          <template #toolbar>
            <a-button
              v-if="plan.status < 2"
              size="small"
              status="danger"
              :disabled="!selectedPlanCases.length"
              @click="removeSelected"
            >移出计划</a-button>
            <template v-if="plan.status === 2">
              <a-button size="small" :disabled="!selectedPlanCases.length" @click="setBatchResult(1)">通过</a-button>
              <a-button size="small" status="danger" :disabled="!selectedPlanCases.length" @click="setBatchResult(2)">失败</a-button>
              <a-button size="small" status="warning" :disabled="!selectedPlanCases.length" @click="setBatchResult(3)">阻塞</a-button>
            </template>
            <a-button  size="small" :disabled="!canCreateDefect" @click="createDefect">创建缺陷</a-button>
            <a-button  size="small" :disabled="!selectedPlanCases.length" @click="openBindDefect">关联已有缺陷</a-button>
            <a-button size="small" :disabled="!selectedDefectOptions.length" @click="openUnbindDefect">取消缺陷关联</a-button>
          </template>
          <template #cell-test_steps="{ row }">{{ row.test_steps?.length || 0 }} 个步骤</template>
        </FunctionalCaseGrid>
      </div>
    </template>
  </TableBody>

  <a-drawer v-model:visible="pickerVisible" title="从用例库选择" width="900px" :footer="false">
    <div class="mango-plan-detail__picker-filter">
      <ProductModuleSelect v-model="pickerFilter.module" :project-product-id="plan.project_product?.id" :selectable-level="0" placeholder="全部模块" />
      <a-input v-model="pickerFilter.title" allow-clear placeholder="用例标题" />
      <a-input v-model="pickerFilter.category_level_1" allow-clear placeholder="分类一" />
      <a-button size="small" type="primary" @click="loadLibraryCases">查询</a-button>
    </div>
    <a-table
      v-model:selected-keys="pickerSelectedKeys"
      :row-selection="{ type: 'checkbox', showCheckedAll: true }"
      :data="libraryCases"
      :loading="pickerLoading"
      :pagination="false"
      row-key="id"
      :scroll="{ x: 1000, y: 520 }"
    >
      <template #columns>
        <a-table-column title="编号" data-index="case_no" :width="130" />
        <a-table-column title="标题" data-index="title" :width="260" />
        <a-table-column title="分类一" data-index="category_level_1" :width="140" />
        <a-table-column title="分类二" data-index="category_level_2" :width="140" />
        <a-table-column title="分类三" data-index="category_level_3" :width="140" />
        <a-table-column title="优先级" data-index="priority" :width="90" />
      </template>
    </a-table>
    <div class="mango-plan-detail__picker-footer">
      <span>已选 {{ pickerSelectedKeys.length }} 条</span>
      <a-button  type="primary" :loading="pickerSaving" @click="confirmPick">加入计划</a-button>
    </div>
  </a-drawer>

  <a-modal v-model:visible="bindVisible" title="关联已有缺陷" width="560px" :ok-loading="bindSaving" @ok="bindExistingDefect">
    <a-form :model="bindForm" layout="vertical">
      <a-form-item label="缺陷" required>
        <a-select v-model="bindForm.defect_id" :options="defectOptions" allow-search :loading="defectOptionLoading" placeholder="仅展示当前项目产品下未关闭缺陷" />
      </a-form-item>
      <a-alert type="info">将把已选的 {{ selectedPlanCases.length }} 条计划用例关联到该缺陷，不会修改执行结果。</a-alert>
    </a-form>
  </a-modal>

  <a-modal v-model:visible="unbindVisible" title="取消缺陷关联" width="560px" :ok-loading="bindSaving" @ok="unbindExistingDefect">
    <a-form :model="unbindForm" layout="vertical">
      <a-form-item label="缺陷" required><a-select v-model="unbindForm.defect_id" :options="selectedDefectOptions" /></a-form-item>
      <a-alert type="warning">仅取消所选计划用例与缺陷的关联，不会删除缺陷或修改执行结果。</a-alert>
    </a-form>
  </a-modal>

  <a-modal v-model:visible="startVisible" title="开始执行" width="560px" :ok-loading="actionLoading" @ok="startPlan">
    <a-form :model="startForm" layout="vertical">
      <a-alert type="info">开始后可以填写本次执行结果。</a-alert>
      <a-form-item v-if="plan.requirement_version" label="需求交付状态">
        <a-checkbox v-model="startForm.update_requirement_status">同时将当前需求版本更新为“测试中”</a-checkbox>
      </a-form-item>
    </a-form>
  </a-modal>
</template>

<script lang="ts" setup>
  import { computed, onMounted, reactive, ref } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import { useRoute, useRouter } from 'vue-router'
  import FunctionalCaseGrid from '@/components/table/FunctionalCaseGrid.vue'
  import TableBody from '@/components/table/TableBody.vue'
  import TableHeader from '@/components/table/TableHeader.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import { useEnum } from '@/store/modules/get-enum'
  import { getUserName } from '@/api/user/user'
  import {
    addFunctionalPlanCases, batchFunctionalPlanResult, bindFunctionalDefectCases, finishFunctionalPlan,
    getFunctionalDefectOptions,
    getFunctionalPlanDetail, getManualCase, putFunctionalPlanCase,
    removeFunctionalPlanCases, startFunctionalPlan, unbindFunctionalDefectCases,
  } from '@/api/functional-test'
  import { createPlanCaseColumns } from './config'

  const route = useRoute()
  const router = useRouter()
  const enumStore = useEnum()
  const plan = reactive<any>({ cases: [], execution_stats: {} })
  const columns = ref<any[]>([])
  const loading = ref(false)
  const actionLoading = ref(false)
  const caseSaving = ref(false)
  const savedOnce = ref(false)
  const saveFailed = ref(false)
  const selectedPlanCases = ref<any[]>([])
  const pickerVisible = ref(false)
  const bindVisible = ref(false)
  const unbindVisible = ref(false)
  const bindSaving = ref(false)
  const defectOptionLoading = ref(false)
  const defectOptions = ref<any[]>([])
  const bindForm = reactive<any>({ defect_id: undefined })
  const unbindForm = reactive<any>({ defect_id: undefined })
  const startVisible = ref(false)
  const startForm = reactive({ update_requirement_status: true })
  const pickerLoading = ref(false)
  const pickerSaving = ref(false)
  const pickerSelectedKeys = ref<(string | number)[]>([])
  const libraryCases = ref<any[]>([])
  const pickerFilter = reactive<any>({ module: undefined, title: '', category_level_1: '' })
  const planId = Number(route.query.id)
  const enumTitle = (options: any[], value: any) => options.find((item) => item.key === value)?.title || '-'
  const formatRate = (value: any) => `${Number(value || 0).toFixed(2).replace(/\.00$/, '')}%`
  const scopeLabel = computed(() => {
    if (plan.scope_type === 0) {
      const version = plan.requirement_version
      return version ? `${version.requirement_name || version.requirement?.name || '需求'} · V${version.version_no || '-'}` : '未选择需求版本'
    }
    if (plan.scope_type === 1) return plan.iteration?.name || '未选择 Sprint'
    return plan.scope_ref || '未填写范围标识'
  })
  const canCreateDefect = computed(() => selectedPlanCases.value.length > 0
    && selectedPlanCases.value.every((item: any) => [2, 3].includes(Number(item.result))))
  const selectedDefectOptions = computed(() => {
    const options = new Map<number, string>()
    selectedPlanCases.value.forEach((item: any) => (item.defects || []).forEach((defect: any) => {
      options.set(defect.id, `${defect.defect_no} ${defect.title}`)
    }))
    return [...options].map(([value, label]) => ({ value, label }))
  })

  function configureResultColumn() {
    columns.value = columns.value.map((column) => ['result', 'actual_result', 'execution_note'].includes(column.field)
      ? { ...column, editable: plan.status === 2 }
      : column)
  }
  async function loadDetail() {
    loading.value = true
    try {
      const data = (await getFunctionalPlanDetail(planId)).data || {}
      data.cases = (data.cases || []).map((item: any) => ({
        ...item,
        defect_summary: (item.defects || []).map((defect: any) => `${defect.defect_no} ${defect.title}`).join('、') || '-',
      }))
      Object.assign(plan, data)
      selectedPlanCases.value = []
      configureResultColumn()
    } finally {
      loading.value = false
    }
  }
  async function savePlanCase({ row, field, oldValue, changes, oldValues }: any) {
    if (!field) return
    caseSaving.value = true
    saveFailed.value = false
    try {
      const res = await putFunctionalPlanCase({ id: row.id, ...(changes || { [field]: row[field] }) })
      Object.assign(row, res.data || {})
      savedOnce.value = true
    } catch {
      Object.entries(oldValues || { [field]: oldValue }).forEach(([key, value]) => { row[key] = value })
      saveFailed.value = true
    } finally {
      caseSaving.value = false
    }
  }
  function removeSelected() {
    Modal.warning({
      title: '移出计划', content: `确认移出 ${selectedPlanCases.value.length} 条用例及其本次结果？`, hideCancel: false,
      onBeforeOk: async () => {
        await removeFunctionalPlanCases({ plan_id: planId, plan_case_ids: selectedPlanCases.value.map((item) => item.id) })
        await loadDetail()
      },
    })
  }
  function openStartPlan() {
    startForm.update_requirement_status = Boolean(plan.requirement_version)
    startVisible.value = true
  }
  async function startPlan() {
    actionLoading.value = true
    try {
      await startFunctionalPlan(planId, startForm.update_requirement_status)
      startVisible.value = false
      Message.success('测试计划已开始，可填写本次结果')
      await loadDetail()
      return true
    } finally { actionLoading.value = false }
  }
  function finishPlan() {
    const warning = plan.unlinked_failed_count
      ? `当前仍有 ${plan.unlinked_failed_count} 条失败或阻塞用例未关联缺陷。完成后计划和结果将只读，是否继续？`
      : '完成后计划和结果将只读。确认完成本次测试？'
    Modal.warning({
      title: '完成测试计划', content: warning, hideCancel: false,
      onBeforeOk: async () => {
        actionLoading.value = true
        try { await finishFunctionalPlan(planId); await loadDetail() }
        finally { actionLoading.value = false }
      },
    })
  }
  async function setBatchResult(result: number) {
    actionLoading.value = true
    try {
      await batchFunctionalPlanResult({
        plan_id: planId, plan_case_ids: selectedPlanCases.value.map((item) => item.id), result,
      })
      await loadDetail()
    } finally { actionLoading.value = false }
  }
  function createDefect() {
    if (!canCreateDefect.value) return
    router.push({ path: '/functional-test/defect/index', query: {
      plan_id: planId,
      plan_case_ids: selectedPlanCases.value.map((item: any) => item.id).join(','),
      project_product: plan.project_product?.id,
    } })
  }
  async function openBindDefect() {
    if (!selectedPlanCases.value.length) return
    bindForm.defect_id = undefined
    bindVisible.value = true
    defectOptionLoading.value = true
    try {
      const res = await getFunctionalDefectOptions({ project_product: plan.project_product?.id })
      defectOptions.value = (res.data || []).map((item: any) => ({
        value: item.id,
        label: `${item.defect_no} ${item.title}`,
      }))
    } finally { defectOptionLoading.value = false }
  }
  async function bindExistingDefect() {
    if (!bindForm.defect_id) { Message.warning('请选择缺陷'); return false }
    bindSaving.value = true
    try {
      await bindFunctionalDefectCases({
        id: bindForm.defect_id,
        plan_case_ids: selectedPlanCases.value.map((item: any) => item.id),
      })
      bindVisible.value = false
      Message.success('已关联缺陷')
      await loadDetail()
      return true
    } finally { bindSaving.value = false }
  }
  function openUnbindDefect() {
    unbindForm.defect_id = selectedDefectOptions.value[0]?.value
    unbindVisible.value = true
  }
  async function unbindExistingDefect() {
    if (!unbindForm.defect_id) { Message.warning('请选择缺陷'); return false }
    bindSaving.value = true
    try {
      await unbindFunctionalDefectCases({
        id: unbindForm.defect_id,
        plan_case_ids: selectedPlanCases.value.map((item: any) => item.id),
      })
      unbindVisible.value = false
      Message.success('已取消缺陷关联')
      await loadDetail()
      return true
    } finally { bindSaving.value = false }
  }
  async function openCasePicker() {
    pickerVisible.value = true
    pickerSelectedKeys.value = []
    await loadLibraryCases()
  }
  async function loadLibraryCases() {
    pickerLoading.value = true
    try {
      const query: any = { project_product: plan.project_product?.id, status: 1, page: 1, pageSize: 500 }
      Object.entries(pickerFilter).forEach(([key, value]) => { if (value !== '' && value !== undefined) query[key] = value })
      libraryCases.value = (await getManualCase(query)).data || []
    } finally { pickerLoading.value = false }
  }
  async function confirmPick() {
    if (!pickerSelectedKeys.value.length) { Message.warning('请选择用例'); return }
    pickerSaving.value = true
    try {
      await addFunctionalPlanCases({ plan_id: planId, case_ids: pickerSelectedKeys.value })
      pickerVisible.value = false
      await loadDetail()
    } finally { pickerSaving.value = false }
  }
  onMounted(async () => {
    await enumStore.getEnum()
    const users = (await getUserName()).data || []
    columns.value = createPlanCaseColumns(enumStore, users).filter(
      (item: any) => !['status', 'version_no', 'update_time'].includes(item.field)
    )
    await loadDetail()
  })
</script>

<style lang="less" scoped>
  .mango-plan-detail__workbench { display: flex; width: 100%; height: 100%; min-width: 0; min-height: 0; flex-direction: column; }
  .mango-plan-detail__meta { display: flex; flex: none; align-items: center; gap: 12px; min-height: 36px; color: var(--m-muted); }
  .mango-plan-detail__grid { height: 0; min-height: 0; flex: 1; }
  .mango-plan-detail__picker-filter { display: flex; gap: 8px; margin-bottom: 10px; }
  .mango-plan-detail__picker-filter > * { width: 180px; }
  .mango-plan-detail__picker-filter > button { width: auto; }
  .mango-plan-detail__picker-footer { display: flex; align-items: center; justify-content: space-between; margin-top: 12px; }
</style>
