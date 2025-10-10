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
          <a-form :model="{}" layout="inline" @keyup.enter="doRefresh">
            <a-form-item v-for="item of conditionItems" :key="item.key" :label="item.label">
              <template v-if="item.type === 'input'">
                <a-input v-model="item.value" :placeholder="item.placeholder" @blur="doRefresh" />
              </template>
              <template v-else-if="item.type === 'cascader' && item.key === 'project_product'">
                <a-cascader
                  style="width: 150px"
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="projectInfo.projectProduct"
                  value-key="key"
                  allow-clear
                  allow-search
                  @change="doRefresh(item.value, true)"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'module'">
                <a-select
                  v-model="item.value"
                  :field-names="fieldNames"
                  :options="productModule.data"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  style="width: 150px"
                  value-key="key"
                  @change="onModulePage(item.value, true)"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'page_id'">
                <a-select
                  v-model="item.value"
                  :field-names="fieldNames"
                  :options="data.pageName"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  style="width: 150px"
                  value-key="key"
                  @change="doRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'status'">
                <a-select
                  v-model="item.value"
                  :field-names="fieldNames"
                  :options="enumStore.task_status"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  style="width: 150px"
                  value-key="key"
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
                  <a-checkbox v-for="it of item.optionItems" :key="it.value" :value="it.value">
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
              <a-button size="small" type="primary" @click="onAdd">新增</a-button>
            </div>
            <div>
              <a-button size="small" status="danger" @click="onDeleteItems">批量删除</a-button>
            </div>
          </a-space>
        </template>
      </a-tabs>
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
              <a-button
                size="mini"
                type="text"
                class="custom-mini-btn"
                :loading="caseRunning"
                @click="onRunCase(record)"
                >调试
              </a-button>
              <a-button size="mini" type="text" class="custom-mini-btn" @click="onClick(record)"
                >步骤
              </a-button>
              <a-dropdown trigger="hover">
                <a-button size="mini" type="text">···</a-button>
                <template #content>
                  <a-doption>
                    <a-button
                      size="mini"
                      type="text"
                      class="custom-mini-btn"
                      @click="onUpdate(record)"
                      >编辑
                    </a-button>
                  </a-doption>
                  <!--                  <a-doption>-->
                  <!--                    <a-button-->
                  <!--                      size="mini"-->
                  <!--                      type="text"-->
                  <!--                      class="custom-mini-btn"-->
                  <!--                      @click="onPageStepsCopy(record)"-->
                  <!--                      >复制-->
                  <!--                    </a-button>-->
                  <!--                  </a-doption>-->
                  <a-doption>
                    <a-button
                      size="mini"
                      status="danger"
                      type="text"
                      class="custom-mini-btn"
                      @click="onDelete(record)"
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
          v-for="item of formItems"
          :key="item.key"
          :class="[item.required ? 'form-item__require' : 'form-item__no_require']"
          :label="item.label"
        >
          <template v-if="item.type === 'input'">
            <a-input v-model="item.value" :placeholder="item.placeholder" />
          </template>
          <template v-else-if="item.type === 'cascader'">
            <a-cascader
              v-model="item.value"
              :options="projectInfo.projectProduct"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              value-key="key"
              @change="onModuleSelect(item.value)"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'module'">
            <a-select
              v-model="item.value"
              :field-names="fieldNames"
              :options="productModule.data"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              value-key="key"
              @change="onModulePage(item.value, false)"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'page'">
            <a-select
              v-model="item.value"
              :field-names="fieldNames"
              :options="data.pageName"
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
    actionTitle: '新增',
    pageName: [],
  })
  const caseRunning = ref(false)

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
    doRefresh()
  }

  function onAdd() {
    data.actionTitle = '新增'
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
          })
          .catch(console.log)
        doRefresh()
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
          })
          .catch(console.log)
        doRefresh()
      },
    })
  }

  function onUpdate(item: any) {
    data.actionTitle = '编辑'
    data.isAdd = false
    data.updateId = item.id
    modalDialogRef.value?.toggle()
    productModule.getProjectModule(item.project_product.id)
    onModulePage(item.module.id, false)
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

  const onRunCase = async (param) => {
    if (userStore.selected_environment == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    if (caseRunning.value) return
    caseRunning.value = true
    try {
      const res = await getUiStepsTest(param.id, userStore.selected_environment)
      Message.loading(res.msg)
      doRefresh()
    } catch (e) {
    } finally {
      caseRunning.value = false
    }
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
