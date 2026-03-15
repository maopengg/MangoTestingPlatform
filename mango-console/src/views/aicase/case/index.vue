<template>
  <TableBody>
    <template #header>
      <TableHeader title="用例管理" :show-filter="true" @search="doRefresh" @reset-search="onResetSearch">
        <template #search-content>
          <a-form layout="inline">
            <a-form-item label="用例标题">
              <a-input v-model="searchTitle" placeholder="用例标题" @blur="doRefresh" />
            </a-form-item>
            <a-form-item label="优先级">
              <a-select v-model="searchPriority" :options="priorityOptions" :field-names="fieldNames" allow-clear style="width:100px" @change="doRefresh" />
            </a-form-item>
            <a-form-item label="类型">
              <a-select v-model="searchCaseType" :options="caseTypeOptions" :field-names="fieldNames" allow-clear style="width:100px" @change="doRefresh" />
            </a-form-item>
          </a-form>
        </template>
      </TableHeader>
    </template>
    <template #default>
      <a-tabs>
        <template #extra>
          <a-space>
            <a-button size="small" status="success" @click="onExportAll">导出全部</a-button>
            <a-button size="small" status="danger" @click="onDelete(null)">批量删除</a-button>
          </a-space>
        </template>
      </a-tabs>
      <a-table :bordered="false" :columns="tableColumns" :data="table.dataList"
        :loading="table.tableLoading.value" :pagination="false"
        :row-selection="{ selectedRowKeys, showCheckedAll }" :rowKey="rowKey"
        @selection-change="onSelectionChange">
        <template #columns>
          <a-table-column v-for="item of tableColumns" :key="item.key"
            :align="item.align" :data-index="item.key" :fixed="item.fixed"
            :title="item.title" :width="item.width" :ellipsis="item.ellipsis" :tooltip="item.tooltip">
            <template v-if="item.key === 'index'" #cell="{ record }">{{ record.id }}</template>
            <template v-else-if="item.key === 'requirement'" #cell="{ record }">{{ record?.requirement?.name }}</template>
            <template v-else-if="item.key === 'priority'" #cell="{ record }">
              <a-tag :color="priorityColorMap[record.priority]">{{ priorityLabelMap[record.priority] }}</a-tag>
            </template>
            <template v-else-if="item.key === 'case_type'" #cell="{ record }">
              <a-tag :color="caseTypeColorMap[record.case_type]">{{ caseTypeLabelMap[record.case_type] }}</a-tag>
            </template>
            <template v-else-if="item.key === 'test_result'" #cell="{ record }">
              <a-tag :color="resultColorMap[record.test_result]">{{ resultLabelMap[record.test_result] }}</a-tag>
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <a-space>
                <a-button size="mini" type="text" @click="onUpdate(record)">编辑</a-button>
                <a-button size="mini" type="text" status="success" @click="onExport(record)">导出</a-button>
                <a-button size="mini" type="text" status="danger" @click="onDelete(record)">删除</a-button>
              </a-space>
            </template>
          </a-table-column>
        </template>
      </a-table>
    </template>
    <template #footer><TableFooter :pagination="pagination" /></template>
  </TableBody>

  <ModalDialog ref="modalDialogRef" title="编辑用例" @confirm="onDataForm">
    <template #content>
      <a-form :model="formData" layout="vertical">
        <a-row :gutter="16">
          <a-col :span="12"><a-form-item label="用例编号"><a-input v-model="formData.case_no" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item label="版本编号"><a-input v-model="formData.version" /></a-form-item></a-col>
        </a-row>
        <a-form-item label="用例标题"><a-input v-model="formData.title" /></a-form-item>
        <a-row :gutter="16">
          <a-col :span="12"><a-form-item label="优先级"><a-select v-model="formData.priority" :options="priorityOptions" :field-names="fieldNames" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item label="用例类型"><a-select v-model="formData.case_type" :options="caseTypeOptions" :field-names="fieldNames" /></a-form-item></a-col>
        </a-row>
        <a-form-item label="前置条件"><a-textarea v-model="formData.precondition" :auto-size="{ minRows: 2, maxRows: 4 }" /></a-form-item>
        <a-form-item label="预期结果"><a-textarea v-model="formData.expected" :auto-size="{ minRows: 2, maxRows: 4 }" /></a-form-item>
        <a-row :gutter="16">
          <a-col :span="8"><a-form-item label="测试结果"><a-select v-model="formData.test_result" :options="resultOptions" :field-names="fieldNames" /></a-form-item></a-col>
          <a-col :span="8"><a-form-item label="自动化标识"><a-select v-model="formData.auto_tag" :options="autoTagOptions" :field-names="fieldNames" /></a-form-item></a-col>
          <a-col :span="8"><a-form-item label="开发自测"><a-select v-model="formData.dev_test_result" :options="resultOptions" :field-names="fieldNames" /></a-form-item></a-col>
        </a-row>
        <a-form-item label="备注"><a-textarea v-model="formData.remark" :auto-size="{ minRows: 2, maxRows: 4 }" /></a-form-item>
      </a-form>
    </template>
  </ModalDialog>
</template>

