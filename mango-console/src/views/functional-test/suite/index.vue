<template>
  <TableBody plain class="mango-detail-workbench-page" :sticky-horizontal-scroll="false">
    <template #header>
      <TableHeader :title="pageTitle" />
    </template>
    <template #default>
      <ProjectProductNavigationWorkbench
        contained-body
        :sticky-horizontal-scroll="false"
        show-modules
        :model-value="activeNavigationProjectProduct"
        :module-value="activeNavigationModule"
        :reset-key="sidebarResetKey"
        @filter-change="onNavigationFilterChange"
        @search="loadActiveView"
        @reset-search="resetActiveSearch"
      >
        <template #search>
          <a-form
            v-if="activeView === 'suite'"
            :model="{}"
            layout="inline"
            @keyup.enter="loadSuites"
          >
            <a-form-item v-for="item of conditionItems" :key="item.key" :label="item.label">
              <template v-if="item.type === 'input'">
                <a-input
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  allow-clear
                  @blur="loadSuites"
                  @clear="loadSuites"
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
                  @change="loadSuites"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'update_user'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="fieldNames"
                  :options="userOptions"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="loadSuites"
                />
              </template>
            </a-form-item>
          </a-form>
          <a-form v-else :model="caseFilter" layout="inline" @keyup.enter="loadCases">
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
            </a-form-item>
            <a-form-item label="用例编号">
              <a-input
                v-model="caseFilter.case_no"
                allow-clear
                placeholder="请输入用例编号"
                @blur="loadCases"
                @clear="loadCases"
              />
            </a-form-item>
            <a-form-item label="用例标题">
              <a-input
                v-model="caseFilter.title"
                allow-clear
                placeholder="请输入用例标题"
                @blur="loadCases"
                @clear="loadCases"
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
                :options="enumStore.manual_test_scenario_type"
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
                :scroll="{ x: 3170, y: '100%' }"
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
    { label: '新版本', onClick: () => openSuiteVersion(record) },
    { label: '编辑', onClick: () => openSuite(record) },
    { label: '删除', danger: true, onClick: () => deleteSuite(record) },
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
                    :options="enumStore.manual_test_scenario_type"
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
                :scroll="{ x: 3260, y: '100%' }"
              >
                <template #columns>
                  <a-table-column v-for="item of caseColumns" :key="item.key" v-bind="item">
                    <template v-if="item.key === 'title'" #cell="{ record }">
                      <a-link @click="goSuite({ id: record.suite?.id || record.suite })">{{
                        record.title || '-'
                      }}</a-link>
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
                        enumTitle(enumStore.manual_test_scenario_type, record.scenario_type)
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
    { label: '编辑', onClick: () => openCase(record) },
    { label: '删除', danger: true, onClick: () => deleteCase(record) },
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

  <a-modal
    v-model:visible="suiteVisible"
    title="需求"
    width="760px"
    :ok-loading="suiteSaving"
    @ok="saveSuite"
  >
    <a-form :model="suiteForm" layout="vertical">
      <a-grid :cols="2" :col-gap="16">
        <a-grid-item :span="2"
          ><a-form-item label="需求名称" required
            ><a-input v-model="suiteForm.requirement_name" /></a-form-item
        ></a-grid-item>
        <a-grid-item
          ><a-form-item label="项目产品" required
            ><ProjectProductSelect
              v-model="suiteForm.project_product"
              @change="onSuiteProductChange" /></a-form-item
        ></a-grid-item>
        <a-grid-item
          ><a-form-item label="模块名称" required
            ><ProductModuleSelect
              v-model="suiteForm.module"
              :project-product-id="suiteForm.project_product"
              :auto-clear="false" /></a-form-item
        ></a-grid-item>
        <a-grid-item
          ><a-form-item label="所属 Sprint" required
            ><a-select
              v-model="suiteForm.iteration_ref"
              :options="iterationOptions"
              allow-search
              :loading="iterationLoading"
              placeholder="请选择 Sprint" /></a-form-item
        ></a-grid-item>
        <a-grid-item
          ><a-form-item label="优先级"
            ><a-select
              v-model="suiteForm.priority"
              :options="enumStore.case_level"
              :field-names="fieldNames" /></a-form-item
        ></a-grid-item>
        <a-grid-item
          ><a-form-item label="开发负责人"
            ><a-select
              v-model="suiteForm.development_owner"
              :options="userOptions"
              :field-names="fieldNames"
              allow-search
              allow-clear /></a-form-item
        ></a-grid-item>
        <a-grid-item
          ><a-form-item label="测试负责人" required
            ><a-select
              v-model="suiteForm.owner"
              :options="userOptions"
              :field-names="fieldNames"
              allow-search
              placeholder="请选择测试负责人" /></a-form-item
        ></a-grid-item>
        <a-grid-item
          ><a-form-item label="计划开始"
            ><a-date-picker
              v-model="suiteForm.planned_start_date"
              value-format="YYYY-MM-DD" /></a-form-item
        ></a-grid-item>
        <a-grid-item
          ><a-form-item label="计划提测"
            ><a-date-picker
              v-model="suiteForm.planned_submit_date"
              value-format="YYYY-MM-DD" /></a-form-item
        ></a-grid-item>
        <a-grid-item
          ><a-form-item label="交付状态"
            ><a-select
              v-model="suiteForm.status"
              :options="enumStore.manual_test_suite_status"
              :field-names="fieldNames" /></a-form-item
        ></a-grid-item>
      </a-grid>
    </a-form>
  </a-modal>

  <a-drawer v-model:visible="caseVisible" title="编辑测试用例" width="720px" @ok="saveCase">
    <a-form :model="caseForm" layout="vertical">
      <a-grid :cols="2" :col-gap="16">
        <a-grid-item>
          <a-form-item label="用例编号" required>
            <a-input v-model="caseForm.case_no" />
          </a-form-item>
        </a-grid-item>
        <a-grid-item>
          <a-form-item label="优先级" required>
            <a-select
              v-model="caseForm.priority"
              :options="enumStore.case_level"
              :field-names="fieldNames"
            />
          </a-form-item>
        </a-grid-item>
        <a-grid-item :span="2">
          <a-form-item label="用例标题" required>
            <a-input v-model="caseForm.title" />
          </a-form-item>
        </a-grid-item>
        <a-grid-item :span="2">
          <a-form-item label="测试场景" required>
            <a-textarea v-model="caseForm.test_point" :auto-size="{ minRows: 3, maxRows: 7 }" />
          </a-form-item>
        </a-grid-item>
        <a-grid-item :span="2">
          <a-form-item label="测试类型" required>
            <a-select
              v-model="caseForm.test_types"
              :options="enumStore.manual_test_type"
              :field-names="fieldNames"
              multiple
            />
          </a-form-item>
        </a-grid-item>
        <a-grid-item>
          <a-form-item label="项目产品" required>
            <ProjectProductSelect
              v-model="caseForm.project_product"
              @change="caseForm.module = null"
            />
          </a-form-item>
        </a-grid-item>
        <a-grid-item>
          <a-form-item label="模块名称" required>
            <ProductModuleSelect
              v-model="caseForm.module"
              :project-product-id="caseForm.project_product"
            />
          </a-form-item>
        </a-grid-item>
        <a-grid-item>
          <a-form-item label="测试层级" required>
            <a-select
              v-model="caseForm.scenario_layer"
              :options="enumStore.api_case_scenario_layer"
              :field-names="fieldNames"
            />
          </a-form-item>
        </a-grid-item>
        <a-grid-item>
          <a-form-item label="验证类型" required>
            <a-select
              v-model="caseForm.scenario_type"
              :options="enumStore.api_case_scenario_type"
              :field-names="fieldNames"
            />
          </a-form-item>
        </a-grid-item>
        <a-grid-item :span="2">
          <a-form-item label="执行场景" required>
            <a-select
              v-model="caseForm.scenario_tags"
              :options="enumStore.api_case_scenario_tag"
              :field-names="fieldNames"
              multiple
            />
          </a-form-item>
        </a-grid-item>
        <a-grid-item :span="2">
          <a-form-item label="负责人" required>
            <a-select
              v-model="caseForm.owner"
              :options="userOptions"
              :field-names="fieldNames"
              allow-search
              placeholder="请选择负责人"
              data-testid="qa-views-functional-test-suite-select-请选择负责人"
            />
          </a-form-item>
        </a-grid-item>
      </a-grid>
    </a-form>
  </a-drawer>
  <RequirementOverviewDrawer
    v-model:visible="overviewVisible"
    :suite-id="overviewSuiteId"
    :status-options="enumStore.manual_test_suite_status"
    @edit-schedule="openSuite"
    @changed="loadSuites"
  />
