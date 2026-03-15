<template>
  <TableBody>
    <template #header>
      <TableHeader title="测试点管理" :show-filter="true" @search="doRefresh" @reset-search="onResetSearch">
        <template #search-content>
          <a-form layout="inline">
            <a-form-item label="测试点名称">
              <a-input v-model="searchName" placeholder="测试点名称" @blur="doRefresh" />
            </a-form-item>
            <a-form-item label="确认状态">
              <a-select v-model="searchConfirmed" :options="confirmOptions" :field-names="fieldNames"
                allow-clear style="width:120px" @change="doRefresh" />
            </a-form-item>
            <a-form-item label="测试类型">
              <a-select v-model="searchType" :options="typeOptions" :field-names="fieldNames"
                allow-clear style="width:120px" @change="doRefresh" />
            </a-form-item>
          </a-form>
        </template>
      </TableHeader>
    </template>
    <template #default>
      <a-table :bordered="false" :columns="tableColumns" :data="table.dataList"
        :loading="table.tableLoading.value" :pagination="false"
        :row-selection="{ selectedRowKeys, showCheckedAll }" :rowKey="rowKey"
        @selection-change="onSelectionChange">
        <template #columns>
          <a-table-column v-for="item of tableColumns" :key="item.key"
            :align="item.align" :data-index="item.key" :fixed="item.fixed"
            :title="item.title" :width="item.width" :ellipsis="item.ellipsis" :tooltip="item.tooltip">
            <template v-if="item.key === 'index'" #cell="{ record }">{{ record.id }}</template>
            <template v-else-if="item.key === 'requirement'" #cell="{ record }">
              {{ record?.requirement?.name }}
            </template>
            <template v-else-if="item.key === 'requirement_split'" #cell="{ record }">
              {{ record?.requirement_split?.name }}
            </template>
            <template v-else-if="item.key === 'test_type'" #cell="{ record }">
              <a-tag :color="typeColorMap[record.test_type]">{{ typeLabelMap[record.test_type] }}</a-tag>
            </template>
            <template v-else-if="item.key === 'is_confirmed'" #cell="{ record }">
              <a-tag :color="confirmColorMap[record.is_confirmed]">{{ confirmLabelMap[record.is_confirmed] }}</a-tag>
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <a-space>
                <a-button size="mini" type="text" status="success" @click="onConfirm(record, 1)">确认</a-button>
                <a-button size="mini" type="text" status="danger" @click="onConfirm(record, 2)">忽略</a-button>
                <a-button size="mini" type="text" @click="onUpdate(record)">编辑</a-button>
              </a-space>
            </template>
          </a-table-column>
        </template>
      </a-table>
    </template>
    <template #footer><TableFooter :pagination="pagination" /></template>
  </TableBody>

  <ModalDialog ref="modalDialogRef" title="编辑测试点" @confirm="onDataForm">
    <template #content>
      <a-form :model="formData" layout="vertical">
        <a-form-item label="测试点名称">
          <a-input v-model="formData.name" placeholder="请输入测试点名称" />
        </a-form-item>
        <a-form-item label="测试类型">
          <a-select v-model="formData.test_type" :options="typeOptions" :field-names="fieldNames" />
        </a-form-item>
        <a-form-item label="描述">
          <a-textarea v-model="formData.description" :auto-size="{ minRows: 3, maxRows: 8 }" />
        </a-form-item>
      </a-form>
    </template>
  </ModalDialog>
</template>

<script lang="ts" setup>
import { onMounted, reactive, ref, nextTick } from 'vue'
import { Message } from '@arco-design/web-vue'
import { usePagination, useRowKey, useRowSelection, useTable, useTableColumn } from '@/hooks/table'
import { fieldNames } from '@/setting'
import { getAiTestPoint, putAiTestPoint, postAiTestPointBatchConfirm } from '@/api/aicase/index'

const table = useTable()
const pagination = usePagination(doRefresh)
const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection()
const rowKey = useRowKey('id')
const modalDialogRef = ref<any>(null)
const searchName = ref('')
const searchConfirmed = ref<any>('')
const searchType = ref<any>('')

const confirmLabelMap: Record<number, string> = { 0: '待确认', 1: '已确认', 2: '已忽略' }
const confirmColorMap: Record<number, string> = { 0: 'gray', 1: 'green', 2: 'red' }
const typeLabelMap: Record<number, string> = { 0: '功能', 1: '边界', 2: '异常', 3: '性能' }
const typeColorMap: Record<number, string> = { 0: 'blue', 1: 'orange', 2: 'red', 3: 'purple' }
const confirmOptions = Object.entries(confirmLabelMap).map(([k, v]) => ({ key: Number(k), title: v }))
const typeOptions = Object.entries(typeLabelMap).map(([k, v]) => ({ key: Number(k), title: v }))

const tableColumns = useTableColumn([
  { title: 'ID', key: 'index', width: 70, align: 'center' as const },
  { title: '所属需求', key: 'requirement', width: 160, ellipsis: true, tooltip: true },
  { title: '所属子模块', key: 'requirement_split', width: 140, ellipsis: true, tooltip: true },
  { title: '测试点名称', key: 'name', ellipsis: true, tooltip: true },
  { title: '类型', key: 'test_type', width: 90, align: 'center' as const },
  { title: '确认状态', key: 'is_confirmed', width: 100, align: 'center' as const },
  { title: '操作', key: 'actions', fixed: 'right' as const, width: 180 },
])

const formData = reactive<any>({ id: null, name: '', test_type: 0, description: '' })

function doRefresh() {
  getAiTestPoint({
    name: searchName.value || undefined,
    is_confirmed: searchConfirmed.value !== '' ? searchConfirmed.value : undefined,
    test_type: searchType.value !== '' ? searchType.value : undefined,
    page: pagination.page,
    pageSize: pagination.pageSize,
  }).then((res: any) => {
    table.handleSuccess(res)
    pagination.setTotalSize(res.totalSize)
  }).catch(console.log)
}

function onResetSearch() {
  searchName.value = ''
  searchConfirmed.value = ''
  searchType.value = ''
  doRefresh()
}

function onUpdate(record: any) {
  nextTick(() => {
    formData.id = record.id
    formData.name = record.name
    formData.test_type = record.test_type
    formData.description = record.description
  })
  modalDialogRef.value?.toggle()
}

function onConfirm(record: any, status: number) {
  postAiTestPointBatchConfirm(record.requirement_id, [{ id: record.id, is_confirmed: status }])
    .then((res: any) => { Message.success(res.msg); doRefresh() })
}

function onDataForm() {
  putAiTestPoint(formData).then((res: any) => {
    modalDialogRef.value?.toggle()
    Message.success(res.msg)
    doRefresh()
  }).catch(console.log).finally(() => modalDialogRef.value?.setConfirmLoading(false))
}

onMounted(() => doRefresh())
</script>