<script lang="ts" setup>
import { onMounted, reactive, ref, nextTick } from 'vue'
import { Message, Modal } from '@arco-design/web-vue'
import { usePagination, useRowKey, useRowSelection, useTable, useTableColumn } from '@/hooks/table'
import { fieldNames } from '@/setting'
import { getAiTestCase, putAiTestCase, deleteAiTestCase } from '@/api/aicase/index'

const table = useTable()
const pagination = usePagination(doRefresh)
const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection()
const rowKey = useRowKey('id')
const modalDialogRef = ref<any>(null)
const searchTitle = ref('')
const searchPriority = ref<any>('')
const searchCaseType = ref<any>('')

const priorityLabelMap: Record<number, string> = { 0: '低', 1: '中', 2: '高', 3: '紧急' }
const priorityColorMap: Record<number, string> = { 0: 'gray', 1: 'blue', 2: 'orange', 3: 'red' }
const caseTypeLabelMap: Record<number, string> = { 0: '正常', 1: '异常', 2: '边界' }
const caseTypeColorMap: Record<number, string> = { 0: 'green', 1: 'red', 2: 'orange' }
const resultLabelMap: Record<number, string> = { 0: '未测试', 1: '通过', 2: '失败', 3: '阻塞', 4: '跳过' }
const resultColorMap: Record<number, string> = { 0: 'gray', 1: 'green', 2: 'red', 3: 'orange', 4: 'blue' }
const autoTagLabelMap: Record<number, string> = { 0: '无需自动化', 1: '界面自动化', 2: '接口自动化', 3: '单元测试' }

const priorityOptions = Object.entries(priorityLabelMap).map(([k, v]) => ({ key: Number(k), title: v }))
const caseTypeOptions = Object.entries(caseTypeLabelMap).map(([k, v]) => ({ key: Number(k), title: v }))
const resultOptions = Object.entries(resultLabelMap).map(([k, v]) => ({ key: Number(k), title: v }))
const autoTagOptions = Object.entries(autoTagLabelMap).map(([k, v]) => ({ key: Number(k), title: v }))

const tableColumns = useTableColumn([
  { title: 'ID', key: 'index', width: 70, align: 'center' as const },
  { title: '所属需求', key: 'requirement', width: 150, ellipsis: true, tooltip: true },
  { title: '用例编号', key: 'case_no', width: 100 },
  { title: '用例标题', key: 'title', ellipsis: true, tooltip: true },
  { title: '优先级', key: 'priority', width: 80, align: 'center' as const },
  { title: '用例类型', key: 'case_type', width: 90, align: 'center' as const },
  { title: '测试结果', key: 'test_result', width: 90, align: 'center' as const },
  { title: '创建时间', key: 'create_time', width: 170 },
  { title: '操作', key: 'actions', fixed: 'right' as const, width: 180 },
])

const formData = reactive<any>({
  id: null, case_no: '', title: '', version: '', priority: 1,
  case_type: 0, precondition: '', expected: '',
  test_result: 0, dev_test_result: 0, auto_tag: 0, remark: ''
})

function doRefresh() {
  getAiTestCase({
    title: searchTitle.value || undefined,
    priority: searchPriority.value !== '' ? searchPriority.value : undefined,
    case_type: searchCaseType.value !== '' ? searchCaseType.value : undefined,
    page: pagination.page,
    pageSize: pagination.pageSize,
  }).then((res: any) => {
    table.handleSuccess(res)
    pagination.setTotalSize(res.totalSize)
  }).catch(console.log)
}

function onResetSearch() {
  searchTitle.value = ''
  searchPriority.value = ''
  searchCaseType.value = ''
  doRefresh()
}

function onUpdate(record: any) {
  nextTick(() => Object.assign(formData, {
    id: record.id, case_no: record.case_no, title: record.title,
    version: record.version, priority: record.priority, case_type: record.case_type,
    precondition: record.precondition, expected: record.expected,
    test_result: record.test_result, dev_test_result: record.dev_test_result,
    auto_tag: record.auto_tag, remark: record.remark
  }))
  modalDialogRef.value?.toggle()
}

function onDelete(record: any) {
  const batch = record === null
  if (batch && selectedRowKeys.value.length === 0) { Message.error('请选择要删除的数据'); return }
  Modal.confirm({
    title: '提示', content: '确定要删除此用例吗？',
    onOk: () => {
      deleteAiTestCase(batch ? selectedRowKeys.value : record.id)
        .then((res: any) => Message.success(res.msg))
        .finally(() => { doRefresh(); if (batch) selectedRowKeys.value = [] })
    }
  })
}

function onDataForm() {
  putAiTestCase(formData).then((res: any) => {
    modalDialogRef.value?.toggle()
    Message.success(res.msg)
    doRefresh()
  }).catch(console.log).finally(() => modalDialogRef.value?.setConfirmLoading(false))
}

function onExport(record: any) {
  const reqId = record.requirement_id || record.requirement?.id
  window.open(`/api/ai/test/case/export/excel?requirement_id=${reqId}`, '_blank')
}

function onExportAll() {
  window.open('/api/ai/test/case/export/excel', '_blank')
}

onMounted(() => doRefresh())
</script>
