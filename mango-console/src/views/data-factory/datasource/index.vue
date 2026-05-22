<template>
  <TableBody>
    <template #header>
      <TableHeader title="数据工厂 / 数据源映射" @search="doRefresh" @reset-search="onResetSearch">
        <template #search-content>
          <a-form :model="{}" layout="inline" @keyup.enter="doRefresh">
            <a-form-item
              v-for="item of datasourceAliasConditionItems"
              :key="item.key"
              :label="item.label"
            >
              <template v-if="item.type === 'input'">
                <a-input v-model="item.value" :placeholder="item.placeholder" @blur="doRefresh" />
              </template>
              <template v-else-if="item.type === 'cascader' && item.key === 'project_product'">
                <a-cascader
                  v-model="item.value"
                  :options="projectInfo.projectProduct"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="doRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'db_type'">
                <a-select
                  v-model="item.value"
                  :field-names="enumFieldNames"
                  :options="enumStore.database_type"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="doRefresh"
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
          <div>
            <a-space>
              <a-button size="small" type="primary" @click="openAlias()">新增逻辑源</a-button>
            </a-space></div
          >
        </template>
      </a-tabs>
      <a-table
        :scroll="{ x: 1100 }"
        :columns="datasourceAliasColumns"
        :data="aliasTable.dataList"
        :loading="aliasTable.tableLoading.value"
        :pagination="false"
        :row-key="'id'"
      >
        <template #columns>
          <a-table-column
            v-for="item of datasourceAliasColumns"
            :key="item.key"
            :align="item.align"
            :data-index="item.key"
            :fixed="item.fixed"
            :ellipsis="item.ellipsis"
            :tooltip="item.tooltip"
            :title="item.title"
            :width="item.width"
          >
            <template v-if="item.key === 'index'" #cell="{ record }">
              {{ record.id }}
            </template>
            <template v-else-if="item.key === 'project_product'" #cell="{ record }">
              {{ record?.project_product?.project?.name + '/' + record?.project_product?.name }}
            </template>
            <template v-else-if="item.key === 'db_type'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record.db_type]" size="small">
                {{ enumTitle(enumStore.database_type, record.db_type) }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <MangoTableActions
                :actions="[
                  { label: '编辑', onClick: () => openAlias(record) },
                  {
                    label: '环境绑定',
                    loading: actionLoading === `binding-${record.id}`,
                    onClick: () => openBinding(record),
                  },
                  {
                    label: '删除',
                    danger: true,
                    loading: actionLoading === `alias-delete-${record.id}`,
                    onClick: () => removeAlias(record),
                  },
                ]"
              />
            </template>
          </a-table-column>
        </template>
      </a-table>
    </template>
    <template #footer><TableFooter :pagination="pagination" /></template>
  </TableBody>

  <a-modal
    v-model:visible="aliasVisible"
    :on-before-ok="saveAlias"
    :ok-loading="aliasSaving"
    :title="aliasForm.id ? '编辑逻辑数据源' : '新增逻辑数据源'"
    width="680px"
  >
    <a-form :model="aliasForm" layout="vertical">
      <a-form-item label="产品" required>
        <a-cascader
          v-model="aliasForm.project_product"
          :options="projectInfo.projectProduct"
          allow-search
          allow-clear
        />
      </a-form-item>
      <a-form-item label="名称" required><a-input v-model="aliasForm.name" /></a-form-item>
      <a-form-item label="编码" required><a-input v-model="aliasForm.code" /></a-form-item>
      <a-form-item label="数据库类型" required>
        <a-select
          v-model="aliasForm.db_type"
          :options="enumStore.database_type"
          :field-names="enumFieldNames"
        />
      </a-form-item>
      <a-form-item label="描述"><a-textarea v-model="aliasForm.description" /></a-form-item>
    </a-form>
  </a-modal>

  <a-drawer
    v-model:visible="bindingVisible"
    :title="`${currentAlias?.name || ''} / 环境绑定`"
    width="900px"
  >
    <a-space class="datasource-toolbar">
      <a-button type="primary" @click="openBindingForm()">新增绑定</a-button>
      <a-button :loading="bindingLoading" @click="loadBindings">刷新</a-button>
    </a-space>
    <a-table
      :scroll="{ x: 1100 }"
      :columns="datasourceBindingColumns"
      :data="bindingRows"
      :loading="bindingLoading"
      :pagination="false"
      :row-key="'id'"
    >
      <template #columns>
        <a-table-column
          v-for="item of datasourceBindingColumns"
          :key="item.key"
          :align="item.align"
          :data-index="item.key"
          :ellipsis="item.ellipsis"
          :tooltip="item.tooltip"
          :title="item.title"
          :width="item.width"
        >
          <template v-if="item.key === 'index'" #cell="{ record }">
            {{ record.id }}
          </template>
          <template v-else-if="item.key === 'test_object'" #cell="{ record }">
            <a-tag :color="enumStore.colors[record.cleanup_strategy]" size="small">
              {{ displayName(record.test_object) }}
            </a-tag>
          </template>
          <template v-else-if="item.key === 'database'" #cell="{ record }">
            {{ displayDatabase(record.database) }}
          </template>
          <template v-else-if="item.key === 'actions'" #cell="{ record }">
            <MangoTableActions
              :actions="[
                { label: '编辑', onClick: () => openBindingForm(record) },
                {
                  label: '删除',
                  danger: true,
                  loading: actionLoading === `binding-delete-${record.id}`,
                  onClick: () => removeBinding(record),
                },
              ]"
            />
          </template>
        </a-table-column>
      </template>
    </a-table>
  </a-drawer>

  <a-modal
    v-model:visible="bindingFormVisible"
    :on-before-ok="saveBinding"
    :ok-loading="bindingSaving"
    :title="bindingForm.id ? '编辑绑定' : '新增绑定'"
    width="680px"
  >
    <a-form :model="bindingForm" layout="vertical">
      <a-form-item label="测试环境" required>
        <a-select
          v-model="bindingForm.test_object"
          :options="testObjectOptions"
          :field-names="{ value: 'id', label: 'name' }"
          allow-search
        />
      </a-form-item>
      <a-form-item label="实际数据库" required>
        <a-select
          v-model="bindingForm.database"
          :options="databaseOptions"
          :field-names="{ value: 'id', label: 'name' }"
          allow-search
        />
      </a-form-item>
      <a-form-item label="描述"><a-textarea v-model="bindingForm.description" /></a-form-item>
    </a-form>
  </a-modal>
