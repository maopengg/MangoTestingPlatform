<template>
  <TableBody plain class="mango-detail-workbench-page">
    <template #header><TableHeader title="评测中心 / 测试用例" /></template>
    <template #default>
      <ProjectProductNavigationWorkbench
        contained-body
        show-modules
        :model-value="filters.project_product"
        :module-value="filters.module"
        :reset-key="resetKey"
        @filter-change="sidebarChanged"
        @search="autoSearch.run"
        @reset-search="autoSearch.cancel(); reset(); autoSearch.sync()"
      >
        <template #search
          ><a-form :model="filters" layout="inline" @keyup.enter="autoSearch.run">
            <a-form-item label="用例名称"
              ><a-input @blur="autoSearch.schedule" @clear="autoSearch.schedule" @mouseleave="autoSearch.schedule" v-model="filters.name" allow-clear placeholder="搜索用例"
            /></a-form-item>
            <a-form-item label="状态"
              ><a-select @change="autoSearch.schedule"
                v-model="filters.status"
                :options="caseStatusOptions"
                multiple
                :max-tag-count="1"
                allow-clear
            /></a-form-item>
            <a-form-item label="目标类型"
              ><a-select @change="autoSearch.schedule"
                v-model="filters.target_type"
                :options="targetTypeOptions"
                multiple
                :max-tag-count="1"
                allow-clear
            /></a-form-item> </a-form
        ></template>
        <template #toolbar
          ><a-button type="primary" size="small" @click="openCreate">新建用例</a-button></template
        >
        <a-table
          class="mango-native-scroll-table"
          :columns="caseColumns"
          :data="rows"
          :loading="loading"
          :pagination="false"
          :scroll="{ x: CASE_SCROLL_X, y: '100%' }"
          row-key="id"
          size="small"
        >
          <template #columns
            ><a-table-column v-for="column in caseColumns" :key="column.key" v-bind="column"
              ><template #cell="{ record }">
                <span v-if="column.key === 'index'">{{ record.id }}</span>
                <span v-else-if="column.key === 'dataset_version_no'">{{
                  formatVersion(record.dataset_version_no)
                }}</span>
                <a-link v-else-if="column.key === 'name'" @click="details(record)">{{
                  record.name
                }}</a-link>
                <span v-else-if="column.key === 'description'">{{
                  record.description || '-'
                }}</span>
                <span v-else-if="column.key === 'project_product'">{{
                  formatProjectProductPath(record.project_product_data)
                }}</span>
                <span v-else-if="column.key === 'module'">{{
                  formatModulePath(record.module_data)
                }}</span>
                <a-tag
                  v-else-if="column.key === 'latest'"
                  size="small"
                  :color="statusColor(record.latest_result?.status)"
                  >{{
                    record.latest_result?.status
                      ? enumTitle('evaluation_execution_status', record.latest_result.status)
                      : '尚未执行'
                  }}</a-tag
                >
                <a-tag
                  v-else-if="column.key === 'target_type'"
                  size="small"
                  :color="
                    getEnumTagColor(
                      enumStore.evaluation_target_type,
                      record.target_type,
                      enumStore.colors
                    )
                  "
                  >{{
                    record.target_type
                      ? enumTitle('evaluation_target_type', record.target_type)
                      : '待配置'
                  }}</a-tag
                >
                <span v-else-if="column.key === 'score'">{{
                  record.latest_result?.average_score ?? '-'
                }}</span>
                <span v-else-if="column.key === 'valid_rate'">{{
                  record.latest_result?.valid_rate == null
                    ? '-'
                    : `${(record.latest_result.valid_rate * 100).toFixed(1)}%`
                }}</span>
                <span v-else-if="column.key === 'finished_at'">{{
                  record.latest_result?.finished_at || '-'
                }}</span>
                <template v-else-if="column.key === 'status'">
                  <a-switch
                    :model-value="record.status === 'enabled'"
                    :loading="statusPending.has(record.id)"
                    :disabled="isBusy(record.id)"
                    :before-change="(checked) => toggleStatus(record, checked)"
                  />
                </template>
                <MangoTableActions
                  v-else-if="column.key === 'actions'"
                  :actions="[
                    {
                      label: '执行',
                      disabled: record.status !== 'enabled' || isBusy(record.id),
                      loading: executing.has(record.id),
                      onClick: () => execute(record),
                    },
                    { label: '详情', onClick: () => details(record) },
                    { label: '历史结果', onClick: () => details(record, true) },
                    {
                      label: '编辑信息',
                      disabled: isBusy(record.id),
                      onClick: () => openEdit(record),
                    },
                    {
                      label: '复制',
                      disabled: isBusy(record.id),
                      loading: copying.has(record.id),
                      onClick: () => copy(record),
                    },
                    {
                      label: '删除',
                      danger: true,
                      disabled: isBusy(record.id),
                      loading: deleting.has(record.id),
                      onClick: () => remove(record),
                    },
                  ]"
                />
                <span v-else-if="column.key === 'dataset_name'">{{
                  record.dataset_name || '-'
                }}</span>
              </template></a-table-column
            ></template
          >
        </a-table>
        <template #footer><TableFooter :pagination="pagination" /></template>
      </ProjectProductNavigationWorkbench>
    </template>
  </TableBody>
  <CaseEditor ref="editor" @saved="load" />
