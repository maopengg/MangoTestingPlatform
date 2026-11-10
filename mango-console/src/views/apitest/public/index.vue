<template>
  <TableBody plain class="mango-api-resource-page mango-detail-workbench-page">
    <template #header>
      <TableHeader title="全局变量" />
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
            :environment-options="environmentOptions"
            :option-overrides="{ status: enabledSearchOptions }"
            @search="onSearchRefresh"
            @reset="onResetSearch"
          />
        </template>
        <template #toolbar>
          <template v-if="usersFailed"><a-button size="small" :loading="userOptionsLoading" @click="loadUsers"
              >重新加载</a-button></template>
          <a-space>
            <div>
              <a-button
                size="small"
                type="primary"
                @click="onAdd"
                data-testid="qa-views-apitest-public-button-新增"
                >新增</a-button
              >
            </div>
            <div>
              <a-button
                size="small"
                status="danger"
                :loading="deletingIds.size > 0"
                @click="onDelete(null)"
                data-testid="qa-views-apitest-public-button-批量删除"
                >批量删除</a-button
              >
            </div>
          </a-space>
        </template>
        <a-table
          class="mango-native-scroll-table"
          :scroll="{ x: tableScrollX, y: '100%' }"
          :bordered="false"
          :columns="tableColumns"
          :data="rows"
          :loading="table.tableLoading.value"
          :pagination="false"
          :row-selection="{ selectedRowKeys, showCheckedAll }"
          :rowKey="rowKey"
          @selection-change="onSelectionChange"
        >
          <template #columns>
            <a-table-column
              v-for="item of tableColumns"
              :key="item.key"
              :align="item.align"
              :data-index="item.dataIndex || item.key"
              :ellipsis="item.ellipsis"
              :fixed="item.fixed"
              :title="item.title"
              :tooltip="item.tooltip"
              :width="item.width"
            >
              <template v-if="item.key === 'index'" #cell="{ record }">
                {{ record.id }}
              </template>
              <template v-else-if="item.key === 'test_env'" #cell="{ record }">
                <a-tag v-if="normalizeEnvironmentList(record.test_envs).length === 0" size="small"
                  >环境通用</a-tag
                >
                <a-space v-else wrap :size="4">
                  <a-tag
                    v-for="env in normalizeEnvironmentList(record.test_envs)"
                    :key="env"
                    :color="enumStore.colors[env]"
                    size="small"
                  >
                    {{
                      enumStore.environment_type.find((item) => String(item.key) === String(env))
                        ?.title || '-'
                    }}
                  </a-tag>
                </a-space>
              </template>
              <template v-else-if="item.key === 'type'" #cell="{ record }">
                <a-tag :color="enumStore.colors[record.type]" size="small"
                  >{{
                    enumStore.api_public_type.find(
                      (option) => String(option.key) === String(record.type)
                    )?.title || '-'
                  }}
                </a-tag>
              </template>
              <template v-else-if="item.key === 'datasource_alias'" #cell="{ record }">
                <a-tag
                  v-if="record.datasource_alias && typeof record.datasource_alias === 'object'"
                  size="small"
                >
                  {{ record.datasource_alias.name }}
                </a-tag>
                <span v-else>-</span>
              </template>

              <template v-else-if="item.key === 'status'" #cell="{ record }">
                <a-switch
                  :beforeChange="(newValue) => onModifyStatus(newValue, record.id)"
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
                      disabled: statusUpdatingIds.has(record.id),
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
  <PublicVariableEditor ref="editorRef" @saved="onSaved" />
</template>

