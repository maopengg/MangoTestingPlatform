<template>
  <TableBody class="mango-detail-workbench-page mango-timing-case-page" :sticky-horizontal-scroll="false">
    <template v-if="!props.embedded" #header>
      <div class="mango-detail-toolbar">
        <div class="mango-detail-heading">
          <div class="mango-detail-title">{{ taskCaseDetailTitle }}</div>
          <div class="mango-detail-subtitle">
            {{
              taskConfigLoading
                ? '正在读取定时任务配置'
                : isManualScope
                  ? '维护当前定时任务绑定的执行用例和执行顺序'
                  : '查看当前规则实时匹配的已发布用例'
            }}
          </div>
        </div>
        <a-space class="mango-detail-actions" wrap>
          <a-button class="mango-back-button" size="small" @click="doResetSearch" data-testid="qa-views-timing-tasks-case-button-返回">返回</a-button>
        </a-space>
      </div>
    </template>

    <template #default>
      <div v-if="taskConfigLoading" class="mango-section-card mango-timing-case-initial-loading">
        <a-spin :loading="true" tip="正在读取定时任务配置..." />
      </div>
      <div
        v-else-if="taskConfig && isManualScope"
        class="mango-workbench-scroll-x mango-timing-case-workbench-scroll"
      >
      <div class="mango-timing-case-workbench">
        <section class="mango-section-card mango-timing-case-picker">
          <div class="mango-section-title">
            <div>
              <h3>添加用例</h3>
              <p>按类型、项目、模块名称筛选后批量添加到当前定时任务</p>
            </div>
            <a-button v-permission="'timing.tasks:edit'"
              size="small"
              type="primary"
              :disabled="addSelectionKeys.length === 0"
              :loading="addLoading"
              @click="onAddSelectedCases" data-testid="qa-views-timing-tasks-case-button-添加选中"
            >
              添加选中 {{ addSelectionKeys.length }}
            </a-button>
          </div>

          <div class="mango-soft-panel mango-timing-case-filter">
            <a-form :model="addForm" layout="horizontal" @keyup.enter="loadCandidateCases">
              <a-form-item label="测试类型">
                <a-select
                  v-model="addForm.type"
                  :field-names="fieldNames"
                  :options="taskCaseTypeOptions"
                  :disabled="fixedTaskType !== null"
                  allow-search
                  value-key="key"
                  @change="changeType"
                />
              </a-form-item>
              <a-form-item label="项目/产品">
                <a-tooltip :content="formatProjectProductPath(taskConfig?.project_product)">
                  <div class="mango-timing-case-selector-tooltip">
                    <ProjectProductSelect
                      v-model="addForm.projectProduct"
                      disabled
                      placeholder="请选择项目/产品"
                      @change="onProjectProductChange" data-testid="qa-views-timing-tasks-case-projectproductselect-请选择项目-产品"
                    />
                  </div>
                </a-tooltip>
              </a-form-item>
              <a-form-item label="模块名称">
                <a-tooltip :content="formatModulePath(taskConfig?.module)" :disabled="!hasFixedTaskModule">
                  <div class="mango-timing-case-selector-tooltip">
                    <ProductModuleSelect
                      v-model="addForm.module"
                      :auto-clear="false"
                      :check-strictly="true"
                      :selectable-level="0"
                      :project-product-id="addForm.projectProduct"
                      :disabled="hasFixedTaskModule"
                      placeholder="请选择模块名称"
                      @change="loadCandidateCases" data-testid="qa-views-timing-tasks-case-productmoduleselect-请选择模块名称"
                    />
                  </div>
                </a-tooltip>
              </a-form-item>
              <a-form-item label="优先级">
                <a-tooltip :content="selectedFilterText(addForm.levels, enumStore.case_level)" :disabled="!addForm.levels.length">
                  <div class="mango-timing-case-selector-tooltip">
                    <a-select
                      v-model="addForm.levels"
                      :field-names="fieldNames"
                      :options="enumStore.case_level"
                      allow-clear
                      allow-search
                      multiple
                      tag-nowrap
                      :max-tag-count="1"
                      :trigger-props="candidateFilterTriggerProps"
                      placeholder="请选择优先级"
                      value-key="key"
                      @change="loadCandidateCases" data-testid="qa-views-timing-tasks-case-select-请选择优先级"
                    />
                  </div>
                </a-tooltip>
              </a-form-item>
              <a-form-item label="测试层级">
                <a-tooltip :content="selectedFilterText(addForm.scenarioLayers, enumStore.api_case_scenario_layer)" :disabled="!addForm.scenarioLayers.length">
                  <div class="mango-timing-case-selector-tooltip">
                    <a-select
                      v-model="addForm.scenarioLayers"
                      :field-names="fieldNames"
                      :options="enumStore.api_case_scenario_layer"
                      allow-clear
                      allow-search
                      multiple
                      tag-nowrap
                      :max-tag-count="1"
                      :trigger-props="candidateFilterTriggerProps"
                      placeholder="请选择测试层级"
                      value-key="key"
                      @change="loadCandidateCases" data-testid="qa-views-timing-tasks-case-select-请选择测试层级"
                    />
                  </div>
                </a-tooltip>
              </a-form-item>
              <a-form-item label="验证类型">
                <a-tooltip :content="selectedFilterText(addForm.scenarioTypes, enumStore.api_case_scenario_type)" :disabled="!addForm.scenarioTypes.length">
                  <div class="mango-timing-case-selector-tooltip">
                    <a-select
                      v-model="addForm.scenarioTypes"
                      :field-names="fieldNames"
                      :options="enumStore.api_case_scenario_type"
                      allow-clear
                      allow-search
                      multiple
                      tag-nowrap
                      :max-tag-count="1"
                      :trigger-props="candidateFilterTriggerProps"
                      placeholder="请选择验证类型"
                      value-key="key"
                      @change="loadCandidateCases" data-testid="qa-views-timing-tasks-case-select-请选择验证类型"
                    />
                  </div>
                </a-tooltip>
              </a-form-item>
              <a-form-item label="执行场景">
                <a-tooltip :content="selectedFilterText(addForm.scenarioTags, enumStore.api_case_scenario_tag)" :disabled="!addForm.scenarioTags.length">
                  <div class="mango-timing-case-selector-tooltip">
                    <a-select
                      v-model="addForm.scenarioTags"
                      :field-names="fieldNames"
                      :options="enumStore.api_case_scenario_tag"
                      allow-clear
                      allow-search
                      multiple
                      tag-nowrap
                      :max-tag-count="1"
                      :trigger-props="candidateFilterTriggerProps"
                      placeholder="请选择执行场景"
                      value-key="key"
                      @change="loadCandidateCases" data-testid="qa-views-timing-tasks-case-select-请选择执行场景"
                    />
                  </div>
                </a-tooltip>
              </a-form-item>
              <a-form-item label="用例名称">
                <a-input
                  v-model="addForm.caseName"
                  allow-clear
                  placeholder="请输入用例名称"
                  @blur="loadCandidateCases"
                  @clear="loadCandidateCases" data-testid="qa-views-timing-tasks-case-input-请输入用例名称"
                />
              </a-form-item>
              <a-form-item v-if="isApiCaseType" label="执行版本">
                <a-tooltip :content="selectedFilterText(addForm.executionVersions, candidateExecutionVersionOptions)" :disabled="!addForm.executionVersions.length">
                  <div class="mango-timing-case-selector-tooltip">
                    <a-select
                      v-model="addForm.executionVersions"
                      :options="candidateExecutionVersionOptions"
                      multiple
                      tag-nowrap
                      :max-tag-count="1"
                      :trigger-props="candidateFilterTriggerProps"
                      allow-clear
                      placeholder="请选择执行版本"
                      @change="onExecutionVersionFilterChange"
                      data-testid="qa-views-timing-tasks-case-select-请选择执行版本"
                    />
                  </div>
                </a-tooltip>
              </a-form-item>
            </a-form>
          </div>

          <div class="mango-timing-case-list-head">
            <a-checkbox
              :disabled="selectableCandidateCases.length === 0"
              :indeterminate="candidateAllCheckedIndeterminate"
              :model-value="candidateAllChecked"
              @change="toggleAllCandidateCases" data-testid="qa-views-timing-tasks-case-checkbox-可添加用例"
            >
              可添加用例
            </a-checkbox>
            <small>
              已加载 {{ filteredCandidateCases.length }} / 可添加 {{ selectableCandidateCases.length }}
            </small>
          </div>
          <div class="mango-timing-case-candidate-table">
            <StickyHorizontalTable :scroll-x="1040">
              <a-table
                class="mango-timing-case-table"
                :bordered="false"
                :columns="candidateColumns"
                :data="pagedCandidateCases"
                :loading="candidateLoading || boundCaseKeysLoading"
                :pagination="false"
                :row-key="'key'"
                size="small"
                :scroll="{ x: 1040, y: '100%' }"
              >
                <template #columns>
                  <a-table-column title="" data-index="selected" :width="54" align="center">
                    <template #cell="{ record }">
                      <a-checkbox
                        :disabled="!isCandidateSelectable(record)"
                        :model-value="addSelectionKeys.includes(record.key)"
                        @change="(checked) => toggleCandidateCase(record.key, checked as boolean)"
                      />
                    </template>
                  </a-table-column>
                  <a-table-column
                    title="用例名称"
                    data-index="title"
                    :ellipsis="true"
                    :tooltip="true"
                  >
                    <template #cell="{ record }">
                      <span :class="{ 'mango-muted-text': isCaseBound(record.key) }">
                        {{ record.title }}
                      </span>
                    </template>
                  </a-table-column>
                  <a-table-column
                    title="模块名称"
                    data-index="module"
                    :width="220"
                    :ellipsis="true"
                    :tooltip="true"
                  >
                    <template #cell="{ record }">
                      {{ formatModulePath(record.module) }}
                    </template>
                  </a-table-column>
                  <a-table-column
                    v-if="isApiCaseType"
                    title="执行版本"
                    data-index="release"
                    :width="190"
                  >
                    <template #cell="{ record }">
                      <a-tag
                        :color="record.published_release_id ? 'green' : 'gray'"
                        size="small"
                      >
                        {{ record.published_release_id ? '当前已发布' : '暂无已发布版本' }}
                      </a-tag>
                    </template>
                  </a-table-column>
                  <a-table-column title="状态" data-index="status" :width="86" align="center">
                    <template #cell="{ record }">
                      <a-tag v-if="isCaseBound(record.key)" size="small">已添加</a-tag>
                      <a-tag v-else-if="!isCandidateSelectable(record)" color="gray" size="small">
                        未发布
                      </a-tag>
                      <a-tag v-else color="green" size="small">可添加</a-tag>
                    </template>
                  </a-table-column>
                </template>
              </a-table>
            </StickyHorizontalTable>
            <TableFooter class="mango-timing-case-footer" :pagination="candidatePagination" />
          </div>
        </section>

        <section class="mango-section-card mango-timing-case-bound">
          <div class="mango-section-title">
            <div>
              <h3>已绑定用例</h3>
              <p>支持搜索、拖拽排序、单个删除和批量删除</p>
            </div>
            <div class="mango-timing-case-bound-actions">
              <div class="mango-timing-case-summary">
                <span>总数 {{ boundStats.total }}</span>
                <span>UI {{ boundStats.ui }}</span>
                <span>API {{ boundStats.api }}</span>
                <span>Pytest {{ boundStats.pytest }}</span>
              </div>
              <a-button v-permission="'timing.tasks:delete'"
                size="small"
                status="danger"
                :loading="deleteLoading"
                @click="onDelete(null)" data-testid="qa-views-timing-tasks-case-button-批量删除"
              >
                批量删除
              </a-button>
            </div>
          </div>

          <div class="mango-soft-panel mango-timing-case-bound-filter">
            <a-form :model="boundFilter" layout="vertical">
              <a-form-item label="测试类型">
                <a-select
                  v-model="boundFilter.type"
                  :field-names="fieldNames"
                  :options="taskCaseTypeOptions"
                  allow-clear
                  allow-search
                  placeholder="全部类型"
                  value-key="key"
                  @change="onBoundTypeChange" data-testid="qa-views-timing-tasks-case-select-全部类型"
                />
              </a-form-item>
              <a-form-item label="项目/产品">
                <ProjectProductSelect
                  v-model="boundFilter.projectProduct"
                  placeholder="全部项目/产品"
                  @change="onBoundProjectProductChange" data-testid="qa-views-timing-tasks-case-projectproductselect-全部项目-产品"
                />
              </a-form-item>
              <a-form-item label="模块名称">
                <ProductModuleSelect
                  v-if="!isBoundPytestCaseType"
                  v-model="boundFilter.module"
                  :auto-clear="false"
                  :check-strictly="true"
                  :selectable-level="0"
                  :project-product-id="boundFilter.projectProduct"
                  placeholder="全部模块名称"
                  @change="onBoundFilterChange" data-testid="qa-views-timing-tasks-case-productmoduleselect-全部模块名称"
                />
                <a-select
                  v-else
                  v-model="boundFilter.module"
                  :field-names="fieldNames"
                  :options="data.boundModuleList"
                  allow-clear
                  allow-search
                  placeholder="全部模块名称"
                  value-key="key"
                  @change="onBoundFilterChange" data-testid="qa-views-timing-tasks-case-select-全部模块名称"
                />
              </a-form-item>
              <a-form-item label="负责人">
                <a-select
                  v-model="boundFilter.casePeople"
                  :field-names="fieldNames"
                  :options="data.nickname"
                  allow-clear
                  allow-search
                  placeholder="全部负责人"
                  value-key="key"
                  @change="onBoundFilterChange" data-testid="qa-views-timing-tasks-case-select-全部负责人"
                />
              </a-form-item>
              <a-form-item label="用例名称">
                <a-input
                  v-model="boundFilter.caseName"
                  allow-clear
                  placeholder="搜索用例名称"
                  @blur="onBoundFilterChange"
                  @clear="onBoundFilterChange"
                  @press-enter="onBoundFilterChange" data-testid="qa-views-timing-tasks-case-input-搜索用例名称"
                />
              </a-form-item>
            </a-form>
          </div>

          <div class="mango-timing-case-bound-table">
            <StickyHorizontalTable :scroll-x="1870">
              <a-table
                class="mango-timing-case-table"
                :bordered="false"
                :columns="tableColumns"
                :data="table.dataList"
                :draggable="{ type: 'handle', width: 40 }"
                :loading="table.tableLoading.value"
                :pagination="false"
                :row-selection="{ selectedRowKeys, showCheckedAll }"
                :row-key="rowKey"
                size="small"
                :scroll="{ x: 1870, y: '100%' }"
                @selection-change="onSelectionChange"
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
                  <template v-else-if="item.key === 'type'" #cell="{ record }">
                    <a-tag :color="enumStore.colors[record.type]" size="small">
                      {{ enumStore.test_case_type[record.type]?.title || '-' }}
                    </a-tag>
                  </template>
                  <template v-else-if="item.key === 'case_id'" #cell="{ record }">
                    {{ getBoundCaseName(record) }}
                  </template>
                  <template v-else-if="item.key === 'project_product'" #cell="{ record }">
                    {{ getBoundCaseProjectProduct(record) }}
                  </template>
                  <template v-else-if="item.key === 'module'" #cell="{ record }">
                    {{ getBoundCaseModule(record) }}
                  </template>
                  <template v-else-if="item.key === 'case_people'" #cell="{ record }">
                    {{ getBoundCaseOwner(record) }}
                  </template>
                  <template v-else-if="item.key === 'scenario_layer'" #cell="{ record }">
                    <a-tag
                      v-if="getBoundCaseEnumValue(record, 'scenario_layer') !== null"
                      :color="enumStore.colors[getBoundCaseEnumValue(record, 'scenario_layer')]"
                      size="small"
                    >
                      {{
                        getEnumTitle(
                          enumStore.api_case_scenario_layer,
                          getBoundCaseEnumValue(record, 'scenario_layer')
                        )
                      }}
                    </a-tag>
                    <span v-else>-</span>
                  </template>
                  <template v-else-if="item.key === 'scenario_tags'" #cell="{ record }">
                    <a-space v-if="getBoundCaseTags(record).length" size="mini" wrap>
                      <a-tag
                        v-for="tag of getBoundCaseTags(record)"
                        :key="tag"
                        :color="enumStore.colors[tag]"
                        size="small"
                      >
                        {{ getEnumTitle(enumStore.api_case_scenario_tag, tag) }}
                      </a-tag>
                    </a-space>
                    <span v-else>-</span>
                  </template>
                  <template v-else-if="item.key === 'scenario_type'" #cell="{ record }">
                    <a-tag
                      v-if="getBoundCaseEnumValue(record, 'scenario_type') !== null"
                      :color="enumStore.colors[getBoundCaseEnumValue(record, 'scenario_type')]"
                      size="small"
                    >
                      {{
                        getEnumTitle(
                          enumStore.api_case_scenario_type,
                          getBoundCaseEnumValue(record, 'scenario_type')
                        )
                      }}
                    </a-tag>
                    <span v-else>-</span>
                  </template>
                  <template v-else-if="item.key === 'level'" #cell="{ record }">
                    <a-tag
                      v-if="getBoundCaseEnumValue(record, 'level') !== null"
                      :color="enumStore.colors[getBoundCaseEnumValue(record, 'level')]"
                      size="small"
                    >
                      {{
                        getEnumTitle(enumStore.case_level, getBoundCaseEnumValue(record, 'level'))
                      }}
                    </a-tag>
                    <span v-else>-</span>
                  </template>
                  <template v-else-if="item.key === 'api_case_version'" #cell="{ record }">
                    <a-tag v-if="Number(record.type) === 1" color="green" size="small">
                      当前已发布
                    </a-tag>
                    <span v-else>-</span>
                  </template>
                  <template v-else-if="item.key === 'actions'" #cell="{ record }">
                    <MangoTableActions
                      :actions="[{ permission: 'timing.tasks:delete', label: '删除', danger: true, onClick: () => onDelete(record) }]"
                    />
                  </template>
                </a-table-column>
              </template>
              </a-table>
            </StickyHorizontalTable>
            <TableFooter
              class="mango-timing-case-footer"
              :pagination="pagination"
            />
          </div>
        </section>
      </div>
      </div>
      <section
        v-else-if="taskConfig"
        class="mango-section-card mango-timing-case-rule-result"
      >
        <div class="mango-section-title">
          <div>
            <h3>规则匹配用例</h3>
            <p>当前列表根据任务保存的项目产品、模块、用例类型、测试场景和发布状态实时计算，仅供查看。</p>
          </div>
        </div>
        <div class="mango-soft-panel mango-timing-case-rule-filter">
          <a-form :model="ruleFilter" layout="inline" @keyup.enter="loadRuleCases">
            <a-form-item label="ID">
              <a-input v-model="ruleFilter.caseId" allow-clear placeholder="请输入用例ID" @clear="loadRuleCases" />
            </a-form-item>
            <a-form-item label="名称">
              <a-input v-model="ruleFilter.caseName" allow-clear placeholder="请输入用例名称" @blur="loadRuleCases" @clear="loadRuleCases" />
            </a-form-item>
            <a-form-item label="用例类型">
              <a-select
                v-model="ruleFilter.caseTypes"
                :field-names="fieldNames"
                :options="taskCaseTypeOptions"
                multiple
                allow-clear
                placeholder="全部类型"
                @change="loadRuleCases"
              />
            </a-form-item>
            <a-form-item label="模块">
              <ProductModuleSelect
                v-model="ruleFilter.moduleId"
                :auto-clear="false"
                :check-strictly="true"
                :selectable-level="0"
                :project-product-id="taskConfig?.project_product?.id"
                placeholder="全部模块"
                @change="loadRuleCases"
              />
            </a-form-item>
            <a-form-item label="执行场景">
              <a-select
                v-model="ruleFilter.scenarioTags"
                :field-names="fieldNames"
                :options="enumStore.api_case_scenario_tag"
                multiple
                allow-clear
                placeholder="全部标签"
                @change="loadRuleCases"
              />
            </a-form-item>
          </a-form>
        </div>
        <div class="mango-timing-case-rule-summary">
          <a-tag size="small">总数 {{ ruleSummary.selected_count || 0 }}</a-tag>
          <a-tag size="small">{{ executionScopeName }}</a-tag>
          <a-tag size="small">{{ executionSceneName }}</a-tag>
        </div>
        <div class="mango-timing-case-rule-table">
          <a-table
            :data="ruleCases"
            :loading="ruleLoading"
            :pagination="false"
            row-key="case_id"
            size="small"
            :scroll="{ x: 1180 }"
          >
            <template #columns>
              <a-table-column title="ID" data-index="case_id" :width="100" align="center" />
              <a-table-column title="用例名称" data-index="case_name" :width="260" :ellipsis="true" :tooltip="true" />
              <a-table-column title="用例类型" data-index="case_type" :width="120" align="center">
                <template #cell="{ record }">
                  <a-tag :color="enumStore.colors[record.case_type]" size="small">
                    {{ getEnumTitle(enumStore.test_case_type, record.case_type) }}
                  </a-tag>
                </template>
              </a-table-column>
              <a-table-column title="模块" data-index="module_full_path" :width="300" :ellipsis="true" :tooltip="true" />
              <a-table-column title="执行场景" data-index="scenario_tags" :width="300">
                <template #cell="{ record }">
                  <a-space :size="4" wrap>
                    <a-tag v-for="tag in record.scenario_tags || []" :key="tag" size="small">
                      {{ getEnumTitle(enumStore.api_case_scenario_tag, tag) }}
                    </a-tag>
                  </a-space>
                </template>
              </a-table-column>
              <a-table-column title="发布状态" data-index="publication_status" :width="110" align="center">
                <template #cell><a-tag color="green" size="small">已发布</a-tag></template>
              </a-table-column>
            </template>
          </a-table>
        </div>
        <TableFooter class="mango-timing-case-footer" :pagination="rulePagination" />
      </section>
      <div v-else class="mango-section-card mango-timing-case-initial-loading">
        <a-empty description="定时任务不存在或无权查看" />
      </div>
    </template>
  </TableBody>
