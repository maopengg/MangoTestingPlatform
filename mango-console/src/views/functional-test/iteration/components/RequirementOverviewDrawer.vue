<template>
  <a-drawer
    :visible="visible && !blocked"
    :width="860"
    unmount-on-close
    @update:visible="changeVisible"
  >
    <template #title>
      <span class="mango-requirement-overview__title"
        >{{ suite?.requirement?.requirement_key || '需求' }} ·
        {{ suite?.requirement_name || '-' }}</span
      >
    </template>
    <template #footer>
      <a-space wrap>
        <a-button
          size="small"
          :disabled="!suite || suiteRegion.loading.value || unlinking"
          @click="editSchedule"
          >编辑排期</a-button
        >
        <a-button
          size="small"
          :disabled="!suite"
          :loading="navigation === 'workspace'"
          @click="openWorkspace"
          >用例生成工作台</a-button
        >
        <a-button
          size="small"
          type="primary"
          :disabled="!suite"
          :loading="navigation === 'detail'"
          @click="openDetail"
          >查看完整需求</a-button
        >
      </a-space>
    </template>
    <div class="mango-requirement-overview">

      <a-alert v-if="unlinkError" type="error" class="mango-requirement-overview__notice"
        >取消关联失败，勾选已保留，请重试。</a-alert
      >
      <a-alert v-if="navigationError" type="error" class="mango-requirement-overview__notice"
        >页面打开失败，请重试。</a-alert
      >
      <a-tabs v-model:active-key="activeTab">
        <a-tab-pane key="overview" title="概览">
          <mango-panel-spin
            class="mango-requirement-overview__panel"
            :loading="suiteRegion.loading.value"
          >
            <a-descriptions v-if="suite" :column="2" bordered size="small">
              <a-descriptions-item label="版本">V{{ suite.version_no }}</a-descriptions-item>
              <a-descriptions-item label="状态"
                ><a-tag size="small" :color="enumStore.colors[suite.status]">{{
                  enumTitle(statusOptions, suite.status)
                }}</a-tag></a-descriptions-item
              >
              <a-descriptions-item label="开发负责人">{{
                suite.development_owner?.name || '-'
              }}</a-descriptions-item>
              <a-descriptions-item label="测试负责人">{{
                suite.owner?.name || '-'
              }}</a-descriptions-item>
              <a-descriptions-item label="计划开始">{{
                suite.planned_start_date || '-'
              }}</a-descriptions-item>
              <a-descriptions-item label="计划提测">{{
                suite.planned_submit_date || '-'
              }}</a-descriptions-item>
              <a-descriptions-item label="用例数">{{ suite.case_count }}</a-descriptions-item>
              <a-descriptions-item label="自动化覆盖">{{
                formatRate(suite.automation_coverage_percent)
              }}</a-descriptions-item>
              <a-descriptions-item label="项目产品">{{
                formatProjectProductPath(suite.project_product)
              }}</a-descriptions-item>
              <a-descriptions-item label="模块">{{
                formatModulePath(suite.module)
              }}</a-descriptions-item>
            </a-descriptions>
            <div
              v-else-if="!suiteRegion.loading.value && !suiteRegion.error.value"
              class="mango-empty-state"
              >暂无需求信息</div
            >
          </mango-panel-spin>
        </a-tab-pane>
        <a-tab-pane key="cases" :title="`来源用例（${cases.length}）`">
          <div class="mango-requirement-overview__toolbar">
            <span>解绑只取消需求来源关系，不会删除用例资产、历史版本、执行快照或缺陷关系。</span>
            <a-button
              size="small"
              status="danger"
              :disabled="
                !selectedCaseKeys.length || casesRegion.loading.value || casesRegion.error.value
              "
              :loading="unlinking"
              @click="unlinkCases"
              >取消关联</a-button
            >
          </div>
          <a-table
            class="mango-native-scroll-table"
            :data="cases"
            :columns="caseColumns"
            :loading="casesRegion.loading.value"
            :pagination="false"
            :scroll="{ x: 720, y: 440 }"
            :row-selection="{ type: 'checkbox', showCheckedAll: true }"
            :selected-keys="selectedCaseKeys"
            row-key="id"
            @selection-change="selectCases"
          >
            <template #case_priority="{ record }"
              ><a-tag size="small" :color="enumStore.colors[record.priority]">{{
                enumTitle(enumStore.case_level, record.priority)
              }}</a-tag></template
            >
          </a-table>
        </a-tab-pane>
        <a-tab-pane key="plans" :title="`测试计划（${plans.length}）`">
          <div class="mango-requirement-overview__toolbar">
            <span>每个计划仅执行一次，执行结果保存在计划用例快照中。</span>
            <a-button
              size="small"
              type="primary"
              :disabled="!suite"
              :loading="navigation === 'create-plan'"
              @click="createPlan"
              >新建测试计划</a-button
            >
          </div>
          <a-table
            class="mango-native-scroll-table"
            :data="plans"
            :columns="planColumns"
            :loading="plansRegion.loading.value"
            :pagination="false"
            :scroll="{ x: 720, y: 440 }"
            row-key="id"
          >
            <template #plan_name="{ record }"
              ><a-link :loading="navigation === 'plan'" @click="openPlan(record)">{{
                record.name
              }}</a-link></template
            >
            <template #plan_status="{ record }"
              ><a-tag size="small" :color="enumStore.colors[record.status]">{{
                enumTitle(enumStore.functional_test_plan_status, record.status)
              }}</a-tag></template
            >
            <template #plan_progress="{ record }">{{
              formatRate(record.execution_stats.progress)
            }}</template>
          </a-table>
        </a-tab-pane>
        <a-tab-pane key="defects" :title="`缺陷（${defects.length}）`">
          <a-table
            class="mango-native-scroll-table"
            :data="defects"
            :columns="defectColumns"
            :loading="defectsRegion.loading.value"
            :pagination="false"
            :scroll="{ x: 720, y: 440 }"
            row-key="id"
          >
            <template #defect_status="{ record }"
              ><a-tag size="small" :color="enumStore.colors[record.status]">{{
                enumTitle(enumStore.functional_test_defect_status, record.status)
              }}</a-tag></template
            >
          </a-table>
        </a-tab-pane>
        <a-tab-pane key="resources" :title="`资料（${resources.length}）`">
          <mango-panel-spin
            class="mango-requirement-overview__panel"
            :loading="resourcesRegion.loading.value"
          >
            <div
              v-if="
                !resources.length && !resourcesRegion.loading.value && !resourcesRegion.error.value
              "
              class="mango-empty-state"
              >暂无资料</div
            >
            <a-list v-else :data="resources" :bordered="false">
              <template #item="{ item }"
                ><a-list-item
                  ><span
                    class="mango-requirement-overview__resource"
                    :title="item.title || item.context_key"
                    >{{ item.title || item.context_key }}</span
                  ><template #extra>{{ item.update_time || '-' }}</template></a-list-item
                ></template
              >
            </a-list>
          </mango-panel-spin>
        </a-tab-pane>
      </a-tabs>
    </div>
  </a-drawer>
