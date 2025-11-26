<template>
  <TableBody ref="tableBody">
    <template #default>
      <a-card :bordered="false" :title="'定时任务：' + route.query.name">
        <template #extra>
          <a-space>
            <a-button size="small" type="primary" @click="doAppend">增加用例</a-button>
            <a-button size="small" status="danger" @click="onDelete(null)">批量删除</a-button>
            <a-button size="small" status="danger" @click="doResetSearch">返回</a-button>
          </a-space>
        </template>
        <a-table
          :bordered="false"
          :columns="tableColumns"
          :data="table.dataList"
          :draggable="{ type: 'handle', width: 40 }"
          :loading="table.tableLoading.value"
          :pagination="false"
          :row-selection="{ selectedRowKeys, showCheckedAll }"
          :rowKey="rowKey"
          @selection-change="onSelectionChange"
        >
          <template #columns>
            <a-table-column
              v-for="item of tableColumns"
              :key="item.key"
              :align="item.align"
              :data-index="item.key"
              :fixed="item.fixed"
              :title="item.title"
              :width="item.width"
            >
              <template v-if="item.key === 'index'" #cell="{ record }">
                {{ record.id }}
              </template>
              <template v-else-if="item.key === 'type'" #cell="{ record }">
                <a-tag :color="enumStore.colors[record.type]" size="small"
                  >{{ enumStore.test_case_type[record.type].title }}
                </a-tag>
              </template>
              <template v-else-if="item.key === 'case_id'" #cell="{ record }">
                {{ record.ui_case?.name || record.api_case?.name || record.pytest_case?.name }}
              </template>
              <template v-else-if="item.key === 'actions'" #cell="{ record }">
                <a-button
                  size="mini"
                  status="danger"
                  type="text"
                  class="custom-mini-btn"
                  @click="onDelete(record)"
                  >删除
                </a-button>
              </template>
            </a-table-column>
          </template>
        </a-table>
      </a-card>
    </template>
  </TableBody>

  <ModalDialog ref="modalDialogRef" :title="data.actionTitle" @confirm="onDataForm">
    <template #content>
      <a-form :model="formModel">
        <a-form-item
          v-for="item of data.formItems"
          :key="item.key"
          :class="[item.required ? 'form-item__require' : 'form-item__no_require']"
          :label="item.label"
        >
          <template v-if="item.type === 'input'">
            <a-input v-model="item.value" :placeholder="item.placeholder" />
          </template>
          <template v-else-if="item.type === 'cascader' && item.key === 'module'">
            <a-cascader
              v-model="item.value"
              :disabled="data.isModule"
              :options="data.moduleList"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              @change="tasksTypeCaseName(item.value)"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'type'">
            <a-select
              v-model="item.value"
              :field-names="fieldNames"
              :options="enumStore.test_case_type"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              value-key="key"
              @change="changeType(item.value)"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'case_id'">
            <a-select
              v-model="item.value"
              :field-names="fieldNames"
              :options="data.caseList"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
            />
          </template>
        </a-form-item>
      </a-form>
    </template>
  </ModalDialog>
