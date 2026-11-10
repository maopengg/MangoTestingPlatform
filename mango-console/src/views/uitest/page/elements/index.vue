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
          <a-button
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
      <div v-if="currentPageId === null" class="mango-soft-panel" role="alert">缺少有效页面ID，请返回后重新进入。</div>
      <div v-if="pageLoading || metadataLoading" class="mango-soft-panel" role="status">正在加载页面信息与元素操作选项…</div>

      <div v-if="actionError || checks.error.value" class="mango-element-page-error" role="alert">{{ actionError || checks.error.value }}</div>
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

            <MangoPanelSpin :loading="categoryLoading" class="mango-ui-element-category-tree">
              <a-tree
                v-model:selected-keys="selectedCategoryKeys"
                :data="categoryTree"
                block-node
                size="small"
                @select="onCategorySelect"
              />
            </MangoPanelSpin>
          </aside>
          <section class="mango-ui-element-main">
            <div class="mango-ui-element-toolbar">
              <a-space wrap>
                <a-button size="small" @click="batchAddVisible = true" data-testid="qa-views-uitest-page-elements-button-批量增加">批量增加</a-button>
                <a-button  type="primary" size="small" @click="doAppend" data-testid="qa-views-uitest-page-elements-button-新增">新增</a-button>
                <a-button  size="small" status="danger" :loading="deleting" @click="onDelete(null)" data-testid="qa-views-uitest-page-elements-button-批量删除">批量删除</a-button>
              </a-space>
            </div>

            <StickyHorizontalTable :scroll-x="TABLE_SCROLL_X">
              <a-table
                class="mango-ui-element-table mango-native-scroll-table"
                :bordered="false"
                :columns="tableColumns"
                :data="elementRows"
                :loading="listLoading"
                :pagination="false"
                :row-selection="{ selectedRowKeys, showCheckedAll }"
                :rowKey="rowKey"
                @selection-change="onSelectionChange"
                :scroll="{ x: TABLE_SCROLL_X, y: '100%' }"
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
    {
        label: '深度检测',
        loading: elementCheckLoading,
        disabled: !pageRecord || pageLoading,
        onClick: () => onCheck(record, 'deep'), },
    {
        label: 'AI自愈',
        loading: aiLoadingKey === String(record.id),
        onClick: () => onAiInfo(record), },
    { label: '编辑', disabled: pageLoading || metadataLoading || !pageRecord || Boolean(metadataError), onClick: () => onUpdate(record) },
    { label: '删除', danger: true, loading: deleting && deletingIds.includes(String(record.id)), onClick: () => onDelete(record) },
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
          :page-url="pageRecord?.url"
          :test-env="userStore.selected_environment"
          :category="activeCategoryName"
          :operation-options="activeOperationOptions"
          :page-type="pageRecord?.project_product?.ui_client_type"
          :project-product-id="pageRecord?.project_product?.id"
          :check-loading="Boolean(checks.pending.loadingKey)"
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
    :context-key="currentPageId ?? undefined"
    :check-loading-key="checks.pending.loadingKey"
    :check-loading="elementCheckLoading"
    @saved="handleElementSaved"
    @check="onCheck"
  />
  <ElementBatchImportModal v-model:visible="batchAddVisible" :page-id="currentPageId" @saved="handleElementSaved" />
  <UiElementAiHealPanel ref="aiHealPanelRef" :test-env="userStore.selected_environment" :context-key="currentPageId ?? undefined" @applied="handleElementSaved" />
  <UiElementDeepCheckVariablesDialog :key="String(currentPageId)" ref="deepCheckVariablesDialogRef" />
  <UiElementCheckResultPanel v-model:visible="elementCheck.visible" :title="elementCheck.title" :data="elementCheck.data" :apply-loading="deepCheckApplyLoading" :applied="deepCheckApplied" @apply="applyDeepCheckUpdates" />