</template>

<script lang="ts" setup>
  import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import { useRoute } from 'vue-router'
  import { fieldNames } from '@/setting'
  import { scaleDensityLength } from '@/hooks/useDisplayDensity'
  import { usePagination, useRowKey, useRowSelection, useTable } from '@/hooks/table'
  import { candidateExecutionVersionOptions, tableColumns } from './config'
  import type { CandidateExecutionVersion } from './config'
  import {
    deleteSystemTasksRunCase,
    getSystemTasksRunCase,
    getSystemTasksTypeCaseName,
    postSystemTasksRunCase,
  } from '@/api/system/tasks_details'
  import { useEnum } from '@/store/modules/get-enum'
  import { getPytestProductName } from '@/api/pytest/product'
  import { getUserName } from '@/api/user/user'
  import TableBody from '@/components/table/TableBody.vue'
  import TableFooter from '@/components/table/TableFooter.vue'
  import StickyHorizontalTable from '@/components/table/StickyHorizontalTable.vue'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import type { ApiCaseTaskCandidate } from '@/types/api-test/case-version'
  import { formatModulePath, formatProjectProductPath } from '@/utils/business-format'
  import {
    getSystemTasks,
    getSystemTaskSelectionCases,
    type ScheduledTaskRuleCase,
  } from '@/api/system/tasks'

  type CandidateCase = Partial<ApiCaseTaskCandidate> & {
    key: string | number
    title: string
    module?: { id: number; name: string; full_path: string } | null
  }

  const enumStore = useEnum()
  const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection()
  const table = useTable()
  const pagination = usePagination(doRefresh, () => table.tableLoading)
  const candidatePagination = usePagination(() => loadCandidateCases(false), () => candidateLoading)
  const rowKey = useRowKey('id')
  const route = useRoute()
  const props = withDefaults(
    defineProps<{
      embedded?: boolean
      taskId?: string | number
      taskName?: string
      taskType?: string | number
      projectProductId?: string | number
      moduleId?: string | number
    }>(),
    {
      embedded: false,
      taskId: '',
      taskName: '',
      taskType: 1,
      projectProductId: '',
      moduleId: '',
    }
  )
  const emit = defineEmits<{
    (e: 'close'): void
  }>()
  const currentTaskId = computed(() => props.taskId || route.query.id || '')
  const currentTaskName = computed(() => props.taskName || String(route.query.name || ''))
  const currentTaskType = computed(() =>
    props.embedded ? props.taskType ?? null : route.query.type ?? null
  )
  const taskConfig = ref<any>(null)
  const taskConfigLoading = ref(true)
  const configuredCaseTypes = computed<number[]>(() => taskConfig.value?.case_types || [])
  const fixedTaskType = computed(() => {
    if (configuredCaseTypes.value.length === 1) return Number(configuredCaseTypes.value[0])
    if (currentTaskType.value === null || currentTaskType.value === '') return null
    return Number(currentTaskType.value)
  })
  const taskCaseTypeOptions = computed(() =>
    (enumStore.test_case_type || []).map((item) => ({
      ...item,
      disabled:
        [3, 4].includes(Number(item.key)) ||
        (configuredCaseTypes.value.length > 0 && !configuredCaseTypes.value.includes(Number(item.key))),
    }))
  )
  const isManualScope = computed(() => taskConfig.value?.execution_scope === 'manual')
  const hasFixedTaskModule = computed(() => Boolean(taskConfig.value?.module?.id))
  const executionScopeName = computed(() =>
    optionTitle(enumStore.automation_execution_scope, taskConfig.value?.execution_scope)
  )
  const executionSceneName = computed(() => {
    const scenes = taskConfig.value?.execution_scenes || []
    return scenes.length
      ? scenes.map((scene: string) => optionTitle(enumStore.api_case_scenario_tag, scene)).join('、')
      : '未分类'
  })
  const currentProjectProductId = computed(
    () => props.projectProductId || route.query.project_product_id || ''
  )
  const currentModuleId = computed(() => props.moduleId || route.query.module_id || '')

  const addForm = reactive({
    type: fixedTaskType.value ?? 1,
    projectProduct: currentProjectProductId.value,
    module: currentModuleId.value,
    caseName: '',
    levels: [] as Array<number | string>,
    scenarioLayers: [] as Array<number | string>,
    scenarioTypes: [] as Array<number | string>,
    scenarioTags: [] as string[],
    executionVersions: [] as CandidateExecutionVersion[],
  })
  const data: any = reactive({
    boundModuleList: [],
    nickname: [],
  })
  const ruleCases = ref<ScheduledTaskRuleCase[]>([])
  const ruleLoading = ref(false)
  const ruleSummary = ref<Record<string, any>>({})
  const ruleFilter = reactive({
    caseId: '',
    caseName: '',
    caseTypes: [] as number[],
    moduleId: '' as string | number,
    scenarioTags: [] as string[],
  })
  const rulePagination = usePagination(loadRuleCases, () => ruleLoading)
  const candidateCases = ref<CandidateCase[]>([])
  const addSelectionKeys = ref<Array<string | number>>([])
  const candidateLoading = ref(false)
  let candidateRequestId = 0
  let boundCaseKeysRequestId = 0
  const boundCaseKeysLoading = ref(false)
  const boundCaseKeySet = ref<Set<string>>(new Set())
  const addLoading = ref(false)
  const deleteLoading = ref(false)
  const boundFilter = reactive({
    type: '',
    projectProduct: '',
    module: '',
    casePeople: '',
    caseName: '',
  })
  const candidateColumns = [
    { title: '', dataIndex: 'selected', width: 54 },
    { title: '用例名称', dataIndex: 'title' },
    { title: '状态', dataIndex: 'status', width: 86 },
  ]

  const taskCaseDetailTitle = computed(() => {
    const id = currentTaskId.value || '-'
    const name = taskConfig.value?.name || currentTaskName.value || '-'
    return `定时任务用例配置 / ${id} / ${name}`
  })
  const isBoundPytestCaseType = computed(() => Number(boundFilter.type) === 2)
  const isApiCaseType = computed(() => Number(addForm.type) === 1)
  const filteredCandidateCases = computed(() => {
    if (!isApiCaseType.value || addForm.executionVersions.length === 0) {
      return candidateCases.value
    }
    return candidateCases.value.filter((item) =>
      addForm.executionVersions.includes(item.published_release_id ? 'published' : 'unpublished')
    )
  })
  const pagedCandidateCases = computed(() => {
    const start = (candidatePagination.page - 1) * candidatePagination.pageSize
    return filteredCandidateCases.value.slice(start, start + candidatePagination.pageSize)
  })
  const selectableCandidateCases = computed(() =>
    filteredCandidateCases.value.filter((item) => isCandidateSelectable(item))
  )
  const candidateAllChecked = computed(() => {
    if (selectableCandidateCases.value.length === 0) return false
    return selectableCandidateCases.value.every((item) => addSelectionKeys.value.includes(item.key))
  })
  const candidateAllCheckedIndeterminate = computed(() => {
    const selectedCount = selectableCandidateCases.value.filter((item) =>
      addSelectionKeys.value.includes(item.key)
    ).length
    return selectedCount > 0 && selectedCount < selectableCandidateCases.value.length
  })
  const boundStats = computed(() => {
    return table.dataList.reduce(
      (acc: any, item: any) => {
        acc.total += 1
        if (Number(item.type) === 0) acc.ui += 1
        if (Number(item.type) === 1) acc.api += 1
        if (Number(item.type) === 2) acc.pytest += 1
        return acc
      },
      { total: 0, ui: 0, api: 0, pytest: 0 }
    )
  })
  watch(
    () => filteredCandidateCases.value.length,
    (total) => {
      candidatePagination.setTotalSize(total)
      const maxPage = Math.max(1, Math.ceil(total / candidatePagination.pageSize))
      if (candidatePagination.page > maxPage) {
        candidatePagination.page = maxPage
      }
    },
    { immediate: true }
  )

  watch(
    () => candidatePagination.pageSize,
    () => {
      candidatePagination.page = 1
    }
  )

  function getBoundCaseName(record: any) {
    return record.ui_case?.name || record.api_case?.name || record.pytest_case?.name || '-'
  }

  function getLeafValue(value: any) {
    if (Array.isArray(value)) {
      return value[value.length - 1] ?? ''
    }
    return value || ''
  }

  function getBoundCase(record: any) {
    return record.ui_case || record.api_case || record.pytest_case || {}
  }

  function getBoundCaseId(record: any) {
    return record.ui_case?.id || record.api_case?.id || record.pytest_case?.id || ''
  }

  function getBoundCaseProjectProduct(record: any) {
    const caseInfo = getBoundCase(record)
    const projectProductPath = formatProjectProductPath(caseInfo.project_product)
    return (
      (projectProductPath !== '-' ? projectProductPath : '') ||
      caseInfo.project_product_name ||
      caseInfo.project?.name ||
      caseInfo.product?.name ||
      '-'
    )
  }

  function getBoundCaseModule(record: any) {
    const caseInfo = getBoundCase(record)
    const modulePath = formatModulePath(caseInfo.module)
    return modulePath !== '-' ? modulePath : caseInfo.module_name || '-'
  }

  function getBoundCaseOwner(record: any) {
    const caseInfo = getBoundCase(record)
    return (
      caseInfo.case_people?.name ||
      caseInfo.case_people_name ||
      caseInfo.user?.name ||
      caseInfo.create_user?.name ||
      '-'
    )
  }

  function getBoundCaseEnumValue(record: any, key: string) {
    const caseInfo = getBoundCase(record)
    const value = caseInfo[key]
    return value === undefined || value === null || value === '' ? null : value
  }

  function getBoundCaseTags(record: any) {
    const tags = getBoundCase(record).scenario_tags
    return Array.isArray(tags) ? tags : []
  }

  function getEnumTitle(options: any[], value: any) {
    return options?.find((item: any) => String(item.key) === String(value))?.title || '-'
  }

  function optionTitle(options: any[], value: any) {
    return options?.find((item: any) => String(item.key) === String(value))?.title || '-'
  }

  function selectedFilterText(
    values: Array<string | number>,
    options: Array<{ key?: string | number; value?: string | number; title?: string; label?: string }> = []
  ) {
    return values.map((value) => {
      const option = options.find((item) => String(item.key ?? item.value) === String(value))
      return option?.title ?? option?.label ?? String(value)
    }).join('、')
  }

  const candidateFilterTriggerProps = computed(() => ({
    autoFitPopupWidth: false,
    autoFitPopupMinWidth: false,
    popupStyle: { minWidth: scaleDensityLength('220px') },
  }))

  function isCaseBound(caseId: string | number) {
    return boundCaseKeySet.value.has(String(caseId))
  }

  function isCandidateSelectable(item: CandidateCase) {
    if (boundCaseKeysLoading.value) return false
    if (isCaseBound(item.key)) return false
    if (!isApiCaseType.value) return true
    return Boolean(item.published_release_id)
  }

  function toggleCandidateCase(caseId: string | number, checked: boolean) {
    const candidate = candidateCases.value.find((item) => item.key === caseId)
    if (!candidate || !isCandidateSelectable(candidate)) return
    if (checked) {
      if (!addSelectionKeys.value.includes(caseId)) addSelectionKeys.value.push(caseId)
      return
    }
    addSelectionKeys.value = addSelectionKeys.value.filter((item) => item !== caseId)
  }

  function toggleAllCandidateCases(checked: boolean) {
    const selectableKeys = selectableCandidateCases.value.map((item) => item.key)
    if (checked) {
      addSelectionKeys.value = Array.from(new Set([...addSelectionKeys.value, ...selectableKeys]))
      return
    }
    addSelectionKeys.value = addSelectionKeys.value.filter((item) => !selectableKeys.includes(item))
  }

  function clearCandidateCases() {
    candidateCases.value = []
    addSelectionKeys.value = []
    candidatePagination.page = 1
  }

  function onProjectProductChange() {
    addForm.module = ''
    clearCandidateCases()
    loadCandidateCases()
  }

  function onBoundFilterChange() {
    pagination.page = 1
    selectedRowKeys.value = []
    doRefresh()
  }

  function onBoundTypeChange(value: number | string) {
    boundFilter.type = value as any
    boundFilter.module = ''
    data.boundModuleList = []
    if (Number(value) === 2) {
      loadBoundPytestModules(boundFilter.projectProduct)
    }
    onBoundFilterChange()
  }

  function onBoundProjectProductChange(value: any) {
    boundFilter.projectProduct = value
    boundFilter.module = ''
    data.boundModuleList = []
    if (isBoundPytestCaseType.value) {
      loadBoundPytestModules(value)
    }
    onBoundFilterChange()
  }

  function changeType(value: number) {
    addForm.type = value
    addForm.executionVersions = []
    clearCandidateCases()
    loadBoundCaseKeys()
    loadCandidateCases()
  }

  function onExecutionVersionFilterChange() {
    candidatePagination.page = 1
    addSelectionKeys.value = []
  }

  function loadCandidateCases(resetPage = true) {
    const requestId = ++candidateRequestId
    if (resetPage) {
      clearCandidateCases()
    }
    const projectProductId = getLeafValue(addForm.projectProduct || currentProjectProductId.value)
    const moduleId = getLeafValue(addForm.module)
    if (!moduleId && !projectProductId) {
      candidateLoading.value = false
      return
    }
    candidateLoading.value = true
    return getSystemTasksTypeCaseName(
      addForm.type,
      moduleId || undefined,
      projectProductId || undefined,
      undefined,
      {
        case_name: addForm.caseName || undefined,
        levels: addForm.levels?.join(','),
        scenario_layers: addForm.scenarioLayers?.join(','),
        scenario_types: addForm.scenarioTypes?.join(','),
        scenario_tags: addForm.scenarioTags?.join(','),
      },
      currentTaskId.value
    )
      .then((res) => {
        if (requestId !== candidateRequestId) return
        candidateCases.value = res.data || []
      })
      .catch(console.log)
      .finally(() => {
        if (requestId !== candidateRequestId) return
        candidateLoading.value = false
      })
  }

  function loadBoundCaseKeys() {
    const requestId = ++boundCaseKeysRequestId
    if (!currentTaskId.value) {
      boundCaseKeySet.value = new Set()
      boundCaseKeysLoading.value = false
      return Promise.resolve()
    }
    boundCaseKeysLoading.value = true
    return getSystemTasksRunCase({
      task_id: currentTaskId.value,
      type: addForm.type,
      case_ids_only: 1,
    })
      .then((res) => {
        if (requestId !== boundCaseKeysRequestId) return
        boundCaseKeySet.value = new Set(
          (res.data || []).map((item: any) => String(item.case_id))
        )
      })
      .catch(console.log)
      .finally(() => {
        if (requestId !== boundCaseKeysRequestId) return
        boundCaseKeysLoading.value = false
      })
  }

  function onAddSelectedCases() {
    if (addSelectionKeys.value.length === 0) {
      Message.error('请选择要添加的用例')
      return
    }
    const typeList = ['ui_case', 'api_case', 'pytest_case']
    const payload: any = {
      type: addForm.type,
      task: currentTaskId.value,
    }
    if (isApiCaseType.value) {
      const selectedKeys = new Set(addSelectionKeys.value.map(String))
      const selectedCases = candidateCases.value.filter((item) =>
        selectedKeys.has(String(item.key))
      )
      if (selectedCases.some((item) => !item.published_release_id)) {
        Message.warning('存在未发布的用例，请刷新后重新选择')
        return
      }
      payload.api_case = selectedCases.map((item) => item.key)
      submitSelectedCases(payload)
      return
    }
    payload[typeList[Number(addForm.type)]] = addSelectionKeys.value
    submitSelectedCases(payload)
  }

  function submitSelectedCases(payload: Record<string, unknown>) {
    addLoading.value = true
    return postSystemTasksRunCase(payload)
      .then((res) => {
        Message.success(bindingResultMessage(res))
        addSelectionKeys.value = []
        loadBoundCaseKeys()
        doRefresh()
      })
      .catch(console.log)
      .finally(() => {
        addLoading.value = false
      })
  }

  function bindingResultMessage(res: any) {
    const result = res.data
    if (!result || typeof result.created_count !== 'number') return res.msg
    return `${res.msg}：新增 ${result.created_count} 条，更新 ${result.updated_count} 条，已添加跳过 ${result.skipped_count} 条`
  }

  function onDelete(record: any) {
    const batch = record === null
    if (batch && selectedRowKeys.value.length === 0) {
      Message.error('请选择要删除的数据')
      return
    }
    Modal.confirm({
      title: '提示',
      content: batch ? '是否要删除选中的定时任务用例？' : '是否要删除此定时任务用例？',
      cancelText: '取消',
      okText: '删除',
      onBeforeOk: () => {
        deleteLoading.value = batch
        return deleteSystemTasksRunCase(batch ? selectedRowKeys.value : record.id)
          .then((res) => {
            Message.success(res.msg)
          })
          .catch(console.log)
          .finally(() => {
            loadBoundCaseKeys()
            doRefresh()
            deleteLoading.value = false
            if (batch) selectedRowKeys.value = []
          })
      },
    })
  }

  function doResetSearch() {
    if (props.embedded) {
      emit('close')
      return
    }
    window.history.back()
  }

  function doRefresh() {
    table.tableLoading.value = true
    const projectProductId = getLeafValue(boundFilter.projectProduct)
    const moduleId = getLeafValue(boundFilter.module)
    const boundType =
      boundFilter.type === '' || boundFilter.type === null ? undefined : boundFilter.type
    getSystemTasksRunCase({
      task_id: currentTaskId.value,
      type: boundType,
      project_product_id: projectProductId || undefined,
      module_id: moduleId || undefined,
      case_people_id: boundFilter.casePeople || undefined,
      case_name: boundFilter.caseName || undefined,
      page: pagination.page,
      pageSize: pagination.pageSize,
    })
      .then((res) => {
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
      })
      .catch((error) => {
        table.tableLoading.value = false
        console.log(error)
      })
  }

  function loadBoundPytestModules(projectProductId: any) {
    const productId = getLeafValue(projectProductId)
    if (!productId) return
    getPytestProductName(productId)
      .then((res) => {
        data.boundModuleList = res.data
      })
      .catch(console.log)
  }

  function getNickName() {
    getUserName()
      .then((res) => {
        data.nickname = res.data
      })
      .catch(console.log)
  }

  async function loadTaskConfig() {
    taskConfigLoading.value = true
    try {
      if (!currentTaskId.value) return
      const res = await getSystemTasks({ id: currentTaskId.value, page: 1, pageSize: 1 })
      const responseData: any = res.data
      const record = Array.isArray(responseData)
        ? responseData[0]
        : Array.isArray(responseData?.items)
          ? responseData.items[0]
          : responseData
      if (!record) {
        Message.error('定时任务不存在或无权查看')
        return
      }
      taskConfig.value = record
      addForm.projectProduct = record.project_product?.id || record.project_product || ''
      addForm.module = record.module?.id || record.module || ''
      const allowedTypes = Array.isArray(record.case_types) ? record.case_types : []
      if (allowedTypes.length && !allowedTypes.includes(Number(addForm.type))) {
        addForm.type = Number(allowedTypes[0])
      }
      boundFilter.projectProduct = addForm.projectProduct
      boundFilter.module = addForm.module
    } finally {
      taskConfigLoading.value = false
    }
  }

  async function loadRuleCases() {
    if (!currentTaskId.value || isManualScope.value) return
    ruleLoading.value = true
    try {
      const res = await getSystemTaskSelectionCases({
        task_id: currentTaskId.value,
        case_id: ruleFilter.caseId || undefined,
        case_name: ruleFilter.caseName || undefined,
        case_types: ruleFilter.caseTypes.length ? ruleFilter.caseTypes.join(',') : undefined,
        module_id: getLeafValue(ruleFilter.moduleId) || undefined,
        scenario_tags: ruleFilter.scenarioTags.length
          ? ruleFilter.scenarioTags.join(',')
          : undefined,
        page: rulePagination.page,
        pageSize: rulePagination.pageSize,
      })
      ruleCases.value = res.data?.items || []
      ruleSummary.value = res.data?.summary || {}
      rulePagination.setTotalSize(res.data?.count || 0)
    } catch (error: any) {
      Message.error(error?.msg || '查询规则匹配用例失败')
    } finally {
      ruleLoading.value = false
    }
  }

  onMounted(() => {
    nextTick(async () => {
      await enumStore.getEnum()
      await loadTaskConfig()
      if (!taskConfig.value) return
      if (isManualScope.value) {
        loadBoundCaseKeys()
        doRefresh()
        getNickName()
        loadCandidateCases()
      } else {
        loadRuleCases()
      }
    })
  })
