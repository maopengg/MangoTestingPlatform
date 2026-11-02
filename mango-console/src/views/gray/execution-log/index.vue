<template>
  <TableBody content-flush>
    <template #header>
      <TableHeader title="执行记录" :show-filter="true" @search="onSearchRefresh" @reset-search="onReset">
        <template #search-content>
          <a-form layout="inline" :model="query" @keyup.enter="onSearchRefresh">
            <a-form-item label="灰度Key">
              <a-input v-model="query.feature_key" allow-clear placeholder="请输入灰度Key" @blur="onSearchRefresh" @clear="onSearchRefresh" data-testid="qa-views-gray-execution-log-input-请输入灰度key" />
            </a-form-item>
            <a-form-item label="目标值">
              <a-input v-model="query.target_value" allow-clear placeholder="请输入目标值" @blur="onSearchRefresh" @clear="onSearchRefresh" data-testid="qa-views-gray-execution-log-input-请输入目标值" />
            </a-form-item>
            <a-form-item label="状态">
              <a-select v-model="query.status" multiple :max-tag-count="1" :options="executionStatusOptions" allow-clear placeholder="请选择状态" @change="onSearchRefresh" data-testid="qa-views-gray-execution-log-select-请选择状态" />
            </a-form-item>
            <a-form-item label="配置类型">
              <a-select v-model="query.config_type" multiple :max-tag-count="1" :options="configTypeOptions" allow-clear placeholder="请选择类型" @change="onSearchRefresh" data-testid="qa-views-gray-execution-log-select-请选择类型" />
            </a-form-item>
            <a-form-item label="用例类型">
              <a-select v-model="query.case_type" multiple :max-tag-count="1" :options="caseTypeOptions" allow-clear placeholder="请选择用例类型" @change="onSearchRefresh" data-testid="qa-views-gray-execution-log-select-请选择用例类型" />
            </a-form-item>
            <a-form-item label="用例名称">
              <a-input v-model="query.case_name" allow-clear placeholder="请输入用例名称" @blur="onSearchRefresh" @clear="onSearchRefresh" data-testid="qa-views-gray-execution-log-input-请输入用例名称" />
            </a-form-item>
            <a-form-item label="报告ID">
              <a-input v-model="query.test_suite_id" allow-clear placeholder="请输入测试报告ID" @blur="onSearchRefresh" @clear="onSearchRefresh" data-testid="qa-views-gray-execution-log-input-请输入测试报告id" />
            </a-form-item>
            <a-form-item label="用例ID">
              <a-input v-model="query.case_id" allow-clear placeholder="请输入用例ID" @blur="onSearchRefresh" @clear="onSearchRefresh" data-testid="qa-views-gray-execution-log-input-请输入用例id" />
            </a-form-item>
            <a-form-item label="配置文件">
              <a-select v-model="query.yaml_file" multiple :max-tag-count="1" :options="yamlOptions" allow-clear allow-search placeholder="请选择配置文件" @change="onSearchRefresh" data-testid="qa-views-gray-execution-log-select-请选择配置文件" />
            </a-form-item>
            <a-form-item label="来源分支">
              <a-input v-model="query.source_branch" allow-clear placeholder="请输入来源分支" @blur="onSearchRefresh" @clear="onSearchRefresh" data-testid="qa-views-gray-execution-log-input-请输入来源分支" />
            </a-form-item>
            <a-form-item label="目标分支">
              <a-input v-model="query.target_branch" allow-clear placeholder="请输入目标分支" @blur="onSearchRefresh" @clear="onSearchRefresh" data-testid="qa-views-gray-execution-log-input-请输入目标分支" />
            </a-form-item>
          </a-form>
        </template>
      </TableHeader>
    </template>

    <template #default>
      <TableTabs>
        <template #extra>
          <a-button
            size="small"
            status="danger"
            :loading="actionLoading === 'cleanup-expired'"
            @click="onCleanupExpired"
            data-testid="qa-views-gray-execution-log-button-清理1个月前"
          >
            清理1个月前
          </a-button>
        </template>
      </TableTabs>
      <a-table
        :bordered="false"
        :columns="logColumns"
        :data="table.dataList"
        :loading="table.tableLoading.value"
        :pagination="false"
        :scroll="{ x: grayPageConfig.scrollX }"
        row-key="id"
      >
        <template #columns>
          <a-table-column v-for="item in logColumns" :key="item.key" v-bind="item">
            <template v-if="item.key === 'index'" #cell="{ record }">{{ record.id }}</template>
            <template v-else-if="item.key === 'status'" #cell="{ record }">
              <a-tag :color="executionStatusColor(record.status)" size="small">{{ statusText(record.status) }}</a-tag>
            </template>
            <template v-else-if="item.key === 'case'" #cell="{ record }">
              {{ record.case_name || record.case_id || '-' }}
            </template>
            <template v-else-if="item.key === 'merge_request'" #cell="{ record }">
              <a-link v-if="record.merge_request_url" :href="record.merge_request_url" target="_blank">
                {{ record.merge_request_iid || record.merge_request_id || '查看PR' }}
              </a-link>
              <span v-else>-</span>
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <MangoTableActions :actions="rowActions(record)" />
            </template>
          </a-table-column>
        </template>
      </a-table>
    </template>

    <template #footer>
      <TableFooter :pagination="pagination" />
    </template>
  </TableBody>

  <BaseSidePanel
    :visible="detailDrawer.visible"
    :title="detailDrawer.title"
    :width="820"
    cancel-button-text="关闭"
    @update:visible="(value) => (detailDrawer.visible = value)"
    @cancel="detailDrawer.visible = false"
  >
    <template #default>
      <CodeEditor
        v-model="detailDrawer.content"
        readonly
        placeholder="暂无详情"
        :code-style="{ height: 'calc(100vh - 190px)' }"
      />
    </template>
    <template #footer-buttons>
      <a-button @click="detailDrawer.visible = false" data-testid="qa-views-gray-execution-log-button-关闭">关闭</a-button>
    </template>
  </BaseSidePanel>
