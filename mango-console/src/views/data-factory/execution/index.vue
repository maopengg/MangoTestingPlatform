<template>
  <TableBody>
    <template #header>
      <TableHeader title="数据工厂 / 执行记录" @search="doRefresh" @reset-search="onResetSearch">
        <template #search-content>
          <a-form :model="{}" layout="inline" @keyup.enter="doRefresh">
            <a-form-item
              v-for="item of executionConditionItems"
              :key="item.key"
              :label="item.label"
            >
              <template v-if="item.type === 'input'">
                <a-input
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  allow-clear
                  @blur="doRefresh"
                  @clear="doRefresh"
                />
              </template>
              <template v-else-if="item.type === 'cascader' && item.key === 'project_product'">
                <ProjectProductSelect
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  @change="onSearchProjectChange(item.value)"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'module'">
                <ProductModuleSelect
                  v-model="item.value"
                  :project-product-id="getSearchItemValue('project_product')"
                  :placeholder="item.placeholder"
                  :auto-clear="false"
                  @change="doRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'stage'">
                <a-select
                  v-model="item.value"
                  :field-names="enumFieldNames"
                  :options="enumStore.data_factory_execution_stage"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="doRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'status'">
                <a-select
                  v-model="item.value"
                  :field-names="enumFieldNames"
                  :options="enumStore.data_factory_execution_status"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="doRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'cleanup_status'">
                <a-select
                  v-model="item.value"
                  :field-names="enumFieldNames"
                  :options="enumStore.data_factory_cleanup_status"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="doRefresh"
                />
              </template>
            </a-form-item>
          </a-form>
        </template>
      </TableHeader>
    </template>

    <template #default>
      <a-table
        :columns="executionTableColumns"
        :data="table.dataList"
        :loading="table.tableLoading.value"
        :pagination="false"
        :row-key="'id'"
        :scroll="{ x: 1420 }"
      >
        <template #columns>
          <a-table-column
            v-for="item of executionTableColumns"
            :key="item.key"
            :align="item.align"
            :data-index="item.key"
            :fixed="item.fixed"
            :ellipsis="item.ellipsis"
            :tooltip="item.tooltip"
            :title="item.title"
            :width="item.width"
          >
            <template v-if="item.key === 'index'" #cell="{ record }">
              {{ record.id }}
            </template>
            <template v-else-if="item.key === 'project_product'" #cell="{ record }">
              {{ formatProjectProductPath(record?.project_product) }}
            </template>
            <template v-else-if="item.key === 'module'" #cell="{ record }">
              {{ formatModulePath(record?.module) }}
            </template>
            <template v-else-if="item.key === 'source_display'" #cell="{ record }">
              <div class="execution-source-cell">
                <a-tooltip :content="record.source_display || '-'" position="top" mini>
                  <span class="execution-source-cell__title">{{ record.source_display || '-' }}</span>
                </a-tooltip>
                <span class="execution-source-cell__meta">
                  {{ formatSourceMeta(record.source_info) }}
                </span>
              </div>
            </template>
            <template v-else-if="item.key === 'stage'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record.stage]" size="small">
                {{ enumTitle(enumStore.data_factory_execution_stage, record.stage) }}</a-tag
              >
            </template>
            <template v-else-if="item.key === 'status'" #cell="{ record }">
              <a-tag :color="enumStore.status_colors[record.status]" size="small">
                {{ enumTitle(enumStore.data_factory_execution_status, record.status) }}</a-tag
              >
            </template>
            <template v-else-if="item.key === 'cleanup_status'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record.cleanup_status]" size="small">{{
                enumTitle(enumStore.data_factory_cleanup_status, record.cleanup_status)
              }}</a-tag>
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <MangoTableActions
                :actions="[
                  {
                    label: '详情',
                    loading: actionLoading === `detail-${record.id}`,
                    onClick: () => openDetail(record),
                  },
                  {
                    label: record.cleanup_status === 1 ? '重试清理' : '清理',
                    danger: true,
                    loading: actionLoading === `cleanup-${record.id}`,
                    onClick: () => cleanup(record),
                  },
                ]"
              />
            </template>
          </a-table-column>
        </template>
      </a-table>
    </template>

    <template #footer><TableFooter :pagination="pagination" /></template>
  </TableBody>

  <a-drawer v-model:visible="detailVisible" title="执行详情" width="860px">
    <a-tabs>
      <a-tab-pane key="source" title="来源">
        <div class="execution-source-detail">
          <div class="execution-source-detail__item">
            <span class="execution-source-detail__label">来源类型</span>
            <span class="execution-source-detail__value">
              {{ detail.execution?.source_info?.source_type_name || '-' }}
            </span>
          </div>
          <div class="execution-source-detail__item">
            <span class="execution-source-detail__label">执行人</span>
            <span class="execution-source-detail__value">
              {{ formatUserName(detail.execution?.source_info?.executor_name, detail.execution?.source_info?.executor_username) }}
            </span>
          </div>
          <div class="execution-source-detail__item">
            <span class="execution-source-detail__label">用例责任人</span>
            <span class="execution-source-detail__value">
              {{ formatUserName(detail.execution?.source_info?.case_owner_name, detail.execution?.source_info?.case_owner_username) }}
            </span>
          </div>
          <div class="execution-source-detail__item">
            <span class="execution-source-detail__label">触发用例</span>
            <span class="execution-source-detail__value">
              {{ detail.execution?.source_info?.case_name || '-' }}
            </span>
          </div>
          <div class="execution-source-detail__item">
            <span class="execution-source-detail__label">所属模块</span>
            <span class="execution-source-detail__value">
              {{ detail.execution?.source_info?.ui_module_name || '-' }}
            </span>
          </div>
          <div class="execution-source-detail__item">
            <span class="execution-source-detail__label">接口</span>
            <span class="execution-source-detail__value">
              {{ detail.execution?.source_info?.api_info_name || '-' }}
            </span>
          </div>
          <div class="execution-source-detail__item execution-source-detail__item--wide">
            <span class="execution-source-detail__label">接口地址</span>
            <span class="execution-source-detail__value">
              {{ formatApiInfo(detail.execution?.source_info) }}
            </span>
          </div>
          <div class="execution-source-detail__item">
            <span class="execution-source-detail__label">接口场景</span>
            <span class="execution-source-detail__value">
              {{ detail.execution?.source_info?.scenario_name || '-' }}
            </span>
          </div>
          <div class="execution-source-detail__item">
            <span class="execution-source-detail__label">场景模板</span>
            <span class="execution-source-detail__value">
              {{ detail.execution?.source_info?.template_name || '-' }}
            </span>
          </div>
          <div class="execution-source-detail__item">
            <span class="execution-source-detail__label">来源ID</span>
            <span class="execution-source-detail__value">
              {{ formatSourceId(detail.execution?.source_info) }}
            </span>
          </div>
        </div>
      </a-tab-pane>
      <a-tab-pane key="context" title="上下文">
        <JsonDisplay :data="detail.context || {}" />
      </a-tab-pane>
      <a-tab-pane key="items" title="创建明细">
        <a-table
          :columns="executionItemColumns"
          :data="detail.items || []"
          :loading="detailLoading"
          :pagination="false"
          :scroll="{ x: 1200 }"
        >
          <template #columns>
            <a-table-column
              v-for="item of executionItemColumns"
              :key="item.key"
              :align="item.align"
              :data-index="item.key"
              :ellipsis="item.ellipsis"
              :tooltip="item.tooltip"
              :title="item.title"
              :width="item.width"
            >
              <template v-if="item.key === 'index'" #cell="{ record }">
                {{ record.id }}
              </template>
              <template v-else-if="item.key === 'cleanup_status'" #cell="{ record }">
                {{ enumTitle(enumStore.data_factory_cleanup_status, record.cleanup_status) }}
              </template>
              <template v-else-if="item.key === 'cleanup_sql'" #cell="{ record }">
                <div v-if="record.cleanup_sql" class="execution-detail-cell-stack">
                  <div class="execution-detail-cell-line">
                    <a-tooltip :content="record.cleanup_sql" position="top" mini>
                      <span class="execution-detail-cell-text">{{ record.cleanup_sql }}</span>
                    </a-tooltip>
                    <a-tooltip content="复制清理SQL" position="top" mini>
                      <a-button
                        class="execution-detail-copy-button"
                        type="text"
                        size="mini"
                        @click="copyCellValue(record.cleanup_sql, '清理SQL')"
                      >
                        <template #icon>
                          <icon-copy />
                        </template>
                      </a-button>
                    </a-tooltip>
                  </div>
                  <a-tooltip
                    v-if="hasObjectValue(record.cleanup_sql_params)"
                    :content="stringifyCellValue(record.cleanup_sql_params)"
                    position="top"
                    mini
                  >
                    <span class="execution-detail-cell-text execution-detail-cell-text--muted">
                      参数：{{ stringifyCellValue(record.cleanup_sql_params) }}
                    </span>
                  </a-tooltip>
                </div>
                <span v-else>-</span>
              </template>
              <template v-else-if="item.key === 'insert_sql'" #cell="{ record }">
                <div v-if="record.insert_sql" class="execution-detail-cell-line">
                  <a-tooltip :content="record.insert_sql" position="top" mini>
                    <span class="execution-detail-cell-text">{{ record.insert_sql }}</span>
                  </a-tooltip>
                  <a-tooltip content="复制插入SQL" position="top" mini>
                    <a-button
                      class="execution-detail-copy-button"
                      type="text"
                      size="mini"
                      @click="copyCellValue(record.insert_sql, '插入SQL')"
                    >
                      <template #icon>
                        <icon-copy />
                      </template>
                    </a-button>
                  </a-tooltip>
                </div>
                <span v-else>-</span>
              </template>
              <template v-else-if="item.key === 'data'" #cell="{ record }">
                <div class="execution-detail-cell-line">
                  <a-tooltip :content="stringifyCellValue(record.data)" position="top" mini>
                    <span class="execution-detail-cell-text">
                      {{ stringifyCellValue(record.data) }}
                    </span>
                  </a-tooltip>
                  <a-tooltip content="复制创建数据" position="top" mini>
                    <a-button
                      class="execution-detail-copy-button"
                      type="text"
                      size="mini"
                      @click="copyCellValue(record.data, '创建数据')"
                    >
                      <template #icon>
                        <icon-copy />
                      </template>
                    </a-button>
                  </a-tooltip>
                </div>
              </template>
            </a-table-column>
          </template>
        </a-table>
      </a-tab-pane>
      <a-tab-pane key="error" title="错误">
        <a-alert v-if="detail.execution?.error_message" type="error">{{
          detail.execution.error_message
        }}</a-alert>
        <div v-else class="mango-empty-state execution-empty">暂无错误</div>
      </a-tab-pane>
    </a-tabs>
  </a-drawer>
