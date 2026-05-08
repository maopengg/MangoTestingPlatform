<template>
  <TableBody>
    <template #header>
      <a-card title="数据工厂 / 数据源映射" :bordered="false">
        <template #extra>
          <a-space>
            <a-button size="small" type="primary" @click="openAlias()">新增逻辑源</a-button>
            <a-button size="small" @click="doRefresh">刷新</a-button>
          </a-space>
        </template>
      </a-card>
    </template>

    <template #default>
      <a-table :columns="datasourceAliasColumns" :data="aliasTable.dataList" :loading="aliasTable.tableLoading.value" :pagination="false" :row-key="'id'">
        <template #columns>
          <a-table-column
            v-for="item of datasourceAliasColumns"
            :key="item.key"
            :data-index="item.key"
            :fixed="item.fixed"
            :title="item.title"
            :width="item.width"
          >
            <template v-if="item.key === 'index'" #cell="{ record }">
              {{ record.id }}
            </template>
            <template v-else-if="item.key === 'db_type'" #cell="{ record }">
              {{ enumTitle(enumStore.database_type, record.db_type) }}
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <a-space>
                <a-button size="mini" type="text" @click="openAlias(record)">编辑</a-button>
                <a-button size="mini" type="text" @click="openBinding(record)">环境绑定</a-button>
                <a-dropdown trigger="hover">
                  <a-button size="mini" type="text">···</a-button>
                  <template #content>
                    <a-doption>
                      <a-button size="mini" status="danger" type="text" @click="removeAlias(record)">删除</a-button>
                    </a-doption>
                  </template>
                </a-dropdown>
              </a-space>
            </template>
          </a-table-column>
        </template>
      </a-table>
    </template>
    <template #footer><TableFooter :pagination="pagination" /></template>
  </TableBody>

  <a-modal v-model:visible="aliasVisible" :title="aliasForm.id ? '编辑逻辑数据源' : '新增逻辑数据源'" width="680px" @ok="saveAlias">
    <a-form :model="aliasForm" layout="vertical">
      <a-form-item label="产品" required>
        <a-cascader v-model="aliasForm.project_product" :options="projectInfo.projectProduct" allow-search allow-clear />
      </a-form-item>
      <a-form-item label="名称" required><a-input v-model="aliasForm.name" /></a-form-item>
      <a-form-item label="编码" required><a-input v-model="aliasForm.code" /></a-form-item>
      <a-form-item label="数据库类型" required>
        <a-select v-model="aliasForm.db_type" :options="enumStore.database_type" :field-names="enumFieldNames" />
      </a-form-item>
      <a-form-item label="描述"><a-textarea v-model="aliasForm.description" /></a-form-item>
    </a-form>
  </a-modal>

  <a-drawer v-model:visible="bindingVisible" :title="`${currentAlias?.name || ''} / 环境绑定`" width="900px">
    <a-space style="margin-bottom: 12px">
      <a-button type="primary" @click="openBindingForm()">新增绑定</a-button>
      <a-button @click="loadBindings">刷新</a-button>
    </a-space>
    <a-table :columns="datasourceBindingColumns" :data="bindingRows" :pagination="false" :row-key="'id'">
      <template #columns>
        <a-table-column
          v-for="item of datasourceBindingColumns"
          :key="item.key"
          :data-index="item.key"
          :title="item.title"
          :width="item.width"
        >
          <template v-if="item.key === 'index'" #cell="{ record }">
            {{ record.id }}
          </template>
          <template v-else-if="item.key === 'test_object'" #cell="{ record }">
            {{ displayName(record.test_object) }}
          </template>
          <template v-else-if="item.key === 'database'" #cell="{ record }">
            {{ displayDatabase(record.database) }}
          </template>
          <template v-else-if="item.key === 'actions'" #cell="{ record }">
            <a-space>
              <a-button size="mini" type="text" @click="openBindingForm(record)">编辑</a-button>
              <a-button size="mini" status="danger" type="text" @click="removeBinding(record)">删除</a-button>
            </a-space>
          </template>
        </a-table-column>
      </template>
    </a-table>
  </a-drawer>

  <a-modal v-model:visible="bindingFormVisible" :title="bindingForm.id ? '编辑绑定' : '新增绑定'" width="680px" @ok="saveBinding">
    <a-form :model="bindingForm" layout="vertical">
      <a-form-item label="测试环境" required>
        <a-select v-model="bindingForm.test_object" :options="testObjectOptions" :field-names="{ value: 'id', label: 'name' }" allow-search />
      </a-form-item>
      <a-form-item label="实际数据库" required>
        <a-select v-model="bindingForm.database" :options="databaseOptions" :field-names="{ value: 'id', label: 'name' }" allow-search />
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
  import { Message, Modal } from '@arco-design/web-vue'
  import { onMounted, reactive, ref } from 'vue'
  import { datasourceAliasColumns, datasourceBindingColumns } from './config'

  const aliasTable = useTable()
  const pagination = usePagination(doRefresh)
  const enumStore = useEnum()
  const projectInfo = useProject()
  const enumFieldNames = { value: 'key', label: 'title' }
  const aliasVisible = ref(false)
  const bindingVisible = ref(false)
  const bindingFormVisible = ref(false)
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
    getDataFactoryDatasourceAlias({ page: pagination.page, pageSize: pagination.pageSize }).then((res) => {
      aliasTable.handleSuccess(res)
      pagination.setTotalSize((res as any).totalSize)
    })
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

  function saveAlias() {
    const request = aliasForm.id ? putDataFactoryDatasourceAlias : postDataFactoryDatasourceAlias
    request({ ...aliasForm }).then((res) => {
      Message.success(res.msg)
      aliasVisible.value = false
      doRefresh()
    })
  }

  function removeAlias(record: any) {
    Modal.confirm({ title: '删除逻辑源', content: `确认删除 ${record.name}？`, onOk: () => deleteDataFactoryDatasourceAlias(record.id).then(doRefresh) })
  }

  function openBinding(alias: any) {
    currentAlias.value = alias
    bindingVisible.value = true
    loadBindings()
  }

  function loadBindings() {
    getDataFactoryDatasourceBinding({ datasource_alias: currentAlias.value.id }).then((res) => {
      bindingRows.value = res.data || []
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

  function saveBinding() {
    const request = bindingForm.id ? putDataFactoryDatasourceBinding : postDataFactoryDatasourceBinding
    request({ ...bindingForm }).then((res) => {
      Message.success(res.msg)
      bindingFormVisible.value = false
      loadBindings()
    })
  }

  function removeBinding(record: any) {
    Modal.confirm({ title: '删除绑定', content: '确认删除该环境绑定？', onOk: () => deleteDataFactoryDatasourceBinding(record.id).then(loadBindings) })
  }

  onMounted(() => {
    enumStore.getEnum()
    projectInfo.projectProductName()
    loadOptions()
    doRefresh()
  })
</script>
