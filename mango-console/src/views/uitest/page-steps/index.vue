<template>
  <TableBody ref="tableBody">
    <template #header>
      <TableHeader
        :show-filter="true"
        title="调试页面步骤"
        @search="doRefresh"
        @reset-search="onResetSearch"
      >
        <template #search-content>
          <a-form layout="inline" :model="{}" @keyup.enter="doRefresh">
            <a-form-item v-for="item of conditionItems" :key="item.key" :label="item.label">
              <template v-if="item.type === 'input'">
                <a-input v-model="item.value" :placeholder="item.placeholder" @blur="doRefresh" />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'project_product'">
                <a-select
                  style="width: 150px"
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="projectInfo.projectProductList"
                  :field-names="fieldNames"
                  value-key="key"
                  allow-clear
                  allow-search
                  @change="doRefresh(item.value, true)"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'module'">
                <a-select
                  style="width: 150px"
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="productModule.data"
                  :field-names="fieldNames"
                  value-key="key"
                  allow-clear
                  allow-search
                  @change="onModulePage(item.value, true)"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'page'">
                <a-select
                  style="width: 150px"
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="data.pageName"
                  :field-names="fieldNames"
                  value-key="key"
                  allow-clear
                  allow-search
                  @change="doRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'status'">
                <a-select
                  style="width: 150px"
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="enumStore.task_status"
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
      <a-tabs>
        <template #extra>
          <a-space>
            <div>
              <a-button type="primary" size="small" @click="onAddPage">新增</a-button>
            </div>
            <div>
              <a-button status="danger" size="small" @click="onDeleteItems">批量删除</a-button>
            </div>
          </a-space>
        </template>
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
            :ellipsis="item.ellipsis"
            :tooltip="item.tooltip"
          >
            <template v-if="item.key === 'index'" #cell="{ record }">
              {{ record.id }}
            </template>
            <template v-else-if="item.key === 'project_product'" #cell="{ record }">
              {{ record?.project_product?.project?.name + '/' + record?.project_product?.name }}
            </template>
            <template v-else-if="item.key === 'module'" #cell="{ record }">
              {{ record?.module?.superior_module ? record?.module?.superior_module + '/' : ''
              }}{{ record?.module?.name }}
            </template>
            <template v-else-if="item.key === 'page'" #cell="{ record }">
              {{ record.page.name }}
            </template>
            <template v-else-if="item.key === 'status'" #cell="{ record }">
              <a-tag :color="enumStore.status_colors[record.status]" size="small"
                >{{ enumStore.task_status[record.status].title }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <a-button type="text" size="mini" @click="onRunCase(record)">调试</a-button>
              <a-button type="text" size="mini" @click="onClick(record)">步骤</a-button>
              <a-dropdown trigger="hover">
                <a-button type="text" size="mini">···</a-button>
                <template #content>
                  <a-doption>
                    <a-button type="text" size="mini" @click="onUpdate(record)">编辑</a-button>
                  </a-doption>
                  <a-doption>
                    <a-button type="text" size="mini" @click="onPageStepsCopy(record)"
                      >复制
                    </a-button>
                  </a-doption>
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
          <template v-else-if="item.type === 'cascader'">
            <a-cascader
              v-model="item.value"
              @change="onModuleSelect(item.value)"
              :placeholder="item.placeholder"
              :options="projectInfo.projectProduct"
              value-key="key"
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
              @change="onModulePage(item.value, false)"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'page'">
            <a-select
              v-model="item.value"
              :placeholder="item.placeholder"
              :options="data.pageName"
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
  import { Message, Modal } from '@arco-design/web-vue'
  import { nextTick, onMounted, reactive, ref } from 'vue'
  import { useRouter } from 'vue-router'
  import { useProject } from '@/store/modules/get-project'
  import { fieldNames } from '@/setting'
  import { getFormItems } from '@/utils/datacleaning'
  import { useProductModule } from '@/store/modules/project_module'
  import { usePageData } from '@/store/page-data'
  import {
    deleteUiSteps,
    getUiPageStepsCopy,
    getUiSteps,
    getUiStepsTest,
    postUiSteps,
    putUiSteps,
  } from '@/api/uitest/page-steps'
  import { getUiPageName } from '@/api/uitest/page'
  import { conditionItems, formItems, tableColumns } from './config'
  import { useEnum } from '@/store/modules/get-enum'
  import useUserStore from '@/store/modules/user'

  const productModule = useProductModule()
  const projectInfo = useProject()
  const enumStore = useEnum()
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const pagination = usePagination(doRefresh)
  const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection()
  const table = useTable()
  const rowKey = useRowKey('id')
  const userStore = useUserStore()

  const formModel = ref({})
  const data = reactive({
    isAdd: false,
    updateId: 0,
    actionTitle: '添加测试对象',
    pageName: [],
  })

  function doRefresh(projectProductId: number | null = null, bool_ = false) {
    let value = getFormItems(conditionItems)
    value['page'] = pagination.page
    value['pageSize'] = pagination.pageSize
    if (projectProductId && bool_) {
      value['project_product'] = projectProductId
      productModule.getProjectModule(projectProductId)
    }
    getUiSteps(value)
      .then((res) => {
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
      })
      .catch(console.log)
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
    formItems.forEach((it: any) => {
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
      content: '是否要删除此步骤？',
      cancelText: '取消',
      okText: '删除',
      onOk: () => {
        deleteUiSteps(data.id)
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
        deleteUiSteps(selectedRowKeys.value)
          .then((res) => {
            Message.success(res.msg)
            // selectedRowKeys.value = []
            doRefresh()
          })
          .catch(console.log)
      },
    })
  }

  function onUpdate(item: any) {
    data.actionTitle = '编辑步骤'
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
          it.value = item.name
        }
      })
    })
  }

  function onDataForm() {
    if (formItems.every((it) => (it.validator ? it.validator() : true))) {
      modalDialogRef.value?.toggle()
      let value = getFormItems(formItems)
      if (data.isAdd) {
        postUiSteps(value)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      } else {
        value['id'] = data.updateId
        putUiSteps(value)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      }
    }
  }

  function onRunCase(record: any) {
    if (userStore.selected_environment == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    getUiStepsTest(record.id, userStore.selected_environment)
      .then((res) => {
        Message.loading(res.msg)
      })
      .catch(console.log)
  }

  const router = useRouter()

  function onClick(record: any) {
    const pageData = usePageData()
    pageData.setRecord(record)
    router.push({
      path: '/uitest/page/steps/details',
      query: {
        id: parseInt(record.id, 10),
        pageId: record.page.id,
        pageType: record.project_product.ui_client_type,
      },
    })
  }

  function onModulePage(moduleId: any, refresh: boolean) {
    if (refresh) {
      doRefresh()
    }
    getUiPageName(moduleId)
      .then((res) => {
        data.pageName = res.data
      })
      .catch(() => {
        data.pageName = []
        formItems.forEach((obj: FormItem) => {
          if (obj.key == 'page') {
            obj.value = null
          }
        })
      })
  }

  function onPageStepsCopy(record: any) {
    getUiPageStepsCopy(record.id)
      .then((res) => {
        Message.success(res.msg)
        doRefresh()
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

  onMounted(() => {
    nextTick(async () => {
      doRefresh()
      onModulePage(null, false)
    })
  })
</script>
