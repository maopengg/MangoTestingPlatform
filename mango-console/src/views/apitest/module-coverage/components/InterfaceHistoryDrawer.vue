<template>
  <a-drawer
    v-model:visible="visible"
    title="接口扫描历史"
    width="920px"
    :footer="false"
    unmount-on-close
  >
    <a-spin :loading="loading" class="mango-interface-history__body">
      <a-alert v-if="!loading && !rows.length" type="info">该接口暂无历史快照</a-alert>
      <a-table
        v-else
        :data="rows"
        :pagination="false"
        :scroll="{ x: 1050, y: 'calc(100vh - 180px)' }"
        row-key="id"
        size="small"
      >
        <template #columns>
          <a-table-column title="快照ID" data-index="id" :width="90" />
          <a-table-column title="扫描" :width="90">
            <template #cell="{ record }">#{{ record.scan }}</template>
          </a-table-column>
          <a-table-column title="变更" :width="100">
            <template #cell="{ record }">
              <a-tag size="small" :color="tagColor(record.sync_action)">
                {{ label(record.sync_action) }}
              </a-tag>
            </template>
          </a-table-column>
          <a-table-column title="链路状态" :width="120">
            <template #cell="{ record }">
              <a-tag size="small" :color="tagColor(record.resolution_status)">
                {{ label(record.resolution_status) }}
              </a-tag>
            </template>
          </a-table-column>
          <a-table-column title="Method" :width="90">
            <template #cell="{ record }">
              <a-tag size="small" :color="methodTagColor(record.method, enumStore.colors)">
                {{ record.method }}
              </a-tag>
            </template>
          </a-table-column>
          <a-table-column title="URL" data-index="url" :width="250" ellipsis tooltip />
          <a-table-column title="Commit" :width="130">
            <template #cell="{ record }">{{ shortCommit(record.commit_sha) }}</template>
          </a-table-column>
          <a-table-column title="创建时间" data-index="create_time" :width="170" />
          <a-table-column title="操作" :width="100" fixed="right">
            <template #cell="{ record, rowIndex }">
              <a-button
                size="mini"
                type="text"
                :disabled="rowIndex === rows.length - 1"
                @click="openDiff(record.id, rows[rowIndex + 1]?.id)"
              >
                对比前版
              </a-button>
            </template>
          </a-table-column>
        </template>
      </a-table>
    </a-spin>
  </a-drawer>

  <a-modal
    v-model:visible="diffVisible"
    title="接口快照差异"
    width="min(1180px, calc(100vw - 48px))"
    :footer="false"
    unmount-on-close
  >
    <a-spin :loading="diffLoading">
      <div class="mango-interface-history__diff-summary">
        <a-descriptions
          v-for="item in diffItems"
          :key="item.title"
          :title="item.title"
          :column="1"
          bordered
          size="small"
        >
          <a-descriptions-item label="快照">#{{ item.data?.id || '-' }}</a-descriptions-item>
          <a-descriptions-item label="扫描">#{{ item.data?.scan || '-' }}</a-descriptions-item>
          <a-descriptions-item label="Commit">{{
            item.data?.commit_sha || '-'
          }}</a-descriptions-item>
          <a-descriptions-item label="接口"
            >{{ item.data?.method || '-' }} {{ item.data?.url || '-' }}</a-descriptions-item
          >
          <a-descriptions-item label="内容Hash">{{
            item.data?.content_hash || '-'
          }}</a-descriptions-item>
        </a-descriptions>
      </div>
      <div class="mango-interface-history__diff-code">
        <section v-for="item in diffItems" :key="`${item.title}-code`">
          <strong>{{ item.title }} Mermaid</strong>
          <pre class="mango-code-panel">{{ item.data?.mermaid || '无' }}</pre>
        </section>
      </div>
    </a-spin>
  </a-modal>
</template>

<script lang="ts" setup>
  import { computed, ref } from 'vue'
  import { useEnum } from '@/store/modules/get-enum'
  import {
    getCoverageInterfaceDiff,
    getCoverageInterfaceSnapshots,
  } from '@/api/apitest/module-coverage'
  import { labels, methodTagColor, tagColor } from '../config'

  const enumStore = useEnum()

  const visible = ref(false)
  const loading = ref(false)
  const rows = ref<any[]>([])
  const interfaceId = ref<number>()
  const diffVisible = ref(false)
  const diffLoading = ref(false)
  const diff = ref<any>({})
  const label = (value: string) => labels[value] || value || '-'
  const shortCommit = (value?: string) => (value ? value.slice(0, 12) : '-')
  const diffItems = computed(() => [
    { title: '当前版本', data: diff.value.current },
    { title: '前一版本', data: diff.value.previous },
  ])

  async function open(id: number) {
    interfaceId.value = id
    visible.value = true
    loading.value = true
    try {
      const response = await getCoverageInterfaceSnapshots(id, 1, 100)
      rows.value = response.data?.items || []
    } finally {
      loading.value = false
    }
  }

  async function openDiff(currentId: number, previousId?: number) {
    if (!interfaceId.value || !previousId) return
    diffVisible.value = true
    diffLoading.value = true
    try {
      diff.value =
        (await getCoverageInterfaceDiff(interfaceId.value, currentId, previousId)).data || {}
    } finally {
      diffLoading.value = false
    }
  }

  defineExpose({ open })
</script>

<style lang="less" scoped>
  .mango-interface-history__body {
    display: block;
    min-height: 280px;
  }
  .mango-interface-history__diff-summary,
  .mango-interface-history__diff-code {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: var(--m-page-gap);
  }
  .mango-interface-history__diff-code {
    margin-top: var(--m-page-gap);
  }
  .mango-interface-history__diff-code section {
    min-width: 0;
  }
  .mango-interface-history__diff-code pre {
    height: 420px;
    overflow: auto;
    white-space: pre-wrap;
  }
</style>
