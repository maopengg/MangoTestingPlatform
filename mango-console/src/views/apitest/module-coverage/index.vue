<template>
  <TableBody
    plain
    class="mango-module-coverage mango-detail-workbench-page"
    :sticky-horizontal-scroll="false"
  >
    <template #header><TableHeader title="模块覆盖" /></template>
    <template #default>
      <ProjectProductNavigationWorkbench
        contained-body
        emit-initial-filter
        show-modules
        :sticky-horizontal-scroll="false"
        :model-value="projectProductId"
        :module-value="moduleId"
        @filter-change="onNavigationFilterChange"
        @search="autoSearch.run"
        @reset-search="autoSearch.cancel(); resetFilters(); autoSearch.sync()"
      >
        <template #search>
          <a-form :model="filters" layout="inline" @keyup.enter="autoSearch.run">
            <a-form-item label="仓库">
              <a-input @mouseleave="autoSearch.schedule" v-model="filters.repository_key" allow-clear placeholder="仓库标识" @blur="autoSearch.schedule" @clear="autoSearch.schedule" />
            </a-form-item>
            <a-form-item label="分支">
              <a-input @mouseleave="autoSearch.schedule" v-model="filters.branch" allow-clear placeholder="分支名称" @blur="autoSearch.schedule" @clear="autoSearch.schedule" />
            </a-form-item>
            <a-form-item v-if="activeTab === 'cases'" label="Case标题">
              <a-input @mouseleave="autoSearch.schedule" v-model="filters.name" allow-clear placeholder="Case标题" @blur="autoSearch.schedule" @clear="autoSearch.schedule" />
            </a-form-item>
            <a-form-item v-if="activeTab === 'cases'" label="接口名称">
              <a-input @mouseleave="autoSearch.schedule" v-model="filters.interface_name" allow-clear placeholder="接口名称" @blur="autoSearch.schedule" @clear="autoSearch.schedule" />
            </a-form-item>
            <a-form-item v-if="activeTab === 'interfaces'" label="接口">
              <a-input @mouseleave="autoSearch.schedule" v-model="filters.name" allow-clear placeholder="接口名称或 URL" @blur="autoSearch.schedule" @clear="autoSearch.schedule" />
            </a-form-item>
            <a-form-item v-if="activeTab === 'interfaces'" label="接口存续">
              <a-select
                v-model="filters.interface_status"
                @change="autoSearch.schedule"
                allow-clear
                placeholder="接口存续"
                :options="interfaceStatusOptions"
              />
            </a-form-item>
            <a-form-item v-if="activeTab === 'interfaces'" label="ApiInfo">
              <a-select
                v-model="filters.api_info_binding_status"
                @change="autoSearch.schedule"
                allow-clear
                placeholder="绑定状态"
                :options="apiInfoBindingOptions"
              />
            </a-form-item>
            <a-form-item v-if="activeTab === 'interfaces'" label="覆盖策略">
              <a-select
                v-model="filters.coverage_policy"
                @change="autoSearch.schedule"
                allow-clear
                placeholder="全部策略"
                :options="enumStore.module_coverage_policy"
                :field-names="{ value: 'key', label: 'title' }"
              />
            </a-form-item>
            <template v-if="activeTab === 'interfaces'">
              <a-form-item
                v-for="item in interfaceSearchSelects"
                :key="item.key"
                :label="item.label"
              >
                <a-select
                  v-model="filters[item.key]"
                  @change="autoSearch.schedule"
                  multiple
                  allow-clear
                  :max-tag-count="1"
                  :placeholder="item.label"
                  :options="item.options"
                />
              </a-form-item>
              <a-form-item label="处理原因">
                <a-input @mouseleave="autoSearch.schedule"
                  v-model="filters.coverage_reason"
                  @blur="autoSearch.schedule"
                  @clear="autoSearch.schedule"
                  allow-clear
                  placeholder="处理原因关键词"
                />
              </a-form-item>
              <a-form-item label="ApiInfo编号">
                <a-input-number @blur="autoSearch.schedule" @mouseleave="autoSearch.schedule"
                  v-model="filters.api_info_id"
                  :min="1"
                  :precision="0"
                  placeholder="ApiInfo 编号"
                />
              </a-form-item>
            </template>
            <a-form-item v-if="activeTab === 'cases'" label="当前状态">
              <a-select
                v-model="filters.status"
                @change="autoSearch.schedule"
                allow-clear
                placeholder="当前状态"
                :options="statusOptions"
              />
            </a-form-item>
            <a-form-item v-if="activeTab === 'cases'" label="变更状态">
              <a-select
                v-model="filters.change_status"
                @change="autoSearch.schedule"
                allow-clear
                placeholder="变更状态"
                :options="changeStatusOptions"
              />
            </a-form-item>
            <a-form-item v-if="activeTab === 'cases'" label="覆盖有效性">
              <a-select
                v-model="filters.coverage_validity"
                @change="autoSearch.schedule"
                allow-clear
                placeholder="覆盖有效性"
                :options="validityOptions"
              />
            </a-form-item>
            <a-form-item v-if="activeTab === 'cases'" label="测试层级">
              <a-select
                v-model="filters.scenario_layer"
                @change="autoSearch.schedule"
                allow-clear
                placeholder="测试层级"
                :options="enumStore.api_case_scenario_layer"
                :field-names="{ value: 'key', label: 'title' }"
              />
            </a-form-item>
            <a-form-item v-if="activeTab === 'cases'" label="验证类型">
              <a-select
                v-model="filters.scenario_type"
                @change="autoSearch.schedule"
                allow-clear
                placeholder="验证类型"
                :options="enumStore.api_case_scenario_type"
                :field-names="{ value: 'key', label: 'title' }"
              />
            </a-form-item>
            <a-form-item v-if="activeTab === 'cases'" label="执行场景">
              <a-select
                v-model="filters.scenario_tag"
                @change="autoSearch.schedule"
                allow-clear
                placeholder="执行场景"
                :options="enumStore.api_case_scenario_tag"
                :field-names="{ value: 'key', label: 'title' }"
              />
            </a-form-item>
          </a-form>
        </template>
        <template #tabs>
          <a-tabs v-model:active-key="activeTab" class="mango-tabs-nav-only" @change="onTabChange">
            <a-tab-pane key="overview" title="覆盖概览" />
            <a-tab-pane key="interfaces" title="接口覆盖" />
            <a-tab-pane key="cases" title="Case明细" />
            <a-tab-pane key="scans" title="扫描记录" />
          </a-tabs>
        </template>

        <CoverageOverview
          v-if="activeTab === 'overview'"
          :data="overview"
          :loading="overviewLoading"
          :error="overviewError"
          @retry="loadOverview"
          @drill="drillOverview"
          @interface="openOverviewInterface"
        />
        <div v-else class="mango-module-coverage__content">
          <template v-if="rowsError"><a-button size="small" :loading="loading" @click="loadRows">重新加载</a-button></template>
          <StickyHorizontalTable :scroll-x="tableScrollX">
            <a-table
              class="mango-native-scroll-table"
              :loading="loading"
              :data="rows"
              :columns="activeColumns"
              :pagination="false"
              :scroll="{ x: tableScrollX, y: '100%' }"
              row-key="id"
            >
              <template #id="{ record }">{{ record.id }}</template>
              <template #project_product="{ record }">{{
                formatProjectProductPath(record.project_product)
              }}</template>
              <template #module="{ record }">{{ formatModulePath(record.module) }}</template>
              <template #name="{ record }"
                ><a-link @click="openDetail(record)">{{ record.name }}</a-link></template
              >
              <template #interface_name="{ record }">
                <a-link @click="openInterfaceFlow(record)">{{ record.interface_name }}</a-link>
              </template>
              <template #case_interface="{ record }">
                <div class="mango-module-coverage__interface-cell">
                  <strong>{{ record.interface_name }}</strong>
                  <span
                    ><a-tag size="small" :color="methodTagColor(record.method, enumStore.colors)">{{
                      record.method
                    }}</a-tag>
                    <span class="mango-module-coverage__interface-url">{{ record.url }}</span></span
                  >
                </div>
              </template>
              <template #method="{ record }"
                ><a-tag size="small" :color="methodTagColor(record.method, enumStore.colors)">{{
                  record.method
                }}</a-tag></template
              >
              <template #test_scenario="{ record }">{{
                record.payload?.test_scenario || '-'
              }}</template>
              <template #core_assertion="{ record }">{{
                record.payload?.core_assertion || record.payload?.scenario_assertion || '-'
              }}</template>
              <template #test_ownership="{ record }">
                <a-tag size="small" :color="ownershipTagColor(record.test_ownership)">
                  {{ record.test_ownership || '-' }}
                </a-tag>
              </template>
              <template #scenario_layer="{ record }">
                <a-tag
                  size="small"
                  :color="enumTagColor(enumStore.api_case_scenario_layer, record.scenario_layer)"
                >
                  {{ enumTitle(enumStore.api_case_scenario_layer, record.scenario_layer) }}
                </a-tag>
              </template>
              <template #scenario_type="{ record }">
                <a-tag
                  size="small"
                  :color="enumTagColor(enumStore.api_case_scenario_type, record.scenario_type)"
                >
                  {{ enumTitle(enumStore.api_case_scenario_type, record.scenario_type) }}
                </a-tag>
              </template>
              <template #scenario_tags="{ record }">
                <ExecutionSceneTagGrid
                  :values="record.scenario_tags"
                  :options="enumStore.api_case_scenario_tag"
                  :colors="enumStore.colors"
                />
              </template>
              <template #change_status="{ record }">
                <a-tag
                  size="small"
                  :color="changeStatusTagColor(record.change_status, enumStore.colors)"
                >
                  {{ label(record.change_status) }}
                </a-tag>
              </template>
              <template #status="{ record }"
                ><a-tag size="small" :color="tagColor(record.status)">{{
                  label(record.status)
                }}</a-tag></template
              >
              <template #coverage_validity="{ record }">
                <a-tooltip
                  :content="record.coverage_validity_reason || label(record.coverage_validity)"
                >
                  <a-tag size="small" :color="tagColor(record.coverage_validity)">{{
                    label(record.coverage_validity)
                  }}</a-tag>
                </a-tooltip>
              </template>
              <template #deferred_reason="{ record }">
                <a-tooltip
                  v-if="record.status === 'deferred'"
                  :content="record.payload?.remark || '未填写暂不处理原因'"
                >
                  <span class="mango-module-coverage__deferred-reason">{{
                    record.payload?.remark || '未填写暂不处理原因'
                  }}</span>
                </a-tooltip>
                <span v-else>-</span>
              </template>
              <template #execution_result="{ record }"
                ><a-tag
                  size="small"
                  :color="executionResultTagColor(record.execution_result, enumStore.status_colors)"
                  >{{ label(record.execution_result) }}</a-tag
                ></template
              >
              <template #api_case="{ record }">
                <a-link v-if="record.api_case" @click="openApiCase(record.api_case)"
                  >#{{ record.api_case }} {{ record.api_case_name }}</a-link
                >
                <span v-else>{{
                  record.api_case ? `#${record.api_case} ${record.api_case_name || ''}` : '-'
                }}</span>
              </template>
              <template #commit="{ record }">{{
                shortCommit(record.current_commit || record.commit_sha)
              }}</template>
              <template #scan_mode="{ record }">{{ label(record.scan_mode) }}</template>
              <template #scope_type="{ record }">{{ label(record.scope_type) }}</template>
              <template #target_interface="{ record }">
                {{ record.target_interface ? `#${record.target_interface}` : '-' }}
              </template>
              <template #scan_status="{ record }"
                ><a-tag size="small" :color="tagColor(record.status)">{{
                  label(record.status)
                }}</a-tag></template
              >
              <template #case_count="{ record }">{{
                record.summary?.case_count ?? record.expected_case_count
              }}</template>
              <template #coverage_rate="{ record }">
                <div class="mango-module-coverage__coverage-cell">
                  <a-progress
                    size="small"
                    :percent="Number(record.coverage_rate || 0) / 100"
                    :show-text="false"
                  />
                  <span
                    >{{ record.effective_completed_case_count }}/{{
                      record.target_case_count
                    }}</span
                  >
                </div>
              </template>
              <template #coverage_status="{ record }">
                <a-tag size="small" :color="tagColor(record.coverage_status)">{{
                  coverageProgressLabels[record.coverage_status || ''] ||
                  label(record.coverage_status)
                }}</a-tag>
              </template>
              <template #coverage_policy="{ record }">
                <a-tag size="small" :color="tagColor(record.coverage_policy)">{{
                  enumStore.module_coverage_policy.find(
                    (option) => option.key === record.coverage_policy
                  )?.title || record.coverage_policy
                }}</a-tag>
              </template>
              <template #resolution_status="{ record }">
                <a-tooltip :content="record.resolution_reason || '已解析影响接口行为的代码链路'">
                  <a-tag size="small" :color="tagColor(record.resolution_status)">{{
                    label(record.resolution_status)
                  }}</a-tag>
                </a-tooltip>
              </template>
              <template #analysis_status="{ record }">
                <a-tooltip :content="record.analysis_reason || '暂无具体分析说明'">
                <a-tag size="small" :color="tagColor(record.analysis_status)">{{
                  interfaceSearchSelects[0].options.find(
                    (item) => item.value === record.analysis_status
                  )?.label || '未核实'
                }}</a-tag>
                </a-tooltip>
              </template>
              <template #lifecycle_status="{ record }">
                <a-tag size="small" :color="tagColor(record.lifecycle_status)">{{
                  label(record.lifecycle_status)
                }}</a-tag>
              </template>
              <template #api_info_binding="{ record }">
                <a-tooltip
                  :content="
                    record.api_info_binding_reason ||
                    (record.api_info_id
                      ? `已绑定 ApiInfo #${record.api_info_id}`
                      : label(record.api_info_binding_status))
                  "
                >
                  <a-link v-if="record.api_info_id" @click="openApiInfo(record.api_info_id)">
                    ApiInfo #{{ record.api_info_id }}
                  </a-link>
                  <a-tag v-else size="small" :color="tagColor(record.api_info_binding_status)">
                    {{ label(record.api_info_binding_status) }}
                  </a-tag>
                </a-tooltip>
              </template>
              <template #coverage_validity_stats="{ record }">
                <span class="mango-module-coverage__validity-stats">
                  <b>{{ record.effective_valid_case_count || 0 }}</b> 有效 ·
                  <b>{{ record.effective_pending_review_case_count || 0 }}</b> 待复核 ·
                  <b>{{ record.effective_invalid_case_count || 0 }}</b> 失效
                </span>
              </template>
              <template #first_scan="{ record }">#{{ record.first_scan_id || '-' }}</template>
              <template #latest_scan="{ record }">#{{ record.latest_scan_id || '-' }}</template>
              <template #latest_commit="{ record }">{{
                shortCommit(record.latest_commit_sha)
              }}</template>
              <template #sync_action="{ record }">
                <a-tag size="small" :color="tagColor(record.sync_action)">{{
                  label(record.sync_action)
                }}</a-tag>
              </template>
              <template #created="{ record }">{{ record.summary?.created ?? '-' }}</template>
              <template #updated="{ record }">{{ record.summary?.updated ?? '-' }}</template>
              <template #removed="{ record }">{{ record.summary?.removed ?? '-' }}</template>
              <template #interface_changes="{ record }">
                +{{ record.summary?.interface_created || 0 }} · ~{{
                  record.summary?.interface_updated || 0
                }}
                · -{{ record.summary?.interface_removed || 0 }}
              </template>
              <template #actions="{ record }">
                <MangoTableActions :actions="rowActions(record)" />
              </template>
            </a-table>
          </StickyHorizontalTable>
        </div>
        <template #footer
          ><TableFooter v-if="activeTab !== 'overview'" :pagination="pagination" compact-pages
        /></template>
      </ProjectProductNavigationWorkbench>
    </template>
  </TableBody>

  <CoverageCaseDetailDrawer
    ref="detailDrawer"
    @history="historyDrawer?.open($event)"
    @locate="locateDetailFlow"
    @case="openApiCase"
  />
  <CoverageBindingModal ref="bindingModal" @saved="reloadAll" />
  <CoveragePolicyModal ref="policyModal" @saved="reloadAll" />
  <CaseFlowDrawer ref="flowDrawer" />
  <CaseDiffDrawer ref="diffDrawer" />
  <CaseHistoryDrawer ref="historyDrawer" />
  <ScanDetailDrawer ref="scanDrawer" />
  <InterfaceHistoryDrawer ref="interfaceHistoryDrawer" />
  <BaseSidePanel
    v-model:visible="assetPanel.visible"
    :title="assetPanelTitle"
    width="calc(92vw - 150px)"
    mode="page"
    @cancel="assetPanel.visible = false"
  >
    <Suspense :key="`${assetPanel.kind}:${assetPanel.id}`">
      <template #default>
        <div class="mango-module-coverage__asset-page">
          <ApiInfoDetails
            v-if="assetPanel.visible && assetPanel.kind === 'info'"
            embedded
            :api-info-id="assetPanel.id"
            @close="assetPanel.visible = false"
          />
          <ApiCaseDetails
            v-else-if="assetPanel.visible && assetPanel.kind === 'case'"
            embedded
            :case-id="assetPanel.id"
            @close="assetPanel.visible = false"
          />
        </div>
      </template>
      <template #fallback>
        <MangoPanelSpin :loading="true" class="mango-module-coverage__asset-loading"
          >正在加载详情…</MangoPanelSpin
        >
      </template>
    </Suspense>
  </BaseSidePanel>
