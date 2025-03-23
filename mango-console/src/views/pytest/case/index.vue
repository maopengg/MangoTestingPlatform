<template>
  <TableBody ref="tableBody">
    <template #header>
      <a-card :bordered="false" title="测试用例">
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
            <template v-else-if="item.key === 'case_people'" #cell="{ record }">
              {{ record.case_people?.name }}
            </template>
            <template v-else-if="item.key === 'file_status'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record.file_status]" size="small"
                >{{ enumStore.file_status[record.file_status].title }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'status'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record.status]" size="small"
                >{{ enumStore.task_status[record.status].title }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'level'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record.level]" size="small">
                {{ record.level !== null ? enumStore.case_level[record.level].title : '-' }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <a-button size="mini" type="text" @click="onRun(record)">执行</a-button>
              <a-button size="mini" type="text" @click="onClick(record)">文件</a-button>
              <a-dropdown trigger="hover">
                <a-button size="mini" type="text">···</a-button>
                <template #content>
                  <a-doption>
                    <a-button size="mini" type="text" @click="onUpdate(record)">编辑</a-button>
                  </a-doption>
                  <a-doption>
                    <a-button size="mini" type="text" @click="onResult(record)">结果</a-button>
                  </a-doption>
                  <a-doption>
                    <a-button size="mini" status="danger" type="text" @click="onDelete(record)"
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
        :visible="data.drawerVisible"
        :width="1000"
        unmountOnClose
        @cancel="data.drawerVisible = false"
        @ok="drawerOk"
      >
        <template #title> {{ data.isResult ? '查看测试结果' : '编辑代码' }}</template>
        <div v-if="!data.isResult">
          <CodeEditor v-model="data.codeText" :lineHeight="600" placeholder="输入python代码" />
        </div>
        <div v-else>
          <a-collapse
            v-for="item of data?.codeText"
            :key="item.uuid"
            :bordered="false"
            accordion
            destroy-on-hide
          >
            <a-collapse-item
              :key="item.uuid"
              :header="item.name + '-' + item.status"
              :style="customStyle"
            >
              <PytestTestReport :resultData="item" />
            </a-collapse-item>
          </a-collapse>
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
            <a-select
              v-model="item.value"
              :options="data.moduleList"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              value-key="key"
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
          <template v-else-if="item.type === 'select' && item.key === 'level'">
            <a-select
              v-model="item.value"
              :field-names="fieldNames"
              :options="enumStore.case_level"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              value-key="key"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'case_people'">
            <a-select
              v-model="item.value"
              :field-names="fieldNames"
              :options="data.userList"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              value-key="key"
              @change="doRefresh"
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
    deletePytestCase,
    getPytestCase,
    getPytestCaseRead,
    getPytestCaseTest,
    getPytestCaseUpdate,
    postPytestCase,
    postPytestCaseWrite,
    putPytestCase,
  } from '@/api/pytest/case'
  import CodeEditor from '@/components/CodeEditor.vue'
  import { getUserName } from '@/api/user/user'
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
    actionTitle: '添加页面',
    drawerVisible: false,
    codeText: '',
    projectPytest: [],
    moduleList: [],
    isResult: false,
  })

  const customStyle = reactive({
    borderRadius: '6px',
    marginBottom: '2px',
    border: 'none',
    overflow: 'hidden',
  })

  function onDelete(data: any) {
    Modal.confirm({
      title: '提示',
      content: '该删除只会删除数据库数据，不会影响git文件！是否要删除此数据？',
      cancelText: '取消',
      okText: '删除',
      onOk: () => {
        deletePytestCase(data.id)
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

    getPytestCaseUpdate()
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
        postPytestCase(value)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      } else {
        value['id'] = data.updateId
        putPytestCase(value)
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
    getPytestCase(value)
      .then((res) => {
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
      })
      .catch(console.log)
  }

  function onRun(record: any) {
    Message.loading('准备开始执行，请前往测试任务中查看测试结果~')
    getPytestCaseTest(record.id)
      .then((res) => {
        Message.success(res.msg)
        doRefresh()
      })
      .catch(console.log)
  }

  function drawerOk() {
    data.drawerVisible = false
    postPytestCaseWrite(data.updateId, data.codeText)
      .then((res) => {
        data.codeText = res.data
        Message.success(res.msg)
      })
      .catch(console.log)
  }

  function onResult(record: any) {
    data.isResult = true
    data.drawerVisible = true
    data.codeText = record.result_data
  }

  function onClick(record: any) {
    data.isResult = false
    data.drawerVisible = true
    data.updateId = record.id
    getPytestCaseRead(record.id)
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

  function getNickName() {
    getUserName()
      .then((res) => {
        data.userList = res.data
      })
      .catch(console.log)
  }

  onMounted(() => {
    nextTick(async () => {
      doRefresh()
      getNickName()
      onPytestProjectName(null)
    })
  })
</script>
