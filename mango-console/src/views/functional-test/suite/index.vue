<template>
  <TableBody plain class="mango-detail-workbench-page" :sticky-horizontal-scroll="false">
    <template #header>
      <TableHeader :title="pageTitle" />

    </template>
    <template #default>
      <ProjectProductNavigationWorkbench
        ref="navigationCreateRef"
        contained-body
        :sticky-horizontal-scroll="false"
        show-modules
        :model-value="activeNavigationProjectProduct"
        :module-value="activeNavigationModule"
        :reset-key="sidebarResetKey"
        @filter-change="onNavigationFilterChange"
        @search="searchActiveView"
        @reset-search="resetActiveSearch"
      >
        <template #search>
          <a-form
            v-if="activeView === 'suite'"
            :model="{}"
            layout="inline"
            @keyup.enter="searchSuites"
          >
            <a-form-item v-for="item of conditionItems" :key="item.key" :label="item.label">
              <template v-if="item.type === 'input'">
                <a-input
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  allow-clear
                  @blur="searchSuites"
                  @clear="searchSuites"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'sync_status'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="fieldNames"
                  :options="enumStore.manual_test_sync_status"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="searchSuites"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'update_user'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="fieldNames"
                  :options="userOptions"
                  :loading="usersLoading"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="searchSuites"
                />
              </template>
            </a-form-item>
          </a-form>
          <a-form v-else :model="caseFilter" layout="inline" @keyup.enter="onCaseFilterChange">
            <a-form-item label="需求名称">
              <a-select
                v-model="caseFilter.requirement_name"
                :loading="requirementLoading"
                :options="requirementOptions"
                allow-clear
                allow-search
                placeholder="请选择需求名称"
                @change="onCaseRequirementChange"
              />
              <a-button
                v-if="requirementError"
                size="small"
                :loading="requirementLoading"
                @click="loadRequirementOptions"
                >重试需求选项</a-button
              >
            </a-form-item>
            <a-form-item label="用例编号">
              <a-input
                v-model="caseFilter.case_no"
                allow-clear
                placeholder="请输入用例编号"
                @blur="onCaseFilterChange"
                @clear="onCaseFilterChange"
              />
            </a-form-item>
            <a-form-item label="用例标题">
              <a-input
                v-model="caseFilter.title"
                allow-clear
                placeholder="请输入用例标题"
                @blur="onCaseFilterChange"
                @clear="onCaseFilterChange"
              />
            </a-form-item>
            <a-form-item label="测试类型">
              <a-select
                v-model="caseFilter.test_type"
                :field-names="fieldNames"
                :options="enumStore.manual_test_type"
                allow-clear
                allow-search
                placeholder="请选择测试类型"
                value-key="key"
                @change="onCaseTestTypeChange"
              />
            </a-form-item>
            <a-form-item label="测试层级">
              <a-select
                v-model="caseFilter.scenario_layer"
                :field-names="fieldNames"
                :options="enumStore.api_case_scenario_layer"
                allow-clear
                placeholder="请选择测试层级"
                @change="onCaseFilterChange"
              />
            </a-form-item>
            <a-form-item label="验证类型">
              <a-select
                v-model="caseFilter.scenario_type"
                :field-names="fieldNames"
                :options="enumStore.api_case_scenario_type"
                allow-clear
                placeholder="请选择验证类型"
                @change="onCaseFilterChange"
              />
            </a-form-item>
            <a-form-item label="执行场景">
              <a-select
                v-model="caseFilter.scenario_tag"
                :field-names="fieldNames"
                :options="enumStore.api_case_scenario_tag"
                allow-clear
                placeholder="请选择执行场景"
                @change="onCaseFilterChange"
              />
            </a-form-item>
            <a-form-item label="变更">
              <a-select
                v-model="caseFilter.change_status"
                :field-names="fieldNames"
                :options="enumStore.manual_test_change_status"
                allow-clear
                placeholder="请选择变更状态"
                @change="onCaseFilterChange"
              />
            </a-form-item>
            <a-form-item label="自动化影响">
              <a-select
                v-model="caseFilter.automation_impact_status"
                :field-names="fieldNames"
                :options="enumStore.manual_test_automation_impact_status"
                allow-clear
                placeholder="请选择自动化影响"
                @change="onCaseFilterChange"
              />
            </a-form-item>
          </a-form>
        </template>
        <template #toolbar>
          <a-space>
            <a-button
              v-if="activeView === 'suite'"
              size="small"
              type="primary"
              :disabled="writeBlocked || caseVisible"
              @click="openSuite()"
              data-testid="qa-views-functional-test-suite-button-新增需求"
            >
              新增需求
            </a-button>
            <a-button
              v-else
              size="small"
              :loading="exportLoading"
              @click="exportCases"
              data-testid="qa-views-functional-test-suite-button-导出"
            >
              导出
            </a-button>
          </a-space>
        </template>
        <div v-if="activeView === 'suite'" class="mango-functional-case-list-workbench">
          <section class="mango-functional-case-list-main">

            <div ref="suiteTableShellRef" class="mango-functional-suite-table">
              <a-table
                class="mango-native-scroll-table"
                :bordered="false"
                :columns="suiteColumns"
                :data="suites"
                :loading="suiteLoading"
                :pagination="false"
                :row-key="'id'"
                :scroll="{ x: suiteScrollWidth, y: '100%' }"
              >
                <template #columns>
                  <a-table-column v-for="item of suiteColumns" :key="item.key" v-bind="item">
                    <template v-if="item.key === 'requirement_name'" #cell="{ record }">
                      <a-link @click="goSuite(record)">{{ record.requirement_name || '-' }}</a-link>
                    </template>
                    <template v-else-if="item.key === 'project_product'" #cell="{ record }">
                      {{ formatProjectProductPath(record.project_product) }}
                    </template>
                    <template v-else-if="item.key === 'module'" #cell="{ record }">
                      <a-space :size="6">
                        <span>{{ formatModulePath(record.module) }}</span>
                        <a-tag
                          v-if="record.module?.level"
                          :color="enumColor(record.module.level - 1)"
                          size="small"
                        >
                          {{ record.module.level }}级
                        </a-tag>
                      </a-space>
                    </template>
                    <template v-else-if="item.key === 'owner'" #cell="{ record }">
                      {{ record.owner?.name || '-' }}
                    </template>
                    <template v-else-if="item.key === 'iteration_ref'" #cell="{ record }">
                      {{ record.iteration_ref?.name || record.iteration || '-' }}
                    </template>
                    <template v-else-if="item.key === 'priority'" #cell="{ record }">
                      <a-tag :color="enumColor(record.priority)" size="small">{{
                        enumTitle(enumStore.case_level, record.priority)
                      }}</a-tag>
                    </template>
                    <template v-else-if="item.key === 'development_owner'" #cell="{ record }">
                      {{ record.development_owner?.name || '-' }}
                    </template>
                    <template v-else-if="item.key === 'status'" #cell="{ record }">
                      <a-tag size="small">{{
                        enumTitle(enumStore.manual_test_suite_status, record.status)
                      }}</a-tag>
                    </template>
                    <template v-else-if="item.key === 'update_user'" #cell="{ record }">
                      {{ record.update_user?.name || record.update_user?.username || '-' }}
                    </template>
                    <template v-else-if="item.key === 'coverage'" #cell="{ record }">
                      <a-progress
                        :percent="Number(record.automation_coverage_percent || 0) / 100"
                        size="small"
                      />
                    </template>
                    <template v-else-if="item.key === 'test_progress'" #cell="{ record }">
                      <span v-if="record.test_metrics?.total"
                        >{{ record.test_metrics.executed || 0 }}/{{
                          record.test_metrics.total || 0
                        }}（{{ formatPercent(record.test_metrics.progress) }}）</span
                      >
                      <span v-else>-</span>
                    </template>
                    <template v-else-if="item.key === 'pass_rate'" #cell="{ record }">
                      {{
                        record.test_metrics?.total
                          ? formatPercent(record.test_metrics.pass_rate)
                          : '-'
                      }}
                    </template>
                    <template v-else-if="item.key === 'sync_status'" #cell="{ record }">
                      <a-tag :color="syncStatusColor(record.sync_status)" size="small">{{
                        enumTitle(enumStore.manual_test_sync_status, record.sync_status)
                      }}</a-tag>
                    </template>
                    <template v-else-if="item.key === 'last_sync_time'" #cell="{ record }">
                      {{ formatDateTime(record.last_sync_time) }}
                    </template>
                    <template v-else-if="item.key === 'actions'" #cell="{ record }">
                      <MangoTableActions
                        :actions="[
                          { label: '用例工作台', onClick: () => goSuiteWorkspace(record) },
                          {
                            label: '新版本',
                            disabled: writeBlocked,
                            onClick: () => openSuiteVersion(record),
                          },
                          {
                            label: '编辑',
                            disabled: writeBlocked,
                            onClick: () => openSuite(record),
                          },
                          {
                            label: '删除',
                            danger: true,
                            disabled: writeBlocked,
                            loading: deleting?.kind === 'suite' && deleting.id === record.id,
                            onClick: () => deleteSuite(record),
                          },
                        ]"
                      />
                    </template>
                  </a-table-column>
                </template>
              </a-table>
            </div>
          </section>
        </div>
        <div v-else class="mango-functional-case-list-workbench">
          <section class="mango-functional-case-list-main">
            <div v-if="false">
              <a-form :model="caseFilter" layout="inline">
                <a-form-item label="需求名称">
                  <a-select
                    v-model="caseFilter.requirement_name"
                    :loading="requirementLoading"
                    :options="requirementOptions"
                    allow-clear
                    allow-search
                    placeholder="请选择需求名称"
                    @change="onCaseRequirementChange"
                    data-testid="qa-views-functional-test-suite-select-请选择需求名称"
                  />
                </a-form-item>
                <a-form-item label="用例编号">
                  <a-input
                    v-model="caseFilter.case_no"
                    allow-clear
                    placeholder="请输入用例编号"
                    @blur="loadCases"
                    @clear="loadCases"
                    data-testid="qa-views-functional-test-suite-input-请输入用例编号"
                  />
                </a-form-item>
                <a-form-item label="用例标题">
                  <a-input
                    v-model="caseFilter.title"
                    allow-clear
                    placeholder="请输入用例标题"
                    @blur="loadCases"
                    @clear="loadCases"
                    data-testid="qa-views-functional-test-suite-input-请输入用例标题"
                  />
                </a-form-item>
                <a-form-item label="测试类型">
                  <a-select
                    v-model="caseFilter.test_type"
                    :field-names="fieldNames"
                    :options="enumStore.manual_test_type"
                    allow-clear
                    allow-search
                    placeholder="请选择测试类型"
                    value-key="key"
                    @change="onCaseTestTypeChange"
                    data-testid="qa-views-functional-test-suite-select-请选择测试类型"
                  />
                </a-form-item>
                <a-form-item label="测试层级">
                  <a-select
                    v-model="caseFilter.scenario_layer"
                    :field-names="fieldNames"
                    :options="enumStore.api_case_scenario_layer"
                    allow-clear
                    placeholder="请选择测试层级"
                    @change="onCaseFilterChange"
                    data-testid="qa-views-functional-test-suite-select-请选择测试层级"
                  />
                </a-form-item>
                <a-form-item label="验证类型">
                  <a-select
                    v-model="caseFilter.scenario_type"
                    :field-names="fieldNames"
                    :options="enumStore.api_case_scenario_type"
                    allow-clear
                    placeholder="请选择验证类型"
                    @change="onCaseFilterChange"
                    data-testid="qa-views-functional-test-suite-select-请选择验证类型"
                  />
                </a-form-item>
                <a-form-item label="执行场景">
                  <a-select
                    v-model="caseFilter.scenario_tag"
                    :field-names="fieldNames"
                    :options="enumStore.api_case_scenario_tag"
                    allow-clear
                    placeholder="请选择执行场景"
                    @change="onCaseFilterChange"
                    data-testid="qa-views-functional-test-suite-select-请选择执行场景"
                  />
                </a-form-item>
                <a-form-item label="变更">
                  <a-select
                    v-model="caseFilter.change_status"
                    :field-names="fieldNames"
                    :options="enumStore.manual_test_change_status"
                    allow-clear
                    placeholder="请选择变更状态"
                    @change="onCaseFilterChange"
                    data-testid="qa-views-functional-test-suite-select-请选择变更状态"
                  />
                </a-form-item>
                <a-form-item label="自动化影响">
                  <a-select
                    v-model="caseFilter.automation_impact_status"
                    :field-names="fieldNames"
                    :options="enumStore.manual_test_automation_impact_status"
                    allow-clear
                    placeholder="请选择自动化影响"
                    @change="onCaseFilterChange"
                    data-testid="qa-views-functional-test-suite-select-请选择自动化影响"
                  />
                </a-form-item>
                <a-form-item>
                  <a-space>
                    <a-button
                      size="small"
                      type="primary"
                      @click="loadCases"
                      data-testid="qa-views-functional-test-suite-button-查询"
                      >查询</a-button
                    >
                    <a-button
                      size="small"
                      @click="resetCaseSearch"
                      data-testid="qa-views-functional-test-suite-button-重置"
                      >重置</a-button
                    >
                    <a-button
                      size="small"
                      :loading="exportLoading"
                      @click="exportCases"
                      data-testid="qa-views-functional-test-suite-button-导出"
                      >导出</a-button
                    >
                  </a-space>
                </a-form-item>
              </a-form>
            </div>
            <div ref="caseTableShellRef" class="mango-functional-case-table-shell">

              <a-table
                class="mango-functional-case-list-table mango-native-scroll-table"
                :bordered="false"
                :columns="caseColumns"
                :data="cases"
                :loading="caseLoading"
                :pagination="false"
                :row-key="'id'"
                :scroll="{ x: caseScrollWidth, y: '100%' }"
              >
                <template #columns>
                  <a-table-column v-for="item of caseColumns" :key="item.key" v-bind="item">
                    <template v-if="item.key === 'title'" #cell="{ record }">
                      <a-link v-if="record.suite" @click="goSuite({ id: record.suite.id })">{{
                        record.title || '-'
                      }}</a-link>
                      <span v-else>{{ record.title || '-' }}</span>
                    </template>
                    <template v-else-if="item.key === 'suite'" #cell="{ record }">
                      {{ record.suite?.requirement_name || '-' }}
                    </template>
                    <template v-else-if="item.key === 'suite_iteration'" #cell="{ record }">
                      {{ record.suite?.iteration_ref?.name || record.suite?.iteration || '-' }}
                    </template>
                    <template v-else-if="item.key === 'test_types'" #cell="{ record }">
                      <a-space wrap :size="4">
                        <a-tag
                          v-for="type of record.test_types || []"
                          :key="type"
                          :color="enumColor(type)"
                          size="small"
                        >
                          {{ enumTitle(enumStore.manual_test_type, type) }}
                        </a-tag>
                      </a-space>
                    </template>
                    <template v-else-if="item.key === 'priority'" #cell="{ record }">
                      <a-tag :color="enumColor(record.priority)" size="small">{{
                        enumTitle(enumStore.case_level, record.priority)
                      }}</a-tag>
                    </template>
                    <template v-else-if="item.key === 'scenario_layer'" #cell="{ record }">
                      <a-tag :color="enumColor(record.scenario_layer)" size="small">{{
                        enumTitle(enumStore.api_case_scenario_layer, record.scenario_layer)
                      }}</a-tag>
                    </template>
                    <template v-else-if="item.key === 'scenario_type'" #cell="{ record }">
                      <a-tag :color="enumColor(record.scenario_type)" size="small">{{
                        enumTitle(enumStore.api_case_scenario_type, record.scenario_type)
                      }}</a-tag>
                    </template>
                    <template v-else-if="item.key === 'scenario_tags'" #cell="{ record }">
                      <a-space wrap :size="4">
                        <a-tag
                          v-for="tag of record.scenario_tags || []"
                          :key="tag"
                          :color="enumColor(tag)"
                          size="small"
                        >
                          {{ enumTitle(enumStore.api_case_scenario_tag, tag) }}
                        </a-tag>
                      </a-space>
                    </template>
                    <template v-else-if="item.key === 'automation_case_ids'" #cell="{ record }">
                      <a-space
                        v-if="automationCaseLinks(record).length"
                        direction="vertical"
                        :size="2"
                      >
                        <a-link
                          v-for="link in automationCaseLinks(record)"
                          :key="`${link.type}:${link.id}`"
                          @click="goAutomationCase(link.type, link.id)"
                          >{{ link.label }}</a-link
                        >
                      </a-space>
                      <span v-else>-</span>
                    </template>
                    <template v-else-if="item.key === 'change_status'" #cell="{ record }">
                      <a-tag :color="changeStatusColor(record.change_status)" size="small">{{
                        enumTitle(enumStore.manual_test_change_status, record.change_status)
                      }}</a-tag>
                    </template>
                    <template
                      v-else-if="item.key === 'automation_impact_status'"
                      #cell="{ record }"
                    >
                      <a-tag
                        :color="impactStatusColor(record.automation_impact_status)"
                        size="small"
                        >{{
                          enumTitle(
                            enumStore.manual_test_automation_impact_status,
                            record.automation_impact_status
                          )
                        }}</a-tag
                      >
                    </template>
                    <template v-else-if="item.key === 'project_product'" #cell="{ record }">
                      {{ formatProjectProductPath(record.project_product) }}
                    </template>
                    <template v-else-if="item.key === 'module'" #cell="{ record }">
                      {{ formatModulePath(record.module) }}
                    </template>
                    <template v-else-if="item.key === 'actions'" #cell="{ record }">
                      <MangoTableActions
                        :actions="[
                          {
                            label: '编辑',
                            disabled: writeBlocked,
                            onClick: () => openCase(record),
                          },
                          {
                            label: '删除',
                            danger: true,
                            disabled: writeBlocked,
                            loading: deleting?.kind === 'case' && deleting.id === record.id,
                            onClick: () => deleteCase(record),
                          },
                        ]"
                      />
                    </template>
                  </a-table-column>
                </template>
              </a-table>
            </div>
          </section>
        </div>
        <template #footer>
          <TableFooter :pagination="activeView === 'suite' ? pagination : casePagination" />
        </template>
      </ProjectProductNavigationWorkbench>
    </template>
  </TableBody>

  <SuiteEditorDialog
    ref="suiteEditor"
    :context-key="editorContextKey"
    :blocked="caseSaving || overviewBusy || !!deleting || confirming"
    :users="userOptions"
    :users-loading="usersLoading"
    :users-error="usersError"
    :priority-options="enumStore.case_level || []"
    :status-options="enumStore.manual_test_suite_status || []"
    @busy="suiteSaving = $event"
    @visible="suiteEditorVisible = $event"
    @saved="onSuiteSaved"
    @retry-users="loadUsers"
  />

  <SuiteListCaseEditor
    ref="caseEditor"
    :context-key="editorContextKey"
    :blocked="suiteSaving || overviewBusy || !!deleting || confirming"
    :users="userOptions"
    :users-loading="usersLoading"
    :users-error="usersError"
    @busy="caseSaving = $event"
    @visible="caseVisible = $event"
    @saved="onCaseSaved"
    @retry-users="loadUsers"
  />
  <RequirementOverviewDrawer
    v-model:visible="overviewVisible"
    :suite-id="overviewSuiteId"
    :status-options="enumStore.manual_test_suite_status"
    :context-key="listContextKey"
    @edit-schedule="openSuite"
    @changed="loadSuites"
    @busy="overviewBusy = $event"
  />
