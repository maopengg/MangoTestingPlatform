<template>
  <TableBody ref="tableBody" plain :embedded="props.embedded" :show-embedded-header="props.embedded" class="mango-detail-workbench-page">
    <template #header>
      <TableHeader title="测试用例">
        <template #header-extra>
          <div class="mango-pytest-title-extra">
            <div class="mango-pytest-title-scope" :title="currentScopeTitle">
              <span>{{ currentProjectProductLabel }}</span>
              <span class="mango-pytest-title-scope__separator">/</span>
              <span>{{ currentModuleLabel }}</span>
              <span class="mango-pytest-title-scope__separator">/</span>
              <strong>{{ currentDirectoryLabel }}</strong>
            </div>
            <a-button
              type="primary"
              size="small"
              @click="openUpdateModal"
              data-testid="qa-views-pytest-case-button-更新目录"
            >
              更新目录
            </a-button>
          </div>
        </template>
      </TableHeader>
    </template>
    <template #default>
      <ProjectProductNavigationWorkbench
        contained-body
        show-modules
        product-source="pytest"
        data-navigation-layout="explorer"
        :model-value="getConditionValue('project_product')"
        :module-value="getConditionValue('module')"
        :reset-key="sidebarResetKey"
        emit-initial-filter
        @filter-change="onSidebarFilterChange"
        @search="onSearchRefresh"
        @reset-search="onResetSearch"
      >
        <template #search>
          <a-form :model="{}" layout="inline" @keyup.enter="onSearchRefresh">
            <a-form-item v-for="item of headerConditionItems" :key="item.key" :label="item.label">
              <a-input v-if="item.type === 'input'" v-model="item.value" :placeholder="item.placeholder"
                allow-clear @clear="onSearchRefresh" />
              <a-select v-else-if="item.type === 'select'" v-model="item.value" :multiple="item.multiple"
                :max-tag-count="item.multiple ? 1 : undefined" :options="searchOptions(item.key)"
                :field-names="fieldNames" :placeholder="item.placeholder" :loading="item.key === 'case_people' && userLoading" allow-clear allow-search
                @change="onSearchRefresh" />
            </a-form-item>
            <a-button v-if="userFailed" type="text" size="small" :loading="userLoading" @click="loadUsers">重试</a-button>
          </a-form>
        </template>
        <div class="mango-pytest-file-workbench">
          <aside class="mango-pytest-file-workbench__directory mango-soft-panel">
            <template v-if="directoryFailed"></template>
            <PytestCaseDirectoryTree v-else
              :data="directoryTree"
              :loading="directoryTreeLoading"
              :selected-key="selectedExplorerFileNode?.key || ''"
              @select="onDirectorySelect"
            >
              <template #actions>
                <a-button
                  v-if="canBatchEditCases"
                  type="text"
                  size="mini"
                  @click.stop="openBatchEditor"
                >
                  批量编辑
                </a-button>
              </template>
            </PytestCaseDirectoryTree>
          </aside>
          <section class="mango-pytest-source-panel">
            <a-button v-if="metadataLoading" type="text" size="small" loading disabled>加载用例信息</a-button>
            
            <div v-if="selectedExplorerRecord" class="mango-pytest-source-panel__header">
              <div class="mango-pytest-source-panel__identity">
                <div class="mango-pytest-source-panel__title-row">
                  <strong :title="selectedExplorerRecord.name">{{ selectedExplorerRecord.name }}</strong>
                  <a-space size="mini">
                    <a-tag
                      class="mango-pytest-module-tag"
                      :color="selectedExplorerRecord.module ? 'arcoblue' : 'orangered'"
                      size="small"
                    >
                      模块：{{ selectedModuleLabel }}
                    </a-tag>
                    <a-tag
                      :color="enumStore.colors[selectedExplorerRecord.file_status]"
                      size="small"
                    >
                      绑定：{{
                        getEnumTitle(enumStore.file_status, selectedExplorerRecord.file_status)
                      }}
                    </a-tag>
                    <a-tag :color="sourceStatusColor" size="small">
                      源码：{{
                        getEnumTitle(
                          enumStore.pytest_source_status,
                          selectedExplorerRecord.source_status
                        )
                      }}
                    </a-tag>
                    <a-tag
                      :color="enumStore.status_colors[selectedExplorerRecord.status]"
                      size="small"
                    >
                      结果：{{ enumStore.task_status[selectedExplorerRecord.status]?.title || '-' }}
                    </a-tag>
                    <a-tag :color="selectedExplorerRecord.publication_status === 'published' ? 'green' : selectedExplorerRecord.publication_status === 'prepublished' ? 'orange' : 'gray'" size="small">
                      {{ getEnumTitle(enumStore.pytest_case_publication_status, selectedExplorerRecord.publication_status) }}
                    </a-tag>
                    <a-tag :color="assetStatusColor" size="small">
                      资产：{{
                        getEnumTitle(
                          enumStore.pytest_asset_status,
                          selectedExplorerRecord.asset_status
                        )
                      }}
                    </a-tag>
                  </a-space>
                </div>
                <span :title="selectedExplorerRecord.file_path">{{ selectedExplorerRecord.file_path }}</span>
              </div>
              <a-space class="mango-pytest-source-panel__actions" size="small" wrap>
                <a-button
                  size="small"
                  status="success"
                  :loading="caseRunning"
                  :disabled="!selectedCaseExecutable || metadataLoading || metadataFailed"
                  @click="onRun(selectedExplorerRecord)"
                >
                  执行文件
                </a-button>
                <a-button  size="small" @click="onUpdate(selectedExplorerRecord)">编辑</a-button>
                <a-button  size="small" @click="onResult(selectedExplorerRecord)">执行结果</a-button>
                <a-dropdown trigger="click">
                  <a-button size="small" :loading="publicationActionCaseId === selectedExplorerRecord.id || deleteCaseId === selectedExplorerRecord.id">更多</a-button>
                  <template #content>
                    <a-doption
                      :disabled="!selectedSourceAvailable"
                      @click="onClick(selectedExplorerRecord)"
                    >
                      编辑代码
                    </a-doption>
                    <a-doption
                      v-if="selectedExplorerRecord.publication_status === 'unpublished'"
                      :disabled="mutationBusy || !selectedSourceAvailable"
                      @click="onPublicationChange(selectedExplorerRecord, 'prepublished')"
                    >提交预发布</a-doption>
                    <a-doption
                      v-if="selectedExplorerRecord.publication_status === 'prepublished'"
                      :disabled="mutationBusy || !selectedSourceAvailable"
                      @click="onPublicationChange(selectedExplorerRecord, 'published')"
                    >通过发布</a-doption>
                    <a-doption
                      v-if="selectedExplorerRecord.publication_status !== 'unpublished'"
                      class="mango-pytest-danger-option" :disabled="mutationBusy"
                      @click="onPublicationChange(selectedExplorerRecord, 'unpublished')"
                    >退回未发布</a-doption>
                    <a-doption
                      class="mango-pytest-danger-option" :disabled="mutationBusy"
                      @click="onDelete(selectedExplorerRecord)"
                    >
                      删除平台资产
                    </a-doption>
                  </template>
                </a-dropdown>
              </a-space>
            </div>
            <a-alert
              v-if="selectedExplorerRecord && !selectedSourceAvailable"
              class="mango-pytest-source-panel__notice"
              type="warning"
              :show-icon="true"
            >
              当前源码不可用，平台仍保留模块、场景、负责人、发布配置和历史执行结果。
              <template v-if="selectedExplorerRecord.missing_since">
                缺失时间：{{ selectedExplorerRecord.missing_since }}。
              </template>
              更新目录后若文件恢复，将自动重新关联到该资产。
            </a-alert>
            <div v-if="selectedExplorerRecord" class="mango-pytest-case-metadata">
              <div class="mango-pytest-case-metadata__properties">
                <div class="mango-pytest-case-metadata__item">
                  <span>优先级</span>
                  <a-tag :color="enumStore.colors[selectedExplorerRecord.level]" size="small">
                    {{ getEnumTitle(enumStore.case_level, selectedExplorerRecord.level) }}
                  </a-tag>
                </div>
                <div class="mango-pytest-case-metadata__item">
                  <span>测试层级</span>
                  <a-tag
                    :color="enumStore.colors[selectedExplorerRecord.scenario_layer]"
                    size="small"
                  >
                    {{
                      getEnumTitle(
                        enumStore.api_case_scenario_layer,
                        selectedExplorerRecord.scenario_layer
                      )
                    }}
                  </a-tag>
                </div>
                <div class="mango-pytest-case-metadata__item">
                  <span>验证类型</span>
                  <a-tag
                    :color="enumStore.colors[selectedExplorerRecord.scenario_type]"
                    size="small"
                  >
                    {{
                      getEnumTitle(
                        enumStore.api_case_scenario_type,
                        selectedExplorerRecord.scenario_type
                      )
                    }}
                  </a-tag>
                </div>
                <div
                  class="mango-pytest-case-metadata__item mango-pytest-case-metadata__item--tags"
                >
                  <span>执行场景</span>
                  <a-space v-if="selectedScenarioTags.length" size="mini" wrap>
                    <a-tag
                      v-for="tag in selectedScenarioTags"
                      :key="tag"
                      :color="enumStore.colors[tag]"
                      size="small"
                    >
                      {{ getEnumTitle(enumStore.api_case_scenario_tag, tag) }}
                    </a-tag>
                  </a-space>
                  <span v-else class="mango-pytest-case-metadata__empty">-</span>
                </div>
              </div>
              <div
                v-if="explorerHasFeature"
                class="mango-pytest-file-switch mango-pytest-file-switch--inline"
              >
                <span>文件视图</span>
                <a-radio-group
                  v-model="explorerFileType"
                  type="button"
                  size="small"
                  @change="onExplorerFileTypeChange"
                >
                  <a-radio value="py">Python</a-radio>
                  <a-radio value="feature">Feature</a-radio>
                </a-radio-group>
              </div>
            </div>
            <a-button v-if="methodsLoading" type="text" size="small" loading disabled>加载方法</a-button>
            <a-button v-else-if="methodsFailed" type="text" size="small" @click="source.loadMethods">重试</a-button>
            <a-button v-if="sourceFiles.feature.loading" type="text" size="small" loading disabled>检查 Feature 文件</a-button>
            <a-button v-else-if="sourceFiles.feature.failed" type="text" size="small" @click="source.loadFile('feature')">重试</a-button>
            
            <mango-panel-spin :loading="explorerSourceLoading" class="mango-pytest-source-panel__body">
              <CodeEditor
                v-if="selectedExplorerFileNode && currentFile.snapshot && !currentFile.failed"
                :model-value="explorerCodeText"
                :code-style="{ height: '100%' }"
                :line-actions="explorerFileType === 'py' ? methodLineActions : []"
                readonly
                placeholder="请选择左侧测试文件"
                @line-action="onRunMethod"
              />
              <div v-else-if="!explorerSourceLoading && !currentFile.failed" class="mango-empty-state">
                请选择目录树中的 Python 文件查看源码
              </div>
            </mango-panel-spin>
          </section>
        </div>
        <PytestCaseCodeDrawer
          ref="codeDrawerRef"
          :context-key="String(props.caseId ?? '')"
          @saved="onCodeSaved"
          @started="onCodeMethodStarted"
        />
        <ExecutionResultHistoryDrawer
          v-model:visible="resultHistoryVisible"
          :title="`Pytest 执行历史：${resultHistoryRecord?.name || '-'}`"
          description="查看历次执行记录、本次执行包含的 Case 及完整结果详情"
          :query="resultHistoryQuery"
        >
          <template #result="{ detail, errorMessage }">
            <PytestExecutionResultDetail :detail="detail" :error-message="errorMessage" />
          </template>
        </ExecutionResultHistoryDrawer>
      </ProjectProductNavigationWorkbench>
    </template>
  </TableBody>
  <CasePublicationReviewModal ref="publicationReviewRef" @published="reviewPublished" />
  <PytestCaseBatchEditor
    v-model:visible="batchEditorVisible"
    :scopes="batchEditorScopes"
    :initial-scope-key="batchEditorInitialScopeKey"
    :user-options="userOptions"
    :current-user-id="userStore.userId"
    @saved="onBatchEditorSaved"
  />
  <PytestCaseSyncDialog ref="syncDialogRef" @synced="onDirectorySynced" />
  <PytestCaseEditor ref="caseEditorRef" @saved="onMetadataSaved" />
