<template>
  <TableBody plain class="mango-detail-workbench-page">
    <template #header>
      <div class="mango-detail-toolbar">
        <div class="mango-detail-heading"
          ><div class="mango-detail-title"
            >测试计划 / {{ planId || '-' }} / {{ plan?.name || '-' }}</div
          ></div
        >
        <a-space class="mango-detail-actions" wrap>
          <a-button
            class="mango-back-button"
            size="small"
            :loading="navigating === 'back'"
            @click="goBack"
            >返回</a-button
          >
          <a-button
            size="small"
            :loading="loading"
            :disabled="writeBusy || execution.confirming.value"
            @click="loadDetail"
            >刷新</a-button
          >
          <a-button
            size="small"
            :disabled="!canOperate || !plan || plan.status >= 2"
            @click="openCasePicker"
            >从用例库选用例</a-button
          >
          <a-button
            v-if="plan && [0, 1].includes(plan.status)"
            size="small"
            type="primary"
            status="success"
            :loading="execution.kind.value === 'start'"
            :disabled="!canOperate || !plan.cases.length"
            @click="execution.openStart"
            >开始执行</a-button
          >
          <a-button
            v-if="plan?.status === 2"
            size="small"
            type="primary"
            status="success"
            :loading="execution.kind.value === 'finish'"
            :disabled="!canOperate"
            @click="execution.finish"
            >完成计划</a-button
          >
        </a-space>
      </div>
    </template>
    <template #default>
      <div class="mango-plan-detail__workbench">
        <a-alert v-if="planId === null" type="error"
          >计划 ID 无效，请返回计划列表重新打开。</a-alert
        >



        <a-alert v-if="execution.error.value" type="error"
          >操作失败，请重试；现有数据及选择已保留。</a-alert
        >
        <a-alert v-if="navigationError" type="error">页面打开失败，请重试。</a-alert>
        <div v-if="plan" class="mango-plan-detail__meta">
          <a-tag :color="enumStore.colors[plan.status]">{{
            enumTitle(enumStore.functional_test_plan_status, plan.status)
          }}</a-tag>
          <span>{{ enumTitle(enumStore.functional_test_plan_scope_type, plan.scope_type) }}</span>
          <span class="mango-plan-detail__scope" :title="scopeLabel">{{ scopeLabel }}</span>
          <span v-if="plan.environment">环境 {{ plan.environment }}</span
          ><span v-if="plan.build_version">构建 {{ plan.build_version }}</span>
          <span>进度 {{ plan.execution_stats.executed }}/{{ plan.execution_stats.total }}</span>
          <span>通过率 {{ formatRate(plan.execution_stats.pass_rate) }}</span>
          <span>缺陷 {{ plan.defect_count }}（未关闭 {{ plan.open_defect_count }}）</span>
          <span v-if="plan.started_at">开始 {{ plan.started_at }}</span
          ><span v-if="plan.finished_at">完成 {{ plan.finished_at }}</span>
        </div>
        <FunctionalCaseGrid
          ref="planGrid"
          class="mango-plan-detail__grid"
          :rows="plan?.cases || []"
          :context-key="gridContextKey"
          :columns="columns"
          :loading="loading"
          :editable="gridEditable"
          :show-hint="false"
          @cell-change="savePlanCase"
          @selection-change="onSelectionChange"
        >
          <template #summary>
            <span
              >已选择 {{ selectedPlanCases.length }} 条　共 {{ plan?.cases.length || 0 }} 条</span
            >
            <a-tag v-if="caseSaving" size="small" color="arcoblue">正在保存…</a-tag>
            <a-tag v-else-if="saveFailed" size="small" color="red">保存失败</a-tag>
            <a-tag v-else-if="savedOnce" size="small" color="green">已保存</a-tag>
          </template>
          <template #toolbar>
            <a-button
              v-if="plan && plan.status < 2"
              size="small"
              status="danger"
              :loading="execution.kind.value === 'remove'"
              :disabled="!canOperate || !selectedPlanCases.length"
              @click="execution.remove"
              >移出计划</a-button
            >
            <template v-if="plan?.status === 2">
              <a-button
                size="small"
                :loading="execution.kind.value === 'batch' && execution.batchResult.value === 1"
                :disabled="!canOperate || !selectedPlanCases.length"
                @click="execution.batch(1)"
                >通过</a-button
              >
              <a-button
                size="small"
                status="danger"
                :loading="execution.kind.value === 'batch' && execution.batchResult.value === 2"
                :disabled="!canOperate || !selectedPlanCases.length"
                @click="execution.batch(2)"
                >失败</a-button
              >
              <a-button
                size="small"
                status="warning"
                :loading="execution.kind.value === 'batch' && execution.batchResult.value === 3"
                :disabled="!canOperate || !selectedPlanCases.length"
                @click="execution.batch(3)"
                >阻塞</a-button
              >
            </template>
            <a-button
              size="small"
              :loading="navigating === 'defect'"
              :disabled="!canOperate || !canCreateDefect"
              @click="createDefect"
              >创建缺陷</a-button
            >
            <a-button
              size="small"
              :disabled="!canOperate || !selectedPlanCases.length"
              @click="openBindDefect"
              >关联已有缺陷</a-button
            >
            <a-button
              size="small"
              :disabled="!canOperate || !selectedDefectOptions.length"
              @click="openUnbindDefect"
              >取消缺陷关联</a-button
            >
          </template>
          <template #cell-test_steps="{ row }">{{ row.test_steps?.length || 0 }} 个步骤</template>
        </FunctionalCaseGrid>
      </div>
    </template>
  </TableBody>
  <PlanCasePickerDrawer
    ref="casePicker"
    :context-key="gridContextKey"
    :plan-id="planId || 0"
    :product-id="plan?.project_product?.id ?? null"
    :editable="!!plan && plan.status < 2 && !caseSaving && !execution.busy.value && !loading"
    :priority-options="enumStore.case_level || []"
    :priority-colors="enumStore.colors"
    @changed="onRelatedChanged"
  />
  <PlanDefectRelationDialog
    ref="defectRelation"
    :context-key="gridContextKey"
    :plan-id="planId || 0"
    :product-id="plan?.project_product?.id ?? null"
    @changed="onRelatedChanged"
  />
  <a-modal
    modal-class="mango-simple-form-modal"
    v-model:visible="execution.startVisible.value"
    title="开始执行"
    :width="560"
    :ok-loading="execution.kind.value === 'start'"
    :on-before-ok="execution.start"
    :on-before-cancel="execution.canCancel"
    @cancel="execution.cancelStart"
  >
    <a-alert v-if="execution.error.value" type="error">执行请求失败，选择已保留，请重试。</a-alert>
    <a-form class="mango-simple-form"
      :model="execution.startForm"
      layout="horizontal"
      auto-label-width
      :disabled="execution.busy.value"
    >
      <a-alert type="info">开始后可以填写本次执行结果。</a-alert>
      <a-form-item class="mango-simple-form-item" v-if="plan?.requirement_version" label="需求交付状态">
        <a-checkbox v-model="execution.startForm.update_requirement_status"
          >同时将当前需求版本更新为“测试中”</a-checkbox
        >
      </a-form-item>
    </a-form>
  </a-modal>
