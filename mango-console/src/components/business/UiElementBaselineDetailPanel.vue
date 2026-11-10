<template>
  <a-drawer
    v-model:visible="visible"
    :title="title"
    width="50%"
    :footer="false"
    unmount-on-close
  >
    
    <MangoPanelSpin :loading="loading">
    <div v-if="detail" class="mango-ui-baseline-detail">
      <section
        v-for="section in detailSections"
        :key="section.title"
        class="mango-ui-baseline-detail__section"
      >
        <div class="mango-ui-baseline-detail__head">
          <h3>{{ section.title }}</h3><span>{{ section.description }}</span>
        </div>
        <div class="mango-ui-baseline-detail__grid">
          <div v-for="item in section.rows" :key="item.label" class="mango-ui-baseline-detail__kv">
            <span>{{ item.label }}</span><strong>{{ item.value }}</strong>
          </div>
        </div>
      </section>

      <section class="mango-ui-baseline-detail__section">
        <div class="mango-ui-baseline-detail__head">
          <h3>结构化特征</h3><span>属性、位置、样式及页面语义摘要</span>
        </div>
        <a-collapse :bordered="false">
          <a-collapse-item v-for="item in jsonSections" :key="item.key" :header="item.label">
            <UiStructuredDataView v-if="item.structured" :data="item.value" />
            <JsonDisplay v-else :data="item.value" :show-drawer-button="false" :default-expanded="false" />
          </a-collapse-item>
        </a-collapse>
      </section>

      <section class="mango-ui-baseline-detail__section">
        <div class="mango-ui-baseline-detail__head">
          <h3>页面结构</h3><span>采集时已脱敏的元素及邻近 HTML</span>
        </div>
        <a-collapse :bordered="false">
          <a-collapse-item v-for="item in htmlSections" :key="item.key" :header="item.label">
            <pre class="mango-code-panel mango-ui-baseline-detail__code">{{ item.value || '-' }}</pre>
          </a-collapse-item>
        </a-collapse>
      </section>
    </div>
    <div v-else class="mango-empty-state">暂无基线详情</div>
    </MangoPanelSpin>
  </a-drawer>
</template>