</template>
<script lang="ts" setup>
  import { nextTick, onMounted, reactive, ref } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import { ModalDialogType } from '@/types/components'
  import { useRoute } from 'vue-router'
  import { getFormItems } from '@/utils/datacleaning'
  import { fieldNames } from '@/setting'
  import { usePagination, useRowKey, useRowSelection, useTable } from '@/hooks/table'
  import { formItems, formItemsCmd, tableColumns } from './config'
  import {
    deleteSystemTasksRunCase,
    getSystemTasksRunCase,
    getSystemTasksTypeCaseName,
    postSystemTasksRunCase,
    putSystemTasksRunCase,
  } from '@/api/system/tasks_details'
  import { getUserModuleName } from '@/api/system/module'
  import { useEnum } from '@/store/modules/get-enum'
  import { getPytestProductName } from '@/api/pytest/product'

  const pagination = usePagination(doRefresh)
  const enumStore = useEnum()

  const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection()
  const table = useTable()
  const rowKey = useRowKey('id')
  const route = useRoute()
  pagination.pageSize = 1000
  const formModel = ref({})
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const data: any = reactive({
    isAdd: false,
    value: null,
    isModule: true,
    updateId: 0,
    actionTitle: '新增',
    caseList: [],
    data: [],
    moduleList: [],
    formItems: [],
  })

  function doAppend() {
    data.actionTitle = '新增'
    data.isAdd = true
    modalDialogRef.value?.toggle()
    data.formItems.forEach((it: any) => {
      if (it.reset) {
        it.reset()
      } else {
        it.value = ''
      }
    })
  }

  function onDelete(record: any) {
    const batch = record === null
    if (batch) {
      if (selectedRowKeys.value.length === 0) {
        Message.error('请选择要删除的数据')
        return
      }
    }
    Modal.confirm({
      title: '提示',
      content: '是否要删除此定时任务？',
      cancelText: '取消',
      okText: '删除',
      onOk: () => {
        deleteSystemTasksRunCase(batch ? selectedRowKeys.value : record.id)
          .then((res) => {
            Message.success(res.msg)
          })
          .catch(console.log)
          .finally(() => {
            doRefresh()
            if (batch) {
              selectedRowKeys.value = []
            }
          })
      },
    })
  }

  function onDataForm() {
    if (data.formItems.every((it: any) => (it.validator ? it.validator() : true))) {
      let value = getFormItems(data.formItems)
      let typeList = ['ui_case', 'api_case', 'pytest_case']
      value[typeList[value.type]] = value.case_id
      delete value['case_id']
      delete value['module']
      if (data.isAdd) {
        value['task'] = route.query.id
        postSystemTasksRunCase(value)
          .then((res) => {
            modalDialogRef.value?.toggle()
            Message.success(res.msg)
            doRefresh()
          })
          .catch((error) => {
            console.log(error)
          })
          .finally(() => {
            modalDialogRef.value?.setConfirmLoading(false)
          })
      } else {
        value['id'] = data.updateId
        putSystemTasksRunCase(value)
          .then((res) => {
            modalDialogRef.value?.toggle()
            Message.success(res.msg)
            doRefresh()
          })
          .catch((error) => {
            console.log(error)
          })
          .finally(() => {
            modalDialogRef.value?.setConfirmLoading(false)
          })
      }
    } else {
      modalDialogRef.value?.setConfirmLoading(false)
    }
  }

  function doResetSearch() {
    window.history.back()
  }

  function doRefresh() {
    data.formItems = Number(route.query.type) === 3 ? formItemsCmd : formItems
    getSystemTasksRunCase({
      task_id: route.query.id,
      type: route.query.type,
      page: pagination.page,
      pageSize: pagination.pageSize,
    })
      .then((res) => {
        data.data = res.data
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
      })
      .catch(console.log)
  }

  function changeType(value: number) {
    data.isModule = false
    formItems.forEach((item: any) => {
      if (item.key === 'module' || item.key === 'case_id') {
        item.value = ''
      }
    })
    if (value === 2) {
      onPytestProductModuleName(route.query.project_product_id)
    } else {
      onProductModuleName(route.query.project_product_id)
    }
  }

  function tasksTypeCaseName(value: number) {
    if (value) {
      const type = formItems.find((item) => item.key === 'type')?.value

      getSystemTasksTypeCaseName(type, value)
        .then((res) => {
          data.caseList = res.data
        })
        .catch(console.log)
    }
  }

  function onProductModuleName(projectProductId: any) {
    getUserModuleName(projectProductId)
      .then((res) => {
        data.moduleList = res.data.map((item) => ({
          value: item.key,
          label: item.title,
        }))
      })
      .catch((error) => {
        console.error(error)
      })
  }

  function onPytestProductModuleName(projectProductId: any) {
    getPytestProductName(projectProductId)
      .then((res) => {
        data.moduleList = res.data
      })
      .catch((error) => {
        console.error(error)
      })
  }

  onMounted(() => {
    nextTick(async () => {
      doRefresh()
    })
  })
</script>
