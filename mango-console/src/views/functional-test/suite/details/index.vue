<template>
  <TableBody class="mango-detail-workbench-page mango-functional-workbench-page">
    <template #header>
      <div class="mango-detail-toolbar">
        <div class="mango-detail-heading">
          <div class="mango-detail-title">{{ workbenchTitle }}</div>
        </div>
        <a-space class="mango-detail-actions" wrap>
          <a-button class="mango-back-button" size="small" @click="router.back()" data-testid="qa-views-functional-test-suite-details-button-返回">返回</a-button>
        </a-space>
      </div>
    </template>

    <template #default>
      <div class="mango-workbench-scroll-x mango-functional-workbench-scroll">
      <div :class="['mango-functional-workbench', { 'mango-functional-workbench-case': activePane === 'cases' }]">
        <aside class="mango-functional-nav">
          <div class="mango-functional-nav-head">
            <div class="mango-functional-nav-head-title">需求用例</div>
            <div class="mango-functional-nav-head-subtitle">上下文资料与来源用例</div>
          </div>
          <div v-for="group in navGroups" :key="group.title" class="mango-functional-nav-section">
            <div class="mango-functional-nav-title">{{ group.title }}</div>
            <div class="mango-functional-nav-items">
              <button
                v-for="item in group.items"
                :key="item.key"
                :class="['mango-functional-nav-item', { 'mango-functional-nav-item-active': activePane === item.key }]"
                type="button"
                @click="activePane = item.key"
              >
                <span class="mango-functional-nav-item-row">
                  <span>{{ item.title }}</span>
                  <em>{{ navItemCount(item) }}</em>
                </span>
                <small>{{ item.description }}</small>
              </button>
            </div>
          </div>
        </aside>

        <section class="mango-functional-main-panel">
          <div class="mango-functional-panel-head">
            <div>
              <div class="mango-functional-panel-title">{{ currentNavItem.title }}</div>
              <div class="mango-functional-panel-subtitle">{{ currentNavItem.tip || currentNavItem.description }}</div>
            </div>
            <a-space v-if="hasActiveContextField">
              <a-button size="small" :loading="resourceLoading || suiteLoading" @click="loadContextResources" data-testid="qa-views-functional-test-suite-details-button-刷新">刷新</a-button>
              <a-button  size="small" type="primary" @click="openResource()" data-testid="qa-views-functional-test-suite-details-button-新增资料">新增资料</a-button>
            </a-space>
            <a-space v-else-if="activePane === 'cases'">
              <a-button  size="small" status="danger" :loading="caseLoading" @click="batchDeleteCases" data-testid="qa-views-functional-test-suite-details-button-批量删除">
                批量删除
              </a-button>

              <a-button  size="small" type="primary" @click="openCase()" data-testid="qa-views-functional-test-suite-details-button-手动新增">手动新增</a-button>
            </a-space>
            <a-space v-else-if="activePane === 'sync'">
              <a-button size="small" :loading="resourceLoading" @click="loadContextResources" data-testid="qa-views-functional-test-suite-details-button-刷新-2">刷新</a-button>
              <a-button  size="small" type="primary" @click="openResource(undefined, rawCaseContextKey)" data-testid="qa-views-functional-test-suite-details-button-新增资料-2">新增资料</a-button>
            </a-space>
            <a-space v-else-if="activePane === 'basic'">
              <a-button size="small" :loading="suiteLoading || qualityLoading" @click="refreshAll">刷新</a-button>
            </a-space>
            <a-space v-else-if="['plans', 'defects'].includes(String(activePane))">
              <a-button size="small" :loading="qualityLoading" @click="loadQualityRelations">刷新</a-button>
              <a-button  v-if="activePane === 'plans'" size="small" type="primary" @click="createRequirementPlan">新建测试计划</a-button>
            </a-space>
          </div>

          <div :class="['mango-functional-panel-body', { 'mango-functional-panel-body-case': activePane === 'cases' }]">
            <mango-panel-spin v-if="hasActiveContextField" :loading="resourceLoading || suiteLoading">
              <div class="mango-functional-resource-pane">
                <a-empty v-if="!activeResources.length" description="暂无上下文资料" />
                <div v-else class="mango-functional-resource-list">
                  <div v-for="resource in activeResources" :key="resource.id" class="mango-functional-resource-item">
                    <div class="mango-functional-resource-main">
                      <div class="mango-functional-resource-title">
                        <span>{{ resource.title }}</span>
                        <a-space :size="4">
                          <a-tag :color="enumColor(resource.content_type)" size="small">{{ enumTitle(enumStore.functional_test_context_content_type, resource.content_type) }}</a-tag>
                          <a-tag v-if="resource.content_type === RESOURCE_CONTENT_URL" :color="enumColor(resource.url_type)" size="small">
                            {{ enumTitle(enumStore.functional_test_context_url_type, resource.url_type) }}
                          </a-tag>
                          <a-tag v-if="!resource.enabled" :color="statusColor(0)" size="small">未启用</a-tag>
                        </a-space>
                      </div>
                      <div class="mango-functional-resource-content">
                        {{ resourceSummary(resource) }}
                      </div>
                    </div>
                    <MangoTableActions
                      :actions="[
    { label: '原文', onClick: () => openRawResource(resource) },
    { label: '编辑', onClick: () => openResource(resource) },
    { label: '删除', danger: true, onClick: () => removeResource(resource) },
]"
                    />
                  </div>
                </div>
              </div>
            </mango-panel-spin>

            <div v-else-if="activePane === 'basic'" class="mango-functional-basic-pane">
              <a-descriptions :column="2" bordered size="small">
                <a-descriptions-item label="需求">{{ suite?.requirement?.name || suite?.requirement_name || '-' }}</a-descriptions-item>
                <a-descriptions-item label="需求版本">V{{ suite?.version_no || '-' }}</a-descriptions-item>
                <a-descriptions-item label="项目/产品">{{ formatProjectProductPath(suite?.project_product) }}</a-descriptions-item>
                <a-descriptions-item label="模块">{{ formatModulePath(suite?.module) }}</a-descriptions-item>
                <a-descriptions-item label="Sprint">{{ suite?.iteration_ref?.name || '-' }}</a-descriptions-item>
                <a-descriptions-item label="状态">{{ enumTitle(enumStore.manual_test_suite_status, suite?.status) }}</a-descriptions-item>
                <a-descriptions-item label="开发负责人">{{ suite?.development_owner?.name || '-' }}</a-descriptions-item>
                <a-descriptions-item label="测试负责人">{{ suite?.owner?.name || '-' }}</a-descriptions-item>
                <a-descriptions-item label="计划周期">{{ suite?.planned_start_date || '-' }} 至 {{ suite?.planned_submit_date || '-' }}</a-descriptions-item>
                <a-descriptions-item label="测试计划">{{ suite?.plan_count || relatedPlans.length || 0 }} 个</a-descriptions-item>
                <a-descriptions-item label="执行进度">{{ suite?.test_metrics?.executed || 0 }}/{{ suite?.test_metrics?.total || 0 }}（{{ formatPercent(suite?.test_metrics?.progress) }}）</a-descriptions-item>
                <a-descriptions-item label="通过率">{{ formatPercent(suite?.test_metrics?.pass_rate) }}</a-descriptions-item>
                <a-descriptions-item label="未关闭缺陷">{{ suite?.open_defect_count || 0 }}</a-descriptions-item>
                <a-descriptions-item label="更新时间">{{ suite?.update_time || '-' }}</a-descriptions-item>
              </a-descriptions>
            </div>

            <div v-else-if="activePane === 'cases'" class="mango-functional-case-pane">
              <div class="mango-functional-case-filters">
                <a-select
                  v-model="caseFilters.test_type"
                  :options="enumStore.manual_test_type"
                  :field-names="fieldNames"
                  allow-clear
                  placeholder="测试类型"
                  @change="searchCases" data-testid="qa-views-functional-test-suite-details-select-测试类型"
                />
                <a-select
                  v-model="caseFilters.scenario_layer"
                  :options="enumStore.api_case_scenario_layer"
                  :field-names="fieldNames"
                  allow-clear
                  placeholder="测试层级"
                  @change="searchCases" data-testid="qa-views-functional-test-suite-details-select-测试层级"
                />
                <a-select
                  v-model="caseFilters.scenario_type"
                  :options="enumStore.api_case_scenario_type"
                  :field-names="fieldNames"
                  allow-clear
                  placeholder="验证类型"
                  @change="searchCases" data-testid="qa-views-functional-test-suite-details-select-验证类型"
                />
                <a-select
                  v-model="caseFilters.scenario_tag"
                  :options="enumStore.api_case_scenario_tag"
                  :field-names="fieldNames"
                  allow-clear
                  placeholder="执行场景"
                  @change="searchCases" data-testid="qa-views-functional-test-suite-details-select-执行场景"
                />
                <a-select
                  v-model="caseFilters.change_status"
                  :options="enumStore.manual_test_change_status"
                  :field-names="fieldNames"
                  allow-clear
                  placeholder="变更"
                  @change="searchCases" data-testid="qa-views-functional-test-suite-details-select-变更"
                />
                <a-select
                  v-model="caseFilters.automation_impact_status"
                  :options="enumStore.manual_test_automation_impact_status"
                  :field-names="fieldNames"
                  allow-clear
                  placeholder="自动化影响"
                  @change="searchCases" data-testid="qa-views-functional-test-suite-details-select-自动化影响"
                />
                <a-button size="small" @click="resetCaseFilters" data-testid="qa-views-functional-test-suite-details-button-重置">重置</a-button>
              </div>
              <div
                ref="caseTableShellRef"
                class="mango-functional-case-table"
              >
                <a-table
                  :bordered="false"
                  :columns="caseColumns"
                  :data="cases"
                  :loading="caseLoading"
                  :pagination="false"
                  :row-key="'id'"
                  v-model:selectedKeys="selectedCaseKeys"
                  :row-selection="{ type: 'checkbox', showCheckedAll: true }"
                  :scroll="{ x: 2810 }"
                >
                  <template #columns>
                    <a-table-column v-for="item of caseColumns" :key="item.key" v-bind="item">
                      <template v-if="item.key === 'title'" #cell="{ record }">
                        <a-link  @click="openCase(record)">{{ record.title }}</a-link>
                      </template>
                      <template v-else-if="item.key === 'project_product'" #cell="{ record }">
                        {{ formatProjectProductPath(record.project_product) }}
                      </template>
                      <template v-else-if="item.key === 'module'" #cell="{ record }">
                        {{ formatModulePath(record.module) }}
                      </template>
                      <template v-else-if="item.key === 'priority'" #cell="{ record }">
                        <a-tag :color="enumColor(record.priority)" size="small">{{ enumTitle(enumStore.case_level, record.priority) }}</a-tag>
                      </template>
                      <template v-else-if="item.key === 'test_types'" #cell="{ record }">
                        <a-space wrap :size="4">
                          <a-tag v-for="type of record.test_types || []" :key="type" :color="enumColor(type)" size="small">
                            {{ enumTitle(enumStore.manual_test_type, type) }}
                          </a-tag>
                        </a-space>
                      </template>
                      <template v-else-if="item.key === 'scenario_layer'" #cell="{ record }">
                        <a-tag :color="enumColor(record.scenario_layer)" size="small">{{ enumTitle(enumStore.api_case_scenario_layer, record.scenario_layer) }}</a-tag>
                      </template>
                      <template v-else-if="item.key === 'scenario_type'" #cell="{ record }">
                        <a-tag :color="enumColor(record.scenario_type)" size="small">{{ enumTitle(enumStore.api_case_scenario_type, record.scenario_type) }}</a-tag>
                      </template>
                      <template v-else-if="item.key === 'scenario_tags'" #cell="{ record }">
                        <a-space wrap :size="4">
                          <a-tag v-for="tag of record.scenario_tags || []" :key="tag" :color="enumColor(tag)" size="small">
                            {{ enumTitle(enumStore.api_case_scenario_tag, tag) }}
                          </a-tag>
                        </a-space>
                      </template>
                      <template v-else-if="item.key === 'automation_case_ids'" #cell="{ record }">
                        <a-space v-if="automationCaseLinks(record).length" wrap :size="4">
                          <a-link
                            v-for="link in automationCaseLinks(record)"
                            :key="link.type"
                            @click="goAutomationCase(record, link.type)"
                          >
                            {{ link.label }}
                          </a-link>
                        </a-space>
                        <span v-else>-</span>
                      </template>
                      <template v-else-if="item.key === 'change_status'" #cell="{ record }">
                        <a-tag :color="changeStatusColor(record.change_status)" size="small">{{ enumTitle(enumStore.manual_test_change_status, record.change_status) }}</a-tag>
                      </template>
                      <template v-else-if="item.key === 'automation_impact_status'" #cell="{ record }">
                        <a-tag :color="impactStatusColor(record.automation_impact_status)" size="small">{{ enumTitle(enumStore.manual_test_automation_impact_status, record.automation_impact_status) }}</a-tag>
                      </template>
                      <template v-else-if="item.key === 'actions'" #cell="{ record }">
                        <MangoTableActions
                          :actions="[
    { label: '编辑', onClick: () => openCase(record) },
    { label: 'UI绑定', onClick: () => openBind(record, AUTOMATION_TYPE_UI) },
    {
        label: '前往API用例',
        disabled: !bindingCaseId(record, AUTOMATION_TYPE_API),
        onClick: () => goAutomationCase(record, AUTOMATION_TYPE_API), },
    {
        label: '前往UI用例',
        disabled: !bindingCaseId(record, AUTOMATION_TYPE_UI),
        onClick: () => goAutomationCase(record, AUTOMATION_TYPE_UI), },
]"
                        />
                      </template>
                    </a-table-column>
                  </template>
                </a-table>
              </div>
              <TableFooter class="mango-functional-case-footer" :pagination="casePagination" />
            </div>

            <div v-else-if="activePane === 'plans'" class="mango-functional-case-pane">
              <a-table :data="relatedPlans" :loading="qualityLoading" :pagination="false" :scroll="{ x: 1160 }" row-key="id">
                <template #columns>
                  <a-table-column title="计划名称" :width="260"><template #cell="{ record }"><a-link @click="goPlan(record)">{{ record.name }}</a-link></template></a-table-column>
                  <a-table-column title="状态" :width="100"><template #cell="{ record }">{{ enumTitle(enumStore.functional_test_plan_status, record.status) }}</template></a-table-column>
                  <a-table-column title="执行进度" :width="160"><template #cell="{ record }">{{ record.execution_stats?.executed || 0 }}/{{ record.execution_stats?.total || 0 }}</template></a-table-column>
                  <a-table-column title="通过率" :width="100"><template #cell="{ record }">{{ formatPercent(record.execution_stats?.pass_rate) }}</template></a-table-column>
                  <a-table-column title="未关闭缺陷" data-index="open_defect_count" :width="110" />
                  <a-table-column title="负责人" :width="110"><template #cell="{ record }">{{ record.owner?.name || '-' }}</template></a-table-column>
                  <a-table-column title="更新时间" data-index="update_time" :width="165" />
                </template>
              </a-table>
            </div>

            <div v-else-if="activePane === 'defects'" class="mango-functional-case-pane">
              <a-table :data="relatedDefects" :loading="qualityLoading" :pagination="false" :scroll="{ x: 1120 }" row-key="id">
                <template #columns>
                  <a-table-column title="缺陷编号" :width="150"><template #cell="{ record }"><a-link @click="goDefect(record)">{{ record.defect_no }}</a-link></template></a-table-column>
                  <a-table-column title="缺陷标题" data-index="title" :width="300" ellipsis tooltip />
                  <a-table-column title="状态" :width="110"><template #cell="{ record }">{{ enumTitle(enumStore.functional_test_defect_status, record.status) }}</template></a-table-column>
                  <a-table-column title="严重程度" :width="110"><template #cell="{ record }">{{ enumTitle(enumStore.functional_test_defect_severity, record.severity) }}</template></a-table-column>
                  <a-table-column title="负责人" :width="110"><template #cell="{ record }">{{ record.assignee?.name || '未分配' }}</template></a-table-column>
                  <a-table-column title="更新时间" data-index="update_time" :width="165" />
                </template>
              </a-table>
            </div>

            <div v-else class="mango-functional-sync-pane">
              <section class="mango-functional-sync-editor">
                <mango-panel-spin :loading="resourceLoading">
                  <a-empty v-if="!rawCaseResources.length" description="暂无原始用例文档" />
                  <div v-else class="mango-functional-resource-list">
                    <div v-for="resource in rawCaseResources" :key="resource.id" class="mango-functional-resource-item">
                      <div class="mango-functional-resource-main">
                        <div class="mango-functional-resource-title">
                          <span>{{ resource.title }}</span>
                          <a-space :size="4">
                            <a-tag :color="enumColor(resource.content_type)" size="small">{{ enumTitle(enumStore.functional_test_context_content_type, resource.content_type) }}</a-tag>
                            <a-tag v-if="resource.content_type === RESOURCE_CONTENT_URL" :color="enumColor(resource.url_type)" size="small">
                              {{ enumTitle(enumStore.functional_test_context_url_type, resource.url_type) }}
                            </a-tag>
                            <a-tag v-if="!resource.enabled" :color="statusColor(0)" size="small">未启用</a-tag>
                          </a-space>
                        </div>
                        <div class="mango-functional-resource-content">
                          {{ resourceSummary(resource) }}
                        </div>
                      </div>
                      <MangoTableActions
                        :actions="[
    { label: '原文', onClick: () => openRawResource(resource) },
    { label: '编辑', onClick: () => openResource(resource) },
    { label: '删除', danger: true, onClick: () => removeResource(resource) },
]"
                      />
                    </div>
                  </div>
                </mango-panel-spin>
              </section>
            </div>
          </div>
        </section>

      </div>
      </div>
    </template>
  </TableBody>

  <a-drawer v-model:visible="caseVisible" title="功能测试用例" width="720px" @ok="saveCase">
    <a-form :model="caseForm" layout="vertical">
      <a-grid :cols="2" :col-gap="16">
        <a-grid-item>
          <a-form-item label="用例编号" required>
            <a-input v-model="caseForm.case_no" />
          </a-form-item>
        </a-grid-item>
        <a-grid-item>
          <a-form-item label="优先级" required>
            <a-select v-model="caseForm.priority" :options="enumStore.case_level" :field-names="fieldNames" />
          </a-form-item>
        </a-grid-item>
        <a-grid-item :span="2">
          <a-form-item label="测试类型" required>
            <a-select v-model="caseForm.test_types" :options="enumStore.manual_test_type" :field-names="fieldNames" multiple />
          </a-form-item>
        </a-grid-item>
        <a-grid-item>
          <a-form-item label="项目产品" required>
            <ProjectProductSelect v-model="caseForm.project_product" @change="caseForm.module = null" />
          </a-form-item>
        </a-grid-item>
        <a-grid-item>
          <a-form-item label="模块名称" required>
            <ProductModuleSelect v-model="caseForm.module" :project-product-id="caseForm.project_product" />
          </a-form-item>
        </a-grid-item>
        <a-grid-item :span="2">
          <a-alert class="mango-functional-case-tip" type="info">
            P0 发布阻塞风险；P1 常规回归与重点分支；P2 边界和低频分支；P3 低价值或暂不优先自动化。
          </a-alert>
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
          <a-alert class="mango-functional-case-tip" type="info">
            层级建议：接口/组件层约 70%，Integration 集成约 20%，E2E 端到端约 10%。验证类型用于区分正常、异常、边界、权限、数据和流程；执行场景统一使用回归、发布验证、冒烟、稳定性监测、数据校验、效果评测、生产巡检和生产回归。
          </a-alert>
        </a-grid-item>
      </a-grid>
      <a-form-item label="用例标题" required>
        <a-input v-model="caseForm.title" />
      </a-form-item>
      <a-form-item label="负责人" required>
        <a-select
          v-model="caseForm.owner"
          :options="userOptions"
          :field-names="fieldNames"
          allow-search
          placeholder="请选择负责人" data-testid="qa-views-functional-test-suite-details-select-请选择负责人"
        />
      </a-form-item>
      <a-form-item label="前置条件">
        <a-textarea v-model="caseForm.precondition" :auto-size="{ minRows: 2, maxRows: 5 }" />
      </a-form-item>
      <a-form-item label="测试场景" required>
        <a-textarea v-model="caseForm.test_point" :auto-size="{ minRows: 3, maxRows: 7 }" />
      </a-form-item>
      <a-form-item label="测试数据">
        <a-textarea v-model="caseForm.test_data" :auto-size="{ minRows: 2, maxRows: 5 }" />
      </a-form-item>
      <a-form-item label="备注">
        <a-textarea v-model="caseForm.remark" :auto-size="{ minRows: 2, maxRows: 5 }" />
      </a-form-item>
    </a-form>
  </a-drawer>

  <a-modal v-model:visible="bindVisible" title="手动绑定自动化用例" width="520px" @ok="confirmBind">
    <a-form :model="bindForm" layout="vertical">
      <a-form-item label="自动化类型">
        <a-select v-model="bindForm.automation_type" :options="enumStore.manual_test_automation_type" :field-names="fieldNames" />
      </a-form-item>
      <a-form-item label="自动化用例 ID" required>
        <a-input-number v-model="bindForm.automation_case_id" :min="1" />
      </a-form-item>
    </a-form>
  </a-modal>

  <BaseSidePanel
    :visible="resourceVisible"
    title="上下文资料"
    :width="760"
    @update:visible="(val) => { resourceVisible = val }"
    @cancel="resourceVisible = false"
  >
    <a-form :model="resourceForm" layout="vertical">
      <a-grid :cols="2" :col-gap="16">
        <a-grid-item>
          <a-form-item label="资料分组">
            <a-select v-model="resourceForm.context_key" :options="enumStore.functional_test_context_key" :field-names="fieldNames" disabled />
          </a-form-item>
        </a-grid-item>
        <a-grid-item>
          <a-form-item label="资料类型">
            <a-select v-model="resourceForm.content_type" :options="enumStore.functional_test_context_content_type" :field-names="fieldNames" />
          </a-form-item>
        </a-grid-item>
        <a-grid-item :span="2">
          <a-alert class="mango-functional-resource-readable-tip" type="info" show-icon>
            URL 需后端可访问且无需额外登录。私有链接、文件和图片可手工补充解析文本，便于查阅。
          </a-alert>
        </a-grid-item>
        <a-grid-item :span="2">
          <a-form-item label="标题" required>
            <a-input v-model="resourceForm.title" placeholder="请输入资料标题" data-testid="qa-views-functional-test-suite-details-input-请输入资料标题" />
          </a-form-item>
        </a-grid-item>
        <a-grid-item v-if="resourceForm.content_type === RESOURCE_CONTENT_URL" :span="2">
          <a-form-item label="URL类型">
            <a-select v-model="resourceForm.url_type" :field-names="fieldNames">
              <a-option :value="RESOURCE_URL_NORMAL" data-testid="qa-views-functional-test-suite-details-option-普通url">普通URL</a-option>
              <a-option :value="RESOURCE_URL_FEISHU" disabled data-testid="qa-views-functional-test-suite-details-option-飞书文档-后续开放">飞书文档（后续开放）</a-option>
            </a-select>
          </a-form-item>
        </a-grid-item>
        <a-grid-item v-if="[RESOURCE_CONTENT_TEXT, RESOURCE_CONTENT_URL].includes(resourceForm.content_type)" :span="2">
          <a-form-item :label="resourceForm.content_type === RESOURCE_CONTENT_URL ? 'URL或链接说明' : '文本内容'">
            <CodeEditor
              v-model="resourceForm.content"
              :code-style="{ width: '100%', height: '260px' }"
              :placeholder="resourceForm.content_type === RESOURCE_CONTENT_URL ? '请输入URL' : '请输入文本内容'"
            />
          </a-form-item>
        </a-grid-item>
        <a-grid-item v-if="[RESOURCE_CONTENT_FILE, RESOURCE_CONTENT_IMAGE].includes(resourceForm.content_type)" :span="2">
          <a-form-item label="上传文件">
            <a-upload
              v-model:file-list="resourceFileList"
              :auto-upload="false"
              :limit="1"
              :accept="resourceForm.content_type === RESOURCE_CONTENT_IMAGE ? 'image/*' : undefined"
              @change="onResourceFileChange"
              @before-remove="onRemoveResourceFile"
            />
            <div v-if="resourceForm.file_name" class="mango-functional-file-meta">当前文件：{{ resourceForm.file_name }}</div>
          </a-form-item>
        </a-grid-item>
        <a-grid-item v-if="[RESOURCE_CONTENT_FILE, RESOURCE_CONTENT_IMAGE].includes(resourceForm.content_type)" :span="2">
          <a-form-item label="文件说明或路径">
            <a-textarea v-model="resourceForm.content" :auto-size="{ minRows: 3, maxRows: 8 }" />
          </a-form-item>
        </a-grid-item>
        <a-grid-item :span="2">
          <a-form-item label="解析文本">
            <CodeEditor
              v-model="resourceForm.extracted_text"
              :code-style="{ width: '100%', height: '180px' }"
              placeholder="可在这里补充文件、图片或 URL 的文本内容。"
            />
          </a-form-item>
        </a-grid-item>
        <a-grid-item>
          <a-form-item label="启用">
            <a-switch v-model="resourceForm.enabled" />
          </a-form-item>
        </a-grid-item>
      </a-grid>
    </a-form>
    <template #extra-buttons>
      <a-button  type="primary" :loading="resourceLoading" @click="saveResource" data-testid="qa-views-functional-test-suite-details-button-保存">保存</a-button>
    </template>
  </BaseSidePanel>

  <BaseSidePanel
    :visible="rawResourceVisible"
    :title="rawResourceTitle"
    width="50vw"
    @update:visible="(val) => { rawResourceVisible = val }"
    @cancel="rawResourceVisible = false"
  >
    <div class="mango-functional-raw-viewer">
      <CodeEditor
        v-model="rawResourceEditText"
        :code-style="{ width: '100%', height: '100%' }"
        placeholder="暂无原文内容"
      />
    </div>
    <template #extra-buttons>
      <a-button  type="primary" :loading="resourceLoading" @click="saveRawResource" data-testid="qa-views-functional-test-suite-details-button-保存-2">保存</a-button>
    </template>
  </BaseSidePanel>

  <BaseSidePanel
    :visible="apiCaseDetailVisible"
    :title="apiCaseDetailTitle"
    width="calc(92vw - 150px)"
    mode="page"
    @update:visible="(val) => { apiCaseDetailVisible = val }"
    @cancel="apiCaseDetailVisible = false"
  >
    <div class="mango-functional-api-case-panel">
      <ApiCaseDetails
        v-if="apiCaseDetailVisible && apiCaseDetailId"
        :key="apiCaseDetailId"
        embedded
        :case-id="apiCaseDetailId"
        :project-product-id="suiteProjectProductId()"
        @close="apiCaseDetailVisible = false"
      />
    </div>
  </BaseSidePanel>
