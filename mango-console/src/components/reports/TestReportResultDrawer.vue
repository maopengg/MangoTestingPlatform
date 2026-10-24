<template>
  <a-drawer
    v-model:visible="localVisible"
    :width="'min(1280px, 80vw)'"
    :footer="false"
    :title="drawerTitle"
    class="mango-test-report-result-drawer"
    unmount-on-close
  >
    <div class="mango-test-report-result-drawer__layout">
      <ExecutionHistoryList
        :items="historyItems"
        :selected-id="selectedResultId"
        :loading="historyLoading"
        empty-text="当前失败记录暂无可切换的执行结果"
        @select="changeResult"
      />
      <mango-panel-spin
        :loading="detailLoading"
        class="mango-test-report-result-drawer__spin"
        :class="{ 'mango-test-report-result-drawer__spin--api': normalizedCaseType === 1 }"
      >
        <div v-if="loadError" class="mango-test-report-result-drawer__feedback" role="alert">
          <icon-exclamation-circle-fill />
          <div>
            <strong>详细报告加载失败</strong>
            <span>{{ loadError }}</span>
          </div>
          <a-button size="small" type="primary" @click="loadDetail">重新加载</a-button>
        </div>
        <div v-else-if="!hasDetail && !detailLoading" class="mango-test-report-result-drawer__feedback">
          <icon-file />
          <div>
            <strong>本次失败没有生成详细结果</strong>
            <span>{{ resultData?.error_message || fallbackError || '后端未返回失败原因' }}</span>
          </div>
        </div>
        <ElementTestReport v-else-if="normalizedCaseType === 0" :result-data="resultData" />
        <ApiTestReport
          v-else-if="normalizedCaseType === 1"
          :result-data="resultData"
          contained
        />
        <PytestTestReport v-else-if="normalizedCaseType === 2" :result-data="resultData" />
      </mango-panel-spin>
    </div>
  </a-drawer>
</template>

<script lang="ts" setup>
  import { computed, ref, watch } from 'vue'
  import { IconExclamationCircleFill, IconFile } from '@arco-design/web-vue/es/icon'
  import {
    getSystemTestSuiteDetailsResultOptionsShare,
    getSystemTestSuiteDetailsResultShare,
  } from '@/api/system/test_sute_details'
  import ExecutionHistoryList from '@/components/business/ExecutionHistoryList.vue'
  import type { ExecutionHistoryItem } from '@/components/business/execution-history'
  import ElementTestReport from './ElementTestReport.vue'
  import ApiTestReport from './ApiTestReport.vue'
  import PytestTestReport from './PytestTestReport.vue'

  const props = withDefaults(
    defineProps<{
      visible?: boolean
      testSuiteDetailId?: number | string
      caseType?: number | string
      caseName?: string
      caseId?: number | string
      fallbackError?: string
    }>(),
    {
      visible: false,
      testSuiteDetailId: '',
      caseType: -1,
      caseName: '',
      caseId: '',
      fallbackError: '',
    }
  )

  const emit = defineEmits<{
    (event: 'update:visible', value: boolean): void
  }>()

  const localVisible = ref(false)
  const detailLoading = ref(false)
  const historyLoading = ref(false)
  const resultData = ref<any>({})
  const resultOptions = ref<any[]>([])
  const selectedResultId = ref<number | string>('')
  const loadError = ref('')
  let requestSequence = 0

  const normalizedCaseType = computed(() => Number(props.caseType))
  const drawerTitle = computed(() => {
    const name = props.caseName || (props.caseId ? `Case #${props.caseId}` : '测试用例')
    return `失败详情：${name}`
  })
  const historyItems = computed<ExecutionHistoryItem[]>(() =>
    resultOptions.value.map((item: any) => ({
      id: item.id,
      title: item.label || item.status_text || '执行结果',
      statusText: item.status_text || '未知',
      statusColor: statusColor(item.status_text),
      time: item.update_time || item.create_time || '-',
      actor: item.trigger_user_name || '',
      latest: Boolean(item.is_case_latest),
      sourceText: item.source_scope_name || '测试报告',
    }))
  )
  const hasDetail = computed(() => {
    const record = resultData.value || {}
    if (normalizedCaseType.value === 0) {
      return Boolean(
        (Array.isArray(record.element_result_list) && record.element_result_list.length) ||
          (Array.isArray(record.children) && record.children.length)
      )
    }
    if (normalizedCaseType.value === 1) {
      return Boolean(record.request || record.response || record.ass || record.error_message || record.name)
    }
    if (normalizedCaseType.value === 2) {
      return Boolean(
        record.attachments ||
          record.statusDetails ||
          record.fullName ||
          record.description ||
          record.error_message ||
          record.name
      )
    }
    return false
  })

  watch(
    () => props.visible,
    (visible) => {
      localVisible.value = visible
      if (visible) {
        resultData.value = {}
        resultOptions.value = []
        selectedResultId.value = ''
        loadError.value = ''
        loadDetail()
      }
    }
  )
  watch(localVisible, (visible) => emit('update:visible', visible))

  function statusColor(status: unknown) {
    const value = String(status || '')
    if (value.includes('通过') || value.includes('成功')) return 'green'
    if (value.includes('失败') || value.includes('错误')) return 'red'
    if (value.includes('警告')) return 'orange'
    if (value.includes('执行中') || value.includes('进行中')) return 'arcoblue'
    return 'gray'
  }

  async function loadDetail(resultId?: number | string) {
    const detailId = props.testSuiteDetailId
    if (!detailId) {
      loadError.value = '缺少测试报告明细 ID，无法加载最近失败结果'
      return
    }
    const sequence = ++requestSequence
    detailLoading.value = true
    loadError.value = ''
    if (!resultOptions.value.length) historyLoading.value = true
    try {
      const requests: Promise<any>[] = [
        getSystemTestSuiteDetailsResultShare(detailId, resultId),
      ]
      if (!resultOptions.value.length) {
        requests.push(getSystemTestSuiteDetailsResultOptionsShare(detailId))
      }
      const [detailResponse, optionsResponse] = await Promise.all(requests)
      if (sequence !== requestSequence) return
      if (optionsResponse) {
        resultOptions.value = optionsResponse.data || []
        selectedResultId.value = resultId || resultOptions.value[0]?.id || ''
      } else if (resultId) {
        selectedResultId.value = resultId
      }
      resultData.value = buildReportRecord(detailResponse.data || {})
    } catch (error: any) {
      if (sequence !== requestSequence) return
      loadError.value = error?.msg || error?.message || '请稍后重试'
    } finally {
      if (sequence === requestSequence) {
        detailLoading.value = false
        historyLoading.value = false
      }
    }
  }

  function changeResult(resultId: number | string) {
    loadDetail(resultId)
  }

  function buildReportRecord(detailRecord: any) {
    const children = Array.isArray(detailRecord?.children) ? detailRecord.children : []
    const matched = children[0] || detailRecord
    const baseRecord = {
      ...matched,
      case_type: normalizedCaseType.value,
      name: matched?.name || props.caseName || detailRecord?.case_name || detailRecord?.name,
      status: matched?.status ?? detailRecord?.status,
      error_message:
        matched?.error_message ||
        matched?.statusDetails?.message ||
        detailRecord?.error_message ||
        props.fallbackError,
      test_suite_detail_id: detailRecord?.id || props.testSuiteDetailId,
    }
    if (normalizedCaseType.value !== 0) return baseRecord
    return {
      ...baseRecord,
      test_time: baseRecord.test_time || detailRecord?.test_time,
      test_object: baseRecord.test_object || detailRecord?.test_object,
      video_path: baseRecord.video_path || detailRecord?.video_path,
      cache_data: baseRecord.cache_data || detailRecord?.cache_data,
      data_factory_cache_data:
        baseRecord.data_factory_cache_data || detailRecord?.data_factory_cache_data,
      element_result_list: [baseRecord],
      children: [baseRecord],
    }
  }
