<template>
  <TableBody
    ref="tableBody"
    plain
    class="mango-api-case-page mango-detail-workbench-page"
    :sticky-horizontal-scroll="false"
  >
    <template #header>
      <TableHeader title="测试用例">
        <template v-if="false" #search-content>
          <a-form :model="{}" layout="inline" @keyup.enter="onSearchRefresh">
            <a-form-item v-for="item of headerConditionItems" :key="item.key" :label="item.label">
              <template v-if="item.type === 'input'">
                <a-input
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  allow-clear
                  @blur="onSearchRefresh"
                  @clear="onSearchRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'case_people'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="fieldNames"
                  :options="data.userList"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="onSearchRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'update_user'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="fieldNames"
                  :options="data.userList"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="onSearchRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'scheduled_task'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="fieldNames"
                  :options="item.optionItems"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="onSearchRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'status'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="fieldNames"
                  :options="enumStore.task_status"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="onSearchRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'level'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="fieldNames"
                  :options="enumStore.case_level"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="onSearchRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'scenario_layer'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="fieldNames"
                  :options="enumStore.api_case_scenario_layer"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="onSearchRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'scenario_type'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="fieldNames"
                  :options="enumStore.api_case_scenario_type"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="onSearchRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'scenario_tags'">
                <a-select
                  v-model="item.value"
                  :field-names="fieldNames"
                  :options="enumStore.api_case_scenario_tag"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  multiple
                  value-key="key"
                  @change="onSearchRefresh"
                />
              </template>
            </a-form-item>
          </a-form>
        </template>
      </TableHeader>
    </template>

    <template #default>
      <ProjectProductNavigationWorkbench
        contained-body
        show-modules
        :model-value="getConditionValue('project_product')"
        :module-value="getConditionValue('module')"
        :reset-key="sidebarResetKey"
        @filter-change="onSidebarFilterChange"
        @search="onSearchRefresh"
        @reset-search="onResetSearch"
      >
        <template #search>
          <ApiCaseSearchFilters
            :items="headerConditionItems"
            :user-list="data.userList"
            :enum-store="enumStore"
            :field-names="fieldNames"
            @search="onSearchRefresh"
          />
        </template>
        <template #tabs>
          <TableTabs :active-key="activePublicationStatus" @tab-click="switchPublicationTab">
            <a-tab-pane v-for="tab in publicationTabs" :key="tab.key" :title="tab.title" />
            <template #extra>
          <a-space wrap>
            <div>
              <a-button
                size="small"
                type="primary"
                @click="onAdd"
                data-testid="qa-views-apitest-case-button-新增"
                >新增</a-button
              >
            </div>
            <div>
              <a-button v-permission="'api.case:execute'"
                size="small"
                status="success"
                :loading="caseRunning"
                :disabled="batchPublicationAction !== null"
                @click="onCaseBatchRun"
                data-testid="qa-views-apitest-case-button-批量执行"
                >批量执行
              </a-button>
            </div>
            <div>
              <a-button v-permission="'timing.tasks:edit'"
                size="small"
                status="warning"
                :disabled="batchPublicationAction !== null"
                @click="handleClick"
                data-testid="qa-views-apitest-case-button-绑定到手动指定任务"
                >绑定到手动定时任务</a-button
              >
              <a-modal v-model:visible="data.visible" @cancel="handleCancel" @ok="handleOk">
                <template #title>绑定到手动定时任务</template>
                <a-form :model="data">
                  <a-form-item class="mango-form-item__require" label="项目产品">
                    <ProjectProductSelect
                      v-model="data.scheduledProjectProduct"
                      placeholder="请选择项目产品"
                      @change="onScheduledProjectProductChange"
                    />
                  </a-form-item>
                  <a-form-item label="模块">
                    <ProductModuleSelect
                      v-model="data.scheduledModule"
                      :auto-clear="false"
                      :disabled="!getOptionId(data.scheduledProjectProduct)"
                      :project-product-id="data.scheduledProjectProduct"
                      :selectable-level="0"
                      show-all-option
                      placeholder="请选择模块分类（可选）"
                      @change="onScheduledModuleChange"
                    />
                  </a-form-item>
                  <a-form-item class="mango-form-item__require" label="定时任务">
                    <a-select
                      v-model="data.value"
                      :disabled="!getOptionId(data.scheduledProjectProduct)"
                      :field-names="fieldNames"
                      :loading="data.scheduledNameLoading"
                      :options="data.scheduledName"
                      allow-clear
                      allow-search
                      placeholder="请选择手动指定任务进行绑定"
                      value-key="key"
                      data-testid="qa-views-apitest-case-select-请选择手动指定任务进行绑定"
                    />
                  </a-form-item>
                </a-form>
              </a-modal>
            </div>
            <div>
              <a-button v-permission="'api.case:publish'"
                size="small"
                :loading="batchPublicationAction === 'publish'"
                :disabled="publicationActionCaseId !== null || batchPublicationAction !== null"
                @click="batchUpdatePrepublication('publish')"
                data-testid="qa-views-apitest-case-button-批量发布"
                >批量发布</a-button
              >
            </div>
            <div>
              <a-button v-permission="'api.case:publish'"
                size="small"
                :loading="batchPublicationAction === 'revert'"
                :disabled="publicationActionCaseId !== null || batchPublicationAction !== null"
                @click="batchUpdatePrepublication('revert')"
                data-testid="qa-views-apitest-case-button-批量未发布"
                >批量未发布</a-button
              >
            </div>
            <div>
              <a-button v-permission="'api.case:delete'"
                size="small"
                status="danger"
                :disabled="batchPublicationAction !== null"
                @click="onDelete(null)"
                data-testid="qa-views-apitest-case-button-批量删除"
                >批量删除</a-button
              >
            </div>
          </a-space>
            </template>
          </TableTabs>
        </template>
        <StickyHorizontalTable :scroll-x="2520">
          <a-table
            :bordered="false"
            :columns="tableColumns"
            :data="batchSelectableDataList"
            :loading="table.tableLoading.value"
            :pagination="false"
            :row-selection="{ selectedRowKeys, showCheckedAll }"
            :rowKey="rowKey"
            :scroll="{ x: 2520, y: '100%' }"
            @selection-change="onApiCaseSelectionChange"
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
                <template v-if="item.key === 'execution_configuration'" #title>
                  <CaseExecutionConfigurationTitle />
                </template>
                <template v-if="item.key === 'index'" #cell="{ record }">
                  {{ record.id }}
                </template>
                <template v-else-if="item.key === 'scenario_type'" #cell="{ record }">
                  <a-tag :color="enumStore.colors[record.scenario_type]" size="small">
                    {{ getEnumTitle(enumStore.api_case_scenario_type, record.scenario_type) }}
                  </a-tag>
                </template>
                <template v-else-if="item.key === 'scenario_layer'" #cell="{ record }">
                  <a-tag :color="enumStore.colors[record.scenario_layer]" size="small">
                    {{ getEnumTitle(enumStore.api_case_scenario_layer, record.scenario_layer) }}
                  </a-tag>
                </template>
                <template v-else-if="item.key === 'scenario_tags'" #cell="{ record }">
                  <ExecutionSceneTagGrid
                    :values="record.scenario_tags"
                    :options="enumStore.api_case_scenario_tag"
                    :colors="enumStore.colors"
                  />
                </template>
                <template v-else-if="item.key === 'scenario_description'" #cell="{ record }">
                  {{ record.scenario_description || '-' }}
                </template>
                <template v-else-if="item.key === 'case_flow'" #cell="{ record }">
                  {{ record.case_flow || '-' }}
                </template>
                <template v-else-if="item.key === 'project_product'" #cell="{ record }">
                  {{ formatProjectProductPath(record.project_product) }}
                </template>
                <template v-else-if="item.key === 'module'" #cell="{ record }">
                  {{ formatModulePath(record.module) }}
                </template>
                <template v-else-if="item.key === 'case_people'" #cell="{ record }">
                  {{ record.case_people?.name }}
                </template>
                <template v-else-if="item.key === 'update_user'" #cell="{ record }">
                  {{ record.update_user?.name || '-' }}
                </template>
                <template v-else-if="item.key === 'level'" #cell="{ record }">
                  <a-tag :color="enumStore.colors[record.level]" size="small">
                    {{
                      record.level !== null ? enumStore.case_level[record.level]?.title || '-' : '-'
                    }}
                  </a-tag>
                </template>
                <template v-else-if="item.key === 'status'" #cell="{ record }">
                  <a-tag :color="enumStore.status_colors[record.status]" size="small"
                    >{{ enumStore.task_status[record.status]?.title || '-' }}
                  </a-tag>
                </template>
                <template v-else-if="item.key === 'execution_configuration'" #cell="{ record }">
                  <a-spin v-if="configurationLoading && !configurationSummaries[record.id]" />
                  <a-button v-else-if="!configurationSummaries[record.id]" type="text" size="mini"
                    @click="reloadConfigurationSummaries">加载失败，重试</a-button>
                  <a-button v-else-if="configurationSummaries[record.id].has_sql || configurationSummaries[record.id].has_data_factory"
                    type="text" size="mini" :disabled="!permissions.hasPermission('api.case:detail')"
                    @click="configurationDrawerRef?.open(Number(record.id), record.name)">
                    <CaseExecutionConfigurationTags :sql-count="configurationSummaries[record.id].sql_count"
                      :factory-count="configurationSummaries[record.id].data_factory_count" />
                  </a-button>
                  <CaseExecutionConfigurationTags v-else :sql-count="configurationSummaries[record.id].sql_count"
                    :factory-count="configurationSummaries[record.id].data_factory_count" />
                </template>
                <template v-else-if="item.key === 'publication_status'" #cell="{ record }">
                  <a-tag
                    :color="
                      getApiCasePublicationMeta(
                        record.publication_status,
                        record.published_version_label,
                        record.has_unpublished_changes,
                        record.prepublished_revision_no
                      ).color
                    "
                    size="small"
                  >
                    {{
                      getApiCasePublicationMeta(
                        record.publication_status,
                        record.published_version_label,
                        record.has_unpublished_changes,
                        record.prepublished_revision_no
                      ).label
                    }}
                  </a-tag>
                </template>
                <template v-else-if="item.key === 'actions'" #cell="{ record }">
                  <MangoTableActions
                    :actions="[
                      { permission: 'api.case:execute',
                        label: '执行',
                        loading: caseRunning,
                        onClick: () => caseRun(record),
                      },
                      { permission: 'api.case:detail', label: '步骤', onClick: () => onStep(record) },
                      { permission: 'api.case:edit', label: '套件', onClick: () => clickSuite(record) },
                      { permission: 'api.case:detail', label: '历史结果', onClick: () => openResultHistory(record) },
                      { permission: 'api.case:detail', label: '关联任务', onClick: () => onBoundTasks(record) },
                      { permission: 'api.case:publish',
                        label: '提交预发布',
                        hidden: !canSubmitCasePrepublication(record),
                        loading: publicationActionCaseId === record.id,
                        onClick: () => submitCasePrepublication(record),
                      },
                      { permission: 'api.case:publish',
                        label: '通过发布',
                        hidden: !canApproveCasePrepublication(record),
                        loading: publicationActionCaseId === record.id,
                        onClick: () => approveCasePrepublication(record),
                      },
                      { permission: 'api.case:publish',
                        label: '退回未发布',
                        hidden: !canApproveCasePrepublication(record),
                        loading: publicationActionCaseId === record.id,
                        onClick: () => revertCasePrepublication(record),
                      },
                      { permission: 'api.case:publish',
                        label: '取消发布',
                        hidden: !hasPublishedCaseVersion(record) || !record.is_product_owner,
                        danger: true,
                        loading: publicationActionCaseId === record.id,
                        onClick: () => unpublishCaseVersion(record),
                      },
                      { permission: 'api.case:edit', label: '编辑', onClick: () => onUpdate(record) },
                      { permission: 'api.case:copy', label: '复制', onClick: () => pageStepsCody(record) },
                      { permission: 'api.case:delete', label: '删除', danger: true, onClick: () => onDelete(record) },
                    ]"
                  />
                </template>
              </a-table-column>
            </template>
          </a-table>
        </StickyHorizontalTable>
        <template #footer>
          <TableFooter :pagination="pagination" />
        </template>
        <ParametrizeDrawer
          v-model:initial-data="data.row.parametrize"
          show-environment
          :visible="data.drawerVisible"
          @cancel="data.drawerVisible = false"
          @ok="drawerOk"
        />
      </ProjectProductNavigationWorkbench>
    </template>
  </TableBody>
  <CasePublicationReviewModal ref="publicationReviewRef" @published="onReviewPublished" />
  <ApiCaseConfigurationDrawer ref="configurationDrawerRef" />
  <BaseSidePanel
    :visible="boundTaskVisible"
    :title="boundTaskTitle"
    width="min(1180px, calc(100vw - 32px))"
    cancel-button-text="关闭"
    @update:visible="handleBoundTaskVisibleChange"
    @cancel="handleBoundTaskCancel"
  >
    <a-space class="mango-bound-task-summary">
      <span>共 {{ boundTaskTotal }} 条关联任务</span>
      <a-tag color="blue" size="small">手动绑定 {{ manualRelatedTaskCount }}</a-tag>
      <a-tag color="purple" size="small">自动匹配 {{ automaticRelatedTaskCount }}</a-tag>
    </a-space>
    <a-table
      :bordered="false"
      :data="boundTaskList"
      :loading="boundTaskLoading"
      :pagination="false"
      row-key="relation_key"
      :scroll="{ x: 1420 }"
      size="small"
    >
      <template #empty>
        <div class="mango-empty-state mango-bound-task-empty">暂无关联定时任务</div>
      </template>
      <template #columns>
        <a-table-column title="ID" data-index="task_id" :width="70" />
        <a-table-column title="关联方式" :width="100" align="center">
          <template #cell="{ record }">
            <a-tag :color="record.relation_type === 'manual' ? 'blue' : 'purple'" size="small">
              {{ record.relation_type === 'manual' ? '手动绑定' : '自动匹配' }}
            </a-tag>
          </template>
        </a-table-column>
        <a-table-column title="任务名称" data-index="task_name" :width="180" ellipsis tooltip />
        <a-table-column title="定时策略" data-index="timing_strategies" :width="180">
          <template #cell="{ record }">
            <span>{{
              (record.timing_strategies || []).map((item: any) => item.name).join('、') || '-'
            }}</span>
          </template>
        </a-table-column>
        <a-table-column
          title="负责人"
          data-index="case_people_name"
          :width="100"
          ellipsis
          tooltip
        />
        <a-table-column title="匹配范围" :width="180" ellipsis tooltip>
          <template #cell="{ record }">
            {{ record.relation_type === 'manual' ? '手动指定' : record.module_name || '产品全量' }}
          </template>
        </a-table-column>
        <a-table-column title="命中环境" data-index="matching_test_envs" :width="150">
          <template #cell="{ record }">
            <a-space :size="4" wrap>
              <a-tag
                v-for="testEnv in record.matching_test_envs || []"
                :key="testEnv"
                :color="enumStore.colors[testEnv]"
                size="small"
              >
                {{ enumStore.environment_type.find((item) => String(item.key) === String(testEnv))?.title || '-' }}
              </a-tag>
            </a-space>
          </template>
        </a-table-column>
        <a-table-column title="执行场景" :width="200">
          <template #cell="{ record }">
            <ExecutionSceneTagGrid
              :values="record.execution_scenes"
              :options="enumStore.api_case_scenario_tag"
              :colors="enumStore.colors"
            />
          </template>
        </a-table-column>
        <a-table-column title="是否开启" data-index="status" :width="90">
          <template #cell="{ record }">
            <a-tag :color="record.status === 1 ? 'green' : 'gray'" size="small">
              {{ record.status === 1 ? '开启' : '关闭' }}
            </a-tag>
          </template>
        </a-table-column>
        <a-table-column title="操作" data-index="actions" fixed="right" :width="150">
          <template #cell="{ record }">
            <MangoTableActions
              :actions="[
                {
                  label: record.relation_type === 'manual' ? '添加用例' : '查看匹配',
                  onClick: () => openBoundTask(record),
                },
                { permission: 'api.case:delete',
                  label: '解绑',
                  danger: true,
                  hidden: record.relation_type !== 'manual',
                  onClick: () => unbindBoundTask(record),
                },
              ]"
            />
          </template>
        </a-table-column>
      </template>
    </a-table>
  </BaseSidePanel>
  <BaseSidePanel
    :visible="taskCasePanel.visible"
    :title="taskCasePanelTitle"
    width="calc(92vw - 150px)"
    mode="page"
    @update:visible="(value) => (taskCasePanel.visible = value)"
    @cancel="taskCasePanel.visible = false"
  >
    <TimingTaskCase
      v-if="taskCasePanel.visible && taskCasePanel.taskId"
      :key="taskCasePanel.taskId"
      embedded
      :task-id="taskCasePanel.taskId"
      :task-name="taskCasePanel.taskName"
      :task-type="taskCasePanel.taskType"
      :project-product-id="taskCasePanel.projectProductId"
      :module-id="taskCasePanel.moduleId"
      @close="taskCasePanel.visible = false"
    />
  </BaseSidePanel>
  <TestExecutionModal
    ref="batchRunModalRef"
    title="批量执行 API 用例"
    name-editable
    version-selectable
    :platform-limit="apiPlatformLimit"
    @confirm="onConfirmCaseBatchRun"
  />
  <ExecutionResultHistoryDrawer
    v-model:visible="resultHistory.visible"
    :title="resultHistory.title"
    :case-id="resultHistory.caseId"
    @show-trace="showExecutionTrace"
  />
  <ApiCaseExecutionTraceDrawer ref="traceDrawerRef" />
  <ModalDialog ref="modalDialogRef" :title="data.actionTitle" @confirm="onDataForm">
    <template #content>
      <a-form :model="formModel">
        <a-form-item
          v-for="item of formItems"
          :key="item.key"
          :class="[item.required ? 'mango-form-item__require' : 'mango-form-item__no_require']"
          :label="item.label"
        >
          <template v-if="item.type === 'input'">
            <a-input v-model="item.value" :placeholder="item.placeholder" />
          </template>
          <template v-else-if="item.type === 'cascader'">
            <ProjectProductSelect
              v-model="item.value"
              :placeholder="item.placeholder"
              @change="onFormProjectProductChange"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'module'">
            <ProductModuleSelect
              v-model="item.value"
              :project-product-id="getFormItemValue('project_product')"
              :placeholder="item.placeholder"
              :auto-clear="false"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'case_people'">
            <a-select
              v-model="item.value"
              :multiple="item.multiple"
              :max-tag-count="item.multiple ? 1 : undefined"
              :field-names="fieldNames"
              :options="data.userList"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              value-key="key"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'level'">
            <a-select
              v-model="item.value"
              :multiple="item.multiple"
              :max-tag-count="item.multiple ? 1 : undefined"
              :field-names="fieldNames"
              :options="enumStore.case_level"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              value-key="key"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'scenario_layer'">
            <a-select
              v-model="item.value"
              :multiple="item.multiple"
              :max-tag-count="item.multiple ? 1 : undefined"
              :field-names="fieldNames"
              :options="enumStore.api_case_scenario_layer"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              value-key="key"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'scenario_type'">
            <a-select
              v-model="item.value"
              :multiple="item.multiple"
              :max-tag-count="item.multiple ? 1 : undefined"
              :field-names="fieldNames"
              :options="enumStore.api_case_scenario_type"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              value-key="key"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'scenario_tags'">
            <a-select
              v-model="item.value"
              :field-names="fieldNames"
              :options="enumStore.api_case_scenario_tag"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              multiple
              value-key="key"
            />
          </template>
          <template v-else-if="item.type === 'textarea'">
            <a-textarea
              v-model="item.value"
              :placeholder="item.placeholder"
              :auto-size="{ minRows: 3, maxRows: 5 }"
            />
          </template>
        </a-form-item>
      </a-form>
    </template>
  </ModalDialog>