</template>
<script setup lang="ts">
  import { useDebouncedSearch } from '@/hooks/useDebouncedSearch'

import { reportLoadError } from '@/utils/load-error'

  import { computed, reactive, ref } from 'vue'
  import { useRouter } from 'vue-router'
  import { Message, Modal } from '@arco-design/web-vue'
  import type { ModalReturn } from '@arco-design/web-vue'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import {
    formatModulePath,
    formatProjectProductPath,
    getEnumTagColor,
  } from '@/utils/business-format'
  import { useEnum } from '@/store/modules/get-enum'
  import useUserStore from '@/store/modules/user'
  import {
    getEvaluationCases,
    updateEvaluationCase,
    deleteEvaluationCase,
    copyEvaluationCase,
    executeEvaluationCase,
  } from '@/api/evaluation'
  import CaseEditor from '../components/CaseEditor.vue'
  import { caseColumns, CASE_SCROLL_X } from './config'
  import { createCaseFilters, navigationId, caseListQuery } from './form'
  import { useEvaluationEnums } from '../components/useEvaluationEnums'
  import { useEvaluationScope } from '../composables/useEvaluationScope'
  import { formatVersion } from '../components/presentation'
  import type {
    CaseListRecord,
    CaseFilters,
    CaseNavigationFilter,
    CaseEditorHandle,
    ResultPage,
  } from '../types'
  const { title: enumTitle, color: statusColor, options: enumOptions } = useEvaluationEnums(),
    enumStore = useEnum()
  const caseStatusOptions = computed(() => enumOptions('evaluation_case_status')),
    targetTypeOptions = computed(() => enumOptions('evaluation_target_type'))
  const user = useUserStore(),
    router = useRouter(),
    editor = ref<Pick<CaseEditorHandle, 'open'> | null>(null)
  const rows = ref<CaseListRecord[]>([]),
    loading = ref(false),
    loadError = ref(false),
    resetKey = ref(0)
  const copying = reactive(new Set<number>()),
    executing = reactive(new Set<number>()),
    statusPending = reactive(new Set<number>()),
    deleting = reactive(new Set<number>())
  const keys = new Map<string, string>(),
    filters: CaseFilters = reactive(createCaseFilters()),
    moduleIds = ref<number[]>([])
  const pagination = reactive({
    page: 1,
    pageSize: 10,
    pageCount: 0,
    pageSizes: [10, 20, 50],
    showSizePicker: true,
    onChange: () => load(),
  })
  let requestId = 0,
    confirmation: ModalReturn | null = null
  let identity = [user.userId, user.roleId, user.token],
    environment = user.selected_environment
  const scope = useEvaluationScope(
    () => [],
    invalidate,
    () => {
      void load()
    }
  )
  function invalidate() {
    ++requestId
    rows.value = []
    loading.value = false
    loadError.value = false
    pagination.pageCount = 0
    confirmation?.close()
    confirmation = null
    const nextIdentity = [user.userId, user.roleId, user.token]
    if (identity.some((value, index) => value !== nextIdentity[index])) {
      Object.assign(filters, createCaseFilters())
      moduleIds.value = []
      resetKey.value++
      pagination.page = 1
    }
    if (environment !== user.selected_environment) pagination.page = 1
    identity = nextIdentity
    environment = user.selected_environment
  }
  async function load() {
    if (!scope.isActive()) return false
    const request = ++requestId,
      version = scope.snapshot(),
      query = caseListQuery(
        filters,
        moduleIds.value,
        pagination.page,
        pagination.pageSize,
        user.selected_environment
      )
    loading.value = true
    loadError.value = false
    try {
      const response: ResultPage<CaseListRecord> = await getEvaluationCases(query)
      if (!scope.current(version) || request !== requestId) return false
      rows.value = response.data?.items || []
      pagination.pageCount = response.data?.count || 0
      return true
    } catch (loadFailure0) {
      if (scope.current(version) && request === requestId) (reportLoadError(loadFailure0, "加载失败，请重试", false), loadError.value = true)
      return false
    } finally {
      if (request === requestId) loading.value = false
    }
  }
  function search() {
    pagination.page = 1
    return load()
  }
  function sidebarChanged(filter: CaseNavigationFilter) {
    filters.project_product = navigationId(filter.projectProduct)
    filters.module = navigationId(filter.module)
    moduleIds.value = (filter.moduleIds || [])
      .map(navigationId)
      .filter((id): id is number => id !== null)
    return search()
  }
  function reset() {
    Object.assign(filters, createCaseFilters())
    moduleIds.value = []
    resetKey.value++
    return search()
  }
  function details(record: CaseListRecord, history = false, execution?: number) {
    if (scope.isActive())
      void router.push({
        path: '/evaluation/case/details',
        query: {
          id: record.id,
          ...(history ? { tab: 'history' } : {}),
          ...(execution ? { execution } : {}),
        },
      })
  }
  function isBusy(id: number) {
    return copying.has(id) || executing.has(id) || statusPending.has(id) || deleting.has(id)
  }
  function openCreate() {
    if (scope.isActive())
      void editor.value?.open(undefined, filters.project_product, filters.module)
  }
  function openEdit(record: CaseListRecord) {
    if (scope.isActive() && !isBusy(record.id)) void editor.value?.open(record.id)
  }
  async function toggleStatus(record: CaseListRecord, checked = record.status !== 'enabled') {
    if (!scope.isActive() || isBusy(record.id)) return false
    const id = record.id,
      version = scope.snapshot(),
      status = checked ? 'enabled' : 'draft'
    statusPending.add(id)
    ++requestId
    loading.value = false
    try {
      const response: { data?: { status?: string } } = await updateEvaluationCase({ id, status })
      if (!scope.current(version)) return false
      const target = rows.value.find((item) => item.id === id)
      if (target) target.status = response.data?.status || status
      await load()
      return true
    } catch {
      return false
    } finally {
      statusPending.delete(id)
    }
  }
  async function execute(record: CaseListRecord) {
    if (!scope.isActive() || isBusy(record.id) || record.status !== 'enabled') return false
    if (!user.selected_environment) {
      Message.warning('请先选择顶部测试环境')
      return false
    }
    const id = record.id,
      version = scope.snapshot(),
      environment = user.selected_environment,
      keyScope = `${user.userId}:${user.roleId}:${id}:${environment}`
    if (!keys.has(keyScope)) keys.set(keyScope, crypto.randomUUID())
    const key = keys.get(keyScope)!
    executing.add(id)
    try {
      const response: { data: { id: number } } = await executeEvaluationCase(
        id,
        { test_env: Number(environment) },
        key
      )
      if (keys.get(keyScope) === key) keys.delete(keyScope)
      if (!scope.current(version)) return false
      Message.success('Case 已提交执行')
      details(record, false, response.data.id)
      return true
    } catch {
      return false
    } finally {
      executing.delete(id)
    }
  }
  async function copy(record: CaseListRecord) {
    if (!scope.isActive() || isBusy(record.id)) return false
    const id = record.id,
      version = scope.snapshot()
    copying.add(id)
    try {
      await copyEvaluationCase(id)
      if (!scope.current(version)) return false
      Message.success('已复制为草稿')
      await load()
      return true
    } catch {
      return false
    } finally {
      copying.delete(id)
    }
  }
  function remove(record: CaseListRecord) {
    if (!scope.isActive() || isBusy(record.id) || confirmation) return
    const id = record.id,
      name = record.name,
      version = scope.snapshot()
    const dialog = Modal.warning({
      title: '删除 Case',
      content: `确定删除“${name}”？存在执行历史的 Case 受删除保护。`,
      hideCancel: false,
      onBeforeOk: async () => {
        if (!scope.current(version) || confirmation !== dialog || isBusy(id)) return false
        deleting.add(id)
        try {
          await deleteEvaluationCase(id)
          if (scope.current(version)) {
            if (rows.value.length === 1 && rows.value[0].id === id && pagination.page > 1)
              pagination.page--
            rows.value = rows.value.filter((item) => item.id !== id)
            await load()
          }
          return true
        } catch {
          return false
        } finally {
          deleting.delete(id)
        }
      },
      onClose: () => {
        if (confirmation === dialog) confirmation = null
      },
    })
    confirmation = dialog
  }
  scope.start()

  const autoSearch = useDebouncedSearch(search, () => filters)
</script>
