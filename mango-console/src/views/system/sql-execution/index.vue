<template>
  <TableBody ref="tableBody" content-flush>
    <template #header>
      <TableHeader
        :show-filter="true"
        title="SQL执行记录"
        @search="doRefresh"
        @reset-search="onResetSearch"
      >
        <template #search-content>
          <a-form :model="{}" layout="inline" @keyup.enter="doRefresh">
            <a-form-item v-for="item in conditionItems" :key="item.key" :label="item.label">
              <a-input
                v-if="item.type === 'input'"
                v-model="item.value"
                :placeholder="item.placeholder"
                @blur="doRefresh"
              />
              <a-select
                v-else-if="item.type === 'select'"
                v-model="item.value"
                :field-names="fieldNames"
                :options="selectOptions(String(item.key))"
                :placeholder="item.placeholder"
                allow-clear
                allow-search
                value-key="key"
                @change="doRefresh"
              />
              <a-range-picker
                v-else-if="item.type === 'range'"
                v-model="item.value"
                show-time
                value-format="YYYY-MM-DD HH:mm:ss"
                @change="doRefresh"
              />
            </a-form-item>
          </a-form>
        </template>
      </TableHeader>
    </template>

    <template #default>
      <a-table
        :scroll="{ x: tableScrollX }"
        :bordered="false"
        :columns="tableColumns"
        :data="table.dataList"
        :loading="table.tableLoading.value"
        :pagination="false"
        :row-key="rowKey"
      >
        <template #columns>
          <a-table-column
            v-for="item in tableColumns"
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
              <a-tag :color="optionTagColor('test_env', record.test_env)" size="small">
                {{ record.test_env_name || '-' }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'source_type'" #cell="{ record }">
              <a-tag :color="optionTagColor('source_type', record.source_type)" size="small">
                {{ optionTitle('source_type', record.source_type) }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'status'" #cell="{ record }">
              <a-tag :color="statusColor(record.status)" size="small">
                {{ statusText(record.status) }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'duration_ms'" #cell="{ record }">
              {{ formatDuration(record.duration_ms) }}
            </template>
            <template v-else-if="item.key === 'is_slow'" #cell="{ record }">
              <a-tag :color="record.is_slow ? 'orange' : 'green'" size="small">
                {{ record.is_slow ? '慢SQL' : '正常' }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'operations'" #cell="{ record }">
              <MangoTableActions
                :actions="[
    {
        key: 'detail',
        label: '详情',
        onClick: () => openDetail(record), },
]"
              />
            </template>
          </a-table-column>
        </template>
      </a-table>
    </template>

    <template #footer>
      <TableFooter :pagination="pagination" />
    </template>
  </TableBody>

  <BaseSidePanel v-model:visible="detail.visible" title="SQL执行详情" width="720px">
    <a-descriptions v-if="detail.record" :column="2" bordered size="small">
      <a-descriptions-item label="记录ID">{{ detail.record.id }}</a-descriptions-item>
      <a-descriptions-item label="请求ID">{{ detail.record.request_id }}</a-descriptions-item>
      <a-descriptions-item label="来源">
        {{ detail.record.source_type }} #{{ detail.record.source_id || '-' }}
      </a-descriptions-item>
      <a-descriptions-item label="阶段">{{ detail.record.source_stage }}</a-descriptions-item>
      <a-descriptions-item label="项目产品">
        {{ detail.record.project_product_name }}
      </a-descriptions-item>
      <a-descriptions-item label="被测环境">{{ detail.record.test_env_name }}</a-descriptions-item>
      <a-descriptions-item label="逻辑数据源">
        {{ detail.record.datasource_alias_name }}
      </a-descriptions-item>
      <a-descriptions-item label="实际数据库">
        {{ detail.record.database_name || '-' }}
      </a-descriptions-item>
      <a-descriptions-item label="状态">{{ statusText(detail.record.status) }}</a-descriptions-item>
      <a-descriptions-item label="耗时">
        {{ formatDuration(detail.record.duration_ms) }}
      </a-descriptions-item>
    </a-descriptions>

    <div v-if="detail.record" class="mango-sql-execution-detail">
      <section>
        <h4>来源说明</h4>
        <JsonDisplay :data="detail.record.source_detail || {}" :default-expanded="true" />
      </section>
      <section>
        <h4>执行 SQL</h4>
        <pre class="mango-code-panel">{{ detail.record.sql_text || '-' }}</pre>
      </section>
      <section>
        <h4>SQL 参数</h4>
        <JsonDisplay :data="detail.record.sql_parameters || {}" :default-expanded="true" />
      </section>
      <section>
        <h4>结果预览</h4>
        <pre class="mango-code-panel">{{ detail.record.result_preview || '-' }}</pre>
        <div v-if="detail.record.result_truncated" class="mango-sql-execution-tip">
          内容已截断，仅保留前 1000 个字符。
        </div>
      </section>
      <section v-if="detail.record.error_message">
        <h4>错误信息</h4>
        <pre class="mango-code-panel">{{ detail.record.error_message }}</pre>
      </section>
    </div>
  </BaseSidePanel>
</template>

<script lang="ts" setup>
  import { onMounted, reactive } from 'vue'
  import { fieldNames } from '@/setting'
  import { usePagination, useRowKey, useTable } from '@/hooks/table'
  import { getFormItems } from '@/utils/datacleaning'
  import { getSqlExecutionList, getSqlExecutionOptions } from '@/api/system/sql_execution'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import JsonDisplay from '@/components/display/JsonDisplay.vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import { useEnum } from '@/store/modules/get-enum'
  import { getEnumTagColor } from '@/utils/business-format'
  import { conditionItems, tableColumns, tableScrollX } from './config'

  const table = useTable()
  const enumStore = useEnum()
  const rowKey = useRowKey('id')
  const pagination = usePagination(doRefresh, () => table.tableLoading)
  const data = reactive<any>({ options: {} })
  const detail = reactive<any>({ visible: false, record: null })

  function selectOptions(key: string) {
    const optionKeys: Record<string, string> = {
      project_product_id: 'project_product_options',
      source_type: 'source_type_options',
      source_stage: 'source_stage_options',
      test_env: 'environment_options',
      datasource_alias_id: 'datasource_alias_options',
      status: 'status_options',
      is_slow: 'slow_options',
    }
    return data.options[optionKeys[key]] || []
  }

  function optionTitle(key: string, value: string | number) {
    return (
      selectOptions(key).find((item: any) => String(item.key) === String(value))?.title ||
      value ||
      '-'
    )
  }

  function optionTagColor(key: string, value: string | number) {
    return getEnumTagColor(selectOptions(key), value, enumStore.colors)
  }

  function buildQuery() {
    const values = getFormItems(conditionItems)
    const createTime = Array.isArray(values.create_time) ? values.create_time : []
    delete values.create_time
    if (createTime.length === 2) {
      values.create_time_start = createTime[0]
      values.create_time_end = createTime[1]
    }
    return Object.fromEntries(
      Object.entries(values).filter(
        ([, value]) => value !== '' && value !== null && value !== undefined
      )
    )
  }

  function doRefresh() {
    table.tableLoading.value = true
    return getSqlExecutionList({
      ...buildQuery(),
      page: pagination.page,
      pageSize: pagination.pageSize,
    })
      .then((res) => {
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
      })
      .catch(() => {
        table.tableLoading.value = false
      })
  }

  function onResetSearch() {
    conditionItems.forEach((item) => {
      item.value = item.type === 'range' ? [] : ''
    })
    doRefresh()
  }

  function openDetail(record: any) {
    detail.record = record
    detail.visible = true
  }

  function statusText(status: string) {
    return (
      { running: '执行中', success: '成功', fail: '失败', timeout: '超时' }[status] || status || '-'
    )
  }

  function statusColor(status: string) {
    return { running: 'blue', success: 'green', fail: 'red', timeout: 'orange' }[status] || 'gray'
  }

  function formatDuration(value: unknown) {
    if (value === null || value === undefined || value === '') return '-'
    const duration = Number(value)
    return Number.isFinite(duration) ? `${duration.toFixed(2)} ms` : `${value} ms`
  }

  onMounted(async () => {
    const [, options] = await Promise.all([enumStore.getEnum(), getSqlExecutionOptions()])
    data.options = options.data || {}
    await doRefresh()
  })
</script>

<style scoped>
  .mango-sql-execution-detail {
    display: grid;
    gap: var(--m-page-gap);
    margin-top: var(--m-page-gap);
  }

  .mango-sql-execution-detail section h4 {
    margin: 0 0 6px;
  }

  .mango-sql-execution-detail .mango-code-panel {
    max-height: 260px;
    margin: 0;
    overflow: auto;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .mango-sql-execution-tip {
    margin-top: 4px;
    color: var(--m-warning);
  }
</style>
