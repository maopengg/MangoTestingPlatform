<template>
  <a-drawer
    v-model:visible="visible"
    title="接口扫描历史"
    width="920px"
    :footer="false"
    unmount-on-close
  >
    <MangoPanelSpin :loading="loading" class="mango-interface-history__body">
      <template v-if="failed"><a-button size="small" :loading="loading" @click="loadRows">重新加载</a-button></template>
      <a-alert v-if="!loading && !failed && !rows.length" type="info">该接口暂无历史快照</a-alert>
      <a-table
        v-else
        class="mango-native-scroll-table"
        :data="rows"
        :pagination="false"
        :scroll="{ x: 1200, y: 'calc(100vh - 240px)' }"
        row-key="id"
        size="small"
      >
        <template #columns>
          <a-table-column title="快照ID" data-index="id" :width="90" align="center" />
          <a-table-column title="扫描" :width="90" align="center">
            <template #cell="{ record }">#{{ record.scan }}</template>
          </a-table-column>
          <a-table-column title="变更" :width="100" align="center">
            <template #cell="{ record }">
              <a-tag size="small" :color="tagColor(record.sync_action)">
                {{ label(record.sync_action) }}
              </a-tag>
            </template>
          </a-table-column>
          <a-table-column title="调用链解析" :width="120" align="center">
            <template #cell="{ record }">
              <a-tag size="small" :color="tagColor(record.resolution_status)">
                {{ label(record.resolution_status) }}
              </a-tag>
            </template>
          </a-table-column>
          <a-table-column title="Method" :width="90" align="center">
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
          <a-table-column title="操作" :width="160" align="center" fixed="right">
            <template #cell="{ record, rowIndex }">
              <MangoTableActions
                :actions="[
                  {
                    label: '对比前版',
                    disabled: rowIndex === rows.length - 1,
                    onClick: () => openDiff(record.id, rows[rowIndex + 1]?.id),
                  },
                ]"
              />
            </template>
          </a-table-column>
        </template>
      </a-table>
    </MangoPanelSpin>
    <a-pagination
      v-if="total > pageSize"
      v-model:current="page"
      :page-size="pageSize"
      :total="total"
      size="small"
      @change="loadRows"
    />
  </a-drawer>

  <a-modal
    v-model:visible="diffVisible"
    title="接口快照差异"
    width="min(1180px, calc(100vw - 48px))"
    :footer="false"
    unmount-on-close
  >
    <MangoPanelSpin :loading="diffLoading">
      <template v-if="diffFailed"><a-button size="small" :loading="diffLoading" @click="loadDiff">重新加载</a-button></template>
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
    </MangoPanelSpin>
  </a-modal>
</template>

<script lang="ts" setup>
import { reportLoadError } from '@/utils/load-error'

  import { computed, ref } from 'vue'
  import MangoPanelSpin from '@/components/feedback/MangoPanelSpin.vue'
  import { useEnum } from '@/store/modules/get-enum'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import {
    getCoverageInterfaceDiff,
    getCoverageInterfaceSnapshots,
  } from '@/api/apitest/module-coverage'
  import { labels, methodTagColor, tagColor } from '../config'
  import { useCoveragePanelScope } from '../composables/useCoveragePanelScope'
  import type { CoverageDiff, CoverageSnapshot } from '../types'
  const enumStore = useEnum()
  const visible = ref(false),
    loading = ref(false),
    failed = ref(false),
    rows = ref<CoverageSnapshot[]>([]),
    interfaceId = ref<number>()
  const diffVisible = ref(false),
    diffLoading = ref(false),
    diffFailed = ref(false),
    diff = ref<CoverageDiff>({})
  const page = ref(1),
    pageSize = 100,
    total = ref(0)
  const diffScope = useCoveragePanelScope(diffVisible, () => {
    diffLoading.value = false
  })
  const { begin, current, close } = useCoveragePanelScope(visible, () => {
    loading.value = false
    diffScope.close()
  })
  const label = (value?: string) => (value ? labels[value] || value : '-')
  const shortCommit = (value?: string) => (value ? value.slice(0, 12) : '-')
  const diffItems = computed(() => [
    { title: '当前版本', data: diff.value.current },
    { title: '前一版本', data: diff.value.previous },
  ])
  async function loadRows() {
    if (!visible.value || !interfaceId.value) return
    const token = begin(),
      id = interfaceId.value
    loading.value = true
    failed.value = false
    diffScope.close()
    try {
      const response = await getCoverageInterfaceSnapshots(id, page.value, pageSize)
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
    interfaceId.value = id
    rows.value = []
    total.value = 0
    page.value = 1
    visible.value = true
    return loadRows()
  }
  let diffTarget: { id: number; currentId: number; previousId: number } | null = null
  async function loadDiff() {
    if (!visible.value || !diffVisible.value || !diffTarget) return
    const token = diffScope.begin(),
      target = { ...diffTarget }
    diffLoading.value = true
    diffFailed.value = false
    try {
      const response = await getCoverageInterfaceDiff(
        target.id,
        target.currentId,
        target.previousId
      )
      if (diffScope.current(token)) diff.value = response.data || {}
    } catch (loadFailure1) {
      if (diffScope.current(token)) (reportLoadError(loadFailure1, "加载失败，请重试", false), diffFailed.value = true)
    } finally {
      if (diffScope.current(token)) diffLoading.value = false
    }
  }
  function openDiff(currentId: number, previousId?: number) {
    if (!visible.value || !interfaceId.value || !previousId) return
    diffTarget = { id: interfaceId.value, currentId, previousId }
    diff.value = {}
    diffVisible.value = true
    return loadDiff()
  }
  defineExpose({ open, close })
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
