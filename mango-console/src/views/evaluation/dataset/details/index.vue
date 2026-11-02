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
              @click="createVersion"
              >新建版本</a-button
            >
          </div>
          <MangoPanelSpin :loading="versionLoading" class="mango-dataset-version-loading">
            <div class="mango-dataset-version-list mango-native-scrollbar" @scroll.passive="onVersionScroll">
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
                  ><strong :title="`V${record.version_no} · ${record.version_label || '未命名版本'}`"
                    >V{{ record.version_no }} · {{ record.version_label || '未命名版本' }}</strong
                  ><a-tag size="small" :color="statusColor(record.status)">{{
                    statusTitle(record.status)
                  }}</a-tag></div
                >
                <div class="mango-muted-text mango-dataset-version-meta"
                  ><span>{{ record.item_count ?? 0 }} 条数据</span><time v-if="record.published_at" class="mango-dataset-version-date" :datetime="record.published_at" :title="record.published_at">{{ formatEvaluationDate(record.published_at) }}</time></div
                >
              </article>
              <div v-if="!versionLoading && !versions.length" class="mango-empty-state"
                >暂无数据集版本</div
              >
              <div v-if="versionLoadingMore || versionLoadError" class="mango-dataset-version-load-state" role="status" aria-live="polite">
                <span v-if="versionLoadingMore">正在加载更多版本…</span>
                <a-button v-else-if="versionLoadError" size="small" @click="retryVersions">加载失败，点击重试</a-button>
              </div>
            </div>
          </MangoPanelSpin>
        </section>
        <section class="mango-dataset-items" aria-label="版本数据条目">
          <div class="mango-section-title mango-dataset-items-header">
            <div
              ><div class="mango-dataset-items-title"><h2>{{ activeVersion ? `V${activeVersion.version_no} 数据条目` : '数据条目' }}</h2><a-tag v-if="activeVersion" size="small" :color="statusColor(activeVersion.status)">{{ statusTitle(activeVersion.status) }}</a-tag></div
              ></div
            >
            <a-space v-if="activeVersion" class="mango-dataset-item-actions" wrap>
              <a-button  size="small" @click="configDrawer?.open(activeVersion, items[0]?.input_data)">数据集配置</a-button>
              <a-button
                v-if="activeVersion.status === 'draft'"

                size="small"
                type="primary"
                @click="openItem()"
                >新增数据条目</a-button
              >
              <a-button v-if="activeVersion.status === 'draft'"  size="small" :loading="publishingVersionId === activeVersion.id" :disabled="publishingVersionId !== undefined || publishConfirmationOpen" @click="publishVersion(activeVersion)">发布</a-button>
              <a-button  size="small" :loading="versionCreating" @click="cloneVersion(activeVersion)">复制新版本</a-button>
              <a-button v-if="activeVersion.status === 'draft'"  size="small" status="danger" :loading="deletingVersionId === activeVersion.id" :disabled="deletingVersionId !== undefined" @click="removeVersion(activeVersion)">删除版本</a-button>
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
              :scroll="{ x: 1280, y: '100%' }"
              size="small"
              row-key="id"
            >
              <template #columns
                ><a-table-column v-for="column in itemColumns" :key="column.key" v-bind="column">
                  <template #cell="{ record }">
                    <span v-if="column.key === 'input_data' || column.key === 'expected_output'">{{
                      dataSummary(record[column.key])
                    }}</span>
                    <a-tooltip v-else-if="column.key === 'tags' && record.tags?.length" :content="record.tags.join('、')">
                      <span class="mango-evaluation-item-tags"><a-tag v-for="tag in record.tags.slice(0, 2)" :key="tag" size="small">{{ tag }}</a-tag><a-tag v-if="record.tags.length > 2" class="mango-evaluation-item-tags__more" size="small">+{{ record.tags.length - 2 }}</a-tag></span>
                    </a-tooltip>
                    <span v-else-if="column.key === 'tags'">-</span>
                    <a-tag v-else-if="column.key === 'priority'" size="small" :color="getEnumTagColor(itemPriorityOptions, record.priority, enumStore.colors)">{{ record.priority || '—' }}</a-tag>
                    <a-switch
                      v-else-if="column.key === 'enabled'"
                      size="small"
                      :model-value="record.enabled"
                      disabled
                    />
                    <template v-else-if="column.key === 'actions'"
                      ><MangoTableActions
                        :actions="activeVersion.status === 'draft'
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
            onClick: () => removeItem(record),
        },
    ]
    : [
        {
            label: '详情',
            onClick: () => viewItem(record),
        },
    ]"
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

  <BaseSidePanel
    v-model:visible="itemEditorVisible"
    :title="itemForm.id ? '编辑评测数据条目' : '新增评测数据条目'"
    width="50%"
    :mask-closable="!itemSaving"
  >
      <a-form :model="itemForm" layout="horizontal" size="small" :disabled="itemSaving" :inert="itemSaving" class="mango-evaluation-item-form">
        <ItemDataSourceEditor :key="`${itemForm.version_id}-${itemForm.id || 'new'}`" v-model="itemForm.data_source" :version-id="itemForm.version_id" :disabled="itemSaving" class="mango-item-editor-section" />
        <ScenarioEditor v-model="itemForm.scenario" :sequence="itemVersion?.schema_snapshot?.workflow?.sequence || 'independent'" :disabled="itemSaving" class="mango-item-editor-section" />
        <section
          v-for="section in itemDataSections"
          :key="section.key"
          class="mango-item-editor-section"
        >
          <h3 class="mango-item-editor-heading">{{ section.title }}</h3>
          <div class="mango-item-editor-body"><DataFieldsEditor
            :model-value="parseFields(itemForm[section.key])"
            :schema="itemVersion?.schema_snapshot?.[section.schema]"
            :disabled="itemSaving"
            @update:model-value="itemForm[section.key] = JSON.stringify($event)"
          /></div>
        </section>
        <section class="mango-item-editor-section">
        <h3 class="mango-item-editor-heading">评分规则</h3>
        <div class="mango-item-editor-body">
        <div class="mango-evaluation-item-fields">
        <a-form-item label="数据条目权重"
          ><a-input-number v-model="itemForm.weight" :min="0.001" :step="0.1"
        /></a-form-item>
        <a-form-item label="评分模式"
          ><a-select
            v-model="itemForm.grading_config.mode"
            :options="[
              { label: '继承 Case 默认评分', value: 'inherit' },
              { label: '替换默认评分', value: 'replace' },
            ]"
            @change="changeItemGradingMode"
        /></a-form-item>
        </div>
        <MangoPanelSpin v-if="itemForm.grading_config.mode === 'replace'" :loading="catalogLoading" class="mango-evaluation-grader-loading"
          ><GraderEditor
            v-model="itemForm.grading_config.graders"
            :disabled="itemSaving"
            :catalog="graderCatalog"
            title="条目专属评分"
            empty-text="替换模式需要至少一个有效评分项；Case 强制项仍会追加"
        /></MangoPanelSpin>
        </div>
        </section>
        <section class="mango-item-editor-section">
        <h3 class="mango-item-editor-heading">其他设置</h3>
        <div class="mango-item-editor-body">
        <div class="mango-evaluation-item-fields">
        <a-form-item label="标签"><a-input v-model="itemForm.tags_text" placeholder="英文逗号分隔，如：有订单,权限边界" /></a-form-item>
        <a-form-item label="优先级"><a-select v-model="itemForm.priority" :options="itemPriorityOptions.map(({ key, title }) => ({ label: title, value: key }))" /></a-form-item>
        <a-form-item label="启用"
          ><a-switch v-model="itemForm.enabled" size="small"
        /></a-form-item>
        </div>
        </div>
        </section>
      </a-form>
    <template #footer-buttons><a-space><a-button  size="small" type="primary" :loading="itemSaving" @click="saveItem">保存</a-button><a-button size="small" :disabled="itemSaving" @click="itemEditorVisible = false">取消</a-button></a-space></template>
  </BaseSidePanel>
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
        <a-descriptions-item label="启用">{{ documentData.enabled ? '是' : '否' }}</a-descriptions-item>
        <a-descriptions-item label="标签">{{ documentData.tags?.join('、') || '—' }}</a-descriptions-item>
        <a-descriptions-item v-if="documentData.scenario?.group_key" label="会话组">{{ documentData.scenario.group_key }}</a-descriptions-item>
        <a-descriptions-item v-if="documentData.scenario?.group_key" label="组内顺序">{{ documentData.scenario.order || 0 }}</a-descriptions-item>
      </a-descriptions>
      <section v-if="documentData?.data_source?.kind && documentData.data_source.kind !== 'manual'" class="mango-item-detail-section">
        <h3 class="mango-section-title">数据来源</h3>
        <DataFieldsView :data="{ '资源': documentData.data_source.binding?.name, ...(documentData.data_source.kind === 'sql' ? { '变量 Key': documentData.data_source.key || '—', 'SQL 查询': documentData.data_source.query } : {}) }" />
      </section>
      <section v-for="section in visibleDetailSections" :key="section.key" class="mango-item-detail-section">
        <h3 class="mango-section-title">{{ section.title }}</h3>
        <DataFieldsView :data="documentData?.[section.key]" :schema="documentSchema?.[section.schema]" />
      </section>
      <section v-for="(turn, index) in documentData?.scenario?.turns || []" :key="index" class="mango-item-detail-section">
        <h3 class="mango-section-title">第 {{ index + 1 }} 轮{{ turn.name ? ` · ${turn.name}` : '' }}</h3>
        <DataFieldsView :data="{ input_data: turn.input_data, ...(turn.score !== false ? { expected_output: turn.expected_output, context: turn.context } : {}) }" :schema="{ properties: { input_data: { ...documentSchema?.input_schema, title: '输入' }, expected_output: { ...documentSchema?.expected_schema, title: '期望输出' }, context: { ...documentSchema?.context_schema, title: '参考证据' } } }" />
      </section>
      <MangoPanelSpin v-if="documentData?.grading_config?.mode === 'replace'" :loading="catalogLoading">
        <section class="mango-item-detail-section"><h3 class="mango-section-title">条目评分规则</h3><DataFieldsView :data="detailGraders" /></section>
      </MangoPanelSpin>
    </div>
  </BaseSidePanel>
  <DatasetConfigDrawer ref="configDrawer" @saved="workflowSaved" />
