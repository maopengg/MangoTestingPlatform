<template>
  <a-drawer
    v-model:visible="visible"
    :title="title"
    width="50%"
    :footer="false"
    unmount-on-close
  >
    <div class="mango-ui-heal-detail">
      <section
        v-for="section in detailSections"
        :key="section.title"
        class="mango-ui-heal-detail__section"
      >
        <div class="mango-ui-heal-detail__head">
          <h3>{{ section.title }}</h3><span>{{ section.description }}</span>
        </div>
        <div class="mango-ui-heal-detail__grid">
          <div v-for="item in section.rows" :key="item.label" class="mango-ui-heal-detail__kv">
            <span>{{ item.label }}</span><strong>{{ item.value }}</strong>
          </div>
        </div>
      </section>

      <section class="mango-ui-heal-detail__section">
        <div class="mango-ui-heal-detail__head">
          <h3>诊断数据</h3><span>按需加载的页面上下文及 AI 输入输出</span>
        </div>
        <a-collapse :bordered="false">
          <a-collapse-item v-for="item in jsonSections" :key="item.key" :header="item.label">
            <UiStructuredDataView v-if="item.structured" :data="item.value" />
            <JsonDisplay v-else :data="item.value" :show-drawer-button="false" :default-expanded="false" />
          </a-collapse-item>
        </a-collapse>
      </section>
    </div>
  </a-drawer>
</template>

<script setup lang="ts">
  import { computed, ref } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { getUiElementAiHealRecordDetail } from '@/api/uitest/element'
  import JsonDisplay from '@/components/display/JsonDisplay.vue'
  import UiStructuredDataView from '@/components/display/UiStructuredDataView.vue'

  const visible = ref(false)
  const loading = ref(false)
  const detail = ref<any>({})
  const title = computed(() => `自愈详情 / 记录 #${detail.value?.id || '-'}`)

  const detailSections = computed(() => {
    const item = detail.value || {}
    return [
      {
        title: '记录信息', description: '记录归属、触发来源和当前状态', rows: [
          { label: '记录ID', value: formatValue(item.id) },
          { label: '元素ID', value: formatValue(item.element_id ?? item.element) },
          { label: '页面ID', value: formatValue(item.page_id ?? item.page) },
          { label: '项目/产品', value: formatValue(item.project_product_id ?? item.project_product) },
          { label: '基线快照ID', value: formatValue(item.snapshot_id ?? item.snapshot) },
          { label: '测试环境', value: formatValue(item.test_env) },
          { label: '触发来源', value: sourceLabel(item.source) },
          { label: '修复状态', value: statusLabel(item.status) },
          { label: '创建时间', value: formatValue(item.create_time) },
          { label: '更新时间', value: formatValue(item.update_time) },
        ],
      },
      {
        title: '失败信息', description: '触发自愈时失败的定位器和页面信息', rows: [
          { label: '失败定位类型', value: expressionTypeLabel(item.failed_exp) },
          { label: '失败定位器', value: formatValue(item.failed_loc) },
          { label: '失败下标', value: formatValue(item.failed_sub) },
          { label: '失败原因', value: formatValue(item.failed_reason) },
          { label: '页面地址', value: formatValue(item.page_url) },
          { label: '错误信息', value: formatValue(item.error_message) },
        ],
      },
      {
        title: '采用结果', description: '最终候选、置信度及写回信息', rows: [
          { label: '采用定位类型', value: expressionTypeLabel(item.selected_exp) },
          { label: '采用定位器', value: formatValue(item.selected_loc) },
          { label: '采用下标', value: formatValue(item.selected_sub) },
          { label: '置信度', value: formatValue(item.confidence) },
          { label: '是否写回', value: item.applied ? '是' : '否' },
          { label: '写回人', value: formatValue(item.applied_by_id ?? item.applied_by) },
          { label: '写回时间', value: formatValue(item.applied_time) },
        ],
      },
    ]
  })
  const jsonSections = computed(() => {
    const item = detail.value || {}
    return [
      { key: 'context', label: '当前页面上下文', value: item.current_context || {} },
      { key: 'prompt', label: 'AI 输入摘要', value: item.ai_prompt_summary || {} },
      { key: 'response', label: 'AI 响应', value: item.ai_response || {} },
      { key: 'candidates', label: '候选定位器', value: item.candidates || [], structured: true },
    ]
  })

  async function open(recordId: string | number, elementId: string | number) {
    if (!recordId || !elementId || loading.value) return false
    loading.value = true
    try {
      const res = await getUiElementAiHealRecordDetail({ record_id: recordId, element_id: elementId })
      detail.value = res.data || {}
      visible.value = true
      return true
    } catch (error) {
      console.log(error)
      Message.error('自愈详情获取失败')
      return false
    } finally {
      loading.value = false
    }
  }
  function formatValue(value: any) { return value == null || value === '' ? '-' : String(value) }
  function expressionTypeLabel(value: any) {
    const labels: Record<number, string> = { 0: 'XPATH', 2: '通用定位器', 3: '文本', 4: '占位符', 9: 'CSS', 11: 'DESCRIPTION', 12: 'BOUNDS', 14: 'RESOURCE_ID' }
    return labels[Number(value)] || formatValue(value)
  }
  function sourceLabel(value: any) {
    return ({ 0: '元素检测', 1: '页面步骤', 2: 'UI Case' } as Record<number, string>)[Number(value)] || formatValue(value)
  }
  function statusLabel(value: any) {
    return ({ 1: '已生成建议', 2: '候选已验证', 3: '修复失败', 4: '人工写回', 5: '临时自愈成功', 6: '自动写回', 7: '自动写回失败' } as Record<number, string>)[Number(value)] || formatValue(value)
  }

  defineExpose({ open, loading })
</script>

<style scoped>
  .mango-ui-heal-detail { display: flex; flex-direction: column; gap: 12px; min-width: 0; }
  .mango-ui-heal-detail__section { padding: 12px; border: 1px solid var(--m-border); border-radius: var(--m-radius-lg); background: var(--m-surface); }
  .mango-ui-heal-detail__head { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; margin-bottom: 10px; }
  .mango-ui-heal-detail__head h3 { margin: 0; color: var(--m-text); font-size: 14px; line-height: 20px; }
  .mango-ui-heal-detail__head span, .mango-ui-heal-detail__kv span { color: var(--m-muted); font-size: 12px; }
  .mango-ui-heal-detail__grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 6px 8px; }
  .mango-ui-heal-detail__kv { display: grid; grid-template-columns: 86px minmax(0, 1fr); gap: 8px; padding: 6px 8px; background: var(--m-surface-soft); border-radius: var(--m-radius-md); }
  .mango-ui-heal-detail__kv strong { overflow-wrap: anywhere; color: var(--m-text); font-size: 13px; line-height: 20px; }
</style>
