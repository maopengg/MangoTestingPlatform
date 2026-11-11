<template>
  <TableBody
    ref="tableBody"
    :embedded="props.embedded"
    :show-embedded-header="props.embedded"
    class="mango-detail-workbench-page"
  >
    <template #header>
      <ApiCasePageHeader
        :title="apiCaseDetailTitle"
        :case-id="apiCaseId"
        :running="caseRunning"
        :execution-disabled="caseExecutionActive"
        :analysis-disabled="caseExecutionActive || !selectedExecutionResultSummary?.id"
        @execute="caseRun(null)"
        @analyze="caseDiagnosisDrawerRef?.open()"
        @search="openConfigSearch"
        @history="versionPanelRef?.openResultHistoryDrawer()"
        @back="doResetSearch"
      >
        <VariableReferencePanel />
      </ApiCasePageHeader>
    </template>
    <template #default>
      <div
        class="mango-workbench-scroll-x api-case-workbench-scroll"
        :class="{ 'api-case-workbench-scroll--scenario-expanded': scenarioWorkbenchExpanded }"
      >
        <div
          class="api-case-workbench mango-detail-workbench"
          :class="{ 'api-case-workbench--scenario-expanded': scenarioWorkbenchExpanded }"
        >
          <section class="api-case-panel api-case-version-sidebar">
            <ApiCaseVersionPanel
              ref="versionPanelRef"
              :case-id="apiCaseId"
              :current-payload="apiCaseCompareCurrentPayload"
              @select="selectExecutionVersion"
              @detail="showVersionDetail"
              @current="showCurrentConfiguration"
              @execute="executeSelectedVersion"
              @published="doRefresh"
              @show-trace="showExecutionTrace"
            />
          </section>

          <ApiCaseOrchestrationPanel
            :active-key="workspaceTabs.apiType"
            :step-count="caseSteps.length || 0"
            :edit-locked="caseEditLocked"
            :show-add="showCaseAddButton"
            :loading="panelLoading.caseConfigLoading"
            @change="switchType"
            @add="addData"
          >
            <template #preparation>
              <a-tabs
                :active-key="workspaceTabs.apiSonType"
                class="case-config-tabs"
                position="left"
                @tab-click="(key) => switchSonType(key)"
              >
                <a-tab-pane key="15">
                  <template #title>
                    <span class="scenario-tab-title">
                      全局变量
                      <span class="scenario-tab-count">{{ getCaseConfigCount('public') }}</span>
                    </span>
                  </template>
                  <div class="mango-case-global-options">
                    <div class="mango-case-global-option">
                      <TipMessage
                        message="开启可选的 key 如果跟默认开启的 key 重复，则会覆盖默认开启的变量值"
                      />
                      <div class="mango-case-global-table mango-case-global-table--public">
                        <div class="mango-case-global-table__head">
                          <span></span>
                          <span>名称</span>
                          <span>Key</span>
                          <span>类型</span>
                          <span>被测环境</span>
                          <span>状态</span>
                        </div>
                        <a-checkbox-group
                          class="mango-case-global-table__body"
                          v-model="frontPublicCheckedValues"
                          :disabled="caseEditLocked || caseGlobalSaving"
                          direction="vertical"
                          @change="changeCaseGlobalOptions"
                        >
                          <a-checkbox
                            v-for="item in optionLists.publicOptions"
                            :key="item.value"
                            :value="item.value"
                            :disabled="caseEditLocked || item.disabled || caseGlobalSaving"
                          >
                            <span class="mango-case-global-table__row">
                              <span class="mango-case-global-table__cell" :title="item.name">{{
                                item.name
                              }}</span>
                              <span class="mango-case-global-table__cell" :title="item.key">{{
                                item.key
                              }}</span>
                              <span class="mango-case-global-table__cell">
                                <a-tag :color="enumStore.colors[item.type]" size="small">{{
                                  item.typeText
                                }}</a-tag>
                              </span>
                              <span class="mango-case-global-table__cell">
                                <a-tag v-if="item.isCommonEnv" size="small">环境通用</a-tag>
                                <a-space v-else wrap :size="4">
                                  <a-tag
                                    v-for="env in item.testEnvs"
                                    :key="env"
                                    :color="enumStore.colors[env]"
                                    size="small"
                                  >
                                    {{ formatEnvironmentText(env) }}
                                  </a-tag>
                                </a-space>
                              </span>
                              <span class="mango-case-global-table__cell">
                                <a-tag :color="item.disabled ? 'green' : 'gray'" size="small">
                                  {{ item.statusText }}
                                </a-tag>
                              </span>
                            </span>
                          </a-checkbox>
                        </a-checkbox-group>
                      </div>
                    </div>
                  </div>
                </a-tab-pane>
                <a-tab-pane key="16">
                  <template #title>
                    <span class="scenario-tab-title">
                      授权管理
                      <span class="scenario-tab-count">{{ getCaseConfigCount('auth') }}</span>
                    </span>
                  </template>
                  <div class="mango-case-global-options">
                    <div class="mango-case-global-option">
                      <div class="mango-case-global-table mango-case-global-table--auth">
                        <div class="mango-case-global-table__head">
                          <span></span>
                          <span>授权名称</span>
                          <span>授权方式</span>
                          <span>被测环境</span>
                          <span>状态</span>
                        </div>
                        <a-checkbox-group
                          class="mango-case-global-table__body"
                          v-model="frontAuthConfigCheckedValues"
                          :disabled="caseEditLocked || caseGlobalSaving"
                          direction="vertical"
                          @change="changeCaseGlobalOptions"
                        >
                          <a-checkbox
                            v-for="item in optionLists.authConfigOptions"
                            :key="item.value"
                            :value="item.value"
                            :disabled="caseEditLocked || item.disabled || caseGlobalSaving"
                          >
                            <span class="mango-case-global-table__row">
                              <span class="mango-case-global-table__cell" :title="item.name">{{
                                item.name
                              }}</span>
                              <span class="mango-case-global-table__cell">
                                <a-tag :color="enumStore.colors[item.authType]" size="small">{{
                                  item.authTypeText
                                }}</a-tag>
                              </span>
                              <span class="mango-case-global-table__cell">
                                <a-tag v-if="item.isCommonEnv" size="small">{{
                                  item.envText
                                }}</a-tag>
                                <a-tag
                                  v-else
                                  :color="enumStore.colors[item.testEnv]"
                                  size="small"
                                  >{{ item.envText }}</a-tag
                                >
                              </span>
                              <span class="mango-case-global-table__cell">
                                <a-tag :color="item.disabled ? 'green' : 'gray'" size="small">{{
                                  item.statusText
                                }}</a-tag>
                              </span>
                            </span>
                          </a-checkbox>
                        </a-checkbox-group>
                      </div>
                    </div>
                  </div>
                </a-tab-pane>
                <a-tab-pane key="11">
                  <template #title>
                    <span class="scenario-tab-title">
                      自定义变量
                      <span class="scenario-tab-count">{{ getCaseConfigCount('custom') }}</span>
                    </span>
                  </template>
                  <div
                    class="mango-horizontal-scroll-region mango-horizontal-scroll-region--compact mango-case-custom-variable-list"
                  >
                    <KeyValueList
                      :data-list="caseRecord.front_custom"
                      layout="environment-key-value"
                      :field-config="[
                        {
                          field: 'test_envs',
                          label: '适用环境',
                          type: 'select',
                          placeholder: '请选择被测环境',
                          options: caseVariableEnvironmentOptions,
                          fieldNames: fieldNames,
                          multiple: true,
                          className: 'mango-env-select',
                          containerClassName: 'mango-case-custom-env-field',
                          getValue: getVariableEnvironmentValue,
                          setValue: setVariableEnvironmentValue,
                        },
                        {
                          field: 'key',
                          label: 'Key',
                          type: 'input',
                          placeholder: '请输入缓存key',
                          className: 'mango-case-custom-key-input',
                          containerClassName: 'mango-case-custom-key-field',
                          showTitle: true,
                        },
                        {
                          field: 'value',
                          label: 'Value',
                          type: 'input',
                          placeholder: '请输入value',
                          className: 'mango-case-custom-value-input',
                          containerClassName: 'mango-case-custom-value-field',
                          showTitle: true,
                        },
                      ]"
                      :on-delete-item="
                        (index) => removeFrontSql1(caseRecord.front_custom, index, false)
                      "
                      :on-save="upDataCaseWithoutScenarioRefresh"
                      @update:item="
                        (index, value) =>
                          updateArrayItem(
                            caseRecord.front_custom,
                            index,
                            value,
                            caseRecord,
                            'front_custom',
                            upDataCaseWithoutScenarioRefresh
                          )
                      "
                    />
                  </div>
                </a-tab-pane>
                <a-tab-pane key="12">
                  <template #title>
                    <span class="scenario-tab-title">
                      数据库操作
                      <span class="scenario-tab-count">{{ getCaseConfigCount('frontSql') }}</span>
                    </span>
                  </template>
                  <DataSourceOperationList
                    :data-list="caseRecord.front_sql"
                    :datasource-options="optionLists.datasourceAliasOptions"
                    :environment-options="sqlEnvironmentOptions"
                    :project-product-id="apiProjectProductId"
                    :test-env="userStore.selected_environment"
                    :on-delete-item="(index) => removeFrontSql1(caseRecord.front_sql, index)"
                    :on-save="upDataCase"
                    @update:item="
                      (index, value) =>
                        updateArrayItem(
                          caseRecord.front_sql,
                          index,
                          value,
                          caseRecord,
                          'front_sql',
                          upDataCase
                        )
                    "
                  />
                </a-tab-pane>
                <a-tab-pane key="14">
                  <template #title>
                    <span class="scenario-tab-title">
                      数据工厂
                      <span class="scenario-tab-count">{{ getCaseConfigCount('factory') }}</span>
                    </span>
                  </template>
                  <DataFactoryCaseConfigPanel
                    v-if="workspaceTabs.apiType === '1' && workspaceTabs.apiSonType === '14'"
                    ref="dataFactoryPanelRef"
                    :case-id="apiCaseId as string"
                    :project-product-id="apiProjectProductId as string"
                    :source-type="1"
                    @count-change="setCaseDataFactoryCount"
                  />
                </a-tab-pane>
                <a-tab-pane key="13">
                  <template #title>
                    <span class="scenario-tab-title">
                      默认请求头
                      <span class="scenario-tab-count">{{ getCaseConfigCount('headers') }}</span>
                    </span>
                  </template>
                  <div class="mango-case-global-options">
                    <div class="mango-case-global-option">
                      <TipMessage message="此处请求头会应用到所有场景扩展中" />
                      <div class="mango-case-global-table mango-case-global-table--headers">
                        <div class="mango-case-global-table__head">
                          <span></span>
                          <span>Key</span>
                          <span>Value</span>
                        </div>
                        <a-checkbox-group
                          class="mango-case-global-table__body"
                          v-model="caseRecord.front_headers"
                          :disabled="caseEditLocked"
                          direction="vertical"
                          @change="changeHeaders"
                        >
                          <a-checkbox
                            v-for="item of optionLists.headers_list"
                            :key="item.id"
                            :value="item.id"
                          >
                            <span class="mango-case-global-table__row">
                              <span class="mango-case-global-table__cell" :title="item.key">{{
                                item.key
                              }}</span>
                              <span class="mango-case-global-table__cell" :title="item.value">{{
                                item.value
                              }}</span>
                            </span>
                          </a-checkbox>
                        </a-checkbox-group>
                      </div>
                    </div>
                  </div>
                </a-tab-pane>
              </a-tabs>
            </template>
            <template #steps>
              <ApiCaseStepTable
                :columns="columns"
                :data="caseSteps"
                :loading="stepTableLoading || sortingSteps"
                :selected-step-id="selectedStep?.id"
                :debug-running-step-id="debugRunningStepId"
                :edit-locked="caseEditLocked"
                :execution-active="caseExecutionActive"
                :status-text="runtimeStatusText"
                :status-color="runtimeStatusColor"
                :get-api-info-id="getApiInfoId"
                @reorder="handleChange"
                @select="select"
                @debug="debugCaseStep"
                @refresh="refresh"
                @api-info="openApiInfoDetail"
                @delete="onDelete"
                @edit="openStepEditor"
              />
            </template>
            <template #cleanup>
              <a-tabs
                :active-key="workspaceTabs.apiSonType"
                class="case-config-tabs"
                position="left"
                @tab-click="(key) => switchSonType(key)"
              >
                <a-tab-pane key="31">
                  <template #title>
                    <span class="scenario-tab-title">
                      数据库操作
                      <span class="scenario-tab-count">{{
                        getCaseConfigCount('posteriorSql')
                      }}</span>
                    </span>
                  </template>
                  <DataSourceOperationList
                    :data-list="caseRecord.posterior_sql"
                    :datasource-options="optionLists.datasourceAliasOptions"
                    :environment-options="sqlEnvironmentOptions"
                    :project-product-id="apiProjectProductId"
                    :test-env="userStore.selected_environment"
                    :on-delete-item="(index) => removeFrontSql1(caseRecord.posterior_sql, index)"
                    :on-save="upDataCase"
                    empty-text="暂无数据库操作配置，点击上方“增加”按钮添加"
                    @update:item="
                      (index, value) =>
                        updateArrayItem(
                          caseRecord.posterior_sql,
                          index,
                          value,
                          caseRecord,
                          'posterior_sql',
                          upDataCase
                        )
                    "
                  />
                </a-tab-pane>
              </a-tabs>
            </template>
          </ApiCaseOrchestrationPanel>
          <ApiCaseScenarioWorkspace
            :edit-locked="caseEditLocked"
            :latest-execution-label="latestScenarioExecutionLabel"
            :result-outdated="selectedRuntimeResultOutdated"
            :summary="selectedStepSummary"
            :expanded="scenarioWorkbenchExpanded"
            @add="addParameter"
            @toggle-size="toggleScenarioWorkbench"
          >
            <a-space direction="vertical" fill>
              <a-space direction="vertical" fill>
                <mango-panel-spin
                  :loading="panelLoading.collapseLoading"
                  tip="场景数据加载中..."
                  class="scenario-loading-spin full-width"
                >
                  <a-collapse
                    :bordered="false"
                    :active-key="scenarioViewport.activeCollapseKey"
                    accordion
                    @change="onCollapseChange"
                  >
                    <a-collapse-item v-for="(item, index) of scenarios" :key="index">
                      <template #header>
                        <ApiCaseScenarioHeader
                          :item="item"
                          :edit-locked="caseEditLocked"
                          :status-text="runtimeStatusText"
                          :status-color="runtimeStatusColor"
                          :is-failure="isRuntimeFailure"
                          :failure-message="runtimeFailureMessage"
                          @edit="parameterEditing(item)"
                          @copy="parameterCopy(item)"
                          @delete="parameterDelete(item)"
                        />
                      </template>
                      <div
                        v-if="isMountedCollapseItem(index)"
                        v-show="isActiveCollapseItem(index)"
                        class="scenario-expand-body"
                      >
                        <mango-panel-spin
                          :loading="!panelLoading.collapseLoading && panelLoading.caseDetailTabLoading"
                          tip="页签内容加载中..."
                          class="scenario-tab-loading-spin"
                        >
                          <ApiCaseScenarioNav
                            :active-key="workspaceTabs.caseDetailsTypeKey"
                            :counts="{
                              front: getScenarioTabCount(item, 'front'),
                              request: getScenarioTabCount(item, 'request'),
                              response: getScenarioTabCount(item, 'response'),
                              posterior: getScenarioTabCount(item, 'posterior'),
                              assertion: getScenarioTabCount(item, 'assertion'),
                              runtime: getScenarioTabCount(item, 'cache'),
                              factory: getScenarioTabCount(item, 'factory'),
                              assertionResult: getScenarioTabCount(item, 'assertionResult'),
                            }"
                            @change="switchApiInfoType($event, item)"
                          >
                            <template #front>
                              <ApiCaseScenarioFrontPanel
                                :item="item"
                                @patch="applyScenarioPatch"
                                :active-key="workspaceTabs.tabsKey"
                                :active="isActiveCaseDetailTab('1', '12')"
                                :edit-locked="caseEditLocked"
                                :datasource-options="optionLists.datasourceAliasOptions"
                                :environment-options="sqlEnvironmentOptions"
                                :project-product-id="apiProjectProductId"
                                :test-env="userStore.selected_environment"
                                @change="tabsChange($event, item)"
                                @count-change="setScenarioDataFactoryCount"
                              />
                            </template>
                            <template #request>
                              <ApiCaseRequestPanel
                                :item="item"
                                @patch="applyScenarioPatch"
                                :active-key="workspaceTabs.tabsKey"
                                :edit-locked="caseEditLocked"
                                :header-options="optionLists.parameter_headers_list"
                                :project-product-id="apiProjectProductId"
                                :protocol-type="getScenarioProtocolType(item)"
                                :body-type="getScenarioBodyType(item)"
                                @change="tabsChange($event, item)"
                                @edit-json="openJsonEditDrawer"
                                @saving-change="changeScenarioSavingCount"
                              />
                            </template>
                            <template #response>
                              <ApiCaseResponsePanel
                                :item="item"
                                :active-key="workspaceTabs.tabsKey"
                                :active-root="workspaceTabs.caseDetailsTypeKey === '2'"
                                :protocol-type="getScenarioProtocolType(item)"
                                :body-type="getScenarioBodyType(item)"
                                @change="tabsChange($event, item)"
                              />
                            </template>
                            <template #posterior>
                              <ApiCasePosteriorPanel
                                :item="item"
                                @patch="applyScenarioPatch"
                                :active-key="workspaceTabs.tabsKey"
                                :edit-locked="caseEditLocked"
                                :datasource-options="optionLists.datasourceAliasOptions"
                                :environment-options="sqlEnvironmentOptions"
                                :project-product-id="apiProjectProductId"
                                :test-env="userStore.selected_environment"
                                @change="tabsChange($event, item)"
                              />
                            </template>
                            <template #assertion>
                              <ApiCaseAssertionPanel
                                :item="item"
                                :active-key="workspaceTabs.tabsKey"
                                :edit-locked="caseEditLocked"
                                :verifying="assertionVerifyLoadingId === item.id"
                                :protocol-saving="protocolSavingId === item.id"
                                :schema-loading="schemaLoadingId === item.id"
                                :compare-open="Boolean(item.__assertion_compare_open)"
                                :compare-results="getAssertionResultData(item)"
                                :compare-source="
                                  Array.isArray(item.__assertion_verify_result)
                                    ? 'verify'
                                    : 'runtime'
                                "
                                :compare-stale="isAssertionVerifyStale(item)"
                                :text-methods="optionLists.textAss"
                                :general-methods="optionLists.ass"
                                :sql-datasource-options="sqlAssertionDatasourceOptions"
                                :sql-method-options="sqlAssertionMethodOptions"
                                @change="tabsChange($event)"
                                @save="blurSave"
                                @save-protocol="saveProtocolExpectation(item, $event)"
                                @verify="verifyAssertions"
                                @toggle-compare="
                                  item.__assertion_compare_open = !item.__assertion_compare_open
                                "
                                @generate-schema="setSchema(item.id)"
                              >
                                <template #callback>
                                  <ApiCaseCallbackPanel
                                    :general-methods="optionLists.ass"
                                    :case-id="apiCaseId || ''"
                                    :product-id="apiProjectProductId || ''"
                                    :rules="caseRecord.callback_checks || []"
                                    :trigger-step="selectedStep"
                                    :scenario-count="scenarios.length"
                                    :scenario-retry="item.error_retry"
                                    :active="
                                      isActiveCaseDetailTab('3', '36') &&
                                      isActiveCollapseItem(index)
                                    "
                                    :edit-locked="caseEditLocked"
                                    :trace-id="lastTraceId"
                                    :save-pending="callbackSavePending"
                                    :persist-rules="saveCallbackRules"
                                  />
                                </template>
                              </ApiCaseAssertionPanel>
                            </template>
                            <template #runtime>
                              <ApiCaseRuntimeCachePanel
                                :active="workspaceTabs.caseDetailsTypeKey === '5'"
                                :data="item.result_data?.cache_data"
                              />
                            </template>
                            <template #factory>
                              <ApiCaseDataFactoryPanel
                                :active="workspaceTabs.caseDetailsTypeKey === '7'"
                                :data="item.result_data?.data_factory_cache_data"
                              />
                            </template>
                            <template #assertion-result>
                              <div
                                v-if="workspaceTabs.caseDetailsTypeKey === '6'"
                                class="mango-scenario-assertion-results"
                              >
                                <header
                                  v-if="getCallbackAssertionResults(item).length"
                                  class="mango-section-title"
                                  ><h2>接口响应断言</h2></header
                                >
                                <AssertionResult
                                  :data="getAssertionResultData(item)"
                                  :stale="isAssertionVerifyStale(item)"
                                />
                                <ApiCaseCallbackPanel
                                  v-if="getCallbackAssertionResults(item).length"
                                  view="results"
                                  :archived-results="getCallbackAssertionResults(item)"
                                  :case-id="apiCaseId || ''"
                                  :product-id="apiProjectProductId || ''"
                                  :rules="caseRecord.callback_checks || []"
                                  :trigger-step="selectedStep"
                                  :scenario-count="scenarios.length"
                                  :active="true"
                                  :edit-locked="true"
                                  :trace-id="lastTraceId"
                                  :save-pending="false"
                                  :persist-rules="saveCallbackRules"
                                />
                              </div>
                            </template>
                          </ApiCaseScenarioNav>
                        </mango-panel-spin>
                      </div>
                      <div v-else-if="isActiveCollapseItem(index)" class="collapse-content-loading">
                        <a-spin tip="内容加载中..." />
                      </div>
                    </a-collapse-item>
                  </a-collapse>
                </mango-panel-spin>
              </a-space>
            </a-space>
          </ApiCaseScenarioWorkspace>
        </div>
      </div>
    </template>
  </TableBody>
  <ApiCaseConfigSearchModal
    v-model:visible="configSearch.visible"
    v-model:keyword="configSearch.keyword"
    :loading="configSearch.loading"
    :searched="configSearch.searched"
    :truncated="configSearch.truncated"
    :completed="configSearch.completed"
    :total="configSearch.total"
    :matches="configSearch.matches"
    :limit="CONFIG_SEARCH_LIMIT"
    @search="runConfigSearch"
    @select="locateConfigSearchResult"
  />
  <MangoJsonEditDrawer
    v-model:visible="jsonEditDrawer.visible"
    v-model="jsonEditDrawer.value"
    :title="jsonEditDrawer.title"
    :description="`当前编辑内容会保存到所选场景的 ${jsonEditDrawer.label} 配置中。`"
    :saving="jsonEditSaving"
    @save="saveJsonEditDrawer"
  />
  <ApiCaseInfoDetailPanel ref="apiInfoDetailPanelRef" />
  <ApiCaseExecutionTraceDrawer ref="traceDrawerRef" />
  <ApiCaseDiagnosisDrawer
    ref="caseDiagnosisDrawerRef"
    :result-id="selectedExecutionResultSummary?.id"
  />
  <ApiCaseStepEditor
    ref="stepEditorRef"
    :case-id="apiCaseId"
    :project-product-id="apiProjectProductId"
    :edit-locked="caseEditLocked || caseExecutionActive"
    :step-count="caseSteps.length"
    @saved="doRefresh"
  />
  <ApiCaseScenarioEditor
    ref="scenarioEditorRef"
    :case-id="apiCaseId"
    :edit-locked="caseEditLocked || caseExecutionActive"
    @saved="onScenarioSaved"
  />
