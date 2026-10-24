<template>
  <div class="mango-structured-data">
    <a-empty v-if="isEmpty" description="暂无数据" />

    <template v-else-if="rootIsArray">
      <UiStructuredDataTable :rows="normalizedRootRows" :field-label="fieldLabel" :format-cell="formatCell" />
    </template>

    <template v-else>
      <div v-if="scalarEntries.length" class="mango-structured-data__grid">
        <div v-for="item in scalarEntries" :key="item.key" class="mango-structured-data__kv">
          <span>{{ fieldLabel(item.key) }}</span><strong>{{ formatCell(item.value, item.key) }}</strong>
        </div>
      </div>

      <a-collapse v-if="longTextEntries.length" :bordered="false">
        <a-collapse-item v-for="item in longTextEntries" :key="item.key" :header="fieldLabel(item.key)">
          <pre class="mango-code-panel mango-structured-data__text">{{ item.value }}</pre>
        </a-collapse-item>
      </a-collapse>

      <section v-for="item in objectEntries" :key="item.key" class="mango-structured-data__group">
        <h4>{{ fieldLabel(item.key) }}</h4>
        <div class="mango-structured-data__grid">
          <div v-for="entry in objectRows(item.value)" :key="entry.key" class="mango-structured-data__kv">
            <span>{{ fieldLabel(entry.key) }}</span><strong>{{ formatCell(entry.value, entry.key) }}</strong>
          </div>
        </div>
      </section>

      <section v-for="item in arrayEntries" :key="item.key" class="mango-structured-data__group">
        <div class="mango-structured-data__group-head">
          <h4>{{ fieldLabel(item.key) }}</h4><span>{{ item.value.length }} 项</span>
        </div>
        <UiStructuredDataTable
          v-if="item.value.length"
          :rows="normalizeRows(item.value)"
          :field-label="fieldLabel"
          :format-cell="formatCell"
        />
        <a-empty v-else description="暂无数据" />
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
  import { computed } from 'vue'
  import UiStructuredDataTable from '@/components/display/UiStructuredDataTable.vue'

  const props = defineProps<{ data: any }>()
  const rootIsArray = computed(() => Array.isArray(props.data))
  const rootObject = computed<Record<string, any>>(() => (
    props.data && typeof props.data === 'object' && !Array.isArray(props.data) ? props.data : {}
  ))
  const isEmpty = computed(() => rootIsArray.value
    ? !props.data.length
    : !Object.keys(rootObject.value).length)
  const entries = computed(() => Object.entries(rootObject.value).map(([key, value]) => ({ key, value })))
  const scalarEntries = computed(() => entries.value.filter(({ value }) => isScalar(value) && String(value ?? '').length <= 240))
  const longTextEntries = computed(() => entries.value.filter(({ value }) => typeof value === 'string' && value.length > 240))
  const arrayEntries = computed(() => entries.value.filter(({ value }) => Array.isArray(value)))
  const objectEntries = computed(() => entries.value.filter(({ value }) => isPlainObject(value)))
  const normalizedRootRows = computed(() => normalizeRows(props.data || []))

  const LABELS: Record<string, string> = {
    _index: '序号', value: '值', snapshot_id: '快照ID', page_url: '页面地址', created_at_ms: '创建时间戳', tree: '语义树',
    nodes: '语义节点', errors: '采集错误', ref: '节点引用', parent_ref: '父节点', frame_index: 'Frame序号',
    frame_url: 'Frame地址', role: '角色', name: '可访问名称', text: '文本', label: '标签',
    placeholder: '占位符', title: '标题', alt: '替代文本', tag: '标签名', disabled: '禁用',
    editable: '可编辑', interactive: '可交互', checked: '选中', selected: '已选择', expanded: '展开',
    required: '必填', attributes: '属性', path: '层级路径', nearby_text: '邻近文本', source: '来源',
    verified: '验证通过', count: '匹配数', score: '初始分数', final_score: '最终分数', exp: '定位类型',
    loc: '定位表达式', sub: '下标', reason: '推荐原因', reject_reason: '失败原因', reject_code: '失败编码',
    duration_ms: '定位耗时(ms)', semantic_score: '语义分数', stability_score: '稳定性分数',
    visible: '可见', enabled: '启用', operation_compatible: '操作兼容', auto_apply_eligible: '允许自动写回', candidate_id: '候选ID',
    target_ref: '目标节点', durable_locator_strategy: '定位策略', used_ai: 'AI生成',
    key: '标识', field: '字段', operator: '比较方式', passed: '是否通过', actual: '实际值', expected: '预期值', message: '结果说明',
  }
  const SOURCE_LABELS: Record<string, string> = {
    applied_heal_record: '已应用修复', latest_snapshot_locator: '最近基线', history_snapshot_locator: '历史基线',
    baseline_semantic: '基线语义', prompt_text_candidate: '提示词文本直查', ai_accessibility: 'AI语义候选', visual_agent: '视觉语义候选',
  }
  function fieldLabel(key: string) { return LABELS[key] || key }
  function isScalar(value: any) { return value == null || ['string', 'number', 'boolean'].includes(typeof value) }
  function isPlainObject(value: any) { return value && typeof value === 'object' && !Array.isArray(value) }
  function objectRows(value: Record<string, any>) { return Object.entries(value || {}).map(([key, rowValue]) => ({ key, value: rowValue })) }
  function formatCell(value: any, key = '') {
    if (value == null || value === '') return '-'
    if (key === 'source') return SOURCE_LABELS[String(value)] || String(value)
    if (key === 'exp') return ({ 0: 'XPATH', 2: '通用定位器', 3: '文本', 4: '占位符', 9: 'CSS' } as Record<number, string>)[Number(value)] || String(value)
    if (typeof value === 'boolean') return value ? '是' : '否'
    if (Array.isArray(value)) return value.map((item) => formatCell(item)).join(' / ') || '-'
    if (isPlainObject(value)) return Object.entries(value).map(([itemKey, itemValue]) => `${fieldLabel(itemKey)}=${formatCell(itemValue, itemKey)}`).join('；') || '-'
    return String(value)
  }
  function normalizeRows(value: any[]) {
    return (value || []).map((item, index) => isPlainObject(item) ? { _index: index + 1, ...item } : { _index: index + 1, value: item })
  }

</script>

<style scoped>
  .mango-structured-data { display: flex; flex-direction: column; gap: 10px; min-width: 0; }
  .mango-structured-data__grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 6px 8px; }
  .mango-structured-data__kv { display: grid; grid-template-columns: 100px minmax(0, 1fr); gap: 8px; padding: 6px 8px; background: var(--m-surface-soft); border-radius: var(--m-radius-md); }
  .mango-structured-data__kv span, .mango-structured-data__group-head span { color: var(--m-muted); font-size: 12px; }
  .mango-structured-data__kv strong { overflow-wrap: anywhere; color: var(--m-text); font-size: 13px; line-height: 20px; }
  .mango-structured-data__group { min-width: 0; }
  .mango-structured-data__group h4 { margin: 0 0 8px; color: var(--m-text); font-size: 13px; }
  .mango-structured-data__group-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
  .mango-structured-data__text { max-height: 320px; margin: 0; padding: 10px 12px; overflow: auto; white-space: pre-wrap; overflow-wrap: anywhere; font-size: 12px; line-height: 20px; }
</style>
