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
                  ? '维护当前定时任务绑定的执行用例'
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
      
      
      <div v-if="taskConfigLoading && !taskConfig" class="mango-section-card mango-timing-case-initial-loading">
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
            <a-button
              size="small"
              type="primary"
              :disabled="addSelectionKeys.length === 0 || writeBusy || candidateLoading || !!candidateError || !!boundCaseKeysError"
              :loading="addLoading"
              @click="onAddSelectedCases" data-testid="qa-views-timing-tasks-case-button-添加选中"
            >
              添加选中 {{ addSelectionKeys.length }}
            </a-button>
          </div>

          
          
          <MangoRequestFeedback v-if="bindingError" :message="(bindingError)" />

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
                        :color="record.published_release_id != null ? 'green' : 'gray'"
                        size="small"
                      >
                        {{ record.published_release_id != null ? '当前已发布' : '暂无已发布版本' }}
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
              <p>支持搜索、单个删除和批量删除</p>
            </div>
            <div class="mango-timing-case-bound-actions">
              <div class="mango-timing-case-summary">
                <span>总数 {{ boundStats.total }}</span>
                <span>UI {{ boundStats.ui }}</span>
                <span>API {{ boundStats.api }}</span>
                <span>Pytest {{ boundStats.pytest }}</span>
              </div>
              <a-button
                size="small"
                status="danger"
                :loading="deleteLoading"
                :disabled="writeBusy || selectedRowKeys.length === 0"
                @click="onDelete(null)" data-testid="qa-views-timing-tasks-case-button-批量删除"
              >
                批量删除
              </a-button>
            </div>
          </div>

          
          
          
          <MangoRequestFeedback v-if="deletionError" :message="(deletionError)" />

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
                  :options="boundModuleOptions"
                  :loading="boundModuleLoading"
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
                  :options="ownerOptions"
                  :loading="ownerLoading"
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
                :data="boundRows"
                :loading="boundLoading"
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
                      :actions="[{ label: '删除', danger: true, disabled: writeBusy, loading: deletingIds.includes(String(record.id)), onClick: () => onDelete(record) }]"
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
        <MangoRequestFeedback v-if="ruleError" :message="(ruleError)"><a-button type="text" size="small" @click="loadRuleCases()">重试</a-button></MangoRequestFeedback>
        <div class="mango-soft-panel mango-timing-case-rule-filter">
          <a-form :model="ruleFilter" layout="inline" @keyup.enter="autoSearch.run">
            <a-form-item label="ID">
              <a-input @blur="autoSearch.schedule" @mouseleave="autoSearch.schedule" v-model="ruleFilter.caseId" allow-clear placeholder="请输入用例ID" @clear="autoSearch.schedule" />
            </a-form-item>
            <a-form-item label="名称">
              <a-input @mouseleave="autoSearch.schedule" v-model="ruleFilter.caseName" allow-clear placeholder="请输入用例名称" @blur="autoSearch.schedule" @clear="autoSearch.schedule" />
            </a-form-item>
            <a-form-item label="用例类型">
              <a-select
                v-model="ruleFilter.caseTypes"
                :field-names="fieldNames"
                :options="taskCaseTypeOptions"
                multiple
                tag-nowrap
                :max-tag-count="1"
                allow-clear
                placeholder="全部类型"
                @change="autoSearch.schedule"
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
                @change="autoSearch.schedule"
              />
            </a-form-item>
            <a-form-item label="执行场景">
              <a-select
                v-model="ruleFilter.scenarioTags"
                :field-names="fieldNames"
                :options="enumStore.api_case_scenario_tag"
                multiple
                tag-nowrap
                :max-tag-count="1"
                allow-clear
                placeholder="全部标签"
                @change="autoSearch.schedule"
              />
            </a-form-item>
          </a-form>
        </div>
        <div class="mango-timing-case-rule-summary">
          <a-tag size="small">总数 {{ ruleSelectedCount }}</a-tag>
          <a-tag size="small">{{ executionScopeName }}</a-tag>
          <a-tag size="small">{{ executionSceneName }}</a-tag>
        </div>
        <div class="mango-timing-case-rule-table">
          <a-table
            :data="ruleCases"
            :loading="ruleLoading"
            :pagination="false"
            row-key="row_key"
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
        <div class="mango-empty-state">
          <MangoRequestFeedback  :message="taskConfigError" />
          <a-button size="small" :loading="taskConfigLoading" @click="initializeTaskCases">重试</a-button>
        </div>
      </div>
    </template>
  </TableBody>