</template>

<script lang="ts" setup>
import { reportLoadError } from '@/utils/load-error'

  import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, shallowRef, watch } from 'vue'
  import { useRoute } from 'vue-router'
  import { Message, Modal } from '@arco-design/web-vue'
  import { usePagePolling, isPendingExecution, type PollingContext } from '@/hooks/use-page-polling'
  import { getPytestCase, getPytestCaseDirectoryTree, getPytestCaseTest, deletePytestCase, putPytestCasePublication } from '@/api/pytest/case'
  import { getUserName } from '@/api/user/user'
  import { fieldNames } from '@/setting'
  import { useEnum } from '@/store/modules/get-enum'
  import { useProject } from '@/store/modules/get-project'
  import useUserStore from '@/store/modules/user'
  import type { ProductModuleOption } from '@/store/modules/project-options'
  import CodeEditor from '@/components/editors/CodeEditor.vue'
  import CasePublicationReviewModal from '@/components/business/CasePublicationReviewModal.vue'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import { flattenProjectProducts } from '@/components/business/project-product-filter'
  import ExecutionResultHistoryDrawer from '@/components/business/ExecutionResultHistoryDrawer.vue'
  import { formatModulePath } from '@/utils/business-format'
  import PytestCaseDirectoryTree from './components/PytestCaseDirectoryTree.vue'
  import PytestExecutionResultDetail from './components/PytestExecutionResultDetail.vue'
  import PytestCaseBatchEditor from './components/PytestCaseBatchEditor.vue'
  import PytestCaseEditor from './components/PytestCaseEditor.vue'
  import PytestCaseSyncDialog from './components/PytestCaseSyncDialog.vue'
  import PytestCaseCodeDrawer from './components/PytestCaseCodeDrawer.vue'
  import { createSearchItems, resetSearchItems, searchQuery } from './config'
  import type { CaseQuery } from './config'
  import { batchSuccess } from './batch-editor'
  import type { BatchOptionId, BatchScope, BatchUserOption } from './batch-editor'
  import { caseUsers, directoryCaseIds, enumTitle as getEnumTitle, findFile, firstFile, optionalCaseId, projectNodes, readCase, readDirectory, readPublication } from './records'
  import type { CaseRecord, DirectoryNode } from './records'
  import { codeTarget, executionEnvironment, methodTarget } from './source'
  import { useCaseSource } from './composables/use-case-source'

  const props = defineProps<{ caseId?: string | number; embedded?: boolean }>()
  const route = useRoute(), userStore = useUserStore(), projectInfo = useProject(), enumStore = useEnum()
  const mountedPath = route.path
  const codeDrawerRef = ref<InstanceType<typeof PytestCaseCodeDrawer> | null>(null)
  const caseEditorRef = ref<InstanceType<typeof PytestCaseEditor> | null>(null)
  const publicationReviewRef = ref<InstanceType<typeof CasePublicationReviewModal> | null>(null)
  const syncDialogRef = ref<InstanceType<typeof PytestCaseSyncDialog> | null>(null)
  const conditionItems = createSearchItems(), headerConditionItems = conditionItems
  const sidebarProjectProductId = ref<BatchOptionId | null>(null), sidebarSelectedModuleId = ref<BatchOptionId | null>(null), sidebarModuleIds = ref<BatchOptionId[]>([]), sidebarResetKey = ref(0)
  const directoryTree = ref<DirectoryNode[]>([]), directoryTreeLoading = ref(false), directoryFailed = ref(false)
  const userOptions = ref<BatchUserOption[]>([]), userLoading = ref(false), userFailed = ref(false)
  const pageVersion = ref(0), linkedCaseId = ref(optionalCaseId(props.caseId ?? route.query.id))
  const resultHistoryVisible = ref(false), resultHistoryRecord = ref<Pick<CaseRecord, 'id' | 'name'> | null>(null)
  const batchEditorVisible = ref(false), batchEditorScopes = ref<BatchScope[]>([]), batchEditorInitialScopeKey = ref('')
  const mutationBusy = ref(false), publicationActionCaseId = ref<number | null>(null), deleteCaseId = ref<number | null>(null), running = ref(new Set<string>())
  let active = true, mounted = false, disposed = false, needsReload = false, initialFileSelectionPending = true
  let directoryRequest = 0, userRequest = 0, confirmationVersion = 0, recordRevision = 0
  let directoryRead: { key: string; current: () => boolean; promise: Promise<boolean> } | null = null
  let userRead: { current: () => boolean; promise: Promise<boolean> } | null = null
  let confirmation: ReturnType<typeof Modal.confirm> | null = null
  const available = () => mounted && active && !disposed && route.path === mountedPath && (typeof document === 'undefined' || !document.hidden)
  const current = (version: number) => available() && pageVersion.value === version
  const source = useCaseSource({ available, version: () => pageVersion.value, loaded: row => {
    recordRevision++
    if (isPendingExecution(row)) startPollingCaseState(row.id)
    else if (pollingCaseId.value === row.id) clearPollingTimer()
  } })
  const { record: selectedExplorerRecord, selectedFile: selectedExplorerFileNode, metadataLoading, metadataFailed, files: sourceFiles, currentFile, fileType: explorerFileType,
    hasFeature: explorerHasFeature, text: explorerCodeText, nodes: sourceMethods, methodsLoading, methodsFailed } = source
  const explorerSourceLoading = computed(() => currentFile.value.loading)
  const selectedModuleLabel = computed(() => selectedExplorerRecord.value?.module ? formatModulePath(selectedExplorerRecord.value.module) : '未绑定')
  const selectedScenarioTags = computed(() => selectedExplorerRecord.value?.scenario_tags ?? [])
  const selectedSourceAvailable = computed(() => !!selectedExplorerRecord.value && ![2, 3, 4].includes(selectedExplorerRecord.value.source_status))
  const selectedCaseExecutable = computed(() => !!selectedExplorerRecord.value && codeTarget(selectedExplorerRecord.value).executable)
  const sourceStatusColor = computed(() => selectedExplorerRecord.value?.source_status === 1 ? 'orange' : selectedSourceAvailable.value ? 'green' : 'red')
  const assetStatusColor = computed(() => Number(selectedExplorerRecord.value?.asset_status) === 1 ? 'green' : [2, 3, 4].includes(Number(selectedExplorerRecord.value?.asset_status)) ? 'gray' : 'arcoblue')
  const currentProjectProductLabel = computed(() => sidebarProjectProductId.value === null ? '全部项目' : flattenProjectProducts(projectInfo.projectProduct).find(item => String(item.projectProductId) === String(sidebarProjectProductId.value))?.title || `产品 ${sidebarProjectProductId.value}`)
  function findModuleLabel(nodes: ProductModuleOption[], id: BatchOptionId): string | null {
    for (const node of nodes) { if (String(node.key) === String(id)) return node.title; const child = findModuleLabel(node.children || [], id); if (child) return child }
    return null
  }
  const currentModuleLabel = computed(() => sidebarSelectedModuleId.value === null ? '全部模块' : findModuleLabel(projectInfo.allProductModuleTreeCache.data, sidebarSelectedModuleId.value) || `模块 ${sidebarSelectedModuleId.value}`)
  const currentDirectoryLabel = computed(() => selectedExplorerFileNode.value?.breadcrumb.join(' / ') || '全部目录')
  const currentScopeTitle = computed(() => `${currentProjectProductLabel.value} / ${currentModuleLabel.value} / ${currentDirectoryLabel.value}`)
  const resultHistoryQuery = computed(() => resultHistoryRecord.value ? { target_type: 'pytest_case', target_id: resultHistoryRecord.value.id } : undefined)
  const reviewPublished = shallowRef<() => void>(() => { onMetadataSaved() })
  function getConditionValue(key: string): BatchOptionId | null { return key === 'project_product' ? sidebarProjectProductId.value : sidebarSelectedModuleId.value }
  function searchOptions(key: string) {
    if (key === 'publication_status') return enumStore.pytest_case_publication_status
    if (key === 'status') return enumStore.task_status
    if (key === 'level') return enumStore.case_level
    if (key === 'case_people') return userOptions.value
    return key === 'source_status' ? enumStore.pytest_source_status : enumStore.pytest_asset_status
  }
  function buildCaseSearchParams(): CaseQuery {
    return { ...searchQuery(conditionItems), ...(sidebarProjectProductId.value === null ? {} : { project_product_id: sidebarProjectProductId.value }), ...(sidebarModuleIds.value.length ? { module_ids: sidebarModuleIds.value.join(',') } : {}) }
  }
  function closeConfirmation(): void { confirmationVersion++; confirmation?.close(); confirmation = null }
  function closeWindows(): void {
    closeConfirmation(); codeDrawerRef.value?.close(); caseEditorRef.value?.close(); syncDialogRef.value?.close(); publicationReviewRef.value?.invalidate()
    batchEditorVisible.value = false; batchEditorScopes.value = []; resultHistoryVisible.value = false; resultHistoryRecord.value = null
  }
  function invalidate(clear: boolean): void {
    pageVersion.value++; directoryRequest++; userRequest++; directoryRead = null; userRead = null
    directoryTreeLoading.value = false; userLoading.value = false; closeWindows(); source.invalidate(clear)
    const epoch = pageVersion.value
    reviewPublished.value = () => { if (current(epoch)) onMetadataSaved() }
    if (clear) { directoryTree.value = []; directoryFailed.value = false; userOptions.value = []; userFailed.value = false }
  }
  function loadDirectoryTree(preferredCaseId: number | null = null, reloadSource = true): Promise<boolean> {
    if (!available()) { needsReload = true; return Promise.resolve(false) }
    const query = buildCaseSearchParams(), key = JSON.stringify([query, preferredCaseId, reloadSource])
    if (directoryRead?.key === key && directoryRead.current()) return directoryRead.promise
    const epoch = pageVersion.value, request = ++directoryRequest
    const isCurrent = () => current(epoch) && directoryRequest === request
    const job = { key, current: isCurrent, promise: Promise.resolve(false) }
    directoryRead = job; directoryTreeLoading.value = true; directoryFailed.value = false
    job.promise = Promise.resolve().then(async () => {
      try {
        if (!isCurrent()) return false
        const next = readDirectory(await getPytestCaseDirectoryTree(query))
        if (!isCurrent()) return false
        directoryTree.value = next
        const selectedId = preferredCaseId ?? selectedExplorerFileNode.value?.case_id ?? linkedCaseId.value
        const file = selectedId ? findFile(next, selectedId) : initialFileSelectionPending ? firstFile(next) : null
        if (!file) { source.invalidate(); clearPollingTimer(); return true }
        initialFileSelectionPending = false
        if (file.case_id === linkedCaseId.value) linkedCaseId.value = null
        if (reloadSource || selectedExplorerFileNode.value?.case_id !== file.case_id) { clearPollingTimer(); void source.select(file) }
        else { selectedExplorerFileNode.value = file; void source.loadMetadata() }
        return true
      } catch (loadFailure0) { if (isCurrent()) (reportLoadError(loadFailure0, "加载失败，请重试", false), directoryFailed.value = true); return false }
      finally { if (directoryRead === job) { directoryRead = null; directoryTreeLoading.value = false } }
    })
    return job.promise
  }
  function loadUsers(): Promise<boolean> {
    if (!available()) return Promise.resolve(false)
    if (userRead?.current()) return userRead.promise
    const epoch = pageVersion.value, request = ++userRequest, isCurrent = () => current(epoch) && userRequest === request
    const job = { current: isCurrent, promise: Promise.resolve(false) }
    userRead = job; userLoading.value = true; userFailed.value = false
    job.promise = Promise.resolve().then(async () => {
      try { if (!isCurrent()) return false; const next = caseUsers(await getUserName()); if (!isCurrent()) return false; userOptions.value = next; return true }
      catch (loadFailure1) { if (isCurrent()) (reportLoadError(loadFailure1, "加载失败，请重试", false), userFailed.value = true); return false }
      finally { if (userRead === job) { userRead = null; userLoading.value = false } }
    })
    return job.promise
  }
  function onSearchRefresh(): void { clearPollingTimer(); invalidate(true); initialFileSelectionPending = true; void loadDirectoryTree(); void loadUsers() }
  function onResetSearch(): void { resetSearchItems(conditionItems); sidebarProjectProductId.value = null; sidebarSelectedModuleId.value = null; sidebarModuleIds.value = []; sidebarResetKey.value++; onSearchRefresh() }
  function onSidebarFilterChange(filter: { projectProduct: BatchOptionId | null; module: BatchOptionId | null; moduleIds?: BatchOptionId[]; selectedModuleId?: BatchOptionId | null }): void {
    sidebarProjectProductId.value = filter.projectProduct; sidebarSelectedModuleId.value = filter.selectedModuleId ?? filter.module; sidebarModuleIds.value = [...(filter.moduleIds || [])]; onSearchRefresh()
  }
  function onDirectorySelect(node: DirectoryNode | null): void {
    if (!node || node.type !== 'file' || !available()) return
    clearPollingTimer(); invalidate(false); void source.select(node); void loadUsers()
  }
  function onExplorerFileTypeChange(value: unknown): void { if (value === 'py' || value === 'feature') explorerFileType.value = value }
  const scopes = computed<BatchScope[]>(() => projectNodes(directoryTree.value).map(node => {
    const caseIds = [...new Set(directoryCaseIds(node))]
    return { key: node.key, label: [currentProjectProductLabel.value, currentModuleLabel.value, ...node.breadcrumb].join(' / '), caseIds, disabled: !caseIds.length || caseIds.length > 500 }
  }))
  const canBatchEditCases = computed(() => scopes.value.some(scope => !scope.disabled))
  function openBatchEditor(): void {
    if (!available()) return
    const id = selectedExplorerFileNode.value?.case_id, project = projectNodes(directoryTree.value).find(node => id == null || directoryCaseIds(node).includes(id))
    const selected = scopes.value.find(scope => scope.key === project?.key)
    if (!selected || selected.disabled) { Message.warning('请选择包含 1-500 条 Case 的项目范围'); return }
    batchEditorScopes.value = scopes.value.map(scope => ({ ...scope, caseIds: [...scope.caseIds] })); batchEditorInitialScopeKey.value = selected.key; batchEditorVisible.value = true
  }
  function onBatchEditorSaved(): void { if (available()) { recordRevision++; source.invalidateMetadata(); void loadDirectoryTree(null, false) } }
  function onMetadataSaved(): void { if (available()) { recordRevision++; source.invalidateMetadata(); void loadDirectoryTree(null, false) } }
  function onDirectorySynced(): void { if (available()) { initialFileSelectionPending = true; void loadDirectoryTree() } }
  function openUpdateModal(): void { if (available()) syncDialogRef.value?.open() }
  function onUpdate(record: CaseRecord): void { if (available()) caseEditorRef.value?.open(record) }
  function onClick(record: CaseRecord): void { if (available()) codeDrawerRef.value?.open(record) }
  function onCodeSaved(caseId: number): void { const node = selectedExplorerFileNode.value; if (available() && node?.case_id === caseId) { clearPollingTimer(); void source.select(node) } }
  function onCodeMethodStarted(caseId: number): void { if (available() && selectedExplorerRecord.value?.id === caseId) startPollingCaseState(caseId) }
  function onResult(record: CaseRecord): void { if (available()) { resultHistoryRecord.value = { id: record.id, name: record.name }; resultHistoryVisible.value = true } }

  const pollingCaseId = ref<number | null>(null)
  let pollingGeneration = 0
  let pollingRead: { current: () => boolean; promise: Promise<CaseRecord | undefined> } | null = null
  const pagePolling = usePagePolling(context => { const id = pollingCaseId.value; if (id) return pollSelectedCaseState(id, context) })
  function clearPollingTimer(): void { pollingGeneration++; pagePolling.stop(); pollingCaseId.value = null; pollingRead = null }
  function startPollingCaseState(id: number): void { if (!available() || selectedExplorerRecord.value?.id !== id) return; clearPollingTimer(); pollingCaseId.value = id; pagePolling.start() }
  function refreshSelectedCaseState(caseId: number, context?: PollingContext): Promise<CaseRecord | undefined> {
    if (!available()) return Promise.resolve(undefined)
    if (pollingRead?.current()) return pollingRead.promise
    const epoch = pageVersion.value, node = selectedExplorerFileNode.value, generation = pollingGeneration, revision = recordRevision
    const isCurrent = () => current(epoch) && generation === pollingGeneration && revision === recordRevision && node === selectedExplorerFileNode.value && selectedExplorerRecord.value?.id === caseId && (!context || context.isCurrent())
    const job = { current: isCurrent, promise: Promise.resolve<CaseRecord | undefined>(undefined) }
    pollingRead = job
    job.promise = Promise.resolve().then(async () => {
      try { if (!isCurrent()) return undefined; const next = readCase(await getPytestCase({ id: caseId, page: 1, pageSize: 1 }), caseId); if (!isCurrent()) return undefined; selectedExplorerRecord.value = next; return next }
      finally { if (pollingRead === job) pollingRead = null }
    })
    return job.promise
  }
  async function pollSelectedCaseState(id: number, context?: PollingContext): Promise<void> {
    try { const record = await refreshSelectedCaseState(id, context); if (record && pollingCaseId.value === id && !isPendingExecution(record)) clearPollingTimer() }
    catch { /* 失败保留轮询，由公共 5 秒周期重试。 */ }
  }
  const executionStartedMessage = '准备开始执行，执行完成之后，请在右侧按钮结果中查看执行结果~'
  const runKey = (id: number, env: number, node = '') => JSON.stringify([id, env, node])
  const caseRunning = computed(() => !!selectedExplorerRecord.value && running.value.has(runKey(selectedExplorerRecord.value.id, Number(userStore.selected_environment))))
  const methodLineActions = computed(() => sourceMethods.value.filter(node => node.line_number !== null).map(node => ({ id: node.nodeid, line: node.line_number!, label: `执行 ${node.class_name ? node.class_name + '.' : ''}${node.method_name}`,
    loading: !!selectedExplorerRecord.value && running.value.has(runKey(selectedExplorerRecord.value.id, Number(userStore.selected_environment), node.nodeid)), disabled: !selectedCaseExecutable.value || metadataLoading.value || metadataFailed.value || methodsLoading.value || methodsFailed.value || currentFile.value.failed || currentFile.value.loading, payload: node })))
  async function execute(record: CaseRecord, node?: ReturnType<typeof methodTarget>): Promise<boolean> {
    if (!available() || metadataLoading.value || metadataFailed.value || selectedExplorerRecord.value?.id !== record.id || !codeTarget(record).executable) { Message.warning('当前测试文件源码不可用，或资产已停用、归档、忽略，不能执行'); return false }
    let env: number
    try { env = executionEnvironment(userStore.selected_environment) } catch { Message.error('请先选择用例执行的环境'); return false }
    const epoch = pageVersion.value, id = record.id, key = runKey(id, env, node?.nodeid)
    if (running.value.has(key)) return false
    running.value = new Set([...running.value, key])
    try { batchSuccess(await getPytestCaseTest(id, env, node || {})); if (!current(epoch) || selectedExplorerRecord.value?.id !== id) return false; Message.success(executionStartedMessage); startPollingCaseState(id); return true }
    catch { if (current(epoch)) Message.error('执行失败，请重试'); return false }
    finally { const next = new Set(running.value); next.delete(key); running.value = next }
  }
  function onRun(record: CaseRecord): Promise<boolean> { return execute(record) }
  function onRunMethod(value: unknown): Promise<boolean> {
    const id = value != null && typeof value === 'object' && 'nodeid' in value ? value.nodeid : null, node = sourceMethods.value.find(node => node.nodeid === id)
    if (!selectedExplorerRecord.value || !node || methodsLoading.value || methodsFailed.value || !sourceFiles.py.snapshot || sourceFiles.py.failed) return Promise.resolve(false)
    return execute(selectedExplorerRecord.value, methodTarget(node))
  }
  function onDelete(record: CaseRecord): void {
    if (!available() || mutationBusy.value || confirmation) return
    const epoch = pageVersion.value, serial = ++confirmationVersion, id = record.id
    confirmation = Modal.confirm({ title: '提示', content: '该操作会删除平台资产及其配置，但不会删除 Git 源文件。确定继续吗？', cancelText: '取消', okText: '删除', okButtonProps: { status: 'danger' },
      onClose: () => { if (serial === confirmationVersion) confirmation = null },
      onBeforeOk: async () => {
        if (!current(epoch) || serial !== confirmationVersion || mutationBusy.value) return false
        mutationBusy.value = true; deleteCaseId.value = id
        try { batchSuccess(await deletePytestCase(id)); if (!current(epoch)) return false; Message.success('删除成功'); closeConfirmation(); clearPollingTimer(); source.invalidate(); initialFileSelectionPending = true; void loadDirectoryTree(); return true }
        catch { if (current(epoch)) Message.error('删除失败，请重试'); return false }
        finally { mutationBusy.value = false; deleteCaseId.value = null }
      },
    })
  }
  function onPublicationChange(record: CaseRecord, target: 'prepublished' | 'published' | 'unpublished'): void {
    if (!available() || mutationBusy.value || confirmation) return
    if (target === 'published') { if (record.publication_status !== 'prepublished') { Message.warning('只有预发布状态的用例可以进入发布审核'); return }; void publicationReviewRef.value?.open('pytest', [record.id]); return }
    if (target !== 'unpublished' && record.status !== 1) { Message.warning('用例必须执行通过后才能提交预发布或正式发布'); return }
    const epoch = pageVersion.value, serial = ++confirmationVersion, id = record.id, title = target === 'prepublished' ? '提交预发布' : '退回未发布'
    confirmation = Modal.confirm({ title, content: target === 'prepublished' ? '提交后由业务项目产品负责人审核，预发布不参与定时执行。确认提交吗？' : '退回后该用例不再参与定时执行。确认退回吗？', cancelText: '取消', okText: title, okButtonProps: target === 'unpublished' ? { status: 'danger' } : undefined,
      onClose: () => { if (serial === confirmationVersion) confirmation = null },
      onBeforeOk: async () => {
        if (!current(epoch) || serial !== confirmationVersion || mutationBusy.value) return false
        mutationBusy.value = true; publicationActionCaseId.value = id
        try {
          const next = readPublication(await putPytestCasePublication(id, target), id, target)
          if (!current(epoch)) return false
          recordRevision++; source.invalidateMetadata()
          if (selectedExplorerRecord.value?.id === id) Object.assign(selectedExplorerRecord.value, next)
          Message.success('操作成功'); closeConfirmation(); void loadDirectoryTree(null, false); return true
        }
        catch { if (current(epoch)) Message.error('发布状态更新失败，请重试'); return false }
        finally { mutationBusy.value = false; publicationActionCaseId.value = null }
      },
    })
  }
  function resetContext(): void {
    clearPollingTimer(); invalidate(true); resetSearchItems(conditionItems); sidebarProjectProductId.value = null; sidebarSelectedModuleId.value = null; sidebarModuleIds.value = []; sidebarResetKey.value++
    linkedCaseId.value = optionalCaseId(props.caseId ?? route.query.id); initialFileSelectionPending = true; needsReload = true
    if (available()) { needsReload = false; void loadDirectoryTree(); void loadUsers() }
  }
  function pause(): void { if (!mounted || disposed) return; pagePolling.pause(); invalidate(false); needsReload = true }
  function resume(): void { if (!available() || !needsReload) return; needsReload = false; void loadDirectoryTree(selectedExplorerFileNode.value?.case_id ?? null); void loadUsers() }
  function visibilityChanged(): void { if (typeof document !== 'undefined' && document.hidden) pause(); else resume() }
  watch(() => [userStore.userId, userStore.roleId, userStore.token, userStore.selected_environment, route.fullPath, props.caseId], resetContext, { flush: 'sync' })
  onMounted(() => { mounted = true; if (typeof document !== 'undefined') document.addEventListener('visibilitychange', visibilityChanged); if (available()) { void loadDirectoryTree(); void loadUsers() } else needsReload = true })
  onActivated(() => { active = true; resume() })
  onDeactivated(() => { active = false; pause() })
  onBeforeUnmount(() => { disposed = true; clearPollingTimer(); invalidate(true); if (typeof document !== 'undefined') document.removeEventListener('visibilitychange', visibilityChanged) })
