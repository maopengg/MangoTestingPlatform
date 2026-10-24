<template>
  <TableBody
    ref="tableBody"
    :embedded="embedded"
    :show-embedded-header="embedded"
    :sticky-horizontal-scroll="false"
    :class="[
      'mango-detail-workbench-page',
      { 'mango-ui-element-page--table-only': !liveWorkbenchVisible },
    ]"
  >
    <template #header>
      <div class="mango-detail-toolbar">
        <div class="mango-detail-heading">
          <div class="mango-detail-title">{{ pageElementDetailTitle }}</div>
          <div class="mango-detail-subtitle">维护页面元素定位、操作配置和批量导入数据</div>
        </div>
        <a-space class="mango-detail-actions" wrap>
          <a-button v-permission="'ui.page:debug'"
            v-if="isWebClient"
            size="small"
            :loading="browserOpening"
            @click="openElementPageBrowser" data-testid="qa-views-uitest-page-elements-button-打开浏览器"
          >
            <template #icon><icon-desktop /></template>
            打开浏览器
          </a-button>
          <a-button
            size="small"
            type="primary"
            :loading="liveWorkbenchOpening"
            @click="toggleElementLiveWorkbench"
          >
            <template #icon><icon-desktop /></template>
            {{ liveWorkbenchVisible ? '收起工作台' : '实时画面' }}
          </a-button>
          <VariableReferencePanel />
          <a-button class="mango-back-button" size="small" @click="doResetSearch" data-testid="qa-views-uitest-page-elements-button-返回">返回</a-button>
        </a-space>
      </div>
    </template>
    <template #default>
      <div class="mango-workbench-scroll-x mango-ui-element-workbench-scroll">
        <div class="mango-ui-element-workbench">
          <aside class="mango-ui-element-category-panel">
            <div class="mango-ui-element-category-head">
              <div>
                <h3>元素分类</h3>
                <p>按页面区域筛选元素</p>
              </div>
              <a-tag size="small">{{ elementCategoryCount }}</a-tag>
            </div>
            <a-input-search v-model="categoryKeyword" allow-clear placeholder="搜索分类" data-testid="qa-views-uitest-page-elements-input-search-搜索分类" />
            <div class="mango-ui-element-category-tree">
              <a-tree
                v-model:selected-keys="selectedCategoryKeys"
                :data="categoryTree"
                block-node
                size="small"
                @select="onCategorySelect"
              />
            </div>
          </aside>
          <section class="mango-ui-element-main">
            <div class="mango-ui-element-toolbar">
              <a-space wrap>
                <a-button size="small" @click="batchAddVisible = true" data-testid="qa-views-uitest-page-elements-button-批量增加">批量增加</a-button>
                <a-button v-permission="'ui.page:create'" type="primary" size="small" @click="doAppend" data-testid="qa-views-uitest-page-elements-button-新增">新增</a-button>
                <a-button v-permission="'ui.page:delete'" size="small" status="danger" @click="onDelete(null)" data-testid="qa-views-uitest-page-elements-button-批量删除">批量删除</a-button>
              </a-space>
            </div>
            <StickyHorizontalTable :scroll-x="2160">
              <a-table
                class="mango-ui-element-table mango-native-scroll-table"
                :bordered="false"
                :columns="tableColumns"
                :data="table.dataList"
                :loading="table.tableLoading.value || categoryLoading"
                :pagination="false"
                :row-selection="{ selectedRowKeys, showCheckedAll }"
                :rowKey="rowKey"
                @selection-change="onSelectionChange"
                :scroll="{ x: 2160, y: '100%' }"
              >
                <template #columns>
                  <a-table-column
                    v-for="item of tableColumns"
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
                    <template v-else-if="item.dataIndex === 'category'" #cell="{ record }">
                      <a-tag size="small">{{ record.category || '未分类' }}</a-tag>
                    </template>
                    <template v-else-if="item.dataIndex === 'ai_heal_status'" #cell="{ record }">
                      <a-tag :color="aiHealStatusMeta(record.ai_heal_status).color" size="small">
                        {{ aiHealStatusMeta(record.ai_heal_status).label }}
                      </a-tag>
                    </template>
                    <template
                      v-else-if="item.dataIndex?.startsWith('locator_group_')"
                      #cell="{ record }"
                    >
                      <UiLocatorGroupCell
                        :locator="
                          getLocatorGroup(
                            record,
                            Number(String(item.dataIndex).replace('locator_group_', ''))
                          )
                        "
                        :type-label="
                          getElementExpName(
                            getLocatorGroup(
                              record,
                              Number(String(item.dataIndex).replace('locator_group_', ''))
                            ).exp
                          )
                        "
                        :type-color="
                          enumStore.colors[
                            getLocatorGroup(
                              record,
                              Number(String(item.dataIndex).replace('locator_group_', ''))
                            ).exp
                          ]
                        "
                        :match-count="
                          getLocatorRuntime(
                            record,
                            Number(String(item.dataIndex).replace('locator_group_', ''))
                          ).count
                        "
                        :text-summary="
                          getLocatorRuntime(
                            record,
                            Number(String(item.dataIndex).replace('locator_group_', ''))
                          ).elementText
                        "
                      />
                    </template>
                    <template v-else-if="item.dataIndex === 'expected_event'" #cell="{ record }">
                      <div
                        v-if="record.expected_event?.ope_key"
                        class="mango-ui-element-expected-cell"
                      >
                        <a-tag color="arcoblue" size="small">
                          {{
                            useSelectValue.getSelectLabel(record.expected_event.ope_key) ||
                            record.expected_event.ope_key
                          }}
                        </a-tag>
                        <a-tooltip
                          v-if="expectedEventParamSummary(record.expected_event)"
                          :content="expectedEventParamSummary(record.expected_event)"
                        >
                          <div class="mango-ui-element-expected-cell-input">
                            预期输入 {{ expectedEventParamSummary(record.expected_event) }}
                          </div>
                        </a-tooltip>
                      </div>
                      <span v-else class="mango-ui-muted">-</span>
                    </template>
                    <template v-else-if="item.dataIndex === 'prompt'" #cell="{ record }">
                      <a-tooltip :content="elementDescriptionSummary(record)">
                        <span>{{ elementDescriptionSummary(record) }}</span>
                      </a-tooltip>
                    </template>
                    <template v-else-if="item.dataIndex === 'update_user'" #cell="{ record }">
                      {{ record.update_user?.name || record.update_user?.username || '-' }}
                    </template>
                    <template v-else-if="item.dataIndex === 'actions'" #cell="{ record }">
                      <MangoTableActions
                        :actions="[
                          { permission: 'ui.page:debug',
                            label: '深度检测',
                            loading: elementCheckLoading,
                            onClick: () => onCheck(record, 'deep'),
                          },
                          { permission: 'ui.page:debug',
                            label: 'AI自愈',
                            loading: aiInfoDrawer.loadingKey === String(record.id),
                            onClick: () => onAiInfo(record),
                          },
                          { permission: 'ui.page:edit', label: '编辑', onClick: () => onUpdate(record) },
                          { permission: 'ui.page:delete', label: '删除', danger: true, onClick: () => onDelete(record) },
                        ]"
                      />
                    </template>
                  </a-table-column>
                </template>
              </a-table>
            </StickyHorizontalTable>
            <div class="mango-ui-element-footer">
              <TableFooter :pagination="pagination" />
            </div>
          </section>
        </div>
      </div>
      <section
        v-if="liveWorkbenchVisible"
        ref="liveWorkbenchSectionRef"
        class="mango-ui-element-live-debug-area"
      >
        <UiLiveWorkbenchPanel
          ref="liveWorkbenchRef"
          class="mango-ui-element-live-debug-panel"
          mode="element"
          :page-id="currentPageId"
          :page-url="pageRecord.url"
          :test-env="userStore.selected_environment"
          :category="activeCategoryName"
          :operation-options="activeOperationOptions"
          :page-type="pageRecord.project_product?.ui_client_type"
          :project-product-id="pageRecord.project_product?.id"
          :check-loading="elementCheckLoading"
          :inline-element-result="false"
          @element-check-started="handleWorkbenchElementCheckStarted"
          @element-check-result="handleWorkbenchElementCheckResult"
          @element-check-finished="handleWorkbenchElementCheckFinished"
          @element-saved="handleWorkbenchElementSaved"
        />
      </section>
    </template>
  </TableBody>
  <UiElementEditPanel
    ref="elementEditPanelRef"
    :operation-options="activeOperationOptions"
    checkable
    :check-loading-key="elementCheck.loadingKey"
    :check-loading="elementCheckLoading"
    @saved="handleElementSaved"
    @check="onCheck"
  />
  <a-modal v-model:visible="batchAddVisible" title="批量增加页面元素" width="560px" :footer="false">
    <div class="mango-ui-element-batch-add">
      <section class="mango-ui-element-batch-add__item">
        <div>
          <strong>下载模板</strong>
          <span>先下载标准模板，按模板格式填写页面元素。</span>
        </div>
        <a-button v-permission="'ui.page:download'" size="small" @click="onDownload" data-testid="qa-views-uitest-page-elements-button-下载模板">下载模板</a-button>
      </section>
      <section class="mango-ui-element-batch-add__item">
        <div>
          <strong>上传模板</strong>
          <span>支持上传填写完成的 Excel 模板并批量增加元素。</span>
        </div>
        <a-upload
          accept=".xlsx,.xls"
          :show-file-list="false"
          :auto-upload="false"
          :disabled="batchUploading"
          @before-upload="beforeUpload"
        >
          <template #upload-button>
            <a-button v-permission="'ui.page:create'" type="primary" size="small" :loading="batchUploading" data-testid="qa-views-uitest-page-elements-button-上传模板"> 上传模板 </a-button>
          </template>
        </a-upload>
      </section>
    </div>
  </a-modal>
  <a-drawer
    v-model:visible="aiInfoDrawer.visible"
    :title="aiInfoDrawer.title"
    width="50%"
    :footer="false"
    unmount-on-close
  >
    <div class="mango-ui-element-ai-drawer">
      <div class="mango-ui-element-ai-summary">
        <div class="mango-ui-element-ai-card">
          <span>基线快照</span>
          <strong>{{ aiInfoDrawer.data?.statistics?.snapshot_count || 0 }}</strong>
        </div>
        <div class="mango-ui-element-ai-card">
          <span>修复记录</span>
          <strong>{{ aiInfoDrawer.data?.statistics?.heal_record_count || 0 }}</strong>
        </div>
        <div class="mango-ui-element-ai-card">
          <span>待确认</span>
          <strong>{{ aiInfoDrawer.data?.statistics?.pending_suggestion_count || 0 }}</strong>
        </div>
        <div class="mango-ui-element-ai-card">
          <span>已应用</span>
          <strong>{{ aiInfoDrawer.data?.statistics?.applied_count || 0 }}</strong>
        </div>
      </div>
      <section class="mango-ui-element-ai-section">
        <div class="mango-ui-element-ai-section-head">
          <h3>候选定位器</h3>
          <span>来源于最近一次修复记录，验证通过的候选可写回元素配置</span>
        </div>
        <UiElementHealCandidatePanel
          :rows="aiCandidateRows"
          :applying-key="aiInfoDrawer.applyingKey"
          :empty-text="aiCandidateEmptyText"
          @apply="applyAiCandidate"
        />
      </section>
      <section
        v-if="aiCandidateSummaryRows.length || aiCandidateSummaryRejections.length"
        class="mango-ui-element-ai-section"
      >
        <div class="mango-ui-element-ai-section-head">
          <h3>候选摘要</h3>
          <span>按候选来源和拒绝原因快速判断修复卡点</span>
        </div>
        <div v-if="aiCandidateSummaryRows.length" class="mango-ui-element-ai-kv-grid">
          <div
            v-for="item in aiCandidateSummaryRows"
            :key="item.label"
            class="mango-ui-element-ai-kv"
          >
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
          </div>
        </div>
        <a-collapse
          v-if="aiCandidateSummaryRejections.length"
          :bordered="false"
          class="mango-ui-element-ai-rejection-list"
        >
          <a-collapse-item :header="`拒绝原因汇总（${aiCandidateSummaryRejections.length} 项）`">
            <div
              v-for="(item, index) in aiCandidateSummaryRejections"
              :key="`${item.source || 'unknown'}-${index}`"
              class="mango-ui-element-ai-rejection-item"
            >
              <a-tag size="small" color="red">{{ item.source_label }}</a-tag>
              <span>{{ item.reason || '-' }}</span>
              <em v-if="item.loc">{{ item.loc }}</em>
            </div>
          </a-collapse-item>
        </a-collapse>
      </section>
      <section class="mango-ui-element-ai-section">
        <div class="mango-ui-element-ai-section-head">
          <h3>元素信息</h3>
          <span>当前元素的分类、模式、基线和最近执行信息</span>
        </div>
        <div class="mango-ui-element-ai-kv-grid">
          <div v-for="item in aiElementInfoRows" :key="item.label" class="mango-ui-element-ai-kv">
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
          </div>
        </div>
      </section>
      <section class="mango-ui-element-ai-section">
        <div class="mango-ui-element-ai-section-head">
          <h3>触发上下文</h3>
          <span>最近一次自愈独有的失败与触发信息</span>
        </div>
        <div v-if="aiLatestHealRecordRows.length" class="mango-ui-element-ai-kv-grid">
          <div
            v-for="item in aiLatestHealRecordRows"
            :key="item.label"
            class="mango-ui-element-ai-kv"
          >
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
          </div>
        </div>
        <a-empty v-else description="暂无修复记录" />
      </section>
      <section class="mango-ui-element-ai-section">
        <div class="mango-ui-element-ai-section-head">
          <h3>基线历史</h3>
          <span>最近 10 次有效基线采集记录</span>
        </div>
        <a-table
          :data="aiSnapshotHistoryRows"
          :pagination="false"
          :bordered="false"
          size="small"
          :scroll="{ x: 920 }"
        >
          <template #columns>
            <a-table-column title="采集时间" data-index="create_time" :width="180" />
            <a-table-column title="环境" data-index="test_env" :width="80" />
            <a-table-column title="匹配数" data-index="match_count" :width="80" />
            <a-table-column title="角色" data-index="element_role" :width="110" />
            <a-table-column title="元素文本" data-index="element_text" :ellipsis="true" :tooltip="true" />
            <a-table-column title="页面地址" data-index="url" :ellipsis="true" :tooltip="true" />
            <a-table-column title="操作" :width="100" fixed="right" align="center">
              <template #cell="{ record }">
                <a-button v-permission="'ui.page:detail'"
                  size="mini"
                  type="text"
                  :loading="aiInfoDrawer.baselineLoadingKey === String(record.id)"
                  :disabled="Boolean(aiInfoDrawer.baselineLoadingKey)"
                  @click="openAiBaselineDetail(record)"
                >
                  详情
                </a-button>
              </template>
            </a-table-column>
          </template>
        </a-table>
      </section>
      <section class="mango-ui-element-ai-section">
        <div class="mango-ui-element-ai-section-head">
          <h3>自愈历史</h3>
          <span>最近 20 次自愈执行和写回记录</span>
        </div>
        <a-table
          :data="aiHealHistoryRows"
          :pagination="false"
          :bordered="false"
          size="small"
          :scroll="{ x: 920 }"
        >
          <template #columns>
            <a-table-column title="触发时间" data-index="create_time" :width="180" />
            <a-table-column title="状态" data-index="status_label" :width="120" />
            <a-table-column title="置信度" data-index="confidence" :width="90" />
            <a-table-column title="写回" data-index="applied_label" :width="70" />
            <a-table-column title="采用定位器" data-index="selected_loc" :ellipsis="true" :tooltip="true" />
            <a-table-column title="失败原因" data-index="failed_reason" :ellipsis="true" :tooltip="true" />
            <a-table-column title="操作" :width="100" fixed="right" align="center">
              <template #cell="{ record }">
                <a-button v-permission="'ui.page:detail'"
                  size="mini"
                  type="text"
                  :loading="aiInfoDrawer.healLoadingKey === String(record.id)"
                  :disabled="Boolean(aiInfoDrawer.healLoadingKey)"
                  @click="openAiHealDetail(record)"
                >
                  详情
                </a-button>
              </template>
            </a-table-column>
          </template>
        </a-table>
      </section>
    </div>
  </a-drawer>
  <UiElementBaselineDetailPanel ref="baselineDetailPanelRef" />
  <UiElementHealRecordDetailPanel ref="healDetailPanelRef" />
  <UiElementDeepCheckVariablesDialog ref="deepCheckVariablesDialogRef" />
  <UiElementCheckResultPanel
    v-model:visible="elementCheck.visible"
    :title="elementCheck.title"
    :data="elementCheck.data"
    :apply-loading="deepCheckApplyLoading"
    :applied="deepCheckApplied"
    @apply="applyDeepCheckUpdates"
  />
