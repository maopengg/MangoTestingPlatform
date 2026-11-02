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
                :field-names="fieldNames" :placeholder="item.placeholder" allow-clear allow-search
                @change="onSearchRefresh" />
            </a-form-item>
          </a-form>
        </template>
        <div class="mango-pytest-file-workbench">
          <aside class="mango-pytest-file-workbench__directory mango-soft-panel">
            <PytestCaseDirectoryTree
              :data="directoryTree"
              :loading="directoryTreeLoading"
              :selected-key="selectedExplorerFileNode?.key || ''"
              @directory-toggle="onDirectoryToggle"
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
            <div v-if="selectedExplorerRecord" class="mango-pytest-source-panel__header">
              <div class="mango-pytest-source-panel__identity">
                <div class="mango-pytest-source-panel__title-row">
                  <strong>{{ selectedExplorerRecord.name }}</strong>
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
                <span>{{ selectedExplorerRecord.file_path }}</span>
              </div>
              <a-space class="mango-pytest-source-panel__actions" size="small" wrap>
                <a-button
                  size="small"
                  status="success"
                  :loading="caseRunning"
                  :disabled="!selectedCaseExecutable"
                  @click="onRun(selectedExplorerRecord)"
                >
                  执行文件
                </a-button>
                <a-button  size="small" @click="onUpdate(selectedExplorerRecord)">编辑</a-button>
                <a-button  size="small" @click="onResult(selectedExplorerRecord)">执行结果</a-button>
                <a-dropdown trigger="click">
                  <a-button size="small" :loading="publicationActionCaseId === selectedExplorerRecord.id">更多</a-button>
                  <template #content>
                    <a-doption
                      :disabled="!selectedSourceAvailable"
                      @click="onClick(selectedExplorerRecord)"
                    >
                      编辑代码
                    </a-doption>
                    <a-doption
                      v-if="selectedExplorerRecord.publication_status === 'unpublished'"
                      :disabled="publicationActionCaseId !== null || !selectedSourceAvailable"
                      @click="onPublicationChange(selectedExplorerRecord, 'prepublished')"
                    >提交预发布</a-doption>
                    <a-doption
                      v-if="selectedExplorerRecord.publication_status === 'prepublished' && selectedExplorerRecord.is_product_owner"
                      :disabled="publicationActionCaseId !== null || !selectedSourceAvailable"
                      @click="onPublicationChange(selectedExplorerRecord, 'published')"
                    >通过发布</a-doption>
                    <a-doption
                      v-if="selectedExplorerRecord.publication_status !== 'unpublished' && selectedExplorerRecord.is_product_owner"
                      class="mango-pytest-danger-option" :disabled="publicationActionCaseId !== null"
                      @click="onPublicationChange(selectedExplorerRecord, 'unpublished')"
                    >退回未发布</a-doption>
                    <a-doption
                      class="mango-pytest-danger-option"
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
            <mango-panel-spin :loading="explorerSourceLoading" class="mango-pytest-source-panel__body">
              <CodeEditor
                v-if="selectedExplorerRecord"
                v-model="explorerCodeText"
                :code-style="{ height: '100%' }"
                :line-actions="explorerFileType === 'py' ? methodLineActions : []"
                readonly
                placeholder="请选择左侧测试文件"
                @line-action="onRunMethod"
              />
              <div v-else-if="!explorerSourceLoading" class="mango-empty-state">
                请选择目录树中的 Python 文件查看源码
              </div>
            </mango-panel-spin>
          </section>
        </div>
        <BaseSidePanel
          :visible="data.drawerVisible"
          title="编辑代码"
          :width="1000"
          @update:visible="
            (val) => {
              data.drawerVisible = val
            }
          "
          @cancel="
            () => {
              data.drawerVisible = false
            }
          "
        >
          <template #default>
            <div>
              <a-tabs
                v-if="data.hasFeatureFile"
                :active-key="data.fileType"
                @change="
                  (key) => {
                    data.fileType = key
                    onFileTypeChange()
                  }
                "
              >
                <a-tab-pane
                  key="py"
                  title="Python 文件"
                  data-testid="qa-views-pytest-case-tab-pane-python-文件"
                >
                  <mango-panel-spin
                    :loading="methodNodesLoading || featureLookupLoading"
                    class="mango-pytest-code-editor-spin"
                  >
                    <CodeEditor
                      v-model="data.codeText"
                      :line-actions="methodLineActions"
                      placeholder="输入python代码"
                      @line-action="onRunMethod"
                    />
                  </mango-panel-spin>
                </a-tab-pane>
                <a-tab-pane
                  key="feature"
                  title="Feature 文件"
                  data-testid="qa-views-pytest-case-tab-pane-feature-文件"
                >
                  <CodeEditor v-model="data.codeText" placeholder="输入 Gherkin 语法" />
                </a-tab-pane>
              </a-tabs>
              <template v-else>
                <mango-panel-spin
                  :loading="methodNodesLoading || featureLookupLoading"
                  class="mango-pytest-code-editor-spin"
                >
                  <CodeEditor
                    v-model="data.codeText"
                    :line-actions="methodLineActions"
                    placeholder="输入python代码"
                    @line-action="onRunMethod"
                  />
                </mango-panel-spin>
              </template>
            </div>
          </template>
          <template #extra-buttons>
            <a-button
              type="primary"
              :loading="codeSaving"
              @click="drawerOk"
              data-testid="qa-views-pytest-case-button-保存"
            >
              保存
            </a-button>
          </template>
        </BaseSidePanel>
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
  <CasePublicationReviewModal ref="publicationReviewRef" @published="loadDirectoryTree()" />
  <PytestCaseBatchEditor
    v-model:visible="batchEditorVisible"
    :scopes="batchEditorScopes"
    :initial-scope-key="batchEditorInitialScopeKey"
    :user-options="data.userList"
    :current-user-id="userStore.userId"
    @saved="onBatchEditorSaved"
  />
  <ModalDialog ref="updateModalRef" title="选择项目进行同步" @confirm="handleUpdateConfirm">
    <template #content>
      <a-form :model="updateForm">
        <a-form-item class="mango-form-item__require" label="项目/产品">
          <a-cascader
            v-model="updateForm.projectId"
            placeholder="请选择项目/产品"
            :options="projectInfo.projectPytest2"
            allow-search
            allow-clear
          />
        </a-form-item>
      </a-form>
    </template>
  </ModalDialog>
  <ModalDialog ref="modalDialogRef" :title="data.actionTitle" @confirm="onDataForm">
    <template #content>
      <a-form :model="formModel">
        <a-form-item
          :class="[item.required ? 'mango-form-item__require' : 'mango-form-item__no_require']"
          :label="item.label"
          v-for="item of formItems"
          :key="item.key"
        >
          <template v-if="item.type === 'input'">
            <a-input :placeholder="item.placeholder" v-model="item.value" />
          </template>
          <template v-else-if="item.type === 'cascader' && item.key === 'project_product'">
            <a-cascader
              v-model="item.value"
              @change="onPytestProjectName(item.value)"
              :placeholder="item.placeholder"
              :options="projectInfo.projectPytest2"
              allow-search
              allow-clear
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'module'">
            <ProductModuleSelect
              v-model="item.value"
              :disabled="!getPytestProjectProductId(getFormItemValue('project_product'))"
              :project-product-id="getPytestProjectProductId(getFormItemValue('project_product'))"
              :placeholder="item.placeholder"
              :auto-clear="false"
              :selectable-level="3"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'asset_status'">
            <a-select
              v-model="item.value"
              :multiple="item.multiple"
              :max-tag-count="item.multiple ? 1 : undefined"
              :placeholder="item.placeholder"
              :options="editableAssetStatusOptions"
              :field-names="fieldNames"
              value-key="key"
              allow-clear
              allow-search
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'level'">
            <a-select
              v-model="item.value"
              :multiple="item.multiple"
              :max-tag-count="item.multiple ? 1 : undefined"
              :placeholder="item.placeholder"
              :options="enumStore.case_level"
              :field-names="fieldNames"
              value-key="key"
              allow-clear
              allow-search
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'scenario_layer'">
            <a-select
              v-model="item.value"
              :multiple="item.multiple"
              :max-tag-count="item.multiple ? 1 : undefined"
              :placeholder="item.placeholder"
              :options="enumStore.api_case_scenario_layer"
              :field-names="fieldNames"
              value-key="key"
              allow-clear
              allow-search
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'scenario_type'">
            <a-select
              v-model="item.value"
              :multiple="item.multiple"
              :max-tag-count="item.multiple ? 1 : undefined"
              :placeholder="item.placeholder"
              :options="enumStore.api_case_scenario_type"
              :field-names="fieldNames"
              value-key="key"
              allow-clear
              allow-search
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'scenario_tags'">
            <a-select
              v-model="item.value"
              :placeholder="item.placeholder"
              :options="enumStore.api_case_scenario_tag"
              :field-names="fieldNames"
              value-key="key"
              allow-clear
              allow-search
              multiple
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'case_people'">
            <a-select
              v-model="item.value"
              :multiple="item.multiple"
              :max-tag-count="item.multiple ? 1 : undefined"
              :placeholder="item.placeholder"
              :options="data.userList"
              :field-names="fieldNames"
              value-key="key"
              allow-clear
              allow-search
              @change="doRefresh"
            />
          </template>
        </a-form-item>
      </a-form>
    </template>
  </ModalDialog>