<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { computed, onBeforeUnmount, ref, watch } from 'vue'
  import { useLiveWorkbenchScope } from '@/hooks/use-live-workbench-scope'
  import { cloneLosslessJson } from '@/utils/lossless-json'
  import { liveId, liveObject, liveError } from './ui-live-workbench'
  import MangoPanelSpin from '@/components/feedback/MangoPanelSpin.vue'
  import type { BaselineEvidence } from './ui-element-ai'
  import { getUiElementAiSnapshotDetail } from '@/api/uitest/element'
  import JsonDisplay from '@/components/display/JsonDisplay.vue'
  import UiStructuredDataView from '@/components/display/UiStructuredDataView.vue'

  const visible = ref(false)
  let disposed = false
  onBeforeUnmount(() => { disposed = true; visible.value = false; detail.value = null; sequence++ })
  const loading = ref(false)
  const detail = ref<BaselineEvidence | null>(null)
  const error = ref('')
  let sequence = 0, target: { id: string | number; elementId: string | number } | null = null
  const scope = useLiveWorkbenchScope(() => null, { invalidate() { sequence++; visible.value = false; detail.value = null; target = null; loading.value = false; error.value = '' }, resume() {} })
  watch(visible, value => { if (!value) { sequence++; loading.value = false } }, { flush: 'sync' })
  const title = computed(() => `基线详情 / 快照 #${detail.value?.id ?? '-'}`)

  const detailSections = computed(() => {
    const item = detail.value || {}
    return [
      {
        title: '采集信息', description: '快照来源、状态和所属环境', rows: [
          { label: '快照ID', value: formatValue(item.id) },
          { label: '元素ID', value: formatValue(item.element_id ?? item.element) },
          { label: '采集时间', value: formatValue(item.create_time) },
          { label: '更新时间', value: formatValue(item.update_time) },
          { label: '测试环境', value: formatValue(item.test_env) },
          { label: '采集来源', value: sourceLabel(item.source) },
          { label: '状态', value: Number(item.status) === 1 ? '有效' : '历史' },
          { label: '截图地址', value: formatValue(item.screenshot_path) },
        ],
      },
      {
        title: '页面信息', description: '成功定位元素时的页面上下文', rows: [
          { label: '页面标题', value: formatValue(item.title) },
          { label: '页面地址', value: formatValue(item.url) },
          { label: 'Iframe地址', value: formatValue(item.frame_url) },
          { label: '页面ID', value: formatValue(item.page_id ?? item.page) },
          { label: '项目/产品', value: formatValue(item.project_product_id ?? item.project_product) },
        ],
      },
      {
        title: '定位信息', description: '本次成功命中的定位表达式及指纹', rows: [
          { label: '定位类型', value: expressionTypeLabel(item.exp) },
          { label: '定位表达式', value: formatValue(item.loc) },
          { label: '下标', value: formatValue(item.sub) },
          { label: '匹配数量', value: formatValue(item.match_count) },
          { label: '定位器指纹', value: formatValue(item.locator_hash) },
          { label: 'HTML指纹', value: formatValue(item.html_hash) },
        ],
      },
      {
        title: '元素信息', description: '元素语义、类型和采集时文本', rows: [
          { label: '元素文本', value: formatValue(item.element_text) },
          { label: '标签', value: formatValue(item.element_tag) },
          { label: '角色', value: formatValue(item.element_role) },
          { label: '元素类型', value: formatValue(item.element_type) },
          { label: '可访问名称', value: formatValue(item.element_name) },
          { label: '占位符', value: formatValue(item.element_placeholder) },
          { label: '元素值', value: item.element_value != null ? formatValue(item.element_value) : '未采集（安全策略）' },
        ],
      },
    ]
  })
  const jsonSections = computed(() => {
    const item = detail.value || {}
    return [
      { key: 'attributes', label: '关键属性', value: item.element_attributes || {} },
      { key: 'rect', label: '元素位置与尺寸', value: item.element_rect || {} },
      { key: 'css', label: '关键样式', value: item.element_css || {} },
      { key: 'dom', label: '页面 DOM 摘要', value: item.page_dom_digest || {} },
      { key: 'accessibility', label: '可访问性语义摘要', value: item.accessibility_digest || {}, structured: true },
    ]
  })
  const htmlSections = computed(() => {
    const item = detail.value || {}
    return [
      { key: 'element', label: '元素 HTML', value: item.outer_html },
      { key: 'parent', label: '父级 HTML', value: item.parent_html },
      { key: 'nearby', label: '邻近 HTML', value: item.nearby_html },
    ]
  })

  async function open(snapshotId: string | number, elementId: string | number) {
    const current = scope.capture(), request = ++sequence
    if (!current() || liveId(snapshotId) === null || liveId(elementId) === null || disposed) return false
    target = { id: snapshotId, elementId }; detail.value = null; error.value = ''; visible.value = true; loading.value = true
    try {
      const response: unknown = await getUiElementAiSnapshotDetail({ snapshot_id: snapshotId, element_id: elementId })
      if (!current() || request !== sequence || !visible.value || disposed) return false
      const envelope = liveObject(response), data = liveObject(envelope.data)
      if ((envelope.code != null && envelope.code !== 200) || String(data.id) !== String(snapshotId) || (liveId(data.element_id ?? data.element) !== null && String(data.element_id ?? data.element) !== String(elementId))) throw Error('详情数据与当前记录不匹配')
      detail.value = cloneLosslessJson(data) as BaselineEvidence
      return true
    } catch (reason) { if (current() && request === sequence) (reportLoadError(reason, "基线详情获取失败，请重试", false), error.value = liveError(reason, '基线详情获取失败，请重试')); return false }
    finally { if (current() && request === sequence) loading.value = false }
  }
  function retry() { if (target) void open(target.id, target.elementId) }
  function formatValue(value: unknown) { return value == null || value === '' ? '-' : String(value) }
  function expressionTypeLabel(value: unknown) {
    const labels: Record<number, string> = { 0: 'XPATH', 2: '通用定位器', 3: '文本', 4: '占位符', 9: 'CSS', 11: 'DESCRIPTION', 12: 'BOUNDS', 14: 'RESOURCE_ID' }
    return labels[Number(value)] || formatValue(value)
  }
  function sourceLabel(value: unknown) {
    return ({ 0: '元素检测', 1: '页面步骤', 2: 'UI Case' } as Record<number, string>)[Number(value)] || formatValue(value)
  }

  defineExpose({ open, loading })
</script>

<style scoped>
  .mango-ui-evidence-error { color: var(--m-danger); padding: var(--m-page-gap); }
  .mango-ui-baseline-detail { display: flex; flex-direction: column; gap: 12px; min-width: 0; }
  .mango-ui-baseline-detail__section { padding: 12px; border: 1px solid var(--m-border); border-radius: var(--m-radius-lg); background: var(--m-surface); }
  .mango-ui-baseline-detail__head { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; margin-bottom: 10px; }
  .mango-ui-baseline-detail__head h3 { margin: 0; color: var(--m-text); font-size: 14px; line-height: 20px; }
  .mango-ui-baseline-detail__head span, .mango-ui-baseline-detail__kv span { color: var(--m-muted); font-size: 12px; }
  .mango-ui-baseline-detail__grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 6px 8px; }
  .mango-ui-baseline-detail__kv { display: grid; grid-template-columns: 86px minmax(0, 1fr); gap: 8px; padding: 6px 8px; background: var(--m-surface-soft); border-radius: var(--m-radius-md); }
  .mango-ui-baseline-detail__kv strong { overflow-wrap: anywhere; color: var(--m-text); font-size: 13px; line-height: 20px; }
  .mango-ui-baseline-detail__code { max-height: 320px; margin: 0; padding: 10px 12px; overflow: auto; white-space: pre-wrap; overflow-wrap: anywhere; font-size: 12px; line-height: 20px; }
</style>
