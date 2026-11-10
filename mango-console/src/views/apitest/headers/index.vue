<template>
  <TableBody ref="tableBody" plain class="mango-api-resource-page mango-detail-workbench-page">
    <template #header>
      <TableHeader title="请求头管理" />
    </template>

    <template #default>
      <ProjectProductNavigationWorkbench
        ref="navigationCreateRef"
        contained-body
        :model-value="projectProductCondition?.value"
        :reset-key="sidebarResetKey"
        @filter-change="onSidebarFilterChange"
        @search="onSearchRefresh"
        @reset-search="onResetSearch"
      >
        <template #search>
          <ApiResourceSearchFilters
            :items="headerConditionItems"
            :field-names="fieldNames"
            :enum-store="enumStore"
            :user-list="userOptions"
            :users-loading="userOptionsLoading"
            @search="onSearchRefresh"
            @reset="onResetSearch"
          />
        </template>
        <template #toolbar>
          <a-space>
            <div>
              <a-button
                size="small"
                type="primary"
                @click="onAdd"
                data-testid="qa-views-apitest-headers-button-新增"
                >新增</a-button
              >
            </div>
            <div>
              <a-button
                size="small"
                status="danger"
                :loading="deletingIds.size > 0"
                @click="onDelete(null)"
                data-testid="qa-views-apitest-headers-button-批量删除"
                >批量删除</a-button
              >
            </div>
          </a-space>
        </template>
        <a-table
          class="mango-native-scroll-table"
          :scroll="{ x: 1480, y: '100%' }"
          :bordered="false"
          :columns="tableColumns"
          :data="batchSelectableDataList"
          :loading="table.tableLoading.value"
          :pagination="false"
          :row-selection="{ selectedRowKeys, showCheckedAll, onlyCurrent: true }"
          :rowKey="rowKey"
          @selection-change="onHeaderSelectionChange"
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
                :color="enumStore.colors[record.project_product?.api_client_type ?? -1] || 'gray'"
                  size="small"
                  >{{
                    enumStore.api_client?.find(
                      (option) =>
                        String(option.key) === String(record.project_product?.api_client_type)
                    )?.title || '-'
                  }}
                </a-tag>
              </template>
              <template v-else-if="item.key === 'status'" #cell="{ record }">
                <a-switch
                  :before-change="(newValue) => onModifyStatus(newValue, record.id)"
                  :model-value="record.status === 1"
                  :loading="statusUpdatingIds.has(record.id)"
                  :disabled="deletingIds.has(String(record.id))"
                />
              </template>
              <template v-else-if="item.key === 'project_product'" #cell="{ record }">
                {{ formatProjectProductPath(record.project_product) }}
              </template>
              <template v-else-if="item.key === 'update_user'" #cell="{ record }">
                {{ record.update_user?.name || '-' }}
              </template>
              <template v-else-if="item.key === 'actions'" #cell="{ record }">
                <MangoTableActions
                  :actions="[
                    { label: '编辑', onClick: () => onUpdate(record) },
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
        <template #footer>
          <TableFooter :pagination="pagination" />
        </template>
      </ProjectProductNavigationWorkbench>
    </template>
  </TableBody>
  <HeaderEditor ref="editorRef" @saved="onSaved" />
</template>

