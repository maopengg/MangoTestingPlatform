<template>
  <BaseSidePanel
    :visible="visible"
    title="执行详情"
    :width="1000"
    :show-footer="false"
    @update:visible="
      (value) => {
        if (!value) close()
      }
    "
  >
    
    <MangoPanelSpin :loading="detailLoading">
      <a-tabs v-if="detail" v-model:active-key="activeTab">
        <a-tab-pane
          key="source"
          title="来源"
          data-testid="qa-views-data-factory-execution-tab-pane-来源"
        >
          <div class="mango-execution-source-detail">
            <div class="mango-execution-source-detail__item">
              <span class="mango-execution-source-detail__label">来源类型</span>
              <span class="mango-execution-source-detail__value">
                {{ detail.execution?.source_info?.source_type_name || '-' }}
              </span>
            </div>
            <div class="mango-execution-source-detail__item">
              <span class="mango-execution-source-detail__label">执行人</span>
              <span class="mango-execution-source-detail__value">
                {{
                  formatUserName(
                    detail.execution?.source_info?.executor_name,
                    detail.execution?.source_info?.executor_username
                  )
                }}
              </span>
            </div>
            <div class="mango-execution-source-detail__item">
              <span class="mango-execution-source-detail__label">用例责任人</span>
              <span class="mango-execution-source-detail__value">
                {{
                  formatUserName(
                    detail.execution?.source_info?.case_owner_name,
                    detail.execution?.source_info?.case_owner_username
                  )
                }}
              </span>
            </div>
            <div class="mango-execution-source-detail__item">
              <span class="mango-execution-source-detail__label">触发用例</span>
              <span class="mango-execution-source-detail__value">
                {{ detail.execution?.source_info?.case_name || '-' }}
              </span>
            </div>
            <div class="mango-execution-source-detail__item">
              <span class="mango-execution-source-detail__label">所属模块名称</span>
              <span class="mango-execution-source-detail__value">
                {{ detail.execution?.source_info?.ui_module_name || '-' }}
              </span>
            </div>
            <div class="mango-execution-source-detail__item">
              <span class="mango-execution-source-detail__label">接口</span>
              <span class="mango-execution-source-detail__value">
                {{ detail.execution?.source_info?.api_info_name || '-' }}
              </span>
            </div>
            <div
              class="mango-execution-source-detail__item mango-execution-source-detail__item--wide"
            >
              <span class="mango-execution-source-detail__label">接口地址</span>
              <span class="mango-execution-source-detail__value">
                {{ formatApiInfo(detail.execution?.source_info) }}
              </span>
            </div>
            <div class="mango-execution-source-detail__item">
              <span class="mango-execution-source-detail__label">接口场景</span>
              <span class="mango-execution-source-detail__value">
                {{ detail.execution?.source_info?.scenario_name || '-' }}
              </span>
            </div>
            <div class="mango-execution-source-detail__item">
              <span class="mango-execution-source-detail__label">场景模板</span>
              <span class="mango-execution-source-detail__value">
                {{ detail.execution?.source_info?.template_name || '-' }}
              </span>
            </div>
            <div class="mango-execution-source-detail__item">
              <span class="mango-execution-source-detail__label">来源ID</span>
              <span class="mango-execution-source-detail__value">
                {{ formatSourceId(detail.execution?.source_info) }}
              </span>
            </div>
          </div>
        </a-tab-pane>
        <a-tab-pane
          key="context"
          title="上下文"
          data-testid="qa-views-data-factory-execution-tab-pane-上下文"
        >
          <JsonDisplay :data="detail.context || {}" />
        </a-tab-pane>
        <a-tab-pane
          key="items"
          title="创建明细"
          data-testid="qa-views-data-factory-execution-tab-pane-创建明细"
        >
          <a-table
            class="mango-native-scroll-table"
            :columns="executionItemColumns"
            :data="detail.items || []"
            :pagination="false"
            :scroll="{ x: 1690, y: 450 }"
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
                <template v-else-if="item.key === 'storage_snapshot'" #cell="{ record }">
                  {{ formatStorageSnapshot(record.storage_snapshot) }}
                </template>
                <template v-else-if="item.key === 'sql_executions'" #cell="{ record }">
                  <div v-if="record.sql_executions?.length" class="mango-execution-sql-audit-list">
                    <div
                      v-for="sqlRecord in record.sql_executions"
                      :key="sqlRecord.id"
                      class="mango-execution-sql-audit-item"
                    >
                      <a-tag size="small" :color="sqlExecutionStatusColor(sqlRecord.status)">
                        {{ sqlExecutionStageName(sqlRecord.source_stage) }}
                      </a-tag>
                      <a-tooltip :content="sqlRecord.sql_text" position="top" mini>
                        <span class="mango-execution-detail-cell-text">{{
                          sqlRecord.sql_text
                        }}</span>
                      </a-tooltip>
                      <span class="mango-execution-sql-audit-duration">
                        {{
                          sqlRecord.duration_ms === null
                            ? '历史记录'
                            : `${Number(sqlRecord.duration_ms || 0).toFixed(2)}ms`
                        }}
                      </span>
                      <a-tag v-if="sqlRecord.is_slow" size="small" color="orangered">慢执行</a-tag>
                      <a-tooltip content="复制执行内容" position="top" mini>
                        <a-button
                          class="mango-execution-detail-copy-button"
                          type="text"
                          size="mini"
                          :loading="copying"
                          @click="copyCellValue(sqlRecord.sql_text, 'SQL')"
                        >
                          <template #icon><icon-copy /></template>
                        </a-button>
                      </a-tooltip>
                    </div>
                  </div>
                  <span v-else>-</span>
                </template>
                <template v-else-if="item.key === 'data'" #cell="{ record }">
                  <div class="mango-execution-detail-cell-line">
                    <a-tooltip :content="stringifyCellValue(record.data)" position="top" mini>
                      <span class="mango-execution-detail-cell-text">
                        {{ stringifyCellValue(record.data) }}
                      </span>
                    </a-tooltip>
                    <a-tooltip content="复制创建数据" position="top" mini>
                      <a-button
                        class="mango-execution-detail-copy-button"
                        type="text"
                        size="mini"
                        :loading="copying"
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
        <a-tab-pane
          key="sql"
          title="数据源执行记录"
          data-testid="qa-views-data-factory-execution-tab-pane-SQL记录"
        >
          <a-table
            class="mango-native-scroll-table"
            :data="detail.sql_executions || []"
            :pagination="false"
            :scroll="{ x: 1180, y: 450 }"
          >
            <template #columns>
              <a-table-column title="阶段" :width="130">
                <template #cell="{ record }">
                  {{ sqlExecutionStageName(record.source_stage) }}
                </template>
              </a-table-column>
              <a-table-column title="状态" :width="110">
                <template #cell="{ record }">
                  <a-tag size="small" :color="sqlExecutionStatusColor(record.status)">
                    {{ sqlExecutionStatusName(record.status) }}
                  </a-tag>
                </template>
              </a-table-column>
              <a-table-column title="执行内容" :width="420">
                <template #cell="{ record }">
                  <div class="mango-execution-detail-cell-line">
                    <a-tooltip :content="record.sql_text" position="top" mini>
                      <span class="mango-execution-detail-cell-text">{{ record.sql_text }}</span>
                    </a-tooltip>
                    <a-button
                      class="mango-execution-detail-copy-button"
                      type="text"
                      size="mini"
                      :loading="copying"
                      @click="copyCellValue(record.sql_text, 'SQL')"
                    >
                      <template #icon><icon-copy /></template>
                    </a-button>
                  </div>
                </template>
              </a-table-column>
              <a-table-column title="耗时" :width="110">
                <template #cell="{ record }">
                  {{ Number(record.duration_ms || 0).toFixed(2) }}ms
                  <a-tag v-if="record.is_slow" size="small" color="orangered">慢</a-tag>
                </template>
              </a-table-column>
              <a-table-column title="影响行数" data-index="affected_rows" :width="100" />
              <a-table-column title="错误/结果" :width="310">
                <template #cell="{ record }">
                  <a-tooltip
                    :content="record.error_message || record.result_preview || '-'"
                    position="top"
                    mini
                  >
                    <span class="mango-execution-detail-cell-text">
                      {{ record.error_message || record.result_preview || '-' }}
                    </span>
                  </a-tooltip>
                </template>
              </a-table-column>
            </template>
          </a-table>
        </a-tab-pane>
        <a-tab-pane
          key="error"
          title="错误"
          data-testid="qa-views-data-factory-execution-tab-pane-错误"
        >
          <a-alert data-feedback-kind="execution-result" v-if="detail.execution?.error_message" type="error">{{
            detail.execution.error_message
          }}</a-alert>
          <div v-else class="mango-empty-state mango-execution-empty">暂无错误</div>
        </a-tab-pane>
        <a-tab-pane key="resources" title="关联资源清理">
          <a-table
            class="mango-native-scroll-table"
            :columns="cleanupResourceColumns"
            row-key="key"
            :data="cleanupResourceRows"
            :pagination="false"
            :scroll="{ x: 1340, y: 450 }"
          />
        </a-tab-pane>
      </a-tabs> </MangoPanelSpin
  ></BaseSidePanel>