</template>

<script lang="ts" setup>
  import {
    getDataFactoryExecution,
    getDataFactoryExecutionDetail,
    postDataFactoryExecutionCleanup,
  } from '@/api/data-factory'
  import { usePagination, useTable } from '@/hooks/table'
  import { useEnum } from '@/store/modules/get-enum'
  import { getFormItems } from '@/utils/datacleaning'
  import JsonDisplay from '@/components/display/JsonDisplay.vue'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import {
    formatModulePath,
    formatProjectProductPath,
    getItemValue,
  } from '@/utils/business-format'
  import { Message, Modal } from '@arco-design/web-vue'
  import { onMounted, ref } from 'vue'
  import { executionConditionItems, executionItemColumns, executionTableColumns } from './config'

  const table = useTable()
  const pagination = usePagination(doRefresh)
  const enumStore = useEnum()
  const enumFieldNames = { value: 'key', label: 'title' }
  const detailVisible = ref(false)
  const detail = ref<any>({})
  const detailLoading = ref(false)
  const actionLoading = ref('')

  function enumTitle(options: any[] = [], value: any) {
    return options.find((it) => it.key === value)?.title || value
  }

  function getOptionId(value: any) {
    return value?.id ?? value
  }

  function stringifyCellValue(value: any) {
    if (typeof value === 'string') return value
    if (typeof value === 'undefined' || value === null) return '-'
    return JSON.stringify(value)
  }

  function hasObjectValue(value: any) {
    return value && typeof value === 'object' && Object.keys(value).length > 0
  }

  function formatSourceMeta(sourceInfo: any) {
    if (!sourceInfo) return '-'
    const parts = [
      sourceInfo.executor_name ? `执行人 ${sourceInfo.executor_name}` : '',
      !sourceInfo.executor_name && sourceInfo.case_owner_name
        ? `责任人 ${sourceInfo.case_owner_name}`
        : '',
      sourceInfo.case_id ? `用例ID ${sourceInfo.case_id}` : '',
      sourceInfo.scenario_id ? `场景ID ${sourceInfo.scenario_id}` : '',
      sourceInfo.template_id ? `模板ID ${sourceInfo.template_id}` : '',
    ].filter(Boolean)
    return parts.join(' / ') || formatSourceId(sourceInfo)
  }

  function formatSourceId(sourceInfo: any) {
    if (!sourceInfo) return '-'
    const parts = [
      sourceInfo.source_id ? `来源 ${sourceInfo.source_id}` : '',
      sourceInfo.template_id ? `模板 ${sourceInfo.template_id}` : '',
    ].filter(Boolean)
    return parts.join(' / ') || '-'
  }

  function formatUserName(name?: string, username?: string) {
    if (name && username) return `${name}（${username}）`
    return name || username || '-'
  }

  function formatApiInfo(sourceInfo: any) {
    if (!sourceInfo?.api_info_url) return '-'
    const method = sourceInfo.api_info_method_name ? `${sourceInfo.api_info_method_name} ` : ''
    return `${method}${sourceInfo.api_info_url}`
  }

  function fallbackCopy(text: string) {
    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.setAttribute('readonly', 'readonly')
    textarea.style.position = 'fixed'
    textarea.style.left = '-9999px'
    textarea.style.top = '0'
    document.body.appendChild(textarea)
    textarea.select()
    textarea.setSelectionRange(0, textarea.value.length)
    const success = document.execCommand('copy')
    document.body.removeChild(textarea)
    return success
  }

  async function copyCellValue(value: any, label: string) {
    const text = stringifyCellValue(value)
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text)
      } else if (!fallbackCopy(text)) {
        throw new Error('copy failed')
      }
      Message.success(`复制${label}成功`)
    } catch {
      Message.error(`复制${label}失败`)
    }
  }

  function getSearchItem(key: string) {
    return executionConditionItems.find((item) => item.key === key)
  }

  function getSearchItemValue(key: string) {
    return getItemValue(executionConditionItems, key)
  }

  function onSearchProjectChange(value: any) {
    const moduleItem = getSearchItem('module')
    if (moduleItem) {
      moduleItem.value = ''
    }
    doRefresh()
  }

  function doRefresh() {
    table.tableLoading.value = true
    const query = getFormItems(executionConditionItems)
    getDataFactoryExecution({
      ...query,
      page: pagination.page,
      pageSize: pagination.pageSize,
    }).then((res) => {
      table.handleSuccess(res)
      pagination.setTotalSize((res as any).totalSize)
    })
  }

  function onResetSearch() {
    executionConditionItems.forEach((it) => {
      it.value = ''
    })
    doRefresh()
  }

  function openDetail(record: any) {
    actionLoading.value = `detail-${record.id}`
    detailLoading.value = true
    getDataFactoryExecutionDetail({ execution_id: record.id })
      .then((res) => {
        detail.value = res.data || {}
        detailVisible.value = true
      })
      .finally(() => {
        actionLoading.value = ''
        detailLoading.value = false
      })
  }

  function cleanup(record: any) {
    const forceCleanup = record.cleanup_status === 1
    Modal.confirm({
      title: forceCleanup ? '重试清理执行数据' : '清理执行数据',
      content: forceCleanup
        ? `该执行记录已标记为清理完成，确认重新按执行明细清理 ${record.execution_no} 创建的数据？`
        : `确认清理 ${record.execution_no} 创建的数据？`,
      onBeforeOk: () => {
        actionLoading.value = `cleanup-${record.id}`
        return postDataFactoryExecutionCleanup({ execution_id: record.id, force_cleanup: forceCleanup })
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .finally(() => {
            actionLoading.value = ''
          })
      },
    })
  }

  onMounted(() => {
    enumStore.getEnum()
    doRefresh()
  })