</template>

<script lang="ts" setup>
  import { isPendingExecution, type PollingContext } from '@/hooks/use-page-polling'
  import { useApiCaseAutoSave } from './composables/useApiCaseAutoSave'
  import {
    computed,
    nextTick,
    onActivated,
    onDeactivated,
    onMounted,
    onUnmounted,
    reactive,
    ref,
    watch,
  } from 'vue'
  import { useRoute } from 'vue-router'
  import { fieldNames } from '@/setting'
  import { Message, Modal } from '@arco-design/web-vue'
  import { usePageData } from '@/store/page-data'
  import { formatJson, formatJsonObj } from '@/utils/tools'
  import {
    COMMON_ENV_VALUE,
    normalizeEnvironmentSelectChange,
    normalizeEnvironmentValues,
    toEnvironmentSelectValue,
  } from '@/utils/environment-scope'
  import { columns, FRONT_FUNC_TEMPLATE, POSTERIOR_FUNC_TEMPLATE } from './config'
  import ApiCaseStepEditor from './components/ApiCaseStepEditor.vue'
  import ApiCaseScenarioEditor from './components/ApiCaseScenarioEditor.vue'
  import type {
    ApiCaseStep,
    ApiCaseScenario,
    CaseWorkspaceRecord,
    CaseResourceOptions,
    ScenarioPatch,
    CaseExecutionSummary,
    CallbackRuleDraft,
  } from './types'
  import { createCaseRequestScope } from './request-scope'
  import { getApiCase, getApiCaseRunRaw, postApiCaseStepDebugRaw } from '@/api/apitest/case'
  import {
    deleteApiCaseDetailed,
    getApiCaseDetailed,
    putApiPutCaseSort,
    putApiPutRefreshApiInfo,
  } from '@/api/apitest/case_detailed'
  import useUserStore from '@/store/modules/user'

  import { useEnum } from '@/store/modules/get-enum'
  import { getApiHeaders } from '@/api/apitest/headers'
  import { getApiPublic } from '@/api/apitest/public'
  import { getApiAuthConfig } from '@/api/apitest/auth-config'
  import {
    deleteApiCaseDetailedParameter,
    getApiCaseDetailedParameter,
    postVerifyApiCaseAssertions,
    putSetSchema,
  } from '@/api/apitest/case-detailed-parameter'
  import { getSystemCacheDataKeyValue } from '@/api/system/cache_data'
  import KeyValueList from '@/components/forms/KeyValueList.vue' // 引入新组件
  import AssertionResult from '@/components/feedback/AssertionResult.vue'
  import TipMessage from '@/components/feedback/TipMessage.vue' // 引入断言结果组件
  import DataFactoryCaseConfigPanel from '@/components/DataFactory/CaseConfigPanel.vue'
  import DataSourceOperationList from '@/components/forms/DataSourceOperationList.vue'
  import ApiCaseVersionPanel from './components/ApiCaseVersionPanel.vue'
  import ApiCasePageHeader from './components/ApiCasePageHeader.vue'
  import ApiCaseConfigSearchModal from './components/ApiCaseConfigSearchModal.vue'
  import ApiCaseExecutionTraceDrawer from './components/ApiCaseExecutionTraceDrawer.vue'
  import ApiCaseDiagnosisDrawer from './components/ApiCaseDiagnosisDrawer.vue'
  import ApiCaseInfoDetailPanel from './components/ApiCaseInfoDetailPanel.vue'
  import ApiCaseStepTable from './components/ApiCaseStepTable.vue'
  import ApiCaseOrchestrationPanel from './components/ApiCaseOrchestrationPanel.vue'
  import ApiCaseCallbackPanel from './components/ApiCaseCallbackPanel.vue'
  import { callbackRulesForStep } from './components/callback-config'
  import {
    callbackResultsForScenario,
    callbackAssertionCount,
    callbackResultsFromAssertions,
  } from './components/callback-results'
  import { latestScenarioAttempts } from './execution-results'
  import ApiCaseScenarioHeader from './components/ApiCaseScenarioHeader.vue'
  import ApiCaseScenarioWorkspace from './components/ApiCaseScenarioWorkspace.vue'
  import ApiCaseScenarioFrontPanel from './components/ApiCaseScenarioFrontPanel.vue'
  import ApiCaseRequestPanel from './components/ApiCaseRequestPanel.vue'
  import ApiCaseResponsePanel from './components/ApiCaseResponsePanel.vue'
  import ApiCasePosteriorPanel from './components/ApiCasePosteriorPanel.vue'
  import ApiCaseAssertionPanel from './components/ApiCaseAssertionPanel.vue'
  import ApiCaseRuntimeCachePanel from './components/ApiCaseRuntimeCachePanel.vue'
  import ApiCaseDataFactoryPanel from './components/ApiCaseDataFactoryPanel.vue'
  import ApiCaseScenarioNav from './components/ApiCaseScenarioNav.vue'
  import { mapWithConcurrency, useApiCaseConfigSearch } from './composables/useApiCaseConfigSearch'
  import type {
    ConfigSearchDocument,
    ConfigSearchMatch,
    ConfigSearchTarget,
  } from './composables/useApiCaseConfigSearch'
  import { useApiCaseExecution } from './composables/useApiCaseExecution'
  import { useApiCasePanelLoader } from './composables/useApiCasePanelLoader'
  import { useApiCaseSelection } from './composables/useApiCaseSelection'
  import VariableReferencePanel from '@/components/business/VariableReferencePanel.vue'
  import type { ApiCaseRevisionDetail } from '@/types/api-test/case-version'
  import { parseApiCaseRevisionPayload } from '@/types/api-test/case-revision-payload'
  import type { ApiCaseExecutionVersion } from '@/utils/api-case-revision'
  import { cloneLosslessJson } from '@/utils/lossless-json'
  import { getDataFactoryCaseConfig, getDataFactoryDatasourceAlias } from '@/api/data-factory'
  import {
    getExecutionResultDetailResolved,
    getExecutionResultList,
  } from '@/api/system/execution_result'

  const requests = createCaseRequestScope()
  let pageActive = true
  function applyScenarioPatch(patch: ScenarioPatch) {
    const index = scenarios.value.findIndex((item) => Number(item.id) === patch.id)
    if (index < 0 || caseEditLocked.value) return
    scenarios.value[index] = { ...scenarios.value[index], ...cloneLosslessJson(patch.changes) }
    if (selectedStep.value)
      parameterCacheByStep.set(String(selectedStep.value.id), cloneVersionValue(scenarios.value))
  }
  const userStore = useUserStore()

  const stepEditorRef = ref<InstanceType<typeof ApiCaseStepEditor> | null>(null)
  const scenarioEditorRef = ref<InstanceType<typeof ApiCaseScenarioEditor> | null>(null)
  const dataFactoryPanelRef = ref<InstanceType<typeof DataFactoryCaseConfigPanel> | null>(null)
  const initialRecord = cloneLosslessJson(usePageData().record) as CaseWorkspaceRecord | null
  const caseRecord = ref<CaseWorkspaceRecord>({
    id: '',
    name: '',
    front_custom: [],
    front_sql: [],
    front_headers: [],
    front_public: [],
    front_auth_config: [],
    callback_checks: [],
    posterior_sql: [],
    project_product: null,
  })
  const props = withDefaults(
    defineProps<{
      caseId?: string | number
      projectProductId?: string | number
      embedded?: boolean
    }>(),
    {
      caseId: '',
      projectProductId: '',
      embedded: false,
    }
  )
  const emit = defineEmits<{
    (event: 'close'): void
  }>()
  const route = useRoute()
  const scalarId = (value: unknown): string | number =>
    Array.isArray(value)
      ? scalarId(value[0])
      : typeof value === 'string' || typeof value === 'number'
      ? value
      : ''
  const apiCaseId = computed(() =>
    scalarId(props.caseId || route.query.case_id || route.query.id || initialRecord?.id)
  )
  const apiProjectProductId = computed(
    () =>
      caseRecord.value.project_product?.id ||
      scalarId(caseRecord.value.project_product) ||
      props.projectProductId ||
      scalarId(route.query.project_product) ||
      initialRecord?.project_product?.id ||
      ''
  )
  const defaultCaseRecord = () => ({
    id: apiCaseId.value,
    name: '',
    front_custom: [],
    front_sql: [],
    front_headers: [],
    front_public: [],
    front_auth_config: [],
    callback_checks: [],
    posterior_sql: [],
    project_product: apiProjectProductId.value ? { id: apiProjectProductId.value } : null,
  })
  caseRecord.value = defaultCaseRecord()
  const enumStore = useEnum()
  const caseVariableEnvironmentOptions = computed(() => [
    { key: COMMON_ENV_VALUE, title: '环境通用' },
    ...enumStore.environment_type,
  ])
  const versionPanelRef = ref<InstanceType<typeof ApiCaseVersionPanel> | null>(null)
  const selectedExecutionVersion = ref<ApiCaseExecutionVersion | null>(null)
  const selectedExecutionResultSummary = ref<CaseExecutionSummary | null>(null)
  const selectedCaseVersionDetail = ref<ApiCaseRevisionDetail | null>(null)
  const snapshotParametersByStep = new Map<string, ApiCaseScenario[]>()
  const liveCaseRecord = ref<CaseWorkspaceRecord | null>(null)
  const liveCaseRows = ref<ApiCaseStep[]>([])
  const caseVersionPayloadActive = ref(false)
  const caseVersionEditUnlocked = ref(false)
  const apiCaseCompareCurrentPayload = computed(() => buildApiCaseCompareCurrentPayload())
  const CONFIG_SEARCH_LIMIT = 200
  const {
    state: configSearch,
    reset: resetConfigSearch,
    search: runConfigSearch,
    setDocuments: setConfigSearchDocuments,
  } = useApiCaseConfigSearch(CONFIG_SEARCH_LIMIT)
  const jsonEditDrawer = reactive({
    visible: false,
    field: '',
    label: '',
    title: '',
    value: '',
    item: null as ApiCaseScenario | null,
  })
  const apiInfoDetailPanelRef = ref<InstanceType<typeof ApiCaseInfoDetailPanel> | null>(null)
  function openStepEditor(step: ApiCaseStep) {
    if (!ensureCaseEditable() || caseExecutionActive.value) return
    stepEditorRef.value?.open(step)
  }
  const caseSteps = ref<ApiCaseStep[]>([])
  const selectedStep = ref<ApiCaseStep | null>(null)
  const scenarios = ref<ApiCaseScenario[]>([])
  const assertionEditingAllowed = ref(true)
  const workspaceTabs = reactive({
    apiType: '2',
    apiSonType: '0',
    caseDetailsTypeKey: '2',
    tabsKey: '10',
  })
  const scenarioViewport = reactive<{
    activeCollapseKey: (string | number)[]
    mountedCollapseKeys: number[]
    expandingIndex: number
  }>({
    activeCollapseKey: [0],
    mountedCollapseKeys: [],
    expandingIndex: -1,
  })
  const panelLoading = reactive({
    collapseLoading: false,
    caseConfigLoading: false,
    caseDetailTabLoading: false,
  })
  const optionLists = reactive<CaseResourceOptions>({
    ass: [],
    textAss: [],
    caseHeadersList: [],
    headers_list: [],
    parameter_headers_list: [],
    datasourceAliasOptions: [],
    publicOptions: [],
    authConfigOptions: [],
  })

  const { saveCase, saveParameter } = useApiCaseAutoSave(
    () => caseRecord.value,
    () => scenarios.value
  )

  const {
    caseRunning,
    caseRequestPending,
    debugRunningStepId,
    debugRequestPending,
    lastTraceId,
    caseRunRefreshActive,
    startCaseRunRefresh,
    stopCaseRunRefresh,
    startCaseRunLoadingLimit,
    stopCaseRunLoadingLimit,
    startDebugRunLoadingLimit,
    stopDebugRunLoadingLimit,
    disposeExecutionTimers,
  } = useApiCaseExecution((context) => refreshCaseRunStatusByStep(context))
  const stepTableLoading = ref(false)
  const sortingSteps = ref(false)
  const caseGlobalSaving = ref(false)
  const callbackSavePending = ref(false)

  async function saveCallbackRules(rules: CallbackRuleDraft[]): Promise<boolean> {
    if (callbackSavePending.value || !ensureCaseEditable()) return false
    const caseId = apiCaseId.value
    const version = selectedCaseVersionDetail.value
    callbackSavePending.value = true
    try {
      const response = await saveCase({ id: caseId, callback_checks: rules })
      if (!response) return true
      if (!Array.isArray(response.data?.callback_checks)) {
        Message.error('服务端尚未支持回调配置，请确认后端版本及数据库迁移')
        return false
      }
      if (
        caseId !== apiCaseId.value ||
        version !== selectedCaseVersionDetail.value ||
        caseEditLocked.value
      )
        return false
      caseRecord.value.callback_checks = response.data.callback_checks
      return true
    } finally {
      callbackSavePending.value = false
    }
  }
  const caseDataFactoryCount = ref(0)
  const scenarioWorkbenchExpanded = ref(false)
  const scenarioHeaderSavingCount = ref(0)

  function changeScenarioSavingCount(saving: boolean) {
    scenarioHeaderSavingCount.value = Math.max(
      0,
      scenarioHeaderSavingCount.value + (saving ? 1 : -1)
    )
  }
  const schemaLoadingId = ref<number | null>(null)
  const assertionVerifyLoadingId = ref<number | null>(null)
  const jsonEditSaving = ref(false)
  const deprecatedRegexAssertionMethods = new Set(['p_matches', 'p_does_not_match'])
  const caseEditLocked = computed(
    () => caseVersionPayloadActive.value && !caseVersionEditUnlocked.value
  )
  const showCaseAddButton = computed(
    () => !(workspaceTabs.apiType === '1' && ['13', '15', '16'].includes(workspaceTabs.apiSonType))
  )
  const toggleScenarioWorkbench = () => {
    scenarioWorkbenchExpanded.value = !scenarioWorkbenchExpanded.value
  }
  const apiCaseDetailTitle = computed(() => {
    const id = apiCaseId.value || '-'
    const name = caseRecord.value?.name || '-'
    return `组合用例场景配置 / ${id} / ${name}`
  })
  const frontPublicCheckedValues = computed({
    get: () => mergeCheckedOptionValues(caseRecord.value.front_public, optionLists.publicOptions),
    set: (value: any[]) => {
      caseRecord.value.front_public = filterOptionalOptionValues(value, optionLists.publicOptions)
    },
  })
  const frontAuthConfigCheckedValues = computed({
    get: () =>
      mergeCheckedOptionValues(caseRecord.value.front_auth_config, optionLists.authConfigOptions),
    set: (value: any[]) => {
      caseRecord.value.front_auth_config = filterOptionalOptionValues(
        value,
        optionLists.authConfigOptions
      )
    },
  })
  const traceDrawerRef = ref<InstanceType<typeof ApiCaseExecutionTraceDrawer> | null>(null)
  const caseDiagnosisDrawerRef = ref<InstanceType<typeof ApiCaseDiagnosisDrawer> | null>(null)
  const selectedStepSummary = computed(() => {
    const step = selectedStep.value
    if (!step?.api_info) {
      return '从左侧选择接口后，可为同一个接口扩展多组场景参数、断言和执行结果'
    }
    const method = formatMethodTitle(step.api_info.method)
    const url = step.api_info.url || '-'
    const name = step.api_info.name || '未命名接口'
    return `${name} / ${method} ${url} / 可扩展多组场景参数、前后置处理、断言和结果`
  })
  const selectedRuntimeResultOutdated = computed(
    () =>
      Boolean(selectedStep.value?.runtime_result_outdated) ||
      scenarios.value.some((item: any) => item.runtime_result_outdated)
  )
  const latestScenarioExecutionLabel = computed(() => {
    const testTime =
      selectedExecutionResultSummary.value?.create_time || getLatestScenarioTestTime()
    if (!testTime) return ''
    const environment = selectedExecutionResultSummary.value
      ? selectedExecutionResultSummary.value.test_env_name ||
        formatEnvironmentText(selectedExecutionResultSummary.value.test_env)
      : ''
    const outdatedText = selectedRuntimeResultOutdated.value ? ' · 执行后配置已变更' : ''
    return `最近执行：${testTime}${
      environment && environment !== '-' ? ` · ${environment}` : ''
    }${outdatedText}`
  })
  const caseExecutionActive = computed(
    () =>
      caseRequestPending.value ||
      debugRequestPending.value ||
      scenarioHeaderSavingCount.value > 0 ||
      caseRunRefreshActive.value ||
      hasRunningCaseStep(caseSteps.value)
  )
  const dataFactoryConfigCache = reactive(new Map<string, number>())
  const parameterCacheByStep = new Map<string, ApiCaseScenario[]>()
  let latestExecutionResultData: any = null
  const {
    nextParameterLoadToken,
    invalidateParameterLoad,
    isCurrentParameterLoad,
    nextExecutionResultLoadToken,
    isCurrentExecutionResultLoad,
    invalidateExecutionResultLoad,
  } = useApiCaseSelection()
  const {
    panelLoaded,
    clearPanelCache,
    markPanelLoaded,
    runWithPanelLoading: runCaseDetailTabLoading,
  } = useApiCasePanelLoader(panelLoading)
  let caseConfigLoadingCount = 0

  async function runCaseConfigLoading(task: () => void | Promise<void>) {
    const isCurrent = requests.capture()
    caseConfigLoadingCount += 1
    panelLoading.caseConfigLoading = true
    try {
      await task()
    } finally {
      if (isCurrent()) {
        caseConfigLoadingCount = Math.max(0, caseConfigLoadingCount - 1)
        panelLoading.caseConfigLoading = caseConfigLoadingCount > 0
      }
    }
  }

  const sqlEnvironmentOptions = computed(() =>
    (enumStore.environment_type || []).map((item: any) => ({
      label: item.title,
      value: item.key,
    }))
  )

  function formatMethodTitle(method: any) {
    const methods = Array.isArray(enumStore.method) ? enumStore.method : []
    const found = methods.find((item: any) => item.key === method)
    return found?.title || method || '-'
  }

  function getLatestScenarioTestTime() {
    const rows = Array.isArray(scenarios.value) ? scenarios.value : []
    for (let index = rows.length - 1; index >= 0; index--) {
      const row = rows[index]
      const testTime = row?.result_data?.test_time || row?.test_time
      if (testTime) return testTime
    }
    return ''
  }

  function isActiveCollapseItem(index: number) {
    return scenarioViewport.activeCollapseKey.some(
      (key: string | number) => String(key) === String(index)
    )
  }

  function isMountedCollapseItem(index: number) {
    return scenarioViewport.mountedCollapseKeys.some(
      (key: string | number) => String(key) === String(index)
    )
  }

  function mountCollapseItem(index: number) {
    if (!isMountedCollapseItem(index)) {
      scenarioViewport.mountedCollapseKeys.push(index)
    }
  }

  function deferMountCollapseItem(index: number) {
    const isCurrent = requests.capture()
    scenarioViewport.expandingIndex = index
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        if (!isCurrent() || !isActiveCollapseItem(index)) {
          return
        }
        mountCollapseItem(index)
        scenarioViewport.expandingIndex = -1
      })
    })
  }

  function isActiveCaseDetailTab(caseDetailsTypeKey: string, tabsKey: string) {
    return (
      workspaceTabs.caseDetailsTypeKey === caseDetailsTypeKey && workspaceTabs.tabsKey === tabsKey
    )
  }

  function isRuntimeResultTab() {
    return workspaceTabs.caseDetailsTypeKey === '2' || workspaceTabs.caseDetailsTypeKey === '6'
  }

  async function switchType(key: any) {
    if (key === '1') {
      workspaceTabs.apiSonType = '15'
    } else if (key === '3') {
      workspaceTabs.apiSonType = '31'
    }
    workspaceTabs.apiType = key
    if (key !== '2') {
      await runCaseConfigLoading(() => ensureActiveCasePanelLoaded())
    }
  }

  function selectExecutionVersion(version: ApiCaseExecutionVersion) {
    requests.invalidate()
    invalidateParameterLoad()
    invalidateExecutionResultLoad()
    clearPanelCache()
    stepEditorRef.value?.close()
    scenarioEditorRef.value?.close()
    jsonEditDrawer.visible = false
    stepTableLoading.value = false
    selectedExecutionVersion.value = version
    caseVersionEditUnlocked.value = false
    clearDisplayedRuntimeResults()
  }

  function showVersionDetail(detail: ApiCaseRevisionDetail) {
    if (selectedExecutionVersion.value?.revisionId !== detail.id) return
    caseVersionEditUnlocked.value = false
    selectedCaseVersionDetail.value = detail
    applyCaseVersionPayload(detail.payload, detail.api_revision_dependencies)
    void refreshSelectedRuntimeResult()
  }

  function showCurrentConfiguration() {
    requests.invalidate()
    invalidateParameterLoad()
    invalidateExecutionResultLoad()
    clearPanelCache()
    jsonEditDrawer.visible = false
    selectedCaseVersionDetail.value = null
    caseVersionPayloadActive.value = false
    caseVersionEditUnlocked.value = false
    snapshotParametersByStep.clear()
    if (liveCaseRecord.value) {
      setCaseRecord(normalizeCaseRecord(liveCaseRecord.value))
    }
    const isCurrent = requests.capture()
    void ensureCaseRecord().then(async () => {
      if (!isCurrent() || caseVersionPayloadActive.value) return
      await Promise.all([doRefresh(), loadCaseDataFactoryCount()])
      if (isCurrent()) await refreshSelectedRuntimeResult()
    }).catch(() => {
      // 公共请求层展示加载错误，不以空记录覆盖已有 Case 配置。
    })
  }

  function ensureCaseEditable() {
    if (!caseEditLocked.value) return true
    Message.warning('当前正在查看只读快照，请先在版本栏迁出到编辑态后再修改')
    return false
  }

  function cloneVersionValue<T>(value: T): T {
    return value == null ? value : cloneLosslessJson(value)
  }

  function pickCaseEditablePayload(record: Record<string, any>) {
    const fields = [
      'id',
      'name',
      'front_custom',
      'front_sql',
      'front_headers',
      'front_public',
      'front_auth_config',
      'callback_checks',
      'posterior_sql',
      'parametrize',
    ]
    return fields.reduce<Record<string, any>>((result, field) => {
      result[field] = cloneVersionValue(record?.[field])
      return result
    }, {})
  }

  function pickCaseStepEditablePayload(row: Record<string, any>, index: number) {
    const apiInfoId = getSnapshotApiInfoId(row) || getApiInfoId(row)
    const fields = [
      'id',
      'logical_id',
      'case_sort',
      'posterior_sql',
      'api_info_revision_id',
      'execution_config',
    ]
    const step = fields.reduce<Record<string, any>>((result, field) => {
      result[field] = cloneVersionValue(row?.[field])
      return result
    }, {})
    step.id = step.id || `step-${index + 1}`
    step.logical_id = step.logical_id || `step-${step.id}`
    step.case_sort = step.case_sort ?? index + 1
    if (!Object.keys(step.execution_config || {}).length) {
      delete step.execution_config
    }
    step.api_info_id = apiInfoId
    step.api_case_detailed_parameter = getCurrentStepParameters(row)
    return step
  }

  function getCurrentStepParameters(row: Record<string, any>) {
    const snapshotParameters = snapshotParametersByStep.get(String(row?.id))
    if (snapshotParameters) return cloneVersionValue(snapshotParameters)
    if (Array.isArray(row?.api_case_detailed_parameter)) {
      return cloneVersionValue(row.api_case_detailed_parameter)
    }
    if (selectedStep.value && String(selectedStep.value.id) === String(row?.id)) {
      return cloneVersionValue(scenarios.value || [])
    }
    return []
  }

  function buildApiCaseCompareCurrentPayload() {
    return {
      api_case: pickCaseEditablePayload(caseRecord.value || {}),
      api_case_detailed: (Array.isArray(caseSteps.value) ? caseSteps.value : []).map(
        (row: Record<string, any>, index: number) => pickCaseStepEditablePayload(row, index)
      ),
    }
  }

  function getSnapshotApiInfoId(step: Record<string, any>) {
    return step.api_info ?? step.api_info_id ?? ''
  }

  function applyCaseVersionPayload(
    payload: Record<string, any>,
    dependencies: ApiCaseRevisionDetail['api_revision_dependencies'] = []
  ) {
    if (!payload || typeof payload !== 'object') return
    requests.invalidate()
    invalidateParameterLoad()
    invalidateExecutionResultLoad()
    clearPanelCache()
    stepTableLoading.value = false
    if (!caseVersionPayloadActive.value) {
      liveCaseRecord.value = cloneVersionValue(caseRecord.value)
      liveCaseRows.value = cloneVersionValue(Array.isArray(caseSteps.value) ? caseSteps.value : [])
    }
    caseVersionPayloadActive.value = true
    const currentRows = liveCaseRows.value
    const revisionPayload = parseApiCaseRevisionPayload(payload)
    const casePayload = revisionPayload.api_case
    const steps = revisionPayload.api_case_detailed
    dataFactoryConfigCache.clear()
    setCaseDataFactoryCount(0)
    revisionPayload.dependencies.data_factory_configs.forEach((config) => {
      if (Number(config.source_type) === 1) {
        setCaseDataFactoryCount(caseDataFactoryCount.value + 1)
        return
      }
      if (Number(config.source_type) !== 3) return
      const sourceId = String(config.source_id || '')
      if (!sourceId) return
      dataFactoryConfigCache.set(sourceId, (dataFactoryConfigCache.get(sourceId) || 0) + 1)
    })
    const dependencyByLogicalId = new Map(dependencies.map((item) => [item.step_logical_id, item]))
    snapshotParametersByStep.clear()
    const rows = steps.map((step: any, index: number) => {
      const apiInfoId = getSnapshotApiInfoId(step)
      const sourceId = String(step.id || '').replace(/^step-/, '')
      const current: Partial<ApiCaseStep> =
        currentRows.find((row: any) => String(row.id) === sourceId) ||
        currentRows.find((row: any) => String(getApiInfoId(row)) === String(apiInfoId)) ||
        {}
      const apiInfoSnapshot = step.api_info_snapshot || {}
      const apiRuntimePayload = apiInfoSnapshot.payload?.api_info || {}
      const dependency = dependencyByLogicalId.get(step.logical_id)
      const row = {
        ...current,
        ...cloneVersionValue(step),
        execution_config: cloneVersionValue(step.execution_config || {}),
        id: step.id || current.id || `version-step-${index + 1}`,
        api_info: {
          ...(current.api_info || {}),
          ...cloneVersionValue(apiRuntimePayload),
          id: apiInfoId,
          name:
            apiInfoSnapshot.name ||
            current.api_info?.name ||
            dependency?.api_info_name ||
            `接口 ${apiInfoId}`,
        },
        api_info_snapshot_source_missing: Boolean(dependency && dependency.status !== 'available'),
        pinned_api_info_revision: step.api_info_revision_id,
      }
      snapshotParametersByStep.set(
        String(row.id),
        cloneVersionValue(step.api_case_detailed_parameter || [])
      )
      return normalizeCaseDetailRow(row)
    })
    setCaseRecord(
      normalizeCaseRecord({
        ...caseRecord.value,
        ...cloneVersionValue(casePayload),
        callback_checks: cloneVersionValue(casePayload.callback_checks || []),
      })
    )
    optionLists.caseHeadersList = caseRecord.value.front_headers
    caseSteps.value = rows
    if (rows.length) select(rows[0])
    else {
      selectedStep.value = null
      scenarios.value = []
    }
  }

  function executeSelectedVersion(version: ApiCaseExecutionVersion) {
    selectedExecutionVersion.value = version
    caseRun(null, version)
  }

  async function ensureCasePanelLoaded(panelKey: string, record: any = selectedStep.value) {
    if (panelKey === 'case-public') {
      await loadCasePublicOptions()
    } else if (panelKey === 'case-auth') {
      await loadCaseAuthOptions()
    } else if (panelKey === 'case-headers') {
      await loadCaseHeaders()
    } else if (panelKey === 'datasource-aliases') {
      await loadDatasourceAliases()
    } else if (panelKey === 'parameter-headers') {
      await loadParameterHeaders(record?.api_info?.project_product)
    }
  }

  async function ensureActiveCasePanelLoaded(record: any = selectedStep.value) {
    if (workspaceTabs.apiType === '1') {
      if (workspaceTabs.apiSonType === '15') {
        await ensureCasePanelLoaded('case-public', record)
      } else if (workspaceTabs.apiSonType === '16') {
        await ensureCasePanelLoaded('case-auth', record)
      } else if (workspaceTabs.apiSonType === '12') {
        await ensureCasePanelLoaded('datasource-aliases', record)
      } else if (workspaceTabs.apiSonType === '13') {
        await ensureCasePanelLoaded('case-headers', record)
      }
      return
    }
    if (workspaceTabs.apiType === '3') {
      if (workspaceTabs.apiSonType === '31') {
        await ensureCasePanelLoaded('datasource-aliases', record)
      }
      return
    }
    if (workspaceTabs.apiType !== '2') {
      return
    }
    if (workspaceTabs.caseDetailsTypeKey === '0' && workspaceTabs.tabsKey === '00') {
      await ensureCasePanelLoaded('parameter-headers', record)
    }
    if (['10', '41'].includes(String(workspaceTabs.tabsKey))) {
      await ensureCasePanelLoaded('datasource-aliases', record)
    }
    if (isRuntimeResultTab()) {
      await refreshSelectedRuntimeResult()
    }
  }

  function hasConfigValue(value: any) {
    if (value === undefined || value === null) return false
    if (typeof value === 'string') {
      const text = value.trim()
      return text !== '' && text !== '{}' && text !== '[]'
    }
    if (Array.isArray(value)) return value.length > 0
    if (typeof value === 'object') return Object.keys(value).length > 0
    return Boolean(value)
  }

  function hasDisplayValue(value: any) {
    if (value === undefined || value === null || value === '') return false
    if (Array.isArray(value)) return value.length > 0
    if (typeof value === 'object') return Object.keys(value).length > 0
    return true
  }

  function configuredItemCount(value: any) {
    if (!hasConfigValue(value)) return 0
    if (Array.isArray(value)) return value.length
    return 1
  }

  function resultItemCount(value: any) {
    if (!hasDisplayValue(value)) return 0
    if (Array.isArray(value)) return value.length
    if (typeof value === 'object') return Object.keys(value).length
    return 1
  }

  function setCaseDataFactoryCount(count: number) {
    caseDataFactoryCount.value = Math.max(0, Number(count) || 0)
  }

  async function loadCaseDataFactoryCount() {
    const isCurrent = requests.capture()
    if (!apiCaseId.value) {
      if (!isCurrent()) return
      setCaseDataFactoryCount(0)
      return
    }
    try {
      const res = await getDataFactoryCaseConfig({ source_type: 1, source_id: apiCaseId.value })
      if (!isCurrent()) return
      setCaseDataFactoryCount(Array.isArray(res.data) ? res.data.length : 0)
    } catch (error) {
      console.log(error)
    }
  }

  function getCaseConfigCount(
    type: 'public' | 'auth' | 'custom' | 'frontSql' | 'factory' | 'headers' | 'posteriorSql'
  ) {
    if (type === 'public') return configuredItemCount(frontPublicCheckedValues.value)
    if (type === 'auth') return configuredItemCount(frontAuthConfigCheckedValues.value)
    if (type === 'custom') return configuredItemCount(caseRecord.value?.front_custom)
    if (type === 'frontSql') return configuredItemCount(caseRecord.value?.front_sql)
    if (type === 'factory') return caseDataFactoryCount.value
    if (type === 'headers') return configuredItemCount(caseRecord.value?.front_headers)
    return configuredItemCount(caseRecord.value?.posterior_sql)
  }

  function setScenarioDataFactoryCount(id: number | string, count: number) {
    dataFactoryConfigCache.set(String(id), Math.max(0, Number(count) || 0))
  }

  async function loadScenarioDataFactoryCounts(items: any[]) {
    const isCurrent = requests.capture()
    await Promise.allSettled(
      items.map(async (item) => {
        const cacheKey = String(item?.id || '')
        if (!cacheKey || dataFactoryConfigCache.has(cacheKey)) return
        const res = await getDataFactoryCaseConfig({ source_type: 3, source_id: item.id })
        if (!isCurrent()) return
        setScenarioDataFactoryCount(item.id, Array.isArray(res.data) ? res.data.length : 0)
      })
    )
  }

  function getScenarioTabCount(
    item: any,
    tab:
      | 'front'
      | 'request'
      | 'response'
      | 'posterior'
      | 'assertion'
      | 'cache'
      | 'factory'
      | 'assertionResult'
  ) {
    if (tab === 'front') {
      return (
        configuredItemCount(item?.front_sql) +
        configuredItemCount(item?.front_func) +
        (dataFactoryConfigCache.get(String(item?.id)) || 0)
      )
    }
    if (tab === 'request') {
      const hasBody =
        getScenarioBodyType(item) !== 'none' || hasConfigValue(item?.body_config) ? 1 : 0
      return (
        configuredItemCount(item?.headers) +
        configuredItemCount(item?.params) +
        hasBody +
        configuredItemCount(item?.sse_config)
      )
    }
    if (tab === 'response') return hasConfigValue(item?.result_data) ? 1 : 0
    if (tab === 'posterior') {
      return (
        configuredItemCount(item?.posterior_response) +
        configuredItemCount(item?.posterior_response_text) +
        configuredItemCount(item?.posterior_sql) +
        configuredItemCount(item?.posterior_sleep) +
        configuredItemCount(item?.posterior_file) +
        configuredItemCount(item?.posterior_func)
      )
    }
    if (tab === 'assertion') {
      return (
        configuredItemCount(item?.ass_json_all) +
        configuredItemCount(item?.ass_text_all) +
        configuredItemCount(item?.ass_jsonpath) +
        configuredItemCount(item?.ass_sql) +
        configuredItemCount(item?.ass_schema) +
        configuredItemCount(item?.ass_general) +
        callbackRulesForStep(caseRecord.value.callback_checks || [], selectedStep.value?.id).length
      )
    }
    if (tab === 'cache') return resultItemCount(item?.result_data?.cache_data)
    if (tab === 'factory') {
      return resultItemCount(item?.result_data?.data_factory_cache_data)
    }
    return (
      getAssertionResultData(item).length +
      callbackAssertionCount(getCallbackAssertionResults(item))
    )
  }

  function getResultRequestParams(item: any) {
    const result = item?.result_data || {}
    return result.response?.request_params ?? result.request?.params
  }

  function getResultRequestBody(item: any) {
    const result = item?.result_data || {}
    return (
      result.response?.request_body ??
      result.request?.request_body ??
      result.request?.data ??
      result.request?.json
    )
  }

  function getResultRequestFiles(item: any) {
    const result = item?.result_data || {}
    return result.response?.request_file ?? result.request?.request_files ?? result.request?.file
  }

  function scenarioProtocolLabel(value: any) {
    const protocol = String(value || 'http').toLowerCase()
    const labels: Record<string, string> = {
      http: 'HTTP',
      sse: 'SSE',
      websocket: 'WebSocket',
      grpc: 'gRPC',
      mcp: 'MCP',
    }
    return labels[protocol] || String(value || '-').toUpperCase()
  }

  function scenarioBodyTypeLabel(value: any) {
    const bodyType = String(value || 'none').toLowerCase()
    const labels: Record<string, string> = {
      none: '无请求体',
      json: 'JSON',
      form: 'Form',
      raw: 'Raw',
      multipart: 'Multipart',
    }
    return labels[bodyType] || String(value || '-')
  }

  function responseHeaderValue(headers: any, name: string) {
    if (!headers || typeof headers !== 'object' || Array.isArray(headers)) return ''
    const targetName = name.toLowerCase()
    const entry = Object.entries(headers).find(([key]) => key.toLowerCase() === targetName)
    return entry?.[1] === undefined || entry?.[1] === null ? '' : String(entry[1])
  }

  function hasResultResponseJson(item: any) {
    const value = item?.result_data?.response?.json
    return value !== undefined && value !== null && value !== ''
  }

  function getScenarioResponseMode(item: any) {
    const mode =
      item?.result_data?.response?.response_mode ||
      item?.result_data?.response?.request_protocol_type ||
      getScenarioProtocolType(item)
    return String(mode || 'http').toLowerCase()
  }

  function isScenarioResponseMode(item: any, mode: string) {
    return getScenarioResponseMode(item) === mode
  }

  function getResultResponseTabKey(item: any) {
    if (isScenarioResponseMode(item, 'sse')) return '26'
    if (isScenarioResponseMode(item, 'websocket')) return '27'
    return hasResultResponseJson(item) ? '23' : '24'
  }

  async function switchApiInfoType(key: any, item: any) {
    if (panelLoading.caseDetailTabLoading) {
      return
    }
    await runCaseDetailTabLoading(async () => {
      workspaceTabs.caseDetailsTypeKey = key
      if (key === '0') {
        if (hasConfigValue(item?.body_config) || getScenarioBodyType(item) !== 'none') {
          workspaceTabs.tabsKey = '02'
        } else if (hasConfigValue(item?.params)) {
          workspaceTabs.tabsKey = '01'
        } else if (hasConfigValue(item?.headers)) {
          workspaceTabs.tabsKey = '00'
        } else {
          workspaceTabs.tabsKey = '02'
        }
      } else if (key === '1') {
        await switchFrontProcessTab(item)
      } else if (key === '2') {
        workspaceTabs.tabsKey = getResultResponseTabKey(item)
      } else if (key === '3') {
        if (item.ass_sql && item.ass_sql.length > 0) {
          workspaceTabs.tabsKey = '35'
          assertionEditingAllowed.value = true
        } else if (item.ass_general && item.ass_general.length > 0) {
          workspaceTabs.tabsKey = '32'
          assertionEditingAllowed.value = true
        } else if (item.ass_jsonpath && item.ass_jsonpath.length > 0) {
          workspaceTabs.tabsKey = '31'
          assertionEditingAllowed.value = true
        } else if (item.ass_text_all) {
          workspaceTabs.tabsKey = '33'
          assertionEditingAllowed.value = false
        } else if (item.ass_schema) {
          workspaceTabs.tabsKey = '34'
          assertionEditingAllowed.value = false
        } else if (
          callbackRulesForStep(caseRecord.value.callback_checks || [], selectedStep.value?.id)
            .length
        ) {
          workspaceTabs.tabsKey = '36'
          assertionEditingAllowed.value = false
        } else {
          workspaceTabs.tabsKey = '30'
          assertionEditingAllowed.value = false
        }
      } else if (key === '4') {
        if (hasConfigValue(item.posterior_response)) {
          workspaceTabs.tabsKey = '40'
        } else if (hasConfigValue(item.posterior_response_text)) {
          workspaceTabs.tabsKey = '44'
        } else if (hasConfigValue(item.posterior_sql)) {
          workspaceTabs.tabsKey = '41'
        } else if (hasConfigValue(item.posterior_sleep)) {
          workspaceTabs.tabsKey = '42'
        } else if (hasConfigValue(item.posterior_func)) {
          workspaceTabs.tabsKey = '43'
        } else {
          workspaceTabs.tabsKey = '40'
        }
        assertionEditingAllowed.value = !['42', '43'].includes(String(workspaceTabs.tabsKey))
      } else if (key === '5') {
        workspaceTabs.tabsKey = '50'
      }
      await ensureActiveCasePanelLoaded(item)
      if (key === '2') {
        workspaceTabs.tabsKey = getResultResponseTabKey(item)
      }
    })
  }

  async function switchFrontProcessTab(item: any) {
    if (item?.front_sql && item.front_sql.length > 0) {
      workspaceTabs.tabsKey = '10'
      assertionEditingAllowed.value = true
      return
    }
    if (item?.front_func) {
      workspaceTabs.tabsKey = '11'
      assertionEditingAllowed.value = false
      return
    }
    try {
      let dataFactoryConfigCount = dataFactoryConfigCache.get(String(item.id))
      if (dataFactoryConfigCount === undefined) {
        const res = await getDataFactoryCaseConfig({ source_type: 3, source_id: item.id })
        dataFactoryConfigCount = Array.isArray(res.data) ? res.data.length : 0
        setScenarioDataFactoryCount(item.id, dataFactoryConfigCount)
      }
      if (dataFactoryConfigCount > 0) {
        workspaceTabs.tabsKey = '12'
        assertionEditingAllowed.value = true
        return
      }
    } catch (error) {
      console.log(error)
    }
    workspaceTabs.tabsKey = '10'
    assertionEditingAllowed.value = true
  }

  async function switchSonType(key: any) {
    workspaceTabs.apiSonType = key
    await runCaseConfigLoading(() => ensureActiveCasePanelLoaded())
  }

  function fillDefaultFunc(item: any, key: string | number) {
    if (caseEditLocked.value) return
    if (!item) return
    if (key === '11' && !item.front_func) {
      item.front_func = FRONT_FUNC_TEMPLATE
    } else if (key === '43' && !item.posterior_func) {
      item.posterior_func = POSTERIOR_FUNC_TEMPLATE
    }
  }

  async function tabsChange(key: string | number, item: any = null) {
    if (panelLoading.caseDetailTabLoading) {
      return
    }
    if (isRuntimeResultTab()) {
      workspaceTabs.tabsKey = String(key)
      return
    }
    await runCaseDetailTabLoading(async () => {
      workspaceTabs.tabsKey = String(key)
      fillDefaultFunc(item, key)
      assertionEditingAllowed.value = !(
        key === '30' ||
        key === '42' ||
        key === '33' ||
        key === '43' ||
        key === '11'
      )
      await ensureActiveCasePanelLoaded(item)
    })
  }

  function addData() {
    if (!ensureCaseEditable()) return
    if (workspaceTabs.apiType == '2') {
      addApiInfo()
      return
    }
    if (workspaceTabs.apiSonType === '11') {
      caseRecord.value.front_custom.push({ key: '', value: '', test_envs: [] })
    } else if (workspaceTabs.apiSonType === '12') {
      caseRecord.value.front_sql.push({ key: '', value: '', datasource_alias: null, test_envs: [] })
    } else if (workspaceTabs.apiSonType === '14') {
      dataFactoryPanelRef.value?.open()
    } else if (workspaceTabs.apiSonType === '31') {
      caseRecord.value.posterior_sql.push({
        key: '',
        value: '',
        datasource_alias: null,
        test_envs: [],
      })
    }
  }

  function doResetSearch() {
    if (props.embedded) {
      emit('close')
      return
    }
    window.history.back()
  }

  function setSchema(id: number) {
    if (!ensureCaseEditable()) return
    if (schemaLoadingId.value) return
    const stepId = selectedStep.value?.id
    const isCurrent = requests.capture()
    schemaLoadingId.value = id
    putSetSchema(id)
      .then((res) => {
        Message.success(res.msg)
        if (stepId && isCurrent() && String(selectedStep.value?.id) === String(stepId))
          void doRefreshParameter(stepId, { force: true })
      })
      .catch(console.log)
      .finally(() => {
        schemaLoadingId.value = null
      })
  }

  function parseAssertionJsonValue(label: string, value: any) {
    if (value === null || value === undefined || value === '') {
      return null
    }
    if (typeof value === 'object') {
      return value
    }
    const parsedValue = formatJsonObj(label, value)
    if (parsedValue === false) {
      throw new Error(`${label}格式不正确`)
    }
    return parsedValue
  }

  function getAssertionResultData(item: any) {
    if (Array.isArray(item?.__assertion_verify_result)) {
      return item.__assertion_verify_result.filter((assertion: any) => assertion.source_type !== 'assertion_group')
    }
    return Array.isArray(item?.result_data?.ass)
      ? item.result_data.ass.filter((assertion: any) => !assertion.callback && assertion.source_type !== 'assertion_group')
      : []
  }

  function getCallbackAssertionResults(item: any) {
    return callbackResultsFromAssertions(
      Array.isArray(item?.result_data?.ass) ? item.result_data.ass : [],
      Array.isArray(item?.result_data?.callback_results) ? item.result_data.callback_results : []
    )
  }

  function getAssertionVerifySignature(item: any) {
    return JSON.stringify([
      Number(userStore.selected_environment ?? 0),
      item.ass_json_all,
      item.ass_text_all,
      item.ass_jsonpath,
      item.ass_schema,
      item.ass_general,
      item.ass_sql,
    ])
  }

  function isAssertionVerifyStale(item: any) {
    return (
      Boolean(item?.__assertion_verify_result) &&
      (Boolean(item.__assertion_verify_stale) ||
        item.__assertion_verify_signature !== getAssertionVerifySignature(item))
    )
  }

  function clearAssertionVerifyResults() {
    scenarios.value.forEach((item: any) => {
      item.__assertion_verify_result = null
      item.__assertion_verify_signature = null
      item.__assertion_verify_stale = false
      item.__assertion_compare_open = false
    })
  }

  async function verifyAssertions(item: any) {
    if (!item?.id || assertionVerifyLoadingId.value !== null) return
    let assJsonAll: any
    let assSchema: any
    try {
      assJsonAll = parseAssertionJsonValue('JSON一致断言', item.ass_json_all)
      assSchema = parseAssertionJsonValue('结构化断言', item.ass_schema)
    } catch {
      return
    }

    assertionVerifyLoadingId.value = item.id
    const verifySignature = getAssertionVerifySignature(item)
    const isCurrent = requests.capture(),
      environment = userStore.selected_environment
    try {
      const verifyPayload = {
        id: item.id,
        test_env: Number(userStore.selected_environment ?? 0),
        assertions: {
          ass_json_all: assJsonAll,
          ass_text_all: item.ass_text_all || null,
          ass_jsonpath: normalizeAssJsonpath(item.ass_jsonpath),
          ass_schema: assSchema,
          ass_general: normalizeAssGeneral(item.ass_general),
          ass_sql: normalizeAssSql(item.ass_sql),
        },
      }
      const res = await postVerifyApiCaseAssertions(verifyPayload)
      if (!isCurrent() || environment !== userStore.selected_environment) return
      const target = scenarios.value.find((scenario) => scenario.id === item.id)
      if (!target) return
      Object.assign(target, {
        __assertion_verify_result: res.data.assertions,
        __assertion_verify_signature: verifySignature,
        __assertion_verify_stale: false,
        __assertion_compare_open: true,
      })
      item.__assertion_verify_result = res.data.assertions
      item.__assertion_verify_signature = verifySignature
      item.__assertion_verify_stale = false
      item.__assertion_compare_open = true
      if (res.data.passed) {
        Message.success('全部断言验证通过')
      } else {
        Message.error(`断言验证完成，共 ${res.data.failed_count} 项未通过`)
      }
    } catch (error) {
      console.log(error)
    } finally {
      assertionVerifyLoadingId.value = null
    }
  }

  function parameterEditing(item: ApiCaseScenario) {
    if (ensureCaseEditable() && selectedStep.value)
      scenarioEditorRef.value?.open(selectedStep.value, 'edit', item)
  }
  function parameterCopy(item: ApiCaseScenario) {
    if (ensureCaseEditable() && selectedStep.value)
      scenarioEditorRef.value?.open(selectedStep.value, 'copy', item)
  }
  function addApiInfo() {
    if (ensureCaseEditable()) stepEditorRef.value?.open()
  }
  function addParameter() {
    if (ensureCaseEditable() && selectedStep.value)
      scenarioEditorRef.value?.open(selectedStep.value)
  }
  function onScenarioSaved(stepId: string | number) {
    parameterCacheByStep.delete(String(stepId))
    if (String(selectedStep.value?.id) === String(stepId))
      void doRefreshParameter(Number(stepId), { force: true })
  }
  function parameterDelete(item: any) {
    if (!ensureCaseEditable()) return
    const stepId = selectedStep.value?.id
    const isCurrent = requests.capture()
    Modal.confirm({
      title: '提示',
      content: '确定要删除此数据吗？',
      cancelText: '取消',
      okText: '删除',
      onBeforeOk: () => {
        return deleteApiCaseDetailedParameter(item.id)
          .then((res) => {
            Message.success(res.msg)
            if (stepId && isCurrent()) onScenarioSaved(stepId)
          })
          .then(() => true)
          .catch(() => false)
      },
    })
  }

  function removeFrontSql1(item: any, index: number, refreshScenario = true) {
    if (!ensureCaseEditable()) return
    item.splice(index, 1)

    upDataCase({ refreshScenario })
  }

  function openJsonEditDrawer(field: string, label: string, item: ApiCaseScenario) {
    if (!ensureCaseEditable() || jsonEditSaving.value) return
    jsonEditDrawer.visible = true
    jsonEditDrawer.field = field
    jsonEditDrawer.label = label
    jsonEditDrawer.title = `${label} JSON 编辑`
    jsonEditDrawer.item = item
    const raw = Object.entries(item).find(([key]) => key === field)?.[1]
    jsonEditDrawer.value = typeof raw === 'string' ? raw : raw == null ? '' : formatJson(raw) ?? ''
  }

  async function saveJsonEditDrawer(value = jsonEditDrawer.value) {
    if (!ensureCaseEditable() || jsonEditSaving.value) return
    const item = jsonEditDrawer.item,
      field = jsonEditDrawer.field
    if (!item || !field) return
    const isCurrent = requests.capture(),
      targetId = item.id
    const parsed = ['ass_json_all', 'ass_schema'].includes(field)
      ? formatJsonObj(field, value)
      : value
    if (parsed === false) return
    jsonEditSaving.value = true
    try {
      await saveParameter({ id: targetId, [field]: parsed })
      if (!isCurrent()) return
      applyScenarioPatch({ id: targetId, changes: { [field]: value } })
      if (jsonEditDrawer.item?.id === targetId && jsonEditDrawer.field === field)
        jsonEditDrawer.visible = false
    } catch {
      // 保留抽屉草稿，允许重试。
    } finally {
      jsonEditSaving.value = false
    }
  }

  function changeHeaders(selectedValues: any) {
    if (!ensureCaseEditable()) return
    const value = {
      id: caseRecord.value.id,
      front_headers: selectedValues,
    }
    saveCase(value)
      .then((res) => {
        if (!res) return
        Message.success(res.msg)
        doRefresh()
      })
      .catch(console.log)
  }

  async function changeCaseGlobalOptions() {
    if (!ensureCaseEditable()) return
    if (caseGlobalSaving.value) return
    caseGlobalSaving.value = true
    const frontPublic = filterOptionalOptionValues(
      caseRecord.value.front_public,
      optionLists.publicOptions
    )
    const frontAuthConfig = filterOptionalOptionValues(
      caseRecord.value.front_auth_config,
      optionLists.authConfigOptions
    )
    caseRecord.value.front_public = frontPublic
    caseRecord.value.front_auth_config = frontAuthConfig
    try {
      const res = await saveCase({
        id: caseRecord.value.id,
        front_public: frontPublic,
        front_auth_config: frontAuthConfig,
      })
      if (res) Message.success(res.msg)
    } catch (error) {
      console.log(error)
    } finally {
      caseGlobalSaving.value = false
    }
  }

  function filterOptionalOptionValues(values: any[], options: any[]) {
    const disabledValues = new Set(
      (options || []).filter((item) => item.disabled).map((item) => item.value)
    )
    return (values || []).filter((item) => !disabledValues.has(item))
  }

  function mergeCheckedOptionValues(values: any[], options: any[]) {
    const result = new Set(values || [])
    ;(options || []).forEach((item) => {
      if (item.disabled) result.add(item.value)
    })
    return Array.from(result)
  }

  function getEnumTitle(options: any, value: any, fallback = '-') {
    if (value === null || value === undefined || value === '') return fallback
    if (!Array.isArray(options)) return fallback
    return (
      options[Number(value)]?.title ||
      options.find((item: any) => String(item.key) === String(value))?.title ||
      fallback
    )
  }

  function formatEnvironmentText(value: any) {
    if (value === null || value === undefined || value === '') return '环境通用'
    return getEnumTitle(enumStore.environment_type, value, `环境${value}`)
  }

  function getVariableEnvironmentValue(item: any) {
    return toEnvironmentSelectValue(item?.test_envs)
  }

  function setVariableEnvironmentValue(value: any, item: any) {
    item.test_envs = normalizeEnvironmentValues(normalizeEnvironmentSelectChange(value))
  }

  function normalizeEnvironmentList(value: any) {
    return Array.isArray(value)
      ? value
      : value === null || value === undefined || value === ''
      ? []
      : [value]
  }

  function formatDefaultStatusText(status: any) {
    return Number(status) === 1 ? '默认开启' : '可选'
  }

  function upDataCase(options: { refreshScenario?: boolean } = {}) {
    if (!ensureCaseEditable()) return
    saveCase({
      id: caseRecord.value.id,
      name: caseRecord.value.name,
      posterior_sql: caseRecord.value.posterior_sql,
      front_sql: caseRecord.value.front_sql,
      front_custom: caseRecord.value.front_custom,
      front_headers: caseRecord.value.front_headers,
      front_public: caseRecord.value.front_public,
      front_auth_config: caseRecord.value.front_auth_config,
    })
      .then((res) => {
        if (!res) return
        Message.success(res.msg)
        if (options.refreshScenario !== false) {
          doRefresh()
        }
      })
      .catch(console.log)
  }

  function upDataCaseWithoutScenarioRefresh() {
    upDataCase({ refreshScenario: false })
  }

  const protocolSavingId = ref<number | null>(null)
  async function saveProtocolExpectation(item: ApiCaseScenario, value: import('@/types/api-test/case-parameter').ApiProtocolExpectation) {
    if (!ensureCaseEditable() || protocolSavingId.value !== null) return
    const id = item.id
    const isCurrent = requests.capture()
    protocolSavingId.value = id
    try {
      const response = await saveParameter({id, protocol_expectation: value})
      if (!response || !isCurrent()) return
      const current = scenarios.value.find(scenario => scenario.id === id)
      if (current) {
        applyScenarioPatch({id, changes: {body_config: {...current.body_config, protocol_expectation: value}}})
      }
      Message.success(response.msg)
    } catch {
      // 保存失败保留协议断言表单草稿，允许重试。
    } finally {
      protocolSavingId.value = null
    }
  }

  function blurSave(key: string, item: unknown, id: number) {
    if (!ensureCaseEditable()) return null
    if (
      [
        'ass_json_all',
        'ass_text_all',
        'ass_jsonpath',
        'ass_schema',
        'ass_general',
        'ass_sql',
      ].includes(key)
    ) {
      const currentItem = scenarios.value.find((scenario: any) => scenario.id === id)
      if (
        currentItem?.__assertion_verify_result &&
        currentItem.__assertion_verify_signature !== getAssertionVerifySignature(currentItem)
      ) {
        currentItem.__assertion_verify_stale = true
      }
    }
    const not_serialize = [
      'url',
      'headers',
      'posterior_sleep',
      'posterior_func',
      'front_func',
      'ass_text_all',
      'params',
    ]
    const in_serialize = ['ass_json_all', 'ass_schema']
    const payload: any = {
      id: id,
      [key]: null,
    }
    if (not_serialize.includes(key)) {
      if (item === '') {
        payload[key] = null
      } else {
        payload[key] = item
      }
    } else if (in_serialize.includes(key)) {
      if (
        formatJsonObj(key, typeof item === 'string' ? item : JSON.stringify(item ?? null)) === false
      ) {
        return null
      } else {
        payload[key] = formatJsonObj(
          key,
          typeof item === 'string' ? item : JSON.stringify(item ?? null)
        )
      }
    } else if (key === 'ass_general') {
      payload[key] = normalizeAssGeneral(item)
    } else if (key === 'ass_jsonpath') {
      payload[key] = normalizeAssJsonpath(item)
    } else {
      payload[key] = item
    }

    const isCurrent = requests.capture()
    return saveParameter(payload)
      .then((res) => {
        if (isCurrent()) applyScenarioPatch({ id, changes: { [key]: item } })
        if (res) Message.success(res.msg)
      })
      .catch(console.log)
  }

  function getScenarioProtocolType(item: any) {
    return selectedStep.value?.api_info?.protocol_type || item?.api_info?.protocol_type || 'http'
  }

  function getScenarioBodyType(item: any) {
    return selectedStep.value?.api_info?.body_type || item?.api_info?.body_type || 'none'
  }

  // 通用断言测试方法
  /*
function testGeneralAssertion(item: any, index: number) {
// 这里可以添加通用断言的测试逻辑
Message.info('通用断言测试功能待实现')
}

// 通用断言保存方法
function saveGeneralAssertion(item: any, index: number) {
blurSave('ass_general', item.ass_general, item.id)
}

// 通用断言删除方法
function removeGeneralAssertion(item: any, index: number) {
removeFrontSql(item.ass_general, index, 'ass_general', item.id)
}
*/

  function getCacheDataKeyValue() {
    getSystemCacheDataKeyValue('ass_select_value')
      .then((res) => {
        filterDeprecatedAssertionMethods(res.data).forEach((item: any) => {
          if (item.value.includes('断言')) {
            optionLists.ass.push(item)
          }
          if (item.value === '内容断言') {
            optionLists.textAss.push(...item.children)
          }
          if (item.value === '自定义断言') {
            optionLists.textAss.push(...item.children)
          }
        })
      })
      .catch(console.log)
  }

  function setCaseRecord(record: CaseWorkspaceRecord) {
    caseRecord.value = record
  }
  function normalizeCaseRecord(record: any) {
    return {
      ...defaultCaseRecord(),
      ...(record || {}),
      front_custom: Array.isArray(record?.front_custom) ? record.front_custom : [],
      front_sql: Array.isArray(record?.front_sql) ? record.front_sql : [],
      front_headers: Array.isArray(record?.front_headers) ? record.front_headers : [],
      front_public: Array.isArray(record?.front_public) ? record.front_public : [],
      front_auth_config: Array.isArray(record?.front_auth_config) ? record.front_auth_config : [],
      posterior_sql: Array.isArray(record?.posterior_sql) ? record.posterior_sql : [],
    }
  }

  function normalizeCaseDetailRow(row: any) {
    return {
      ...(row || {}),
      front_sql: Array.isArray(row?.front_sql) ? row.front_sql : [],
      ass_jsonpath: Array.isArray(row?.ass_jsonpath) ? row.ass_jsonpath : [],
      ass_general: Array.isArray(row?.ass_general) ? row.ass_general : [],
      ass_sql: Array.isArray(row?.ass_sql) ? row.ass_sql : [],
      posterior_response: Array.isArray(row?.posterior_response) ? row.posterior_response : [],
      posterior_sql: Array.isArray(row?.posterior_sql) ? row.posterior_sql : [],
      posterior_response_text: Array.isArray(row?.posterior_response_text)
        ? row.posterior_response_text
        : [],
    }
  }

  async function ensureCaseRecord() {
    const caseId = apiCaseId.value
    if (!caseId) return
    const isCurrent = requests.begin('record')
    const res = await getApiCase({ id: caseId, page: 1, pageSize: 1 })
    if (!isCurrent() || String(caseId) !== String(apiCaseId.value)) return
    setCaseRecord(normalizeCaseRecord((res.data || [])[0] || { id: caseId }))
  }
  async function doRefresh(options: { loadParameters?: boolean } = {}) {
    if (!apiCaseId.value || !pageActive || caseVersionPayloadActive.value) return
    const isCurrent = requests.begin('steps')
    const caseId = apiCaseId.value
    stepTableLoading.value = true
    optionLists.caseHeadersList = caseRecord.value.front_headers
    try {
      const res = await getApiCaseDetailed(caseId)
      if (!isCurrent() || caseVersionPayloadActive.value) return
      const rows = Array.isArray(res.data) ? res.data.map(normalizeCaseDetailRow) : []
      caseSteps.value = rows
      const selectedId = selectedStep.value?.id
      const nextStep =
        rows.find((item: ApiCaseStep) => String(item.id) === String(selectedId)) || rows[0]
      if (nextStep) await select(nextStep, { loadParameters: options.loadParameters !== false })
      else {
        selectedStep.value = null
        scenarios.value = []
        invalidateParameterLoad()
      }
      if (isCurrent()) syncCaseRunRefreshByRows(rows)
    } catch {
      // 公共请求层展示错误，保留已加载数据。
    } finally {
      if (isCurrent()) stepTableLoading.value = false
    }
  }

  function doRefreshParameter(
    id: string | number,
    options: { force?: boolean } = {}
  ): Promise<boolean> {
    const cacheKey = String(id)
    const isPageCurrent = requests.capture()
    const loadToken = nextParameterLoadToken()
    const isCurrentSelection = () =>
      isPageCurrent() &&
      isCurrentParameterLoad(loadToken) &&
      String(selectedStep.value?.id || '') === cacheKey
    if (!options.force && parameterCacheByStep.has(cacheKey)) {
      if (!isCurrentSelection()) return Promise.resolve(false)
      panelLoading.collapseLoading = false
      scenarios.value = cloneVersionValue(parameterCacheByStep.get(cacheKey) || [])
      scenarioViewport.activeCollapseKey = scenarios.value.length ? [0] : []
      scenarioViewport.mountedCollapseKeys = []
      scenarioViewport.expandingIndex = -1
      onCollapseChange(scenarios.value.length ? [0] : [])
      void loadScenarioDataFactoryCounts(scenarios.value)
      return Promise.resolve(true)
    }
    panelLoading.collapseLoading = true
    dataFactoryConfigCache.clear()
    scenarioViewport.mountedCollapseKeys = []
    scenarioViewport.expandingIndex = -1
    return getApiCaseDetailedParameter({ case_detailed_id: id })
      .then(
        (res) =>
          new Promise<boolean>((resolve) => {
            const formattedItems: any[] = []
            if (!isCurrentSelection()) {
              resolve(false)
              return
            }
            if (!res.data || res.data.length === 0) {
              parameterCacheByStep.set(cacheKey, [])
              if (isCurrentSelection()) {
                scenarios.value = []
                scenarioViewport.activeCollapseKey = []
                panelLoading.collapseLoading = false
                resolve(true)
              } else {
                resolve(false)
              }
              return
            }

            const BATCH_SIZE = 5 // 每帧渲染条数，可按实际数据量调整
            let index = 0

            function writeBatch() {
              if (!isCurrentSelection()) {
                resolve(false)
                return
              }
              const end = Math.min(index + BATCH_SIZE, res.data.length)
              for (; index < end; index++) {
                formattedItems.push(formatParameterJsonFields(res.data[index]))
              }
              if (index < res.data.length) {
                // 还有数据，下一帧继续写入，让浏览器有机会响应用户操作
                requestAnimationFrame(writeBatch)
              } else {
                parameterCacheByStep.set(cacheKey, cloneVersionValue(formattedItems))
                scenarios.value = formattedItems
                scenarioViewport.activeCollapseKey = formattedItems.length ? [0] : []
                panelLoading.collapseLoading = false
                onCollapseChange(formattedItems.length ? [0] : [])
                void loadScenarioDataFactoryCounts(formattedItems)
                resolve(true)
              }
            }

            requestAnimationFrame(writeBatch)
          })
      )
      .catch(() => {
        if (isCurrentSelection()) panelLoading.collapseLoading = false
        return false
      })
  }

  function normalizeExecutionResultSteps(resultData: any) {
    if (Array.isArray(resultData)) return resultData
    return Array.isArray(resultData?.steps) ? resultData.steps : []
  }

  function findScenarioResult(resultData: any, scenarioId: any) {
    const steps = latestScenarioAttempts(normalizeExecutionResultSteps(resultData))
    return (
      steps.find((step: any) => String(step?.parameter_id) === String(scenarioId)) ||
      steps
        .flatMap((step: any) => (Array.isArray(step?.parameters) ? step.parameters : []))
        .find((parameter: any) => String(parameter?.id) === String(scenarioId)) ||
      null
    )
  }

  function clearDisplayedRuntimeResults() {
    invalidateExecutionResultLoad()
    latestExecutionResultData = null
    lastTraceId.value = ''
    parameterCacheByStep.clear()
    selectedExecutionResultSummary.value = null
    caseSteps.value.forEach((row: any) => {
      row.status = 2
      row.error_message = null
      row.runtime_result_outdated = false
    })
    scenarios.value.forEach((parameter: any) => {
      parameter.status = 2
      parameter.result_data = null
      parameter.error_message = null
      parameter.runtime_result_outdated = false
    })
  }

  async function getLatestCaseExecutionResult() {
    if (!apiCaseId.value) return null
    const query: any = {
      target_type: 'api_case',
      target_id: apiCaseId.value,
      page: 1,
      pageSize: 1,
    }
    // 全局环境只决定执行目标；结果查看按修订隔离，展示该修订跨环境的最近一次执行。
    if (selectedExecutionVersion.value?.revisionId) {
      query.revision_id = selectedExecutionVersion.value.revisionId
    } else {
      query.revision_id_isnull = 1
    }
    const listRes = await getExecutionResultList(query)
    const latest = Array.isArray(listRes.data) ? listRes.data[0] : null
    if (!latest?.id) return null
    const detailRes = await getExecutionResultDetailResolved(latest.id)
    return {
      summary: latest,
      resultData: detailRes.data?.result_data || null,
    }
  }

  async function refreshSelectedRuntimeResult(silent = false, context?: PollingContext) {
    const loadToken = nextExecutionResultLoadToken()
    if (!silent) {
      latestExecutionResultData = null
      selectedExecutionResultSummary.value = null
      caseSteps.value.forEach((row: any) => {
        row.runtime_result_outdated = false
      })
      scenarios.value.forEach((parameter: any) => {
        parameter.result_data = null
        parameter.error_message = null
        parameter.runtime_result_outdated = false
      })
    }
    try {
      const latest = await getLatestCaseExecutionResult()
      if (!isCurrentExecutionResultLoad(loadToken) || (context && !context.isCurrent())) return
      if (!latest?.resultData) return
      selectedExecutionResultSummary.value = latest.summary
      latestExecutionResultData = latest.resultData
      lastTraceId.value = latest.resultData?.trace_id || ''
      applyLatestExecutionResultToSnapshot(latest.resultData)
    } catch (error) {
      console.log(error)
    }
  }

  function applyLatestExecutionResultToSnapshot(resultData: any) {
    const resultSteps = normalizeExecutionResultSteps(resultData)
    const configChangedAfterExecution =
      Boolean(caseRecord.value?.update_time) &&
      Boolean(selectedExecutionResultSummary.value?.create_time) &&
      String(caseRecord.value.update_time) >
        String(selectedExecutionResultSummary.value?.create_time)
    caseSteps.value.forEach((row: any) => {
      const stepResults = latestScenarioAttempts(
        resultSteps.filter((item: any) => String(item?.id) === String(row?.id))
      )
      row.runtime_result_outdated = !stepResults.length && configChangedAfterExecution
      if (!stepResults.length) return
      const failed = stepResults.find((item: any) => Number(item?.status) === 0)
      const warning = stepResults.find((item: any) => Number(item?.status) === 4)
      const running = stepResults.find((item: any) => Number(item?.status) === 3)
      const result = failed || warning || running || stepResults[stepResults.length - 1]
      row.status = result.status
      row.error_message = result.error_message
      if (String(selectedStep.value?.id) === String(row.id)) {
        selectedStep.value = row
      }
    })
    scenarios.value.forEach((parameter: any) => {
      const result = findScenarioResult(resultData, parameter.id)
      parameter.runtime_result_outdated = !result && configChangedAfterExecution
      if (!result) return
      parameter.status = result.status
      parameter.result_data = {
        ...result,
        callback_results: callbackResultsForScenario(
          resultData,
          selectedStep.value?.id,
          parameter.id,
          caseRecord.value.callback_checks || []
        ),
      }
      parameter.error_message = result.error_message
    })
    if (!caseVersionPayloadActive.value && selectedStep.value?.id) {
      parameterCacheByStep.set(String(selectedStep.value.id), cloneVersionValue(scenarios.value))
    }
  }

  async function refreshCaseDetailAfterRun() {
    parameterCacheByStep.clear()
    try {
      if (caseVersionPayloadActive.value) {
        await refreshSelectedRuntimeResult()
        return
      }
      await doRefresh({ loadParameters: true })
      await refreshSelectedRuntimeResult()
    } catch (error) {
      console.log(error)
    }
  }

  function hasRunningCaseStep(rows: any[]) {
    return rows.some(isPendingExecution)
  }

  function syncCaseRunRefreshByRows(rows: any[]) {
    if (hasRunningCaseStep(rows)) {
      startCaseRunRefresh()
    } else if (!caseRequestPending.value && !debugRequestPending.value) {
      stopCaseRunRefresh()
    }
  }

  function mergeCaseStepRows(rows: any[]) {
    caseSteps.value = rows
    const selectedId = selectedStep.value?.id
    if (!selectedId) {
      if (rows.length > 0) selectedStep.value = rows[0]
      return
    }
    const latestSelected = rows.find((item: any) => String(item.id) === String(selectedId))
    if (latestSelected) selectedStep.value = latestSelected
  }

  function refreshCaseRunStatusByStep(context?: PollingContext) {
    if (!apiCaseId.value) return Promise.resolve(false)
    const isCurrent = requests.capture()
    return getApiCaseDetailed(apiCaseId.value)
      .then(async (res) => {
        if (!isCurrent() || (context && !context.isCurrent())) return false
        const rows = Array.isArray(res.data) ? res.data : []
        mergeCaseStepRows(rows)
        if (isRuntimeResultTab()) {
          await refreshSelectedRuntimeResult(true, context)
        }
        if (context && !context.isCurrent()) return false
        const running = hasRunningCaseStep(rows)
        if (running || caseRequestPending.value || debugRequestPending.value) {
          startCaseRunRefresh()
        } else {
          stopCaseRunRefresh()
        }
        return running
      })
      .catch((error) => {
        console.log(error)
        return null
      })
  }

  function getStepDebugContextStorageKey() {
    if (!apiCaseId.value || userStore.selected_environment == null) return ''
    return [
      'mango:api-case-step-debug',
      userStore.userId,
      apiCaseId.value,
      userStore.selected_environment,
    ].join(':')
  }

  function getStepDebugContextId() {
    const key = getStepDebugContextStorageKey()
    if (!key) return null
    try {
      return window.sessionStorage.getItem(key)
    } catch (error) {
      console.log(error)
      return null
    }
  }

  function saveStepDebugContextId(contextId: any) {
    const key = getStepDebugContextStorageKey()
    if (!key || !contextId) return
    try {
      window.sessionStorage.setItem(key, String(contextId))
    } catch (error) {
      console.log(error)
    }
  }

  function clearStepDebugContextId() {
    const key = getStepDebugContextStorageKey()
    if (!key) return
    try {
      window.sessionStorage.removeItem(key)
    } catch (error) {
      console.log(error)
    }
  }

  function handleStepDebugResponse(res: any) {
    const payload = res?.data || {}
    const runResult = payload.run_result || {}
    if (payload.context_id) saveStepDebugContextId(payload.context_id)
    if (runResult.trace_id) lastTraceId.value = runResult.trace_id
    if ([1117, 1118].includes(Number(res?.code))) clearStepDebugContextId()
    if (Number(res?.code) === 200) {
      Message.success(res.msg || '当前步骤调试完成')
    } else {
      Message.error(res?.msg || runResult.error_message || '当前步骤调试失败')
    }
  }

  function formatParameterJsonFields(item: any) {
    const propertiesToFormat = ['ass_json_all', 'file', 'ass_schema']
    propertiesToFormat.forEach((prop) => {
      if (item && typeof item[prop] === 'object' && item[prop] !== null) {
        item[prop] = formatJson(item[prop])
      }
    })
    item.ass_jsonpath = normalizeAssJsonpath(item.ass_jsonpath)
    item.ass_general = normalizeAssGeneral(item.ass_general)
    item.ass_sql = normalizeAssSql(item.ass_sql)
    item.headers = Array.isArray(item.headers) ? item.headers : []
    item.__persistedHeaders = [...item.headers]
    item.__headersSaving = false
    item.__formatted = true
    return item
  }

  // 在 collapse 展开时懒格式化当前 item，避免首次渲染时阻塞主线程
  function onCollapseChange(keys: any[]) {
    if (keys.length === 0) {
      scenarioViewport.activeCollapseKey = []
      scenarioViewport.expandingIndex = -1
      return
    }
    const idx = Number(keys[keys.length - 1])
    scenarioViewport.activeCollapseKey = keys
    if (!isMountedCollapseItem(idx)) {
      deferMountCollapseItem(idx)
    } else {
      scenarioViewport.expandingIndex = -1
    }
    // 懒格式化当前 item
    const item = scenarios.value[idx]
    if (item && !item.__formatted) {
      formatParameterJsonFields(item)
    }
  }

  function getProjectProductId(value: any = apiProjectProductId.value) {
    if (value && typeof value === 'object') return value.id
    return value
  }

  function addConfigSearchDocument(
    documents: ConfigSearchDocument[],
    location: string,
    fieldLabel: string,
    value: any,
    target: ConfigSearchTarget = {}
  ) {
    if (!hasConfigValue(value)) return
    documents.push({ location, fieldLabel, value, ...target })
  }

  function scenarioSearchFieldConfig(): Array<{
    key: string
    label: string
    detailType?: string
    detailTab?: string
  }> {
    return [
      { key: 'name', label: '场景名称' },
      { key: 'front_sql', label: '前置数据库', detailType: '1', detailTab: '10' },
      { key: 'front_func', label: '前置函数', detailType: '1', detailTab: '11' },
      { key: 'headers', label: '请求头', detailType: '0', detailTab: '00' },
      { key: 'resolved_headers', label: '实际请求头', detailType: '0', detailTab: '00' },
      { key: 'params', label: '请求参数', detailType: '0', detailTab: '01' },
      { key: 'body_config', label: '请求体', detailType: '0', detailTab: '02' },
      { key: 'sse_config', label: 'SSE配置', detailType: '0', detailTab: '02' },
      { key: 'posterior_response', label: '响应JSON提取', detailType: '4', detailTab: '40' },
      {
        key: 'posterior_response_text',
        label: '响应文本提取',
        detailType: '4',
        detailTab: '44',
      },
      { key: 'posterior_sql', label: '后置数据库', detailType: '4', detailTab: '41' },
      { key: 'posterior_sleep', label: '强制等待', detailType: '4', detailTab: '42' },
      { key: 'posterior_file', label: '响应文件', detailType: '4', detailTab: '40' },
      { key: 'posterior_func', label: '后置函数', detailType: '4', detailTab: '43' },
      { key: 'ass_json_all', label: 'JSON一致断言', detailType: '3', detailTab: '30' },
      { key: 'ass_text_all', label: '文本一致断言', detailType: '3', detailTab: '33' },
      { key: 'ass_jsonpath', label: '响应字段断言', detailType: '3', detailTab: '31' },
      { key: 'ass_sql', label: 'SQL断言', detailType: '3', detailTab: '35' },
      { key: 'ass_schema', label: '结构化断言', detailType: '3', detailTab: '34' },
      { key: 'ass_general', label: '通用断言', detailType: '3', detailTab: '32' },
    ]
  }

  function appendScenarioSearchDocuments(
    documents: ConfigSearchDocument[],
    step: any,
    parameter: any
  ) {
    const stepName = step?.api_info?.name || `步骤 ${step?.id || '-'}`
    const scenarioName = parameter?.name || `场景 ${parameter?.id || '-'}`
    const location = `${stepName} / ${scenarioName}`
    scenarioSearchFieldConfig().forEach((field) => {
      addConfigSearchDocument(documents, location, field.label, parameter?.[field.key], {
        stepId: step.id,
        scenarioId: parameter.id,
        detailType: field.detailType || '0',
        detailTab: field.detailTab || '02',
      })
    })
  }

  function appendScenarioExecutionSearchDocuments(
    documents: ConfigSearchDocument[],
    step: any,
    parameter: any,
    resultData: any
  ) {
    // 优先使用刚查询到的最近执行结果；页面已经展示结果时保留当前场景结果作为兜底，
    // 避免版本筛选或历史接口短暂失败造成“看得到却搜不到”。
    const runtimeResult = findScenarioResult(resultData, parameter?.id) || parameter?.result_data
    if (!runtimeResult) return
    const stepName = step?.api_info?.name || `步骤 ${step?.id || '-'}`
    const scenarioName = parameter?.name || `场景 ${parameter?.id || '-'}`
    const location = `${stepName} / ${scenarioName} / 最近执行`
    const target = {
      stepId: step.id,
      scenarioId: parameter.id,
    }
    const runtimeItem = { ...parameter, result_data: runtimeResult }
    const responseTab = getResultResponseTabKey(runtimeItem)
    const request = runtimeResult?.request || {}
    const response = runtimeResult?.response || {}
    const append = (label: string, value: any, detailType: string, detailTab: string) => {
      addConfigSearchDocument(documents, location, label, value, {
        ...target,
        detailType,
        detailTab,
      })
    }

    const requestMethod = request.method ?? response.request_method
    const protocolType =
      request.protocol_type ?? response.request_protocol_type ?? response.response_mode
    const requestBodyType = request.body_type ?? response.request_body_type
    append('HTTP状态码', response.code, '2', '20')
    append('协议状态', runtimeResult.protocol_status, '2', '20')
    append('请求方法', requestMethod, '2', '20')
    append(
      '协议类型',
      protocolType
        ? { value: protocolType, label: scenarioProtocolLabel(protocolType) }
        : protocolType,
      '2',
      '20'
    )
    append(
      '请求体类型',
      requestBodyType
        ? { value: requestBodyType, label: scenarioBodyTypeLabel(requestBodyType) }
        : requestBodyType,
      '2',
      '20'
    )
    append('响应模式', response.response_mode, '2', '20')
    append(
      '请求Content-Type',
      response.request_content_type ?? request.request_content_type,
      '2',
      '20'
    )
    append('响应Content-Type', responseHeaderValue(response.headers, 'content-type'), '2', '20')
    append('实际请求URL', request.url ?? response.request_url ?? response.url, '2', '20')
    append('实际请求头', response.request_headers ?? request.headers, '2', '21')
    append('响应头', response.headers, '2', '21')
    append('实际请求参数', getResultRequestParams(runtimeItem), '2', '25')
    append('实际请求体', getResultRequestBody(runtimeItem), '2', '25')
    append('实际请求文件', getResultRequestFiles(runtimeItem), '2', '25')
    append('响应JSON', response.json, '2', responseTab)
    append('响应文本', response.text, '2', responseTab)
    append('SSE事件', response.sse_events, '2', '26')
    append('WebSocket消息', response.ws_messages, '2', '27')
    append('运行缓存', runtimeResult.cache_data, '5', '50')
    append('工厂缓存', runtimeResult.data_factory_cache_data, '7', '70')
    append('断言结果', runtimeResult.ass, '6', '60')
    append('失败信息', runtimeResult.error_message, '2', '20')
  }

  async function loadConfigSearchDocuments(isCurrent: () => boolean = () => true) {
    const documents: ConfigSearchDocument[] = []
    const caseLocation = `Case ${apiCaseId.value} / ${caseRecord.value?.name || '-'}`
    const caseFields: Array<{
      key: string
      label: string
      caseApiType?: string
      caseApiSonType?: string
    }> = [
      { key: 'name', label: '用例名称' },
      { key: 'scenario_description', label: '场景描述' },
      { key: 'parametrize', label: '参数化' },
      { key: 'front_custom', label: '自定义变量', caseApiType: '1', caseApiSonType: '11' },
      { key: 'front_sql', label: 'SQL变量', caseApiType: '1', caseApiSonType: '12' },
      { key: 'posterior_sql', label: '后置数据库', caseApiType: '3', caseApiSonType: '31' },
    ]
    caseFields.forEach((field) => {
      addConfigSearchDocument(documents, caseLocation, field.label, caseRecord.value?.[field.key], {
        caseApiType: field.caseApiType,
        caseApiSonType: field.caseApiSonType,
      })
    })

    const steps = Array.isArray(caseSteps.value) ? caseSteps.value : []
    const stepParameters = new Map<string, ApiCaseScenario[]>()
    const latestExecutionPromise = getLatestCaseExecutionResult().catch((error) => {
      console.log(error)
      return null
    })
    configSearch.total = steps.length + 1
    configSearch.completed = 0
    await mapWithConcurrency(steps, async (step) => {
      const stepKey = String(step.id)
      let parameters: any[] = []
      if (caseVersionPayloadActive.value) {
        parameters = cloneVersionValue(snapshotParametersByStep.get(stepKey) || [])
      } else if (parameterCacheByStep.has(stepKey)) {
        parameters = cloneVersionValue(parameterCacheByStep.get(stepKey) || [])
      } else {
        try {
          const response = await getApiCaseDetailedParameter({ case_detailed_id: step.id })
          parameters = Array.isArray(response.data) ? response.data : []
          parameterCacheByStep.set(stepKey, cloneVersionValue(parameters))
        } catch (error) {
          console.log(error)
        }
      }
      stepParameters.set(stepKey, parameters)
      if (isCurrent()) configSearch.completed += 1
    })
    const latestExecution = await latestExecutionPromise
    if (isCurrent()) configSearch.completed += 1

    steps.forEach((step) => {
      const stepName = step?.api_info?.name || `步骤 ${step?.id || '-'}`
      const apiInfoFields = [
        { key: 'name', label: '接口名称', detailTab: '20' },
        { key: 'url', label: '接口URL', detailTab: '20' },
        { key: 'headers', label: '接口请求头', detailTab: '00' },
        { key: 'params', label: '接口请求参数', detailTab: '01' },
        { key: 'body_config', label: '接口请求体', detailTab: '02' },
        { key: 'sse_config', label: '接口SSE配置', detailTab: '02' },
      ]
      apiInfoFields.forEach((field) => {
        addConfigSearchDocument(documents, stepName, field.label, step?.api_info?.[field.key], {
          stepId: step.id,
          detailType: field.detailTab === '20' ? '2' : '0',
          detailTab: field.detailTab,
        })
      })
      const apiInfo = step?.api_info || {}
      if (hasConfigValue(apiInfo.method)) {
        addConfigSearchDocument(
          documents,
          stepName,
          '请求方法',
          { value: apiInfo.method, label: formatMethodTitle(apiInfo.method) },
          { stepId: step.id, detailType: '2', detailTab: '20' }
        )
      }
      if (hasConfigValue(apiInfo.protocol_type)) {
        addConfigSearchDocument(
          documents,
          stepName,
          '协议类型',
          {
            value: apiInfo.protocol_type,
            label: scenarioProtocolLabel(apiInfo.protocol_type),
          },
          { stepId: step.id, detailType: '2', detailTab: '20' }
        )
      }
      if (hasConfigValue(apiInfo.body_type)) {
        addConfigSearchDocument(
          documents,
          stepName,
          '请求体类型',
          { value: apiInfo.body_type, label: scenarioBodyTypeLabel(apiInfo.body_type) },
          { stepId: step.id, detailType: '2', detailTab: '20' }
        )
      }
      ;(stepParameters.get(String(step.id)) || []).forEach((parameter) => {
        appendScenarioSearchDocuments(documents, step, parameter)
        appendScenarioExecutionSearchDocuments(
          documents,
          step,
          parameter,
          latestExecution?.resultData
        )
      })
    })

    if (caseVersionPayloadActive.value && selectedCaseVersionDetail.value?.payload) {
      const snapshot = parseApiCaseRevisionPayload(selectedCaseVersionDetail.value.payload)
      addConfigSearchDocument(
        documents,
        `${caseLocation} / 默认请求头`,
        '已解析请求头',
        snapshot.runtime.resolved_front_headers,
        { caseApiType: '1', caseApiSonType: '13' }
      )
      snapshot.dependencies.data_factory_configs.forEach((factoryConfig) => {
        const sourceType = Number(factoryConfig.source_type)
        const sourceId = String(factoryConfig.source_id || '')
        const step = steps.find((item) =>
          (stepParameters.get(String(item.id)) || []).some(
            (parameter) => String(parameter.id) === sourceId
          )
        )
        const parameter = step
          ? (stepParameters.get(String(step.id)) || []).find((item) => String(item.id) === sourceId)
          : null
        addConfigSearchDocument(
          documents,
          sourceType === 1
            ? `${caseLocation} / 数据工厂`
            : `${step?.api_info?.name || '步骤'} / ${parameter?.name || '场景'} / 数据工厂`,
          '数据工厂配置',
          factoryConfig,
          sourceType === 1
            ? { caseApiType: '1', caseApiSonType: '14' }
            : {
                stepId: step?.id,
                scenarioId: parameter?.id,
                detailType: '1',
                detailTab: '12',
              }
        )
      })
    } else {
      const productId = getProjectProductId(caseRecord.value?.project_product)
      const [headersResult, publicResult, authResult, caseFactoryResult] = await Promise.allSettled(
        [
          getApiHeaders({ page: 1, pageSize: 10000, project_product_id: productId }),
          getApiPublic({ page: 1, pageSize: 10000, project_product_id: productId }),
          getApiAuthConfig({ page: 1, pageSize: 10000, project_product_id: productId }),
          getDataFactoryCaseConfig({ source_type: 1, source_id: apiCaseId.value }),
        ]
      )
      const responseData = (result: PromiseSettledResult<any>) =>
        result.status === 'fulfilled' && Array.isArray(result.value?.data) ? result.value.data : []
      const headerMap = new Map<string, any>(
        responseData(headersResult).map((item: any): [string, any] => [String(item.id), item])
      )
      const publicMap = new Map<string, any>(
        responseData(publicResult).map((item: any): [string, any] => [String(item.id), item])
      )
      const authMap = new Map<string, any>(
        responseData(authResult).map((item: any): [string, any] => [String(item.id), item])
      )
      const appendReferencedConfig = (
        ids: any[],
        source: Map<string, any>,
        location: string,
        label: string,
        target: ConfigSearchTarget
      ) => {
        ;(Array.isArray(ids) ? ids : []).forEach((id) => {
          const item = source.get(String(id))
          if (!item) return
          const searchableValue =
            label === '授权配置'
              ? {
                  name: item.name,
                  auth_type: item.auth_type,
                  api_info: item.api_info,
                  custom_code: item.custom_code,
                }
              : label === '全局变量'
              ? {
                  name: item.name,
                  key: item.key,
                  value: item.value,
                  type: item.type,
                  test_envs: item.test_envs,
                }
              : { key: item.key, value: item.value }
          addConfigSearchDocument(documents, location, `${label} #${id}`, searchableValue, target)
        })
      }
      appendReferencedConfig(
        caseRecord.value?.front_headers,
        headerMap,
        `${caseLocation} / 默认请求头`,
        '请求头',
        { caseApiType: '1', caseApiSonType: '13' }
      )
      appendReferencedConfig(
        caseRecord.value?.front_public,
        publicMap,
        `${caseLocation} / 全局变量`,
        '全局变量',
        { caseApiType: '1', caseApiSonType: '15' }
      )
      appendReferencedConfig(
        caseRecord.value?.front_auth_config,
        authMap,
        `${caseLocation} / 授权管理`,
        '授权配置',
        { caseApiType: '1', caseApiSonType: '16' }
      )
      responseData(caseFactoryResult).forEach((item: any) => {
        addConfigSearchDocument(documents, `${caseLocation} / 数据工厂`, '数据工厂配置', item, {
          caseApiType: '1',
          caseApiSonType: '14',
        })
      })
      const scenarioEntries = steps.flatMap((step) =>
        (stepParameters.get(String(step.id)) || []).map((parameter) => ({ step, parameter }))
      )
      if (isCurrent()) configSearch.total += scenarioEntries.length
      await mapWithConcurrency(scenarioEntries, async ({ step, parameter }) => {
        try {
          const response = await getDataFactoryCaseConfig({
            source_type: 3,
            source_id: parameter.id,
          })
          ;(Array.isArray(response.data) ? response.data : []).forEach((item: any) => {
            addConfigSearchDocument(
              documents,
              `${step?.api_info?.name || '步骤'} / ${parameter?.name || '场景'} / 数据工厂`,
              '数据工厂配置',
              item,
              {
                stepId: step.id,
                scenarioId: parameter.id,
                detailType: '1',
                detailTab: '12',
              }
            )
          })
        } catch (error) {
          console.log(error)
        } finally {
          if (isCurrent()) configSearch.completed += 1
        }
      })
      steps.forEach((step) => {
        ;(stepParameters.get(String(step.id)) || []).forEach((parameter) => {
          appendReferencedConfig(
            parameter.headers || [],
            headerMap,
            `${step?.api_info?.name || '步骤'} / ${parameter?.name || '场景'} / 请求头`,
            '请求头',
            { stepId: step.id, scenarioId: parameter.id, detailType: '0', detailTab: '00' }
          )
        })
      })
    }
    if (isCurrent()) setConfigSearchDocuments(documents)
  }

  async function openConfigSearch() {
    const isCurrent = requests.begin('config-search')
    configSearch.visible = true
    resetConfigSearch()
    try {
      await loadConfigSearchDocuments(isCurrent)
    } catch (error) {
      console.log(error)
      if (isCurrent()) Message.error('当前 Case 数据加载失败，请重试')
    } finally {
      if (isCurrent()) configSearch.loading = false
    }
  }

  async function locateConfigSearchResult(result: ConfigSearchMatch) {
    configSearch.visible = false
    if (result.caseApiType) {
      workspaceTabs.apiType = result.caseApiType
      workspaceTabs.apiSonType = result.caseApiSonType || workspaceTabs.apiSonType
      await runCaseDetailTabLoading(() => ensureActiveCasePanelLoaded())
      return
    }
    if (!result.stepId) return
    const step = caseSteps.value.find((item: any) => String(item.id) === String(result.stepId))
    if (!step) return
    workspaceTabs.apiType = '2'
    await select(step)
    if (result.scenarioId) {
      const scenarioIndex = scenarios.value.findIndex(
        (item: any) => String(item.id) === String(result.scenarioId)
      )
      if (scenarioIndex >= 0) onCollapseChange([scenarioIndex])
    }
    workspaceTabs.caseDetailsTypeKey = result.detailType || '0'
    workspaceTabs.tabsKey = result.detailTab || '02'
    await runCaseDetailTabLoading(() => ensureActiveCasePanelLoaded(step))
  }

  function loadCaseHeaders(project_product_id: any = apiProjectProductId.value) {
    const isCurrent = requests.capture()
    const productId = getProjectProductId(project_product_id)
    if (!productId) return Promise.resolve()
    const cacheKey = `case-headers:${productId}`
    if (panelLoaded(cacheKey)) return Promise.resolve()
    const value = {
      page: 1,
      pageSize: 10000,
      project_product_id: productId,
    }
    return getApiHeaders(value)
      .then((res) => {
        if (!isCurrent()) return
        optionLists.headers_list = res.data
        markPanelLoaded(cacheKey)
      })
      .catch(console.log)
  }

  function loadParameterHeaders(project_product_id: any) {
    const isCurrent = requests.capture()
    const productId = getProjectProductId(project_product_id)
    if (!productId) return Promise.resolve()
    const cacheKey = `parameter-headers:${productId}`
    if (panelLoaded(cacheKey)) return Promise.resolve()
    const value = {
      page: 1,
      pageSize: 10000,
      project_product_id: productId,
    }
    return getApiHeaders(value)
      .then((res) => {
        if (!isCurrent()) return
        optionLists.parameter_headers_list = res.data
        markPanelLoaded(cacheKey)
      })
      .catch(console.log)
  }

  function loadCasePublicOptions(project_product_id: any = apiProjectProductId.value) {
    const isCurrent = requests.capture()
    const productId = getProjectProductId(project_product_id)
    if (!productId) return Promise.resolve()
    const cacheKey = `case-public:${productId}`
    if (panelLoaded(cacheKey)) return Promise.resolve()
    const params = {
      page: 1,
      pageSize: 10000,
      project_product_id: productId,
    }
    return getApiPublic(params)
      .then((res) => {
        if (!isCurrent()) return
        optionLists.publicOptions = (res.data || []).map((item: any) => ({
          value: item.id,
          name: item.name || item.key || `全局变量 ${item.id}`,
          key: item.key || '-',
          type: item.type,
          typeText: getEnumTitle(enumStore.api_public_type, item.type),
          testEnvs: normalizeEnvironmentList(item.test_envs),
          isCommonEnv: normalizeEnvironmentList(item.test_envs).length === 0,
          statusText: formatDefaultStatusText(item.status),
          disabled: Number(item.status) === 1,
        }))
        markPanelLoaded(cacheKey)
      })
      .catch(console.log)
  }

  function loadCaseAuthOptions(project_product_id: any = apiProjectProductId.value) {
    const isCurrent = requests.capture()
    const productId = getProjectProductId(project_product_id)
    if (!productId) return Promise.resolve()
    const cacheKey = `case-auth:${productId}`
    if (panelLoaded(cacheKey)) return Promise.resolve()
    const params = {
      page: 1,
      pageSize: 10000,
      project_product_id: productId,
    }
    return getApiAuthConfig(params)
      .then((res) => {
        if (!isCurrent()) return
        optionLists.authConfigOptions = (res.data || []).map((item: any) => ({
          value: item.id,
          name: item.name || `授权配置 ${item.id}`,
          authType: item.auth_type,
          authTypeText: getEnumTitle(enumStore.api_auth_type, item.auth_type),
          testEnv: item.test_env,
          isCommonEnv:
            item.test_env === null || item.test_env === undefined || item.test_env === '',
          envText: formatEnvironmentText(item.test_env),
          statusText: formatDefaultStatusText(item.status),
          disabled: Number(item.status) === 1,
        }))
        markPanelLoaded(cacheKey)
      })
      .catch(console.log)
  }

  const caseRun = async (
    param: number | string | null,
    executionVersion: ApiCaseExecutionVersion | null = selectedExecutionVersion.value
  ) => {
    if (!apiCaseId.value) return
    if (!executionVersion && !caseRecord.value?.published_release_id) {
      await versionPanelRef.value?.selectPreferredRevision()
      Message.warning(
        caseRecord.value?.publication_status === 'prepublished'
          ? '当前预发布修订尚未通过，已定位到版本盒子；可等待产品负责人发布，或执行当前配置验证'
          : '当前用例尚未发布，已定位到版本盒子；请先创建修订并提交预发布，或执行当前配置验证'
      )
      return
    }
    if (userStore.selected_environment == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    if (caseExecutionActive.value) return
    const isCurrent = requests.capture()
    clearAssertionVerifyResults()
    caseRequestPending.value = true
    caseRunning.value = true
    startCaseRunLoadingLimit()
    try {
      const response = await getApiCaseRunRaw(
        apiCaseId.value,
        userStore.selected_environment,
        param,
        executionVersion?.revisionId,
        executionVersion?.releaseId
      )
      if (!isCurrent()) return
      const res = response.data || {}
      lastTraceId.value = res.data?.trace_id || ''
      saveStepDebugContextId(res.data?.execution_context_id)
      if (res.code === 200) {
        Message.success(res.msg)
      } else if (Number(res.code) === 1125) {
        await versionPanelRef.value?.selectPreferredRevision()
        Message.warning('当前用例尚未发布，已定位到版本盒子；请先创建或选择修订')
      } else {
        Message.error(res.msg || '执行失败')
      }
    } catch (e) {
      console.log(e)
    } finally {
      caseRequestPending.value = false
      caseRunning.value = false
      stopCaseRunLoadingLimit()
      if (!isCurrent()) return
      await refreshCaseDetailAfterRun()
      syncCaseRunRefreshByRows(caseSteps.value)
    }
  }

  const debugCaseStep = async (record: any) => {
    if (!apiCaseId.value || !record?.id) return
    if (userStore.selected_environment == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    if (caseExecutionActive.value) return
    const isCurrent = requests.capture()
    clearAssertionVerifyResults()
    debugRequestPending.value = true
    debugRunningStepId.value = record.id
    startDebugRunLoadingLimit()
    try {
      const response = await postApiCaseStepDebugRaw({
        case_id: apiCaseId.value,
        case_detailed_id: record.id,
        test_env: userStore.selected_environment,
        context_id: getStepDebugContextId(),
      })
      if (isCurrent()) handleStepDebugResponse(response.data || {})
    } catch (error: any) {
      if (!isCurrent()) return
      const res = error?.response?.data
      if (res) {
        handleStepDebugResponse(res)
      } else {
        console.log(error)
        Message.error('当前步骤调试请求失败，请检查网络或服务状态')
      }
    } finally {
      debugRequestPending.value = false
      debugRunningStepId.value = null
      stopDebugRunLoadingLimit()
      if (!isCurrent()) return
      const running = await refreshCaseRunStatusByStep()
      if (running !== false) {
        startCaseRunRefresh()
      } else {
        stopCaseRunRefresh()
      }
    }
  }

  async function showExecutionTrace(query: {
    result_id?: number | string
    trace_id?: string
    test_suite_detail_id?: any
    case_id?: any
  }) {
    await traceDrawerRef.value?.open(query)
  }

  function runtimeStatusText(record: any) {
    if (record?.runtime_result_outdated) return '配置变更后未执行'
    return enumStore.task_status[record?.status]?.title || '-'
  }

  function runtimeStatusColor(record: any) {
    if (record?.runtime_result_outdated) return 'orange'
    return enumStore.status_colors[record?.status]
  }

  function isRuntimeFailure(record: any) {
    return !record?.runtime_result_outdated && [0, 4].includes(Number(record?.status))
  }

  function runtimeFailureMessage(record: any) {
    return (
      record?.error_message || record?.result_data?.error_message || '执行失败，暂无详细错误信息'
    )
  }

  function loadDatasourceAliases() {
    const isCurrent = requests.capture()
    const productId = getProjectProductId(apiProjectProductId.value)
    if (!productId) return Promise.resolve()
    const cacheKey = `datasource-aliases:${productId}`
    if (panelLoaded(cacheKey)) return Promise.resolve()
    return getDataFactoryDatasourceAlias({
      project_product: productId,
      status: 1,
    })
      .then((res) => {
        if (!isCurrent()) return
        optionLists.datasourceAliasOptions = (res.data || []).map((item: any) => ({
          label: item.name,
          value: item.id,
          dbType: item.db_type,
        }))
        markPanelLoaded(cacheKey)
      })
      .catch(console.log)
  }

  async function handleChange(rows: ApiCaseStep[]) {
    if (!ensureCaseEditable() || caseExecutionActive.value || sortingSteps.value) return
    const isCurrent = requests.capture(),
      previous = [...caseSteps.value]
    const next = [...rows]
    const payload = next.map((item, index) => ({ id: item.id, case_sort: index }))
    caseSteps.value = next
    sortingSteps.value = true
    try {
      const response = await putApiPutCaseSort(payload)
      if (isCurrent()) Message.success(response.msg)
    } catch {
      if (isCurrent()) caseSteps.value = previous
    } finally {
      if (isCurrent()) sortingSteps.value = false
    }
  }

  function onDelete(record: any) {
    if (!ensureCaseEditable()) return
    const caseId = apiCaseId.value,
      isCurrent = requests.capture()
    Modal.confirm({
      title: '提示',
      content: '是否要删除此接口？',
      cancelText: '取消',
      okText: '删除',
      onBeforeOk: () => {
        return deleteApiCaseDetailed(record.id, caseId)
          .then((res) => {
            Message.success(res.msg)
          })
          .then(() => {
            if (isCurrent()) void doRefresh()
            return true
          })
          .catch(() => false)
      },
    })
  }

  function refresh(id: number) {
    if (!ensureCaseEditable()) return
    Modal.confirm({
      title: '提示',
      content: '是否确实从接口管理中同步接口数据？点击确认后，原始数据会丢失！',
      cancelText: '取消',
      okText: '同步',
      onBeforeOk: () => {
        return putApiPutRefreshApiInfo(id)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .then(() => true)
          .catch(() => false)
      },
    })
  }

  function getApiInfoId(record: any) {
    const apiInfo = record?.api_info
    return apiInfo?.id || apiInfo || ''
  }

  function openApiInfoDetail(record: any) {
    const apiInfoId = getApiInfoId(record)
    if (!apiInfoId) {
      Message.error('未找到接口ID')
      return
    }
    apiInfoDetailPanelRef.value?.open(apiInfoId)
  }

  function select(record: any, options: { loadParameters?: boolean } = {}): Promise<void> {
    if (!record?.api_info) {
      selectedStep.value = record || null
      scenarios.value = []
      return Promise.resolve()
    }
    selectedStep.value = record
    if (options.loadParameters === false) {
      scenarios.value = []
      scenarioViewport.activeCollapseKey = []
      scenarioViewport.mountedCollapseKeys = []
      scenarioViewport.expandingIndex = -1
      return Promise.resolve()
    }
    if (caseVersionPayloadActive.value) {
      const parameters = snapshotParametersByStep.get(String(record.id)) || []
      scenarios.value = parameters.map((item: any) => formatParameterJsonFields(item))
      if (latestExecutionResultData) applyLatestExecutionResultToSnapshot(latestExecutionResultData)
      switchApiInfoType(workspaceTabs.caseDetailsTypeKey, scenarios.value[0] || record)
      onCollapseChange(scenarios.value.length ? [0] : [])
      return Promise.resolve()
    }
    return doRefreshParameter(record.id).then(async (applied) => {
      if (!applied || String(selectedStep.value?.id) !== String(record.id)) return
      if (latestExecutionResultData) applyLatestExecutionResultToSnapshot(latestExecutionResultData)
      await switchApiInfoType(workspaceTabs.caseDetailsTypeKey, scenarios.value[0] || record)
      onCollapseChange(scenarios.value.length ? [0] : [])
    })
  }

  function invalidatePageContext() {
    pageActive = false
    caseConfigLoadingCount = 0
    sortingSteps.value = false
    requests.invalidate()
    invalidateParameterLoad()
    invalidateExecutionResultLoad()
    clearPanelCache()
    disposeExecutionTimers()
    traceDrawerRef.value?.close()
    caseDiagnosisDrawerRef.value?.close()
    apiInfoDetailPanelRef.value?.close()
    stepEditorRef.value?.close()
    scenarioEditorRef.value?.close()
    jsonEditDrawer.visible = false
    configSearch.visible = false
    stepTableLoading.value = false
    panelLoading.collapseLoading =
      panelLoading.caseConfigLoading =
      panelLoading.caseDetailTabLoading =
        false
  }
  async function initializePage(reset = false) {
    invalidatePageContext()
    pageActive = true
    const isCurrent = requests.capture()
    if (reset) {
      caseVersionPayloadActive.value = false
      caseVersionEditUnlocked.value = false
      selectedExecutionVersion.value = null
      selectedCaseVersionDetail.value = null
      selectedExecutionResultSummary.value = null
      latestExecutionResultData = null
      liveCaseRecord.value = null
      liveCaseRows.value = []
      snapshotParametersByStep.clear()
      parameterCacheByStep.clear()
      dataFactoryConfigCache.clear()
      caseRecord.value = defaultCaseRecord()
      caseSteps.value = []
      selectedStep.value = null
      scenarios.value = []
      optionLists.publicOptions = []
      optionLists.authConfigOptions = []
      optionLists.headers_list = []
      optionLists.parameter_headers_list = []
    }
    try {
      if (caseVersionPayloadActive.value) {
        await refreshSelectedRuntimeResult()
        return
      }
      await ensureCaseRecord()
      if (!isCurrent()) return
      await Promise.all([doRefresh(), loadCaseDataFactoryCount()])
    } catch {
      // 保留错误提示及局部状态，可通过重新进入页面重试。
    }
  }
  watch(
    () => configSearch.visible,
    (visible) => {
      if (!visible) {
        requests.begin('config-search')
        configSearch.loading = false
      }
    }
  )
  watch(apiCaseId, () => {
    if (props.embedded || route.path === '/apitest/case/details') void initializePage(true)
  })
  onMounted(() => {
    getCacheDataKeyValue()
    void initializePage()
  })
  onDeactivated(invalidatePageContext)
  onActivated(() => {
    if (!pageActive) void initializePage()
  })
  onUnmounted(invalidatePageContext)

  function updateArrayItem(
    array: any[],
    index: number,
    value: any,
    item: any,
    fieldName: string,
    saveCallback?: () => void
  ) {
    if (!ensureCaseEditable()) return
    // 更新数组元素
    if (array && index < array.length) {
      array[index] = value
    }
    // 如果提供了保存回调，则执行保存
    if (saveCallback) {
      saveCallback()
    }
  }

  function normalizeGroupLogic(value: unknown): 'AND' | 'OR' {
    const logic = String(value || 'AND').toUpperCase()
    return logic === 'OR' ? 'OR' : 'AND'
  }

  type AssertionType = 'jsonpath' | 'regex' | 'cache'

  function normalizeAssertionType(value: any): AssertionType {
    const assertionType = String(value || 'jsonpath').toLowerCase()
    if (assertionType === 'regex' || assertionType === 'cache') {
      return assertionType
    }
    return 'jsonpath'
  }

  function filterDeprecatedAssertionMethods(items: any[]): any[] {
    return (Array.isArray(items) ? items : [])
      .filter((item: any) => !deprecatedRegexAssertionMethods.has(item?.value))
      .map((item: any) => ({
        ...item,
        children: Array.isArray(item?.children)
          ? filterDeprecatedAssertionMethods(item.children)
          : item?.children,
      }))
  }

  function normalizeAssGeneral(assGeneral: any) {
    if (!Array.isArray(assGeneral)) {
      return []
    }
    return assGeneral.map((assItem: any) => ({
      group_name: assItem?.group_name || '',
      group_logic: normalizeGroupLogic(assItem?.group_logic),
      method: assItem?.method || assItem?.value?.value || '',
      value: normalizeAssGeneralValue(assItem?.value),
    }))
  }

  function normalizeAssJsonpath(assJsonpath: any) {
    if (!Array.isArray(assJsonpath)) {
      return []
    }
    return assJsonpath.map((assItem: any) => ({
      group_name: assItem?.group_name || '',
      group_logic: normalizeGroupLogic(assItem?.group_logic),
      assertion_type: normalizeAssertionType(assItem?.assertion_type),
      actual: assItem?.actual || '',
      method: assItem?.method || '',
      expect: assItem?.expect ?? null,
    }))
  }

  function normalizeAssSql(assSql: any) {
    if (!Array.isArray(assSql)) {
      return []
    }
    return assSql.map((assItem: any) => ({
      actual: assItem?.actual || '',
      method: assItem?.method || '',
      expect: assItem?.expect ?? '',
      datasource_alias: assItem?.datasource_alias ?? null,
    }))
  }

  const sqlAssertionDatasourceOptions = computed(() =>
    optionLists.datasourceAliasOptions.filter((item: any) =>
      [0, 1, 2].includes(Number(item.dbType))
    )
  )

  const sqlAssertionMethodOptions = computed(() => {
    const result: Array<{ label: string; value: string }> = []
    const walk = (items: any[]) => {
      for (const item of items || []) {
        if (String(item?.value || '').startsWith('assert_sql_')) {
          result.push({
            label: item.label || item.title || item.value,
            value: item.value,
          })
        }
        if (Array.isArray(item?.children)) walk(item.children)
      }
    }
    walk(optionLists.ass)
    return result
  })

  function normalizeAssGeneralValue(value: any) {
    return {
      value: value?.value || '',
      label: value?.label || '',
      parameter: Array.isArray(value?.parameter)
        ? value.parameter.map((param: any) => ({
            f: param?.f || '',
            n: param?.n || '',
            p: param?.p || '',
            d: Boolean(param?.d),
            v: param?.v ?? '',
          }))
        : [],
    }
  }
</script>

<style scoped src="./styles.css"></style>
