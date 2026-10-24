<template>
  <TableBody ref="tableBody" plain class="mango-api-resource-page mango-detail-workbench-page">
    <template #header>
      <TableHeader title="请求头管理" />
    </template>

    <template #default>
      <ProjectProductNavigationWorkbench
          contained-body
          :model-value="projectProductCondition?.value"
          :reset-key="sidebarResetKey"
          @filter-change="onSidebarFilterChange"
          @search="onSearchRefresh"
          @reset-search="onResetSearch"
        >
          <template #search>
              <ApiResourceSearchFilters
                :items="headerConditionItems"
                :field-names="fieldNames"
                :enum-store="enumStore"
                :user-list="data.userList"
                @search="onSearchRefresh"
                @reset="onResetSearch"
              />
          </template>
          <template #toolbar>
          <a-space>
            <div>
              <a-button v-permission="'api.headers:create'" size="small" type="primary" @click="onAdd" data-testid="qa-views-apitest-headers-button-新增">新增</a-button>
            </div>
            <div>
              <a-button v-permission="'api.headers:delete'" size="small" status="danger" @click="onDelete(null)" data-testid="qa-views-apitest-headers-button-批量删除">批量删除</a-button>
            </div>
          </a-space>
          </template>
      <a-table
        class="mango-native-scroll-table"
        :scroll="{ x: 1480, y: '100%' }"
        :bordered="false"
        :columns="tableColumns"
        :data="batchSelectableDataList"
        :loading="table.tableLoading.value"
        :pagination="false"
        :row-selection="{ selectedRowKeys, showCheckedAll, onlyCurrent: true }"
        :rowKey="rowKey"
        @selection-change="onHeaderSelectionChange"
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
            <template v-else-if="item.key === 'client'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record.project_product.api_client_type]" size="small"
                >{{ enumStore.api_client[record.project_product.api_client_type]?.title }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'status'" #cell="{ record }">
              <a-switch v-permission="'api.headers:status'"
                :beforeChange="(newValue) => onModifyStatus(newValue, record.id)"
                :default-checked="record.status === 1"
              />
            </template>
            <template v-else-if="item.key === 'project_product'" #cell="{ record }">
              {{ formatProjectProductPath(record.project_product) }}
            </template>
            <template v-else-if="item.key === 'update_user'" #cell="{ record }">
              {{ record.update_user?.name || '-' }}
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <MangoTableActions
                :actions="[
                  { permission: 'api.headers:edit', label: '编辑', onClick: () => onUpdate(record) },
                  { permission: 'api.headers:delete', label: '删除', danger: true, onClick: () => onDelete(record) },
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
          v-for="item of formItems"
          :key="item.key"
          :class="[item.required ? 'mango-form-item__require' : 'mango-form-item__no_require']"
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
            <ProjectProductSelect
              v-model="item.value"
              :placeholder="item.placeholder"
            />
          </template>
        </a-form-item>
      </a-form>
    </template>
  </ModalDialog>
</template>

<script lang="ts" setup>
  import { formatProjectProductPath } from '@/utils/business-format'
  import { usePagination, useRowKey, useTable } from '@/hooks/table'
  import { useProjectLockedRowSelection } from '@/hooks/use-project-locked-row-selection'
  import { useLatestRequest } from '@/hooks/use-latest-request'
  import { ModalDialogType } from '@/types/components'
  import { Message, Modal } from '@arco-design/web-vue'
  import { computed, onMounted, ref, nextTick, reactive } from 'vue'
  import { getFormItems } from '@/utils/datacleaning'
  import { fieldNames } from '@/setting'
  import { tableColumns, formItems, conditionItems } from './config'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import ApiResourceSearchFilters from '@/components/business/ApiResourceSearchFilters.vue'
  import {
    deleteApiHeaders,
    getApiHeaders,
    postApiHeaders,
    putApiHeaders,
  } from '@/api/apitest/headers'
  import { useEnum } from '@/store/modules/get-enum'
  import { getUserName } from '@/api/user/user'

  const enumStore = useEnum()
  const headerConditionItems = computed(() => conditionItems.filter((item) => item.key !== 'project_product'))
  const projectProductCondition = computed(() => conditionItems.find((item) => item.key === 'project_product'))
  const sidebarResetKey = ref(0)

  function onSidebarFilterChange({ projectProduct }: { projectProduct: string | number | null }) {
    if (projectProductCondition.value) projectProductCondition.value.value = projectProduct
    selectedRowKeys.value = []
    pagination.page = 1
    doRefresh(true)
  }

  const modalDialogRef = ref<ModalDialogType | null>(null)
  const pagination = usePagination(doRefresh, () => table.tableLoading)
  const table = useTable()
  const {
    selectedRowKeys,
    showCheckedAll,
    selectableDataList: batchSelectableDataList,
    onSelectionChange: onHeaderSelectionChange,
    validateSingleProject: validateSingleProduct,
  } = useProjectLockedRowSelection<any>(
    () => table.dataList,
    (row) => row?.project_product,
    { scopeLabel: '项目/产品', actionLabel: '删除', itemLabel: '请求头' }
  )
  const { beginRequest, isLatestRequest } = useLatestRequest()
  const rowKey = useRowKey('id')
  const formModel = ref({})
  const data = reactive({
    actionTitle: '新增',
    isAdd: false,
    updateId: 0,
    moduleList: [],
    userList: [],
  })

  function onSearchRefresh() {
    doRefresh(true)
  }

  function doRefresh(showLoading = false) {
    const requestId = beginRequest()
    if (showLoading) {
      table.tableLoading.value = true
    }
    let value = getFormItems(conditionItems)
    if (
      value['project_product__api_client_type'] === null ||
      value['project_product__api_client_type'] === ''
    ) {
      delete value['project_product__api_client_type']
    }
    if (value.update_user === null || value.update_user === '') {
      delete value.update_user
    }
    value['page'] = pagination.page
    value['pageSize'] = pagination.pageSize
    getApiHeaders(value)
      .then((res) => {
        if (!isLatestRequest(requestId)) return
        table.handleSuccess(res)
        const currentRowKeys = new Set((res.data || []).map((item: any) => String(item.id)))
        selectedRowKeys.value = selectedRowKeys.value.filter((key) =>
          currentRowKeys.has(String(key))
        )
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

  function onResetSearch() {
    conditionItems.forEach((it) => {
      it.value = it.multiple ? [] : ''
    })
    sidebarResetKey.value += 1
    doRefresh(true)
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
      if (!validateSingleProduct('所选请求头')) return
    }
    Modal.confirm({
      title: '提示',
      content: '是否要删除此参数？',
      cancelText: '取消',
      okText: '删除',
      onBeforeOk: () => {
        return deleteApiHeaders(batch ? selectedRowKeys.value : record.id)
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

  function onDataForm() {
    if (formItems.every((it) => (it.validator ? it.validator() : true))) {
      let value = getFormItems(formItems)
      if (data.isAdd) {
        postApiHeaders(value)
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
        putApiHeaders(value)
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

  const onModifyStatus = async (newValue: boolean, id: number) => {
    return new Promise<any>((resolve, reject) => {
      setTimeout(async () => {
        try {
          let value: any = false
          await putApiHeaders({ id: id, status: newValue ? 1 : 0 })
            .then((res) => {
              Message.success(res.msg)
              value = res.code === 200
            })
            .catch(reject)
          resolve(value)
        } catch (error) {
          reject(error)
        }
      }, 300)
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
    if (projectProductCondition.value) projectProductCondition.value.value = ''
    nextTick(async () => {
      doRefresh()
      getNickName()
    })
  })
</script>
