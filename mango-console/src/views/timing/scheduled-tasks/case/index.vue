<template>
  <div>
    <div id="tableHeaderContainer" class="relative" :style="{ zIndex: 9 }">
      <a-card :title="'定时任务：' + route.query.name">
        <template #extra>
          <a-affix :offsetTop="80">
            <a-space>
              <a-button type="primary" size="small" @click="doAppend">增加用例</a-button>
              <a-button status="warning" size="small" @click="handleClick">批量设置环境</a-button>
              <a-modal v-model:visible="data.visible" @ok="handleOk" @cancel="handleCancel">
                <template #title> 设为定时任务 </template>
                <div>
                  <a-select
                    v-model="data.value"
                    placeholder="请选择定时任务进行绑定"
                    :options="testObj.data"
                    :field-names="fieldNames"
                    value-key="key"
                    allow-clear
                    allow-search
                  />
                </div>
              </a-modal>
              <a-button status="danger" size="small" @click="onDeleteItems">批量删除</a-button>
              <a-button status="danger" size="small" @click="doResetSearch">返回</a-button>
            </a-space>
          </a-affix>
        </template>
        <a-table
          :draggable="{ type: 'handle', width: 40 }"
          :bordered="false"
          :row-selection="{ selectedRowKeys, showCheckedAll }"
          :loading="table.tableLoading.value"
          :data="table.dataList"
          :columns="tableColumns"
          :pagination="false"
          :rowKey="rowKey"
          @selection-change="onSelectionChange"
          @change="handleChange"
        >
          <template #columns>
            <a-table-column
              v-for="item of tableColumns"
              :key="item.key"
              :align="item.align"
              :title="item.title"
              :width="item.width"
              :data-index="item.key"
              :fixed="item.fixed"
            >
              <template v-if="item.key === 'index'" #cell="{ record }">
                {{ record.id }}
              </template>
              <template v-else-if="item.key === 'task'" #cell="{ record }">
                {{ record.task.name }}
              </template>
              <template v-else-if="item.key === 'case'" #cell="{ record }">
                {{ record.case }}
              </template>
              <template v-else-if="item.key === 'test_object'" #cell="{ record }">
                {{ record.test_object == null ? '跟随定时任务' : record.test_object?.name }}
              </template>
              <template v-else-if="item.key === 'actions'" #cell="{ record }">
                <!--                <a-button type="text" size="mini" @click="onUpdate(record)">编辑</a-button>-->
                <a-button status="danger" type="text" size="mini" @click="onDelete(record)"
                  >删除
                </a-button>
              </template>
            </a-table-column>
          </template>
        </a-table>
      </a-card>
      <ModalDialog ref="modalDialogRef" :title="data.actionTitle" @confirm="onDataForm">
        <template #content>
          <a-form :model="formModel">
            <a-form-item
              :class="[item.required ? 'form-item__require' : 'form-item__no_require']"
              :label="item.label"
              v-for="item of formItems"
              :key="item.key"
            >
              <template v-if="item.type === 'input'">
                <a-input :placeholder="item.placeholder" v-model="item.value" />
              </template>
              <template v-else-if="item.type === 'cascader'">
                <a-cascader
                  v-model="item.value"
                  @change="onProductModuleName(item.value)"
                  :placeholder="item.placeholder"
                  :options="projectInfo.projectProduct"
                  allow-search
                  allow-clear
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'module'">
                <a-select
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="data.moduleList"
                  :field-names="fieldNames"
                  value-key="key"
                  allow-clear
                  allow-search
                  @change="tasksTypeCaseName(item.value)"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'case'">
                <a-select
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="data.caseList"
                  :field-names="fieldNames"
                  allow-clear
                  allow-search
                />
              </template>
            </a-form-item>
          </a-form>
        </template>
      </ModalDialog>
    </div>
  </div>
