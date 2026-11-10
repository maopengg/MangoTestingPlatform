<template>
  <a-drawer v-model:visible="visible" title="模块覆盖 Case" width="820px" unmount-on-close>
    <MangoPanelSpin :loading="loading">
      <template v-if="failed"><a-button size="small" :loading="loading" @click="load">重新加载</a-button></template>
      <a-descriptions v-if="detail.id" :column="2" bordered size="small">
        <a-descriptions-item label="当前状态" :span="2">{{
          label(detail.status)
        }}</a-descriptions-item>
        <a-descriptions-item label="来源Key" :span="2">{{ detail.source_key }}</a-descriptions-item>
        <a-descriptions-item label="仓库/分支" :span="2"
          >{{ detail.repository_key }} / {{ detail.branch }}</a-descriptions-item
        >
        <a-descriptions-item label="接口" :span="2"
          >{{ detail.method }} {{ detail.url }}</a-descriptions-item
        >
        <a-descriptions-item label="Case标题" :span="2">{{ detail.name }}</a-descriptions-item>
        <a-descriptions-item label="测试场景" :span="2">{{
          detail.payload?.test_scenario || '-'
        }}</a-descriptions-item>
        <a-descriptions-item label="核心断言" :span="2">{{
          detail.payload?.core_assertion || detail.payload?.scenario_assertion || '-'
        }}</a-descriptions-item>
        <a-descriptions-item label="测试归属">{{
          detail.test_ownership || '-'
        }}</a-descriptions-item>
        <a-descriptions-item label="测试层级">
          {{ enumTitle(enumStore.api_case_scenario_layer, detail.scenario_layer) }}
        </a-descriptions-item>
        <a-descriptions-item label="验证类型">
          {{ enumTitle(enumStore.api_case_scenario_type, detail.scenario_type) }}
        </a-descriptions-item>
        <a-descriptions-item label="执行场景">
          {{ enumTitles(enumStore.api_case_scenario_tag, detail.scenario_tags) }}
        </a-descriptions-item>
        <a-descriptions-item label="前置条件" :span="2">{{
          detail.payload?.preconditions || '-'
        }}</a-descriptions-item>
        <a-descriptions-item label="数据策略" :span="2">{{
          detail.payload?.data_strategy || '-'
        }}</a-descriptions-item>
        <a-descriptions-item label="清理策略" :span="2">{{
          detail.payload?.cleanup_strategy || '-'
        }}</a-descriptions-item>
        <a-descriptions-item label="ApiCase">{{
          detail.api_case ? `#${detail.api_case} ${detail.api_case_name || ''}` : '未绑定'
        }}</a-descriptions-item>
        <a-descriptions-item label="Commit">{{
          shortCommit(detail.current_commit)
        }}</a-descriptions-item>
        <a-descriptions-item
          :label="detail.status === 'deferred' ? '暂不处理原因' : '备注'"
          :span="2"
          >{{ detail.payload?.remark || '-' }}</a-descriptions-item
        >
      </a-descriptions>
      <h4>代码证据</h4>
      <pre class="mango-code-panel mango-module-coverage__evidence">{{
        pretty(detail.payload?.code_evidence)
      }}</pre>
      <div v-if="detail.id && !failed" class="mango-module-coverage__drawer-actions">
        <a-button size="small" @click="emit('history', detail.id)">扫描历史</a-button>
        <a-button size="small" @click="emit('locate', detail)">定位到接口图</a-button>
        <a-button
          v-if="detail.api_case"
          size="small"
          type="primary"
          @click="emit('case', detail.api_case)"
          >打开 ApiCase</a-button
        >
      </div>
    </MangoPanelSpin>
  </a-drawer>
</template>
<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { ref } from 'vue'
  import MangoPanelSpin from '@/components/feedback/MangoPanelSpin.vue'
  import { useEnum } from '@/store/modules/get-enum'
  import { getCoverageCaseDetail } from '@/api/apitest/module-coverage'
  import { labels } from '../config'
  import type { CoverageRecord } from '../types'
  import { useCoveragePanelScope } from '../composables/useCoveragePanelScope'
  const emit = defineEmits<{
    (event: 'history', id: number): void
    (event: 'locate', row: CoverageRecord): void
    (event: 'case', id: number): void
  }>()
  const visible = ref(false),
    loading = ref(false),
    failed = ref(false),
    detail = ref<CoverageRecord>({ id: 0 }),
    selectedId = ref<number>()
  const enumStore = useEnum()
  const { begin, current, close } = useCoveragePanelScope(visible, () => {
    loading.value = false
  })
  const label = (value?: string) => (value ? labels[value] || value : '-')
  const shortCommit = (value?: string) => (value ? value.slice(0, 12) : '-')
  const pretty = (value: unknown) => JSON.stringify(value ?? [], null, 2)
  const enumTitle = (options: Array<{ key: string | number; title: string }>, value: unknown) =>
    options.find((item) => String(item.key) === String(value))?.title || '-'
  const enumTitles = (
    options: Array<{ key: string | number; title: string }>,
    values?: Array<string | number>
  ) => values?.map((value) => enumTitle(options, value)).join('、') || '-'
  async function load() {
    if (!visible.value || !selectedId.value) return
    const token = begin(),
      id = selectedId.value
    loading.value = true
    failed.value = false
    try {
      const response = await getCoverageCaseDetail(id)
      if (current(token)) detail.value = response.data
    } catch (loadFailure0) {
      if (current(token)) (reportLoadError(loadFailure0, "加载失败，请重试", false), failed.value = true)
    } finally {
      if (current(token)) loading.value = false
    }
  }
  function open(id: number) {
    selectedId.value = id
    detail.value = { id: 0 }
    visible.value = true
    return load()
  }
  defineExpose({ open, close })
</script>
<style scoped>
  .mango-module-coverage__evidence {
    min-height: 180px;
    max-height: 340px;
    overflow: auto;
    white-space: pre-wrap;
  }
  .mango-module-coverage__drawer-actions {
    display: flex;
    justify-content: flex-start;
    gap: var(--m-page-gap);
    margin-top: var(--m-page-gap);
  }
</style>
