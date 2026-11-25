<template>
  <BaseSidePanel v-model:visible="visible" title="执行内容检索" :width="1100" cancel-button-text="关闭" @cancel="close">
    <div class="mango-content-search">
      <a-form :model="draft" layout="horizontal" class="mango-content-search-form" @submit-success="start">
        <a-form-item field="product" label="项目产品">
          <ProjectProductSelect v-model="draft.product" :disabled="busy" placeholder="全部可访问项目产品" />
        </a-form-item>
        <a-form-item field="environment" label="被测环境">
          <a-select v-model="draft.environment" :options="environments" :loading="optionsLoading" :disabled="busy" placeholder="全部被测环境" allow-clear />
        </a-form-item>
        <a-form-item field="day" label="搜索日期" required>
          <a-date-picker v-model="draft.day" value-format="YYYY-MM-DD" :disabled-date="disabledDate" :disabled="busy" :allow-clear="false" />
        </a-form-item>
        <a-form-item field="keyword" label="关键词" required>
          <a-input v-model="draft.keyword" :max-length="200" :disabled="busy" placeholder="输入业务 ID、名称或特征值" @press-enter="start" />
        </a-form-item>
      </a-form>
      <a-space wrap>
        <a-button type="primary" size="small" :loading="starting" :disabled="busy || optionsLoading" @click="start">开始检索</a-button>
        <a-button v-if="running" size="small" :loading="cancelling" @click="cancel">取消检索</a-button>
        <span class="mango-content-search-note">仅检索所选日期当天的数据</span>
      </a-space>
      <div v-if="task" class="mango-content-search-summary" aria-live="polite">
        <a-spin v-if="running" :size="14" />
        <strong>{{ enums.execution_content_search_status.find(item => item.key === task?.status)?.title || statuses[task.status] }}</strong>
        <span>已处理 {{ task.scanned }} 条执行记录 · 命中 {{ task.count }} 条 · 覆盖缺口 {{ task.skipped }} 条 · 累计读取 {{ (task.read_bytes / 1048576).toFixed(2) }}MiB</span>
        <span v-if="task.message" data-feedback-kind="execution-result">{{ task.message }}</span>
      </div>
      <div class="mango-content-search-note">仅限制单份文件解压后不超过 20MiB；不限制累计大小、记录数、命中数和检索时长。逐份读取并释放内容，结果分页展示。文件超限、缺失或内容截断会标记“检索不完整”；未命中不代表不是平台创建，命中也不等于由平台创建。</div>
      <a-table v-if="task" :data="task.items" :loading="reading" :pagination="false" :bordered="false"
        :scroll="{ x: 1080, y: 400 }" class="mango-native-scroll-table" row-key="record_id">
        <template #columns>
          <a-table-column title="执行记录" :width="170">
            <template #cell="{ record }">
              <div>#{{ record.record_id }}</div>
              <small>{{ record.create_time.replace('T', ' ').slice(0, 19) }}</small>
            </template>
          </a-table-column>
          <a-table-column title="关联用例 / 来源" :width="260">
            <template #cell="{ record }">
              <div>{{ targetNames[record.target_type] || record.target_type }}<template v-if="record.target_id"> #{{ record.target_id }}</template></div>
              <div class="mango-content-search-name" :title="record.name">{{ record.name || '未记录用例名称' }}</div>
              <small>{{ record.stage || record.source_type }}<template v-if="record.trigger_user"> · {{ record.trigger_user }}</template></small>
              <div v-if="record.report_id">执行报告 #{{ record.report_id }}</div>
            </template>
          </a-table-column>
          <a-table-column title="命中位置与片段" :width="490">
            <template #cell="{ record }">
              <div class="mango-content-search-path">{{ record.path }}</div>
              <span v-for="(part, index) in highlight(record.snippet)" :key="index">
                <mark v-if="part.matched">{{ part.text }}</mark><template v-else>{{ part.text }}</template>
              </span>
            </template>
          </a-table-column>
          <a-table-column title="操作" :width="160" fixed="right">
            <template #cell="{ record }">
              <MangoTableActions :actions="[{ label: '查看记录', loading: openingId === record.record_id, onClick: () => openHit(record) }]" />
            </template>
          </a-table-column>
        </template>
        <template #empty><div class="mango-empty-state">{{ running ? '正在检索，命中后将在此显示' : '本次检索范围内未发现命中记录' }}</div></template>
      </a-table>
      <a-pagination v-if="task && task.count > 20" :current="page" :total="task.count" :page-size="20" :disabled="reading" @change="changePage" />
    </div>
  </BaseSidePanel>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onDeactivated, reactive, ref, watch } from 'vue'
