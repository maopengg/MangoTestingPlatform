<template>
  <TableBody content-flush>
    <template #header
      ><TableHeader title="评测数据集" @search="autoSearch.run" @reset-search="autoSearch.cancel(); onResetSearch(); autoSearch.sync()"
        ><template #search-content>
          <a-form :model="filters" layout="inline" size="small" @keyup.enter="autoSearch.run">
            <a-form-item label="数据集名称"
              ><a-input @blur="autoSearch.schedule" @clear="autoSearch.schedule" @mouseleave="autoSearch.schedule" v-model="filters.name" allow-clear placeholder="请输入数据集名称"
            /></a-form-item>
            <a-form-item label="任务类型"
              ><a-input-tag @change="autoSearch.schedule"
                v-model="filters.task_type"
                :max-tag-count="1"
                allow-clear
                placeholder="输入任务类型后回车"
            /></a-form-item>
            <a-form-item label="状态"
              ><a-select @change="autoSearch.schedule"
                v-model="filters.status"
                :options="datasetStatusOptions"
                multiple
                :max-tag-count="1"
                allow-clear
            /></a-form-item>
          </a-form> </template></TableHeader
    ></template>
    <template #default>
      <TableTabs>
        <template #extra
          ><a-button type="primary" size="small" @click="openCreate">新建数据集</a-button></template
        >
      </TableTabs>
      
      <a-table
        :columns="datasetColumns"
        :data="rows"
        :loading="loading"
        :pagination="false"
        :bordered="false"
        :scroll="{ x: DATASET_SCROLL_X }"
        row-key="id"
        size="small"
      >
        <template #columns>
          <a-table-column v-for="column in datasetColumns" :key="column.key" v-bind="column">
            <template #cell="{ record }">
              <span v-if="column.key === 'index'">{{ record.id }}</span>
              <span v-else-if="column.key === 'current_version'">{{
                formatVersion(record.current_version)
              }}</span>
              <span v-else-if="column.key === 'update_time'" :title="record.update_time">{{
                formatEvaluationDate(record.update_time)
              }}</span>
              <a-link v-else-if="column.key === 'name'" @click="openVersions(record)">{{
                record.name
              }}</a-link>
              <a-tag
                v-else-if="column.key === 'status'"
                size="small"
                :color="statusColor(record.status)"
                >{{ statusTitle(record.status) }}</a-tag
              >
              <a-tooltip
                v-else-if="column.key === 'task_type' && record.task_type?.length"
                :content="record.task_type.join('、')"
              >
                <span class="mango-dataset-task-tags"
                  ><a-tag v-for="type in record.task_type.slice(0, 2)" :key="type" size="small">{{
                    type
                  }}</a-tag
                  ><a-tag
                    v-if="record.task_type.length > 2"
                    class="mango-dataset-task-tags__more"
                    size="small"
                    >+{{ record.task_type.length - 2 }}</a-tag
                  ></span
                >
              </a-tooltip>
              <span v-else-if="column.key === 'task_type'">-</span>
              <template v-else-if="column.key === 'actions'"
                ><MangoTableActions
                  :actions="[
                    {
                      label: '条目',
                      onClick: () => openVersions(record),
                    },
                    {
                      label: '编辑',
                      disabled: rowBusy(record.id),
                      onClick: () => openEdit(record),
                    },
                    {
                      label: record.status === 'archived' ? '恢复' : '归档',
                      loading: statusSaving.has(record.id),
                      disabled: rowBusy(record.id),
                      onClick: () => changeDatasetStatus(record),
                    },
                    {
                      label: '删除',
                      danger: true,
                      loading: deleting.has(record.id),
                      disabled: rowBusy(record.id) || confirmationOpen,
                      onClick: () => remove(record),
                    },
                  ]"
              /></template>
              <span v-else>{{ record[column.dataIndex as string] ?? '-' }}</span>
            </template>
          </a-table-column>
        </template>
      </a-table> </template
    ><template #footer><TableFooter :pagination="pagination" /></template>
  </TableBody>
  <DatasetEditor ref="editor" :context-key="contextKey" @saved="load" />
</template>

<script setup lang="ts">
  import { useDebouncedSearch } from '@/hooks/useDebouncedSearch'

