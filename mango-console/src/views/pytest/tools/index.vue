<template>
  <TableBody ref="tableBody">
    <template #header>
      <a-card :bordered="false" title="工具文件">
        <template #extra>
          <a-button size="small" type="primary" @click="clickUpdate">更新目录</a-button>
        </template>
      </a-card>
    </template>

    <template #default>
      <a-table
        :bordered="false"
        :columns="tableColumns"
        :data="table.dataList"
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
            <template v-else-if="item.key === 'project_product'" #cell="{ record }">
              <span
                v-if="record?.project_product?.project_product && record?.project_product?.name"
              >
                {{
                  record.project_product.project_product.project.name +
                  '/' +
                  record.project_product.name
                }}
              </span>
            </template>
            <template v-else-if="item.key === 'module'" #cell="{ record }">
              <span v-if="record?.module?.name">
                <span v-if="record.module.superior_module">
                  {{ record.module.superior_module + '/' }}
                </span>
                {{ record.module.name }}
              </span>
            </template>
            <template v-else-if="item.key === 'file_status'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record.file_status]" size="small"
                >{{ enumStore.file_status[record.file_status].title }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <a-button size="mini" type="text" class="custom-mini-btn" @click="onUpdate(record)"
                >编辑</a-button
              >
              <a-button size="mini" type="text" class="custom-mini-btn" @click="onClick(record)"
                >文件</a-button
              >
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
      <a-drawer
        :visible="data.drawerVisible"
        :width="1000"
        unmountOnClose
        @cancel="data.drawerVisible = false"
        @ok="drawerOk"
      >
        <template #title> 编辑代码</template>
        <div>
          <CodeEditor v-model="data.codeText" placeholder="输入python代码" />
        </div>
      </a-drawer>
    </template>
    <template #footer>
      <TableFooter :pagination="pagination" />
    </template>
  </TableBody>
  <ModalDialog ref="modalDialogRef" :title="data.actionTitle" @confirm="onDataForm">
    <template #content>
      <a-form :model="formModel">
        <a-form-item
          v-for="item of formItems"
          :key="item.key"
          :class="[item.required ? 'form-item__require' : 'form-item__no_require']"
          :label="item.label"
        >
          <template v-if="item.type === 'input'">
            <a-input v-model="item.value" :placeholder="item.placeholder" />
          </template>
          <template v-else-if="item.type === 'cascader' && item.key === 'project_product'">
            <a-cascader
              v-model="item.value"
              :options="data.projectPytest"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              @change="onPytestProjectName(item.value)"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'module'">
            <a-cascader
              v-model="item.value"
              :options="data.moduleList"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'file_status'">
            <a-select
              v-model="item.value"
              :field-names="fieldNames"
              :options="enumStore.file_status"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              value-key="key"
            />
          </template>
        </a-form-item>
      </a-form>
    </template>
  </ModalDialog>
</template>

<script lang="ts" setup>
  import { usePagination, useRowKey, useRowSelection, useTable } from '@/hooks/table'
  import { FormItem, ModalDialogType } from '@/types/components'
  import { Message, Modal } from '@arco-design/web-vue'
  import { nextTick, onMounted, reactive, ref } from 'vue'
  import { getFormItems } from '@/utils/datacleaning'
  import { fieldNames } from '@/setting'
  import { formItems, tableColumns } from './config'
  import { useEnum } from '@/store/modules/get-enum'
  import {
    deletePytestTools,
    getPytestTools,
    getPytestToolsRead,
    getPytestToolsUpdate,
    postPytestTools,
    postPytestToolsWrite,
    putPytestTools,
  } from '@/api/pytest/tools'
  import CodeEditor from '@/components/CodeEditor.vue'
  import { useProject } from '@/store/modules/get-project'

  const projectInfo = useProject()

  const modalDialogRef = ref<ModalDialogType | null>(null)
  const pagination = usePagination(doRefresh)
  const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection()
  const table = useTable()
  const rowKey = useRowKey('id')
  const formModel = ref({})
  const enumStore = useEnum()

  const data: any = reactive({
    isAdd: false,
    updateId: 0,
    actionTitle: '新增',
    drawerVisible: false,
    codeText: '',
    projectNameList: [],
    moduleList: [],
  })

  function onDelete(data: any) {
    Modal.confirm({
      title: '提示',
      content: '该删除只会删除数据库数据，不会影响git文件！是否要删除此数据？',
      cancelText: '取消',
      okText: '删除',
      onOk: () => {
        deletePytestTools(data.id)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      },
    })
  }

  function clickUpdate() {
    Message.loading('文件更新中，请耐心等待10秒左右...')
    getPytestToolsUpdate()
      .then((res) => {
        Message.success(res.msg)
        doRefresh()
      })
      .catch(console.log)
  }

  function onDataForm() {
    if (formItems.every((it) => (it.validator ? it.validator() : true))) {
      modalDialogRef.value?.toggle()
      let value = getFormItems(formItems)
      if (data.isAdd) {
        postPytestTools(value)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      } else {
        value['id'] = data.updateId
        putPytestTools(value)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      }
    }
  }

  function onUpdate(item: any) {
    data.actionTitle = '编辑'
    data.isAdd = false
    data.updateId = item.id
    modalDialogRef.value?.toggle()
    if (item.project_product) {
      onPytestProjectName(item.project_product.id)
    }
    nextTick(() => {
      formItems.forEach((it) => {
        const propName = item[it.key]
        if (typeof propName === 'object' && propName !== null) {
          it.value = propName.id
        } else {
          it.value = propName
        }
      })
    })
  }

  function doRefresh() {
    const value = {}
    value['page'] = pagination.page
    value['pageSize'] = pagination.pageSize
    getPytestTools(value)
      .then((res) => {
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
      })
      .catch(console.log)
  }

  function drawerOk() {
    data.drawerVisible = false
    postPytestToolsWrite(data.updateId, data.codeText)
      .then((res) => {
        data.codeText = res.data
        Message.success(res.msg)
      })
      .catch(console.log)
  }

  function onClick(record: any) {
    data.drawerVisible = true
    data.updateId = record.id
    getPytestToolsRead(record.id)
      .then((res) => {
        data.codeText = res.data
      })
      .catch(console.log)
  }

  function onPytestProjectName(projectProductId: any) {
    if (!projectProductId) {
      projectInfo.projectPytestName()
      data.projectPytest = JSON.parse(JSON.stringify(projectInfo.projectPytest))
      data.projectPytest.forEach((item) => {
        item.children.forEach((item1) => {
          delete item1.children
        })
      })
    } else {
      projectInfo.projectPytest.forEach((item) => {
        item.children.forEach((item1) => {
          if (projectProductId === item1.value) {
            data.moduleList = item1.children
          }
        })
      })
    }
    formItems.forEach((item: FormItem) => {
      if (item.key === 'module') {
        item.value = ''
      }
    })
  }

  onMounted(() => {
    nextTick(async () => {
      doRefresh()
      onPytestProjectName(null)
    })
  })
</script>