</script>

<style lang="less" scoped>
  .mango-timing-case-initial-loading {
    display: flex;
    min-height: 240px;
    align-items: center;
    justify-content: center;
  }

  .mango-timing-case-workbench {
    display: grid;
    height: 100%;
    min-height: 0;
    grid-template-columns: minmax(420px, 0.9fr) minmax(0, 1.35fr);
    gap: var(--m-page-gap);
    align-items: stretch;
  }

  .mango-timing-case-workbench-scroll {
    --mango-workbench-min-width: 980px;
    height: calc(100% - var(--m-page-gap));
    margin-top: var(--m-page-gap);
  }

  .mango-timing-case-workbench-scroll > .mango-timing-case-workbench {
    min-width: var(--mango-workbench-min-width);
  }

  .mango-timing-case-workbench > .mango-section-card + .mango-section-card {
    margin-top: 0;
  }

  .mango-timing-case-picker,
  .mango-timing-case-bound {
    display: flex;
    min-width: 0;
    min-height: 0;
    flex-direction: column;
    overflow: hidden;
  }

  .mango-timing-case-table {
    min-height: 0;
  }

  .mango-timing-case-candidate-table {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
    min-height: 0;
  }

  .mango-timing-case-bound-table {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
    min-height: 0;
  }

  .mango-timing-case-footer {
    flex: 0 0 42px;
    margin-top: 8px;
  }

  .mango-timing-case-footer.mango-table-mango-footer-container {
    height: 42px;
  }

  .mango-timing-case-picker > .mango-section-title,
  .mango-timing-case-bound > .mango-section-title {
    min-height: 42px;
    align-items: center;
    margin-bottom: 6px;
  }

  .mango-timing-case-picker > .mango-section-title h3,
  .mango-timing-case-bound > .mango-section-title h3 {
    margin: 0;
    color: var(--m-text);
    font-size: 15px;
    font-weight: 600;
    line-height: 20px;
  }

  .mango-timing-case-picker > .mango-section-title p,
  .mango-timing-case-bound > .mango-section-title p {
    margin: 2px 0 0;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 17px;
  }

  .mango-timing-case-filter {
    margin-bottom: 10px;
    padding: 10px 10px 0;
  }

  .mango-timing-case-selector-tooltip {
    width: 100%;
    min-width: 0;
  }

  .mango-timing-case-filter :deep(.arco-form) {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0 12px;
  }

  .mango-timing-case-filter :deep(.arco-form-item) {
    display: flex;
    min-width: 0;
    align-items: center;
    margin-bottom: 10px;
  }

  .mango-timing-case-filter :deep(.arco-form-item-label-col) {
    flex: 0 0 78px;
    width: 78px;
    min-width: 78px;
    padding-right: 8px;
    text-align: right;
  }

  .mango-timing-case-filter :deep(.arco-form-item-label) {
    justify-content: flex-end;
  }

  .mango-timing-case-filter :deep(.arco-form-item-wrapper-col) {
    flex: 1;
    min-width: 0;
  }

  .mango-timing-case-filter :deep(.arco-select-view-inner.arco-select-view-nowrap) {
    flex-wrap: nowrap;
    align-items: center;
    min-width: 0;
  }

  .mango-timing-case-filter :deep(.arco-select-view-tag) {
    flex: 1 1 0;
    min-width: 0;
    max-width: 100%;
    white-space: nowrap;
  }

  .mango-timing-case-filter :deep(.arco-select-view-tag:not(:first-child)) {
    flex: 0 0 auto;
    margin-right: 0;
    padding-inline: 4px;
  }

  .mango-timing-case-filter :deep(.arco-select-view-tag:first-child) {
    min-width: 36px;
  }

  .mango-timing-case-filter :deep(.arco-tag-text) {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-timing-case-filter :deep(.arco-tag-close-btn) {
    flex-shrink: 0;
  }

  .mango-timing-case-filter :deep(.arco-select-view-input) {
    min-width: 0;
    flex: 0 1 auto;
  }

  .mango-timing-case-filter :deep(.arco-select-view-has-tag:not(.arco-select-view-focus) .arco-select-view-input) {
    width: 0;
    flex: 0 0 0;
  }

  .mango-timing-case-list-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
    color: var(--m-text-2);
    font-size: 13px;
  }

  .mango-timing-case-list-head small {
    color: var(--m-muted);
    font-size: 12px;
  }

  .mango-timing-case-bound-filter {
    margin-bottom: 10px;
    padding: 10px 10px 0;
  }

  .mango-timing-case-bound-filter :deep(.arco-form) {
    display: grid;
    grid-template-columns: repeat(5, minmax(120px, 1fr));
    gap: 0 10px;
  }

  .mango-timing-case-bound-filter :deep(.arco-form-item) {
    margin-bottom: 10px;
  }

  .mango-timing-case-summary {
    display: flex;
    flex-wrap: nowrap;
    justify-content: flex-end;
    gap: 4px;
  }

  .mango-timing-case-bound-actions {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    flex-wrap: nowrap;
    gap: 6px;
  }

  .mango-timing-case-rule-result {
    display: flex;
    height: calc(100% - var(--m-page-gap));
    min-height: 0;
    margin-top: var(--m-page-gap);
    flex-direction: column;
    overflow: hidden;
  }

  .mango-timing-case-rule-filter {
    margin-bottom: var(--m-page-gap);
    padding: 8px 10px 0;
  }

  .mango-timing-case-rule-summary {
    display: flex;
    margin-bottom: var(--m-page-gap);
    gap: 6px;
  }

  .mango-timing-case-rule-table {
    min-height: 0;
    flex: 1;
    overflow: auto;
  }

  .mango-timing-case-summary span {
    padding: 2px 6px;
    border: 1px solid var(--m-border);
    border-radius: 999px;
    background: var(--m-surface-soft);
    color: var(--m-text-2);
    font-size: 12px;
    line-height: 17px;
  }

  @media (max-width: 1380px) {
    .mango-timing-case-workbench {
      grid-template-columns: minmax(360px, 0.82fr) minmax(0, 1.28fr);
    }

    .mango-timing-case-filter :deep(.arco-form) {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .mango-timing-case-bound-filter :deep(.arco-form) {
      grid-template-columns: repeat(3, minmax(120px, 1fr));
    }
  }

  @media (max-width: 1120px) {
    .mango-timing-case-workbench {
      grid-template-columns: minmax(0, 1fr);
    }

    .mango-timing-case-filter :deep(.arco-form),
    .mango-timing-case-bound-filter :deep(.arco-form) {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }
</style>