</template>
<script lang="ts" setup>
import { reportLoadError } from '@/utils/load-error'

  import { computed, onMounted, ref } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import { IconDesktop } from '@arco-design/web-vue/es/icon'
  import { useRoute } from 'vue-router'
  import { usePageData } from '@/store/page-data'
  import useUserStore from '@/store/modules/user'
  import { useEnum } from '@/store/modules/get-enum'
  import { usePagination } from '@/hooks/table'
  import { useSelectValueStore } from '@/store/modules/get-ope-value'
  import { deleteUiElement, postUiElementOpenBrowser } from '@/api/uitest/element'
  import { useLiveWorkbenchScope } from '@/hooks/use-live-workbench-scope'
  import { useUiLiveWorkbench } from '@/hooks/use-ui-live-workbench'
  import { liveId, liveError, liveObject, type LiveId } from '@/components/business/ui-live-workbench'
  import { tableColumns, TABLE_SCROLL_X, aiHealStatusMeta } from './config'
  import { elementId, elementResponse, elementDescriptionSummary, getLocatorGroup, getLocatorRuntime, expectedEventParamSummary, type ElementRow } from './element-records'
  import { useElementResources } from './composables/useElementResources'
  import { useElementChecks, type ElementWorkbenchPort } from '@/hooks/use-ui-element-checks'
  import UiElementEditPanel from '@/components/business/UiElementEditPanel.vue'
  import UiElementAiHealPanel from '@/components/business/UiElementAiHealPanel.vue'
  import UiElementDeepCheckVariablesDialog from '@/components/business/UiElementDeepCheckVariablesDialog.vue'
  import UiLiveWorkbenchPanel from '@/components/business/UiLiveWorkbenchPanel.vue'
  import UiLocatorGroupCell from '@/components/business/UiLocatorGroupCell.vue'
  import UiElementCheckResultPanel from '@/components/business/UiElementCheckResultPanel.vue'
  import VariableReferencePanel from '@/components/business/VariableReferencePanel.vue'
  import StickyHorizontalTable from '@/components/table/StickyHorizontalTable.vue'
  import MangoPanelSpin from '@/components/feedback/MangoPanelSpin.vue'
  import ElementBatchImportModal from './components/ElementBatchImportModal.vue'

  const props = withDefaults(defineProps<{ pageId?: string | number; embedded?: boolean }>(), { pageId: '', embedded: false })
  const emit = defineEmits<{ (event: 'close'): void }>()
  const route = useRoute(), pageData = usePageData(), userStore = useUserStore(), enumStore = useEnum(), useSelectValue = useSelectValueStore()
  const currentPageId = computed(() => props.pageId !== '' ? elementId(props.pageId) : Object.prototype.hasOwnProperty.call(route.query, 'id') ? elementId(route.query.id) : elementId(liveObject(pageData.record).id))
  const categoryKeyword = ref(''), selectedCategoryKeys = ref<string[]>(['__all__']), selectedRowKeys = ref<LiveId[]>([])
  const activeCategory = computed(() => selectedCategoryKeys.value[0] || '__all__')
  const activeCategoryName = computed(() => activeCategory.value === '__all__' ? '未分类' : activeCategory.value)
  const listLoading = ref(false)
  const pagination = usePagination(doRefresh, listLoading)
  const rowKey = 'id', showCheckedAll = true
  const batchAddVisible = ref(false), browserOpening = ref(false), deleting = ref(false), deletingIds = ref<string[]>([]), actionError = ref('')
  const metadataLoading = ref(false), metadataError = ref('')
  let metadataSequence = 0
  let confirmation: { close: () => void } | null = null
  const elementEditPanelRef = ref<InstanceType<typeof UiElementEditPanel> | null>(null)
  const aiHealPanelRef = ref<InstanceType<typeof UiElementAiHealPanel> | null>(null)
  const deepCheckVariablesDialogRef = ref<InstanceType<typeof UiElementDeepCheckVariablesDialog> | null>(null)
  const liveWorkbenchRef = ref<(ElementWorkbenchPort & { refreshElements: () => Promise<unknown> }) | null>(null)
  const { visible: liveWorkbenchVisible, opening: liveWorkbenchOpening, sectionRef: liveWorkbenchSectionRef, toggle: toggleElementLiveWorkbench, close: closeWorkbench } = useUiLiveWorkbench(() => scope.available() && currentPageId.value !== null && liveId(userStore.selected_environment) !== null)
  const scope = useLiveWorkbenchScope(() => [currentPageId.value, props.embedded], {
    invalidate() {
      metadataSequence++; metadataLoading.value = false; metadataError.value = ''; actionError.value = ''
      confirmation?.close(); confirmation = null
      resources.invalidate(); checks.invalidate(); closeWorkbench()
      batchAddVisible.value = false; categoryKeyword.value = ''; selectedCategoryKeys.value = ['__all__']; selectedRowKeys.value = []; pagination.page = 1; listLoading.value = false
    },
    resume() { void initialize() },
  })
  const resources = useElementResources({ scope, pageId: () => currentPageId.value, category: () => activeCategory.value, pagination, loading: listLoading, clearSelection() { selectedRowKeys.value = [] } })
  const { page: pageRecord, pageLoading, pageError, categoryLoading, categoryError, listError, rows: elementRows, categories: categoryList } = resources
  const isWebClient = computed(() => pageRecord.value !== null && String(pageRecord.value.project_product?.ui_client_type) === '0')
  const activeOperationOptions = computed(() => useSelectValue.getOperationOptions(pageRecord.value?.project_product?.ui_client_type ?? 0))
  const pageElementDetailTitle = computed(() => `页面元素配置 / ${currentPageId.value ?? '-'} / ${pageRecord.value?.name || '-'}`)
  const categoryTree = computed(() => categoryList.value.filter(item => !categoryKeyword.value.trim() || item.title.toLowerCase().includes(categoryKeyword.value.trim().toLowerCase())).map(item => ({ key: item.key, title: `${item.title} (${item.count})` })))
  const elementCategoryCount = computed(() => categoryList.value.filter(item => item.key !== '__all__').length)
  const checks = useElementChecks({ scope, pageId: () => currentPageId.value, environment: () => liveId(userStore.selected_environment), owner: () => JSON.stringify([userStore.userId, userStore.roleId, userStore.selected_environment]), pageUrl: () => pageRecord.value?.url || '', rows: () => elementRows.value,
    liveVisible: () => liveWorkbenchVisible.value, workbench: () => liveWorkbenchRef.value,
    variables: record => deepCheckVariablesDialogRef.value?.open(record) ?? Promise.resolve(null),
    applyRuntime: result => elementEditPanelRef.value?.applyRuntimeResult(result), refresh: refreshAll,
  })
  const elementCheckLoading = checks.busy
  const elementCheck = checks.result, deepCheckApplyLoading = checks.applying, deepCheckApplied = checks.applied
  const aiLoadingKey = ref('')
  async function loadMetadata() {
    const current = scope.capture(), request = ++metadataSequence
    if (!current()) return
    metadataLoading.value = true; metadataError.value = ''
    const outcomes = await Promise.allSettled([useSelectValue.getSelectValue(), enumStore.getEnum()])
    if (!current() || request !== metadataSequence) return
    metadataLoading.value = false
    if (outcomes.some(result => result.status === 'rejected')) (reportLoadError(undefined, "元素操作或枚举加载失败，请重试", false), (reportLoadError(undefined, "元素操作或枚举加载失败，请重试", false), metadataError.value = '元素操作或枚举加载失败，请重试'))
  }
  async function initialize() {
    if (!scope.available()) return
    const current = scope.capture()
    void loadMetadata(); void resources.loadPage(); void loadCategories()
    if (current()) await doRefresh()
  }
  async function doRefresh() {
    const current = scope.capture(), success = await resources.loadList()
    if (success && current() && !checks.busy.value) await checks.recover()
    return success
  }
  async function loadCategories() {
    const current = scope.capture()
    const success = await resources.loadCategories()
    if (success && current() && activeCategory.value !== '__all__' && !categoryList.value.some(item => item.key === activeCategory.value)) {
      selectedCategoryKeys.value = ['__all__']; pagination.page = 1; await doRefresh()
    }
    return success
  }
  async function refreshAll() {
    const current = scope.capture()
    if (!current()) return
    await Promise.allSettled([loadCategories(), doRefresh()])
    if (current()) await liveWorkbenchRef.value?.refreshElements()
  }
  function onSelectionChange(keys: LiveId[]) { selectedRowKeys.value = keys.filter(key => elementRows.value.some(row => String(row.id) === String(key))) }
  function onCategorySelect(keys: string[]) { confirmation?.close(); confirmation = null; selectedCategoryKeys.value = [keys[0] || '__all__']; pagination.page = 1; void doRefresh() }
  function editorReady() { if (!pageRecord.value || pageLoading.value || metadataLoading.value || metadataError.value) { actionError.value = '页面信息或元素操作尚未加载完成，请稍后重试'; return false }; return scope.available() }
  function doAppend() { if (editorReady() && currentPageId.value !== null) elementEditPanelRef.value?.openCreate(currentPageId.value, activeCategoryName.value) }
  function onUpdate(record: ElementRow) { if (editorReady()) void elementEditPanelRef.value?.openEdit(record) }
  function doResetSearch() { if (props.embedded) emit('close'); else window.history.back() }
  function onDelete(record: ElementRow | null) {
    if (!scope.available() || deleting.value || confirmation) return
    const current = scope.capture(), ids = record ? [record.id] : [...selectedRowKeys.value], category = activeCategory.value
    if (!ids.length) return Message.warning('请选择要删除的数据')
    actionError.value = ''
    confirmation = Modal.confirm({ title: '提示', content: `是否删除选中的 ${ids.length} 个元素？`, cancelText: '取消', okText: '删除',
      async onBeforeOk() {
        if (!current() || deleting.value || category !== activeCategory.value) return false
        deleting.value = true; deletingIds.value = ids.map(String)
        try {
          const response: unknown = await deleteUiElement(record ? ids[0] : [...ids]); elementResponse(response)
          if (!current()) return false
          elementRows.value = elementRows.value.filter(row => !deletingIds.value.includes(String(row.id)))
          selectedRowKeys.value = selectedRowKeys.value.filter(id => !deletingIds.value.includes(String(id)))
          Message.success('删除成功'); await refreshAll(); return true
        } catch (error) { if (current()) actionError.value = liveError(error, '删除失败，请重试'); return false }
        finally { deleting.value = false; deletingIds.value = [] }
      },
      onClose() { confirmation = null },
    })
  }
  async function onAiInfo(record: ElementRow) {
    if (!scope.available() || aiLoadingKey.value) return
    aiLoadingKey.value = String(record.id)
    try { await aiHealPanelRef.value?.open(record) }
    finally { aiLoadingKey.value = '' }
  }
  async function onCheck(record: unknown, mode: 'normal' | 'deep' = 'deep') { return checks.start(record, mode) }
  const applyDeepCheckUpdates = checks.apply
  const handleWorkbenchElementCheckStarted = checks.workbenchStarted
  const handleWorkbenchElementCheckResult = checks.workbenchResult
  const handleWorkbenchElementCheckFinished = checks.workbenchFinished
  const handleElementSaved = refreshAll, handleWorkbenchElementSaved = refreshAll
  function getElementExpName(value: unknown) { return enumStore.element_exp.find(item => String(item.key) === String(value))?.title || '-' }
  async function openElementPageBrowser() {
    const current = scope.capture(), pageId = currentPageId.value, environment = liveId(userStore.selected_environment)
    if (!current() || browserOpening.value || pageId === null || environment === null || !isWebClient.value) return
    browserOpening.value = true; actionError.value = ''
    try { const response: unknown = await postUiElementOpenBrowser({ page_id: pageId, test_env: environment }); elementResponse(response); if (current()) Message.success('已通知执行器打开目标页面') }
    catch (reason) { if (current()) actionError.value = liveError(reason, '打开浏览器失败，请重试') }
    finally { browserOpening.value = false }
  }
  onMounted(() => void initialize())
</script>
<style scoped>
  .mango-detail-workbench-page {
    --ui-element-panel-gap: var(--m-page-gap);
  }
  .mango-detail-workbench-page :deep(.mango-table-body__content) {
    display: flex;
    flex-direction: column;
    gap: var(--m-page-gap);
  }

  .mango-ui-element-page--table-only :deep(.mango-table-body__content) {
    display: flex;
    flex-direction: column;
    overflow-y: hidden;
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
    flex: 1;
    height: auto;
    min-height: 0;
    margin-top: 0;
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
  .mango-ui-element-category-tree :deep(> .mango-panel-spin__content) { min-height: 100%; }

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
    height: min(760px, calc(100vh - 128px));
    min-height: 0;
    flex: 0 0 auto;
    margin-top: 0;
    flex-direction: column;
    overflow: hidden;
  }
  .mango-detail-workbench-page:not(.mango-ui-element-page--table-only) .mango-ui-element-workbench-scroll {
    flex: 0 0 clamp(320px, 55vh, 640px);
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

  .mango-element-page-error { padding: var(--m-page-gap); color: var(--m-danger); }
</style>
