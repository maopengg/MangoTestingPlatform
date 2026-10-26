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
        @search="search"
        @reset-search="resetFilters"
      >
        <template #search>
          <a-form :model="filters" layout="inline" @keyup.enter="search">
            <a-form-item label="仓库">
              <a-input v-model="filters.repository_key" allow-clear placeholder="仓库标识" />
            </a-form-item>
            <a-form-item label="分支">
              <a-input v-model="filters.branch" allow-clear placeholder="分支名称" />
            </a-form-item>
            <a-form-item v-if="activeTab === 'cases'" label="Case标题">
              <a-input v-model="filters.name" allow-clear placeholder="Case标题" />
            </a-form-item>
            <a-form-item v-if="activeTab === 'cases'" label="接口名称">
              <a-input v-model="filters.interface_name" allow-clear placeholder="接口名称" />
            </a-form-item>
            <a-form-item v-if="activeTab === 'interfaces'" label="接口">
              <a-input v-model="filters.name" allow-clear placeholder="接口名称或 URL" />
            </a-form-item>
            <a-form-item v-if="activeTab === 'interfaces'" label="接口状态">
              <a-select
                v-model="filters.interface_status"
                allow-clear
                placeholder="接口状态"
                :options="interfaceStatusOptions"
              />
            </a-form-item>
            <a-form-item v-if="activeTab === 'interfaces'" label="ApiInfo">
              <a-select
                v-model="filters.api_info_binding_status"
                allow-clear
                placeholder="绑定状态"
                :options="apiInfoBindingOptions"
              />
            </a-form-item>
            <a-form-item v-if="activeTab === 'cases'" label="当前状态">
              <a-select
                v-model="filters.status"
                allow-clear
                placeholder="当前状态"
                :options="statusOptions"
              />
            </a-form-item>
            <a-form-item v-if="activeTab === 'cases'" label="变更状态">
              <a-select
                v-model="filters.change_status"
                allow-clear
                placeholder="变更状态"
                :options="changeStatusOptions"
              />
            </a-form-item>
            <a-form-item v-if="activeTab === 'cases'" label="覆盖有效性">
              <a-select
                v-model="filters.coverage_validity"
                allow-clear
                placeholder="覆盖有效性"
                :options="validityOptions"
              />
            </a-form-item>
            <a-form-item v-if="activeTab === 'cases'" label="测试层级">
              <a-select
                v-model="filters.scenario_layer"
                allow-clear
                placeholder="测试层级"
                :options="enumStore.api_case_scenario_layer"
                :field-names="{ value: 'key', label: 'title' }"
              />
            </a-form-item>
            <a-form-item v-if="activeTab === 'cases'" label="验证类型">
              <a-select
                v-model="filters.scenario_type"
                allow-clear
                placeholder="验证类型"
                :options="enumStore.api_case_scenario_type"
                :field-names="{ value: 'key', label: 'title' }"
              />
            </a-form-item>
            <a-form-item v-if="activeTab === 'cases'" label="执行场景">
              <a-select
                v-model="filters.scenario_tag"
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
              <template #owner_module="{ record }">
                <span v-if="record.owner_module">
                  {{ formatModulePath(record.owner_module) }}
                  <a-tag v-if="record.is_cross_module_reuse" size="small" color="arcoblue">
                    跨模块复用
                  </a-tag>
                </span>
                <span v-else>-</span>
              </template>
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
                <a-link
                  v-if="record.api_case && permissionStore.hasPermission('api.case:detail')"
                  @click="openApiCase(record.api_case)"
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
                  label(record.coverage_status)
                }}</a-tag>
              </template>
              <template #resolution_status="{ record }">
                <a-tooltip :content="record.resolution_reason || '已解析影响接口行为的代码链路'">
                  <a-tag size="small" :color="tagColor(record.resolution_status)">{{
                    label(record.resolution_status)
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
                  <a-link
                    v-if="record.api_info_id && permissionStore.hasPermission('api.info:detail')"
                    @click="openApiInfo(record.api_info_id)"
                  >
                    <a-tag size="small" :color="tagColor(record.api_info_binding_status)">
                      ApiInfo #{{ record.api_info_id }}
                    </a-tag>
                  </a-link>
                  <a-tag v-else size="small" :color="tagColor(record.api_info_binding_status)">
                    {{
                      record.api_info_id
                        ? `ApiInfo #${record.api_info_id}`
                        : label(record.api_info_binding_status)
                    }}
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

  <a-drawer v-model:visible="detailVisible" title="模块覆盖 Case" width="820px" unmount-on-close>
    <a-spin :loading="detailLoading">
      <a-descriptions v-if="detail.id" :column="2" bordered size="small">
        <a-descriptions-item label="当前状态" :span="2">{{
          label(detail.status)
        }}</a-descriptions-item>
        <a-descriptions-item label="来源Key" :span="2">{{ detail.source_key }}</a-descriptions-item>
        <a-descriptions-item label="仓库/分支" :span="2"
          >{{ detail.repository_key }} / {{ detail.branch }}</a-descriptions-item
        >
        <a-descriptions-item label="接口" :span="2"
          >{{ detail.method }} {{ detail.url }}</a-descriptions-item
        >
        <a-descriptions-item label="Case标题" :span="2">{{ detail.name }}</a-descriptions-item>
        <a-descriptions-item label="测试场景" :span="2">{{
          detail.payload?.test_scenario || '-'
        }}</a-descriptions-item>
        <a-descriptions-item label="核心断言" :span="2">{{
          detail.payload?.core_assertion || detail.payload?.scenario_assertion || '-'
        }}</a-descriptions-item>
        <a-descriptions-item label="测试归属">{{
          detail.test_ownership || '-'
        }}</a-descriptions-item>
        <a-descriptions-item label="测试层级">
          {{ enumTitle(enumStore.api_case_scenario_layer, detail.scenario_layer) }}
        </a-descriptions-item>
        <a-descriptions-item label="验证类型">
          {{ enumTitle(enumStore.api_case_scenario_type, detail.scenario_type) }}
        </a-descriptions-item>
        <a-descriptions-item label="执行场景">
          {{ enumTitles(enumStore.api_case_scenario_tag, detail.scenario_tags) }}
        </a-descriptions-item>
        <a-descriptions-item label="前置条件" :span="2">{{
          detail.payload?.preconditions || '-'
        }}</a-descriptions-item>
        <a-descriptions-item label="数据策略" :span="2">{{
          detail.payload?.data_strategy || '-'
        }}</a-descriptions-item>
        <a-descriptions-item label="清理策略" :span="2">{{
          detail.payload?.cleanup_strategy || '-'
        }}</a-descriptions-item>
        <a-descriptions-item label="ApiCase">{{
          detail.api_case ? `#${detail.api_case} ${detail.api_case_name || ''}` : '未绑定'
        }}</a-descriptions-item>
        <a-descriptions-item label="Commit">{{
          shortCommit(detail.current_commit)
        }}</a-descriptions-item>
        <a-descriptions-item
          :label="detail.status === 'deferred' ? '暂不处理原因' : '备注'"
          :span="2"
          >{{ detail.payload?.remark || '-' }}</a-descriptions-item
        >
      </a-descriptions>
      <h4>代码证据</h4>
      <pre class="mango-code-panel mango-module-coverage__evidence">{{
        pretty(detail.payload?.code_evidence)
      }}</pre>
      <div class="mango-module-coverage__drawer-actions">
        <a-button
          v-permission="'api.module_coverage:detail'"
          size="small"
          @click="historyDrawer?.open(detail.id)"
          >扫描历史</a-button
        >
        <a-button size="small" @click="locateDetailFlow">定位到接口图</a-button>
        <a-button
          v-if="detail.api_case"
          v-permission="'api.case:detail'"
          size="small"
          type="primary"
          @click="openApiCase(detail.api_case)"
          >打开 ApiCase</a-button
        >
      </div>
    </a-spin>
  </a-drawer>

  <a-modal
    v-model:visible="bindingVisible"
    title="绑定已有 ApiCase"
    width="540px"
    :ok-loading="bindingLoading"
    @ok="saveBinding"
  >
    <a-form layout="horizontal" :model="bindingForm">
      <a-form-item label="ApiCase" required>
        <a-select
          v-model="bindingForm.apiCaseId"
          allow-search
          :options="apiCaseOptions"
          :field-names="{ value: 'key', label: 'title' }"
        />
      </a-form-item>
    </a-form>
  </a-modal>

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
  import { computed, defineAsyncComponent, reactive, ref } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import usePermissionStore from '@/store/modules/permission'
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
  import { getApiCaseName } from '@/api/apitest/case'
  import {
    archiveCoverageCases,
    bindCoverageApiCase,
    getCoverageCaseDetail,
    getCoverageCases,
    getCoverageInterfaces,
    getCoverageScans,
    getCoverageOverview,
  } from '@/api/apitest/module-coverage'
  import type {
    CoverageOverview as CoverageOverviewData,
    CoverageModuleOverview,
  } from '@/api/apitest/module-coverage'
  import CoverageOverview from './components/CoverageOverview.vue'
  import CaseDiffDrawer from './components/CaseDiffDrawer.vue'
  import CaseFlowDrawer from './components/CaseFlowDrawer.vue'
  import CaseHistoryDrawer from './components/CaseHistoryDrawer.vue'
  import InterfaceHistoryDrawer from './components/InterfaceHistoryDrawer.vue'
  import ScanDetailDrawer from './components/ScanDetailDrawer.vue'
  import {
    caseColumns,
    apiInfoBindingOptions,
    changeStatusTagColor,
    changeStatusOptions,
    interfaceColumns,
    tableScrollXByTab,
    interfaceStatusOptions,
    labels,
    executionResultTagColor,
    methodTagColor,
    ownershipTagColor,
    scanColumns,
    statusOptions,
    tagColor,
    validityOptions,
  } from './config'

  const permissionStore = usePermissionStore()
  const ApiInfoDetails = defineAsyncComponent(
    () => import('@/views/apitest/info/details/index.vue')
  )
  const ApiCaseDetails = defineAsyncComponent(
    () => import('@/views/apitest/case/details/index.vue')
  )
  const assetPanel = reactive({ visible: false, kind: 'info', id: 0 })
  const assetPanelTitle = computed(() =>
    assetPanel.kind === 'info'
      ? `接口管理详情 / ApiInfo #${assetPanel.id}`
      : `API 用例详情 / Case #${assetPanel.id}`
  )
  const enumStore = useEnum()
  const projectProductId = ref<number>()
  const moduleId = ref<number>()
  const moduleIds = ref<Array<string | number>>([])
  const activeTab = ref('overview')
  const overview = ref<CoverageOverviewData>()
  const overviewLoading = ref(false)
  const overviewError = ref(false)
  let overviewRequest = 0
  let overviewScope = ''
  let rowsRequest = 0
  const rows = ref<any[]>([])
  const loading = ref(false)
  const filters = reactive<any>({
    repository_key: '',
    branch: '',
    name: '',
    interface_name: '',
    status: undefined,
    change_status: undefined,
    coverage_validity: undefined,
    interface_status: undefined,
    api_info_binding_status: undefined,
    scenario_layer: undefined,
    scenario_type: undefined,
    scenario_tag: undefined,
  })
  const pagination = usePagination(loadRows, () => loading)
  const detailVisible = ref(false)
  const detailLoading = ref(false)
  const detail = reactive<any>({})
  const bindingVisible = ref(false)
  const bindingLoading = ref(false)
  const bindingForm = reactive<any>({
    coverageCaseId: undefined,
    moduleId: undefined,
    apiCaseId: undefined,
  })
  const apiCaseOptions = ref<any[]>([])
  const flowDrawer = ref<InstanceType<typeof CaseFlowDrawer>>()
  const diffDrawer = ref<InstanceType<typeof CaseDiffDrawer>>()
  const historyDrawer = ref<InstanceType<typeof CaseHistoryDrawer>>()
  const scanDrawer = ref<InstanceType<typeof ScanDetailDrawer>>()
  const interfaceHistoryDrawer = ref<InstanceType<typeof InterfaceHistoryDrawer>>()

  const activeColumns = computed(() => {
    if (activeTab.value === 'interfaces') return interfaceColumns
    if (activeTab.value === 'cases') return caseColumns
    return scanColumns
  })
  const tableScrollX = computed(() => {
    return tableScrollXByTab[activeTab.value] || tableScrollXByTab.scans
  })

  const label = (value: string) => labels[value] || value || '-'
  const shortCommit = (value?: string) => (value ? value.slice(0, 12) : '-')
  const pretty = (value: unknown) => JSON.stringify(value || [], null, 2)
  const enumTitle = (options: Array<{ key: string | number; title: string }>, value: unknown) =>
    options.find((item) => String(item.key) === String(value))?.title || '-'
  const enumTitles = (
    options: Array<{ key: string | number; title: string }>,
    values?: Array<string | number>
  ) => (values?.length ? values.map((value) => enumTitle(options, value)).join('、') : '-')
  const enumTagColor = (
    options: Array<{ key: string | number; title: string }>,
    value: unknown
  ) => {
    const index = options.findIndex((item) => String(item.key) === String(value))
    return enumStore.colors[index >= 0 ? index : 0]
  }

  async function loadRows() {
    if (activeTab.value === 'overview') return loadOverview()
    const request = ++rowsRequest
    loading.value = true
    try {
      const query: Record<string, unknown> = {
        project_product: projectProductId.value,
        repository_key: filters.repository_key || undefined,
        branch: filters.branch || undefined,
        page: pagination.page,
        pageSize: pagination.pageSize,
      }
      applyModuleFilter(query)
      let response: any
      if (activeTab.value === 'interfaces') {
        query.name = filters.name || undefined
        query.status = filters.interface_status
        query.api_info_binding_status = filters.api_info_binding_status
        query.include_removed = filters.interface_status === 'removed' ? true : undefined
        response = await getCoverageInterfaces(query)
      } else if (activeTab.value === 'cases') {
        Object.assign(query, {
          name: filters.name || undefined,
          interface_name: filters.interface_name || undefined,
          status: filters.status,
          change_status: filters.change_status,
          coverage_validity: filters.coverage_validity,
          scenario_layer: filters.scenario_layer,
          scenario_type: filters.scenario_type,
          scenario_tag: filters.scenario_tag,
          include_removed: true,
        })
        response = await getCoverageCases(query)
      } else response = await getCoverageScans(query)
      if (request === rowsRequest) {
        rows.value = response.data?.items || []
        pagination.setTotalSize(response.data?.count || 0)
      }
    } finally {
      if (request === rowsRequest) loading.value = false
    }
  }

  async function reloadAll() {
    if (activeTab.value === 'overview') return loadOverview()
    await loadRows()
  }

  async function loadOverview() {
    const request = ++overviewRequest
    overviewLoading.value = true
    overviewError.value = false
    const query: Record<string, unknown> = {
      project_product: projectProductId.value,
      repository_key: filters.repository_key || undefined,
      branch: filters.branch || undefined,
    }
    applyModuleFilter(query)
    const scope = JSON.stringify(query)
    if (scope !== overviewScope) overview.value = undefined
    overviewScope = scope
    try {
      const response = await getCoverageOverview(query)
      if (request === overviewRequest) overview.value = response.data
    } catch {
      if (request === overviewRequest) overviewError.value = true
    } finally {
      if (request === overviewRequest) overviewLoading.value = false
    }
  }

  function drillOverview(row: CoverageModuleOverview, tab: string) {
    const descendants = new Set([row.id])
    const modules = overview.value?.modules || []
    let previousSize = 0
    while (descendants.size !== previousSize) {
      previousSize = descendants.size
      for (const item of modules) {
        if (item.parent_id && descendants.has(item.parent_id)) descendants.add(item.id)
      }
    }
    projectProductId.value = row.project_product_id
    moduleId.value = row.id
    moduleIds.value = [...descendants]
    activeTab.value = tab
    resetTabFilters()
    reloadAll()
  }

  function openOverviewInterface(id: number) {
    openInterfaceFlow({ id })
  }

  function applyModuleFilter(query: Record<string, unknown>) {
    if (moduleIds.value.length) query.module__in = moduleIds.value.join(',')
    else if (moduleId.value) query.module = moduleId.value
  }

  async function onNavigationFilterChange(filter: {
    projectProduct: any
    module: any
    moduleIds?: Array<string | number>
  }) {
    projectProductId.value = filter.projectProduct || undefined
    moduleId.value = filter.module || undefined
    moduleIds.value = filter.moduleIds || []
    pagination.page = 1
    await reloadAll()
  }

  function onTabChange() {
    resetTabFilters()
    reloadAll()
  }
  function resetTabFilters() {
    pagination.page = 1
    Object.assign(filters, {
      name: '',
      interface_name: '',
      status: undefined,
      change_status: undefined,
      coverage_validity: undefined,
      interface_status: undefined,
      api_info_binding_status: undefined,
      scenario_layer: undefined,
      scenario_type: undefined,
      scenario_tag: undefined,
    })
  }
  function search() {
    pagination.page = 1
    reloadAll()
  }
  function resetFilters() {
    Object.assign(filters, {
      repository_key: '',
      branch: '',
      name: '',
      interface_name: '',
      status: undefined,
      change_status: undefined,
      coverage_validity: undefined,
      interface_status: undefined,
      api_info_binding_status: undefined,
      scenario_layer: undefined,
      scenario_type: undefined,
      scenario_tag: undefined,
    })
    search()
  }
  function openApiCase(id: number) {
    if (!id || !permissionStore.hasPermission('api.case:detail')) return
    Object.assign(assetPanel, { visible: true, kind: 'case', id })
  }

  function openApiInfo(id: number) {
    if (!id || !permissionStore.hasPermission('api.info:detail')) return
    Object.assign(assetPanel, { visible: true, kind: 'info', id })
  }

  function openInterfaceFlow(row: any, caseId?: number) {
    flowDrawer.value?.open(row, caseId)
  }

  function locateDetailFlow() {
    const row = { ...detail }
    detailVisible.value = false
    activeTab.value = 'interfaces'
    pagination.page = 1
    loadRows()
    openInterfaceFlow(row, detail.id)
  }

  async function openDetail(row: any) {
    detailVisible.value = true
    detailLoading.value = true
    try {
      Object.assign(detail, (await getCoverageCaseDetail(row.id)).data || {})
    } finally {
      detailLoading.value = false
    }
  }

  async function openBinding(row: any) {
    Object.assign(bindingForm, {
      coverageCaseId: row.id,
      moduleId: row.module?.id,
      apiCaseId: row.api_case || undefined,
    })
    apiCaseOptions.value = (await getApiCaseName(bindingForm.moduleId)).data || []
    bindingVisible.value = true
  }

  async function saveBinding() {
    if (!bindingForm.apiCaseId) {
      Message.warning('请选择 ApiCase')
      return false
    }
    bindingLoading.value = true
    try {
      await bindCoverageApiCase(bindingForm.coverageCaseId, bindingForm.apiCaseId)
      bindingVisible.value = false
      Message.success('绑定成功')
      await reloadAll()
      return true
    } finally {
      bindingLoading.value = false
    }
  }

  function archiveRow(row: any) {
    Modal.warning({
      title: '归档模块覆盖 Case',
      content: `确认归档「${row.name}」？绑定的 ApiCase 不会被删除。`,
      hideCancel: false,
      onBeforeOk: async () => {
        await archiveCoverageCases([row.id])
        await reloadAll()
      },
    })
  }

  const caseActions = (row: any) => [
    { permission: 'api.module_coverage:detail', label: '详情', onClick: () => openDetail(row) },
    {
      permission: 'api.module_coverage:detail',
      label: '定位流程',
      onClick: () => openInterfaceFlow(row, row.id),
    },
    {
      permission: 'api.module_coverage:detail',
      label: '差异',
      onClick: () => diffDrawer.value?.open(row.id),
    },
    { label: row.api_case ? '重新绑定' : '绑定Case', onClick: () => openBinding(row) },
    {
      permission: 'api.module_coverage:delete',
      label: '归档',
      danger: true,
      onClick: () => archiveRow(row),
    },
  ]
  const scanActions = (row: any) => [
    {
      permission: 'api.module_coverage:detail',
      label: '详情',
      onClick: () => scanDrawer.value?.open(row.id),
    },
  ]
  const interfaceActions = (row: any) => [
    {
      permission: 'api.module_coverage:detail',
      label: '查看全景',
      onClick: () => openInterfaceFlow(row),
    },
    {
      permission: 'api.module_coverage:detail',
      label: '扫描历史',
      onClick: () => interfaceHistoryDrawer.value?.open(row.id),
    },
  ]
  const rowActions = (row: any) => {
    if (activeTab.value === 'interfaces') return interfaceActions(row)
    if (activeTab.value === 'cases') return caseActions(row)
    return scanActions(row)
  }
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
  .mango-module-coverage__evidence {
    min-height: 180px;
    max-height: 340px;
    overflow: auto;
    white-space: pre-wrap;
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
  .mango-module-coverage__drawer-actions {
    display: flex;
    justify-content: flex-end;
    gap: var(--m-page-gap);
    margin-top: var(--m-page-gap);
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