</template>

<script lang="ts" setup>
  import CasePublicationReviewModal from '@/components/business/CasePublicationReviewModal.vue'
  import { usePagination, useTable } from '@/hooks/table'
  import { useLatestRequest } from '@/hooks/use-latest-request'
  import { useProjectLockedRowSelection } from '@/hooks/use-project-locked-row-selection'
  import { FormItem, ModalDialogType } from '@/types/components'
  import { Message, Modal } from '@arco-design/web-vue'
  import { computed, h, nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'
  import { useRoute } from 'vue-router'
  import { getFormItems } from '@/utils/datacleaning'
  import { fieldNames } from '@/setting'
  import { formItems } from './config'
  import { useEnum } from '@/store/modules/get-enum'
  import {
    deletePytestCase,
    getPytestCase,
    getPytestCaseRead,
    getPytestCaseMethodNodes,
    getPytestCaseDirectoryTree,
    getPytestCaseTest,
    postPytestCaseUpdate,
    postPytestCase,
    postPytestCaseWrite,
    postPytestCaseBatch,
    putPytestCase,
    putPytestCasePublication,
  } from '@/api/pytest/case'
  import CodeEditor from '@/components/editors/CodeEditor.vue'
  import { getUserName } from '@/api/user/user'
  import { useProject } from '@/store/modules/get-project'
  import useUserStore from '@/store/modules/user'
  import { conditionItems } from '@/views/pytest/case/config'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import { formatModulePath } from '@/utils/business-format'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import { flattenProjectProducts } from '@/components/business/project-product-filter'
  import PytestCaseDirectoryTree, {
    type PytestDirectoryNode,
  } from './components/PytestCaseDirectoryTree.vue'
  import ExecutionResultHistoryDrawer from '@/components/business/ExecutionResultHistoryDrawer.vue'
  import PytestExecutionResultDetail from './components/PytestExecutionResultDetail.vue'
  import PytestCaseBatchEditor from './components/PytestCaseBatchEditor.vue'

  const projectInfo = useProject()

  const modalDialogRef = ref<ModalDialogType | null>(null)
  const publicationReviewRef = ref<InstanceType<typeof CasePublicationReviewModal> | null>(null)
  const updateModalRef = ref<ModalDialogType | null>(null)
  const table = useTable()
  const pagination = usePagination(doRefresh, () => table.tableLoading)
  const { selectedRowKeys, validateSingleProject } = useProjectLockedRowSelection<any>(
    () => table.dataList,
    (row) => row?.project_product?.project_product?.project
  )
  const sidebarModuleIds = ref<Array<string | number>>([])
  const props = defineProps<{ caseId?: string | number; embedded?: boolean }>()
  const sidebarProjectProductId = ref<string | number | null>(null)
  const route = useRoute()
  const linkedCaseId = ref(Number(props.caseId || route.query.id) > 0 ? Number(props.caseId || route.query.id) : null)
  const sidebarSelectedModuleId = ref<string | number | null>(null)
  const directoryTree = ref<PytestDirectoryNode[]>([])
  const directoryTreeLoading = ref(false)
  const selectedDirectoryNode = ref<PytestDirectoryNode | null>(null)
  const activeDirectoryNode = ref<PytestDirectoryNode | null>(null)
  const selectedExplorerFileNode = ref<PytestDirectoryNode | null>(null)
  const selectedExplorerRecord = ref<any | null>(null)
  const explorerCodeText = ref('')
  const explorerPythonText = ref('')
  const explorerFeatureText = ref('')
  const explorerFileType = ref<'py' | 'feature'>('py')
  const explorerHasFeature = ref(false)
  const explorerSourceLoading = ref(false)
  const sourceSnapshots = reactive({
    py: { commit: '', contentHash: '' },
    feature: { commit: '', contentHash: '' },
  })
  const resultHistoryVisible = ref(false)
  const resultHistoryRecord = ref<any | null>(null)
  const batchEditorVisible = ref(false)
  const batchEditorScopes = ref<
    Array<{ key: string; label: string; caseIds: number[]; disabled?: boolean }>
  >([])
  const batchEditorInitialScopeKey = ref('')
  let directoryTreeRequestId = 0
  let explorerSourceRequestId = 0
  let initialFileSelectionPending = true
  const { beginRequest, isLatestRequest } = useLatestRequest()
  const sidebarResetKey = ref(0)
  const headerConditionItems = computed(() =>
    conditionItems.filter((item) => ['id', 'name', 'file_path', 'publication_status', 'status',
      'source_status', 'asset_status', 'level', 'case_people'].includes(item.key))
  )
  function searchOptions(key: string) {
    if (key === 'publication_status') return enumStore.pytest_case_publication_status
    if (key === 'status') return enumStore.task_status
    if (key === 'level') return enumStore.case_level
    if (key === 'case_people') return data.userList
    return getLifecycleOptions(key)
  }

  function buildCaseSearchParams() {
    const params = getFormItems(conditionItems)
    Object.keys(params).forEach((key) => {
      if (params[key] === '' || params[key] === null || params[key] === undefined ||
          (Array.isArray(params[key]) && !params[key].length)) delete params[key]
    })
    return params
  }

  function onSearchRefresh() {
    pagination.page = 1
    selectedRowKeys.value = []
    clearPollingTimer()
    explorerSourceRequestId += 1
    explorerSourceLoading.value = false
    selectedDirectoryNode.value = null
    activeDirectoryNode.value = null
    initialFileSelectionPending = true
    loadDirectoryTree()
  }
  const formModel = ref({})
  const enumStore = useEnum()
  const userStore = useUserStore()

  const currentProjectProductLabel = computed(() => {
    if (sidebarProjectProductId.value === null) return '全部项目'
    return (
      flattenProjectProducts(projectInfo.projectProduct || []).find(
        (item) => String(item.projectProductId) === String(sidebarProjectProductId.value)
      )?.title || `产品 ${sidebarProjectProductId.value}`
    )
  })

  function findModuleLabel(nodes: any[], moduleId: string | number | null): string | null {
    if (moduleId === null) return null
    for (const node of nodes || []) {
      const id = node.id ?? node.key ?? node.value
      if (String(id) === String(moduleId)) return node.title || node.name || node.label || null
      const childLabel = findModuleLabel(node.children || [], moduleId)
      if (childLabel) return childLabel
    }
    return null
  }

  const currentModuleLabel = computed(() => {
    if (sidebarSelectedModuleId.value === null) return '全部模块'
    return (
      findModuleLabel(projectInfo.allProductModuleTreeCache.data, sidebarSelectedModuleId.value) ||
      `模块 ${sidebarSelectedModuleId.value}`
    )
  })

  const currentDirectoryLabel = computed(() =>
    selectedExplorerFileNode.value?.breadcrumb?.length
      ? selectedExplorerFileNode.value.breadcrumb.join(' / ')
      : '全部目录'
  )
  const currentScopeTitle = computed(
    () =>
      `${currentProjectProductLabel.value} / ${currentModuleLabel.value} / ${currentDirectoryLabel.value}`
  )
  const resultHistoryQuery = computed(() =>
    resultHistoryRecord.value
      ? {
          target_type: 'pytest_case',
          target_id: resultHistoryRecord.value.id,
        }
      : undefined
  )
  const selectedModuleLabel = computed(() =>
    selectedExplorerRecord.value?.module
      ? formatModulePath(selectedExplorerRecord.value.module)
      : '未绑定'
  )
  const selectedScenarioTags = computed(() =>
    Array.isArray(selectedExplorerRecord.value?.scenario_tags)
      ? selectedExplorerRecord.value.scenario_tags
      : []
  )
  const selectedSourceAvailable = computed(
    () => ![2, 3, 4].includes(Number(selectedExplorerRecord.value?.source_status ?? 0))
  )
  const selectedCaseExecutable = computed(() => {
    const assetStatus = Number(
      selectedExplorerRecord.value?.asset_status ??
        (selectedExplorerRecord.value?.publication_status === 'published' ? 1 : 0)
    )
    return selectedSourceAvailable.value && ![2, 3, 4].includes(assetStatus)
  })
  const sourceStatusColor = computed(() => {
    const status = Number(selectedExplorerRecord.value?.source_status ?? 0)
    if (status === 1) return 'orange'
    if ([2, 3, 4].includes(status)) return 'red'
    return 'green'
  })
  const assetStatusColor = computed(() => {
    const status = Number(
      selectedExplorerRecord.value?.asset_status ??
        (selectedExplorerRecord.value?.publication_status === 'published' ? 1 : 0)
    )
    if (status === 1) return 'green'
    if ([2, 3, 4].includes(status)) return 'gray'
    return 'arcoblue'
  })
  const editableAssetStatusOptions = computed(() => (enumStore.pytest_asset_status || []).filter((option) => {
    if (selectedExplorerRecord.value?.publication_status === 'prepublished') {
      return Number(option.key) === Number(selectedExplorerRecord.value.asset_status)
    }
    return (Number(option.key) === 1) === (selectedExplorerRecord.value?.publication_status === 'published')
  }))
  const canBatchEditCases = computed(() => getBatchEditScopes().some((scope) => !scope.disabled))

  const data: any = reactive({
    isAdd: false,
    updateId: 0,
    actionTitle: '新增',
    drawerVisible: false,
    codeText: '',
    moduleList: [],
    fileType: 'py',
    hasFeatureFile: false,
    methodNodes: [],
  })

  const updateForm = reactive({
    projectId: null as number | null,
  })
  const caseRunning = ref(false)
  const publicationActionCaseId = ref<number | null>(null)
  const methodNodesLoading = ref(false)
  const featureLookupLoading = ref(false)
  const codeSaving = ref(false)
  const methodRunLoading = reactive<Record<string, boolean>>({})
  const executionStartedMessage = '准备开始执行，执行完成之后，请在右侧按钮结果中查看执行结果~'
  const methodLineActions = computed(() =>
    (data.methodNodes || [])
      .filter((node: any) => Number(node.line_number) > 0)
      .map((node: any) => ({
        id: node.nodeid,
        line: Number(node.line_number),
        label: `执行 ${node.class_name ? `${node.class_name}.` : ''}${node.method_name}`,
        loading: Boolean(methodRunLoading[node.nodeid]),
        payload: node,
      }))
  )
  const pollingTimer = ref<ReturnType<typeof window.setInterval> | null>(null)
  const pollingCaseId = ref<number | null>(null)
  let pollingRequestPending = false

  function getConditionValue(key: string) {
    return conditionItems.find((item) => item.key === key)?.value
  }

  function getFormItemValue(key: string) {
    return formItems.find((item) => item.key === key)?.value
  }

  function getEnumTitle(options: any[] | null | undefined, value: any) {
    return options?.find((item: any) => String(item.key) === String(value))?.title || '-'
  }

  function getLifecycleOptions(key: string) {
    if (key === 'source_status') return enumStore.pytest_source_status
    if (key === 'asset_status') return enumStore.pytest_asset_status
    return enumStore.file_status
  }

  function getPytestProjectProductId(pytestProductId: any) {
    return projectInfo.getPytestProjectProductId(pytestProductId)
  }

  function clearPollingTimer() {
    if (pollingTimer.value) {
      window.clearInterval(pollingTimer.value)
      pollingTimer.value = null
    }
    pollingCaseId.value = null
  }

  async function refreshSelectedCaseState(caseId: number) {
    if (pollingRequestPending) return undefined
    pollingRequestPending = true
    try {
      const res = await getPytestCase({ id: caseId, page: 1, pageSize: 1 })
      const record = res.data?.[0] || null
      if (record && Number(selectedExplorerRecord.value?.id) === Number(caseId)) {
        selectedExplorerRecord.value = {
          ...selectedExplorerRecord.value,
          ...record,
        }
      }
      return record
    } finally {
      pollingRequestPending = false
    }
  }

  async function pollSelectedCaseState(caseId: number) {
    try {
      const record = await refreshSelectedCaseState(caseId)
      if (record === undefined || pollingCaseId.value !== caseId) return
      if (!record || Number(record.status) !== 3) clearPollingTimer()
    } catch {
      // 短暂请求失败时保留轮询，下一个周期继续同步执行状态。
    }
  }

  function startPollingCaseState(caseId: number) {
    clearPollingTimer()
    pollingCaseId.value = caseId
    void pollSelectedCaseState(caseId)
    pollingTimer.value = window.setInterval(() => {
      if (pollingCaseId.value === caseId) void pollSelectedCaseState(caseId)
    }, 5000)
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
      content: '该操作会删除平台资产及其配置，但不会删除 Git 源文件。确定继续吗？',
      cancelText: '取消',
      okText: '删除',
      onBeforeOk: () => {
        return deletePytestCase(batch ? selectedRowKeys.value : record.id)
          .then((res) => {
            Message.success(res.msg)
          })
          .catch(() => undefined)
          .finally(() => {
            doRefresh()
            loadDirectoryTree()
            if (batch) {
              selectedRowKeys.value = []
            }
          })
      },
    })
  }

  function onPublicationChange(record: any, target: 'prepublished' | 'published' | 'unpublished') {
    if (target === 'published') {
      if (record.publication_status !== 'prepublished') {
        Message.warning('只有预发布状态的用例可以进入发布审核')
        return
      }
      void publicationReviewRef.value?.open('pytest', [Number(record.id)])
      return
    }
    if (target !== 'unpublished' && record.status !== 1) {
      Message.warning('用例必须执行通过后才能提交预发布或正式发布')
      return
    }
    const title = target === 'prepublished' ? '提交预发布' : '退回未发布'
    Modal.confirm({
      title,
      content: target === 'prepublished' ? '提交后由业务项目产品负责人审核，预发布不参与定时执行。确认提交吗？'
        : '退回后该用例不再参与定时执行。确认退回吗？',
      cancelText: '取消',
      okText: title,
      okButtonProps: target === 'unpublished' ? { status: 'danger' } : undefined,
      onBeforeOk: async () => {
        publicationActionCaseId.value = record.id
        try {
          const res = await putPytestCasePublication(record.id, target)
          Message.success(res.msg)
          Object.assign(record, res.data)
          loadDirectoryTree(record.id, false)
          return true
        } finally {
          publicationActionCaseId.value = null
        }
      },
    })
  }

  function openUpdateModal() {
    updateForm.projectId = null
    updateModalRef.value?.toggle()
  }

  function handleUpdateConfirm() {
    const projectId = Array.isArray(updateForm.projectId)
      ? updateForm.projectId[updateForm.projectId.length - 1]
      : updateForm.projectId

    if (!projectId) {
      Message.error('请选择项目/产品')
      updateModalRef.value?.setConfirmLoading(false)
      return
    }
    Message.loading('文件更新中，请耐心等待10秒左右...')

    postPytestCaseUpdate(projectId)
      .then((res) => {
        updateModalRef.value?.toggle()
        Message.success(res.msg)
        selectedDirectoryNode.value = null
        loadDirectoryTree()
        doRefresh()
      })
      .catch((error) => {
        Message.error(error?.msg || '同步失败')
      })
      .finally(() => {
        updateModalRef.value?.setConfirmLoading(false)
      })
  }

  function onDataForm() {
    if (formItems.every((it) => (it.validator ? it.validator() : true))) {
      let value = getFormItems(formItems)
      value['scenario_layer'] = value['scenario_layer'] ?? 0
      value['scenario_type'] = value['scenario_type'] ?? 0
      value['scenario_tags'] = value['scenario_tags'] || []
      if (data.isAdd) {
        postPytestCase(value)
          .then((res) => {
            modalDialogRef.value?.toggle()
            Message.success(res.msg)
            doRefresh()
          })
          .catch(() => undefined)
          .finally(() => {
            modalDialogRef.value?.setConfirmLoading(false)
          })
      } else {
        value['id'] = data.updateId
        putPytestCase(value)
          .then((res) => {
            modalDialogRef.value?.toggle()
            Message.success(res.msg)
            doRefresh()
            loadDirectoryTree(data.updateId, false)
          })
          .catch(() => undefined)
          .finally(() => {
            modalDialogRef.value?.setConfirmLoading(false)
          })
      }
    } else {
      modalDialogRef.value?.setConfirmLoading(false)
    }
  }

  function onUpdate(item: any) {
    data.actionTitle = '编辑'
    data.isAdd = false
    data.updateId = item.id
    modalDialogRef.value?.toggle()
    if (item.project_product) {
      onPytestProjectName(item.project_product.id)
    }
    nextTick(() => {
      formItems.forEach((it) => {
        const propName =
          it.key === 'asset_status' && item[it.key] === undefined
            ? item.publication_status === 'published'
              ? 1
              : 0
            : item[it.key]
        if (it.key === 'scenario_layer' && (propName === undefined || propName === null)) {
          it.value = 0
        } else if (it.key === 'scenario_type' && (propName === undefined || propName === null)) {
          it.value = 0
        } else if (it.key === 'scenario_tags' && !Array.isArray(propName)) {
          it.value = []
        } else if (Array.isArray(propName)) {
          it.value = propName
        } else if (typeof propName === 'object' && propName !== null) {
          it.value = propName.id
        } else {
          it.value = propName
        }
      })
    })
  }

  function doRefresh(projectProductId: number | null = null, bool_ = false) {
    const requestId = beginRequest()
    table.tableLoading.value = true
    const value = buildCaseSearchParams()
    if (
      value.project_product !== null &&
      value.project_product !== undefined &&
      value.project_product !== ''
    ) {
      value['project_product__project_product_id'] = value.project_product
      delete value.project_product
    }
    if (sidebarModuleIds.value.length) value['module__in'] = sidebarModuleIds.value.join(',')
    const directoryNode = selectedDirectoryNode.value
    if (directoryNode) {
      if (directoryNode.pytest_project_id) {
        value.project_product = directoryNode.pytest_project_id
      }
      if (directoryNode.type === 'directory') {
        value['file_path__startswith'] = `${directoryNode.path.replace(/\/$/, '')}/`
      } else if (directoryNode.type === 'file') {
        value['file_path__exact'] = directoryNode.path
      }
    }
    if (!Array.isArray(value.scenario_tags) || !value.scenario_tags.length) {
      delete value.scenario_tags
    }
    if (value.update_user === null || value.update_user === '') {
      delete value.update_user
    }
    value['page'] = pagination.page
    value['pageSize'] = pagination.pageSize
    if (projectProductId && bool_) {
      value['project_product__project_product_id'] = projectProductId
      data.moduleList = projectInfo.getProjectPytestModule(projectProductId)
    }
    getPytestCase(value)
      .then((res) => {
        if (!isLatestRequest(requestId)) return
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
      })
      .catch(() => undefined)
      .finally(() => {
        if (isLatestRequest(requestId)) table.tableLoading.value = false
      })
  }

  function onSidebarFilterChange(filter: {
    projectProduct: any
    module: any
    moduleIds?: Array<string | number>
    selectedModuleId?: string | number | null
  }) {
    const projectItem = conditionItems.find((item) => item.key === 'project_product')
    const moduleItem = conditionItems.find((item) => item.key === 'module')
    if (projectItem) projectItem.value = filter.projectProduct
    if (moduleItem) moduleItem.value = filter.module
    sidebarProjectProductId.value = filter.projectProduct
    sidebarSelectedModuleId.value = filter.selectedModuleId ?? filter.module ?? null
    sidebarModuleIds.value = filter.moduleIds || []
    clearPollingTimer()
    selectedDirectoryNode.value = null
    activeDirectoryNode.value = null
    pagination.page = 1
    selectedRowKeys.value = []
    loadDirectoryTree()
  }

  function loadDirectoryTree(preferredCaseId: number | null = null, reloadSource = true) {
    const requestId = ++directoryTreeRequestId
    directoryTreeLoading.value = true
    const params: Record<string, any> = buildCaseSearchParams()
    delete params.project_product
    delete params.module
    if (sidebarProjectProductId.value !== null) {
      params.project_product_id = sidebarProjectProductId.value
    }
    if (sidebarModuleIds.value.length) {
      params.module_ids = sidebarModuleIds.value.join(',')
    }
    getPytestCaseDirectoryTree(params)
      .then((res) => {
        if (requestId !== directoryTreeRequestId) return
        directoryTree.value = Array.isArray(res.data) ? res.data : []
        const existingCaseId =
          selectedDirectoryNode.value?.type === 'file'
            ? selectedDirectoryNode.value.case_id || null
            : null
        const selectedCaseId = preferredCaseId || existingCaseId || linkedCaseId.value
        const selectLinkedCase = Boolean(linkedCaseId.value && selectedCaseId === linkedCaseId.value)
        const shouldSelectInitialFile = initialFileSelectionPending && !selectedCaseId
        const selectedFile = selectedCaseId
          ? findDirectoryFileByCaseId(directoryTree.value, selectedCaseId)
          : shouldSelectInitialFile
          ? findFirstDirectoryFile(directoryTree.value)
          : null
        if (selectedFile) {
          if (selectLinkedCase) linkedCaseId.value = null
          if (shouldSelectInitialFile) initialFileSelectionPending = false
          selectedDirectoryNode.value = selectedFile
          if (
            shouldSelectInitialFile || selectLinkedCase ||
            (preferredCaseId &&
              (reloadSource ||
                Number(selectedExplorerRecord.value?.id) !== Number(selectedFile.case_id)))
          ) {
            loadExplorerFile(selectedFile)
          } else {
            selectedExplorerFileNode.value = selectedFile
            if (selectedFile.case_id) {
              void refreshSelectedCaseState(selectedFile.case_id).catch(() => undefined)
            }
          }
        } else {
          selectedDirectoryNode.value = null
          activeDirectoryNode.value = null
          selectedExplorerFileNode.value = null
          selectedExplorerRecord.value = null
          explorerCodeText.value = ''
          explorerPythonText.value = ''
          explorerFeatureText.value = ''
          explorerFileType.value = 'py'
          explorerHasFeature.value = false
          data.methodNodes = []
        }
      })
      .catch(() => {
        if (requestId !== directoryTreeRequestId) return
        directoryTree.value = []
        selectedDirectoryNode.value = null
        activeDirectoryNode.value = null
        selectedExplorerFileNode.value = null
        selectedExplorerRecord.value = null
        explorerCodeText.value = ''
        explorerPythonText.value = ''
        explorerFeatureText.value = ''
        explorerFileType.value = 'py'
        explorerHasFeature.value = false
        data.methodNodes = []
      })
      .finally(() => {
        if (requestId === directoryTreeRequestId) directoryTreeLoading.value = false
      })
  }

  function findFirstDirectoryFile(nodes: PytestDirectoryNode[]): PytestDirectoryNode | null {
    for (const node of nodes || []) {
      if (node.type === 'file') return node
      const child = findFirstDirectoryFile(node.children || [])
      if (child) return child
    }
    return null
  }

  function findDirectoryFileByCaseId(
    nodes: PytestDirectoryNode[],
    caseId: number
  ): PytestDirectoryNode | null {
    for (const node of nodes || []) {
      if (node.type === 'file' && node.case_id === caseId) return node
      const child = findDirectoryFileByCaseId(node.children || [], caseId)
      if (child) return child
    }
    return null
  }

  function collectDirectoryCaseIds(node: PytestDirectoryNode | null): number[] {
    if (!node) return []
    if (node.type === 'file') return node.case_id ? [node.case_id] : []
    return (node.children || []).flatMap((child) => collectDirectoryCaseIds(child))
  }

  async function loadExplorerFile(node: PytestDirectoryNode) {
    if (!node.case_id) return
    const requestId = ++explorerSourceRequestId
    selectedExplorerFileNode.value = node
    explorerSourceLoading.value = true
    data.updateId = node.case_id
    data.methodNodes = []
    try {
      const [caseResponse, sourceResponse, methodResponse, featureResponse] = await Promise.all([
        getPytestCase({ id: node.case_id, page: 1, pageSize: 1 }),
        getPytestCaseRead(node.case_id, 'py').catch(() => null),
        getPytestCaseMethodNodes(node.case_id, true).catch(() => null),
        getPytestCaseRead(node.case_id, 'feature', true).catch(() => null),
      ])
      if (requestId !== explorerSourceRequestId) return
      explorerPythonText.value = sourceResponse
        ? typeof sourceResponse.data === 'string'
          ? sourceResponse.data
          : sourceResponse.data?.content || ''
        : ''
      sourceSnapshots.py.commit = sourceResponse?.data?.commit_hash || ''
      sourceSnapshots.py.contentHash = sourceResponse?.data?.content_hash || ''
      explorerFeatureText.value = featureResponse
        ? typeof featureResponse.data === 'string'
          ? featureResponse.data
          : featureResponse.data?.content || ''
        : ''
      sourceSnapshots.feature.commit = featureResponse?.data?.commit_hash || ''
      sourceSnapshots.feature.contentHash = featureResponse?.data?.content_hash || ''
      explorerHasFeature.value = featureResponse !== null
      explorerFileType.value = 'py'
      explorerCodeText.value = explorerPythonText.value
      data.methodNodes = methodResponse?.data || []
      selectedExplorerRecord.value = caseResponse.data?.[0] || {
        id: node.case_id,
        name: node.title,
        file_path: node.path,
      }
      if (Number(selectedExplorerRecord.value?.status) === 3) {
        startPollingCaseState(Number(node.case_id))
      }
    } catch {
      if (requestId !== explorerSourceRequestId) return
      selectedExplorerRecord.value = null
      explorerCodeText.value = ''
      explorerPythonText.value = ''
      explorerFeatureText.value = ''
      explorerFileType.value = 'py'
      explorerHasFeature.value = false
      data.methodNodes = []
    } finally {
      if (requestId === explorerSourceRequestId) explorerSourceLoading.value = false
    }
  }

  function onDirectorySelect(node: PytestDirectoryNode | null) {
    if (!node || node.type !== 'file') return
    clearPollingTimer()
    selectedDirectoryNode.value = node
    activeDirectoryNode.value = null
    loadExplorerFile(node)
  }

  function onDirectoryToggle(node: PytestDirectoryNode) {
    activeDirectoryNode.value = node
  }

  function onExplorerFileTypeChange(value: string | number | boolean) {
    explorerCodeText.value =
      value === 'feature' ? explorerFeatureText.value : explorerPythonText.value
  }

  function findProjectNodeForCase(
    nodes: PytestDirectoryNode[],
    caseId: number
  ): PytestDirectoryNode | null {
    for (const node of nodes) {
      if (node.type === 'project' && collectDirectoryCaseIds(node).includes(caseId)) return node
      const child = findProjectNodeForCase(node.children || [], caseId)
      if (child) return child
    }
    return null
  }

  function findFirstProjectNode(nodes: PytestDirectoryNode[]): PytestDirectoryNode | null {
    for (const node of nodes) {
      if (node.type === 'project') return node
      const child = findFirstProjectNode(node.children || [])
      if (child) return child
    }
    return null
  }

  function getBatchEditProjectNode() {
    const selectedCaseId = Number(selectedExplorerFileNode.value?.case_id || 0)
    return selectedCaseId
      ? findProjectNodeForCase(directoryTree.value, selectedCaseId)
      : findFirstProjectNode(directoryTree.value)
  }

  function collectProjectNodes(nodes: PytestDirectoryNode[]): PytestDirectoryNode[] {
    return nodes.flatMap((node) => [
      ...(node.type === 'project' ? [node] : []),
      ...collectProjectNodes(node.children || []),
    ])
  }

  function getBatchEditScopes() {
    return collectProjectNodes(directoryTree.value).map((node) => {
      const caseIds = Array.from(new Set(collectDirectoryCaseIds(node)))
      return {
        key: node.key,
        label: [currentProjectProductLabel.value, currentModuleLabel.value, ...node.breadcrumb]
          .filter(Boolean)
          .join(' / '),
        caseIds,
        disabled: caseIds.length === 0 || caseIds.length > 500,
      }
    })
  }

  function openBatchEditor() {
    const targetNode = getBatchEditProjectNode()
    const scopes = getBatchEditScopes()
    const targetScope = scopes.find((scope) => scope.key === targetNode?.key)
    if (!targetScope?.caseIds.length) {
      Message.warning('当前项目绑定下没有可编辑的 Case')
      return
    }
    if (targetScope.caseIds.length > 500) {
      Message.warning('一次最多批量编辑 500 条 Case，请先选择更小的目录范围')
      return
    }
    batchEditorScopes.value = scopes
    batchEditorInitialScopeKey.value = targetScope.key
    batchEditorVisible.value = true
  }

  function onBatchEditorSaved() {
    const preferredCaseId = selectedExplorerRecord.value?.id || null
    loadDirectoryTree(preferredCaseId, false)
  }

  function onResetSearch() {
    pagination.page = 1
    selectedRowKeys.value = []
    explorerSourceRequestId += 1
    explorerSourceLoading.value = false
    initialFileSelectionPending = true
    clearPollingTimer()
    sidebarModuleIds.value = []
    sidebarProjectProductId.value = null
    sidebarSelectedModuleId.value = null
    selectedDirectoryNode.value = null
    conditionItems.forEach((it) => {
      it.value = it.key === 'project_product' || it.key === 'module' ? null : it.multiple ? [] : ''
    })
    data.moduleList = []
    sidebarResetKey.value += 1
    loadDirectoryTree()
  }

  function onSearchProjectProductChange(projectProductId: any) {
    const moduleItem = conditionItems.find((it) => it.key === 'module')
    if (moduleItem) {
      moduleItem.value = null
    }
    if (projectProductId) {
      data.moduleList = projectInfo.getProjectPytestModule(projectProductId)
    } else {
      data.moduleList = []
    }
    doRefresh(projectProductId, true)
  }

  function onBatchRun() {
    if (userStore.selected_environment == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    if (selectedRowKeys.value.length === 0) {
      Message.error('请选择要批量执行的用例')
      return
    }
    if (!validateSingleProject()) return
    Modal.confirm({
      title: '批量执行 Pytest Case',
      content: `确定执行已选择的 ${selectedRowKeys.value.length} 条用例吗？`,
      cancelText: '取消',
      okText: '执行',
      onBeforeOk: async () => {
        caseRunning.value = true
        try {
          const res = await postPytestCaseBatch(
            selectedRowKeys.value,
            Number(userStore.selected_environment)
          )
          const reportId = res.data?.test_suite_id
          Message.success(reportId ? `${res.msg}，测试报告 ID：${reportId}` : res.msg)
          selectedRowKeys.value = []
          doRefresh()
          return true
        } finally {
          caseRunning.value = false
        }
      },
    })
  }

  const onRun = async (param) => {
    if (!selectedCaseExecutable.value) {
      Message.warning('当前测试文件源码不可用，或资产已停用、归档、忽略，不能执行')
      return
    }
    if (userStore.selected_environment == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    if (caseRunning.value) return
    caseRunning.value = true
    try {
      await getPytestCaseTest(param.id, userStore.selected_environment)
      Message.success(executionStartedMessage)
      startPollingCaseState(Number(param.id))
    } catch {
    } finally {
      caseRunning.value = false
    }
  }

  const onRunMethod = async (node: any) => {
    if (!selectedCaseExecutable.value) {
      Message.warning('当前测试文件源码不可用，或资产已停用、归档、忽略，不能执行')
      return
    }
    if (userStore.selected_environment == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    methodRunLoading[node.nodeid] = true
    try {
      await getPytestCaseTest(data.updateId, userStore.selected_environment, {
        nodeid: node.nodeid,
        node_type: node.node_type,
        class_name: node.class_name,
        method_name: node.method_name,
        parameter_id: node.parameter_id,
      })
      Message.success(executionStartedMessage)
      startPollingCaseState(Number(data.updateId))
    } catch {
    } finally {
      methodRunLoading[node.nodeid] = false
    }
  }

  function drawerOk() {
    Modal.confirm({
      title: '确认保存平台代码',
      content: () =>
        h('div', [
          h('div', '请确认已了解以下事项：'),
          h('ol', [
            h(
              'li',
              '平台保存只会修改本地仓库工作区；你还需要自行提交并推送到 Git 远端，代码才会作为仓库版本正式生效。'
            ),
            h(
              'li',
              '建议优先在本地 IDE 或代码仓库中修改并正常提交，不建议长期通过测试平台直接编辑源码。'
            ),
          ]),
        ]),
      cancelText: '继续编辑',
      okText: '仍要保存',
      onBeforeOk: async () => {
        const snapshot = sourceSnapshots[data.fileType as 'py' | 'feature']
        codeSaving.value = true
        try {
          const res = await postPytestCaseWrite(
            data.updateId,
            data.codeText,
            data.fileType,
            snapshot.commit,
            snapshot.contentHash
          )
          data.codeText = res.data?.content || ''
          snapshot.commit = res.data?.commit_hash || ''
          snapshot.contentHash = res.data?.content_hash || ''
          data.drawerVisible = false
          Message.success(`${res.msg}；请提交并推送到 Git 远端`)
          if (selectedExplorerFileNode.value) loadExplorerFile(selectedExplorerFileNode.value)
          return true
        } catch {
          return false
        } finally {
          codeSaving.value = false
        }
      },
    })
  }

  function onResult(record: any) {
    resultHistoryRecord.value = record
    resultHistoryVisible.value = true
  }

  function onFileTypeChange() {
    data.methodNodes = []
    getPytestCaseRead(data.updateId, data.fileType)
      .then((res) => {
        data.codeText = typeof res.data === 'string' ? res.data : res.data?.content || ''
        const snapshot = sourceSnapshots[data.fileType as 'py' | 'feature']
        snapshot.commit = res.data?.commit_hash || ''
        snapshot.contentHash = res.data?.content_hash || ''
        if (data.fileType === 'py') {
          loadMethodNodes(data.updateId)
        }
      })
      .catch(() => undefined)
  }

  function onClick(record: any) {
    data.drawerVisible = true
    data.updateId = record.id
    data.fileType = 'py'
    data.hasFeatureFile = !!record.feature_file_path
    data.methodNodes = []
    featureLookupLoading.value = true
    getPytestCaseRead(record.id, 'feature', true)
      .then(() => {
        data.hasFeatureFile = true
      })
      .catch(() => {
        data.hasFeatureFile = false
      })
      .finally(() => {
        featureLookupLoading.value = false
      })
    getPytestCaseRead(record.id, 'py')
      .then((res) => {
        data.codeText = typeof res.data === 'string' ? res.data : res.data?.content || ''
        sourceSnapshots.py.commit = res.data?.commit_hash || ''
        sourceSnapshots.py.contentHash = res.data?.content_hash || ''
        loadMethodNodes(record.id)
      })
      .catch(() => undefined)
  }

  function loadMethodNodes(id: any) {
    methodNodesLoading.value = true
    getPytestCaseMethodNodes(id)
      .then((res) => {
        data.methodNodes = res.data || []
      })
      .catch(() => undefined)
      .finally(() => {
        methodNodesLoading.value = false
      })
  }

  function onPytestProjectName(projectProductId: any) {
    data.moduleList = projectInfo.getProjectPytestModule(projectProductId)
    formItems.forEach((item: FormItem) => {
      if (item.key === 'module') {
        item.value = item.multiple ? [] : ''
      }
    })
  }

  function getNickName() {
    getUserName()
      .then((res) => {
        data.userList = res.data
      })
      .catch(() => undefined)
  }

  onMounted(() => {
    nextTick(async () => {
      await projectInfo.projectPytestName()
      getNickName()
      onPytestProjectName(null)
    })
  })
  onUnmounted(() => {
    clearPollingTimer()
  })
</script>
<style lang="less" scoped>
  .mango-pytest-code-editor-spin {
    width: 100%;

    :deep(> .mango-panel-spin__content) {
      width: 100%;
    }
  }

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
