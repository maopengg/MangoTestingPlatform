<template>
  <TableBody content-flush>
    <template #header
      ><TableHeader title="评测数据集" @search="onSearch" @reset-search="onResetSearch"
        ><template #search-content>
          <a-form :model="filters" layout="inline" size="small" @keyup.enter="onSearch">
            <a-form-item label="数据集名称"
              ><a-input v-model="filters.name" allow-clear placeholder="请输入数据集名称"
            /></a-form-item>
            <a-form-item label="任务类型"
              ><a-input-tag
                v-model="filters.task_type"
                :max-tag-count="1"
                allow-clear
                placeholder="输入任务类型后回车"
            /></a-form-item>
            <a-form-item label="状态"
              ><a-select
                v-model="filters.status"
                :options="datasetStatusOptions"
                multiple
                :max-tag-count="1"
                allow-clear
            /></a-form-item>
          </a-form> </template
        ></TableHeader
      ></template
    >
    <template #default>
      <TableTabs>
        <template #extra><a-button

            type="primary"
            size="small"
            @click="openCreate"
            >新建数据集</a-button
          ></template>
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
              <span v-else-if="column.key === 'current_version'">{{ formatVersion(record.current_version) }}</span>
              <span v-else-if="column.key === 'update_time'" :title="record.update_time">{{ formatEvaluationDate(record.update_time) }}</span>
              <a-link
                v-else-if="column.key === 'name'"
                @click="openVersions(record)"
                >{{ record.name }}</a-link
              >
              <a-tag
                v-else-if="column.key === 'status'"
                size="small"
                :color="statusColor(record.status)"
                >{{ statusTitle(record.status) }}</a-tag
              >
              <a-tooltip v-else-if="column.key === 'task_type' && record.task_type?.length" :content="record.task_type.join('、')">
                <span class="mango-dataset-task-tags"><a-tag v-for="type in record.task_type.slice(0, 2)" :key="type" size="small">{{
                  type
                }}</a-tag
                ><a-tag v-if="record.task_type.length > 2" class="mango-dataset-task-tags__more" size="small">+{{ record.task_type.length - 2 }}</a-tag></span>
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
        onClick: () => openEdit(record),
    },
    {
        label: record.status === 'archived' ? '恢复' : '归档',
        loading: statusSaving.has(record.id),
        onClick: () => changeDatasetStatus(record),
    },
    {
        label: '删除',
        danger: true,
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
  <ModalDialog
    ref="createDialogRef"
    :title="form.id ? '编辑评测数据集' : '新建评测数据集'"
    width="560px"
    @confirm="saveDataset"
  >
    <template #content
      ><a-form :model="form" layout="horizontal" auto-label-width>
        <a-grid :cols="1" :col-gap="12">
          <a-grid-item
            ><a-form-item label="数据集名称" required><a-input v-model="form.name" /></a-form-item
          ></a-grid-item>
          <a-grid-item
            ><a-form-item label="任务类型" required
              ><a-input-tag
                :model-value="form.task_type"
                :unique-value="true"
                placeholder="自由输入，如：记忆，问答；回车确认"
                @update:model-value="updateTaskTypes" /></a-form-item
          ></a-grid-item>
          <a-grid-item v-if="form.id"
            ><a-form-item label="状态"
              ><a-select
                v-model="form.status"
                :options="datasetStatusOptions"
                :disabled="false" /></a-form-item
          ></a-grid-item>
          <a-grid-item
            ><a-form-item label="说明"><a-textarea v-model="form.description" /></a-form-item
          ></a-grid-item>
        </a-grid> </a-form
    ></template>
  </ModalDialog>
</template>

<script setup lang="ts">
  import { Message, Modal } from '@arco-design/web-vue'
  import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
  import { useRouter } from 'vue-router'
  import {
    createEvaluationDataset,
    deleteEvaluationDataset,
    getEvaluationDatasets,
    updateEvaluationDataset,
  } from '@/api/evaluation'
  import { DATASET_SCROLL_X, datasetColumns } from './config'
  import type { ModalDialogType } from '@/types/components'
  import usePermissionStore from '@/store/modules/permission'
  import { useEvaluationEnums } from '../components/useEvaluationEnums'
  import { formatVersion, formatEvaluationDate } from '../components/presentation'
  import TableTabs from '@/components/table/TableTabs.vue'
  const router = useRouter(),
    permissions = usePermissionStore()
  const savingDataset = ref(false),
    statusSaving = reactive(new Set<number>())
  const { title: enumTitle, color: statusColor, options: enumOptions } = useEvaluationEnums()
  const datasetStatusOptions = computed(() => enumOptions('evaluation_case_status'))
  const statusTitle = (value: string) => enumTitle('evaluation_case_status', value)
  const rows = ref<any[]>([]),
    loading = ref(false)
  const createDialogRef = ref<ModalDialogType | null>(null)
  let listRequest = 0
  const filters = reactive<any>({
    name: '',
    task_type: [],
    status: [],
  })
  const pagination = reactive({
    page: 1,
    pageSize: 10,
    pageCount: 0,
    pageSizes: [10, 20, 50],
    showSizePicker: true,
    onChange: () => load(),
  })
  const form = reactive<any>({
    name: '',
    task_type: [],
    description: '',
  })
  async function load() {
    const request = ++listRequest
    loading.value = true
    try {
      const query: any = {
        name: filters.name || undefined,
        task_types: filters.task_type.length
          ? JSON.stringify(normalizeLabels(filters.task_type))
          : undefined,
        status__in: filters.status.length ? filters.status.join(',') : undefined,
        page: pagination.page,
        pageSize: pagination.pageSize,
      }
      const res: any = await getEvaluationDatasets(query)
      if (request !== listRequest) return
      rows.value = (res.data || []).map((record: any) => ({
        ...record,
        task_type: normalizeLabels(record.task_type),
      }))
      pagination.pageCount = res.totalSize || rows.value.length
    } finally {
      if (request === listRequest) loading.value = false
    }
  }
  function onSearch() {
    pagination.page = 1
    load()
  }
  function onResetSearch() {
    Object.assign(filters, {
      name: '',
      task_type: [],
      status: [],
    })
    onSearch()
  }
  function openCreate() {
    if (savingDataset.value) return
    Object.assign(form, {
      id: undefined,
      version_count: 0,
      status: 'draft',
      name: '',
      task_type: [],
      description: '',
    })
    createDialogRef.value?.show()
  }
  function openEdit(record: any) {
    if (savingDataset.value)
    return;
    Object.assign(form, {
      id: record.id,
      name: record.name,
      task_type: normalizeLabels(record.task_type),
      description: record.description || '',
      status: record.status,
      version_count: record.version_count,
    })
    createDialogRef.value?.show()
  }
  async function changeDatasetStatus(record: any) {
    if (statusSaving.has(record.id))
    return;
    statusSaving.add(record.id)
    try {
      await updateEvaluationDataset({
        id: record.id,
        status:
          record.status === 'archived'
            ? record.current_version
              ? 'enabled'
              : 'draft'
            : 'archived',
      })
      await load()
    } finally {
      statusSaving.delete(record.id)
    }
  }
  function normalizeLabels(value: unknown): string[] {
    const values = Array.isArray(value) ? value : typeof value === 'string' ? [value] : []
    return [
      ...new Set(
        values
          .filter((entry): entry is string => typeof entry === 'string')
          .flatMap((value) => value.split(/[,，\n]/))
          .map((value) => value.trim())
          .filter(Boolean)
      ),
    ]
  }
  function updateTaskTypes(value: unknown) {
    form.task_type = normalizeLabels(value)
  }
  async function saveDataset() {
    try {
      if (savingDataset.value)
    return;
      if (!form.name) {
        Message.warning('请填写数据集名称')
        return
      }
      form.task_type = normalizeLabels(form.task_type)
      if (!form.task_type.length) {
        Message.warning('请至少输入一个任务类型')
        return
      }
      savingDataset.value = true
      const payload = {
        id: form.id,
        name: form.name,
        description: form.description,
        task_type: [...form.task_type],
      }
      if (form.id) await updateEvaluationDataset({ ...payload, status: form.status })
      else await createEvaluationDataset(payload)
      createDialogRef.value?.close()
      await load()
    } finally {
      savingDataset.value = false
      createDialogRef.value?.setConfirmLoading(false)
    }
  }
  function remove(record: any) {
    Modal.warning({
      title: '删除数据集',
      content: `确认删除“${record.name}”吗？有关联版本或用例时后端会阻止删除。`,
      hideCancel: false,
      onOk: async () => {
        await deleteEvaluationDataset(record.id)
        await load()
      },
    })
  }
  function openVersions(record: any) {

    router.push({
      path: '/evaluation/dataset/details',
      query: { id: record.id, name: record.name },
    })
  }
  onBeforeUnmount(() => {
    listRequest += 1
  })
  onMounted(load)
</script>
<style scoped>
  .mango-dataset-task-tags { display: inline-flex; align-items: center; gap: var(--m-space-xs); max-width: 100%; min-width: 0; vertical-align: middle; }
  .mango-dataset-task-tags :deep(.arco-tag) { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .mango-dataset-task-tags__more { flex-shrink: 0; }
</style>
