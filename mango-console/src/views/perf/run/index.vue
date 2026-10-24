<template>
  <TableBody plain class="mango-detail-workbench-page mango-perf-page">
    <template #header><TableHeader title="性能测试 / 运行历史" @search="load" @reset-search="resetSearch"><template #search-content><a-form :model="filters" layout="inline"><a-form-item label="名称"><a-input v-model="filters.name" allow-clear /></a-form-item><a-form-item label="状态"><a-select v-model="filters.status" multiple :max-tag-count="1" :options="statusOptions" allow-clear /></a-form-item><a-form-item label="结论"><a-select v-model="filters.verdict" multiple :max-tag-count="1" :options="verdictOptions" allow-clear /></a-form-item></a-form></template></TableHeader></template>
    <template #default>
      <a-table :columns="runColumns" :data="rows" :loading="loading" :pagination="false" :scroll="{ x: runScrollX }" row-key="id">
        <template #columns><a-table-column v-for="column in runColumns" :key="column.key" v-bind="column">
          <template v-if="column.key === 'index'" #cell="{ record }"><a-link @click="open(record)">{{ record.id }}</a-link></template>
          <template v-else-if="column.key === 'project_product'" #cell="{ record }">{{ record.project_product?.name || '-' }}</template>
          <template v-else-if="column.key === 'module'" #cell="{ record }">{{ record.module_full_path || '-' }}</template>
          <template v-else-if="column.key === 'status'" #cell="{ record }"><a-tag :color="runStatusColor(record.status)" size="small">{{ runStatusTitle[record.status] || record.status }}</a-tag></template>
          <template v-else-if="column.key === 'verdict'" #cell="{ record }"><a-tag :color="runVerdictColor(record.verdict)" size="small">{{ verdictTitle[record.verdict] || record.verdict }}</a-tag></template>
          <template v-else-if="column.key === 'nodes'" #cell="{ record }">{{ record.actual_node_count }}/{{ record.requested_node_count }}</template>
          <template v-else-if="column.key === 'actions'" #cell="{ record }"><MangoTableActions :actions="[{ permission: 'perf.run:detail', label: '查看', onClick: () => open(record) }, { permission: 'perf.run:stop', label: '停止', danger: true, hidden: !activeRunStatuses.has(record.status), loading: stoppingId === record.id, onClick: () => stop(record) }]" /></template>
        </a-table-column></template>
      </a-table>
    </template>
    <template #footer><TableFooter :pagination="pagination" /></template>
  </TableBody>
</template>

<script setup lang="ts">
  import { Message } from '@arco-design/web-vue'
  import { onMounted, reactive, ref } from 'vue'
  import { useRouter } from 'vue-router'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import { usePagination } from '@/hooks/table'
  import { getPerfRuns, stopPerfRun } from '@/api/perf'
  import { activeRunStatuses, runStatusColor, runStatusTitle, runVerdictColor, verdictTitle } from '../types'
  import { runColumns, runScrollX } from './config'
  import { normalizeMultiSelectSearchParams } from '@/utils/search-condition'
  const router = useRouter(); const rows = ref<any[]>([]); const loading = ref(false); const stoppingId = ref<number>(); const filters = reactive<any>({ name: '', status: [], verdict: [] }); const pagination = usePagination(load, () => loading)
  const statusOptions = Object.entries(runStatusTitle).map(([value, label]) => ({ value, label })); const verdictOptions = Object.entries(verdictTitle).map(([value, label]) => ({ value, label }))
  async function load() { loading.value = true; try { const query = Object.fromEntries(Object.entries(normalizeMultiSelectSearchParams({ ...filters, page: pagination.page, pageSize: pagination.pageSize }, ['status', 'verdict'])).filter(([, value]) => value !== '' && value !== undefined)); const response: any = await getPerfRuns(query); rows.value = response.data || []; pagination.setTotalSize(response.totalSize || 0) } finally { loading.value = false } }
  function resetSearch() { Object.assign(filters, { name: '', status: [], verdict: [] }); load() }
  function open(record: any) { router.push({ path: '/perf/run/details', query: { id: record.id } }) }
  async function stop(record: any) { stoppingId.value = record.id; try { await stopPerfRun(record.id); Message.success('停止请求已提交'); load() } finally { stoppingId.value = undefined } }
  onMounted(load)
</script>