</template>
<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { computed, ref, shallowRef } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { getDataFactoryExecutionDetail } from '@/api/data-factory'
  import { useEnum } from '@/store/modules/get-enum'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import MangoPanelSpin from '@/components/feedback/MangoPanelSpin.vue'
  import JsonDisplay from '@/components/display/JsonDisplay.vue'
  import { executionItemColumns, cleanupResourceColumns } from '../config'
  import {
    enumTitle,
    stringifyCellValue,
    formatUserName,
    formatSourceId,
    formatApiInfo,
    formatStorageSnapshot,
    sqlExecutionStatusColor,
    sqlExecutionStatusName,
    formatStage,
    cleanupResources,
  } from '../display'
  import { useExecutionScope } from '../composables/useExecutionScope'
  import type { ExecutionRecord, ExecutionDetail, JsonValue } from '../types'
  const enumStore = useEnum(),
    visible = ref(false),
    detail = shallowRef<ExecutionDetail | null>(null),
    detailLoading = ref(false),
    loadError = ref(false),
    activeTab = ref('source'),
    copying = ref(false)
  const cleanupResourceRows = computed(() => cleanupResources(detail.value))
  let id: number | null = null,
    request = 0
  const scope = useExecutionScope(close)
  const sqlExecutionStageName = (stage: string) =>
    formatStage(stage, enumStore.datasource_audit_stage || [])
  function open(record: ExecutionRecord) {
    if (!scope.isActive()) return
    close()
    id = record.id
    visible.value = true
    void load()
  }
  function close() {
    ++request
    visible.value = false
    id = null
    detail.value = null
    detailLoading.value = false
    loadError.value = false
    activeTab.value = 'source'
  }
  function refreshFor(value: number) {
    if (visible.value && id === value) void load()
  }
  async function load() {
    if (!visible.value || id === null || !scope.isActive()) return
    const current = ++request,
      version = scope.snapshot(),
      snapshot = id
    detailLoading.value = true
    loadError.value = false
    try {
      const response = await getDataFactoryExecutionDetail({ execution_id: snapshot })
      if (current === request && scope.current(version)) detail.value = response.data || null
    } catch (loadFailure0) {
      if (current === request && scope.current(version)) (reportLoadError(loadFailure0, "加载失败，请重试", false), loadError.value = true)
    } finally {
      if (current === request) detailLoading.value = false
    }
  }
  function fallbackCopy(text: string) {
    const textarea = document.createElement('textarea')
    textarea.className = 'mango-execution-copy-fallback'
    textarea.value = text
    textarea.setAttribute('readonly', 'readonly')
    document.body.appendChild(textarea)
    try {
      textarea.select()
      textarea.setSelectionRange(0, textarea.value.length)
      return document.execCommand('copy')
    } finally {
      textarea.remove()
    }
  }
  async function copyCellValue(value: JsonValue | undefined, label: string) {
    if (copying.value || !visible.value || !scope.isActive()) return
    const current = request,
      version = scope.snapshot(),
      text = stringifyCellValue(value)
    copying.value = true
    try {
      if (navigator.clipboard && window.isSecureContext) await navigator.clipboard.writeText(text)
      else if (!fallbackCopy(text)) throw Error('copy-failed')
      if (current === request && scope.current(version)) Message.success(`复制${label}成功`)
    } catch {
      if (current === request && scope.current(version)) Message.error(`复制${label}失败`)
    } finally {
      copying.value = false
    }
  }
  defineExpose({ open, close, refreshFor })