</template>

<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { Message } from '@arco-design/web-vue'
  import {
    computed,
    onMounted,
    onActivated,
    onDeactivated,
    onBeforeUnmount,
    reactive,
    ref,
    watch,
  } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import RequirementOverviewDrawer from '@/views/functional-test/iteration/components/RequirementOverviewDrawer.vue'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import { useEnum } from '@/store/modules/get-enum'
  import useUserStore from '@/store/modules/user'
  import SuiteEditorDialog from './components/SuiteEditorDialog.vue'
  import SuiteListCaseEditor from './components/SuiteListCaseEditor.vue'
  import { useSuiteDeletion } from './composables/useSuiteDeletion'
  import type { ListCaseRecord, ListCaseEditorHandle } from './list-case-form'
  import { useCaseExport } from './composables/useCaseExport'
  import { readListPage } from './list-page'
  import { parseSuiteListRow, parseCaseListRow, parseUserOptions } from './list-records'
  import type { SuiteListRow, CaseListRow, UserOption } from './list-records'
  import type { CaseExportOption } from './export-rows'
  import type { SuiteEditRecord, SuiteEditorHandle } from './editor-form'
  import {
    createSuiteConditions,
    suiteColumns,
    caseColumns,
    suiteScrollWidth,
    caseScrollWidth,
  } from './config'
  import { usePagination } from '@/hooks/table'
  import { useLatestRequest } from '@/hooks/use-latest-request'
  import { getUserName } from '@/api/user/user'
  import { formatProjectProductPath, formatModulePath } from '@/utils/business-format'
  import {
    getStatusTagColor,
    MANUAL_TEST_CHANGE_STATUS_COLORS,
    MANUAL_TEST_IMPACT_STATUS_COLORS,
    MANUAL_TEST_SYNC_STATUS_COLORS,
  } from '@/utils/status-color'
  import { getManualCase, getManualSuite } from '@/api/functional-test'
  import { NavigationCreateSource } from '@/utils/navigation-create-defaults'

  const navigationCreateRef = ref<NavigationCreateSource | null>(null)

  const router = useRouter()
  const route = useRoute()
  const enumStore = useEnum()
  const fieldNames = { value: 'key', label: 'title' }
  const activeView = ref<'suite' | 'case'>(getViewFromRoute())
  const suites = ref<SuiteListRow[]>([])
  const cases = ref<CaseListRow[]>([])
  const requirementOptions = ref<Array<{ label: string; value: string }>>([])
  const userOptions = ref<UserOption[]>([])
  const suiteEditor = ref<SuiteEditorHandle | null>(null)
  const caseEditor = ref<ListCaseEditorHandle | null>(null)
  const suiteEditorVisible = ref(false),
    caseSaving = ref(false),
    overviewBusy = ref(false)
  const editorUser = useUserStore()
  const usersLoading = ref(false),
    usersError = ref(false)
  const enumsLoading = ref(false),
    enumsError = ref(false)
  let enumsSequence = 0
  let usersSequence = 0
  let usersActive = true,
    usersMounted = false
  const overviewVisible = ref(false)
  const overviewSuiteId = ref<number>()
  const pagination = usePagination(loadSuites, () => suiteLoading)
  const casePagination = usePagination(loadCases, () => caseLoading)
  const suiteRequest = useLatestRequest()
  const caseRequest = useLatestRequest()
  const sidebarResetKey = ref(0)
  const suiteLoading = ref(false)
  const suiteSaving = ref(false)
  const caseLoading = ref(false)
  const requirementLoading = ref(false)
  const suiteError = ref(false),
    caseError = ref(false),
    requirementError = ref(false)
  let listGeneration = 0,
    requirementSequence = 0
  const caseVisible = ref(false)
  const suiteTableShellRef = ref<HTMLElement>()
  const caseTableShellRef = ref<HTMLElement>()
  const suiteTreeProjectProduct = ref<number | undefined>()
  const suiteTreeModule = ref<number | undefined>()
  const activeNavigationProjectProduct = computed(() =>
    activeView.value === 'suite'
      ? suiteTreeProjectProduct.value
      : normalizeProjectProductValue(caseFilter.project_product)
  )
  const activeNavigationModule = computed(() =>
    activeView.value === 'suite' ? suiteTreeModule.value : caseFilter.module
  )
  const conditionItems = reactive(createSuiteConditions())
  const caseFilter = reactive({
    project_product: undefined as number | string | Array<number | string> | undefined,
    module: undefined as number | string | undefined,
    requirement_name: '',
    title: '',
    case_no: '',
    test_type: undefined as number | string | undefined,
    scenario_layer: undefined as number | string | undefined,
    scenario_type: undefined as number | string | undefined,
    scenario_tag: undefined as number | string | undefined,
    change_status: undefined as number | string | undefined,
    automation_impact_status: undefined as number | string | undefined,
  })
  const AUTOMATION_TYPE_API = 0
  const AUTOMATION_TYPE_UI = 1
  const pageTitle = computed(
    () => `研发协同 / ${activeView.value === 'case' ? '测试用例' : '需求管理'}`
  )

  function enumTitle(options: CaseExportOption[] = [], value: unknown) {
    return (
      options.find((item) => item.key === value)?.title ??
      (typeof value === 'string' || typeof value === 'number' ? value : '-')
    )
  }
  function enumColor(value: unknown) {
    return enumStore.colors?.[Number(value)]
  }
  const syncStatusColor = (value: number) =>
    getStatusTagColor(MANUAL_TEST_SYNC_STATUS_COLORS, value)
  const changeStatusColor = (value: number) =>
    getStatusTagColor(MANUAL_TEST_CHANGE_STATUS_COLORS, value)
  const impactStatusColor = (value: number) =>
    getStatusTagColor(MANUAL_TEST_IMPACT_STATUS_COLORS, value)
  function bindingCaseId(record: CaseListRow, type: number) {
    const binding = record.bindings.find((item) => item.automation_type === type)
    return (
      (type === AUTOMATION_TYPE_API ? binding?.api_case : binding?.ui_case) ??
      binding?.automation_case_id ??
      ''
    )
  }
  function automationCaseLinks(record: CaseListRow) {
    const links: Array<{ type: number; id: number; label: string }> = []
    const apiCaseId = Number(bindingCaseId(record, AUTOMATION_TYPE_API) || 0)
    const uiCaseId = Number(bindingCaseId(record, AUTOMATION_TYPE_UI) || 0)
    if (apiCaseId)
      links.push({ type: AUTOMATION_TYPE_API, id: apiCaseId, label: `apiid：${apiCaseId}` })
    if (uiCaseId) links.push({ type: AUTOMATION_TYPE_UI, id: uiCaseId, label: `uiid：${uiCaseId}` })
    return links
  }
  function goAutomationCase(type: number, caseId: number) {
    router.push({
      path: type === AUTOMATION_TYPE_API ? '/apitest/info/details' : '/uitest/case/details',
      query: type === AUTOMATION_TYPE_API ? { case_id: caseId } : { id: caseId },
    })
  }
  function formatDateTime(value?: string | null) {
    if (!value) return '-'
    return value.replace('T', ' ').split('.')[0]
  }
  function formatPercent(value: unknown) {
    return `${Number(value || 0)
      .toFixed(2)
      .replace(/\.00$/, '')}%`
  }
  function normalizeProjectProductValue(value: unknown) {
    const leaf: unknown = Array.isArray(value) ? value[value.length - 1] : value
    if (typeof leaf !== 'number' && typeof leaf !== 'string') return undefined
    const id = Number(leaf)
    return Number.isSafeInteger(id) && id > 0 ? id : undefined
  }
  function buildQuery() {
    const query: Record<string, unknown> = { page: pagination.page, pageSize: pagination.pageSize }
    conditionItems.forEach((item) => {
      if (item.multiple && Array.isArray(item.value)) {
        if (item.value.length) query[`${item.key}__in`] = item.value.join(',')
      } else if (item.value !== undefined && item.value !== null && item.value !== '') {
        query[item.key] = item.value
      }
    })
    if (suiteTreeProjectProduct.value) query.project_product = suiteTreeProjectProduct.value
    if (suiteTreeModule.value) {
      query.module = suiteTreeModule.value
      query.include_descendants = true
    }
    return query
  }
  function buildCaseQuery() {
    const query: Record<string, unknown> = {
      page: casePagination.page,
      pageSize: casePagination.pageSize,
    }
    const projectProduct = normalizeProjectProductValue(caseFilter.project_product)
    if (projectProduct) query.project_product = projectProduct
    if (caseFilter.module) {
      query.module = caseFilter.module
      query.include_descendants = true
    }
    if (caseFilter.title) query.title = caseFilter.title
    if (caseFilter.case_no) query.case_no = caseFilter.case_no
    if (
      caseFilter.test_type !== undefined &&
      caseFilter.test_type !== null &&
      caseFilter.test_type !== ''
    ) {
      query.test_type = caseFilter.test_type
    }
    for (const key of [
      'scenario_layer',
      'scenario_type',
      'scenario_tag',
      'change_status',
      'automation_impact_status',
    ] as const) {
      const value = caseFilter[key]
      if (value !== undefined && value !== null && value !== '') query[key] = value
    }
    if (caseFilter.requirement_name) query.suite__requirement_name = caseFilter.requirement_name
    return query
  }
  function buildRequirementQuery() {
    const query: Record<string, unknown> = { page: 1, pageSize: 1000 }
    const projectProduct = normalizeProjectProductValue(caseFilter.project_product)
    if (projectProduct) query.project_product = projectProduct
    if (caseFilter.module) {
      query.module = caseFilter.module
      query.include_descendants = true
    }
    return query
  }
  function onNavigationFilterChange(filter: {
    projectProduct: number | string | null
    module: number | string | null
  }) {
    if (activeView.value === 'suite') {
      suiteTreeProjectProduct.value = normalizeProjectProductValue(filter.projectProduct)
      suiteTreeModule.value = normalizeProjectProductValue(filter.module)
      pagination.page = 1
      loadSuites()
      return
    }
    caseFilter.project_product = filter.projectProduct || undefined
    caseFilter.module = filter.module || undefined
    caseFilter.requirement_name = ''
    casePagination.page = 1
    loadRequirementOptions()
    loadCases()
  }
  function getViewFromRoute() {
    return route.path.includes('/functional-test/case/index') ? 'case' : 'suite'
  }
  function searchSuites() {
    pagination.page = 1
    return loadSuites()
  }
  function searchActiveView() {
    if (activeView.value === 'case') {
      casePagination.page = 1
      return loadCases()
    }
    return searchSuites()
  }
  function resetActiveSearch() {
    if (activeView.value === 'case') {
      resetCaseSearch()
      return
    }
    resetSearch()
  }

  function onCaseRequirementChange() {
    casePagination.page = 1
    loadCases()
  }
  function onCaseTestTypeChange() {
    casePagination.page = 1
    loadCases()
  }
  function onCaseFilterChange() {
    casePagination.page = 1
    loadCases()
  }
  function resetSearch() {
    conditionItems.forEach((item) => {
      item.value = item.multiple ? [] : undefined
    })
    const requirementItem = conditionItems.find((item) => item.key === 'requirement_name')
    if (requirementItem) requirementItem.value = ''
    suiteTreeProjectProduct.value = undefined
    suiteTreeModule.value = undefined
    sidebarResetKey.value += 1
    pagination.page = 1
    loadSuites()
  }
  function resetCaseSearch() {
    caseFilter.project_product = undefined
    caseFilter.module = undefined
    caseFilter.requirement_name = ''
    caseFilter.title = ''
    caseFilter.case_no = ''
    caseFilter.test_type = undefined
    caseFilter.scenario_layer = undefined
    caseFilter.scenario_type = undefined
    caseFilter.scenario_tag = undefined
    caseFilter.change_status = undefined
    caseFilter.automation_impact_status = undefined
    casePagination.page = 1
    requirementOptions.value = []
    sidebarResetKey.value += 1
    loadRequirementOptions()
    loadCases()
  }
  async function loadSuites() {
    if (!usersActive) {
      suiteLoading.value = false
      return false
    }
    const requestId = suiteRequest.beginRequest()
    const generation = listGeneration,
      context = listContextKey.value
    const query = buildQuery()
    const current = () =>
      usersActive &&
      generation === listGeneration &&
      context === listContextKey.value &&
      suiteRequest.isLatestRequest(requestId)
    suiteLoading.value = true
    suiteError.value = false
    try {
      const res = await getManualSuite(query)
      if (!current()) return false
      const result = readListPage(res)
      if (JSON.stringify(query) !== JSON.stringify(buildQuery())) return false
      suites.value = result.rows.map(parseSuiteListRow)
      pagination.setTotalSize(result.total)
      return true
    } catch (loadFailure0) {
      if (current()) (reportLoadError(loadFailure0, "加载失败，请重试", false), suiteError.value = true)
      return false
    } finally {
      if (current()) suiteLoading.value = false
    }
  }
  async function loadCases() {
    if (!usersActive) {
      caseLoading.value = false
      return false
    }
    const requestId = caseRequest.beginRequest()
    const generation = listGeneration,
      context = listContextKey.value
    const query = buildCaseQuery()
    const current = () =>
      usersActive &&
      generation === listGeneration &&
      context === listContextKey.value &&
      caseRequest.isLatestRequest(requestId)
    caseLoading.value = true
    caseError.value = false
    try {
      const res = await getManualCase(query)
      if (!current()) return false
      const result = readListPage(res)
      if (JSON.stringify(query) !== JSON.stringify(buildCaseQuery())) return false
      cases.value = result.rows.map(parseCaseListRow)
      casePagination.setTotalSize(result.total)
      return true
    } catch (loadFailure1) {
      if (current()) (reportLoadError(loadFailure1, "加载失败，请重试", false), caseError.value = true)
      return false
    } finally {
      if (current()) caseLoading.value = false
    }
  }
  async function loadRequirementOptions() {
    if (!usersActive) {
      requirementLoading.value = false
      return
    }
    const sequence = ++requirementSequence,
      generation = listGeneration,
      context = listContextKey.value
    const query = buildRequirementQuery()
    const current = () =>
      usersActive &&
      sequence === requirementSequence &&
      generation === listGeneration &&
      context === listContextKey.value
    requirementLoading.value = true
    requirementError.value = false
    try {
      const res = await getManualSuite(query)
      if (!current() || JSON.stringify(query) !== JSON.stringify(buildRequirementQuery())) return
      const seen = new Set<string>()
      const options: Array<{ label: string; value: string }> = []
      for (const item of readListPage(res).rows) {
        if (
          typeof item.requirement_name !== 'string' ||
          !item.requirement_name ||
          seen.has(item.requirement_name)
        )
          continue
        seen.add(item.requirement_name)
        options.push({ label: item.requirement_name, value: item.requirement_name })
      }
      // 选项接口只加载前 1000 条，不能以缺席为由清掉仍然有效的查询条件。
      if (caseFilter.requirement_name && !seen.has(caseFilter.requirement_name))
        options.push({ label: caseFilter.requirement_name, value: caseFilter.requirement_name })
      requirementOptions.value = options
    } catch (loadFailure0) {
      if (current()) (reportLoadError(loadFailure0, "加载失败，请重试", false), requirementError.value = true)
    } finally {
      if (current()) requirementLoading.value = false
    }
  }
  const listContextKey = computed(() =>
    JSON.stringify([
      route.fullPath,
      editorUser.userId,
      editorUser.roleId,
      editorUser.token,
      editorUser.selected_environment,
      activeView.value,
    ])
  )
  const editorContextKey = computed(() =>
    JSON.stringify([
      route.fullPath,
      editorUser.userId,
      editorUser.roleId,
      editorUser.token,
      editorUser.selected_environment,
      activeView.value,
      activeNavigationProjectProduct.value,
      activeNavigationModule.value,
    ])
  )
  const { exportLoading, exportCases } = useCaseExport({
    contextKey: () => editorContextKey.value,
    query: buildCaseQuery,
    enums: () => ({
      testTypes: enumStore.manual_test_type || [],
      priorities: enumStore.case_level || [],
      layers: enumStore.api_case_scenario_layer || [],
      types: enumStore.api_case_scenario_type || [],
      tags: enumStore.api_case_scenario_tag || [],
      changes: enumStore.manual_test_change_status || [],
      impacts: enumStore.manual_test_automation_impact_status || [],
    }),
  })
  const { deleting, confirming, confirmDelete } = useSuiteDeletion({
    contextKey: () => editorContextKey.value,
    blocked: () => suiteSaving.value || caseSaving.value || overviewBusy.value,
    refresh: async (kind, id) => {
      if (kind === 'suite') {
        if (suites.value.length === 1 && suites.value[0].id === id && pagination.page > 1)
          --pagination.page
        return loadSuites()
      }
      if (cases.value.length === 1 && cases.value[0].id === id && casePagination.page > 1)
        --casePagination.page
      const [loaded] = await Promise.all([loadCases(), loadRequirementOptions()])
      return loaded
    },
  })
  const writeBlocked = computed(
    () =>
      suiteSaving.value ||
      caseSaving.value ||
      overviewBusy.value ||
      !!deleting.value ||
      confirming.value
  )

  function openSuite(record?: SuiteEditRecord) {
    if (!usersActive || writeBlocked.value || caseVisible.value) return
    const defaults = record ? undefined : navigationCreateRef.value?.getCreateDefaults()
    overviewVisible.value = false
    suiteEditor.value?.open(record ? 'edit' : 'create', record, defaults)
  }
  function openSuiteVersion(record: SuiteEditRecord) {
    if (!usersActive || writeBlocked.value || caseVisible.value) return
    overviewVisible.value = false
    suiteEditor.value?.open('version', record)
  }
  async function onSuiteSaved() {
    const generation = listGeneration,
      context = listContextKey.value
    if (
      !(await loadSuites()) &&
      usersActive &&
      generation === listGeneration &&
      context === listContextKey.value
    ) {
      Message.error('需求已保存，列表读取失败，请重试查询')
    }
  }
  async function onCaseSaved() {
    const generation = listGeneration,
      context = listContextKey.value
    if (
      !(await loadCases()) &&
      usersActive &&
      generation === listGeneration &&
      context === listContextKey.value
    )
      Message.error('用例已保存，列表读取失败，请重试查询')
  }
  function invalidateLists() {
    ++listGeneration
    ++requirementSequence
    ++enumsSequence
    enumsLoading.value = false
    enumsError.value = false
    suiteRequest.invalidateRequests()
    caseRequest.invalidateRequests()
    suiteLoading.value = false
    caseLoading.value = false
    requirementLoading.value = false
    suiteError.value = false
    caseError.value = false
    requirementError.value = false
    suites.value = []
    cases.value = []
    requirementOptions.value = []
    pagination.setTotalSize(0)
    casePagination.setTotalSize(0)
    overviewVisible.value = false
    overviewSuiteId.value = undefined
    caseVisible.value = false
  }
  function reloadLists() {
    if (activeView.value === 'case') return Promise.all([loadCases(), loadRequirementOptions()])
    return loadSuites()
  }
  watch(
    listContextKey,
    () => {
      invalidateLists()
      pagination.page = 1
      casePagination.page = 1
      if (
        usersMounted &&
        usersActive &&
        ['/functional-test/suite/index', '/functional-test/case/index'].includes(route.path)
      ) {
        void reloadLists()
        void loadEnums()
      }
    },
    { flush: 'sync' }
  )
  async function loadUsers() {
    if (!usersActive) return
    const sequence = ++usersSequence,
      context = listContextKey.value
    usersLoading.value = true
    usersError.value = false
    try {
      const response = await getUserName()
      if (sequence !== usersSequence || context !== listContextKey.value) return
      userOptions.value = parseUserOptions(response.data)
    } catch (loadFailure2) {
      if (sequence === usersSequence && context === listContextKey.value) (reportLoadError(loadFailure2, "加载失败，请重试", false), usersError.value = true)
    } finally {
      if (sequence === usersSequence && context === listContextKey.value) usersLoading.value = false
    }
  }
  async function loadEnums() {
    if (!usersActive) return
    const sequence = ++enumsSequence,
      generation = listGeneration,
      context = listContextKey.value
    const current = () =>
      usersActive &&
      sequence === enumsSequence &&
      generation === listGeneration &&
      context === listContextKey.value
    enumsLoading.value = true
    enumsError.value = false
    try {
      await enumStore.getEnum()
    } catch (loadFailure3) {
      if (current()) (reportLoadError(loadFailure3, "加载失败，请重试", false), enumsError.value = true)
    } finally {
      if (current()) enumsLoading.value = false
    }
  }
  function loadPage() {
    // 导航组件自行管理产品读取；列表、枚举和用户选项不相互阻塞。
    return Promise.allSettled([reloadLists(), loadEnums(), loadUsers()])
  }
  watch(
    listContextKey,
    () => {
      ++usersSequence
      usersLoading.value = false
      usersError.value = false
      userOptions.value = []
      if (
        usersMounted &&
        usersActive &&
        ['/functional-test/suite/index', '/functional-test/case/index'].includes(route.path)
      )
        void loadUsers()
    },
    { flush: 'sync' }
  )
  onDeactivated(() => {
    usersActive = false
    invalidateLists()
    ++usersSequence
    usersLoading.value = false
    userOptions.value = []
  })
  onActivated(() => {
    if (!usersActive) {
      usersActive = true
      void loadPage()
    }
  })
  onBeforeUnmount(() => {
    usersActive = false
    invalidateLists()
    ++usersSequence
  })
  function deleteSuite(record: SuiteEditRecord) {
    if (suiteEditorVisible.value || caseVisible.value || overviewVisible.value) return
    confirmDelete('suite', record.id, record.requirement_name ?? '')
  }
  function openCase(record: ListCaseRecord) {
    if (!usersActive || writeBlocked.value || suiteEditorVisible.value || overviewVisible.value)
      return
    caseEditor.value?.open(record)
  }
  function deleteCase(record: ListCaseRecord) {
    if (suiteEditorVisible.value || caseVisible.value || overviewVisible.value) return
    confirmDelete('case', record.id, record.case_no || record.title || '')
  }
  function goSuite(record: { id: number }) {
    if (!usersActive || writeBlocked.value || suiteEditorVisible.value || caseVisible.value) return
    if (!Number.isSafeInteger(record.id) || record.id <= 0) return
    overviewSuiteId.value = record.id
    overviewVisible.value = true
  }
  function goSuiteWorkspace(record: { id: number }) {
    router.push({ path: '/functional-test/requirement/details', query: { id: record.id } })
  }
  onMounted(() => {
    usersMounted = true
    void loadPage()
  })

  watch(
    () => route.path,
    () => {
      const view = getViewFromRoute()
      if (activeView.value === view) return
      activeView.value = view
    },
    { flush: 'sync' }
  )