</script>
<style scoped>
  .execution-source-cell {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 2px;
  }

  .execution-source-cell__title {
    overflow: hidden;
    color: var(--m-text);
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .execution-source-cell__meta {
    overflow: hidden;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .execution-source-detail {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px 16px;
  }

  .execution-source-detail__item {
    min-width: 0;
    padding: 10px 12px;
    border: 1px solid var(--m-border);
    border-radius: 6px;
    background: var(--m-bg);
  }

  .execution-source-detail__item--wide {
    grid-column: 1 / -1;
  }

  .execution-source-detail__label {
    display: block;
    margin-bottom: 4px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .execution-source-detail__value {
    display: block;
    min-height: 22px;
    overflow: hidden;
    color: var(--m-text);
    line-height: 22px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .execution-empty {
    min-height: 120px;
  }

  .execution-detail-cell-stack {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 4px;
  }

  .execution-detail-cell-line {
    display: flex;
    min-width: 0;
    align-items: flex-start;
    gap: 4px;
  }

  .execution-detail-cell-text {
    display: -webkit-box;
    flex: 1;
    min-width: 0;
    max-height: 40px;
    overflow: hidden;
    color: var(--m-text);
    font-size: 12px;
    line-height: 20px;
    word-break: break-all;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
  }

  .execution-detail-cell-text--muted {
    color: var(--m-muted);
  }

  .execution-detail-copy-button {
    flex: none;
    width: 22px;
    height: 22px;
    padding: 0;
  }
</style>
