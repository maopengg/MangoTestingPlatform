<template>
  <TableBody ref="tableBody" plain class="mango-api-resource-page mango-detail-workbench-page">
    <template #header>
      <TableHeader title="Token授权管理" />
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
            @search="onSearchRefresh"
            @reset="onResetSearch"
          />
        </template>
        <template #toolbar>
          <div>
            <a-space>
              <a-button
                size="small"
                type="primary"
                @click="onAdd"
                data-testid="qa-views-apitest-auth-config-button-新增"
                >新增</a-button
              >
              <a-button
                size="small"
                status="danger"
                @click="onDelete(null)"
                data-testid="qa-views-apitest-auth-config-button-批量删除"
                >批量删除</a-button
              >
            </a-space></div
          >
        </template>
        <a-table
          class="mango-native-scroll-table"
          :scroll="{ x: tableScrollX, y: '100%' }"
          :bordered="false"
          :columns="tableColumns"
          :data="table.dataList"
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
              <template v-else-if="item.key === 'test_env'" #cell="{ record }">
                <a-tag :color="enumStore.colors[record.test_env]" size="small">
                  {{
                    enumStore.environment_type.find(
                      (item) => String(item.key) === String(record.test_env)
                    )?.title
                  }}
                </a-tag>
              </template>
              <template v-else-if="item.key === 'auth_type'" #cell="{ record }">
                <a-tag :color="enumStore.colors[record.auth_type]" size="small">
                  {{ enumStore.api_auth_type[record.auth_type]?.title }}
                </a-tag>
              </template>
              <template v-else-if="item.key === 'auth_source'" #cell="{ record }">
                <a-tooltip :content="getAuthSourceText(record)">
                  <div class="mango-auth-source-text">
                    {{ getAuthSourceText(record) }}
                  </div>
                </a-tooltip>
              </template>
              <template v-else-if="item.key === 'target_address'" #cell="{ record }">
                {{ record.target_address || '默认地址' }}
              </template>
              <template v-else-if="item.key === 'refresh_mode'" #cell="{ record }">
                <a-tag :color="enumStore.colors[record.refresh_mode]" size="small">
                  {{ enumStore.api_auth_refresh_mode[record.refresh_mode]?.title }}
                </a-tag>
              </template>
              <template v-else-if="item.key === 'time_task'" #cell="{ record }">
                <a-tooltip :content="getRefreshStrategyText(record)">
                  <div class="mango-auth-source-text">
                    {{ getRefreshStrategyText(record) }}
                  </div>
                </a-tooltip>
              </template>
              <template v-else-if="item.key === 'last_refresh_status'" #cell="{ record }">
                <a-tag :color="authRefreshStatusColor(record.last_refresh_status)" size="small">
                  {{ enumStore.api_auth_refresh_status[record.last_refresh_status]?.title }}
                </a-tag>
              </template>
              <template v-else-if="item.key === 'status'" #cell="{ record }">
                <a-switch
                  :beforeChange="(newValue) => onModifyStatus(newValue, record.id)"
                  :checked="record.status === 1"
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
                    { label: '查看', onClick: () => onPreview(record) },
                    {
                      label: '自定义代码',
                      hidden: record.auth_type !== 1,
                      overflow: true,
                      onClick: () => onViewCustomCode(record),
                    },
                    { label: '刷新', onClick: () => onRefresh(record) },
                    { label: '编辑', onClick: () => onUpdate(record) },
                    {
                      label: '清空',
                      danger: true,
                      loading: clearingIds.has(record.id),
                      disabled: clearingIds.has(record.id),
                      onClick: () => onClear(record),
                    },
                    { label: '删除', danger: true, onClick: () => onDelete(record) },
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

  <AuthConfigEditor ref="editorRef" @saved="refreshTable" />
  <AuthCustomCodePanel ref="codePanelRef" @refreshed="refreshTable" />
  <AuthCacheDrawer ref="cacheDrawerRef" @refreshed="refreshTable" />
</template>

