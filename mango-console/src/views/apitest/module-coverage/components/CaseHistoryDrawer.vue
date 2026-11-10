<template>
  <a-drawer v-model:visible="visible" title="Case 扫描历史" width="900px" unmount-on-close>
    <template v-if="failed"><a-button size="small" :loading="loading" @click="loadRows">重新加载</a-button></template>
    <a-table
      :data="rows"
      :loading="loading"
      :columns="columns"
      :pagination="false"
      :scroll="{ x: caseSnapshotScrollX }"
      row-key="id"
    >
      <template #commit_sha="{ record }">{{ shortCommit(record.commit_sha) }}</template>
      <template #sync_action="{ record }">
        <a-tag size="small" :color="tagColor(record.sync_action)">{{
          label(record.sync_action)
        }}</a-tag>
      </template>
    </a-table>
    <a-pagination
      v-if="total > pageSize"
      v-model:current="page"
      :page-size="pageSize"
      :total="total"
      size="small"
      class="mango-coverage-history__pagination"
      @change="loadRows"
    />
  </a-drawer>
</template>

<script lang="ts" setup>
import { reportLoadError } from '@/utils/load-error'

  import { ref } from 'vue'
  import { getCoverageCaseSnapshots } from '@/api/apitest/module-coverage'
  import { caseSnapshotColumns as columns, caseSnapshotScrollX, labels, tagColor } from '../config'
  import { useCoveragePanelScope } from '../composables/useCoveragePanelScope'
  import type { CoverageSnapshot } from '../types'
  const visible = ref(false),
    loading = ref(false),
    failed = ref(false),
    coverageCaseId = ref<number>(),
    rows = ref<CoverageSnapshot[]>([])
  const page = ref(1),
    pageSize = 10,
    total = ref(0)
  const { begin, current, close } = useCoveragePanelScope(visible, () => {
    loading.value = false
  })
  const label = (value?: string) => (value ? labels[value] || value : '-')
  const shortCommit = (value?: string) => (value ? value.slice(0, 12) : '-')
  async function loadRows() {
    if (!visible.value || !coverageCaseId.value) return
    const token = begin(),
      id = coverageCaseId.value,
      requestedPage = page.value
    loading.value = true
    failed.value = false
    try {
      const response = await getCoverageCaseSnapshots(id, requestedPage, pageSize)
      if (current(token)) {
        rows.value = response.data?.items || []
        total.value = response.data?.count || 0
      }
    } catch (loadFailure0) {
      if (current(token)) (reportLoadError(loadFailure0, "加载失败，请重试", false), failed.value = true)
    } finally {
      if (current(token)) loading.value = false
    }
  }
  function open(id: number) {
    coverageCaseId.value = id
    page.value = 1
    rows.value = []
    total.value = 0
    visible.value = true
    return loadRows()
  }
  defineExpose({ open, close })
</script>
<style lang="less" scoped>
  .mango-coverage-history__spin {
    display: block;
    width: 100%;
  }
  .mango-coverage-history__pagination {
    display: flex;
    justify-content: flex-end;
    margin-top: var(--m-page-gap);
  }
</style>
