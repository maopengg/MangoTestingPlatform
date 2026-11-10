<template>
  <TableBody plain class="mango-detail-workbench-page mango-dataset-detail-page">
    <template #header>
      <div class="mango-detail-toolbar">
        <div class="mango-detail-heading"
          ><div class="mango-detail-title"
            >评测数据集 / {{ datasetId || '-' }} / {{ activeDataset?.name || '-' }}</div
          ></div
        >
        <a-button
          size="small"
          class="mango-back-button"
          @click="router.push('/evaluation/dataset/index')"
          >返回数据集</a-button
        >
      </div>
    </template>
    <template #default>
      <div v-if="!activeDataset" class="mango-empty-state">请选择有效的数据集。</div>
      <div v-else class="mango-dataset-workbench">
        <section class="mango-dataset-master" aria-label="数据集版本">
          <div class="mango-section-title mango-dataset-master-header">
            <h2>数据集版本</h2>
            <a-button
              size="small"
              type="primary"
              :loading="versionCreating"
              :disabled="versionBusy || confirmationOpen"
              @click="createVersion"
              >新建版本</a-button
            >
          </div>
          <MangoPanelSpin :loading="versionLoading" class="mango-dataset-version-loading">
            <div
              class="mango-dataset-version-list mango-native-scrollbar"
              @scroll.passive="onVersionScroll"
            >
              <article
                v-for="record in versions"
                :key="record.id"
                class="mango-dataset-version-card"
                :class="{ 'mango-dataset-version-card--active': activeVersion?.id === record.id }"
                role="button"
                tabindex="0"
                :aria-pressed="activeVersion?.id === record.id"
                @click="selectVersion(record)"
                @keydown.enter.self="selectVersion(record)"
                @keydown.space.self.prevent="selectVersion(record)"
              >
                <div class="mango-dataset-version-heading"
                  ><strong
                    :title="`V${record.version_no} · ${record.version_label || '未命名版本'}`"
                    >V{{ record.version_no }} · {{ record.version_label || '未命名版本' }}</strong
                  ><a-tag size="small" :color="statusColor(record.status)">{{
                    statusTitle(record.status)
                  }}</a-tag></div
                >
                <div class="mango-muted-text mango-dataset-version-meta"
                  ><span>{{ record.item_count ?? 0 }} 条数据</span
                  ><time
                    v-if="record.published_at"
                    class="mango-dataset-version-date"
                    :datetime="record.published_at"
                    :title="record.published_at"
                    >{{ formatEvaluationDate(record.published_at) }}</time
                  ></div
                >
              </article>
              <div v-if="!versionLoading && !versions.length" class="mango-empty-state"
                >暂无数据集版本</div
              >
              <template v-if="versionLoadingMore || versionLoadError"><a-button  size="small" @click="retryVersions">重新加载</a-button></template>
            </div>
          </MangoPanelSpin>
        </section>
        <section class="mango-dataset-items" aria-label="版本数据条目">
          <div class="mango-section-title mango-dataset-items-header">
            <div
              ><div class="mango-dataset-items-title"
                ><h2>{{ activeVersion ? `V${activeVersion.version_no} 数据条目` : '数据条目' }}</h2
                ><a-tag
                  v-if="activeVersion"
                  size="small"
                  :color="statusColor(activeVersion.status)"
                  >{{ statusTitle(activeVersion.status) }}</a-tag
                ></div
              ></div
            >
            <a-space v-if="activeVersion" class="mango-dataset-item-actions" wrap>
              <a-button
                size="small"
                @click="configDrawer?.open(activeVersion, items[0]?.input_data)"
                >数据集配置</a-button
              >
              <a-button
                v-if="activeVersion.status === 'draft'"
                size="small"
                type="primary"
                @click="openItem()"
                >新增数据条目</a-button
              >
              <a-button
                v-if="activeVersion.status === 'draft'"
                size="small"
                :loading="publishingVersionId === activeVersion.id"
                :disabled="versionBusy || confirmationOpen"
                @click="publishVersion(activeVersion)"
                >发布</a-button
              >
              <a-button
                size="small"
                :loading="versionCreating"
                :disabled="versionBusy || confirmationOpen"
                @click="cloneVersion(activeVersion)"
                >复制新版本</a-button
              >
              <a-button
                v-if="activeVersion.status === 'draft'"
                size="small"
                status="danger"
                :loading="deletingVersionId === activeVersion.id"
                :disabled="versionBusy || confirmationOpen"
                @click="removeVersion(activeVersion)"
                >删除版本</a-button
              >
            </a-space>
          </div>
          <template v-if="activeVersion">
            <a-table
              class="mango-native-scroll-table"
              :columns="itemColumns"
              :data="items"
              :loading="itemLoading"
              :pagination="false"
              :bordered="false"
              :scroll="{ x: ITEM_SCROLL_X, y: '100%' }"
              size="small"
              row-key="id"
            >
              <template #columns
                ><a-table-column v-for="column in itemColumns" :key="column.key" v-bind="column">
                  <template #cell="{ record }">
                    <span v-if="column.key === 'input_data' || column.key === 'expected_output'">{{
                      dataSummary(record[column.key])
                    }}</span>
                    <a-tooltip
                      v-else-if="column.key === 'tags' && record.tags?.length"
                      :content="record.tags.join('、')"
                    >
                      <span class="mango-evaluation-item-tags"
                        ><a-tag v-for="tag in record.tags.slice(0, 2)" :key="tag" size="small">{{
                          tag
                        }}</a-tag
                        ><a-tag
                          v-if="record.tags.length > 2"
                          class="mango-evaluation-item-tags__more"
                          size="small"
                          >+{{ record.tags.length - 2 }}</a-tag
                        ></span
                      >
                    </a-tooltip>
                    <span v-else-if="column.key === 'tags'">-</span>
                    <a-tag
                      v-else-if="column.key === 'priority'"
                      size="small"
                      :color="
                        getEnumTagColor(itemPriorityOptions, record.priority, enumStore.colors)
                      "
                      >{{ record.priority || '—' }}</a-tag
                    >
                    <a-switch
                      v-else-if="column.key === 'enabled'"
                      :model-value="record.enabled"
                      disabled
                    />
                    <template v-else-if="column.key === 'actions'"
                      ><MangoTableActions
                        :actions="
                          activeVersion.status === 'draft'
                            ? [
                                {
                                  label: '详情',
                                  onClick: () => viewItem(record),
                                },
                                {
                                  label: '编辑',
                                  onClick: () => openItem(record),
                                },
                                {
                                  label: '删除',
                                  danger: true,
                                  loading: deletingItems.has(record.id),
                                  disabled: versionBusy || confirmationOpen,
                                  onClick: () => removeItem(record),
                                },
                              ]
                            : [
                                {
                                  label: '详情',
                                  onClick: () => viewItem(record),
                                },
                              ]
                        "
                    /></template>
                    <span v-else>{{ record[column.dataIndex as string] ?? '-' }}</span>
                  </template>
                </a-table-column></template
              >
            </a-table>
            <TableFooter :pagination="itemPagination" />
          </template>
          <div v-else class="mango-empty-state">请先选择左侧版本</div>
        </section>
      </div>
    </template>
  </TableBody>

  <DatasetItemEditor
    ref="itemEditor"
    :context-key="contextKey"
    :grader-catalog="graderCatalog"
    :catalog-loading="catalogLoading"
    :catalog-error="catalogError"
    @load-catalog="loadCatalog"
    @saved="itemSaved"
  />
  <ModalDialog ref="qualityDialogRef" title="发布检查未通过" width="760px" :show-footer="false"
    ><template #content>
      <div class="mango-evaluation-quality"
        ><a-descriptions :column="3" bordered size="small"
          ><a-descriptions-item label="数据条目数">{{
            qualityReport.item_count ?? '-'
          }}</a-descriptions-item
          ><a-descriptions-item label="启用数据条目">{{
            qualityReport.enabled_count ?? '-'
          }}</a-descriptions-item
          ><a-descriptions-item label="缺少真值">{{
            qualityReport.missing_expected_count ?? '-'
          }}</a-descriptions-item></a-descriptions
        ><a-alert
          v-for="item in qualityReport.errors || []"
          :key="`e-${item.key}-${item.item_id || ''}`"
          type="error"
          >{{ item.item_id ? `条目 ID ${item.item_id}：` : '' }}{{ item.message }}</a-alert
        ><a-alert v-for="item in qualityReport.warnings || []" :key="`w-${item.key}`" type="warning"
          >{{ item.message }}<template v-if="item.count">（{{ item.count }}）</template></a-alert
        ><div
          class="mango-empty-state"
          v-if="!(qualityReport.errors || []).length && !(qualityReport.warnings || []).length"
          >未发现数据质量问题</div
        ></div
      ></template
    >
  </ModalDialog>
  <BaseSidePanel
    v-model:visible="documentVisible"
    :title="documentTitle"
    :width="900"
    :show-footer="false"
  >
    <div class="mango-evaluation-drawer">
      <a-descriptions v-if="documentData" :column="2" size="small">
        <a-descriptions-item label="优先级">{{ documentData.priority || '—' }}</a-descriptions-item>
        <a-descriptions-item label="权重">{{ documentData.weight ?? 1 }}</a-descriptions-item>
        <a-descriptions-item label="启用">{{
          documentData.enabled ? '是' : '否'
        }}</a-descriptions-item>
        <a-descriptions-item label="标签">{{
          documentData.tags?.join('、') || '—'
        }}</a-descriptions-item>
        <a-descriptions-item v-if="documentData.scenario?.group_key" label="会话组">{{
          documentData.scenario.group_key
        }}</a-descriptions-item>
        <a-descriptions-item v-if="documentData.scenario?.group_key" label="组内顺序">{{
          documentData.scenario.order || 0
        }}</a-descriptions-item>
      </a-descriptions>
      <section
        v-if="documentData?.data_source?.kind && documentData.data_source.kind !== 'manual'"
        class="mango-item-detail-section"
      >
        <h3 class="mango-section-title">数据来源</h3>
        <DataFieldsView
          :data="{
            资源: documentData.data_source.binding?.name,
            ...(documentData.data_source.kind === 'sql'
              ? {
                  '变量 Key': documentData.data_source.key || '—',
                  'SQL 查询': documentData.data_source.query,
                }
              : {}),
          }"
        />
      </section>
      <section
        v-for="section in visibleDetailSections"
        :key="section.key"
        class="mango-item-detail-section"
      >
        <h3 class="mango-section-title">{{ section.title }}</h3>
        <DataFieldsView
          :data="documentData?.[section.key]"
          :schema="documentSchema?.[section.schema]"
        />
      </section>
      <section
        v-for="(turn, index) in documentData?.scenario?.turns || []"
        :key="index"
        class="mango-item-detail-section"
      >
        <h3 class="mango-section-title"
          >第 {{ index + 1 }} 轮{{ turn.name ? ` · ${turn.name}` : '' }}</h3
        >
        <DataFieldsView
          :data="{
            input_data: turn.input_data,
            ...(turn.score !== false
              ? { expected_output: turn.expected_output, context: turn.context }
              : {}),
          }"
          :schema="{
            properties: {
              input_data: { ...documentSchema?.input_schema, title: '输入' },
              expected_output: { ...documentSchema?.expected_schema, title: '期望输出' },
              context: { ...documentSchema?.context_schema, title: '参考证据' },
            },
          }"
        />
      </section>
      <MangoPanelSpin
        v-if="documentData?.grading_config?.mode === 'replace'"
        :loading="catalogLoading"
      >
        <section class="mango-item-detail-section"
          ><h3 class="mango-section-title">条目评分规则</h3><DataFieldsView :data="detailGraders"
        /></section>
      </MangoPanelSpin>
    </div>
  </BaseSidePanel>
  <DatasetConfigDrawer ref="configDrawer" @saved="workflowSaved" />
