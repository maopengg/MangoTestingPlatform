<template>
  <TableBody plain class="mango-detail-workbench-page" :sticky-horizontal-scroll="false">
    <template #header><TableHeader title="研发协同 / 测试计划" /></template>
    <template #default>
      <ProjectProductNavigationWorkbench
        ref="navigationCreateRef"
        contained-body
        :sticky-horizontal-scroll="false"
        :model-value="navigationProjectProduct"
        @filter-change="onNavigationFilterChange"
        @search="search"
        @reset-search="reset"
      >
        <template #search>
          <a-form :model="filters" layout="inline" @keyup.enter="search">
            <a-form-item label="计划类型"
              ><a-select
                v-model="filters.scope_type"
                :options="scopeOptions"
                :field-names="fieldNames"
                :loading="enumsLoading"
                multiple
                :max-tag-count="1"
                allow-clear
                placeholder="请选择计划类型"
                @change="search"
            /></a-form-item>
            <a-form-item label="计划名称"
              ><a-input
                v-model="filters.name"
                allow-clear
                placeholder="请输入计划名称"
                @blur="search"
                @clear="search"
            /></a-form-item>
            <a-form-item label="状态"
              ><a-select
                v-model="filters.status"
                :options="statusOptions"
                :field-names="fieldNames"
                :loading="enumsLoading"
                multiple
                :max-tag-count="1"
                allow-clear
                placeholder="请选择状态"
                @change="search"
            /></a-form-item>
          </a-form>
        </template>
        <template #toolbar
          ><a-space wrap>
            <a-button size="small" :loading="loading" @click="loadPlans">刷新</a-button>
            <a-button size="small" type="primary" @click="openEditor()">新建计划</a-button>
          </a-space></template
        >
        <div class="mango-plan-page__table">
          
          
          
          <MangoRequestFeedback v-if="navigationError" :message="&quot;计划详情打开失败，请重新点击进入用例。&quot;" />
          <a-table
            class="mango-native-scroll-table"
            :data="rows"
            :columns="planColumns"
            :loading="loading"
            :pagination="false"
            :scroll="{ x: 2140, y: '100%' }"
            row-key="id"
          >
            <template #name="{ record }"
              ><a-link :loading="navigatingId === record.id" @click="goDetail(record)">{{
                record.name
              }}</a-link></template
            >
            <template #project_product="{ record }">{{
              formatProjectProductPath(record.project_product)
            }}</template>
            <template #scope_type="{ record }"
              ><a-tag :color="enumStore.colors[record.scope_type]">{{
                enumTitle(scopeOptions, record.scope_type)
              }}</a-tag></template
            >
            <template #scope_ref="{ record }">{{
              record.scope_type === 0
                ? `${
                    record.requirement_version?.requirement_name ||
                    record.requirement_version?.requirement?.name ||
                    '-'
                  } · V${record.requirement_version?.version_no || '-'}`
                : record.scope_type === 1
                ? record.iteration?.name || '-'
                : record.scope_ref || '-'
            }}</template>
            <template #status="{ record }"
              ><a-tag :color="enumStore.colors[record.status]">{{
                enumTitle(statusOptions, record.status)
              }}</a-tag></template
            >
            <template #execution_progress="{ record }"
              ><div v-if="record.case_count" class="mango-plan-page__metric">
                <a-progress
                  :percent="record.execution_stats.progress / 100"
                  size="small"
                  :show-text="false"
                />
                <span
                  >{{ record.execution_stats.executed }}/{{ record.execution_stats.total }}</span
                > </div
              ><span v-else>-</span></template
            >
            <template #pass_rate="{ record }"
              ><a-tooltip v-if="record.case_count" :content="resultSummary(record.execution_stats)"
                ><span>{{ formatRate(record.execution_stats.pass_rate) }}</span></a-tooltip
              ><span v-else>-</span></template
            >
            <template #owner="{ record }">{{ record.owner?.name || '-' }}</template>
            <template #actions="{ record }"
              ><MangoTableActions
                :actions="[
                  {
                    label: '进入用例',
                    loading: navigatingId === record.id,
                    disabled: isBusy(record.id),
                    onClick: () => goDetail(record),
                  },
                  { label: '编辑', disabled: isBusy(record.id), onClick: () => openEditor(record) },
                  {
                    label: '删除',
                    danger: true,
                    loading: deletingIds.has(record.id),
                    disabled: isBusy(record.id),
                    onClick: () => removePlan(record),
                  },
                ]"
            /></template>
          </a-table>
        </div>
        <template #footer><TableFooter :pagination="pagination" /></template>
      </ProjectProductNavigationWorkbench>
    </template>
  </TableBody>
  <PlanEditor
    ref="editorRef"
    :context-key="contextKey"
    :users="userOptions"
    :scope-options="scopeOptions"
    :users-loading="usersLoading"
    :users-error="usersError"
    :enums-loading="enumsLoading"
    :enums-error="enumsError"
    :busy-ids="[...confirmations.keys(), ...deletingIds]"
    @retry-users="loadUsers"
    @retry-enums="loadEnums"
    @saved="onSaved"
  />