</template>

<script lang="ts" setup>
  import { useDebouncedSearch } from '@/hooks/useDebouncedSearch'

import { reportLoadError } from '@/utils/load-error'

  import {
    computed,
    defineAsyncComponent,
    onActivated,
    onBeforeUnmount,
    onDeactivated,
    reactive,
    ref,
  } from 'vue'
  import { Modal } from '@arco-design/web-vue'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import MangoPanelSpin from '@/components/feedback/MangoPanelSpin.vue'
  import { useEnum } from '@/store/modules/get-enum'
  import TableBody from '@/components/table/TableBody.vue'
  import TableFooter from '@/components/table/TableFooter.vue'
  import TableHeader from '@/components/table/TableHeader.vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import StickyHorizontalTable from '@/components/table/StickyHorizontalTable.vue'
  import ExecutionSceneTagGrid from '@/components/display/ExecutionSceneTagGrid.vue'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import { usePagination } from '@/hooks/table'
  import { formatModulePath, formatProjectProductPath } from '@/utils/business-format'
  import {
    archiveCoverageCases,
    getCoverageCases,
    getCoverageInterfaces,
    getCoverageScans,
    getCoverageOverview,
  } from '@/api/apitest/module-coverage'
  import type {
    CoverageOverview as CoverageOverviewData,
    CoverageModuleOverview,
    PageResult,
  } from '@/api/apitest/module-coverage'
  import CoverageOverview from './components/CoverageOverview.vue'
  import CaseDiffDrawer from './components/CaseDiffDrawer.vue'
  import CaseFlowDrawer from './components/CaseFlowDrawer.vue'
  import CaseHistoryDrawer from './components/CaseHistoryDrawer.vue'
  import InterfaceHistoryDrawer from './components/InterfaceHistoryDrawer.vue'
  import ScanDetailDrawer from './components/ScanDetailDrawer.vue'
  import CoverageCaseDetailDrawer from './components/CoverageCaseDetailDrawer.vue'
  import CoverageBindingModal from './components/CoverageBindingModal.vue'
  import CoveragePolicyModal from './components/CoveragePolicyModal.vue'
  import {
    caseColumns,
    apiInfoBindingOptions,
    changeStatusTagColor,
    changeStatusOptions,
    interfaceColumns,
    tableScrollXByTab,
    interfaceStatusOptions,
    interfaceSearchSelects,
    coverageProgressLabels,
    labels,
    executionResultTagColor,
    methodTagColor,
    ownershipTagColor,
    scanColumns,
    statusOptions,
    tagColor,
    validityOptions,
  } from './config'
  import { coverageQuery, createCoverageFilters } from './query'
  import type { CoverageRecord, CoverageTab } from './types'
  const ApiInfoDetails = defineAsyncComponent(
    () => import('@/views/apitest/info/details/index.vue')
  )
  const ApiCaseDetails = defineAsyncComponent(
    () => import('@/views/apitest/case/details/index.vue')
  )
  const assetPanel = reactive<{ visible: boolean; kind: 'info' | 'case'; id: number }>({
    visible: false,
    kind: 'info',
    id: 0,
  })
  const assetPanelTitle = computed(() =>
    assetPanel.kind === 'info'
      ? `接口管理详情 / ApiInfo #${assetPanel.id}`
      : `API 用例详情 / Case #${assetPanel.id}`
  )
  const enumStore = useEnum()
  const projectProductId = ref<number>(),
    moduleId = ref<number>(),
    moduleIds = ref<Array<string | number>>([])
  const activeTab = ref<CoverageTab>('overview'),
    filters = reactive(createCoverageFilters())
  const overview = ref<CoverageOverviewData>(),
    overviewLoading = ref(false),
    overviewError = ref(false)
  const rows = ref<CoverageRecord[]>([]),
    loading = ref(false),
    rowsError = ref(false)
  const pagination = usePagination(loadRows, () => loading)
  let pageActive = true,
    scopeVersion = 0,
    overviewRequest = 0,
    rowsRequest = 0,
    overviewScope = ''
  let archiveConfirmation: ReturnType<typeof Modal.warning> | null = null
  const archivingIds = reactive(new Set<number>())
  const detailDrawer = ref<InstanceType<typeof CoverageCaseDetailDrawer>>()
  const bindingModal = ref<InstanceType<typeof CoverageBindingModal>>()
  const policyModal = ref<InstanceType<typeof CoveragePolicyModal>>()
  const flowDrawer = ref<InstanceType<typeof CaseFlowDrawer>>()
  const diffDrawer = ref<InstanceType<typeof CaseDiffDrawer>>()
  const historyDrawer = ref<InstanceType<typeof CaseHistoryDrawer>>()
  const scanDrawer = ref<InstanceType<typeof ScanDetailDrawer>>()
  const interfaceHistoryDrawer = ref<InstanceType<typeof InterfaceHistoryDrawer>>()
  const activeColumns = computed(() =>
    activeTab.value === 'interfaces'
      ? interfaceColumns
      : activeTab.value === 'cases'
      ? caseColumns
      : scanColumns
  )
  const tableScrollX = computed(() => tableScrollXByTab[activeTab.value] || tableScrollXByTab.scans)
  const label = (value?: string) => (value ? labels[value] || value : '-')
  const shortCommit = (value?: string) => (value ? value.slice(0, 12) : '-')
  const enumTitle = (options: Array<{ key: string | number; title: string }>, value: unknown) =>
    options.find((item) => String(item.key) === String(value))?.title || '-'
  const enumTagColor = (options: Array<{ key: string | number; title: string }>, value: unknown) =>
    enumStore.colors[
      Math.max(
        0,
        options.findIndex((item) => String(item.key) === String(value))
      )
    ]
  function query(tab = activeTab.value) {
    return coverageQuery(
      tab,
      filters,
      {
        projectProduct: projectProductId.value,
        module: moduleId.value,
        moduleIds: moduleIds.value,
      },
      pagination.page,
      pagination.pageSize
    )
  }
  function closeWindows() {
    detailDrawer.value?.close()
    bindingModal.value?.close()
    policyModal.value?.close()
    flowDrawer.value?.close()
    diffDrawer.value?.close()
    historyDrawer.value?.close()
    scanDrawer.value?.close()
    interfaceHistoryDrawer.value?.close()
    assetPanel.visible = false
    archiveConfirmation?.close()
    archiveConfirmation = null
  }
  function resetRowScope() {
    ++rowsRequest
    rows.value = []
    pagination.setTotalSize(0)
    loading.value = false
  }
  function invalidateScope() {
    ++scopeVersion
    ++overviewRequest
    resetRowScope()
    overviewLoading.value = false
    closeWindows()
  }
  async function loadRows() {
    if (!pageActive) return
    if (activeTab.value === 'overview') return loadOverview()
    const request = ++rowsRequest,
      params = query(),
      tab = activeTab.value
    loading.value = true
    rowsError.value = false
    try {
      const response = await (tab === 'interfaces'
        ? getCoverageInterfaces(params)
        : tab === 'cases'
        ? getCoverageCases(params)
        : getCoverageScans(params))
      if (!pageActive || request !== rowsRequest) return
      const result: PageResult<CoverageRecord> = response.data
      rows.value = result?.items || []
      pagination.setTotalSize(result?.count || 0)
    } catch (loadFailure0) {
      if (pageActive && request === rowsRequest) (reportLoadError(loadFailure0, "加载失败，请重试", false), rowsError.value = true)
    } finally {
      if (request === rowsRequest) loading.value = false
    }
  }
  function reloadAll() {
    return activeTab.value === 'overview' ? loadOverview() : loadRows()
  }
  async function loadOverview() {
    if (!pageActive || activeTab.value !== 'overview') return
    const request = ++overviewRequest,
      params = query('overview'),
      scope = JSON.stringify(params)
    overviewLoading.value = true
    overviewError.value = false
    if (scope !== overviewScope) overview.value = undefined
    overviewScope = scope
    try {
      const response = await getCoverageOverview(params)
      if (pageActive && request === overviewRequest) overview.value = response.data
    } catch (loadFailure0) {
      if (pageActive && request === overviewRequest) (reportLoadError(loadFailure0, "加载失败，请重试", false), overviewError.value = true)
    } finally {
      if (request === overviewRequest) overviewLoading.value = false
    }
  }
  function resetTabFilters() {
    resetRowScope()
    const { repository_key, branch } = filters
    Object.assign(filters, createCoverageFilters(), { repository_key, branch })
    pagination.page = 1
  }
  function onTabChange() {
    invalidateScope()
    resetTabFilters()
    void reloadAll()
  }
  function search() {
    invalidateScope()
    pagination.page = 1
    void reloadAll()
  }
  function resetFilters() {
    Object.assign(filters, createCoverageFilters())
    search()
  }
  function onNavigationFilterChange(filter: {
    projectProduct: string | number | null
    module: string | number | null
    moduleIds?: Array<string | number>
  }) {
    invalidateScope()
    projectProductId.value =
      filter.projectProduct == null ? undefined : Number(filter.projectProduct)
    moduleId.value = filter.module == null ? undefined : Number(filter.module)
    moduleIds.value = [...(filter.moduleIds || [])]
    pagination.page = 1
    void reloadAll()
  }
  function drillOverview(
    row: CoverageModuleOverview,
    tab: CoverageTab,
    drillQuery: Record<string, string[]> = {}
  ) {
    const descendants = new Set([row.id]),
      modules = overview.value?.modules || []
    let previousSize = 0
    while (descendants.size !== previousSize) {
      previousSize = descendants.size
      for (const item of modules)
        if (item.parent_id != null && descendants.has(item.parent_id)) descendants.add(item.id)
    }
    invalidateScope()
    projectProductId.value = row.project_product_id
    moduleId.value = row.id
    moduleIds.value = [...descendants]
    activeTab.value = tab
    resetTabFilters()
    if (drillQuery.analysis_statuses) filters.analysis_statuses = [...drillQuery.analysis_statuses]
    if (drillQuery.coverage_statuses) filters.coverage_statuses = [...drillQuery.coverage_statuses]
    void reloadAll()
  }
  function openApiCase(id: number) {
    if (id) Object.assign(assetPanel, { visible: true, kind: 'case', id })
  }
  function openApiInfo(id: number) {
    if (id) Object.assign(assetPanel, { visible: true, kind: 'info', id })
  }
  function openInterfaceFlow(row: CoverageRecord, caseId?: number) {
    return flowDrawer.value?.open(row, caseId)
  }
  function openOverviewInterface(id: number) {
    return openInterfaceFlow({ id })
  }
  function locateDetailFlow(row: CoverageRecord) {
    detailDrawer.value?.close()
    activeTab.value = 'interfaces'
    resetTabFilters()
    void loadRows()
    void openInterfaceFlow(row, row.id)
  }
  function openDetail(row: CoverageRecord) {
    return detailDrawer.value?.open(row.id)
  }
  function openBinding(row: CoverageRecord) {
    return bindingModal.value?.open(row)
  }
  function openCoveragePolicy(row: CoverageRecord) {
    policyModal.value?.open(row)
  }
  function archiveRow(row: CoverageRecord) {
    if (!pageActive || archiveConfirmation || archivingIds.has(row.id)) return
    const id = row.id,
      version = scopeVersion
    const dialog = Modal.warning({
      title: '归档模块覆盖 Case',
      content: `确认归档「${row.name}」？绑定的 ApiCase 不会被删除。`,
      hideCancel: false,
      okButtonProps: { status: 'danger' },
      async onBeforeOk() {
        if (!pageActive || version !== scopeVersion || archivingIds.has(id)) return false
        archivingIds.add(id)
        try {
          await archiveCoverageCases([id])
          if (pageActive && version === scopeVersion) await reloadAll()
          return true
        } catch {
          return false
        } finally {
          archivingIds.delete(id)
        }
      },
      onClose() {
        if (archiveConfirmation === dialog) archiveConfirmation = null
      },
    })
    archiveConfirmation = dialog
  }
  const caseActions = (row: CoverageRecord) => [
    { label: '详情', onClick: () => openDetail(row) },
    { label: '定位流程', onClick: () => openInterfaceFlow(row, row.id) },
    { label: '差异', onClick: () => diffDrawer.value?.open(row.id) },
    { label: row.api_case ? '重新绑定' : '绑定Case', onClick: () => openBinding(row) },
    {
      label: '归档',
      danger: true,
      loading: archivingIds.has(row.id),
      onClick: () => archiveRow(row),
    },
  ]
  const scanActions = (row: CoverageRecord) => [
    { label: '详情', onClick: () => scanDrawer.value?.open(row.id) },
  ]
  const interfaceActions = (row: CoverageRecord) => [
    { label: '编辑', onClick: () => openCoveragePolicy(row) },
    { label: '查看全景', onClick: () => openInterfaceFlow(row) },
    { label: '扫描历史', onClick: () => interfaceHistoryDrawer.value?.open(row.id) },
  ]
  const rowActions = (row: CoverageRecord) =>
    activeTab.value === 'interfaces'
      ? interfaceActions(row)
      : activeTab.value === 'cases'
      ? caseActions(row)
      : scanActions(row)
  function deactivate() {
    pageActive = false
    invalidateScope()
  }
  onDeactivated(deactivate)
  onBeforeUnmount(deactivate)
  onActivated(() => {
    if (!pageActive) {
      pageActive = true
      void reloadAll()
    }
  })

  const autoSearch = useDebouncedSearch(search, () => filters)
