<template>
  <TableBody class="mango-detail-workbench-page mango-functional-workbench-page">
    <template #header>
      <div class="mango-detail-toolbar">
        <div class="mango-detail-heading">
          <div class="mango-detail-title">{{ workbenchTitle }}</div>
        </div>
        <a-space class="mango-detail-actions" wrap>
          <a-button
            class="mango-back-button"
            size="small"
            @click="router.back()"
            data-testid="qa-views-functional-test-suite-details-button-返回"
            >返回</a-button
          >
        </a-space>
      </div>
    </template>

    <template #default>
      <div class="mango-workbench-scroll-x mango-functional-workbench-scroll">
        <div
          :class="[
            'mango-functional-workbench',
            { 'mango-functional-workbench-case': activePane === 'cases' },
          ]"
        >
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
                  :class="[
                    'mango-functional-nav-item',
                    { 'mango-functional-nav-item-active': activePane === item.key },
                  ]"
                  type="button"
                  @click="choosePane(item.key)"
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
                <div class="mango-functional-panel-subtitle">{{
                  currentNavItem.tip || currentNavItem.description
                }}</div>
              </div>
              <a-space v-if="hasActiveContextField">
                <a-button
                  size="small"
                  :loading="resourceLoading"
                  @click="loadContextResources"
                  data-testid="qa-views-functional-test-suite-details-button-刷新"
                  >刷新</a-button
                >
                <a-button
                  size="small"
                  type="primary"
                  @click="openResource()"
                  data-testid="qa-views-functional-test-suite-details-button-新增资料"
                  >新增资料</a-button
                >
              </a-space>
              <a-space v-else-if="activePane === 'cases'">
                <a-button
                  size="small"
                  status="danger"
                  :loading="caseDeleting"
                  :disabled="caseWriteBusy"
                  @click="batchDeleteCases"
                  data-testid="qa-views-functional-test-suite-details-button-批量删除"
                >
                  批量删除
                </a-button>

                <a-button
                  size="small"
                  type="primary"
                  @click="openCase()"
                  data-testid="qa-views-functional-test-suite-details-button-手动新增"
                  >手动新增</a-button
                >
              </a-space>
              <a-space v-else-if="activePane === 'sync'">
                <a-button
                  size="small"
                  :loading="resourceLoading"
                  @click="loadContextResources"
                  data-testid="qa-views-functional-test-suite-details-button-刷新-2"
                  >刷新</a-button
                >
                <a-button
                  size="small"
                  type="primary"
                  @click="openResource(undefined, rawCaseContextKey)"
                  data-testid="qa-views-functional-test-suite-details-button-新增资料-2"
                  >新增资料</a-button
                >
              </a-space>
              <a-space v-else-if="activePane === 'basic'">
                <a-button size="small" :loading="suiteLoading || qualityLoading" @click="refreshAll"
                  >刷新</a-button
                >
              </a-space>
              <a-space v-else-if="['plans', 'defects'].includes(String(activePane))">
                <a-button size="small" :loading="qualityLoading" @click="loadQualityRelations"
                  >刷新</a-button
                >
                <a-button
                  v-if="activePane === 'plans'"
                  size="small"
                  type="primary"
                  @click="createRequirementPlan"
                  >新建测试计划</a-button
                >
              </a-space>
            </div>

            <div
              :class="[
                'mango-functional-panel-body',
                { 'mango-functional-panel-body-case': activePane === 'cases' },
              ]"
            >
              <div v-if="!resourceSuiteId" class="mango-empty-state">需求版本 ID 无效</div>
              
              
              
              
              
              
              <mango-panel-spin v-if="hasActiveContextField" :loading="resourceLoading">
                <div class="mango-functional-resource-pane">
                  <div v-if="!activeResources.length" class="mango-empty-state">暂无上下文资料</div>
                  <div v-else class="mango-functional-resource-list">
                    <div
                      v-for="resource in activeResources"
                      :key="resource.id"
                      class="mango-functional-resource-item"
                    >
                      <div class="mango-functional-resource-main">
                        <div class="mango-functional-resource-title">
                          <span>{{ resource.title }}</span>
                          <a-space :size="4">
                            <a-tag :color="enumColor(resource.content_type)" size="small">{{
                              enumTitle(
                                enumStore.functional_test_context_content_type,
                                resource.content_type
                              )
                            }}</a-tag>
                            <a-tag
                              v-if="resource.content_type === RESOURCE_CONTENT_URL"
                              :color="enumColor(resource.url_type)"
                              size="small"
                            >
                              {{
                                enumTitle(
                                  enumStore.functional_test_context_url_type,
                                  resource.url_type
                                )
                              }}
                            </a-tag>
                            <a-tag v-if="!resource.enabled" :color="statusColor(0)" size="small"
                              >未启用</a-tag
                            >
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

              <mango-panel-spin
                v-else-if="activePane === 'basic'"
                :loading="suiteLoading"
                class="mango-functional-basic-pane"
              >
                <a-descriptions :column="2" bordered size="small">
                  <a-descriptions-item label="需求">{{
                    suite?.requirement?.name || suite?.requirement_name || '-'
                  }}</a-descriptions-item>
                  <a-descriptions-item label="需求版本"
                    >V{{ suite?.version_no || '-' }}</a-descriptions-item
                  >
                  <a-descriptions-item label="项目/产品">{{
                    formatProjectProductPath(suite?.project_product)
                  }}</a-descriptions-item>
                  <a-descriptions-item label="模块">{{
                    formatModulePath(suite?.module)
                  }}</a-descriptions-item>
                  <a-descriptions-item label="Sprint">{{
                    suite?.iteration_ref?.name || '-'
                  }}</a-descriptions-item>
                  <a-descriptions-item label="状态">{{
                    enumTitle(enumStore.manual_test_suite_status, suite?.status)
                  }}</a-descriptions-item>
                  <a-descriptions-item label="开发负责人">{{
                    suite?.development_owner?.name || '-'
                  }}</a-descriptions-item>
                  <a-descriptions-item label="测试负责人">{{
                    suite?.owner?.name || '-'
                  }}</a-descriptions-item>
                  <a-descriptions-item label="计划周期"
                    >{{ suite?.planned_start_date || '-' }} 至
                    {{ suite?.planned_submit_date || '-' }}</a-descriptions-item
                  >
                  <a-descriptions-item label="测试计划"
                    >{{ suite?.plan_count || relatedPlans.length || 0 }} 个</a-descriptions-item
                  >
                  <a-descriptions-item label="执行进度"
                    >{{ suite?.test_metrics?.executed || 0 }}/{{
                      suite?.test_metrics?.total || 0
                    }}（{{ formatPercent(suite?.test_metrics?.progress) }}）</a-descriptions-item
                  >
                  <a-descriptions-item label="通过率">{{
                    formatPercent(suite?.test_metrics?.pass_rate)
                  }}</a-descriptions-item>
                  <a-descriptions-item label="未关闭缺陷">{{
                    suite?.open_defect_count || 0
                  }}</a-descriptions-item>
                  <a-descriptions-item label="更新时间">{{
                    suite?.update_time || '-'
                  }}</a-descriptions-item>
                </a-descriptions>
              </mango-panel-spin>

              <div v-else-if="activePane === 'cases'" class="mango-functional-case-pane">
                <TableHeader class="mango-functional-case-filters"
                  ><a-form :model="caseFilters" layout="inline">
                    <a-form-item label="测试类型"
                      ><a-select
                        v-model="caseFilters.test_type"
                        :options="enumStore.manual_test_type"
                        :field-names="fieldNames"
                        allow-clear
                        placeholder="测试类型"
                        @change="searchCases"
                    /></a-form-item>
                    <a-form-item label="测试层级"
                      ><a-select
                        v-model="caseFilters.scenario_layer"
                        :options="enumStore.api_case_scenario_layer"
                        :field-names="fieldNames"
                        allow-clear
                        placeholder="测试层级"
                        @change="searchCases"
                    /></a-form-item>
                    <a-form-item label="验证类型"
                      ><a-select
                        v-model="caseFilters.scenario_type"
                        :options="enumStore.api_case_scenario_type"
                        :field-names="fieldNames"
                        allow-clear
                        placeholder="验证类型"
                        @change="searchCases"
                    /></a-form-item>
                    <a-form-item label="执行场景"
                      ><a-select
                        v-model="caseFilters.scenario_tag"
                        :options="enumStore.api_case_scenario_tag"
                        :field-names="fieldNames"
                        allow-clear
                        placeholder="执行场景"
                        @change="searchCases"
                    /></a-form-item>
                    <a-form-item label="变更"
                      ><a-select
                        v-model="caseFilters.change_status"
                        :options="enumStore.manual_test_change_status"
                        :field-names="fieldNames"
                        allow-clear
                        placeholder="变更"
                        @change="searchCases"
                    /></a-form-item>
                    <a-form-item label="自动化影响"
                      ><a-select
                        v-model="caseFilters.automation_impact_status"
                        :options="enumStore.manual_test_automation_impact_status"
                        :field-names="fieldNames"
                        allow-clear
                        placeholder="自动化影响"
                        @change="searchCases"
                    /></a-form-item>
                    <TableSearchActions
                      :loading="caseLoading"
                      @search="searchCases"
                      @reset="resetCaseFilters"
                    /> </a-form
                ></TableHeader>
                <div class="mango-functional-case-table">
                  <a-table
                    :bordered="false"
                    :columns="caseColumns"
                    :data="cases"
                    :loading="caseLoading"
                    :pagination="false"
                    :row-key="'id'"
                    :selected-keys="selectedCaseKeys"
                    @selection-change="selectedCaseKeys = $event"
                    :row-selection="{ type: 'checkbox', showCheckedAll: true }"
                    :scroll="{ x: caseScrollWidth, y: '100%' }"
                    class="mango-native-scroll-table"
                  >
                    <template #columns>
                      <a-table-column v-for="item of caseColumns" :key="item.key" v-bind="item">
                        <template v-if="item.key === 'title'" #cell="{ record }">
                          <a-link @click="openCase(record)">{{ record.title }}</a-link>
                        </template>
                        <template v-else-if="item.key === 'project_product'" #cell="{ record }">
                          {{ formatProjectProductPath(record.project_product) }}
                        </template>
                        <template v-else-if="item.key === 'module'" #cell="{ record }">
                          {{ formatModulePath(record.module) }}
                        </template>
                        <template v-else-if="item.key === 'priority'" #cell="{ record }">
                          <a-tag :color="enumColor(record.priority)" size="small">{{
                            enumTitle(enumStore.case_level, record.priority)
                          }}</a-tag>
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
                        <template v-else-if="item.key === 'actions'" #cell="{ record }">
                          <MangoTableActions
                            :actions="[
                              { label: '编辑', onClick: () => openCase(record) },
                              {
                                label: 'UI绑定',
                                onClick: () => openBind(record, AUTOMATION_TYPE_UI),
                              },
                              {
                                label: '前往API用例',
                                disabled: !bindingCaseId(record, AUTOMATION_TYPE_API),
                                onClick: () => goAutomationCase(record, AUTOMATION_TYPE_API),
                              },
                              {
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
                <a-table
                  :data="relatedPlans"
                  :loading="plansLoading"
                  :pagination="false"
                  :scroll="{ x: 1160 }"
                  row-key="id"
                >
                  <template #columns>
                    <a-table-column title="计划名称" :width="260"
                      ><template #cell="{ record }"
                        ><a-link @click="goPlan(record)">{{ record.name }}</a-link></template
                      ></a-table-column
                    >
                    <a-table-column title="状态" :width="100"
                      ><template #cell="{ record }">{{
                        enumTitle(enumStore.functional_test_plan_status, record.status)
                      }}</template></a-table-column
                    >
                    <a-table-column title="执行进度" :width="160"
                      ><template #cell="{ record }"
                        >{{ record.execution_stats?.executed || 0 }}/{{
                          record.execution_stats?.total || 0
                        }}</template
                      ></a-table-column
                    >
                    <a-table-column title="通过率" :width="100"
                      ><template #cell="{ record }">{{
                        formatPercent(record.execution_stats?.pass_rate)
                      }}</template></a-table-column
                    >
                    <a-table-column
                      title="未关闭缺陷"
                      data-index="open_defect_count"
                      :width="110"
                    />
                    <a-table-column title="负责人" :width="110"
                      ><template #cell="{ record }">{{
                        record.owner?.name || '-'
                      }}</template></a-table-column
                    >
                    <a-table-column title="更新时间" data-index="update_time" :width="165" />
                  </template>
                </a-table>
              </div>

              <div v-else-if="activePane === 'defects'" class="mango-functional-case-pane">
                <a-table
                  :data="relatedDefects"
                  :loading="defectsLoading"
                  :pagination="false"
                  :scroll="{ x: 1120 }"
                  row-key="id"
                >
                  <template #columns>
                    <a-table-column title="缺陷编号" :width="150"
                      ><template #cell="{ record }"
                        ><a-link @click="goDefect(record)">{{ record.defect_no }}</a-link></template
                      ></a-table-column
                    >
                    <a-table-column
                      title="缺陷标题"
                      data-index="title"
                      :width="300"
                      ellipsis
                      tooltip
                    />
                    <a-table-column title="状态" :width="110"
                      ><template #cell="{ record }">{{
                        enumTitle(enumStore.functional_test_defect_status, record.status)
                      }}</template></a-table-column
                    >
                    <a-table-column title="严重程度" :width="110"
                      ><template #cell="{ record }">{{
                        enumTitle(enumStore.functional_test_defect_severity, record.severity)
                      }}</template></a-table-column
                    >
                    <a-table-column title="负责人" :width="110"
                      ><template #cell="{ record }">{{
                        record.assignee?.name || '未分配'
                      }}</template></a-table-column
                    >
                    <a-table-column title="更新时间" data-index="update_time" :width="165" />
                  </template>
                </a-table>
              </div>

              <div v-else class="mango-functional-sync-pane">
                <section class="mango-functional-sync-editor">
                  <mango-panel-spin :loading="resourceLoading">
                    <div v-if="!rawCaseResources.length" class="mango-empty-state"
                      >暂无原始用例文档</div
                    >
                    <div v-else class="mango-functional-resource-list">
                      <div
                        v-for="resource in rawCaseResources"
                        :key="resource.id"
                        class="mango-functional-resource-item"
                      >
                        <div class="mango-functional-resource-main">
                          <div class="mango-functional-resource-title">
                            <span>{{ resource.title }}</span>
                            <a-space :size="4">
                              <a-tag :color="enumColor(resource.content_type)" size="small">{{
                                enumTitle(
                                  enumStore.functional_test_context_content_type,
                                  resource.content_type
                                )
                              }}</a-tag>
                              <a-tag
                                v-if="resource.content_type === RESOURCE_CONTENT_URL"
                                :color="enumColor(resource.url_type)"
                                size="small"
                              >
                                {{
                                  enumTitle(
                                    enumStore.functional_test_context_url_type,
                                    resource.url_type
                                  )
                                }}
                              </a-tag>
                              <a-tag v-if="!resource.enabled" :color="statusColor(0)" size="small"
                                >未启用</a-tag
                              >
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
                            {
                              label: '删除',
                              danger: true,
                              onClick: () => removeResource(resource),
                            },
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

  <SuiteCaseEditor
    ref="caseEditor"
    :suite-id="resourceSuiteId"
    :context-key="resourceContextKey"
    :available="editorAvailable"
    :defaults="caseDefaults"
    :blocked="bindingSaving || caseDeleting"
    @busy="caseSaving = $event"
    @changed="onCaseChanged"
  />
  <SuiteAutomationBinding
    ref="bindingEditor"
    :suite-id="resourceSuiteId"
    :context-key="resourceContextKey"
    :available="editorAvailable"
    :blocked="caseSaving || caseDeleting"
    :type-options="enumStore.manual_test_automation_type || []"
    @busy="bindingSaving = $event"
    @changed="onCaseChanged"
  />

  <SuiteResourceEditor
    ref="resourceEditor"
    :suite-id="resourceSuiteId"
    :product-id="resourceProductId"
    :context-key="resourceContextKey"
    :available="editorAvailable"
    :group-options="enumStore.functional_test_context_key || []"
    :type-options="enumStore.functional_test_context_content_type || []"
    @busy="resourceSaving = $event"
    @changed="onResourceChanged"
  />

  <BaseSidePanel
    :visible="apiCaseDetailVisible"
    :title="apiCaseDetailTitle"
    width="calc(92vw - 150px)"
    mode="page"
    @update:visible="
      (val) => {
        if (!val) closeApiDetails()
      }
    "
    @cancel="closeApiDetails"
  >
    <MangoPanelSpin :loading="apiDetailsLoading" class="mango-functional-api-case-panel">
      
      <component
        :is="ApiCaseDetails"
        v-if="available && apiCaseDetailVisible && apiCaseDetailId && ApiCaseDetails"
        :key="apiCaseDetailId"
        embedded
        :case-id="apiCaseDetailId"
        :project-product-id="apiCaseProductId"
        @close="closeApiDetails"
      />
    </MangoPanelSpin>
  </BaseSidePanel>
