<template>
  <TableBody ref="tableBody">
    <template #header>
      <a-card :bordered="false" title="项目绑定">
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
            <template v-else-if="item.key === 'client'" #cell="{ record }">
              <a-tag
                :color="enumStore.colors[record.project_product.ui_client_type]"
                size="small"
                >{{ enumStore.drive_type[record.project_product.ui_client_type].title }}</a-tag
              >
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <a-button type="text" size="mini" @click="onUpdate(record)">编辑</a-button>
              <a-button type="text" size="mini" @click="onClick(record)">模块</a-button>
              <a-dropdown trigger="hover">
                <a-button type="text" size="mini">···</a-button>
                <template #content>
                  <a-doption>
                    <a-button type="text" size="mini" @click="onEditFile(record)"
                      >初始化文件</a-button
                    >
                  </a-doption>
                  <a-doption>
                    <a-button status="danger" type="text" size="mini" @click="onDelete()"
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
          <template v-else-if="item.type === 'textarea'">
            <a-textarea
              v-model="item.value"
              :placeholder="item.placeholder"
              :auto-size="{ minRows: 3, maxRows: 5 }"
            />
          </template>
          <template v-else-if="item.type === 'cascader'">
            <a-cascader
              v-model="item.value"
              @change="onModuleSelect(item.value)"
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
              :options="productModule.data"
              :field-names="fieldNames"
              value-key="key"
              allow-clear
              allow-search
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'type'">
            <a-select
              v-model="item.value"
              :placeholder="item.placeholder"
              :options="productModule.data"
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
  import { FormItem, ModalDialogType } from '@/types/components'
  import { Message } from '@arco-design/web-vue'
  import { onMounted, ref, nextTick, reactive } from 'vue'
  import { useRouter } from 'vue-router'
  import { getFormItems } from '@/utils/datacleaning'
  import { fieldNames } from '@/setting'
  import { useProductModule } from '@/store/modules/project_module'
  import { usePageData } from '@/store/page-data'
  import { tableColumns, formItems } from './config'
  import { useProject } from '@/store/modules/get-project'
  import { useEnum } from '@/store/modules/get-enum'
  import {
    getPytestProject,
    getPytestProjectRead,
    getPytestUpdate,
    postPytestProject,
    postPytestProjectWrite,
    putPytestProject,
  } from '@/api/pytest/project'
  import CodeEditor from '@/components/CodeEditor.vue'

  const productModule = useProductModule()
  const projectInfo = useProject()
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const pagination = usePagination(doRefresh)
  const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection()
  const table = useTable()
  const rowKey = useRowKey('id')
  const formModel = ref({})
  const router = useRouter()
  const enumStore = useEnum()

  const data: any = reactive({
    isAdd: false,
    updateId: 0,
    actionTitle: '添加页面',
    drawerVisible: false,
    codeText: '',
  })

  function onDelete() {
    Message.error('请在git中删除项目目录~')
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

  function onDataForm() {
    if (formItems.every((it) => (it.validator ? it.validator() : true))) {
      modalDialogRef.value?.toggle()
      let value = getFormItems(formItems)
      if (data.isAdd) {
        postPytestProject(value)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      } else {
        value['id'] = data.updateId
        putPytestProject(value)
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
    productModule.getProjectModule(item.project_product.id)
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
    getPytestProject(value)
      .then((res) => {
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
      })
      .catch(console.log)
  }

  function onModuleSelect(projectProductId: number) {
    productModule.getProjectModule(projectProductId)
    formItems.forEach((item: FormItem) => {
      if (item.key === 'module') {
        item.value = ''
      }
    })
  }

  function onClick(record: any) {
    const pageData = usePageData()
    pageData.setRecord(record)
    router.push({
      path: '/pytest/project/module',
      query: {
        id: record.id,
      },
    })
  }

  function drawerOk() {
    data.drawerVisible = false
    postPytestProjectWrite(data.updateId, data.codeText)
      .then((res) => {
        data.codeText = res.data
        Message.success(res.msg)
      })
      .catch(console.log)
  }

  function onEditFile(record: any) {
    data.drawerVisible = true
    data.updateId = record.id
    getPytestProjectRead(record.id)
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
