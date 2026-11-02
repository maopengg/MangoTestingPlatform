<template>
  <TableBody ref="tableBody" plain class="mango-detail-workbench-page">
    <template #header>
      <TableHeader title="页面元素" />
    </template>
    <template #default>
      <ProjectProductNavigationWorkbench
        contained-body
        show-modules
        :model-value="getConditionValue('project_product')"
        :module-value="getConditionValue('module')"
        :reset-key="sidebarResetKey"
        @filter-change="onSidebarFilterChange"
        @search="onSearchRefresh"
        @reset-search="onResetSearch"
      >
        <template #search>
          <a-form :model="{}" layout="inline" @keyup.enter="onSearchRefresh">
                <a-form-item
                  v-for="item of headerConditionItems"
                  :key="item.key"
                  :label="item.label"
                >
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
                  @change="onSearchRefresh"
                />
              </template>
              <template
                    v-else-if="
                      item.type === 'select' && item.key === 'project_product__ui_client_type'
                    "
              >
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="fieldNames"
                  :options="enumStore.drive_type"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="onSearchRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'update_user'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="fieldNames"
                  :options="item.optionItems"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="onSearchRefresh"
                />
              </template>
            </a-form-item>
          </a-form>
        </template>
        <template #toolbar>
          <a-space>
            <div>
                  <a-button
                    type="primary"
                    size="small"
                    @click="onAdd"
                    data-testid="qa-views-uitest-page-button-新增"
                    >新增</a-button
                  >
            </div>
            <div>
                  <a-button
                    status="danger"
                    size="small"
                    @click="onDelete(null)"
                    data-testid="qa-views-uitest-page-button-批量删除"
                    >批量删除</a-button
                  >
            </div>
          </a-space>
        </template>
      <a-table
        class="mango-native-scroll-table"
        :bordered="false"
        :row-selection="{ selectedRowKeys, showCheckedAll }"
        :loading="table.tableLoading.value"
        :data="table.dataList"
        :columns="tableColumns"
        :pagination="false"
        :rowKey="rowKey"
        :scroll="{ x: 1310, y: '100%' }"
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
            <template v-else-if="item.key === 'client'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record.project_product.ui_client_type]" size="small"
                >{{ enumStore.drive_type[record.project_product.ui_client_type]?.title || '-' }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'project_product'" #cell="{ record }">
              {{ formatProjectProductPath(record.project_product) }}
            </template>
            <template v-else-if="item.key === 'module'" #cell="{ record }">
              {{ formatModulePath(record.module) }}
            </template>
            <template v-else-if="item.key === 'update_user'" #cell="{ record }">
              {{ record.update_user?.name || record.update_user?.username || '-' }}
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <MangoTableActions
                :actions="[
    { label: '编辑', onClick: () => onUpdate(record) },
    { label: '添加元素', onClick: () => onClick(record) },
    { label: '删除', danger: true, onClick: () => onDelete(record) },
]"
              />
            </template>
          </a-table-column>
        </template>
      </a-table>
    <template #footer>
      <TableFooter :pagination="pagination" />
    </template>
      </ProjectProductNavigationWorkbench>
    </template>
  </TableBody>
  <ModalDialog ref="modalDialogRef" :title="data.actionTitle" @confirm="onDataForm">
    <template #content>
      <a-form :model="formModel">
        <a-form-item
          :class="[item.required ? 'mango-form-item__require' : 'mango-form-item__no_require']"
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
            />
          </template>
        </a-form-item>
      </a-form>
    </template>
  </ModalDialog>
</template>

