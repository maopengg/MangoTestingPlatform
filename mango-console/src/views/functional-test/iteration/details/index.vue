<template>
  <TableBody plain class="mango-detail-workbench-page" :sticky-horizontal-scroll="false">
    <template #header>
      <TableHeader :title="headerTitle">
        <template #header-extra>
          <a-space
            ><a-button class="mango-back-button" size="small" @click="router.back()">返回</a-button
            ><a-button size="small" :loading="loading" @click="loadAll">刷新</a-button></a-space
          >
        </template>
      </TableHeader>
    </template>
    <template #default>
      <section class="mango-iteration-detail">
        <a-alert v-if="iterationId === null" type="error"
          >迭代 ID 无效，请返回列表重新选择。</a-alert
        >
        
        <a-alert v-if="mutations.error.value" type="error">{{ mutations.error.value }}</a-alert>
        <mango-panel-spin :loading="detailRegion.loading.value">
          <div class="mango-iteration-detail__summary">
            <a-space wrap>
              <a-tag :color="enumStore.colors[iteration?.status ?? '']">{{
                enumTitle(iterationStatusOptions, iteration?.status)
              }}</a-tag>
              <span>{{ iteration?.start_date || '-' }} 至 {{ iteration?.end_date || '-' }}</span>
              <span>负责人：{{ iteration?.owner?.name || '-' }}</span>
              <span>需求 {{ ganttData.summary.requirement_count }} 条</span>
              <a-tag v-if="saveState === 'saving'" color="arcoblue">正在保存…</a-tag>
              <a-tag v-else-if="saveState === 'saved'" color="green">已保存</a-tag>
              <a-tag v-else-if="saveState === 'failed'" color="red">保存失败</a-tag>
              <a-tag v-if="ganttData.summary?.overdue_count" color="red"
                >逾期 {{ ganttData.summary.overdue_count }}</a-tag
              >
              <a-tag v-if="ganttData.summary?.overlap_count" color="orangered"
                >排期重叠 {{ ganttData.summary.overlap_count }}</a-tag
              >
            </a-space>
          </div>
        </mango-panel-spin>
        <a-tabs v-model:active-key="activeSection" class="mango-iteration-detail__tabs">
          <a-tab-pane key="board" title="需求看板">
            <RequirementKanban
              :columns="boardColumns"
              :loading="boardRegion.loading.value"
              :busy-ids="Array.from(mutations.busy.keys())"
              :context-key="gridContextKey"
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
                  <a-table
                    class="mango-native-scroll-table"
                    :data="suites"
                    :columns="scheduleColumns"
                    :loading="suitesRegion.loading.value"
                    :pagination="false"
                    :scroll="{ x: 1420, y: '100%' }"
                    row-key="id"
                  >
                    <template #requirement_key="{ record }">{{
                      record.requirement?.requirement_key || '-'
                    }}</template>
                    <template #priority="{ record }">{{
                      enumTitle(priorityOptions, record.priority)
                    }}</template>
                    <template #development_owner="{ record }">{{
                      record.development_owner?.name || '未分配'
                    }}</template>
                    <template #status="{ record }"
                      ><a-tag :color="enumStore.colors[record.status]">{{
                        enumTitle(suiteStatusOptions, record.status)
                      }}</a-tag></template
                    >
                    <template #owner="{ record }">{{ record.owner?.name || '-' }}</template>
                    <template #actions="{ record }"
                      ><MangoTableActions
                        :actions="[
                          {
                            label: '编辑排期',
                            disabled: isBusy(record.id),
                            onClick: () => openSchedule(record),
                          },
                          {
                            label: '确认提测',
                            disabled: record.status >= 4 || isBusy(record.id),
                            loading: mutations.busy.get(record.id) === 'submit',
                            onClick: () => confirmSubmit(record),
                          },
                        ]"
                    /></template>
                  </a-table>
                </div>
              </a-tab-pane>
              <a-tab-pane key="gantt" title="用户甘特图">
                <UserScheduleGantt
                  :data="ganttData"
                  :loading="ganttRegion.loading.value"
                  :status-options="suiteStatusOptions"
                  :context-key="gridContextKey"
                  :busy-ids="suites.filter((suite) => isBusy(suite.id)).map((suite) => suite.id)"
                  @edit="openGanttSchedule"
                />
              </a-tab-pane>
            </a-tabs>
          </a-tab-pane>
          <a-tab-pane key="cases" :title="`迭代用例（${iterationCaseTotal}）`">
            <FunctionalCaseGrid
              :rows="iterationCases"
              :context-key="gridContextKey"
              :columns="iterationCaseColumns"
              :loading="casesRegion.loading.value"
              :editable="false"
              :selectable="false"
              :show-hint="false"
            >
              <template #summary
                >共 {{ iterationCaseTotal }} 条，汇总需求来源与本迭代测试计划中的全部用例</template
              >
            </FunctionalCaseGrid>
          </a-tab-pane>
          <a-tab-pane key="plans" :title="`测试计划（${plans.length}）`">
            <div class="mango-iteration-detail__table">
              <a-table
                class="mango-native-scroll-table"
                :data="plans"
                :columns="iterationPlanColumns"
                :loading="plansRegion.loading.value"
                :pagination="false"
                :scroll="{ x: 1140, y: '100%' }"
                row-key="id"
              >
                <template #name="{ record }"
                  ><a-link :loading="navigationLoading" @click="goPlan(record)">{{
                    record.name
                  }}</a-link></template
                >
                <template #scope_type="{ record }">{{
                  enumTitle(planScopeOptions, record.scope_type)
                }}</template>
                <template #plan_status="{ record }"
                  ><a-tag :color="enumStore.colors[record.status]">{{
                    enumTitle(planStatusOptions, record.status)
                  }}</a-tag></template
                >
                <template #execution_progress="{ record }"
                  >{{ record.execution_stats?.executed || 0 }}/{{
                    record.execution_stats?.total || 0
                  }}（{{ formatRate(record.execution_stats?.progress) }}）</template
                >
                <template #pass_rate="{ record }">{{
                  formatRate(record.execution_stats?.pass_rate)
                }}</template>
                <template #plan_owner="{ record }">{{ record.owner?.name || '-' }}</template>
              </a-table>
            </div>
          </a-tab-pane>
          <a-tab-pane key="defects" :title="`缺陷（${defects.length}）`">
            <div class="mango-iteration-detail__table">
              <a-table
                class="mango-native-scroll-table"
                :data="defects"
                :columns="iterationDefectColumns"
                :loading="defectsRegion.loading.value"
                :pagination="false"
                :scroll="{ x: 1120, y: '100%' }"
                row-key="id"
              >
                <template #defect_no="{ record }"
                  ><a-link :loading="navigationLoading" @click="goDefect(record)">{{
                    record.defect_no
                  }}</a-link></template
                >
                <template #defect_status="{ record }"
                  ><a-tag :color="enumStore.colors[record.status]">{{
                    enumTitle(defectStatusOptions, record.status)
                  }}</a-tag></template
                >
                <template #severity="{ record }">{{
                  enumTitle(defectSeverityOptions, record.severity)
                }}</template>
                <template #defect_priority="{ record }">{{
                  enumTitle(defectPriorityOptions, record.priority)
                }}</template>
                <template #assignee="{ record }">{{ record.assignee?.name || '未分配' }}</template>
              </a-table>
            </div>
          </a-tab-pane>
        </a-tabs>
      </section>
    </template>
  </TableBody>

  <IterationScheduleDialog
    ref="scheduleDialog"
    :context-key="gridContextKey"
    :iteration-id="iterationId ?? 0"
    :users="userOptions"
    :priority-options="priorityOptions"
    :status-options="suiteStatusOptions"
    :users-loading="usersRegion.loading.value"
    :users-error="usersRegion.error.value"
    :enums-loading="enumsRegion.loading.value"
    :enums-error="enumsRegion.error.value"
    @retry-users="usersRegion.load()"
    @retry-enums="enumsRegion.load()"
    @saved="onScheduleSaved"
  />

  <RequirementOverviewDrawer
    v-model:visible="overviewVisible"
    :suite-id="overviewSuiteId"
    :status-options="suiteStatusOptions"
    @edit-schedule="openSchedule"
    @changed="loadAll"
  />