</template>

<script lang="ts" setup>
  import CasePublicationReviewModal from '@/components/business/CasePublicationReviewModal.vue'
  import ApiCaseConfigurationDrawer from './components/ApiCaseConfigurationDrawer.vue'
  import CaseExecutionConfigurationTags from '@/components/display/CaseExecutionConfigurationTags.vue'
  import CaseExecutionConfigurationTitle from '@/components/display/CaseExecutionConfigurationTitle.vue'
  import { useCaseConfigurationSummary } from './useCaseConfigurationSummary'
  import usePermissionStore from '@/store/modules/permission'
  import { usePagination, useRowKey, useTable } from '@/hooks/table'
  import { useLatestRequest } from '@/hooks/use-latest-request'
  import { useProjectLockedRowSelection } from '@/hooks/use-project-locked-row-selection'
  import { ModalDialogType } from '@/types/components'
  import { Message, Modal } from '@arco-design/web-vue'
  import { computed, onMounted, ref, nextTick, reactive, onUnmounted } from 'vue'
  import { getFormItems } from '@/utils/datacleaning'
  import { fieldNames } from '@/setting'
  import { useRoute, useRouter } from 'vue-router'
  import { usePageData } from '@/store/page-data'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ExecutionSceneTagGrid from '@/components/display/ExecutionSceneTagGrid.vue'
  import ExecutionResultHistoryDrawer from '@/components/business/ExecutionResultHistoryDrawer.vue'
  import { formatProjectProductPath, formatModulePath, getOptionId } from '@/utils/business-format'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import StickyHorizontalTable from '@/components/table/StickyHorizontalTable.vue'
  import ApiCaseSearchFilters from './ApiCaseSearchFilters.vue'
  import TestExecutionModal from '@/components/overlays/TestExecutionModal.vue'
  import ApiCaseExecutionTraceDrawer from './details/components/ApiCaseExecutionTraceDrawer.vue'
  import type { ApiCaseExecutionTraceQuery } from './details/types'
  import { tableColumns, formItems, conditionItems, publicationTabs } from './config'

  import { getUserName } from '@/api/user/user'
  import { useEnum } from '@/store/modules/get-enum'
  import useUserStore from '@/store/modules/user'
  import {
    getApiCase,
    getApiCaseRelatedTasks,
    deleteApiCase,
    postApiCase,
    postApiCaseCody,
    getApiCaseRun,
    getApiCaseExecutionOptions,
    postApiCaseBatchRun,
    putApiCase,
  } from '@/api/apitest/case'
  import {
    deleteSystemTasksRunCase,
    postSystemTasksBatchSetCaseVersions,
  } from '@/api/system/tasks_details'
  import { getSystemTasksName } from '@/api/system/tasks'
  import TimingTaskCase from '@/views/timing/tasks/case/index.vue'
  import type { ApiCaseVersionListRow } from '@/types/api-test/case-version'
  import {
    buildPublishedBatchItems,
    getApiCasePublicationMeta,
    toApiCaseBatchRunItems,
  } from '@/utils/api-case-version'
  import {
    createApiCaseRevision,
    revertApiCasePrepublication,
    submitApiCasePrepublication,
    unpublishApiCaseRelease,
  } from '@/api/apitest/case-version'

  const router = useRouter()
  const permissions = usePermissionStore()
  const configurationDrawerRef = ref<InstanceType<typeof ApiCaseConfigurationDrawer> | null>(null)
  const { summaries: configurationSummaries, loading: configurationLoading,
    load: loadConfigurationSummaries, reset: resetConfigurationSummaries } = useCaseConfigurationSummary()
  function reloadConfigurationSummaries() {
    void loadConfigurationSummaries(table.dataList.map(row => Number(row.id)))
  }
  const publicationReviewRef = ref<InstanceType<typeof CasePublicationReviewModal> | null>(null)
  function onReviewPublished(ids: number[]) {
    const published = new Set(ids.map(String))
    selectedRowKeys.value = selectedRowKeys.value.filter((id) => !published.has(String(id)))
    doRefresh(null, false, true)
  }
  const route = useRoute()
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const batchRunModalRef = ref<InstanceType<typeof TestExecutionModal> | null>(null)
  const table = useTable()
  const pagination = usePagination(doRefresh, () => table.tableLoading)
  const {
    selectedRowKeys,
    showCheckedAll,
    selectableDataList: batchSelectableDataList,
    onSelectionChange: onApiCaseSelectionChange,
    validateSingleProject,
  } = useProjectLockedRowSelection<ApiCaseVersionListRow>(
    () => table.dataList as ApiCaseVersionListRow[],
    (row) => row?.project_product?.project
  )
  const { beginRequest, isLatestRequest } = useLatestRequest()
  const rowKey = useRowKey('id')
  const formModel = ref({})
  const enumStore = useEnum()
  const activePublicationStatus = ref('all')

  function switchPublicationTab(key: string | number) {
    activePublicationStatus.value = String(key)
    pagination.page = 1
    selectedRowKeys.value = []
    doRefresh(null, false, true)
  }
  const userStore = useUserStore()
  const headerConditionItems = computed(() =>
    conditionItems.filter((item) => item.key !== 'project_product' && item.key !== 'module')
  )

  const data: any = reactive({
    actionTitle: '新增',
    isAdd: false,
    updateId: 0,
    userList: [],
    scheduledName: [],
    scheduledNameLoading: false,
    scheduledProjectProduct: null,
    scheduledModule: '__all__',
    value: null,
    visible: false,
    drawerVisible: false,
    row: {},
  })
  const caseRunning = ref(false)
  const publicationActionCaseId = ref<number | null>(null)
  const batchPublicationAction = ref<'publish' | 'revert' | null>(null)
  const sidebarModuleIds = ref<Array<string | number>>([])
  const sidebarResetKey = ref(0)
  const apiPlatformLimit = ref(1)
  const pendingBatchRunCaseIds = ref<number[]>([])
  const pollingTimer = ref<NodeJS.Timeout | null>(null)
  const boundTaskVisible = ref(false)
  const boundTaskLoading = ref(false)
  const boundTaskTitle = ref('关联任务')
  const boundTaskList = ref<any[]>([])
  const boundTaskTotal = ref(0)
  const traceDrawerRef = ref<InstanceType<typeof ApiCaseExecutionTraceDrawer> | null>(null)
  const resultHistory = reactive({
    visible: false,
    caseId: '' as number | string,
    title: '用例执行历史',
  })
  const manualRelatedTaskCount = computed(
    () => boundTaskList.value.filter((item) => item.relation_type === 'manual').length
  )
  const automaticRelatedTaskCount = computed(
    () => boundTaskList.value.filter((item) => item.relation_type === 'automatic').length
  )
  const taskCasePanel = reactive({
    visible: false,
    taskId: '' as number | string,
    taskName: '',
    taskType: 1,
    projectProductId: '' as number | string,
    moduleId: '' as number | string,
    relationType: 'manual' as 'manual' | 'automatic',
  })
  const taskCasePanelTitle = computed(() =>
    taskCasePanel.relationType === 'automatic'
      ? `匹配用例 - ${taskCasePanel.taskName}`
      : `添加用例 - ${taskCasePanel.taskName}`
  )

  function clearPollingTimer() {
    if (pollingTimer.value) {
      clearInterval(pollingTimer.value)
      pollingTimer.value = null
    }
  }

  function getItemValue(items: any[], key: string) {
    return items.find((item: any) => item.key === key)?.value ?? ''
  }

  function setItemValue(items: any[], key: string, value: any) {
    const item = items.find((option: any) => option.key === key)
    if (item) {
      item.value = value
    }
  }

  function getConditionValue(key: string) {
    return getItemValue(conditionItems, key)
  }

  function getFormItemValue(key: string) {
    return getItemValue(formItems, key)
  }

  function onSidebarFilterChange(filter: { projectProduct: any; module: any; moduleIds?: any[] }) {
    setItemValue(conditionItems, 'project_product', filter.projectProduct)
    setItemValue(conditionItems, 'module', filter.module)
    sidebarModuleIds.value = filter.moduleIds || []
    selectedRowKeys.value = []
    pagination.page = 1
    doRefresh(null, false, true)
  }

  function onFormProjectProductChange() {
    setItemValue(formItems, 'module', null)
  }

  function onSearchRefresh() {
    doRefresh(null, false, true)
  }

  function doRefresh(projectProductId: any = null, bool_ = false, showLoading = false) {
    clearPollingTimer()
    resetConfigurationSummaries(true)
    const requestId = beginRequest()
    if (showLoading) {
      table.tableLoading.value = true
    }
    let value = getFormItems(conditionItems)
    if (activePublicationStatus.value !== 'all') {
      value.publication_status = activePublicationStatus.value
    }
    if (sidebarModuleIds.value.length) value['module__in'] = sidebarModuleIds.value.join(',')
    if (!Array.isArray(value.scenario_tags) || !value.scenario_tags.length) {
      delete value.scenario_tags
    }
    value['page'] = pagination.page
    value['pageSize'] = pagination.pageSize
    if (projectProductId && bool_) {
      value['project_product'] = projectProductId
    }
    getApiCase(value)
      .then((res) => {
        if (!isLatestRequest(requestId)) return
        table.handleSuccess(res)
        void loadConfigurationSummaries((res.data || []).map((row: any) => Number(row.id)))
        pagination.setTotalSize((res as any).totalSize)
        const hasRunningItem =
          res.data && Array.isArray(res.data) && res.data.some((item: any) => item.status === 3)

        if (hasRunningItem) {
          // 5秒后再次刷新
          pollingTimer.value = setInterval(() => {
            doRefresh()
          }, 5000)
        }
      })
      .catch((error) => {
        if (isLatestRequest(requestId)) {
          resetConfigurationSummaries()
          console.log(error)
        }
      })
      .finally(() => {
        if (isLatestRequest(requestId)) {
          table.tableLoading.value = false
        }
      })
  }

  function onResetSearch() {
    pagination.page = 1
    sidebarModuleIds.value = []
    sidebarResetKey.value += 1
    conditionItems.forEach((it) => {
      if (it.key === 'project_product' || it.key === 'module') {
        it.value = null
      } else if (it.reset) {
        it.reset()
      } else {
        it.value = it.multiple ? [] : ''
      }
    })
    doRefresh(null, false, true)
  }

  function getEnumTitle(options: any[] | null, value: any) {
    return options?.find((item: any) => Number(item.key) === Number(value))?.title || '-'
  }

  function onAdd() {
    data.actionTitle = '新增'
    data.isAdd = true
    modalDialogRef.value?.toggle()
    formItems.forEach((it) => {
      if (it.reset) {
        it.reset()
      } else {
        it.value = it.multiple ? [] : ''
      }
    })
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
      content: '是否要删除此用例？',
      cancelText: '取消',
      okText: '删除',
      onBeforeOk: () => {
        return deleteApiCase(batch ? selectedRowKeys.value : record.id)
          .then((res) => {
            Message.success(res.msg)
          })
          .catch(console.log)
          .finally(() => {
            doRefresh()
            if (batch) {
              selectedRowKeys.value = []
            }
          })
      },
    })
  }

  function onUpdate(item: any) {
    data.actionTitle = '编辑'
    data.isAdd = false
    data.updateId = item.id
    modalDialogRef.value?.toggle()
    nextTick(() => {
      formItems.forEach((it) => {
        const propName = item[it.key]
        if (it.key === 'scenario_layer' && (propName === undefined || propName === null)) {
          it.value = 0
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

  function onDataForm() {
    if (formItems.every((it) => (it.validator ? it.validator() : true))) {
      let value = getFormItems(formItems)
      value['scenario_tags'] = value['scenario_tags'] || []
      if (data.isAdd) {
        value['front_custom'] = []
        value['front_sql'] = []
        value['posterior_sql'] = []
        value['front_headers'] = []
        value['front_public'] = []
        value['front_auth_config'] = []
        value['scenario_layer'] = value['scenario_layer'] ?? 0
        postApiCase(value)
          .then((res) => {
            modalDialogRef.value?.toggle()
            Message.success(res.msg)
            doRefresh()
          })
          .catch((error) => {
            console.log(error)
          })
          .finally(() => {
            modalDialogRef.value?.setConfirmLoading(false)
          })
      } else {
        value['id'] = data.updateId
        putApiCase(value)
          .then((res) => {
            modalDialogRef.value?.toggle()
            Message.success(res.msg)
            doRefresh()
          })
          .catch((error) => {
            console.log(error)
          })
          .finally(() => {
            modalDialogRef.value?.setConfirmLoading(false)
          })
      }
    } else {
      modalDialogRef.value?.setConfirmLoading(false)
    }
  }

  function clickSuite(record: any) {
    data.drawerVisible = true
    data.row = record
  }

  function drawerOk(paramData: any) {
    data.drawerVisible = false

    const hasValidData = paramData.some(
      (suite: any) => suite.name || suite.parametrize.some((param: any) => param.key)
    )

    let value = {
      id: data.row.id,
      parametrize: hasValidData ? paramData : [],
    }
    putApiCase(value)
      .then((res) => {
        Message.success(res.msg)
        doRefresh()
      })
      .catch(console.log)
  }

  function getNickName() {
    getUserName()
      .then((res) => {
        data.userList = res.data
      })
      .catch(console.log)
  }

  const caseRun = async (param) => {
    if (userStore.selected_environment == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    if (caseRunning.value) return
    caseRunning.value = true

    const timeoutId = setTimeout(() => {
      Message.info('测试用例异步执行中，请稍后刷新页面查看该用例的测试结果~')
      caseRunning.value = false
      doRefresh()
    }, 30000)

    try {
      const res = await getApiCaseRun(param.id, userStore.selected_environment, null)
      clearTimeout(timeoutId)
      Message.success(res.msg)
      doRefresh()
      caseRunning.value = false
    } catch (e) {
      clearTimeout(timeoutId)
      caseRunning.value = false
    }
  }

  function hasPublishedCaseVersion(record: any) {
    return Boolean(record?.published_release_id && record?.published_revision_id)
  }

  function canSubmitCasePrepublication(record: ApiCaseVersionListRow) {
    if (record.prepublished_revision_id || !record.has_product_owner) return false
    return !hasPublishedCaseVersion(record) || record.has_unpublished_changes
  }

  function canApproveCasePrepublication(record: ApiCaseVersionListRow) {
    return Boolean(
      record.publication_status === 'prepublished' &&
        record.prepublished_revision_id &&
        record.is_product_owner
    )
  }

  function batchUpdatePrepublication(action: 'publish' | 'revert') {
    if (publicationActionCaseId.value !== null || batchPublicationAction.value !== null) return
    const selectedIds = new Set(selectedRowKeys.value.map(String))
    if (!selectedIds.size) {
      Message.warning('请选择要处理的用例')
      return
    }
    const selectedRows = (table.dataList as ApiCaseVersionListRow[]).filter((row) =>
      selectedIds.has(String(row.id))
    )
    if (selectedRows.length !== selectedIds.size) {
      Message.warning('部分选中用例已不在当前列表，请刷新后重新选择')
      return
    }
    const invalidRows = selectedRows.filter((row) => !canApproveCasePrepublication(row))
    if (invalidRows.length) {
      const names = invalidRows
        .slice(0, 5)
        .map((row) => `#${row.id} ${row.name}`)
        .join('、')
      const suffix = invalidRows.length > 5 ? ` 等 ${invalidRows.length} 条` : ''
      Message.warning(
        `以下用例不符合操作条件：${names}${suffix}。仅允许产品负责人处理预发布状态的用例`
      )
      return
    }
    if (action === 'publish') {
      void publicationReviewRef.value?.open('api', selectedRows.map((row) => Number(row.id)))
      return
    }
    const title = '批量未发布'
    Modal.confirm({
      title,
      content: `确认将所选 ${selectedRows.length} 个用例退回未发布吗？旧版本仅保留历史记录，不会自动恢复发布。`,
      okText: '确认退回',
      async onBeforeOk() {
        if (publicationActionCaseId.value !== null || batchPublicationAction.value !== null) {
          return false
        }
        batchPublicationAction.value = action
        const succeededIds = new Set<string>()
        const failedNames: string[] = []
        try {
          for (const row of selectedRows) {
            try {
              await revertApiCasePrepublication(Number(row.id))
              succeededIds.add(String(row.id))
            } catch {
              failedNames.push(`#${row.id} ${row.name}`)
            }
          }
          selectedRowKeys.value = selectedRowKeys.value.filter(
            (id) => !succeededIds.has(String(id))
          )
          if (failedNames.length) {
            Message.warning(
              `${title}成功 ${succeededIds.size} 条，失败 ${failedNames.length} 条：${failedNames
                .slice(0, 5)
                .join('、')}。请刷新后检查状态或权限`
            )
          } else Message.success(`${title}成功，共 ${succeededIds.size} 条`)
          doRefresh(null, false, true)
          return true
        } finally {
          batchPublicationAction.value = null
        }
      },
    })
  }

  function submitCasePrepublication(record: ApiCaseVersionListRow) {
    if (publicationActionCaseId.value !== null || batchPublicationAction.value !== null) return
    Modal.confirm({
      title: '提交预发布',
      content: `确认根据用例「${record.name}」的当前编辑态生成修订并提交审核吗？提交后旧正式版本转为历史版本，用例暂停参与定时执行。`,
      okText: '提交预发布',
      async onBeforeOk() {
        publicationActionCaseId.value = Number(record.id)
        try {
          const response: any = await createApiCaseRevision({
            case_id: Number(record.id),
            summary: '从用例列表提交预发布时生成修订',
          })
          const revision = response?.data ?? response
          const revisionId = Number(revision?.id)
          if (!revisionId) {
            Message.error('生成用例修订失败，请稍后重试')
            return false
          }
          await submitApiCasePrepublication(Number(record.id), revisionId)
          Message.success('已生成修订并提交预发布')
          doRefresh(null, false, true)
          return true
        } catch {
          return false
        } finally {
          publicationActionCaseId.value = null
        }
      },
    })
  }

  function approveCasePrepublication(record: ApiCaseVersionListRow) {
    if (
      publicationActionCaseId.value !== null ||
      batchPublicationAction.value !== null ||
      !canApproveCasePrepublication(record)
    )
      return
    if (record.status !== 1) {
      Message.warning('用例尚未处于执行通过状态，请执行通过后再发布')
      return
    }
    void publicationReviewRef.value?.open('api', [Number(record.id)])
  }

  function revertCasePrepublication(record: ApiCaseVersionListRow) {
    if (
      publicationActionCaseId.value !== null ||
      batchPublicationAction.value !== null ||
      !canApproveCasePrepublication(record)
    )
      return
    Modal.confirm({
      title: '退回未发布',
      content: `确认将用例「${record.name}」退回未发布吗？不会自动恢复旧版本。`,
      okText: '确认退回',
      async onBeforeOk() {
        publicationActionCaseId.value = Number(record.id)
        try {
          await revertApiCasePrepublication(Number(record.id))
          Message.success('已退回未发布')
          doRefresh(null, false, true)
          return true
        } catch {
          return false
        } finally {
          publicationActionCaseId.value = null
        }
      },
    })
  }

  function unpublishCaseVersion(record: ApiCaseVersionListRow) {
    if (
      publicationActionCaseId.value !== null ||
      batchPublicationAction.value !== null ||
      !record.published_release_id
    )
      return
    Modal.confirm({
      title: '取消发布用例版本',
      content: `确认取消用例「${record.name}」的当前发布版本吗？取消后，定时任务将不再按已发布版本选中该 Case。`,
      okText: '确认取消',
      okButtonProps: { status: 'danger' },
      async onBeforeOk() {
        publicationActionCaseId.value = Number(record.id)
        try {
          await unpublishApiCaseRelease(Number(record.id), Number(record.published_release_id))
          Message.success('已取消发布')
          doRefresh(null, false, true)
          return true
        } catch {
          return false
        } finally {
          publicationActionCaseId.value = null
        }
      },
    })
  }

  const onCaseBatchRun = async () => {
    if (userStore.selected_environment == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    if (selectedRowKeys.value.length === 0) {
      Message.error('请选择要执行的用例')
      return
    }
    if (caseRunning.value) return

    const selectedIds = new Set(selectedRowKeys.value.map(String))
    const selectedRows = table.dataList.filter((row) =>
      selectedIds.has(String(row.id))
    ) as ApiCaseVersionListRow[]
    if (selectedRows.length !== selectedIds.size) {
      Message.warning('部分已选用例不在当前列表中，请刷新后重新选择')
      return
    }
    if (!validateSingleProject()) return
    pendingBatchRunCaseIds.value = selectedRows.map((item) => item.id)

    caseRunning.value = true
    try {
      const res = await getApiCaseExecutionOptions()
      apiPlatformLimit.value = Number(res.data?.api_platform_limit || 1)
      batchRunModalRef.value?.show({
        executionName: buildBatchExecutionName(),
        testEnv: Number(userStore.selected_environment),
        apiConcurrencyLimit: null,
        executionVersion: 'editing',
      })
    } catch (error: any) {
      Message.error(error?.msg || '获取平台并发配置失败')
    } finally {
      caseRunning.value = false
    }
  }

  function buildBatchExecutionName() {
    const now = new Date()
    const pad = (value: number) => String(value).padStart(2, '0')
    return `API批量执行-${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}${pad(
      now.getHours()
    )}${pad(now.getMinutes())}${pad(now.getSeconds())}`
  }

  async function onConfirmCaseBatchRun(config: {
    executionName: string
    testEnv: number
    apiConcurrencyLimit: number | null
    executionVersion?: 'editing' | 'published'
  }) {
    if (pendingBatchRunCaseIds.value.length === 0) {
      Message.error('没有可执行的用例，请重新选择')
      batchRunModalRef.value?.setConfirmLoading(false)
      return
    }
    const executionVersion = config.executionVersion || 'editing'
    if (executionVersion === 'published') {
      const selectedIds = new Set(pendingBatchRunCaseIds.value.map(String))
      const unpublishedRows = (table.dataList as ApiCaseVersionListRow[]).filter(
        (row) => selectedIds.has(String(row.id)) && !hasPublishedCaseVersion(row)
      )
      if (unpublishedRows.length) {
        const names = unpublishedRows
          .slice(0, 5)
          .map((row) => `${row.id}-${row.name}`)
          .join('、')
        const suffix = unpublishedRows.length > 5 ? ` 等 ${unpublishedRows.length} 条` : ''
        Message.warning(`以下用例尚未发布，不能按已发布版本执行：${names}${suffix}`)
        batchRunModalRef.value?.setConfirmLoading(false)
        return
      }
    }
    caseRunning.value = true
    try {
      const res = await postApiCaseBatchRun(
        pendingBatchRunCaseIds.value,
        config.testEnv,
        config.executionName,
        config.apiConcurrencyLimit,
        executionVersion
      )
      const reportId = res.data?.test_suite_id
      Message.success(reportId ? `${res.msg}，测试报告 ID：${reportId}` : res.msg)
      pendingBatchRunCaseIds.value = []
      batchRunModalRef.value?.close()
      doRefresh()
    } catch (error: any) {
      Message.error(error?.msg || '批量执行任务创建失败')
    } finally {
      caseRunning.value = false
      batchRunModalRef.value?.setConfirmLoading(false)
    }
  }

  function onStep(record: any) {
    const pageData = usePageData()
    pageData.setRecord(record)
    router.push({
      path: '/apitest/case/details',
      query: {
        id: record.id,
      },
    })
  }

  function openResultHistory(record: any) {
    resultHistory.caseId = record.id
    resultHistory.title = `用例执行历史：${record.name || `Case #${record.id}`}`
    resultHistory.visible = true
  }

  async function showExecutionTrace(query: ApiCaseExecutionTraceQuery) {
    await traceDrawerRef.value?.open(query)
  }

  function pageStepsCody(record: any) {
    postApiCaseCody(record.id)
      .then((res) => {
        Message.success(res.msg)
        doRefresh()
      })
      .catch(console.log)
  }

  function resetBoundTaskPanel() {
    boundTaskList.value = []
    boundTaskTotal.value = 0
  }

  function handleBoundTaskVisibleChange(value: boolean) {
    boundTaskVisible.value = value
    if (!value) {
      resetBoundTaskPanel()
    }
  }

  function handleBoundTaskCancel() {
    boundTaskVisible.value = false
    resetBoundTaskPanel()
  }

  async function onBoundTasks(record: any) {
    boundTaskTitle.value = `关联任务 - ${record.name || record.id}`
    boundTaskVisible.value = true
    boundTaskLoading.value = true
    resetBoundTaskPanel()
    try {
      const res = await getApiCaseRelatedTasks(record.id)
      boundTaskList.value = Array.isArray(res.data) ? res.data : []
      boundTaskTotal.value = (res as any).totalSize || boundTaskList.value.length
    } finally {
      boundTaskLoading.value = false
    }
  }

  function openBoundTask(record: any) {
    taskCasePanel.taskId = record.task_id
    taskCasePanel.taskName = record.task_name || ''
    taskCasePanel.taskType = 1
    taskCasePanel.projectProductId = record.project_product_id || ''
    taskCasePanel.moduleId = record.module_id || ''
    taskCasePanel.relationType = record.relation_type || 'manual'
    taskCasePanel.visible = true
  }

  function unbindBoundTask(record: any) {
    Modal.confirm({
      title: '确认解绑',
      content: `确认解除当前用例与定时任务「${record.task_name || record.task_id}」的绑定吗？`,
      cancelText: '取消',
      okText: '解绑',
      onBeforeOk: () =>
        deleteSystemTasksRunCase(record.task_detail_id).then((res) => {
          Message.success(res.msg)
          boundTaskList.value = boundTaskList.value.filter(
            (item) => item.task_detail_id !== record.task_detail_id
          )
          boundTaskTotal.value = boundTaskList.value.length
        }),
    })
  }

  const handleClick = () => {
    if (selectedRowKeys.value.length === 0) {
      Message.error('请选择要添加定时任务的用例')
      return
    }
    data.scheduledProjectProduct = null
    data.scheduledModule = '__all__'
    data.scheduledName = []
    data.value = null
    data.visible = true
  }
  const handleOk = () => {
    if (!getOptionId(data.scheduledProjectProduct)) {
      Message.warning('请选择项目产品')
      return
    }
    if (!data.value) {
      Message.warning('请选择定时任务')
      return
    }
    const selectedIds = new Set(selectedRowKeys.value.map(String))
    const selectedRows = table.dataList.filter((row) =>
      selectedIds.has(String(row.id))
    ) as ApiCaseVersionListRow[]
    const plan = buildPublishedBatchItems(selectedRows)
    if (selectedRows.length !== selectedIds.size || plan.blocked.length) {
      Message.warning('所选用例必须全部存在可执行的已发布版本')
      return
    }
    postSystemTasksBatchSetCaseVersions(toApiCaseBatchRunItems(plan.executable), data.value, 1)
      .then((res) => {
        Message.success(res.msg)
        data.visible = false
        doRefresh()
      })
      .catch(console.log)
  }
  const handleCancel = () => {
    data.visible = false
  }

  function scheduledName(projectProductId: number | string, moduleId?: number | string | null) {
    data.scheduledNameLoading = true
    getSystemTasksName(projectProductId, moduleId, 1, 'manual')
      .then((res) => {
        data.scheduledName = res.data
      })
      .catch(console.log)
      .finally(() => {
        data.scheduledNameLoading = false
      })
  }

  function onScheduledProjectProductChange(value: any) {
    const projectProductId = getOptionId(value)
    data.scheduledModule = '__all__'
    data.value = null
    data.scheduledName = []
    if (projectProductId) scheduledName(projectProductId)
  }

  function onScheduledModuleChange(value: any) {
    const projectProductId = getOptionId(data.scheduledProjectProduct)
    const selectedModuleId = getOptionId(value)
    const moduleId = selectedModuleId === '__all__' ? null : selectedModuleId
    data.value = null
    data.scheduledName = []
    if (projectProductId) scheduledName(projectProductId, moduleId)
  }

  onMounted(() => {
    const routeProjectProduct = route.query.project_product
    const routePublicationStatus = route.query.publication_status
    setItemValue(
      conditionItems,
      'project_product',
      routeProjectProduct ? Number(routeProjectProduct) : null
    )
    if (typeof routePublicationStatus === 'string') {
      const status = routePublicationStatus
      activePublicationStatus.value = publicationTabs.some((tab) => tab.key === status) ? status : 'all'
    }
    nextTick(async () => {
      getNickName()
      await doRefresh()
    })
  })
  onUnmounted(() => {
    clearPollingTimer()
  })
</script>

<style lang="less" scoped>
  .mango-api-case-workbench {
    --mango-workbench-min-width: 1120px;
    display: grid;
    height: 100%;
    min-height: 100%;
    padding-top: var(--m-page-gap);
    box-sizing: border-box;
    grid-template-columns: 240px minmax(830px, 1fr);
    gap: var(--m-page-gap);
  }

  .mango-api-case-main {
    display: grid;
    box-sizing: border-box;
    min-width: 0;
    min-height: 0;
    overflow: hidden;
    border: 1px solid var(--m-border-strong);
    border-radius: var(--m-radius-lg);
    background: var(--m-surface);
    grid-template-rows: auto minmax(0, 1fr);
    gap: var(--m-page-gap);
  }

  .mango-api-case-workbench :deep(.mango-project-navigation-sidebar) {
    height: 100%;
    max-height: 100%;
  }

  .mango-api-case-search {
    flex: none;
    padding: 4px 6px;
  }

  .mango-api-case-search :deep(.arco-card-header) {
    display: none;
  }

  .mango-api-case-search :deep(.arco-form-layout-inline),
  .mango-api-case-search :deep(.arco-form-inline) {
    grid-template-columns: repeat(auto-fit, minmax(235px, 1fr));
  }

  .mango-api-case-search :deep(.arco-form-layout-inline .arco-form-item),
  .mango-api-case-search :deep(.arco-form-item-layout-inline),
  .mango-api-case-search :deep(.arco-form-inline .arco-form-item) {
    width: 100% !important;
    max-width: none !important;
    flex-basis: auto !important;
  }

  .mango-api-case-search :deep(.arco-form-item-wrapper-col),
  .mango-api-case-search :deep(.arco-form-item-content-wrapper) {
    width: auto !important;
    max-width: none !important;
    flex: 1 1 auto !important;
  }

  .mango-api-case-search :deep(.arco-form-item-content),
  .mango-api-case-search :deep(.arco-input-wrapper),
  .mango-api-case-search :deep(.arco-select),
  .mango-api-case-search :deep(.arco-select-view) {
    width: 100% !important;
  }

  .mango-api-case-content-panel {
    display: flex;
    min-width: 0;
    min-height: 0;
    flex-direction: column;
    overflow: hidden;
    background: var(--m-surface);
  }

  .mango-api-case-actions {
    display: flex;
    min-height: 42px;
    flex: none;
    align-items: center;
    justify-content: flex-end;
    padding: 4px 0 6px;
    border-bottom: 1px solid var(--m-border);
  }

  .mango-api-case-actions-box {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    margin-right: var(--m-page-gap);
  }

  .mango-api-case-table-region {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    overscroll-behavior-y: contain;
  }

  .mango-api-case-pagination {
    flex: none;
    border-top: 1px solid var(--m-border);
    background: var(--m-surface);
  }

  .mango-api-case-pagination :deep(.mango-table-mango-footer-container) {
    height: 48px;
    border-top: 0;
  }

  .mango-bound-task-summary {
    margin-bottom: 12px;
    color: var(--m-muted);
    font-size: 13px;
  }

  .mango-bound-task-empty {
    padding: 28px 0;
  }
</style>