</template>

<script setup lang="ts">
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import MangoPanelSpin from '@/components/feedback/MangoPanelSpin.vue'
  import DataFieldsView from '../../components/DataFieldsView.vue'
  import DataFieldsEditor from '../../components/DataFieldsEditor.vue'
  import { dataSummary, formatEvaluationDate } from '../../components/presentation'
  import {
    acknowledgeDatasetQuality,
    createDatasetVersion,
    createEvaluationDatasetItem,
    deleteEvaluationDatasetItem,
    deleteDatasetVersion,
    getDatasetQuality,
    getDatasetVersions,
    getEvaluationDatasetItems,
    publishDatasetVersion,
    updateEvaluationDatasetItem,
  } from '@/api/evaluation'
  import { itemColumns, itemPriorityOptions, itemEditorSections } from '../config'
  import { useEnum } from '@/store/modules/get-enum'
  import { getEnumTagColor } from '@/utils/business-format'
  import type { ModalDialogType } from '@/types/components'
  import usePermissionStore from '@/store/modules/permission'
  import GraderEditor from '../../components/GraderEditor.vue'
  import DatasetConfigDrawer from '../../components/DatasetConfigDrawer.vue'
  import ScenarioEditor from '../../components/ScenarioEditor.vue'
  import ItemDataSourceEditor from '../../components/ItemDataSourceEditor.vue'
  import { itemDataSourceError } from '../workflow'
  import { useEvaluationEnums } from '../../components/useEvaluationEnums'
  import { getDatasetGraderCatalog } from '@/api/evaluation'
  const permissions = usePermissionStore(),
    graderCatalog = ref<any[]>([]),
    catalogLoading = ref(false)
  const configDrawer = ref<InstanceType<typeof DatasetConfigDrawer>>()
  function workflowSaved(record: any) { if (activeVersion.value?.id === record.id) activeVersion.value = record; const index = versions.value.findIndex(item => item.id === record.id); if (index >= 0) versions.value[index] = record }
  const versionCreating = ref(false)
  const cloneConfirmationOpen = ref(false)
  const deletingVersionId = ref<number>()
  function removeVersion(record: any) {
    if (record.status !== 'draft' || deletingVersionId.value !== undefined)
    return;
    const id = record.id, dataset = datasetId.value
    Modal.warning({
      title: '删除草稿版本',
      content: `确认删除 V${record.version_no}？该版本的数据条目和流程配置也将删除。`,
      hideCancel: false,
      onOk: async () => {
        if (deletingVersionId.value !== undefined) return
        deletingVersionId.value = id
        try {
          await deleteDatasetVersion(id)
          if (datasetId.value !== dataset) return
          versions.value = versions.value.filter(version => version.id !== id)
          versionPagination.pageCount = Math.max(0, versionPagination.pageCount - 1)
          await loadVersions()
          if (activeVersion.value?.id === id) {
            activeVersion.value = undefined
            items.value = []
            itemPagination.pageCount = 0
            if (versions.value.length) await selectVersion(versions.value[0])
          }
          Message.success('草稿版本已删除')
        } finally { deletingVersionId.value = undefined }
      },
    })
  }
  const { title: enumTitle, color: statusColor } = useEvaluationEnums()
  const enumStore = useEnum()
  const documentVisible = ref(false),
    documentTitle = ref(''),
    documentData = ref<any>(),
    documentSchema = ref<any>()
  const detailSections = [{ key: 'input_data', title: '输入', schema: 'input_schema' }, { key: 'expected_output', title: '期望输出', schema: 'expected_schema' }, { key: 'context', title: '评分依据', schema: 'context_schema' }]
  const visibleDetailSections = computed(() => detailSections.filter(section => ['input_data', 'expected_output'].includes(section.key) || Object.keys(documentData.value?.[section.key] || {}).length))
  const detailGraders = computed(() => (documentData.value?.grading_config?.graders || []).map((binding: any) => {
    const grader = graderCatalog.value.find(item => item.grader_key === binding.grader_key && item.grader_version === binding.grader_version)
    return { '评分器': `${grader?.name || binding.grader_key} V${binding.grader_version || 1}`, '通过阈值': binding.threshold ?? '未设置', '权重': binding.weight ?? 1, '硬门禁': Boolean(binding.hard_gate), '启用': binding.enabled !== false, ...(Object.keys(binding.parameters || {}).length ? { '参数': binding.parameters } : {}) }
  }))
  function viewItem(record: any) {

    documentTitle.value = `V${activeVersion.value?.version_no} · ${record.id}`
    documentData.value = JSON.parse(
      JSON.stringify({ version: activeVersion.value?.version_no, ...record })
    )
    documentSchema.value = JSON.parse(JSON.stringify(activeVersion.value?.schema_snapshot || {}))
    if (record.grading_config?.mode === 'replace') void loadCatalog().catch(() => {})
    documentVisible.value = true
  }
  let versionRequest = 0,
    itemRequest = 0
  const versionPagination = reactive({ page: 1, pageSize: 20, pageCount: 0 })
  const versionLoadingMore = ref(false),
    versionLoadError = ref(false),
    versionRetryAppend = ref(false)
  const hasMoreVersions = computed(() => versionPagination.page * versionPagination.pageSize < versionPagination.pageCount)
  const itemPagination = reactive({
    page: 1,
    pageSize: 20,
    pageCount: 0,
    pageSizes: [20, 50, 100],
    showSizePicker: true,
    onChange: () => activeVersion.value && selectVersion(activeVersion.value, false),
  })

  const versions = ref<any[]>([]),
    items = ref<any[]>([])
  const versionLoading = ref(false),
    itemLoading = ref(false)
  const itemEditorVisible = ref(false), itemSaving = ref(false), itemVersion = ref<any>()
  const qualityDialogRef = ref<ModalDialogType | null>(null)
  const qualityReport = ref<any>({})
  const publishingVersionId = ref<number>(), publishConfirmationOpen = ref(false)
  const activeDataset = ref<any>(),
    activeVersion = ref<any>()
  const itemForm = reactive<any>({
    grading_config: { schema_version: 1, mode: 'inherit', graders: [] },
    input_text: '{\n  "question": "我的订单有哪些？"\n}',
    expected_text: '{\n  "contract_ids": []\n}',
    context_text: '{}',
    tags_text: '',
  })
  const statusTitle = (value: string) =>
    enumTitle(
      ['published', 'deprecated'].includes(value)
        ? 'evaluation_version_status'
        : 'evaluation_case_status',
      value
    )
  const itemDataSections = itemEditorSections
  const parseFields = (text?: string) => {
    try {
      return JSON.parse(text || '{}')
    } catch {
      return {}
    }
  }
  function onVersionScroll(event: Event) {
    const container = event.currentTarget as HTMLElement
    if (container.scrollTop + container.clientHeight >= container.scrollHeight - 1 && !versionLoadError.value)
      loadMoreVersions()
  }
  function loadMoreVersions() {
    if (!hasMoreVersions.value || versionLoading.value || versionLoadingMore.value) return
    return fetchVersions(true)
  }
  function retryVersions() {
    return versionRetryAppend.value ? loadMoreVersions() : loadVersions()
  }
  function loadVersions() {
    return fetchVersions(false)
  }
  async function fetchVersions(append: boolean) {
    if (!activeDataset.value) return
    const request = ++versionRequest
    const page = append ? versionPagination.page + 1 : 1
    versionLoading.value = !append
    versionLoadingMore.value = append
    versionLoadError.value = false
    try {
      const res: any = await getDatasetVersions(activeDataset.value.id, {
        page,
        pageSize: versionPagination.pageSize,
      })
      if (request === versionRequest) {
        const incoming = res.data?.items || []
        const existingIds = new Set(versions.value.map(record => record.id))
        versions.value = append ? [...versions.value, ...incoming.filter(record => !existingIds.has(record.id))] : incoming
        versionPagination.page = page
        versionPagination.pageCount = res.data?.count || 0
      }
    } catch {
      if (request === versionRequest) {
        versionLoadError.value = true
        versionRetryAppend.value = append
      }
    } finally {
      if (request === versionRequest) {
        versionLoading.value = false
        versionLoadingMore.value = false
      }
    }
  }
  async function createVersion() {
    if (!activeDataset.value) return
    if (versionCreating.value) return
    versionCreating.value = true
    try {
      await createDatasetVersion(activeDataset.value.id, {
        version_label: '草稿',
        schema_snapshot: {
          schema_version: 1,
          input_schema: { type: 'object' },
          expected_schema: { type: 'object' },
          context_schema: { type: 'object' },
        },
      })
      await loadVersions()
    } finally {
      versionCreating.value = false
    }
  }
  function cloneVersion(record: any) {
    if (!activeDataset.value || !record || versionCreating.value || cloneConfirmationOpen.value)
    return;
    const dataset = activeDataset.value.id, source = record.id, version = record.version_no
    cloneConfirmationOpen.value = true
    Modal.confirm({
      title: '复制新版本',
      content: `确认基于 V${version} 复制数据条目和配置，创建新的草稿版本？`,
      okText: '确认复制',
      cancelText: '取消',
      onBeforeOk: async () => {
        if (versionCreating.value || datasetId.value !== dataset)
    return false;
        versionCreating.value = true
        try {
          await createDatasetVersion(dataset, { source_version_id: source })
          if (datasetId.value === dataset) await loadVersions()
          Message.success(`已基于 V${version} 复制数据条目和字段配置`)
          return true
        } catch {
          return false
        } finally {
          versionCreating.value = false
        }
      },
      onClose: () => { cloneConfirmationOpen.value = false },
    })
  }

  async function selectVersion(record: any, reset = true) {
    if (reset) itemPagination.page = 1
    activeVersion.value = record
    const request = ++itemRequest
    itemLoading.value = true
    try {
      const res: any = await getEvaluationDatasetItems(record.id, {
        page: itemPagination.page,
        pageSize: itemPagination.pageSize,
      })
      if (request === itemRequest) {
        items.value = res.data?.items || []
        itemPagination.pageCount = res.data?.count || 0
      }
    } finally {
      if (request === itemRequest) itemLoading.value = false
    }
  }
  async function publishVersion(record: any) {
    if (publishingVersionId.value !== undefined || publishConfirmationOpen.value || record.status !== 'draft')
    return;
    publishingVersionId.value = record.id
    try {

      const res: any = await getDatasetQuality(record.id)
      const report = res.data || {}
      if ((report.errors || []).length) {
        qualityReport.value = report
        qualityDialogRef.value?.show()
        return
      }
      if ((report.warnings || []).length && !report.warning_acknowledged) {
        publishConfirmationOpen.value = true
        Modal.warning({
          title: '发布前提醒',
          content: report.warnings.map((item: any) => `${item.message}${item.groups?.length ? `（条目 ID：${item.groups.map((group: number[]) => group.join('、')).join('；')}）` : item.count ? `（${item.count} 条）` : ''}`).join('；') + '。是否继续发布？',
          hideCancel: false,
          onBeforeOk: async () => {
            if (publishingVersionId.value !== undefined)
    return false;
            publishingVersionId.value = record.id
            try {
              await acknowledgeDatasetQuality(record.id)
              await doPublish(record)
              return true
            } finally { publishingVersionId.value = undefined }
          },
          onClose: () => { publishConfirmationOpen.value = false },
        })
        return
      }
      await doPublish(record)
    } finally { publishingVersionId.value = undefined }
  }
  async function doPublish(record: any) {
    await publishDatasetVersion(record.id)
    await loadVersions()
    if (activeVersion.value?.id === record.id)
      activeVersion.value = { ...activeVersion.value, status: 'published' }
  }
  function openItem(record?: any) {
    if (itemSaving.value || activeVersion.value?.status !== 'draft')
    return;
    itemVersion.value = JSON.parse(JSON.stringify(activeVersion.value))
    itemForm.version_id = activeVersion.value?.id
    Object.assign(
      itemForm,
      record
        ? {
            id: record.id,
            scenario: JSON.parse(JSON.stringify(record.scenario || { group_key: '', order: 0, turns: [] })),
            grading_config: JSON.parse(
              JSON.stringify(
                record.grading_config || { schema_version: 1, mode: 'inherit', graders: [] }
              )
            ),
            data_source: JSON.parse(JSON.stringify(record.data_source || { kind: 'manual' })),
            input_text: JSON.stringify(record.input_data ?? {}, null, 2),
            expected_text: JSON.stringify(record.expected_output || {}, null, 2),
            context_text: JSON.stringify(record.context || {}, null, 2),
            tags_text: (record.tags || []).join(','),
            priority: record.priority,
            weight: record.weight,
            enabled: record.enabled,
          }
        : {
            id: undefined,
            scenario: { group_key: '', order: 0, turns: [] },
            grading_config: { schema_version: 1, mode: 'inherit', graders: [] },
            data_source: { kind: 'manual' },
            input_text: '{}',
            expected_text: '{}',
            context_text: '{}',
            tags_text: '',
            priority: 'P1',
            weight: 1,
            enabled: true,
          }
    )
    itemEditorVisible.value = true
    if (itemForm.grading_config.mode === 'replace') void loadCatalog().catch(() => {})
  }
  function changeItemGradingMode() {
    itemForm.grading_config.graders = []
    if (itemForm.grading_config.mode === 'replace') void loadCatalog().catch(() => {})
  }
  async function saveItem() {
    if (itemSaving.value || !itemEditorVisible.value)
    return;
    itemSaving.value = true
    try {
      const sourceError = itemDataSourceError(itemForm.data_source)
      if (sourceError) { Message.warning(sourceError); return }
      if (!itemForm.version_id) return
      const payload = {
        id: itemForm.id,
        input_data: JSON.parse(itemForm.input_text),
        expected_output: JSON.parse(itemForm.expected_text),
        context: JSON.parse(itemForm.context_text || '{}'),
        tags: itemForm.tags_text
          .split(',')
          .map((item: string) => item.trim())
          .filter(Boolean),
        priority: itemForm.priority || 'P1',
        weight: itemForm.weight || 1,
        enabled: itemForm.enabled,
        grading_config: JSON.parse(JSON.stringify(itemForm.grading_config)),
        scenario: JSON.parse(JSON.stringify(itemForm.scenario || {})),
        data_source: JSON.parse(JSON.stringify(itemForm.data_source || { kind: 'manual' })),
      }
      itemForm.id
        ? await updateEvaluationDatasetItem(payload)
        : await createEvaluationDatasetItem(itemForm.version_id, payload)
      itemEditorVisible.value = false
      if (activeVersion.value?.id === itemForm.version_id) await selectVersion(activeVersion.value)
    } catch (error) {
      if (error instanceof SyntaxError) Message.error('数据条目 JSON 格式不正确')
    } finally {
      itemSaving.value = false
    }
  }
  function removeItem(record: any) {
    Modal.warning({
      title: '删除评测数据条目',
      content: `确认删除“${record.id}”吗？`,
      hideCancel: false,
      onOk: async () => {
        await deleteEvaluationDatasetItem(record.id)
        await selectVersion(activeVersion.value)
      },
    })
  }
  async function loadCatalog() {
    if (graderCatalog.value.length || catalogLoading.value) return
    catalogLoading.value = true
    try {
      const response: any = await getDatasetGraderCatalog()
      graderCatalog.value = Array.isArray(response.data)
        ? response.data
        : response.data?.items || []
    } finally {
      catalogLoading.value = false
    }
  }
  const route = useRoute(),
    router = useRouter()
  const datasetId = computed(() => Number(route.query.id))
  async function loadPage() {
    itemEditorVisible.value = false
    const id = datasetId.value
    versionRequest += 1
    itemRequest += 1
    activeDataset.value = undefined
    activeVersion.value = undefined
    versions.value = []
    items.value = []
    versionLoading.value = false
    versionLoadingMore.value = false
    versionLoadError.value = false
    versionPagination.pageCount = 0
    itemLoading.value = false
    versionPagination.page = 1
    if (!Number.isInteger(id) || id <= 0)
    return;
    activeDataset.value = { id, name: typeof route.query.name === 'string' ? route.query.name : '' }
    await loadVersions()
    if (activeDataset.value?.id === id && versions.value.length)
      await selectVersion(versions.value[0])
  }
  watch(() => route.query.id, loadPage, { immediate: true })
  onBeforeUnmount(() => {
    versionRequest += 1
    itemRequest += 1
    activeDataset.value = undefined
  })