<script lang="ts" setup>
import { reportLoadError } from '@/utils/load-error'

  import {
    computed,
    onActivated,
    onBeforeUnmount,
    onDeactivated,
    onMounted,
    reactive,
    ref,
  } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import { formatProjectProductPath, getOptionId } from '@/utils/business-format'
  import { usePagination, useRowKey, useRowSelection, useTable } from '@/hooks/table'
  import { useLatestRequest } from '@/hooks/use-latest-request'
  import { getFormItems } from '@/utils/datacleaning'
  import { fieldNames } from '@/setting'
  import {
    tableColumns,
    createConditionItems,
    tableScrollX,
    COMMON_ENV_VALUE,
    enabledSearchOptions,
  } from './config'
  import { normalizeEnvironmentList } from './form'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import ApiResourceSearchFilters from '@/components/business/ApiResourceSearchFilters.vue'
  import PublicVariableEditor from './components/PublicVariableEditor.vue'
  import { deleteApiPublic, getApiPublic, putApiPublicPutStatus } from '@/api/apitest/public'
  import { useEnum } from '@/store/modules/get-enum'
  import { getUserName } from '@/api/user/user'
  import type { NavigationCreateSource } from '@/utils/navigation-create-defaults'
  import type { PublicRecord, PublicUserOption } from './types'
  const navigationCreateRef = ref<NavigationCreateSource | null>(null),
    editorRef = ref<InstanceType<typeof PublicVariableEditor>>()
  const enumStore = useEnum(),
    conditionItems = createConditionItems()
  const headerConditionItems = computed(() =>
    conditionItems.filter((item) => item.key !== 'project_product')
  )
  const projectProductCondition = computed(() =>
    conditionItems.find((item) => item.key === 'project_product')
  )
  const sidebarResetKey = ref(0),
    table = useTable(),
    rows = computed(() => table.dataList as PublicRecord[])
  const pagination = usePagination(
    () => doRefresh(true),
    () => table.tableLoading
  )
  const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection(),
    rowKey = useRowKey('id')
  const { beginRequest, isLatestRequest, invalidateRequests } = useLatestRequest()
  const userOptions = ref<PublicUserOption[]>([]),
    userOptionsLoading = ref(false),
    usersFailed = ref(false),
    listFailed = ref(false)
  const statusUpdatingIds = reactive(new Set<number>()),
    deletingIds = reactive(new Set<string>())
  const environmentOptions = computed(() => [
    { key: COMMON_ENV_VALUE, title: '环境通用' },
    ...enumStore.environment_type,
  ])
  let pageActive = true,
    pageVersion = 0,
    userRequest = 0
  let deleteConfirmation: ReturnType<typeof Modal.confirm> | null = null
  function requestParams() {
    const query: Record<string, unknown> = getFormItems(conditionItems)
    if (query.project_product != null) query.project_product = getOptionId(query.project_product)
    const environments = normalizeEnvironmentList(query.test_envs)
    if (environments.length) query.test_envs = environments.join(',')
    else delete query.test_envs
    for (const key of Object.keys(query)) {
      const value = query[key]
      if (value === '' || value == null || (Array.isArray(value) && !value.length))
        delete query[key]
    }
    return { ...query, page: pagination.page, pageSize: pagination.pageSize }
  }
  async function doRefresh(showLoading = true) {
    if (!pageActive) return
    const request = beginRequest()
    if (showLoading) table.tableLoading.value = true
    listFailed.value = false
    try {
      const response = await getApiPublic(requestParams())
      if (!pageActive || !isLatestRequest(request)) return
      table.handleSuccess(response)
      pagination.setTotalSize(response.totalSize)
      const ids = new Set(rows.value.map((row) => String(row.id)))
      selectedRowKeys.value = selectedRowKeys.value.filter((id) => ids.has(String(id)))
    } catch (loadFailure0) {
      if (pageActive && isLatestRequest(request)) (reportLoadError(loadFailure0, "加载失败，请重试", false), listFailed.value = true)
    } finally {
      if (isLatestRequest(request)) table.tableLoading.value = false
    }
  }
  function changeContext() {
    ++pageVersion
    invalidateRequests()
    table.tableLoading.value = false
    editorRef.value?.close()
    deleteConfirmation?.close()
    deleteConfirmation = null
  }
  function onSearchRefresh() {
    changeContext()
    pagination.page = 1
    selectedRowKeys.value = []
    void doRefresh(true)
  }
  function onSidebarFilterChange({ projectProduct }: { projectProduct: string | number | null }) {
    if (projectProductCondition.value) projectProductCondition.value.value = projectProduct
    onSearchRefresh()
  }
  function onResetSearch() {
    conditionItems.forEach((item) => {
      item.value = item.multiple || item.key === 'test_envs' ? [] : ''
    })
    sidebarResetKey.value++
    onSearchRefresh()
  }
  function onAdd() {
    const product = navigationCreateRef.value?.getCreateDefaults().projectProduct ?? null
    editorRef.value?.open(undefined, product)
  }
  function onUpdate(record: PublicRecord) {
    editorRef.value?.open(record)
  }
  function onSaved() {
    selectedRowKeys.value = []
    void doRefresh(true)
  }
  function onDelete(record: PublicRecord | null) {
    if (!pageActive || deleteConfirmation) return
    const batch = record === null
    if (batch && !selectedRowKeys.value.length) {
      Message.error('请选择要删除的数据')
      return
    }
    const ids = record?.id ?? [...selectedRowKeys.value],
      keys = (Array.isArray(ids) ? ids : [ids]).map(String),
      version = pageVersion
    if (keys.some((id) => deletingIds.has(id) || statusUpdatingIds.has(Number(id)))) return
    const confirmation = Modal.confirm({
      title: '删除全局变量',
      content: '是否要删除所选全局变量？',
      cancelText: '取消',
      okText: '删除',
      okButtonProps: { status: 'danger' },
      async onBeforeOk() {
        if (
          !pageActive ||
          version !== pageVersion ||
          keys.some((id) => deletingIds.has(id) || statusUpdatingIds.has(Number(id)))
        )
          return false
        keys.forEach((id) => deletingIds.add(id))
        try {
          const response = await deleteApiPublic(ids)
          if (pageActive && version === pageVersion) {
            Message.success(response.msg)
            selectedRowKeys.value = selectedRowKeys.value.filter((id) => !keys.includes(String(id)))
            if (
              rows.value.length &&
              rows.value.every((row) => keys.includes(String(row.id))) &&
              pagination.page > 1
            )
              pagination.page--
            await doRefresh(true)
          }
          return true
        } catch {
          return false
        } finally {
          keys.forEach((id) => deletingIds.delete(id))
        }
      },
      onClose() {
        if (deleteConfirmation === confirmation) deleteConfirmation = null
      },
    })
    deleteConfirmation = confirmation
  }
  async function onModifyStatus(newValue: boolean, id: number): Promise<boolean> {
    if (!pageActive || statusUpdatingIds.has(id) || deletingIds.has(String(id))) return false
    const version = pageVersion,
      status = newValue ? 1 : 0
    statusUpdatingIds.add(id)
    invalidateRequests()
    table.tableLoading.value = false
    try {
      await putApiPublicPutStatus(id, status)
      if (!pageActive || version !== pageVersion) return false
      const target = rows.value.find((row) => row.id === id)
      if (target) target.status = status
      invalidateRequests()
      await doRefresh(false)
      return true
    } catch {
      return false
    } finally {
      statusUpdatingIds.delete(id)
    }
  }
  async function loadUsers() {
    if (!pageActive) return
    const request = ++userRequest
    userOptionsLoading.value = true
    usersFailed.value = false
    try {
      const response = await getUserName()
      if (pageActive && request === userRequest) userOptions.value = response.data || []
    } catch (loadFailure1) {
      if (pageActive && request === userRequest) (reportLoadError(loadFailure1, "加载失败，请重试", false), usersFailed.value = true)
    } finally {
      if (request === userRequest) userOptionsLoading.value = false
    }
  }
  function deactivate() {
    pageActive = false
    ++userRequest
    userOptionsLoading.value = false
    changeContext()
  }
  onMounted(() => {
    void doRefresh(true)
    void loadUsers()
  })
  onDeactivated(deactivate)
  onBeforeUnmount(deactivate)
  onActivated(() => {
    if (!pageActive) {
      pageActive = true
      void doRefresh(true)
      void loadUsers()
    }
  })
</script>
