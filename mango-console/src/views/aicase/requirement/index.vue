<template>
  <TableBody ref="tableBody">
    <template #header>
      <TableHeader title="需求管理" :show-filter="true" @search="doRefresh" @reset-search="onResetSearch">
        <template #search-content>
          <a-form layout="inline">
            <a-form-item label="需求名称">
              <a-input v-model="searchName" placeholder="请输入需求名称" @blur="doRefresh" />
            </a-form-item>
            <a-form-item label="状态">
              <a-select v-model="searchStatus" :options="statusOptions" :field-names="fieldNames"
                allow-clear style="width:150px" @change="doRefresh" />
            </a-form-item>
          </a-form>
        </template>
      </TableHeader>
    </template>
    <template #default>
      <a-tabs>
        <template #extra>
          <a-space>
            <a-button size="small" type="primary" @click="onAdd">新增需求</a-button>
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
            <template v-else-if="item.key === 'project_product'" #cell="{ record }">
              {{ record?.project_product?.project?.name }}/{{ record?.project_product?.name }}
            </template>
            <template v-else-if="item.key === 'create_user'" #cell="{ record }">
              {{ record?.create_user?.nickname }}
            </template>
            <template v-else-if="item.key === 'status'" #cell="{ record }">
              <a-tag :color="statusColorMap[record.status]">{{ statusLabelMap[record.status] }}</a-tag>
            </template>
            <template v-else-if="item.key === 'input_type'" #cell="{ record }">
              <a-tag color="arcoblue">{{ inputTypeLabelMap[record.input_type] }}</a-tag>
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <a-space>
                <a-button size="mini" type="text" @click="onDetail(record)">详情</a-button>
                <a-button size="mini" type="text" @click="onUpdate(record)">编辑</a-button>
                <a-button size="mini" type="text" @click="onAnalyze(record)"
                  :disabled="record.status === 6">启动分析</a-button>
                <a-button size="mini" type="text" status="danger" @click="onDelete(record)">删除</a-button>
              </a-space>
            </template>
          </a-table-column>
        </template>
      </a-table>
    </template>
    <template #footer><TableFooter :pagination="pagination" /></template>
  </TableBody>

  <ModalDialog ref="modalDialogRef" :title="formState.actionTitle" @confirm="onDataForm">
    <template #content>
      <a-form :model="formData" layout="vertical">
        <a-form-item label="项目/产品" required>
          <a-cascader v-model="formData.project_product" :options="projectInfo.projectProduct"
            placeholder="请选择项目产品" allow-clear allow-search />
        </a-form-item>
        <a-form-item label="需求名称" required>
          <a-input v-model="formData.name" placeholder="请输入需求名称" />
        </a-form-item>
        <a-form-item label="创建人" required>
          <a-select v-model="formData.create_user" :options="userList" :field-names="fieldNames"
            placeholder="请选择创建人" allow-clear allow-search />
        </a-form-item>
        <a-form-item label="输入类型" required>
          <a-select v-model="formData.input_type" :options="inputTypeOptions" :field-names="fieldNames"
            placeholder="请选择输入类型" @change="formData.input_content = ''" />
        </a-form-item>
        <a-form-item v-if="formData.input_type === 0" label="需求内容">
          <a-textarea v-model="formData.input_content" placeholder="请输入需求文本内容"
            :auto-size="{ minRows: 6, maxRows: 16 }" />
        </a-form-item>
        <a-form-item v-else-if="formData.input_type === 3" label="需求URL">
          <a-input v-model="formData.input_content" placeholder="请输入可访问的需求文档URL" />
        </a-form-item>
        <a-form-item v-else label="上传文件（图片/Word）">
          <a-upload :limit="1" :custom-request="handleUpload">
            <template #upload-button>
              <a-button><icon-upload />点击上传</a-button>
            </template>
          </a-upload>
        </a-form-item>
      </a-form>
    </template>
  </ModalDialog>
</template>

