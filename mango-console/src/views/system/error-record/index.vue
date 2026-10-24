<template>
  <TableBody ref="tableBody" content-flush>
    <template #header>
      <TableHeader
        :show-filter="true"
        title="系统异常记录"
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
                allow-clear
                @blur="doRefresh"
                @clear="doRefresh"
              />
              <a-select
                v-else-if="item.type === 'select'"
                v-model="item.value"
                :options="item.optionItems"
                :placeholder="item.placeholder"
                :multiple="item.multiple"
                :max-tag-count="item.multiple ? 1 : undefined"
                allow-clear
                @change="doRefresh"
              />
            </a-form-item>
          </a-form>
        </template>
      </TableHeader>
    </template>

    <template #default>
      <a-table
        :bordered="false"
        :columns="tableColumns"
        :data="table.dataList"
        :loading="table.tableLoading.value"
        :pagination="false"
        :scroll="{ x: tableScrollX }"
        row-key="__rowKey"
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
            <template v-if="item.key === 'source_name'" #cell="{ record }">
              <a-tag :color="sourceTypeColor(record.event_source)" size="small">
                {{ record.source_name || '-' }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'exception_type'" #cell="{ record }">
              {{ record.exception_type || '-' }}
            </template>
            <template v-else-if="item.key === 'count'" #cell="{ record }">
              {{ record.count || 1 }}
            </template>
            <template v-else-if="item.key === 'status_name'" #cell="{ record }">
              <a-tag color="red" size="small">{{ record.status_name || '异常' }}</a-tag>
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <MangoTableActions
                :actions="[
                  { permission: 'system.error_record:detail', label: '详情', onClick: () => openDetail(record) },
                  { permission: 'system.error_record:detail',
                    label: '来源页面',
                    hidden: !record.link,
                    onClick: () => openSource(record.link),
                  },
                  { permission: 'system.error_record:detail', label: '日志', onClick: () => openLog(record.log_query) },
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

  <BaseSidePanel
    v-model:visible="detail.visible"
    :show-footer="false"
    title="系统异常详情"
    width="760px"
  >
    <template #header-actions>
      <a-button v-if="detail.record" size="small" @click="copyErrorDetail">
        <template #icon><icon-copy /></template>
        复制详情
      </a-button>
    </template>

    <div v-if="detail.record" class="mango-error-record-panel">
      <section class="mango-error-record-section">
        <div class="mango-error-record-section__header">
          <div>
            <h3>基础信息</h3>
            <p>异常来源、发生位置和聚合次数</p>
          </div>
          <a-tag color="red" size="small">{{ detail.record.status_name || '异常' }}</a-tag>
        </div>
        <a-descriptions :column="2" bordered size="small">
          <a-descriptions-item label="记录类型">
            <a-tag :color="sourceTypeColor(detail.record.event_source)" size="small">
              {{ detail.record.source_name || '-' }}
            </a-tag>
          </a-descriptions-item>
          <a-descriptions-item label="记录ID">{{ detail.record.object_id }}</a-descriptions-item>
          <a-descriptions-item label="发生时间">{{
            detail.record.time || '-'
          }}</a-descriptions-item>
          <a-descriptions-item label="出现次数">{{ detail.record.count || 1 }}</a-descriptions-item>
          <a-descriptions-item label="服务名称">
            {{ detail.record.service_name || '-' }}
          </a-descriptions-item>
          <a-descriptions-item label="异常类型">
            {{ detail.record.exception_type || '-' }}
          </a-descriptions-item>
          <a-descriptions-item label="对象" :span="2">
            <span class="mango-error-record-object">{{ detail.record.title || '-' }}</span>
          </a-descriptions-item>
        </a-descriptions>
      </section>

      <section class="mango-error-record-section">
        <div class="mango-error-record-section__header">
          <div>
            <h3>错误摘要</h3>
            <p>用于快速识别本次异常原因</p>
          </div>
          <a-button size="mini" type="text" @click="copyText(detail.record.message, '错误摘要')">
            <template #icon><icon-copy /></template>
            复制
          </a-button>
        </div>
        <div class="mango-error-record-summary">{{ detail.record.message || '-' }}</div>
      </section>

      <section
        v-if="detail.record.traceback"
        class="mango-error-record-section mango-error-record-trace"
      >
        <div class="mango-error-record-section__header">
          <div>
            <h3>异常堆栈</h3>
            <p>{{ tracebackLineCount }} 行 · 支持横向和纵向滚动</p>
          </div>
          <a-button size="mini" type="text" @click="copyText(detail.record.traceback, '异常堆栈')">
            <template #icon><icon-copy /></template>
            复制
          </a-button>
        </div>
        <pre class="mango-code-panel">{{ detail.record.traceback }}</pre>
      </section>

      <div v-else class="mango-empty-state">该记录没有异常堆栈</div>
    </div>
  </BaseSidePanel>
</template>

<script lang="ts" setup>
  import { computed, onMounted, reactive } from 'vue'
  import { useRouter } from 'vue-router'
  import { Message } from '@arco-design/web-vue'
  import { IconCopy } from '@arco-design/web-vue/es/icon'
  import { usePagination, useTable } from '@/hooks/table'
  import { getFormItems } from '@/utils/datacleaning'
  import { getSystemErrorRecordList } from '@/api/system/error-record'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import { useEnum } from '@/store/modules/get-enum'
  import { getEnumTagColor } from '@/utils/business-format'
  import { conditionItems, sourceTagOptions, tableColumns, tableScrollX } from './config'

  const router = useRouter()
  const enumStore = useEnum()
  const table = useTable()
  const pagination = usePagination(doRefresh, () => table.tableLoading)
  const detail = reactive<any>({ visible: false, record: null })
  const tracebackLineCount = computed(() => {
    const traceback = String(detail.record?.traceback || '')
    return traceback ? traceback.split('\n').length : 0
  })

  function buildQuery() {
    const query = Object.fromEntries(
      Object.entries(getFormItems(conditionItems)).filter(
        ([, value]) => value !== '' && value !== null && value !== undefined
      )
    )
    if (Array.isArray(query.source)) {
      query.source = query.source.filter(Boolean).join(',')
    }
    return query
  }

  function doRefresh() {
    table.tableLoading.value = true
    return getSystemErrorRecordList({
      ...buildQuery(),
      page: pagination.page,
      pageSize: pagination.pageSize,
    })
      .then((res) => {
        const rows = (res.data || []).map((item: any) => ({
          ...item,
          __rowKey: `${item.source}-${item.object_id}`,
        }))
        table.handleSuccess({ ...res, data: rows })
        pagination.setTotalSize((res as any).totalSize || 0)
      })
      .catch(() => {
        table.tableLoading.value = false
      })
  }

  function onResetSearch() {
    conditionItems.forEach((item) => {
      item.value = item.multiple ? [] : ''
    })
    doRefresh()
  }

  function openDetail(record: any) {
    detail.record = record
    detail.visible = true
  }

  function sourceTypeColor(source: string) {
    const normalizedSource = source === 'drf' ? 'http' : source
    return getEnumTagColor(sourceTagOptions, normalizedSource, enumStore.colors)
  }

  function openSource(link?: string) {
    if (link) router.push(link)
  }

  async function copyText(value: unknown, label: string) {
    const text = String(value || '').trim()
    if (!text) {
      Message.warning(`暂无${label}`)
      return
    }
    try {
      await navigator.clipboard.writeText(text)
      Message.success(`${label}已复制`)
    } catch {
      Message.error('复制失败，请手动选择文本复制')
    }
  }

  function copyErrorDetail() {
    const record = detail.record
    if (!record) return
    const text = [
      `记录类型：${record.source_name || '-'}`,
      `记录ID：${record.object_id || '-'}`,
      `发生时间：${record.time || '-'}`,
      `出现次数：${record.count || 1}`,
      `服务名称：${record.service_name || '-'}`,
      `异常类型：${record.exception_type || '-'}`,
      `对象：${record.title || '-'}`,
      `错误摘要：${record.message || '-'}`,
      record.traceback ? `异常堆栈：\n${record.traceback}` : '',
    ]
      .filter(Boolean)
      .join('\n')
    copyText(text, '异常详情')
  }

  function openLog(query?: string) {
    if (!query) {
      Message.warning('暂无日志查询条件')
      return
    }
    const logPlatformUrl = String(import.meta.env.VITE_APP_LOG_PLATFORM_URL || '').trim()
    if (logPlatformUrl) {
      const separator = logPlatformUrl.includes('?') ? '&' : '?'
      window.open(`${logPlatformUrl}${separator}query=${encodeURIComponent(query)}`, '_blank')
      return
    }
    navigator.clipboard?.writeText(query)
    Message.success('日志查询条件已复制')
  }

  onMounted(async () => {
    await enumStore.getEnum()
    doRefresh()
  })
</script>

<style scoped>
  .mango-error-record-panel {
    box-sizing: border-box;
    display: flex;
    min-height: 100%;
    padding: 0;
    flex-direction: column;
    gap: var(--m-page-gap);
    background: var(--m-bg);
  }

  .mango-error-record-section {
    padding: 16px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-lg);
    background: var(--m-surface);
    box-shadow: var(--m-shadow-sm);
  }

  .mango-error-record-section__header {
    display: flex;
    margin-bottom: 12px;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
  }

  .mango-error-record-section__header h3,
  .mango-error-record-section__header p {
    margin: 0;
  }

  .mango-error-record-section__header h3 {
    color: var(--m-text);
    font-size: 14px;
    font-weight: 600;
    line-height: 22px;
  }

  .mango-error-record-section__header p {
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .mango-error-record-object {
    word-break: break-all;
  }

  .mango-error-record-summary {
    padding: 10px 12px;
    border-left: 3px solid var(--m-danger);
    border-radius: var(--m-radius-sm);
    background: var(--m-surface-soft);
    color: var(--m-text);
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 13px;
    line-height: 20px;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .mango-error-record-trace {
    min-height: 0;
  }

  .mango-error-record-trace .mango-code-panel {
    max-height: 460px;
    min-height: 220px;
    margin: 0;
    overflow: auto;
    font-size: 12px;
    line-height: 20px;
    white-space: pre;
  }

  @media (max-width: 720px) {
    .mango-error-record-panel {
      padding: 0;
    }

    .mango-error-record-section {
      padding: 12px;
    }

    .mango-error-record-trace .mango-code-panel {
      max-height: calc(100vh - 560px);
      min-height: 180px;
    }
  }
</style>