</template>

<script lang="ts" setup>
  import {
    deleteDataFactoryDatasourceAlias,
    deleteDataFactoryDatasourceBinding,
    getDataFactoryDatasourceAlias,
    getDataFactoryDatasourceBinding,
    postDataFactoryDatasourceAlias,
    postDataFactoryDatasourceBinding,
    putDataFactoryDatasourceAlias,
    putDataFactoryDatasourceBinding,
  } from '@/api/data-factory'
  import { getSystemDatabase } from '@/api/system/database'
  import { getUserTestObject } from '@/api/system/test_object'
  import { usePagination, useTable } from '@/hooks/table'
  import { useEnum } from '@/store/modules/get-enum'
  import { useProject } from '@/store/modules/get-project'
  import { getFormItems } from '@/utils/datacleaning'
  import { Message, Modal } from '@arco-design/web-vue'
  import { onMounted, reactive, ref } from 'vue'
  import {
    datasourceAliasColumns,
    datasourceAliasConditionItems,
    datasourceBindingColumns,
  } from './config'

  const aliasTable = useTable()
  const pagination = usePagination(doRefresh)
  const enumStore = useEnum()
  const projectInfo = useProject()
  const enumFieldNames = { value: 'key', label: 'title' }
  const aliasVisible = ref(false)
  const bindingVisible = ref(false)
  const bindingFormVisible = ref(false)
  const aliasSaving = ref(false)
  const bindingSaving = ref(false)
  const bindingLoading = ref(false)
  const actionLoading = ref('')
  const currentAlias = ref<any>(null)
  const bindingRows = ref<any[]>([])
  const testObjectOptions = ref<any[]>([])
  const databaseOptions = ref<any[]>([])
  const aliasForm = reactive<any>({})
  const bindingForm = reactive<any>({})

  function enumTitle(options: any[] = [], value: any) {
    return options.find((it) => it.key === value)?.title || value
  }

  function displayName(value: any) {
    return value?.name || value?.title || value
  }

  function displayDatabase(value: any) {
    return value?.name ? `${value.name}(${value.host}:${value.port})` : value
  }

  function doRefresh() {
    aliasTable.tableLoading.value = true
    const query = getFormItems(datasourceAliasConditionItems)
    getDataFactoryDatasourceAlias({
      ...query,
      page: pagination.page,
      pageSize: pagination.pageSize,
    }).then((res) => {
      aliasTable.handleSuccess(res)
      pagination.setTotalSize((res as any).totalSize)
    })
  }

  function onResetSearch() {
    datasourceAliasConditionItems.forEach((it) => {
      it.value = ''
    })
    doRefresh()
  }

  function loadOptions() {
    getUserTestObject({}).then((res) => (testObjectOptions.value = res.data || []))
    getSystemDatabase({}).then((res) => (databaseOptions.value = res.data || []))
  }

  function openAlias(record?: any) {
    Object.keys(aliasForm).forEach((key) => delete aliasForm[key])
    Object.assign(aliasForm, {
      id: record?.id,
      project_product: record?.project_product?.id || record?.project_product || null,
      name: record?.name || '',
      code: record?.code || '',
      db_type: record?.db_type ?? 0,
      description: record?.description || '',
      status: record?.status ?? 1,
    })
    aliasVisible.value = true
  }

  async function saveAlias() {
    const request = aliasForm.id ? putDataFactoryDatasourceAlias : postDataFactoryDatasourceAlias
    aliasSaving.value = true
    try {
      const res = await request({ ...aliasForm })
      Message.success(res.msg)
      doRefresh()
      return true
    } catch (error) {
      return false
    } finally {
      aliasSaving.value = false
    }
  }

  function removeAlias(record: any) {
    Modal.confirm({
      title: '删除逻辑源',
      content: `确认删除 ${record.name}？`,
      onBeforeOk: () => {
        actionLoading.value = `alias-delete-${record.id}`
        return deleteDataFactoryDatasourceAlias(record.id)
          .then(doRefresh)
          .finally(() => {
            actionLoading.value = ''
          })
      },
    })
  }

  function openBinding(alias: any) {
    currentAlias.value = alias
    bindingVisible.value = true
    actionLoading.value = `binding-${alias.id}`
    loadBindings().finally(() => {
      actionLoading.value = ''
    })
  }

  function loadBindings() {
    bindingLoading.value = true
    return getDataFactoryDatasourceBinding({ datasource_alias: currentAlias.value.id })
      .then((res) => {
        bindingRows.value = res.data || []
      })
      .finally(() => {
        bindingLoading.value = false
      })
  }

  function openBindingForm(record?: any) {
    Object.keys(bindingForm).forEach((key) => delete bindingForm[key])
    Object.assign(bindingForm, {
      id: record?.id,
      datasource_alias: currentAlias.value.id,
      test_object: record?.test_object?.id || record?.test_object || null,
      database: record?.database?.id || record?.database || null,
      description: record?.description || '',
      status: record?.status ?? 1,
    })
    bindingFormVisible.value = true
  }

  async function saveBinding() {
    const request = bindingForm.id
      ? putDataFactoryDatasourceBinding
      : postDataFactoryDatasourceBinding
    bindingSaving.value = true
    try {
      const res = await request({ ...bindingForm })
      Message.success(res.msg)
      loadBindings()
      return true
    } catch (error) {
      return false
    } finally {
      bindingSaving.value = false
    }
  }

  function removeBinding(record: any) {
    Modal.confirm({
      title: '删除绑定',
      content: '确认删除该环境绑定？',
      onBeforeOk: () => {
        actionLoading.value = `binding-delete-${record.id}`
        return deleteDataFactoryDatasourceBinding(record.id)
          .then(loadBindings)
          .finally(() => {
            actionLoading.value = ''
          })
      },
    })
  }

  onMounted(() => {
    enumStore.getEnum()
    projectInfo.projectProductName()
    loadOptions()
    doRefresh()
  })
</script>
<style scoped>
  .datasource-toolbar {
    margin-bottom: 12px;
  }
</style>
