<template>
  <TableBody
    ref="tableBody"
    plain
    class="mango-detail-workbench-page"
    :sticky-horizontal-scroll="false"
  >
    <template #header>
      <TableHeader title="接口管理" />
    </template>

    <template #default>
      <ProjectProductNavigationWorkbench
        ref="navigationCreateRef"
        contained-body
        show-modules
        :show-toolbar="false"
        :module-value="getConditionValue('module')"
        :model-value="getConditionValue('project_product')"
        :reset-key="sidebarResetKey"
        @filter-change="onSidebarFilterChange"
        @search="onSearchRefresh"
        @reset-search="onResetSearch"
      >
        <template #search>
          <ApiInfoSearchFilters
            :items="headerConditionItems"
            :user-list="userOptions"
            :users-loading="userOptionsLoading"
            :enum-store="enumStore"
            :field-names="fieldNames"
            :project-product-id="getConditionValue('project_product')"
            @search="onSearchRefresh"
          />
        </template>
        <template #tabs>
          <a-tabs
            class="mango-api-info-tabs mango-tabs-nav-only"
            :active-key="activeProtocol"
            @tab-click="(key) => switchProtocol(key)"
          >
            <template #extra>
              <a-space>
                <a-button
                  v-if="isStandardCreateProtocol"
                  size="small"
                  type="primary"
                  @click="onAdd(0)"
                  data-testid="qa-views-apitest-info-button-新增"
                >
                  新增
                </a-button>
                <a-button
                  v-if="activeProtocol === 'grpc'"
                  size="small"
                  type="primary"
                  @click="openGrpcImport"
                  data-testid="qa-views-apitest-info-button-导入grpc-method"
                >
                  导入gRPC Method
                </a-button>
                <a-button
                  v-if="activeProtocol === 'mcp'"
                  size="small"
                  type="primary"
                  @click="onAdd(0)"
                  data-testid="qa-views-apitest-info-button-mcp工具"
                >
                  新增 MCP 接口
                </a-button>
                <a-button
                  v-if="isHttpProtocol"
                  type="primary"
                  size="small"
                  @click="onAdd(1)"
                  data-testid="qa-views-apitest-info-button-导入"
                  >导入</a-button
                >
                <a-button
                  v-if="isHttpProtocol"
                  size="small"
                  type="primary"
                  :loading="recordingLoading"
                  @click="onBatchUpload"
                  data-testid="qa-views-apitest-info-button-录制"
                  >录制</a-button
                >
                <a-button
                  v-if="isHttpProtocol"
                  size="small"
                  type="primary"
                  @click="showBatchImportModal"
                  data-testid="qa-views-apitest-info-button-批量导入"
                  >批量导入</a-button
                >
                <a-button
                  size="small"
                  status="success"
                  :loading="batchRunning"
                  :disabled="caseRunning && !batchRunning"
                  @click="onConcurrency"
                  data-testid="qa-views-apitest-info-button-批量执行"
                  >批量执行
                </a-button>
                <a-button
                  size="small"
                  status="danger"
                  :loading="deletingIds.size > 0"
                  @click="onDelete(null)"
                  data-testid="qa-views-apitest-info-button-批量删除"
                  >批量删除</a-button
                >
              </a-space>
            </template>
            <a-tab-pane key="all" title="全部" data-testid="qa-views-apitest-info-tab-pane-全部" />
            <a-tab-pane v-for="item in protocolTabs" :key="item.value" :title="item.label" />
          </a-tabs>
        </template>
        <StickyHorizontalTable :scroll-x="2090">
          <a-table
            :bordered="false"
            :columns="tableColumns"
            :data="rows"
            :loading="table.tableLoading.value"
            :pagination="false"
            :row-selection="{ selectedRowKeys, showCheckedAll }"
            :rowKey="rowKey"
            :scroll="{ x: 2090, y: '100%' }"
            @selection-change="onSelectionChange"
          >
            <template #columns>
              <a-table-column
                v-for="item of tableColumns"
                :key="item.key"
                :align="item.align"
                :data-index="item.key"
                :ellipsis="item.ellipsis"
                :fixed="item.fixed"
                :title="item.title"
                :tooltip="item.tooltip"
                :width="item.width"
              >
                <template v-if="item.key === 'index'" #cell="{ record }">
                  {{ record.id }}
                </template>
                <template v-else-if="item.key === 'client'" #cell="{ record }">
                  <a-tag
                    :color="
                      enumStore.colors[record.project_product?.api_client_type ?? -1] || 'gray'
                    "
                    size="small"
                    >{{
                      enumStore.api_client?.find(
                        (option) =>
                          String(option.key) === String(record.project_product?.api_client_type)
                      )?.title || '-'
                    }}
                  </a-tag>
                </template>
                <template v-else-if="item.key === 'method'" #cell="{ record }">
                  <a-tag :color="enumStore.colors[record.method]" size="small">
                    {{
                      enumStore.method?.find(
                        (option) => String(option.key) === String(record.method)
                      )?.title || '-'
                    }}
                  </a-tag>
                </template>
                <template v-else-if="item.key === 'protocol_type'" #cell="{ record }">
                  <a-tag :color="protocolTagColor(record.protocol_type)" size="small">
                    {{ protocolTagText(record.protocol_type) }}
                  </a-tag>
                </template>
                <template v-else-if="item.key === 'status'" #cell="{ record }">
                  <a-tag :color="enumStore.status_colors[record.status]" size="small"
                    >{{
                      enumStore.task_status?.find(
                        (option) => String(option.key) === String(record.status)
                      )?.title || '-'
                    }}
                  </a-tag>
                </template>
                <template v-else-if="item.key === 'publication_status'" #cell="{ record }">
                  <a-tag
                    :color="
                      getApiInfoPublicationMeta(
                        record.publication_status,
                        record.published_version_label,
                        record.has_unpublished_changes
                      ).color
                    "
                    size="small"
                  >
                    {{
                      getApiInfoPublicationMeta(
                        record.publication_status,
                        record.published_version_label,
                        record.has_unpublished_changes
                      ).label
                    }}
                  </a-tag>
                </template>
                <template v-else-if="item.key === 'project_product'" #cell="{ record }">
                  {{ formatProjectProductPath(record.project_product) }}
                </template>
                <template v-else-if="item.key === 'module'" #cell="{ record }">
                  {{ formatModulePath(record.module) }}
                </template>
                <template v-else-if="item.key === 'update_user'" #cell="{ record }">
                  {{ record.update_user?.name || '-' }}
                </template>
                <template v-else-if="item.key === 'actions'" #cell="{ record }">
                  <MangoTableActions
                    :actions="[
                      {
                        label: '执行',
                        loading:
                          runningApiId !== null && String(runningApiId) === String(record.id),
                        disabled: caseRunning && String(runningApiId) !== String(record.id),
                        onClick: () => onRunCase(record),
                      },
                      { label: '详情', onClick: () => onStep(record) },
                      ...(canCopyApiInfoCurl(record)
                        ? [
                            {
                              label: '复制 cURL',
                              loading: copyingId === String(record.id),
                              onClick: () =>
                                copyApiInfoCurl(record.id, userStore.selected_environment),
                            },
                          ]
                        : []),
                      { label: '绑定Case', onClick: () => onBoundCases(record) },
                      {
                        label: '编辑',
                        loading: editingId === String(record.id),
                        onClick: () => onUpdate(record),
                      },
                      {
                        label: '删除',
                        danger: true,
                        loading: deletingIds.has(String(record.id)),
                        onClick: () => onDelete(record),
                      },
                    ]"
                  />
                </template>
              </a-table-column>
            </template>
          </a-table>
        </StickyHorizontalTable>
        <template #footer>
          <TableFooter :pagination="pagination" />
        </template>
      </ProjectProductNavigationWorkbench>
    </template>
  </TableBody>
  <ApiInfoRuntimeParametersModal ref="runtimeParametersRef" />
  <ApiInfoEditor ref="editorRef" @saved="onAssetsChanged" />
  <ApiInfoGrpcImport ref="grpcImportRef" @saved="onAssetsChanged" />
  <ApiInfoBatchImport ref="batchImportRef" @saved="onAssetsChanged" />
  <ApiInfoBoundCases ref="boundCasesRef" />
