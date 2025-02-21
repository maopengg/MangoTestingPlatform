<template>
  <TableBody ref="tableBody">
    <template #header>
      <a-card :bordered="false" title="过程对象">
        <template #extra>
          <a-button type="primary" size="small" @click="clickUpdate">更新项目</a-button>
        </template>
      </a-card>
    </template>

    <template #default>
      <a-table
        :bordered="false"
        :row-selection="{ selectedRowKeys, showCheckedAll }"
        :loading="table.tableLoading.value"
        :data="table.dataList"
        :columns="tableColumns"
        :pagination="false"
        :rowKey="rowKey"
        @selection-change="onSelectionChange"
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
            <template v-else-if="item.key === 'pytest_project'" #cell="{ record }">
              {{ record?.pytest_project?.name }}
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
              <a-tag :color="enumStore.colors[record.file_status]" size="small">{{
                enumStore.file_status[record.file_status].title
              }}</a-tag>
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <a-button type="text" size="mini" @click="onUpdate(record)">编辑</a-button>
              <a-button type="text" size="mini" @click="onClick(record)">文件</a-button>
              <a-dropdown trigger="hover">
                <a-button type="text" size="mini">···</a-button>
                <template #content>
                  <a-doption>
                    <a-button status="danger" type="text" size="mini" @click="onDelete(record)"
                      >删除
                    </a-button>
                  </a-doption>
                </template>
              </a-dropdown>
            </template>
          </a-table-column>
        </template>
      </a-table>
      <a-drawer
        :width="1000"
        :visible="data.drawerVisible"
        @ok="drawerOk"
        @cancel="data.drawerVisible = false"
        unmountOnClose
      >
        <template #title> 编辑代码</template>
        <div>
          <CodeEditor v-model="data.codeText" />
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
          :class="[item.required ? 'form-item__require' : 'form-item__no_require']"
          :label="item.label"
          v-for="item of formItems"
          :key="item.key"
        >
          <template v-if="item.type === 'input'">
            <a-input :placeholder="item.placeholder" v-model="item.value" />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'pytest_project'">
            <a-select
              v-model="item.value"
              :placeholder="item.placeholder"
              :options="data.projectNameList"
              :field-names="fieldNames"
              value-key="key"
              @change="onModuleSelect(item.value)"
              allow-clear
              allow-search
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
  import { onMounted, ref, nextTick, reactive } from 'vue'
  import { getFormItems } from '@/utils/datacleaning'
  import { fieldNames } from '@/setting'
  import { tableColumns, formItems } from './config'
  import { useEnum } from '@/store/modules/get-enum'
  import {
    getPytestAct,
    getPytestActRead,
    getPytestActUpdate,
    postPytestAct,
    postPytestActWrite,
    putPytestAct,
  } from '@/api/pytest/act'
  import { deletePytestTools } from '@/api/pytest/tools'
  import CodeEditor from '@/components/CodeEditor.vue'
  import { getPytestProjectName } from '@/api/pytest/project'
  import { getPytestModuleName } from '@/api/pytest/module'

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
    actionTitle: '添加',
    drawerVisible: false,
    codeText: '',
    projectNameList: [],
    moduleList: [],
  })

  function onDelete(data: any) {
    Message.info('该删除只会删除数据库数据，不会影响git文件！')
    Modal.confirm({
      title: '提示',
      content: '是否要删除此数据？',
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
    Message.loading('ACT目录更新中...')
    getPytestActUpdate()
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
        postPytestAct(value)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      } else {
        value['id'] = data.updateId
        putPytestAct(value)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      }
    }
  }

  function onUpdate(item: any) {
    data.actionTitle = '编辑页面'
    data.isAdd = false
    data.updateId = item.id
    modalDialogRef.value?.toggle()
    onPytestProjectName()
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
    getPytestAct(value)
      .then((res) => {
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
      })
      .catch(console.log)
  }

  function drawerOk() {
    data.drawerVisible = false
    postPytestActWrite(data.updateId, data.codeText)
      .then((res) => {
        data.codeText = res.data
        Message.success(res.msg)
      })
      .catch(console.log)
  }
  function onPytestProjectName() {
    getPytestProjectName()
      .then((res) => {
        data.projectNameList = res.data
      })
      .catch(console.log)
  }
  function onModuleSelect(pytestProductId: number) {
    getPytestModuleName(pytestProductId)
      .then((res) => {
        data.moduleList = res.data
      })
      .catch(console.log)
  }

  function onClick(record: any) {
    data.drawerVisible = true
    data.updateId = record.id
    getPytestActRead(record.id)
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
