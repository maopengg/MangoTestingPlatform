<template>
  <div>
    <div class="main-container">
      <TableBody ref="tableBody">
        <template #header>
          <TableHeader
            :show-filter="true"
            title="Ui元素页面对象"
            @search="doRefresh"
            @reset-search="onResetSearch"
          >
            <template #search-content>
              <a-form layout="inline" :model="{}" @keyup.enter="doRefresh">
                <a-form-item v-for="item of conditionItems" :key="item.key" :label="item.label">
                  <template v-if="item.type === 'input'">
                    <a-input
                      v-model="item.value"
                      :placeholder="item.placeholder"
                      @change="doRefresh"
                    />
                  </template>
                  <template v-else-if="item.type === 'select' && item.key === 'module_name'">
                    <a-select
                      style="width: 150px"
                      v-model="item.value"
                      :placeholder="item.placeholder"
                      :options="data.moduleList"
                      :field-names="fieldNames"
                      value-key="key"
                      allow-clear
                      allow-search
                      @change="doRefresh"
                    />
                  </template>
                  <template v-if="item.type === 'date'">
                    <a-date-picker v-model="item.value" />
                  </template>
                  <template v-if="item.type === 'time'">
                    <a-time-picker v-model="item.value" value-format="HH:mm:ss" />
                  </template>
                  <template v-if="item.type === 'check-group'">
                    <a-checkbox-group v-model="item.value">
                      <a-checkbox v-for="it of item.optionItems" :value="it.value" :key="it.value">
                        {{ item.label }}
                      </a-checkbox>
                    </a-checkbox-group>
                  </template>
                </a-form-item>
              </a-form>
            </template>
          </TableHeader>
        </template>

        <template #default>
          <a-tabs @tab-click="(key) => switchType(key)">
            <template #extra>
              <a-space>
                <a-button type="primary" size="small" @click="onAddPage">新增</a-button>
                <a-button status="danger" size="small" @click="onDeleteItems">批量删除</a-button>
              </a-space>
            </template>
            <a-tab-pane key="0" title="Web页面对象" />
            <a-tab-pane key="1" title="Android页面对象" />
            <a-tab-pane key="2" title="IOS页面对象" />
            <a-tab-pane key="3" title="桌面页面对象" />
          </a-tabs>
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
                  {{ record.project_product?.project?.name + '/' + record.project_product?.name }}
                </template>
                <template v-else-if="item.key === 'module'" #cell="{ record }">
                  {{ record.module?.superior_module ? record.module?.superior_module + '/' : ''
                  }}{{ record.module?.name }}
                </template>
                <template v-else-if="item.key === 'actions'" #cell="{ record }">
                  <a-button type="text" size="mini" @click="onUpdate(record)">编辑</a-button>
                  <a-button type="text" size="mini" @click="onClick(record)">添加元素</a-button>
                  <a-dropdown trigger="hover">
                    <a-button type="text" size="mini">···</a-button>
                    <template #content>
                      <a-doption>
                        <a-button type="text" size="mini" @click="PageCopy(record.id)"
                          >复制</a-button
                        >
                      </a-doption>
                      <a-doption>
                        <a-button status="danger" type="text" size="mini" @click="onDelete(record)"
                          >删除</a-button
                        >
                      </a-doption>
                    </template>
                  </a-dropdown>
                </template>
              </a-table-column>
            </template>
          </a-table>
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
              <template v-else-if="item.type === 'cascader' && item.key === 'project_product'">
                <a-cascader
                  v-model="item.value"
                  @change="getProjectModule(item.value)"
                  :placeholder="item.placeholder"
                  :options="data.projectProductName"
                  allow-search
                  allow-clear
                />

                <!--                <a-select-->
                <!--                  v-model="item.value"-->
                <!--                  :placeholder="item.placeholder"-->
                <!--                  :options="data.projectProductName"-->
                <!--                  :field-names="fieldNames"-->
                <!--                  @change="getProjectModule(item.value)"-->
                <!--                  value-key="key"-->
                <!--                  allow-clear-->
                <!--                  allow-search-->
                <!--                />-->
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
    </div>
  </div>
</template>

<script lang="ts" setup>
  import { getUiPage, deleteUiPage, postUiPage, putUiPage, postUiPageCopy } from '@/api/uitest'
  import { usePagination, useRowKey, useRowSelection, useTable } from '@/hooks/table'
  import { ModalDialogType } from '@/types/components'
  import { Message, Modal } from '@arco-design/web-vue'
  import { onMounted, ref, nextTick, reactive } from 'vue'
  import { useRouter } from 'vue-router'
  import { getFormItems } from '@/utils/datacleaning'
  import { fieldNames } from '@/setting'
  import { useProjectModule } from '@/store/modules/project_module'
  import { usePageData } from '@/store/page-data'
  import { conditionItems, tableColumns, formItems } from './config'
  import { getUserProjectModuleGetAll, getUserProjectProductName } from '@/api/user'

  const projectModule = useProjectModule()
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const pagination = usePagination(doRefresh)
  const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection()
  const table = useTable()
  const rowKey = useRowKey('id')
  const formModel = ref({})
  const router = useRouter()

  const data: any = reactive({
    isAdd: false,
    updateId: 0,
    actionTitle: '添加页面',
    pageType: 0,
    moduleList: projectModule.data,
    projectProductName: [],
  })

  function switchType(key: any) {
    data.pageType = key
    doRefresh()
  }

  function onResetSearch() {
    conditionItems.forEach((it) => {
      it.value = ''
    })
  }

  function onAddPage() {
    data.actionTitle = '添加页面'
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

  function onDelete(data: any) {
    Modal.confirm({
      title: '提示',
      content: '是否要删除此页面？',
      cancelText: '取消',
      okText: '删除',
      onOk: () => {
        deleteUiPage(data.id)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      },
    })
  }

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
        deleteUiPage(selectedRowKeys.value)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      },
    })
  }
  function onDataForm() {
    if (formItems.every((it) => (it.validator ? it.validator() : true))) {
      modalDialogRef.value?.toggle()
      let value = getFormItems(formItems)
      value['type'] = data.pageType
      if (data.isAdd) {
        postUiPage(value)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      } else {
        value['id'] = data.updateId
        putUiPage(value)
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
    getProjectModule(item.project.id)
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
    const value = getFormItems(conditionItems)
    value['type'] = data.pageType
    value['page'] = pagination.page
    value['pageSize'] = pagination.pageSize
    getUiPage(value)
      .then((res) => {
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
      })
      .catch(console.log)
  }
  function PageCopy(id: number) {
    postUiPageCopy(id)
      .then((res) => {
        Message.success(res.msg)
      })
      .catch(console.log)
  }

  function getProjectModule(projectProductId: number) {
    doRefresh()
    getUserProjectModuleGetAll(projectProductId)
      .then((res) => {
        data.moduleList = res.data
      })
      .catch((error) => {
        console.error(error)
      })
  }
  function projectProductName() {
    getUserProjectProductName()
      .then((res) => {
        data.projectProductName = res.data
      })
      .catch((error) => {
        console.error(error)
      })
  }

  function onClick(record: any) {
    const pageData = usePageData()
    pageData.setRecord(record)
    router.push({
      path: '/uitest/page/elements',
      query: {
        id: record.id,
        pageType: data.pageType,
      },
    })
  }

  onMounted(() => {
    nextTick(async () => {
      doRefresh()
      projectProductName()
    })
  })
</script>
