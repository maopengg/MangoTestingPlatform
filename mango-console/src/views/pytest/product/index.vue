<template>
  <TableBody ref="tableBody">
    <template #header>
      <a-card :bordered="false" title="项目绑定">
        <template #extra>
          <a-space>
            <a-button size="small" type="primary" @click="clickUpdate">更新项目</a-button>
            <a-button size="small" type="primary" @click="clickPush">提交项目</a-button>
          </a-space>
        </template>
        <div>
          <h4>注意项：</h4>
          <h1> 1. 右上角的**更新项目**是git pull+git clone</h1>
          <h1> 2. 右上角的**提交项目**是git push，冲突会默认接收远程最新的</h1>
          <h1>
            3.
            现在编辑文件功能，如果多个人同时编辑一个文件，那么会以最后一个人提交的为主，不会合并，所以自己编辑自己的用例~</h1
          >
        </div>
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
            :ellipsis="item.ellipsis"
            :fixed="item.fixed"
            :title="item.title"
            :tooltip="item.tooltip"
            :width="item.width"
          >
            <template v-if="item.key === 'index'" #cell="{ record }">
              {{ record.id }}
            </template>
            <template v-else-if="item.key === 'project_product'" #cell="{ record }">
              <span v-if="record?.project_product?.project && record?.project_product?.name">
                {{ record.project_product.project.name + '/' + record.project_product.name }}
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
            <template v-else-if="item.key === 'auto_type'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record?.auto_type]" size="small"
                >{{ enumStore.test_case_type[record?.auto_type].title }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <a-button size="mini" type="text" class="custom-mini-btn" @click="onUpdate(record)"
                >编辑
              </a-button>
              <a-button size="mini" type="text" class="custom-mini-btn" @click="onEditFile(record)"
                >初始化文件
              </a-button>
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
      <BaseSidePanel
        :visible="data.drawerVisible"
        :title="'编辑代码'"
        :width="1000"
        @update:visible="
          (val) => {
            data.drawerVisible = val
          }
        "
        @cancel="
          () => {
            data.drawerVisible = false
          }
        "
      >
        <template #default>
          <div>
            <CodeEditor v-model="data.codeText" placeholder="输入python代码" />
          </div>
        </template>
        <template #extra-buttons>
          <a-button type="primary" @click="drawerOk">保存</a-button>
        </template>
      </BaseSidePanel>
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
          <template v-else-if="item.type === 'textarea'">
            <a-textarea
              v-model="item.value"
              :auto-size="{ minRows: 3, maxRows: 5 }"
              :placeholder="item.placeholder"
            />
          </template>
          <template v-else-if="item.type === 'cascader'">
            <a-cascader
              v-model="item.value"
              :options="projectInfo.projectProduct"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
            />
          </template>

          <template v-else-if="item.type === 'select' && item.key === 'auto_type'">
            <a-select
              v-model="item.value"
              :field-names="fieldNames"
              :options="enumStore.test_case_type"
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
  import { ModalDialogType } from '@/types/components'
  import { Message, Modal } from '@arco-design/web-vue'
  import { nextTick, onMounted, reactive, ref } from 'vue'
  import { getFormItems } from '@/utils/datacleaning'
  import { fieldNames } from '@/setting'
  import { formItems, tableColumns } from './config'
  import { useProject } from '@/store/modules/get-project'
  import { useEnum } from '@/store/modules/get-enum'
  import {
    deletePytestProduct,
    getPytestProduct,
    getPytestProductRead,
    getPytestPush,
    getPytestUpdate,
    postPytestProduct,
    postPytestProductWrite,
    putPytestProduct,
  } from '@/api/pytest/product'
  import CodeEditor from '@/components/CodeEditor.vue'
  import BaseSidePanel from '@/components/BaseSidePanel.vue'

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
  })

  function onDelete(record: any) {
    Modal.confirm({
      title: '提示',
      content: '该删除只会删除数据库数据，不会影响git文件！是否要删除此数据？',
      cancelText: '取消',
      okText: '删除',
      onOk: () => {
        deletePytestProduct(record.id)
          .then((res) => {
            Message.success(res.msg)
          })
          .catch(console.log)
          .finally(() => {
            doRefresh()
            projectInfo.projectPytestName()
          })
      },
    })
  }

  function clickUpdate() {
    Message.loading('项目更新中...')

    getPytestUpdate()
      .then((res) => {
        Message.success(res.msg)
        doRefresh()
      })
      .catch(console.log)
  }

  function clickPush() {
    Message.loading('项目提交中...')
    getPytestPush()
      .then((res) => {
        Message.success(res.msg)
      })
      .catch(console.log)
  }

  function onDataForm() {
    if (formItems.every((it) => (it.validator ? it.validator() : true))) {
      let value = getFormItems(formItems)
      if (data.isAdd) {
        postPytestProduct(value)
          .then((res) => {
            modalDialogRef.value?.toggle()
            Message.success(res.msg)
            doRefresh()
            projectInfo.projectPytestName()
          })
          .catch((error) => {
            console.log(error)
          })
          .finally(() => {
            modalDialogRef.value?.setConfirmLoading(false)
          })
      } else {
        value['id'] = data.updateId
        putPytestProduct(value)
          .then((res) => {
            modalDialogRef.value?.toggle()
            Message.success(res.msg)
            doRefresh()
            projectInfo.projectPytestName()
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

  function onUpdate(item: any) {
    data.actionTitle = '编辑'
    data.isAdd = false
    data.updateId = item.id
    modalDialogRef.value?.toggle()
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
    getPytestProduct(value)
      .then((res) => {
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
      })
      .catch(console.log)
  }

  function drawerOk() {
    data.drawerVisible = false
    postPytestProductWrite(data.updateId, data.codeText)
      .then((res) => {
        data.codeText = res.data
        Message.success(res.msg)
      })
      .catch(console.log)
  }

  function onEditFile(record: any) {
    data.drawerVisible = true
    data.updateId = record.id
    getPytestProductRead(record.id)
      .then((res) => {
        data.codeText = res.data
      })
      .catch(console.log)
  }

  onMounted(() => {
    nextTick(async () => {
      doRefresh()
    })
  })
</script>