</template>

<script lang="ts" setup>
  import { computed, onActivated, onBeforeUnmount, onDeactivated, ref, watch } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import { useRoute, useRouter } from 'vue-router'
  import { useEnum } from '@/store/modules/get-enum'
  import useUserStore from '@/store/modules/user'
  import { formatModulePath, formatProjectProductPath } from '@/utils/business-format'
  import {
    getFunctionalContextResource,
    getFunctionalRequirementCases,
    getManualSuite,
    getRelatedFunctionalDefects,
    getRelatedFunctionalPlans,
    unbindFunctionalRequirementCases,
  } from '@/api/functional-test'
  import { useIterationRegion } from '../composables/useIterationRegion'
  import {
    iterationList,
    iterationObject,
    parseIterationDefect,
    parseIterationPlan,
    parseRequirementOverviewCase,
    parseRequirementOverviewResource,
    parseRequirementOverviewSuite,
  } from '../presentation'
  import {
    overviewCaseColumns as caseColumns,
    overviewPlanColumns as planColumns,
    overviewDefectColumns as defectColumns,
  } from './requirement-overview-config'
  import type {
    RequirementOverviewSuite,
    RequirementOverviewCase,
    RequirementOverviewResource,
    IterationPlan,
    IterationDefect,
  } from '../types'
  import type { IterationUserOption } from '../details/types'

  const props = withDefaults(
    defineProps<{
      visible: boolean
      suiteId?: number
      statusOptions?: IterationUserOption[]
      contextKey?: string
    }>(),
    { statusOptions: () => [], contextKey: '' }
  )
  const emit = defineEmits<{
    (event: 'update:visible', value: boolean): void
    (event: 'edit-schedule', suite: RequirementOverviewSuite): void
    (event: 'changed'): void
    (event: 'busy', value: boolean): void
  }>()
  const router = useRouter(),
    route = useRoute(),
    enumStore = useEnum(),
    user = useUserStore()
  const blocked = ref(false),
    unlinking = ref(false),
    unlinkError = ref(false),
    navigationError = ref(false)
  const navigation = ref<'workspace' | 'detail' | 'create-plan' | 'plan' | null>(null)
  const activeTab = ref('overview'),
    selectedCaseKeys = ref<number[]>([])
  watch(unlinking, (value) => emit('busy', value), { flush: 'sync' })
  let active = true,
    generation = 0
  let confirmation: ReturnType<typeof Modal.warning> | null = null
  const identity = computed(() =>
    JSON.stringify([
      route.fullPath,
      user.userId,
      user.roleId,
      user.token,
      user.selected_environment,
      props.contextKey,
    ])
  )
  const canRead = () =>
    active &&
    props.visible &&
    !blocked.value &&
    typeof props.suiteId === 'number' &&
    Number.isSafeInteger(props.suiteId) &&
    props.suiteId > 0
  const current = (version: number) => canRead() && version === generation
  function region<T>(initial: () => T, read: () => Promise<T>) {
    return useIterationRegion(initial, read, () => generation, canRead)
  }
  const suiteRegion = region<RequirementOverviewSuite | null>(
    () => null,
    async () => {
      const id = props.suiteId!,
        value = iterationList((await getManualSuite({ id })).data)
      if (value.length !== 1) throw Error('需求记录未找到')
      const saved = parseRequirementOverviewSuite(value[0])
      if (saved.id !== id) throw Error('需求记录不匹配')
      return saved
    }
  )
  const casesRegion = region(
    (): RequirementOverviewCase[] => [],
    async () =>
      iterationList((await getFunctionalRequirementCases(props.suiteId!)).data).map(
        parseRequirementOverviewCase
      )
  )
  const plansRegion = region(
    (): IterationPlan[] => [],
    async () =>
      iterationList(
        (await getRelatedFunctionalPlans({ requirement_version_id: props.suiteId })).data
      ).map(parseIterationPlan)
  )
  const defectsRegion = region(
    (): IterationDefect[] => [],
    async () =>
      iterationList(
        (await getRelatedFunctionalDefects({ requirement_version_id: props.suiteId })).data
      ).map(parseIterationDefect)
  )
  const resourcesRegion = region(
    (): RequirementOverviewResource[] => [],
    async () =>
      iterationList((await getFunctionalContextResource({ suite: props.suiteId })).data).map(
        parseRequirementOverviewResource
      )
  )
  const enumsRegion = region(
    () => false,
    async () => {
      await enumStore.getEnum()
      return true
    }
  )
  const regions = {
    suite: suiteRegion,
    cases: casesRegion,
    plans: plansRegion,
    defects: defectsRegion,
    resources: resourcesRegion,
    enums: enumsRegion,
  }
  const titles = {
    suite: '需求概览',
    cases: '来源用例',
    plans: '测试计划',
    defects: '缺陷',
    resources: '资料',
    enums: '枚举选项',
  }
  type RegionKey = 'suite' | 'cases' | 'plans' | 'defects' | 'resources' | 'enums'
  const regionErrors = computed(() =>
    (Object.keys(regions) as RegionKey[])
      .filter((key) => regions[key].error.value)
      .map((key) => ({ key, title: titles[key], loading: regions[key].loading.value }))
  )
  const suite = suiteRegion.data,
    cases = casesRegion.data,
    plans = plansRegion.data,
    defects = defectsRegion.data,
    resources = resourcesRegion.data
  const enumTitle = (options: IterationUserOption[] = [], value: unknown) =>
    options.find((item) => item.key === value)?.title || '-'
  const formatRate = (value: number) => `${Number.isFinite(value) ? value.toFixed(0) : '0'}%`
  function invalidate() {
    ++generation
    for (const item of Object.values(regions)) item.invalidate(true)
    selectedCaseKeys.value = []
    unlinkError.value = false
    navigationError.value = false
    confirmation?.close()
    confirmation = null
  }
  function close() {
    blocked.value = true
    invalidate()
    emit('update:visible', false)
  }
  function changeVisible(value: boolean) {
    if (!value) close()
  }
  async function loadAll() {
    if (canRead()) await Promise.allSettled(Object.values(regions).map((item) => item.load()))
  }
  function retryRegion(key: RegionKey) {
    return regions[key].load()
  }
  function selectCases(values: (string | number)[]) {
    if (!canRead() || unlinking.value) return
    selectedCaseKeys.value = [
      ...new Set(
        values.filter(
          (value): value is number =>
            typeof value === 'number' && cases.value.some((row) => row.id === value)
        )
      ),
    ]
  }
  function unlinkCases() {
    if (
      !canRead() ||
      unlinking.value ||
      casesRegion.loading.value ||
      casesRegion.error.value ||
      confirmation
    )
      return
    const ids = selectedCaseKeys.value.filter((id) => cases.value.some((row) => row.id === id))
    if (!ids.length) return
    const id = props.suiteId!,
      version = generation
    let dialog: ReturnType<typeof Modal.warning> | null = null
    dialog = Modal.warning({
      title: '确认取消关联',
      content: `将 ${ids.length} 条用例从当前需求中取消关联，用例资产本身仍会保留。`,
      hideCancel: false,
      onBeforeOk: async () => {
        if (
          !current(version) ||
          unlinking.value ||
          !ids.every((id) => cases.value.some((row) => row.id === id))
        )
          return false
        unlinking.value = true
        unlinkError.value = false
        try {
          const result = iterationObject(
            (await unbindFunctionalRequirementCases(id, [...ids])).data
          )
          if (!current(version)) return false
          if (
            typeof result.unbound_count !== 'number' ||
            !Number.isSafeInteger(result.unbound_count) ||
            result.unbound_count < 0
          )
            throw Error('取消关联未确认')
          casesRegion.invalidate()
          cases.value = cases.value.filter((row) => !ids.includes(row.id))
          selectedCaseKeys.value = []
          Message.success('已取消用例关联')
          emit('changed')
          void Promise.allSettled([suiteRegion.load(), casesRegion.load()])
          return true
        } catch {
          if (current(version)) unlinkError.value = true
          return false
        } finally {
          unlinking.value = false
        }
      },
      onBeforeCancel: () => !unlinking.value,
      onClose: () => {
        if (confirmation === dialog) confirmation = null
      },
    })
    confirmation = dialog
  }
  function editSchedule() {
    if (canRead() && suite.value && !suiteRegion.loading.value && !unlinking.value)
      emit('edit-schedule', suite.value)
  }
  async function navigate(
    kind: 'workspace' | 'detail' | 'create-plan' | 'plan',
    path: string,
    query: { id?: number; requirement_version?: number }
  ) {
    if (!canRead() || !suite.value || navigation.value) return
    const version = generation
    navigation.value = kind
    navigationError.value = false
    try {
      const failure = await router.push({ path, query })
      if (current(version)) {
        if (failure) navigationError.value = true
        else close()
      }
    } catch {
      if (current(version)) navigationError.value = true
    } finally {
      navigation.value = null
    }
  }
  function openWorkspace() {
    return navigate('workspace', '/functional-test/suite/details', { id: props.suiteId })
  }
  function openDetail() {
    return navigate('detail', '/functional-test/requirement/details', { id: props.suiteId })
  }
  function createPlan() {
    return navigate('create-plan', '/functional-test/plan/index', {
      requirement_version: props.suiteId,
    })
  }
  function openPlan(row: IterationPlan) {
    if (plans.value.includes(row))
      return navigate('plan', '/functional-test/plan/details', { id: row.id })
  }
  watch(
    identity,
    () => {
      if (props.visible && !blocked.value) close()
      else invalidate()
    },
    { flush: 'sync' }
  )
  watch(
    cases,
    () => {
      selectedCaseKeys.value = selectedCaseKeys.value.filter((id) =>
        cases.value.some((row) => row.id === id)
      )
    },
    { flush: 'sync' }
  )
  watch(
    [() => props.visible, () => props.suiteId],
    () => {
      invalidate()
      blocked.value = false
      activeTab.value = 'overview'
      if (canRead()) void loadAll()
    },
    { immediate: true, flush: 'sync' }
  )
  onDeactivated(() => {
    active = false
    close()
  })
  onActivated(() => {
    if (active) return
    active = true
    if (canRead()) void loadAll()
  })
  onBeforeUnmount(() => {
    active = false
    blocked.value = true
    invalidate()
  })
</script>

<style lang="less" scoped>
  .mango-requirement-overview__title,
  .mango-requirement-overview__resource {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .mango-requirement-overview__toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--m-page-gap);
    margin-bottom: var(--m-page-gap);
    color: var(--m-muted);
  }
  .mango-requirement-overview__notice {
    margin-bottom: var(--m-page-gap);
  }
  .mango-requirement-overview__panel {
    min-height: 160px;
  }
</style>
