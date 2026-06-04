<template>
  <TableBody ref="tableBody">
    <template #header>
      <TableHeader
        :show-filter="true"
        title="调试页面步骤"
        @search="onSearchRefresh"
        @reset-search="onResetSearch"
      >
        <template #search-content>
          <a-form :model="{}" layout="inline" @keyup.enter="onSearchRefresh">
            <a-form-item v-for="item of conditionItems" :key="item.key" :label="item.label">
              <template v-if="item.type === 'input'">
                <a-input
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  allow-clear
                  @blur="onSearchRefresh"
                  @clear="onSearchRefresh"
                />
              </template>
              <template v-else-if="item.type === 'cascader' && item.key === 'project_product'">
                <ProjectProductSelect
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  @change="onSearchProjectProductChange"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'module'">
                <ProductModuleSelect
                  v-model="item.value"
                  :project-product-id="getConditionValue('project_product')"
                  :placeholder="item.placeholder"
                  :auto-clear="false"
                  @change="onSearchModuleChange"
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
                  value-key="key"
                  @change="onSearchRefresh"
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
                  value-key="key"
                  @change="onSearchRefresh"
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
              <a-button size="small" status="danger" @click="onDelete(null)">批量删除</a-button>
            </div>
          </a-space>
        </template>
      </a-tabs>
      <a-table
        :scroll="{ x: 1100 }"
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
              {{ formatProjectProductPath(record?.project_product) }}
            </template>
            <template v-else-if="item.key === 'module'" #cell="{ record }">
              {{ formatModulePath(record?.module) }}
            </template>
            <template v-else-if="item.key === 'page'" #cell="{ record }">
              {{ record.page.name }}
            </template>
            <template v-else-if="item.key === 'status'" #cell="{ record }">
              <a-tag :color="enumStore.status_colors[record.status]" size="small"
                >{{ enumStore.task_status[record.status]?.title || '-' }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <MangoTableActions
                :actions="[
                  { label: '调试', loading: caseRunning, onClick: () => onRunCase(record) },
                  { label: '步骤', onClick: () => onClick(record) },
                  { label: '编辑', onClick: () => onUpdate(record) },
                  { label: '删除', danger: true, onClick: () => onDelete(record) },
                ]"
              />
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
          :class="[item.required ? 'mango-form-item__require' : 'mango-form-item__no_require']"
          :label="item.label"
        >
          <template v-if="item.type === 'input'">
            <a-input v-model="item.value" :placeholder="item.placeholder" />
          </template>
          <template v-else-if="item.type === 'cascader'">
            <ProjectProductSelect
              v-model="item.value"
              :placeholder="item.placeholder"
              @change="onFormProjectProductChange"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'module'">
            <ProductModuleSelect
              v-model="item.value"
              :project-product-id="getFormItemValue('project_product')"
              :placeholder="item.placeholder"
              :auto-clear="false"
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
  import { ModalDialogType } from '@/types/components'
  import { Message, Modal } from '@arco-design/web-vue'
  import { nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'
  import { useRouter } from 'vue-router'
  import { fieldNames } from '@/setting'
  import { getFormItems } from '@/utils/datacleaning'
  import { usePageData } from '@/store/page-data'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import {
    formatModulePath,
    formatProjectProductPath,
    getItemValue,
    setItemValue,
  } from '@/utils/business-format'
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
  const pollingTimer = ref<NodeJS.Timeout | null>(null)

  function clearPollingTimer() {
    if (pollingTimer.value) {
      clearInterval(pollingTimer.value)
      pollingTimer.value = null
    }
  }

  function getConditionValue(key: string) {
    return getItemValue(conditionItems, key)
  }

  function getFormItemValue(key: string) {
    return getItemValue(formItems, key)
  }

  function onSearchProjectProductChange(value: any) {
    setItemValue(conditionItems, 'module', '')
    setItemValue(conditionItems, 'page_id', '')
    data.pageName = []
    doRefresh(value, true, true)
  }

  function onSearchModuleChange(value: any) {
    setItemValue(conditionItems, 'page_id', '')
    onModulePage(value, true)
  }

  function onFormProjectProductChange() {
    setItemValue(formItems, 'module', '')
    setItemValue(formItems, 'page', '')
    data.pageName = []
  }

  function onSearchRefresh() {
    doRefresh(null, false, true)
  }

  function doRefresh(projectProductId: any = null, bool_ = false, showLoading = false) {
    clearPollingTimer()
    if (showLoading) {
      table.tableLoading.value = true
    }
    let value = getFormItems(conditionItems)
    value['page'] = pagination.page
    value['pageSize'] = pagination.pageSize
    if (projectProductId && bool_) {
      value['project_product'] = projectProductId
    }
    getUiSteps(value)
      .then((res) => {
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
        const hasRunningItem =
          res.data && Array.isArray(res.data) && res.data.some((item: any) => item.status === 3)

        if (hasRunningItem) {
          // 5秒后再次刷新
          pollingTimer.value = setInterval(() => {
            doRefresh(projectProductId, bool_, false)
          }, 5000)
        }
      })
      .catch(console.log)
      .finally(() => {
        if (showLoading) {
          table.tableLoading.value = false
        }
      })
  }

  function onResetSearch() {
    conditionItems.forEach((it) => {
      it.value = ''
    })
    doRefresh(null, false, true)
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
      content: '是否要删除此步骤？',
      cancelText: '取消',
      okText: '删除',
      onBeforeOk: () => {
        return deleteUiSteps(batch ? selectedRowKeys.value : record.id)
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

  function onUpdate(item: any) {
    data.actionTitle = '编辑'
    data.isAdd = false
    data.updateId = item.id
    modalDialogRef.value?.toggle()
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
      let value = getFormItems(formItems)
      if (data.isAdd) {
        postUiSteps(value)
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
        value['parent_id'] = data.updateId
        putUiSteps(value)
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
    } catch (e) {
    } finally {
      caseRunning.value = false
      doRefresh()
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
      doRefresh(null, false, true)
    }
    getUiPageName(moduleId)
      .then((res) => {
        data.pageName = res.data
      })
      .catch(() => {
        data.pageName = []
        setItemValue(formItems, 'page', null)
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

  onMounted(() => {
    nextTick(async () => {
      doRefresh()
      onModulePage(null, false)
    })
  })
  onUnmounted(() => {
    clearPollingTimer()
  })
</script>