</template>

<script lang="ts" setup>
  import { useDebouncedSearch } from '@/hooks/useDebouncedSearch'

  import { requestFailureMessage, reportLoadError } from '@/utils/load-error'
  import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, reactive, ref, watch } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import { useRoute } from 'vue-router'
  import useUserStore from '@/store/modules/user'
  import usePermissionStore from '@/store/modules/permission'
  import { fieldNames } from '@/setting'
  import { scaleDensityLength } from '@/hooks/useDisplayDensity'
  import { usePagination, useRowKey, useRowSelection } from '@/hooks/table'
  import { candidateColumns, candidateExecutionVersionOptions, tableColumns } from './config'
  import type { CandidateExecutionVersion } from './config'
  import { parseTaskCaseConfig, type TaskCaseConfig, type TaskCaseId } from './task-config'
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
  import { formatModulePath, formatProjectProductPath } from '@/utils/business-format'
  import { getSystemTasks } from '@/api/system/tasks'
  import { parseBoundCases, parseBoundCaseKeys, parseCandidateCases, parseTaskCaseOptions, taskCaseLeaf, taskCaseSuccessMessage,
    type BoundCaseRecord, type CandidateCase, type TaskCaseOption } from './case-records'
  import { useRuleCaseSelection } from './composables/useRuleCaseSelection'

  const enumStore = useEnum()
  const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection()
  const boundRows = ref<BoundCaseRecord[]>([])
  const boundLoading = ref(false)
  const boundError = ref('')
  const pagination = usePagination(doRefresh, boundLoading)
  const candidatePageChanging = ref(false)
  const candidatePagination = usePagination(() => { candidatePageChanging.value = false }, candidatePageChanging)
  const rowKey = useRowKey('id')
  const route = useRoute()
  const user = useUserStore(), permission = usePermissionStore(), pagePath = route.path
  let mounted = false, active = true, disposed = false, contextVersion = 0, needsReload = true
  let pendingInitialization: Promise<void> | null = null
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
  const currentTaskId = computed(() => {
    if (props.taskId !== '') return props.taskId
    const queryId = route.query.id
    return (Array.isArray(queryId) ? queryId[0] : queryId) ?? ''
  })
  const currentTaskName = computed(() => props.taskName || String(route.query.name || ''))
  const currentTaskType = computed(() =>
    props.embedded ? props.taskType ?? null : route.query.type ?? null
  )
  const taskConfig = ref<TaskCaseConfig | null>(null)
  const taskConfigLoading = ref(true)
  const taskConfigError = ref('')
  const enumLoading = ref(false), enumError = ref('')
  let taskConfigRequestId = 0
  let enumRequestId = 0
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
  const hasFixedTaskModule = computed(() => taskConfig.value?.module != null)
  const executionScopeName = computed(() =>
    optionTitle(enumStore.automation_execution_scope, taskConfig.value?.execution_scope)
  )
  const executionSceneName = computed(() => {
    const scenes = taskConfig.value?.execution_scenes || []
    return scenes.length
      ? scenes.map((scene: string) => optionTitle(enumStore.api_case_scenario_tag, scene)).join('、')
      : '未分类'
  })
  const currentProjectProductId = computed(() => {
    const query = route.query.project_product_id
    return props.projectProductId !== '' ? props.projectProductId : (Array.isArray(query) ? query[0] : query) ?? ''
  })
  const currentModuleId = computed(() => {
    const query = route.query.module_id
    return props.moduleId !== '' ? props.moduleId : (Array.isArray(query) ? query[0] : query) ?? ''
  })

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
  const boundModuleOptions = ref<TaskCaseOption[]>([]), ownerOptions = ref<TaskCaseOption[]>([])
  const boundModuleLoading = ref(false), ownerLoading = ref(false)
  const boundModuleError = ref(''), ownerError = ref('')
  const { ruleCases, ruleLoading, ruleError, ruleSelectedCount, ruleFilter, rulePagination, loadRuleCases,
    invalidate: invalidateRuleCases, reset: resetRuleCases } = useRuleCaseSelection({
    getTaskId: () => currentTaskId.value, isManual: () => isManualScope.value,
    available: () => available(), captureContext: () => captureContext(),
  })
  const candidateCases = ref<CandidateCase[]>([])
  const addSelectionKeys = ref<Array<string | number>>([])
  const candidateLoading = ref(false)
  const candidateError = ref(''), boundCaseKeysError = ref('')
  let candidateRequestId = 0
  let boundCaseKeysRequestId = 0
  let boundRequestId = 0, ownerRequestId = 0, moduleRequestId = 0
  const boundCaseKeysLoading = ref(false)
  const boundCaseKeySet = ref<Set<string>>(new Set())
  const addLoading = ref(false)
  const deleteLoading = ref(false)
  const deletingIds = ref<string[]>([])
  const bindingError = ref(''), deletionError = ref('')
  const writeBusy = computed(() => addLoading.value || deleteLoading.value)
  let confirmation: ReturnType<typeof Modal.confirm> | null = null, confirmationVersion = 0
  const boundFilter = reactive({
    type: '' as string | number,
    projectProduct: '' as string | number | Array<string | number>,
    module: '' as string | number | Array<string | number>,
    casePeople: '' as string | number,
    caseName: '',
  })

  const identity = () => JSON.stringify([route.path, route.fullPath, currentTaskId.value, currentTaskType.value, props.embedded,
    props.projectProductId, props.moduleId, user.userId, user.roleId, user.token, user.selected_environment, permission.permissionKeys])
  const available = () => active && !disposed && route.path === pagePath && (typeof document === 'undefined' || document.visibilityState === 'visible')
  function captureContext() {
    const key = identity(), version = contextVersion
    return () => available() && key === identity() && version === contextVersion
  }

  const taskCaseDetailTitle = computed(() => {
    const id = currentTaskId.value === '' ? '-' : currentTaskId.value
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
      addForm.executionVersions.includes(item.published_release_id != null ? 'published' : 'unpublished')
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
    return boundRows.value.reduce(
      (acc, item) => {
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

  function getBoundCaseName(record: BoundCaseRecord) {
    return record.case_name
  }

  function getLeafValue(value: unknown) {
    return taskCaseLeaf(value)
  }

  function getBoundCaseProjectProduct(record: BoundCaseRecord) {
    return record.product_path
  }

  function getBoundCaseModule(record: BoundCaseRecord) {
    return record.module_path
  }

  function getBoundCaseOwner(record: BoundCaseRecord) {
    return record.owner_name
  }

  function getBoundCaseEnumValue(record: BoundCaseRecord, key: 'scenario_layer' | 'scenario_type' | 'level') {
    return record[key]
  }

  function getBoundCaseTags(record: BoundCaseRecord) {
    return record.scenario_tags
  }

  function getEnumTitle(options: Array<{ key: string | number; title: string }> | undefined, value: unknown) {
    return options?.find(item => String(item.key) === String(value))?.title || '-'
  }

  function optionTitle(options: Array<{ key: string | number; title: string }> | undefined, value: unknown) {
    return getEnumTitle(options, value)
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
    if (writeBusy.value || candidateLoading.value || candidateError.value || boundCaseKeysLoading.value || boundCaseKeysError.value) return false
    if (isCaseBound(item.key)) return false
    if (!isApiCaseType.value) return true
    return item.published_release_id != null
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
    boundFilter.type = value ?? ''
    boundFilter.module = ''
    boundModuleOptions.value = []
    if (Number(value) === 2) {
      loadBoundPytestModules(boundFilter.projectProduct)
    }
    onBoundFilterChange()
  }

  function onBoundProjectProductChange(value: unknown) {
    boundFilter.projectProduct = getLeafValue(value)
    boundFilter.module = ''
    boundModuleOptions.value = []
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
    if (!available()) { candidateLoading.value = false; return Promise.resolve() }
    const requestId = ++candidateRequestId
    const taskId = currentTaskId.value
    const context = captureContext(), current = () => context() && requestId === candidateRequestId
    if (resetPage !== false) {
      clearCandidateCases()
    }
    const projectProductId = getLeafValue(addForm.projectProduct === '' ? currentProjectProductId.value : addForm.projectProduct)
    const moduleId = getLeafValue(addForm.module)
    if (moduleId === '' && projectProductId === '') {
      candidateLoading.value = false
      return
    }
    candidateLoading.value = true
    candidateError.value = ''
    return getSystemTasksTypeCaseName(
      addForm.type,
      moduleId === '' ? undefined : moduleId,
      projectProductId === '' ? undefined : projectProductId,
      undefined,
      {
        case_name: addForm.caseName.trim() || undefined,
        levels: addForm.levels?.join(','),
        scenario_layers: addForm.scenarioLayers?.join(','),
        scenario_types: addForm.scenarioTypes?.join(','),
        scenario_tags: addForm.scenarioTags?.join(','),
      },
      taskId
    )
      .then((res) => {
        if (!current()) return
        candidateCases.value = parseCandidateCases(res)
      })
      .catch((loadFailure0) => { if (current()) (reportLoadError(loadFailure0, "候选用例加载失败，请重试", false), candidateError.value = '候选用例加载失败，请重试') })
      .finally(() => {
        if (!current()) return
        candidateLoading.value = false
      })
  }

  function loadBoundCaseKeys() {
    if (!available()) { boundCaseKeysLoading.value = false; return Promise.resolve() }
    const requestId = ++boundCaseKeysRequestId
    const taskId = currentTaskId.value
    const context = captureContext(), current = () => context() && requestId === boundCaseKeysRequestId
    boundCaseKeysError.value = ''
    if (taskId === '') {
      boundCaseKeySet.value = new Set()
      boundCaseKeysLoading.value = false
      return Promise.resolve()
    }
    boundCaseKeysLoading.value = true
    return getSystemTasksRunCase({
      task_id: taskId,
      type: addForm.type,
      case_ids_only: 1,
    })
      .then((res) => {
        if (!current()) return
        boundCaseKeySet.value = parseBoundCaseKeys(res)
        addSelectionKeys.value = addSelectionKeys.value.filter(key => !boundCaseKeySet.value.has(String(key)))
      })
      .catch((loadFailure1) => { if (current()) (reportLoadError(loadFailure1, "已添加用例标识加载失败，请重试", false), boundCaseKeysError.value = '已添加用例标识加载失败，请重试') })
      .finally(() => {
        if (!current()) return
        boundCaseKeysLoading.value = false
      })
  }

  function onAddSelectedCases() {
    if (!available() || writeBusy.value || !isManualScope.value || currentTaskId.value === '') return
    if (addSelectionKeys.value.length === 0) {
      Message.error('请选择要添加的用例')
      return
    }
    const type = Number(addForm.type)
    if (![0, 1, 2].includes(type)) return
    const selectedKeys = new Set(addSelectionKeys.value.map(String))
    const selectedCases = candidateCases.value.filter(item => selectedKeys.has(String(item.key)))
    if (selectedCases.length !== selectedKeys.size || selectedCases.some(item => !isCandidateSelectable(item))) {
      Message.warning('选中用例已变化，请重新选择')
      return
    }
    const payload: {
      type: number; task: TaskCaseId; ui_case?: TaskCaseId[]; api_case?: TaskCaseId[]; pytest_case?: TaskCaseId[]
    } = {
      type: addForm.type,
      task: currentTaskId.value,
    }
    if (isApiCaseType.value) {
      if (selectedCases.some((item) => item.published_release_id == null)) {
        Message.warning('存在未发布的用例，请刷新后重新选择')
        return
      }
      payload.api_case = selectedCases.map((item) => item.key)
      return submitSelectedCases(payload)
    }
    if (type === 0) payload.ui_case = selectedCases.map(item => item.key)
    else payload.pytest_case = selectedCases.map(item => item.key)
    return submitSelectedCases(payload)
  }

  async function submitSelectedCases(payload: { type: number; task: TaskCaseId; ui_case?: TaskCaseId[]; api_case?: TaskCaseId[]; pytest_case?: TaskCaseId[] }) {
    if (!available() || writeBusy.value) return
    const snapshot = { ...payload }
    if (payload.ui_case) snapshot.ui_case = payload.ui_case.slice()
    if (payload.api_case) snapshot.api_case = payload.api_case.slice()
    if (payload.pytest_case) snapshot.pytest_case = payload.pytest_case.slice()
    const selectionVersion = candidateRequestId, key = identity(), current = captureContext()
    let refreshAttempted = false
    addLoading.value = true
    bindingError.value = ''
    try {
      const response = await postSystemTasksRunCase(snapshot), message = taskCaseSuccessMessage(response, true)
      if (key === identity()) needsReload = true
      if (!current()) return
      Message.success(message)
      if (selectionVersion === candidateRequestId && Number(addForm.type) === snapshot.type) addSelectionKeys.value = []
      needsReload = false; refreshAttempted = true
      await Promise.allSettled([loadBoundCaseKeys(), doRefresh()])
    } catch (requestFailure) { if (current()) bindingError.value = requestFailureMessage(requestFailure, '添加用例失败，请重试') }
    finally { addLoading.value = false; if (!refreshAttempted || !current()) resume() }
  }

  function closeConfirmation() { confirmationVersion++; confirmation?.close(); confirmation = null }

  function onDelete(record: BoundCaseRecord | null) {
    if (!available() || writeBusy.value || !isManualScope.value || currentTaskId.value === '') return
    const batch = record === null
    if (batch && selectedRowKeys.value.length === 0) {
      Message.error('请选择要删除的数据')
      return
    }
    const targetIds = batch ? selectedRowKeys.value.map(String) : [String(record.id)]
    const target = batch ? targetIds.slice() : record.id, key = identity(), context = captureContext()
    closeConfirmation()
    const version = confirmationVersion, current = () => version === confirmationVersion && context()
    confirmation = Modal.confirm({
      title: '提示',
      content: batch ? '是否要删除选中的定时任务用例？' : '是否要删除此定时任务用例？',
      cancelText: '取消',
      okText: '删除',
      onCancel: () => { if (version === confirmationVersion) closeConfirmation() },
      onBeforeOk: async () => {
        if (!current() || writeBusy.value) return false
        deleteLoading.value = true; deletingIds.value = targetIds; deletionError.value = ''
        let refreshAttempted = false
        try {
          const response = await deleteSystemTasksRunCase(target), message = taskCaseSuccessMessage(response)
          if (key === identity()) needsReload = true
          if (!current()) return false
          closeConfirmation(); Message.success(message)
          selectedRowKeys.value = selectedRowKeys.value.filter(key => !targetIds.includes(String(key)))
          needsReload = false; refreshAttempted = true
          await Promise.allSettled([loadBoundCaseKeys(), doRefresh()]); return true
        } catch (requestFailure) { if (current()) deletionError.value = requestFailureMessage(requestFailure, '删除用例失败，请重试'); return false }
        finally { deleteLoading.value = false; deletingIds.value = []; if (!refreshAttempted || !context()) resume() }
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

  function doRefresh(): Promise<void> {
    if (!available()) { boundLoading.value = false; return Promise.resolve() }
    const requestId = ++boundRequestId, taskId = currentTaskId.value
    const context = captureContext(), current = () => context() && requestId === boundRequestId
    if (taskId === '') { boundLoading.value = false; return Promise.resolve() }
    boundLoading.value = true
    boundError.value = ''
    const projectProductId = getLeafValue(boundFilter.projectProduct)
    const moduleId = getLeafValue(boundFilter.module)
    const boundType =
      boundFilter.type === '' || boundFilter.type === null ? undefined : boundFilter.type
    return getSystemTasksRunCase({
      task_id: taskId,
      type: boundType,
      project_product_id: projectProductId === '' ? undefined : projectProductId,
      module_id: moduleId === '' ? undefined : moduleId,
      case_people_id: boundFilter.casePeople === '' ? undefined : boundFilter.casePeople,
      case_name: boundFilter.caseName.trim() || undefined,
      page: pagination.page,
      pageSize: pagination.pageSize,
    })
      .then(async (res) => {
        if (!current()) return
        const result = parseBoundCases(res)
        pagination.setTotalSize(result.total)
        const lastPage = Math.max(1, Math.ceil(result.total / pagination.pageSize))
        if (pagination.page > lastPage) { pagination.page = lastPage; await doRefresh(); return }
        boundRows.value = result.rows
      })
      .catch((loadFailure2) => { if (current()) (reportLoadError(loadFailure2, "已绑定用例加载失败，请重试", false), boundError.value = '已绑定用例加载失败，请重试') })
      .finally(() => { if (current()) boundLoading.value = false })
  }

  function loadBoundPytestModules(projectProductId: unknown) {
    if (!available()) { boundModuleLoading.value = false; return Promise.resolve() }
    const requestId = ++moduleRequestId, taskId = currentTaskId.value
    const productId = getLeafValue(projectProductId)
    const context = captureContext(), current = () => context() && requestId === moduleRequestId && productId === getLeafValue(boundFilter.projectProduct) && isBoundPytestCaseType.value
    boundModuleError.value = ''
    if (productId === '') { boundModuleOptions.value = []; boundModuleLoading.value = false; return Promise.resolve() }
    boundModuleLoading.value = true
    return getPytestProductName(productId)
      .then((res) => {
        if (current()) boundModuleOptions.value = parseTaskCaseOptions(res)
      })
      .catch((loadFailure3) => { if (current()) (reportLoadError(loadFailure3, "模块选项加载失败，请重试", false), boundModuleError.value = '模块选项加载失败，请重试') })
      .finally(() => { if (context() && requestId === moduleRequestId) boundModuleLoading.value = false })
  }

  function getNickName() {
    if (!available()) { ownerLoading.value = false; return Promise.resolve() }
    const requestId = ++ownerRequestId, taskId = currentTaskId.value
    const context = captureContext(), current = () => context() && requestId === ownerRequestId
    ownerLoading.value = true; ownerError.value = ''
    return getUserName()
      .then((res) => {
        if (current()) ownerOptions.value = parseTaskCaseOptions(res)
      })
      .catch((loadFailure4) => { if (current()) (reportLoadError(loadFailure4, "负责人选项加载失败，请重试", false), ownerError.value = '负责人选项加载失败，请重试') })
      .finally(() => { if (current()) ownerLoading.value = false })
  }

  async function loadTaskConfig() {
    if (!available()) { taskConfigLoading.value = false; return false }
    const requestId = ++taskConfigRequestId
    const taskId = currentTaskId.value
    const context = captureContext(), current = () => context() && requestId === taskConfigRequestId
    taskConfigLoading.value = true
    taskConfigError.value = ''
    try {
      if (taskId === '') {
        taskConfig.value = null
        taskConfigError.value = '缺少定时任务 ID'
        return false
      }
      const res = await getSystemTasks({ id: taskId, page: 1, pageSize: 1 })
      if (!current()) return false
      const record = parseTaskCaseConfig(res, taskId)
      if (!record) {
        taskConfig.value = null
        taskConfigError.value = '定时任务不存在或无权查看'
        return false
      }
      const firstLoad = taskConfig.value === null
      taskConfig.value = record
      if (firstLoad) {
        addForm.projectProduct = record.project_product?.id ?? ''
        addForm.module = record.module?.id ?? ''
        boundFilter.projectProduct = addForm.projectProduct
        boundFilter.module = addForm.module
      }
      const allowedTypes = record.case_types
      if (allowedTypes.length && !allowedTypes.includes(Number(addForm.type))) {
        addForm.type = Number(allowedTypes[0])
      }
      return true
    } catch (loadFailure5) {
      if (current()) (reportLoadError(loadFailure5, "定时任务配置加载失败，请重试", false), taskConfigError.value = '定时任务配置加载失败，请重试')
      return false
    } finally {
      if (current()) taskConfigLoading.value = false
    }
  }

  function initializeTaskCases(): Promise<void> {
    if (!available() || writeBusy.value) { needsReload = true; return Promise.resolve() }
    if (pendingInitialization) return pendingInitialization
    const current = captureContext()
    needsReload = false
    const request = Promise.resolve().then(async () => {
      if (!current() || !await loadTaskConfig() || !current()) return
      if (isManualScope.value) {
        await Promise.allSettled([loadBoundCaseKeys(), doRefresh(), getNickName(), loadCandidateCases(false),
          ...(isBoundPytestCaseType.value ? [loadBoundPytestModules(boundFilter.projectProduct)] : [])])
      } else {
        await loadRuleCases()
      }
    }).catch((loadFailure0) => { if (current()) (reportLoadError(loadFailure0, "加载失败，请重试", false), taskConfigError.value = '任务用例初始化失败，请重试') })
      .finally(() => { if (pendingInitialization === request) pendingInitialization = null })
    pendingInitialization = request
    return request
  }

  async function loadEnums() {
    if (!available()) return
    const request = ++enumRequestId, context = captureContext(), current = () => context() && request === enumRequestId
    enumLoading.value = true; enumError.value = ''
    try { await enumStore.getEnum() }
    catch (loadFailure6) { if (current()) (reportLoadError(loadFailure6, "枚举加载失败，请重试", false), enumError.value = '枚举加载失败，请重试') }
    finally { if (current()) enumLoading.value = false }
  }

  function pause() {
    contextVersion++; taskConfigRequestId++; candidateRequestId++; boundCaseKeysRequestId++; boundRequestId++
    invalidateRuleCases(); moduleRequestId++; ownerRequestId++; enumRequestId++
    needsReload = true; pendingInitialization = null; closeConfirmation()
    taskConfigLoading.value = false; candidateLoading.value = false; boundCaseKeysLoading.value = false
    boundLoading.value = false; ownerLoading.value = false; boundModuleLoading.value = false; enumLoading.value = false
  }
  function resume() {
    if (!mounted || !available() || writeBusy.value || !needsReload) return
    void loadEnums(); void initializeTaskCases()
  }
  function visibilityChanged() { if (document.visibilityState === 'visible') resume(); else pause() }
  watch(identity, () => {
    pause(); taskConfig.value = null
    boundRows.value = []; candidateCases.value = []; ownerOptions.value = []; boundModuleOptions.value = []
    selectedRowKeys.value = []; addSelectionKeys.value = []; boundCaseKeySet.value = new Set(); resetRuleCases()
    Object.assign(addForm, { type: fixedTaskType.value ?? 1, projectProduct: '', module: '', caseName: '', levels: [], scenarioLayers: [], scenarioTypes: [], scenarioTags: [], executionVersions: [] })
    Object.assign(boundFilter, { type: '', projectProduct: '', module: '', casePeople: '', caseName: '' })
    for (const paginationInfo of [pagination, candidatePagination]) { paginationInfo.page = 1; paginationInfo.setTotalSize(0) }
    for (const error of [taskConfigError, candidateError, boundCaseKeysError, boundError, ownerError, boundModuleError, bindingError, deletionError, enumError]) error.value = ''
    resume()
  }, { flush: 'sync' })

  onMounted(() => {
    mounted = true
    document.addEventListener('visibilitychange', visibilityChanged)
    resume()
  })
  onActivated(() => { active = true; resume() })
  onDeactivated(() => { active = false; pause() })
  onBeforeUnmount(() => { disposed = true; pause(); document.removeEventListener('visibilitychange', visibilityChanged) })

  const autoSearch = useDebouncedSearch(() => loadRuleCases(true), () => ruleFilter, { enabled: () => available() && !isManualScope.value })
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
