<template>
  <a-drawer v-model:visible="visible" title="Case 扫描历史" width="900px" unmount-on-close>
    <a-spin :loading="loading" class="mango-coverage-history__spin">
      <a-table
        :data="rows"
        :columns="columns"
        :pagination="false"
        :scroll="{ x: 940 }"
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
    </a-spin>
  </a-drawer>
</template>

<script lang="ts" setup>
  import { ref } from 'vue'
  import type { TableColumnData } from '@arco-design/web-vue'
  import { getCoverageCaseSnapshots } from '@/api/apitest/module-coverage'
  import { labels, tagColor } from '../config'

  const columns: TableColumnData[] = [
    { title: '快照ID', dataIndex: 'id', width: 90, align: 'center' },
    { title: '扫描ID', dataIndex: 'scan', width: 90, align: 'center' },
    { title: 'Commit', dataIndex: 'commit_sha', slotName: 'commit_sha', width: 150 },
    {
      title: '变更状态',
      dataIndex: 'sync_action',
      slotName: 'sync_action',
      width: 120,
      align: 'center',
    },
    { title: '创建时间', dataIndex: 'create_time', width: 190 },
    { title: '内容哈希', dataIndex: 'content_hash', width: 300, ellipsis: true, tooltip: true },
  ]
  const visible = ref(false)
  const loading = ref(false)
  const coverageCaseId = ref<number>()
  const rows = ref<any[]>([])
  const page = ref(1)
  const pageSize = 10
  const total = ref(0)

  const label = (value: string) => labels[value] || value || '-'
  const shortCommit = (value?: string) => (value ? value.slice(0, 12) : '-')

  async function loadRows() {
    if (!coverageCaseId.value) return
    loading.value = true
    try {
      const response = await getCoverageCaseSnapshots(coverageCaseId.value, page.value, pageSize)
      rows.value = response.data?.items || []
      total.value = response.data?.count || 0
    } finally {
      loading.value = false
    }
  }

  async function open(id: number) {
    coverageCaseId.value = id
    page.value = 1
    visible.value = true
    await loadRows()
  }

  defineExpose({ open })
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
