<template>
  <TableBody
    ref="tableBody"
    :embedded="props.embedded"
    :show-embedded-header="props.embedded"
    class="mango-detail-workbench-page"
  >
    <template #header>
      <div class="mango-detail-toolbar">
        <div class="mango-detail-heading">
          <div class="mango-detail-title">{{ uiCaseDetailTitle }}</div>
          <div class="mango-detail-subtitle">维护用例前后置、步骤编排、断言和执行结果</div>
        </div>
        <a-space class="mango-detail-actions" wrap>
          <a-button
            size="small"
            status="success"
            :loading="caseRunning"
            :disabled="caseExecutionActive || caseSubmitting"
            @click="onCaseRun(false)" data-testid="qa-views-uitest-case-details-button-执行"
          >
            执行
          </a-button>
          <a-button
            size="small"
            type="primary"
            :loading="caseLiveOpening"
            @click="toggleCaseLiveStream"
          >
            <template #icon><icon-desktop /></template>
            {{ liveStreamVisible ? '收起直播' : '开始直播' }}
          </a-button>
          <VariableReferencePanel />
          <a-button size="small" @click="resultHistoryVisible = true" data-testid="qa-views-uitest-case-details-button-历史结果"> 历史结果 </a-button>
          <a-button class="mango-back-button" size="small" @click="doResetSearch" data-testid="qa-views-uitest-case-details-button-返回">返回</a-button>
        </a-space>
      </div>
    </template>
    <template #default>
      <div v-if="caseExecutionRecovering" class="mango-soft-panel" role="status">正在核对执行任务…</div>
      <MangoRequestFeedback v-if="caseExecutionError" :message="(caseExecutionError)"><a-button size="small" :loading="caseExecutionRecovering" :disabled="caseSubmitting" @click="recoverCaseExecution()">重试核对</a-button></MangoRequestFeedback>
      <div
        class="ui-case-workbench mango-detail-workbench mango-detail-workbench--fill mango-detail-workbench--flex mango-workbench-scroll-x"
      >
        <section class="ui-case-panel">
          <div class="ui-case-panel-head">
            <div>
              <div class="ui-case-panel-title">用例编排</div>
              <div class="ui-case-panel-subtitle">维护前置准备、执行编排和后置清理</div>
            </div>
          </div>
          <div class="ui-case-panel-body ui-case-step-compose-body">
            <div v-if="caseConfigurationLoading" class="mango-soft-panel" role="status">正在加载用例配置…</div>
            
            <div v-if="caseConfigurationSaveError || caseGlobalSaving || caseConfigurationDirty" class="mango-soft-panel" role="status">
              <MangoRequestFeedback :message="caseConfigurationSaveError" />
              <span>{{ caseGlobalSaving ? '正在保存用例配置…' : '配置尚未保存' }}</span>
              <a-button size="small" :loading="caseGlobalSaving" :disabled="!caseRecord" @click="upDataCase">保存配置</a-button>
            </div>
            <MangoRequestFeedback v-for="item in configurationOptionErrors" :key="item.label" :message="item.message"><a-button size="small" :loading="item.loading" @click="item.retry">重试{{ item.label }}</a-button></MangoRequestFeedback>
            <a-tabs
              class="ui-case-step-tabs"
              :active-key="caseTab"
              @tab-click="(key) => switchType(key)"
            >
              <template #extra>
                <a-button  v-if="showCaseAddButton" size="small" type="primary" @click="addData" data-testid="qa-views-uitest-case-details-button-新增">
                  新增
                </a-button>
              </template>
              <a-tab-pane key="1" title="前置准备" data-testid="qa-views-uitest-case-details-tab-pane-前置准备">
                <a-tabs
                  class="ui-case-config-tabs"
                  :active-key="caseConfigTab"
                  position="left"
                  @tab-click="(key) => switchSonType(key)"
                >
                  <a-tab-pane key="15">
                    <template #title>
                      <span class="case-config-tab-title">
                        全局变量
                        <span class="case-config-tab-count">{{
                          getCaseConfigCount('public')
                        }}</span>
                      </span>
                    </template>
                    <div class="mango-case-global-options">
                      <a-spin v-if="publicOptionsLoading" />
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
                            :disabled="caseGlobalSaving || !caseRecord || publicOptionsLoading || !!publicVariables.error.value"
                            direction="vertical"
                            @change="changeCaseGlobalOptions"
                          >
                            <a-checkbox
                              v-for="item in publicOptions"
                              :key="item.value"
                              :value="item.value"
                              :disabled="item.disabled || caseGlobalSaving"
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
                  <a-tab-pane key="16">
                    <template #title>
                      <span class="case-config-tab-title">
                        授权管理
                        <span class="case-config-tab-count">{{ getCaseConfigCount('auth') }}</span>
                      </span>
                    </template>
                    <div class="mango-case-global-options">
                      <a-spin v-if="authOptionsLoading" />
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
                            :disabled="caseGlobalSaving || !caseRecord || authOptionsLoading || !!authorizations.error.value"
                            direction="vertical"
                            @change="changeCaseGlobalOptions"
                          >
                            <a-checkbox
                              v-for="item in authConfigOptions"
                              :key="item.value"
                              :value="item.value"
                              :disabled="item.disabled || caseGlobalSaving"
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
                      <span class="case-config-tab-title">
                        自定义变量
                        <span class="case-config-tab-count">{{
                          getCaseConfigCount('custom')
                        }}</span>
                      </span>
                    </template>
                    <div
                      class="mango-horizontal-scroll-region mango-horizontal-scroll-region--compact mango-case-custom-variable-list"
                    >
                      <KeyValueList
                        :data-list="caseDraft.front_custom"
                        :disabled="caseGlobalSaving || !caseRecord"
                        layout="environment-key-value"
                        :field-config="caseVariableFields"
                        :on-delete-item="
                          (index) => removeFrontSql(caseDraft.front_custom, index)
                        "
                        :on-save="upDataCase"
                      />
                    </div>
                  </a-tab-pane>
                  <a-tab-pane key="12">
                    <template #title>
                      <span class="case-config-tab-title">
                        数据库变量
                        <span class="case-config-tab-count">{{
                          getCaseConfigCount('frontSql')
                        }}</span>
                      </span>
                    </template>
                    <DataSourceOperationList
                      :data-list="caseDraft.front_sql"
                      :disabled="caseGlobalSaving || !caseRecord"
                      :datasource-options="datasourceOptions"
                      :datasource-loading="datasourceOptionsLoading"
                      :on-operation-draft-change="caseOperationDraftChanged"
                      :environment-options="sqlEnvironmentOptions"
                      :project-product-id="uiProjectProductId"
                      :test-env="userStore.selected_environment"
                      operation-field="sql"
                      key-field="key_list"
                      key-label="缓存 Key"
                      key-placeholder="请输入查询结果缓存 Key"
                      :on-delete-item="(index) => removeFrontSql(caseDraft.front_sql, index)"
                      :on-save="upDataCase"
                    />
                  </a-tab-pane>
                  <a-tab-pane key="14">
                    <template #title>
                      <span class="case-config-tab-title">
                        数据工厂
                        <span class="case-config-tab-count" :title="caseFactorySummary.error"><a-spin v-if="caseFactorySummary.loading" :size="scaleDensityPixels(12)" /><template v-else>{{ getCaseConfigCount('factory') }}</template></span>
                      </span>
                    </template>
                    <DataFactoryCaseConfigPanel
                      ref="dataFactoryPanelRef"
                      :case-id="uiCaseId ?? ''"
                      :project-product-id="uiProjectProductId ?? ''"
                      :source-type="2"
                      @collection-state="handleCaseFactorySummary"
                    />
                  </a-tab-pane>
                </a-tabs>
              </a-tab-pane>

              <a-tab-pane key="2" title="执行编排" data-testid="qa-views-uitest-case-details-tab-pane-执行编排">
                <section class="ui-case-step-table-drop">
                  
                  <MangoRequestFeedback v-if="stepStructureError" :message="(stepStructureError)" />
                  <MangoRequestFeedback v-if="stepExecutionError" :message="(stepExecutionError)"><a-button size="small" :loading="stepRunning" @click="retryStepExecution()">重试</a-button></MangoRequestFeedback>
                  <div v-if="stepStructurePending?.kind === 'sort'" class="mango-soft-panel" role="status">正在保存步骤顺序…</div>
                  <mango-panel-spin :loading="stepTableLoading" class="ui-case-step-card-spin">
                    <div
                      v-if="caseSteps.length"
                      class="ui-case-step-card-list mango-native-scrollbar"
                    >
                      <article
                        v-for="(record, index) in caseSteps"
                        :key="record.id"
                        :class="[
                          'ui-case-step-card',
                          {
                            'ui-case-step-card--selected':
                              String(selectedCaseStep?.id) === String(record.id),
                            'ui-case-step-card--dragging': String(draggingStepId) === String(record.id),
                          },
                        ]"
                        :draggable="!stepStructurePending"
                        @click="select(record)"
                        @dragstart="onCaseStepDragStart($event, record.id)"
                        @dragend="cancelStepDrag"
                        @dragover.prevent
                        @drop.prevent="dropCaseStep(record.id)"
                      >
                        <div class="ui-case-step-card__head">
                          <div class="ui-case-step-card__identity">
                            <span class="ui-case-step-card__handle" title="拖动调整顺序">⋮⋮</span>
                            <span class="ui-case-step-card__index">{{
                              String(index + 1).padStart(2, '0')
                            }}</span>
                            <strong :title="record.page_step?.name || ''">
                              {{ record.page_step?.name || '未命名页面步骤' }}
                            </strong>
                          </div>
                          <a-tag :color="enumStore.status_colors[record.status]" size="small">
                            {{ enumStore.task_status[record.status]?.title || '-' }}
                          </a-tag>
                        </div>

                        <div class="ui-case-step-card__path" :title="getCaseStepPath(record)">
                          {{ getCaseStepPath(record) }}
                        </div>

                        <div class="ui-case-step-card__footer" @click.stop>
                          <div class="ui-case-step-card__settings">
                            <span class="ui-case-step-card__setting">
                              切换 URL
                              <UiCaseStepUrlSwitch
                                :case-id="uiCaseId ?? ''"
                                :record-id="record.id"
                                :value="record.switch_step_open_url"
                                @saved="applyCaseStepUrl"
                              />
                            </span>
                            <UiCaseStepRetryEditor
                              :case-id="uiCaseId ?? ''"
                              :record-id="record.id"
                              :retry-count="record.error_retry"
                              @saved="applyCaseStepRetry"
                            />
                          </div>
                          <a-space :size="4">
                            <a-button
                              size="mini"
                              type="text"
                              :loading="!!stepExecutionPending && String(stepExecutionPending.recordId) === String(record.id)"
                              :disabled="caseSubmitting || (stepRunning && String(stepExecutionPending?.recordId) !== String(record.id))"
                              @click="onPageStep(record)" data-testid="qa-views-uitest-case-details-button-单步执行"
                            >
                              单步执行
                            </a-button>
                            <a-button size="mini" type="text" :loading="stepStructurePending?.kind === 'sync' && String(stepStructurePending.recordId) === String(record.id)" :disabled="!!stepStructurePending" @click="syncCaseStep(record.id)" data-testid="qa-views-uitest-case-details-button-同步">
                              同步
                            </a-button>
                            <a-button
                              size="mini"
                              type="text"
                              status="danger"
                              :loading="stepStructurePending?.kind === 'delete' && String(stepStructurePending.recordId) === String(record.id)"
                              :disabled="!!stepStructurePending"
                              @click="deleteCaseStep(record.id)" data-testid="qa-views-uitest-case-details-button-删除"
                            >
                              删除
                            </a-button>
                          </a-space>
                        </div>

                        <a-tooltip v-if="record.error_message" :content="record.error_message">
                          <div class="ui-case-step-card__error">
                            {{ record.error_message }}
                          </div>
                        </a-tooltip>
                      </article>
                    </div>
                    <div v-else class="mango-empty-state">暂无执行步骤，请点击新增</div>
                  </mango-panel-spin>
                </section>
              </a-tab-pane>
              <a-tab-pane key="3" title="后置清理" data-testid="qa-views-uitest-case-details-tab-pane-后置清理">
                <a-tabs
                  class="ui-case-config-tabs"
                  position="left"
                  @tab-click="(key) => switchSonType(key)"
                >
                  <a-tab-pane key="31">
                    <template #title>
                      <span class="case-config-tab-title">
                        数据库操作
                        <span class="case-config-tab-count">{{
                          getCaseConfigCount('posteriorSql')
                        }}</span>
                      </span>
                    </template>
                    <DataSourceOperationList
                      :data-list="caseDraft.posterior_sql"
                      :disabled="caseGlobalSaving || !caseRecord"
                      :datasource-options="datasourceOptions"
                      :datasource-loading="datasourceOptionsLoading"
                      :on-operation-draft-change="caseOperationDraftChanged"
                      :environment-options="sqlEnvironmentOptions"
                      :project-product-id="uiProjectProductId"
                      :test-env="userStore.selected_environment"
                      :show-key="false"
                      operation-field="sql"
                      :on-delete-item="
                        (index) => removeFrontSql(caseDraft.posterior_sql, index)
                      "
                      :on-save="upDataCase"
                    />
                  </a-tab-pane>
                </a-tabs>
              </a-tab-pane>
            </a-tabs>
          </div>
        </section>
        <section class="ui-case-panel ui-case-unified-step-panel">
          <div v-if="caseResultLoading" class="mango-soft-panel" role="status"><a-spin :size="scaleDensityPixels(16)" /> 正在读取执行结果…</div>
          <MangoRequestFeedback v-if="caseResultError" :message="(caseResultError)"><a-button size="small" :loading="caseResultLoading" @click="loadLatestUiCaseExecutionResult()">重试</a-button></MangoRequestFeedback>
          <PageStepsDetails
            v-if="selectedCaseStep && getPageStepId(selectedCaseStep) !== ''"
            :key="`case-${uiCaseId}-step-${selectedCaseStep.id}-page-step-${getPageStepId(selectedCaseStep)}`"
            embedded
            compact
            case-input-mode
            :case-id="uiCaseId ?? ''"
            :case-step-id="selectedCaseStep.id"
            :case-data="selectedCaseStep.case_data || []"
            :case-result="selectedPageStepResult"
            :page-steps-id="getPageStepId(selectedCaseStep)"
            :page-id="getPageId(selectedCaseStep)"
            :refresh-token="caseCanvasRefreshStamp"
            @open-page-step-detail="openPageStepDetail(selectedCaseStep)"
            @open-cache-data="cacheVariablePanel.visible = true"
            @case-data-saved="handleCaseNodeInputsSaved"
          />
          <div v-else class="mango-empty-state">请先在步骤编排中选择一个页面步骤</div>

        </section>
      </div>
      <section v-if="liveStreamVisible" ref="caseLiveSectionRef" class="ui-case-live-area">
        <div class="ui-case-live-toolbar">
          <div>
            <div class="ui-case-live-toolbar__title">Case 实时画面</div>
            <div class="ui-case-live-toolbar__subtitle">
              选择执行器后，点击页面顶部“执行”，Case 与实时画面将使用同一执行器
            </div>
          </div>
          <a-space wrap>
            <span class="ui-case-live-toolbar__label">执行器</span>
            <a-select
              v-model="selectedCaseActuatorUsername"
              size="small"
              placeholder="请选择执行器"
              :loading="caseActuatorLoading"
              :disabled="caseExecutionActive || caseSubmitting"
              class="ui-case-live-toolbar__actuator-select"
              data-testid="qa-views-uitest-case-details-select-请选择执行器"
            >
              <a-option
                v-for="item in caseActuatorOptions"
                :key="item.username"
                :value="item.username"
                :label="`${item.name || item.username}（${item.username} · ${
                  item.activeUsers
                }/${item.maxUsers} 人）`"
                :disabled="item.disabled"
              >
                <div class="ui-case-live-actuator-option">
                  <span>{{ item.name || item.username }}（{{ item.username }}）</span>
                  <a-tag v-if="item.owner" size="small">本人</a-tag>
                  <a-tag v-else color="green" size="small">已开放</a-tag>
                  <a-tag size="small"
                    >{{ item.activeUsers }}/{{ item.maxUsers }} 人</a-tag
                  >
                </div>
              </a-option>
            </a-select>
            <a-button
              size="small"
              :loading="caseActuatorLoading"
              :disabled="caseExecutionActive || caseSubmitting"
              @click="loadCaseActuatorOptions(true)" data-testid="qa-views-uitest-case-details-button-刷新执行器"
            >
              刷新执行器
            </a-button>
          </a-space>
        </div>
        <MangoRequestFeedback v-if="caseLiveError" :message="(caseLiveError)"><a-button size="small" :loading="caseActuatorLoading" @click="loadCaseActuatorOptions()">重试</a-button></MangoRequestFeedback>
        <div v-if="!caseActuatorLoading && !caseLiveError && !caseActuatorOptions.length" class="ui-case-live-notice">
          暂无支持 Web 直播的在线执行器，请启动本人执行器或开放其他执行器。
        </div>
        <UiLiveStreamPanel
          v-if="caseLiveExecutionId"
          v-model:visible="liveStreamVisible"
          execution-type="ui_case"
          :execution-id="caseLiveExecutionId"
          :resource-id="uiCaseId ?? ''"
          :actuator-username="caseLiveActuatorUsername"
          embedded
          @stream-ready="handleCaseLiveReady"
        />
        <div v-else class="ui-case-live-waiting">
          <icon-desktop />
          <strong>等待开始执行</strong>
          <span>选择执行器并点击页面顶部“执行”后，这里将自动展示 Case 执行画面。</span>
        </div>
      </section>
    </template>
  </TableBody>

  <BaseSidePanel
    v-model:visible="pageStepDetailVisible"
    title="页面步骤详情"
    page-description="从界面用例的 Case 步骤中打开，当前展示已存在的页面步骤及其完整操作区域"
    width="calc(92vw - 150px)"
    mode="page"
    @cancel="closePageStepDetail"
  >
    <div class="mango-ui-case-page-step-panel">
      <div v-if="pageStepDetailLoading" class="mango-soft-panel" role="status"><a-spin :size="scaleDensityPixels(16)" /> 正在读取页面步骤…</div>
      
      <PageStepsDetails
        v-if="pageStepDetailVisible && pageStepDetailTarget"
        :key="`${uiCaseId}-${pageStepDetailTarget.pageStepsId}`"
        embedded
        :page-steps-id="pageStepDetailTarget.pageStepsId"
        :page-id="pageStepDetailTarget.pageId"
        :page-type="String(pageStepDetailTarget.pageType)"
        @close="closePageStepDetail"
      />
    </div>
  </BaseSidePanel>

  <ExecutionResultHistoryDrawer
    v-model:visible="resultHistoryVisible"
    title="UI 用例执行历史"
    description="查看多轮执行记录、执行概览及 UI 自动化运行详情"
    width="min(1280px, 80vw)"
    :query="uiCaseResultHistoryQuery"
  >
    <template #result="{ detail }">
      <UiCaseExecutionResult :detail="detail" />
    </template>
  </ExecutionResultHistoryDrawer>

  <BaseSidePanel
    :visible="cacheVariablePanel.visible"
    title="全局缓存变量"
    width="50%"
    @update:visible="
      (val) => {
        cacheVariablePanel.visible = val
      }
    "
    @cancel="cacheVariablePanel.visible = false"
  >
    <div class="mango-ui-case-cache-panel">
      <section class="mango-ui-case-cache-section">
        <div class="mango-ui-case-cache-section__head">
          <strong>当前步骤缓存变量</strong>
          <span>{{ selectedCaseStep?.page_step?.name || selectedCaseStep?.name || '-' }}</span>
        </div>
        <JsonDisplay
          :data="currentStepCacheData"
          :show-drawer-button="false"
          :default-expanded="false"
        />
      </section>
      <section class="mango-ui-case-cache-section">
        <div class="mango-ui-case-cache-section__head">
          <strong>整个 Case 缓存变量</strong>
          <span>最近一次完整执行后的最终缓存快照</span>
        </div>
        <JsonDisplay :data="caseCacheData" :show-drawer-button="false" :default-expanded="false" />
      </section>
      <section class="mango-ui-case-cache-section">
        <div class="mango-ui-case-cache-section__head">
          <strong>数据工厂缓存变量</strong>
          <span>数据工厂生成或注入的上下文</span>
        </div>
        <JsonDisplay
          :data="caseDataFactoryCacheData"
          :show-drawer-button="false"
          :default-expanded="false"
        />
      </section>
    </div>
  </BaseSidePanel>

  <UiCaseStepCreateDialog
    ref="caseStepCreateDialogRef"
    :case-id="uiCaseId ?? ''"
    :case-step-count="caseSteps.length"
    @created="doRefresh"
  />

</template>
<script lang="ts" setup>
  import { scaleDensityPixels } from '@/hooks/useDisplayDensity'
  import { usePagePolling, isPendingExecution, type PollingContext } from '@/hooks/use-page-polling'
  import { computed, nextTick, onMounted, onUnmounted, onDeactivated, reactive, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { IconDesktop } from '@arco-design/web-vue/es/icon'

  import { useRoute } from 'vue-router'
  import { usePageData } from '@/store/page-data'
  import { createUiCaseVariableFields } from './config'
  import { useCaseStepList } from './composables/useCaseStepList'
  import type { CaseStepRow } from './step-list'
  import { formatModulePath } from '@/utils/business-format'
  import { useCaseExecution } from './composables/useCaseExecution'
  import type { CaseExecutionLaunch, CaseExecutionTask } from './case-execution'
  import { useCaseStepExecution } from './composables/useCaseStepExecution'
  import { useCaseStepDetail } from './composables/useCaseStepDetail'
  import { useCaseRuntimeResults } from './composables/useCaseRuntimeResults'
  import { applyCaseRuntimeRows, caseRuntimeCache, caseRuntimeStepEvidence } from './runtime-results'
  import { useCaseLiveStream } from './composables/useCaseLiveStream'
  import useUserStore from '@/store/modules/user'
  import usePermissionStore from '@/store/modules/permission'
  import type { CaseNodeInputContext } from './case-node-inputs'
  import { useEnum } from '@/store/modules/get-enum'
  import KeyValueList from '@/components/forms/KeyValueList.vue'
  import DataSourceOperationList from '@/components/forms/DataSourceOperationList.vue'
  import DataFactoryCaseConfigPanel from '@/components/DataFactory/CaseConfigPanel.vue'
  import UiCaseStepCreateDialog from '@/components/business/UiCaseStepCreateDialog.vue'
  import UiCaseStepRetryEditor from './components/UiCaseStepRetryEditor.vue'
  import UiCaseStepUrlSwitch from './components/UiCaseStepUrlSwitch.vue'
  import { useCaseStepStructure } from './composables/useCaseStepStructure'
  import { useUiCaseConfiguration } from './composables/useUiCaseConfiguration'
  import { useCaseConfigurationOptions } from './composables/useCaseConfigurationOptions'
  import { bootstrapUiCaseContextId, firstUiCaseContextId } from './case-configuration'
  import { uiCaseAssetObject, type UiCaseAssetId } from '@/components/business/ui-case-step-create'
  import type { CaseStepStructureChange } from './step-structure'
  import UiLiveStreamPanel from '@/components/business/UiLiveStreamPanel.vue'
  import VariableReferencePanel from '@/components/business/VariableReferencePanel.vue'
  import ExecutionResultHistoryDrawer from '@/components/business/ExecutionResultHistoryDrawer.vue'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import JsonDisplay from '@/components/display/JsonDisplay.vue'
  import TipMessage from '@/components/feedback/TipMessage.vue'
  import UiCaseExecutionResult from '@/components/reports/UiCaseExecutionResult.vue'
  import PageStepsDetails from '@/views/uitest/page-steps/details/index.vue'
  import type { FactoryConfigSummary } from '@/components/DataFactory/case-config-record'
  import type { UiCaseFrontCustomItem, UiCaseFrontSqlItem, UiCasePosteriorSqlItem } from '@/types/ui-test/case'
  import {
    COMMON_ENV_VALUE,
    normalizeEnvironmentSelectChange,
    normalizeEnvironmentValues,
    toEnvironmentSelectValue,
  } from '@/utils/environment-scope'

  const userStore = useUserStore()
  const enumStore = useEnum()

  const bootstrapCaseId = bootstrapUiCaseContextId(usePageData().record)
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
  const initialRoute = route.fullPath
  const uiCaseId = computed(() => firstUiCaseContextId(
    props.caseId, route.query.id, route.query.case_id, route.fullPath === initialRoute ? bootstrapCaseId : null
  ))
  const {
    record: caseRecord, draft: caseDraft, loading: caseConfigurationLoading,
    loadError: caseConfigurationLoadError, saving: caseGlobalSaving,
    saveError: caseConfigurationSaveError, dirty: caseConfigurationDirty,
    load: loadCaseConfiguration, save: saveCaseConfiguration,
    operationDraftChanged: caseOperationDraftChanged,
  } = useUiCaseConfiguration(() => uiCaseId.value)
  const uiProjectProductId = computed(
    () => firstUiCaseContextId(props.projectProductId, route.query.project_product, caseRecord.value?.project_product?.id)
  )
  const { publicVariables, authorizations, datasources } = useCaseConfigurationOptions(() => uiProjectProductId.value)
  const publicOptionsLoading = publicVariables.loading, authOptionsLoading = authorizations.loading
  const datasourceOptions = datasources.rows, datasourceOptionsLoading = datasources.loading
  const publicOptions = computed(() => publicVariables.rows.value.map(item => ({ ...item, typeText: getEnumTitle(enumStore.api_public_type, item.type) })))
  const authConfigOptions = computed(() => authorizations.rows.value.map(item => ({ ...item, authTypeText: getEnumTitle(enumStore.ui_auth_type, item.authType), envText: formatEnvironmentText(item.testEnv) })))
  const configurationOptionErrors = computed(() => [
    { label: '全局变量', resource: publicVariables },
    { label: '授权配置', resource: authorizations },
    { label: '逻辑数据源', resource: datasources },
  ].filter(item => item.resource.error.value).map(item => ({ label: item.label, message: item.resource.error.value, loading: item.resource.loading.value, retry: () => item.resource.load() })))

  const sqlEnvironmentOptions = computed(() =>
    (enumStore.environment_type || []).map((item: { title: string; key: number | string }) => ({
      label: item.title,
      value: item.key,
    }))
  )
  const caseVariableEnvironmentOptions = computed(() => [
    { key: COMMON_ENV_VALUE, title: '环境通用' },
    ...enumStore.environment_type,
  ])
  const caseVariableFields = computed(() => createUiCaseVariableFields(
    caseVariableEnvironmentOptions.value, getVariableEnvironmentValue, setVariableEnvironmentValue
  ))

  const dataFactoryPanelRef = ref<InstanceType<typeof DataFactoryCaseConfigPanel> | null>(null)

  const caseStepCreateDialogRef = ref<InstanceType<typeof UiCaseStepCreateDialog> | null>(null)

  const resultHistoryVisible = ref(false)
  const uiCaseResultHistoryQuery = computed(() => ({
    source_type: 'page',
    target_type: 'ui_case',
    target_id: uiCaseId.value,
  }))
  // 同步成功后递增，驱动右侧嵌入画布重新拉取最新步骤数据
  const caseCanvasRefreshStamp = ref(0)
  const cacheVariablePanel = reactive({
    visible: false,
  })
  const permissionStore = usePermissionStore()
  function closeCaseAuxiliaryPanels() {
    cacheVariablePanel.visible = false
    resultHistoryVisible.value = false
  }
  watch(() => JSON.stringify([uiCaseId.value, route.fullPath, userStore.userId, userStore.roleId, userStore.token, userStore.selected_environment, permissionStore.permissionKeys]), closeCaseAuxiliaryPanels, { flush: 'sync' })
  const pauseCaseAuxiliaryPanels = () => { if (document.visibilityState !== 'visible') closeCaseAuxiliaryPanels() }
  onMounted(() => document.addEventListener('visibilitychange', pauseCaseAuxiliaryPanels))
  onDeactivated(closeCaseAuxiliaryPanels)
  onUnmounted(() => document.removeEventListener('visibilitychange', pauseCaseAuxiliaryPanels))
  const caseTab = ref('2')
  const caseConfigTab = ref('11')

  const { running: stepRunning, pending: stepExecutionPending, error: stepExecutionError, run: runCaseStep, retry: retryStepExecution } = useCaseStepExecution({
    caseId: () => uiCaseId.value, rows: () => caseSteps.value, busy: () => caseSubmitting.value,
    refresh: async current => {
      if (!current()) return
      const [loaded] = await Promise.all([loadCaseSteps(true, current), loadCaseConfiguration(false, current)])
      if (current() && !loaded) throw Error('Step refresh failed')
    },
  })
  const caseLiveSectionRef = ref<HTMLElement | null>(null)
  const {
    submitting: caseSubmitting, recovering: caseExecutionRecovering, active: caseExecutionActive,
    executionId: caseExecutionId, error: caseExecutionError, start: startCaseExecution, recover: recoverCaseExecution,
  } = useCaseExecution({
    caseId: () => uiCaseId.value, name: () => caseRecord.value?.name ?? '', busy: () => stepRunning.value,
    started: handleCaseExecutionStarted, finished: handleCaseExecutionFinished,
  })
  const caseLive = useCaseLiveStream({
    caseId: () => uiCaseId.value, busy: () => caseSubmitting.value, executionActive: () => caseExecutionActive.value,
    shown: async current => { await nextTick(); if (current()) caseLiveSectionRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' }) },
  })
  const {
    visible: liveStreamVisible, opening: caseLiveOpening, executionId: caseLiveExecutionId,
    actuator: caseLiveActuatorUsername, choices: caseActuatorOptions, loading: caseActuatorLoading,
    selected: selectedCaseActuatorUsername, error: caseLiveError, load: loadCaseActuatorOptions,
    toggle: toggleCaseLiveStream, ready: handleCaseLiveReady,
  } = caseLive
  const caseRunning = computed(() => caseSubmitting.value || stepRunning.value)
  const {
    rows: caseSteps, selected: selectedCaseStep, select: selectCaseStep, replace: replaceCaseSteps,
    loading: stepTableLoading, error: stepListError, load: loadCaseSteps,
    invalidate: invalidateCaseSteps, capture: captureCaseSteps,
  } = useCaseStepList({ caseId: () => uiCaseId.value, running: () => caseExecutionActive.value, loaded: handleCaseStepsLoaded })
  const { visible: pageStepDetailVisible, target: pageStepDetailTarget, loading: pageStepDetailLoading, error: pageStepDetailError, open: showPageStepDetail, close: closePageStepDetail, retry: retryPageStepDetail } = useCaseStepDetail({ caseId: () => uiCaseId.value, rows: () => caseSteps.value })
  const {
    result: latestUiCaseResult, pending: latestUiCaseResultPending,
    loading: caseResultLoading, error: caseResultError, load: loadLatestUiCaseExecutionResult,
    reset: resetCaseResults, requireLatest: requireLatestCaseResult, acceptFinal: applyCaseFinalResult,
  } = useCaseRuntimeResults({
    caseId: () => uiCaseId.value, executionId: () => caseExecutionId.value,
    stepIds: () => caseSteps.value.map(row => row.id),
    updated: (result, final) => replaceCaseSteps(applyCaseRuntimeRows(caseSteps.value, result, final)),
    refresh: () => doRefresh(false),
    finished: executionId => caseLive.finish(executionId),
  })
  const caseFactorySummary = ref<FactoryConfigSummary>({ count: null, loading: true, error: '' })

  const uiCaseDetailTitle = computed(() => {
    const id = uiCaseId.value ?? '-'
    const name = caseRecord.value?.name || '-'
    return `界面用例配置 / ${id} / ${name}`
  })
  const frontPublicCheckedValues = computed({
    get: () => mergeCheckedOptionValues(caseDraft.front_public, publicOptions.value),
    set: (value: UiCaseAssetId[]) => {
      caseDraft.front_public = filterOptionalOptionValues(value, publicOptions.value)
    },
  })
  const frontAuthConfigCheckedValues = computed({
    get: () => mergeCheckedOptionValues(caseDraft.front_auth_config, authConfigOptions.value),
    set: (value: UiCaseAssetId[]) => {
      caseDraft.front_auth_config = filterOptionalOptionValues(value, authConfigOptions.value)
    },
  })
  const pagePolling = usePagePolling(context => doRefresh(false, context), () => invalidateCaseSteps())
  const {
    pending: stepStructurePending, error: stepStructureError, draggingId: draggingStepId,
    beginDrag: beginStepDrag, cancelDrag: cancelStepDrag, drop: dropCaseStep,
    remove: deleteCaseStep, sync: syncCaseStep,
  } = useCaseStepStructure({
    caseId: () => uiCaseId.value,
    stepIds: () => caseSteps.value.map((record) => record.id),
    committed: applyStepStructureChange,
  })
  const showCaseAddButton = computed(() => {
    if (caseTab.value === '2') return true
    if (caseTab.value === '1') return ['11', '12', '14'].includes(caseConfigTab.value)
    return caseTab.value === '3' && caseConfigTab.value === '31'
  })
  const selectedCaseRuntimeStep = computed(() => latestUiCaseResult.value?.steps.find(
    step => selectedCaseStep.value !== null && String(step.detailId) === String(selectedCaseStep.value.id)
  ) ?? null)
  const selectedPageStepResult = computed(() => caseRuntimeStepEvidence(selectedCaseRuntimeStep.value))
  const currentStepCacheData = computed(() => selectedCaseRuntimeStep.value?.cache ?? {})
  const caseCacheData = computed(() => caseRuntimeCache(latestUiCaseResult.value))
  const caseDataFactoryCacheData = computed(() => caseRuntimeCache(latestUiCaseResult.value, true))

  function clearPollingTimer() { pagePolling.stop() }

  function switchType(key: string | number) {
    if (key === '1') {
      caseConfigTab.value = '15'
    } else if (key === '3') {
      caseConfigTab.value = '31'
    }
    caseTab.value = String(key)
  }

  function switchSonType(key: string | number) {
    caseConfigTab.value = String(key)
  }

  function configuredItemCount(value: unknown) {
    if (!Array.isArray(value)) return value ? 1 : 0
    return value.length
  }

  function handleCaseFactorySummary(summary: FactoryConfigSummary) { caseFactorySummary.value = { ...summary } }

  function getCaseConfigCount(
    type: 'public' | 'auth' | 'custom' | 'frontSql' | 'factory' | 'posteriorSql'
  ) {
    if (type === 'public') return configuredItemCount(frontPublicCheckedValues.value)
    if (type === 'auth') return configuredItemCount(frontAuthConfigCheckedValues.value)
    if (type === 'custom') return configuredItemCount(caseDraft.front_custom)
    if (type === 'frontSql') return configuredItemCount(caseDraft.front_sql)
    if (type === 'factory') return caseFactorySummary.value.count ?? '—'
    return configuredItemCount(caseDraft.posterior_sql)
  }

  function addData() {
    if (caseTab.value == '2') {
      caseStepCreateDialogRef.value?.open()
      return
    }
    if (caseGlobalSaving.value || !caseRecord.value) return
    if (caseConfigTab.value === '11') {
      caseDraft.front_custom.push({ key: '', value: '', test_envs: [] })
    } else if (caseConfigTab.value === '12') {
      caseDraft.front_sql.push({
        sql: '',
        key_list: '',
        datasource_alias: null,
        test_envs: [],
      })
    } else if (caseConfigTab.value === '14') {
      dataFactoryPanelRef.value?.open()
    } else if (caseConfigTab.value === '31') {
      caseDraft.posterior_sql.push({ sql: '', datasource_alias: null, test_envs: [] })
    }
  }

  function removeFrontSql(item: Array<UiCaseFrontCustomItem | UiCaseFrontSqlItem | UiCasePosteriorSqlItem>, index: number) {
    if (caseGlobalSaving.value || !Number.isInteger(index) || index < 0 || index >= item.length) return
    const [removed] = item.splice(index, 1)
    caseOperationDraftChanged(removed, false)
    return upDataCase()
  }

  function getVariableEnvironmentValue(item: unknown) {
    return toEnvironmentSelectValue(uiCaseAssetObject(item).test_envs)
  }

  function setVariableEnvironmentValue(value: unknown, item: unknown) {
    uiCaseAssetObject(item).test_envs = normalizeEnvironmentValues(normalizeEnvironmentSelectChange(value))
  }

  async function upDataCase() {
    return saveCaseConfiguration('all')
  }

  async function changeCaseGlobalOptions() {
    if (caseGlobalSaving.value) return
    const frontPublic = filterOptionalOptionValues(caseDraft.front_public, publicOptions.value)
    const frontAuthConfig = filterOptionalOptionValues(
      caseDraft.front_auth_config,
      authConfigOptions.value
    )
    caseDraft.front_public = frontPublic
    caseDraft.front_auth_config = frontAuthConfig
    return saveCaseConfiguration('globals')
  }

  function filterOptionalOptionValues(values: UiCaseAssetId[], options: Array<{ value: UiCaseAssetId; disabled: boolean }>) {
    const disabledValues = new Set(
      options.filter((item) => item.disabled).map((item) => String(item.value))
    )
    return values.filter((item) => !disabledValues.has(String(item)))
  }

  function mergeCheckedOptionValues(values: UiCaseAssetId[], options: Array<{ value: UiCaseAssetId; disabled: boolean }>) {
    const result = new Map(values.map(value => [String(value), value]))
    options.forEach((item) => {
      if (item.disabled) result.set(String(item.value), item.value)
    })
    return [...result.values()]
  }

  function getEnumTitle(options: unknown, value: unknown, fallback = '-') {
    if (value === null || value === undefined || value === '') return fallback
    if (!Array.isArray(options)) return fallback
    const item = options.find(item => item && typeof item === 'object' && !Array.isArray(item) && String(uiCaseAssetObject(item).key) === String(value))
    const title = item ? uiCaseAssetObject(item).title : null
    return typeof title === 'string' ? title : fallback
  }

  function formatEnvironmentText(value: unknown) {
    if (value === null || value === undefined || value === '') return '环境通用'
    return getEnumTitle(enumStore.environment_type, value, `环境${value}`)
  }

  function onCaseStepDragStart(event: DragEvent, id: number | string) {
    if (!beginStepDrag(id)) { event.preventDefault(); return }
    if (event.dataTransfer) {
      event.dataTransfer.effectAllowed = 'move'
      event.dataTransfer.setData('text/plain', String(id))
    }
  }

  function applyStepStructureChange(change: CaseStepStructureChange) {
    if (String(uiCaseId.value) !== String(change.caseId)) return
    invalidateCaseSteps()
    if (change.kind === 'sort') {
      const rows = new Map<string, CaseStepRow>(
        caseSteps.value.map((record) => [String(record.id), record])
      )
      const order = new Set(change.order.map(String))
      replaceCaseSteps([
        ...change.order.flatMap(id => { const row = rows.get(String(id)); return row ? [row] : [] }),
        ...caseSteps.value.filter((record) => !order.has(String(record.id))),
      ])
      return
    }
    if (change.kind === 'delete') {
      replaceCaseSteps(caseSteps.value.filter((record) => String(record.id) !== String(change.recordId)))
    } else caseCanvasRefreshStamp.value++
    void doRefresh(false)
  }

  function getCaseStepPath(record: CaseStepRow) {
    const pageStep = record.page_step
    const projectProduct = pageStep?.project_product
    const values = [
      projectProduct?.project?.name,
      projectProduct?.name,
      pageStep?.module ? formatModulePath(pageStep.module) : null,
      pageStep?.page?.name,
    ].filter((item) => item !== null && item !== undefined && item !== '')
    return values.length ? values.join(' / ') : '暂无页面层级信息'
  }

  function applyCaseStepRetry(value: { caseId: number | string; recordId: number | string; retryCount: number }) {
    if (String(uiCaseId.value) !== String(value.caseId)) return
    replaceCaseSteps(caseSteps.value.map((record) =>
      String(record.id) === String(value.recordId) ? { ...record, error_retry: value.retryCount } : record
    ))
  }

  function applyCaseStepUrl(value: { caseId: number | string; recordId: number | string; value: 0 | 1 }) {
    if (String(uiCaseId.value) !== String(value.caseId)) return
    replaceCaseSteps(caseSteps.value.map((record) =>
      String(record.id) === String(value.recordId) ? { ...record, switch_step_open_url: value.value } : record
    ))
  }

  function doResetSearch() {
    if (props.embedded) {
      emit('close')
      return
    }
    window.history.back()
  }

  async function ensureCaseRecord() {
    return loadCaseConfiguration(true)
  }

  function handleCaseStepsLoaded(current: () => boolean) {
    const hasRunningItem = caseSteps.value.some(isPendingExecution)
    if (hasRunningItem || latestUiCaseResultPending.value) pagePolling.start()
    else pagePolling.stop()
    if (!hasRunningItem && latestUiCaseResultPending.value) {
      void loadLatestUiCaseExecutionResult(true, false).then(loaded => {
        if (current() && loaded && !caseSteps.value.some(isPendingExecution)) pagePolling.stop()
      })
    }
  }

  async function doRefresh(showLoading = true, context?: PollingContext) {
    if (uiCaseId.value === null) return
    await Promise.all([refreshCaseRecord(context), loadCaseSteps(showLoading, context?.isCurrent)])
  }

  function resetCaseRuntimeState(executionId: string) {
    resetCaseResults(executionId)
    const pending = caseSteps.value.map(item => ({ ...item, status: 2, error_message: null }))
    const result = latestUiCaseResult.value
    replaceCaseSteps(result?.executionId === executionId ? applyCaseRuntimeRows(pending, result, false) : pending)
  }

  function refreshCaseRecord(context?: PollingContext) {
    return loadCaseConfiguration(false, context?.isCurrent)
  }

  function handleCaseExecutionStarted(launch: CaseExecutionLaunch & { executionId: string }) {
    resetCaseRuntimeState(launch.executionId)
    caseLive.started(launch)
  }

  async function handleCaseExecutionFinished(task: CaseExecutionTask, current: () => boolean) {
    if (!current()) return
    if (task.result) applyCaseFinalResult(task.result)
    requireLatestCaseResult()
    await doRefresh(false)
    if (current()) caseLive.finish(caseExecutionId.value)
  }

  async function onCaseRun(withLive = false) {
    if (userStore.selected_environment == null) { Message.error('请先选择用例执行的环境'); return }
    const useLive = withLive || liveStreamVisible.value
    return startCaseExecution(current => caseLive.prepare(useLive, current))
  }

  function select(record: CaseStepRow) {
    selectCaseStep(record.id)
  }

  function handleCaseNodeInputsSaved(caseData: unknown[], context: CaseNodeInputContext) {
    if (String(context.caseId) !== String(uiCaseId.value)) return
    replaceCaseSteps(caseSteps.value.map(item =>
      String(item.id) === String(context.caseStepId) && String(item.page_step?.id) === String(context.pageStepId) ? { ...item, case_data: caseData } : item
    ))
  }

  function onPageStep(record: CaseStepRow) { return runCaseStep(record.id) }

  function getPageStepId(record: CaseStepRow | null) {
    return record?.page_step?.id ?? ''
  }

  function getPageId(record: CaseStepRow | null) {
    return record?.page_step?.page?.id ?? ''
  }

  function openPageStepDetail(record: CaseStepRow | null) { if (record) return showPageStepDetail(record.id) }

  onMounted(() => {
    nextTick(async () => {
      await ensureCaseRecord()
      void doRefresh()
    })
  })
  onUnmounted(() => {
    clearPollingTimer()
  })
</script>

<style scoped>
  .mango-ui-step-structure-error { color: var(--m-danger); }
  .ui-case-live-toolbar__actuator-select {
    width: 260px;
  }

  .ui-case-workbench {
    display: grid !important;
    grid-template-columns: 500px minmax(1032px, 1fr);
    align-items: stretch;
    min-height: 0;
    gap: var(--steps-panel-gap, var(--m-page-gap));
  }

  .ui-case-step-assets-panel {
    flex: 1.5 1 0;
  }

  .ui-case-panel {
    display: flex;
    overflow: hidden;
    flex: 1 1 0;
    flex-direction: column;
    min-width: 0;
    min-height: 0;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
  }

  .ui-case-workbench > .ui-case-panel:first-child {
    width: 500px;
  }

  .ui-case-unified-step-panel {
    min-width: 1032px;
    border: 0;
    background: transparent;
  }

  .ui-case-unified-step-panel :deep(.page-steps-workbench-page),
  .ui-case-unified-step-panel :deep(.arco-layout-content),
  .ui-case-unified-step-panel :deep(.steps-workbench) {
    height: 100%;
    min-height: 0;
  }

  .ui-case-panel,
  .ui-case-unified-step-panel :deep(.center-panel),
  .ui-case-unified-step-panel :deep(.inspector-panel) {
    height: 100%;
    margin-top: 0;
  }

  .ui-case-panel-head,
  .ui-case-unified-step-panel :deep(.flow-panel-head),
  .ui-case-unified-step-panel :deep(.panel-head) {
    box-sizing: border-box;
    height: 64px;
    min-height: 64px;
    margin: 0;
    padding: 10px 12px;
    align-items: center;
  }

  .ui-case-step-assets-panel + .ui-case-panel {
    flex: 3.7 1 0;
  }

  .ui-case-step-assets-panel + .ui-case-panel + .ui-case-panel {
    flex: 4.8 1 0;
  }

  .ui-case-panel-head {
    display: flex;
    box-sizing: border-box;
    flex: none;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    height: 64px;
    min-height: 64px;
    margin: 0;
    padding: 10px 12px;
    border-bottom: 1px solid var(--m-border);
    background: var(--m-surface);
  }

  .ui-case-panel-head--steps {
    align-items: flex-start;
  }

  .step-result-head-main {
    display: flex;
    flex: 1;
    flex-direction: column;
    min-width: 0;
    gap: 8px;
  }

  .step-result-side {
    display: flex;
    flex: 0 0 auto;
    flex-direction: column;
    align-items: flex-end;
    min-width: 0;
    gap: 6px;
  }

  .step-result-actions {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 6px;
  }

  .ui-case-panel-title {
    color: var(--m-text);
    font-size: 15px;
    font-weight: 600;
    line-height: 22px;
  }

  .ui-case-panel-subtitle {
    display: -webkit-box;
    overflow: hidden;
    margin-top: 2px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 1;
  }

  .ui-case-panel-body {
    flex: 1;
    min-height: 0;
    overflow: hidden;
    padding: 12px;
  }

  .ui-case-step-assets-body {
    display: flex;
    flex-direction: column;
    padding: 0;
  }

  .ui-case-step-assets__filters {
    display: flex;
    flex: none;
    flex-direction: column;
    gap: 8px;
    padding: 10px;
    border-bottom: 1px solid var(--m-border);
    background: var(--m-surface-soft);
  }

  .ui-case-step-assets__list {
    display: flex;
    flex: 1;
    flex-direction: column;
    min-height: 0;
    gap: 8px;
    padding: 10px;
    overflow: auto;
  }

  .ui-case-step-assets-body :deep(.arco-spin),
  .ui-case-step-assets-body :deep(> .mango-panel-spin__content) {
    display: flex;
    flex: 1;
    min-height: 0;
    flex-direction: column;
  }

  .ui-case-step-asset-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    min-width: 0;
    padding: 8px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-lg);
    background: var(--m-surface);
    cursor: grab;
    transition: border-color 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease;
  }

  .ui-case-step-asset-item:hover {
    border-color: var(--m-primary);
    box-shadow: var(--m-shadow);
    transform: translateY(-1px);
  }

  .ui-case-step-asset-item:active {
    cursor: grabbing;
  }

  .ui-case-step-asset-item__main {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 2px;
  }

  .ui-case-step-asset-item__main strong,
  .ui-case-step-asset-item__main span {
    overflow: hidden;
    min-width: 0;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .ui-case-step-asset-item__main strong {
    color: var(--m-text);
    font-size: 13px;
    line-height: 20px;
  }

  .ui-case-step-asset-item__main span {
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .ui-case-step-table-drop {
    position: relative;
    min-width: 0;
    height: 100%;
    min-height: 420px;
    overflow: hidden;
    border-radius: var(--m-radius-md);
    transition: background-color 0.18s ease;
  }

  .ui-case-step-card-spin,
  .ui-case-step-card-spin :deep(> .mango-panel-spin__content) {
    display: flex;
    width: 100%;
    height: 100%;
    min-height: 0;
    flex-direction: column;
  }

  .ui-case-step-card-list {
    display: flex;
    min-height: 0;
    padding: 2px;
    flex: 1;
    flex-direction: column;
    gap: var(--m-page-gap);
    overflow-y: auto;
  }

  .ui-case-step-card {
    display: flex;
    flex: none;
    min-width: 0;
    padding: 10px 12px;
    flex-direction: column;
    gap: 8px;
    border: 1px solid var(--m-border);
    border-left: 3px solid var(--m-border-strong);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
    cursor: pointer;
    transition: border-color 0.18s ease, background-color 0.18s ease, box-shadow 0.18s ease;
  }

  .ui-case-step-card:hover {
    border-color: color-mix(in srgb, var(--m-primary) 46%, var(--m-border));
    box-shadow: var(--m-shadow);
  }

  .ui-case-step-card--selected {
    border-color: var(--m-primary);
    border-left-color: var(--m-primary);
    background: color-mix(in srgb, var(--m-primary) 5%, var(--m-surface));
    box-shadow: 0 0 0 2px color-mix(in srgb, var(--m-primary) 10%, transparent);
  }

  .ui-case-step-card--dragging {
    opacity: 0.55;
  }

  .ui-case-step-card__head,
  .ui-case-step-card__footer,
  .ui-case-step-card__identity,
  .ui-case-step-card__settings,
  .ui-case-step-card__setting {
    display: flex;
    align-items: center;
  }

  .ui-case-step-card__head,
  .ui-case-step-card__footer {
    justify-content: space-between;
    gap: 10px;
  }

  .ui-case-step-card__identity {
    min-width: 0;
    flex: 1;
    gap: 8px;
  }

  .ui-case-step-card__identity strong {
    overflow: hidden;
    min-width: 0;
    color: var(--m-text);
    font-size: 13px;
    line-height: 20px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .ui-case-step-card__handle {
    flex: none;
    color: var(--m-muted);
    cursor: grab;
    font-weight: 700;
    letter-spacing: -2px;
  }

  .ui-case-step-card__handle:active {
    cursor: grabbing;
  }

  .ui-case-step-card__index {
    flex: none;
    min-width: 26px;
    color: var(--m-primary);
    font-size: 12px;
    font-weight: 600;
    text-align: center;
  }

  .ui-case-step-card__path {
    overflow: hidden;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .ui-case-step-card__settings {
    flex-wrap: wrap;
    gap: 12px;
  }

  .ui-case-step-card__setting {
    gap: 6px;
    color: var(--m-text-2);
    font-size: 12px;
    white-space: nowrap;
  }

  .ui-case-step-card__error {
    overflow: hidden;
    padding: 5px 8px;
    border-radius: var(--m-radius-sm);
    background: color-mix(in srgb, var(--m-danger) 7%, var(--m-surface));
    color: var(--m-danger);
    font-size: 12px;
    line-height: 18px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .ui-case-step-table-drop--active {
    background: var(--m-surface-soft);
  }

  .ui-case-step-compose-body {
    display: flex;
    flex-direction: column;
  }

  .ui-case-step-tabs {
    display: flex;
    flex: 1;
    min-height: 0;
    flex-direction: column;
  }

  .ui-case-step-tabs :deep(.arco-tabs-content) {
    flex: 1;
    min-height: 0;
  }

  .ui-case-step-tabs :deep(.arco-tabs-content-list),
  .ui-case-step-tabs :deep(.arco-tabs-pane) {
    height: 100%;
    min-height: 0;
  }

  .ui-case-step-tabs
    :deep(.ui-case-config-tabs > .arco-tabs-nav.arco-tabs-nav-vertical .arco-tabs-tab) {
    padding-right: 5px;
    padding-left: 5px;
  }

  .case-config-tab-title {
    display: inline-flex;
    min-width: 0;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .case-config-tab-count {
    display: inline-flex;
    min-width: 20px;
    height: 18px;
    padding: 0 5px;
    align-items: center;
    justify-content: center;
    border-radius: 9px;
    background: var(--m-fill-1);
    color: var(--m-text-2);
    font-size: 11px;
    font-variant-numeric: tabular-nums;
    line-height: 18px;
  }

  :deep(.arco-tabs-tab-active) .case-config-tab-count {
    background: var(--m-primary-soft);
    color: var(--m-primary);
  }

  .step-result-workbench {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
    gap: var(--m-page-gap);
  }

  .step-result-subtitle {
    margin-top: 2px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .step-result-hint {
    margin-top: 2px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .step-result-metrics {
    display: flex;
    flex: 0 0 auto;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 6px;
  }

  .step-execution-collapse {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    overflow-x: hidden;
    padding-right: 4px;
  }

  .step-execution-collapse :deep(.arco-collapse-item) {
    margin-bottom: var(--m-page-gap);
    overflow: hidden;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-lg);
    background-color: var(--m-surface);
  }

  .step-execution-collapse :deep(.arco-collapse-item-header) {
    align-items: flex-start;
    padding: 10px 12px;
    background-color: var(--m-surface);
  }

  .step-execution-collapse :deep(.arco-collapse-item-header-left) {
    box-sizing: border-box;
    display: block;
    flex: 1 1 auto;
    min-width: 0;
    padding-right: 0;
    padding-left: 34px;
  }

  .step-execution-collapse :deep(.arco-collapse-item-icon-hover) {
    top: 14px;
    left: 12px;
    transform: none;
  }

  .step-execution-collapse :deep(.arco-collapse-item-header-title) {
    display: block;
    flex: 1 1 auto;
    min-width: 0;
    width: 100%;
  }

  .step-execution-collapse :deep(.arco-collapse-item-content-box) {
    padding: 0 12px 12px;
  }

  .step-execution-collapse :deep(.arco-collapse-item-active .arco-collapse-item-header) {
    border-bottom: 1px solid var(--m-border);
  }

  .case-error-text {
    display: block;
    overflow: hidden;
    max-width: 100%;
    color: var(--m-danger);
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .case-error-empty {
    color: var(--m-muted);
  }

  .step-header {
    color: var(--m-text);
    font-size: 16px;
    font-weight: 600;
  }

  .step-collapse-header {
    min-width: 0;
    width: 100%;
  }

  .step-collapse-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 4px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .step-collapse-meta span {
    overflow: hidden;
    max-width: min(100%, 360px);
    padding: 1px 0;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .step-list-item {
    transition: all 0.2s ease;
  }

  .step-list-item:hover {
    border-color: var(--m-border-strong);
    background-color: var(--m-surface-soft);
    box-shadow: var(--m-shadow);
  }

  .step-container {
    width: 100%;
  }

  .step-card-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    min-width: 0;
    gap: 12px;
  }

  .step-card-title {
    display: flex;
    flex: 1 1 220px;
    align-items: center;
    min-width: 0;
    gap: 8px;
  }

  .step-main-name {
    overflow: hidden;
    color: var(--m-text);
    font-size: 15px;
    font-weight: 600;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .step-card-tags {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 64px;
    flex: 1 1 240px;
    align-items: center;
    min-width: 0;
    max-width: 100%;
    gap: 10px;
    padding-right: 8px;
  }

  .step-card-tag-list {
    display: grid;
    grid-template-columns: max-content max-content max-content;
    align-items: center;
    justify-content: start;
    min-width: 0;
    gap: 6px;
    padding-left: 72px;
  }

  .step-card-tag-list :deep(.arco-tag),
  .step-type-card,
  .step-card-element-action {
    flex: 0 0 auto;
  }

  .step-card-tag-list :deep(.arco-tag) {
    justify-content: center;
  }

  .step-card-tag-placeholder {
    display: inline-block;
    width: 1px;
    min-height: 24px;
  }

  .step-card-element-action {
    justify-self: end;
    width: 64px;
  }

  .step-card-element-action--placeholder {
    display: inline-block;
    height: 24px;
  }

  .step-type-card {
    display: inline-flex;
    align-items: center;
    max-width: 100%;
    min-width: 0;
    gap: 8px;
    padding: 3px 8px;
    color: var(--m-text-2);
    font-size: 12px;
    line-height: 18px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
  }

  .step-type-card--meta {
    padding: 0;
    border: 0;
    background: transparent;
  }

  .step-type-dot {
    flex: 0 0 auto;
    width: 8px;
    height: 8px;
    border-radius: 50%;
  }

  .step-meta-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(128px, 1fr));
    gap: 6px;
    padding: 8px;
    background-color: var(--m-surface);
    border-radius: var(--m-radius-md);
  }

  .step-meta-item {
    display: flex;
    align-items: center;
    min-width: 0;
    gap: 6px;
    padding: 6px 8px;
    background-color: var(--m-surface-soft);
    border-radius: var(--m-radius-md);
  }

  .step-meta-label {
    flex: 0 0 auto;
    color: var(--m-muted);
    font-size: 12px;
  }

  .step-meta-value {
    overflow: hidden;
    min-width: 0;
    color: var(--m-text);
    font-size: 12px;
    font-weight: 500;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .step-meta-value--type {
    display: inline-flex;
  }

  .step-runtime-panel {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-bottom: 8px;
    padding: 8px;
    max-height: min(520px, 58vh);
    overflow: auto;
    background-color: var(--m-surface-soft);
    border-radius: var(--m-radius-md);
  }

  .step-runtime-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    color: var(--m-text);
    font-size: 13px;
    font-weight: 600;
  }

  .step-runtime-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(128px, 1fr));
    gap: 6px;
  }

  .step-runtime-grid > div {
    display: flex;
    align-items: center;
    min-width: 0;
    gap: 6px;
    padding: 6px 8px;
    background-color: var(--m-surface);
    border-radius: 4px;
  }

  .step-runtime-grid span,
  .step-element-result-row span,
  .step-runtime-shot-head span,
  .step-locator-sub {
    flex: 0 0 auto;
    color: var(--m-muted);
    font-size: 12px;
  }

  .step-runtime-grid strong,
  .step-element-result-row strong {
    overflow: hidden;
    min-width: 0;
    color: var(--m-text);
    font-size: 12px;
    font-weight: 500;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .step-runtime-grid .step-runtime-wide {
    grid-column: 1 / -1;
  }

  .step-runtime-error {
    color: var(--m-danger) !important;
  }

  .step-element-result-list {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 8px;
  }

  .step-element-result-card {
    min-width: 0;
    padding: 8px;
    background-color: var(--m-surface);
    border-radius: var(--m-radius-md);
  }

  .step-element-result-head,
  .step-element-result-row {
    display: flex;
    align-items: center;
    min-width: 0;
    gap: 6px;
  }

  .step-element-result-head {
    justify-content: space-between;
    margin-bottom: 6px;
  }

  .step-element-result-head strong {
    overflow: hidden;
    min-width: 0;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .step-element-result-row + .step-element-result-row {
    margin-top: 4px;
  }

  .step-element-result-row--locators {
    align-items: flex-start;
  }

  .step-locator-list {
    display: flex;
    flex: 1 1 auto;
    flex-direction: column;
    min-width: 0;
    gap: 4px;
  }

  .step-locator-item {
    display: flex;
    align-items: center;
    min-width: 0;
    gap: 6px;
    padding: 4px 6px;
    background-color: var(--m-surface-soft);
    border-radius: 4px;
  }

  .step-locator-item strong {
    overflow: hidden;
    min-width: 0;
    color: var(--m-text);
    font-size: 12px;
    font-weight: 500;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .step-runtime-shot {
    display: flex;
    align-items: flex-start;
    flex-direction: column;
    gap: 8px;
    padding: 8px;
    background-color: var(--m-surface);
    border-radius: var(--m-radius-md);
  }

  .step-runtime-shot-head {
    display: flex;
    align-items: center;
    min-width: 0;
    gap: 6px;
  }

  .step-runtime-shot-head strong {
    overflow: hidden;
    min-width: 0;
    color: var(--m-text);
    font-size: 12px;
    font-weight: 500;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  /* 步骤详情区域 */
  .step-details {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-bottom: 8px;
    padding: 8px;
    background-color: var(--m-surface-soft);
    border-radius: var(--m-radius-md);
  }

  .step-section-title {
    color: var(--m-text);
    font-size: 13px;
    font-weight: 600;
    line-height: 20px;
  }

  /* 输入框样式 */
  .input-label {
    display: block;
    min-width: 0;
    font-weight: 500;
    color: var(--m-muted);
    line-height: 32px;
    text-align: right;
  }

  .custom-textarea {
    width: 100%;
    min-width: 0;
  }

  /* 条件判断输入 */
  .condition-input {
    display: grid;
    grid-template-columns: 112px minmax(0, 1fr);
    align-items: flex-start;
    gap: 8px;
    padding: 8px;
    border: 1px solid color-mix(in srgb, var(--m-warning) 28%, var(--m-border));
    background-color: var(--m-surface);
    border-radius: var(--m-radius-md);
  }

  /* 操作输入 */
  .operation-input {
    display: grid;
    grid-template-columns: 112px minmax(0, 1fr);
    align-items: flex-start;
    gap: 8px;
    padding: 8px;
    background-color: var(--m-surface);
    border-radius: var(--m-radius-md);
  }

  /* 断言输入 */
  .assertion-input {
    display: grid;
    grid-template-columns: 112px minmax(0, 1fr);
    align-items: flex-start;
    gap: 8px;
    padding: 8px;
    background-color: var(--m-surface);
    border-radius: var(--m-radius-md);
  }

  /* 自定义参数输入 */
  .custom-param-input {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 8px;
    background-color: var(--m-surface);
    border-radius: var(--m-radius-md);
  }

  .param-row {
    display: grid;
    grid-template-columns: 112px minmax(0, 1fr);
    align-items: flex-start;
    gap: 8px;
  }

  /* SQL输入 */
  .sql-input {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 8px;
    background-color: var(--m-surface);
    border-radius: var(--m-radius-md);
  }

  .sql-row {
    display: grid;
    grid-template-columns: 112px minmax(0, 1fr);
    align-items: flex-start;
    gap: 8px;
  }

  .sql-textarea {
    min-width: 0;
  }

  /* Python代码编辑器 */
  .python-code {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .code-editor {
    height: 360px;
    width: 100%;
    max-width: 700px;
  }

  .save-btn {
    align-self: flex-start;
  }

  .mango-case-custom-variable-list {
    overflow-y: hidden;
    scrollbar-gutter: stable;
  }

  .mango-case-custom-variable-list :deep(.mango-key-value-container) {
    width: 100%;
    min-width: 480px;
  }

  /* 确保KeyValueList中的所有元素都在一行 */
  :deep(.mango-key-value-row) {
    flex-wrap: nowrap;
    align-items: flex-start;
    width: max-content;
    min-width: 100%;
    overflow-x: visible;
  }

  :deep(.mango-key-value-field) {
    flex: 1 0 160px;
    min-width: 120px;
    overflow: hidden; /* 防止内容溢出 */
  }

  :deep(.mango-button-container) {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    flex-shrink: 0;
    white-space: nowrap; /* 防止按钮内文字换行 */
    min-width: fit-content; /* 确保按钮容器不会收缩 */
  }

  :deep(.mango-remove-btn) {
    flex-shrink: 0;
    margin-top: 18px;
    min-width: fit-content; /* 确保按钮不会收缩 */
  }

  /* 响应式处理：在小屏幕上允许换行，但保持按钮在同一行 */
  @media (max-width: 1px) {
    :deep(.mango-key-value-row) {
      flex-wrap: wrap;
    }

    :deep(.mango-key-value-field) {
      min-width: 120px;
    }

    :deep(.mango-button-container) {
      width: 100%;
      justify-content: flex-end;
      margin-top: 8px;
    }

    :deep(.mango-remove-btn) {
      margin-top: 0;
      align-self: center;
    }
  }

  .drag-handle {
    cursor: move;
    color: var(--m-muted);
  }

  .drag-handle:hover {
    color: var(--m-primary);
  }

  .mango-ui-case-page-step-panel {
    display: flex;
    flex: 1 1 auto;
    width: 100%;
    height: 100%;
    min-height: 0;
  }

  .mango-ui-case-page-step-panel :deep(.mango-detail-workbench-page) {
    flex: 1 1 auto;
    height: 100%;
    min-height: 0;
  }

  .ui-case-live-area {
    display: flex;
    flex-direction: column;
    min-height: min(760px, calc(100vh - 132px));
    margin-top: var(--m-page-gap);
    overflow: hidden;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
  }

  .ui-case-live-area :deep(.mango-live-stream--embedded) {
    flex: 1 1 auto;
    width: 100%;
    min-height: 0;
  }

  .ui-case-live-area :deep(.mango-live-stream__viewport) {
    min-height: 480px;
  }

  .ui-case-live-toolbar {
    display: flex;
    flex: 0 0 auto;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 10px 12px;
    border-bottom: 1px solid var(--m-border);
    background: var(--m-bg);
  }

  .ui-case-live-toolbar__title {
    color: var(--m-text);
    font-size: 14px;
    font-weight: 600;
  }

  .ui-case-live-toolbar__subtitle {
    margin-top: 2px;
    color: var(--m-muted);
    font-size: 12px;
  }

  .ui-case-live-toolbar__label {
    color: var(--m-text-2);
    font-size: 12px;
  }

  .ui-case-live-actuator-option {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    width: 100%;
  }

  .ui-case-live-notice {
    padding: 8px 12px;
    border-bottom: 1px solid var(--m-border);
    color: var(--m-warning);
    font-size: 12px;
    background: var(--m-surface-soft);
  }

  .ui-case-live-waiting {
    display: flex;
    flex: 1 1 auto;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 8px;
    min-height: 360px;
    color: var(--m-muted);
  }

  .ui-case-live-waiting svg {
    font-size: 36px;
  }

  .ui-case-live-waiting strong {
    color: var(--m-text);
    font-size: 14px;
  }

  .ui-case-live-waiting span {
    font-size: 12px;
  }

  .mango-ui-case-cache-panel {
    display: flex;
    flex-direction: column;
    gap: 12px;
    height: 100%;
    min-height: 0;
  }

  .mango-ui-case-cache-section {
    padding: 10px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
  }

  .mango-ui-case-cache-section__head {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 8px;
  }

  .mango-ui-case-cache-section__head strong {
    color: var(--m-text);
    font-size: 13px;
  }

  .mango-ui-case-cache-section__head span {
    color: var(--m-muted);
    font-size: 12px;
  }

  .mango-ui-case-cache-panel :deep(.mango-json-display-content) {
    max-height: 280px;
    overflow: auto;
  }

  @media (max-width: 720px) {
    .step-card-head {
      flex-direction: column;
      align-items: stretch;
    }

    .step-card-tags {
      grid-template-columns: 1fr;
      justify-content: flex-start;
      padding-right: 0;
    }

    .step-card-tag-list {
      grid-template-columns: max-content max-content max-content;
      justify-content: stretch;
      padding-left: 0;
    }

    .step-card-element-action,
    .step-card-element-action--placeholder {
      width: auto;
    }

    .step-card-element-action--placeholder {
      display: none;
    }

    .ui-case-panel-head--steps {
      flex-direction: column;
      align-items: stretch;
    }

    .step-result-side {
      align-items: flex-start;
    }

    .step-result-actions,
    .ui-case-panel-head--steps .step-result-metrics {
      justify-content: flex-start;
    }

    .ui-case-step-builder {
      grid-template-columns: 1fr;
    }

    .ui-case-step-assets {
      max-height: 360px;
    }

    .condition-input,
    .operation-input,
    .assertion-input,
    .param-row,
    .sql-row {
      grid-template-columns: 1fr;
      gap: 4px;
    }

    .ui-case-live-area {
      min-height: min(760px, calc(100% - 12px));
    }

    .ui-case-live-area :deep(.mango-live-stream__viewport) {
      min-height: 360px;
    }

    .ui-case-live-toolbar {
      align-items: stretch;
      flex-direction: column;
    }

    .input-label {
      line-height: 20px;
      text-align: left;
    }
  }
</style>