<script lang="ts" setup>
  import {
    computed,
    onMounted,
    onActivated,
    onDeactivated,
    onBeforeUnmount,
    ref,
    reactive,
  } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import { formatProjectProductPath, getOptionId } from '@/utils/business-format'
  import { usePagination, useRowKey, useTable } from '@/hooks/table'
  import { useProjectLockedRowSelection } from '@/hooks/use-project-locked-row-selection'
  import { useLatestRequest } from '@/hooks/use-latest-request'
  import { getFormItems } from '@/utils/datacleaning'
  import { fieldNames } from '@/setting'
  import { tableColumns, createConditionItems } from './config'
  import HeaderEditor from './components/HeaderEditor.vue'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import ApiResourceSearchFilters from '@/components/business/ApiResourceSearchFilters.vue'
  import { deleteApiHeaders, getApiHeaders, putApiHeaders } from '@/api/apitest/headers'
  import { useEnum } from '@/store/modules/get-enum'
  import { getUserName } from '@/api/user/user'
  import type { NavigationCreateSource } from '@/utils/navigation-create-defaults'
  import type { HeaderRecord, HeaderUserOption } from './types'

  const navigationCreateRef = ref<NavigationCreateSource | null>(null)
  const editorRef = ref<InstanceType<typeof HeaderEditor> | null>(null)
  const enumStore = useEnum()
  const conditionItems = createConditionItems()
  const headerConditionItems = computed(() =>
    conditionItems.filter((item) => item.key !== 'project_product')
  )
  const projectProductCondition = computed(() =>
    conditionItems.find((item) => item.key === 'project_product')
  )
  const sidebarResetKey = ref(0)
  const table = useTable()
  const rows = computed(() => table.dataList as HeaderRecord[])
  const pagination = usePagination(
    () => doRefresh(true),
    () => table.tableLoading
  )
  const {
    selectedRowKeys,
    showCheckedAll,
    selectableDataList: batchSelectableDataList,
    onSelectionChange: onHeaderSelectionChange,
    validateSingleProject: validateSingleProduct,
  } = useProjectLockedRowSelection<HeaderRecord>(
    () => rows.value,
    (row) => row?.project_product ?? undefined,
    { scopeLabel: '项目/产品', actionLabel: '删除', itemLabel: '请求头' }
  )
  const { beginRequest, isLatestRequest, invalidateRequests } = useLatestRequest()
  const rowKey = useRowKey('id')
  const userOptions = ref<HeaderUserOption[]>([])
  const userOptionsLoading = ref(false)
  const statusUpdatingIds = reactive(new Set<number>())
  const deletingIds = reactive(new Set<string>())
  const pageActive = ref(true)
  let pageVersion = 0
  let deleteConfirmation: ReturnType<typeof Modal.confirm> | null = null

  function onSidebarFilterChange({ projectProduct }: { projectProduct: string | number | null }) {
    if (projectProductCondition.value) projectProductCondition.value.value = projectProduct
    onSearchRefresh()
  }

  function onSearchRefresh() {
    pagination.page = 1
    selectedRowKeys.value = []
    void doRefresh(true)
  }

  async function doRefresh(showLoading = true) {
    if (!pageActive.value) return
    const requestId = beginRequest()
    if (showLoading) table.tableLoading.value = true
    const query = getFormItems(conditionItems)
    if (query.project_product != null) query.project_product = getOptionId(query.project_product)
    for (const key of Object.keys(query)) {
      const value = query[key]
      if (
        value === '' ||
        value === null ||
        value === undefined ||
        (Array.isArray(value) && !value.length)
      )
        delete query[key]
    }
    query.page = pagination.page
    query.pageSize = pagination.pageSize
    try {
      const response = await getApiHeaders(query)
      if (!isLatestRequest(requestId)) return
      table.handleSuccess(response)
      const currentIds = new Set(
        ((response.data as HeaderRecord[]) || []).map((item) => String(item.id))
      )
      selectedRowKeys.value = selectedRowKeys.value.filter((id) => currentIds.has(String(id)))
      pagination.setTotalSize(response.totalSize)
    } catch {
      /* 请求失败保留当前列表，公共请求层提示错误。 */
    } finally {
      if (isLatestRequest(requestId)) table.tableLoading.value = false
    }
  }

  function onResetSearch() {
    conditionItems.forEach((item) => {
      item.value = item.multiple ? [] : ''
    })
    sidebarResetKey.value++
    onSearchRefresh()
  }

  function onAdd() {
    const product = navigationCreateRef.value?.getCreateDefaults()?.projectProduct ?? null
    editorRef.value?.open(undefined, product)
  }

  function onUpdate(record: HeaderRecord) {
    editorRef.value?.open(record)
  }

  function onSaved() {
    selectedRowKeys.value = []
    void doRefresh(true)
  }

  function onDelete(record: HeaderRecord | null) {
    if (deleteConfirmation) return
    const batch = record === null
    if (batch && !selectedRowKeys.value.length) {
      Message.error('请选择要删除的数据')
      return
    }
    if (batch && !validateSingleProduct('所选请求头')) return
    const ids = record?.id ?? [...selectedRowKeys.value]
    const keys = (Array.isArray(ids) ? ids : [ids]).map(String)
    const version = pageVersion
    const confirmation = Modal.confirm({
      title: '提示',
      content: '是否要删除此请求头？',
      cancelText: '取消',
      okText: '删除',
      okButtonProps: { status: 'danger' },
      onBeforeOk: async () => {
        if (version !== pageVersion || !pageActive.value || keys.some((id) => deletingIds.has(id)))
          return false
        keys.forEach((id) => deletingIds.add(id))
        try {
          const response = await deleteApiHeaders(ids)
          if (version === pageVersion && pageActive.value) {
            Message.success(response.msg)
            selectedRowKeys.value = selectedRowKeys.value.filter((id) => !keys.includes(String(id)))
            await doRefresh(true)
          }
          return true
        } catch {
          return false
        } finally {
          keys.forEach((id) => deletingIds.delete(id))
        }
      },
      onClose: () => {
        if (deleteConfirmation === confirmation) deleteConfirmation = null
      },
    })
    deleteConfirmation = confirmation
  }

  async function onModifyStatus(newValue: boolean, id: number): Promise<boolean> {
    if (!pageActive.value || statusUpdatingIds.has(id) || deletingIds.has(String(id))) return false
    const target = rows.value.find((item) => item.id === id)
    if (!target) return false
    const version = pageVersion,
      status = newValue ? 1 : 0
    statusUpdatingIds.add(id)
    try {
      const response = await putApiHeaders({ id, status })
      if (response.code !== 200 || version !== pageVersion || !pageActive.value) return false
      Message.success(response.msg)
      if (rows.value.find((item) => item.id === id) === target) target.status = status
      else await doRefresh(true)
      return true
    } catch {
      return false
    } finally {
      statusUpdatingIds.delete(id)
    }
  }

  async function loadUsers() {
    const version = pageVersion
    userOptionsLoading.value = true
    try {
      const response = await getUserName()
      if (version === pageVersion && pageActive.value) userOptions.value = response.data || []
    } catch {
      /* 公共请求层反馈错误，重新进入页面可重试。 */
    } finally {
      if (version === pageVersion) userOptionsLoading.value = false
    }
  }

  function deactivate() {
    pageVersion++
    pageActive.value = false
    invalidateRequests()
    table.tableLoading.value = false
    userOptionsLoading.value = false
    editorRef.value?.close()
    deleteConfirmation?.close()
    deleteConfirmation = null
  }

  onMounted(() => {
    void doRefresh(true)
    void loadUsers()
  })
  onDeactivated(deactivate)
  onBeforeUnmount(deactivate)
  onActivated(() => {
    if (!pageActive.value) {
      pageActive.value = true
      void doRefresh(true)
      void loadUsers()
    }
  })
</script>
