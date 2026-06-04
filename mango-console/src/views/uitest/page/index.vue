<template>
  <TableBody ref="tableBody">
    <template #header>
      <TableHeader
        :show-filter="true"
        title="Ui元素页面对象"
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
                  @change="onSearchRefresh"
                />
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
              <a-button type="primary" size="small" @click="onAdd">新增</a-button>
            </div>
            <div>
              <a-button status="danger" size="small" @click="onDelete(null)">批量删除</a-button>
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
        :scroll="{ x: 1160 }"
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
              {{ formatProjectProductPath(record?.project_product) }}
            </template>
            <template v-else-if="item.key === 'module'" #cell="{ record }">
              {{ formatModulePath(record?.module) }}
            </template>
            <template v-else-if="item.key === 'client'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record.project_product.ui_client_type]" size="small"
                >{{ enumStore.drive_type[record.project_product.ui_client_type]?.title || '-' }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <MangoTableActions
                :actions="[
                  { label: '编辑', onClick: () => onUpdate(record) },
                  { label: '添加元素', onClick: () => onClick(record) },
                  { label: '复制', onClick: () => onPageCopy(record.id) },
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
  import { deleteUiPage, getUiPage, postUiPage, postUiPageCopy, putUiPage } from '@/api/uitest/page'
  import { usePagination, useRowKey, useRowSelection, useTable } from '@/hooks/table'
  import { ModalDialogType } from '@/types/components'
  import { Message, Modal } from '@arco-design/web-vue'
  import { nextTick, onMounted, reactive, ref } from 'vue'
  import { useRouter } from 'vue-router'
  import { getFormItems } from '@/utils/datacleaning'
  import { usePageData } from '@/store/page-data'
  import { conditionItems, formItems, tableColumns } from './config'
  import { useEnum } from '@/store/modules/get-enum'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import {
    formatModulePath,
    formatProjectProductPath,
    getItemValue,
    setItemValue,
  } from '@/utils/business-format'

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
    actionTitle: '新增',
  })

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
    formItems.forEach((it) => {
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

  function doRefresh(projectProductId: any = null, bool_ = false, showLoading = false) {
    if (showLoading) {
      table.tableLoading.value = true
    }
    const value = getFormItems(conditionItems)
    value['page'] = pagination.page
    value['pageSize'] = pagination.pageSize
    if (projectProductId && bool_) {
      value['project_product'] = projectProductId
    }
    getUiPage(value)
      .then((res) => {
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
      })
      .catch(console.log)
      .finally(() => {
        if (showLoading) {
          table.tableLoading.value = false
        }
      })
  }

  function onPageCopy(id: number) {
    postUiPageCopy(id)
      .then((res) => {
        Message.success(res.msg)
        doRefresh()
      })
      .catch(console.log)
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
      doRefresh()
    })
  })
</script>