</template>

<script lang="ts" setup>
  import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { useRoute, useRouter } from 'vue-router'
  import TableBody from '@/components/table/TableBody.vue'
  import TableHeader from '@/components/table/TableHeader.vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import FunctionalCaseGrid from '@/components/table/FunctionalCaseGrid.vue'
  import type { FunctionalGridColumn } from '@/components/table/functional-case-grid'
  import { useEnum } from '@/store/modules/get-enum'
  import useUserStore from '@/store/modules/user'
  import { getUserName } from '@/api/user/user'
  import {
    getFunctionalIterationDetail,
    getFunctionalIterationGantt,
    getFunctionalIterationBoard,
    getFunctionalIterationCases,
    getManualSuite,
    getRelatedFunctionalDefects,
    getRelatedFunctionalPlans,
  } from '@/api/functional-test'
  import UserScheduleGantt from '../components/UserScheduleGantt.vue'
  import RequirementKanban from '../components/RequirementKanban.vue'
  import RequirementOverviewDrawer from '../components/RequirementOverviewDrawer.vue'
  import { createCaseLibraryColumns } from '../../case-library/config'
  import { iterationDefectColumns, iterationPlanColumns, scheduleColumns } from './config'
  import IterationScheduleDialog from './components/IterationScheduleDialog.vue'
  import { useIterationRegion } from '../composables/useIterationRegion'
  import { useIterationSuiteMutations } from './composables/useIterationSuiteMutations'
  import {
    emptyIterationGantt,
    iterationList,
    iterationObject,
    parseIterationBoard,
    parseIterationCase,
    parseIterationDefect,
    parseIterationDetail,
    parseIterationGantt,
    parseIterationPlan,
    parseIterationSuite,
  } from '../presentation'
  import type {
    IterationScheduleHandle,
    IterationScheduleSubject,
    IterationUserOption,
  } from './types'
  import type { IterationDetail, IterationSuite, IterationGanttItem } from '../types'

  const route = useRoute(),
    router = useRouter(),
    gridUser = useUserStore(),
    enumStore = useEnum()
  const iterationId = computed(() => {
    const value = route.query.id
    return typeof value === 'string' &&
      /^\d+$/.test(value) &&
      Number.isSafeInteger(Number(value)) &&
      Number(value) > 0
      ? Number(value)
      : null
  })
  const gridContextKey = computed(() =>
    JSON.stringify([
      route.fullPath,
      gridUser.userId,
      gridUser.roleId,
      gridUser.token,
      gridUser.selected_environment,
    ])
  )
  let active = true,
    mounted = false,
    generation = 0
  const available = () =>
    active && route.path === '/functional-test/iteration/details' && iterationId.value !== null
  const scope = () => generation
  function region<T>(initial: () => T, read: () => Promise<T>) {
    return useIterationRegion(initial, read, scope, available)
  }
  const detailRegion = region<IterationDetail | null>(
    () => null,
    async () => {
      const id = iterationId.value!,
        value = parseIterationDetail((await getFunctionalIterationDetail(id)).data)
      if (value.id !== id) throw Error('迭代详情不匹配')
      return value
    }
  )
  const suitesRegion = region(
    (): IterationSuite[] => [],
    async () =>
      iterationList((await getManualSuite({ iteration_ref: iterationId.value })).data).map(
        parseIterationSuite
      )
  )
  const ganttRegion = region(emptyIterationGantt, async () => {
    const id = iterationId.value!,
      value = parseIterationGantt((await getFunctionalIterationGantt({ iteration_id: id })).data)
    if (value.iteration?.id !== id) throw Error('排期数据不匹配')
    return value
  })
  const boardRegion = region(
    (): ReturnType<typeof parseIterationBoard> => [],
    async () => {
      const id = iterationId.value!,
        value: unknown = (await getFunctionalIterationBoard(id)).data
      if (iterationObject(value).iteration_id !== id) throw Error('看板数据不匹配')
      return parseIterationBoard(value)
    }
  )
  const plansRegion = region(
    (): ReturnType<typeof parseIterationPlan>[] => [],
    async () =>
      iterationList(
        (await getRelatedFunctionalPlans({ iteration_id: iterationId.value })).data
      ).map(parseIterationPlan)
  )
  const defectsRegion = region(
    (): ReturnType<typeof parseIterationDefect>[] => [],
    async () =>
      iterationList(
        (await getRelatedFunctionalDefects({ iteration_id: iterationId.value })).data
      ).map(parseIterationDefect)
  )
  const casesRegion = region(
    () => ({ rows: [] as ReturnType<typeof parseIterationCase>[], total: 0 }),
    async () => {
      const result = await getFunctionalIterationCases({
        iteration_id: iterationId.value,
        page: 1,
        pageSize: 500,
      })
      const rows = iterationList(result.data).map(parseIterationCase)
      return { rows, total: typeof result.totalSize === 'number' ? result.totalSize : rows.length }
    }
  )
  const usersRegion = region(
    (): IterationUserOption[] => [],
    async () =>
      iterationList((await getUserName()).data).map((value) => {
        const row = iterationObject(value)
        if (
          (typeof row.key !== 'number' && typeof row.key !== 'string') ||
          typeof row.title !== 'string'
        )
          throw Error('用户选项格式错误')
        return { key: row.key, title: row.title }
      })
  )
  const enumsRegion = region(
    () => false,
    async () => {
      await enumStore.getEnum()
      return true
    }
  )
  const regions = {
    detail: detailRegion,
    suites: suitesRegion,
    gantt: ganttRegion,
    board: boardRegion,
    cases: casesRegion,
    plans: plansRegion,
    defects: defectsRegion,
    users: usersRegion,
    enums: enumsRegion,
  }
  const regionTitles = {
    detail: '迭代信息',
    suites: '排期表格',
    gantt: '甘特图',
    board: '需求看板',
    cases: '迭代用例',
    plans: '测试计划',
    defects: '缺陷',
    users: '用户选项',
    enums: '枚举选项',
  }
  type RegionKey =
    | 'detail'
    | 'suites'
    | 'gantt'
    | 'board'
    | 'cases'
    | 'plans'
    | 'defects'
    | 'users'
    | 'enums'
  const regionErrors = computed(() =>
    (Object.keys(regions) as RegionKey[])
      .filter((key) => regions[key].error.value)
      .map((key) => ({ key, title: regionTitles[key], loading: regions[key].loading.value }))
  )
  const loading = computed(() => Object.values(regions).some((item) => item.loading.value))
  const iteration = detailRegion.data,
    suites = suitesRegion.data,
    ganttData = ganttRegion.data,
    boardColumns = boardRegion.data,
    plans = plansRegion.data,
    defects = defectsRegion.data,
    userOptions = usersRegion.data
  const iterationCases = computed(() => casesRegion.data.value.rows),
    iterationCaseTotal = computed(() => casesRegion.data.value.total)
  const scheduleDialog = ref<IterationScheduleHandle | null>(null)
  const overviewVisible = ref(false),
    overviewSuiteId = ref<number>()
  const activeView = ref('table'),
    activeSection = ref('board'),
    navigationLoading = ref(false)
  const iterationStatusOptions = computed(() => enumStore.functional_test_iteration_status ?? [])
  const suiteStatusOptions = computed(() => enumStore.manual_test_suite_status ?? [])
  const priorityOptions = computed(() => enumStore.case_level ?? [])
  const planScopeOptions = computed(() => enumStore.functional_test_plan_scope_type ?? [])
  const planStatusOptions = computed(() => enumStore.functional_test_plan_status ?? [])
  const defectStatusOptions = computed(() => enumStore.functional_test_defect_status ?? [])
  const defectSeverityOptions = computed(() => enumStore.functional_test_defect_severity ?? [])
  const defectPriorityOptions = computed(() => enumStore.functional_test_defect_priority ?? [])
  const headerTitle = computed(
    () => `迭代详情 / ${iterationId.value ?? '-'} / ${iteration.value?.name || '-'}`
  )
  const enumTitle = (options: IterationUserOption[], value: unknown) =>
    options.find((item) => item.key === value)?.title || '-'
  const formatRate = (value: unknown) =>
    `${(typeof value === 'number' && Number.isFinite(value) ? value : 0)
      .toFixed(2)
      .replace(/\.00$/, '')}%`
  const iterationCaseColumns = computed<FunctionalGridColumn[]>(() => {
    const base = createCaseLibraryColumns(enumStore, userOptions.value)
    return [
      ...base.filter((item) => !['project_product_id', 'module_id'].includes(item.field)),
      { field: 'source_requirement', title: '来源需求', width: 260, editable: false },
      { field: 'iteration_plan_count', title: '关联计划数', width: 100, editable: false },
      {
        field: 'iteration_recent_result',
        title: '最近结果',
        width: 100,
        editable: false,
        options: (enumStore.functional_test_result ?? []).map((item) => ({
          label: item.title,
          value: item.key,
          colorToken: item.key === 1 ? '--m-success' : item.key === 2 ? '--m-danger' : '--m-muted',
        })),
      },
      { field: 'iteration_open_defect_count', title: '未关闭缺陷', width: 100, editable: false },
      ...base.filter((item) => ['project_product_id', 'module_id'].includes(item.field)),
    ]
  })
  function owns(row: IterationSuite) {
    return (
      suites.value.includes(row) || boardColumns.value.some((column) => column.items.includes(row))
    )
  }
  const mutations = useIterationSuiteMutations({
    context: scope,
    active: available,
    owns,
    available: (id) => !scheduleDialog.value?.isSaving(id),
    saved: (saved) => {
      for (const region of [suitesRegion, boardRegion, ganttRegion]) region.invalidate()
      suites.value = suites.value.map((row) => (row.id === saved.id ? saved : row))
      const hadBoardRow = boardColumns.value.some((column) =>
        column.items.some((row) => row.id === saved.id)
      )
      boardColumns.value = boardColumns.value.map((column) => ({
        ...column,
        items: [
          ...column.items.filter((row) => row.id !== saved.id),
          ...(hadBoardRow && column.status === saved.status ? [saved] : []),
        ],
      }))
      void refreshBusiness()
    },
  })
  const saveState = mutations.state
  const isBusy = (id: number) =>
    mutations.busy.has(id) || Boolean(scheduleDialog.value?.isSaving(id))
  async function loadAll() {
    if (!available()) return
    await Promise.allSettled(Object.values(regions).map((item) => item.load()))
  }
  async function refreshBusiness() {
    await Promise.allSettled(
      [suitesRegion, boardRegion, ganttRegion, casesRegion, plansRegion, defectsRegion].map(
        (item) => item.load()
      )
    )
  }
  function retryRegion(key: RegionKey) {
    return regions[key].load()
  }
  function openSchedule(row: IterationScheduleSubject) {
    if (!available() || isBusy(row.suite_id ?? row.id)) return
    const current =
      suites.value.find((item) => item.id === (row.suite_id ?? row.id)) ||
      boardColumns.value
        .flatMap((column) => column.items)
        .find((item) => item.id === (row.suite_id ?? row.id))
    if (current) scheduleDialog.value?.open(row)
  }
  function openOverview(row: IterationSuite) {
    if (!available() || !owns(row)) return
    overviewSuiteId.value = row.id
    overviewVisible.value = true
  }
  function moveRequirement(payload: { item: IterationSuite; status: number }) {
    return mutations.transition(payload.item, payload.status)
  }
  function cancelRequirement(row: IterationSuite) {
    return mutations.transition(row, 7)
  }
  function confirmSubmit(row: IterationSuite) {
    return mutations.submit(row)
  }
  function openGanttSchedule(row: IterationGanttItem) {
    if (!available() || !ganttData.value.groups.some((group) => group.items.includes(row))) return
    const suite = suites.value.find((item) => item.id === row.suite_id)
    if (suite) openSchedule(suite)
  }
  async function onScheduleSaved() {
    if (!available()) return
    saveState.value = 'saved'
    await refreshBusiness()
  }
  async function navigate(path: string, query: { id?: number; defect_id?: number }) {
    if (!available() || navigationLoading.value) return
    const version = generation
    navigationLoading.value = true
    try {
      await router.push({ path, query })
    } catch {
      if (active && version === generation) Message.error('页面打开失败，请重试')
    } finally {
      navigationLoading.value = false
    }
  }
  function goPlan(row: { id: number }) {
    if (plans.value.some((item) => item.id === row.id))
      return navigate('/functional-test/plan/details', { id: row.id })
  }
  function goDefect(row: { id: number }) {
    if (defects.value.some((item) => item.id === row.id))
      return navigate('/functional-test/defect/index', { defect_id: row.id })
  }
  function invalidate(clear: boolean) {
    ++generation
    for (const item of Object.values(regions)) item.invalidate(clear)
    mutations.invalidate()
    overviewVisible.value = false
    overviewSuiteId.value = undefined
  }
  watch(
    gridContextKey,
    () => {
      invalidate(true)
      if (mounted && available()) void loadAll()
    },
    { flush: 'sync' }
  )
  onMounted(() => {
    mounted = true
    void loadAll()
  })
  onDeactivated(() => {
    active = false
    invalidate(true)
  })
  onActivated(() => {
    if (active) return
    active = true
    if (mounted) void loadAll()
  })
  onBeforeUnmount(() => {
    active = false
    mounted = false
    invalidate(true)
  })