</script>
<style lang="less" scoped>

  .mango-pytest-title-extra {
    display: flex;
    min-width: 0;
    align-items: center;
    justify-content: flex-end;
    gap: 8px;
  }

  .mango-pytest-title-scope {
    display: flex;
    min-width: 0;
    max-width: min(760px, 58vw);
    align-items: center;
    gap: 5px;
    overflow: hidden;
    color: var(--m-text-2);
    font-size: 12px;
    white-space: nowrap;
  }

  .mango-pytest-title-scope > span,
  .mango-pytest-title-scope > strong {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .mango-pytest-title-scope > strong {
    color: var(--m-primary);
    font-weight: 500;
  }

  .mango-pytest-title-scope__separator {
    flex: 0 0 auto;
    color: var(--m-border-strong);
  }

  .mango-pytest-title-extra :deep(.arco-btn) {
    flex: 0 0 auto;
  }

  .mango-pytest-file-workbench {
    display: grid;
    height: 100%;
    min-height: 0;
    grid-template-columns: 280px minmax(0, 1fr);
    gap: var(--m-page-gap);
    padding: var(--m-page-gap);
    overflow: hidden;
  }

  .mango-pytest-file-workbench__directory {
    min-width: 0;
    min-height: 0;
    padding: 8px;
    overflow: hidden;
  }

  .mango-pytest-source-panel {
    display: flex;
    min-width: 0;
    min-height: 0;
    flex-direction: column;
    overflow: hidden;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
  }

  .mango-pytest-source-panel__header {
    display: flex;
    min-height: 54px;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    padding: 8px 12px;
    border-bottom: 1px solid var(--m-border);
    background: var(--m-surface-soft);
  }

  .mango-pytest-source-panel__identity {
    min-width: 0;
  }

  .mango-pytest-source-panel__identity > span {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-pytest-source-panel__title-row {
    display: flex;
    min-width: 0;
    align-items: center;
    gap: 8px;
  }

  .mango-pytest-source-panel__title-row > strong {
    min-width: 0;
    overflow: hidden;
    color: var(--m-text);
    font-size: 13px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-pytest-source-panel__identity > span {
    margin-top: 3px;
    color: var(--m-muted);
    font-size: 10px;
  }

  .mango-pytest-source-panel__actions {
    flex: 0 0 auto;
  }

  .mango-pytest-source-panel__notice {
    flex: 0 0 auto;
    margin: 6px 12px 0;
  }

  .mango-pytest-case-metadata {
    display: flex;
    min-height: 38px;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    padding: 5px 12px;
    overflow-x: auto;
    border-bottom: 1px solid var(--m-border);
    background: var(--m-surface);
  }

  .mango-pytest-case-metadata__properties {
    display: flex;
    min-width: max-content;
    align-items: center;
    gap: 18px;
  }

  .mango-pytest-case-metadata__item {
    display: flex;
    flex: 0 0 auto;
    align-items: center;
    gap: 6px;
  }

  .mango-pytest-case-metadata__item > span:first-child {
    color: var(--m-muted);
    font-size: 11px;
    white-space: nowrap;
  }

  .mango-pytest-case-metadata__item--tags {
    min-width: 0;
  }

  .mango-pytest-case-metadata__empty {
    color: var(--m-text-3);
  }

  .mango-pytest-file-switch {
    display: flex;
    min-height: 38px;
    align-items: center;
    gap: 10px;
    padding: 4px 12px;
    border-bottom: 1px solid var(--m-border);
    background: var(--m-surface);
  }

  .mango-pytest-file-switch > span {
    color: var(--m-muted);
    font-size: 11px;
  }

  .mango-pytest-file-switch--inline {
    min-height: 28px;
    flex: 0 0 auto;
    padding: 0;
    border-bottom: 0;
  }

  .mango-pytest-module-tag {
    max-width: 220px;

    :deep(.arco-tag-content) {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  :global(.mango-pytest-danger-option) {
    color: var(--m-danger);
  }

  .mango-pytest-source-panel__body {
    width: 100%;
    min-height: 0;
    flex: 1;
    overflow: hidden;

    :deep(> .mango-panel-spin__content),
    :deep(.code-editor),
    :deep(.cm-editor) {
      height: 100%;
      min-height: 0;
    }

    :deep(.cm-scroller) {
      overflow: auto;
    }
  }
</style>