</template>
<script lang="ts" setup>
  import { nextTick, onMounted, reactive, ref } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import { ModalDialogType } from '@/types/components'
  import { useRoute } from 'vue-router'
  import { getFormItems } from '@/utils/datacleaning'
  import { fieldNames } from '@/setting'
  import { usePagination, useRowKey, useRowSelection, useTable } from '@/hooks/table'
  import { useTestObj } from '@/store/modules/get-test-obj'
  import { formItems, tableColumns } from './config'
  import {
    deleteSystemTasksRunCase,
    getSystemTasksRunCase,
    getSystemTasksTypeCaseName,
    postSystemTasksRunCase,
    putSystemTasksCaseSort,
    putSystemTasksCaseTestObject,
    putSystemTasksRunCase,
  } from '@/api/system'
  import { getUserModuleName } from '@/api/user'
  import { useProject } from '@/store/modules/get-project'
  const testObj = useTestObj()
  const projectInfo = useProject()
  const pagination = usePagination(doRefresh)
  const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection()
  const table = useTable()
  const rowKey = useRowKey('id')
  const route = useRoute()
  pagination.pageSize = 1000
  const formModel = ref({})
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const data = reactive({
    isAdd: false,
    visible: false,
    value: null,
    updateId: 0,
    actionTitle: '添加定时任务',
    caseList: [],
    data: [],
    moduleList: [],
  })

  function onDeleteItems() {
    if (selectedRowKeys.value.length === 0) {
      Message.error('请选择要删除的数据')
      return
    }
    Modal.confirm({
      title: '提示',
      content: '确定要删除此数据吗？',
      cancelText: '取消',
      okText: '删除',
      onOk: () => {
        deleteSystemTasksRunCase(selectedRowKeys.value)
          .then((res) => {
            Message.success(res.msg)
            selectedRowKeys.value = []
            doRefresh()
          })
          .catch(console.log)
      },
    })
  }

  function doAppend() {
    data.actionTitle = '添加用例'
    data.isAdd = true
    modalDialogRef.value?.toggle()
    formItems.forEach((it) => {
      if (it.reset) {
        it.reset()
      } else {
        it.value = ''
      }
    })
  }

  function onDelete(record: any) {
    Modal.confirm({
      title: '提示',
      content: '是否要删除此定时任务？',
      cancelText: '取消',
      okText: '删除',
      onOk: () => {
        deleteSystemTasksRunCase(record.id)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      },
    })
  }

  function onUpdate(record: any) {
    data.actionTitle = '编辑用例'
    data.isAdd = false
    data.updateId = record.id
    modalDialogRef.value?.toggle()
    nextTick(() => {
      formItems.forEach((it) => {
        const propName = record[it.key]
        if (propName) {
          it.value = record.case
        }
      })
    })
  }

  function onDataForm() {
    if (formItems.every((it) => (it.validator ? it.validator() : true))) {
      modalDialogRef.value?.toggle()
      let value = getFormItems(formItems)
      if (data.isAdd) {
        value['task'] = route.query.id
        value['sort'] = data.data.length
        postSystemTasksRunCase(value)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      } else {
        value['id'] = data.updateId
        putSystemTasksRunCase(value)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      }
    }
  }
  const handleChange = (_data: any) => {
    let data: any = []
    _data.forEach((item: any, index: number) => {
      data.push({
        id: item.id,
        sort: index,
      })
    })
    putSystemTasksCaseSort(data)
      .then((res) => {
        Message.success(res.msg)
      })
      .catch(console.log)
  }
  function doResetSearch() {
    window.history.back()
  }

  function doRefresh() {
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

  function tasksTypeCaseName(value: number) {
    getSystemTasksTypeCaseName(route.query.type, value)
      .then((res) => {
        data.caseList = res.data
      })
      .catch(console.log)
  }
  const handleCancel = () => {
    data.visible = false
  }
  const handleClick = () => {
    if (selectedRowKeys.value.length === 0) {
      Message.error('请选择要绑定测试的用例环境')
      return
    }
    data.visible = true
  }
  function onProductModuleName(projectProductId: number) {
    getUserModuleName(projectProductId)
      .then((res) => {
        data.moduleList = res.data
      })
      .catch((error) => {
        console.error(error)
      })
  }
  const handleOk = () => {
    putSystemTasksCaseTestObject(selectedRowKeys.value, data.value)
      .then((res) => {
        Message.success(res.msg)
        data.visible = false
        doRefresh()
      })
      .catch(console.log)
  }
  onMounted(() => {
    nextTick(async () => {
      doRefresh()
    })
  })
</script>