</template>
<script lang="ts" setup>
  import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import { IconDesktop } from '@arco-design/web-vue/es/icon'
  import { tableColumns } from './config'
  import { useRoute } from 'vue-router'
  import { usePageData } from '@/store/page-data'
  import {
    deleteUiElement,
    getUiElementAiHealRecords,
    getUiElementAiInfo,
    getUiElementAiSnapshots,
    getUiElementCategory,
    getUiElement,
    getUiElementUpload,
    putUiElementAiHealApply,
    postUiElementCheck,
    postUiElementOpenBrowser,
    putUiElementDeepCheckApply,
  } from '@/api/uitest/element'
  import { getUiPage } from '@/api/uitest/page'
  import useUserStore from '@/store/modules/user'
  import { useEnum } from '@/store/modules/get-enum'
  import { usePagination, useRowKey, useRowSelection, useTable } from '@/hooks/table'
  import { useSelectValueStore } from '@/store/modules/get-ope-value'
  import UiElementEditPanel from '@/components/business/UiElementEditPanel.vue'
  import UiElementBaselineDetailPanel from '@/components/business/UiElementBaselineDetailPanel.vue'
  import UiElementHealRecordDetailPanel from '@/components/business/UiElementHealRecordDetailPanel.vue'
  import UiElementDeepCheckVariablesDialog from '@/components/business/UiElementDeepCheckVariablesDialog.vue'
  import UiElementHealCandidatePanel from '@/components/business/UiElementHealCandidatePanel.vue'
  import UiLiveWorkbenchPanel from '@/components/business/UiLiveWorkbenchPanel.vue'
  import StickyHorizontalTable from '@/components/table/StickyHorizontalTable.vue'
  import UiLocatorGroupCell from '@/components/business/UiLocatorGroupCell.vue'
  import UiElementCheckResultPanel from '@/components/business/UiElementCheckResultPanel.vue'
  import VariableReferencePanel from '@/components/business/VariableReferencePanel.vue'
  import { useUiLiveWorkbench } from '@/hooks/use-ui-live-workbench'
  import { getActiveExecutorTasks, getExecutorTask } from '@/api/system/executor-task'
  import {
    clearExecutorTaskObservation,
    loadExecutorTaskObservation,
    saveExecutorTaskObservation,
  } from '@/utils/executor-task-observer.mjs'

  const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection()
  const pagination = usePagination(doRefresh, () => table.tableLoading)
  const rowKey = useRowKey('id')
  const table = useTable()

  const userStore = useUserStore()
  const enumStore = useEnum()
  const useSelectValue = useSelectValueStore()
  const categoryList = ref<any[]>([])
  const categoryLoading = ref(false)
  const browserOpening = ref(false)
  const batchAddVisible = ref(false)
  const batchUploading = ref(false)
  const deepCheckVariablesDialogRef = ref<InstanceType<
    typeof UiElementDeepCheckVariablesDialog
  > | null>(null)
  const categoryKeyword = ref('')
  const selectedCategoryKeys = ref<string[]>(['__all__'])
  const {
    visible: liveWorkbenchVisible,
    opening: liveWorkbenchOpening,
    sectionRef: liveWorkbenchSectionRef,
    toggle: toggleElementLiveWorkbench,
  } = useUiLiveWorkbench(() => {
    if (userStore.selected_environment == null) {
      Message.error('请先选择测试环境')
      return false
    }
    return true
  })
  const aiInfoDrawer = reactive({
    visible: false,
    title: 'AI自愈',
    data: {},
    currentElement: null as any,
    applyingKey: '',
    loadingKey: '',
    baselineLoadingKey: '',
    healLoadingKey: '',
  })
  const elementCheck = reactive({
    visible: false,
    title: '元素检测结果',
    data: null as any,
    currentElement: null as any,
    checkId: '',
    loadingKey: '',
    taskId: '',
  })
  const elementCheckLoading = computed(() => Boolean(elementCheck.loadingKey))
  const deepCheckApplyLoading = ref(false)
  const deepCheckApplied = ref(false)
  const deepCheckWritableUpdates = computed(() => {
    if (elementCheck.data?.check_mode !== 'deep') return []
    const updates = elementCheck.data?.selected_result?.locator_engine?.locator_updates
    return Array.isArray(updates)
      ? updates.filter((item: any) => item?.same_target === true && item?.slot && item?.loc)
      : []
  })
  // 元素检测超时保护：执行器长时间未回结果时自动恢复按钮，避免 loadingKey 永久卡死吞掉后续点击
  let elementCheckTimer: ReturnType<typeof setTimeout> | null = null
  let elementCheckPollTimer: ReturnType<typeof setTimeout> | null = null

  function clearElementCheckTimer() {
    if (elementCheckTimer) {
      clearTimeout(elementCheckTimer)
      elementCheckTimer = null
    }
    if (elementCheckPollTimer) {
      clearTimeout(elementCheckPollTimer)
      elementCheckPollTimer = null
    }
  }
  const pageData: any = usePageData()

  const props = withDefaults(
    defineProps<{
      pageId?: string | number
      embedded?: boolean
    }>(),
    {
      pageId: '',
      embedded: false,
    }
  )
  const emit = defineEmits<{
    (event: 'close'): void
  }>()
  const route = useRoute()
  function firstQueryValue(value: any) {
    return Array.isArray(value) ? value[0] : value
  }

  const currentPageId = computed(
    () => firstQueryValue(props.pageId || route.query.id || pageData.record?.id) || ''
  )
  const defaultPageRecord = () => ({
    id: currentPageId.value,
    name: '',
    project_product: {
      id: '',
      ui_client_type: '0',
    },
  })
  const pageRecord = ref<any>({
    ...defaultPageRecord(),
    ...(pageData.record || {}),
    project_product: pageData.record?.project_product || defaultPageRecord().project_product,
  })
  if (!props.embedded && !pageData.record) {
    pageData.setRecord(defaultPageRecord())
  }
  const isWebClient = computed(
    () => String(pageRecord.value?.project_product?.ui_client_type) === '0'
  )
  const activeOperationOptions = computed(() =>
    useSelectValue.getOperationOptions(pageRecord.value?.project_product?.ui_client_type ?? 0)
  )
  const pageElementDetailTitle = computed(() => {
    const id = currentPageId.value || '-'
    const name = pageRecord.value?.name || '-'
    return `页面元素配置 / ${id} / ${name}`
  })
  const activeCategory = computed(() => selectedCategoryKeys.value[0] || '__all__')
  const elementCategoryCount = computed(
    () => categoryList.value.filter((item) => item.key !== '__all__').length
  )
  const activeCategoryName = computed(() =>
    activeCategory.value === '__all__' ? '未分类' : activeCategory.value
  )
  const categoryTree = computed(() => {
    const keyword = categoryKeyword.value.trim().toLowerCase()
    return categoryList.value
      .filter(
        (item) =>
          !keyword ||
          String(item.title || '')
            .toLowerCase()
            .includes(keyword)
      )
      .map((item) => ({
        key: item.key,
        title: `${item.title} (${item.count || 0})`,
      }))
  })
  const aiCandidateRows = computed(() => {
    const record = (aiInfoDrawer.data as any)?.latest_heal_record
    const recordId = record?.id
    const trigger = record?.ai_prompt_summary?.locator_engine?.trigger || {}
    return (record?.candidates || []).map((item: any, index: number) => ({
      ...item,
      record_id: recordId,
      candidate_index: item.candidate_index ?? index,
      trigger,
      source_label: aiCandidateSourceLabel(item.source),
      final_score: item.final_score ?? item.score ?? item.confidence ?? 0,
      diagnostic_text: aiCandidateDiagnosticText(item),
    }))
  })
  const aiCandidateEmptyText = computed(() => {
    const record = (aiInfoDrawer.data as any)?.latest_heal_record
    if (!record) {
      return '暂无修复候选。元素当前可正常定位，只有定位失败并触发 AI 自愈后才会生成候选定位器。'
    }
    return '最近一次修复记录未生成可用候选。请检查执行器日志中的统一定位引擎候选生成和验证信息。'
  })
  const aiLocatorEngineData = computed(() => {
    const data = aiInfoDrawer.data as any
    const healEngine = data?.latest_heal_record?.ai_prompt_summary?.locator_engine
    const runtimeEngine = data?.element?.latest_runtime_snapshot?.locator_engine
    if (
      healEngine &&
      typeof healEngine === 'object' &&
      Object.keys(healEngine?.candidate_summary || {}).length
    ) {
      return healEngine
    }
    if (runtimeEngine && typeof runtimeEngine === 'object') return runtimeEngine
    if (healEngine && typeof healEngine === 'object') return healEngine
    return {}
  })
  const aiCandidateSummary = computed(() => {
    const summary = aiLocatorEngineData.value?.candidate_summary
    return summary && typeof summary === 'object' ? summary : {}
  })
  const aiCandidateSummaryRows = computed(() => {
    const summary = aiCandidateSummary.value as any
    if (!summary || !Object.keys(summary).length) return []
    return [
      { label: 'Trace ID', value: formatAiValue(aiLocatorEngineData.value?.trace_id) },
      { label: '候选总数', value: formatAiValue(summary.total) },
      { label: '已验证', value: formatAiValue(summary.checked) },
      { label: '通过候选', value: formatAiValue(summary.verified) },
      { label: '来源分布', value: formatCandidateSourceSummary(summary.by_source) },
      { label: '拒绝分布', value: formatCandidateRejectSummary(summary.by_source) },
      { label: '最终来源', value: aiCandidateSourceLabel(aiLocatorEngineData.value?.used_source) },
      { label: 'Agent调用', value: aiLocatorEngineData.value?.harness?.agent_called ? '是' : '否' },
      {
        label: 'Harness耗时',
        value:
          aiLocatorEngineData.value?.harness?.duration_ms != null
            ? `${aiLocatorEngineData.value.harness.duration_ms} ms`
            : '-',
      },
      {
        label: 'Prompt版本',
        value: formatAiValue(aiLocatorEngineData.value?.harness?.prompt_version),
      },
    ]
  })
  const aiCandidateSummaryRejections = computed(() => {
    const summary = aiCandidateSummary.value as any
    const rows = Array.isArray(summary?.top_rejections) ? summary.top_rejections : []
    return rows.slice(0, 8).map((item: any) => ({
      ...item,
      source_label: aiCandidateSourceLabel(item.source),
    }))
  })
  const aiElementInfoRows = computed(() => {
    const element = (aiInfoDrawer.data as any)?.element || {}
    return [
      { label: '元素ID', value: formatAiValue(element.id) },
      { label: '元素名称', value: formatAiValue(element.name) },
      { label: '元素分类', value: formatAiValue(element.category) },
      { label: '自愈状态', value: aiHealStatusMeta(element.ai_heal_status).label },
      { label: '稳定通过次数', value: formatAiValue(element.ai_stable_pass_count) },
      { label: '最近匹配数量', value: formatAiValue(element.latest_match_count) },
      { label: '最近文本', value: formatAiValue(element.latest_element_text) },
      { label: '最近基线时间', value: formatAiValue(element.ai_last_snapshot_time) },
      { label: '最近自愈时间', value: formatAiValue(element.ai_last_heal_time) },
    ]
  })
  const aiLatestHealRecordRows = computed(() => {
    const record = (aiInfoDrawer.data as any)?.latest_heal_record
    if (!record) return []
    const trigger = record?.ai_prompt_summary?.locator_engine?.trigger || {}
    return [
      { label: '失败原因', value: formatAiValue(record.failed_reason) },
      { label: '触发原因', value: formatAiValue(trigger.error) },
      { label: '触发操作', value: formatAiValue(trigger.ope_key) },
      { label: '原始定位', value: formatAiValue(trigger.origin_loc) },
      { label: '原始下标', value: formatAiValue(trigger.origin_sub) },
      { label: '页面URL', value: formatAiValue(record.page_url) },
    ]
  })
  const aiSnapshotHistoryRows = computed(() => {
    const rows = (aiInfoDrawer.data as any)?.snapshots
    return (Array.isArray(rows) ? rows : []).map((item: any) => ({
      ...item,
      create_time: formatAiValue(item.create_time),
      test_env: formatAiEnvironment(item.test_env),
      match_count: formatAiValue(item.match_count),
      element_role: formatAiValue(item.element_role),
      element_text: formatAiValue(item.element_text),
      url: formatAiValue(item.url),
    }))
  })
  const aiHealHistoryRows = computed(() => {
    const rows = (aiInfoDrawer.data as any)?.heal_records
    return (Array.isArray(rows) ? rows : []).map((item: any) => ({
      ...item,
      create_time: formatAiValue(item.create_time),
      status_label: aiHealRecordStatusLabel(item.status),
      confidence: formatAiValue(item.confidence),
      applied_label: item.applied ? '是' : '否',
      selected_loc: formatAiValue(item.selected_loc),
      failed_reason: formatAiValue(item.failed_reason || item.error_message),
    }))
  })

  const elementEditPanelRef = ref<InstanceType<typeof UiElementEditPanel> | null>(null)
  const baselineDetailPanelRef = ref<InstanceType<typeof UiElementBaselineDetailPanel> | null>(null)
  const healDetailPanelRef = ref<InstanceType<typeof UiElementHealRecordDetailPanel> | null>(null)
  const liveWorkbenchRef = ref<InstanceType<typeof UiLiveWorkbenchPanel> | null>(null)

  function formatAiValue(value: any) {
    if (value === null || value === undefined || value === '') return '-'
    if (typeof value === 'object') return JSON.stringify(value)
    return String(value)
  }

  function formatAiEnvironment(value: any) {
    if (value === null || value === undefined || value === '') return '-'
    return enumStore.environment_type.find((item) => String(item.key) === String(value))?.title || '-'
  }

  function aiHealRecordStatusLabel(value: any) {
    const status = Number(value)
    if (status === 1) return '已生成建议'
    if (status === 2) return '候选已验证'
    if (status === 3) return '修复失败'
    if (status === 4) return '人工写回'
    if (status === 5) return '临时自愈成功'
    if (status === 6) return '自动写回'
    if (status === 7) return '自动写回失败'
    return '-'
  }

  function aiCandidateSourceLabel(value: any) {
    const map: Record<string, string> = {
      applied_heal_record: '已应用修复',
      latest_snapshot_locator: '最近基线',
      history_snapshot_locator: '历史基线',
      baseline_semantic: '基线语义',
      semantic_role_name: '语义角色',
      semantic_placeholder: '占位符语义',
      semantic_text: '文本语义',
      prompt_text_candidate: '提示词文本直查',
      playwright_label: 'Playwright标签语义',
      playwright_role: 'Playwright角色语义',
      dom_stable_attr: 'DOM稳定属性',
      dom_proximity: 'DOM邻近控件',
      dom_proximity_xpath: 'DOM邻近控件XPath',
      label_relative_xpath: '标签相对XPath',
      portal_text_option: '弹层文本选项',
      unique_visible_text: '唯一可见文本',
      playwright_text_sub: 'Playwright文本下标',
      popup_text_option: '弹层普通文本选项',
      ai_accessibility: 'AI语义候选',
      visual_agent: '视觉语义候选',
      candidate_exhausted: '候选耗尽',
      fixed_locator: '固定定位',
    }
    const key = String(value || '')
    return map[key] || key || '-'
  }

  function formatCandidateSourceSummary(value: any) {
    if (!value || typeof value !== 'object') return '-'
    const rows = Object.entries(value)
      .filter(([, item]: any) => Number(item?.total || item?.checked || 0) > 0)
      .slice(0, 6)
      .map(([source, item]: any) => {
        const total = Number(item?.total || 0)
        const verified = Number(item?.verified || 0)
        return `${aiCandidateSourceLabel(source)} ${verified}/${total}`
      })
    return rows.length ? rows.join('；') : '-'
  }

  function formatCandidateRejectSummary(value: any) {
    if (!value || typeof value !== 'object') return '-'
    const reasons: string[] = []
    Object.entries(value).forEach(([source, item]: any) => {
      const reasonMap = item?.reasons || {}
      Object.entries(reasonMap).forEach(([reason, count]: any) => {
        reasons.push(`${aiCandidateSourceLabel(source)}:${reason} ${count}`)
      })
    })
    return reasons.length ? reasons.slice(0, 6).join('；') : '-'
  }

  function aiCandidateDiagnosticText(item: any) {
    const parts = [
      item?.matched_label ? `标签=${item.matched_label}` : '',
      item?.candidate_text ? `文本=${item.candidate_text}` : '',
      item?.element_text ? `结果=${item.element_text}` : '',
      item?.actionability_checked ? '已做可操作性检查' : '',
      item?.trigger?.error ? `触发=${item.trigger.error}` : '',
      item?.reason ? `原因=${item.reason}` : '',
    ].filter(Boolean)
    return parts.length ? parts.join('；') : '-'
  }

  function elementDescriptionSummary(record: any) {
    const parts = [
      record?.location_description
        ? `识别线索：${String(record.location_description).trim()}`
        : '',
      record?.surrounding_text
        ? `排除：${String(record.surrounding_text).trim()}`
        : '',
    ].filter(Boolean)
    return parts.join('；') || String(record?.prompt || '').trim() || '-'
  }

  function doAppend() {
    elementEditPanelRef.value?.openCreate(currentPageId.value, activeCategoryName.value)
  }

  const beforeUpload = async (file: File) => {
    if (batchUploading.value) return false
    batchUploading.value = true
    const formData = new FormData()
    formData.append('file', file)
    formData.append('page_id', String(currentPageId.value))
    formData.append('name', file.name)
    try {
      const res = await getUiElementUpload(formData)
      Message.success(res.msg)
      batchAddVisible.value = false
      loadCategories()
      doRefresh()
      await liveWorkbenchRef.value?.refreshElements?.()
    } catch (error) {
      console.log(error)
    } finally {
      batchUploading.value = false
    }
    return false
  }

  function onDelete(record: any) {
    const batch = record === null
    if (batch) {
      if (selectedRowKeys.value.length === 0) {
        Message.error('请选择要删除的数据')
        return
      }
    }
    Modal.confirm({
      title: '提示',
      content: '是否要删除此元素？',
      cancelText: '取消',
      okText: '删除',
      onBeforeOk: () => {
        return deleteUiElement(batch ? selectedRowKeys.value : record.id)
          .then((res) => {
            Message.success(res.msg)
          })
          .catch(console.log)
          .finally(() => {
            loadCategories()
            doRefresh()
            if (batch) {
              selectedRowKeys.value = []
            }
          })
      },
    })
  }

  function onUpdate(record: any) {
    elementEditPanelRef.value?.openEdit(record)
  }

  function doResetSearch() {
    if (props.embedded) {
      emit('close')
      return
    }
    window.history.back()
  }

  async function ensurePageRecord() {
    if (!currentPageId.value) return
    if (
      !props.embedded &&
      pageData.record?.id &&
      String(pageData.record.id) === String(currentPageId.value)
    ) {
      const record = {
        ...defaultPageRecord(),
        ...pageData.record,
        project_product: pageData.record.project_product || defaultPageRecord().project_product,
      }
      pageRecord.value = record
      pageData.setRecord(record)
      return
    }
    const res = await getUiPage({ id: currentPageId.value, page: 1, pageSize: 1 })
    const record = (res.data || [])[0]
    const resolvedRecord = {
      ...defaultPageRecord(),
      ...(record || {}),
      project_product: record?.project_product || defaultPageRecord().project_product,
    }
    pageRecord.value = resolvedRecord
    if (!props.embedded) {
      pageData.setRecord(resolvedRecord)
    }
  }

  async function doRefresh() {
    if (!currentPageId.value) return
    let value = {}
    value['page'] = pagination.page
    value['pageSize'] = pagination.pageSize
    value['page_id'] = currentPageId.value
    if (activeCategory.value !== '__all__') {
      value['category'] = activeCategory.value
    }
    try {
      const res = await getUiElement(value)
      table.handleSuccess(res)
      pagination.setTotalSize((res as any).totalSize)
    } catch (error) {
      console.log(error)
    }
  }

  async function resumeElementCheckTask() {
    try {
      for (const record of table.dataList) {
        const observation = loadExecutorTaskObservation('ui-element-check', record.id)
        if (!observation?.taskId) continue
        elementCheck.loadingKey = String(record.id)
        elementCheck.currentElement = record
        elementCheck.checkId = String(observation.meta?.checkId || '')
        elementCheck.taskId = String(observation.taskId)
        elementCheck.data = null
        scheduleElementTaskPoll(0)
        return
      }
      const res = await getActiveExecutorTasks({ business_type: 'u_element_check' })
      const task = (res.data || []).find((item: any) =>
        table.dataList.some((record: any) => String(record.id) === String(item.business_id))
      )
      if (!task?.task_id) return
      const record = table.dataList.find(
        (item: any) => String(item.id) === String(task.business_id)
      )
      if (!record) return
      elementCheck.loadingKey = String(record.id)
      elementCheck.currentElement = record
      elementCheck.checkId = ''
      elementCheck.taskId = String(task.task_id)
      elementCheck.data = null
      saveExecutorTaskObservation('ui-element-check', record.id, {
        taskId: elementCheck.taskId,
        businessType: 'u_element_check',
      })
      scheduleElementTaskPoll(0)
    } catch (error) {
      console.log(error)
    }
  }

  function loadCategories() {
    if (!currentPageId.value) return
    categoryLoading.value = true
    getUiElementCategory({ page_id: currentPageId.value })
      .then((res) => {
        categoryList.value = res.data || []
        if (!categoryList.value.some((item) => item.key === activeCategory.value)) {
          selectedCategoryKeys.value = ['__all__']
        }
      })
      .catch(console.log)
      .finally(() => {
        categoryLoading.value = false
      })
  }

  function onCategorySelect(keys: Array<string>) {
    selectedCategoryKeys.value = [keys[0] || '__all__']
    pagination.page = 1
    doRefresh()
  }

  async function handleElementSaved() {
    loadCategories()
    doRefresh()
    await liveWorkbenchRef.value?.refreshElements?.()
  }

  function aiHealStatusMeta(status: number) {
    const map: Record<number, { label: string; color: string }> = {
      0: { label: '无基线', color: 'gray' },
      1: { label: '已有基线', color: 'green' },
      2: { label: '待确认', color: 'orange' },
      3: { label: '已修复', color: 'blue' },
      4: { label: '修复失败', color: 'red' },
    }
    return map[status] || map[0]
  }

  function getElementExpName(value: any) {
    return enumStore.element_exp.find((item) => item.key === value)?.title || '-'
  }

  function getLocatorGroup(record: any, index: number) {
    if (index === 1) {
      return { exp: record.exp, loc: record.loc, sub: record.sub }
    }
    return {
      exp: record[`exp${index}`],
      loc: record[`loc${index}`],
      sub: record[`sub${index}`],
    }
  }

  function getLocatorRuntime(record: any, index: number) {
    const groups = Array.isArray(record?.latest_runtime_snapshot?.locator_groups)
      ? record.latest_runtime_snapshot.locator_groups
      : []
    const runtime =
      groups.find(
        (item: any, groupIndex: number) => Number(item?.group || groupIndex + 1) === index
      ) || {}
    return {
      count:
        runtime.count ??
        runtime.match_count ??
        (index === 1 ? record?.latest_match_count ?? null : null),
      elementText:
        runtime.element_text ||
        runtime.text ||
        (index === 1 ? record?.latest_element_text || '' : ''),
    }
  }

  function expectedEventParamSummary(expectedEvent: any) {
    const values = Array.isArray(expectedEvent?.ope_value) ? expectedEvent.ope_value : []
    return values
      .filter((item: any) => item?.v !== undefined && item?.v !== null && item?.v !== '')
      .map((item: any) => `${item.n || item.f}=${item.v}`)
      .join('；')
  }

  function onAiInfo(record: any) {
    if (aiInfoDrawer.loadingKey) return
    aiInfoDrawer.loadingKey = String(record.id)
    const query = {
      element_id: record.id,
      test_env: userStore.selected_environment,
    }
    Promise.all([
      getUiElementAiInfo(query),
      getUiElementAiSnapshots({ ...query, page: 1, pageSize: 10 }),
      getUiElementAiHealRecords({ ...query, page: 1, pageSize: 20 }),
    ])
      .then(([res, snapshotsRes, healRecordsRes]) => {
        aiInfoDrawer.title = `AI自愈 / ${record.name}`
        aiInfoDrawer.data = {
          ...(res.data || {}),
          snapshots: snapshotsRes.data?.items || [],
          heal_records: healRecordsRes.data?.items || [],
        }
        aiInfoDrawer.currentElement = record
        aiInfoDrawer.visible = true
      })
      .catch(console.log)
      .finally(() => {
        aiInfoDrawer.loadingKey = ''
      })
  }

  async function openAiBaselineDetail(record: any) {
    if (!record?.id || !aiInfoDrawer.currentElement?.id || aiInfoDrawer.baselineLoadingKey) return
    aiInfoDrawer.baselineLoadingKey = String(record.id)
    try {
      await baselineDetailPanelRef.value?.open(record.id, aiInfoDrawer.currentElement.id)
    } finally {
      aiInfoDrawer.baselineLoadingKey = ''
    }
  }

  async function openAiHealDetail(record: any) {
    if (!record?.id || !aiInfoDrawer.currentElement?.id || aiInfoDrawer.healLoadingKey) return
    aiInfoDrawer.healLoadingKey = String(record.id)
    try {
      await healDetailPanelRef.value?.open(record.id, aiInfoDrawer.currentElement.id)
    } finally {
      aiInfoDrawer.healLoadingKey = ''
    }
  }

  function applyAiCandidate(record: any, rowIndex: number, targetSlot: number) {
    if (!record.record_id) {
      Message.error('缺少修复记录ID')
      return
    }
    const applyingKey = `${record.record_id}-${rowIndex}-${targetSlot}`
    aiInfoDrawer.applyingKey = applyingKey
    putUiElementAiHealApply({
      record_id: record.record_id,
      candidate_index: record.candidate_index ?? rowIndex,
      target_slot: targetSlot,
    })
      .then((res) => {
        Message.success(res.msg || '写回成功')
        if (aiInfoDrawer.currentElement) {
          onAiInfo(aiInfoDrawer.currentElement)
        }
        loadCategories()
        doRefresh()
      })
      .catch(console.log)
      .finally(() => {
        if (aiInfoDrawer.applyingKey === applyingKey) {
          aiInfoDrawer.applyingKey = ''
        }
      })
  }

  async function onCheck(record: any, checkMode: 'normal' | 'deep' = 'deep') {
    // 普通检测和深度检测共用页面级互斥状态，避免从不同入口并发发送检测任务。
    if (elementCheckLoading.value) return
    if (userStore.selected_environment == null) {
      Message.error('请先选择测试环境')
      return
    }
    const runtimeVariables =
      checkMode === 'deep'
        ? await deepCheckVariablesDialogRef.value?.open({
            ...record,
            page_url: pageRecord.value.url,
          })
        : {}
    if (runtimeVariables === null) return
    if (liveWorkbenchVisible.value) {
      if (!liveWorkbenchRef.value) {
        Message.warning('实时工作区正在加载，请稍后重试')
        return
      }
      await liveWorkbenchRef.value.checkElementInWorkspace(record, checkMode, runtimeVariables)
      return
    }
    elementCheck.loadingKey = String(record.id)
    elementCheck.currentElement = record
    elementCheck.checkId = ''
    elementCheck.taskId = ''
    elementCheck.data = null
    clearElementCheckTimer()
    elementCheckTimer = setTimeout(() => {
      if (elementCheck.loadingKey) {
        elementCheck.loadingKey = ''
        elementCheck.currentElement = null
        Message.warning(
          `${checkMode === 'deep' ? '元素深度检测' : '元素检测'}超时，请确认执行器在线后重试`
        )
      }
    }, checkMode === 'deep' ? 180000 : 60000)
    postUiElementCheck({
      element_id: record.id,
      test_env: userStore.selected_environment,
      check_mode: checkMode,
      runtime_variables: runtimeVariables || {},
    })
      .then((res) => {
        elementCheck.checkId = String(res.data?.check_id || '')
        elementCheck.taskId = String(res.data?.task_id || '')
        if (elementCheck.taskId) {
          saveExecutorTaskObservation('ui-element-check', record.id, {
            taskId: elementCheck.taskId,
            businessType: 'u_element_check',
            meta: { checkId: elementCheck.checkId, checkMode },
          })
          scheduleElementTaskPoll(0)
        }
        Message.success(res.msg)
      })
      .catch((error) => {
        console.log(error)
        clearElementCheckTimer()
        elementCheck.loadingKey = ''
        elementCheck.currentElement = null
      })
  }

  function scheduleElementTaskPoll(delay = 1000) {
    if (!elementCheck.loadingKey || !elementCheck.taskId) return
    if (elementCheckPollTimer) clearTimeout(elementCheckPollTimer)
    elementCheckPollTimer = setTimeout(() => void pollElementTask(), delay)
  }

  async function pollElementTask() {
    if (!elementCheck.loadingKey || !elementCheck.taskId) return
    try {
      const res = await getExecutorTask(elementCheck.taskId)
      const task = res.data || {}
      if (!task.terminal) {
        scheduleElementTaskPoll()
        return
      }
      const result = task.result || {}
      const finishedTaskId = elementCheck.taskId
      const finishedElementId = elementCheck.currentElement?.id
      if (result.check_id || result.element_id) {
        applyElementCheckResult({ ...result, executor_task_id: finishedTaskId })
        if (finishedElementId) {
          clearExecutorTaskObservation('ui-element-check', finishedElementId, finishedTaskId)
        }
        return
      }
      applyElementCheckResult({
        executor_task_id: finishedTaskId,
        check_id: elementCheck.checkId,
        element_id: elementCheck.currentElement?.id,
        element_name: elementCheck.currentElement?.name,
        check_mode: task.task_type === 'element_deep_check' ? 'deep' : 'normal',
        status: 0,
        check_status: 'invalid',
        error_message: task.error_message || '执行器任务未返回检测结果',
      })
      if (finishedElementId) {
        clearExecutorTaskObservation('ui-element-check', finishedElementId, finishedTaskId)
      }
    } catch (error) {
      console.log(error)
      scheduleElementTaskPoll(1500)
    }
  }

  async function openElementPageBrowser() {
    if (browserOpening.value) return
    if (userStore.selected_environment == null) {
      Message.error('请先选择测试环境')
      return
    }
    if (!currentPageId.value) {
      Message.warning('当前元素未绑定页面')
      return
    }
    browserOpening.value = true
    try {
      const res = await postUiElementOpenBrowser({
        page_id: currentPageId.value,
        test_env: userStore.selected_environment,
      })
      Message.success(res.msg || '已通知执行器打开目标页面')
    } finally {
      browserOpening.value = false
    }
  }

  function handleWorkbenchElementCheckStarted(payload: any) {
    const elementId = payload?.element_id
    const scanRowKey = payload?.scan_row_key
    if (!elementId && !scanRowKey) return
    const record = scanRowKey
      ? {
          id: 0,
          name: payload?.element_name || '扫描元素',
          scan_row_key: scanRowKey,
        }
      : table.dataList.find((item: any) => String(item.id) === String(elementId)) || {
          id: elementId,
          name: `元素 ${elementId}`,
        }
    elementCheck.loadingKey = scanRowKey ? `scan:${scanRowKey}` : String(elementId)
    elementCheck.currentElement = record
    elementCheck.checkId = ''
    elementCheck.data = null
  }

  function applyElementCheckResult(result: any, showPanel = true) {
    if (!result) return
    const currentElement =
      elementCheck.currentElement ||
      table.dataList.find((item: any) => String(item.id) === String(result.element_id)) || {
        id: result.element_id,
        name: result.element_name || `元素 ${result.element_id || '-'}`,
      }
    if (
      result.check_id &&
      elementCheck.data?.check_id &&
      String(result.check_id) === String(elementCheck.data.check_id)
    ) {
      // 页面级与实时工作区监听器可能先后收到同一结果。重复回传不再刷新数据，
      // 但必须保持打开结果窗口，避免监听顺序造成第二次检测无弹窗。
      if (showPanel) elementCheck.visible = true
      clearElementCheckTimer()
      elementCheck.loadingKey = ''
      return
    }
    elementCheck.data = result
    deepCheckApplied.value = false
    elementEditPanelRef.value?.applyRuntimeResult?.(result)
    elementCheck.checkId = String(result.check_id || elementCheck.checkId)
    elementCheck.taskId = ''
    elementCheck.title = `${result.check_mode === 'deep' ? '元素深度检测结果' : '元素检测结果'} / ${result.element_name || currentElement.name}`
    elementCheck.visible = showPanel
    clearElementCheckTimer()
    elementCheck.loadingKey = ''
    elementCheck.currentElement = null
    loadCategories()
    doRefresh()
  }

  async function applyDeepCheckUpdates() {
    if (deepCheckApplyLoading.value || deepCheckApplied.value) return
    const elementId = elementCheck.data?.element_id
    const taskId = String(elementCheck.data?.executor_task_id || '')
    if (!elementId || !taskId || !deepCheckWritableUpdates.value.length) return
    deepCheckApplyLoading.value = true
    try {
      const res = await putUiElementDeepCheckApply({ element_id: elementId, task_id: taskId })
      deepCheckApplied.value = true
      const slots = res.data?.applied_slots || []
      Message.success(slots.length ? `已写入第 ${slots.join('、')} 组定位` : res.msg)
      await loadCategories()
      await doRefresh()
      await liveWorkbenchRef.value?.refreshElements?.()
    } finally {
      deepCheckApplyLoading.value = false
    }
  }

  function handleWorkbenchElementCheckResult(result: any) {
    if (!result) return
    liveWorkbenchRef.value?.acceptElementCheckResult?.(result)
    if (!elementCheck.currentElement && result.element_id) {
      handleWorkbenchElementCheckStarted({ element_id: result.element_id })
    }
    // 元素页面统一负责展示检测结果。实时工作区只负责回传，避免其内部状态过滤
    // 导致执行器已经返回结果但半屏窗口没有打开。
    applyElementCheckResult(result)
  }

  function handleWorkbenchElementCheckFinished() {
    clearElementCheckTimer()
    elementCheck.loadingKey = ''
    elementCheck.currentElement = null
  }

  async function handleWorkbenchElementSaved() {
    await loadCategories()
    await doRefresh()
  }

  function onDownload() {
    const file_name = '元素批量上传模版.xlsx'
    const file_path = `/api/download?file_name=${encodeURIComponent(file_name)}`
    let aLink = document.createElement('a')
    aLink.href = file_path
    aLink.download = file_name
    Message.loading('文件下载中~')
    document.body.appendChild(aLink)
    aLink.click()
    document.body.removeChild(aLink)
  }

  onMounted(() => {
    nextTick(async () => {
      await ensurePageRecord()
      loadCategories()
      await doRefresh()
      await resumeElementCheckTask()
      useSelectValue.getSelectValue()
    })
  })
  onBeforeUnmount(() => {
    clearElementCheckTimer()
  })