</script>

<style scoped>
  .mango-test-report-result-drawer__layout {
    box-sizing: border-box;
    display: grid;
    height: 100%;
    min-height: 0;
    padding: var(--m-page-gap);
    grid-template-columns: 260px minmax(0, 1fr);
    gap: var(--m-page-gap);
    background: var(--m-bg);
  }

  .mango-test-report-result-drawer__spin {
    display: block;
    min-width: 0;
    min-height: 0;
    overflow: auto;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-lg);
    background: var(--m-surface);
  }

  .mango-test-report-result-drawer__spin :deep(> .mango-panel-spin__content) {
    display: block;
    min-height: 100%;
  }

  .mango-test-report-result-drawer__spin--api {
    height: 100%;
    min-height: 0;
    overflow: hidden;
  }

  .mango-test-report-result-drawer__spin--api :deep(> .mango-panel-spin__content) {
    height: 100%;
    min-height: 0;
    overflow: hidden;
  }

  .mango-test-report-result-drawer__feedback {
    box-sizing: border-box;
    display: flex;
    min-height: 180px;
    margin: 12px;
    padding: 24px;
    align-items: center;
    justify-content: center;
    gap: 12px;
    border: 1px dashed var(--m-border);
    border-radius: var(--m-radius-lg);
    color: var(--m-muted);
    text-align: left;
  }

  .mango-test-report-result-drawer__feedback > svg {
    flex: none;
    color: var(--m-danger);
    font-size: 24px;
  }

  .mango-test-report-result-drawer__feedback > div {
    display: flex;
    max-width: 560px;
    flex: 1;
    flex-direction: column;
    gap: 4px;
  }

  .mango-test-report-result-drawer__feedback strong {
    color: var(--m-text);
  }

  :global(.mango-test-report-result-drawer .arco-drawer-body) {
    min-height: 0;
    padding: 0;
    overflow: hidden;
  }

  @media (max-width: 1100px) {
    .mango-test-report-result-drawer__layout {
      min-width: 920px;
    }
  }
</style>