</template>

<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { computed, reactive, ref } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import { Message, Modal } from '@arco-design/web-vue'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import MangoPanelSpin from '@/components/feedback/MangoPanelSpin.vue'
  import { cloneLosslessJson } from '@/utils/lossless-json'
  import { useEnum } from '@/store/modules/get-enum'
  import { getEnumTagColor } from '@/utils/business-format'
  import type { ModalDialogType } from '@/types/components'
  import {
    acknowledgeDatasetQuality,
    createDatasetVersion,
    deleteEvaluationDatasetItem,
    deleteDatasetVersion,
    getDatasetQuality,
    getDatasetVersions,
    getEvaluationDatasetItems,
    publishDatasetVersion,
    getDatasetGraderCatalog,
  } from '@/api/evaluation'
  import DataFieldsView from '../../components/DataFieldsView.vue'
  import DatasetConfigDrawer from '../../components/DatasetConfigDrawer.vue'
  import DatasetItemEditor from './components/DatasetItemEditor.vue'
  import { dataSummary, formatEvaluationDate } from '../../components/presentation'
  import { useEvaluationEnums } from '../../components/useEvaluationEnums'
  import { useEvaluationScope } from '../../composables/useEvaluationScope'
  import type { GraderCatalogEntry } from '../../types'
  import type {
    DatasetItem,
    DatasetVersion,
    DatasetSchemaSnapshot,
    DatasetQualityReport,
  } from '../types'
  import { itemColumns, itemPriorityOptions, ITEM_SCROLL_X, detailSections } from './config'

  const route = useRoute(),
    router = useRouter(),
    enumStore = useEnum()
  const { title: enumTitle, color: statusColor } = useEvaluationEnums()
  const datasetId = computed(() => Number(route.query.id))
  const contextKey = ref(0)
  const configDrawer = ref<InstanceType<typeof DatasetConfigDrawer>>()
  const itemEditor = ref<InstanceType<typeof DatasetItemEditor>>()
  const activeDataset = ref<{ id: number; name: string } | null>(null)
  const activeVersion = ref<DatasetVersion | null>(null)
  const versions = ref<DatasetVersion[]>([]),
    items = ref<DatasetItem[]>([])
  const versionLoading = ref(false),
    versionLoadingMore = ref(false),
    versionLoadError = ref(false)
  const itemLoading = ref(false),
    itemLoadError = ref(false)
  const versionPagination = reactive({ page: 1, pageSize: 20, pageCount: 0 })
  const itemPagination = reactive({
    page: 1,
    pageSize: 20,
    pageCount: 0,
    pageSizes: [20, 50, 100],
    showSizePicker: true,
    onChange: () => activeVersion.value && selectVersion(activeVersion.value, false),
  })
  const hasMoreVersions = computed(
    () => versionPagination.page * versionPagination.pageSize < versionPagination.pageCount
  )
  const versionCreating = ref(false),
    deletingVersionId = ref<number>(),
    publishingVersionId = ref<number>()
  const deletingItems = reactive(new Set<number>())
  const confirmationOpen = ref(false)
  let confirmation: { close(): void } | undefined,
    confirmationToken = 0
  let versionRequest = 0,
    itemRequest = 0,
    catalogRequest = 0,
    versionRetryAppend = false
  const versionBusy = computed(
    () =>
      versionCreating.value ||
      deletingVersionId.value !== undefined ||
      publishingVersionId.value !== undefined ||
      deletingItems.size > 0
  )
  const graderCatalog = ref<GraderCatalogEntry[]>([]),
    catalogLoading = ref(false),
    catalogError = ref('')
  const qualityDialogRef = ref<ModalDialogType | null>(null),
    qualityReport = ref<DatasetQualityReport>({})
  const documentVisible = ref(false),
    documentTitle = ref('')
  const documentData = ref<DatasetItem | null>(null),
    documentSchema = ref<DatasetSchemaSnapshot>({})
  const visibleDetailSections = computed(() => {
    const context = documentData.value?.context
    const hasContext = context != null && (typeof context !== 'object' || Object.keys(context).length > 0)
    return detailSections.filter(section => section.key !== 'context' || hasContext)
  })
  const detailGraders = computed(() =>
    (documentData.value?.grading_config?.graders || []).map((binding) => {
      const grader = graderCatalog.value.find(
        (item) =>
          item.grader_key === binding.grader_key && item.grader_version === binding.grader_version
      )
      return {
        评分器: `${grader?.name || binding.grader_key} V${binding.grader_version || 1}`,
        通过阈值: binding.threshold ?? '未设置',
        权重: binding.weight ?? 1,
        硬门禁: Boolean(binding.hard_gate),
        启用: binding.enabled !== false,
        ...(Object.keys(binding.parameters || {}).length ? { 参数: binding.parameters } : {}),
      }
    })
  )
  const statusTitle = (value: string) =>
    enumTitle(
      ['published', 'deprecated'].includes(value)
        ? 'evaluation_version_status'
        : 'evaluation_case_status',
      value
    )

  function reset() {
    ++contextKey.value
    ++versionRequest
    ++itemRequest
    ++catalogRequest
    ++confirmationToken
    confirmation?.close()
    confirmation = undefined
    confirmationOpen.value = false
    itemEditor.value?.close()
    configDrawer.value?.close()
    qualityDialogRef.value?.close()
    activeDataset.value = null
    activeVersion.value = null
    versions.value = []
    items.value = []
    documentVisible.value = false
    documentData.value = null
    documentSchema.value = {}
    qualityReport.value = {}
    graderCatalog.value = []
    catalogError.value = ''
    catalogLoading.value = false
    versionLoading.value = false
    versionLoadingMore.value = false
    versionLoadError.value = false
    itemLoading.value = false
    itemLoadError.value = false
    versionPagination.page = 1
    versionPagination.pageCount = 0
    itemPagination.page = 1
    itemPagination.pageCount = 0
  }
  const scope = useEvaluationScope(
    () => [route.query.id],
    reset,
    () => {
      void loadPage()
    }
  )
  async function loadPage() {
    const id = datasetId.value,
      current = scope.snapshot()
    if (!Number.isSafeInteger(id) || id <= 0 || !scope.isActive()) return
    activeDataset.value = { id, name: typeof route.query.name === 'string' ? route.query.name : '' }
    if (
      (await loadVersions()) &&
      scope.current(current) &&
      versions.value.length &&
      !activeVersion.value
    )
      await selectVersion(versions.value[0])
  }
  function onVersionScroll(event: Event) {
    const container = event.currentTarget as HTMLElement
    if (
      container.scrollTop + container.clientHeight >= container.scrollHeight - 1 &&
      !versionLoadError.value
    )
      void loadMoreVersions()
  }
  function loadMoreVersions() {
    if (!hasMoreVersions.value || versionLoading.value || versionLoadingMore.value) return
    return fetchVersions(true)
  }
  function retryVersions() {
    return versionRetryAppend ? loadMoreVersions() : loadVersions()
  }
  function loadVersions() {
    return fetchVersions(false)
  }
  async function fetchVersions(append: boolean) {
    if (!activeDataset.value || !scope.isActive()) return false
    const request = ++versionRequest,
      current = scope.snapshot(),
      dataset = activeDataset.value.id
    const page = append ? versionPagination.page + 1 : 1
    versionLoading.value = !append
    versionLoadingMore.value = append
    versionLoadError.value = false
    try {
      const response: { data: { items?: DatasetVersion[]; count?: number } } =
        await getDatasetVersions(dataset, { page, pageSize: versionPagination.pageSize })
      if (request !== versionRequest || !scope.current(current)) return false
      const incoming = response.data?.items || [],
        ids = new Set(versions.value.map((item) => item.id))
      versions.value = append
        ? [...versions.value, ...incoming.filter((item) => !ids.has(item.id))]
        : incoming
      versionPagination.page = page
      versionPagination.pageCount = response.data?.count || 0
      const selected = incoming.find((item) => item.id === activeVersion.value?.id)
      if (selected) activeVersion.value = selected
      return true
    } catch (loadFailure0) {
      if (request === versionRequest && scope.current(current)) {
        void (reportLoadError(loadFailure0, "加载失败，请重试", false), versionLoadError.value = true)
        versionRetryAppend = append
      }
      return false
    } finally {
      if (request === versionRequest && scope.current(current)) {
        versionLoading.value = false
        versionLoadingMore.value = false
      }
    }
  }
  async function selectVersion(record: DatasetVersion, resetPage = true) {
    if (!scope.isActive()) return false
    if (activeVersion.value?.id !== record.id) {
      items.value = []
      itemPagination.pageCount = 0
      itemEditor.value?.close()
    }
    if (resetPage) itemPagination.page = 1
    activeVersion.value = record
    const request = ++itemRequest,
      current = scope.snapshot()
    itemLoading.value = true
    itemLoadError.value = false
    try {
      const response: { data: { items?: DatasetItem[]; count?: number } } =
        await getEvaluationDatasetItems(record.id, {
          page: itemPagination.page,
          pageSize: itemPagination.pageSize,
        })
      if (request !== itemRequest || !scope.current(current)) return false
      items.value = response.data?.items || []
      itemPagination.pageCount = response.data?.count || 0
      return true
    } catch (loadFailure1) {
      if (request === itemRequest && scope.current(current)) (reportLoadError(loadFailure1, "加载失败，请重试", false), itemLoadError.value = true)
      return false
    } finally {
      if (request === itemRequest && scope.current(current)) itemLoading.value = false
    }
  }
  function workflowSaved(record: DatasetVersion) {
    if (!scope.isActive()) return
    if (activeVersion.value?.id === record.id) activeVersion.value = record
    const index = versions.value.findIndex((item) => item.id === record.id)
    if (index >= 0) versions.value[index] = record
  }
  function openItem(record?: DatasetItem) {
    if (activeVersion.value && !versionBusy.value && !confirmationOpen.value)
      itemEditor.value?.open(activeVersion.value, record)
  }
  async function itemSaved(versionId: number) {
    if (scope.isActive() && activeVersion.value?.id === versionId)
      await selectVersion(activeVersion.value)
  }
  function viewItem(record: DatasetItem) {
    if (!activeVersion.value || !scope.isActive()) return
    documentTitle.value = `V${activeVersion.value.version_no} · ${record.id}`
    documentData.value = cloneLosslessJson(record)
    documentSchema.value = cloneLosslessJson(activeVersion.value.schema_snapshot || {})
    documentVisible.value = true
    if (record.grading_config?.mode === 'replace') void loadCatalog()
  }
  async function loadCatalog() {
    if (!scope.isActive() || graderCatalog.value.length || catalogLoading.value) return
    const request = ++catalogRequest,
      current = scope.snapshot()
    catalogLoading.value = true
    catalogError.value = ''
    try {
      const response: { data: GraderCatalogEntry[] | { items?: GraderCatalogEntry[] } } =
        await getDatasetGraderCatalog()
      if (request === catalogRequest && scope.current(current))
        graderCatalog.value = Array.isArray(response.data)
          ? response.data
          : response.data?.items || []
    } catch (loadFailure2) {
      if (request === catalogRequest && scope.current(current))
        void (reportLoadError(loadFailure2, "评分器加载失败，请重试", false), catalogError.value = '评分器加载失败，请重试')
    } finally {
      if (request === catalogRequest && scope.current(current)) catalogLoading.value = false
    }
  }
  function confirm(
    title: string,
    content: string,
    submit: (current: number) => Promise<boolean>,
    warning = true
  ) {
    if (confirmationOpen.value || !scope.isActive()) return
    const current = scope.snapshot(),
      token = ++confirmationToken
    confirmationOpen.value = true
    let pending = false, successful = false
    confirmation = (warning ? Modal.warning : Modal.confirm)({
      title,
      content,
      hideCancel: false,
      onBeforeOk: async () => {
        if (pending || successful || token !== confirmationToken || !scope.current(current)) return false
        pending = true
        try {
          successful = await submit(current)
          return successful
        } catch {
          return false
        } finally {
          pending = false
        }
      },
      onClose: () => {
        if (token === confirmationToken) {
          ++confirmationToken
          confirmationOpen.value = false
          confirmation = undefined
        }
      },
    })
  }
  async function createVersion() {
    if (!activeDataset.value || versionBusy.value || confirmationOpen.value || !scope.isActive())
      return false
    const dataset = activeDataset.value.id,
      current = scope.snapshot()
    versionCreating.value = true
    try {
      await createDatasetVersion(dataset, {
        version_label: '草稿',
        schema_snapshot: {
          schema_version: 1,
          input_schema: { type: 'object' },
          expected_schema: { type: 'object' },
          context_schema: { type: 'object' },
        },
      })
      if (!scope.current(current)) return false
      await loadVersions()
      if (scope.current(current) && !activeVersion.value && versions.value.length)
        await selectVersion(versions.value[0])
      return true
    } catch {
      return false
    } finally {
      versionCreating.value = false
    }
  }
  function cloneVersion(record: DatasetVersion) {
    if (!activeDataset.value || versionBusy.value) return
    const dataset = activeDataset.value.id,
      id = record.id,
      version = record.version_no
    confirm(
      '复制新版本',
      `确认基于 V${version} 复制数据条目和配置，创建新的草稿版本？`,
      async (current) => {
        if (versionBusy.value) return false
        versionCreating.value = true
        try {
          await createDatasetVersion(dataset, { source_version_id: id })
          if (!scope.current(current)) return false
          await loadVersions()
          if (scope.current(current)) Message.success(`已基于 V${version} 复制数据条目和字段配置`)
          return true
        } finally {
          versionCreating.value = false
        }
      },
      false
    )
  }
  function removeVersion(record: DatasetVersion) {
    if (record.status !== 'draft' || versionBusy.value) return
    const id = record.id
    confirm(
      '删除草稿版本',
      `确认删除 V${record.version_no}？该版本的数据条目和流程配置也将删除。`,
      async (current) => {
        if (versionBusy.value) return false
        deletingVersionId.value = id
        try {
          await deleteDatasetVersion(id)
          if (!scope.current(current)) return false
          versions.value = versions.value.filter((item) => item.id !== id)
          if (activeVersion.value?.id === id) {
            ++itemRequest
            activeVersion.value = null
            items.value = []
            itemPagination.pageCount = 0
            itemEditor.value?.close()
          }
          await loadVersions()
          if (!scope.current(current)) return true
          if (!activeVersion.value && versions.value.length) await selectVersion(versions.value[0])
          if (scope.current(current)) Message.success('草稿版本已删除')
          return true
        } finally {
          deletingVersionId.value = undefined
        }
      }
    )
  }
  function removeItem(record: DatasetItem) {
    if (!activeVersion.value || activeVersion.value.status !== 'draft' || versionBusy.value) return
    const id = record.id,
      versionId = activeVersion.value.id
    confirm('删除评测数据条目', `确认删除“${id}”吗？`, async (current) => {
      if (versionBusy.value) return false
      deletingItems.add(id)
      try {
        await deleteEvaluationDatasetItem(id)
        if (!scope.current(current)) return false
        if (activeVersion.value?.id === versionId) {
          if (items.value.length === 1 && itemPagination.page > 1) itemPagination.page--
          await selectVersion(activeVersion.value, false)
        }
        return true
      } finally {
        deletingItems.delete(id)
      }
    })
  }
  async function doPublish(record: DatasetVersion, current: number) {
    if (!scope.current(current)) return false
    await publishDatasetVersion(record.id)
    if (!scope.current(current)) return false
    workflowSaved({ ...record, status: 'published' })
    itemEditor.value?.close()
    await loadVersions()
    return true
  }
  async function publishVersion(record: DatasetVersion) {
    if (
      versionBusy.value ||
      confirmationOpen.value ||
      record.status !== 'draft' ||
      !scope.isActive()
    )
      return false
    const snapshot = cloneLosslessJson(record),
      current = scope.snapshot()
    publishingVersionId.value = snapshot.id
    try {
      const response: { data: DatasetQualityReport } = await getDatasetQuality(snapshot.id)
      if (!scope.current(current)) return false
      const report = response.data || {}
      if (report.errors?.length) {
        qualityReport.value = report
        qualityDialogRef.value?.show()
        return false
      }
      if (report.warnings?.length && !report.warning_acknowledged) {
        const content =
          report.warnings
            .map(
              (item) =>
                `${item.message}${
                  item.groups?.length
                    ? `（条目 ID：${item.groups.map((group) => group.join('、')).join('；')}）`
                    : item.count
                    ? `（${item.count} 条）`
                    : ''
                }`
            )
            .join('；') + '。是否继续发布？'
        confirm('发布前提醒', content, async (confirmed) => {
          if (versionBusy.value) return false
          publishingVersionId.value = snapshot.id
          try {
            await acknowledgeDatasetQuality(snapshot.id)
            return await doPublish(snapshot, confirmed)
          } finally {
            publishingVersionId.value = undefined
          }
        })
        return false
      }
      return await doPublish(snapshot, current)
    } catch {
      return false
    } finally {
      publishingVersionId.value = undefined
    }
  }
  scope.start()