</script>

<style scoped lang="less">
  .mango-evaluation-item-tags { display: inline-flex; align-items: center; gap: var(--m-space-xs); max-width: 100%; min-width: 0; vertical-align: middle; }
  .mango-evaluation-item-tags :deep(.arco-tag) { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .mango-evaluation-item-tags__more { flex-shrink: 0; }
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
  .mango-dataset-items-header > div { min-width: 0; }
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
  .mango-dataset-version-card:hover { background: var(--m-surface-soft); }
  .mango-dataset-version-card--active {
    background: var(--m-primary-soft);
  }
  .mango-dataset-version-card--active:hover { background: var(--m-primary-soft); }
  .mango-dataset-version-card--active strong { color: var(--m-primary); }
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
  .mango-dataset-version-heading :deep(.arco-tag) { flex-shrink: 0; }
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
  .mango-dataset-items > :deep(.mango-table-mango-footer-container) { flex-shrink: 0; }

  .mango-evaluation-drawer {
    display: flex;
    flex-direction: column;
    gap: var(--m-page-gap);
    min-width: 0;
  }
  .mango-item-detail-section > h3 { margin: 0 0 var(--m-space-sm); font-size: var(--m-font-body); }
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
  .mango-evaluation-item-form { container-type: inline-size; display: flex; flex-direction: column; gap: 12px; min-width: 0; }
  .mango-evaluation-item-form :deep(.arco-form-item-label-col) { flex: 0 0 112px; max-width: 112px; }
  .mango-evaluation-item-form :deep(.arco-form-item-wrapper-col) { flex: 1; min-width: 0; max-width: none; }
  .mango-evaluation-item-form :deep(.arco-form-item) { margin-bottom: 12px; }
  .mango-item-editor-section { min-width: 0; }
  .mango-item-editor-body { padding-inline-start: 16px; min-width: 0; }
  .mango-item-editor-section + .mango-item-editor-section { padding-top: 12px; border-top: 1px solid var(--m-border); }
  .mango-item-editor-heading, .mango-evaluation-item-form :deep(.mango-item-source > h3) { margin: 0 0 8px; font-size: 15px; font-weight: 600; line-height: 24px; color: var(--m-text); }
  .mango-item-editor-subheading { margin: var(--m-page-gap) 0; font-size: 13px; font-weight: 500; color: var(--m-text-2); }
  .mango-evaluation-item-fields {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    column-gap: var(--m-page-gap);
  }
  .mango-evaluation-item-fields :deep(.arco-input-number) { width: 100%; }
  .mango-evaluation-grader-loading { width: 100%; margin-bottom: var(--m-page-gap); }
  @container (max-width: 600px) {
    .mango-evaluation-item-fields { grid-template-columns: minmax(0, 1fr); }
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
