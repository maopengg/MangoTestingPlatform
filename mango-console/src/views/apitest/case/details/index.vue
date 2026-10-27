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
            :active-key="data.apiType"
            :step-count="data.data.length || 0"
            :edit-locked="caseEditLocked"
            :show-add="showCaseAddButton"
            :loading="data.caseConfigLoading"
            @change="switchType"
            @add="addData"
          >
            <template #preparation>
              <a-tabs
                :active-key="data.apiSonType"
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
                            v-for="item in data.publicOptions"
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
                            v-for="item in data.authConfigOptions"
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
                      :data-list="pageData.record.front_custom"
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
                        (index) => removeFrontSql1(pageData.record.front_custom, index, false)
                      "
                      :on-save="upDataCaseWithoutScenarioRefresh"
                      @update:item="
                        (index, value) =>
                          updateArrayItem(
                            pageData.record.front_custom,
                            index,
                            value,
                            pageData.record,
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
                    :data-list="pageData.record.front_sql"
                    :datasource-options="data.datasourceAliasOptions"
                    :environment-options="sqlEnvironmentOptions"
                    :project-product-id="apiProjectProductId"
                    :test-env="userStore.selected_environment"
                    :on-delete-item="(index) => removeFrontSql1(pageData.record.front_sql, index)"
                    :on-save="upDataCase"
                    @update:item="
                      (index, value) =>
                        updateArrayItem(
                          pageData.record.front_sql,
                          index,
                          value,
                          pageData.record,
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
                    v-if="data.apiType === '1' && data.apiSonType === '14'"
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
                          v-model="pageData.record.front_headers"
                          :disabled="caseEditLocked"
                          direction="vertical"
                          @change="changeHeaders"
                        >
                          <a-checkbox
                            v-for="item of data.headers_list"
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
                :data="data.data"
                :loading="stepTableLoading"
                :selected-step-id="data.tabelJson?.id"
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
                @recovery="openRecoveryConfig"
              />
            </template>
            <template #cleanup>
              <a-tabs
                :active-key="data.apiSonType"
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
                    :data-list="pageData.record.posterior_sql"
                    :datasource-options="data.datasourceAliasOptions"
                    :environment-options="sqlEnvironmentOptions"
                    :project-product-id="apiProjectProductId"
                    :test-env="userStore.selected_environment"
                    :on-delete-item="
                      (index) => removeFrontSql1(pageData.record.posterior_sql, index)
                    "
                    :on-save="upDataCase"
                    empty-text="暂无数据库操作配置，点击上方“增加”按钮添加"
                    @update:item="
                      (index, value) =>
                        updateArrayItem(
                          pageData.record.posterior_sql,
                          index,
                          value,
                          pageData.record,
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
                  :loading="data.collapseLoading"
                  tip="场景数据加载中..."
                  class="scenario-loading-spin full-width"
                >
                  <a-collapse
                    :bordered="false"
                    :active-key="data.activeCollapseKey"
                    accordion
                    @change="onCollapseChange"
                  >
                    <a-collapse-item v-for="(item, index) of data.selectDataObj" :key="index">
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
                          :loading="!data.collapseLoading && data.caseDetailTabLoading"
                          tip="页签内容加载中..."
                          class="scenario-tab-loading-spin"
                        >
                          <ApiCaseScenarioNav
                            :active-key="data.caseDetailsTypeKey"
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
                                :active-key="data.tabsKey"
                                :active="isActiveCaseDetailTab('1', '12')"
                                :edit-locked="caseEditLocked"
                                :datasource-options="data.datasourceAliasOptions"
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
                                :active-key="data.tabsKey"
                                :edit-locked="caseEditLocked"
                                :header-options="data.parameter_headers_list"
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
                                :active-key="data.tabsKey"
                                :active-root="data.caseDetailsTypeKey === '2'"
                                :protocol-type="getScenarioProtocolType(item)"
                                :body-type="getScenarioBodyType(item)"
                                @change="tabsChange($event, item)"
                              />
                            </template>
                            <template #posterior>
                              <ApiCasePosteriorPanel
                                :item="item"
                                :active-key="data.tabsKey"
                                :edit-locked="caseEditLocked"
                                :datasource-options="data.datasourceAliasOptions"
                                :environment-options="sqlEnvironmentOptions"
                                :project-product-id="apiProjectProductId"
                                :test-env="userStore.selected_environment"
                                @change="tabsChange($event, item)"
                              />
                            </template>
                            <template #assertion>
                              <ApiCaseAssertionPanel
                                :item="item"
                                :active-key="data.tabsKey"
                                :edit-locked="caseEditLocked"
                                :verifying="assertionVerifyLoadingId === item.id"
                                :schema-loading="schemaLoadingId === item.id"
                                :compare-open="Boolean(item.__assertion_compare_open)"
                                :compare-results="getAssertionResultData(item)"
                                :compare-source="Array.isArray(item.__assertion_verify_result) ? 'verify' : 'runtime'"
                                :compare-stale="isAssertionVerifyStale(item)"
                                :text-methods="data.textAss"
                                :general-methods="data.ass"
                                :sql-datasource-options="sqlAssertionDatasourceOptions"
                                :sql-method-options="sqlAssertionMethodOptions"
                                @change="tabsChange($event)"
                                @save="blurSave"
                                @verify="verifyAssertions(item)"
                                @toggle-compare="item.__assertion_compare_open = !item.__assertion_compare_open"
                                @generate-schema="setSchema(item.id)"
                              />
                            </template>
                            <template #runtime>
                              <ApiCaseRuntimeCachePanel
                                :active="data.caseDetailsTypeKey === '5'"
                                :data="item.result_data?.cache_data"
                              />
                            </template>
                            <template #factory>
                              <ApiCaseDataFactoryPanel
                                :active="data.caseDetailsTypeKey === '7'"
                                :data="item.result_data?.data_factory_cache_data"
                              />
                            </template>
                            <template #assertion-result>
                              <div class="m-2">
                                <AssertionResult
                                  v-if="data.caseDetailsTypeKey === '6'"
                                  :data="getAssertionResultData(item)"
                                  :stale="isAssertionVerifyStale(item)"
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
  <ApiCaseRecoveryConfig ref="recoveryConfigRef" @saved="doRefresh" />
  <ApiCaseExecutionTraceDrawer ref="traceDrawerRef" />
  <ApiCaseDiagnosisDrawer ref="caseDiagnosisDrawerRef" :result-id="selectedExecutionResultSummary?.id" />
  <ModalDialog ref="modalDialogRef" :title="data.actionTitle" @confirm="onDataForm">
    <template #content>
      <a-form :model="formModel">
        <a-form-item
          v-for="item of formItems"
          :key="item.key"
          v-show="!item.hidden"
          :class="[item.required ? 'mango-form-item__require' : 'mango-form-item__no_require']"
          :label="item.label"
        >
          <template v-if="item.type === 'input'">
            <a-input v-model="item.value" :placeholder="item.placeholder" />
          </template>
          <template v-else-if="item.type === 'cascader' && item.key === 'module'">
            <ProductModuleSelect
              v-model="item.value"
              :project-product-id="apiProjectProductId as string"
              :placeholder="item.placeholder"
              @change="getModuleApi"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'api_info'">
            <a-select
              v-model="item.value"
              :field-names="fieldNames"
              :options="data.apiList"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              value-key="key"
              @change="loadApiInfoRevisions"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'pinned_api_info_revision'">
            <a-select
              v-model="item.value"
              :field-names="fieldNames"
              :options="data.apiRevisionList"
              :placeholder="item.placeholder"
              allow-clear
            />
          </template>
        </a-form-item>
      </a-form>
    </template>
  </ModalDialog>
  <ModalDialog
    ref="modalDialogRefParameter"
    :title="data.actionParameterTitle"
    @confirm="onDataFormParameter"
  >
    <template #content>
      <a-form :model="formParameterModel">
        <a-form-item
          v-for="item of formParameterItems"
          v-show="isParameterFormItemVisible(item)"
          :key="item.key"
          :class="[item.required ? 'mango-form-item__require' : 'mango-form-item__no_require']"
          :label="item.label"
        >
          <template v-if="item.type === 'input'">
            <a-input v-model="item.value" :placeholder="item.placeholder" />
          </template>
          <template v-else-if="item.type === 'select'">
            <div class="scenario-protocol-expectation-control">
              <a-select v-model="item.value" :options="item.optionItems" />
              <span class="scenario-allow-failure-control__hint">{{ item.placeholder }}</span>
            </div>
          </template>
          <template v-else-if="item.type === 'switch'">
            <div class="scenario-allow-failure-control">
              <a-switch v-model="item.value" size="small" />
              <span class="scenario-allow-failure-control__hint">{{ item.placeholder }}</span>
            </div>
          </template>
        </a-form-item>
      </a-form>
    </template>
  </ModalDialog>
</template>

<script lang="ts" setup>
  import { computed, nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'
  import { useRoute } from 'vue-router'
  import { getFormItems } from '@/utils/datacleaning'
  import { ModalDialogType } from '@/types/components'
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
  import { columns, formItems, formParameterItems } from './config'
  import {
    getApiCase,
    getApiCaseRunRaw,
    postApiCaseStepDebugRaw,
    putApiCase,
  } from '@/api/apitest/case'
  import {
    deleteApiCaseDetailed,
    getApiCaseDetailed,
    postApiCaseDetailed,
    putApiPutCaseSort,
    putApiPutRefreshApiInfo,
  } from '@/api/apitest/case_detailed'
  import { getApiInfoName } from '@/api/apitest/info'
  import useUserStore from '@/store/modules/user'
  import { useEnum } from '@/store/modules/get-enum'
  import { getApiHeaders } from '@/api/apitest/headers'
  import { getApiPublic } from '@/api/apitest/public'
  import { getApiAuthConfig } from '@/api/apitest/auth-config'
  import {
    deleteApiCaseDetailedParameter,
    getApiCaseDetailedParameter,
    postApiCaseDetailedParameter,
    postApiCaseDetailedParameterCopy,
    postVerifyApiCaseAssertions,
    putApiCaseDetailedParameter,
    putSetSchema,
  } from '@/api/apitest/case-detailed-parameter'
  import { getSystemCacheDataKeyValue } from '@/api/system/cache_data'
  import KeyValueList from '@/components/forms/KeyValueList.vue' // 引入新组件
  import AssertionResult from '@/components/feedback/AssertionResult.vue'
  import TipMessage from '@/components/feedback/TipMessage.vue' // 引入断言结果组件
  import DataFactoryCaseConfigPanel from '@/components/DataFactory/CaseConfigPanel.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import DataSourceOperationList from '@/components/forms/DataSourceOperationList.vue'
  import ApiCaseVersionPanel from './components/ApiCaseVersionPanel.vue'
  import ApiCasePageHeader from './components/ApiCasePageHeader.vue'
  import ApiCaseConfigSearchModal from './components/ApiCaseConfigSearchModal.vue'
  import ApiCaseExecutionTraceDrawer from './components/ApiCaseExecutionTraceDrawer.vue'
  import ApiCaseDiagnosisDrawer from './components/ApiCaseDiagnosisDrawer.vue'
  import ApiCaseInfoDetailPanel from './components/ApiCaseInfoDetailPanel.vue'
  import ApiCaseStepTable from './components/ApiCaseStepTable.vue'
  import ApiCaseRecoveryConfig from './components/ApiCaseRecoveryConfig.vue'
  import ApiCaseOrchestrationPanel from './components/ApiCaseOrchestrationPanel.vue'
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

  const userStore = useUserStore()
  const FRONT_FUNC_TEMPLATE = `def func(self, request):
    # self 是当前执行上下文，常用能力：
    # self.test_setup.test_data：变量/缓存工具，支持 get_cache、set_cache、replace 等
    # self.case_parameter：当前场景参数对象，可查看当前场景配置
    test_data = self.test_setup.test_data
    try:
        username = test_data.get_cache('username')
    except Exception:
        username = None

    # request 是本次即将发送的请求模型，常用字段：
    method = request.method  # 请求方法：GET/POST/PUT/PATCH/DELETE...
    url = request.url  # 请求地址，通常已拼接环境域名
    headers = request.headers or {}  # 请求头
    params = request.params  # Query 参数，支持 dict/list/str
    protocol_type = request.protocol_type  # 协议类型：http/sse
    body_type = request.body_type  # 请求体类型：none/json/form/raw/multipart
    body_config = request.body_config or {}  # 请求体配置
    sse_config = request.sse_config  # SSE 停止条件配置
    posterior_file = request.posterior_file  # 响应文件保存到缓存的 key

    # 修改请求示例：追加请求头
    headers['X-Debug-User'] = username or 'anonymous'
    request.headers = headers

    # 修改 JSON 请求体示例
    if body_type == 'json':
        body = body_config.get('body_text') if body_config.get('source_type') == 'template' else body_config.get('body')
        if isinstance(body, dict):
            body['operator'] = username
            request.body_config = {'source_type': 'value', 'body': body}

    return request`

  const POSTERIOR_FUNC_TEMPLATE = `def func(self, response):
    # self 是当前执行上下文，常用能力：
    # self.test_setup.test_data：变量/缓存工具，支持 get_cache、set_cache、replace 等
    # self.case_parameter：当前场景参数对象，可查看当前场景配置
    test_data = self.test_setup.test_data

    # response 是本次接口响应模型，常用字段：
    code = response.code  # HTTP 状态码
    time = response.time  # 响应耗时，单位秒
    url = response.url  # 实际请求 URL
    headers = response.headers or {}  # 响应头
    json_body = response.json  # 解析后的 JSON，可能是 dict/list/str/number/bool/null
    text = response.text  # 原始响应文本，非 JSON 或文本断言可使用
    response_mode = response.response_mode  # 响应模式：http/sse/grpc/websocket
    sse_events = response.sse_events  # SSE 事件列表，仅 SSE 场景有值
    sse_stop_reason = response.sse_stop_reason  # SSE 停止原因
    request_body = response.request_body  # 实际发送的请求体
    request_headers = response.request_headers  # 实际发送的请求头

    # 提取响应数据到缓存示例
    if isinstance(json_body, dict):
        data = json_body.get('data') or {}
        if isinstance(data, dict) and data.get('id'):
            test_data.set_cache('response_id', data.get('id'))

    # 修改响应示例：追加自定义错误信息
    if code >= 400 and not response.error_msg:
        response.error_msg = text

    return response`

  const modalDialogRef = ref<ModalDialogType | null>(null)
  const modalDialogRefParameter = ref<ModalDialogType | null>(null)
  const dataFactoryPanelRef = ref<InstanceType<typeof DataFactoryCaseConfigPanel> | null>(null)
  const formModel = ref({})
  const formParameterModel = ref({})
  const pageData: any = usePageData()
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
  const apiCaseId = computed(
    () => props.caseId || route.query.case_id || route.query.id || pageData.record?.id || ''
  )
  const apiProjectProductId = computed(
    () =>
      props.projectProductId ||
      route.query.project_product ||
      pageData.record?.project_product?.id ||
      pageData.record?.project_product ||
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
    posterior_sql: [],
    project_product: apiProjectProductId.value ? { id: apiProjectProductId.value } : null,
  })
  if (!pageData.record) {
    pageData.setRecord(defaultCaseRecord())
  }
  const enumStore = useEnum()
  const caseVariableEnvironmentOptions = computed(() => [
    { key: COMMON_ENV_VALUE, title: '环境通用' },
    ...enumStore.environment_type,
  ])
  const versionPanelRef = ref<InstanceType<typeof ApiCaseVersionPanel> | null>(null)
  const selectedExecutionVersion = ref<ApiCaseExecutionVersion | null>(null)
  const selectedExecutionResultSummary = ref<any>(null)
  const selectedCaseVersionDetail = ref<ApiCaseRevisionDetail | null>(null)
  const snapshotParametersByStep = new Map<string, any[]>()
  const liveCaseRecord = ref<any>(null)
  const liveCaseRows = ref<any[]>([])
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
    item: null as any,
  })
  const apiInfoDetailPanelRef = ref<InstanceType<typeof ApiCaseInfoDetailPanel> | null>(null)
  const recoveryConfigRef = ref<InstanceType<typeof ApiCaseRecoveryConfig> | null>(null)

  function openRecoveryConfig(step: any) {
    if (!ensureCaseEditable() || caseExecutionActive.value) return
    recoveryConfigRef.value?.open(step)
  }
  const data: any = reactive({
    actionTitle: '新增执行编排',

    assClickAdd: true,
    results: null,
    selectDataObj: [],
    data: [],
    apiList: [],
    apiRevisionList: [],
    ass: [],
    textAss: [],
    caseHeadersList: [],
    caseDetailsHeadersList: [],
    headers_list: [],
    parameter_headers_list: [],
    apiType: '2',
    apiSonType: '0',
    caseDetailsTypeKey: '2',
    tabsKey: '10',

    actionParameterTitle: '新增接口场景',
    isAdd: true,
    isCopy: false,
    copyParameterId: null,
    updateId: null,
    activeCollapseKey: [0],
    mountedCollapseKeys: [],
    collapseLoading: false, // 列表整体 loading
    caseConfigLoading: false,
    caseDetailTabLoading: false,
    expandingIndex: -1, // 正在展开中的 item index，-1 表示无
    datasourceAliasOptions: [],
    publicOptions: [],
    authConfigOptions: [],
  })

  const {
    caseRunning,
    caseRequestPending,
    debugRunningStepId,
    debugRequestPending,
    lastTraceId,
    caseRunRefreshTimer,
    startCaseRunRefresh,
    stopCaseRunRefresh,
    startCaseRunLoadingLimit,
    stopCaseRunLoadingLimit,
    startDebugRunLoadingLimit,
    stopDebugRunLoadingLimit,
    disposeExecutionTimers,
  } = useApiCaseExecution(() => refreshCaseRunStatusByStep())
  const stepTableLoading = ref(false)
  const caseGlobalSaving = ref(false)
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
    () => !(data.apiType === '1' && ['13', '15', '16'].includes(data.apiSonType))
  )
  const toggleScenarioWorkbench = () => {
    scenarioWorkbenchExpanded.value = !scenarioWorkbenchExpanded.value
  }
  const apiCaseDetailTitle = computed(() => {
    const id = apiCaseId.value || '-'
    const name = pageData.record?.name || '-'
    return `组合用例场景配置 / ${id} / ${name}`
  })
  const frontPublicCheckedValues = computed({
    get: () => mergeCheckedOptionValues(pageData.record.front_public, data.publicOptions),
    set: (value: any[]) => {
      pageData.record.front_public = filterOptionalOptionValues(value, data.publicOptions)
    },
  })
  const frontAuthConfigCheckedValues = computed({
    get: () => mergeCheckedOptionValues(pageData.record.front_auth_config, data.authConfigOptions),
    set: (value: any[]) => {
      pageData.record.front_auth_config = filterOptionalOptionValues(value, data.authConfigOptions)
    },
  })
  const traceDrawerRef = ref<InstanceType<typeof ApiCaseExecutionTraceDrawer> | null>(null)
  const caseDiagnosisDrawerRef = ref<InstanceType<typeof ApiCaseDiagnosisDrawer> | null>(null)
  const selectedStepSummary = computed(() => {
    const step = data.tabelJson
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
      Boolean(data.tabelJson?.runtime_result_outdated) ||
      data.selectDataObj.some((item: any) => item.runtime_result_outdated)
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
      caseRunRefreshTimer.value !== null ||
      hasRunningCaseStep(data.data)
  )
  const dataFactoryConfigCache = reactive(new Map<string, number>())
  const parameterCacheByStep = new Map<string, any[]>()
  let latestExecutionResultData: any = null
  const {
    nextParameterLoadToken,
    isCurrentParameterLoad,
    nextExecutionResultLoadToken,
    isCurrentExecutionResultLoad,
    invalidateExecutionResultLoad,
  } = useApiCaseSelection()
  const {
    panelLoaded,
    markPanelLoaded,
    runWithPanelLoading: runCaseDetailTabLoading,
  } = useApiCasePanelLoader(data)
  let caseConfigLoadingCount = 0

  async function runCaseConfigLoading(task: () => void | Promise<void>) {
    caseConfigLoadingCount += 1
    data.caseConfigLoading = true
    try {
      await task()
    } finally {
      caseConfigLoadingCount = Math.max(0, caseConfigLoadingCount - 1)
      data.caseConfigLoading = caseConfigLoadingCount > 0
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
    const rows = Array.isArray(data.selectDataObj) ? data.selectDataObj : []
    for (let index = rows.length - 1; index >= 0; index--) {
      const row = rows[index]
      const testTime = row?.result_data?.test_time || row?.test_time
      if (testTime) return testTime
    }
    return ''
  }

  function isActiveCollapseItem(index: number) {
    return data.activeCollapseKey.some((key: string | number) => String(key) === String(index))
  }

  function isMountedCollapseItem(index: number) {
    return data.mountedCollapseKeys.some((key: string | number) => String(key) === String(index))
  }

  function mountCollapseItem(index: number) {
    if (!isMountedCollapseItem(index)) {
      data.mountedCollapseKeys.push(index)
    }
  }

  function deferMountCollapseItem(index: number) {
    data.expandingIndex = index
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        if (!isActiveCollapseItem(index)) {
          return
        }
        mountCollapseItem(index)
        data.expandingIndex = -1
      })
    })
  }

  function isActiveCaseDetailTab(caseDetailsTypeKey: string, tabsKey: string) {
    return data.caseDetailsTypeKey === caseDetailsTypeKey && data.tabsKey === tabsKey
  }

  function isRuntimeResultTab() {
    return data.caseDetailsTypeKey === '2' || data.caseDetailsTypeKey === '6'
  }

  async function switchType(key: any) {
    if (key === '1') {
      data.apiSonType = '15'
    } else if (key === '3') {
      data.apiSonType = '31'
    }
    data.apiType = key
    if (key !== '2') {
      await runCaseConfigLoading(() => ensureActiveCasePanelLoaded())
    }
  }

  function selectExecutionVersion(version: ApiCaseExecutionVersion) {
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
    selectedCaseVersionDetail.value = null
    caseVersionPayloadActive.value = false
    caseVersionEditUnlocked.value = false
    snapshotParametersByStep.clear()
    if (liveCaseRecord.value) {
      pageData.setRecord(normalizeCaseRecord(liveCaseRecord.value))
    }
    void Promise.all([doRefresh(), loadCaseDataFactoryCount()]).then(() =>
      refreshSelectedRuntimeResult()
    )
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
    const fields = ['id', 'logical_id', 'case_sort', 'posterior_sql', 'api_info_revision_id',
      'execution_config']
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
    if (data.tabelJson && String(data.tabelJson.id) === String(row?.id)) {
      return cloneVersionValue(data.selectDataObj || [])
    }
    return []
  }

  function buildApiCaseCompareCurrentPayload() {
    return {
      api_case: pickCaseEditablePayload(pageData.record || {}),
      api_case_detailed: (Array.isArray(data.data) ? data.data : []).map(
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
    if (!caseVersionPayloadActive.value) {
      liveCaseRecord.value = cloneVersionValue(pageData.record)
      liveCaseRows.value = cloneVersionValue(Array.isArray(data.data) ? data.data : [])
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
      const current =
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
    pageData.setRecord(
      normalizeCaseRecord({ ...pageData.record, ...cloneVersionValue(casePayload) })
    )
    data.caseHeadersList = pageData.record.front_headers
    data.data = rows
    if (rows.length) select(rows[0])
    else {
      data.tabelJson = null
      data.selectDataObj = []
    }
  }

  function executeSelectedVersion(version: ApiCaseExecutionVersion) {
    selectedExecutionVersion.value = version
    caseRun(null, version)
  }

  async function ensureCasePanelLoaded(panelKey: string, record: any = data.tabelJson) {
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

  async function ensureActiveCasePanelLoaded(record: any = data.tabelJson) {
    if (data.apiType === '1') {
      if (data.apiSonType === '15') {
        await ensureCasePanelLoaded('case-public', record)
      } else if (data.apiSonType === '16') {
        await ensureCasePanelLoaded('case-auth', record)
      } else if (data.apiSonType === '12') {
        await ensureCasePanelLoaded('datasource-aliases', record)
      } else if (data.apiSonType === '13') {
        await ensureCasePanelLoaded('case-headers', record)
      }
      return
    }
    if (data.apiType === '3') {
      if (data.apiSonType === '31') {
        await ensureCasePanelLoaded('datasource-aliases', record)
      }
      return
    }
    if (data.apiType !== '2') {
      return
    }
    if (data.caseDetailsTypeKey === '0' && data.tabsKey === '00') {
      await ensureCasePanelLoaded('parameter-headers', record)
    }
    if (['10', '41'].includes(String(data.tabsKey))) {
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
    if (!apiCaseId.value) {
      setCaseDataFactoryCount(0)
      return
    }
    try {
      const res = await getDataFactoryCaseConfig({ source_type: 1, source_id: apiCaseId.value })
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
    if (type === 'custom') return configuredItemCount(pageData.record?.front_custom)
    if (type === 'frontSql') return configuredItemCount(pageData.record?.front_sql)
    if (type === 'factory') return caseDataFactoryCount.value
    if (type === 'headers') return configuredItemCount(pageData.record?.front_headers)
    return configuredItemCount(pageData.record?.posterior_sql)
  }

  function setScenarioDataFactoryCount(id: number | string, count: number) {
    dataFactoryConfigCache.set(String(id), Math.max(0, Number(count) || 0))
  }

  async function loadScenarioDataFactoryCounts(items: any[]) {
    await Promise.allSettled(
      items.map(async (item) => {
        const cacheKey = String(item?.id || '')
        if (!cacheKey || dataFactoryConfigCache.has(cacheKey)) return
        const res = await getDataFactoryCaseConfig({ source_type: 3, source_id: item.id })
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
        configuredItemCount(item?.ass_general)
      )
    }
    if (tab === 'cache') return resultItemCount(item?.result_data?.cache_data)
    if (tab === 'factory') {
      return resultItemCount(item?.result_data?.data_factory_cache_data)
    }
    return getAssertionResultData(item).length
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
    if (data.caseDetailTabLoading) {
      return
    }
    await runCaseDetailTabLoading(async () => {
      data.caseDetailsTypeKey = key
      if (key === '0') {
        if (hasConfigValue(item?.body_config) || getScenarioBodyType(item) !== 'none') {
          data.tabsKey = '02'
        } else if (hasConfigValue(item?.params)) {
          data.tabsKey = '01'
        } else if (hasConfigValue(item?.headers)) {
          data.tabsKey = '00'
        } else {
          data.tabsKey = '02'
        }
      } else if (key === '1') {
        await switchFrontProcessTab(item)
      } else if (key === '2') {
        data.tabsKey = getResultResponseTabKey(item)
      } else if (key === '3') {
        if (item.ass_sql && item.ass_sql.length > 0) {
          data.tabsKey = '35'
          data.assClickAdd = true
        } else if (item.ass_general && item.ass_general.length > 0) {
          data.tabsKey = '32'
          data.assClickAdd = true
        } else if (item.ass_jsonpath && item.ass_jsonpath.length > 0) {
          data.tabsKey = '31'
          data.assClickAdd = true
        } else if (item.ass_text_all) {
          data.tabsKey = '33'
          data.assClickAdd = false
        } else if (item.ass_schema) {
          data.tabsKey = '34'
          data.assClickAdd = false
        } else {
          data.tabsKey = '30'
          data.assClickAdd = false
        }
      } else if (key === '4') {
        if (hasConfigValue(item.posterior_response)) {
          data.tabsKey = '40'
        } else if (hasConfigValue(item.posterior_response_text)) {
          data.tabsKey = '44'
        } else if (hasConfigValue(item.posterior_sql)) {
          data.tabsKey = '41'
        } else if (hasConfigValue(item.posterior_sleep)) {
          data.tabsKey = '42'
        } else if (hasConfigValue(item.posterior_func)) {
          data.tabsKey = '43'
        } else {
          data.tabsKey = '40'
        }
        data.assClickAdd = !['42', '43'].includes(String(data.tabsKey))
      } else if (key === '5') {
        data.tabsKey = '50'
      }
      await ensureActiveCasePanelLoaded(item)
      if (key === '2') {
        data.tabsKey = getResultResponseTabKey(item)
      }
    })
  }

  async function switchFrontProcessTab(item: any) {
    if (item?.front_sql && item.front_sql.length > 0) {
      data.tabsKey = '10'
      data.assClickAdd = true
      return
    }
    if (item?.front_func) {
      data.tabsKey = '11'
      data.assClickAdd = false
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
        data.tabsKey = '12'
        data.assClickAdd = true
        return
      }
    } catch (error) {
      console.log(error)
    }
    data.tabsKey = '10'
    data.assClickAdd = true
  }

  async function switchSonType(key: any) {
    data.apiSonType = key
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
    if (data.caseDetailTabLoading) {
      return
    }
    if (isRuntimeResultTab()) {
      data.tabsKey = key
      return
    }
    await runCaseDetailTabLoading(async () => {
      data.tabsKey = key
      fillDefaultFunc(item, key)
      data.assClickAdd = !(
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
    if (data.apiType == '2') {
      addApiInfo()
      return
    }
    if (data.apiSonType === '11') {
      pageData.record.front_custom.push({ key: '', value: '', test_envs: [] })
    } else if (data.apiSonType === '12') {
      pageData.record.front_sql.push({ key: '', value: '', datasource_alias: null, test_envs: [] })
    } else if (data.apiSonType === '14') {
      dataFactoryPanelRef.value?.open()
    } else if (data.apiSonType === '31') {
      pageData.record.posterior_sql.push({
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
    schemaLoadingId.value = id
    putSetSchema(id)
      .then((res) => {
        Message.success(res.msg)
        doRefreshParameter(data.tabelJson.id, { force: true })
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
      return item.__assertion_verify_result
    }
    return Array.isArray(item?.result_data?.ass) ? item.result_data.ass : []
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
    return Boolean(item?.__assertion_verify_result) && (
      Boolean(item.__assertion_verify_stale)
      || item.__assertion_verify_signature !== getAssertionVerifySignature(item)
    )
  }

  function clearAssertionVerifyResults() {
    data.selectDataObj.forEach((item: any) => {
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
    try {
      const res = await postVerifyApiCaseAssertions({
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

  function parameterEditing(item: any) {
    if (!ensureCaseEditable()) return
    data.actionParameterTitle = '编辑接口场景名称'
    data.isAdd = false
    data.isCopy = false
    data.copyParameterId = null
    data.updateId = item.id
    modalDialogRefParameter.value?.toggle()
    nextTick(() => {
      formParameterItems.forEach((it) => {
        const expectation = item.body_config?.protocol_expectation || {}
        const legacyStatusCodes = getLegacyExpectedStatusCodes(item)
        const propName =
          it.key === 'protocol_expectation_mode'
            ? expectation.mode || (legacyStatusCodes.length ? 'codes' : 'auto')
            : it.key === 'protocol_expectation_codes'
            ? (expectation.status_codes || legacyStatusCodes).join(',')
            : it.key === 'allow_failure'
            ? Boolean(item[it.key])
            : item[it.key]
        if (typeof propName === 'object' && propName !== null) {
          it.value = propName.id
        } else {
          it.value = propName
        }
      })
    })
  }

  function parameterCopy(item: any) {
    if (!ensureCaseEditable()) return
    data.actionParameterTitle = '复制接口场景'
    data.isAdd = false
    data.isCopy = true
    data.copyParameterId = item.id
    data.updateId = null
    modalDialogRefParameter.value?.toggle()
    nextTick(() => {
      formParameterItems.forEach((it) => {
        const expectation = item.body_config?.protocol_expectation || {}
        const legacyStatusCodes = getLegacyExpectedStatusCodes(item)
        const propName =
          it.key === 'protocol_expectation_mode'
            ? expectation.mode || (legacyStatusCodes.length ? 'codes' : 'auto')
            : it.key === 'protocol_expectation_codes'
            ? (expectation.status_codes || legacyStatusCodes).join(',')
            : it.key === 'allow_failure'
            ? Boolean(item[it.key])
            : item[it.key]
        if (typeof propName === 'object' && propName !== null) {
          it.value = propName.id
        } else {
          it.value = propName
        }
      })
    })
  }

  function parameterDelete(item: any) {
    if (!ensureCaseEditable()) return
    Modal.confirm({
      title: '提示',
      content: '确定要删除此数据吗？',
      cancelText: '取消',
      okText: '删除',
      onBeforeOk: () => {
        return deleteApiCaseDetailedParameter(item.id)
          .then((res) => {
            Message.success(res.msg)
            doRefreshParameter(data.tabelJson.id, { force: true })
          })
          .catch(console.log)
      },
    })
  }

  function removeFrontSql1(item: any, index: number, refreshScenario = true) {
    if (!ensureCaseEditable()) return
    item.splice(index, 1)

    upDataCase({ refreshScenario })
  }

  function openJsonEditDrawer(field: string, label: string, item: any) {
    if (!ensureCaseEditable()) return
    jsonEditDrawer.visible = true
    jsonEditDrawer.field = field
    jsonEditDrawer.label = label
    jsonEditDrawer.title = `${label} JSON 编辑`
    jsonEditDrawer.item = item
    jsonEditDrawer.value = item?.[field] || ''
  }

  function saveJsonEditDrawer(value = jsonEditDrawer.value) {
    if (!ensureCaseEditable()) return
    const item = jsonEditDrawer.item
    const field = jsonEditDrawer.field
    if (!item || !field) return
    if (jsonEditSaving.value) return
    jsonEditSaving.value = true
    item[field] = value
    const saveTask = blurSave(field, value, item.id)
    if (!saveTask) {
      jsonEditSaving.value = false
      return
    }
    saveTask
      .then(() => {
        jsonEditDrawer.visible = false
      })
      .finally(() => {
        jsonEditSaving.value = false
      })
  }

  function changeHeaders(selectedValues: any) {
    if (!ensureCaseEditable()) return
    const value = {
      id: pageData.record.id,
      front_headers: selectedValues,
    }
    putApiCase(value)
      .then((res) => {
        Message.success(res.msg)
        doRefresh()
      })
      .catch(console.log)
  }

  async function changeCaseGlobalOptions() {
    if (!ensureCaseEditable()) return
    if (caseGlobalSaving.value) return
    caseGlobalSaving.value = true
    const frontPublic = filterOptionalOptionValues(pageData.record.front_public, data.publicOptions)
    const frontAuthConfig = filterOptionalOptionValues(
      pageData.record.front_auth_config,
      data.authConfigOptions
    )
    pageData.record.front_public = frontPublic
    pageData.record.front_auth_config = frontAuthConfig
    try {
      const res = await putApiCase({
        id: pageData.record.id,
        front_public: frontPublic,
        front_auth_config: frontAuthConfig,
      })
      Message.success(res.msg)
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
    putApiCase({
      id: pageData.record.id,
      name: pageData.record.name,
      posterior_sql: pageData.record.posterior_sql,
      front_sql: pageData.record.front_sql,
      front_custom: pageData.record.front_custom,
      front_headers: pageData.record.front_headers,
      front_public: pageData.record.front_public,
      front_auth_config: pageData.record.front_auth_config,
    })
      .then((res) => {
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

  function blurSave(key: string, item: string | null, id: number) {
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
      const currentItem = data.selectDataObj.find((scenario: any) => scenario.id === id)
      if (currentItem?.__assertion_verify_result
        && currentItem.__assertion_verify_signature !== getAssertionVerifySignature(currentItem)) {
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
      if (formatJsonObj(key, item) === false) {
        return null
      } else {
        payload[key] = formatJsonObj(key, item)
      }
    } else if (key === 'ass_general') {
      payload[key] = normalizeAssGeneral(item)
    } else if (key === 'ass_jsonpath') {
      payload[key] = normalizeAssJsonpath(item)
    } else {
      payload[key] = item
    }

    return putApiCaseDetailedParameter(payload)
      .then((res) => {
        Message.success(res.msg)
      })
      .catch(console.log)
  }

  function getScenarioProtocolType(item: any) {
    return data.tabelJson?.api_info?.protocol_type || item?.api_info?.protocol_type || 'http'
  }

  function isParameterFormItemVisible(item: any) {
    const protocolType = String(data.tabelJson?.api_info?.protocol_type || 'http').toLowerCase()
    if (['mcp', 'grpc', 'websocket'].includes(protocolType)) {
      return !String(item.key).startsWith('protocol_expectation_')
    }
    if (item.key === 'protocol_expectation_codes') {
      return (
        formParameterItems.find((formItem) => formItem.key === 'protocol_expectation_mode')
          ?.value === 'codes'
      )
    }
    return true
  }

  function getLegacyExpectedStatusCodes(item: any) {
    const codes = new Set<number>()
    const addCode = (value: unknown) => {
      const code = Number(value)
      if (Number.isInteger(code) && code >= 100 && code <= 599) {
        codes.add(code)
        return
      }
      const prefix = Number(String(value || '').slice(0, 3))
      if ([400, 404, 405, 409, 422].includes(prefix)) codes.add(prefix)
    }
    let jsonAll = item?.ass_json_all
    if (typeof jsonAll === 'string') {
      try {
        jsonAll = JSON.parse(jsonAll)
      } catch {
        jsonAll = null
      }
    }
    if (jsonAll && typeof jsonAll === 'object') addCode(jsonAll.code)
    ;(item?.ass_jsonpath || []).forEach((assertion: any) => {
      const actual = String(assertion?.actual || '').trim()
      const method = String(assertion?.method || '').toLowerCase()
      if (
        ['$.code', '$["code"]', "$['code']"].includes(actual) &&
        (!method || method.includes('equal'))
      ) {
        addCode(assertion.expect)
      }
    })
    addCode(item?.ass_schema?.properties?.code?.const)
    const latestHttpStatus = Number(item?.result_data?.response?.code)
    if ([400, 404, 405, 409, 422].includes(latestHttpStatus)) codes.add(latestHttpStatus)
    return Array.from(codes).sort((left, right) => left - right)
  }

  function getScenarioBodyType(item: any) {
    return data.tabelJson?.api_info?.body_type || item?.api_info?.body_type || 'none'
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
            data.ass.push(item)
          }
          if (item.value === '内容断言') {
            data.textAss.push(...item.children)
          }
          if (item.value === '自定义断言') {
            data.textAss.push(...item.children)
          }
        })
      })
      .catch(console.log)
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
    if (pageData.record?.id && String(pageData.record.id) === String(caseId)) {
      pageData.setRecord(normalizeCaseRecord(pageData.record))
      return
    }
    const res = await getApiCase({ id: caseId, page: 1, pageSize: 1 } as any)
    const record = (res.data || [])[0]
    pageData.setRecord(normalizeCaseRecord(record || { id: caseId }))
  }

  function doRefresh(options: { loadParameters?: boolean } = {}) {
    if (!apiCaseId.value) return Promise.resolve()
    stepTableLoading.value = true
    data.caseHeadersList = pageData.record.front_headers
    return getApiCaseDetailed(apiCaseId.value)
      .then((res) => {
        const rows = Array.isArray(res.data) ? res.data.map(normalizeCaseDetailRow) : []
        data.data = rows
        let selectionRefresh: Promise<void> = Promise.resolve()
        if (data.tabelJson && rows.length) {
          const selected = rows.find((item: any) => item.id === data.tabelJson.id)
          if (selected) {
            selectionRefresh = select(selected, {
              loadParameters: options.loadParameters !== false,
            })
          }
        } else if (rows.length) {
          selectionRefresh = select(rows[0], {
            loadParameters: options.loadParameters !== false,
          })
        } else {
          data.tabelJson = null
          data.selectDataObj = []
        }
        syncCaseRunRefreshByRows(rows)
        return selectionRefresh
      })
      .catch(console.log)
      .finally(() => {
        stepTableLoading.value = false
      })
  }

  function doRefreshParameter(id: number, options: { force?: boolean } = {}): Promise<boolean> {
    const cacheKey = String(id)
    const loadToken = nextParameterLoadToken()
    const isCurrentSelection = () =>
      isCurrentParameterLoad(loadToken) && String(data.tabelJson?.id || '') === cacheKey
    if (!options.force && parameterCacheByStep.has(cacheKey)) {
      if (!isCurrentSelection()) return Promise.resolve(false)
      data.collapseLoading = false
      data.selectDataObj = cloneVersionValue(parameterCacheByStep.get(cacheKey) || [])
      data.activeCollapseKey = data.selectDataObj.length ? [0] : []
      data.mountedCollapseKeys = []
      data.expandingIndex = -1
      onCollapseChange(data.selectDataObj.length ? [0] : [])
      void loadScenarioDataFactoryCounts(data.selectDataObj)
      return Promise.resolve(true)
    }
    data.collapseLoading = true
    dataFactoryConfigCache.clear()
    data.mountedCollapseKeys = []
    data.expandingIndex = -1
    return getApiCaseDetailedParameter({ case_detailed_id: id })
      .then(
        (res) =>
          new Promise<boolean>((resolve) => {
            const formattedItems: any[] = []
            if (!res.data || res.data.length === 0) {
              parameterCacheByStep.set(cacheKey, [])
              if (isCurrentSelection()) {
                data.selectDataObj = []
                data.activeCollapseKey = []
                data.collapseLoading = false
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
                data.selectDataObj = formattedItems
                data.activeCollapseKey = formattedItems.length ? [0] : []
                data.collapseLoading = false
                onCollapseChange(formattedItems.length ? [0] : [])
                void loadScenarioDataFactoryCounts(formattedItems)
                resolve(true)
              }
            }

            requestAnimationFrame(writeBatch)
          })
      )
      .catch(() => {
        if (isCurrentSelection()) data.collapseLoading = false
        return false
      })
  }

  function normalizeExecutionResultSteps(resultData: any) {
    if (Array.isArray(resultData)) return resultData
    return Array.isArray(resultData?.steps) ? resultData.steps : []
  }

  function findScenarioResult(resultData: any, scenarioId: any) {
    const steps = normalizeExecutionResultSteps(resultData)
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
    parameterCacheByStep.clear()
    selectedExecutionResultSummary.value = null
    data.data.forEach((row: any) => {
      row.status = 2
      row.error_message = null
      row.runtime_result_outdated = false
    })
    data.selectDataObj.forEach((parameter: any) => {
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

  async function refreshSelectedRuntimeResult() {
    const loadToken = nextExecutionResultLoadToken()
    latestExecutionResultData = null
    selectedExecutionResultSummary.value = null
    data.data.forEach((row: any) => {
      row.runtime_result_outdated = false
    })
    data.selectDataObj.forEach((parameter: any) => {
      parameter.result_data = null
      parameter.error_message = null
      parameter.runtime_result_outdated = false
    })
    try {
      const latest = await getLatestCaseExecutionResult()
      if (!isCurrentExecutionResultLoad(loadToken)) return
      if (!latest?.resultData) return
      selectedExecutionResultSummary.value = latest.summary
      latestExecutionResultData = latest.resultData
      applyLatestExecutionResultToSnapshot(latest.resultData)
    } catch (error) {
      console.log(error)
    }
  }

  function applyLatestExecutionResultToSnapshot(resultData: any) {
    const resultSteps = normalizeExecutionResultSteps(resultData)
    const configChangedAfterExecution =
      Boolean(pageData.record?.update_time) &&
      Boolean(selectedExecutionResultSummary.value?.create_time) &&
      String(pageData.record.update_time) > String(selectedExecutionResultSummary.value.create_time)
    data.data.forEach((row: any) => {
      const stepResults = resultSteps.filter((item: any) => String(item?.id) === String(row?.id))
      row.runtime_result_outdated = !stepResults.length && configChangedAfterExecution
      if (!stepResults.length) return
      const failed = stepResults.find((item: any) => Number(item?.status) === 0)
      const warning = stepResults.find((item: any) => Number(item?.status) === 4)
      const running = stepResults.find((item: any) => Number(item?.status) === 3)
      const result = failed || warning || running || stepResults[stepResults.length - 1]
      row.status = result.status
      row.error_message = result.error_message
      if (String(data.tabelJson?.id) === String(row.id)) {
        data.tabelJson = row
      }
    })
    data.selectDataObj.forEach((parameter: any) => {
      const result = findScenarioResult(resultData, parameter.id)
      parameter.runtime_result_outdated = !result && configChangedAfterExecution
      if (!result) return
      parameter.status = result.status
      parameter.result_data = result
      parameter.error_message = result.error_message
    })
    if (!caseVersionPayloadActive.value && data.tabelJson?.id) {
      parameterCacheByStep.set(String(data.tabelJson.id), cloneVersionValue(data.selectDataObj))
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
    return rows.some((item: any) => Number(item?.status) === 3)
  }

  function syncCaseRunRefreshByRows(rows: any[]) {
    if (hasRunningCaseStep(rows)) {
      startCaseRunRefresh()
    } else if (!caseRequestPending.value && !debugRequestPending.value) {
      stopCaseRunRefresh()
    }
  }

  function mergeCaseStepRows(rows: any[]) {
    data.data = rows
    const selectedId = data.tabelJson?.id
    if (!selectedId) {
      if (rows.length > 0) data.tabelJson = rows[0]
      return
    }
    const latestSelected = rows.find((item: any) => String(item.id) === String(selectedId))
    if (latestSelected) data.tabelJson = latestSelected
  }

  function refreshCaseRunStatusByStep() {
    if (!apiCaseId.value) return Promise.resolve(false)
    return getApiCaseDetailed(apiCaseId.value)
      .then(async (res) => {
        const rows = Array.isArray(res.data) ? res.data : []
        mergeCaseStepRows(rows)
        if (isRuntimeResultTab()) {
          await refreshSelectedRuntimeResult()
        }
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
      data.activeCollapseKey = []
      data.expandingIndex = -1
      return
    }
    const idx = Number(keys[keys.length - 1])
    data.activeCollapseKey = keys
    if (!isMountedCollapseItem(idx)) {
      deferMountCollapseItem(idx)
    } else {
      data.expandingIndex = -1
    }
    // 懒格式化当前 item
    const item = data.selectDataObj[idx]
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

  async function loadConfigSearchDocuments() {
    const documents: ConfigSearchDocument[] = []
    const caseLocation = `Case ${apiCaseId.value} / ${pageData.record?.name || '-'}`
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
      addConfigSearchDocument(documents, caseLocation, field.label, pageData.record?.[field.key], {
        caseApiType: field.caseApiType,
        caseApiSonType: field.caseApiSonType,
      })
    })

    const steps = Array.isArray(data.data) ? data.data : []
    const stepParameters = new Map<string, any[]>()
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
      configSearch.completed += 1
    })
    const latestExecution = await latestExecutionPromise
    configSearch.completed += 1

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
      const productId = getProjectProductId(pageData.record?.project_product)
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
        pageData.record?.front_headers,
        headerMap,
        `${caseLocation} / 默认请求头`,
        '请求头',
        { caseApiType: '1', caseApiSonType: '13' }
      )
      appendReferencedConfig(
        pageData.record?.front_public,
        publicMap,
        `${caseLocation} / 全局变量`,
        '全局变量',
        { caseApiType: '1', caseApiSonType: '15' }
      )
      appendReferencedConfig(
        pageData.record?.front_auth_config,
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
      configSearch.total += scenarioEntries.length
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
          configSearch.completed += 1
        }
      })
      steps.forEach((step) => {
        ;(stepParameters.get(String(step.id)) || []).forEach((parameter) => {
          appendReferencedConfig(
            parameter.headers,
            headerMap,
            `${step?.api_info?.name || '步骤'} / ${parameter?.name || '场景'} / 请求头`,
            '请求头',
            { stepId: step.id, scenarioId: parameter.id, detailType: '0', detailTab: '00' }
          )
        })
      })
    }
    setConfigSearchDocuments(documents)
  }

  async function openConfigSearch() {
    configSearch.visible = true
    resetConfigSearch()
    try {
      await loadConfigSearchDocuments()
    } catch (error) {
      console.log(error)
      Message.error('当前 Case 数据加载失败，请重试')
    } finally {
      configSearch.loading = false
    }
  }

  async function locateConfigSearchResult(result: ConfigSearchMatch) {
    configSearch.visible = false
    if (result.caseApiType) {
      data.apiType = result.caseApiType
      data.apiSonType = result.caseApiSonType || data.apiSonType
      await runCaseDetailTabLoading(() => ensureActiveCasePanelLoaded())
      return
    }
    if (!result.stepId) return
    const step = data.data.find((item: any) => String(item.id) === String(result.stepId))
    if (!step) return
    data.apiType = '2'
    await select(step)
    if (result.scenarioId) {
      const scenarioIndex = data.selectDataObj.findIndex(
        (item: any) => String(item.id) === String(result.scenarioId)
      )
      if (scenarioIndex >= 0) onCollapseChange([scenarioIndex])
    }
    data.caseDetailsTypeKey = result.detailType || '0'
    data.tabsKey = result.detailTab || '02'
    await runCaseDetailTabLoading(() => ensureActiveCasePanelLoaded(step))
  }

  function loadCaseHeaders(project_product_id: any = apiProjectProductId.value) {
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
        data.headers_list = res.data
        markPanelLoaded(cacheKey)
      })
      .catch(console.log)
  }

  function loadParameterHeaders(project_product_id: any) {
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
        data.parameter_headers_list = res.data
        markPanelLoaded(cacheKey)
      })
      .catch(console.log)
  }

  function loadCasePublicOptions(project_product_id: any = apiProjectProductId.value) {
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
        data.publicOptions = (res.data || []).map((item: any) => ({
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
        data.authConfigOptions = (res.data || []).map((item: any) => ({
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
    if (!executionVersion && !pageData.record?.published_release_id) {
      await versionPanelRef.value?.selectPreferredRevision()
      Message.warning(
        pageData.record?.publication_status === 'prepublished'
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
      await refreshCaseDetailAfterRun()
      stopCaseRunRefresh()
    }
  }

  const debugCaseStep = async (record: any) => {
    if (!apiCaseId.value || !record?.id) return
    if (userStore.selected_environment == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    if (caseExecutionActive.value) return
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
      handleStepDebugResponse(response.data || {})
    } catch (error: any) {
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

  function getModuleApi(moduleId: number) {
    data.apiRevisionList = []
    const apiInfoItem = formItems.find((item) => item.key === 'api_info')
    const revisionItem = formItems.find((item) => item.key === 'pinned_api_info_revision')
    if (apiInfoItem) apiInfoItem.value = ''
    if (revisionItem) revisionItem.value = ''
    getApiInfoName(moduleId)
      .then((res) => {
        data.apiList = res.data
      })
      .catch(console.log)
  }

  function loadApiInfoRevisions(apiInfoId: number | string) {
    const revisionItem = formItems.find((item) => item.key === 'pinned_api_info_revision')
    data.apiRevisionList = []
    if (revisionItem) revisionItem.value = ''
    if (!apiInfoId) return
    const selectedApi = data.apiList.find((item: any) => String(item.key) === String(apiInfoId))
    if (!selectedApi?.published_revision_id) {
      Message.warning('该接口未发布，不能添加到 Case')
      return
    }
    data.apiRevisionList = [
      {
        key: selectedApi.published_revision_id,
        title: selectedApi.published_version_label || '当前发布版本',
      },
    ]
    if (revisionItem) revisionItem.value = selectedApi.published_revision_id
  }

  function loadDatasourceAliases() {
    const productId = getProjectProductId(apiProjectProductId.value)
    if (!productId) return Promise.resolve()
    const cacheKey = `datasource-aliases:${productId}`
    if (panelLoaded(cacheKey)) return Promise.resolve()
    return getDataFactoryDatasourceAlias({
      project_product: productId,
      status: 1,
    })
      .then((res) => {
        data.datasourceAliasOptions = (res.data || []).map((item: any) => ({
          label: item.name,
          value: item.id,
          dbType: item.db_type,
        }))
        markPanelLoaded(cacheKey)
      })
      .catch(console.log)
  }

  const handleChange = (_data: any) => {
    data.data = _data
    let data1: any = []
    data.data.forEach((item: any, index: any) => {
      data1.push({
        id: item.id,
        case_sort: index,
      })
    })
    putApiPutCaseSort(data1)
      .then((res) => {
        Message.success(res.msg)
      })
      .catch(console.log)
  }

  function onDataForm() {
    if (!ensureCaseEditable()) {
      modalDialogRef.value?.setConfirmLoading(false)
      return
    }
    if (formItems.every((it) => (it.validator ? it.validator() : true))) {
      if (!apiCaseId.value) return
      let value = getFormItems(formItems)
      value['case'] = apiCaseId.value
      value['case_sort'] = data.data.length
      postApiCaseDetailed(value, apiCaseId.value)
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
      modalDialogRef.value?.setConfirmLoading(false)
    }
  }

  function onDataFormParameter() {
    if (!ensureCaseEditable()) {
      modalDialogRefParameter.value?.setConfirmLoading(false)
      return
    }
    if (formParameterItems.every((it) => (it.validator ? it.validator() : true))) {
      modalDialogRefParameter.value?.toggle()
      let value = getFormItems(formParameterItems)
      const expectationMode = value.protocol_expectation_mode || 'auto'
      const protocolType = String(data.tabelJson?.api_info?.protocol_type || 'http').toLowerCase()
      if (!['mcp', 'grpc', 'websocket'].includes(protocolType)) {
        value.protocol_expectation = {
          mode: expectationMode,
          status_codes:
            expectationMode === 'codes'
              ? String(value.protocol_expectation_codes || '')
                  .split(',')
                  .map((code) => code.trim())
                  .filter(Boolean)
                  .map((code) => Number(code))
              : [],
        }
      }
      delete value.protocol_expectation_mode
      delete value.protocol_expectation_codes
      if (data.isCopy) {
        value['id'] = data.copyParameterId
        postApiCaseDetailedParameterCopy(value)
          .then((res) => {
            Message.success(res.msg)
            data.isCopy = false
            data.copyParameterId = null
            doRefreshParameter(data.tabelJson.id, { force: true })
          })
          .catch(console.log)
      } else if (data.isAdd) {
        value['case_detailed'] = data.tabelJson.id
        value['api_info'] = data.tabelJson.api_info.id
        postApiCaseDetailedParameter(value)
          .then((res) => {
            Message.success(res.msg)
            doRefreshParameter(data.tabelJson.id, { force: true })
          })
          .catch(console.log)
      } else {
        value['id'] = data.updateId
        putApiCaseDetailedParameter(value)
          .then((res) => {
            Message.success(res.msg)
            doRefreshParameter(data.tabelJson.id, { force: true })
          })
          .catch(console.log)
      }
    }
  }

  function onDelete(record: any) {
    if (!ensureCaseEditable()) return
    Modal.confirm({
      title: '提示',
      content: '是否要删除此接口？',
      cancelText: '取消',
      okText: '删除',
      onBeforeOk: () => {
        return deleteApiCaseDetailed(record.id, apiCaseId.value)
          .then((res) => {
            Message.success(res.msg)
          })
          .catch(console.log)
          .finally(() => {
            doRefresh()
          })
      },
    })
  }

  function addApiInfo() {
    if (!ensureCaseEditable()) return
    data.actionTitle = '新增执行编排'
    modalDialogRef.value?.toggle()
    formItems.forEach((it) => {
      if (it.reset) {
        it.reset()
      } else {
        it.value = ''
      }
    })
    data.apiRevisionList = []
  }

  function addParameter() {
    if (!ensureCaseEditable()) return
    data.actionParameterTitle = '增加接口场景'
    data.isAdd = true
    data.isCopy = false
    data.copyParameterId = null
    modalDialogRefParameter.value?.toggle()
    formParameterItems.forEach((it) => {
      if (it.reset) {
        it.reset()
      } else {
        it.value = ''
      }
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
          .catch(console.log)
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
      data.tabelJson = record || null
      data.selectDataObj = []
      return Promise.resolve()
    }
    data.tabelJson = record
    if (options.loadParameters === false) {
      data.selectDataObj = []
      data.activeCollapseKey = []
      data.mountedCollapseKeys = []
      data.expandingIndex = -1
      return Promise.resolve()
    }
    if (caseVersionPayloadActive.value) {
      const parameters = snapshotParametersByStep.get(String(record.id)) || []
      data.selectDataObj = parameters.map((item: any) => formatParameterJsonFields(item))
      if (latestExecutionResultData) applyLatestExecutionResultToSnapshot(latestExecutionResultData)
      switchApiInfoType(data.caseDetailsTypeKey, data.selectDataObj[0] || record)
      onCollapseChange(data.selectDataObj.length ? [0] : [])
      return Promise.resolve()
    }
    return doRefreshParameter(record.id).then(async (applied) => {
      if (!applied || String(data.tabelJson?.id) !== String(record.id)) return
      if (latestExecutionResultData) applyLatestExecutionResultToSnapshot(latestExecutionResultData)
      await switchApiInfoType(data.caseDetailsTypeKey, data.selectDataObj[0] || record)
      onCollapseChange(data.selectDataObj.length ? [0] : [])
    })
  }

  onMounted(() => {
    nextTick(async () => {
      await ensureCaseRecord()
      void Promise.all([doRefresh(), loadCaseDataFactoryCount()])
      getCacheDataKeyValue()
    })
  })

  onUnmounted(() => {
    disposeExecutionTimers()
  })

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

  function normalizeGroupLogic(value: any) {
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
    data.datasourceAliasOptions.filter((item: any) => [0, 1, 2].includes(Number(item.dbType)))
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
    walk(data.ass)
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
