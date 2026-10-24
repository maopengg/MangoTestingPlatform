<template>
  <BaseSidePanel
    :visible="visible"
    :title="title"
    width="50%"
    @update:visible="emit('update:visible', $event)"
    @cancel="emit('update:visible', false)"
  >
    <div v-if="data" class="mango-ui-element-check-panel">
      <div class="mango-ui-element-check-summary">
        <div class="mango-ui-element-check-summary-main">
          <a-tag size="small" color="arcoblue">
            {{ data.check_mode === 'deep' ? '深度检测' : '普通检测' }}
          </a-tag>
          <a-tag :color="checkStatusMeta(data.check_status).color" size="small">
            {{ checkStatusMeta(data.check_status).label }}
          </a-tag>
          <strong>{{ data.element_name || '-' }}</strong>
        </div>
        <div class="mango-ui-element-check-summary-meta">
          <span>检测时间 {{ formatValue(data.checked_time) }}</span>
          <span>耗时 {{ formatDuration(data.duration_ms) }}</span>
          <a-button
            v-if="writableUpdates.length"
            type="primary"
            size="small"
            :loading="applyLoading"
            :disabled="applied"
            @click="emit('apply')"
          >
            {{ applied ? '已写入定位组' : `写入定位组（${writableUpdates.length}）` }}
          </a-button>
        </div>
      </div>

      <section class="mango-ui-element-check-section">
        <div class="mango-ui-element-check-section-head">
          <h3>定位方式检测</h3>
          <span>逐组验证匹配数量、可见性和可操作状态</span>
        </div>
        <div v-if="data.locator_groups?.length" class="mango-ui-element-check-locators">
          <article
            v-for="item in data.locator_groups"
            :key="`${item.group}-${item.loc}`"
            class="mango-ui-element-check-locator"
          >
            <div class="mango-ui-element-check-locator-head">
              <strong>第 {{ item.group }} 组</strong>
              <a-tag :color="locatorStatusMeta(item.status).color" size="small">
                {{ locatorStatusMeta(item.status).label }}
              </a-tag>
              <a-tag size="small" color="arcoblue">匹配 {{ item.count ?? 0 }}</a-tag>
              <a-tag v-if="item.highlighted" size="small" color="green">
                已高亮 {{ item.highlighted_count ?? item.count ?? 0 }} 个
              </a-tag>
              <span>{{ formatDuration(item.duration_ms) }}</span>
            </div>
            <div class="mango-ui-element-check-locator-expression">
              <span>{{ elementExpName(item.exp) }}</span>
              <strong>{{ item.loc || '-' }}</strong>
              <em>下标 {{ item.sub || '-' }}</em>
            </div>
            <div class="mango-ui-element-check-state-list">
              <a-tag
                v-if="item.visible !== null && item.visible !== undefined"
                size="small"
                :color="item.visible ? 'green' : 'red'"
              >
                {{ item.visible ? '可见' : '不可见' }}
              </a-tag>
              <a-tag
                v-if="item.enabled !== null && item.enabled !== undefined"
                size="small"
                :color="item.enabled ? 'green' : 'red'"
              >
                {{ item.enabled ? '启用' : '禁用' }}
              </a-tag>
              <a-tag
                v-if="item.editable !== null && item.editable !== undefined"
                size="small"
                :color="item.editable ? 'green' : 'gray'"
              >
                {{ item.editable ? '可编辑' : '不可编辑' }}
              </a-tag>
              <span v-if="item.element_text">文本摘要 {{ item.element_text }}</span>
            </div>
            <div v-if="item.error_message" class="mango-ui-element-check-error">
              {{ item.error_message }}
            </div>
            <div v-else-if="item.highlight_error" class="mango-ui-element-check-error">
              元素已匹配，但高亮失败：{{ item.highlight_error }}
            </div>
          </article>
        </div>
        <div v-else class="mango-empty-state">未返回定位方式检测信息</div>
      </section>

      <section class="mango-ui-element-check-section">
        <div class="mango-ui-element-check-section-head">
          <h3>检测配置</h3>
          <span>预期事件仅在元素已配置时执行</span>
        </div>
        <div class="mango-ui-element-check-kv-grid">
          <div><span>预期事件</span><strong>{{ expectedEventText }}</strong></div>
          <div><span>执行状态</span><strong>{{ expectedEventStatusText }}</strong></div>
          <div><span>基线状态</span><strong>{{ baselineStatusText }}</strong></div>
          <div><span>页面标题</span><strong>{{ formatValue(data.page_title) }}</strong></div>
          <div class="mango-ui-element-check-kv-wide">
            <span>页面地址</span><strong>{{ formatValue(data.page_url) }}</strong>
          </div>
          <div v-if="data.error_message" class="mango-ui-element-check-kv-wide">
            <span>错误提示</span>
            <strong class="mango-ui-element-check-error-text">{{ data.error_message }}</strong>
          </div>
          <div
            v-if="data.selected_result?.locator_engine?.screenshot_error"
            class="mango-ui-element-check-kv-wide"
          >
            <span>检测截图</span>
            <strong class="mango-ui-element-check-error-text">
              {{ data.selected_result.locator_engine.screenshot_error }}
            </strong>
          </div>
        </div>
      </section>

      <section class="mango-ui-element-check-section">
        <UiStepRuntimeResult
          :result="data.selected_result"
          picture-title="检测截图"
          frameless
        />
      </section>
    </div>
    <div v-else class="mango-empty-state">暂无元素检测结果</div>
  </BaseSidePanel>
