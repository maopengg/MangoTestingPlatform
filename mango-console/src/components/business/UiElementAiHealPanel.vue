<template>
  <a-drawer
    v-model:visible="visible"
    :title="title"
    width="50%"
    :footer="false"
    unmount-on-close
  >
    <div class="mango-ui-ai-heal">
      <div class="mango-ui-ai-heal__summary">
        <div v-for="item in summaryCards" :key="item.label" class="mango-ui-ai-heal__card">
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
        </div>
      </div>

      <section class="mango-ui-ai-heal__section">
        <div class="mango-ui-ai-heal__head">
          <h3>候选定位器</h3>
          <span>来源于最近一次修复记录，验证通过的候选可写回元素配置</span>
        </div>
        <UiElementHealCandidatePanel
          :rows="candidateRows"
          :applying-key="applyingKey"
          :empty-text="candidateEmptyText"
          @apply="applyCandidate"
        />
      </section>

      <section v-if="candidateSummaryRows.length || candidateRejections.length" class="mango-ui-ai-heal__section">
        <div class="mango-ui-ai-heal__head">
          <h3>候选摘要</h3>
          <span>按候选来源和拒绝原因快速判断修复卡点</span>
        </div>
        <div v-if="candidateSummaryRows.length" class="mango-ui-ai-heal__grid">
          <div v-for="item in candidateSummaryRows" :key="item.label" class="mango-ui-ai-heal__kv">
            <span>{{ item.label }}</span><strong>{{ item.value }}</strong>
          </div>
        </div>
        <a-collapse v-if="candidateRejections.length" :bordered="false" class="mango-ui-ai-heal__rejections">
          <a-collapse-item :header="`拒绝原因汇总（${candidateRejections.length} 项）`">
            <div v-for="(item, index) in candidateRejections" :key="`${item.source || 'unknown'}-${index}`" class="mango-ui-ai-heal__rejection">
              <a-tag size="small" color="red">{{ item.source_label }}</a-tag>
              <span>{{ item.reason || '-' }}</span><em v-if="item.loc">{{ item.loc }}</em>
            </div>
          </a-collapse-item>
        </a-collapse>
      </section>

      <section v-for="section in infoSections" :key="section.title" class="mango-ui-ai-heal__section">
        <div class="mango-ui-ai-heal__head">
          <h3>{{ section.title }}</h3><span>{{ section.description }}</span>
        </div>
        <div v-if="section.rows.length" class="mango-ui-ai-heal__grid">
          <div v-for="item in section.rows" :key="item.label" class="mango-ui-ai-heal__kv">
            <span>{{ item.label }}</span><strong>{{ item.value }}</strong>
          </div>
        </div>
        <div v-else class="mango-empty-state">暂无{{ section.title }}</div>
      </section>

      <section class="mango-ui-ai-heal__section">
        <div class="mango-ui-ai-heal__head"><h3>基线历史</h3><span>最近 10 次有效基线采集记录</span></div>
        <a-table :data="snapshotHistoryRows" :pagination="false" :bordered="false" size="small" :scroll="{ x: 920 }">
          <template #columns>
            <a-table-column title="采集时间" data-index="create_time" :width="180" />
            <a-table-column title="环境" data-index="test_env" :width="80" />
            <a-table-column title="匹配数" data-index="match_count" :width="80" />
            <a-table-column title="角色" data-index="element_role" :width="110" />
            <a-table-column title="元素文本" data-index="element_text" :ellipsis="true" :tooltip="true" />
            <a-table-column title="页面地址" data-index="url" :ellipsis="true" :tooltip="true" />
            <a-table-column title="操作" :width="100" fixed="right" align="center">
              <template #cell="{ record }">
                <a-button
                  size="mini"
                  type="text"
                  :loading="snapshotDetailLoadingId === String(record.id)"
                  :disabled="Boolean(snapshotDetailLoadingId)"
                  @click="openSnapshotDetail(record)"
                >
                  详情
                </a-button>
              </template>
            </a-table-column>
          </template>
        </a-table>
      </section>

      <section class="mango-ui-ai-heal__section">
        <div class="mango-ui-ai-heal__head"><h3>自愈历史</h3><span>最近 20 次自愈执行和写回记录</span></div>
        <a-table :data="healHistoryRows" :pagination="false" :bordered="false" size="small" :scroll="{ x: 920 }">
          <template #columns>
            <a-table-column title="触发时间" data-index="create_time" :width="180" />
            <a-table-column title="状态" data-index="status_label" :width="120" />
            <a-table-column title="置信度" data-index="confidence" :width="90" />
            <a-table-column title="写回" data-index="applied_label" :width="70" />
            <a-table-column title="采用定位器" data-index="selected_loc" :ellipsis="true" :tooltip="true" />
            <a-table-column title="失败原因" data-index="failed_reason" :ellipsis="true" :tooltip="true" />
            <a-table-column title="操作" :width="100" fixed="right" align="center">
              <template #cell="{ record }">
                <a-button
                  size="mini"
                  type="text"
                  :loading="healDetailLoadingId === String(record.id)"
                  :disabled="Boolean(healDetailLoadingId)"
                  @click="openHealDetail(record)"
                >
                  详情
                </a-button>
              </template>
            </a-table-column>
          </template>
        </a-table>
      </section>
    </div>
  </a-drawer>

  <UiElementBaselineDetailPanel ref="baselineDetailPanelRef" />
  <UiElementHealRecordDetailPanel ref="healDetailPanelRef" />
