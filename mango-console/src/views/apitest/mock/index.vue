<template>
  <TableBody plain class="mango-api-mock-list-page mango-detail-workbench-page">
    <template #header>
      <TableHeader title="Mock服务" />
    </template>
    <template #default>
      <ProjectProductNavigationWorkbench
        ref="navigationCreateRef"
        contained-body
        :model-value="filters.project_product"
        :reset-key="sidebarResetKey"
        @filter-change="onProjectChange"
        @search="refresh(true)"
        @reset-search="resetFilters"
      >
        <template #search>
          <a-form :model="filters" layout="inline" @keyup.enter="refresh(true)">
            <a-form-item label="ID"><a-input v-model="filters.id" allow-clear placeholder="请输入ID" /></a-form-item>
            <a-form-item label="接口名称"><a-input v-model="filters.name" allow-clear placeholder="请输入接口名称" /></a-form-item>
            <a-form-item label="请求路径"><a-input v-model="filters.mock_key" allow-clear placeholder="请输入路径关键字" /></a-form-item>
            <a-form-item label="方法"><a-select v-model="filters.method" multiple :max-tag-count="1" allow-clear :options="methodOptions" placeholder="请选择方法" /></a-form-item>
            <a-form-item label="启用状态"><a-select v-model="filters.enabled" multiple :max-tag-count="1" allow-clear :options="booleanOptions" placeholder="请选择状态" /></a-form-item>
            <a-form-item label="调用记录"><a-select v-model="filters.record_call_log" multiple :max-tag-count="1" allow-clear :options="logOptions" placeholder="请选择状态" /></a-form-item>
          </a-form>
        </template>
        <template #toolbar>
          <a-space>
            <a-button  size="small" type="primary" @click="createConfig">新增 Mock 接口</a-button>
            <a-button
              size="small"
              status="danger"
              :loading="clearAllLoading"
              @click="clearAllLogs"
            >
              清空全部 Mock 日志
            </a-button>
          </a-space>
        </template>
        <a-table
          class="mango-native-scroll-table"
          :columns="tableColumns"
          :data="table.dataList"
          :loading="table.tableLoading.value"
          :pagination="false"
          :scroll="{ x: tableScrollX, y: '100%' }"
          row-key="id"
        >
          <template #columns>
            <a-table-column
              v-for="column in tableColumns"
              :key="column.key"
              :align="column.align"
              :data-index="column.dataIndex"
              :ellipsis="column.ellipsis"
              :fixed="column.fixed"
              :title="column.title"
              :tooltip="column.tooltip"
              :width="column.width"
            >
              <template #cell="{ record }">
                <template v-if="column.key === 'index'">{{ record.id }}</template>
                <template v-else-if="column.key === 'mock_url'">
                  <a-tooltip content="点击复制 cURL">
                    <a-link @click="copyCurl(record)">{{ requestPath(record) }}</a-link>
                  </a-tooltip>
                </template>
                <template v-else-if="column.key === 'method_name'">
                  <a-tag size="small" :color="enumStore.colors[record.method]">
                    {{ record.method_name || '-' }}
                  </a-tag>
                </template>
                <template v-else-if="column.key === 'enabled'">
                  <a-switch  :model-value="record.enabled" :before-change="(value) => changeState(record, { enabled: value })" />
                </template>
                <template v-else-if="column.key === 'record_call_log'">
                  <a-tooltip content="关闭后合法请求不记录；断言失败和平台异常仍会记录">
                    <a-switch  :model-value="record.record_call_log" :before-change="(value) => changeState(record, { record_call_log: value })" />
                  </a-tooltip>
                </template>
                <template v-else-if="column.key === 'update_user'">{{ record.update_user?.name || '-' }}</template>
                <template v-else-if="column.key === 'project_product'">{{ formatProjectProductPath(record.project_product) }}</template>
                <template v-else-if="column.key === 'actions'">
                  <MangoTableActions :actions="[
    { label: '配置', onClick: () => openConfig(record.id) },
    { label: '调用记录', onClick: () => openLogs(record) },
    { label: '复制 cURL', onClick: () => copyCurl(record) },
    { label: '删除', danger: true, onClick: () => removeConfig(record) },
]" />
                </template>
                <template v-else>{{ cellValue(record, column.dataIndex) }}</template>
              </template>
            </a-table-column>
          </template>
        </a-table>
        <template #footer><TableFooter :pagination="pagination" /></template>
      </ProjectProductNavigationWorkbench>
    </template>
  </TableBody>
  <MockCallLogsPanel
    v-if="logsTarget"
    v-model:visible="logsVisible"
    :mock-id="logsTarget.id"
    :mock-key="logsTarget.mock_key"
  />
</template>

