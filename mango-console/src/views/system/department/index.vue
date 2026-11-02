<template>
  <TableBody content-flush>
    <template #header>
      <TableHeader title="部门管理" />
    </template>
    <template #default>
      <TableTabs>
        <template #extra>
          <a-button
            size="small"
            type="primary"
            @click="onAdd"
            data-testid="qa-views-system-department-button-新增"
          >
            新增
          </a-button>
        </template>
      </TableTabs>
      <a-table
        :scroll="{ x: tableScrollX }"
        :bordered="false"
        :columns="tableColumns"
        :data="table.dataList"
        :loading="table.tableLoading.value"
        :pagination="false"
        :rowKey="rowKey"
      >
        <template #columns>
          <a-table-column
            v-for="item of tableColumns"
            :key="item.key"
            :align="item.align"
            :data-index="item.key"
            :fixed="item.fixed"
            :title="item.title"
            :width="item.width"
            :ellipsis="item.ellipsis"
            :tooltip="item.tooltip"
          >
            <template v-if="item.key === 'index'" #cell="{ record }">
              {{ record.id }}
            </template>
            <template v-else-if="item.key === 'status'" #cell="{ record }">
              <a-switch
                size="small"
                :default-checked="record.status === 1"
                :before-change="(checked) => onStatusChange(record, checked)"
              />
            </template>
            <template v-else-if="item.key === 'update_user'" #cell="{ record }">
              {{ record.update_user_info?.name || record.update_user_info?.username || '-' }}
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <MangoTableActions
                :actions="[
    { label: '范围', onClick: () => onScope(record) },
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

  <ModalDialog ref="modalDialogRef" :title="pageState.actionTitle" @confirm="onDataForm">
    <template #content>
      <a-form :model="formModel">
        <a-form-item
          v-for="item of formItems"
          :key="item.key"
          :class="[item.required ? 'mango-form-item__require' : 'mango-form-item__no_require']"
          :label="item.label"
        >
          <a-input
            v-if="item.type === 'input'"
            v-model="item.value"
            :placeholder="item.placeholder"
          />
          <a-switch
            v-else-if="item.type === 'switch'"
            v-model="item.value"
            :checked-value="1"
            :unchecked-value="0"
          />
          <a-textarea
            v-else-if="item.type === 'textarea'"
            v-model="item.value"
            :auto-size="{ minRows: 3, maxRows: 5 }"
            :placeholder="item.placeholder"
          />
        </a-form-item>
      </a-form>
    </template>
  </ModalDialog>

  <a-drawer
    v-model:visible="scopeDrawer.visible"
    class="mango-department-scope-drawer"
    :width="620"
    :footer="false"
    unmount-on-close
  >
    <template #title>项目产品范围 - {{ scopeDrawer.departmentName }}</template>
    <div class="mango-department-scope-drawer__body">
      <a-spin :loading="scopeDrawer.loading">
        <a-checkbox-group
          v-model="scopeDrawer.selectedProductIds"
          class="mango-department-scope-list"
        >
          <a-checkbox
            v-for="product in scopeDrawer.products"
            :key="product.id"
            :value="product.id"
            class="mango-department-scope-item"
          >
            <span class="mango-department-scope-item__project">{{
              product.project?.name || '-'
            }}</span>
            <span class="mango-department-scope-item__product">{{ product.name }}</span>
          </a-checkbox>
        </a-checkbox-group>
      </a-spin>
    </div>
    <div class="mango-department-scope-drawer__footer">
      <a-button
        @click="scopeDrawer.visible = false"
        data-testid="qa-views-system-department-button-取消"
        >取消</a-button
      >
      <a-button
        type="primary"
        :loading="scopeDrawer.saving"
        @click="onSaveScope"
        data-testid="qa-views-system-department-button-保存"
        >保存</a-button
      >
    </div>
  </a-drawer>
</template>