<script lang="ts" setup>
import { onMounted, reactive, ref, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { Message, Modal } from '@arco-design/web-vue'
import { usePagination, useRowKey, useRowSelection, useTable, useTableColumn } from '@/hooks/table'
import { fieldNames } from '@/setting'
import { useProject } from '@/store/modules/get-project'
import {
  getAiRequirement, postAiRequirement, putAiRequirement,
  deleteAiRequirement, postAiRequirementAnalyze
} from '@/api/aicase/index'
import { getUserName } from '@/api/user/user'

const router = useRouter()
const projectInfo = useProject()
const table = useTable()
const pagination = usePagination(doRefresh)
const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection()
const rowKey = useRowKey('id')
const modalDialogRef = ref<any>(null)
const searchName = ref('')
const searchStatus = ref<any>('')
const userList = ref<any[]>([])

const statusLabelMap: Record<number, string> = {
  0: '待分析', 1: '拆分需求中', 2: '待确认拆分',
  3: '生成测试点中', 4: '待确认测试点', 5: '生成用例中', 6: '已完成', 9: '失败'
}
const statusColorMap: Record<number, string> = {
  0: 'gray', 1: 'blue', 2: 'orange', 3: 'blue', 4: 'orange', 5: 'blue', 6: 'green', 9: 'red'
}
const inputTypeLabelMap: Record<number, string> = { 0: '文本', 1: '图片', 2: 'Word', 3: 'URL' }
const statusOptions = Object.entries(statusLabelMap).map(([k, v]) => ({ key: Number(k), title: v }))
const inputTypeOptions = Object.entries(inputTypeLabelMap).map(([k, v]) => ({ key: Number(k), title: v }))

const tableColumns = useTableColumn([
  { title: 'ID', key: 'index', width: 80, align: 'center' as const },
  { title: '项目/产品', key: 'project_product', width: 200 },
  { title: '需求名称', key: 'name', ellipsis: true, tooltip: true },
  { title: '输入类型', key: 'input_type', width: 100, align: 'center' as const },
  { title: '创建人', key: 'create_user', width: 100 },
  { title: '状态', key: 'status', width: 140, align: 'center' as const },
  { title: '创建时间', key: 'create_time', width: 180 },
  { title: '操作', key: 'actions', fixed: 'right' as const, width: 200 },
])

const formState = reactive({ isAdd: true, updateId: 0, actionTitle: '新增需求' })
const formData = reactive<any>({
  project_product: null, name: '', input_type: 0, input_content: '', create_user: null
})

function doRefresh() {
  getAiRequirement({
    name: searchName.value || undefined,
    status: searchStatus.value !== '' ? searchStatus.value : undefined,
    page: pagination.page,
    pageSize: pagination.pageSize,
  }).then((res: any) => {
    table.handleSuccess(res)
    pagination.setTotalSize(res.totalSize)
  }).catch(console.log)
}

function onResetSearch() {
  searchName.value = ''
  searchStatus.value = ''
  doRefresh()
}

function onAdd() {
  formState.isAdd = true
  formState.actionTitle = '新增需求'
  Object.assign(formData, { project_product: null, name: '', input_type: 0, input_content: '', create_user: null })
  modalDialogRef.value?.toggle()
}

function onUpdate(record: any) {
  formState.isAdd = false
  formState.updateId = record.id
  formState.actionTitle = '编辑需求'
  nextTick(() => {
    formData.project_product = record.project_product?.id
    formData.name = record.name
    formData.input_type = record.input_type
    formData.input_content = record.input_content
    formData.create_user = record.create_user?.id
  })
  modalDialogRef.value?.toggle()
}

function onDetail(record: any) {
  router.push({ path: '/aicase/requirement/detail', query: { id: record.id, name: record.name } })
}

function onAnalyze(record: any) {
  Modal.confirm({
    title: '启动AI分析',
    content: `确定要对「${record.name}」启动AI需求分析吗？`,
    onOk: () => {
      postAiRequirementAnalyze(record.id).then((res: any) => {
        Message.success(res.msg)
        doRefresh()
      }).catch(console.log)
    },
  })
}

function onDelete(record: any) {
  const batch = record === null
  if (batch && selectedRowKeys.value.length === 0) { Message.error('请选择要删除的数据'); return }
  Modal.confirm({
    title: '提示', content: '确定要删除此需求吗？',
    onOk: () => {
      deleteAiRequirement(batch ? selectedRowKeys.value : record.id)
        .then((res: any) => Message.success(res.msg))
        .finally(() => { doRefresh(); if (batch) selectedRowKeys.value = [] })
    },
  })
}

function onDataForm() {
  if (!formData.name) { Message.error('请输入需求名称'); modalDialogRef.value?.setConfirmLoading(false); return }
  if (!formData.create_user) { Message.error('请选择创建人'); modalDialogRef.value?.setConfirmLoading(false); return }
  const payload = { ...formData }
  if (Array.isArray(payload.project_product))
    payload.project_product = payload.project_product[payload.project_product.length - 1]
  const req = formState.isAdd
    ? postAiRequirement(payload)
    : putAiRequirement({ ...payload, id: formState.updateId })
  req.then((res: any) => {
    modalDialogRef.value?.toggle()
    Message.success(res.msg)
    doRefresh()
  }).catch(console.log).finally(() => modalDialogRef.value?.setConfirmLoading(false))
}

function handleUpload() {}

onMounted(() => {
  doRefresh()
  projectInfo.projectProductName()
  getUserName().then((res: any) => { userList.value = res.data }).catch(console.log)
})
</script>