</template>

<script setup lang="ts">
  import { computed, onMounted, reactive, ref } from 'vue'

  import { Message, Modal } from '@arco-design/web-vue'

  import { useRoute, useRouter } from 'vue-router'

  import CodeEditor from '@/components/editors/CodeEditor.vue'

  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'

  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'

  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'

  import ApiCaseDetails from '@/views/apitest/case/details/index.vue'

  import { usePagination } from '@/hooks/table'

  import { useEnum } from '@/store/modules/get-enum'

  import { deleteFunctionalContextResource, deleteManualCase, getFunctionalContextResource, getRelatedFunctionalDefects, getRelatedFunctionalPlans, getManualCase, getManualSuite, postFunctionalContextResource, postManualAutomationBind, postManualCase, putFunctionalContextResource, putManualCase } from '@/api/functional-test'

  import { postUserFile } from '@/api/system/file_data'

  import { getUserName } from '@/api/user/user'

  import { formatModulePath, formatProjectProductPath } from '@/utils/business-format'

  import { getStatusTagColor, MANUAL_TEST_CHANGE_STATUS_COLORS, MANUAL_TEST_IMPACT_STATUS_COLORS } from '@/utils/status-color'

  const route = useRoute()

  const router = useRouter()

  const enumStore = useEnum()

  const fieldNames = { value: 'key', label: 'title' }

  const casePagination = usePagination(loadCases, () => caseLoading)

  const MANUAL_TEST_TYPE_MANUAL = 0

  const AUTOMATION_TYPE_API = 0

  const AUTOMATION_TYPE_UI = 1

  const RESOURCE_KEY_REQUIREMENT_DOC = 0

  const RESOURCE_KEY_DEVELOPMENT_DESIGN = 1

  const RESOURCE_KEY_API_DOC = 2

  const RESOURCE_KEY_DEVELOPMENT_CODE = 3

  const RESOURCE_KEY_SQL_QUERY = 4

  const RESOURCE_KEY_RAW_CASE_DOC = 5

  const RESOURCE_KEY_PLATFORM_CASE = 6

  const RESOURCE_KEY_PAGE_DATA = 7

  const RESOURCE_KEY_TEST_UNDERSTANDING = 8

  const RESOURCE_CONTENT_TEXT = 0

  const RESOURCE_CONTENT_URL = 1

  const RESOURCE_CONTENT_FILE = 2

  const RESOURCE_CONTENT_IMAGE = 3

  const RESOURCE_URL_NORMAL = 0

  const RESOURCE_URL_FEISHU = 1

  const RESOURCE_PARSE_NOT_PARSED = 0

  const suite = ref<any>(null)

  const cases = ref<any[]>([])

  const selectedCaseKeys = ref<Array<number | string>>([])

  const caseTableShellRef = ref<HTMLElement>()

  const caseFilters = reactive<any>({
    test_type: undefined,
    scenario_layer: undefined,
    scenario_type: undefined,
    scenario_tag: undefined,
    change_status: undefined,
    automation_impact_status: undefined,
  })

  const contextResources = ref<any[]>([])

  const relatedPlans = ref<any[]>([])

  const relatedDefects = ref<any[]>([])

  const currentCase = ref<any>(null)

  const suiteLoading = ref(false)

  const caseLoading = ref(false)

  const resourceLoading = ref(false)

  const qualityLoading = ref(false)

  const activePane = ref<number | string>('cases')

  const caseVisible = ref(false)

  const bindVisible = ref(false)

  const resourceVisible = ref(false)

  const rawResourceVisible = ref(false)

  const apiCaseDetailVisible = ref(false)

  const apiCaseDetailId = ref<number | string>('')

  const apiCaseDetailName = ref('')

  const caseForm = reactive<any>({})

  const userOptions = ref<any[]>([])

  const resourceForm = reactive<any>({})

  const rawResource = ref<any>(null)

  const rawResourceEditText = ref('')

  const resourceFile = ref<File | null>(null)

  const resourceFileList = ref<any[]>([])

  const bindForm = reactive<any>({ automation_type: AUTOMATION_TYPE_UI, automation_case_id: null })

  const rawCaseContextKey = RESOURCE_KEY_RAW_CASE_DOC

  const requirementDocNavItem = {
      key: RESOURCE_KEY_REQUIREMENT_DOC,
      title: '需求文档',
      description: '用于核对测试用例是否有遗漏',
      tip: '需求文档记录业务场景、异常场景与验收点，便于核对用例覆盖。',
  }

  const developmentDesignNavItem = {
      key: RESOURCE_KEY_DEVELOPMENT_DESIGN,
      title: '开发设计',
      description: '用于创建 API 接口、API 用例和数据工厂',
      tip: '开发设计记录接口实现方案、模块边界、核心流程和数据处理逻辑。',
  }

  const apiDocNavItem = {
      key: RESOURCE_KEY_API_DOC,
      title: '接口文档',
      description: '用于创建 API 接口、API 用例和数据工厂',
      tip: '接口文档记录请求方法、路径、参数、响应、鉴权和错误码。',
  }

  const developmentCodeNavItem = {
      key: RESOURCE_KEY_DEVELOPMENT_CODE,
      title: '开发代码',
      description: '用于识别数据库表关系并创建数据工厂',
      tip: '开发代码用于查阅落库逻辑、实体关系、枚举取值、字段默认值和依赖调用。',
  }

  const sqlQueryNavItem = {
      key: RESOURCE_KEY_SQL_QUERY,
      title: 'SQL语句',
      description: '用于识别数据库表关系并创建数据工厂',
      tip: 'SQL语句用于记录表名、字段、关联条件和数据校验方式。',
  }

  const rawCaseDocNavItem = {
    key: 'sync',
    title: '原始用例文档',
    description: '记录需求对应的原始用例文档',
    tip: '原始用例文档用于查阅来源内容并核对平台用例。',
  }

  const rawCaseDocContextItem = {
    ...rawCaseDocNavItem,
    key: RESOURCE_KEY_RAW_CASE_DOC,
  }

  const pageDataContextItem = {
    key: RESOURCE_KEY_PAGE_DATA,
    title: '页面数据',
    description: '用于补充页面实际数据和预期结果',
    tip: '页面数据记录页面字段、状态、展示数据和操作结果。',
  }

  const testUnderstandingContextItem = {
    key: RESOURCE_KEY_TEST_UNDERSTANDING,
    title: '测试理解',
    description: '用于补充测试人员理解和风险点',
    tip: '测试理解记录需求边界、风险点、异常路径与验收关注点。',
  }

  const platformCaseNavItem = {
    key: 'cases',
    title: '来源用例',
    description: '当前需求版本沉淀到用例库的功能用例',
    tip: '来源用例是当前需求版本沉淀到用例库的可复用资产，可继续维护字段和自动化绑定。',
  }

  const contextNavItems = [
    requirementDocNavItem,
    developmentDesignNavItem,
    apiDocNavItem,
    developmentCodeNavItem,
    sqlQueryNavItem,
    rawCaseDocContextItem,
    pageDataContextItem,
    testUnderstandingContextItem,
  ]

  const navGroups = [
    { title: '产品角色', items: [requirementDocNavItem] },
    { title: '开发角色', items: [developmentDesignNavItem, apiDocNavItem, developmentCodeNavItem, sqlQueryNavItem] },
    { title: '测试角色', items: [rawCaseDocNavItem, pageDataContextItem, testUnderstandingContextItem] },
    { title: '交付产物', items: [platformCaseNavItem] },
  ]

  const allNavItems = navGroups.flatMap((group) => group.items)

  const contextFieldKeys = new Set(contextNavItems.map((item) => item.key))

  const currentNavItem = computed(
    () => allNavItems.find((item) => item.key === activePane.value) || contextNavItems[0]
  )

  const activeContextField = computed(() => (contextFieldKeys.has(activePane.value) ? activePane.value : ''))

  const hasActiveContextField = computed(() => activeContextField.value !== '')

  const activeResources = computed(() => contextResources.value.filter((item) => Number(item.context_key) === Number(activeContextField.value)))

  const rawCaseResources = computed(() => contextResources.value.filter((item) => Number(item.context_key) === Number(rawCaseContextKey)))

  const rawResourceTitle = computed(() => rawResource.value?.title || '原文')

  const apiCaseDetailTitle = computed(() =>
    apiCaseDetailName.value ? `API 用例详情 / ${apiCaseDetailName.value}` : 'API 用例详情'
  )

  const rawResourceText = computed(() => {
    const resource = rawResource.value || {}
    if (resource.content_type === RESOURCE_CONTENT_TEXT) {
      return resource.content || ''
    }
    return resource.extracted_text || ''
  })

  const workbenchTitle = computed(() => {
    const id = suite.value?.id || route.query.id || '-'
    const name = suite.value?.requirement_name || '需求版本'
    return `需求用例工作台 / ${id} / ${name}`
  })

  const caseColumns = [
    { title: '用例编号', key: 'case_no', dataIndex: 'case_no', width: 120, ellipsis: true, tooltip: true },
    { title: '项目/产品', key: 'project_product', dataIndex: 'project_product', width: 160, ellipsis: true, tooltip: true },
    { title: '模块名称', key: 'module', dataIndex: 'module', width: 220, ellipsis: true, tooltip: true },
    { title: '标题', key: 'title', dataIndex: 'title', width: 240, ellipsis: true, tooltip: true },
    { title: '前置条件', key: 'precondition', dataIndex: 'precondition', width: 220, ellipsis: true, tooltip: true },
    { title: '测试场景', key: 'test_point', dataIndex: 'test_point', width: 260, ellipsis: true, tooltip: true },
    { title: '测试数据', key: 'test_data', dataIndex: 'test_data', width: 180, ellipsis: true, tooltip: true },
    { title: '测试类型', key: 'test_types', dataIndex: 'test_types', width: 220 },
    { title: '测试层级', key: 'scenario_layer', dataIndex: 'scenario_layer', width: 120 },
    { title: '验证类型', key: 'scenario_type', dataIndex: 'scenario_type', width: 110 },
    { title: '执行场景', key: 'scenario_tags', dataIndex: 'scenario_tags', width: 220 },
    { title: '自动化用例ID', key: 'automation_case_ids', dataIndex: 'automation_case_ids', width: 180 },
    { title: '变更', key: 'change_status', dataIndex: 'change_status', width: 100 },
    { title: '自动化影响', key: 'automation_impact_status', dataIndex: 'automation_impact_status', width: 120 },
    { title: '备注', key: 'remark', dataIndex: 'remark', width: 180, ellipsis: true, tooltip: true },
    { title: '操作', key: 'actions', dataIndex: 'actions', align: 'center', fixed: 'right', width: 160 },
  ]

  function enumTitle(options: any[] = [], value: any) {
    return options.find((item) => item.key === value)?.title || value || '-'
  }

  function formatPercent(value: any) {
    return `${Number(value || 0).toFixed(2).replace(/\.00$/, '')}%`
  }

  function enumColor(value: any) {
    return enumStore.colors?.[Number(value)]
  }

  function statusColor(value: any) {
    return enumStore.status_colors?.[Number(value)]
  }

  const changeStatusColor = (value: number) =>
    getStatusTagColor(MANUAL_TEST_CHANGE_STATUS_COLORS, value)

  const impactStatusColor = (value: number) =>
    getStatusTagColor(MANUAL_TEST_IMPACT_STATUS_COLORS, value)

  function bindingCaseId(record: any, type: number) {
    const binding = (record.bindings || []).find((item: any) => item.automation_type === type)
    return binding?.api_case_id || binding?.ui_case_id || binding?.automation_case_id
  }

  function automationCaseLinks(record: any) {
    const links = []
    const apiCaseId = bindingCaseId(record, AUTOMATION_TYPE_API)
    const uiCaseId = bindingCaseId(record, AUTOMATION_TYPE_UI)
    if (apiCaseId) links.push({ type: AUTOMATION_TYPE_API, label: `apiid：${apiCaseId}` })
    if (uiCaseId) links.push({ type: AUTOMATION_TYPE_UI, label: `uiid：${uiCaseId}` })
    return links
  }

  function suiteProjectProductId() {
    const projectProduct = suite.value?.project_product
    return projectProduct?.id || projectProduct || ''
  }

  function goAutomationCase(record: any, type: number) {
    const caseId = bindingCaseId(record, type)
    if (!caseId) return
    if (type === AUTOMATION_TYPE_API) {
      apiCaseDetailId.value = caseId
      apiCaseDetailName.value = record.title || ''
      apiCaseDetailVisible.value = true
      return
    }
    router.push({
      path: '/uitest/case/details',
      query: { id: caseId },
    })
  }

  function enabledContextResources(contextKey: number | string) {
    return contextResources.value.filter((item) => Number(item.context_key) === Number(contextKey) && item.enabled)
  }

  function contextResourceCount(contextKey: number | string) {
    if (Number(contextKey) === RESOURCE_KEY_PLATFORM_CASE) {
      return suite.value?.case_count || casePagination.pageCount || cases.value.length || 0
    }
    return enabledContextResources(contextKey).length
  }

  function navItemCount(item: any) {
    if (item.key === 'basic') return 1
    if (item.key === 'cases') {
      return suite.value?.case_count || casePagination.pageCount || cases.value.length || 0
    }
    if (item.key === 'sync') {
      return contextResourceCount(rawCaseContextKey)
    }
    if (item.key === 'plans') return relatedPlans.value.length
    if (item.key === 'defects') return relatedDefects.value.length
    if (contextFieldKeys.has(item.key)) {
      return contextResourceCount(item.key)
    }
    return 0
  }

  function navPaneHasData(item: any) {
    return Number(navItemCount(item)) > 0
  }

  function selectBestInitialPane(force = false) {
    const currentItem = allNavItems.find((item) => item.key === activePane.value)
    if (!force && currentItem && navPaneHasData(currentItem)) {
      return
    }
    if (navPaneHasData(platformCaseNavItem)) {
      activePane.value = platformCaseNavItem.key
      return
    }
    const firstValuableItem = allNavItems.find((item) => item.key !== platformCaseNavItem.key && navPaneHasData(item))
    activePane.value = firstValuableItem?.key ?? RESOURCE_KEY_REQUIREMENT_DOC
  }

  async function loadSuite() {
    suiteLoading.value = true
    try {
      const res = await getManualSuite({ id: route.query.id })
      suite.value = (res.data || [])[0] || null
    } finally {
      suiteLoading.value = false
    }
  }

  async function loadQualityRelations() {
    qualityLoading.value = true
    try {
      const [plansRes, defectsRes] = await Promise.all([
        getRelatedFunctionalPlans({ requirement_version_id: route.query.id }),
        getRelatedFunctionalDefects({ requirement_version_id: route.query.id }),
      ])
      relatedPlans.value = plansRes.data || []
      relatedDefects.value = defectsRes.data || []
    } finally { qualityLoading.value = false }
  }

  function goPlan(record: any) {
    router.push({ path: '/functional-test/plan/details', query: { id: record.id } })
  }

  function goDefect(record: any) {
    router.push({ path: '/functional-test/defect/index', query: { defect_id: record.id } })
  }

  function createRequirementPlan() {
    router.push({
      path: '/functional-test/plan/index',
      query: {
        create: '1',
        requirement_version: route.query.id,
        project_product: suiteProjectProductId(),
      },
    })
  }

  async function loadCases() {
    caseLoading.value = true
    try {
      const res = await getManualCase({
        suite: route.query.id,
        page: casePagination.page,
        pageSize: casePagination.pageSize,
        ...caseFilterPayload(),
      })
      cases.value = res.data || []
      selectedCaseKeys.value = selectedCaseKeys.value.filter((key) => cases.value.some((item) => item.id === key))
      casePagination.setTotalSize((res as any).totalSize || cases.value.length)
    } finally {
      caseLoading.value = false
    }
  }

  function caseFilterPayload() {
    return Object.fromEntries(
      Object.entries(caseFilters).filter(([, value]) => value !== undefined && value !== null && value !== '')
    )
  }

  function searchCases() {
    casePagination.page = 1
    selectedCaseKeys.value = []
    loadCases()
  }

  function resetCaseFilters() {
    Object.keys(caseFilters).forEach((key) => {
      caseFilters[key] = undefined
    })
    searchCases()
  }

  function batchDeleteCases() {
    if (!selectedCaseKeys.value.length) {
      Message.warning('请选择要删除的用例')
      return
    }
    Modal.confirm({
      title: '批量删除用例',
      content: `确认删除已选择的 ${selectedCaseKeys.value.length} 条用例吗？`,
      okText: '删除',
      cancelText: '取消',
      onBeforeOk: async () => {
        caseLoading.value = true
        try {
          await deleteManualCase({ ids: selectedCaseKeys.value })
          Message.success('删除成功')
          selectedCaseKeys.value = []
          await Promise.all([loadCases(), loadSuite()])
        } finally {
          caseLoading.value = false
        }
      },
    })
  }

  async function loadContextResources() {
    resourceLoading.value = true
    try {
      const res = await getFunctionalContextResource({ suite: route.query.id, page: 1, pageSize: 200 })
      contextResources.value = (res.data || []).map((item: any) => ({ ...item, context_key: Number(item.context_key) }))
    } finally {
      resourceLoading.value = false
    }
  }

  async function refreshAll() {
    await Promise.all([loadSuite(), loadCases(), loadContextResources(), loadQualityRelations()])
    selectBestInitialPane()
  }

  function resourceSummary(resource: any) {
    if (resource.extracted_text) return resource.extracted_text
    if (resource.content) return resource.content
    if (resource.file_name || resource.file_path) return [resource.file_name, resource.file_path].filter(Boolean).join(' / ')
    return '暂无内容'
  }

  function openRawResource(resource: any) {
    rawResource.value = resource
    rawResourceEditText.value = rawResourceText.value === '暂无原文内容' ? '' : rawResourceText.value
    rawResourceVisible.value = true
  }

  async function saveRawResource() {
    if (!rawResource.value?.id) return
    resourceLoading.value = true
    try {
      const payload = { ...rawResource.value }
      if (payload.content_type === RESOURCE_CONTENT_TEXT) {
        payload.content = rawResourceEditText.value
      } else {
        payload.extracted_text = rawResourceEditText.value
      }
      await putFunctionalContextResource(payload)
      Message.success('原文已保存')
      rawResourceVisible.value = false
      await loadContextResources()
    } finally {
      resourceLoading.value = false
    }
  }

  function openResource(record?: any, contextKey = activeContextField.value) {
    const navItem = allNavItems.find((item) => item.key === contextKey)
    Object.keys(resourceForm).forEach((key) => delete resourceForm[key])
    Object.assign(
      resourceForm,
      record || {
        suite: Number(route.query.id),
        context_key: contextKey,
        content_type: RESOURCE_CONTENT_TEXT,
        url_type: RESOURCE_URL_NORMAL,
        title: navItem?.title || currentNavItem.value.title,
        content: '',
        extracted_text: '',
        enabled: true,
      }
    )
    resourceFile.value = null
    resourceFileList.value = []
    resourceVisible.value = true
  }

  function onResourceFileChange(fileList: any[], fileItem: any) {
    resourceFileList.value = fileList.slice(-1)
    resourceFile.value = fileItem?.file || resourceFileList.value[0]?.file || null
  }

  function onRemoveResourceFile() {
    resourceFile.value = null
    resourceFileList.value = []
    return true
  }

  async function uploadResourceFileIfNeeded() {
    if (!resourceFile.value) return {}
    const formData = new FormData()
    const originalName = resourceFile.value.name
    formData.append('test_file', resourceFile.value)
    formData.append('type', '0')
    formData.append('name', `${Date.now()}-${originalName}`)
    const projectProductId = suite.value?.project_product?.id || suite.value?.project_product
    if (projectProductId) {
      formData.append('project_product', String(projectProductId))
    }
    const res = await postUserFile(formData)
    const fileData = res.data || {}
    return {
      file: fileData.id,
      file_name: originalName,
      file_path: fileData.test_file || fileData.file_path || '',
      mime_type: resourceFile.value.type || '',
      file_size: resourceFile.value.size || null,
      parse_status: RESOURCE_PARSE_NOT_PARSED,
    }
  }

  async function saveResource() {
    if (!resourceForm.title) {
      Message.error('请输入资料标题')
      return
    }
    if (resourceForm.url_type === RESOURCE_URL_FEISHU) {
      Message.error('飞书文档后续开放，请先选择普通URL')
      return
    }
    resourceLoading.value = true
    try {
      const filePayload = await uploadResourceFileIfNeeded()
      const payload = {
        ...resourceForm,
        ...filePayload,
        suite: Number(route.query.id),
        context_key: resourceForm.context_key ?? (hasActiveContextField.value ? activeContextField.value : rawCaseContextKey),
        url_type: resourceForm.content_type === RESOURCE_CONTENT_URL ? resourceForm.url_type || RESOURCE_URL_NORMAL : RESOURCE_URL_NORMAL,
      }
      const action = payload.id ? putFunctionalContextResource : postFunctionalContextResource
      await action(payload)
      Message.success('资料已保存')
      resourceVisible.value = false
      await loadContextResources()
      selectBestInitialPane()
    } finally {
      resourceLoading.value = false
    }
  }

  function removeResource(resource: any) {
    Modal.confirm({
      title: '删除资料',
      content: `确认删除「${resource.title}」吗？`,
      okText: '删除',
      cancelText: '取消',
      onBeforeOk: async () => {
        await deleteFunctionalContextResource(resource.id)
        Message.success('已删除')
        await loadContextResources()
        selectBestInitialPane()
      },
    })
  }

  function openCase(record?: any) {
    Object.keys(caseForm).forEach((key) => delete caseForm[key])
    Object.assign(
      caseForm,
      record
        ? {
            ...record,
            project_product: record.project_product?.id || record.project_product,
            module: record.module?.id || record.module,
            owner: record.owner?.id || record.owner,
          }
        : {
            suite: Number(route.query.id),
            priority: 1,
            test_types: [MANUAL_TEST_TYPE_MANUAL],
            scenario_layer: 0,
            scenario_type: 0,
            scenario_tags: [],
            title: '',
            test_point: '',
            project_product: suite.value?.project_product?.id || suite.value?.project_product,
            module: suite.value?.module?.id || suite.value?.module,
            owner: suite.value?.owner?.id || suite.value?.owner,
          }
    )
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
    if (caseForm.scenario_layer === undefined || caseForm.scenario_layer === null || caseForm.scenario_layer === '') {
      Message.error('请选择测试层级')
      return false
    }
    if (caseForm.scenario_type === undefined || caseForm.scenario_type === null || caseForm.scenario_type === '') {
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
    const action = caseForm.id ? putManualCase : postManualCase
    await action({ ...caseForm, suite: Number(route.query.id) })
    Message.success('保存成功')
    caseVisible.value = false
    refreshAll()
  }

  function openBind(record: any, type: number) {
    currentCase.value = record
    bindForm.automation_type = type
    bindForm.automation_case_id = null
    bindVisible.value = true
  }

  async function confirmBind() {
    await postManualAutomationBind({ case_id: currentCase.value.id, ...bindForm })
    Message.success('绑定成功')
    bindVisible.value = false
    refreshAll()
  }

  onMounted(async () => {
    await enumStore.getEnum(true)
    getUserName().then((res) => (userOptions.value = res.data || []))
    await refreshAll()
    selectBestInitialPane(true)
  })
</script>

<style scoped>
  .mango-functional-workbench {
    display: grid;
    grid-template-columns: 220px minmax(0, 1fr);
    gap: var(--m-page-gap);
    height: calc(100% - var(--m-page-gap));
    margin-top: var(--m-page-gap);
    min-height: 0;
  }

  .mango-functional-workbench-scroll {
    --mango-workbench-min-width: 710px;
  }

  .mango-functional-workbench-scroll > .mango-functional-workbench {
    min-width: var(--mango-workbench-min-width);
  }

  .mango-functional-workbench-case {
    align-items: stretch;
    height: calc(100% - var(--m-page-gap));
    min-height: 0;
  }

  .mango-functional-nav,
  .mango-functional-main-panel {
    min-height: 0;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
  }

  .mango-functional-nav {
    display: flex;
    overflow: auto;
    flex-direction: column;
    gap: 14px;
    padding: 12px;
  }

  .mango-functional-workbench-case .mango-functional-nav {
    align-self: start;
    height: 100%;
    overflow: auto;
  }

  .mango-functional-nav-head {
    padding-bottom: 12px;
    border-bottom: 1px solid var(--m-border);
  }

  .mango-functional-nav-head-title {
    color: var(--m-text);
    font-size: 15px;
    font-weight: 600;
    line-height: 22px;
  }

  .mango-functional-nav-head-subtitle {
    margin-top: 2px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .mango-functional-nav-section {
    min-width: 0;
  }

  .mango-functional-nav-title,
  .mango-functional-panel-title {
    color: var(--m-text);
    font-size: 15px;
    font-weight: 600;
    line-height: 22px;
  }

  .mango-functional-nav-title {
    margin-bottom: 8px;
  }

  .mango-functional-nav-items {
    display: flex;
    max-height: 158px;
    min-height: 0;
    overflow-x: hidden;
    overflow-y: auto;
    flex-direction: column;
    gap: 8px;
    padding-right: 3px;
    scrollbar-width: thin;
    scrollbar-color: var(--m-scrollbar-thumb) transparent;
  }

  .mango-functional-nav-items::-webkit-scrollbar {
    width: 4px;
  }

  .mango-functional-nav-items::-webkit-scrollbar-track {
    background: transparent;
  }

  .mango-functional-nav-items::-webkit-scrollbar-thumb {
    border-radius: 999px;
    background: var(--m-scrollbar-thumb);
  }

  .mango-functional-panel-subtitle {
    margin-top: 2px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .mango-functional-nav-item {
    display: block;
    width: 100%;
    margin: 0;
    padding: 9px 10px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface-soft);
    color: var(--m-text-2);
    cursor: pointer;
    text-align: left;
    transition: border-color 0.2s ease, background 0.2s ease;
  }

  .mango-functional-nav-item:hover {
    border-color: color-mix(in srgb, var(--m-primary) 28%, var(--m-border));
    background: var(--m-surface);
  }

  .mango-functional-nav-item-active {
    border-color: var(--m-primary);
    background: color-mix(in srgb, var(--m-primary) 7%, var(--m-surface));
  }

  .mango-functional-nav-item .mango-functional-nav-item-row,
  .mango-functional-nav-item .mango-functional-nav-item-row span,
  .mango-functional-nav-item small {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-functional-nav-item .mango-functional-nav-item-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    min-width: 0;
  }

  .mango-functional-nav-item .mango-functional-nav-item-row span {
    min-width: 0;
    color: var(--m-text);
    font-size: 13px;
    font-weight: 600;
    line-height: 20px;
  }

  .mango-functional-nav-item .mango-functional-nav-item-row em {
    flex-shrink: 0;
    min-width: 20px;
    padding: 0 6px;
    border: 1px solid var(--m-border);
    border-radius: 999px;
    background: var(--m-surface);
    color: var(--m-text-2);
    font-size: 12px;
    font-style: normal;
    line-height: 18px;
    text-align: center;
  }

  .mango-functional-nav-item small {
    margin-top: 2px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .mango-functional-main-panel {
    display: flex;
    min-width: 0;
    overflow: hidden;
    flex-direction: column;
  }

  .mango-functional-workbench-case .mango-functional-main-panel {
    display: flex;
    height: 100%;
    overflow: hidden;
  }

  .mango-functional-panel-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    min-height: 58px;
    padding: 10px 12px;
    border-bottom: 1px solid var(--m-border);
  }

  .mango-functional-panel-body {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
    overflow: auto;
    padding: 12px;
  }

  .mango-functional-panel-body-case {
    display: block;
    flex: 1;
    min-height: 0;
    padding: 0;
    overflow-x: hidden;
    overflow-y: auto;
  }

  .mango-functional-panel-body > :deep(.arco-spin) {
    height: 100%;
  }

  .mango-functional-resource-pane {
    flex: 1;
    min-height: 0;
  }

  .mango-functional-case-pane {
    display: block;
    flex: none;
    min-height: 0;
  }

  .mango-functional-case-filters {
    display: grid;
    grid-template-columns: repeat(6, minmax(120px, 1fr)) auto;
    gap: 8px;
    align-items: center;
    padding: 10px 12px;
    border-bottom: 1px solid var(--m-border);
  }

  .mango-functional-case-table {
    display: block;
    flex: none;
    min-height: 0;
    min-width: 0;
    padding-bottom: 45px;
  }

  .mango-functional-case-table :deep(.arco-table) {
    display: block;
    flex: none;
    min-width: 0;
    min-height: 0;
  }

  .mango-functional-case-table :deep(.arco-table-container) {
    flex: none;
    min-height: 0;
  }

  .mango-functional-case-table :deep(.arco-spin),
  .mango-functional-case-table :deep(.arco-table-content),
  .mango-functional-case-table :deep(.arco-scrollbar),
  .mango-functional-case-table :deep(.arco-scrollbar-container) {
    min-height: 0;
  }

  .mango-functional-case-table :deep(.arco-table-body) {
    max-height: none;
  }

  .mango-functional-case-footer {
    position: sticky;
    z-index: 30;
    bottom: 0;
    flex-shrink: 0;
    margin-top: -45px;
    background: var(--m-surface);
  }

  .mango-functional-case-table :deep(.arco-table-td-fixed-right),
  .mango-functional-case-table :deep(.arco-table-th-fixed-right),
  .mango-functional-case-table :deep(.arco-table-cell-fixed-right) {
    z-index: 10;
  }

  .mango-functional-resource-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .mango-functional-resource-item {
    display: grid;
    align-items: flex-start;
    grid-template-columns: minmax(0, 1fr) 170px;
    gap: 12px;
    min-width: 0;
    padding: 12px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    background: var(--m-surface);
  }

  .mango-functional-resource-main {
    min-width: 0;
  }

  .mango-functional-resource-title {
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
    color: var(--m-text);
    font-weight: 600;
    line-height: 22px;
  }

  .mango-functional-resource-title span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-functional-resource-content {
    display: -webkit-box;
    overflow: hidden;
    margin-top: 6px;
    color: var(--m-text-2);
    font-size: 12px;
    line-height: 20px;
    white-space: pre-wrap;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 4;
  }

  .mango-functional-file-meta {
    margin-top: 8px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .mango-functional-resource-readable-tip {
    margin-bottom: 4px;
  }

  .mango-functional-raw-viewer {
    height: 100%;
    min-height: 0;
  }

  .mango-functional-api-case-panel {
    min-width: 0;
    min-height: 0;
  }

  .mango-functional-api-case-panel :deep(.mango-detail-workbench-page) {
    height: 100%;
    min-height: 0;
  }

  .mango-functional-case-tip {
    margin-bottom: 4px;
  }

  .mango-functional-sync-pane {
    display: flex;
    flex-direction: column;
    min-height: 0;
  }

  .mango-functional-sync-editor {
    min-width: 0;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }
</style>
