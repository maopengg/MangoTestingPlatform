<template>
  <BaseSidePanel
    :visible="visible"
    :title="title"
    :width="920"
    cancel-button-text="关闭"
    @update:visible="
      (value) => {
        if (!value) close()
      }
    "
    @cancel="close"
  >
    <div class="mango-bound-case-summary">共 {{ total }} 个绑定 Case</div>
    <a-table
      :columns="boundCaseColumns"
      :data="rows"
      :loading="loading"
      :pagination="false"
      :bordered="false"
      :scroll="{ x: 850 }"
      row-key="case_id"
      size="small"
    >
      <template #case_id="{ record }"
        ><a-link @click="openCase(record)">{{ record.case_id }}</a-link></template
      >
      <template #actions="{ record }"
        ><MangoTableActions :actions="[{ label: '步骤', onClick: () => openCase(record) }]"
      /></template>
      <template #empty
        ><div class="mango-empty-state"
          >{{ failed ? '' : '暂无绑定用例'
          }}<a-button v-if="failed" size="small" @click="load">重试</a-button></div
        ></template
      >
    </a-table>
  </BaseSidePanel>
  <BaseSidePanel
    :visible="casePanel.visible"
    :title="casePanel.name ? `API 用例详情 / ${casePanel.name}` : 'API 用例详情'"
    width="calc(92vw - 150px)"
    mode="page"
    @update:visible="(value) => (casePanel.visible = value)"
    @cancel="casePanel.visible = false"
  >
    <ApiCaseDetails
      v-if="casePanel.visible && casePanel.id != null"
      :key="casePanel.id"
      embedded
      :case-id="casePanel.id"
      :project-product-id="casePanel.product"
      @close="casePanel.visible = false"
    />
  </BaseSidePanel>
</template>
<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { reactive, ref, onBeforeUnmount, onDeactivated } from 'vue'
  import { getApiInfoBoundCases } from '@/api/apitest/info'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import ApiCaseDetails from '@/views/apitest/case/details/index.vue'
  import { boundCaseColumns } from '../config'
  import type { ApiInfoListRow, BoundApiCase, ApiEntityId } from '../types'
  const visible = ref(false),
    loading = ref(false),
    failed = ref(false),
    title = ref('绑定Case'),
    total = ref(0)
  const rows = ref<BoundApiCase[]>([])
  const casePanel = reactive<{
    visible: boolean
    id: ApiEntityId | null
    name: string
    product: ApiEntityId | ''
  }>({ visible: false, id: null, name: '', product: '' })
  let target: ApiEntityId | null = null,
    request = 0
  function close() {
    request++
    visible.value = false
    loading.value = false
    rows.value = []
    total.value = 0
    casePanel.visible = false
  }
  async function open(record: ApiInfoListRow) {
    close()
    target = record.id
    title.value = `绑定Case - ${record.name || record.id}`
    visible.value = true
    await load()
  }
  async function load() {
    if (target == null || !visible.value) return
    const current = ++request,
      id = target
    loading.value = true
    failed.value = false
    try {
      const response = await getApiInfoBoundCases(id)
      if (current !== request) return
      rows.value = response.data || []
      total.value = response.totalSize ?? rows.value.length
    } catch (loadFailure0) {
      if (current === request) (reportLoadError(loadFailure0, "加载失败，请重试", false), failed.value = true)
    } finally {
      if (current === request) loading.value = false
    }
  }
  function openCase(record: BoundApiCase) {
    if (record.case_id == null) return
    Object.assign(casePanel, {
      visible: true,
      id: record.case_id,
      name: record.case_name,
      product: record.project_product_id ?? '',
    })
  }
  onBeforeUnmount(close)
  onDeactivated(close)
  defineExpose({ open, close })
</script>
<style scoped>
  .mango-bound-case-summary {
    margin-bottom: var(--m-page-gap);
    color: var(--m-muted);
    font-size: 13px;
  }
</style>
