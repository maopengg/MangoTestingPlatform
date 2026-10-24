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
            <div class="mango-functional-nav-head-title">用例生成</div>
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
              <a-button v-permission="'functional.suite:create'" size="small" type="primary" @click="openResource()" data-testid="qa-views-functional-test-suite-details-button-新增资料">新增资料</a-button>
            </a-space>
            <a-space v-else-if="activePane === 'cases'">
              <a-button v-permission="'functional.case:delete'" size="small" status="danger" :loading="caseLoading" @click="batchDeleteCases" data-testid="qa-views-functional-test-suite-details-button-批量删除">
                批量删除
              </a-button>
              <a-button v-permission="'ai.task:execute'" size="small" type="primary" status="success" :loading="suiteLoading || resourceLoading" @click="continueDialog('case')" data-testid="qa-views-functional-test-suite-details-button-自动生成">自动生成</a-button>
              <a-button v-permission="'ai.task:execute'" size="small" type="primary" status="success" :loading="apiPlanSubmitting" @click="openSelectedBatchApiPlanDialog" data-testid="qa-views-functional-test-suite-details-button-批量api">批量API</a-button>
              <a-button v-permission="'functional.case:create'" size="small" type="primary" @click="openCase()" data-testid="qa-views-functional-test-suite-details-button-手动新增">手动新增</a-button>
            </a-space>
            <a-space v-else-if="activePane === 'sync'">
              <a-button size="small" :loading="resourceLoading" @click="loadContextResources" data-testid="qa-views-functional-test-suite-details-button-刷新-2">刷新</a-button>
              <a-button v-permission="'functional.suite:create'" size="small" type="primary" @click="openResource(undefined, rawCaseContextKey)" data-testid="qa-views-functional-test-suite-details-button-新增资料-2">新增资料</a-button>
            </a-space>
            <a-space v-else-if="activePane === 'basic'">
              <a-button size="small" :loading="suiteLoading || qualityLoading" @click="refreshAll">刷新</a-button>
            </a-space>
            <a-space v-else-if="['plans', 'defects'].includes(String(activePane))">
              <a-button size="small" :loading="qualityLoading" @click="loadQualityRelations">刷新</a-button>
              <a-button v-permission="'functional.plan:create'" v-if="activePane === 'plans'" size="small" type="primary" @click="createRequirementPlan">新建测试计划</a-button>
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
                        { permission: 'functional.suite:detail', label: '原文', onClick: () => openRawResource(resource) },
                        { permission: 'functional.suite:edit', label: '编辑', onClick: () => openResource(resource) },
                        { permission: 'functional.suite:delete', label: '删除', danger: true, onClick: () => removeResource(resource) },
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
                        <a-link v-permission="['functional.case:create', 'functional.case:edit']" @click="openCase(record)">{{ record.title }}</a-link>
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
                            { permission: 'functional.case:edit', label: '编辑', onClick: () => openCase(record) },
                            { permission: 'ai.task:execute', label: 'API生成', loading: actionLoading === `plan-${record.id}`, onClick: () => openApiPlanDialog(record) },
                            { permission: 'functional.case:edit', label: 'UI绑定', onClick: () => openBind(record, AUTOMATION_TYPE_UI) },
                            { permission: 'api.case',
                              label: '前往API用例',
                              disabled: !bindingCaseId(record, AUTOMATION_TYPE_API),
                              onClick: () => goAutomationCase(record, AUTOMATION_TYPE_API),
                            },
                            { permission: 'ui.case',
                              label: '前往UI用例',
                              disabled: !bindingCaseId(record, AUTOMATION_TYPE_UI),
                              onClick: () => goAutomationCase(record, AUTOMATION_TYPE_UI),
                            },
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
                          { permission: 'functional.suite:detail', label: '原文', onClick: () => openRawResource(resource) },
                          { permission: 'functional.suite:edit', label: '编辑', onClick: () => openResource(resource) },
                          { permission: 'functional.suite:delete', label: '删除', danger: true, onClick: () => removeResource(resource) },
                        ]"
                      />
                    </div>
                  </div>
                </mango-panel-spin>
              </section>
            </div>
          </div>
        </section>

        <aside class="mango-functional-side-panel">
          <div class="mango-functional-side-head">
            <div>
              <div class="mango-functional-side-title">生成进度</div>
              <div class="mango-functional-side-subtitle">用例生成与自动化任务状态</div>
            </div>
          </div>
          <div class="mango-functional-metrics">
            <div>
              <span>用例数</span>
              <strong>{{ suite?.case_count || 0 }}</strong>
            </div>
            <div>
              <span>自动化数</span>
              <strong>{{ suite?.automated_case_count || 0 }}</strong>
            </div>
            <div>
              <span>完成百分比</span>
              <strong>{{ suite?.automation_coverage_percent || 0 }}%</strong>
            </div>
          </div>
          <div class="mango-functional-task-card">
            <mango-panel-spin :loading="caseDialogLoading || caseTaskLoading || contextHistoryLoading">
              <div class="mango-functional-task-card-head">
                <div class="mango-functional-task-card-title">生成用例对话</div>
                <div class="mango-functional-dialog-status">
                  <a-tag size="small" :color="dialogStatusColor(latestCaseTask)">{{ dialogStatusText(latestCaseTask, caseDialogHistories) }}</a-tag>
                  <a-tooltip v-if="isDialogFailed(latestCaseTask)" content="重新生成">
                    <a-button v-permission="'ai.task:retry'" size="mini" type="text" :loading="syncLoading" @click="retryFailedDialog('case')">
                      <template #icon><icon-refresh /></template>
                    </a-button>
                  </a-tooltip>
                  <a-button v-permission="'ai.task:retry'"
                    v-if="latestCaseTask?.status === TASK_STATUS_WAITING_CONFIRM"
                    size="mini"
                    type="primary"
                    @click="openAmbiguityConfirmation" data-testid="qa-views-functional-test-suite-details-button-确认"
                  >
                    确认
                  </a-button>
                </div>
              </div>
              <a-progress
                :percent="dialogProgress(latestCaseTask, caseDialogHistories) / 100"
                :status="dialogProgressStatus(latestCaseTask)"
                size="small"
              />
              <div class="mango-functional-dialog-meta">
                <span>{{ dialogProgressText(latestCaseTask, caseDialogHistories) }}</span>
                <small>{{ dialogContextSummary(caseDialogHistories) }}</small>
                <small v-if="latestCaseTask?.error_message" class="mango-functional-task-error">{{ latestCaseTask.error_message }}</small>
              </div>
              <div class="mango-functional-dialog-history">
                <div v-for="item in caseDialogHistories.slice(0, 2)" :key="item.id" class="mango-functional-dialog-line">
                  <span>{{ item.summary || contextHistoryTitle(item) }}</span>
                  <small>{{ contextHistoryMeta(item) }}</small>
                </div>
                <a-empty v-if="!caseDialogHistories.length" description="暂无对话记录" />
              </div>
              <a-space class="mango-functional-dialog-actions">
                <a-button v-permission="'ai.task:execute'" size="small" type="primary" :loading="suiteLoading || resourceLoading" @click="continueDialog('case')" data-testid="qa-views-functional-test-suite-details-button-继续追问">继续追问</a-button>
                <a-button v-permission="'ai.task:detail'" size="small" @click="openConversationDetail('case')" data-testid="qa-views-functional-test-suite-details-button-查看对话">查看对话</a-button>
                <a-button v-permission="'ai.task:delete'" size="small" status="danger" :loading="contextHistoryLoading" @click="clearConversation('case')" data-testid="qa-views-functional-test-suite-details-button-清空">清空</a-button>
              </a-space>
            </mango-panel-spin>
          </div>
          <div class="mango-functional-task-card">
            <mango-panel-spin :loading="apiDialogLoading || apiTaskLoading || contextHistoryLoading">
              <div class="mango-functional-task-card-head">
                <div class="mango-functional-task-card-title">生成 API 自动化对话</div>
                <div class="mango-functional-dialog-status">
                  <a-tag size="small" :color="dialogStatusColor(latestApiTask)">{{ dialogStatusText(latestApiTask, apiDialogHistories) }}</a-tag>
                  <a-tooltip v-if="isDialogFailed(latestApiTask)" :content="latestApiTask?.input_data?.mode === 'batch' ? '继续生成' : '重新生成'">
                    <a-button v-permission="'ai.task:retry'" size="mini" type="text" :loading="!!actionLoading" @click="retryFailedDialog('api')">
                      <template #icon><icon-refresh /></template>
                    </a-button>
                  </a-tooltip>
                </div>
              </div>
              <a-progress
                :percent="dialogProgress(latestApiTask, apiDialogHistories) / 100"
                :status="dialogProgressStatus(latestApiTask)"
                size="small"
              />
              <div class="mango-functional-dialog-meta">
                <span>{{ dialogProgressText(latestApiTask, apiDialogHistories) }}</span>
                <small>{{ dialogContextSummary(apiDialogHistories) }}</small>
                <small v-if="latestApiTask?.error_message" class="mango-functional-task-error">{{ latestApiTask.error_message }}</small>
              </div>
              <div class="mango-functional-dialog-history">
                <div v-for="item in apiDialogHistories.slice(0, 2)" :key="item.id" class="mango-functional-dialog-line">
                  <span>{{ item.summary || contextHistoryTitle(item) }}</span>
                  <small>{{ contextHistoryMeta(item) }}</small>
                </div>
                <a-empty v-if="!apiDialogHistories.length" description="暂无对话记录" />
              </div>
              <a-space class="mango-functional-dialog-actions">
                <a-button v-permission="'ai.task:execute'" size="small" type="primary" :disabled="!currentCase" :loading="suiteLoading || resourceLoading" @click="continueDialog('api')" data-testid="qa-views-functional-test-suite-details-button-继续追问-2">继续追问</a-button>
                <a-button v-permission="'ai.task:detail'" size="small" @click="openConversationDetail('api')" data-testid="qa-views-functional-test-suite-details-button-查看对话-2">查看对话</a-button>
                <a-button v-permission="'ai.task:delete'" size="small" status="danger" :loading="contextHistoryLoading" @click="clearConversation('api')" data-testid="qa-views-functional-test-suite-details-button-清空-2">清空</a-button>
              </a-space>
            </mango-panel-spin>
          </div>
        </aside>
      </div>
      </div>
    </template>
  </TableBody>

  <a-modal
    v-model:visible="ambiguityConfirmVisible"
    title="确认需求歧义"
    :ok-loading="ambiguityConfirmLoading"
    :on-before-ok="confirmRequirementAmbiguities"
  >
    <a-alert type="warning">以下内容会影响测试预期，请补充明确结论后继续生成。</a-alert>
    <div class="mango-functional-ambiguity-list">
      <div v-for="(item, index) in waitingConfirmationAmbiguities" :key="index">
        {{ index + 1 }}. {{ item.description || item }}
      </div>
    </div>
    <a-textarea
      v-model="ambiguityConfirmationAnswer"
      :max-length="4000"
      :auto-size="{ minRows: 4, maxRows: 10 }"
      show-word-limit
      placeholder="请说明采用哪种业务规则或预期结果" data-testid="qa-views-functional-test-suite-details-textarea-请说明采用哪种业务规则或预期结果"
    />
  </a-modal>

  <a-modal
    v-model:visible="syncDialogVisible"
    title="同步功能测试用例"
    width="760px"
    :ok-loading="syncSubmitting"
    @before-ok="submitSyncDialog"
  >
    <div class="mango-functional-ai-dialog">
      <div class="mango-functional-ai-context-panel">
        <div class="mango-functional-ai-panel-title">上下文</div>
        <div v-for="group in contextSelectionGroups" :key="group.title" class="mango-functional-ai-context-section">
          <div class="mango-functional-ai-context-title">{{ group.title }}</div>
          <a-checkbox-group v-model="syncForm.context_keys" class="mango-functional-ai-context-options">
            <a-checkbox
              v-for="item in group.items"
              :key="item.key"
              :value="item.key"
              :disabled="!contextResourceCount(item.key)"
            >
              <div class="mango-functional-ai-context-option">
                <span>{{ item.title }}</span>
                <small>{{ contextResourceCount(item.key) }} 份资料 / {{ item.description }}</small>
              </div>
            </a-checkbox>
          </a-checkbox-group>
        </div>
      </div>
      <div class="mango-functional-ai-context-panel">
        <div class="mango-functional-ai-panel-title mango-functional-ai-panel-title--actions">
          <span>历史版本参考</span>
          <a-button
            size="mini"
            :disabled="!previousRequirementVersion"
            @click="selectPreviousRequirementVersion" data-testid="qa-views-functional-test-suite-details-button-选择上一版本"
          >选择上一版本</a-button>
        </div>
        <mango-panel-spin :loading="historicalContextLoading">
          <a-empty v-if="!historicalContextSuites.length" description="暂无可选历史上下文" />
          <div v-else class="mango-functional-history-context-list">
            <div v-for="item in historicalContextSuites" :key="item.suite_id" class="mango-functional-history-context-item">
              <div class="mango-functional-history-context-head">
                <strong>{{ item.requirement_name }}</strong>
                <span>{{ item.relation === 'requirement_version' ? '同一需求历史版本' : '同模块历史需求' }}</span>
              </div>
              <small>V{{ item.version_no || '-' }} / {{ item.iteration || '未填写迭代' }} / {{ item.module_path || item.module_name || '未绑定模块' }}</small>
              <a-checkbox-group v-model="syncForm.historical_selections" class="mango-functional-history-context-options">
                <a-checkbox
                  v-for="resource in item.resources || []"
                  :key="`${item.suite_id}:resource:${resource.id}`"
                  :value="`${item.suite_id}:resource:${resource.id}`"
                  :disabled="!resource.selectable"
                >
                  {{ resource.title }}
                </a-checkbox>
                <a-checkbox
                  v-if="item.case_count"
                  :value="`${item.suite_id}:cases`" data-testid="qa-views-functional-test-suite-details-checkbox-测试平台用例-条"
                >
                  测试平台用例（{{ item.case_count }} 条）
                </a-checkbox>
              </a-checkbox-group>
            </div>
          </div>
        </mango-panel-spin>
      </div>
      <div class="mango-functional-ai-option-row">
        <div class="mango-functional-ai-option-field">
          <span>AI角色：</span>
          <a-select
            v-model="syncForm.ai_role"
            :options="aiRoleOptions"
            :field-names="fieldNames"
            :allow-clear="false"
            placeholder="请选择角色提示词" data-testid="qa-views-functional-test-suite-details-select-请选择角色提示词"
          />
        </div>
        <div class="mango-functional-ai-option-field">
          <span>技能：</span>
          <a-select
            v-model="syncForm.skill_id"
            :options="functionalCaseSkillOptions"
            :loading="aiOptionLoading"
            :field-names="fieldNames"
            allow-clear
            placeholder="请选择技能" data-testid="qa-views-functional-test-suite-details-select-请选择技能"
          />
        </div>
      </div>
      <div class="mango-functional-ai-extra-options">
        <a-checkbox v-model="syncForm.deep_check" data-testid="qa-views-functional-test-suite-details-checkbox-深度补漏">
          深度补漏
        </a-checkbox>
        <span>开启后会在快速生成后额外核对需求和原始用例，补充可能遗漏的场景，耗时会增加。</span>
      </div>
      <a-form layout="vertical" class="mango-functional-ai-form">
        <a-form-item label="追问/补充要求">
          <a-textarea v-model="syncForm.user_instruction" placeholder="补充本次生成用例的追问或要求" :auto-size="{ minRows: 2, maxRows: 4 }" data-testid="qa-views-functional-test-suite-details-textarea-补充本次生成用例的追问或要求" />
        </a-form-item>
      </a-form>
    </div>
  </a-modal>

  <a-modal
    v-model:visible="apiPlanDialogVisible"
    :title="apiPlanDialogTitle"
    width="820px"
    :ok-loading="apiPlanSubmitting"
    @before-ok="submitApiPlanDialog"
  >
    <div class="mango-functional-ai-dialog">
      <a-alert v-if="apiPlanSummary" class="mango-functional-ai-summary" type="info">
        {{ apiPlanSummary }}
      </a-alert>
      <div class="mango-functional-ai-context-panel">
        <div class="mango-functional-ai-panel-title">上下文</div>
        <div v-for="group in apiContextSelectionGroups" :key="group.title" class="mango-functional-ai-context-section">
          <div class="mango-functional-ai-context-title">{{ group.title }}</div>
          <a-checkbox-group v-model="apiPlanForm.context_keys" class="mango-functional-ai-context-options">
            <a-checkbox
              v-for="item in group.items"
              :key="item.key"
              :value="item.key"
              :disabled="!contextResourceCount(item.key)"
            >
              <div class="mango-functional-ai-context-option">
                <span>{{ item.title }}</span>
                <small>{{ contextResourceCount(item.key) }} 份资料 / {{ item.description }}</small>
              </div>
            </a-checkbox>
          </a-checkbox-group>
        </div>
      </div>
      <div class="mango-functional-ai-option-row">
        <div class="mango-functional-ai-option-field">
          <span>AI角色：</span>
          <a-select
            v-model="apiPlanForm.ai_role"
            :options="aiRoleOptions"
            :field-names="fieldNames"
            placeholder="请选择角色提示词" data-testid="qa-views-functional-test-suite-details-select-请选择角色提示词-2"
          />
        </div>
        <div class="mango-functional-ai-option-field">
          <span>技能：</span>
          <a-select
            v-model="apiPlanForm.skill_id"
            :options="skillOptions"
            :loading="aiOptionLoading"
            :field-names="fieldNames"
            allow-clear
            placeholder="请选择技能" data-testid="qa-views-functional-test-suite-details-select-请选择技能-2"
          />
        </div>
        <div class="mango-functional-ai-option-field">
          <span>MCP：</span>
          <a-select
            v-model="apiPlanForm.mcp_server_ids"
            :options="mcpServerOptions"
            :loading="aiOptionLoading"
            :field-names="fieldNames"
            placeholder="请选择 MCP 服务"
            multiple
            allow-clear data-testid="qa-views-functional-test-suite-details-select-请选择-mcp-服务"
          />
        </div>
      </div>
      <a-form layout="vertical" class="mango-functional-ai-form">
        <a-form-item label="追问/补充要求">
          <a-textarea v-model="apiPlanForm.user_instruction" placeholder="补充本次 API 自动化生成要求" :auto-size="{ minRows: 2, maxRows: 4 }" data-testid="qa-views-functional-test-suite-details-textarea-补充本次-api-自动化生成要求" />
        </a-form-item>
      </a-form>
    </div>
  </a-modal>

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

  <BaseSidePanel
    class="mango-functional-conversation-panel"
    :visible="contextHistoryVisible"
    :title="conversationDetailTitle"
    @update:visible="(val) => { contextHistoryVisible = val }"
    @cancel="contextHistoryVisible = false"
  >
    <mango-panel-spin class="mango-functional-conversation-spin" :loading="false">
      <div ref="conversationDetailRef" class="mango-functional-conversation-detail">
        <a-empty v-if="!activeConversationThreadMessages.length" description="暂无对话记录" />
        <div v-else-if="conversationDetailType === 'case'" class="mango-functional-case-chat-thread">
          <div
            v-for="message in caseConversationThreadMessages"
            :key="message.key"
            :class="['mango-functional-chat-row', `mango-functional-chat-row-${message.role}`]"
          >
            <div class="mango-functional-chat-avatar">
              <span v-if="message.role === 'user'">用户</span>
              <icon-robot v-else class="mango-functional-chat-avatar-icon" />
            </div>
            <div
              :class="['mango-functional-chat-bubble', { 'mango-functional-chat-bubble-final': message.finalOnly, 'mango-functional-chat-bubble-clickable': message.role === 'user' }]"
              @click="message.role === 'user' && openUserMessageDetail(message)"
            >
              <div v-if="message.title" class="mango-functional-chat-title">{{ message.title }}</div>
              <div v-if="message.content" class="mango-functional-chat-content">{{ message.content }}</div>
              <div v-if="message.meta" class="mango-functional-chat-meta">{{ message.meta }}</div>
              <div v-if="message.time" class="mango-functional-chat-time">{{ message.time }}</div>
              <div v-if="message.caseInfos?.length" class="mango-functional-case-list">
                <div v-for="(caseInfo, index) in message.caseInfos" :key="`${message.key}-case-${index}`" class="mango-functional-case-item">
                  <div class="mango-functional-case-item-title">{{ caseInfoHeader(caseInfo, index) }}</div>
                  <div v-if="caseInfo.precondition" class="mango-functional-chat-collection-text">前置条件：{{ caseInfo.precondition }}</div>
                  <div v-if="caseInfo.test_point" class="mango-functional-chat-collection-text">测试场景：{{ caseInfo.test_point }}</div>
                  <div v-if="caseInfo.test_data" class="mango-functional-chat-collection-text">测试数据：{{ caseInfo.test_data }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="mango-functional-api-chat-thread">
          <div
            v-for="message in apiConversationThreadMessages"
            :key="message.key"
            :class="['mango-functional-chat-row', `mango-functional-chat-row-${message.role}`]"
          >
            <div class="mango-functional-chat-avatar">
              <span v-if="message.role === 'user'">用户</span>
              <icon-robot v-else class="mango-functional-chat-avatar-icon" />
            </div>
            <div
              :class="['mango-functional-chat-bubble', { 'mango-functional-chat-bubble-final': message.finalOnly, 'mango-functional-chat-bubble-clickable': message.role === 'user' }]"
              @click="message.role === 'user' && openUserMessageDetail(message)"
            >
              <div v-if="message.title" class="mango-functional-chat-title">{{ message.title }}</div>
              <div v-if="message.content" class="mango-functional-chat-content">{{ message.content }}</div>
              <div v-if="message.time" class="mango-functional-chat-time">{{ message.time }}</div>
              <a-collapse
                v-if="message.detailItems?.length"
                class="mango-functional-chat-inline-collapse"
                :bordered="false"
              >
                <a-collapse-item key="detail">
                  <template #header>
                    <span class="mango-functional-chat-inline-collapse-title">生成配置</span>
                  </template>
                  <div class="mango-functional-chat-detail-list">
                    <div v-for="detail in message.detailItems" :key="detail.label" class="mango-functional-chat-detail-item">
                      <span>{{ detail.label }}</span>
                      <strong>{{ detail.value }}</strong>
                    </div>
                  </div>
                </a-collapse-item>
              </a-collapse>
            </div>
          </div>
        </div>
        <a-collapse
          v-if="conversationRunEvidenceTaskId"
          class="mango-functional-run-evidence"
          :bordered="false"
        >
          <a-collapse-item key="evidence" header="运行证据">
            <mango-panel-spin :loading="conversationRunEvidenceLoading">
              <div class="mango-functional-run-evidence-summary">
                <span>Harness：{{ conversationRunEvidence.task?.agent_key || '-' }} V{{ conversationRunEvidence.task?.agent_version || '-' }}</span>
                <span>阶段：{{ conversationRunEvidence.steps?.length || 0 }}</span>
                <span>产物：{{ conversationRunEvidence.artifacts?.length || 0 }}</span>
                <span>评估：{{ conversationRunEvidence.evaluations?.length || 0 }}</span>
              </div>
              <div v-if="conversationRunEvidence.evaluations?.length" class="mango-functional-run-evaluation-list">
                <div v-for="item in conversationRunEvidence.evaluations" :key="item.id" class="mango-functional-run-evaluation-item">
                  <a-tag size="small" :color="item.passed ? 'green' : 'red'">{{ item.passed ? '通过' : '未通过' }}</a-tag>
                  <strong>{{ item.evaluator_key }}</strong>
                  <span>评分 {{ item.score }}</span>
                  <small v-if="item.findings?.length">{{ evidenceFindingSummary(item.findings) }}</small>
                </div>
              </div>
              <a-empty v-else description="暂无评估记录" />
            </mango-panel-spin>
          </a-collapse-item>
        </a-collapse>
      </div>
    </mango-panel-spin>
  </BaseSidePanel>

  <BaseSidePanel
    :visible="userMessageVisible"
    :title="userMessageTitle"
    :width="720"
    @update:visible="(val) => { userMessageVisible = val }"
    @cancel="userMessageVisible = false"
  >
    <div class="mango-functional-user-audit">
      <div class="mango-functional-user-audit-grid">
        <div v-for="item in userMessageAudit.meta" :key="item.label" class="mango-functional-user-audit-meta">
          <span>{{ item.label }}</span>
          <strong>{{ item.value || '-' }}</strong>
        </div>
      </div>
      <div v-if="userMessageAudit.cases?.length" class="mango-functional-user-audit-section">
        <div class="mango-functional-user-audit-title">发送用例</div>
        <div class="mango-functional-user-audit-case-list">
          <div v-for="(item, index) in userMessageAudit.cases" :key="`${item.case_no || item.id || index}`" class="mango-functional-user-audit-case">
            <div>
              <strong>{{ item.case_no || item.id || index + 1 }}</strong>
              <span>{{ item.title || '-' }}</span>
            </div>
            <small v-if="item.test_point">{{ item.test_point }}</small>
            <a-tag v-if="item.status" :color="auditCaseStatusColor(item.status)" size="small">{{ item.status }}</a-tag>
            <a-tag v-if="item.api_case_id" size="small">API用例 {{ item.api_case_id }}</a-tag>
          </div>
        </div>
      </div>
      <div v-if="userMessageAudit.contextContent" class="mango-functional-user-audit-section">
        <div class="mango-functional-user-audit-title">发送上下文内容</div>
        <div class="mango-functional-user-audit-content">{{ userMessageAudit.contextContent }}</div>
      </div>
    </div>
  </BaseSidePanel>

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
            AI 只能读取平台保存的文本内容。URL 需要后端服务可访问且无需额外登录；内网、鉴权页面、飞书等私有链接需要先解析成文本。文件和图片请确认解析文本可读，无法自动解析时请手工补充。
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
              placeholder="AI会优先读取这里的解析文本。文件、图片或无法访问的URL，请在这里补充AI可读的文本内容。"
            />
          </a-form-item>
        </a-grid-item>
        <a-grid-item>
          <a-form-item label="参与AI">
            <a-switch v-model="resourceForm.enabled" />
          </a-form-item>
        </a-grid-item>
      </a-grid>
    </a-form>
    <template #extra-buttons>
      <a-button v-permission="['functional.suite:create', 'functional.suite:edit']" type="primary" :loading="resourceLoading" @click="saveResource" data-testid="qa-views-functional-test-suite-details-button-保存">保存</a-button>
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
      <a-button v-permission="['functional.suite:create', 'functional.suite:edit']" type="primary" :loading="resourceLoading" @click="saveRawResource" data-testid="qa-views-functional-test-suite-details-button-保存-2">保存</a-button>
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
  import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import { useRoute, useRouter } from 'vue-router'
  import CodeEditor from '@/components/editors/CodeEditor.vue'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import ApiCaseDetails from '@/views/apitest/case/details/index.vue'
  import {
    deleteAiAgentContext,
    getAiAgentContext,
    getAiAgentRunEvents,
    getAiAgentRunEvidence,
    getAiApiAutomationAgentStatus,
    getAiFunctionalCaseAgentStatus,
    getAiMcpServer,
    getAiSkill,
    postAiApiAutomationAgentRetry,
    postAiApiAutomationAgentStart,
    postAiAgentRunConfirm,
    postAiFunctionalCaseAgentRetry,
    postAiFunctionalCaseAgentStart,
  } from '@/api/ai'
  import { usePagination } from '@/hooks/table'
  import { useEnum } from '@/store/modules/get-enum'
  import {
    deleteFunctionalContextResource,
    deleteManualCase,
    getFunctionalContextResource,
    getRelatedFunctionalDefects,
    getRelatedFunctionalPlans,
    getManualCase,
    getManualSuite,
    getManualSuiteContextCandidates,
    postFunctionalContextResource,
    postManualAutomationBind,
    postManualCase,
    putFunctionalContextResource,
    putManualCase,
  } from '@/api/functional-test'
  import { postUserFile } from '@/api/system/file_data'
  import { getUserName } from '@/api/user/user'
  import { formatModulePath, formatProjectProductPath } from '@/utils/business-format'
  import {
    getStatusTagColor,
    MANUAL_TEST_CHANGE_STATUS_COLORS,
    MANUAL_TEST_IMPACT_STATUS_COLORS,
  } from '@/utils/status-color'

  const route = useRoute()
  const router = useRouter()
  const enumStore = useEnum()
  const fieldNames = { value: 'key', label: 'title' }
  const casePagination = usePagination(loadCases, () => caseLoading)
  const MANUAL_TEST_TYPE_MANUAL = 0
  const MANUAL_TEST_TYPE_API = 1
  const AUTOMATION_TYPE_API = 0
  const AUTOMATION_TYPE_UI = 1
  const TASK_TYPE_MANUAL_CASE_SYNC = 1
  const TASK_TYPE_GENERATE_API_CASE = 2
  const TASK_STATUS_FAIL = 0
  const TASK_STATUS_SUCCESS = 1
  const TASK_STATUS_PENDING = 2
  const TASK_STATUS_RUNNING = 3
  const TASK_STATUS_WAITING_CONFIRM = 4
  const TASK_STATUS_PARTIAL_SUCCESS = 5
  const TASK_STATUS_CANCELLED = 6
  const TASK_STATUS_CLAIMED = 7
  const TASK_STATUS_WAITING_MODEL = 8
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
  const DIALOG_PROGRESS_POLL_INTERVAL = 5000
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
  const caseDialogTask = ref<any>(null)
  const apiDialogTask = ref<any>(null)
  const contextHistories = ref<any[]>([])
  const currentCase = ref<any>(null)
  const suiteLoading = ref(false)
  const caseLoading = ref(false)
  const resourceLoading = ref(false)
  const qualityLoading = ref(false)
  const caseTaskLoading = ref(false)
  const apiTaskLoading = ref(false)
  const ambiguityConfirmVisible = ref(false)
  const ambiguityConfirmLoading = ref(false)
  const ambiguityConfirmationAnswer = ref('')
  const contextHistoryLoading = ref(false)
  const caseDialogLoading = ref(false)
  const apiDialogLoading = ref(false)
  const syncLoading = ref(false)
  const syncSubmitting = ref(false)
  const apiPlanSubmitting = ref(false)
  const aiOptionLoading = ref(false)
  const actionLoading = ref('')
  const activePane = ref<number | string>('cases')
  const caseVisible = ref(false)
  const bindVisible = ref(false)
  const resourceVisible = ref(false)
  const rawResourceVisible = ref(false)
  const contextHistoryVisible = ref(false)
  const userMessageVisible = ref(false)
  const conversationDetailRef = ref<HTMLElement>()
  const conversationRunEvidence = ref<any>({ task: {}, steps: [], artifacts: [], evaluations: [] })
  const conversationRunEvidenceLoading = ref(false)
  const apiCaseDetailVisible = ref(false)
  const apiCaseDetailId = ref<number | string>('')
  const apiCaseDetailName = ref('')
  const syncDialogVisible = ref(false)
  const apiPlanDialogVisible = ref(false)
  const apiPlanMode = ref<'single' | 'batch'>('single')
  const latestTaskEvents = reactive<Record<number, any>>({})
  const apiPlanBatchScope = ref('')
  const apiPlanBatchCases = ref<any[]>([])
  const apiPlanFilteredCount = ref(0)
  const userMessageTitle = ref('用户发送内容')
  const userMessageAudit = ref<any>({ meta: [], cases: [], contextContent: '' })
  const syncTask = ref<any>(null)
  const retrySourceTask = ref<any>(null)
  const syncPollTimer = ref<number | null>(null)
  const apiPollTimer = ref<number | null>(null)
  const caseForm = reactive<any>({})
  const userOptions = ref<any[]>([])
  const resourceForm = reactive<any>({})
  const rawResource = ref<any>(null)
  const conversationDetailType = ref<'case' | 'api'>('case')
  const rawResourceEditText = ref('')
  const resourceFile = ref<File | null>(null)
  const resourceFileList = ref<any[]>([])
  const bindForm = reactive<any>({ automation_type: AUTOMATION_TYPE_UI, automation_case_id: null })
  const syncForm = reactive<any>({
    context_keys: [],
    historical_selections: [],
    ai_role: 'business_test_expert',
    skill_id: null,
    deep_check: false,
    user_instruction: '',
  })
  const historicalContextLoading = ref(false)
  const historicalContextSuites = ref<any[]>([])
  const apiPlanForm = reactive<any>({ context_keys: [], ai_role: 'api_automation_expert', skill_id: null, mcp_server_ids: [], user_instruction: '' })
  const apiFollowUpInstruction = ref('')
  const aiSkills = ref<any[]>([])
  const mcpServers = ref<any[]>([])
  const rawCaseContextKey = RESOURCE_KEY_RAW_CASE_DOC
  const aiRoleOptions = [
    { key: 'business_test_expert', title: '业务测试专家' },
    { key: 'api_automation_expert', title: 'API自动化测试专家' },
  ]

  const requirementDocNavItem = {
      key: RESOURCE_KEY_REQUIREMENT_DOC,
      title: '需求文档',
      description: '用于核对测试用例是否有遗漏',
      tip: '需求文档用于和已生成/已导入的功能测试用例做覆盖核对，帮助 AI 判断是否遗漏业务场景、异常场景或验收点。',
  }
  const developmentDesignNavItem = {
      key: RESOURCE_KEY_DEVELOPMENT_DESIGN,
      title: '开发设计',
      description: '用于创建 API 接口、API 用例和数据工厂',
      tip: '开发设计用于理解接口实现方案、模块边界、核心流程和数据处理逻辑，辅助 AI 创建 API 接口、API 用例以及相关数据工厂。',
  }
  const apiDocNavItem = {
      key: RESOURCE_KEY_API_DOC,
      title: '接口文档',
      description: '用于创建 API 接口、API 用例和数据工厂',
      tip: '接口文档用于识别请求方法、路径、参数、响应、鉴权和错误码，辅助 AI 创建 API 接口、API 用例以及接口入参所需的数据工厂。',
  }
  const developmentCodeNavItem = {
      key: RESOURCE_KEY_DEVELOPMENT_CODE,
      title: '开发代码',
      description: '用于识别数据库表关系并创建数据工厂',
      tip: '开发代码用于分析落库逻辑、实体关系、枚举取值、字段默认值和依赖调用，帮助 AI 找到数据库表关系并创建更准确的数据工厂。',
  }
  const sqlQueryNavItem = {
      key: RESOURCE_KEY_SQL_QUERY,
      title: 'SQL语句',
      description: '用于识别数据库表关系并创建数据工厂',
      tip: 'SQL语句用于补充表名、字段、关联条件和数据校验方式，帮助 AI 识别数据库表关系并生成数据工厂准备或校验数据。',
  }
  const rawCaseDocNavItem = {
    key: 'sync',
    title: '原始用例文档',
    description: '用于生成测试平台用例',
    tip: '原始用例文档用于解析并生成测试平台要求的功能测试用例。',
  }
  const rawCaseDocContextItem = {
    ...rawCaseDocNavItem,
    key: RESOURCE_KEY_RAW_CASE_DOC,
  }
  const pageDataContextItem = {
    key: RESOURCE_KEY_PAGE_DATA,
    title: '页面数据',
    description: '用于补充页面实际数据和预期结果',
    tip: '页面数据用于补充页面实际字段、状态、展示数据、用户操作后的页面结果，帮助 AI 补齐测试数据和预期结果。',
  }
  const testUnderstandingContextItem = {
    key: RESOURCE_KEY_TEST_UNDERSTANDING,
    title: '测试理解',
    description: '用于补充测试人员理解和风险点',
    tip: '测试理解用于记录测试人员对需求边界、风险点、异常路径、验收关注点的理解，帮助 AI 做补漏和优先级判断。',
  }
  const platformCaseNavItem = {
    key: 'cases',
    title: '来源用例',
    description: '当前需求版本沉淀到用例库的功能用例',
    tip: '来源用例是当前需求版本沉淀到用例库的可复用资产，可继续维护字段和自动化绑定。',
  }
  const basicInfoNavItem = {
    key: 'basic',
    title: '基本信息',
    description: '需求版本、排期与质量概况',
  }
  const platformCaseContextItem = {
    key: RESOURCE_KEY_PLATFORM_CASE,
    title: '测试平台用例',
    description: '用于在已有平台用例基础上重新编辑',
  }
  const testPlanNavItem = {
    key: 'plans',
    title: '测试计划',
    description: '当前需求版本的单次测试活动',
  }
  const defectNavItem = {
    key: 'defects',
    title: '缺陷',
    description: '当前需求执行中发现的缺陷',
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
  const contextSelectionGroups = [
    { title: '产品角色', items: [requirementDocNavItem] },
    { title: '开发角色', items: [developmentDesignNavItem, apiDocNavItem, developmentCodeNavItem, sqlQueryNavItem] },
    { title: '测试角色', items: [rawCaseDocContextItem, pageDataContextItem, testUnderstandingContextItem] },
    { title: '交付产物', items: [platformCaseContextItem] },
  ]
  const apiContextSelectionGroups = contextSelectionGroups.filter((group) => group.title !== '交付产物')
  const allNavItems = navGroups.flatMap((group) => group.items)
  const contextFieldKeys = new Set(contextNavItems.map((item) => item.key))
  const skillOptions = computed(() =>
    [...aiSkills.value]
      .filter((item) => item.status === 1)
      .filter((item) => item.skill_type === 1)
      .sort((left, right) => Number(!!right.is_builtin) - Number(!!left.is_builtin))
      .map((item) => ({ key: item.id, title: item.is_builtin ? `${item.name}（内置）` : item.name }))
  )
  const functionalCaseSkillOptions = computed(() =>
    [...aiSkills.value]
      .filter((item) => item.status === 1)
      .filter((item) => item.skill_type === 0)
      .sort((left, right) => Number(!!right.is_builtin) - Number(!!left.is_builtin))
      .map((item) => ({ key: item.id, title: item.is_builtin ? `${item.name}（内置）` : item.name }))
  )
  const mcpServerOptions = computed(() =>
    mcpServers.value
      .filter((item) => item.status === 1)
      .map((item) => ({ key: item.id, title: item.is_connected ? item.name : `${item.name}（未连接）` }))
  )
  const caseDialogHistories = computed(() =>
    contextHistories.value.filter((item) => item.context_type === 'manual_case_sync_dialog')
  )
  const apiDialogHistories = computed(() =>
    contextHistories.value.filter((item) => item.context_type === 'api_case_plan')
  )
  const latestCaseTask = computed(() => caseDialogTask.value)
  const waitingConfirmationAmbiguities = computed<any[]>(() =>
    latestCaseTask.value?.output_data?.waiting_confirmation?.ambiguities || []
  )
  const latestApiTask = computed(() => apiDialogTask.value)
  const conversationHistories = computed(() =>
    conversationDetailType.value === 'case' ? caseDialogHistories.value : apiDialogHistories.value
  )
  const conversationDetailTitle = computed(() =>
    conversationDetailType.value === 'case' ? '生成用例对话' : '生成 API 自动化对话'
  )
  const conversationRunEvidenceTaskId = computed(() =>
    conversationDetailType.value === 'case' ? latestCaseTask.value?.id : latestApiTask.value?.id
  )
  const activeConversationThreadMessages = computed(() =>
    conversationDetailType.value === 'case' ? caseConversationThreadMessages.value : apiConversationThreadMessages.value
  )
  const caseConversationThreadMessages = computed(() =>
    [
      ...caseDialogHistories.value
        .slice()
        .reverse()
        .flatMap((item) =>
          conversationMessages(item).map((message) => ({
            ...message,
            key: `${item.id}-${message.key}`,
            time: item.create_time || '',
          }))
        ),
      ...runningTaskConversationMessages(latestCaseTask.value, 'case'),
    ]
  )
  const apiConversationThreadMessages = computed(() =>
    [
      ...apiDialogHistories.value
        .slice()
        .reverse()
        .flatMap((item) =>
          conversationMessages(item).map((message) => ({
            ...message,
            key: `${item.id}-${message.key}`,
            time: item.create_time || '',
          }))
        ),
      ...runningTaskConversationMessages(latestApiTask.value, 'api'),
    ]
  )
  const apiPlanDialogTitle = computed(() =>
    apiPlanMode.value === 'batch' ? '批量生成 API 自动化用例' : '生成 API 自动化用例'
  )
  const apiPlanSummary = computed(() => {
    if (apiPlanMode.value !== 'batch') {
      const record = currentCase.value || {}
      return record.id ? `当前用例：${[record.case_no, record.title].filter(Boolean).join(' / ') || record.id}` : ''
    }
    if (apiPlanBatchScope.value === 'unbound_api_cases') {
      return '将处理当前需求下测试类型包含 API 自动化且未绑定 API 用例的用例。'
    }
    const total = apiPlanBatchCases.value.length
    const bound = apiPlanBatchCases.value.filter((item) => bindingCaseId(item, AUTOMATION_TYPE_API)).length
    const unbound = total - bound
    const filtered = apiPlanFilteredCount.value ? `，已过滤 ${apiPlanFilteredCount.value} 条非 API 自动化用例` : ''
    return `共 ${total} 条，未绑定 ${unbound} 条，已绑定覆盖 ${bound} 条${filtered}`
  })
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
    return `用例生成工作台 / ${id} / ${name}`
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

  function auditCaseStatusColor(value: string) {
    const statusMap: Record<string, number> = {
      pending: TASK_STATUS_PENDING,
      running: TASK_STATUS_RUNNING,
      success: TASK_STATUS_SUCCESS,
      fail: TASK_STATUS_FAIL,
    }
    return statusColor(statusMap[value] ?? TASK_STATUS_PENDING)
  }

  function taskStatusText(status: number) {
    return enumTitle(enumStore.ai_agent_task_status, status)
  }

  function isActiveTaskStatus(status: number) {
    return [
      TASK_STATUS_PENDING,
      TASK_STATUS_CLAIMED,
      TASK_STATUS_RUNNING,
      TASK_STATUS_WAITING_MODEL,
      TASK_STATUS_WAITING_CONFIRM,
    ].includes(status)
  }

  function taskTypeText(type: number) {
    const labels: Record<number, string> = {
      [TASK_TYPE_MANUAL_CASE_SYNC]: '同步功能用例',
      [TASK_TYPE_GENERATE_API_CASE]: '生成 API 用例',
    }
    return labels[type] || enumTitle(enumStore.ai_agent_task_type, type)
  }

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

  function contextHistoryTitle(item: any) {
    const reuse = contextSourceSnapshot(item)?.reuse_context ? '复用上下文' : '新上下文'
    return `${reuse} / ${item.context_type || '-'}`
  }

  function contextHistoryTypeText(type: string) {
    const labels: Record<string, string> = {
      manual_case_sync_dialog: '同步功能用例',
      api_case_plan: '生成 API 用例',
    }
    return labels[type] || type || '-'
  }

  function contextHistoryMeta(item: any) {
    const hash = item.context_hash || contextResultSnapshot(item)?.context_hash || ''
    const shortHash = hash ? ` / ${hash.slice(0, 8)}` : ''
    const reuseId = contextSourceSnapshot(item)?.reuse_context_id
    return `${item.create_time || '-'}${shortHash}${reuseId ? ` / 复用 #${reuseId}` : ''}`
  }

  function contextKeyTitle(key: number | string) {
    const map: Record<number, string> = {
      [RESOURCE_KEY_REQUIREMENT_DOC]: '需求文档',
      [RESOURCE_KEY_DEVELOPMENT_DESIGN]: '开发设计',
      [RESOURCE_KEY_API_DOC]: '接口文档',
      [RESOURCE_KEY_DEVELOPMENT_CODE]: '开发代码',
      [RESOURCE_KEY_SQL_QUERY]: 'SQL语句',
      [RESOURCE_KEY_RAW_CASE_DOC]: '原始用例文档',
      [RESOURCE_KEY_PLATFORM_CASE]: '测试平台用例',
      [RESOURCE_KEY_PAGE_DATA]: '页面数据',
      [RESOURCE_KEY_TEST_UNDERSTANDING]: '测试理解',
    }
    return map[Number(key)] || String(key)
  }

  function contextHistoryContextSummary(item: any) {
    const keys = contextSourceSnapshot(item)?.selected_context_keys || []
    const keyText = keys.length ? keys.map((key: number | string) => contextKeyTitle(key)).join('、') : '未记录上下文范围'
    const reuseText = contextSourceSnapshot(item)?.reuse_context ? ' / 复用已有上下文' : ' / 新上下文'
    return `${keyText}${reuseText}`
  }

  function contextSourceSnapshot(item: any) {
    return item?.source_snapshot || {}
  }

  function contextResultSnapshot(item: any) {
    return item?.result_snapshot || {}
  }

  function safeJsonParse(value: any, fallback: any = null) {
    if (!value) return fallback
    if (typeof value !== 'string') return value
    try {
      return JSON.parse(value)
    } catch {
      return fallback ?? value
    }
  }

  function conversationSkillName(item: any) {
    return item.skill_snapshot?.name || item.skill_snapshot?.title || ''
  }

  function conversationMcpName(item: any) {
    const snapshot = item.mcp_snapshot || contextResultSnapshot(item)
    const names = snapshot?.mcp_server_names
    if (Array.isArray(names) && names.length) return names.join('、')
    const serverIds = snapshot?.mcp_server_ids
    if (Array.isArray(serverIds) && serverIds.length) return serverIds.map((id) => `#${id}`).join('、')
    return snapshot?.mcp_server_id ? `#${snapshot.mcp_server_id}` : ''
  }

  function conversationAiRoleName(item: any) {
    const role = contextResultSnapshot(item)?.ai_role || 'api_automation_expert'
    return aiRoleOptions.find((option) => option.key === role)?.title || role
  }

  function conversationSessionTitle(item: any) {
    if (item.context_type === 'api_case_plan') {
      const caseText = [item.case_no, item.case_title].filter(Boolean).join(' / ')
      return caseText ? `生成 API 自动化：${caseText}` : '生成 API 自动化'
    }
    return '生成测试平台用例'
  }

  function conversationSessionHeader(item: any) {
    const time = item.create_time || '-'
    return `${conversationSessionTitle(item)} / ${time}`
  }

  function shortJson(value: any, maxLength = 360) {
    const text = typeof value === 'string' ? value : JSON.stringify(value || {}, null, 2)
    return text.length > maxLength ? `${text.slice(0, maxLength)}...` : text
  }

  function caseInfoHeader(caseInfo: any, index: number) {
    const idText = caseInfo.case_no || caseInfo.api_case_id || caseInfo.id || index + 1
    const titleText = caseInfo.title || caseInfo.name || '未命名用例'
    return `${idText} / ${titleText}`
  }

  function userInstructionText(item: any) {
    const parsed = safeJsonParse(item.user_instruction, {})
    if (typeof parsed === 'string') return parsed
    if (parsed && typeof parsed === 'object' && 'user_instruction' in parsed) {
      return parsed.user_instruction || ''
    }
    return item.user_instruction || ''
  }

  function apiResultSummary(item: any) {
    const result = contextResultSnapshot(item) || {}
    if (result.mode === 'batch') {
      const total = result.total || result.items?.length || 0
      return `批量生成完成：成功 ${result.success_count || 0}，失败 ${result.fail_count || 0}，共 ${total}`
    }
    const plan = result?.plan || {}
    if (plan.assistant_message) return plan.assistant_message
    return item.summary || 'API 自动化生成已完成'
  }

  function batchResultLines(result: any) {
    const items = result?.items || []
    if (!items.length) return ''
    return items
      .map((item: any, index: number) => {
        const status = item.status === 'success' ? '成功' : item.status === 'fail' ? '失败' : '未完成'
        const apiCaseText = item.api_case_id ? `，API用例 ${item.api_case_id}` : ''
        const reason = item.error_message ? `，原因：${item.error_message}` : ''
        return `${index + 1}. ${item.case_no || item.manual_case_id} / ${item.title || '-'}：${status}${apiCaseText}${reason}`
      })
      .join('\n')
  }

  function apiCaseInfoList(item: any) {
    const plan = contextResultSnapshot(item)?.plan || {}
    const confirmResult = plan.confirm_result || {}
    const generatedCase = confirmResult.api_case || {}
    const apiCase = plan.api_case || {}
    const apiCaseId = confirmResult.api_case_id || plan.api_case_id || plan.mcp_api_case_id || generatedCase.id || apiCase.id
    const caseName = generatedCase.name || apiCase.name || item.case_title || 'API 自动化用例'
    const flow = generatedCase.case_flow || ''
    const assistantMessage = plan.assistant_message || ''
    return [
      { api_case_id: apiCaseId, name: caseName, diff_summary: flow || assistantMessage || item.summary || '' },
    ]
  }

  function mcpCallList(item: any) {
    const plan = contextResultSnapshot(item)?.plan || {}
    const snapshot = contextResultSnapshot(item)
    const candidates = [
      plan.tool_calls,
      plan.confirm_result?.tool_calls,
      plan.output_data?.tool_calls,
      plan.output_data?.confirm_result?.tool_calls,
      snapshot.tool_calls,
      snapshot.confirm_result?.tool_calls,
    ]
    const calls = candidates.find((value) => Array.isArray(value) && value.length)
    return calls || []
  }

  function caseResultSummary(item: any) {
    const stats = manualCaseSyncStats(item)
    if (stats) return manualCaseSyncStatsText(stats)
    const casesCount = parsedManualCaseList(item).length
    if (casesCount) return `已解析生成 ${casesCount} 条测试平台用例`
    return item.summary || '已完成处理'
  }

  function isManualCasePayload(value: any) {
    return value && typeof value === 'object' && ['case_no', 'title', 'precondition', 'test_point', 'test_data'].some((key) => value[key])
  }

  function parsedManualCaseList(item: any) {
    const snapshots = Array.isArray(contextResultSnapshot(item)?.cases) ? contextResultSnapshot(item).cases : []
    return snapshots.filter(isManualCasePayload)
  }

  function manualCaseSyncStats(item: any) {
    const candidates = [contextResultSnapshot(item)?.sync_stats]
    return candidates.find((value) =>
      value && typeof value === 'object' && ['case_count', 'added_count', 'changed_count', 'removed_count', 'unchanged_count'].some((key) => typeof value[key] === 'number')
    )
  }

  function manualCaseSyncStatsText(stats: any) {
    const parts = [
      `共 ${stats.case_count ?? 0} 条`,
      `新增 ${stats.added_count ?? 0}`,
      `变更 ${stats.changed_count ?? 0}`,
      `移除 ${stats.removed_count ?? 0}`,
      `未变 ${stats.unchanged_count ?? 0}`,
    ]
    return `同步完成：${parts.join('，')}`
  }

  function parsedCaseInfoList(item: any) {
    return parsedManualCaseList(item).map((caseInfo: any, index: number) => ({
      id: caseInfo.id || index + 1,
      case_no: caseInfo.case_no,
      title: caseInfo.title,
      precondition: caseInfo.precondition,
      test_point: caseInfo.test_point,
      test_data: caseInfo.test_data,
    }))
  }

  function conversationMessages(item: any) {
    const messages: any[] = []
    const selectedContext = contextHistoryContextSummary(item)
    const instruction = userInstructionText(item)
    if (item.context_type === 'api_case_plan') {
      const result = contextResultSnapshot(item)
      if (result.mode === 'batch') {
        const total = result.total || result.items?.length || 0
        messages.push({
          key: `${item.id}-user-batch`,
          role: 'user',
          title: '批量生成 API 自动化',
          content: [`范围：共 ${total} 条用例`, instruction ? `补充要求：${instruction}` : '请根据功能用例批量生成 API 自动化。'].join('\n'),
          meta: selectedContext,
          sourceRecord: item,
        })
        messages.push({
          key: `${item.id}-ai-batch-result`,
          role: 'ai',
          title: '',
          content: [apiResultSummary(item), batchResultLines(result)].filter(Boolean).join('\n\n'),
          meta: '',
          finalOnly: true,
        })
        return messages
      }
      const caseText = [result.case_no, result.case_title].filter(Boolean).join(' / ') || `用例 #${item.manual_case_id || '-'}`
      messages.push({
        key: `${item.id}-user-case`,
        role: 'user',
        title: '发送功能用例',
        content: `${caseText}${instruction ? `\n补充要求：${instruction}` : ''}`,
        meta: selectedContext,
        sourceRecord: item,
      })
      messages.push({
        key: `${item.id}-ai-result`,
        role: 'ai',
        title: '',
        content: apiResultSummary(item),
        meta: '',
        finalOnly: true,
      })
      return messages
    }
    messages.push({
      key: `${item.id}-user-sync`,
      role: 'user',
      title: '发送生成上下文',
      content: instruction || '请根据需求文档、测试描述和已选择的上下文资料生成测试平台用例。',
      meta: selectedContext,
      sourceRecord: item,
    })
    messages.push({
      key: `${item.id}-ai-sync-result`,
      role: 'ai',
      title: '解析结果',
      content: caseResultSummary(item),
      meta: item.summary || '',
      caseInfos: parsedCaseInfoList(item),
    })
    return messages
  }

  function runningTaskConversationMessages(task: any, type: 'case' | 'api') {
    if (!task || ![
      TASK_STATUS_PENDING,
      TASK_STATUS_CLAIMED,
      TASK_STATUS_RUNNING,
      TASK_STATUS_WAITING_MODEL,
      TASK_STATUS_WAITING_CONFIRM,
    ].includes(task.status)) {
      return []
    }
    const input = task.input_data || {}
    const selectedKeys = input.selected_context_keys || input.context_keys || []
    const contextText = selectedKeys.length
      ? selectedKeys.map((key: number | string) => contextKeyTitle(key)).join('、')
      : '未记录上下文范围'
    const instruction = input.user_instruction || ''
    const progress = taskProgress(task)
    const progressText = dialogProgressText(task, type === 'case' ? caseDialogHistories.value : apiDialogHistories.value)
    const userTitle = type === 'case' ? '发起生成测试平台用例' : '发起生成 API 自动化'
    const aiTitle = type === 'case' ? '正在生成测试平台用例' : '正在生成 API 自动化'
    const manualCase = input.manual_case_snapshot || cases.value.find((item) => item.id === input.manual_case_id) || {}
    const manualCaseText = [manualCase.case_no, manualCase.title].filter(Boolean).join(' / ')
    const isApiBatch = type === 'api' && input.mode === 'batch'
    const batchTotal = input.batch_summary?.total || input.manual_case_snapshots?.length || task.output_data?.total || 0
    const batchCurrent = task.output_data?.current_index || 0
    const batchSuccess = task.output_data?.success_count || 0
    const batchFail = task.output_data?.fail_count || 0
    return [
      {
        key: `running-${type}-${task.id}-user`,
        role: 'user',
        title: userTitle,
        content: isApiBatch
          ? [`范围：共 ${batchTotal} 条用例`, instruction ? `补充要求：${instruction}` : '请根据功能用例批量生成 API 自动化。'].join('\n')
          : type === 'api'
          ? [manualCaseText || (input.manual_case_id ? `用例 #${input.manual_case_id}` : '当前功能用例'), instruction ? `补充要求：${instruction}` : '请根据功能用例生成 API 自动化。'].filter(Boolean).join('\n')
          : instruction || '请根据需求文档、测试描述和已选择的上下文资料生成测试平台用例。',
        meta: `上下文：${contextText}`,
        time: task.create_time || '',
        sourceTask: task,
        sourceType: type,
      },
      {
        key: `running-${type}-${task.id}-ai`,
        role: 'ai',
        title: aiTitle,
        content: isApiBatch
          ? `${task.latest_event?.message || progress?.detail || '批量生成进行中'}\n成功 ${batchSuccess}，失败 ${batchFail}${batchCurrent ? `，当前 ${batchCurrent}/${batchTotal}` : ''}`
          : task.latest_event?.message || progress?.detail || progress?.stage || task.title || '任务已开始，正在等待 AI 返回。',
        meta: progressText,
        time: task.update_time || task.create_time || '',
      },
    ]
  }

  function dialogContextSummary(histories: any[]) {
    if (!histories.length) return '上下文：暂无记录'
    return `上下文：${contextHistoryContextSummary(histories[0])}`
  }

  function dialogStatusText(task: any, histories: any[]) {
    if (task) return taskStatusText(task.status)
    return histories.length ? '已有对话' : '未开始'
  }

  function dialogStatusColor(task: any) {
    return task ? statusColor(task.status) : 'gray'
  }

  function isDialogFailed(task: any) {
    return task?.status === TASK_STATUS_FAIL
  }

  function taskProgress(task: any) {
    return task?.output_data?.progress || null
  }

  function dialogProgress(task: any, histories: any[]) {
    const progress = taskProgress(task)
    if (progress && Number.isFinite(Number(progress.percent))) {
      return Math.max(0, Math.min(100, Number(progress.percent)))
    }
    if (!task) return histories.length ? 100 : 0
    const progressMap: Record<number, number> = {
      [TASK_STATUS_PENDING]: 0,
      [TASK_STATUS_CLAIMED]: 0,
      [TASK_STATUS_RUNNING]: 0,
      [TASK_STATUS_WAITING_MODEL]: 0,
      [TASK_STATUS_WAITING_CONFIRM]: 80,
      [TASK_STATUS_SUCCESS]: 100,
      [TASK_STATUS_PARTIAL_SUCCESS]: 100,
      [TASK_STATUS_FAIL]: 100,
      [TASK_STATUS_CANCELLED]: 100,
    }
    return progressMap[task.status] ?? 0
  }

  function dialogProgressStatus(task: any) {
    if (!task) return 'normal'
    if ([TASK_STATUS_SUCCESS, TASK_STATUS_PARTIAL_SUCCESS].includes(task.status)) return 'success'
    if ([TASK_STATUS_FAIL, TASK_STATUS_CANCELLED].includes(task.status)) return 'danger'
    return 'normal'
  }

  function dialogProgressText(task: any, histories: any[]) {
    if (task) {
      const progress = taskProgress(task)
      const time = progress?.updated_at || task.update_time || task.create_time || '-'
      if (progress?.stage) {
        const detail = progress.detail ? `：${progress.detail}` : ''
        return `${progress.stage}${detail} / ${dialogProgress(task, histories)}% / ${time}`
      }
      return `${task.title || taskTypeText(task.task_type)} / ${taskStatusText(task.status)} / ${time}`
    }
    const latest = histories[0]
    return latest ? `最近对话 / ${latest.create_time || '-'}` : '还没有开始对话'
  }

  function openAmbiguityConfirmation() {
    ambiguityConfirmationAnswer.value = ''
    ambiguityConfirmVisible.value = true
  }

  async function confirmRequirementAmbiguities() {
    const answer = ambiguityConfirmationAnswer.value.trim()
    if (!answer) {
      Message.warning('请填写对关键需求歧义的确认说明')
      return false
    }
    const taskId = latestCaseTask.value?.id
    if (!taskId) {
      Message.error('未找到等待确认的生成任务')
      return false
    }
    ambiguityConfirmLoading.value = true
    try {
      const res = await postAiAgentRunConfirm({
        id: taskId,
        confirmation: { answer },
      })
      caseDialogTask.value = res.data || latestCaseTask.value
      startSyncTaskPolling(taskId)
      Message.success('已提交确认，任务将继续执行')
      return true
    } finally {
      ambiguityConfirmLoading.value = false
    }
  }

  async function openConversationDetail(type: 'case' | 'api') {
    conversationDetailType.value = type
    contextHistoryVisible.value = true
    scrollToConversationLatest()
    await refreshConversationDetail(type)
    await loadConversationRunEvidence()
  }

  async function loadConversationRunEvidence() {
    const taskId = conversationRunEvidenceTaskId.value
    if (!taskId) {
      conversationRunEvidence.value = { task: {}, steps: [], artifacts: [], evaluations: [] }
      return
    }
    conversationRunEvidenceLoading.value = true
    try {
      const res = await getAiAgentRunEvidence({ task_id: taskId })
      conversationRunEvidence.value = res.data || { task: {}, steps: [], artifacts: [], evaluations: [] }
    } finally {
      conversationRunEvidenceLoading.value = false
    }
  }

  function evidenceFindingSummary(findings: any[]) {
    return findings
      .slice(0, 3)
      .map((item) => item?.message || String(item))
      .filter(Boolean)
      .join('；')
  }

  async function refreshConversationDetail(type: 'case' | 'api') {
    try {
      if (type === 'case' && latestCaseTask.value?.id && isActiveTaskStatus(latestCaseTask.value.status)) {
        const res = await getAiFunctionalCaseAgentStatus({ id: latestCaseTask.value.id })
        caseDialogTask.value = await attachLatestTaskEvent(res.data || null)
      } else if (type === 'api' && latestApiTask.value?.id && isActiveTaskStatus(latestApiTask.value.status)) {
        const res = await getAiApiAutomationAgentStatus({ id: latestApiTask.value.id })
        apiDialogTask.value = await attachLatestTaskEvent(res.data || null)
      }
      await loadContextHistory()
      if (contextHistoryVisible.value && conversationDetailType.value === type) {
        scrollToConversationLatest()
      }
    } catch (error) {
      console.log(error)
    }
  }

  async function scrollToConversationLatest() {
    await nextTick()
    const scrollToBottom = () => {
      const target = conversationDetailRef.value
      if (!target) return
      target.scrollTop = target.scrollHeight
    }
    requestAnimationFrame(scrollToBottom)
    window.setTimeout(scrollToBottom, 120)
  }

  function openUserMessageDetail(message: any) {
    userMessageTitle.value = message.title || '用户发送内容'
    userMessageAudit.value = buildUserMessageAudit(message)
    userMessageVisible.value = true
  }

  function buildUserMessageAudit(message: any) {
    if (message.sourceTask) {
      return buildRunningUserMessageAudit(message)
    }
    if (message.sourceRecord) {
      return buildHistoryUserMessageAudit(message)
    }
    return {
      meta: [
        { label: '发送内容', value: message.content || '-' },
        { label: '上下文', value: message.meta || '-' },
      ],
      cases: [],
      contextContent: '',
    }
  }

  function buildHistoryUserMessageAudit(message: any) {
    const record = message.sourceRecord || {}
    const source = contextSourceSnapshot(record)
    const result = contextResultSnapshot(record)
    const taskInput = record.task?.input_data || {}
    const selectedKeys = source.selected_context_keys || taskInput.selected_context_keys || []
    return {
      meta: [
        { label: '发送类型', value: historyUserMessageTypeText(record, result) },
        { label: '发送时间', value: record.create_time || '-' },
        { label: '上下文', value: selectedKeys.length ? selectedKeys.map((key: number | string) => contextKeyTitle(key)).join('、') : '-' },
        { label: '上下文复用', value: source.reuse_context ? `是，复用对话 #${source.reuse_context_id || '-'}` : '否，本次发送完整上下文' },
        { label: '补充要求', value: userInstructionText(record) || '-' },
      ],
      cases: userMessageCaseAuditItems(record, result, taskInput),
      contextContent: source.content || '',
    }
  }

  function buildRunningUserMessageAudit(message: any) {
    const task = message.sourceTask || {}
    const input = task.input_data || {}
    const selectedKeys = input.selected_context_keys || input.context_keys || []
    return {
      meta: [
        { label: '发送类型', value: message.sourceType === 'api' ? (input.mode === 'batch' ? '批量生成 API 自动化' : '生成 API 自动化') : '生成测试平台用例' },
        { label: '发送时间', value: task.create_time || '-' },
        { label: '上下文', value: selectedKeys.length ? selectedKeys.map((key: number | string) => contextKeyTitle(key)).join('、') : '-' },
        { label: '上下文复用', value: input.reuse_context ? `是，复用对话 #${input.reuse_context_id || '-'}` : '否或未记录' },
        { label: '补充要求', value: input.user_instruction || '-' },
      ],
      cases: runningTaskCaseAuditItems(input),
      contextContent: '',
    }
  }

  function historyUserMessageTypeText(record: any, result: any) {
    if (record.context_type === 'api_case_plan') {
      return result.mode === 'batch' ? '批量生成 API 自动化' : '生成 API 自动化'
    }
    return '生成测试平台用例'
  }

  function userMessageCaseAuditItems(record: any, result: any, taskInput: any) {
    if (result.mode === 'batch') {
      const items = result.items || taskInput.manual_case_snapshots || []
      return normalizeUserMessageCaseItems(items)
    }
    const manualCase = taskInput.manual_case_snapshot || {}
    const caseNo = result.case_no || manualCase.case_no
    const title = result.case_title || manualCase.title
    if (caseNo || title) {
      return [{ ...manualCase, case_no: caseNo, title }]
    }
    const casesList = parsedCaseInfoList(record)
    return normalizeUserMessageCaseItems(casesList)
  }

  function runningTaskCaseAuditItems(input: any) {
    if (input.mode === 'batch') {
      return normalizeUserMessageCaseItems(input.manual_case_snapshots || [])
    }
    const manualCase = input.manual_case_snapshot || {}
    if (!Object.keys(manualCase).length) return []
    return [manualCase]
  }

  function normalizeUserMessageCaseItems(items: any[] = []) {
    return items
      .map((item: any, index: number) => ({
        ...item,
        id: item.id || item.manual_case_id || index + 1,
        case_no: item.case_no || item.id || item.manual_case_id || index + 1,
        title: item.title || item.case_title || '-',
      }))
  }

  function continueDialog(type: 'case' | 'api') {
    if (type === 'case') {
      openSyncDialog()
      return
    }
    if (!currentCase.value?.id) {
      Message.error('请先在下方功能用例表格中选择一个用例')
      activePane.value = 'cases'
      return
    }
    openApiPlanDialog(currentCase.value)
  }

  function retryFailedDialog(type: 'case' | 'api') {
    if (type === 'case') {
      if (!latestCaseTask.value?.id) return
      openSyncDialog(latestCaseTask.value)
      return
    }
    if (latestApiTask.value?.input_data?.mode === 'batch') {
      continueBatchApiTask()
      return
    }
    const manualCaseId = latestApiTask.value?.input_data?.manual_case_id || currentCase.value?.id
    const targetCase = cases.value.find((item) => item.id === manualCaseId)
    if (!targetCase) {
      Message.error('未找到需要重新生成的功能用例，请先在下方表格选择用例')
      activePane.value = 'cases'
      return
    }
    openApiPlanDialog(targetCase)
  }

  async function continueBatchApiTask() {
    if (!latestApiTask.value?.id) return
    actionLoading.value = 'batch-api-continue'
    try {
      const res = await postAiApiAutomationAgentRetry({ id: latestApiTask.value.id })
      Message.success('已继续生成未成功的 API 自动化用例')
      apiDialogTask.value = res.data || null
      if (res.data?.id) {
        startApiTaskPolling(res.data.id)
      }
    } finally {
      actionLoading.value = ''
    }
  }

  function clearConversation(type: 'case' | 'api') {
    const histories = type === 'case' ? caseDialogHistories.value : apiDialogHistories.value
    if (!histories.length) {
      Message.info('暂无可清空的对话')
      return
    }
    Modal.confirm({
      title: type === 'case' ? '清空生成用例对话' : '清空生成 API 自动化对话',
      content: '只会清空右侧对话上下文记录，不会删除资料、功能用例或自动化用例。',
      okText: '清空',
      cancelText: '取消',
      onBeforeOk: async () => {
        contextHistoryLoading.value = true
        try {
          await Promise.all(histories.map((item: any) => deleteAiAgentContext(item.id)))
          Message.success('对话已清空')
          await loadContextHistory()
        } finally {
          contextHistoryLoading.value = false
        }
      },
    })
  }

  async function loadAiOptions() {
    aiOptionLoading.value = true
    try {
      const [skillRes, mcpRes] = await Promise.all([
        getAiSkill({ status: 1, page: 1, pageSize: 100 }),
        getAiMcpServer({}),
      ])
      aiSkills.value = skillRes.data || []
      mcpServers.value = mcpRes.data || []
      ensureSyncDialogRoleDefault()
      ensureApiPlanBuiltinSkillDefault()
      if (!apiPlanForm.mcp_server_ids?.length && mcpServerOptions.value.length) {
        const connected = mcpServers.value.find((item) => item.status === 1 && item.is_connected)
        apiPlanForm.mcp_server_ids = [connected?.id || mcpServerOptions.value[0].key]
      }
    } finally {
      aiOptionLoading.value = false
    }
  }

  function ensureSyncDialogRoleDefault() {
    if (!syncForm.ai_role || !aiRoleOptions.some((item) => item.key === syncForm.ai_role)) {
      syncForm.ai_role = 'business_test_expert'
    }
  }

  function ensureApiPlanBuiltinSkillDefault() {
    if (apiPlanForm.skill_id) return
    const builtinSkill = aiSkills.value.find((item) => item.status === 1 && item.skill_type === 1 && item.is_builtin)
    apiPlanForm.skill_id = builtinSkill?.id || null
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

  async function loadCaseDialogTask(params: Record<string, unknown> = {}) {
    caseTaskLoading.value = true
    try {
      const res = await getAiFunctionalCaseAgentStatus({ suite_id: route.query.id, ...params })
      caseDialogTask.value = await attachLatestTaskEvent(res.data || null)
    } finally {
      caseTaskLoading.value = false
    }
  }

  async function loadApiDialogTask(params: Record<string, unknown> = {}) {
    apiTaskLoading.value = true
    try {
      const res = await getAiApiAutomationAgentStatus({ suite_id: route.query.id, ...params })
      apiDialogTask.value = await attachLatestTaskEvent(res.data || null)
    } finally {
      apiTaskLoading.value = false
    }
  }

  async function loadDialogTasks() {
    await Promise.all([loadCaseDialogTask(), loadApiDialogTask()])
  }

  async function attachLatestTaskEvent(task: any) {
    if (!task?.id) return task
    const previous = latestTaskEvents[task.id]
    const res = await getAiAgentRunEvents({ task_id: task.id, after_id: previous?.id || 0 })
    const events = res.data || []
    const latest = events[events.length - 1] || previous || null
    if (latest) latestTaskEvents[task.id] = latest
    return { ...task, latest_event: latest }
  }

  async function loadContextHistory() {
    contextHistoryLoading.value = true
    try {
      const res = await getAiAgentContext({ suite_id: route.query.id, page: 1, pageSize: 50 })
      contextHistories.value = (res.data || []).filter((item: any) =>
        ['manual_case_sync_dialog', 'api_case_plan'].includes(item.context_type)
      )
    } finally {
      contextHistoryLoading.value = false
    }
  }

  async function refreshAll() {
    await Promise.all([loadSuite(), loadCases(), loadContextResources(), loadDialogTasks(), loadContextHistory(), loadQualityRelations()])
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

  async function openSyncDialog(task?: any) {
    await Promise.all([loadSuite(), loadContextResources(), loadHistoricalContextCandidates()])
    retrySourceTask.value = task || null
    syncForm.context_keys = [
      RESOURCE_KEY_REQUIREMENT_DOC,
      RESOURCE_KEY_TEST_UNDERSTANDING,
      RESOURCE_KEY_PAGE_DATA,
      RESOURCE_KEY_RAW_CASE_DOC,
      RESOURCE_KEY_PLATFORM_CASE,
    ].filter((key) => contextResourceCount(key))
    ensureSyncDialogRoleDefault()
    syncForm.skill_id = null
    syncForm.historical_selections = []
    syncForm.deep_check = false
    syncForm.user_instruction = ''
    activePane.value = 'sync'
    syncDialogVisible.value = true
    if (!functionalCaseSkillOptions.value.length) {
      await loadAiOptions()
      ensureSyncDialogRoleDefault()
    }
  }

  async function loadHistoricalContextCandidates() {
    historicalContextLoading.value = true
    try {
      const res = await getManualSuiteContextCandidates(Number(route.query.id))
      historicalContextSuites.value = [
        ...(res.data?.requirement_versions || []),
        ...(res.data?.module_requirements || []),
      ]
    } finally {
      historicalContextLoading.value = false
    }
  }

  function selectedHistoricalContext() {
    const references = new Map<number, { suite_id: number; resource_ids: number[]; include_case_snapshot: boolean }>()
    for (const selection of syncForm.historical_selections || []) {
      const [suiteValue, type, value] = String(selection).split(':')
      const suiteId = Number(suiteValue)
      if (!suiteId) continue
      const reference = references.get(suiteId) || {
        suite_id: suiteId,
        resource_ids: [],
        include_case_snapshot: false,
      }
      if (type === 'resource' && Number(value)) reference.resource_ids.push(Number(value))
      if (type === 'cases') reference.include_case_snapshot = true
      references.set(suiteId, reference)
    }
    return Array.from(references.values())
  }

  const previousRequirementVersion = computed(() =>
    historicalContextSuites.value.find((item) => item.relation === 'requirement_version')
  )

  function selectPreviousRequirementVersion() {
    const item = previousRequirementVersion.value
    if (!item) return
    const selections = (item.resources || [])
      .filter((resource: any) => resource.selectable)
      .map((resource: any) => `${item.suite_id}:resource:${resource.id}`)
    if (item.case_count) selections.push(`${item.suite_id}:cases`)
    syncForm.historical_selections = Array.from(
      new Set([...(syncForm.historical_selections || []), ...selections])
    )
  }

  function selectedCurrentResourceIds() {
    const selectedKeys = new Set((syncForm.context_keys || []).map(Number))
    return contextResources.value
      .filter((item) => item.enabled && selectedKeys.has(Number(item.context_key)))
      .map((item) => Number(item.id))
  }

  async function submitSyncDialog() {
    const hasRawCaseContext = syncForm.context_keys.includes(RESOURCE_KEY_RAW_CASE_DOC)
    const hasPlatformCaseContext = syncForm.context_keys.includes(RESOURCE_KEY_PLATFORM_CASE)
    if (hasRawCaseContext && !rawCaseResources.value.some((item) => item.enabled)) {
      Message.error('请先新增原始用例文档，或取消选择原始用例文档')
      return false
    }
    if (hasPlatformCaseContext && !contextResourceCount(RESOURCE_KEY_PLATFORM_CASE)) {
      Message.error('当前没有测试平台用例，无法选择交付产物')
      return false
    }
    if (!syncForm.ai_role) {
      Message.error('请选择角色提示词')
      return false
    }
    syncSubmitting.value = true
    try {
      const isRetry = !!retrySourceTask.value?.id
      const payload = {
        context_keys: syncForm.context_keys,
        current_resource_ids: selectedCurrentResourceIds(),
        historical_context: selectedHistoricalContext(),
        ai_role: syncForm.ai_role,
        skill_id: syncForm.skill_id || null,
        deep_check: syncForm.deep_check,
        user_instruction: syncForm.user_instruction,
      }
      const res = retrySourceTask.value?.id
        ? await postAiFunctionalCaseAgentRetry({ id: retrySourceTask.value.id, ...payload })
        : await postAiFunctionalCaseAgentStart({
            suite_id: Number(route.query.id),
            ...payload,
          })
      syncTask.value = await attachLatestTaskEvent(res.data)
      syncDialogVisible.value = false
      retrySourceTask.value = null
      Message.success(isRetry ? '已继续生成用例对话' : '已创建生成用例对话，可在右侧查看进度')
      caseDialogTask.value = syncTask.value
      startSyncTaskPolling(syncTask.value.id)
      return true
    } catch {
      return false
    } finally {
      syncSubmitting.value = false
    }
  }

  function stopSyncTaskPolling() {
    if (syncPollTimer.value) {
      window.clearInterval(syncPollTimer.value)
      syncPollTimer.value = null
    }
  }

  function startSyncTaskPolling(taskId: number) {
    stopSyncTaskPolling()
    pollSyncTask(taskId)
    syncPollTimer.value = window.setInterval(() => pollSyncTask(taskId), DIALOG_PROGRESS_POLL_INTERVAL)
  }

  async function pollSyncTask(taskId: number) {
    caseDialogLoading.value = true
    try {
      const res = await getAiFunctionalCaseAgentStatus({ id: taskId })
      syncTask.value = res.data
      caseDialogTask.value = syncTask.value
      const status = syncTask.value?.status
      if ([TASK_STATUS_SUCCESS, TASK_STATUS_PARTIAL_SUCCESS].includes(status)) {
        stopSyncTaskPolling()
        Message.success('用例同步完成')
        await refreshAll()
        activePane.value = 'cases'
      } else if ([TASK_STATUS_FAIL, TASK_STATUS_CANCELLED].includes(status)) {
        stopSyncTaskPolling()
        Message.error(syncTask.value.error_message || '同步任务失败')
        await loadContextHistory()
      }
    } finally {
      caseDialogLoading.value = false
    }
  }

  function stopApiTaskPolling() {
    if (apiPollTimer.value) {
      window.clearInterval(apiPollTimer.value)
      apiPollTimer.value = null
    }
  }

  function startApiTaskPolling(taskId: number) {
    stopApiTaskPolling()
    pollApiTask(taskId)
    apiPollTimer.value = window.setInterval(() => pollApiTask(taskId), DIALOG_PROGRESS_POLL_INTERVAL)
  }

  async function pollApiTask(taskId: number) {
    apiDialogLoading.value = true
    try {
      const res = await getAiApiAutomationAgentStatus({ id: taskId })
      const task = await attachLatestTaskEvent(res.data)
      apiDialogTask.value = task || null
      const status = task?.status
      if ([TASK_STATUS_SUCCESS, TASK_STATUS_PARTIAL_SUCCESS].includes(status)) {
        stopApiTaskPolling()
        Message.success('API 自动化生成完成')
        await refreshAll()
        await loadContextHistory()
        activePane.value = 'cases'
      } else if ([TASK_STATUS_FAIL, TASK_STATUS_CANCELLED].includes(status)) {
        stopApiTaskPolling()
        Message.error(task?.error_message || 'API 自动化生成失败')
        await loadContextHistory()
      }
    } finally {
      apiDialogLoading.value = false
    }
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

  async function openApiPlanDialog(record: any) {
    apiPlanMode.value = 'single'
    apiPlanBatchScope.value = ''
    apiPlanBatchCases.value = []
    apiPlanFilteredCount.value = 0
    await Promise.all([loadSuite(), loadContextResources()])
    currentCase.value = record
    await initApiPlanForm()
    apiPlanDialogVisible.value = true
  }

  async function openSelectedBatchApiPlanDialog() {
    if (!selectedCaseKeys.value.length) {
      Message.warning('请选择要批量生成 API 自动化的用例')
      return
    }
    const selectedCases = cases.value.filter((item) => selectedCaseKeys.value.includes(item.id))
    const apiCases = selectedCases.filter((item) => (item.test_types || []).includes(MANUAL_TEST_TYPE_API))
    const filteredCount = selectedCases.length - apiCases.length
    if (!apiCases.length) {
      Message.warning('已选择用例中没有包含 API 自动化测试类型的用例')
      return
    }
    await Promise.all([loadSuite(), loadContextResources()])
    currentCase.value = null
    apiPlanMode.value = 'batch'
    apiPlanBatchScope.value = ''
    apiPlanBatchCases.value = apiCases
    apiPlanFilteredCount.value = filteredCount
    await initApiPlanForm()
    apiPlanDialogVisible.value = true
  }

  async function initApiPlanForm() {
    apiPlanForm.context_keys = [
      RESOURCE_KEY_REQUIREMENT_DOC,
      RESOURCE_KEY_DEVELOPMENT_DESIGN,
      RESOURCE_KEY_API_DOC,
      RESOURCE_KEY_DEVELOPMENT_CODE,
      RESOURCE_KEY_SQL_QUERY,
    ].filter((key) => contextResourceCount(key))
    apiPlanForm.ai_role = 'api_automation_expert'
    apiPlanForm.skill_id = null
    apiPlanForm.mcp_server_ids = []
    apiPlanForm.user_instruction = apiFollowUpInstruction.value || ''
    if (!aiSkills.value.length || !mcpServers.value.length) {
      await loadAiOptions()
    } else {
      ensureApiPlanBuiltinSkillDefault()
      if (mcpServerOptions.value.length) {
        const connected = mcpServers.value.find((item) => item.status === 1 && item.is_connected)
        apiPlanForm.mcp_server_ids = [connected?.id || mcpServerOptions.value[0].key]
      }
    }
  }

  async function submitApiPlanDialog() {
    const record = currentCase.value
    if (apiPlanMode.value === 'single' && !record?.id) return false
    if (apiPlanMode.value === 'batch' && !apiPlanBatchScope.value && !apiPlanBatchCases.value.length) return false
    if (!apiPlanForm.ai_role) {
      Message.error('请选择角色提示词')
      return false
    }
    if (!apiPlanForm.skill_id) {
      Message.error('请选择技能')
      return false
    }
    if (!apiPlanForm.mcp_server_ids?.length) {
      Message.error('请选择 MCP 服务')
      return false
    }
    apiPlanSubmitting.value = true
    actionLoading.value = apiPlanMode.value === 'single' ? `plan-${record.id}` : 'batch-api'
    try {
      const payload: any = {
        context_keys: apiPlanForm.context_keys,
        ai_role: apiPlanForm.ai_role,
        skill_id: apiPlanForm.skill_id,
        mcp_server_ids: apiPlanForm.mcp_server_ids,
        user_instruction: apiPlanForm.user_instruction,
      }
      if (apiPlanMode.value === 'batch') {
        payload.suite_id = Number(route.query.id)
        if (apiPlanBatchScope.value) {
          payload.scope = apiPlanBatchScope.value
        } else {
          payload.manual_case_ids = apiPlanBatchCases.value.map((item) => item.id)
        }
      } else {
        payload.manual_case_id = record.id
      }
      const res = await postAiApiAutomationAgentStart(payload)
      apiPlanDialogVisible.value = false
      Message.success(apiPlanMode.value === 'batch' ? '已创建批量 API 自动化生成任务，可在右侧查看进度' : '已创建 API 自动化生成任务，可在右侧查看进度')
      apiDialogTask.value = res.data || null
      if (res.data?.id) {
        startApiTaskPolling(res.data.id)
      }
      return true
    } catch {
      return false
    } finally {
      apiPlanSubmitting.value = false
      actionLoading.value = ''
    }
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
    loadAiOptions()
    await refreshAll()
    selectBestInitialPane(true)
  })

  onBeforeUnmount(() => {
    stopSyncTaskPolling()
    stopApiTaskPolling()
  })
</script>

<style scoped>
  .mango-functional-workbench {
    display: grid;
    grid-template-columns: 220px minmax(0, 1fr) 330px;
    gap: var(--m-page-gap);
    height: calc(100% - var(--m-page-gap));
    margin-top: var(--m-page-gap);
    min-height: 0;
  }

  .mango-functional-workbench-scroll {
    --mango-workbench-min-width: 1040px;
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
  .mango-functional-main-panel,
  .mango-functional-side-panel {
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

  .mango-functional-workbench-case .mango-functional-nav,
  .mango-functional-workbench-case .mango-functional-side-panel {
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
  .mango-functional-panel-title,
  .mango-functional-side-title {
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

  .mango-functional-panel-subtitle,
  .mango-functional-side-subtitle {
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

  .mango-functional-main-panel,
  .mango-functional-side-panel {
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

  .mango-functional-panel-head,
  .mango-functional-side-head {
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

  .mango-functional-panel-body > :deep(.arco-spin),
  .mango-functional-panel-body > :deep(.arco-spin > .mango-panel-spin__content) {
    height: 100%;
  }

  .mango-functional-context-editor-shell {
    flex: 1;
    width: 100%;
    height: 100%;
    min-height: 520px;
    min-width: 0;
  }

  .mango-functional-context-editor-shell :deep(.code-editor),
  .mango-functional-context-editor-shell :deep(.cm-editor) {
    display: block;
    width: 100%;
    height: 100%;
  }

  .mango-functional-context-editor-shell :deep(.cm-scroller) {
    width: 100%;
    overflow: auto;
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
  .mango-functional-case-table :deep(> .mango-panel-spin__content),
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

  .mango-functional-case-footer :deep(.mango-table-mango-footer-container) {
    border-top: 1px solid var(--m-border);
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

  .mango-functional-resource-item > :deep(.mango-table-actions) {
    justify-content: flex-end;
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

  .mango-functional-raw-viewer :deep(.code-editor),
  .mango-functional-raw-viewer :deep(.cm-editor) {
    width: 100%;
    height: 100%;
  }

  .mango-functional-raw-viewer :deep(.cm-scroller) {
    overflow: auto;
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

  .mango-functional-ai-dialog {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .mango-functional-ai-summary {
    margin-bottom: 0;
  }

  .mango-functional-ai-form {
    padding: 12px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    background: var(--m-surface-soft);
  }

  .mango-functional-ai-option-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1.3fr);
    gap: 14px;
    padding: 12px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    background: var(--m-surface-soft);
  }

  .mango-functional-ai-option-field {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    align-items: center;
    gap: 8px;
    min-width: 0;
  }

  .mango-functional-ai-option-field > span {
    color: var(--m-text);
    font-size: 13px;
    font-weight: 600;
    line-height: 32px;
    white-space: nowrap;
  }

  .mango-functional-ai-extra-options {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 2px 0;
    color: var(--m-text-secondary);
    font-size: 12px;
    line-height: 20px;
  }

  .mango-functional-ai-context-panel {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 12px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    background: var(--m-surface);
  }

  .mango-functional-ai-panel-title {
    color: var(--m-text);
    font-size: 14px;
    font-weight: 600;
    line-height: 22px;
  }

  .mango-functional-ai-panel-title--actions {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  .mango-functional-ai-context-section {
    display: flex;
    flex-direction: column;
    gap: 8px;
    min-width: 0;
    padding-top: 10px;
    border-top: 1px solid var(--m-border);
  }

  .mango-functional-ai-context-section:first-of-type {
    padding-top: 0;
    border-top: 0;
  }

  .mango-functional-ai-context-options {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px 12px;
  }

  .mango-functional-ai-context-options :deep(.arco-checkbox) {
    min-width: 0;
    width: 100%;
    margin-right: 0;
  }

  .mango-functional-ai-context-options :deep(.arco-checkbox-label) {
    min-width: 0;
    flex: 1;
  }

  .mango-functional-ai-context-group {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 12px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
  }

  .mango-functional-ai-context-title {
    color: var(--m-text);
    font-size: 13px;
    font-weight: 600;
    line-height: 20px;
  }

  .mango-functional-ai-context-option {
    display: flex;
    flex-direction: column;
    min-width: 0;
    width: 100%;
    padding: 8px 10px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    background: var(--m-surface-soft);
  }

  .mango-functional-ai-context-option span {
    color: var(--m-text);
    font-size: 13px;
    line-height: 20px;
  }

  .mango-functional-ai-context-option small {
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .mango-functional-history-context-list {
    display: flex;
    max-height: 260px;
    flex-direction: column;
    gap: 8px;
    overflow-y: auto;
  }

  .mango-functional-history-context-item {
    padding: 10px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    background: var(--m-surface-soft);
  }

  .mango-functional-history-context-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  .mango-functional-history-context-head strong {
    min-width: 0;
    overflow: hidden;
    color: var(--m-text);
    font-size: 13px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-functional-history-context-head span,
  .mango-functional-history-context-item > small {
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .mango-functional-history-context-head span {
    flex: none;
  }

  .mango-functional-history-context-options {
    display: flex;
    margin-top: 8px;
    flex-wrap: wrap;
    gap: 6px 14px;
  }

  .mango-functional-side-panel {
    overflow: auto;
  }

  .mango-functional-metrics {
    display: grid;
    flex-shrink: 0;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;
    padding: 12px;
    border-bottom: 1px solid var(--m-border);
  }

  .mango-functional-metrics > div {
    min-width: 0;
    padding: 9px 10px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    background: var(--m-surface-soft);
  }

  .mango-functional-metrics span {
    display: block;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .mango-functional-metrics strong {
    display: block;
    overflow: hidden;
    margin-top: 3px;
    color: var(--m-text);
    font-size: 14px;
    font-weight: 600;
    line-height: 20px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-functional-summary {
    margin: 12px;
  }

  .mango-functional-task-card {
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin: 12px;
    padding: 12px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    background: var(--m-surface);
  }

  .mango-functional-task-card :deep(> .arco-spin),
  .mango-functional-task-card :deep(> .arco-spin > .mango-panel-spin__content) {
    width: 100%;
  }

  .mango-functional-task-card :deep(> .arco-spin > .mango-panel-spin__content) {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .mango-functional-task-card-head,
  .mango-functional-task-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    min-width: 0;
  }

  .mango-functional-task-card-title {
    color: var(--m-text);
    font-size: 15px;
    font-weight: 600;
    line-height: 22px;
  }

  .mango-functional-dialog-status {
    display: inline-flex;
    flex-shrink: 0;
    align-items: center;
    gap: 4px;
  }

  .mango-functional-dialog-meta {
    display: flex;
    flex-direction: column;
    gap: 6px;
    min-width: 0;
    padding: 10px 12px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    background: var(--m-surface-soft);
  }

  .mango-functional-dialog-meta span,
  .mango-functional-dialog-meta small,
  .mango-functional-dialog-line span,
  .mango-functional-dialog-line small {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-functional-dialog-meta span {
    color: var(--m-text);
    font-size: 13px;
    font-weight: 600;
    line-height: 20px;
  }

  .mango-functional-dialog-meta small,
  .mango-functional-dialog-line small {
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .mango-functional-dialog-history,
  .mango-functional-conversation-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-top: 4px;
  }

  .mango-functional-dialog-actions {
    flex-wrap: nowrap;
    margin-top: 6px;
    padding-top: 10px;
    border-top: 1px solid var(--m-border);
  }

  .mango-functional-dialog-actions :deep(.arco-space-item) {
    flex-shrink: 0;
  }

  .mango-functional-dialog-line {
    min-width: 0;
    padding: 8px 10px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    background: var(--m-surface);
  }

  .mango-functional-dialog-line span {
    color: var(--m-text);
    font-size: 13px;
    line-height: 20px;
  }

  .mango-functional-conversation-detail {
    display: flex;
    box-sizing: border-box;
    flex-direction: column;
    gap: 10px;
    width: 100%;
    min-height: 0;
    height: 100%;
    padding: 12px;
    overflow: auto;
    border: none;
    border-radius: 0;
    background: transparent;
  }

  .mango-functional-conversation-spin {
    display: block;
    width: 100%;
  }

  .mango-functional-conversation-spin :deep(> .mango-panel-spin__content) {
    width: 100%;
  }

  .mango-functional-conversation-item {
    padding: 4px 2px 2px;
    background: transparent;
  }

  .mango-functional-session-collapse {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .mango-functional-session-collapse :deep(.mango-functional-session-item) {
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    background: var(--m-surface);
    overflow: hidden;
  }

  .mango-functional-session-collapse :deep(.mango-functional-session-item > .arco-collapse-item-header) {
    min-width: 0;
    padding: 0 0 0 28px;
    color: var(--m-text);
  }

  .mango-functional-session-collapse :deep(.mango-functional-session-item > .arco-collapse-item-header .arco-collapse-item-header-title) {
    min-width: 0;
    width: 100%;
    margin-left: 0;
  }

  .mango-functional-session-collapse :deep(.mango-functional-session-item > .arco-collapse-item-header .arco-collapse-item-icon) {
    left: 10px;
  }

  .mango-functional-session-header {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: center;
    gap: 12px;
    min-width: 0;
    width: 100%;
    padding: 10px 12px;
  }

  .mango-functional-session-header-title {
    overflow: hidden;
    color: var(--m-text);
    font-size: 14px;
    font-weight: 600;
    line-height: 22px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-functional-session-header-meta {
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
    white-space: nowrap;
  }

  .mango-functional-session-collapse :deep(.mango-functional-session-item > .arco-collapse-item-content > .arco-collapse-item-content-box) {
    padding: 0 12px 12px;
    border-top: 1px solid var(--m-border);
    background: var(--m-surface-soft);
  }

  .mango-functional-conversation-item-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    min-width: 0;
    margin-bottom: 10px;
  }

  .mango-functional-conversation-item-head span {
    color: var(--m-text);
    font-size: 14px;
    font-weight: 600;
    line-height: 22px;
  }

  .mango-functional-conversation-item-head small {
    overflow: hidden;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-functional-conversation-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    padding: 10px 0 12px;
  }

  .mango-functional-chat-thread {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .mango-functional-case-chat-thread {
    display: flex;
    flex-direction: column;
    gap: 18px;
    width: 100%;
    min-height: 0;
    padding: 4px 2px 12px;
  }

  .mango-functional-api-chat-thread {
    display: flex;
    flex-direction: column;
    gap: 18px;
    width: 100%;
    min-height: 0;
    padding: 4px 2px 12px;
  }

  .mango-functional-chat-row {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    min-width: 0;
    width: 100%;
  }

  .mango-functional-chat-row-user {
    flex-direction: row-reverse;
    justify-content: flex-start;
    margin-left: auto;
    padding-left: 72px;
  }

  .mango-functional-chat-row-ai {
    padding-right: 72px;
  }

  .mango-functional-chat-avatar {
    display: inline-flex;
    flex-shrink: 0;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border: 1px solid var(--m-border);
    border-radius: 50%;
    background: var(--m-surface);
    color: var(--m-muted);
    font-size: 12px;
    line-height: 30px;
    text-align: center;
  }

  .mango-functional-chat-avatar-icon {
    color: var(--m-primary);
    font-size: 18px;
  }

  .mango-functional-chat-bubble {
    max-width: 100%;
    min-width: 0;
    padding: 12px 14px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
    box-shadow: var(--m-shadow-xs);
  }

  .mango-functional-chat-row-user .mango-functional-chat-bubble {
    max-width: 100%;
    border-color: var(--m-border);
    background: var(--m-surface);
  }

  .mango-functional-chat-row-ai .mango-functional-chat-avatar {
    background: var(--m-surface);
    color: var(--m-text);
    font-weight: 600;
  }

  .mango-functional-chat-row-user .mango-functional-chat-avatar {
    background: var(--m-surface);
    color: var(--m-muted);
  }

  .mango-functional-chat-bubble-final {
    max-width: 100%;
    padding: 12px 14px;
  }

  .mango-functional-chat-bubble-final .mango-functional-chat-content {
    margin-top: 0;
    color: var(--m-text);
    line-height: 22px;
  }

  .mango-functional-chat-bubble-clickable {
    cursor: pointer;
  }

  .mango-functional-chat-title {
    color: var(--m-text);
    font-size: 13px;
    font-weight: 600;
    line-height: 20px;
  }

  .mango-functional-chat-content {
    margin-top: 4px;
    color: var(--m-text-2);
    font-size: 13px;
    line-height: 20px;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .mango-functional-chat-meta {
    margin-top: 6px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .mango-functional-chat-time {
    margin-top: 6px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
    text-align: right;
  }

  .mango-functional-chat-row-ai .mango-functional-chat-time {
    text-align: left;
  }

  .mango-functional-chat-inline-collapse {
    margin-top: 8px;
    border-top: 1px solid var(--m-border);
  }

  .mango-functional-chat-inline-collapse :deep(.arco-collapse-item-header) {
    padding: 7px 0 7px 24px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .mango-functional-chat-inline-collapse :deep(.arco-collapse-item-icon) {
    left: 2px;
  }

  .mango-functional-chat-inline-collapse :deep(.arco-collapse-item-header-title) {
    min-width: 0;
  }

  .mango-functional-chat-inline-collapse :deep(.arco-collapse-item-content-box) {
    padding: 0 0 2px;
  }

  .mango-functional-chat-inline-collapse-title {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-functional-chat-detail-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .mango-functional-chat-detail-item {
    display: grid;
    grid-template-columns: 64px minmax(0, 1fr);
    gap: 8px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .mango-functional-chat-detail-item strong {
    overflow: hidden;
    color: var(--m-text-2);
    font-weight: 400;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-functional-chat-collapse {
    margin-top: 10px;
    border-top: 1px solid var(--m-border);
  }

  .mango-functional-chat-collapse :deep(.arco-collapse-item-header) {
    padding: 8px 0 8px 26px;
    color: var(--m-text);
    font-size: 13px;
    font-weight: 600;
  }

  .mango-functional-chat-collapse :deep(.arco-collapse-item-header .arco-collapse-item-icon) {
    left: 4px;
  }

  .mango-functional-chat-collapse :deep(.arco-collapse-item-header-title) {
    min-width: 0;
  }

  .mango-functional-mcp-collapse-title {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-functional-chat-collapse :deep(.arco-collapse-item-content-box) {
    padding: 0 0 4px;
  }

  .mango-functional-chat-collection {
    display: flex;
    flex-direction: column;
    gap: 8px;
    max-height: 420px;
    overflow: auto;
  }

  .mango-functional-chat-collection-item {
    min-width: 0;
    padding: 8px 10px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    background: var(--m-surface);
  }

  .mango-functional-case-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-top: 10px;
    padding-top: 10px;
    border-top: 1px solid var(--m-border);
  }

  .mango-functional-case-list-title {
    color: var(--m-text);
    font-size: 13px;
    font-weight: 600;
    line-height: 20px;
  }

  .mango-functional-case-item {
    min-width: 0;
    padding: 8px 10px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    background: var(--m-surface);
  }

  .mango-functional-case-item-title {
    overflow: hidden;
    color: var(--m-text);
    font-size: 13px;
    font-weight: 600;
    line-height: 20px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-functional-chat-collection-title {
    overflow: hidden;
    color: var(--m-text);
    font-size: 13px;
    font-weight: 600;
    line-height: 20px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-functional-chat-collection-text {
    margin-top: 4px;
    color: var(--m-text-2);
    font-size: 12px;
    line-height: 18px;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .mango-functional-conversation-section {
    display: grid;
    grid-template-columns: 72px minmax(0, 1fr);
    gap: 8px;
    margin-top: 8px;
    color: var(--m-text-2);
    font-size: 13px;
    line-height: 20px;
  }

  .mango-functional-conversation-section strong {
    color: var(--m-text);
    font-weight: 600;
  }

  .mango-functional-user-audit {
    display: flex;
    flex-direction: column;
    gap: 14px;
  }

  .mango-functional-user-audit-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
  }

  .mango-functional-user-audit-meta {
    min-width: 0;
    padding: 10px 12px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    background: var(--m-surface-soft);
  }

  .mango-functional-user-audit-meta span,
  .mango-functional-user-audit-case small {
    display: block;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .mango-functional-user-audit-meta strong {
    display: block;
    margin-top: 4px;
    color: var(--m-text);
    font-size: 13px;
    line-height: 20px;
    word-break: break-word;
  }

  .mango-functional-user-audit-section {
    min-width: 0;
  }

  .mango-functional-user-audit-title {
    margin-bottom: 8px;
    color: var(--m-text);
    font-size: 14px;
    font-weight: 600;
    line-height: 22px;
  }

  .mango-functional-user-audit-case-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .mango-functional-user-audit-case {
    min-width: 0;
    padding: 10px 12px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    background: var(--m-surface);
  }

  .mango-functional-user-audit-case > div {
    display: flex;
    gap: 8px;
    align-items: center;
    min-width: 0;
  }

  .mango-functional-user-audit-case strong {
    flex: none;
    color: var(--m-text);
    font-size: 13px;
  }

  .mango-functional-user-audit-case span {
    min-width: 0;
    overflow: hidden;
    color: var(--m-text);
    font-size: 13px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-functional-user-audit-case small {
    margin-top: 4px;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .mango-functional-user-audit-content {
    max-height: 360px;
    padding: 12px;
    overflow: auto;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    background: var(--m-surface-soft);
    color: var(--m-text-2);
    font-size: 13px;
    line-height: 21px;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .mango-functional-ambiguity-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
    max-height: 180px;
    margin: 12px 0;
    overflow: auto;
    color: var(--m-text-2);
    font-size: 13px;
    line-height: 20px;
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

  .mango-functional-json {
    margin-top: 12px;
  }

  .mango-functional-task-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .mango-functional-task-item {
    padding: 9px 10px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    background: var(--m-surface-soft);
  }

  .mango-functional-task-item-main {
    min-width: 0;
  }

  .mango-functional-task-item-main span,
  .mango-functional-task-item-main small {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-functional-task-item-main span {
    color: var(--m-text);
    font-size: 13px;
    font-weight: 600;
    line-height: 20px;
  }

  .mango-functional-task-item-main small {
    margin-top: 2px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .mango-functional-task-item-main .mango-functional-task-error {
    color: var(--m-danger);
  }

  .mango-functional-run-evidence {
    margin-top: 16px;
    background: var(--m-surface);
  }

  .mango-functional-run-evidence-summary {
    display: flex;
    flex-wrap: wrap;
    gap: 8px 16px;
    color: var(--m-text-2);
    font-size: 12px;
    line-height: 20px;
  }

  .mango-functional-run-evaluation-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-top: 12px;
  }

  .mango-functional-run-evaluation-item {
    display: grid;
    grid-template-columns: auto minmax(120px, 1fr) auto;
    gap: 8px;
    align-items: center;
    padding: 8px 10px;
    background: var(--m-surface-soft);
    border-radius: var(--m-radius-sm);
    color: var(--m-text-2);
    font-size: 12px;
  }

  .mango-functional-run-evaluation-item small {
    grid-column: 2 / -1;
    color: var(--m-danger);
    line-height: 18px;
    word-break: break-word;
  }
</style>