</template>

<script setup lang="ts">
  import { computed, ref } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import {
    getUiElementAiHealRecords,
    getUiElementAiInfo,
    getUiElementAiSnapshots,
    putUiElementAiHealApply,
  } from '@/api/uitest/element'
  import UiElementBaselineDetailPanel from '@/components/business/UiElementBaselineDetailPanel.vue'
  import UiElementHealCandidatePanel from '@/components/business/UiElementHealCandidatePanel.vue'
  import UiElementHealRecordDetailPanel from '@/components/business/UiElementHealRecordDetailPanel.vue'
  import { useEnum } from '@/store/modules/get-enum'

  const props = defineProps<{ testEnv?: string | number | null }>()
  const enumStore = useEnum()
  const emit = defineEmits<{ (event: 'applied'): void }>()
  const visible = ref(false)
  const loading = ref(false)
  const applyingKey = ref('')
  const data = ref<any>({})
  const currentElement = ref<any>(null)
  const baselineDetailPanelRef = ref<InstanceType<typeof UiElementBaselineDetailPanel> | null>(null)
  const healDetailPanelRef = ref<InstanceType<typeof UiElementHealRecordDetailPanel> | null>(null)
  const snapshotDetailLoadingId = ref('')
  const healDetailLoadingId = ref('')
  const title = computed(() => `AI自愈 / ${currentElement.value?.name || '-'}`)

  const summaryCards = computed(() => [
    { label: '基线快照', value: data.value?.statistics?.snapshot_count || 0 },
    { label: '修复记录', value: data.value?.statistics?.heal_record_count || 0 },
    { label: '待确认', value: data.value?.statistics?.pending_suggestion_count || 0 },
    { label: '已应用', value: data.value?.statistics?.applied_count || 0 },
  ])
  const candidateRows = computed(() => {
    const record = data.value?.latest_heal_record
    const trigger = record?.ai_prompt_summary?.locator_engine?.trigger || {}
    return (record?.candidates || []).map((item: any, index: number) => ({
      ...item,
      record_id: record?.id,
      candidate_index: item.candidate_index ?? index,
      trigger,
      source_label: sourceLabel(item.source),
      final_score: item.final_score ?? item.score ?? item.confidence ?? 0,
      diagnostic_text: diagnosticText(item),
    }))
  })
  const candidateEmptyText = computed(() => data.value?.latest_heal_record
    ? '最近一次修复记录未生成可用候选。请检查统一定位引擎候选生成和验证信息。'
    : '暂无修复候选。元素当前可正常定位，只有定位失败并触发 AI 自愈后才会生成候选定位器。')
  const locatorEngine = computed(() => {
    const heal = data.value?.latest_heal_record?.ai_prompt_summary?.locator_engine
    const runtime = data.value?.element?.latest_runtime_snapshot?.locator_engine
    if (heal && Object.keys(heal?.candidate_summary || {}).length) return heal
    return runtime && typeof runtime === 'object' ? runtime : heal || {}
  })
  const candidateSummary = computed(() => locatorEngine.value?.candidate_summary || {})
  const candidateSummaryRows = computed(() => Object.keys(candidateSummary.value).length ? [
    { label: 'Trace ID', value: formatValue(locatorEngine.value?.trace_id) },
    { label: '候选总数', value: formatValue(candidateSummary.value.total) },
    { label: '已验证', value: formatValue(candidateSummary.value.checked) },
    { label: '通过候选', value: formatValue(candidateSummary.value.verified) },
    { label: '来源分布', value: formatSourceSummary(candidateSummary.value.by_source) },
    { label: '最终来源', value: sourceLabel(locatorEngine.value?.used_source) },
    { label: 'Agent调用', value: locatorEngine.value?.harness?.agent_called ? '是' : '否' },
    { label: 'Harness耗时', value: locatorEngine.value?.harness?.duration_ms != null ? `${locatorEngine.value.harness.duration_ms} ms` : '-' },
    { label: 'Prompt版本', value: formatValue(locatorEngine.value?.harness?.prompt_version) },
  ] : [])
  const candidateRejections = computed(() => (candidateSummary.value?.top_rejections || []).slice(0, 8).map((item: any) => ({ ...item, source_label: sourceLabel(item.source) })))
  const elementRows = computed(() => {
    const element = data.value?.element || {}
    return [
      { label: '元素ID', value: formatValue(element.id) }, { label: '元素名称', value: formatValue(element.name) },
      { label: '元素分类', value: formatValue(element.category) }, { label: '自愈状态', value: healStatus(element.ai_heal_status) },
      { label: '稳定通过次数', value: formatValue(element.ai_stable_pass_count) }, { label: '最近匹配数量', value: formatValue(element.latest_match_count) },
      { label: '最近文本', value: formatValue(element.latest_element_text) }, { label: '最近基线时间', value: formatValue(element.ai_last_snapshot_time) },
      { label: '最近自愈时间', value: formatValue(element.ai_last_heal_time) },
    ]
  })
  const healRows = computed(() => {
    const item = data.value?.latest_heal_record
    const trigger = item?.ai_prompt_summary?.locator_engine?.trigger || {}
    return item ? [
      { label: '失败原因', value: formatValue(item.failed_reason) }, { label: '触发原因', value: formatValue(trigger.error) },
      { label: '触发操作', value: formatValue(trigger.ope_key) }, { label: '原始定位', value: formatValue(trigger.origin_loc) },
      { label: '原始下标', value: formatValue(trigger.origin_sub) }, { label: '页面URL', value: formatValue(item.page_url) },
    ] : []
  })
  const infoSections = computed(() => [
    { title: '元素信息', description: '当前元素的分类、模式、基线和最近执行信息', rows: elementRows.value },
    { title: '触发上下文', description: '最近一次自愈独有的失败与触发信息', rows: healRows.value },
  ])
  const snapshotHistoryRows = computed(() => (data.value?.snapshots || []).map((item: any) => ({
    ...item,
    create_time: formatValue(item.create_time),
    test_env: formatEnvironment(item.test_env),
    match_count: formatValue(item.match_count),
    element_role: formatValue(item.element_role),
    element_text: formatValue(item.element_text),
    url: formatValue(item.url),
  })))
  const healHistoryRows = computed(() => (data.value?.heal_records || []).map((item: any) => ({
    ...item,
    create_time: formatValue(item.create_time),
    status_label: recordStatus(item.status),
    confidence: formatValue(item.confidence),
    applied_label: item.applied ? '是' : '否',
    selected_loc: formatValue(item.selected_loc),
    failed_reason: formatValue(item.failed_reason || item.error_message),
  })))
  async function open(element: any) {
    if (!element?.id || loading.value) return false
    loading.value = true
    try {
      const query = { element_id: element.id, test_env: props.testEnv }
      const [res, snapshotsRes, healRecordsRes] = await Promise.all([
        getUiElementAiInfo(query),
        getUiElementAiSnapshots({ ...query, page: 1, pageSize: 10 }),
        getUiElementAiHealRecords({ ...query, page: 1, pageSize: 20 }),
      ])
      currentElement.value = element
      data.value = {
        ...(res.data || {}),
        snapshots: snapshotsRes.data?.items || [],
        heal_records: healRecordsRes.data?.items || [],
      }
      visible.value = true
      return true
    } catch (error) {
      console.log(error)
      return false
    } finally {
      loading.value = false
    }
  }
  async function applyCandidate(record: any, rowIndex: number, targetSlot: number) {
    if (!record.record_id) return Message.error('缺少修复记录ID')
    const key = `${record.record_id}-${rowIndex}-${targetSlot}`
    applyingKey.value = key
    try {
      const res = await putUiElementAiHealApply({ record_id: record.record_id, candidate_index: record.candidate_index ?? rowIndex, target_slot: targetSlot })
      Message.success(res.msg || '写回成功')
      emit('applied')
      await open(currentElement.value)
    } catch (error) {
      console.log(error)
    } finally {
      if (applyingKey.value === key) applyingKey.value = ''
    }
  }
  async function openSnapshotDetail(record: any) {
    if (!record?.id || !currentElement.value?.id || snapshotDetailLoadingId.value) return
    snapshotDetailLoadingId.value = String(record.id)
    try {
      await baselineDetailPanelRef.value?.open(record.id, currentElement.value.id)
    } finally {
      snapshotDetailLoadingId.value = ''
    }
  }
  async function openHealDetail(record: any) {
    if (!record?.id || !currentElement.value?.id || healDetailLoadingId.value) return
    healDetailLoadingId.value = String(record.id)
    try {
      await healDetailPanelRef.value?.open(record.id, currentElement.value.id)
    } finally {
      healDetailLoadingId.value = ''
    }
  }
  function formatValue(value: any) { return value == null || value === '' ? '-' : typeof value === 'object' ? JSON.stringify(value) : String(value) }
  function formatEnvironment(value: any) { return value == null || value === '' ? '-' : enumStore.environment_type.find((item) => String(item.key) === String(value))?.title || '-' }
  function healStatus(value: any) { return Number(value) === 1 ? '已有基线' : Number(value) === 2 ? '待确认' : Number(value) === 3 ? '已修复' : Number(value) === 4 ? '已忽略' : '无基线' }
  function recordStatus(value: any) { return ({ 1: '已生成建议', 2: '候选已验证', 3: '修复失败', 4: '人工写回', 5: '临时自愈成功', 6: '自动写回', 7: '自动写回失败' } as Record<number, string>)[Number(value)] || '-' }
  function sourceLabel(value: any) {
    const map: Record<string, string> = { applied_heal_record: '已应用修复', latest_snapshot_locator: '最近基线', history_snapshot_locator: '历史基线', baseline_semantic: '基线语义', semantic_role_name: '语义角色', semantic_placeholder: '占位符语义', semantic_text: '文本语义', prompt_text_candidate: '提示词文本直查', playwright_label: 'Playwright标签语义', playwright_role: 'Playwright角色语义', dom_stable_attr: 'DOM稳定属性', dom_proximity: 'DOM邻近控件', dom_proximity_xpath: 'DOM邻近控件XPath', label_relative_xpath: '标签相对XPath', portal_text_option: '弹层文本选项', unique_visible_text: '唯一可见文本', playwright_text_sub: 'Playwright文本下标', popup_text_option: '弹层普通文本', ai_accessibility: 'AI语义候选', visual_agent: '视觉语义候选', candidate_exhausted: '候选耗尽', fixed_locator: '固定定位' }
    return map[String(value || '')] || String(value || '-')
  }
  function diagnosticText(item: any) {
    const parts = []
    if (item?.element_text) parts.push(`文本：${item.element_text}`)
    if (item?.element_name) parts.push(`名称：${item.element_name}`)
    if (item?.element_role) parts.push(`角色：${item.element_role}`)
    return parts.join('；') || item?.diagnostic_text || '-'
  }
  function formatSourceSummary(value: any) {
    if (!value || typeof value !== 'object') return '-'
    const rows = Object.entries(value).filter(([, item]: any) => Number(item?.total || item?.checked || 0) > 0).slice(0, 6).map(([source, item]: any) => `${sourceLabel(source)} ${Number(item?.verified || 0)}/${Number(item?.total || 0)}`)
    return rows.join('；') || '-'
  }

  defineExpose({ open, loading })