</script>
<style scoped>
  .mango-detail-workbench-page {
    --ui-element-panel-gap: var(--m-page-gap);
  }

  .mango-ui-element-page--table-only :deep(.mango-table-body__content) {
    overflow-y: hidden;
  }

  .operation-select {
    width: 380px;
  }

  .mango-ui-element-batch-add {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .mango-ui-element-batch-add__item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    padding: 12px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface-soft);
  }

  .mango-ui-element-batch-add__item > div {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 2px;
  }

  .mango-ui-element-batch-add__item strong {
    color: var(--m-text);
    font-size: 13px;
    line-height: 20px;
  }

  .mango-ui-element-batch-add__item span {
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .mango-ui-element-workbench {
    display: grid;
    grid-template-columns: 260px minmax(0, 1fr);
    gap: var(--ui-element-panel-gap);
    height: calc(100% - var(--ui-element-panel-gap));
    margin-top: var(--ui-element-panel-gap);
    min-height: 0;
  }

  .mango-ui-element-workbench-scroll {
    --mango-workbench-min-width: 960px;
    height: calc(100% - var(--ui-element-panel-gap));
    margin-top: var(--ui-element-panel-gap);
  }

  .mango-ui-element-workbench-scroll > .mango-ui-element-workbench {
    min-width: var(--mango-workbench-min-width);
    height: 100%;
    margin-top: 0;
  }

  .mango-ui-element-category-panel,
  .mango-ui-element-main {
    min-height: 0;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-lg);
    background: var(--m-surface);
  }

  .mango-ui-element-category-panel {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 12px;
  }

  .mango-ui-element-category-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 8px;
  }

  .mango-ui-element-category-head h3 {
    margin: 0;
    color: var(--m-text);
    font-size: 16px;
    font-weight: 600;
  }

  .mango-ui-element-category-head p {
    margin: 4px 0 0;
    color: var(--m-muted);
    font-size: 12px;
  }

  .mango-ui-element-category-tree {
    flex: 1;
    min-height: 0;
    overflow: auto;
  }

  .mango-ui-element-main {
    display: flex;
    flex-direction: column;
    padding: 10px 10px 0;
    overflow: hidden;
  }

  .mango-ui-element-toolbar {
    flex: none;
    display: flex;
    justify-content: flex-end;
    margin-bottom: 10px;
  }

  .mango-ui-element-table-region {
    flex: 1;
    min-height: 0;
    overflow-x: hidden;
    overflow-y: auto;
  }

  .mango-ui-element-table {
    min-width: 0;
  }

  .mango-ui-element-footer {
    flex: none;
    margin: 0 -10px;
  }

  .mango-ui-element-footer :deep(.mango-table-mango-footer-container) {
    border-right: 0;
    border-bottom: 0;
    border-left: 0;
    border-radius: 0;
  }

  .mango-ui-element-live-debug-area {
    position: relative;
    display: flex;
    min-height: min(760px, calc(100vh - 128px));
    margin-top: var(--ui-element-panel-gap);
    flex-direction: column;
    overflow: hidden;
  }

  .mango-ui-element-live-debug-panel {
    flex: 1;
    min-height: 0;
  }

  .mango-ui-element-live-debug-area :deep(.mango-ui-live-workbench-panel) {
    height: 100%;
    min-height: 0;
    grid-template-columns: minmax(0, 3fr) minmax(360px, 1.25fr);
    background: var(--m-bg-soft);
    gap: var(--ui-element-panel-gap);
  }

  .mango-ui-element-live-debug-area :deep(.mango-ui-live-workbench-panel__stage) {
    padding: 0;
    gap: var(--ui-element-panel-gap);
    border: 0;
    border-radius: 0;
    background: transparent;
  }

  .mango-ui-element-live-debug-area :deep(.mango-ui-live-workbench-panel__tools) {
    padding: 10px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
  }

  .mango-ui-element-expected-cell {
    display: flex;
    min-width: 0;
    flex-direction: column;
    align-items: flex-start;
    gap: 5px;
  }

  .mango-ui-element-expected-cell-input {
    max-width: 100%;
    overflow: hidden;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-ui-muted {
    color: var(--m-muted);
  }

  .mango-ui-element-ai-drawer {
    display: flex;
    min-height: 0;
    flex-direction: column;
    gap: 12px;
  }

  .mango-ui-element-ai-summary {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 10px;
  }

  .mango-ui-element-ai-card,
  .mango-ui-element-ai-section {
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-lg);
    background: var(--m-surface);
  }

  .mango-ui-element-ai-card {
    display: flex;
    min-height: 64px;
    flex-direction: column;
    justify-content: center;
    padding: 10px 12px;
  }

  .mango-ui-element-ai-card span {
    color: var(--m-muted);
    font-size: 12px;
  }

  .mango-ui-element-ai-card strong {
    margin-top: 4px;
    color: var(--m-text);
    font-size: 22px;
    font-weight: 700;
  }

  .mango-ui-element-ai-section {
    min-height: 0;
    padding: 12px;
  }

  .mango-ui-element-ai-section-head {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 10px;
  }

  .mango-ui-element-ai-section-head h3 {
    margin: 0;
    color: var(--m-text);
    font-size: 15px;
    font-weight: 600;
  }

  .mango-ui-element-ai-section-head span {
    color: var(--m-muted);
    font-size: 12px;
  }

  .mango-ui-element-ai-empty-tip {
    margin-bottom: 8px;
  }

  .mango-ui-element-ai-kv-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 6px 8px;
  }

  .mango-ui-element-ai-kv {
    display: flex;
    min-width: 0;
    align-items: flex-start;
    gap: 8px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-fill-1);
    padding: 6px 8px;
  }

  .mango-ui-element-ai-kv span {
    flex: 0 0 86px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 20px;
    text-align: right;
    white-space: nowrap;
  }

  .mango-ui-element-ai-kv strong {
    flex: 1;
    min-width: 0;
    color: var(--m-text);
    font-size: 13px;
    font-weight: 500;
    line-height: 20px;
    overflow-wrap: anywhere;
    white-space: pre-wrap;
  }

  .mango-ui-element-ai-rejection-list {
    margin-top: 8px;
    background: var(--m-surface-soft);
    border-radius: var(--m-radius-md);
  }

  .mango-ui-element-ai-rejection-item {
    display: grid;
    grid-template-columns: auto minmax(120px, 1fr) minmax(180px, 2fr);
    align-items: center;
    gap: 8px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-fill-1);
    padding: 6px 8px;
    color: var(--m-text);
    font-size: 12px;
  }

  .mango-ui-element-ai-rejection-item + .mango-ui-element-ai-rejection-item {
    margin-top: 6px;
  }

  .mango-ui-element-ai-rejection-item span,
  .mango-ui-element-ai-rejection-item em {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-ui-element-ai-rejection-item em {
    color: var(--m-muted);
    font-style: normal;
  }

  .mango-ui-element-ai-json-scroll {
    max-height: min(52vh, 520px);
    overflow: auto;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-fill-1);
    padding: 8px;
  }

  @media (max-width: 900px) {
    .mango-ui-element-workbench {
      grid-template-columns: 1fr;
    }

    .mango-ui-element-ai-summary {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .mango-ui-element-ai-kv-grid {
      grid-template-columns: 1fr;
    }

    .mango-ui-element-ai-rejection-item {
      grid-template-columns: 1fr;
    }

  }
</style>
