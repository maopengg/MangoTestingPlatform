<template>
  <TableBody plain class="mango-detail-workbench-page">
    <template #header><TableHeader title="产品配置" /></template>
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
                  :options="userOptions"
                  :loading="optionLoading.users"
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
                  :options="userOptions"
                  :loading="optionLoading.users"
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
  <ProductEditor
    ref="editorRef"
    :projects="productProjectOptions"
    :users="userOptions"
    :options-loading="optionLoading.projects"
    :users-loading="optionLoading.users"
    @saved="onSaved"
  />
</template>
<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { onMounted, reactive, ref } from 'vue'
  import { useRouter } from 'vue-router'
  import { Modal, Message } from '@arco-design/web-vue'
  import { useProject } from '@/store/modules/get-project'
  import { useEnum } from '@/store/modules/get-enum'
  import { fieldNames } from '@/setting'
  import { getUserProduct, getProductProjectOptions, deleteUserProduct } from '@/api/system/product'
  import { getUserName } from '@/api/user/user'
  import { createConditionItems } from './config'
  import ProductOverview from './components/ProductOverview.vue'
  import ProductEditor from './components/ProductEditor.vue'
  import { loadAllProducts } from './overview'
  import { useProductPageScope } from './composables/useProductPageScope'
  import type { ProductRecord, ProductOption, ProductEditorHandle, ProductId } from './types'
  const enumStore = useEnum(),
    router = useRouter(),
    project = useProject(),
    conditionItems = createConditionItems()
  const table = { dataList: reactive<ProductRecord[]>([]), tableLoading: ref(false) }
  const loadError = ref(''),
    productProjectOptions = ref<ProductOption[]>([]),
    userOptions = ref<ProductOption[]>([])
  const editorRef = ref<ProductEditorHandle | null>(null)
  const optionLoading = reactive({ projects: false, users: false })
  let requestVersion = 0,
    optionVersion = 0,
    userVersion = 0
  let confirmation: ReturnType<typeof Modal.confirm> | null = null
  const deleting = new Set<ProductId>()
  const scope = useProductPageScope(() => [], reset, resume)
  function reset() {
    ++requestVersion
    ++optionVersion
    ++userVersion
    table.dataList.splice(0)
    table.tableLoading.value = false
    productProjectOptions.value = []
    userOptions.value = []
    loadError.value = ''
    optionLoading.projects = false
    optionLoading.users = false
    editorRef.value?.close()
    confirmation?.close()
    confirmation = null
  }
  function resume() {
    void doRefresh()
    void refreshProductProjectOptions()
    void refreshUserOptions()
  }
  function onResetSearch() {
    conditionItems.forEach((item) => {
      item.value = item.multiple ? [] : ''
    })
    onSearch()
  }
  function onSearch() {
    conditionItems.forEach((item) => {
      if (typeof item.value === 'string') item.value = item.value.trim()
    })
  }
  async function doRefresh() {
    if (!scope.isActive()) return
    const current = ++requestVersion,
      version = scope.snapshot()
    table.tableLoading.value = true
    loadError.value = ''
    try {
      const products = await loadAllProducts(
        getUserProduct,
        () => current === requestVersion && scope.current(version)
      )
      if (current === requestVersion && scope.current(version))
        table.dataList.splice(0, table.dataList.length, ...products)
    } catch (loadFailure0) {
      if (current === requestVersion && scope.current(version)) {
        table.dataList.splice(0)
        void (reportLoadError(loadFailure0, "加载失败，请重试", false), loadError.value = '产品未能完整加载，请重试。')
      }
    } finally {
      if (current === requestVersion) table.tableLoading.value = false
    }
  }
  async function refreshProductProjectOptions() {
    if (!scope.isActive()) return
    optionLoading.projects = true
    const current = ++optionVersion,
      version = scope.snapshot()
    try {
      const res = await getProductProjectOptions()
      if (current === optionVersion && scope.current(version))
        productProjectOptions.value = res.data || []
    } catch {
    } finally {
      if (current === optionVersion) optionLoading.projects = false
    }
  }
  async function refreshUserOptions() {
    if (!scope.isActive()) return
    optionLoading.users = true
    const current = ++userVersion,
      version = scope.snapshot()
    try {
      const res = await getUserName()
      if (current === userVersion && scope.current(version)) userOptions.value = res.data || []
    } catch {
    } finally {
      if (current === userVersion) optionLoading.users = false
    }
  }
  function onAdd(projectId?: string) {
    editorRef.value?.open(undefined, projectId)
    void refreshProductProjectOptions()
    void refreshUserOptions()
  }
  function onUpdate(record: ProductRecord) {
    if (!deleting.has(record.id)) {
      editorRef.value?.open(record)
      void refreshProductProjectOptions()
      void refreshUserOptions()
    }
  }
  async function refreshNavigation() {
    try {
      await project.projectProductName()
    } catch {}
  }
  function onSaved() {
    void doRefresh()
    void refreshNavigation()
  }
  function onDelete(record: ProductRecord) {
    if (!scope.isActive() || confirmation || deleting.has(record.id)) return
    const id = record.id,
      version = scope.snapshot()
    const dialog = Modal.confirm({
      title: '提示',
      content: '是否要删除此产品？',
      cancelText: '取消',
      okText: '删除',
      okButtonProps: { status: 'danger' },
      async onBeforeOk() {
        if (!scope.current(version) || deleting.has(id)) return false
        deleting.add(id)
        try {
          const res = await deleteUserProduct(id)
          project.invalidateProjectOptionsCache()
          if (scope.current(version)) {
            Message.success(res.msg)
            await doRefresh()
            await refreshNavigation()
          }
          return true
        } catch {
          return false
        } finally {
          deleting.delete(id)
        }
      },
      onClose() {
        if (confirmation === dialog) confirmation = null
      },
    })
    confirmation = dialog
  }
  function onModule(record: ProductRecord) {
    void router.push({
      path: '/config/product/module',
      query: { id: record.id, name: record.name },
    })
  }
  function onDatasource(record: ProductRecord) {
    void router.push({
      path: '/config/product/datasource',
      query: { id: record.id, name: record.name },
    })
  }
  onMounted(resume)
</script>