</template>

<script lang="ts" setup>
  import { computed } from 'vue'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import UiStepRuntimeResult from '@/components/reports/UiStepRuntimeResult.vue'
  import { useSelectValueStore } from '@/store/modules/get-ope-value'

  const props = withDefaults(
    defineProps<{
      visible: boolean
      title?: string
      data?: any
      applyLoading?: boolean
      applied?: boolean
    }>(),
    {
      title: '元素检测结果',
      data: null,
      applyLoading: false,
      applied: false,
    }
  )
  const emit = defineEmits<{
    (event: 'update:visible', value: boolean): void
    (event: 'apply'): void
  }>()
  const methodStore = useSelectValueStore()

  const writableUpdates = computed(() => {
    if (props.data?.check_mode !== 'deep') return []
    const updates = props.data?.selected_result?.locator_engine?.locator_updates
    return Array.isArray(updates)
      ? updates.filter((item: any) => item?.same_target === true && item?.slot && item?.loc)
      : []
  })
  const expectedEventText = computed(() => {
    const result = props.data?.expected_event_result
    if (!result?.configured) return '未配置，仅检测定位有效性'
    return methodStore.getSelectLabel(result.ope_key) || result.ope_key || '-'
  })
  const expectedEventStatusText = computed(() => {
    const result = props.data?.expected_event_result
    if (!result?.configured || !result?.executed) return '未执行'
    return Number(result.status) === 1 ? '执行通过' : '执行失败'
  })
  const baselineStatusText = computed(() => {
    const baseline = props.data?.baseline || {}
    if (baseline.after === 'created') return '已创建基线'
    if (baseline.after === 'refreshed') return '已刷新基线'
    if (baseline.before === 'existing') return '已有基线'
    if (baseline.collection_requested) return '已请求采集'
    return '暂无基线'
  })

  function formatValue(value: any) {
    if (value === null || value === undefined || value === '') return '-'
    if (typeof value === 'object') return JSON.stringify(value)
    return String(value)
  }

  function formatDuration(value: any) {
    const duration = Number(value)
    if (!Number.isFinite(duration)) return '-'
    if (duration >= 1000) return `${(duration / 1000).toFixed(duration >= 10000 ? 1 : 2)} 秒`
    return `${Math.max(0, Math.round(duration))} ms`
  }

  function checkStatusMeta(status: string) {
    const map: Record<string, { label: string; color: string }> = {
      valid: { label: '有效', color: 'green' },
      risk: { label: '存在风险', color: 'orange' },
      healed: { label: '自愈后有效', color: 'blue' },
      invalid: { label: '无效', color: 'red' },
    }
    return map[status] || map.invalid
  }

  function locatorStatusMeta(status: string) {
    const map: Record<string, { label: string; color: string }> = {
      valid: { label: '有效', color: 'green' },
      healed: { label: '自愈后有效', color: 'blue' },
      risk: { label: '有歧义', color: 'orange' },
      invalid: { label: '无效', color: 'red' },
    }
    return map[status] || map.invalid
  }

  function elementExpName(value: any) {
    const labels: Record<number, string> = {
      0: 'XPATH',
      1: 'ID',
      2: '通用定位器',
      3: '文本',
      4: '占位符',
      5: '标签',
      6: '角色',
      7: '标题',
      8: '链接文本',
      9: 'CSS',
    }
    return labels[Number(value)] || `类型 ${value ?? '-'}`
  }