<script setup lang="ts">
  import {
    computed,
    onActivated,
    onBeforeUnmount,
    onDeactivated,
    onMounted,
    ref,
    reactive,
    watch,
  } from 'vue'
  import { useRoute } from 'vue-router'
  import { Message, Modal } from '@arco-design/web-vue'
  import { formatProjectProductPath, getOptionId } from '@/utils/business-format'
  import { AUTH_REFRESH_STATUS_COLORS, getStatusTagColor } from '@/utils/status-color'
  import { usePagination, useRowKey, useRowSelection, useTable } from '@/hooks/table'
  import { useLatestRequest } from '@/hooks/use-latest-request'
  import { getFormItems } from '@/utils/datacleaning'
  import { fieldNames } from '@/setting'
  import { useEnum } from '@/store/modules/get-enum'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import ApiResourceSearchFilters from '@/components/business/ApiResourceSearchFilters.vue'
  import { getUserName } from '@/api/user/user'
  import {
    getApiAuthConfig,
    deleteApiAuthConfig,
    postApiAuthConfigClear,
    putApiAuthConfigStatus,
  } from '@/api/apitest/auth-config'
  import type { NavigationCreateSource } from '@/utils/navigation-create-defaults'
  import { createConditionItems, tableColumns, tableScrollX } from './config'
  import type { AuthRecord, AuthEditorHandle, AuthCacheHandle, AuthCodeHandle } from './types'
  import AuthConfigEditor from './components/AuthConfigEditor.vue'
  import AuthCustomCodePanel from './components/AuthCustomCodePanel.vue'
  import AuthCacheDrawer from './components/AuthCacheDrawer.vue'
  const conditionItems = createConditionItems()
  const navigationCreateRef = ref<NavigationCreateSource | null>(null)
  const editorRef = ref<AuthEditorHandle | null>(null)
  const codePanelRef = ref<AuthCodeHandle | null>(null)
  const cacheDrawerRef = ref<AuthCacheHandle | null>(null)
  const userOptions = ref<Array<{ key: number; title: string }>>([])
  const clearingIds = reactive(new Set<number>())
  const statusUpdatingIds = new Set<number>()
  const enumStore = useEnum()
  const route = useRoute()
  const authRefreshStatusColor = (value: number) =>
    getStatusTagColor(AUTH_REFRESH_STATUS_COLORS, value)
  const headerConditionItems = computed(() =>
    conditionItems.filter((item) => item.key !== 'project_product')
  )
  const projectProductCondition = computed(() =>
    conditionItems.find((item) => item.key === 'project_product')
  )
  const sidebarResetKey = ref(0)
  const pagination = usePagination(doRefresh, () => table.tableLoading)
  const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection()
  const table = useTable()
  const { beginRequest, isLatestRequest, invalidateRequests } = useLatestRequest()
  const rowKey = useRowKey('id')
  function onSidebarFilterChange({ projectProduct }: { projectProduct: string | number | null }) {
    if (projectProductCondition.value) projectProductCondition.value.value = projectProduct
    onSearchRefresh()
  }
  function onAdd() {
    editorRef.value?.open(
      undefined,
      navigationCreateRef.value?.getCreateDefaults().projectProduct ?? null
    )
  }
  function onUpdate(record: AuthRecord) {
    editorRef.value?.open(record)
  }
  function onViewCustomCode(record: AuthRecord) {
    codePanelRef.value?.open(record)
  }
  function onPreview(record: AuthRecord) {
    void cacheDrawerRef.value?.open(record)
  }
  function onRefresh(record: AuthRecord) {
    void cacheDrawerRef.value?.open(record, true)
  }
  function onSearchRefresh() {
    selectedRowKeys.value = []
    pagination.page = 1
    void doRefresh(true)
  }

  function doRefresh(showLoading = false) {
    const requestId = beginRequest()
    if (showLoading) {
      table.tableLoading.value = true
    }
    const value = getFormItems(conditionItems)
    for (const key of Object.keys(value)) clearEmptyFilter(value, key)
    if (value.project_product != null) value.project_product = getOptionId(value.project_product)
    value['page'] = pagination.page
    value['pageSize'] = pagination.pageSize
    return getApiAuthConfig(value)
      .then((res) => {
        if (!isLatestRequest(requestId)) return
        table.handleSuccess(res)
        pagination.setTotalSize(res.totalSize)
      })
      .catch(() => {
        // 公共请求层展示错误，保留现有列表以便重试。
      })
      .finally(() => {
        if (isLatestRequest(requestId)) {
          table.tableLoading.value = false
        }
      })
  }

  function clearEmptyFilter(value: Record<string, unknown>, key: string) {
    if (value[key] === null || value[key] === '' || value[key] === undefined) {
      delete value[key]
    }
  }

  function refreshTable() {
    selectedRowKeys.value = []
    return doRefresh(true)
  }

  function onResetSearch() {
    conditionItems.forEach((it) => {
      it.value = it.multiple ? [] : ''
    })
    sidebarResetKey.value += 1
    selectedRowKeys.value = []
    pagination.page = 1
    void doRefresh(true)
  }

  function applyRouteIdFilter(value: unknown) {
    const routeValue = Array.isArray(value) ? value[0] : value
    const idCondition = conditionItems.find((item) => item.key === 'id')
    if (idCondition) idCondition.value = typeof routeValue === 'string' ? routeValue : ''
  }

  function getAuthSourceText(record: AuthRecord) {
    if (record.auth_type === 0) {
      const apiInfo = record.api_info
      if (!apiInfo) return '-'
      return `ID：${apiInfo.id ?? '-'} / 名称：${apiInfo.name || '-'}`
    }
    if (record.auth_type === 1) {
      return record.custom_code || '-'
    }
    return '-'
  }

  function getRefreshStrategyText(record: AuthRecord) {
    const tokenStrategy = `有效期${record.token_ttl ?? '-'}分钟，提前${
      record.refresh_margin ?? '-'
    }分钟刷新`
    const timeTaskStrategy = record.time_task?.name
      ? `定时策略：${record.time_task.name}`
      : '定时策略：-'
    if (record.refresh_mode === 0) {
      return tokenStrategy
    }
    if (record.refresh_mode === 1) {
      return timeTaskStrategy
    }
    if (record.refresh_mode === 2) {
      return `${timeTaskStrategy}；${tokenStrategy}`
    }
    if (record.refresh_mode === 3) {
      return '手动刷新（永久有效）'
    }
    if (record.refresh_mode === 4) {
      const tokenStrategy = `有效期${record.token_ttl ?? '-'}分钟，提前${
        record.expire_notice_minutes ?? '-'
      }分钟通知`
      const noticeGroup = record.notice_group?.name
        ? `通知组：${record.notice_group.name}`
        : '通知组：-'
      return `${tokenStrategy}；${noticeGroup}`
    }
    return '-'
  }

  function onDelete(record: AuthRecord | null) {
    const ids = record ? record.id : [...selectedRowKeys.value]
    if (Array.isArray(ids) && !ids.length) {
      Message.error('请选择要删除的数据')
      return
    }
    Modal.confirm({
      title: '提示',
      content: '是否要删除此授权配置？',
      cancelText: '取消',
      okText: '删除',
      onBeforeOk: async () => {
        try {
          const response = await deleteApiAuthConfig(ids)
          Message.success(response.msg)
          void refreshTable()
          return true
        } catch {
          return false
        }
      },
    })
  }
  async function onClear(record: AuthRecord) {
    if (clearingIds.has(record.id)) return
    clearingIds.add(record.id)
    try {
      const response = await postApiAuthConfigClear(record.id)
      Message.success(response.msg)
      await doRefresh(true)
    } catch {
      // 公共请求层展示错误，释放按钮后允许重试。
    } finally {
      clearingIds.delete(record.id)
    }
  }
  async function onModifyStatus(newValue: boolean, id: number): Promise<boolean> {
    if (statusUpdatingIds.has(id)) return false
    statusUpdatingIds.add(id)
    try {
      const response = await putApiAuthConfigStatus(id, newValue ? 1 : 0)
      if (response.code !== 200) return false
      const record: AuthRecord | undefined = table.dataList.find((row) => row.id === id)
      if (record) record.status = newValue ? 1 : 0
      Message.success(response.msg)
      return true
    } catch {
      return false
    } finally {
      statusUpdatingIds.delete(id)
    }
  }
  watch(
    () => route.query.id,
    (value) => {
      if (route.path !== '/apitest/auth-config/index') return
      applyRouteIdFilter(value)
      onSearchRefresh()
    }
  )
  onMounted(() => {
    applyRouteIdFilter(route.query.id)
    void doRefresh(true)
    getUserName()
      .then((response) => {
        userOptions.value = response.data || []
      })
      .catch(() => {})
  })
  let needsActivationRefresh = false
  onDeactivated(() => {
    needsActivationRefresh = true
    invalidateRequests()
    table.tableLoading.value = false
  })
  onActivated(() => {
    if (needsActivationRefresh) {
      needsActivationRefresh = false
      void doRefresh(true)
    }
  })
  onBeforeUnmount(invalidateRequests)
</script>
<style scoped>
  .mango-auth-source-text {
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
</style>