</template>

<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import {
    computed,
    onMounted,
    onActivated,
    onDeactivated,
    onBeforeUnmount,
    reactive,
    ref,
    shallowRef,
    watch,
  } from 'vue'
  import type { Component } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import { useRoute, useRouter } from 'vue-router'
  import useUserStore from '@/store/modules/user'
  import { useEnum } from '@/store/modules/get-enum'
  import { usePagination } from '@/hooks/table'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import SuiteResourceEditor from './components/SuiteResourceEditor.vue'
  import SuiteCaseEditor from './components/SuiteCaseEditor.vue'
  import SuiteAutomationBinding from './components/SuiteAutomationBinding.vue'
  import { resourceId, objectValue } from './resource-form'
  import type { ResourceEditorHandle, SuiteResource } from './resource-form'
  import { relationId } from './case-form'
  import type { SuiteCaseEditorHandle, SuiteBindingHandle } from './case-form'
  import {
    summary,
    caseRow,
    resourceRow,
    planRow,
    defectRow,
    list,
    createSuiteFilters,
    filterPayload,
  } from './presentation'
  import type { SuiteSummary, SuiteCaseRow, SuitePlan, SuiteDefect } from './presentation'
  import {
    AUTOMATION_TYPE_API,
    AUTOMATION_TYPE_UI,
    RESOURCE_KEY_REQUIREMENT_DOC,
    RESOURCE_KEY_RAW_CASE_DOC,
    RESOURCE_KEY_PLATFORM_CASE,
    RESOURCE_CONTENT_URL,
    navGroups,
    allNavItems,
    contextNavItems,
    contextFieldKeys,
    platformCaseNavItem,
    caseColumns,
    caseScrollWidth,
  } from './config'
  import {
    deleteFunctionalContextResource,
    deleteManualCase,
    getFunctionalContextResource,
    getRelatedFunctionalDefects,
    getRelatedFunctionalPlans,
    getManualCase,
    getManualSuite,
  } from '@/api/functional-test'
  import { formatModulePath, formatProjectProductPath } from '@/utils/business-format'
  import {
    getStatusTagColor,
    MANUAL_TEST_CHANGE_STATUS_COLORS,
    MANUAL_TEST_IMPACT_STATUS_COLORS,
  } from '@/utils/status-color'

  const route = useRoute(),
    router = useRouter(),
    enumStore = useEnum(),
    resourceUser = useUserStore()
  const ownerPath = route.path
  const fieldNames = { value: 'key', label: 'title' }
  const resourceSuiteId = computed(() => resourceId(route.query.id))
  const resourceContextKey = computed(() =>
    JSON.stringify([
      route.fullPath,
      resourceUser.userId,
      resourceUser.roleId,
      resourceUser.token,
      resourceUser.selected_environment,
    ])
  )
  const suite = shallowRef<SuiteSummary | null>(null)
  const cases = shallowRef<SuiteCaseRow[]>([])
  const contextResources = shallowRef<SuiteResource[]>([])
  const relatedPlans = shallowRef<SuitePlan[]>([]),
    relatedDefects = shallowRef<SuiteDefect[]>([])
  const selectedCaseKeys = ref<Array<number | string>>([])
  const caseFilters = reactive(createSuiteFilters())
  const casePagination = usePagination(loadCases, () => caseLoading)
  const suiteLoading = ref(false),
    caseLoading = ref(false),
    resourceLoading = ref(false)
  const plansLoading = ref(false),
    defectsLoading = ref(false),
    enumsLoading = ref(false)
  const suiteError = ref(false),
    caseError = ref(false),
    resourceError = ref(false)
  const plansError = ref(false),
    defectsError = ref(false),
    enumsError = ref(false)
  const loading = {
    suite: suiteLoading,
    cases: caseLoading,
    resources: resourceLoading,
    plans: plansLoading,
    defects: defectsLoading,
    enums: enumsLoading,
  }
  const errors = {
    suite: suiteError,
    cases: caseError,
    resources: resourceError,
    plans: plansError,
    defects: defectsError,
    enums: enumsError,
  }
  type ReadKey = 'suite' | 'cases' | 'resources' | 'plans' | 'defects' | 'enums'
  const sequences: Record<ReadKey, number> = {
    suite: 0,
    cases: 0,
    resources: 0,
    plans: 0,
    defects: 0,
    enums: 0,
  }
  const qualityLoading = computed(() => plansLoading.value || defectsLoading.value)
  const activePane = ref<number | string>('cases')
  const caseEditor = ref<SuiteCaseEditorHandle | null>(null),
    bindingEditor = ref<SuiteBindingHandle | null>(null)
  const resourceEditor = ref<ResourceEditorHandle | null>(null)
  const caseSaving = ref(false),
    bindingSaving = ref(false),
    resourceSaving = ref(false)
  const caseDeleting = ref(false),
    resourceDeleting = ref(false)
  const caseWriteBusy = computed(
    () => caseSaving.value || bindingSaving.value || caseDeleting.value
  )
  const resourceWriteBusy = computed(() => resourceSaving.value || resourceDeleting.value)
  const pendingCaseRefresh = ref(false),
    pendingResourceRefresh = ref(false)
  const resourceProductId = computed(() => suite.value?.project_product?.id ?? null)
  const caseDefaults = computed(() => ({
    productId: resourceProductId.value,
    moduleId: suite.value?.module?.id ?? null,
    ownerId: suite.value?.owner?.id ?? null,
  }))
  const available = computed(
    () => active.value && route.path === ownerPath && resourceSuiteId.value !== null
  )
  const editorAvailable = computed(
    () => available.value && !suiteError.value && suite.value?.id === resourceSuiteId.value
  )
  const active = ref(true)
  let mounted = false,
    generation = 0,
    paneTouched = false
  let caseConfirmation: ReturnType<typeof Modal.confirm> | null = null
  let resourceConfirmation: ReturnType<typeof Modal.confirm> | null = null
  const current = (version: number) => available.value && version === generation
  const rawCaseContextKey = RESOURCE_KEY_RAW_CASE_DOC
  const currentNavItem = computed(
    () => allNavItems.find((item) => item.key === activePane.value) || contextNavItems[0]
  )
  const activeContextField = computed(() =>
    contextFieldKeys.has(activePane.value) ? activePane.value : ''
  )
  const hasActiveContextField = computed(() => activeContextField.value !== '')
  const activeResources = computed(() =>
    contextResources.value.filter((item) => item.context_key === activeContextField.value)
  )
  const rawCaseResources = computed(() =>
    contextResources.value.filter((item) => item.context_key === rawCaseContextKey)
  )
  const workbenchTitle = computed(
    () =>
      `需求用例工作台 / ${suite.value?.id ?? resourceSuiteId.value ?? '-'} / ${
        suite.value?.requirement_name || '需求版本'
      }`
  )
  const apiCaseDetailVisible = ref(false),
    apiDetailsLoading = ref(false),
    apiDetailsError = ref(false)
  const apiCaseDetailId = ref<number | null>(null),
    apiCaseProductId = ref<number | null>(null),
    apiCaseDetailName = ref('')
  const ApiCaseDetails = shallowRef<Component | null>(null)
  const apiCaseDetailTitle = computed(() =>
    apiCaseDetailName.value ? `API 用例详情 / ${apiCaseDetailName.value}` : 'API 用例详情'
  )
  const navigationLoading = ref(false)
  let apiSequence = 0

  function enumTitle(options: Array<{ key: string | number; title: string }> = [], value: unknown) {
    return (
      options.find((item) => String(item.key) === String(value))?.title ??
      (value === null || value === undefined || value === '' ? '-' : String(value))
    )
  }
  const formatPercent = (value: unknown) =>
    `${(typeof value === 'number' && Number.isFinite(value) ? value : 0)
      .toFixed(2)
      .replace(/\.00$/, '')}%`
  const enumColor = (value: string | number | null) => enumStore.colors?.[Number(value)]
  const statusColor = (value: number) => enumStore.status_colors?.[value]
  const changeStatusColor = (value: number) =>
    getStatusTagColor(MANUAL_TEST_CHANGE_STATUS_COLORS, value)
  const impactStatusColor = (value: number) =>
    getStatusTagColor(MANUAL_TEST_IMPACT_STATUS_COLORS, value)
  function bindingCaseId(record: SuiteCaseRow, type: number) {
    const binding = record.bindings.find((item) => item.automation_type === type)
    return binding
      ? (type === AUTOMATION_TYPE_API ? binding.api_case : binding.ui_case) ??
          binding.automation_case_id
      : null
  }
  function automationCaseLinks(record: SuiteCaseRow) {
    return [AUTOMATION_TYPE_API, AUTOMATION_TYPE_UI].flatMap((type) => {
      const id = bindingCaseId(record, type)
      return id === null
        ? []
        : [{ type, label: `${type === AUTOMATION_TYPE_API ? 'API' : 'UI'} ID：${id}` }]
    })
  }
  function navItemCount(item: { key: number | string }) {
    if (item.key === 'basic') return suite.value ? 1 : 0
    if (item.key === 'cases' || item.key === RESOURCE_KEY_PLATFORM_CASE)
      return suite.value?.case_count ?? casePagination.pageCount
    if (item.key === 'plans') return relatedPlans.value.length
    if (item.key === 'defects') return relatedDefects.value.length
    const key = item.key === 'sync' ? rawCaseContextKey : item.key
    return contextResources.value.filter(
      (resource) => resource.context_key === key && resource.enabled
    ).length
  }
  function selectBestInitialPane() {
    if (paneTouched) return
    if (navItemCount(platformCaseNavItem)) {
      activePane.value = 'cases'
      return
    }
    activePane.value =
      allNavItems.find((item) => navItemCount(item) > 0)?.key ?? RESOURCE_KEY_REQUIREMENT_DOC
  }
  function choosePane(key: number | string) {
    paneTouched = true
    activePane.value = key
  }
  async function readRegion<T>(
    key: ReadKey,
    request: () => Promise<T>,
    apply: (response: T) => void
  ) {
    if (!available.value) {
      loading[key].value = false
      return false
    }
    const version = generation,
      sequence = ++sequences[key]
    loading[key].value = true
    errors[key].value = false
    try {
      const response = await request()
      if (!current(version) || sequence !== sequences[key]) return false
      apply(response)
      return true
    } catch {
      if (current(version) && sequence === sequences[key]) errors[key].value = true
      return false
    } finally {
      if (current(version) && sequence === sequences[key]) loading[key].value = false
    }
  }
  function loadSuite() {
    if (caseWriteBusy.value) {
      pendingCaseRefresh.value = true
      return Promise.resolve(false)
    }
    const id = resourceSuiteId.value
    if (id === null) return Promise.resolve(false)
    return readRegion(
      'suite',
      () => getManualSuite({ id }),
      (response) => {
        const rows = list(response.data, (row) => summary(row, id))
        suite.value = rows[0] ?? null
      }
    )
  }
  function loadPlans() {
    const id = resourceSuiteId.value
    if (id === null) return Promise.resolve(false)
    return readRegion(
      'plans',
      () => getRelatedFunctionalPlans({ requirement_version_id: id }),
      (response) => {
        relatedPlans.value = list(response.data, planRow)
      }
    )
  }
  function loadDefects() {
    const id = resourceSuiteId.value
    if (id === null) return Promise.resolve(false)
    return readRegion(
      'defects',
      () => getRelatedFunctionalDefects({ requirement_version_id: id }),
      (response) => {
        relatedDefects.value = list(response.data, defectRow)
      }
    )
  }
  function loadQualityRelations() {
    return Promise.all([loadPlans(), loadDefects()])
  }
  function loadEnums() {
    return readRegion(
      'enums',
      () => enumStore.getEnum(true),
      () => {}
    )
  }
  function loadCases() {
    if (caseWriteBusy.value) {
      pendingCaseRefresh.value = true
      caseLoading.value = false
      return Promise.resolve(false)
    }
    const id = resourceSuiteId.value
    if (id === null) {
      caseLoading.value = false
      return Promise.resolve(false)
    }
    const query = {
      suite: id,
      page: casePagination.page,
      pageSize: casePagination.pageSize,
      ...filterPayload(caseFilters),
    }
    return readRegion(
      'cases',
      () => getManualCase(query),
      (response) => {
        const rows = list(response.data, (row) => caseRow(row, id))
        const total = response.totalSize
        if (typeof total !== 'number' || !Number.isSafeInteger(total) || total < 0)
          throw Error('Invalid count')
        cases.value = rows
        casePagination.setTotalSize(total)
        selectedCaseKeys.value = selectedCaseKeys.value.filter((key) =>
          rows.some((row) => row.id === resourceId(key))
        )
      }
    )
  }
  function searchCases() {
    casePagination.page = 1
    selectedCaseKeys.value = []
    return loadCases()
  }
  function resetCaseFilters() {
    Object.assign(caseFilters, createSuiteFilters())
    return searchCases()
  }
  function loadContextResources() {
    if (resourceWriteBusy.value) {
      pendingResourceRefresh.value = true
      return Promise.resolve(false)
    }
    const id = resourceSuiteId.value
    if (id === null) return Promise.resolve(false)
    return readRegion(
      'resources',
      () => getFunctionalContextResource({ suite: id, page: 1, pageSize: 200 }),
      (response) => {
        contextResources.value = list(response.data, (row) => resourceRow(row, id))
      }
    )
  }
  async function refreshAll() {
    const version = generation
    await Promise.all([
      loadSuite(),
      loadCases(),
      loadContextResources(),
      loadQualityRelations(),
      loadEnums(),
    ])
    if (current(version)) selectBestInitialPane()
  }
  const resourceSummary = (resource: SuiteResource) =>
    resource.extracted_text ||
    resource.content ||
    [resource.file_name, resource.file_path].filter(Boolean).join(' / ') ||
    '暂无内容'
  function ownsCase(record: SuiteCaseRow) {
    return (
      editorAvailable.value &&
      relationId(record.suite) === resourceSuiteId.value &&
      cases.value.some((row) => row.id === record.id)
    )
  }
  function ownsResource(record: SuiteResource) {
    return (
      editorAvailable.value &&
      record.suite === resourceSuiteId.value &&
      contextResources.value.some((row) => row.id === record.id)
    )
  }
  function openCase(record?: SuiteCaseRow) {
    if (!caseWriteBusy.value && editorAvailable.value && (!record || ownsCase(record)))
      caseEditor.value?.open(record)
  }
  function openBind(record: SuiteCaseRow, type: number) {
    if (!caseWriteBusy.value && ownsCase(record)) bindingEditor.value?.open(record, type)
  }
  function openRawResource(record: SuiteResource) {
    if (!resourceWriteBusy.value && ownsResource(record))
      resourceEditor.value?.open(record.context_key, record.title, record, true)
  }
  function openResource(record?: SuiteResource, contextKey = activeContextField.value) {
    if (!editorAvailable.value || resourceWriteBusy.value || (record && !ownsResource(record)))
      return
    const key = Number(record?.context_key ?? contextKey)
    const item = contextNavItems.find((nav) => nav.key === key)
    if (item) resourceEditor.value?.open(key, item.title, record)
  }
  function onCaseChanged(id: number) {
    if (available.value && id === resourceSuiteId.value) pendingCaseRefresh.value = true
  }
  function onResourceChanged(id: number) {
    if (available.value && id === resourceSuiteId.value) pendingResourceRefresh.value = true
  }
  watch(
    [caseWriteBusy, pendingCaseRefresh],
    () => {
      if (caseWriteBusy.value || !pendingCaseRefresh.value || !available.value) return
      pendingCaseRefresh.value = false
      void Promise.all([loadCases(), loadSuite()])
    },
    { flush: 'post' }
  )
  watch(
    [resourceWriteBusy, pendingResourceRefresh],
    () => {
      if (resourceWriteBusy.value || !pendingResourceRefresh.value || !available.value) return
      pendingResourceRefresh.value = false
      void loadContextResources()
    },
    { flush: 'post' }
  )
  watch(
    caseWriteBusy,
    (busy) => {
      if (busy) {
        ++sequences.cases
        ++sequences.suite
        caseLoading.value = false
        suiteLoading.value = false
      }
    },
    { flush: 'sync' }
  )
  watch(
    resourceWriteBusy,
    (busy) => {
      if (busy) {
        ++sequences.resources
        resourceLoading.value = false
      }
    },
    { flush: 'sync' }
  )

  function batchDeleteCases() {
    if (!editorAvailable.value || caseWriteBusy.value || caseConfirmation) return
    const ids = [
      ...new Set(
        selectedCaseKeys.value
          .map(resourceId)
          .filter((id): id is number => id !== null && cases.value.some((row) => row.id === id))
      ),
    ]
    if (!ids.length) {
      Message.warning('请选择要删除的用例')
      return
    }
    const version = generation
    caseConfirmation = Modal.confirm({
      title: '批量删除用例',
      content: `确认删除已选择的 ${ids.length} 条用例吗？`,
      okText: '删除',
      cancelText: '取消',
      onBeforeCancel: () => !caseDeleting.value,
      onCancel: () => {
        caseConfirmation = null
      },
      onBeforeOk: async () => {
        if (!current(version) || caseWriteBusy.value) return false
        caseDeleting.value = true
        try {
          const response = await deleteManualCase({ ids: [...ids] })
          if (!current(version)) return false
          if (objectValue(response.data).count !== ids.length)
            throw Error('Invalid deletion response')
          cases.value = cases.value.filter((row) => !ids.includes(row.id))
          selectedCaseKeys.value = selectedCaseKeys.value.filter((id) => !ids.includes(Number(id)))
          casePagination.setTotalSize(Math.max(0, casePagination.pageCount - ids.length))
          casePagination.page = Math.min(
            casePagination.page,
            Math.max(1, Math.ceil(casePagination.pageCount / casePagination.pageSize))
          )
          Message.success('删除成功')
          caseConfirmation = null
          pendingCaseRefresh.value = true
          return true
        } catch {
          if (current(version)) Message.error('删除失败，请重试')
          return false
        } finally {
          caseDeleting.value = false
        }
      },
    })
  }
  function removeResource(record: SuiteResource) {
    if (!ownsResource(record) || resourceWriteBusy.value || resourceConfirmation) return
    const id = record.id,
      version = generation
    resourceConfirmation = Modal.confirm({
      title: '删除资料',
      content: `确认删除「${record.title}」吗？`,
      okText: '删除',
      cancelText: '取消',
      onBeforeCancel: () => !resourceDeleting.value,
      onCancel: () => {
        resourceConfirmation = null
      },
      onBeforeOk: async () => {
        if (!current(version) || resourceWriteBusy.value) return false
        resourceDeleting.value = true
        try {
          const response = await deleteFunctionalContextResource(id)
          if (!current(version)) return false
          const result = objectValue(response.data)
          if (
            result.deleted_count !== 1 ||
            !Array.isArray(result.deleted_resource_ids) ||
            result.deleted_resource_ids.length !== 1 ||
            resourceId(result.deleted_resource_ids[0]) !== id
          )
            throw Error('Invalid deletion response')
          contextResources.value = contextResources.value.filter((item) => item.id !== id)
          Message.success('已删除')
          resourceConfirmation = null
          pendingResourceRefresh.value = true
          return true
        } catch {
          if (current(version)) Message.error('删除失败，请重试')
          return false
        } finally {
          resourceDeleting.value = false
        }
      },
    })
  }
  async function navigate(target: Parameters<typeof router.push>[0]) {
    if (!available.value || navigationLoading.value) return
    const version = generation
    navigationLoading.value = true
    try {
      await router.push(target)
    } catch {
      if (current(version)) Message.error('页面打开失败，请重试')
    } finally {
      navigationLoading.value = false
    }
  }
  const goPlan = (record: SuitePlan) =>
    relatedPlans.value.some((row) => row.id === record.id)
      ? navigate({ path: '/functional-test/plan/details', query: { id: record.id } })
      : undefined
  const goDefect = (record: SuiteDefect) =>
    relatedDefects.value.some((row) => row.id === record.id)
      ? navigate({ path: '/functional-test/defect/index', query: { defect_id: record.id } })
      : undefined
  function createRequirementPlan() {
    if (!editorAvailable.value || resourceProductId.value === null) return
    return navigate({
      path: '/functional-test/plan/index',
      query: {
        create: '1',
        requirement_version: resourceSuiteId.value,
        project_product: resourceProductId.value,
      },
    })
  }
  async function loadApiDetails() {
    if (!available.value || !apiCaseDetailVisible.value) return
    const version = generation,
      sequence = ++apiSequence
    apiDetailsLoading.value = true
    apiDetailsError.value = false
    try {
      const module = await import('@/views/apitest/case/details/index.vue')
      if (current(version) && sequence === apiSequence && apiCaseDetailVisible.value)
        ApiCaseDetails.value = module.default
    } catch (loadFailure0) {
      if (current(version) && sequence === apiSequence) (reportLoadError(loadFailure0, "加载失败，请重试", false), apiDetailsError.value = true)
    } finally {
      if (current(version) && sequence === apiSequence) apiDetailsLoading.value = false
    }
  }
  function closeApiDetails() {
    ++apiSequence
    apiCaseDetailVisible.value = false
    apiCaseDetailId.value = null
    apiCaseProductId.value = null
    apiDetailsLoading.value = false
    apiDetailsError.value = false
  }
  function goAutomationCase(record: SuiteCaseRow, type: number) {
    if (!ownsCase(record)) return
    const id = bindingCaseId(record, type)
    if (id === null) return
    if (type === AUTOMATION_TYPE_API) {
      closeApiDetails()
      apiCaseDetailId.value = id
      apiCaseProductId.value = record.project_product?.id ?? resourceProductId.value
      apiCaseDetailName.value = record.title
      apiCaseDetailVisible.value = true
      void loadApiDetails()
    } else void navigate({ path: '/uitest/case/details', query: { id } })
  }
  function resetPage(resetFilters = true) {
    ++generation
    for (const key of Object.keys(sequences) as ReadKey[]) {
      ++sequences[key]
      loading[key].value = false
      errors[key].value = false
    }
    suite.value = null
    cases.value = []
    contextResources.value = []
    relatedPlans.value = []
    relatedDefects.value = []
    selectedCaseKeys.value = []
    pendingCaseRefresh.value = false
    pendingResourceRefresh.value = false
    caseConfirmation?.close()
    caseConfirmation = null
    resourceConfirmation?.close()
    resourceConfirmation = null
    closeApiDetails()
    if (resetFilters) {
      Object.assign(caseFilters, createSuiteFilters())
      casePagination.page = 1
      casePagination.setTotalSize(0)
      paneTouched = false
      activePane.value = 'cases'
    }
  }
  watch(
    resourceContextKey,
    () => {
      resetPage()
      if (mounted && available.value) void refreshAll()
    },
    { flush: 'sync' }
  )
  onMounted(() => {
    mounted = true
    if (available.value) void refreshAll()
  })
  onDeactivated(() => {
    active.value = false
    resetPage(false)
  })
  onActivated(() => {
    if (!active.value) {
      active.value = true
      void refreshAll()
    }
  })
  onBeforeUnmount(() => {
    active.value = false
    resetPage()
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
    --mango-workbench-min-width: 960px;
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
    align-self: stretch;
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
    display: flex;
    flex: 1;
    min-height: 0;
    padding: 0;
    overflow-x: hidden;
    overflow-y: hidden;
  }

  .mango-functional-panel-body > :deep(.arco-spin) {
    height: 100%;
  }

  .mango-functional-resource-pane {
    flex: 1;
    min-height: 0;
  }

  .mango-functional-case-pane {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
  }

  .mango-functional-case-filters {
    flex-shrink: 0;
    border-bottom: 1px solid var(--m-border);
  }

  .mango-functional-case-table {
    display: flex;
    flex: 1;
    min-height: 0;
    min-width: 0;
  }

  .mango-functional-case-table :deep(.arco-table) {
    flex: 1;
    min-width: 0;
    min-height: 0;
  }

  .mango-functional-case-table :deep(.arco-spin),
  .mango-functional-case-table :deep(.arco-table-content),
  .mango-functional-case-table :deep(.arco-scrollbar),
  .mango-functional-case-table :deep(.arco-scrollbar-container) {
    min-height: 0;
  }

  .mango-functional-case-footer {
    flex-shrink: 0;
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
    display: flex;
    height: 100%;
    width: 100%;
    min-width: 0;
    min-height: 0;
  }

  .mango-functional-api-case-panel :deep(> .mango-panel-spin__content) {
    height: 100%;
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
