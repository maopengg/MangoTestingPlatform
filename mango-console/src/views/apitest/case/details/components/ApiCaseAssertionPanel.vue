<!-- eslint-disable vue/no-mutating-props -->
<template>
  <a-tabs
    class="mango-api-case-assertion-tabs"
    :active-key="activeKey"
    @tab-click="emit('change', String($event))"
  >
    <template #extra>
      <MangoTableActions :actions="toolbarActions" :max-inline="1" />
    </template>
    <a-tab-pane key="30" title="JSON一致">
      <div class="m-2"
        ><TipMessage
          margin-bottom="8px"
          message="仅断言已配置的JSON字段，未填写的字段不参与校验" />
        <JsonDisplay
          :data="draft.ass_json_all ?? ''"
          show-edit-button
          :show-drawer-button="false"
          :edit-disabled="editLocked"
          @edit="openJsonAssertion"
        />
      </div>
    </a-tab-pane>
    <a-tab-pane key="33" title="文本一致">
      <div class="m-2"
        ><TipMessage margin-bottom="8px" message="对响应文本进行完整匹配" /><a-textarea
          v-model="draft.ass_text_all"
          :disabled="editLocked"
          :auto-size="fixedRows"
          allow-clear
          placeholder="请输入期望的响应文本"
          @blur="save('ass_text_all')"
      /></div>
    </a-tab-pane>
    <a-tab-pane key="31" title="响应字段">
      <div class="m-2">
        <p class="mango-assertion-config-hint">“未分组”是默认组；组内可选且/或，组间固定为且。</p>
        <p v-if="compareOpen && compareStale" class="mango-assertion-config-hint">
          配置或环境已变化，当前验证结果已过期；请重新验证后对照。
        </p>
        <p v-else-if="compareOpen && !compareResults?.length" class="mango-assertion-config-hint">
          暂无断言结果，请先执行或点击“一键验证”。
        </p>
        <p
          v-else-if="showRowComparison && !fieldCompareResults.length"
          class="mango-assertion-config-hint"
        >
          当前结果不包含响应字段校验，请查看其他断言类型的结果。
        </p>
        <p v-else-if="showRowComparison && !resultByIndex.size" class="mango-assertion-config-hint">
          历史结果无法确认对应行，请点击“一键验证”后对照。
        </p>
        <p
          v-else-if="showRowComparison && resultByIndex.size < fieldCompareResults.length"
          class="mango-assertion-config-hint"
        >
          部分历史结果无法确认对应行，仅展示已匹配的结果；完整结果可在“断言结果”查看。
        </p>
        <div class="mango-assertion-table-region">
          <a-table
            class="mango-assertion-config-table"
            :bordered="false"
            :data="assertionRows"
            :pagination="false"
            :scroll="{ x: 1080 }"
            :row-class="assertionRowClass"
          >
            <template #columns>
              <a-table-column title="断言组" :width="112">
                <template #cell="{ record }">
                  <a-select
                    size="small"
                    :model-value="String(record.assertion.group_name || '').trim()"
                    :options="assertionGroupOptions"
                    :disabled="editLocked"
                    :allow-clear="false"
                    allow-search
                    allow-create
                    placeholder="选择或输入组名"
                    aria-label="选择断言组"
                    @change="assignAssertionGroup(record.index, $event)"
                  />
                </template>
              </a-table-column>
              <a-table-column title="组内关系" :width="100" align="center">
                <template #cell="{ record }">
                  <a-select
                    size="small"
                    :model-value="record.groupLogic"
                    :options="relationOptions"
                    :disabled="editLocked"
                    :allow-clear="false"
                    aria-label="组内关系"
                    @change="changeAssertionRowLogic(record, $event)"
                  />
                  <span
                    v-if="showRowComparison && canShowGroupSummary(record)"
                    class="mango-assertion-config-table__group-summary"
                    >组校验：{{
                      Number(groupSummaryByName.get(record.groupName || '未分组')?.status) === 1
                        ? '通过'
                        : '失败'
                    }}</span
                  >
                </template>
              </a-table-column>
              <a-table-column title="提取方法" :width="128">
                <template #cell="{ record }">
                  <a-select
                    size="small"
                    :model-value="normalizeType(record.assertion.assertion_type)"
                    :options="typeOptions"
                    :disabled="editLocked"
                    :allow-clear="false"
                    @change="updateAssertionType($event, draft.ass_jsonpath, record.index)"
                  />
                </template>
              </a-table-column>
              <a-table-column title="实际值（响应值）" :width="240">
                <template #cell="{ record }">
                  <a-input
                    size="small"
                    v-model="record.assertion.actual"
                    :disabled="editLocked"
                    :placeholder="expressionPlaceholder(record.assertion)"
                    @blur="save('ass_jsonpath')"
                  />
                  <a-tooltip
                    v-if="showRowComparison && getResultForRow(record)"
                    :content="formatResultValue(getResultForRow(record)?.actual, 2000)"
                    mini
                  >
                    <span class="mango-assertion-config-table__inline-result">
                      响应值：{{ formatResultValue(getResultForRow(record)?.actual) }}
                    </span>
                  </a-tooltip>
                </template>
              </a-table-column>
              <a-table-column title="断言方法" :width="240">
                <template #cell="{ record }">
                  <a-cascader
                    size="small"
                    v-model="record.assertion.method"
                    :options="textMethods"
                    :disabled="editLocked"
                    expand-trigger="hover"
                    value-key="key"
                    placeholder="请选择断言方法"
                    @change="updateJsonpathMethod($event, draft.ass_jsonpath, record.index)"
                  />
                  <a-tooltip :content="assertionPreview(record.assertion)">
                    <span class="mango-assertion-config-table__preview">{{
                      assertionPreview(record.assertion)
                    }}</span>
                  </a-tooltip>
                  <a-tooltip
                    v-if="showRowComparison && getResultForRow(record)"
                    :content="getResultForRow(record)?.ass_msg || '暂无执行消息'"
                    mini
                  >
                    <span
                      class="mango-assertion-config-table__result-status"
                      :class="
                        Number(getResultForRow(record)?.status) === 1
                          ? 'mango-assertion-config-table__result-status--pass'
                          : 'mango-assertion-config-table__result-status--fail'
                      "
                      >校验：{{
                        Number(getResultForRow(record)?.status) === 1 ? '通过' : '失败'
                      }}</span
                    >
                  </a-tooltip>
                </template>
              </a-table-column>
              <a-table-column title="预期值" :width="180">
                <template #cell="{ record }">
                  <a-input
                    size="small"
                    v-if="showExpect(record.assertion)"
                    v-model="record.assertion.expect"
                    :disabled="editLocked"
                    placeholder="请输入预期值"
                    @blur="save('ass_jsonpath')"
                  />
                  <span v-else class="mango-assertion-config-table__muted">无需预期值</span>
                  <a-tooltip
                    v-if="
                      showRowComparison && showExpect(record.assertion) && getResultForRow(record)
                    "
                    :content="formatResultValue(getResultForRow(record)?.expect, 2000)"
                    mini
                  >
                    <span class="mango-assertion-config-table__inline-result">
                      执行时：{{ formatResultValue(getResultForRow(record)?.expect) }}
                    </span>
                  </a-tooltip>
                </template>
              </a-table-column>
              <a-table-column title="操作" :width="160" align="center" fixed="right">
                <template #cell="{ record }">
                  <a-button
                    size="small"
                    type="text"
                    status="danger"
                    :disabled="editLocked"
                    @click="remove('ass_jsonpath', record.index)"
                    >移除</a-button
                  >
                </template>
              </a-table-column>
            </template>
            <template #empty>
              <div class="mango-empty-state">暂无响应字段断言，点击上方“增加”添加</div>
            </template>
          </a-table>
        </div>
      </div>
    </a-tab-pane>
    <a-tab-pane key="35" title="SQL">
      <div class="m-2"
        ><TipMessage
          message="按当前环境解析逻辑数据源并执行只读查询；支持 MySQL、PostgreSQL、SQLite" /><div
          class="mango-horizontal-scroll-region"
        >
          <KeyValueList
            layout="assertion"
            :data-list="draft.ass_sql"
            :field-config="sqlFields"
            :on-delete-item="(index) => remove('ass_sql', index)"
            :on-save="() => save('ass_sql')"
            @update:item="(index, value) => update('ass_sql', index, value)"
            empty-text='暂无SQL断言，点击上方"增加"按钮添加'
          /> </div
      ></div>
    </a-tab-pane>
    <a-tab-pane key="34" title="结构化">
      <div class="m-2 mango-assertion-schema"
        ><a-space
          ><TipMessage message="场景配置会覆盖接口管理中开启的结构化断言" /><a-button
            size="mini"
            type="primary"
            :loading="schemaLoading"
            @click="emit('generate-schema')"
            >自动生成</a-button
          ></a-space
        >
        <JsonDisplay
          :data="draft.ass_schema ?? ''"
          show-edit-button
          :show-drawer-button="false"
          :edit-disabled="editLocked || schemaLoading"
          @edit="openJsonAssertion('ass_schema')"
        />
      </div>
    </a-tab-pane>
    <a-tab-pane key="32" title="通用断言">
      <div class="m-2"
        ><TipMessage message="支持任意类型断言，实际值和预期值均可使用缓存变量" /><div
          class="mango-horizontal-scroll-region"
        >
          <GeneralAssertionEditor
            v-model="draft.ass_general"
            :methods="generalMethods"
            :edit-locked="editLocked"
            @save="save('ass_general')"
          /> </div
      ></div>
    </a-tab-pane>
    <a-tab-pane key="36" title="回调">
      <slot name="callback"></slot>
    </a-tab-pane>
    <a-tab-pane key="37" title="协议断言">
      <ApiCaseProtocolAssertions
        :scenario-id="draft.id"
        :value="draft.body_config?.protocol_expectation"
        :edit-locked="editLocked"
        :saving="protocolSaving"
        @save="emit('save-protocol', $event)"
      />
    </a-tab-pane>
  </a-tabs>
  <MangoJsonEditDrawer
    v-model:visible="jsonEditVisible"
    :model-value="jsonEditText"
    :title="jsonEditField === 'ass_schema' ? '编辑结构化断言' : '编辑 JSON 一致断言'"
    :description="jsonEditField === 'ass_schema' ? '使用 JSON Schema 校验响应结构；留空可清除场景配置。' : '仅断言已配置的 JSON 字段；留空可清除该断言。'"
    :placeholder="jsonEditField === 'ass_schema' ? '请输入响应结构' : '请输入期望的响应JSON'"
    @save="saveJsonAssertion"
  />