</script>

<style scoped lang="less">
  .mango-evaluation-item-tags {
    display: inline-flex;
    align-items: center;
    gap: var(--m-space-xs);
    max-width: 100%;
    min-width: 0;
    vertical-align: middle;
  }
  .mango-evaluation-item-tags :deep(.arco-tag) {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .mango-evaluation-item-tags__more {
    flex-shrink: 0;
  }
  .mango-dataset-detail-page :deep(> .mango-table-body__content) {
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  .mango-dataset-workbench {
    display: grid;
    grid-template-columns: 280px minmax(0, 1fr);
    grid-template-rows: minmax(0, 1fr);
    gap: var(--m-page-gap);
    flex: 1;
    min-width: 0;
    min-height: 0;
    margin-top: var(--m-page-gap);
  }
  .mango-dataset-master,
  .mango-dataset-items {
    display: flex;
    flex-direction: column;
    min-width: 0;
    min-height: 0;
    background: var(--m-surface);
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    overflow: hidden;
  }
  .mango-dataset-master-header,
  .mango-dataset-items-header {
    align-items: center;
    flex-wrap: wrap;
    padding: var(--m-card-padding);
    margin: 0;
    border-bottom: 1px solid var(--m-border);
  }
  .mango-dataset-master-header h2,
  .mango-dataset-items-header h2 {
    font-size: var(--m-font-body);
  }
  .mango-dataset-items-header > div {
    min-width: 0;
  }
  .mango-dataset-items-title {
    display: flex;
    align-items: center;
    gap: var(--m-space-sm);
  }
  .mango-dataset-item-actions {
    justify-content: flex-end;
    margin-left: auto;
  }
  .mango-dataset-version-loading {
    flex: 1;
    min-height: 0;
    width: 100%;
  }
  .mango-dataset-version-loading :deep(> .mango-panel-spin__content) {
    height: 100%;
  }
  .mango-dataset-version-list {
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow: auto;
  }
  .mango-dataset-version-card {
    flex-shrink: 0;
    padding: var(--m-card-padding);
    border-bottom: 1px solid var(--m-border);
    background: var(--m-surface);
    cursor: pointer;
  }
  .mango-dataset-version-card:hover {
    background: var(--m-surface-soft);
  }
  .mango-dataset-version-card--active {
    background: var(--m-primary-soft);
  }
  .mango-dataset-version-card--active:hover {
    background: var(--m-primary-soft);
  }
  .mango-dataset-version-card--active strong {
    color: var(--m-primary);
  }
  .mango-dataset-version-card:focus-visible {
    outline: 2px solid var(--m-primary);
    outline-offset: -2px;
  }
  .mango-dataset-version-heading {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--m-space-sm);
    margin-bottom: var(--m-space-sm);
  }
  .mango-dataset-version-heading strong {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: var(--m-font-body);
  }
  .mango-dataset-version-heading :deep(.arco-tag) {
    flex-shrink: 0;
  }
  .mango-dataset-version-meta {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: var(--m-space-xs) var(--m-page-gap);
    font-size: var(--m-font-caption);
  }
  .mango-dataset-version-date {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: var(--m-font-caption);
  }
  .mango-dataset-version-load-state {
    flex-shrink: 0;
    padding: var(--m-page-gap);
    text-align: center;
    color: var(--m-muted);
    font-size: var(--m-font-caption);
  }
  .mango-dataset-items > :deep(.arco-table) {
    flex: 1;
    min-height: 0;
  }
  .mango-dataset-items > :deep(.mango-table-mango-footer-container) {
    flex-shrink: 0;
  }

  .mango-evaluation-drawer {
    display: flex;
    flex-direction: column;
    gap: var(--m-page-gap);
    min-width: 0;
  }
  .mango-item-detail-section > h3 {
    margin: 0 0 var(--m-space-sm);
    font-size: var(--m-font-body);
  }
  .mango-evaluation-import-input {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: var(--m-page-gap);
    align-items: end;
    margin: var(--m-page-gap) 0;
  }
  .mango-evaluation-quality {
    width: 100%;
    min-height: 160px;
    display: flex;
    flex-direction: column;
    gap: var(--m-page-gap);
    overflow-wrap: anywhere;
  }
  code {
    display: block;
    overflow: hidden;
    color: var(--m-text-2);
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  @container (max-width: 1100px) {
    .mango-dataset-workbench {
      grid-template-columns: 240px minmax(0, 1fr);
    }
  }
</style>