</template>

<script setup lang="ts">
  import { computed, onMounted, reactive, ref } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import TableBody from '@/components/table/TableBody.vue'
  import TableHeader from '@/components/table/TableHeader.vue'
  import TableFooter from '@/components/table/TableFooter.vue'
  import TableTabs from '@/components/table/TableTabs.vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import CodeEditor from '@/components/editors/CodeEditor.vue'
  import { usePagination, useTable } from '@/hooks/table'
  import { createIdSearchValue } from '@/utils/id-search'
  import { normalizeMultiSelectSearchParams } from '@/utils/search-condition'
  import {
    getGrayExecutionLog,
    getGrayYamlFile,
    postGrayExecutionLogCleanupExpired,
    postGrayExecutionRetryRestore,
  } from '@/api/gray'
  import { caseTypeOptions, configTypeOptions, executionStatusOptions, grayPageConfig } from './config'

  const table = useTable()
  const pagination = usePagination(onSearch, () => table.tableLoading)
  const query = reactive<any>({
    status: [], config_type: [], case_type: [], yaml_file: [],
    test_suite_id: createIdSearchValue('', false),
    case_id: createIdSearchValue('', false),
  })
  const yamlList = ref<any[]>([])
  const actionLoading = ref('')
  const detailDrawer = reactive({ visible: false, title: '', content: '' })
  const logColumns = computed(() => grayPageConfig.columns)
  const yamlOptions = computed(() => yamlList.value.map((item) => ({ label: item.name, value: item.id })))

  function cleanParams(params: Record<string, any>) {
    const result: Record<string, any> = {}
    Object.entries(params).forEach(([key, value]) => {
      if (value !== '' && value !== null && value !== undefined) {
        result[key] = value
      }
    })
    return result
  }

  function requestParams() {
    return cleanParams(normalizeMultiSelectSearchParams({
      page: pagination.page,
      pageSize: pagination.pageSize,
      feature_key: query.feature_key,
      target_value: query.target_value,
      status: query.status,
      config_type: query.config_type,
      case_type: query.case_type,
      case_name: query.case_name,
      test_suite_id: query.test_suite_id,
      case_id: query.case_id,
      yaml_file: query.yaml_file,
      source_branch: query.source_branch,
      target_branch: query.target_branch,
    }, ['status', 'config_type', 'case_type', 'yaml_file']))
  }

  async function loadOptions() {
    const res = await getGrayYamlFile({})
    yamlList.value = res.data || []
  }

  async function onSearch() {
    table.tableLoading.value = true
    try {
      const res = await getGrayExecutionLog(requestParams())
      table.handleSuccess(res)
      pagination.setTotalSize(res.totalSize || 0)
    } finally {
      table.tableLoading.value = false
    }
  }

  function onSearchRefresh() {
    pagination.page = 1
    onSearch()
  }

  function onReset() {
    Object.keys(query).forEach((key) => {
      query[key] = ['status', 'config_type', 'case_type', 'yaml_file'].includes(key) ? [] : undefined
    })
    onSearchRefresh()
  }

  function statusText(status: number) {
    return ({ 0: '待执行', 1: '成功', 2: '失败', 3: '已恢复', 4: '恢复失败' } as Record<number, string>)[status] || '-'
  }

  function executionStatusColor(status: number) {
    return ({ 0: 'gray', 1: 'green', 2: 'red', 3: 'blue', 4: 'red' } as Record<number, string>)[status] || 'gray'
  }

  function rowActions(record: any) {
    const actions: any[] = [{  label: '详情', onClick: () => onDetail(record) }]
    if ([1, 2, 4].includes(record.status)) {
      actions.push({  label: '恢复', loading: actionLoading.value === `restore-${record.id}`, onClick: () => onRetryRestore(record) })
    }
    return actions
  }

  function onDetail(record: any) {
    detailDrawer.title = '灰度执行详情'
    detailDrawer.content = JSON.stringify(record, null, 2)
    detailDrawer.visible = true
  }

  function onRetryRestore(record: any) {
    Modal.confirm({
      title: '恢复灰度',
      content: `确认根据执行记录 ${record.id} 重新恢复灰度？`,
      onOk: async () => {
        actionLoading.value = `restore-${record.id}`
        try {
          const res = await postGrayExecutionRetryRestore({ execution_log_id: record.id })
          if (res.data?.status === 1) {
            Message.success('恢复成功')
          } else {
            Message.error('恢复失败，请在执行记录中查看详情')
          }
          await onSearch()
        } finally {
          actionLoading.value = ''
        }
      },
    })
  }

  function onCleanupExpired() {
    Modal.confirm({
      title: '清理灰度执行记录',
      content: '确认删除 1 个月前的灰度执行记录？该操作不可恢复。',
      onOk: async () => {
        actionLoading.value = 'cleanup-expired'
        try {
          const res = await postGrayExecutionLogCleanupExpired({ retention_days: 30 })
          Message.success(`清理完成，共删除 ${res.data?.deleted_count || 0} 条`)
          await onSearch()
        } finally {
          actionLoading.value = ''
        }
      },
    })
  }

  onMounted(async () => {
    await loadOptions()
    await onSearch()
  })
</script>