</script>

<style lang="less" scoped>
  .mango-module-coverage__asset-page,
  .mango-module-coverage__asset-loading {
    height: 100%;
    min-height: 0;
  }
  .mango-module-coverage__content {
    display: flex;
    flex: 1;
    min-width: 0;
    min-height: 0;
    flex-direction: column;
    gap: var(--m-page-gap);
  }
  .mango-module-coverage__deferred-reason {
    display: block;
    overflow: hidden;
    color: var(--m-text-2);
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .mango-module-coverage__interface-cell {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 4px;
  }
  .mango-module-coverage__interface-cell strong,
  .mango-module-coverage__interface-cell span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .mango-module-coverage__interface-cell span {
    display: flex;
    min-width: 0;
    align-items: center;
    gap: 6px;
    color: var(--m-text-2);
  }
  .mango-module-coverage__interface-cell :deep(.arco-tag) {
    flex: 0 0 auto;
  }
  .mango-module-coverage__interface-url {
    display: block !important;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .mango-module-coverage__coverage-cell {
    display: grid;
    grid-template-columns: minmax(72px, 1fr) 52px;
    align-items: center;
    gap: var(--m-page-gap);
  }
  .mango-module-coverage__coverage-cell span {
    color: var(--m-text-2);
    font-variant-numeric: tabular-nums;
  }
  .mango-module-coverage__validity-stats {
    color: var(--m-text-2);
    font-size: 12px;
    white-space: nowrap;
  }
  .mango-module-coverage__validity-stats b {
    color: var(--m-text);
    font-weight: 600;
  }
</style>
