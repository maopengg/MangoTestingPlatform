<template>
  <TableBody plain class="mango-detail-workbench-page">
    <template #header><TableHeader title="项目与产品" /></template>
    <template #default>
      <ProductOverview
        :products="table.dataList"
        :projects="productProjectOptions"
        :conditions="conditionItems"
        :loading="table.tableLoading.value"
        :error="loadError"
        @search="onSearch"
        @reset-search="onResetSearch"
        @refresh="doRefresh"
        @add="onAdd"
        @module="onModule"
        @datasource="onDatasource"
        @edit="onUpdate"
        @delete="onDelete"
      >
        <template #search>
          <a-form :model="{}" layout="inline" @keyup.enter="onSearch">
            <a-form-item v-for="item of conditionItems" :key="item.key" :label="item.label">
              <template v-if="item.type === 'input'">
                <a-input v-model="item.value" :placeholder="item.placeholder" @blur="onSearch" />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'ui_client_type'">
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
                  @change="onSearch"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'api_client_type'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="fieldNames"
                  :options="enumStore.api_client"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="onSearch"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'owners'">
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
                  @change="onSearch"
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
                  @change="onSearch"
                />
              </template>
            </a-form-item>
          </a-form>
        </template>
      </ProductOverview>
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
          <template v-else-if="item.type === 'select' && item.key === 'project'">
            <a-select
              v-model="item.value"
              :multiple="item.multiple"
              :max-tag-count="item.multiple ? 1 : undefined"
              :field-names="fieldNames"
              :options="productProjectOptions"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              value-key="key"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'ui_client_type'">
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
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'api_client_type'">
            <a-select
              v-model="item.value"
              :multiple="item.multiple"
              :max-tag-count="item.multiple ? 1 : undefined"
              :field-names="fieldNames"
              :options="enumStore.api_client"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              value-key="key"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'owners'">
            <a-select
              v-model="item.value"
              :multiple="item.multiple"
              :max-tag-count="1"
              :field-names="fieldNames"
              :options="item.optionItems"
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
  import { useTable } from '@/hooks/table'
  import { ModalDialogType } from '@/types/components'
  import { Message, Modal } from '@arco-design/web-vue'
  import { nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
  import { getFormItems } from '@/utils/datacleaning'
  import { useRouter } from 'vue-router'
  import { useProject } from '@/store/modules/get-project'
  import { fieldNames } from '@/setting'
  import { conditionItems, formItems } from './config'
  import ProductOverview from './components/ProductOverview.vue'
  import { loadAllProducts } from './overview'
  import {
    deleteUserProduct,
    getProductProjectOptions,
    getUserProduct,
    postUserProduct,
    putUserProduct,
  } from '@/api/system/product'
  import { useEnum } from '@/store/modules/get-enum'
  import { getUserName } from '@/api/user/user'
  import { setUpdateUserOptions } from '@/utils/update-user'

  const enumStore = useEnum()

  const modalDialogRef = ref<ModalDialogType | null>(null)
  const table = useTable()
  const loadError = ref('')
  let requestVersion = 0
  const formModel = ref({})
  const router = useRouter()
  const project = useProject()
  const productProjectOptions = ref<any[]>([])

  const data = reactive({
    isAdd: false,
    updateId: 0,
    actionTitle: '新增',
  })

  function onResetSearch() {
    conditionItems.forEach((it) => {
      it.value = it.multiple ? [] : ''
    })
    onSearch()
  }

  function onSearch() {
    conditionItems.forEach((item) => {
      if (typeof item.value === 'string') item.value = item.value.trim()
    })
  }

  async function doRefresh() {
    const version = ++requestVersion
    table.tableLoading.value = true
    loadError.value = ''
    try {
      const products = await loadAllProducts(getUserProduct, () => version === requestVersion)
      if (version === requestVersion) table.dataList.splice(0, table.dataList.length, ...products)
    } catch {
      if (version === requestVersion) {
        table.dataList.splice(0)
        loadError.value = '产品未能完整加载，请重试。'
      }
    } finally {
      if (version === requestVersion) table.tableLoading.value = false
    }
  }

  function refreshProductProjectOptions() {
    return getProductProjectOptions()
      .then((res) => {
        productProjectOptions.value = Array.isArray(res.data) ? res.data : []
      })
      .catch(console.log)
  }

  function refreshUserOptions() {
    return getUserName()
      .then((res) => {
        const users = res.data || []
        setUpdateUserOptions(conditionItems, users)
        const ownerCondition = conditionItems.find((item) => item.key === 'owners')
        const ownerFormItem = formItems.find((item) => item.key === 'owners')
        if (ownerCondition) ownerCondition.optionItems = users
        if (ownerFormItem) ownerFormItem.optionItems = users
      })
      .catch(console.log)
  }

  function onAdd(projectId?: string) {
    data.actionTitle = '新增'
    data.isAdd = true
    refreshProductProjectOptions()
    modalDialogRef.value?.toggle()
    formItems.forEach((it) => {
      if (it.reset) {
        it.reset()
      } else {
        it.value = it.multiple ? [] : ''
      }
    })
    if (projectId != null) {
      const projectField = formItems.find((item) => item.key === 'project')
      if (projectField)
        projectField.value = productProjectOptions.value.find(
          (item) => String(item.key) === projectId
        )?.key
    }
  }

  function onDelete(record: any) {
    Modal.confirm({
      title: '提示',
      content: '是否要删除此产品？',
      cancelText: '取消',
      okText: '删除',
      onBeforeOk: () => {
        return deleteUserProduct(record.id)
          .then((res) => {
            Message.success(res.msg)
            project.invalidateAllProductModuleTreeCache()
          })
          .catch(console.log)
          .finally(() => {
            doRefresh()
            project.projectProductName()
          })
      },
    })
  }

  function onUpdate(item: any) {
    data.actionTitle = '编辑'
    data.isAdd = false
    data.updateId = item.id
    refreshProductProjectOptions()
    modalDialogRef.value?.toggle()
    nextTick(() => {
      formItems.forEach((it) => {
        const propName = item[it.key]
        if (Array.isArray(propName)) {
          it.value = propName.map((value) => value.id)
        } else if (typeof propName === 'object' && propName !== null) {
          it.value = propName.id
        } else {
          it.value = propName
        }
      })
    })
  }

  function onModule(record: any) {
    router.push({
      path: '/config/product/module',
      query: {
        id: record.id,
        name: record.name,
      },
    })
  }

  function onDatasource(record: any) {
    router.push({
      path: '/config/product/datasource',
      query: {
        id: record.id,
        name: record.name,
      },
    })
  }

  function onDataForm() {
    if (formItems.every((it) => (it.validator ? it.validator() : true))) {
      let value = getFormItems(formItems)
      if (data.isAdd) {
        value['status'] = 1
        postUserProduct(value)
          .then((res) => {
            modalDialogRef.value?.toggle()
            Message.success(res.msg)
            doRefresh()
            project.projectProductName()
            project.invalidateAllProductModuleTreeCache()
          })
          .catch((error) => {
            console.log(error)
          })
          .finally(() => {
            modalDialogRef.value?.setConfirmLoading(false)
          })
      } else {
        value['id'] = data.updateId
        putUserProduct(value)
          .then((res) => {
            modalDialogRef.value?.toggle()
            Message.success(res.msg)
            doRefresh()
            project.projectProductName()
            project.invalidateAllProductModuleTreeCache()
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

  onMounted(() => {
    nextTick(async () => {
      refreshUserOptions()
      refreshProductProjectOptions()
      doRefresh()
    })
  })
  onBeforeUnmount(() => {
    requestVersion += 1
  })
</script>

<style></style>