import dayjs from 'dayjs'
import { Message } from '@arco-design/web-vue'
import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
import MangoTableActions from '@/components/table/MangoTableActions.vue'
import { useEnum } from '@/store/modules/get-enum'
import useUserStore from '@/store/modules/user'
import usePermissionStore from '@/store/modules/permission'
import { usePagePolling } from '@/hooks/use-page-polling'
import { reportLoadError, runLoadRequest } from '@/utils/load-error'
import { parseContentSearch, highlightSearchText } from '@/utils/execution-content-search'
import { startContentSearch, getContentSearch, cancelContentSearch } from '@/api/system/execution_content_search'
import type { ContentSearchKind, ContentSearchHit, ContentSearchTask } from '@/api/system/execution_content_search'

const props = defineProps<{ kind: ContentSearchKind; onOpen: (hit: ContentSearchHit) => unknown | Promise<unknown> }>()
const visible = ref(false), starting = ref(false), reading = ref(false), cancelling = ref(false), optionsLoading = ref(false)
const task = ref<ContentSearchTask | null>(null), page = ref(1), openingId = ref<number | null>(null)
const user = useUserStore(), permissions = usePermissionStore(), enums = useEnum()
const draft = reactive<{ product: string | number | Array<string | number> | null; environment: number | undefined; day: string; keyword: string }>({
  product: null, environment: undefined, day: dayjs().format('YYYY-MM-DD'), keyword: '',
})
const running = computed(() => task.value?.status === 'running')
const busy = computed(() => starting.value || running.value || cancelling.value)
const environments = computed(() => enums.environment_type.map(option => ({ value: Number(option.key), label: option.title })))
const statuses = { running: '检索中', completed: '检索完成', partial: '检索不完整', cancelled: '已取消', failed: '检索失败' }
const targetNames: Record<string, string> = { api_case: 'API 用例', api_info: 'API 接口', ui_case: 'UI 用例', ui_page_step: 'UI 步骤', pytest_case: 'Pytest 用例', data_factory: '数据工厂' }
let version = 0
const identity = () => JSON.stringify([user.userId, user.roleId, user.token, permissions.permissionKeys])
const polling = usePagePolling(async context => { if (visible.value && running.value && context.isCurrent()) await refresh(true) })
function disabledDate(value: Date) {
  const day = dayjs(value).startOf('day'), today = dayjs().startOf('day')
  return day.isAfter(today) || day.isBefore(today.subtract(29, 'day'))
}
function close() {
  const id = task.value?.task_id
  if (running.value && id) void runLoadRequest(true, () => cancelContentSearch(props.kind, id)).catch(() => {})
  version++; polling.stop(); visible.value = false; task.value = null
  starting.value = false; reading.value = false; cancelling.value = false; optionsLoading.value = false; openingId.value = null
}
async function open() {
  close(); visible.value = true; page.value = 1
  const current = version
  optionsLoading.value = true
  try { await enums.getEnum() } catch (error) { if (current === version) reportLoadError(error, '被测环境选项加载失败，请重新打开') }
  finally { if (current === version) optionsLoading.value = false }
}
async function start() {
  if (busy.value || !visible.value) return
  const selected = Array.isArray(draft.product) ? draft.product.at(-1) : draft.product
  const product = selected == null || selected === '' ? undefined : Number(selected)
  if ((product !== undefined && (!Number.isInteger(product) || product <= 0)) || !draft.day || disabledDate(dayjs(draft.day).toDate()) || !draft.keyword.trim()) {
    Message.warning('请选择有效的搜索日期并填写关键词；项目产品、被测环境可不选'); return
  }
  const current = ++version, actor = identity()
  starting.value = true; task.value = null; page.value = 1
  try {
    const response = await startContentSearch(props.kind, { project_product_id: product, test_env: draft.environment, day: draft.day, keyword: draft.keyword.trim() })
    if (current !== version || !visible.value || identity() !== actor) {
      if (identity() === actor) void runLoadRequest(true, () => cancelContentSearch(props.kind, response.data.task_id)).catch(() => {})
      return
    }
    task.value = parseContentSearch(response.data); polling.start()
  } catch (error) { if (current === version) reportLoadError(error, '检索启动失败，请重试') }
  finally { if (current === version) starting.value = false }
}
async function refresh(silent: boolean) {
  if (!visible.value || !task.value || reading.value) return
  const current = version, id = task.value.task_id, targetPage = page.value
  if (!silent) reading.value = true
  try {
    const response = await runLoadRequest(silent, () => getContentSearch(props.kind, id, targetPage))
    if (current === version && visible.value && page.value === targetPage && task.value?.task_id === id) {
      const parsed = parseContentSearch(response.data)
      if (parsed.task_id !== id || parsed.page !== targetPage) throw new Error('检索响应与当前任务不一致')
      task.value = parsed
      if (!running.value) polling.stop()
    }
  } catch (error) { if (current === version) reportLoadError(error, '检索结果读取失败，请稍后重试', silent) }
  finally { if (current === version && !silent) reading.value = false }
}
async function cancel() {
  if (!task.value || cancelling.value) return
  const current = version
  cancelling.value = true
  try { await cancelContentSearch(props.kind, task.value.task_id); if (current === version) await refresh(false) }
  catch (error) { if (current === version) reportLoadError(error, '取消失败，请重试') }
  finally { if (current === version) cancelling.value = false }
}
function changePage(value: number) { page.value = value; void refresh(false) }
async function openHit(hit: ContentSearchHit) {
  if (openingId.value !== null) return
  const current = version
  openingId.value = hit.record_id
  try { await props.onOpen(hit) } catch (error) { if (current === version) reportLoadError(error, '执行记录加载失败，请重试') }
  finally { if (current === version) openingId.value = null }
}
function highlight(text: string) {
  return highlightSearchText(text, task.value?.query.keyword || '')
}
watch(draft, () => { if (!busy.value) { version++; task.value = null; page.value = 1; polling.stop() } })
watch(visible, value => { if (!value) close() })
watch(identity, () => { version++; polling.stop(); visible.value = false; task.value = null; starting.value = false; reading.value = false; cancelling.value = false }, { flush: 'sync' })
onBeforeUnmount(close)
onDeactivated(close)
defineExpose({ open, close })
</script>

<style scoped>
.mango-content-search { display: flex; flex-direction: column; gap: var(--m-page-gap); min-width: 0; }
.mango-content-search-form { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 var(--m-page-gap); }
.mango-content-search-form :deep(.arco-picker) { width: 100%; }
.mango-content-search-note, .mango-content-search small { color: var(--m-muted); font-size: 12px; }
.mango-content-search-summary { display: flex; flex-wrap: wrap; align-items: center; gap: var(--m-page-gap); padding: 10px; background: var(--m-surface-soft); }
.mango-content-search-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mango-content-search-path { color: var(--m-muted); overflow-wrap: anywhere; }
.mango-content-search mark { background: var(--m-primary-soft); color: var(--m-primary); }
@media (max-width: 760px) { .mango-content-search-form { grid-template-columns: minmax(0, 1fr); } }
</style>