</template>
<script lang="ts" setup>
  import { requestFailureMessage, reportLoadError } from '@/utils/load-error'
  import {
    computed,
    nextTick,
    onActivated,
    onBeforeUnmount,
    onDeactivated,
    onMounted,
    reactive,
    ref,
    shallowRef,
    watch,
  } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import { useRoute, useRouter } from 'vue-router'
  import TableBody from '@/components/table/TableBody.vue'
  import TableHeader from '@/components/table/TableHeader.vue'
  import TableFooter from '@/components/table/TableFooter.vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import { useEnum } from '@/store/modules/get-enum'
  import useUserStore from '@/store/modules/user'
  import { usePagination } from '@/hooks/table'
  import { getUserName } from '@/api/user/user'
  import { formatProjectProductPath } from '@/utils/business-format'
  import { deleteFunctionalPlan, getFunctionalPlans } from '@/api/functional-test'
  import type { NavigationCreateSource } from '@/utils/navigation-create-defaults'
  import PlanEditor from './components/PlanEditor.vue'
  import { planColumns } from './config'
  import { planList, planObject } from './presentation'
  import { parsePlanListRow, planSelectionId } from './list-form'
  import type { PlanListRow, PlanEditorHandle } from './types'

  const navigationCreateRef = ref<NavigationCreateSource | null>(null),
    editorRef = ref<PlanEditorHandle | null>(null)
  const router = useRouter(),
    route = useRoute(),
    enumStore = useEnum(),
    user = useUserStore()
  const fieldNames = { value: 'key', label: 'title' }
  const rows = shallowRef<PlanListRow[]>([])
  const userOptions = shallowRef<Array<{ key: number | string; title: string }>>([])
  const scopeOptions = computed(() => enumStore.functional_test_plan_scope_type || []),
    statusOptions = computed(() => enumStore.functional_test_plan_status || [])
  const loading = ref(false),
    usersLoading = ref(false),
    enumsLoading = ref(false)
  const readError = ref(false),
    usersError = ref(false),
    enumsError = ref(false)
  const filters = reactive({
    name: '',
    scope_type: [] as Array<number | string>,
    status: [] as Array<number | string>,
  })
  const navigationProjectProduct = ref<number | null>(null)
  const appliedQuery = shallowRef<Record<string, unknown>>({})
  const identityKey = computed(() =>
    JSON.stringify([user.userId, user.roleId, user.token, user.selected_environment])
  )
  const contextKey = computed(() => JSON.stringify([route.fullPath, identityKey.value]))
  let active = true,
    mounted = false,
    generation = 0,
    listSequence = 0,
    userSequence = 0,
    enumSequence = 0,
    previousIdentity = identityKey.value
  const available = () => active && route.path === '/functional-test/plan/index'
  const current = (version: number) => available() && generation === version
  const pagination = usePagination(loadPlans, loading)
  async function loadPlans() {
    if (!available()) {
      loading.value = false
      return false
    }
    const version = generation,
      sequence = ++listSequence
    const valid = () => current(version) && listSequence === sequence
    loading.value = true
    readError.value = false
    try {
      const response = await getFunctionalPlans({
        ...appliedQuery.value,
        page: pagination.page,
        pageSize: pagination.pageSize,
      })
      if (!valid()) return false
      const parsed = planList(response.data).map(parsePlanListRow)
      if (
        typeof response.totalSize !== 'number' ||
        !Number.isSafeInteger(response.totalSize) ||
        response.totalSize < 0
      )
        throw Error('分页总数无效')
      rows.value = parsed
      pagination.setTotalSize(response.totalSize)
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
      sequence = ++userSequence,
      valid = () => current(version) && userSequence === sequence
    usersLoading.value = true
    usersError.value = false
    try {
      const data = (await getUserName()).data
      if (!valid()) return false
      userOptions.value = planList(data).map((value) => {
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
      sequence = ++enumSequence,
      valid = () => current(version) && enumSequence === sequence
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
  function search() {
    const query: Record<string, unknown> = {}
    if (navigationProjectProduct.value !== null)
      query.project_product = navigationProjectProduct.value
    if (filters.name !== '') query.name = filters.name
    for (const key of ['scope_type', 'status'] as const)
      if (filters[key].length) query[`${key}__in`] = filters[key].join(',')
    appliedQuery.value = query
    pagination.page = 1
    return loadPlans()
  }
  function reset() {
    Object.assign(filters, { scope_type: [], name: '', status: [] })
    return search()
  }
  function onNavigationFilterChange(filter: { projectProduct: number | string | null }) {
    navigationProjectProduct.value = planSelectionId(filter.projectProduct)
    return search()
  }
  const deletingIds = reactive(new Set<number>())
  const confirmations = reactive(new Map<number, ReturnType<typeof Modal.warning>>())
  const isBusy = (id: number) =>
    deletingIds.has(id) || confirmations.has(id) || !!editorRef.value?.isSaving(id)
  const owned = (record: PlanListRow) => available() && rows.value.includes(record)
  function openEditor(record: PlanListRow | null = null) {
    if (!available() || (record && (!owned(record) || isBusy(record.id)))) return
    editorRef.value?.open(record, {
      productId: planSelectionId(navigationCreateRef.value?.getCreateDefaults().projectProduct),
    })
  }
  function onSaved() {
    if (available()) {
      ++listSequence
      void loadPlans()
    }
  }
  function removePlan(record: PlanListRow) {
    if (!owned(record) || isBusy(record.id)) return
    const id = record.id,
      name = record.name,
      version = generation
    const release = () => confirmations.delete(id)
    const dialog = Modal.warning({
      title: '删除测试计划',
      content: `确认删除「${name}」及其计划用例和执行结果？`,
      hideCancel: false,
      onCancel: release,
      onBeforeCancel: () => !deletingIds.has(id),
      onBeforeOk: async () => {
        if (!current(version) || deletingIds.has(id) || editorRef.value?.isSaving(id)) return false
        deletingIds.add(id)
        try {
          await deleteFunctionalPlan(id)
          if (!current(version)) return false
          ++listSequence
          const displayed = rows.value.some((row) => row.id === id)
          rows.value = rows.value.filter((row) => row.id !== id)
          if (displayed) pagination.setTotalSize(Math.max(0, pagination.pageCount - 1))
          if (!rows.value.length && pagination.page > 1) --pagination.page
          release()
          Message.success('删除成功')
          void loadPlans()
          return true
        } catch {
          if (current(version)) Message.error('删除失败，请重试')
          return false
        } finally {
          deletingIds.delete(id)
        }
      },
    })
    confirmations.set(id, dialog)
  }
  const navigatingId = ref<number | null>(null),
    navigationError = ref(false)
  async function goDetail(record: PlanListRow) {
    if (!owned(record) || isBusy(record.id) || navigatingId.value !== null) return
    const version = generation
    navigatingId.value = record.id
    navigationError.value = false
    try {
      const failure = await router.push({
        path: '/functional-test/plan/details',
        query: { id: record.id },
      })
      if (failure && current(version)) navigationError.value = true
    } catch (requestFailure) {
      if (current(version)) navigationError.value = requestFailureMessage(requestFailure, true, "计划详情打开失败，请重新点击进入用例。")
    } finally {
      navigatingId.value = null
    }
  }
  const routeCreates = new Set<string>()
  async function openRouteCreate() {
    if (!available() || route.query.create !== '1' || routeCreates.has(route.fullPath)) return
    const version = generation,
      path = route.fullPath
    await nextTick()
    if (
      !current(version) ||
      path !== route.fullPath ||
      routeCreates.has(path) ||
      !editorRef.value ||
      editorRef.value.isSaving()
    )
      return
    routeCreates.add(path)
    editorRef.value.open(null, {
      productId:
        typeof route.query.project_product === 'string'
          ? planSelectionId(route.query.project_product)
          : null,
      requirementId:
        typeof route.query.requirement_version === 'string'
          ? planSelectionId(route.query.requirement_version)
          : null,
    })
  }
  const enumTitle = (options: Array<{ key: number | string; title: string }>, value: number) =>
    options.find((item) => Number(item.key) === value)?.title || '-'
  const formatRate = (value: number) => `${value.toFixed(2).replace(/\.00$/, '')}%`
  const resultSummary = (stats: PlanListRow['execution_stats']) =>
    `通过 ${stats.passed}，失败 ${stats.failed}，阻塞 ${stats.blocked}，跳过 ${stats.skipped}`
  function invalidate() {
    ++generation
    ++listSequence
    ++userSequence
    ++enumSequence
    rows.value = []
    userOptions.value = []
    pagination.setTotalSize(0)
    loading.value = false
    usersLoading.value = false
    enumsLoading.value = false
    readError.value = false
    usersError.value = false
    enumsError.value = false
    navigationError.value = false
    for (const dialog of confirmations.values()) dialog.close()
    confirmations.clear()
  }
  function loadAll() {
    return Promise.allSettled([loadPlans(), loadUsers(), loadEnums()])
  }
  watch(
    () => editorRef.value?.isSaving(),
    (pending) => {
      if (!pending && mounted) void openRouteCreate()
    }
  )
  watch(
    contextKey,
    () => {
      invalidate()
      pagination.page = 1
      if (identityKey.value !== previousIdentity) {
        previousIdentity = identityKey.value
        Object.assign(filters, { name: '', scope_type: [], status: [] })
        navigationProjectProduct.value = null
        appliedQuery.value = {}
      }
      if (mounted) {
        void loadAll()
        void openRouteCreate()
      }
    },
    { flush: 'sync' }
  )
  onMounted(() => {
    mounted = true
    void loadAll()
    void openRouteCreate()
  })
  onDeactivated(() => {
    active = false
    invalidate()
  })
  onActivated(() => {
    if (active) return
    active = true
    if (mounted) {
      void loadAll()
      void openRouteCreate()
    }
  })
  onBeforeUnmount(() => {
    active = false
    mounted = false
    invalidate()
  })
</script>
<style lang="less" scoped>
  .mango-plan-page__table {
    display: flex;
    flex: 1;
    min-width: 0;
    min-height: 0;
    flex-direction: column;
    gap: var(--m-page-gap);
    overflow: hidden;
  }
  .mango-plan-page__metric {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .mango-plan-page__metric :deep(.arco-progress) {
    min-width: 92px;
    flex: 1;
  }
  .mango-plan-page__metric span {
    flex: none;
    color: var(--m-muted);
  }
</style>