</template>

<script setup lang="ts">
  import { Message, Modal } from '@arco-design/web-vue'
  import { computed, onMounted, reactive, ref, watch } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import * as XLSX from 'xlsx'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import RequirementOverviewDrawer from '@/views/functional-test/iteration/components/RequirementOverviewDrawer.vue'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import { useEnum } from '@/store/modules/get-enum'
  import { useProject } from '@/store/modules/get-project'
  import { usePagination } from '@/hooks/table'
  import { useLatestRequest } from '@/hooks/use-latest-request'
  import type { FormItem } from '@/types/components'
  import { getUserName } from '@/api/user/user'
  import { formatProjectProductPath, formatModulePath } from '@/utils/business-format'
  import {
    getStatusTagColor,
    MANUAL_TEST_CHANGE_STATUS_COLORS,
    MANUAL_TEST_IMPACT_STATUS_COLORS,
    MANUAL_TEST_SYNC_STATUS_COLORS,
  } from '@/utils/status-color'
  import { createUpdateUserCondition, updateUserColumn } from '@/utils/update-user'
  import { enableMultiSelectSearch } from '@/utils/search-condition'
  import {
    getManualCase,
    getManualCaseExport,
    getManualSuite,
    deleteManualCase,
    deleteManualSuite,
    postManualSuite,
    putManualCase,
    putManualSuite,
    getFunctionalIterations,
  } from '@/api/functional-test'

  const router = useRouter()
  const route = useRoute()
  const enumStore = useEnum()
  const projectStore = useProject()
  const fieldNames = { value: 'key', label: 'title' }
  const activeView = ref<'suite' | 'case'>(getViewFromRoute())
  const suites = ref<any[]>([])
  const cases = ref<any[]>([])
  const requirementOptions = ref<any[]>([])
  const userOptions = ref<any[]>([])
  const iterationOptions = ref<any[]>([])
  const iterationLoading = ref(false)
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
  const exportLoading = ref(false)
  const suiteVisible = ref(false)
  const caseVisible = ref(false)
  const suiteForm = reactive<any>({})
  const caseForm = reactive<any>({})
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
  const conditionItems = reactive<Array<FormItem>>([
    {
      key: 'requirement_name',
      label: '需求名称',
      type: 'input',
      value: '',
      placeholder: '请输入需求名称',
    },
    {
      key: 'sync_status',
      label: '同步状态',
      type: 'select',
      value: undefined as string | undefined,
      placeholder: '请选择同步状态',
    },
    createUpdateUserCondition(),
  ])
  enableMultiSelectSearch(conditionItems)
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

  const suiteColumns = [
    { title: 'ID', key: 'id', dataIndex: 'id', width: 72 },
    {
      title: '需求名称',
      key: 'requirement_name',
      dataIndex: 'requirement_name',
      width: 220,
      ellipsis: true,
      tooltip: true,
    },
    {
      title: '所属 Sprint',
      key: 'iteration_ref',
      dataIndex: 'iteration_ref',
      width: 140,
      ellipsis: true,
      tooltip: true,
    },
    { title: '优先级', key: 'priority', dataIndex: 'priority', width: 90 },
    { title: '开发负责人', key: 'development_owner', dataIndex: 'development_owner', width: 120 },
    { title: '计划开始', key: 'planned_start_date', dataIndex: 'planned_start_date', width: 120 },
    { title: '计划提测', key: 'planned_submit_date', dataIndex: 'planned_submit_date', width: 120 },
    { title: '交付状态', key: 'status', dataIndex: 'status', width: 110 },
    { title: '测试负责人', key: 'owner', dataIndex: 'owner', width: 120 },
    { title: '用例数', key: 'case_count', dataIndex: 'case_count', width: 90 },
    { title: '测试进度', key: 'test_progress', dataIndex: 'test_metrics', width: 170 },
    { title: '通过率', key: 'pass_rate', dataIndex: 'test_metrics', width: 100 },
    { title: '未关闭缺陷', key: 'open_defect_count', dataIndex: 'open_defect_count', width: 110 },
    {
      title: '自动化数',
      key: 'automated_case_count',
      dataIndex: 'automated_case_count',
      width: 100,
    },
    { title: '完成百分比', key: 'coverage', dataIndex: 'automation_coverage_percent', width: 160 },
    { title: '同步状态', key: 'sync_status', dataIndex: 'sync_status', width: 110 },
    { title: '最近同步', key: 'last_sync_time', dataIndex: 'last_sync_time', width: 180 },
    updateUserColumn(120),
    { title: '更新时间', key: 'update_time', dataIndex: 'update_time', width: 180 },
    {
      title: '项目/产品',
      key: 'project_product',
      dataIndex: 'project_product',
      width: 140,
      ellipsis: true,
      tooltip: true,
    },
    {
      title: '模块',
      key: 'module',
      dataIndex: 'module',
      width: 240,
      ellipsis: true,
      tooltip: true,
    },
    {
      title: '操作',
      key: 'actions',
      dataIndex: 'actions',
      align: 'center',
      fixed: 'right',
      width: 160,
    },
  ]
  const caseColumns = [
    { title: 'ID', key: 'id', dataIndex: 'id', width: 72, align: 'center' },
    {
      title: '需求名称',
      key: 'suite',
      dataIndex: 'suite',
      width: 220,
      ellipsis: true,
      tooltip: true,
    },
    {
      title: '所属 Sprint',
      key: 'suite_iteration',
      dataIndex: 'suite_iteration',
      width: 140,
      ellipsis: true,
      tooltip: true,
    },
    {
      title: '用例编号',
      key: 'case_no',
      dataIndex: 'case_no',
      width: 130,
      ellipsis: true,
      tooltip: true,
    },
    { title: '标题', key: 'title', dataIndex: 'title', width: 220, ellipsis: true, tooltip: true },
    {
      title: '前置条件',
      key: 'precondition',
      dataIndex: 'precondition',
      width: 220,
      ellipsis: true,
      tooltip: true,
    },
    {
      title: '测试场景',
      key: 'test_point',
      dataIndex: 'test_point',
      width: 260,
      ellipsis: true,
      tooltip: true,
    },
    {
      title: '测试数据',
      key: 'test_data',
      dataIndex: 'test_data',
      width: 220,
      ellipsis: true,
      tooltip: true,
    },
    { title: '测试类型', key: 'test_types', dataIndex: 'test_types', width: 150 },
    { title: '优先级', key: 'priority', dataIndex: 'priority', width: 90 },
    { title: '测试层级', key: 'scenario_layer', dataIndex: 'scenario_layer', width: 120 },
    { title: '验证类型', key: 'scenario_type', dataIndex: 'scenario_type', width: 110 },
    { title: '执行场景', key: 'scenario_tags', dataIndex: 'scenario_tags', width: 220 },
    {
      title: '自动化用例 ID',
      key: 'automation_case_ids',
      dataIndex: 'automation_case_ids',
      width: 150,
    },
    { title: '变更', key: 'change_status', dataIndex: 'change_status', width: 90 },
    {
      title: '自动化影响',
      key: 'automation_impact_status',
      dataIndex: 'automation_impact_status',
      width: 120,
    },
    {
      title: '备注',
      key: 'remark',
      dataIndex: 'remark',
      width: 180,
      ellipsis: true,
      tooltip: true,
    },
    {
      title: '项目/产品',
      key: 'project_product',
      dataIndex: 'project_product',
      width: 140,
      ellipsis: true,
      tooltip: true,
    },
    {
      title: '模块',
      key: 'module',
      dataIndex: 'module',
      width: 240,
      ellipsis: true,
      tooltip: true,
    },
    {
      title: '操作',
      key: 'actions',
      dataIndex: 'actions',
      align: 'center',
      fixed: 'right',
      width: 160,
    },
  ]

  function enumTitle(options: any[] = [], value: any) {
    return options.find((item) => item.key === value)?.title || value || '-'
  }
  function enumColor(value: any) {
    return enumStore.colors?.[Number(value)]
  }
  const syncStatusColor = (value: number) =>
    getStatusTagColor(MANUAL_TEST_SYNC_STATUS_COLORS, value)
  const changeStatusColor = (value: number) =>
    getStatusTagColor(MANUAL_TEST_CHANGE_STATUS_COLORS, value)
  const impactStatusColor = (value: number) =>
    getStatusTagColor(MANUAL_TEST_IMPACT_STATUS_COLORS, value)
  function enumTitles(options: any[] = [], values: any[] = []) {
    if (!Array.isArray(values) || values.length === 0) return '-'
    return values.map((value) => enumTitle(options, value)).join('、')
  }
  function bindingCaseId(record: any, type: number) {
    const binding = (record.bindings || []).find((item: any) => item.automation_type === type)
    return binding?.api_case_id || binding?.ui_case_id || binding?.automation_case_id || ''
  }
  function automationCaseLinks(record: any) {
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
  function formatDateTime(value?: string) {
    if (!value) return '-'
    return value.replace('T', ' ').split('.')[0]
  }
  function formatPercent(value: any) {
    return `${Number(value || 0)
      .toFixed(2)
      .replace(/\.00$/, '')}%`
  }
  function formatExportFileName() {
    const stamp = new Date().toISOString().replace('T', '_').replaceAll(':', '-').split('.')[0]
    return `功能测试用例_${stamp}.xlsx`
  }
  function getLeafValue(value: any) {
    return Array.isArray(value) ? value[value.length - 1] : value
  }
  function normalizeProjectProductValue(value: any) {
    const leaf = getLeafValue(value)
    return leaf === undefined || leaf === null || leaf === '' ? undefined : Number(leaf)
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
  function onNavigationFilterChange(filter: { projectProduct: any; module: any }) {
    if (activeView.value === 'suite') {
      suiteTreeProjectProduct.value = filter.projectProduct || undefined
      suiteTreeModule.value = filter.module || undefined
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
  function loadActiveView() {
    if (activeView.value === 'case') {
      loadCases()
      return
    }
    loadSuites()
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
    const iterationItem = conditionItems.find((item) => item.key === 'iteration')
    if (requirementItem) requirementItem.value = ''
    if (iterationItem) iterationItem.value = ''
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
    const requestId = suiteRequest.beginRequest()
    suiteLoading.value = true
    try {
      const res = await getManualSuite(buildQuery())
      if (!suiteRequest.isLatestRequest(requestId)) return
      suites.value = res.data || []
      pagination.setTotalSize((res as any).totalSize || suites.value.length)
    } finally {
      if (suiteRequest.isLatestRequest(requestId)) suiteLoading.value = false
    }
  }
  async function loadCases() {
    const requestId = caseRequest.beginRequest()
    caseLoading.value = true
    try {
      const res = await getManualCase(buildCaseQuery())
      if (!caseRequest.isLatestRequest(requestId)) return
      cases.value = res.data || []
      casePagination.setTotalSize((res as any).totalSize || cases.value.length)
    } finally {
      if (caseRequest.isLatestRequest(requestId)) caseLoading.value = false
    }
  }
  async function loadRequirementOptions() {
    requirementLoading.value = true
    try {
      const res = await getManualSuite(buildRequirementQuery())
      const seen = new Set()
      requirementOptions.value = (res.data || [])
        .filter((item: any) => item.requirement_name)
        .filter((item: any) => {
          if (seen.has(item.requirement_name)) return false
          seen.add(item.requirement_name)
          return true
        })
        .map((item: any) => ({ label: item.requirement_name, value: item.requirement_name }))
      if (
        caseFilter.requirement_name &&
        !requirementOptions.value.some((item) => item.value === caseFilter.requirement_name)
      ) {
        caseFilter.requirement_name = ''
      }
    } finally {
      requirementLoading.value = false
    }
  }
  async function initCaseView() {
    await projectStore.projectProductName()
    await Promise.all([loadRequirementOptions(), loadCases()])
  }
  async function fetchExportCases() {
    const pageSize = 1000
    const firstRes = await getManualCaseExport({ ...buildCaseQuery(), page: 1, pageSize })
    const rows = [...(firstRes.data || [])]
    const total = Number((firstRes as any).totalSize || rows.length)
    const pageCount = Math.ceil(total / pageSize)
    for (let page = 2; page <= pageCount; page += 1) {
      const res = await getManualCaseExport({ ...buildCaseQuery(), page, pageSize })
      rows.push(...(res.data || []))
    }
    return rows
  }
  function buildExportRows(rows: any[]) {
    return rows.map((record) => ({
      ID: record.id || '',
      '项目/产品': formatProjectProductPath(record.project_product),
      模块: formatModulePath(record.module),
      用例编号: record.case_no || '',
      标题: record.title || '',
      需求名称: record.suite?.requirement_name || '',
      所属Sprint: record.suite?.iteration_ref?.name || record.suite?.iteration || '',
      前置条件: record.precondition || '',
      测试场景: record.test_point || '',
      测试数据: record.test_data || '',
      测试类型: enumTitles(enumStore.manual_test_type, record.test_types),
      优先级: enumTitle(enumStore.case_level, record.priority),
      测试层级: enumTitle(enumStore.api_case_scenario_layer, record.scenario_layer),
      验证类型: enumTitle(enumStore.manual_test_scenario_type, record.scenario_type),
      执行场景: enumTitles(enumStore.api_case_scenario_tag, record.scenario_tags),
      'API 用例 ID': bindingCaseId(record, AUTOMATION_TYPE_API),
      'UI 用例 ID': bindingCaseId(record, AUTOMATION_TYPE_UI),
      变更: enumTitle(enumStore.manual_test_change_status, record.change_status),
      自动化影响: enumTitle(
        enumStore.manual_test_automation_impact_status,
        record.automation_impact_status
      ),
      备注: record.remark || '',
    }))
  }
  async function exportCases() {
    if (exportLoading.value) return
    exportLoading.value = true
    try {
      const rows = await fetchExportCases()
      if (!rows.length) {
        Message.warning('暂无可导出的用例')
        return
      }
      const worksheet = XLSX.utils.json_to_sheet(buildExportRows(rows))
      const workbook = XLSX.utils.book_new()
      XLSX.utils.book_append_sheet(workbook, worksheet, '测试用例')
      XLSX.writeFile(workbook, formatExportFileName())
      Message.success('导出成功')
    } finally {
      exportLoading.value = false
    }
  }
  async function loadSuiteIterations() {
    const productId = normalizeProjectProductValue(suiteForm.project_product)
    iterationOptions.value = []
    if (!productId) return
    iterationLoading.value = true
    try {
      const res = await getFunctionalIterations({
        project_product: productId,
        page: 1,
        pageSize: 500,
      })
      iterationOptions.value = (res.data || []).map((item: any) => ({
        value: item.id,
        label: `${item.iteration_no} ${item.name}`,
      }))
    } finally {
      iterationLoading.value = false
    }
  }
  async function onSuiteProductChange() {
    suiteForm.module = null
    suiteForm.iteration_ref = undefined
    await loadSuiteIterations()
  }
  async function openSuite(record?: any) {
    Object.keys(suiteForm).forEach((key) => delete suiteForm[key])
    Object.assign(
      suiteForm,
      record
        ? {
            ...record,
            project_product: record.project_product?.id || record.project_product,
            module: record.module?.id || record.module,
            owner: record.owner?.id || record.owner,
            iteration_ref: record.iteration_ref?.id || record.iteration_ref,
            development_owner: record.development_owner?.id || record.development_owner,
          }
        : {}
    )
    if (!record) Object.assign(suiteForm, { priority: 1, status: 1 })
    await loadSuiteIterations()
    suiteVisible.value = true
  }
  async function openSuiteVersion(record: any) {
    await openSuite()
    Object.assign(suiteForm, {
      requirement: record.requirement?.id || record.requirement,
      previous_version: record.id,
      project_product: record.project_product?.id || record.project_product,
      module: record.module?.id || record.module,
      owner: record.owner?.id || record.owner,
      requirement_name: record.requirement_name,
      iteration: '',
      iteration_ref: record.iteration_ref?.id || record.iteration_ref,
      priority: record.priority,
      development_owner: record.development_owner?.id || record.development_owner,
      planned_start_date: undefined,
      planned_submit_date: undefined,
      status: 1,
    })
    await loadSuiteIterations()
  }
  async function saveSuite() {
    const payload = { ...suiteForm }
    if (!String(payload.requirement_name || '').trim()) {
      Message.error('请输入需求名称')
      return
    }
    if (!payload.project_product) {
      Message.error('请选择项目产品')
      return
    }
    if (!payload.module) {
      Message.error('请选择模块名称')
      return
    }
    if (!payload.iteration_ref) {
      Message.error('请选择所属 Sprint')
      return
    }
    if (!payload.owner) {
      Message.error('请选择测试负责人')
      return
    }
    suiteSaving.value = true
    try {
      const action = payload.id ? putManualSuite : postManualSuite
      await action(payload)
      Message.success('保存成功')
      suiteVisible.value = false
      await loadSuites()
    } finally {
      suiteSaving.value = false
    }
  }
  function deleteSuite(record: any) {
    Modal.confirm({
      title: '删除需求',
      content: `确认删除需求「${
        record.requirement_name || record.id
      }」吗？需求资料会删除，已生成的用例库资产会保留。`,
      cancelText: '取消',
      okText: '删除',
      okButtonProps: { status: 'danger' },
      onBeforeOk: async () => {
        suiteLoading.value = true
        try {
          await deleteManualSuite(record.id)
          Message.success('删除成功')
          await loadSuites()
        } finally {
          suiteLoading.value = false
        }
      },
    })
  }
  function openCase(record: any) {
    Object.keys(caseForm).forEach((key) => delete caseForm[key])
    Object.assign(caseForm, {
      ...record,
      suite: record.suite?.id || record.suite,
      project_product: record.project_product?.id || record.project_product,
      module: record.module?.id || record.module,
      owner: record.owner?.id || record.owner,
    })
    caseVisible.value = true
  }
  function validateCaseForm() {
    const required = [
      ['case_no', '请输入用例编号'],
      ['title', '请输入用例标题'],
      ['test_point', '请输入测试场景'],
      ['project_product', '请选择项目产品'],
      ['module', '请选择模块名称'],
      ['owner', '请选择负责人'],
    ]
    for (const [field, message] of required) {
      if (!String(caseForm[field] || '').trim()) {
        Message.error(message)
        return false
      }
    }
    if (!caseForm.test_types?.length) {
      Message.error('请选择测试类型')
      return false
    }
    if (caseForm.priority === undefined || caseForm.priority === null || caseForm.priority === '') {
      Message.error('请选择优先级')
      return false
    }
    if (
      caseForm.scenario_layer === undefined ||
      caseForm.scenario_layer === null ||
      caseForm.scenario_layer === ''
    ) {
      Message.error('请选择测试层级')
      return false
    }
    if (
      caseForm.scenario_type === undefined ||
      caseForm.scenario_type === null ||
      caseForm.scenario_type === ''
    ) {
      Message.error('请选择验证类型')
      return false
    }
    if (!caseForm.scenario_tags?.length) {
      Message.error('请选择执行场景')
      return false
    }
    return true
  }
  async function saveCase() {
    if (!validateCaseForm()) return
    await putManualCase({ ...caseForm, suite: caseForm.suite?.id || caseForm.suite })
    Message.success('保存成功')
    caseVisible.value = false
    await loadCases()
  }
  function deleteCase(record: any) {
    Modal.confirm({
      title: '删除测试用例',
      content: `确认删除测试用例「${record.case_no || record.title || record.id}」吗？`,
      cancelText: '取消',
      okText: '删除',
      okButtonProps: { status: 'danger' },
      onBeforeOk: async () => {
        caseLoading.value = true
        try {
          await deleteManualCase(record.id)
          Message.success('删除成功')
          await Promise.all([loadCases(), loadRequirementOptions()])
        } finally {
          caseLoading.value = false
        }
      },
    })
  }
  function goSuite(record: any) {
    overviewSuiteId.value = record.id
    overviewVisible.value = true
  }
  function goSuiteWorkspace(record: any) {
    router.push({ path: '/functional-test/requirement/details', query: { id: record.id } })
  }
  async function initSuiteView() {
    await projectStore.projectProductName()
    await loadSuites()
  }

  onMounted(async () => {
    await enumStore.getEnum()
    const userPromise = getUserName().then((res) => {
      userOptions.value = res.data || []
    })
    if (activeView.value === 'case') await initCaseView()
    else await initSuiteView()
    await userPromise
  })

  watch(
    () => route.path,
    () => {
      const view = getViewFromRoute()
      if (activeView.value === view) return
      activeView.value = view
      if (view === 'case') {
        initCaseView()
        return
      }
      initSuiteView()
    }
  )
</script>

<style scoped>
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
