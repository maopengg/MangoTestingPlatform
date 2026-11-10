<template>
  <div class="case-version-snapshot">
    <section class="case-version-snapshot-panel">
      <header class="case-version-snapshot-head">
        <div>
          <strong>用例编排</strong>
          <span>前置准备、执行编排和后置清理配置</span>
        </div>
        <a-space :size="6">
          <a-tag size="small" color="arcoblue">版本快照</a-tag>
          <a-tag size="small">只读</a-tag>
          <a-tag size="small" color="arcoblue">{{ steps.length }} 个步骤</a-tag>
        </a-space>
      </header>

      <a-tabs v-model:active-key="caseTab" class="case-version-snapshot-tabs">
        <a-tab-pane
          key="front"
          title="前置准备"
          data-testid="qa-views-apitest-case-details-components-apicaseversionsnapshot-tab-pane-前置准备"
        >
          <a-tabs position="left" class="snapshot-left-tabs">
            <a-tab-pane
              key="public"
              title="全局变量"
              data-testid="qa-views-apitest-case-details-components-apicaseversionsnapshot-tab-pane-全局变量"
            >
              <SnapshotSectionList :sections="frontPublicSections" empty-text="暂无全局变量配置" />
            </a-tab-pane>
            <a-tab-pane
              key="auth"
              title="授权管理"
              data-testid="qa-views-apitest-case-details-components-apicaseversionsnapshot-tab-pane-授权管理"
            >
              <SnapshotSectionList :sections="frontAuthSections" empty-text="暂无授权配置" />
            </a-tab-pane>
            <a-tab-pane
              key="gray"
              title="灰度配置"
              data-testid="qa-views-apitest-case-details-components-apicaseversionsnapshot-tab-pane-灰度配置"
            >
              <SnapshotSectionList :sections="caseGraySections" empty-text="暂无灰度配置" />
            </a-tab-pane>
            <a-tab-pane
              key="custom"
              title="自定义变量"
              data-testid="qa-views-apitest-case-details-components-apicaseversionsnapshot-tab-pane-自定义变量"
            >
              <SnapshotSectionList :sections="frontCustomSections" empty-text="暂无自定义变量" />
            </a-tab-pane>
            <a-tab-pane
              key="sql"
              title="SQL变量"
              data-testid="qa-views-apitest-case-details-components-apicaseversionsnapshot-tab-pane-sql变量"
            >
              <SnapshotSectionList :sections="frontSqlSections" empty-text="暂无前置 SQL" />
            </a-tab-pane>
            <a-tab-pane
              key="factory"
              title="数据工厂"
              data-testid="qa-views-apitest-case-details-components-apicaseversionsnapshot-tab-pane-数据工厂"
            >
              <SnapshotSectionList :sections="caseFactorySections" empty-text="暂无数据工厂绑定" />
            </a-tab-pane>
            <a-tab-pane
              key="headers"
              title="默认请求头"
              data-testid="qa-views-apitest-case-details-components-apicaseversionsnapshot-tab-pane-默认请求头"
            >
              <SnapshotSectionList :sections="frontHeaderSections" empty-text="暂无默认请求头" />
            </a-tab-pane>
          </a-tabs>
        </a-tab-pane>

        <a-tab-pane
          key="steps"
          title="执行编排"
          data-testid="qa-views-apitest-case-details-components-apicaseversionsnapshot-tab-pane-执行编排"
        >
          <a-table
            class="snapshot-step-table"
            :bordered="false"
            :data="steps"
            :pagination="false"
            :scroll="{ x: 470 }"
            row-key="logical_id"
            @row-click="selectStep"
          >
            <template #columns>
              <a-table-column title="接口名称" :width="220">
                <template #cell="{ record, rowIndex }">
                  <div
                    class="snapshot-table-api"
                    :class="{ 'snapshot-table-api--active': selectedStep === record }"
                  >
                    <span class="snapshot-step-order">{{ rowIndex + 1 }}</span>
                    <span>
                      <strong>{{ stepName(record) }}</strong>
                      <a-tag v-if="record.execution_config?.is_recovery" size="small">恢复</a-tag>
                      <small>修订 {{ displayValue(record.api_info_revision_id) }}</small>
                    </span>
                  </div>
                </template>
              </a-table-column>
              <a-table-column title="测试结果" :width="100" align="center">
                <template #cell><a-tag size="small">版本快照</a-tag></template>
              </a-table-column>
              <a-table-column title="场景" :width="80" align="center">
                <template #cell="{ record }">{{ parametersFor(record).length }}</template>
              </a-table-column>
              <a-table-column title="顺序" :width="70" align="center">
                <template #cell="{ record }">{{ displayValue(record.case_sort) }}</template>
              </a-table-column>
            </template>
          </a-table>
        </a-tab-pane>

        <a-tab-pane
          key="posterior"
          title="后置清理"
          data-testid="qa-views-apitest-case-details-components-apicaseversionsnapshot-tab-pane-后置清理"
        >
          <a-tabs position="left" class="snapshot-left-tabs">
            <a-tab-pane
              key="sql"
              title="SQL变量"
              data-testid="qa-views-apitest-case-details-components-apicaseversionsnapshot-tab-pane-sql变量-2"
            >
              <SnapshotSectionList :sections="posteriorSections" empty-text="暂无后置 SQL" />
            </a-tab-pane>
          </a-tabs>
        </a-tab-pane>
      </a-tabs>
    </section>

    <section class="case-version-snapshot-panel">
      <header class="case-version-snapshot-head">
        <div>
          <strong>场景扩展</strong>
          <span>{{ selectedStepDescription }}</span>
        </div>
        <a-tag size="small" color="arcoblue">{{ selectedScenarios.length }} 个场景</a-tag>
      </header>

      <div class="case-version-scenario-scroll">
        <a-collapse
          v-if="selectedScenarios.length"
          :bordered="false"
          :default-active-key="defaultScenarioKeys"
        >
          <a-collapse-item
            v-for="(scenario, scenarioIndex) in selectedScenarios"
            :key="scenarioKey(scenario, scenarioIndex)"
          >
            <template #header>
              <a-space size="small">
                <span>{{ scenario.name || `场景 ${scenarioIndex + 1}` }}</span>
                <a-tag v-if="scenario.allow_failure" size="small" color="orange">允许失败</a-tag>
              </a-space>
            </template>
            <a-tabs position="left" class="snapshot-left-tabs snapshot-scenario-tabs">
              <a-tab-pane
                key="front"
                title="前置准备"
                data-testid="qa-views-apitest-case-details-components-apicaseversionsnapshot-tab-pane-前置准备-2"
              >
                <a-tabs type="rounded" class="snapshot-request-tabs">
                  <a-tab-pane
                    key="sql"
                    title="前置sql"
                    data-testid="qa-views-apitest-case-details-components-apicaseversionsnapshot-tab-pane-前置sql"
                  >
                    <SnapshotSectionList
                      :sections="fieldSections(scenario, 'front_sql', '前置sql')"
                      empty-text="暂无前置sql"
                      compact
                    />
                  </a-tab-pane>
                  <a-tab-pane
                    key="func"
                    title="前置函数"
                    data-testid="qa-views-apitest-case-details-components-apicaseversionsnapshot-tab-pane-前置函数"
                  >
                    <SnapshotSectionList
                      :sections="fieldSections(scenario, 'front_func', '前置函数')"
                      empty-text="暂无前置函数"
                      compact
                    />
                  </a-tab-pane>
                  <a-tab-pane
                    key="factory"
                    title="数据工厂"
                    data-testid="qa-views-apitest-case-details-components-apicaseversionsnapshot-tab-pane-数据工厂-2"
                  >
                    <SnapshotSectionList
                      :sections="scenarioFactorySections(scenario)"
                      empty-text="暂无数据工厂绑定"
                      compact
                    />
                  </a-tab-pane>
                  <a-tab-pane
                    key="gray"
                    title="灰度配置"
                    data-testid="qa-views-apitest-case-details-components-apicaseversionsnapshot-tab-pane-灰度配置-2"
                  >
                    <SnapshotSectionList
                      :sections="fieldSections(scenario, 'gray_configs', '灰度配置')"
                      empty-text="暂无灰度配置"
                      compact
                    />
                  </a-tab-pane>
                </a-tabs>
              </a-tab-pane>
              <a-tab-pane
                key="request"
                title="请求配置"
                data-testid="qa-views-apitest-case-details-components-apicaseversionsnapshot-tab-pane-请求配置"
              >
                <a-tabs type="rounded" class="snapshot-request-tabs">
                  <a-tab-pane
                    key="headers"
                    title="请求头"
                    data-testid="qa-views-apitest-case-details-components-apicaseversionsnapshot-tab-pane-请求头"
                  >
                    <SnapshotSectionList
                      :sections="scenarioRequestSections(scenario, 'headers')"
                      empty-text="暂无请求头"
                      compact
                    />
                  </a-tab-pane>
                  <a-tab-pane
                    key="params"
                    title="参数"
                    data-testid="qa-views-apitest-case-details-components-apicaseversionsnapshot-tab-pane-参数"
                  >
                    <SnapshotSectionList
                      :sections="scenarioRequestSections(scenario, 'params')"
                      empty-text="暂无请求参数"
                      compact
                    />
                  </a-tab-pane>
                  <a-tab-pane
                    key="body"
                    title="请求体"
                    data-testid="qa-views-apitest-case-details-components-apicaseversionsnapshot-tab-pane-请求体"
                  >
                    <SnapshotSectionList
                      :sections="scenarioRequestSections(scenario, 'body')"
                      empty-text="暂无请求体"
                      compact
                    />
                  </a-tab-pane>
                </a-tabs>
              </a-tab-pane>
              <a-tab-pane
                key="posterior"
                title="响应处理"
                data-testid="qa-views-apitest-case-details-components-apicaseversionsnapshot-tab-pane-响应处理"
              >
                <a-tabs type="rounded" class="snapshot-request-tabs">
                  <a-tab-pane
                    key="json"
                    title="响应JSON提取"
                    data-testid="qa-views-apitest-case-details-components-apicaseversionsnapshot-tab-pane-响应json提取"
                    ><SnapshotSectionList
                      :sections="fieldSections(scenario, 'posterior_response', '响应JSON提取')"
                      empty-text="暂无响应JSON提取"
                      compact
                  /></a-tab-pane>
                  <a-tab-pane
                    key="text"
                    title="响应文本提取"
                    data-testid="qa-views-apitest-case-details-components-apicaseversionsnapshot-tab-pane-响应文本提取"
                    ><SnapshotSectionList
                      :sections="fieldSections(scenario, 'posterior_response_text', '响应文本提取')"
                      empty-text="暂无响应文本提取"
                      compact
                  /></a-tab-pane>
                  <a-tab-pane
                    key="sql"
                    title="后置SQL"
                    data-testid="qa-views-apitest-case-details-components-apicaseversionsnapshot-tab-pane-后置sql"
                    ><SnapshotSectionList
                      :sections="fieldSections(scenario, 'posterior_sql', '后置SQL')"
                      empty-text="暂无后置SQL"
                      compact
                  /></a-tab-pane>
                  <a-tab-pane
                    key="sleep"
                    title="强制等待"
                    data-testid="qa-views-apitest-case-details-components-apicaseversionsnapshot-tab-pane-强制等待"
                    ><SnapshotSectionList
                      :sections="fieldSections(scenario, 'posterior_sleep', '强制等待')"
                      empty-text="暂无强制等待"
                      compact
                  /></a-tab-pane>
                  <a-tab-pane
                    key="file"
                    title="文件保存"
                    data-testid="qa-views-apitest-case-details-components-apicaseversionsnapshot-tab-pane-文件保存"
                    ><SnapshotSectionList
                      :sections="fieldSections(scenario, 'posterior_file', '文件保存')"
                      empty-text="暂无文件保存"
                      compact
                  /></a-tab-pane>
                  <a-tab-pane
                    key="func"
                    title="后置函数"
                    data-testid="qa-views-apitest-case-details-components-apicaseversionsnapshot-tab-pane-后置函数"
                    ><SnapshotSectionList
                      :sections="fieldSections(scenario, 'posterior_func', '后置函数')"
                      empty-text="暂无后置函数"
                      compact
                  /></a-tab-pane>
                </a-tabs>
              </a-tab-pane>
              <a-tab-pane
                key="assertion"
                title="断言配置"
                data-testid="qa-views-apitest-case-details-components-apicaseversionsnapshot-tab-pane-断言配置"
              >
                <a-tabs type="rounded" class="snapshot-request-tabs">
                  <a-tab-pane
                    key="json"
                    title="json一致断言"
                    data-testid="qa-views-apitest-case-details-components-apicaseversionsnapshot-tab-pane-json一致断言"
                    ><SnapshotSectionList
                      :sections="fieldSections(scenario, 'ass_json_all', 'json一致断言')"
                      empty-text="暂无json一致断言"
                      compact
                  /></a-tab-pane>
                  <a-tab-pane
                    key="text"
                    title="文本一致断言"
                    data-testid="qa-views-apitest-case-details-components-apicaseversionsnapshot-tab-pane-文本一致断言"
                    ><SnapshotSectionList
                      :sections="fieldSections(scenario, 'ass_text_all', '文本一致断言')"
                      empty-text="暂无文本一致断言"
                      compact
                  /></a-tab-pane>
                  <a-tab-pane
                    key="jsonpath"
                    title="响应字段断言"
                    data-testid="qa-views-apitest-case-details-components-apicaseversionsnapshot-tab-pane-响应字段断言"
                    ><SnapshotSectionList
                      :sections="fieldSections(scenario, 'ass_jsonpath', '响应字段断言')"
                      empty-text="暂无响应字段断言"
                      compact
                  /></a-tab-pane>
                  <a-tab-pane
                    key="schema"
                    title="结构化断言"
                    data-testid="qa-views-apitest-case-details-components-apicaseversionsnapshot-tab-pane-结构化断言"
                    ><SnapshotSectionList
                      :sections="fieldSections(scenario, 'ass_schema', '结构化断言')"
                      empty-text="暂无结构化断言"
                      compact
                  /></a-tab-pane>
                  <a-tab-pane
                    key="general"
                    title="通用断言"
                    data-testid="qa-views-apitest-case-details-components-apicaseversionsnapshot-tab-pane-通用断言"
                    ><SnapshotSectionList
                      :sections="fieldSections(scenario, 'ass_general', '通用断言')"
                      empty-text="暂无通用断言"
                      compact
                  /></a-tab-pane>
                  <a-tab-pane
                    key="sql"
                    title="SQL断言"
                    data-testid="qa-views-apitest-case-details-components-apicaseversionsnapshot-tab-pane-sql断言"
                    ><SnapshotSectionList
                      :sections="fieldSections(scenario, 'ass_sql', 'SQL断言')"
                      empty-text="暂无SQL断言"
                      compact
                  /></a-tab-pane>
                </a-tabs>
              </a-tab-pane>
              <a-tab-pane
                key="factory"
                title="数据工厂"
                data-testid="qa-views-apitest-case-details-components-apicaseversionsnapshot-tab-pane-数据工厂-3"
              >
                <SnapshotSectionList
                  :sections="scenarioFactorySections(scenario)"
                  empty-text="暂无数据工厂绑定"
                  compact
                />
              </a-tab-pane>
            </a-tabs>
          </a-collapse-item>
        </a-collapse>
        <div v-else class="snapshot-empty">{{ scenarioEmptyText }}</div>
      </div>
    </section>
  </div>
