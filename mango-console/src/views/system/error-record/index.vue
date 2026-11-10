<template>
  <TableBody content-flush>
    <template #header>
      <TableHeader
        :show-filter="true"
        title="系统异常记录"
        @search="onSearch"
        @reset-search="onResetSearch"
      >
        <template #search-content>
          <a-form :model="{}" layout="inline" @keyup.enter="onSearch">
            <a-form-item v-for="item in conditionItems" :key="item.key" :label="item.label">
              <a-input
                v-if="item.type === 'input'"
                v-model="item.value"
                :placeholder="item.placeholder"
                allow-clear
                @blur="onSearch"
                @clear="onSearch"
              />
              <a-select
                v-else-if="item.type === 'select'"
                v-model="item.value"
                :options="item.optionItems"
                :placeholder="item.placeholder"
                :multiple="item.multiple"
                :max-tag-count="item.multiple ? 1 : undefined"
                allow-clear
                @change="onSearch"
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
        :data="rows"
        :loading="listLoading"
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
              {{ record.count }}
            </template>
            <template v-else-if="item.key === 'status_name'" #cell="{ record }">
              <a-tag :color="record.status === 'warning' ? 'orange' : 'red'" size="small">{{ record.status_name || '异常' }}</a-tag>
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <MangoTableActions
                :actions="[
    { label: '详情', onClick: () => openDetail(record) },
    {
        label: '来源页面',
        hidden: !record.link,
        loading: sourceOpening, disabled: sourceOpening, onClick: () => openSource(record.link), },
    { label: '日志', loading: copying, disabled: copying, onClick: () => openLog(record.log_query) },
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
    :width="760"
    @cancel="closeDetail"
  >
    <template #header-actions>
      <a-button v-if="detail.record" size="small" :loading="copying" @click="copyErrorDetail">
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
          <a-tag :color="detail.record.status === 'warning' ? 'orange' : 'red'" size="small">{{ detail.record.status_name || '异常' }}</a-tag>
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
          <a-descriptions-item label="出现次数">{{ detail.record.count }}</a-descriptions-item>
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
          <a-button size="mini" type="text" :loading="copying" @click="copyText(detail.record.message, '错误摘要')">
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
            <h3>{{ detail.record.status === 'warning' ? '校验诊断' : '异常堆栈' }}</h3>
            <p>{{ tracebackLineCount }} 行 · 支持横向和纵向滚动</p>
          </div>
          <a-button size="mini" type="text" :loading="copying" @click="copyText(detail.record.traceback, '异常堆栈')">
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
import { reportLoadError } from '@/utils/load-error'

  import { computed, onMounted, onBeforeUnmount, onActivated, onDeactivated, reactive, ref, watch } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import { Message } from '@arco-design/web-vue'
  import { IconCopy } from '@arco-design/web-vue/es/icon'
  import { usePagination } from '@/hooks/table'
  import useUserStore from '@/store/modules/user'
  import usePermissionStore from '@/store/modules/permission'
  import { getSystemErrorRecordList } from '@/api/system/error-record'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import { useEnum } from '@/store/modules/get-enum'
  import { getEnumTagColor } from '@/utils/business-format'
  import { createConditionItems, sourceTagOptions, tableColumns, tableScrollX } from './config'
  import { buildErrorRecordQuery, resetErrorRecordConditions, parseErrorRecords, errorRecordDetail, errorRecordSourcePath, errorRecordLogUrl } from './error-record'
  import type { ErrorRecordRow } from './error-record'

  const router = useRouter(), route = useRoute(), user = useUserStore(), permission = usePermissionStore(), pagePath = route.path
  const enumStore = useEnum(), conditionItems = createConditionItems()
  const rows = ref<ErrorRecordRow[]>([]), listLoading = ref(false), listError = ref('')
  const enumLoading = ref(false), enumError = ref('')
  const pagination = usePagination(doRefresh, listLoading)
  const detail = reactive<{ visible: boolean; record: ErrorRecordRow | null }>({ visible: false, record: null })
  const copying = ref(false), sourceOpening = ref(false)
  const tracebackLineCount = computed(() => detail.record?.traceback ? detail.record.traceback.split('\n').length : 0)
  let mounted = false, active = true, disposed = false, needsLoad = true, needsEnums = true
  let version = 0, listVersion = 0, enumVersion = 0, detailVersion = 0
  let pendingList: { key: string; promise: Promise<void> } | null = null
  const available = () => mounted && active && !disposed && route.path === pagePath && document.visibilityState === 'visible'
  const identity = () => JSON.stringify([route.fullPath, user.userId, user.roleId, user.token, user.selected_environment, permission.permissionKeys])
  const current = (generation: number, key: string) => available() && generation === version && key === identity()
  function buildQuery() { return buildErrorRecordQuery(conditionItems) }
  function doRefresh(): Promise<void> {
    if (!available()) { needsLoad = true; listLoading.value = false; return Promise.resolve() }
    const query = { ...buildQuery(), page: pagination.page, pageSize: pagination.pageSize }
    const context = version, identityKey = identity(), key = JSON.stringify([identityKey, query])
    if (pendingList?.key === key) return pendingList.promise
    const generation = ++listVersion
    listLoading.value = true; listError.value = ''; needsLoad = false
    const valid = () => current(context, identityKey) && generation === listVersion && key === JSON.stringify([identity(), { ...buildQuery(), page: pagination.page, pageSize: pagination.pageSize }])
    const promise = Promise.resolve().then(async () => {
      try {
        if (!valid()) return
        const result = parseErrorRecords(await getSystemErrorRecordList(query))
        if (!valid()) return
        rows.value = result.rows; pagination.setTotalSize(result.total)
      } catch (loadFailure0) { if (valid()) { rows.value = []; pagination.setTotalSize(0); (reportLoadError(loadFailure0, "系统异常加载失败，请重试", false), listError.value = '系统异常加载失败，请重试') } }
      finally { if (generation === listVersion) { listLoading.value = false; pendingList = null } }
    })
    pendingList = { key, promise }
    return promise
  }
  function onSearch() { pagination.page = 1; return doRefresh() }
  function onResetSearch() { resetErrorRecordConditions(conditionItems); return onSearch() }
  async function loadEnums() {
    if (!available() || enumLoading.value) return
    const generation = ++enumVersion, context = version, key = identity()
    enumLoading.value = true; enumError.value = ''; needsEnums = false
    try { await enumStore.getEnum() }
    catch (loadFailure1) { if (current(context, key) && generation === enumVersion) { (reportLoadError(loadFailure1, "来源颜色配置加载失败", false), enumError.value = '来源颜色配置加载失败'); needsEnums = true } }
    finally { if (generation === enumVersion) enumLoading.value = false }
  }
  function closeDetail() { detailVersion++; detail.visible = false; detail.record = null }
  function openDetail(record: ErrorRecordRow) {
    if (!available()) return
    detailVersion++; detail.record = { ...record }; detail.visible = true
  }
  function sourceTypeColor(source: string) {
    return getEnumTagColor(sourceTagOptions, source === 'drf' ? 'http' : source, enumStore.colors)
  }
  async function openSource(link: string) {
    if (!available() || sourceOpening.value) return
    const path = errorRecordSourcePath(link)
    if (!path) { Message.warning('暂无有效来源页面'); return }
    const context = version, key = identity()
    sourceOpening.value = true
    try { await router.push(path) }
    catch { if (current(context, key)) Message.error('来源页面打开失败，请重试') }
    finally { sourceOpening.value = false }
  }
  async function copyText(value: unknown, label: string, fromDetail = true) {
    if (!available() || copying.value || (fromDetail && !detail.visible)) return
    const text = typeof value === 'string' ? value.trim() : ''
    if (!text) { Message.warning(`暂无${label}`); return }
    const context = version, key = identity(), generation = detailVersion
    const valid = () => current(context, key) && (!fromDetail || (detail.visible && generation === detailVersion))
    copying.value = true
    try {
      if (!navigator.clipboard?.writeText) throw new Error('Clipboard unavailable')
      await navigator.clipboard.writeText(text)
      if (valid()) Message.success(`${label}已复制`)
    } catch { if (valid()) Message.error('复制失败，请手动选择文本复制') }
    finally { copying.value = false }
  }
  function copyErrorDetail() {
    if (!detail.record) return
    return copyText(errorRecordDetail(detail.record), '异常详情')
  }
  async function openLog(query: string) {
    if (!available()) return
    if (!query) { Message.warning('暂无日志查询条件'); return }
    const logPlatformUrl = String(import.meta.env.VITE_APP_LOG_PLATFORM_URL || '').trim()
    if (!logPlatformUrl) return copyText(query, '日志查询条件', false)
    const url = errorRecordLogUrl(logPlatformUrl, query, window.location.origin)
    if (!url) { Message.error('日志平台地址无效'); return }
    try { window.open(url, '_blank', 'noopener,noreferrer') }
    catch { Message.error('日志平台打开失败，请重试') }
  }
  function pause() {
    version++; listVersion++; enumVersion++; pendingList = null
    needsLoad = true; needsEnums = true; listLoading.value = false; enumLoading.value = false
    closeDetail()
  }
  function resume() {
    if (!available()) return
    if (needsLoad) void doRefresh()
    if (needsEnums) void loadEnums()
  }
  function visibilityChanged() { if (document.visibilityState === 'visible') resume(); else pause() }
  watch(identity, () => { pause(); rows.value = []; pagination.setTotalSize(0); pagination.page = 1; resume() }, { flush: 'sync' })
  watch(() => detail.visible, visible => { if (!visible && detail.record) closeDetail() })
  onMounted(() => { mounted = true; document.addEventListener('visibilitychange', visibilityChanged); resume() })
  onActivated(() => { active = true; resume() })
  onDeactivated(() => { active = false; pause() })
  onBeforeUnmount(() => { disposed = true; pause(); document.removeEventListener('visibilitychange', visibilityChanged) })
</script>

<style scoped>
  .mango-error-record-feedback {
    padding: var(--m-page-gap);
    color: var(--m-muted);
  }

  .mango-error-record-feedback--error {
    color: var(--m-danger);
  }

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

</style>