</script>
<style scoped>
  .mango-execution-source-cell {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 2px;
  }

  .mango-execution-selection-summary {
    color: var(--m-muted);
    font-size: 12px;
    white-space: nowrap;
  }

  .mango-execution-source-cell__title {
    overflow: hidden;
    color: var(--m-text);
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-execution-source-cell__meta {
    overflow: hidden;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-execution-source-detail {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px 16px;
  }

  .mango-execution-source-detail__item {
    min-width: 0;
    padding: 10px 12px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-bg);
  }

  .mango-execution-source-detail__item--wide {
    grid-column: 1 / -1;
  }

  .mango-execution-source-detail__label {
    display: block;
    margin-bottom: 4px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .mango-execution-source-detail__value {
    display: block;
    min-height: 22px;
    overflow: hidden;
    color: var(--m-text);
    line-height: 22px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-execution-empty {
    min-height: 120px;
  }

  .mango-execution-detail-cell-line {
    display: flex;
    min-width: 0;
    align-items: flex-start;
    gap: 4px;
  }

  .mango-execution-detail-cell-text {
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

  .mango-execution-detail-copy-button {
    flex: none;
    width: 22px;
    height: 22px;
    padding: 0;
  }

  .mango-execution-sql-audit-list {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 4px;
  }

  .mango-execution-sql-audit-item {
    display: flex;
    min-width: 0;
    align-items: center;
    gap: 6px;
  }

  .mango-execution-sql-audit-duration {
    flex: none;
    color: var(--m-muted);
    font-size: 12px;
    white-space: nowrap;
  }
  :global(.mango-execution-copy-fallback) {
    position: fixed;
    left: -9999px;
    top: 0;
  }
</style>