<script lang="ts" setup>
  import { deleteUiPage, getUiPage, postUiPage, putUiPage } from '@/api/uitest/page'
  import { usePagination, useRowKey, useRowSelection, useTable } from '@/hooks/table'
  import { useLatestRequest } from '@/hooks/use-latest-request'
  import { ModalDialogType } from '@/types/components'
  import { Message, Modal } from '@arco-design/web-vue'
  import { computed, nextTick, onMounted, reactive, ref } from 'vue'
  import { useRouter } from 'vue-router'
  import { getFormItems } from '@/utils/datacleaning'
  import { usePageData } from '@/store/page-data'
  import { conditionItems, formItems, tableColumns } from './config'
  import { useEnum } from '@/store/modules/get-enum'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import { formatProjectProductPath, formatModulePath, getItemValue, setItemValue } from '@/utils/business-format'
  import { fieldNames } from '@/setting'
  import { getUserName } from '@/api/user/user'
  import { setUpdateUserOptions } from '@/utils/update-user'

  const modalDialogRef = ref<ModalDialogType | null>(null)
  const pagination = usePagination(doRefresh, () => table.tableLoading)
  const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection()
  const table = useTable()
  const { beginRequest, isLatestRequest } = useLatestRequest()
  const rowKey = useRowKey('id')
  const sidebarResetKey = ref(0)
  const headerConditionItems = computed(() =>
    conditionItems.filter((item) => item.key !== 'project_product' && item.key !== 'module')
  )
  const formModel = ref({})
  const router = useRouter()
  const enumStore = useEnum()

  const data: any = reactive({
    isAdd: false,
    updateId: 0,
    actionTitle: '新增',
  })

  function onResetSearch() {
    conditionItems.forEach((it) => {
      it.value = it.multiple ? [] : ''
    })
    sidebarResetKey.value += 1
    doRefresh(null, false, true)
  }

  function onAdd() {
    data.actionTitle = '新增'
    data.isAdd = true
    modalDialogRef.value?.toggle()
    formItems.forEach((it) => {
      if (it.reset) {
        it.reset()
      } else {
        it.value = it.multiple ? [] : ''
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
      content: '是否要删除此页面？',
      cancelText: '取消',
      okText: '删除',
      onBeforeOk: () => {
        return deleteUiPage(batch ? selectedRowKeys.value : record.id)
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

  function onDataForm() {
    if (formItems.every((it) => (it.validator ? it.validator() : true))) {
      let value = getFormItems(formItems)
      if (data.isAdd) {
        postUiPage(value)
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
        putUiPage(value)
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

  function getConditionValue(key: string) {
    return getItemValue(conditionItems, key)
  }

  function getFormItemValue(key: string) {
    return getItemValue(formItems, key)
  }

  function onSearchProjectProductChange(value: any) {
    setItemValue(conditionItems, 'module', '')
    doRefresh(value, true, true)
  }

  function onFormProjectProductChange() {
    setItemValue(formItems, 'module', '')
  }

  function onSearchRefresh() {
    doRefresh(null, false, true)
  }

  function onSidebarFilterChange(filter: { projectProduct: any; module: any }) {
    setItemValue(conditionItems, 'project_product', filter.projectProduct)
    setItemValue(conditionItems, 'module', filter.module)
    pagination.page = 1
    selectedRowKeys.value = []
    doRefresh(null, false, true)
  }

  function doRefresh(projectProductId: any = null, bool_ = false, showLoading = false) {
    const requestId = beginRequest()
    if (showLoading) {
      table.tableLoading.value = true
    }
    const value = getFormItems(conditionItems)
    value['page'] = pagination.page
    value['pageSize'] = pagination.pageSize
    clearEmptyFilter(value, 'project_product__ui_client_type')
    clearEmptyFilter(value, 'update_user')
    if (projectProductId && bool_) {
      value['project_product'] = projectProductId
    }
    getUiPage(value)
      .then((res) => {
        if (!isLatestRequest(requestId)) return
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
      })
      .catch((error) => {
        if (isLatestRequest(requestId)) console.log(error)
      })
      .finally(() => {
        if (isLatestRequest(requestId)) {
          table.tableLoading.value = false
        }
      })
  }

  function clearEmptyFilter(value: Record<string, any>, key: string) {
    if (value[key] === null || value[key] === '') {
      delete value[key]
    }
  }

  function onClick(record: any) {
    const pageData = usePageData()
    pageData.setRecord(record)
    router.push({
      path: '/uitest/page/elements',
      query: {
        id: record.id,
      },
    })
  }

  onMounted(() => {
    nextTick(async () => {
      getUserName().then((res) => setUpdateUserOptions(conditionItems, res.data || []))
      doRefresh(null, false, true)
    })
  })
</script>