</script>

<style scoped>
  .mango-ui-element-check-panel { display: flex; flex-direction: column; gap: 12px; }
  .mango-ui-element-check-summary,
  .mango-ui-element-check-section {
    border: 1px solid var(--m-border);
    border-radius: 8px;
    background: var(--m-surface);
  }
  .mango-ui-element-check-summary {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 12px 14px;
  }
  .mango-ui-element-check-summary-main,
  .mango-ui-element-check-summary-meta,
  .mango-ui-element-check-locator-head,
  .mango-ui-element-check-state-list {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
  }
  .mango-ui-element-check-summary-meta,
  .mango-ui-element-check-locator-head span,
  .mango-ui-element-check-state-list span { color: var(--m-muted); font-size: 12px; }
  .mango-ui-element-check-section { padding: 14px; }
  .mango-ui-element-check-section-head { margin-bottom: 10px; }
  .mango-ui-element-check-section-head h3 { margin: 0; color: var(--m-text); font-size: 14px; }
  .mango-ui-element-check-section-head span { color: var(--m-muted); font-size: 12px; }
  .mango-ui-element-check-locators { display: flex; flex-direction: column; gap: 8px; }
  .mango-ui-element-check-locator {
    padding: 10px 12px;
    border: 1px solid var(--m-border);
    border-radius: 6px;
    background: var(--m-surface-soft);
  }
  .mango-ui-element-check-locator-expression {
    display: grid;
    grid-template-columns: 96px minmax(0, 1fr) 90px;
    gap: 8px;
    margin: 8px 0;
  }
  .mango-ui-element-check-locator-expression span,
  .mango-ui-element-check-locator-expression em { color: var(--m-muted); font-size: 12px; font-style: normal; }
  .mango-ui-element-check-locator-expression strong { overflow-wrap: anywhere; }
  .mango-ui-element-check-error,
  .mango-ui-element-check-error-text { color: var(--m-danger); }
  .mango-ui-element-check-error { margin-top: 8px; font-size: 12px; }
  .mango-ui-element-check-kv-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
  .mango-ui-element-check-kv-grid > div { display: flex; min-width: 0; gap: 8px; padding: 8px 10px; background: var(--m-surface-soft); }
  .mango-ui-element-check-kv-grid span { flex: 0 0 80px; color: var(--m-muted); font-size: 12px; }
  .mango-ui-element-check-kv-grid strong { min-width: 0; overflow-wrap: anywhere; }
  .mango-ui-element-check-kv-wide { grid-column: 1 / -1; }
  @media (max-width: 900px) {
    .mango-ui-element-check-summary { align-items: flex-start; flex-direction: column; }
    .mango-ui-element-check-kv-grid { grid-template-columns: 1fr; }
  }
</style>