<script lang="ts" setup>
  import { onMounted, reactive, ref } from 'vue'
  import { useRouter } from 'vue-router'
  import { Message, Modal } from '@arco-design/web-vue'
  import { usePagination, useTable } from '@/hooks/table'
  import { useEnum } from '@/store/modules/get-enum'
  import { formatProjectProductPath } from '@/utils/business-format'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import MockCallLogsPanel from './components/MockCallLogsPanel.vue'
  import {
    clearAllMockLogs,
    deleteMockConfig,
    getMockConfigs,
    getMockEndpointUrl,
    updateMockConfigState,
  } from '@/api/apitest/mock'
  import { booleanOptions, logOptions, methodOptions, tableColumns, tableScrollX } from './config'
  import type { NavigationCreateSource } from '@/utils/navigation-create-defaults'

  const navigationCreateRef = ref<NavigationCreateSource | null>(null)

  const router = useRouter()
  const enumStore = useEnum()
  const table = useTable()
  const sidebarResetKey = ref(0)
  const clearAllLoading = ref(false)
  const logsVisible = ref(false)
  const logsTarget = ref<{ id: number; mock_key: string } | null>(null)
  const filters = reactive<Record<string, any>>({
    project_product: '', id: '', name: '', mock_key: '', method: [], enabled: [], record_call_log: [],
  })
  const pagination = usePagination(() => refresh(), () => table.tableLoading)

  function requestParams() {
    const result: Record<string, unknown> = { page: pagination.page, pageSize: pagination.pageSize }
    Object.entries(filters).forEach(([key, value]) => {
      if (value === '' || value === null || value === undefined) return
      if (Array.isArray(value)) {
        if (value.length) result[`${key}__in`] = value.join(',')
        return
      }
      if (key === 'mock_key') {
        result[key] = String(value).trim().replace(/^\/+/, '').split('/')[0]
        return
      }
      result[key] = value
    })
    return result
  }

  async function refresh(showLoading = false) {
    if (showLoading) table.tableLoading.value = true
    try {
      const response = await getMockConfigs(requestParams())
      await table.handleSuccess(response)
      pagination.setTotalSize(response.totalSize)
    } finally {
      table.tableLoading.value = false
    }
  }

  function onProjectChange({ projectProduct }: { projectProduct: string | number | null }) {
    filters.project_product = projectProduct || ''
    pagination.page = 1
    refresh(true)
  }

  function resetFilters() {
    Object.keys(filters).forEach((key) => {
      filters[key] = ['method', 'enabled', 'record_call_log'].includes(key) ? [] : ''
    })
    sidebarResetKey.value += 1
    pagination.page = 1
    refresh(true)
  }

  function createConfig() {
    const projectProduct = navigationCreateRef.value?.getCreateDefaults().projectProduct
    router.push({ path: '/apitest/mock/details', query: projectProduct ? { project_product: projectProduct } : {} })
  }
  function openConfig(id: number) { router.push({ path: '/apitest/mock/details', query: { id } }) }
  function openLogs(record: { id: number; mock_key: string }) {
    logsTarget.value = { id: record.id, mock_key: record.mock_key }
    logsVisible.value = true
  }
  function cellValue(record: Record<string, any>, dataIndex?: string) {
    if (!dataIndex) return '-'
    return record[dataIndex] ?? '-'
  }
  function requestPath(record: any) {
    return `/${record.mock_key}${record.path && record.path !== '/' ? record.path : ''}`
  }
  function mockUrl(record: any) { return getMockEndpointUrl(requestPath(record)) }

  async function copyCurl(record: any) {
    const method = record.method_name === '全部' ? 'GET' : String(record.method_name || 'GET').split(' / ')[0]
    const command = `curl -X ${method} '${mockUrl(record)}'`
    await navigator.clipboard.writeText(command)
    Message.success('cURL 已复制')
  }

  async function changeState(record: any, value: { enabled?: boolean; record_call_log?: boolean }) {
    await updateMockConfigState(record.id, value)
    Object.assign(record, value)
    return true
  }

  function removeConfig(record: any) {
    Modal.confirm({
      title: '删除 Mock 接口',
      content: '删除后配置及其全部调用记录都会被清理，确认继续吗？',
      okButtonProps: { status: 'danger' },
      async onOk() {
        await deleteMockConfig(record.id)
        Message.success('删除成功')
        await refresh(true)
      },
    })
  }

  function clearAllLogs() {
    Modal.confirm({
      title: '清空全部 Mock 日志',
      content:
        '将暂停 Mock 日志写入，并永久清空所有 Mock 接口的调用记录。该操作会立即释放日志表占用的物理空间，且无法恢复，确认继续吗？',
      okText: '确认全部清空',
      okButtonProps: { status: 'danger' },
      async onOk() {
        clearAllLoading.value = true
        try {
          const response = await clearAllMockLogs()
          Message.success(`已清空 ${response.data?.deleted_count || 0} 条 Mock 日志`)
        } finally {
          clearAllLoading.value = false
        }
      },
    })
  }

  onMounted(() => refresh(true))
</script>
