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
          <a-button v-permission="'ui.case:execute'"
            size="small"
            status="success"
            :loading="caseRunning"
            :disabled="caseExecutionActive"
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
            <a-tabs
              class="ui-case-step-tabs"
              :active-key="data.uiType"
              @tab-click="(key) => switchType(key)"
            >
              <template #extra>
                <a-button v-permission="'ui.case:create'" v-if="showCaseAddButton" size="small" type="primary" @click="addData" data-testid="qa-views-uitest-case-details-button-新增">
                  新增
                </a-button>
              </template>
              <a-tab-pane key="1" title="前置准备" data-testid="qa-views-uitest-case-details-tab-pane-前置准备">
                <a-tabs
                  class="ui-case-config-tabs"
                  :active-key="data.uiSonType"
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
                            <span>环境</span>
                            <span>状态</span>
                          </div>
                          <a-checkbox-group
                            class="mango-case-global-table__body"
                            v-model="frontPublicCheckedValues"
                            :disabled="caseGlobalSaving"
                            direction="vertical"
                            @change="changeCaseGlobalOptions"
                          >
                            <a-checkbox
                              v-for="item in data.publicOptions"
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
                      <div class="mango-case-global-option">
                        <div class="mango-case-global-table mango-case-global-table--auth">
                          <div class="mango-case-global-table__head">
                            <span></span>
                            <span>授权名称</span>
                            <span>授权方式</span>
                            <span>环境</span>
                            <span>状态</span>
                          </div>
                          <a-checkbox-group
                            class="mango-case-global-table__body"
                            v-model="frontAuthConfigCheckedValues"
                            :disabled="caseGlobalSaving"
                            direction="vertical"
                            @change="changeCaseGlobalOptions"
                          >
                            <a-checkbox
                              v-for="item in data.authConfigOptions"
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
                        :data-list="pageData.record.front_custom"
                        layout="environment-key-value"
                        :field-config="[
                          {
                            field: 'test_envs',
                            label: '适用环境',
                            type: 'select',
                            placeholder: '请选择环境',
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
                          (index) => removeFrontSql(pageData.record.front_custom, index)
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
                      :data-list="pageData.record.front_sql"
                      :datasource-options="data.datasourceAliasOptions"
                      :environment-options="sqlEnvironmentOptions"
                      :project-product-id="uiProjectProductId"
                      :test-env="userStore.selected_environment"
                      operation-field="sql"
                      key-field="key_list"
                      key-label="缓存 Key"
                      key-placeholder="请输入查询结果缓存 Key"
                      :on-delete-item="(index) => removeFrontSql(pageData.record.front_sql, index)"
                      :on-save="upDataCase"
                    />
                  </a-tab-pane>
                  <a-tab-pane key="14">
                    <template #title>
                      <span class="case-config-tab-title">
                        数据工厂
                        <span class="case-config-tab-count">{{
                          getCaseConfigCount('factory')
                        }}</span>
                      </span>
                    </template>
                    <DataFactoryCaseConfigPanel
                      ref="dataFactoryPanelRef"
                      :case-id="uiCaseId as string"
                      :project-product-id="uiProjectProductId as string"
                      :source-type="2"
                      @count-change="setCaseDataFactoryCount"
                    />
                  </a-tab-pane>
                </a-tabs>
              </a-tab-pane>

              <a-tab-pane key="2" title="执行编排" data-testid="qa-views-uitest-case-details-tab-pane-执行编排">
                <section class="ui-case-step-table-drop">
                  <mango-panel-spin :loading="stepTableLoading" class="ui-case-step-card-spin">
                    <div
                      v-if="data.data.length"
                      class="ui-case-step-card-list mango-native-scrollbar"
                    >
                      <article
                        v-for="(record, index) in data.data"
                        :key="record.id"
                        :class="[
                          'ui-case-step-card',
                          {
                            'ui-case-step-card--selected':
                              String(data.selectData?.id) === String(record.id),
                            'ui-case-step-card--dragging': caseStepDragIndex === index,
                          },
                        ]"
                        draggable="true"
                        @click="select(record)"
                        @dragstart="onCaseStepDragStart($event, index)"
                        @dragend="onCaseStepDragEnd"
                        @dragover.prevent
                        @drop.prevent="onCaseStepDrop(index)"
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
                              <a-switch v-permission="'ui.case:edit'"
                                size="small"
                                :beforeChange="
                                  (newValue) =>
                                    onModifyStatus(newValue, record.id, 'switch_step_open_url')
                                "
                                :default-checked="record.switch_step_open_url === 1"
                              />
                            </span>
                            <a-popover
                              trigger="click"
                              position="bottom"
                              :popup-visible="retryEditor.recordId === String(record.id)"
                              @popup-visible-change="
                                (visible) => onRetryEditorVisibleChange(visible, record)
                              "
                            >
                              <a-button
                                size="mini"
                                type="text"
                                class="ui-case-step-card__retry-trigger"
                                :loading="retryEditor.savingId === String(record.id)" data-testid="qa-views-uitest-case-details-button-重试-次"
                              >
                                重试 {{ record.error_retry ?? 0 }} 次
                              </a-button>
                              <template #content>
                                <div class="ui-case-step-card__retry-editor">
                                  <span>失败重试次数</span>
                                  <a-input-number
                                    v-model="retryEditor.value"
                                    size="small"
                                    :min="0"
                                    :precision="0"
                                    class="ui-case-step-card__retry-input"
                                    placeholder="请输入重试次数"
                                    @press-enter="saveCaseStepRetry(record)" data-testid="qa-views-uitest-case-details-input-number-请输入重试次数"
                                  />
                                  <a-space :size="6">
                                    <a-button size="mini" @click="closeRetryEditor(record)" data-testid="qa-views-uitest-case-details-button-取消">
                                      取消
                                    </a-button>
                                    <a-button v-permission="['ui.case:create', 'ui.case:edit']"
                                      size="mini"
                                      type="primary"
                                      :loading="retryEditor.savingId === String(record.id)"
                                      @click="saveCaseStepRetry(record)" data-testid="qa-views-uitest-case-details-button-保存"
                                    >
                                      保存
                                    </a-button>
                                  </a-space>
                                </div>
                              </template>
                            </a-popover>
                          </div>
                          <a-space :size="4">
                            <a-button
                              size="mini"
                              type="text"
                              :loading="caseRunning"
                              @click="onPageStep(record)" data-testid="qa-views-uitest-case-details-button-单步执行"
                            >
                              单步执行
                            </a-button>
                            <a-button v-permission="'ui.case:edit'" size="mini" type="text" @click="oeFreshSteps(record)" data-testid="qa-views-uitest-case-details-button-同步">
                              同步
                            </a-button>
                            <a-button v-permission="'ui.case:delete'"
                              size="mini"
                              type="text"
                              status="danger"
                              @click="onDelete(record)" data-testid="qa-views-uitest-case-details-button-删除"
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
                    <a-empty v-else description="暂无执行步骤，请点击新增" />
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
                      :data-list="pageData.record.posterior_sql"
                      :datasource-options="data.datasourceAliasOptions"
                      :environment-options="sqlEnvironmentOptions"
                      :project-product-id="uiProjectProductId"
                      :test-env="userStore.selected_environment"
                      :show-key="false"
                      operation-field="sql"
                      :on-delete-item="
                        (index) => removeFrontSql(pageData.record.posterior_sql, index)
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
          <PageStepsDetails
            v-if="getPageStepId(data.selectData)"
            :key="`case-step-${data.selectData.id}`"
            embedded
            compact
            case-input-mode
            :case-id="uiCaseId"
            :case-step-id="data.selectData.id"
            :case-data="data.selectData.case_data || []"
            :case-result="selectedPageStepResult"
            :page-steps-id="getPageStepId(data.selectData)"
            :page-id="getPageId(data.selectData)"
            :refresh-token="caseCanvasRefreshStamp"
            @open-page-step-detail="openPageStepDetail(data.selectData)"
            @open-cache-data="cacheVariablePanel.visible = true"
            @case-data-saved="handleCaseNodeInputsSaved"
          />
          <div v-else class="mango-empty-state">请先在步骤编排中选择一个页面步骤</div>
          <template v-if="false">
            <div class="ui-case-panel-head ui-case-panel-head--steps">
              <div class="step-result-head-main">
                <div>
                  <div class="step-header">{{
                    data.selectData?.page_step?.name || '步骤执行明细'
                  }}</div>
                  <div class="step-result-subtitle">
                    配置步骤 {{ getCaseStepList().length }} 个，最近结果
                    {{ selectedResultSteps.length }} 个
                  </div>
                  <div class="step-result-hint">
                    存在条件判断节点时，实际执行顺序会按运行时分支流转。
                  </div>
                </div>
              </div>
              <div class="step-result-side">
                <div class="step-result-actions">
                  <a-button v-permission="'ui.case:detail'"
                    type="primary"
                    size="small"
                    :disabled="!getPageStepId(data.selectData)"
                    @click="openPageStepDetail(data.selectData)" data-testid="qa-views-uitest-case-details-button-步骤详情"
                  >
                    步骤详情
                  </a-button>
                </div>
                <div class="step-result-metrics">
                  <a-tag size="small" color="green">通过 {{ resultPassedCount }}</a-tag>
                  <a-tag size="small" color="red">失败 {{ resultFailedCount }}</a-tag>
                  <a-tag size="small" color="gray">未测 {{ resultPendingCount }}</a-tag>
                </div>
              </div>
            </div>
            <div class="ui-case-panel-body">
              <section class="step-result-workbench">
                <div v-if="getCaseStepList().length === 0" class="mango-empty-state">
                  暂无步骤数据
                </div>
                <a-collapse
                  v-else
                  :key="data.selectData?.id || 'empty'"
                  :bordered="false"
                  :default-active-key="defaultOpenStepKeys"
                  class="step-execution-collapse"
                >
                  <a-collapse-item
                    v-for="(item, index) of getCaseStepList()"
                    :key="getStepKey(item, index)"
                    class="step-list-item"
                  >
                    <template #header>
                      <div class="step-collapse-header">
                        <div class="step-card-head">
                          <div class="step-card-title">
                            <span class="step-main-name">
                              {{
                                item.page_step_details_name ||
                                getStepMethodLabel(item.ope_key) ||
                                '未命名步骤'
                              }}
                            </span>
                          </div>
                          <div class="step-card-tags">
                            <div class="step-card-tag-list">
                              <span class="step-type-card">
                                <span
                                  class="step-type-dot"
                                  :style="{ backgroundColor: getStepTypeColor(item.type) }"
                                ></span>
                                {{ getStepTypeLabel(item.type) }}
                              </span>
                              <a-tag v-if="item.ope_key" size="small" color="arcoblue">
                                {{ getStepMethodLabel(item.ope_key) }}
                              </a-tag>
                              <span v-else class="step-card-tag-placeholder"></span>
                              <a-tag
                                size="small"
                                :color="getStepResultColor(getStepResult(item, index))"
                              >
                                {{ getStepResultStatusText(getStepResult(item, index)) }}
                              </a-tag>
                            </div>
                            <a-button
                              v-if="getElementRows(getStepResult(item, index)).length"
                              class="step-card-element-action"
                              size="mini"
                              :loading="elementEditLoading"
                              @click.stop="openElementEditPanel(item)" data-testid="qa-views-uitest-case-details-button-查看元素"
                            >
                              查看元素
                            </a-button>
                            <span
                              v-else
                              class="step-card-element-action step-card-element-action--placeholder"
                            ></span>
                          </div>
                        </div>
                        <div class="step-collapse-meta">
                          <span>ID {{ item.page_step_details_id || '-' }}</span>
                          <span v-if="item.page_step_details_name"
                            >元素 {{ item.page_step_details_name }}</span
                          >
                          <span>参数 {{ getStepParamCount(item) }} 项</span>
                          <span v-if="getStepHeaderParamSummary(item)">
                            入参 {{ getStepHeaderParamSummary(item) }}
                          </span>
                          <span>{{ getStepResultSummary(getStepResult(item, index)) }}</span>
                        </div>
                      </div>
                    </template>

                    <div class="step-container">
                      <!-- 步骤详情数据 -->
                      <div class="step-details">
                        <div class="step-section-title">步骤配置</div>
                        <div class="step-meta-grid">
                          <div class="step-meta-item">
                            <span class="step-meta-label">步骤ID</span>
                            <span class="step-meta-value">{{
                              item.page_step_details_id || '-'
                            }}</span>
                          </div>
                          <div class="step-meta-item">
                            <span class="step-meta-label">类型</span>
                            <span class="step-meta-value step-meta-value--type">
                              <span class="step-type-card step-type-card--meta">
                                <span
                                  class="step-type-dot"
                                  :style="{ backgroundColor: getStepTypeColor(item.type) }"
                                ></span>
                                {{ getStepTypeLabel(item.type) }}
                              </span>
                            </span>
                          </div>
                          <div class="step-meta-item">
                            <span class="step-meta-label">方法</span>
                            <span class="step-meta-value">{{
                              getStepMethodLabel(item.ope_key)
                            }}</span>
                          </div>
                          <div v-if="item.page_step_details_name" class="step-meta-item">
                            <span class="step-meta-label">元素名称</span>
                            <span class="step-meta-value">{{ item.page_step_details_name }}</span>
                          </div>
                          <div class="step-meta-item">
                            <span class="step-meta-label">参数数</span>
                            <span class="step-meta-value">{{ getStepParamCount(item) }}</span>
                          </div>
                          <div v-if="item.condition_value" class="step-meta-item">
                            <span class="step-meta-label">条件</span>
                            <span class="step-meta-value">{{
                              getConditionSummary(item.condition_value)
                            }}</span>
                          </div>
                        </div>
                        <!-- 条件判断值 -->
                        <div v-if="item.condition_value" class="condition-input">
                          <span class="input-label">条件判断值：</span>
                          <a-textarea
                            v-model="item.condition_value.expect"
                            :auto-size="{ minRows: 1, maxRows: 5 }"
                            class="custom-textarea"
                            @blur="onUpdate"
                          />
                        </div>
                        <DataSourceOperationList
                          v-if="item.type === 2"
                          :data-list="getStepParams(item)"
                          :datasource-options="data.datasourceAliasOptions"
                          :environment-options="sqlEnvironmentOptions"
                          :project-product-id="uiProjectProductId"
                          :test-env="userStore.selected_environment"
                          :show-delete="false"
                          operation-field="sql"
                          key-field="key_list"
                          key-label="缓存 Key"
                          key-placeholder="请输入查询结果缓存 Key"
                          :on-save="onUpdate"
                        />
                        <template
                          v-else
                          v-for="(item1, idx) of item.page_step_details_data"
                          :key="item1.id || `${item.page_step_details_id}-${idx}`"
                        >
                          <!-- 操作类型 (type === 0) -->
                          <template v-if="item.type === 0">
                            <div v-if="item1.d" class="operation-input">
                              <span class="input-label">{{ item1.n }}：</span>
                              <a-textarea
                                v-model="item1.v"
                                :auto-size="{ minRows: 1, maxRows: 5 }"
                                class="custom-textarea"
                                @blur="onUpdate"
                              />
                            </div>
                          </template>

                          <!-- 断言类型 (type === 1) -->
                          <template v-else-if="item.type === 1">
                            <div v-if="item1.f === 'datasource_alias'" class="assertion-input">
                              <span class="input-label">{{ item1.n }}：</span>
                              <a-select
                                v-model="item1.v"
                                :options="sqlAssertionDatasourceOptions"
                                placeholder="请选择 MySQL、PostgreSQL 或 SQLite 逻辑数据源"
                                allow-clear
                                allow-search
                                @change="onUpdate" data-testid="qa-views-uitest-case-details-select-请选择-mysql-postgresql-或-sqlite-逻辑数据源"
                              />
                            </div>
                            <div v-else-if="item1.f !== 'actual'" class="assertion-input">
                              <span class="input-label">{{ item1.n }}：</span>
                              <a-textarea
                                v-model="item1.v"
                                :auto-size="{ minRows: 1, maxRows: 5 }"
                                class="custom-textarea"
                                @blur="onUpdate"
                              />
                            </div>
                          </template>

                          <!-- 自定义参数类型 (type === 3) -->
                          <template v-else-if="item.type === 3">
                            <div class="custom-param-input">
                              <div class="param-row">
                                <span class="input-label">key：</span>
                                <a-textarea
                                  v-model="item1.key"
                                  :auto-size="{ minRows: 1, maxRows: 5 }"
                                  class="custom-textarea"
                                  @blur="onUpdate"
                                />
                              </div>
                              <div class="param-row">
                                <span class="input-label">value：</span>
                                <a-textarea
                                  v-model="item1.value"
                                  :auto-size="{ minRows: 1, maxRows: 5 }"
                                  class="custom-textarea"
                                  @blur="onUpdate"
                                />
                              </div>
                            </div>
                          </template>

                          <!-- Python代码类型 (type === 5) -->
                          <template v-else-if="item.type === 5">
                            <div class="python-code">
                              <CodeEditor
                                v-model="item1.func"
                                placeholder="请输入python代码"
                                class="code-editor"
                              />
                              <a-button v-permission="['ui.case:create', 'ui.case:edit']"
                                type="primary"
                                class="save-btn"
                                :loading="detailSaving"
                                @click="onUpdate" data-testid="qa-views-uitest-case-details-button-保存-2"
                                >保存
                              </a-button>
                            </div>
                          </template>

                          <!-- 条件判断类型 (type === 4) -->
                          <template v-else-if="item.type === 4">
                            <!-- 条件判断暂无内容 -->
                          </template>
                        </template>
                      </div>

                      <UiStepRuntimeResult
                        :result="getStepResult(item, index)"
                        :fallback-ope-key="item.ope_key"
                        :fallback-element-name="item.page_step_details_name"
                        image-width="220"
                      />
                    </div>
                  </a-collapse-item>
                </a-collapse>
              </section>
            </div>
          </template>
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
              :disabled="caseExecutionActive"
              class="ui-case-live-toolbar__actuator-select"
              @change="handleCaseActuatorChange" data-testid="qa-views-uitest-case-details-select-请选择执行器"
            >
              <a-option
                v-for="item in caseActuatorOptions"
                :key="item.username"
                :value="item.username"
                :label="`${item.name || item.username}（${item.username} · ${
                  item.active_user_count || 0
                }/${item.max_user_count || 5} 人）`"
                :disabled="item.is_full && !(item.users || []).some((user: any) => user.username === userStore.userName)"
              >
                <div class="ui-case-live-actuator-option">
                  <span>{{ item.name || item.username }}（{{ item.username }}）</span>
                  <a-tag v-if="item.is_owner" size="small">本人</a-tag>
                  <a-tag v-else color="green" size="small">已开放</a-tag>
                  <a-tag size="small"
                    >{{ item.active_user_count || 0 }}/{{ item.max_user_count || 5 }} 人</a-tag
                  >
                </div>
              </a-option>
            </a-select>
            <a-button
              size="small"
              :loading="caseActuatorLoading"
              :disabled="caseExecutionActive"
              @click="loadCaseActuatorOptions(true)" data-testid="qa-views-uitest-case-details-button-刷新执行器"
            >
              刷新执行器
            </a-button>
          </a-space>
        </div>
        <div v-if="!caseActuatorLoading && !caseActuatorOptions.length" class="ui-case-live-notice">
          暂无支持 Web 直播的在线执行器，请启动本人执行器或开放其他执行器。
        </div>
        <UiLiveStreamPanel
          v-if="caseLiveExecutionId"
          v-model:visible="liveStreamVisible"
          execution-type="ui_case"
          :execution-id="caseLiveExecutionId"
          :resource-id="uiCaseId"
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
    :visible="pageStepDetailPanel.visible"
    title="页面步骤详情"
    page-description="从界面用例的 Case 步骤中打开，当前展示已存在的页面步骤及其完整操作区域"
    width="calc(92vw - 150px)"
    mode="page"
    @update:visible="
      (val) => {
        pageStepDetailPanel.visible = val
      }
    "
    @cancel="pageStepDetailPanel.visible = false"
  >
    <div class="mango-ui-case-page-step-panel">
      <PageStepsDetails
        v-if="pageStepDetailPanel.visible && pageStepDetailPanel.pageStepsId"
        :key="pageStepDetailPanel.pageStepsId"
        embedded
        :page-steps-id="pageStepDetailPanel.pageStepsId"
        :page-id="pageStepDetailPanel.pageId"
        :page-type="pageStepDetailPanel.pageType"
        @close="pageStepDetailPanel.visible = false"
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
          <span>{{ data.selectData?.page_step?.name || data.selectData?.name || '-' }}</span>
        </div>
        <JsonDisplay
          :data="currentStepCacheData"
          :show-drawer-button="false"
          :default-expanded="true"
        />
      </section>
      <section class="mango-ui-case-cache-section">
        <div class="mango-ui-case-cache-section__head">
          <strong>整个 Case 缓存变量</strong>
          <span>最近一次完整执行后的最终缓存快照</span>
        </div>
        <JsonDisplay :data="caseCacheData" :show-drawer-button="false" :default-expanded="true" />
      </section>
      <section class="mango-ui-case-cache-section">
        <div class="mango-ui-case-cache-section__head">
          <strong>数据工厂缓存变量</strong>
          <span>数据工厂生成或注入的上下文</span>
        </div>
        <JsonDisplay
          :data="caseDataFactoryCacheData"
          :show-drawer-button="false"
          :default-expanded="true"
        />
      </section>
    </div>
  </BaseSidePanel>

  <UiElementEditPanel ref="elementEditPanelRef" @saved="doRefresh" />
  <UiCaseStepCreateDialog
    ref="caseStepCreateDialogRef"
    :case-id="uiCaseId"
    :case-step-count="data.data.length"
    @created="doRefresh"
  />

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
          <template v-else-if="item.type === 'cascader' && item.key === 'module'">
            <ProductModuleSelect
              v-model="item.value"
              :project-product-id="uiProjectProductId as string"
              :placeholder="item.placeholder"
              @change="doUiPageNameAll"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'page'">
            <a-select
              v-model="item.value"
              :field-names="fieldNames"
              :options="data.pageName"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              value-key="key"
              @change="doUiStepsPageStepsName(item.value)"
            />
          </template>
          <template v-else-if="item.type === 'switch' && item.key === 'switch_step_open_url'">
            <a-switch v-model="item.value" :checked-value="1" :unchecked-value="0" />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'page_step'">
            <a-select
              v-model="item.value"
              :field-names="fieldNames"
              :options="data.pageStepsName"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              value-key="key"
            />
          </template>
        </a-form-item>
      </a-form>
    </template>
  </ModalDialog>
</template>
<script lang="ts" setup>
  import { computed, nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'
  import { Message, Modal, Notification } from '@arco-design/web-vue'
  import { IconDesktop } from '@arco-design/web-vue/es/icon'

  import { ModalDialogType } from '@/types/components'
  import { useRoute } from 'vue-router'
  import { getFormItems } from '@/utils/datacleaning'
  import { fieldNames } from '@/setting'
  import ModalDialog from '@/components/overlays/ModalDialog.vue'
  import { usePageData } from '@/store/page-data'
  import { formItems } from './config'
  import {
    deleteUiCaseStepsDetailed,
    getUiCaseStepsDetailed,
    getUiCaseStepsRefreshCacheData,
    postUiCaseStepsDetailed,
    putUiCasePutCaseSort,
    putUiCaseStepsDetailed,
  } from '@/api/uitest/case-steps-detailed'
  import { getUiCase, getUiCaseRun, putUiCase } from '@/api/uitest/case'
  import {
    getUiPageStepAssetModules,
    getUiPageStepAssetProducts,
    getUiPageStepAssetSteps,
    getUiSteps,
    getUiStepsPageStepsName,
    getUiStepsTest,
  } from '@/api/uitest/page-steps'
  import { getUiPageName } from '@/api/uitest/page'
  import { getExecutionResultLatestResolved } from '@/api/system/execution_result'
  import { getSystemSocketCurrentActuatorStatus } from '@/api/system/socket_api'
  import useUserStore from '@/store/modules/user'
  import { useEnum } from '@/store/modules/get-enum'
  import { useSelectValueStore } from '@/store/modules/get-ope-value'
  import CodeEditor from '@/components/editors/CodeEditor.vue'
  import KeyValueList from '@/components/forms/KeyValueList.vue'
  import DataSourceOperationList from '@/components/forms/DataSourceOperationList.vue'
  import DataFactoryCaseConfigPanel from '@/components/DataFactory/CaseConfigPanel.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import UiElementEditPanel from '@/components/business/UiElementEditPanel.vue'
  import UiCaseStepCreateDialog from '@/components/business/UiCaseStepCreateDialog.vue'
  import UiLiveStreamPanel from '@/components/business/UiLiveStreamPanel.vue'
  import VariableReferencePanel from '@/components/business/VariableReferencePanel.vue'
  import ExecutionResultHistoryDrawer from '@/components/business/ExecutionResultHistoryDrawer.vue'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import JsonDisplay from '@/components/display/JsonDisplay.vue'
  import TipMessage from '@/components/feedback/TipMessage.vue'
  import UiStepRuntimeResult from '@/components/reports/UiStepRuntimeResult.vue'
  import UiCaseExecutionResult from '@/components/reports/UiCaseExecutionResult.vue'
  import PageStepsDetails from '@/views/uitest/page-steps/details/index.vue'
  import { getDataFactoryCaseConfig, getDataFactoryDatasourceAlias } from '@/api/data-factory'
  import { getUiPageStepsDetailedById } from '@/api/uitest/page-steps-detailed'
  import { getUiPublic } from '@/api/uitest/public'
  import { getUiAuthConfig } from '@/api/uitest/auth-config'
  import type { UiCasePayload } from '@/types/ui-test/case'
  import { waitForMinimumLoading } from '@/utils/minimum-loading'
  import {
    COMMON_ENV_VALUE,
    normalizeEnvironmentSelectChange,
    normalizeEnvironmentValues,
    toEnvironmentSelectValue,
  } from '@/utils/environment-scope'
  import { getActiveExecutorTasks, getExecutorTask } from '@/api/system/executor-task'
  import {
    clearExecutorTaskObservation,
    loadExecutorTaskObservation,
    saveExecutorTaskObservation,
  } from '@/utils/executor-task-observer.mjs'
  import { claimExecutorTaskNotification } from '@/utils/executor-task-notification'

  const userStore = useUserStore()
  const enumStore = useEnum()

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
  const uiCaseId = computed(
    () => props.caseId || route.query.id || route.query.case_id || pageData.record?.id || ''
  )
  const uiProjectProductId = computed(
    () =>
      props.projectProductId ||
      route.query.project_product ||
      pageData.record?.project_product?.id ||
      pageData.record?.project_product ||
      ''
  )
  const uiCaseModuleId = computed(
    () => pageData.record?.module?.id || pageData.record?.module || ''
  )
  const sqlEnvironmentOptions = computed(() =>
    (enumStore.environment_type || []).map((item: any) => ({
      label: item.title,
      value: item.key,
    }))
  )
  const caseVariableEnvironmentOptions = computed(() => [
    { key: COMMON_ENV_VALUE, title: '环境通用' },
    ...enumStore.environment_type,
  ])
  const defaultCaseRecord = () => ({
    id: uiCaseId.value,
    name: '',
    front_custom: [],
    front_sql: [],
    front_public: [],
    front_auth_config: [],
    posterior_sql: [],
    project_product: uiProjectProductId.value ? { id: uiProjectProductId.value } : null,
  })
  if (!pageData.record) {
    pageData.setRecord(defaultCaseRecord())
  }
  const formModel = ref({})
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const dataFactoryPanelRef = ref<InstanceType<typeof DataFactoryCaseConfigPanel> | null>(null)
  const elementEditPanelRef = ref<InstanceType<typeof UiElementEditPanel> | null>(null)
  const caseStepCreateDialogRef = ref<InstanceType<typeof UiCaseStepCreateDialog> | null>(null)
  const elementEditLoading = ref(false)
  const caseStepDragIndex = ref<number | null>(null)
  const retryEditor = reactive({
    recordId: '',
    value: 0,
    savingId: '',
  })
  const latestUiCaseResult = ref<any>(null)
  const latestUiCaseResultPending = ref(false)
  const resultHistoryVisible = ref(false)
  const uiCaseResultHistoryQuery = computed(() => ({
    source_type: 'page',
    target_type: 'ui_case',
    target_id: uiCaseId.value,
  }))
  // 同步成功后递增，驱动右侧嵌入画布重新拉取最新步骤数据
  const caseCanvasRefreshStamp = ref(0)
  const pageStepDetailPanel = reactive({
    visible: false,
    pageStepsId: '',
    pageId: '',
    pageType: '',
  })
  const cacheVariablePanel = reactive({
    visible: false,
  })
  const data: any = reactive({
    isAdd: true,
    updateId: null,
    pageName: [],
    pageStepsName: [],
    data: [],
    selectData: {},
    actionTitle: '新增',
    uiType: '2',
    uiSonType: '11',
    datasourceAliasOptions: [],
    publicOptions: [],
    authConfigOptions: [],
  })
  const stepAsset: any = reactive({
    product: '',
    productOptions: [],
    module: '',
    moduleOptions: [],
    steps: [],
    loadingProducts: false,
    loadingModules: false,
    loadingSteps: false,
    appendLoading: '',
    draggingStep: null,
    dragOver: false,
  })
  const useSelectValue = useSelectValueStore()

  const caseRunning = ref(false)
  const caseExecutionId = ref('')
  const caseExecutorTaskId = ref('')
  let caseExecutorTaskTimer: ReturnType<typeof window.setTimeout> | null = null
  const liveStreamVisible = ref(false)
  const caseLiveOpening = ref(false)
  const caseLiveExecutionId = ref('')
  const caseLiveSectionRef = ref<HTMLElement | null>(null)
  const caseLiveActuatorUsername = ref('')
  const caseActuatorOptions = ref<any[]>([])
  const caseActuatorLoading = ref(false)
  const selectedCaseActuatorUsername = ref('')
  const caseExecutionActive = ref(false)
  let lastNotifiedCaseTaskId = ''
  const stepTableLoading = ref(false)
  const caseGlobalSaving = ref(false)
  const caseDataFactoryCount = ref(0)
  const detailSaving = ref(false)
  const uiCaseDetailTitle = computed(() => {
    const id = uiCaseId.value || '-'
    const name = pageData.record?.name || '-'
    return `界面用例配置 / ${id} / ${name}`
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
  const pollingTimer = ref<NodeJS.Timeout | null>(null)
  const showCaseAddButton = computed(() => {
    if (data.uiType === '2') return true
    if (data.uiType === '1') return ['11', '12', '14'].includes(data.uiSonType)
    return data.uiType === '3' && data.uiSonType === '31'
  })
  const casePageStepResults = computed(() =>
    Array.isArray(latestUiCaseResult.value?.steps) ? latestUiCaseResult.value.steps : []
  )
  const selectedPageStepResult = computed(() =>
    casePageStepResults.value.find(
      (item: any) =>
        data.selectData?.id && String(item?.case_step_details_id) === String(data.selectData.id)
    )
  )
  const selectedResultSteps = computed(() =>
    Array.isArray(selectedPageStepResult.value?.element_result_list)
      ? selectedPageStepResult.value.element_result_list
      : []
  )
  const resultPassedCount = computed(
    () => selectedResultSteps.value.filter((item: any) => item.status === 1).length
  )
  const resultFailedCount = computed(
    () => selectedResultSteps.value.filter((item: any) => item.status === 0).length
  )
  const resultPendingCount = computed(() => {
    const configuredCount = getCaseStepList().length
    const resultCount = selectedResultSteps.value.length
    return Math.max(
      configuredCount - resultPassedCount.value - resultFailedCount.value,
      configuredCount - resultCount
    )
  })
  const stepAssets = computed(() => (Array.isArray(stepAsset.steps) ? stepAsset.steps : []))
  const defaultOpenStepKeys = computed(() => {
    const steps = getCaseStepList()
    const failedKeys = steps
      .map((item: any, index: number) => ({ item, index, result: getStepResult(item, index) }))
      .filter(({ result }: any) => result?.status === 0)
      .map(({ item, index }: any) => getStepKey(item, index))
    return failedKeys
  })
  const currentStepCacheData = computed(() => {
    return normalizeRuntimeObject(selectedPageStepResult.value?.cache_data)
  })
  const caseCacheData = computed(() => {
    const caseResultData = latestUiCaseResult.value || {}
    if (hasRuntimeValue(caseResultData?.cache_data)) {
      return normalizeRuntimeObject(caseResultData.cache_data)
    }
    const steps = Array.isArray(caseResultData?.steps) ? caseResultData.steps : []
    const lastStepWithCache = [...steps]
      .reverse()
      .find((item: any) => hasRuntimeValue(item?.cache_data))
    return normalizeRuntimeObject(lastStepWithCache?.cache_data)
  })
  const caseDataFactoryCacheData = computed(() => {
    const caseResultData = latestUiCaseResult.value || {}
    if (hasRuntimeValue(caseResultData?.data_factory_cache_data)) {
      return normalizeRuntimeObject(caseResultData.data_factory_cache_data)
    }
    const steps = Array.isArray(caseResultData?.steps) ? caseResultData.steps : []
    const lastStepWithCache = [...steps]
      .reverse()
      .find((item: any) => hasRuntimeValue(item?.data_factory_cache_data))
    return normalizeRuntimeObject(lastStepWithCache?.data_factory_cache_data)
  })

  function hasRuntimeValue(value: unknown) {
    if (value === null || value === undefined || value === '') return false
    if (Array.isArray(value)) return value.length > 0
    if (typeof value === 'object') return Object.keys(value as Record<string, unknown>).length > 0
    return true
  }

  function normalizeRuntimeObject(value: unknown) {
    return hasRuntimeValue(value) ? value : {}
  }

  function clearPollingTimer() {
    if (pollingTimer.value) {
      clearInterval(pollingTimer.value)
      pollingTimer.value = null
    }
  }

  function switchType(key: any) {
    if (key === '1') {
      data.uiSonType = '15'
    } else if (key === '3') {
      data.uiSonType = '31'
    }
    data.uiType = key
  }

  function switchSonType(key: any) {
    data.uiSonType = key
  }

  function configuredItemCount(value: any) {
    if (!Array.isArray(value)) return value ? 1 : 0
    return value.length
  }

  function setCaseDataFactoryCount(count: number) {
    caseDataFactoryCount.value = Math.max(0, Number(count) || 0)
  }

  async function loadCaseDataFactoryCount() {
    if (!uiCaseId.value) {
      setCaseDataFactoryCount(0)
      return
    }
    try {
      const res = await getDataFactoryCaseConfig({ source_type: 2, source_id: uiCaseId.value })
      setCaseDataFactoryCount(Array.isArray(res.data) ? res.data.length : 0)
    } catch (error) {
      console.log(error)
    }
  }

  function getCaseConfigCount(
    type: 'public' | 'auth' | 'custom' | 'frontSql' | 'factory' | 'posteriorSql'
  ) {
    if (type === 'public') return configuredItemCount(frontPublicCheckedValues.value)
    if (type === 'auth') return configuredItemCount(frontAuthConfigCheckedValues.value)
    if (type === 'custom') return configuredItemCount(pageData.record?.front_custom)
    if (type === 'frontSql') return configuredItemCount(pageData.record?.front_sql)
    if (type === 'factory') return caseDataFactoryCount.value
    return configuredItemCount(pageData.record?.posterior_sql)
  }

  function addData() {
    data.isAdd = true

    if (data.uiType == '2') {
      caseStepCreateDialogRef.value?.open()
      return
    }
    if (data.uiSonType === '11') {
      pageData.record.front_custom.push({ key: '', value: '', test_envs: [] })
    } else if (data.uiSonType === '12') {
      pageData.record.front_sql.push({
        sql: '',
        key_list: '',
        datasource_alias: null,
        test_envs: [],
      })
    } else if (data.uiSonType === '14') {
      dataFactoryPanelRef.value?.open()
    } else if (data.uiSonType === '31') {
      pageData.record.posterior_sql.push({ sql: '', datasource_alias: null, test_envs: [] })
    }
  }

  function removeFrontSql(item: any, index: number) {
    item.splice(index, 1)
    upDataCase()
  }

  function getVariableEnvironmentValue(item: any) {
    return toEnvironmentSelectValue(item?.test_envs)
  }

  function setVariableEnvironmentValue(value: any, item: any) {
    item.test_envs = normalizeEnvironmentValues(normalizeEnvironmentSelectChange(value))
  }

  function upDataCase() {
    const payload: UiCasePayload = {
      id: pageData.record.id,
      name: pageData.record.name,
      posterior_sql: pageData.record.posterior_sql,
      front_sql: pageData.record.front_sql,
      front_custom: pageData.record.front_custom,
      front_public: pageData.record.front_public,
      front_auth_config: pageData.record.front_auth_config,
    }
    putUiCase(payload)
      .then((res) => {
        Message.success(res.msg)
        doRefresh()
      })
      .catch(console.log)
  }

  async function changeCaseGlobalOptions() {
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
      const res = await putUiCase({
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

  function getOptionValue(item: any) {
    return item?.key ?? item?.value ?? item?.id ?? ''
  }

  function getOptionTitle(item: any) {
    return String(item?.title ?? item?.label ?? item?.name ?? getOptionValue(item) ?? '-')
  }

  function findFirstLeafOption(options: any[]): any {
    for (const option of options || []) {
      if (Array.isArray(option?.children) && option.children.length) {
        const child = findFirstLeafOption(option.children)
        if (child) return child
      } else if (getOptionValue(option) !== '') {
        return option
      }
    }
    return null
  }

  function normalizeLeafValue(value: any) {
    if (Array.isArray(value)) {
      return value[value.length - 1] ?? ''
    }
    return value ?? ''
  }

  function findOptionByLeafValue(options: any[], value: any): any {
    const normalizedValue = String(normalizeLeafValue(value))
    for (const option of options || []) {
      if (String(getOptionValue(option)) === normalizedValue) return option
      const child = findOptionByLeafValue(option?.children || [], normalizedValue)
      if (child) return child
    }
    return null
  }

  async function loadStepAssetProducts() {
    stepAsset.loadingProducts = true
    stepAsset.productOptions = []
    stepAsset.product = ''
    stepAsset.moduleOptions = []
    stepAsset.module = ''
    stepAsset.steps = []
    try {
      const res = await getUiPageStepAssetProducts()
      const options = Array.isArray(res.data) ? res.data : []
      stepAsset.productOptions = options
      const currentProduct = findOptionByLeafValue(options, uiProjectProductId.value)
      const firstProduct = currentProduct || findFirstLeafOption(options)
      const productId = getOptionValue(firstProduct)
      if (productId) {
        stepAsset.product = productId
        await onStepAssetProductChange(productId)
      }
    } catch (error) {
      console.log(error)
      stepAsset.productOptions = []
    } finally {
      stepAsset.loadingProducts = false
    }
  }

  async function loadStepAssetModules(productIdValue = stepAsset.product) {
    const productId = normalizeLeafValue(productIdValue)
    stepAsset.loadingModules = true
    stepAsset.moduleOptions = []
    stepAsset.module = ''
    stepAsset.steps = []
    if (!productId || String(productId).startsWith('project:')) {
      stepAsset.loadingModules = false
      return
    }
    try {
      const res = await getUiPageStepAssetModules(productId)
      const options = Array.isArray(res.data) ? res.data : []
      stepAsset.moduleOptions = options
      const currentModule = findOptionByLeafValue(options, uiCaseModuleId.value)
      const selectedModule = currentModule || findFirstLeafOption(options)
      const moduleId = getOptionValue(selectedModule)
      if (moduleId) {
        stepAsset.module = moduleId
        await onStepAssetModuleChange(moduleId)
      }
    } catch (error) {
      console.log(error)
      stepAsset.moduleOptions = []
    } finally {
      stepAsset.loadingModules = false
    }
  }

  async function onStepAssetProductChange(productId: any) {
    const normalizedProductId = normalizeLeafValue(productId)
    stepAsset.product = normalizedProductId
    if (String(normalizedProductId).startsWith('project:')) {
      stepAsset.product = ''
      stepAsset.moduleOptions = []
      stepAsset.module = ''
      stepAsset.steps = []
      return
    }
    await loadStepAssetModules(normalizedProductId)
  }

  async function onStepAssetModuleChange(moduleId: any) {
    const normalizedModuleId = normalizeLeafValue(moduleId)
    stepAsset.module = normalizedModuleId
    stepAsset.steps = []
    if (!normalizedModuleId) return
    stepAsset.loadingSteps = true
    try {
      const res = await getUiPageStepAssetSteps(
        normalizeLeafValue(stepAsset.product),
        normalizedModuleId
      )
      stepAsset.steps = Array.isArray(res.data) ? res.data : []
    } catch (error) {
      console.log(error)
      stepAsset.steps = []
    } finally {
      stepAsset.loadingSteps = false
    }
  }

  function buildCaseStepPayload(step: any) {
    return {
      case: uiCaseId.value,
      module: step.module_id,
      page: step.page_id,
      page_step: getOptionValue(step),
      case_cache_data: [],
      case_cache_ass: [],
      case_sort: data.data.length,
    }
  }

  async function appendCaseStepFromAsset(step: any) {
    if (!uiCaseId.value) return
    const stepId = getOptionValue(step)
    if (!stepId || !step.page_id || !step.module_id) {
      Message.error('页面步骤信息不完整，请刷新后重试')
      return
    }
    if (stepAsset.appendLoading) return
    stepAsset.appendLoading = stepId
    try {
      const res = await postUiCaseStepsDetailed(buildCaseStepPayload(step), uiCaseId.value)
      Message.success(res.msg || '添加步骤成功')
      if (res.data?.id) {
        try {
          await getUiCaseStepsRefreshCacheData(res.data.id)
        } catch (error) {
          console.log(error)
        }
      }
      doRefresh(false)
    } catch (error) {
      console.log(error)
    } finally {
      stepAsset.appendLoading = ''
    }
  }

  function onStepAssetDragStart(event: DragEvent, step: any) {
    stepAsset.draggingStep = step
    event.dataTransfer?.setData('text/plain', String(getOptionValue(step)))
    if (event.dataTransfer) {
      event.dataTransfer.effectAllowed = 'copy'
    }
  }

  function onStepAssetDragEnd() {
    stepAsset.draggingStep = null
    stepAsset.dragOver = false
  }

  function onStepAssetDragOver() {
    if (stepAsset.draggingStep) {
      stepAsset.dragOver = true
    }
  }

  function onStepAssetDragLeave(event: DragEvent) {
    const current = event.currentTarget as HTMLElement | null
    const related = event.relatedTarget as Node | null
    if (current && related && current.contains(related)) return
    stepAsset.dragOver = false
  }

  async function onStepAssetDrop() {
    const step = stepAsset.draggingStep
    stepAsset.draggingStep = null
    try {
      if (step) {
        await appendCaseStepFromAsset(step)
      }
    } finally {
      stepAsset.dragOver = false
    }
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

  function doAppend() {
    modalDialogRef.value?.toggle()
    formItems.forEach((it) => {
      if (it.reset) {
        it.reset()
      } else {
        it.value = ''
      }
    })
  }

  function onDelete(record: any) {
    Modal.confirm({
      title: '提示',
      content: '是否要删除此步骤？',
      cancelText: '取消',
      okText: '删除',
      onBeforeOk: () => {
        return deleteUiCaseStepsDetailed(record.id, record.case.id)
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

  const handleChange = (_data: any) => {
    data.data = _data
    let data1: any = []
    data.data.forEach((item: any, index: number) => {
      data1.push({
        id: item.id,
        case_sort: index,
      })
    })
    putUiCasePutCaseSort(data1)
      .then((res) => {
        Message.success(res.msg)
      })
      .catch(console.log)
  }

  function onCaseStepDragStart(event: DragEvent, index: number) {
    caseStepDragIndex.value = index
    if (event.dataTransfer) {
      event.dataTransfer.effectAllowed = 'move'
      event.dataTransfer.setData('text/plain', String(index))
    }
  }

  function onCaseStepDragEnd() {
    caseStepDragIndex.value = null
  }

  function onCaseStepDrop(targetIndex: number) {
    const sourceIndex = caseStepDragIndex.value
    caseStepDragIndex.value = null
    if (sourceIndex === null || sourceIndex === targetIndex) return
    const nextList = [...data.data]
    const [movedItem] = nextList.splice(sourceIndex, 1)
    if (!movedItem) return
    nextList.splice(targetIndex, 0, movedItem)
    handleChange(nextList)
  }

  function getCaseStepPath(record: any) {
    const pageStep = record?.page_step || {}
    const projectProduct = pageStep.project_product || {}
    const values = [
      projectProduct.project?.name,
      projectProduct.name,
      pageStep.module?.name,
      pageStep.page?.name,
    ].filter((item) => item !== null && item !== undefined && item !== '')
    return values.length ? values.join(' / ') : '暂无页面层级信息'
  }

  function onRetryEditorVisibleChange(visible: boolean, record: any) {
    if (visible) {
      retryEditor.recordId = String(record.id)
      retryEditor.value = Number(record.error_retry ?? 0)
    } else if (
      retryEditor.recordId === String(record.id) &&
      retryEditor.savingId !== String(record.id)
    ) {
      retryEditor.recordId = ''
    }
  }

  function closeRetryEditor(record: any) {
    if (retryEditor.savingId === String(record.id)) return
    retryEditor.recordId = ''
  }

  async function saveCaseStepRetry(record: any) {
    const recordId = String(record.id)
    const retryCount = Number(retryEditor.value)
    if (!Number.isInteger(retryCount) || retryCount < 0) {
      Message.error('失败重试次数请输入大于或等于 0 的整数')
      return
    }
    if (retryEditor.savingId) return
    retryEditor.savingId = recordId
    try {
      const res = await putUiCaseStepsDetailed(
        {
          id: record.id,
          error_retry: retryCount,
        },
        uiCaseId.value
      )
      record.error_retry = retryCount
      if (String(data.selectData?.id) === recordId) {
        data.selectData.error_retry = retryCount
      }
      Message.success(res.msg || '重试次数保存成功')
      retryEditor.recordId = ''
    } catch (error) {
      console.log(error)
    } finally {
      retryEditor.savingId = ''
    }
  }

  function onDataForm() {
    if (formItems.every((it: any) => (it.validator ? it.validator() : true))) {
      if (!uiCaseId.value) return
      let value = getFormItems(formItems)
      if (data.isAdd) {
        value['case'] = uiCaseId.value
        value['case_cache_data'] = []
        value['case_cache_ass'] = []
        value['case_sort'] = data.data.length
        postUiCaseStepsDetailed(value, uiCaseId.value)
          .then((res) => {
            modalDialogRef.value?.toggle()
            Message.success(res.msg)
            getUiCaseStepsRefreshCacheData(res.data.id)
              .then((res) => {
                Message.success(res.msg)
                doRefresh()
              })
              .catch(console.log)
          })
          .catch((error) => {
            console.log(error)
          })
          .finally(() => {
            modalDialogRef.value?.setConfirmLoading(false)
          })
      } else {
        value['id'] = data.updateId
        putUiCaseStepsDetailed(value, uiCaseId.value)
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

  function doResetSearch() {
    if (props.embedded) {
      emit('close')
      return
    }
    window.history.back()
  }

  function normalizeCaseRecord(record: any) {
    return {
      ...defaultCaseRecord(),
      ...(record || {}),
      front_custom: Array.isArray(record?.front_custom) ? record.front_custom : [],
      front_sql: Array.isArray(record?.front_sql) ? record.front_sql : [],
      front_public: Array.isArray(record?.front_public) ? record.front_public : [],
      front_auth_config: Array.isArray(record?.front_auth_config) ? record.front_auth_config : [],
      posterior_sql: Array.isArray(record?.posterior_sql) ? record.posterior_sql : [],
    }
  }

  function loadCaseGlobalOptions(project_product_id: any) {
    if (!project_product_id) return
    const params = {
      page: 1,
      pageSize: 10000,
      project_product_id,
    }
    getUiPublic(params)
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
      })
      .catch(console.log)
    getUiAuthConfig(params)
      .then((res) => {
        data.authConfigOptions = (res.data || []).map((item: any) => ({
          value: item.id,
          name: item.name || `授权配置 ${item.id}`,
          authType: item.auth_type,
          authTypeText: getEnumTitle(enumStore.ui_auth_type, item.auth_type),
          testEnv: item.test_env,
          isCommonEnv:
            item.test_env === null || item.test_env === undefined || item.test_env === '',
          envText: formatEnvironmentText(item.test_env),
          statusText: formatDefaultStatusText(item.status),
          disabled: Number(item.status) === 1,
        }))
      })
      .catch(console.log)
  }

  async function ensureCaseRecord() {
    const caseId = uiCaseId.value
    if (!caseId) return
    if (pageData.record?.id && String(pageData.record.id) === String(caseId)) {
      pageData.setRecord(normalizeCaseRecord(pageData.record))
      return
    }
    const res = await getUiCase({ id: caseId, page: 1, pageSize: 1 })
    const record = (res.data || [])[0]
    pageData.setRecord(normalizeCaseRecord(record || { id: caseId }))
  }

  const UI_RESULT_SOCKET_EVENTS = new Set([
    'u_page_steps',
    'u_page_step_node_progress',
    'u_test_case',
    'u_test_suite_details',
  ])
  let websocketRefreshTimer: number | null = null
  let caseLiveCloseTimer: number | null = null
  let caseLiveReadyNotified = false
  let caseStepsRefreshRequestId = 0

  function clearCaseLiveCloseTimer() {
    if (!caseLiveCloseTimer) return
    window.clearTimeout(caseLiveCloseTimer)
    caseLiveCloseTimer = null
  }

  async function loadCaseActuatorOptions(showMessage = false) {
    caseActuatorLoading.value = true
    try {
      const res = await getSystemSocketCurrentActuatorStatus()
      const options = Array.isArray(res.data?.available_actuators)
        ? res.data.available_actuators.filter((item: any) => item.web_live_stream_supported)
        : []
      caseActuatorOptions.value = options
      const selectedAvailable = options.some(
        (item: any) => item.username === selectedCaseActuatorUsername.value
      )
      if (!selectedAvailable) {
        const defaultActuator = options.find((item: any) => item.is_owner) || options[0]
        selectedCaseActuatorUsername.value = defaultActuator?.username || ''
      }
      if (showMessage) {
        if (options.length) Message.success('执行器列表已刷新')
        else Message.warning('暂无支持 Web 直播的在线执行器')
      }
    } catch (error) {
      console.log(error)
      caseActuatorOptions.value = []
      selectedCaseActuatorUsername.value = ''
    } finally {
      caseActuatorLoading.value = false
    }
  }

  async function openCaseLiveStream() {
    if (caseLiveOpening.value) return
    caseLiveOpening.value = true
    const startedAt = Date.now()
    clearCaseLiveCloseTimer()
    caseLiveReadyNotified = false
    try {
      liveStreamVisible.value = true
      await loadCaseActuatorOptions()
      if (selectedCaseActuatorUsername.value) {
        Message.success('执行器连接创建完成，点击页面顶部“执行”后开始直播')
      }
      await nextTick()
      caseLiveSectionRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    } finally {
      await waitForMinimumLoading(startedAt)
      caseLiveOpening.value = false
    }
  }

  function toggleCaseLiveStream() {
    if (caseLiveOpening.value) return
    if (liveStreamVisible.value) closeCaseLiveStream()
    else void openCaseLiveStream()
  }

  function handleCaseActuatorChange(username: string) {
    if (!username) return
    Message.success('执行器连接创建完成，点击页面顶部“执行”后开始直播')
  }

  function closeCaseLiveStream() {
    clearCaseLiveCloseTimer()
    liveStreamVisible.value = false
    if (!caseExecutionActive.value) {
      caseLiveExecutionId.value = ''
      caseLiveActuatorUsername.value = ''
      caseLiveReadyNotified = false
    }
  }

  function handleCaseLiveReady() {
    if (caseLiveReadyNotified) return
    caseLiveReadyNotified = true
    Message.success('实时画面连接成功，正在展示执行过程')
  }

  function scheduleCaseLiveAutoClose() {
    clearCaseLiveCloseTimer()
    if (!liveStreamVisible.value) return
    // 执行器在 Case 结束时已经保留画面 5 秒；任务终态到达前推流已正常停止，
    // 前端此时应立即收起，避免再等 5 秒并把正常停流误报为“连接异常”。
    closeCaseLiveStream()
    Message.success('Case 执行完成，实时画面已自动收起')
  }

  function mergeActiveCaseStepList(list: any[]) {
    const currentById = new Map(
      data.data.map((item: any) => [String(item.id), item])
    )
    return list.map((item: any) => {
      const current = currentById.get(String(item.id))
      if (!current) return item
      const currentStatus = Number(current.status)
      const incomingStatus = Number(item.status)
      let status = 2
      if ([0, 1].includes(currentStatus)) status = currentStatus
      else if (currentStatus === 3 && [0, 1].includes(incomingStatus)) status = incomingStatus
      else if (currentStatus === 3 || incomingStatus === 3) status = 3
      return {
        ...item,
        status,
        error_message:
          currentStatus === 3 && [0, 1].includes(incomingStatus) && item.error_message
            ? item.error_message
            : current.error_message || item.error_message,
      }
    })
  }

  function doRefresh(showLoading = true) {
    if (!uiCaseId.value) return
    const requestId = ++caseStepsRefreshRequestId
    clearPollingTimer()
    if (showLoading) {
      stepTableLoading.value = true
    }
    refreshCaseRecord()

    getUiCaseStepsDetailed(uiCaseId.value)
      .then((res) => {
        if (requestId !== caseStepsRefreshRequestId) return
        const list = Array.isArray(res.data) ? res.data : []
        const displayList = caseExecutionActive.value ? mergeActiveCaseStepList(list) : list
        data.data = displayList

        const selectedId = data.selectData?.id
        const selectedItem = selectedId
          ? displayList.find((item: any) => item.id === selectedId)
          : null
        data.selectData = selectedItem || displayList[0] || {}

        const hasRunningItem = displayList.some((item: any) => item.status === 3)

        if (hasRunningItem) {
          // 5秒后再次刷新
          pollingTimer.value = setInterval(() => {
            doRefresh()
          }, 5000)
        } else if (latestUiCaseResultPending.value) {
          loadLatestUiCaseExecutionResult().finally(() => {
            latestUiCaseResultPending.value = false
          })
        }
      })
      .catch(console.log)
      .finally(() => {
        if (requestId === caseStepsRefreshRequestId) {
          stepTableLoading.value = false
        }
      })
  }

  function handleWebsocketMessage(event: Event) {
    const message = (event as CustomEvent).detail
    const funcName = message?.data?.func_name
    if (!UI_RESULT_SOCKET_EVENTS.has(funcName)) {
      return
    }
    const funcArgs = message?.data?.func_args
    const currentCaseId = uiCaseId.value
    if (!currentCaseId) {
      return
    }
    if (funcName === 'u_page_steps' || funcName === 'u_page_step_node_progress') {
      const detailId = funcArgs?.case_step_details_id
      if (
        caseExecutionId.value &&
        funcArgs?.execution_id &&
        String(funcArgs.execution_id) !== caseExecutionId.value
      ) {
        return
      }
      const hasCurrentDetail =
        detailId && data.data.some((item: any) => String(item.id) === String(detailId))
      if (detailId && data.data.length && !hasCurrentDetail) {
        return
      }
      if (funcName === 'u_page_step_node_progress') {
        applyCaseNodeProgress(funcArgs)
      } else {
        applyCaseStepProgress(funcArgs)
      }
    } else {
      if (String(funcArgs?.id || '') !== String(currentCaseId)) return
      if (
        caseExecutionId.value &&
        funcArgs?.execution_id &&
        String(funcArgs.execution_id) !== caseExecutionId.value
      ) {
        return
      }
      if (funcName === 'u_test_case') {
        applyCaseFinalResult(funcArgs)
      }
    }
    if (
      funcName === 'u_test_case' &&
      caseLiveExecutionId.value &&
      String(funcArgs?.execution_id || '') === String(caseLiveExecutionId.value)
    ) {
      caseExecutionActive.value = false
      scheduleCaseLiveAutoClose()
    }
    if (websocketRefreshTimer) {
      window.clearTimeout(websocketRefreshTimer)
    }
    websocketRefreshTimer = window.setTimeout(() => {
      doRefresh(false)
      websocketRefreshTimer = null
    }, 500)
  }

  function applyCaseStepProgress(stepResult: any) {
    if (!stepResult?.case_step_details_id) return
    const displayStepResult = withActiveCaseNode(stepResult)
    const currentResult = latestUiCaseResult.value || {
      id: uiCaseId.value,
      execution_id: stepResult.execution_id || caseExecutionId.value,
      status: 3,
      steps: [],
    }
    const steps = Array.isArray(currentResult.steps) ? [...currentResult.steps] : []
    const index = steps.findIndex(
      (item: any) =>
        String(item?.case_step_details_id) === String(displayStepResult.case_step_details_id)
    )
    if (index >= 0) {
      steps[index] = displayStepResult
    } else {
      steps.push(displayStepResult)
    }
    latestUiCaseResult.value = {
      ...currentResult,
      status: displayStepResult.is_final && displayStepResult.status === 0 ? 0 : 3,
      steps,
    }
    data.data = data.data.map((item: any) =>
      String(item.id) === String(stepResult.case_step_details_id)
        ? {
            ...item,
            status: stepResult.is_final ? stepResult.status : 3,
            error_message: stepResult.error_message,
          }
        : item
    )
  }

  function withActiveCaseNode(stepResult: any) {
    const elementResults = Array.isArray(stepResult?.element_result_list)
      ? stepResult.element_result_list.filter((item: any) => !item?.runtime_pending)
      : []
    if (stepResult?.is_final || !elementResults.length) {
      return { ...stepResult, element_result_list: elementResults }
    }
    const lastResult = elementResults[elementResults.length - 1]
    if (lastResult?.status === 0 || !lastResult?.next_node_id) {
      return { ...stepResult, element_result_list: elementResults }
    }
    const hasNextResult = elementResults.some(
      (item: any) => String(item?.id) === String(lastResult.next_node_id)
    )
    return {
      ...stepResult,
      element_result_list: hasNextResult
        ? elementResults
        : [
            ...elementResults,
            {
              id: lastResult.next_node_id,
              status: 3,
              runtime_pending: true,
            },
          ],
    }
  }

  function applyCaseNodeProgress(progress: any) {
    const detailId = progress?.case_step_details_id
    const elementResult = progress?.element_result
    if (!detailId || !elementResult) return
    const existingStep = (
      Array.isArray(latestUiCaseResult.value?.steps) ? latestUiCaseResult.value.steps : []
    ).find((item: any) => String(item?.case_step_details_id) === String(detailId))
    const elementResults = Array.isArray(existingStep?.element_result_list)
      ? existingStep.element_result_list.filter((item: any) => !item?.runtime_pending)
      : []
    const previousIndex = elementResults.findIndex(
      (item: any) => String(item?.id) === String(elementResult.id)
    )
    if (previousIndex >= 0) {
      elementResults[previousIndex] = elementResult
    } else {
      elementResults.push(elementResult)
    }
    applyCaseStepProgress({
      ...(existingStep || {}),
      execution_id: progress.execution_id,
      id: progress.id,
      case_step_details_id: detailId,
      status: 3,
      is_final: false,
      element_result_list: elementResults,
    })
  }

  function applyCaseFinalResult(result: any) {
    latestUiCaseResult.value = result
    latestUiCaseResultPending.value = false
    const stepStatus = new Map(
      (Array.isArray(result?.steps) ? result.steps : [])
        .filter((item: any) => item?.case_step_details_id)
        .map((item: any): [string, any] => [String(item.case_step_details_id), item])
    )
    data.data = data.data.map((item: any) => {
      const runtimeStep: any = stepStatus.get(String(item.id))
      return runtimeStep
        ? {
            ...item,
            status: runtimeStep.status,
            error_message: runtimeStep.error_message,
          }
        : {
            ...item,
            status: 2,
            error_message: null,
          }
    })
    const selectedId = data.selectData?.id
    if (selectedId) {
      data.selectData =
        data.data.find((item: any) => String(item.id) === String(selectedId)) || data.selectData
    }
  }

  function resetCaseRuntimeState() {
    latestUiCaseResult.value = null
    latestUiCaseResultPending.value = true
    data.data = data.data.map((item: any) => ({
      ...item,
      status: 2,
      error_message: null,
    }))
    const selectedId = data.selectData?.id
    if (selectedId) {
      data.selectData =
        data.data.find((item: any) => String(item.id) === String(selectedId)) || data.selectData
    }
  }

  function refreshCaseRecord() {
    getUiCase({ id: uiCaseId.value, page: 1, pageSize: 1 })
      .then((res) => {
        const record = (res.data || [])[0]
        if (record) {
          pageData.setRecord(normalizeCaseRecord(record))
        }
      })
      .catch(console.log)
  }

  function oeFreshSteps(record: any) {
    Modal.confirm({
      title: '同步页面步骤',
      content: '仅同步当前页面步骤中发生变化的节点，未变化节点及其 Case 入参会保留。是否继续？',
      cancelText: '取消',
      okText: '同步',
      onBeforeOk: () => {
        return getUiCaseStepsRefreshCacheData(record.id)
          .then((res) => {
            const summary = res.data?.updated?.[0]
            const details = summary
              ? `新增 ${summary.added_count || 0}，更新 ${summary.updated_count || 0}，删除 ${summary.removed_count || 0}，保留 ${
                  (summary.unchanged_count || 0) + (summary.initialized_count || 0)
                }`
              : ''
            Message.success(details ? `同步完成：${details}` : res.msg)
            caseCanvasRefreshStamp.value += 1
            doRefresh()
          })
          .catch(console.log)
      },
    })
  }

  function doUiPageNameAll(moduleId: number) {
    getUiPageName(moduleId)
      .then((res) => {
        data.pageName = res.data
      })
      .catch(console.log)
  }

  function doUiStepsPageStepsName(pageId: number) {
    getUiStepsPageStepsName(pageId)
      .then((res) => {
        data.pageStepsName = res.data
      })
      .catch(console.log)
  }

  function loadDatasourceAliases() {
    if (!uiProjectProductId.value) return
    getDataFactoryDatasourceAlias({
      project_product: uiProjectProductId.value,
      status: 1,
    })
      .then((res) => {
        data.datasourceAliasOptions = (res.data || []).map((item: any) => ({
          label: item.name,
          value: item.id,
          dbType: Number(item.db_type),
        }))
      })
      .catch(console.log)
  }

  const sqlAssertionDatasourceOptions = computed(() =>
    data.datasourceAliasOptions.filter((item: any) => [0, 1, 2].includes(Number(item.dbType)))
  )

  function getStepTypeLabel(type: any) {
    return enumStore.element_ope[type]?.title || '未知类型'
  }

  function getStepTypeColor(type: any) {
    const typeColorMap: Record<number, string> = {
      0: 'var(--m-node-element)',
      1: 'var(--m-node-assertion)',
      2: 'var(--m-node-sql)',
      3: 'var(--m-node-custom)',
      4: 'var(--m-node-condition)',
      5: 'var(--m-node-python)',
      6: 'var(--m-node-wait)',
    }
    return typeColorMap[Number(type)] || 'var(--m-muted)'
  }

  function getCaseStepList() {
    return Array.isArray(data.selectData?.case_data) ? data.selectData.case_data : []
  }

  function getStepKey(item: any, index: number) {
    return String(item?.page_step_details_id || item?.id || index)
  }

  function getStepMethodLabel(opeKey: any) {
    if (!opeKey) return '-'
    return useSelectValue.findItemByValue(opeKey)?.label || opeKey
  }

  function getStepParams(item: any) {
    return Array.isArray(item?.page_step_details_data) ? item.page_step_details_data : []
  }

  function getVisibleStepParams(item: any) {
    const params = getStepParams(item)
    if (item?.type === 0) {
      return params.filter((param: any) => param?.d)
    }
    if (item?.type === 1) {
      return params.filter((param: any) => param?.f !== 'actual')
    }
    if (item?.type === 4) {
      return []
    }
    return params
  }

  function getStepParamCount(item: any) {
    return getVisibleStepParams(item).length
  }

  function stringifyStepValue(value: any) {
    if (value === undefined || value === null || value === '') return '-'
    if (Array.isArray(value)) return value.join(', ')
    if (typeof value === 'object') return JSON.stringify(value)
    return String(value)
  }

  function getStepParamLabel(param: any, index: number) {
    return param?.n || param?.key || param?.f || param?.name || `参数${index + 1}`
  }

  function getStepParamValue(param: any) {
    return stringifyStepValue(
      param?.v ?? param?.value ?? param?.sql ?? param?.key_list ?? param?.func ?? param?.expect
    )
  }

  function getStepParamSummary(item: any) {
    return getVisibleStepParams(item)
      .map((param: any, index: number) => ({
        key: `${item?.page_step_details_id || 'step'}-${index}`,
        label: getStepParamLabel(param, index),
        value: getStepParamValue(param),
      }))
      .filter((param: any) => param.value !== '-')
      .slice(0, 4)
  }

  function getStepHeaderParamSummary(item: any) {
    const summary = getStepParamSummary(item)
      .slice(0, 2)
      .map((param: any) => `${param.label}=${param.value}`)
      .join('，')
    return summary.length > 48 ? `${summary.slice(0, 48)}...` : summary
  }

  function getConditionSummary(conditionValue: any) {
    if (!conditionValue) return '-'
    if (typeof conditionValue === 'string') return conditionValue
    return stringifyStepValue(conditionValue.expect ?? conditionValue.value ?? conditionValue)
  }

  function getStepResult(item: any, index: number) {
    const detailId = item?.page_step_details_id
    return (
      selectedResultSteps.value.find(
        (result: any) => detailId && String(result?.id) === String(detailId)
      ) ||
      selectedResultSteps.value[index] ||
      null
    )
  }

  function getStepResultStatusText(result: any) {
    if (!result) return '未测试'
    if (result.status === 1) return '通过'
    if (result.status === 0) return '失败'
    if (result.status === 3) return '执行中'
    return '未测试'
  }

  function getStepResultColor(result: any) {
    if (!result) return 'gray'
    if (result.status === 1) return 'green'
    if (result.status === 0) return 'red'
    if (result.status === 3) return 'arcoblue'
    return 'gray'
  }

  function getStepResultSummary(result: any) {
    if (!result) return '暂无最近执行结果'
    if (result.error_message) return result.error_message
    const count = getElementRows(result).length
    const matchedCount = getResultMatchedCount(result)
    if (count) return `元素 ${count} 项，匹配 ${matchedCount}`
    return '已记录执行结果'
  }

  function getResultMatchedCount(result: any) {
    return getElementRows(result).reduce((total: number, element: any) => {
      const count = Number(element?.ele_quantity)
      return total + (Number.isFinite(count) ? count : 0)
    }, 0)
  }

  function getElementRows(result: any) {
    if (Array.isArray(result?.elements) && result.elements.length) return result.elements
    if (result?.ele_name) return [result.ele_name]
    if (result?.loc) {
      return [
        {
          name: result.name,
          exp: result.exp,
          loc: result.loc,
          sub: result.sub,
          ele_quantity: result.ele_quantity,
          element_text: result.element_text,
        },
      ]
    }
    return []
  }

  async function openElementEditPanel(item: any) {
    if (!item?.page_step_details_id) {
      Message.error('未找到页面步骤明细ID')
      return
    }
    elementEditLoading.value = true
    try {
      const res = await getUiPageStepsDetailedById(item.page_step_details_id)
      const detail = (res.data || [])[0]
      const element = detail?.ele_name
      if (!element?.id) {
        Message.error('当前步骤没有绑定可编辑元素')
        return
      }
      elementEditPanelRef.value?.openEdit(element)
    } catch (error) {
      console.log(error)
      Message.error('元素信息获取失败')
    } finally {
      elementEditLoading.value = false
    }
  }

  const runCaseWithActuator = async (actuatorUsername?: string, withLive = false) => {
    if (withLive) {
      clearCaseLiveCloseTimer()
      caseLiveExecutionId.value = ''
      caseLiveActuatorUsername.value = actuatorUsername || ''
    }
    const res = await getUiCaseRun(uiCaseId.value, userStore.selected_environment, actuatorUsername)
    resetCaseRuntimeState()
    caseExecutionActive.value = true
    caseExecutionId.value = String(res.data?.execution_id || '')
    caseExecutorTaskId.value = String(res.data?.task_id || '')
    if (caseExecutorTaskId.value) {
      saveExecutorTaskObservation('ui-case-run', uiCaseId.value, {
        taskId: caseExecutorTaskId.value,
        businessType: 'u_case',
      })
      caseExecutionActive.value = true
      scheduleCaseExecutorTaskPoll(0)
    }
    if (withLive) {
      caseLiveExecutionId.value = res.data?.execution_id || ''
    }
    if (withLive && caseLiveExecutionId.value) {
      caseExecutionActive.value = true
      caseLiveReadyNotified = false
    }
    Message.loading(res.msg)
  }

  function clearCaseExecutorTaskPoll() {
    if (caseExecutorTaskTimer) {
      window.clearTimeout(caseExecutorTaskTimer)
      caseExecutorTaskTimer = null
    }
  }

  function scheduleCaseExecutorTaskPoll(delay = 1000) {
    clearCaseExecutorTaskPoll()
    if (!caseExecutorTaskId.value) return
    caseExecutorTaskTimer = window.setTimeout(() => void pollCaseExecutorTask(), delay)
  }

  function notifyCaseTaskTerminal(taskId: string, task: any) {
    if (!taskId || lastNotifiedCaseTaskId === taskId) return
    lastNotifiedCaseTaskId = taskId
    if (!claimExecutorTaskNotification(taskId)) return
    const caseName = pageData.record?.name || `用例 ${uiCaseId.value}`
    if (task.status === 'success') {
      Notification.success({
        title: 'Case 执行完成',
        content: `「${caseName}」已执行成功`,
        duration: 5000,
        closable: true,
      })
      return
    }
    if (task.status === 'cancelled') {
      Notification.warning({
        title: 'Case 执行已取消',
        content: `「${caseName}」已停止执行`,
        duration: 5000,
        closable: true,
      })
      return
    }
    Notification.error({
      title: task.status === 'timeout' ? 'Case 执行超时' : 'Case 执行失败',
      content: task.error_message || `「${caseName}」执行未通过，请查看执行结果`,
      duration: 8000,
      closable: true,
    })
  }

  async function pollCaseExecutorTask() {
    if (!caseExecutorTaskId.value) return
    try {
      const res = await getExecutorTask(caseExecutorTaskId.value)
      const task = res.data || {}
      if (!task.terminal) {
        scheduleCaseExecutorTaskPoll()
        return
      }
      clearCaseExecutorTaskPoll()
      const finishedTaskId = caseExecutorTaskId.value
      notifyCaseTaskTerminal(finishedTaskId, task)
      if (task.result?.id) {
        applyCaseFinalResult(task.result)
      } else if (task.status !== 'success') {
        Message.error(task.error_message || 'UI 用例执行失败')
      }
      caseExecutionActive.value = false
      latestUiCaseResultPending.value = true
      doRefresh(false)
      if (liveStreamVisible.value) scheduleCaseLiveAutoClose()
      caseExecutorTaskId.value = ''
      clearExecutorTaskObservation('ui-case-run', uiCaseId.value, finishedTaskId)
    } catch (error) {
      console.log(error)
      scheduleCaseExecutorTaskPoll(1500)
    }
  }

  async function resumeActiveCaseTask() {
    if (!uiCaseId.value || caseExecutorTaskId.value) return
    try {
      const observation = loadExecutorTaskObservation('ui-case-run', uiCaseId.value)
      if (observation?.taskId) {
        caseExecutorTaskId.value = String(observation.taskId)
        caseExecutionActive.value = true
        scheduleCaseExecutorTaskPoll(0)
        return
      }
      const res = await getActiveExecutorTasks({
        business_type: 'u_case',
        business_id: uiCaseId.value,
      })
      const task = (res.data || [])[0]
      if (!task?.task_id) return
      caseExecutorTaskId.value = String(task.task_id)
      saveExecutorTaskObservation('ui-case-run', uiCaseId.value, {
        taskId: caseExecutorTaskId.value,
        businessType: 'u_case',
      })
      caseExecutionActive.value = true
      scheduleCaseExecutorTaskPoll(0)
    } catch (error) {
      console.log(error)
    }
  }

  async function loadLatestUiCaseExecutionResult(enforceCurrentExecution = true) {
    if (!uiCaseId.value) return
    const res = await getExecutionResultLatestResolved({
      source_type: 'page',
      target_type: 'ui_case',
      target_id: uiCaseId.value,
      test_env: userStore.selected_environment,
      page: 1,
      pageSize: 1,
    })
    const result = res.data?.result_data || null
    if (
      enforceCurrentExecution &&
      caseExecutionId.value &&
      result?.execution_id &&
      String(result.execution_id) !== caseExecutionId.value
    ) {
      return null
    }
    latestUiCaseResult.value = result
    return result
  }

  const onCaseRun = async (withLive = false) => {
    if (userStore.selected_environment == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    if (caseRunning.value) return
    caseRunning.value = true
    try {
      const useLiveWorkbench = withLive || liveStreamVisible.value
      if (useLiveWorkbench && !selectedCaseActuatorUsername.value) {
        await loadCaseActuatorOptions()
      }
      if (useLiveWorkbench && !selectedCaseActuatorUsername.value) {
        Message.error('请选择支持 Web 直播的在线执行器')
        return
      }
      await runCaseWithActuator(
        useLiveWorkbench ? selectedCaseActuatorUsername.value : undefined,
        useLiveWorkbench
      )
    } catch (e) {
      console.log(e)
      caseExecutionActive.value = false
    } finally {
      caseRunning.value = false
      doRefresh()
    }
  }

  function select(record: any) {
    data.selectData = record
  }

  function handleCaseNodeInputsSaved(caseData: any[]) {
    data.data = data.data.map((item: any) =>
      String(item.id) === String(data.selectData?.id) ? { ...item, case_data: caseData } : item
    )
    data.selectData = {
      ...data.selectData,
      case_data: caseData,
    }
  }

  function onUpdate1(item: any) {
    data.actionTitle = '编辑'
    data.isAdd = false
    data.updateId = item.id
    modalDialogRef.value?.toggle()
    nextTick(() => {
      formItems.forEach((it) => {
        const propName = item[it.key]
        if (it.key === 'module') {
          it.value = item.page_step.module
          doUiPageNameAll(item.page_step.module)
        } else if (it.key === 'page') {
          it.value = item.page_step.page
          doUiStepsPageStepsName(item.page_step.page)
        } else if (it.key === 'page_step') {
          it.value = item.page_step.id
        } else {
          it.value = propName
        }
      })
    })
  }

  function onUpdate() {
    if (detailSaving.value) return
    detailSaving.value = true
    putUiCaseStepsDetailed(
      {
        id: data.selectData.id,
        case_data: data.selectData.case_data,
      },
      uiCaseId.value
    )
      .then((res) => {
        Message.success(res.msg)
      })
      .catch(console.log)
      .finally(() => {
        detailSaving.value = false
      })
  }

  const onPageStep = async (record) => {
    if (userStore.selected_environment == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    if (caseRunning.value) return
    caseRunning.value = true
    try {
      const res = await getUiStepsTest(record.page_step.id, userStore.selected_environment)
      Message.loading(res.msg)
    } catch (e) {
    } finally {
      caseRunning.value = false
      doRefresh()
    }
  }

  function getPageStepId(record: any) {
    const pageStep = record?.page_step
    return pageStep?.id || pageStep || ''
  }

  function getPageId(record: any) {
    const page = record?.page_step?.page
    return page?.id || page || ''
  }

  async function getFullPageStep(record: any) {
    const pageStepId = getPageStepId(record)
    if (!pageStepId) return null
    const pageStep = record?.page_step
    if (pageStep?.page?.id && pageStep?.project_product?.ui_client_type !== undefined) {
      return pageStep
    }
    const res = await getUiSteps({ id: pageStepId })
    return res.data?.[0] || pageStep || { id: pageStepId }
  }

  async function openPageStepDetail(record: any) {
    const pageStepId = getPageStepId(record)
    if (!pageStepId) {
      Message.error('未找到页面步骤ID')
      return
    }
    try {
      const pageStep = await getFullPageStep(record)
      const pageId = pageStep?.page?.id || pageStep?.page || ''
      const pageType = pageStep?.project_product?.ui_client_type ?? ''
      pageStepDetailPanel.pageStepsId = String(pageStepId)
      pageStepDetailPanel.pageId = pageId ? String(pageId) : ''
      pageStepDetailPanel.pageType = pageType !== '' && pageType !== null ? String(pageType) : ''
      pageStepDetailPanel.visible = true
    } catch (error) {
      console.log(error)
      Message.error('页面步骤信息获取失败')
    }
  }

  function onModifyStatus(newValue: any, id: number, key: string) {
    let obj: any = {
      id: id,
    }
    if (key) {
      obj[key] = newValue ? 1 : 0
    }
    return new Promise<any>((resolve, reject) => {
      setTimeout(async () => {
        try {
          let value: any = false
          await putUiCaseStepsDetailed(obj, uiCaseId.value)
            .then((res) => {
              Message.success(res.msg)
              value = res.code === 200
            })
            .catch(reject)
          resolve(value)
        } catch (error) {
          reject(error)
        }
      }, 300)
    })
  }

  onMounted(() => {
    window.addEventListener('mango:websocket-message', handleWebsocketMessage)
    nextTick(async () => {
      await ensureCaseRecord()
      void Promise.all([doRefresh(), loadCaseDataFactoryCount()]).then(() => resumeActiveCaseTask())
      useSelectValue.getSelectValue()
      loadDatasourceAliases()
      loadCaseGlobalOptions(uiProjectProductId.value)
      loadLatestUiCaseExecutionResult(false).catch((error) => {
        console.log(error)
      })
    })
  })
  onUnmounted(() => {
    window.removeEventListener('mango:websocket-message', handleWebsocketMessage)
    if (websocketRefreshTimer) {
      window.clearTimeout(websocketRefreshTimer)
      websocketRefreshTimer = null
    }
    clearCaseLiveCloseTimer()
    clearCaseExecutorTaskPoll()
    clearPollingTimer()
  })
</script>

<style scoped>
  .ui-case-step-card__retry-input {
    width: 128px;
  }

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

  .ui-case-step-card__retry-trigger {
    padding: 0 4px;
    color: var(--m-text-2);
    font-size: 12px;
  }

  .ui-case-step-card__retry-editor {
    display: flex;
    min-width: 190px;
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
    color: var(--m-text);
    font-size: 12px;
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