</script>

<style scoped>
  .mango-ui-ai-heal { display: flex; flex-direction: column; gap: 12px; min-width: 0; }
  .mango-ui-ai-heal__summary { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }
  .mango-ui-ai-heal__card, .mango-ui-ai-heal__section { border: 1px solid var(--m-border); border-radius: var(--m-radius-lg); background: var(--m-surface); }
  .mango-ui-ai-heal__card { display: flex; min-height: 60px; flex-direction: column; justify-content: center; gap: 3px; padding: 8px 10px; }
  .mango-ui-ai-heal__card span, .mango-ui-ai-heal__head span, .mango-ui-ai-heal__kv span { color: var(--m-muted); font-size: 12px; }
  .mango-ui-ai-heal__card strong { font-size: 18px; line-height: 24px; color: var(--m-text); }
  .mango-ui-ai-heal__section { padding: 12px; }
  .mango-ui-ai-heal__head { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; margin-bottom: 10px; }
  .mango-ui-ai-heal__head h3 { margin: 0; font-size: 14px; line-height: 20px; color: var(--m-text); }
  .mango-ui-ai-heal__grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 6px 8px; }
  .mango-ui-ai-heal__kv { display: grid; grid-template-columns: 86px minmax(0, 1fr); gap: 8px; padding: 6px 8px; background: var(--m-surface-soft); border-radius: var(--m-radius-md); }
  .mango-ui-ai-heal__kv strong { overflow-wrap: anywhere; color: var(--m-text); font-size: 13px; line-height: 20px; }
  .mango-ui-ai-heal__rejections { margin-top: 8px; background: var(--m-surface-soft); border-radius: var(--m-radius-md); }
  .mango-ui-ai-heal__rejection { display: grid; grid-template-columns: 120px minmax(0, 1fr); gap: 6px 8px; align-items: start; font-size: 12px; }
  .mango-ui-ai-heal__rejection + .mango-ui-ai-heal__rejection { margin-top: 6px; }
  .mango-ui-ai-heal__rejection em { grid-column: 2; color: var(--m-muted); overflow-wrap: anywhere; }
  @media (max-width: 1100px) { .mango-ui-ai-heal__summary, .mango-ui-ai-heal__grid { grid-template-columns: 1fr 1fr; } }
</style>