</template>

<script lang="ts" setup>
  import { computed, defineComponent, h, ref, watch, type PropType } from 'vue'
  import { stringifyLosslessJson } from '@/utils/lossless-json'
  import { parseApiCaseRevisionPayload } from '@/types/api-test/case-revision-payload'

  type SnapshotRecord = Record<string, any>
  type SnapshotSection = { key: string; title: string; value: unknown }

  const props = defineProps<{ payload: Record<string, unknown> }>()

  const caseTab = ref('front')
  const selectedStep = ref<SnapshotRecord>()
  const revisionPayload = computed(() => parseApiCaseRevisionPayload(props.payload))

  const casePayload = computed<SnapshotRecord>(() => revisionPayload.value.api_case)
  const runtimePayload = computed<SnapshotRecord>(
    () => revisionPayload.value.runtime as SnapshotRecord
  )
  const dependenciesPayload = computed<SnapshotRecord>(
    () => revisionPayload.value.dependencies as SnapshotRecord
  )
  const steps = computed<SnapshotRecord[]>(() => revisionPayload.value.api_case_detailed)
  const dataFactoryConfigs = computed<SnapshotRecord[]>(() =>
    Array.isArray(dependenciesPayload.value.data_factory_configs)
      ? (dependenciesPayload.value.data_factory_configs as SnapshotRecord[])
      : []
  )
  const selectedScenarios = computed(() => parametersFor(selectedStep.value))
  const selectedStepDescription = computed(() =>
    selectedStep.value
      ? `接口 ${displayValue(selectedStep.value.api_info)} / 修订 ${displayValue(
          selectedStep.value.api_info_revision_id
        )}`
      : '请先在执行编排中选择一个步骤'
  )
  const scenarioEmptyText = computed(() =>
    selectedStep.value ? '该步骤暂无场景扩展' : '该版本暂无执行步骤'
  )
  const defaultScenarioKeys = computed(() =>
    selectedScenarios.value.length ? [scenarioKey(selectedScenarios.value[0], 0)] : []
  )

  const frontPublicSections = computed(() => section(casePayload.value, 'front_public', '全局变量'))
  const frontAuthSections = computed(() =>
    section(casePayload.value, 'front_auth_config', '授权配置')
  )
  const caseGraySections = computed(() => section(runtimePayload.value, 'gray_configs', '灰度配置'))
  const frontCustomSections = computed(() =>
    section(casePayload.value, 'front_custom', '自定义变量')
  )
  const frontSqlSections = computed(() => section(casePayload.value, 'front_sql', '前置 SQL'))
  const frontHeaderSections = computed(() =>
    section(runtimePayload.value, 'resolved_front_headers', '默认请求头')
  )
  const caseFactorySections = computed(() =>
    valueSection(
      'case_data_factory_configs',
      '数据工厂绑定',
      dataFactoryConfigs.value.filter((config) => Number(config.source_type) === 1)
    )
  )
  const posteriorSections = computed(() => section(casePayload.value, 'posterior_sql', '后置 SQL'))

  watch(
    steps,
    (value) => {
      selectedStep.value = value[0]
    },
    { immediate: true }
  )

  const SnapshotSectionList = defineComponent({
    name: 'SnapshotSectionList',
    props: {
      sections: { type: Array as PropType<SnapshotSection[]>, required: true },
      emptyText: { type: String, required: true },
      compact: Boolean,
    },
    setup(componentProps) {
      return () =>
        componentProps.sections.length
          ? h(
              'div',
              {
                class: [
                  'snapshot-section-list',
                  componentProps.compact && 'snapshot-section-list--compact',
                ],
              },
              componentProps.sections.map((item) =>
                h('section', { class: 'snapshot-section', key: item.key }, [
                  h('h4', item.title),
                  h('pre', formatValue(item.value)),
                ])
              )
            )
          : h('div', { class: 'snapshot-empty' }, componentProps.emptyText)
    },
  })

  function selectStep(step: SnapshotRecord) {
    selectedStep.value = step
  }

  function parametersFor(step?: SnapshotRecord): SnapshotRecord[] {
    if (!step) return []
    if (Array.isArray(step.api_case_detailed_parameter)) return step.api_case_detailed_parameter
    return []
  }

  function fieldSections(
    scenario: SnapshotRecord,
    field: string,
    title: string
  ): SnapshotSection[] {
    return valueSection(field, title, scenario[field])
  }

  function scenarioRequestSections(
    scenario: SnapshotRecord,
    type: 'headers' | 'params' | 'body'
  ): SnapshotSection[] {
    if (type === 'headers') return pickSections(scenario, [['resolved_headers', '请求头']])
    if (type === 'params') return pickSections(scenario, [['params', '参数']])
    return pickSections(scenario, [
      ['body_config', '请求体'],
      ['sse_config', 'SSE 配置'],
    ])
  }

  function scenarioFactorySections(scenario: SnapshotRecord): SnapshotSection[] {
    return valueSection(
      'scenario_data_factory_configs',
      '数据工厂绑定',
      dataFactoryConfigs.value.filter(
        (config) =>
          Number(config.source_type) === 3 && String(config.source_id) === String(scenario.id)
      )
    )
  }

  function section(record: Record<string, unknown>, key: string, title: string): SnapshotSection[] {
    return valueSection(key, title, record[key])
  }

  function valueSection(key: string, title: string, value: unknown): SnapshotSection[] {
    return hasContent(value) ? [{ key, title, value }] : []
  }

  function pickSections(
    record: SnapshotRecord,
    fields: Array<[string, string]>
  ): SnapshotSection[] {
    return fields.flatMap(([key, title]) => valueSection(key, title, record[key]))
  }

  function hasContent(value: unknown): boolean {
    if (value === null || value === undefined || value === '') return false
    if (Array.isArray(value)) return value.length > 0
    if (typeof value === 'object') return Object.keys(value as object).length > 0
    return true
  }

  function formatValue(value: unknown): string {
    return typeof value === 'string' ? value : stringifyLosslessJson(value, 2)
  }

  function displayValue(value: unknown): string {
    return value === null || value === undefined || value === '' ? '-' : String(value)
  }

  function stepName(step: SnapshotRecord): string {
    const apiInfo = step.api_info
    if (apiInfo && typeof apiInfo === 'object') {
      return String(apiInfo.name || `接口 ${displayValue(apiInfo.id)}`)
    }
    return `接口 ${displayValue(apiInfo)}`
  }

  function stepKey(step: SnapshotRecord, index: number): string {
    return String(step.logical_id || step.id || `step-${index}`)
  }

  function scenarioKey(scenario: SnapshotRecord, index: number): string {
    return String(scenario.id || `scenario-${index}`)
  }