</script>

<style lang="less" scoped>
  .mango-iteration-detail {
    display: flex;
    height: 100%;
    min-height: 0;
    flex-direction: column;
    gap: var(--m-page-gap);
    padding-top: var(--m-page-gap);
  }
  .mango-iteration-detail__summary {
    padding: 8px 12px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
    color: var(--m-text-2);
  }
  .mango-iteration-detail__tabs {
    display: flex;
    flex: 1;
    min-height: 0;
    flex-direction: column;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
  }
  .mango-iteration-detail__tabs :deep(.arco-tabs-content),
  .mango-iteration-detail__tabs :deep(.arco-tabs-content-list),
  .mango-iteration-detail__tabs :deep(.arco-tabs-pane) {
    height: 100%;
    min-height: 0;
  }
  .mango-iteration-detail__tabs :deep(.arco-tabs-content) {
    flex: 1;
    min-height: 0;
    padding: 0;
  }
  .mango-iteration-detail__schedule-tabs {
    display: flex;
    height: 100%;
    min-height: 0;
    flex-direction: column;
  }
  .mango-iteration-detail__schedule-tabs :deep(.arco-tabs-content),
  .mango-iteration-detail__schedule-tabs :deep(.arco-tabs-content-list),
  .mango-iteration-detail__schedule-tabs :deep(.arco-tabs-pane) {
    height: 100%;
    min-height: 0;
  }
  .mango-iteration-detail__schedule-tabs :deep(.arco-tabs-content) {
    flex: 1;
    min-height: 0;
    padding: 0;
  }
  .mango-iteration-detail__table {
    display: flex;
    height: 100%;
    min-height: 0;
    flex-direction: column;
    overflow: hidden;
  }
</style>