</template>

<script setup lang="ts">
  import { useApiCaseScenarioDraft } from '../composables/useApiCaseScenarioDraft'
  import type { ApiCaseScenario } from '../types'
  import { computed, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import JsonDisplay from '@/components/display/JsonDisplay.vue'
  import MangoJsonEditDrawer from '@/components/editors/MangoJsonEditDrawer.vue'
  import { parseLosslessJson, stringifyLosslessJson } from '@/utils/lossless-json'
  import KeyValueList from '@/components/forms/KeyValueList.vue'
  import GeneralAssertionEditor from '@/components/forms/GeneralAssertionEditor.vue'
  import TipMessage from '@/components/feedback/TipMessage.vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import ApiCaseProtocolAssertions from './ApiCaseProtocolAssertions.vue'
  import type { ApiProtocolExpectation } from '@/types/api-test/case-parameter'

  type AssertionField =
    | 'ass_json_all'
    | 'ass_text_all'
    | 'ass_jsonpath'
    | 'ass_sql'
    | 'ass_schema'
    | 'ass_general'
  type AssertionListField = 'ass_jsonpath' | 'ass_sql' | 'ass_general'
  const props = withDefaults(
    defineProps<{
      item: ApiCaseScenario
      activeKey: string
      editLocked: boolean
      verifying: boolean
      protocolSaving?: boolean
      schemaLoading: boolean
      compareOpen: boolean
      compareResults?: any[] | null
      compareSource?: 'verify' | 'runtime'
      compareStale?: boolean
      textMethods?: any[]
      generalMethods?: any[]
      sqlDatasourceOptions?: any[]
      sqlMethodOptions?: any[]
    }>(),
    {
      textMethods: () => [],
      generalMethods: () => [],
      sqlDatasourceOptions: () => [],
      sqlMethodOptions: () => [],
      compareResults: () => [],
      compareSource: 'runtime',
      compareStale: false,
      protocolSaving: false,
    }
  )
  const emit = defineEmits<{
    (event: 'change', value: string): void
    (event: 'save', field: AssertionField, value: any, id: number): void
    (event: 'verify', scenario: ApiCaseScenario): void
    (event: 'toggle-compare'): void
    (event: 'generate-schema'): void
    (event: 'save-protocol', value: ApiProtocolExpectation): void
  }>()
  const { draft } = useApiCaseScenarioDraft(
    () => props.item,
    () => {}
  )

  const fixedRows = { minRows: 9, maxRows: 9 }
  const jsonEditVisible = ref(false)
  const jsonEditText = ref('')
  const jsonEditField = ref<'ass_json_all' | 'ass_schema'>('ass_json_all')
  watch(() => [props.item.id, props.editLocked], () => { jsonEditVisible.value = false })
  function openJsonAssertion(field: 'ass_json_all' | 'ass_schema' = 'ass_json_all') {
    if (props.editLocked || (field === 'ass_schema' && props.schemaLoading)) return
    jsonEditField.value = field
    const value = draft.value[field]
    jsonEditText.value = typeof value === 'string' ? value : value == null ? '' : stringifyLosslessJson(value, 2)
    jsonEditVisible.value = true
  }
  function saveJsonAssertion(value: string) {
    if (props.editLocked) return
    if (value.trim()) {
      try { parseLosslessJson(value) } catch {
        Message.error(jsonEditField.value === 'ass_schema' ? '结构化断言JSON格式不正确，请修正后保存' : 'JSON一致断言格式不正确，请修正后保存')
        return
      }
    }
    jsonEditVisible.value = false
    if (value === jsonEditText.value) return
    draft.value[jsonEditField.value] = value
    save(jsonEditField.value)
  }
  const relationOptions = [
    { label: '且', value: 'AND' },
    { label: '或', value: 'OR' },
  ]
  const typeOptions = [
    { label: 'JSONPath', value: 'jsonpath' },
    { label: '正则表达式', value: 'regex' },
    { label: '缓存变量', value: 'cache' },
  ]
  const canAdd = computed(() => ['31', '32', '35'].includes(props.activeKey))
  const canAddGroup = computed(() => ['31', '32'].includes(props.activeKey))
  const toolbarActions = computed(() => [
    { label: '增加', hidden: !canAdd.value, disabled: props.editLocked, onClick: addItem },
    { label: '增加关系组', hidden: !canAddGroup.value, overflow: true, disabled: props.editLocked, onClick: addOrGroup },
    { label: props.compareOpen ? '收起对照' : '对照结果', hidden: props.activeKey !== '31', overflow: true, onClick: () => emit('toggle-compare') },
    { label: props.verifying ? '验证中…' : '一键验证', hidden: ['36', '37'].includes(props.activeKey), overflow: canAdd.value, loading: props.verifying, disabled: props.verifying, onClick: () => emit('verify', draft.value) },
  ])
  const assertionRowKeys = new WeakMap<object, number>()
  let assertionRowSequence = 0
  function getAssertionRowKey(assertion: object) {
    if (!assertionRowKeys.has(assertion)) assertionRowKeys.set(assertion, ++assertionRowSequence)
    return assertionRowKeys.get(assertion)!
  }
  const assertionRows = computed(() => {
    const groupNames = new Map<string, { order: number; logic: 'AND' | 'OR'; color: number }>()
    const rows = (draft.value.ass_jsonpath || []).map((assertion: any, index: number) => {
      const groupName = String(assertion.group_name || '').trim()
      if (!groupNames.has(groupName)) {
        groupNames.set(groupName, {
          order: groupNames.size,
          logic: String(assertion.group_logic || 'AND').toUpperCase() === 'OR' ? 'OR' : 'AND',
          color: groupNames.size % 5,
        })
      }
      const group = groupNames.get(groupName)
      return {
        key: getAssertionRowKey(assertion),
        index,
        assertion,
        groupName,
        groupLogic: group?.logic || 'AND',
        groupOrder: group?.order ?? -1,
        colorIndex: group?.color ?? -1,
      }
    })
    rows.sort((left: any, right: any) => {
      const leftRank = left.groupLogic === 'AND' ? 0 : 1
      const rightRank = right.groupLogic === 'AND' ? 0 : 1
      return leftRank - rightRank || left.groupOrder - right.groupOrder || left.index - right.index
    })
    return rows
  })
  const fieldCompareResults = computed(() =>
    (props.compareResults || []).filter((result: any) =>
      ['jsonpath', 'regex', 'cache'].includes(String(result?.source_type || ''))
    )
  )
  function assertionSignature(assertion: any) {
    if (!assertion || typeof assertion !== 'object' || Array.isArray(assertion)) return ''
    return JSON.stringify([
      String(assertion.assertion_type || 'jsonpath').toLowerCase(),
      String(assertion.actual ?? ''),
      String(assertion.method ?? ''),
      assertion.expect ?? null,
      String(assertion.group_name || '').trim(),
      String(assertion.group_logic || 'AND').toUpperCase() === 'OR' ? 'OR' : 'AND',
    ])
  }
  const resultByIndex = computed(() => {
    const results = new Map<number, any>()
    const configSignatures = (draft.value.ass_jsonpath || []).map(assertionSignature)
    const configMatches = new Map<string, number[]>()
    configSignatures.forEach((signature: string, index: number) => {
      if (signature) configMatches.set(signature, [...(configMatches.get(signature) || []), index])
    })
    const candidates = fieldCompareResults.value
    const resultCounts = new Map<string, number>()
    candidates.forEach((result: any) => {
      const signature = assertionSignature(result.raw_config)
      if (signature) resultCounts.set(signature, (resultCounts.get(signature) || 0) + 1)
    })
    for (const result of candidates) {
      const signature = assertionSignature(result.raw_config)
      const explicitIndex = Number(result.assertion_index) - 1
      if (
        Number.isInteger(explicitIndex) &&
        explicitIndex >= 0 &&
        explicitIndex < configSignatures.length &&
        (props.compareSource === 'verify' ||
          (signature && signature === configSignatures[explicitIndex]))
      ) {
        results.set(explicitIndex, result)
        continue
      }
      const matches = configMatches.get(signature) || []
      if (
        signature &&
        matches.length === 1 &&
        resultCounts.get(signature) === 1 &&
        !results.has(matches[0])
      ) {
        results.set(matches[0], result)
      }
    }
    return results
  })
  const groupSummaryByName = computed(() => {
    const summaries = new Map<string, any>()
    for (const result of props.compareResults || []) {
      if (result?.source_type === 'assertion_group' && result?.group_source_type === 'jsonpath') {
        summaries.set(String(result.group_name || '未分组').trim(), result)
      }
    }
    return summaries
  })
  const showRowComparison = computed(() => props.compareOpen && !props.compareStale)
  function getResultForRow(record: any) {
    return resultByIndex.value.get(record.index)
  }
  function isFirstGroupRow(record: any) {
    return (
      assertionRows.value.find((row: any) => row.groupName === record.groupName)?.index ===
      record.index
    )
  }
  function canShowGroupSummary(record: any) {
    const name = record.groupName || '未分组'
    if (!isFirstGroupRow(record) || !groupSummaryByName.value.has(name)) return false
    return assertionRows.value
      .filter((row: any) => row.groupName === record.groupName)
      .every((row: any) => resultByIndex.value.has(row.index))
  }
  function formatResultValue(value: any, maxLength = 120) {
    if (value === undefined) return '未提供'
    if (value === null) return 'null'
    let text: string
    if (typeof value === 'object') {
      try {
        text = JSON.stringify(value) ?? String(value)
      } catch {
        text = String(value)
      }
    } else {
      text = String(value)
    }
    return text.length > maxLength ? `${text.slice(0, maxLength)}…` : text
  }
  const assertionGroupOptions = computed(() => [
    { label: '未分组', value: '' },
    ...[...new Set(assertionRows.value.map((row: any) => row.groupName).filter(Boolean))].map(
      (name) => ({
        label: name,
        value: name,
      })
    ),
  ])
  function assertionRowClass(record: any) {
    return record.colorIndex < 0 ? '' : `mango-assertion-config-row--group-${record.colorIndex}`
  }
  function newJsonpathAssertion(): import('@/types/api-test/case-parameter').ApiJsonPathAssertionItem {
    const defaultGroup = draft.value.ass_jsonpath.find(
      (assertion: any) => !String(assertion.group_name || '').trim()
    )
    return {
      group_name: '',
      group_logic: String(defaultGroup?.group_logic || '').toUpperCase() === 'OR' ? 'OR' : 'AND',
      assertion_type: 'jsonpath',
      actual: '',
      method: '',
      expect: null,
    }
  }
  function changeGroupLogic(name: string, value: any) {
    if (props.editLocked) return
    const logic = String(value).toUpperCase() === 'OR' ? 'OR' : 'AND'
    draft.value.ass_jsonpath.forEach((assertion: any) => {
      if (String(assertion.group_name || '').trim() === name) assertion.group_logic = logic
    })
    save('ass_jsonpath')
  }
  function changeAssertionRowLogic(record: any, value: any) {
    if (props.editLocked) return
    changeGroupLogic(record.groupName, value)
  }
  function assignAssertionGroup(index: number, value: any) {
    if (props.editLocked) return
    const name = String(value || '').trim()
    const existing = draft.value.ass_jsonpath.find(
      (item: any, itemIndex: number) =>
        itemIndex !== index && String(item.group_name || '').trim() === name
    )
    const assertion = draft.value.ass_jsonpath[index]
    if (String(assertion.group_name || '').trim() === name) return
    assertion.group_name = name
    assertion.group_logic =
      String(existing?.group_logic || '').toUpperCase() === 'OR' ? 'OR' : 'AND'
    save('ass_jsonpath')
  }

  function findMethod(items: any[] = [], value: any): any {
    for (const option of items) {
      if (String(option.value) === String(value)) return option
      const child = findMethod(option.children, value)
      if (child) return child
    }
    return null
  }
  function normalizeType(value: any) {
    return ['regex', 'cache'].includes(String(value).toLowerCase())
      ? String(value).toLowerCase()
      : 'jsonpath'
  }
  function expressionPlaceholder(assertion: any) {
    return (
      {
        jsonpath: '请输入 JSONPath',
        regex: '请输入正则表达式',
        cache: '请输入 ${{缓存Key}}',
      } as any
    )[normalizeType(assertion?.assertion_type)]
  }
  function save(field: AssertionField) {
    if (!props.editLocked) emit('save', field, draft.value[field], draft.value.id)
  }
  function remove(field: AssertionListField, index: number) {
    if (!props.editLocked) {
      draft.value[field].splice(index, 1)
      save(field)
    }
  }
  function update(field: AssertionListField, index: number, value: any) {
    if (!props.editLocked) {
      draft.value[field][index] = value
      save(field)
    }
  }
  function updateGroup(value: any, list: any[], index: number, field: AssertionListField) {
    const logic = String(value).toUpperCase() === 'OR' ? 'OR' : 'AND'
    const name = list[index].group_name
    if (name) {
      list.forEach((assertion) => {
        if (assertion.group_name === name) assertion.group_logic = logic
      })
    } else {
      list[index].group_logic = logic
    }
    save(field)
  }
  function updateJsonpathMethod(value: any, list: any[], index: number) {
    const method = findMethod(props.textMethods, value)
    if (method && !(method.parameter || []).some((parameter: any) => parameter.f === 'expect'))
      list[index].expect = null
    save('ass_jsonpath')
  }
  function updateAssertionType(value: any, list: any[], index: number) {
    list[index].assertion_type = normalizeType(value)
    if (['p_matches', 'p_does_not_match'].includes(list[index].method))
      Object.assign(list[index], { method: '', expect: null })
    save('ass_jsonpath')
  }
  function showExpect(assertion: any) {
    if (!assertion?.method) return true
    const method = findMethod(props.textMethods, assertion.method)
    return !method || (method.parameter || []).some((parameter: any) => parameter.f === 'expect')
  }
  function assertionPreview(assertion: any) {
    const actual = String(assertion?.actual ?? '').trim()
    if (!actual) return '填写实际值后预览'
    const methodValue = String(assertion?.method || '')
    if (!methodValue) return `${actual} · 请选择断言方法`

    const noExpectedMethods: Record<string, string> = {
      p_is_not_none: '不是 null',
      p_is_none: '是 null',
      p_is_true: '是 True',
      p_is_false: '是 False',
      p_is_empty: '为空',
      p_is_not_empty: '不为空',
    }
    if (noExpectedMethods[methodValue]) return `${actual} ${noExpectedMethods[methodValue]}`

    const methodLabel = String(findMethod(props.textMethods, methodValue)?.label || methodValue)
    if (!showExpect(assertion)) return `${actual} ${methodLabel}`
    const expected = assertion?.expect
    if (expected === null || expected === undefined) return `${actual} · 请填写预期值`
    const expectedText = typeof expected === 'string' ? expected : JSON.stringify(expected)
    const comparisonMethods: Record<string, string> = {
      p_is_equal_to: '等于',
      p_is_not_equal_to: '不等于',
      p_contains: '包含',
      p_does_not_contain: '不包含',
    }
    if (comparisonMethods[methodValue])
      return `${actual} ${comparisonMethods[methodValue]} ${expectedText}`
    const readableMethod = methodLabel.replace(/expect|预期值/g, expectedText)
    return `${actual} ${readableMethod}${readableMethod === methodLabel ? ` ${expectedText}` : ''}`
  }
  function addItem() {
    if (props.editLocked) return
    if (props.activeKey === '31') draft.value.ass_jsonpath.push(newJsonpathAssertion())
    if (props.activeKey === '32')
      draft.value.ass_general.push({ group_name: '', group_logic: 'AND', method: '', value: {} })
    if (props.activeKey === '35')
      draft.value.ass_sql.push({
        actual: '',
        method: 'assert_sql_count',
        expect: '',
        datasource_alias: null,
      })
  }
  function addOrGroup() {
    if (props.editLocked) return
    if (props.activeKey === '31') {
      const groupName = `关系组${Date.now()}`
      draft.value.ass_jsonpath.push(
        { ...newJsonpathAssertion(), group_name: groupName, group_logic: 'OR' },
        { ...newJsonpathAssertion(), group_name: groupName, group_logic: 'OR' }
      )
    }
    if (props.activeKey === '32') {
      const groupName = `或关系${Date.now().toString().slice(-4)}`
      draft.value.ass_general.push(
        { group_name: groupName, group_logic: 'OR', method: '', value: {} },
        { group_name: groupName, group_logic: 'OR', method: '', value: {} }
      )
      save('ass_general')
    }
  }
  const sqlFields = computed(() => [
    {
      field: 'datasource_alias',
      label: '逻辑数据源',
      type: 'select',
      options: props.sqlDatasourceOptions,
      allowClear: false,
    },
    {
      field: 'method',
      label: '断言方法',
      type: 'select',
      options: props.sqlMethodOptions,
      allowClear: false,
    },
    { field: 'actual', label: 'SQL语句', placeholder: '请输入只读查询SQL，可使用缓存变量' },
    { field: 'expect', label: '预期值', placeholder: '请输入预期值' },
  ])
</script>

<style scoped>
  .mango-assertion-schema {
    display: flex;
    flex-direction: column;
    gap: var(--m-page-gap);
  }
  .mango-api-case-assertion-tabs
    :deep(.arco-tabs-nav-type-line.arco-tabs-nav-horizontal .arco-tabs-tab) {
    margin-inline: 6px;
  }
  .mango-assertion-table-region {
    min-width: 0;
  }
  .mango-assertion-config-hint {
    margin: 0 0 var(--m-space-xs);
    color: var(--m-muted);
    font-size: 12px;
    line-height: 1.4;
  }
  .mango-horizontal-scroll-region {
    min-width: 0;
    overflow-x: auto;
  }
  .mango-assertion-config-table {
    min-width: 0;
    width: 100%;
  }
  .mango-assertion-config-table :deep(.arco-select-view),
  .mango-assertion-config-table :deep(.arco-cascader-view),
  .mango-assertion-config-table :deep(.arco-input-wrapper) {
    width: 100%;
    min-width: 0;
  }
  .mango-assertion-config-table__muted {
    color: var(--m-muted);
    font-size: 12px;
  }
  .mango-assertion-config-table__preview {
    display: block;
    overflow: hidden;
    margin-top: var(--m-space-xs);
    color: var(--m-text-2);
    font-size: 12px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .mango-assertion-config-table__inline-result {
    display: block;
    overflow: hidden;
    margin-top: var(--m-space-xs);
    color: var(--m-text-2);
    font-size: 12px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .mango-assertion-config-table__result-status {
    display: inline-block;
    font-size: 12px;
    font-weight: 600;
  }
  .mango-assertion-config-table__result-status--pass {
    color: var(--m-success);
  }
  .mango-assertion-config-table__result-status--fail {
    color: var(--m-danger);
  }
  .mango-assertion-config-table__group-summary {
    display: block;
    margin-top: var(--m-space-xs);
    color: var(--m-text-2);
    font-size: 11px;
  }
  .mango-assertion-config-table :deep(.mango-assertion-config-row--group-0 > .arco-table-td) {
    background: color-mix(in srgb, var(--m-chart-1) 7%, var(--m-surface));
  }
  .mango-assertion-config-table :deep(.mango-assertion-config-row--group-1 > .arco-table-td) {
    background: color-mix(in srgb, var(--m-chart-2) 7%, var(--m-surface));
  }
  .mango-assertion-config-table :deep(.mango-assertion-config-row--group-2 > .arco-table-td) {
    background: color-mix(in srgb, var(--m-chart-3) 7%, var(--m-surface));
  }
  .mango-assertion-config-table :deep(.mango-assertion-config-row--group-3 > .arco-table-td) {
    background: color-mix(in srgb, var(--m-chart-4) 7%, var(--m-surface));
  }
  .mango-assertion-config-table :deep(.mango-assertion-config-row--group-4 > .arco-table-td) {
    background: color-mix(in srgb, var(--m-chart-5) 7%, var(--m-surface));
  }
</style>