</script>

<style scoped>
  .case-version-snapshot {
    display: grid;
    min-height: 0;
    height: 100%;
    grid-template-columns: minmax(340px, 42fr) minmax(460px, 58fr);
    gap: 12px;
  }

  .case-version-snapshot-panel {
    display: flex;
    min-width: 0;
    min-height: 0;
    overflow: hidden;
    flex-direction: column;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
  }

  .case-version-snapshot-head {
    display: flex;
    min-height: 58px;
    padding: 10px 12px;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    border-bottom: 1px solid var(--m-border);
  }

  .case-version-snapshot-head > div {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 3px;
  }

  .case-version-snapshot-head strong {
    color: var(--m-text);
    font-size: 15px;
  }

  .case-version-snapshot-head span {
    overflow: hidden;
    color: var(--m-muted);
    font-size: 12px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .case-version-snapshot-tabs,
  .snapshot-left-tabs {
    min-height: 0;
    flex: 1;
  }

  .case-version-snapshot-tabs :deep(.arco-tabs-content),
  .case-version-snapshot-tabs :deep(.arco-tabs-content-list),
  .case-version-snapshot-tabs :deep(.arco-tabs-pane),
  .snapshot-left-tabs :deep(.arco-tabs-content),
  .snapshot-left-tabs :deep(.arco-tabs-content-list),
  .snapshot-left-tabs :deep(.arco-tabs-pane) {
    height: 100%;
    min-height: 0;
  }

  .snapshot-left-tabs :deep(.arco-tabs-content) {
    overflow: auto;
  }

  .case-version-snapshot-scroll,
  .case-version-scenario-scroll,
  .snapshot-left-tabs :deep(.arco-tabs-pane) {
    padding: 12px;
  }

  .case-version-snapshot-scroll,
  .case-version-scenario-scroll {
    height: 100%;
    min-height: 0;
    overflow: auto;
  }

  .case-version-scenario-scroll {
    flex: 1;
  }

  .case-version-snapshot :deep(.snapshot-section-list) {
    display: flex;
    flex-direction: column;
    gap: var(--m-page-gap);
  }

  .snapshot-step-order {
    display: flex;
    width: 26px;
    height: 26px;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    background: var(--m-primary);
    color: var(--m-on-primary);
  }

  .snapshot-table-api {
    display: flex;
    min-width: 0;
    padding: 6px;
    align-items: center;
    gap: 10px;
    border-radius: var(--m-radius-sm);
  }

  .snapshot-table-api > span:last-child {
    display: flex;
    flex-direction: column;
    gap: 3px;
  }

  .snapshot-table-api--active {
    background: var(--m-surface-soft);
  }

  .snapshot-table-api small {
    color: var(--m-muted);
  }

  .snapshot-step-table :deep(.arco-table-tr) {
    cursor: pointer;
  }

  .case-version-snapshot :deep(.snapshot-section) {
    padding: 12px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    background: var(--m-surface-soft);
  }

  .case-version-snapshot :deep(.snapshot-section h4) {
    margin: 0 0 6px;
    color: var(--m-text);
    font-size: 12px;
  }

  .case-version-snapshot :deep(.snapshot-section pre) {
    max-height: 420px;
    padding: 8px;
    margin: 0;
    overflow: auto;
    border-radius: var(--m-radius-sm);
    background: var(--m-surface);
    color: var(--m-text);
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 11px;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .case-version-snapshot :deep(.snapshot-section-list--compact) {
    gap: var(--m-page-gap);
  }

  .snapshot-request-tabs {
    min-height: 240px;
  }

  .snapshot-empty {
    display: flex;
    min-height: 120px;
    padding: 16px;
    align-items: center;
    justify-content: center;
    color: var(--m-muted);
    font-size: 12px;
    text-align: center;
  }

  @media (max-width: 1280px) {
    .case-version-snapshot {
      grid-template-columns: 1fr;
    }

    .case-version-snapshot-panel {
      min-height: 460px;
    }
  }
</style>