</template>
<script lang="ts" setup>
import { reportLoadError } from '@/utils/load-error'

  import {
    computed,
    onActivated,
    onBeforeUnmount,
    onDeactivated,
    onMounted,
    ref,
    shallowRef,
    watch,
  } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import FunctionalCaseGrid from '@/components/table/FunctionalCaseGrid.vue'
  import TableBody from '@/components/table/TableBody.vue'
  import { useEnum } from '@/store/modules/get-enum'
  import useUserStore from '@/store/modules/user'
  import { getUserName } from '@/api/user/user'
  import { getFunctionalPlanDetail } from '@/api/functional-test'
  import { usePlanCaseSave } from './composables/usePlanCaseSave'
  import { usePlanExecution } from './composables/usePlanExecution'
  import PlanCasePickerDrawer from './components/PlanCasePickerDrawer.vue'
  import PlanDefectRelationDialog from './components/PlanDefectRelationDialog.vue'
  import { createPlanCaseColumns } from './config'
  import { parsePlanCase, parsePlanDetail, planList, planObject } from './presentation'
  import type {
    PlanCasePickerHandle,
    PlanDefectRelationHandle,
    PlanDetail,
    PlanCaseRow,
    PlanExecutionResult,
  } from './types'

  const route = useRoute(),
    router = useRouter(),
    gridUser = useUserStore(),
    enumStore = useEnum()
  const planId = computed(() =>
    typeof route.query.id === 'string' &&
    /^\d+$/.test(route.query.id) &&
    Number.isSafeInteger(Number(route.query.id)) &&
    Number(route.query.id) > 0
      ? Number(route.query.id)
      : null
  )
  const gridContextKey = computed(() =>
    JSON.stringify([
      route.fullPath,
      gridUser.userId,
      gridUser.roleId,
      gridUser.token,
      gridUser.selected_environment,
    ])
  )
  const plan = shallowRef<PlanDetail | null>(null)
  const selectedPlanCases = shallowRef<PlanCaseRow[]>([])
  const users = shallowRef<Array<{ key: number | string; title: string }>>([])
  const loading = ref(false),
    usersLoading = ref(false),
    enumsLoading = ref(false)
  const readError = ref(false),
    usersError = ref(false),
    enumsError = ref(false)
  const planGrid = ref<{ refreshRowCells: (id: number | string) => void } | null>(null)
  const casePicker = ref<PlanCasePickerHandle | null>(null),
    defectRelation = ref<PlanDefectRelationHandle | null>(null)
  const refreshPending = ref(false)
  let active = true,
    mounted = false,
    generation = 0,
    detailSequence = 0,
    userSequence = 0,
    enumSequence = 0
  const available = () =>
    active && route.path === '/functional-test/plan/details' && planId.value !== null
  const current = (version: number) => available() && generation === version
  const childOpen = computed(() => !!casePicker.value?.isOpen() || !!defectRelation.value?.isOpen())
  const childSaving = computed(
    () => !!casePicker.value?.isSaving() || !!defectRelation.value?.isSaving()
  )
  const columns = computed(() =>
    createPlanCaseColumns(enumStore, users.value)
      .filter((item) => !['status', 'version_no', 'update_time'].includes(item.field))
      .map((column) =>
        ['result', 'actual_result', 'execution_note'].includes(column.field)
          ? { ...column, editable: plan.value?.status === 2 }
          : column
      )
  )
  const execution = usePlanExecution({
    context: () => gridContextKey.value,
    available,
    blocked: () => loading.value || caseSaving.value || childOpen.value,
    subject: () =>
      plan.value
        ? {
            id: plan.value.id,
            status: plan.value.status,
            caseIds: plan.value.cases.map((row) => row.id),
            hasRequirement: !!plan.value.requirement_version,
            unlinkedFailedCount: plan.value.unlinked_failed_count,
          }
        : null,
    selectedIds: () =>
      selectedPlanCases.value.filter((row) => plan.value?.cases.includes(row)).map((row) => row.id),
    accepted: onExecutionAccepted,
  })
  const gridEditable = computed(
    () =>
      available() &&
      !!plan.value &&
      plan.value.status < 3 &&
      !loading.value &&
      !execution.busy.value &&
      !execution.confirming.value &&
      !childOpen.value
  )
  const { caseSaving, savedOnce, saveFailed, savePlanCase } = usePlanCaseSave({
    context: () => gridContextKey.value,
    ownsRow: (row) => !!plan.value?.cases.some((item) => item === row),
    columns: () => columns.value,
    editable: () => gridEditable.value,
    normalizeResponse: (value) => {
      const row = parsePlanCase(value)
      if (row.plan !== plan.value?.id) throw Error('计划用例范围无效')
      return row
    },
    refresh: (row) => {
      const id: unknown = Reflect.get(row, 'id')
      if (typeof id === 'number') planGrid.value?.refreshRowCells(id)
    },
  })
  const writeBusy = computed(() => caseSaving.value || execution.busy.value || childSaving.value)
  const canOperate = computed(
    () =>
      available() &&
      !!plan.value &&
      !loading.value &&
      !writeBusy.value &&
      !execution.confirming.value &&
      !childOpen.value
  )
  const canCreateDefect = computed(
    () =>
      selectedPlanCases.value.length > 0 &&
      selectedPlanCases.value.every((row) => [2, 3].includes(row.result))
  )
  const selectedDefectOptions = computed(() => {
    const values = new Map<number, string>()
    for (const row of selectedPlanCases.value)
      for (const defect of row.defects) values.set(defect.id, `${defect.defect_no} ${defect.title}`)
    return [...values].map(([value, label]) => ({ value, label }))
  })
  const enumTitle = (options: Array<{ key: number | string; title: string }>, value: number) =>
    options?.find((item) => Number(item.key) === value)?.title || '-'
  const formatRate = (value: number) => `${value.toFixed(2).replace(/\.00$/, '')}%`
  const scopeLabel = computed(() => {
    const value = plan.value
    if (!value) return '-'
    if (value.scope_type === 0)
      return value.requirement_version
        ? `${
            value.requirement_version.requirement_name ||
            value.requirement_version.requirement?.name ||
            '需求'
          } · V${value.requirement_version.version_no || '-'}`
        : '未选择需求版本'
    if (value.scope_type === 1) return value.iteration?.name || '未选择 Sprint'
    return value.scope_ref || '未填写范围标识'
  })
  function onSelectionChange(rows: object[]) {
    selectedPlanCases.value = plan.value?.cases.filter((row) => rows.includes(row)) || []
  }
  async function loadDetail() {
    if (!available()) return false
    if (writeBusy.value || childOpen.value) {
      refreshPending.value = true
      return false
    }
    refreshPending.value = false
    const id = planId.value!,
      version = generation,
      sequence = ++detailSequence
    const valid = () => current(version) && sequence === detailSequence
    loading.value = true
    readError.value = false
    try {
      const data = (await getFunctionalPlanDetail(id)).data
      if (!valid()) return false
      plan.value = parsePlanDetail(data, id)
      selectedPlanCases.value = []
      return true
    } catch (loadFailure0) {
      if (valid()) (reportLoadError(loadFailure0, "加载失败，请重试", false), readError.value = true)
      return false
    } finally {
      if (valid()) loading.value = false
    }
  }
  async function loadUsers() {
    if (!available()) return false
    const version = generation,
      sequence = ++userSequence
    const valid = () => current(version) && sequence === userSequence
    usersLoading.value = true
    usersError.value = false
    try {
      const data = (await getUserName()).data
      if (!valid()) return false
      users.value = planList(data).map((value) => {
        const item = planObject(value)
        if (
          (typeof item.key !== 'number' && typeof item.key !== 'string') ||
          typeof item.title !== 'string'
        )
          throw Error('用户选项格式错误')
        return { key: item.key, title: item.title }
      })
      return true
    } catch (loadFailure1) {
      if (valid()) (reportLoadError(loadFailure1, "加载失败，请重试", false), usersError.value = true)
      return false
    } finally {
      if (valid()) usersLoading.value = false
    }
  }
  async function loadEnums() {
    if (!available()) return false
    const version = generation,
      sequence = ++enumSequence
    const valid = () => current(version) && sequence === enumSequence
    enumsLoading.value = true
    enumsError.value = false
    try {
      await enumStore.getEnum()
      return valid()
    } catch (loadFailure2) {
      if (valid()) (reportLoadError(loadFailure2, "加载失败，请重试", false), enumsError.value = true)
      return false
    } finally {
      if (valid()) enumsLoading.value = false
    }
  }
  function onExecutionAccepted(result: PlanExecutionResult) {
    if (!plan.value || !available()) return
    ++detailSequence
    if (result.kind === 'remove')
      plan.value = {
        ...plan.value,
        cases: plan.value.cases.filter((row) => !result.ids.includes(row.id)),
      }
    else if (result.kind === 'batch') {
      const updated = new Map(result.rows.map((row) => [row.id, row]))
      plan.value = {
        ...plan.value,
        cases: plan.value.cases.map((row) => updated.get(row.id) || row),
      }
    } else
      plan.value = {
        ...plan.value,
        status: result.status,
        started_at: result.started_at || plan.value.started_at,
        finished_at: result.finished_at || plan.value.finished_at,
      }
    selectedPlanCases.value = []
    void loadDetail()
  }
  function openCasePicker() {
    if (canOperate.value) casePicker.value?.open()
  }
  function openBindDefect() {
    if (canOperate.value && selectedPlanCases.value.length)
      defectRelation.value?.open(
        'bind',
        selectedPlanCases.value.map((row) => row.id)
      )
  }
  function openUnbindDefect() {
    if (canOperate.value && selectedDefectOptions.value.length)
      defectRelation.value?.open(
        'unbind',
        selectedPlanCases.value.map((row) => row.id),
        selectedDefectOptions.value
      )
  }
  function onRelatedChanged(id: number) {
    if (id === planId.value && available()) {
      ++detailSequence
      void loadDetail()
    }
  }
  const navigating = ref<'defect' | 'back' | null>(null),
    navigationError = ref(false)
  async function navigate(kind: 'defect' | 'back') {
    if (
      !available() ||
      navigating.value !== null ||
      (kind === 'defect' && (!canOperate.value || !canCreateDefect.value))
    )
      return
    const version = generation
    navigating.value = kind
    navigationError.value = false
    try {
      const failure =
        kind === 'defect'
          ? await router.push({
              path: '/functional-test/defect/index',
              query: {
                plan_id: planId.value,
                plan_case_ids: selectedPlanCases.value.map((row) => row.id).join(','),
                project_product: plan.value?.project_product?.id,
              },
            })
          : await router.back()
      if (failure && current(version)) navigationError.value = true
    } catch {
      if (current(version)) navigationError.value = true
    } finally {
      navigating.value = null
    }
  }
  const createDefect = () => navigate('defect'),
    goBack = () => navigate('back')
  function invalidate() {
    ++generation
    ++detailSequence
    ++userSequence
    ++enumSequence
    refreshPending.value = false
    plan.value = null
    selectedPlanCases.value = []
    users.value = []
    loading.value = false
    usersLoading.value = false
    enumsLoading.value = false
    readError.value = false
    usersError.value = false
    enumsError.value = false
    navigationError.value = false
  }
  function loadAll() {
    return Promise.allSettled([loadDetail(), loadUsers(), loadEnums()])
  }
  watch([writeBusy, childOpen, refreshPending], () => {
    if (refreshPending.value && available() && !writeBusy.value && !childOpen.value)
      void loadDetail()
  })
  watch(
    gridContextKey,
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
<style lang="less" scoped>
  .mango-plan-detail__workbench {
    display: flex;
    width: 100%;
    height: 100%;
    min-width: 0;
    min-height: 0;
    flex-direction: column;
    gap: var(--m-page-gap);
  }
  .mango-plan-detail__meta {
    display: flex;
    flex: none;
    align-items: center;
    flex-wrap: wrap;
    gap: 12px;
    min-height: 36px;
    color: var(--m-muted);
  }
  .mango-plan-detail__scope {
    max-width: 320px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .mango-plan-detail__grid {
    height: 0;
    min-height: 0;
    flex: 1;
  }
</style>