</template>
<script setup lang="ts">
  import {
    computed,
    onMounted,
    ref,
    reactive,
    onBeforeUnmount,
    onActivated,
    onDeactivated,
  } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import type { ModalConfig } from '@arco-design/web-vue'
  import { useRouter } from 'vue-router'
  import { usePagePolling, isPendingExecution } from '@/hooks/use-page-polling'
  import { usePagination, useRowKey, useRowSelection, useTable } from '@/hooks/table'
  import { useLatestRequest } from '@/hooks/use-latest-request'
  import { getFormItems } from '@/utils/datacleaning'
  import { fieldNames } from '@/setting'
  import { useEnum } from '@/store/modules/get-enum'
  import useUserStore from '@/store/modules/user'
  import { getUserName } from '@/api/user/user'
  import {
    deleteApiInfo,
    getApiCaseInfoRun,
    getApiInfo,
    postApiInfoBatchRun,
  } from '@/api/apitest/info'
  import { getSystemSocketNewBrowser } from '@/api/system/socket_api'
  import { getApiInfoPublicationMeta } from '@/utils/api-info-revision'
  import {
    formatProjectProductPath,
    formatModulePath,
    getOptionId,
    getItemValue,
    setItemValue,
  } from '@/utils/business-format'
  import type { NavigationCreateSource } from '@/utils/navigation-create-defaults'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import StickyHorizontalTable from '@/components/table/StickyHorizontalTable.vue'
  import ApiInfoRuntimeParametersModal from '@/components/business/ApiInfoRuntimeParametersModal.vue'
  import ApiInfoSearchFilters from './components/ApiInfoSearchFilters.vue'
  import ApiInfoEditor from './components/ApiInfoEditor.vue'
  import ApiInfoGrpcImport from './components/ApiInfoGrpcImport.vue'
  import ApiInfoBatchImport from './components/ApiInfoBatchImport.vue'
  import ApiInfoBoundCases from './components/ApiInfoBoundCases.vue'
  import { tableColumns, createConditionItems, apiProtocolTabOptions } from './config'
  import { normalizeProtocolType } from './form'
  import { canCopyApiInfoCurl, useApiInfoCurl } from './composables/useApiInfoCurl'
  import type { ApiInfoListRow, ApiEntityId, UserOption } from './types'

  const navigationCreateRef = ref<NavigationCreateSource | null>(null)
  const editorRef = ref<InstanceType<typeof ApiInfoEditor> | null>(null)
  const grpcImportRef = ref<InstanceType<typeof ApiInfoGrpcImport> | null>(null)
  const batchImportRef = ref<InstanceType<typeof ApiInfoBatchImport> | null>(null)
  const boundCasesRef = ref<InstanceType<typeof ApiInfoBoundCases> | null>(null)
  const runtimeParametersRef = ref<InstanceType<typeof ApiInfoRuntimeParametersModal> | null>(null)
  const router = useRouter(),
    enumStore = useEnum(),
    userStore = useUserStore()
  const table = useTable(),
    rows = computed(() => table.dataList as ApiInfoListRow[])
  const pagination = usePagination(
    () => doRefresh(null, false, true),
    () => table.tableLoading
  )
  const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection()
  const { beginRequest, isLatestRequest, invalidateRequests } = useLatestRequest()
  const conditionItems = createConditionItems(),
    rowKey = useRowKey('id')
  const headerConditionItems = computed(() =>
    conditionItems.filter((item) => item.key !== 'project_product' && item.key !== 'module')
  )
  const activeProtocol = ref('all'),
    userOptions = ref<UserOption[]>([]),
    userOptionsLoading = ref(false)
  const sidebarModuleIds = ref<ApiEntityId[]>([]),
    sidebarResetKey = ref(0)
  const pageActive = ref(true),
    recordingLoading = ref(false)
  const execution = ref<{ kind: 'single'; id: ApiEntityId } | { kind: 'batch' } | null>(null)
  const caseRunning = computed(() => execution.value !== null)
  const batchRunning = computed(() => execution.value?.kind === 'batch')
  const runningApiId = computed(() =>
    execution.value?.kind === 'single' ? execution.value.id : null
  )
  const deletingIds = reactive(new Set<string>())
  const editingId = computed(() => editorRef.value?.loadingId || '')
  const protocolTabs = apiProtocolTabOptions
  const isStandardCreateProtocol = computed(() => !['grpc', 'mcp'].includes(activeProtocol.value))
  const isHttpProtocol = computed(() => normalizeProtocolType(activeProtocol.value) === 'http')
  let pageVersion = 0,
    confirmation: ReturnType<typeof Modal.confirm> | null = null
  const { copyingId, copyApiInfoCurl } = useApiInfoCurl(() => `${pageActive.value}:${pageVersion}`)
  const pagePolling = usePagePolling(
    () => doRefresh(null, false, false),
    () => {
      if (table.tableLoading.value) pagePolling.start()
      invalidateRequests()
      table.tableLoading.value = false
    }
  )
  function clearPollingTimer() {
    pagePolling.stop()
  }
  function isCurrent(version: number) {
    return pageActive.value && pageVersion === version
  }
  function protocolTagText(value?: string) {
    return String(value || 'http').toUpperCase()
  }
  function protocolTagColor(value?: string) {
    return (
      ({ http: 'blue', sse: 'orange', grpc: 'purple', mcp: 'green' } as Record<string, string>)[
        normalizeProtocolType(value)
      ] || 'gray'
    )
  }
  function getConditionValue(key: string) {
    return getItemValue(conditionItems, key)
  }
  function currentProtocolKey() {
    return activeProtocol.value
  }
  function isLatestRefresh(request: number, protocol: string) {
    return pageActive.value && isLatestRequest(request) && currentProtocolKey() === protocol
  }
  function switchProtocol(key: string | number) {
    activeProtocol.value = String(key || 'all')
    onSearchRefresh()
  }
  function onSidebarFilterChange(filter: {
    projectProduct: ApiEntityId | null
    module: ApiEntityId | null
    moduleIds?: ApiEntityId[]
  }) {
    setItemValue(conditionItems, 'project_product', filter.projectProduct)
    setItemValue(conditionItems, 'module', filter.module)
    sidebarModuleIds.value = filter.moduleIds || []
    onSearchRefresh()
  }
  function onSearchRefresh() {
    pagination.page = 1
    selectedRowKeys.value = []
    void doRefresh(null, false, true)
  }
  async function doRefresh(
    projectProductId: ApiEntityId | null = null,
    bool_ = false,
    showLoading = false
  ) {
    if (!pageActive.value) return
    const request = beginRequest(),
      protocol = currentProtocolKey()
    if (showLoading) table.tableLoading.value = true
    const value = getFormItems(conditionItems)
    if (value.project_product != null) value.project_product = getOptionId(value.project_product)
    if (value.module != null) value.module = getOptionId(value.module)
    if (sidebarModuleIds.value.length) {
      delete value.module
      value['module__in'] = sidebarModuleIds.value.join(',')
    }
    for (const key of Object.keys(value))
      if (
        value[key] == null ||
        value[key] === '' ||
        (Array.isArray(value[key]) && !value[key].length)
      )
        delete value[key]
    value['page'] = pagination.page
    value['pageSize'] = pagination.pageSize
    value['summary'] = true
    if (protocol !== 'all') value['protocol_type'] = protocol
    if (projectProductId != null && bool_) value.project_product = projectProductId
    try {
      const response = await getApiInfo(value)
      if (!isLatestRefresh(request, protocol)) return
      table.handleSuccess(response)
      pagination.setTotalSize(response.totalSize)
      const ids = new Set(((response.data as ApiInfoListRow[]) || []).map((row) => String(row.id)))
      selectedRowKeys.value = selectedRowKeys.value.filter((id) => ids.has(String(id)))
      if (Array.isArray(response.data) && response.data.some(isPendingExecution))
        pagePolling.start()
      else pagePolling.stop()
    } catch {
      /* 保留列表；轮询请求失败后继续由公共轮询调度器重试。 */
    } finally {
      if (isLatestRefresh(request, protocol)) table.tableLoading.value = false
    }
  }
  async function getNickName() {
    const version = pageVersion
    userOptionsLoading.value = true
    try {
      const response = await getUserName()
      if (isCurrent(version)) userOptions.value = response.data || []
    } catch {
      /* 公共请求层反馈错误，重新进入页面时重试。 */
    } finally {
      if (isCurrent(version)) userOptionsLoading.value = false
    }
  }
  function onResetSearch() {
    sidebarModuleIds.value = []
    sidebarResetKey.value++
    conditionItems.forEach((item) => {
      item.value = ['project_product', 'module'].includes(String(item.key))
        ? null
        : item.multiple
        ? []
        : ''
    })
    onSearchRefresh()
  }
  function onAdd(type: 0 | 1) {
    editorRef.value?.open(
      type === 1 ? 'import' : 'create',
      navigationCreateRef.value?.getCreateDefaults(),
      activeProtocol.value
    )
  }
  function onUpdate(record: ApiInfoListRow) {
    void editorRef.value?.openEdit(record.id)
  }
  function openGrpcImport() {
    void grpcImportRef.value?.open()
  }
  function showBatchImportModal() {
    batchImportRef.value?.open()
  }
  function onBoundCases(record: ApiInfoListRow) {
    void boundCasesRef.value?.open(record)
  }
  function onAssetsChanged() {
    selectedRowKeys.value = []
    void doRefresh(null, false, true)
  }
  function showConfirmation(config: ModalConfig) {
    if (confirmation) return
    const modal = Modal.confirm({
      ...config,
      onClose: () => {
        if (confirmation === modal) confirmation = null
      },
    })
    confirmation = modal
  }
  function onBatchUpload() {
    const version = pageVersion
    showConfirmation({
      title: '注意事项',
      content:
        '录制接口只支持 Web 端，将通过执行器启动浏览器并绑定当前项目，使用所选测试环境域名过滤请求。请确认项目、测试环境及执行器已就绪。',
      cancelText: '取消',
      okText: '确定',
      async onBeforeOk() {
        if (!isCurrent(version) || recordingLoading.value) return false
        recordingLoading.value = true
        try {
          const response = await getSystemSocketNewBrowser(null, 1)
          if (isCurrent(version)) Message.success(response.msg)
          return true
        } catch {
          return false
        } finally {
          recordingLoading.value = false
        }
      },
    })
  }
  function onDelete(record: ApiInfoListRow | null) {
    if (record === null && !selectedRowKeys.value.length) {
      Message.error('请选择要删除的数据')
      return
    }
    const ids = record?.id ?? [...selectedRowKeys.value],
      keys = (Array.isArray(ids) ? ids : [ids]).map(String),
      version = pageVersion
    showConfirmation({
      title: '提示',
      content: '是否要删除此接口？',
      cancelText: '取消',
      okText: '删除',
      okButtonProps: { status: 'danger' },
      async onBeforeOk() {
        if (!isCurrent(version) || keys.some((id) => deletingIds.has(id))) return false
        keys.forEach((id) => deletingIds.add(id))
        try {
          const response = await deleteApiInfo(ids)
          if (isCurrent(version)) {
            Message.success(response.msg)
            selectedRowKeys.value = selectedRowKeys.value.filter((id) => !keys.includes(String(id)))
            await doRefresh(null, false, true)
          }
          return true
        } catch {
          return false
        } finally {
          keys.forEach((id) => deletingIds.delete(id))
        }
      },
    })
  }
  async function onRunCase(record: ApiInfoListRow) {
    if (userStore.selected_environment == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    if (caseRunning.value || !pageActive.value) return
    const version = pageVersion,
      id = record.id,
      environment = userStore.selected_environment
    let issued = false
    execution.value = { kind: 'single', id }
    try {
      const parameters = await runtimeParametersRef.value?.prepare([{ id }])
      if (parameters == null || !isCurrent(version)) return
      issued = true
      const response = await getApiCaseInfoRun(id, environment, undefined, parameters)
      if (!isCurrent(version)) return
      if (response.data?.status === 0)
        Message.error(response.data.error_message || '接口调用失败，请查看执行结果')
      else Message.success(response.msg)
    } catch {
      /* 公共请求层反馈错误，保留当前列表。 */
    } finally {
      execution.value = null
      if (issued && isCurrent(version)) void doRefresh(null, false, true)
    }
  }
  function hasPublishedApiInfoVersion(record: ApiInfoListRow): record is ApiInfoListRow & {
    published_release_id: ApiEntityId
    published_revision_id: ApiEntityId
  } {
    return Boolean(record.published_release_id && record.published_revision_id)
  }
  async function onConcurrency() {
    if (userStore.selected_environment == null) {
      Message.error('请先选择测试环境')
      return
    }
    if (caseRunning.value || !pageActive.value) return
    if (!selectedRowKeys.value.length) {
      Message.error('请选择要执行的接口')
      return
    }
    const ids = new Set(selectedRowKeys.value.map(String)),
      selected = rows.value.filter((row) => ids.has(String(row.id)))
    if (selected.length !== ids.size) {
      Message.warning('部分已选接口不在当前列表中，请刷新后重新选择')
      return
    }
    const executable = selected.filter(hasPublishedApiInfoVersion)
    if (executable.length !== selected.length) {
      Message.warning(
        `所选接口中有 ${selected.length - executable.length} 条尚未发布，请先发布后再执行`
      )
      return
    }
    const items = executable.map((row) => ({
      api_info_id: row.id,
      api_info_release_id: row.published_release_id,
    }))
    const targets = items.map((item) => ({
      id: item.api_info_id,
      release_id: item.api_info_release_id,
    }))
    const version = pageVersion,
      environment = userStore.selected_environment
    let issued = false
    execution.value = { kind: 'batch' }
    try {
      const parameters = await runtimeParametersRef.value?.prepare(targets)
      if (parameters == null || !isCurrent(version)) return
      issued = true
      const response = await postApiInfoBatchRun(items, environment, parameters)
      if (!isCurrent(version)) return
      const count = Number(response.data?.fail_count || 0)
      if (count > 0) Message.warning(`批量执行完成，其中 ${count} 条执行失败`)
      else Message.success(response.msg || '批量执行完成')
    } catch {
      /* 公共请求层反馈错误，允许重新执行。 */
    } finally {
      execution.value = null
      if (issued && isCurrent(version)) void doRefresh(null, false, true)
    }
  }
  function onStep(record: ApiInfoListRow) {
    void router.push({ path: '/apitest/info/details', query: { id: record.id } })
  }
  function deactivate() {
    pageVersion++
    pageActive.value = false
    invalidateRequests()
    table.tableLoading.value = false
    userOptionsLoading.value = false
    editorRef.value?.close()
    grpcImportRef.value?.close()
    batchImportRef.value?.close()
    boundCasesRef.value?.close()
    runtimeParametersRef.value?.cancel()
    confirmation?.close()
    confirmation = null
    clearPollingTimer()
  }
  onMounted(() => {
    void doRefresh(null, false, true)
    void getNickName()
  })
  onDeactivated(deactivate)
  onBeforeUnmount(deactivate)
  onActivated(() => {
    if (!pageActive.value) {
      pageActive.value = true
      void doRefresh(null, false, true)
      void getNickName()
    }
  })
</script>
<style scoped>
  .mango-api-info-tabs {
    overflow: hidden;
    flex: none;
  }
  .mango-api-info-tabs :deep(.arco-tabs-nav-extra) {
    margin-right: var(--m-page-gap);
  }
</style>