import { reportLoadError } from '@/utils/load-error'

  import { computed, reactive, ref } from 'vue'
  import { useRouter } from 'vue-router'
  import { Modal } from '@arco-design/web-vue'
  import {
    deleteEvaluationDataset,
    getEvaluationDatasets,
    updateEvaluationDataset,
  } from '@/api/evaluation'
  import useUserStore from '@/store/modules/user'
  import TableTabs from '@/components/table/TableTabs.vue'
  import DatasetEditor from './components/DatasetEditor.vue'
  import { useEvaluationEnums } from '../components/useEvaluationEnums'
  import { useEvaluationScope } from '../composables/useEvaluationScope'
  import { formatVersion, formatEvaluationDate } from '../components/presentation'
  import { DATASET_SCROLL_X, datasetColumns } from './config'
  import {
    createDatasetFilters,
    datasetQuery,
    normalizeLabels,
    restoredDatasetStatus,
  } from './form'
  import type { EvaluationDatasetRecord, EvaluationDatasetRow } from './types'

  const router = useRouter(),
    user = useUserStore()
  const { title: enumTitle, color: statusColor, options: enumOptions } = useEvaluationEnums()
  const datasetStatusOptions = computed(() => enumOptions('evaluation_case_status'))
  const statusTitle = (value: string) => enumTitle('evaluation_case_status', value)
  const rows = ref<EvaluationDatasetRow[]>([]),
    loading = ref(false),
    listError = ref('')
  const filters = reactive(createDatasetFilters()),
    contextKey = ref(0)
  const editor = ref<InstanceType<typeof DatasetEditor>>()
  const statusSaving = reactive(new Set<number>()),
    deleting = reactive(new Set<number>())
  const pagination = reactive({
    page: 1,
    pageSize: 10,
    pageCount: 0,
    pageSizes: [10, 20, 50],
    showSizePicker: true,
    onChange: () => load(),
  })
  let listRequest = 0,
    confirmationToken = 0
  let confirmation: { close(): void } | undefined
  const confirmationOpen = ref(false)
  const identity = () => JSON.stringify([user.userId, user.roleId, user.token])
  let loadedIdentity = identity()
  function reset() {
    ++contextKey.value
    ++listRequest
    ++confirmationToken
    confirmation?.close()
    confirmation = undefined
    confirmationOpen.value = false
    editor.value?.close()
    rows.value = []
    loading.value = false
    listError.value = ''
    pagination.pageCount = 0
    if (loadedIdentity !== identity()) {
      loadedIdentity = identity()
      Object.assign(filters, createDatasetFilters())
      pagination.page = 1
    }
  }
  const scope = useEvaluationScope(
    () => [],
    reset,
    () => {
      void load()
    }
  )
  function rowBusy(id: number) {
    return statusSaving.has(id) || deleting.has(id) || Boolean(editor.value?.isSaving(id))
  }
  async function load() {
    if (!scope.isActive()) return false
    const request = ++listRequest,
      current = scope.snapshot()
    const query = datasetQuery(filters, pagination.page, pagination.pageSize)
    loading.value = true
    listError.value = ''
    try {
      const response: { data?: EvaluationDatasetRecord[]; totalSize?: number } =
        await getEvaluationDatasets(query)
      if (request !== listRequest || !scope.current(current)) return false
      rows.value = (response.data || []).map((record) => ({
        ...record,
        task_type: normalizeLabels(record.task_type),
      }))
      pagination.pageCount = response.totalSize ?? rows.value.length
      return true
    } catch (loadFailure0) {
      if (request === listRequest && scope.current(current))
        void (reportLoadError(loadFailure0, "数据集加载失败，请重试", false), listError.value = '数据集加载失败，请重试')
      return false
    } finally {
      if (request === listRequest && scope.current(current)) loading.value = false
    }
  }
  function onSearch() {
    pagination.page = 1
    return load()
  }
  function onResetSearch() {
    Object.assign(filters, createDatasetFilters())
    return onSearch()
  }
  function openCreate() {
    if (scope.isActive()) editor.value?.open()
  }
  function openEdit(record: EvaluationDatasetRecord) {
    if (scope.isActive() && !rowBusy(record.id)) editor.value?.open(record)
  }
  async function changeDatasetStatus(record: EvaluationDatasetRecord) {
    if (!scope.isActive() || rowBusy(record.id)) return false
    const id = record.id,
      status = restoredDatasetStatus(record),
      current = scope.snapshot()
    statusSaving.add(id)
    try {
      await updateEvaluationDataset({ id, status })
      if (!scope.current(current)) return false
      const row = rows.value.find((item) => item.id === id)
      if (row) row.status = status
      await load()
      return true
    } catch {
      return false
    } finally {
      statusSaving.delete(id)
    }
  }
  function remove(record: EvaluationDatasetRecord) {
    if (!scope.isActive() || rowBusy(record.id) || confirmationOpen.value) return
    const id = record.id,
      name = record.name,
      current = scope.snapshot(),
      token = ++confirmationToken
    let pending = false,
      successful = false
    confirmationOpen.value = true
    confirmation = Modal.warning({
      title: '删除数据集',
      content: `确认删除“${name}”吗？有关联版本或用例时后端会阻止删除。`,
      hideCancel: false,
      onBeforeOk: async () => {
        if (
          pending ||
          successful ||
          token !== confirmationToken ||
          !scope.current(current) ||
          rowBusy(id)
        )
          return false
        pending = true
        deleting.add(id)
        try {
          await deleteEvaluationDataset(id)
          successful = true
          if (!scope.current(current)) return false
          if (rows.value.length === 1 && rows.value[0].id === id && pagination.page > 1)
            pagination.page--
          await load()
          return true
        } catch {
          return false
        } finally {
          pending = false
          deleting.delete(id)
        }
      },
      onClose: () => {
        if (token === confirmationToken) {
          ++confirmationToken
          confirmationOpen.value = false
          confirmation = undefined
        }
      },
    })
  }
  function openVersions(record: EvaluationDatasetRecord) {
    if (scope.isActive())
      return router.push({
        path: '/evaluation/dataset/details',
        query: { id: record.id, name: record.name },
      })
  }
  scope.start()

  const autoSearch = useDebouncedSearch(onSearch, () => filters)
</script>

<style scoped>
  .mango-dataset-task-tags {
    display: inline-flex;
    align-items: center;
    gap: var(--m-space-xs);
    max-width: 100%;
    min-width: 0;
    vertical-align: middle;
  }
  .mango-dataset-task-tags :deep(.arco-tag) {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .mango-dataset-task-tags__more {
    flex-shrink: 0;
  }
</style>