</script>

<style scoped>
  .mango-functional-list-error {
    display: flex;
    align-items: center;
    gap: var(--m-page-gap);
    padding: var(--m-page-gap);
    color: var(--m-danger);
  }
  .mango-functional-case-list-workbench {
    display: flex;
    flex: 1;
    min-width: 0;
    min-height: 0;
    flex-direction: column;
    overflow: hidden;
    box-sizing: border-box;
  }

  .mango-functional-case-list-main {
    display: flex;
    flex: 1;
    min-width: 0;
    min-height: 0;
    flex-direction: column;
    overflow: hidden;
    background: var(--m-surface);
  }

  .mango-functional-suite-table,
  .mango-functional-case-table-shell {
    display: flex;
    flex: 1;
    min-width: 0;
    min-height: 0;
    flex-direction: column;
    overflow: hidden;
  }

  .mango-functional-case-search-legacy {
    flex: none;
    margin-bottom: 10px;
    padding: 8px 10px 0;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    background: var(--m-surface-soft);
  }

  .mango-functional-case-search-legacy :deep(.arco-form) {
    display: grid;
    grid-template-columns: repeat(3, minmax(180px, 1fr));
    gap: 0 10px;
  }

  .mango-functional-case-search-legacy :deep(.arco-form-item) {
    margin-bottom: 10px;
  }

  @media (max-width: 1120px) {
    .mango-functional-case-search-legacy :deep(.arco-form) {
      grid-template-columns: repeat(2, minmax(150px, 1fr));
    }
  }
</style>