<script lang="ts" setup>
  import { Message, Modal } from '@arco-design/web-vue'
  import { nextTick, onMounted, reactive, ref } from 'vue'
  import { usePagination, useRowKey, useTable } from '@/hooks/table'
  import { ModalDialogType } from '@/types/components'
  import { getFormItems } from '@/utils/datacleaning'
  import {
    deleteUserDepartment,
    getUserDepartment,
    getUserDepartmentProductScope,
    postUserDepartment,
    putUserDepartment,
    putUserDepartmentProductScope,
  } from '@/api/user/department'
  import { getUserProduct } from '@/api/system/product'
  import { formItems, tableColumns, tableScrollX } from './config'
  import TableTabs from '@/components/table/TableTabs.vue'

  const modalDialogRef = ref<ModalDialogType | null>(null)
  const pagination = usePagination(doRefresh, () => table.tableLoading)
  const table = useTable()
  const rowKey = useRowKey('id')
  const formModel = ref({})
  const pageState = reactive({
    isAdd: false,
    updateId: 0,
    actionTitle: '新增',
  })
  const scopeDrawer = reactive({
    visible: false,
    loading: false,
    saving: false,
    departmentId: 0,
    departmentName: '',
    products: [] as any[],
    selectedProductIds: [] as number[],
  })

  function doRefresh() {
    table.tableLoading.value = true
    getUserDepartment({ page: pagination.page, pageSize: pagination.pageSize })
      .then((res) => {
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
      })
      .catch(() => {
        table.tableLoading.value = false
      })
  }

  async function onStatusChange(record: any, checked: boolean) {
    try {
      const status = checked ? 1 : 0
      const res = await putUserDepartment({
        id: record.id,
        name: record.name,
        description: record.description,
        status,
      })
      record.status = status
      Message.success(res.msg)
      return true
    } catch {
      return false
    }
  }

  function resetFormItems() {
    formItems.forEach((it) => {
      if (it.reset) {
        it.reset()
      } else if (it.key === 'status') {
        it.value = 1
      } else {
        it.value = ''
      }
    })
  }

  function onAdd() {
    pageState.actionTitle = '新增'
    pageState.isAdd = true
    resetFormItems()
    modalDialogRef.value?.toggle()
  }

  function onUpdate(record: any) {
    pageState.actionTitle = '编辑'
    pageState.isAdd = false
    pageState.updateId = record.id
    modalDialogRef.value?.toggle()
    nextTick(() => {
      formItems.forEach((it) => {
        it.value = record[it.key] ?? ''
      })
    })
  }

  function onDelete(record: any) {
    Modal.confirm({
      title: '提示',
      content: '是否要删除此部门？',
      cancelText: '取消',
      okText: '删除',
      onBeforeOk: () => {
        return deleteUserDepartment(record.id)
          .then((res) => {
            Message.success(res.msg)
            return true
          })
          .catch(() => false)
          .finally(doRefresh)
      },
    })
  }

  function onDataForm() {
    if (!formItems.every((it) => (it.validator ? it.validator() : true))) {
      modalDialogRef.value?.setConfirmLoading(false)
      return
    }
    const value = getFormItems(formItems)
    const request = pageState.isAdd
      ? postUserDepartment(value)
      : putUserDepartment({ ...value, id: pageState.updateId })
    request
      .then((res) => {
        modalDialogRef.value?.toggle()
        Message.success(res.msg)
        doRefresh()
      })
      .catch(console.log)
      .finally(() => {
        modalDialogRef.value?.setConfirmLoading(false)
      })
  }

  function onScope(record: any) {
    scopeDrawer.visible = true
    scopeDrawer.loading = true
    scopeDrawer.departmentId = record.id
    scopeDrawer.departmentName = record.name
    Promise.all([getUserProduct({}), getUserDepartmentProductScope(record.id)])
      .then(([productRes, scopeRes]) => {
        scopeDrawer.products = productRes.data || []
        scopeDrawer.selectedProductIds = (scopeRes.data || []).map(
          (item: any) => item.project_product?.id
        )
      })
      .catch(console.log)
      .finally(() => {
        scopeDrawer.loading = false
      })
  }

  function onSaveScope() {
    scopeDrawer.saving = true
    putUserDepartmentProductScope({
      department_id: scopeDrawer.departmentId,
      project_product_ids: scopeDrawer.selectedProductIds,
    })
      .then((res) => {
        Message.success(res.msg)
        scopeDrawer.visible = false
      })
      .catch(console.log)
      .finally(() => {
        scopeDrawer.saving = false
      })
  }

  onMounted(() => {
    doRefresh()
  })
</script>

<style scoped>
  .mango-department-scope-drawer__body {
    height: calc(100vh - 112px);
    overflow: auto;
    padding-right: 4px;
  }

  .mango-department-scope-list {
    display: grid;
    grid-template-columns: 1fr;
    gap: 8px;
  }

  .mango-department-scope-item {
    display: flex;
    width: 100%;
    min-height: 36px;
    align-items: center;
    padding: 6px 8px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-bg-container);
  }

  .mango-department-scope-item__project {
    color: var(--m-muted);
    margin-right: 8px;
  }

  .mango-department-scope-item__product {
    font-weight: 500;
  }

  .mango-department-scope-drawer__footer {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    padding-top: 12px;
    border-top: 1px solid var(--m-border);
  }
</style>
