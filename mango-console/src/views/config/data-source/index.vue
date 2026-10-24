<template>
  <TableBody class="mango-source-page" content-flush>
    <template #header>
      <TableHeader title="数据源工作台" :show-filter="false" />
    </template>
    <DataSourceWorkbench
      :sources="table.dataList"
      :loading="table.tableLoading.value"
      :testing-ids="testingIds"
      @add="onAdd"
      @edit="onUpdate"
      @remove="onDelete"
      @test="onTest"
    />
  </TableBody>

  <ModalDialog ref="modalDialogRef" :title="data.actionTitle" @confirm="onDataForm">
    <template #content>
      <a-form :model="formModel">
        <a-form-item
          v-for="item of visibleFormItems"
          :key="item.key"
          :class="item.required ? 'mango-form-item__require' : 'mango-form-item__no_require'"
          :label="item.label"
        >
          <a-select
            v-if="item.key === 'source_category'"
            v-model="item.value"
            :field-names="fieldNames"
            :options="enumStore.data_source_category"
            :placeholder="item.placeholder"
            value-key="key"
            @change="onCategoryChange"
          />
          <a-select
            v-else-if="item.key === 'db_type'"
            v-model="item.value"
            :field-names="fieldNames"
            :options="sourceTypeOptions"
            :placeholder="item.placeholder"
            allow-search
            value-key="key"
            @change="onSourceTypeChange"
          />
          <a-input-password
            v-else-if="item.key === 'password'"
            v-model="item.value"
            :placeholder="item.placeholder"
          />
          <a-input v-else v-model="item.value" :placeholder="item.placeholder" />
        </a-form-item>
        <template v-if="currentSourceType === 10">
          <a-form-item label="TLS"><a-switch v-model="extraConfig.ssl" size="small" /></a-form-item>
        </template>
        <template v-else-if="currentSourceType === 20">
          <a-form-item label="访问协议">
            <a-select v-model="extraConfig.scheme" :options="['http', 'https']" />
          </a-form-item>
          <a-form-item label="路径前缀">
            <a-input
              v-model="extraConfig.path_prefix"
              placeholder="例如 elasticsearch，可留空"
              data-testid="qa-views-config-data-source-input-例如-elasticsearch-可留空"
            />
          </a-form-item>
          <a-form-item label="校验证书">
            <a-switch v-model="extraConfig.verify_certs" size="small" />
          </a-form-item>
        </template>
      </a-form>
    </template>
  </ModalDialog>
</template>

<script lang="ts" setup>
  import { Message, Modal, Notification } from '@arco-design/web-vue'
  import { computed, h, nextTick, onMounted, reactive, ref } from 'vue'
  import {
    deleteSystemDataSource,
    getSystemDataSource,
    postSystemDataSource,
    putSystemDataSource,
  } from '@/api/system/data_source'
  import { postDataSourceExecution } from '@/api/data-source-execution'
  import DataSourceWorkbench from './components/DataSourceWorkbench.vue'
  import { useTable } from '@/hooks/table'
  import { fieldNames } from '@/setting'
  import { useEnum } from '@/store/modules/get-enum'
  import { ModalDialogType } from '@/types/components'
  import { getFormItems } from '@/utils/datacleaning'
  import { formItems } from './config'

  const enumStore = useEnum()
  const table = useTable()
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const formModel = ref({})
  const testingIds = ref<any[]>([])
  const data = reactive({ isAdd: true, updateId: 0, actionTitle: '新增数据库' })
  const extraConfig = reactive<any>({})

  const currentCategory = computed(() =>
    Number(formItems.find((item) => item.key === 'source_category')?.value ?? 0)
  )
  const currentSourceType = computed(() =>
    Number(formItems.find((item) => item.key === 'db_type')?.value ?? 0)
  )
  const sourceTypeOptions = computed(() =>
    (enumStore.data_source_type || []).filter((item: any) => {
      return enumStore.data_source_type_category[item.key] === currentCategory.value && ![3, 4].includes(item.key)
    })
  )
  const visibleFormItems = computed(() =>
    formItems.filter((item) => {
      if (item.key === 'file_path') return currentSourceType.value === 2
      if (['host', 'port', 'user', 'password'].includes(item.key)) return currentSourceType.value !== 2
      return true
    })
  )

  function dataSourceConnectionName(record: any) {
    if (record.db_type === 2) return record.file_path || '-'
    if (record.db_type === 10) {
      return `${record.host}:${record.port}`
    }
    if (record.db_type === 20) {
      const prefix = String(record.extra_config?.path_prefix || '').replace(/^\/+|\/+$/g, '')
      return `${record.host}:${record.port}${prefix ? `/${prefix}` : ''}`
    }
    return `${record.host}:${record.port}`
  }

  function dataSourceDisplayLabel(record: any) {
    const name = dataSourceConnectionName(record)
    if (record.display_name && record.display_name !== name) {
      return `${record.display_name}（${name}）`
    }
    return name
  }

  function onCategoryChange() {
    const typeItem = formItems.find((item) => item.key === 'db_type')
    if (typeItem) typeItem.value = sourceTypeOptions.value[0]?.key ?? null
    onSourceTypeChange()
  }

  function onSourceTypeChange() {
    const portItem = formItems.find((item) => item.key === 'port')
    if (portItem) {
      const defaults: Record<number, number> = { 0: 3306, 1: 5432, 10: 6379, 20: 9200 }
      portItem.value = defaults[currentSourceType.value] || portItem.value
    }
    Object.keys(extraConfig).forEach((key) => delete extraConfig[key])
    if (currentSourceType.value === 10) Object.assign(extraConfig, { ssl: false })
    if (currentSourceType.value === 20)
      Object.assign(extraConfig, { scheme: 'http', path_prefix: '', verify_certs: true })
  }

  function doRefresh() {
    table.tableLoading.value = true
    getSystemDataSource({})
      .then((res) => {
        table.handleSuccess(res)
      })
      .catch((error) => Message.error(error?.message || error?.msg || '数据源配置加载失败'))
      .finally(() => {
        table.tableLoading.value = false
      })
  }

  function resetForm() {
    formItems.forEach((item) => {
      if (item.key === 'source_category' || item.key === 'db_type') item.value = 0
      else if (item.reset) item.reset()
      else item.value = item.multiple ? [] : ''
    })
    onSourceTypeChange()
  }

  function onAdd() {
    data.isAdd = true
    data.updateId = 0
    data.actionTitle = '新增数据库'
    resetForm()
    modalDialogRef.value?.toggle()
  }

  function onUpdate(record: any) {
    data.isAdd = false
    data.updateId = record.id
    data.actionTitle = '编辑数据库'
    modalDialogRef.value?.toggle()
    nextTick(() => {
      formItems.forEach((item) => {
        item.value = item.key === 'password' ? '' : record[item.key] ?? ''
      })
      Object.keys(extraConfig).forEach((key) => delete extraConfig[key])
      Object.assign(extraConfig, record.extra_config || {})
    })
  }

  function onDataForm() {
    if (!visibleFormItems.value.every((item) => (item.validator ? item.validator() : true))) {
      modalDialogRef.value?.setConfirmLoading(false)
      return
    }
    const value = getFormItems(visibleFormItems.value)
    if (currentSourceType.value !== 2) value.file_path = ''
    value.extra_config = { ...extraConfig }
    if (!value.password) delete value.password
    const request = data.isAdd ? postSystemDataSource : putSystemDataSource
    if (!data.isAdd) value.id = data.updateId
    request(value)
      .then((res) => {
        modalDialogRef.value?.toggle()
        Message.success(res.msg)
        doRefresh()
      })
      .finally(() => modalDialogRef.value?.setConfirmLoading(false))
  }

  function onTest(record: any) {
    testingIds.value = [...testingIds.value, record.id]
    postDataSourceExecution({ action: 'test_connection', data_source_id: record.id })
      .then((res) => {
        const checks = Array.isArray(res.data?.checks) ? res.data.checks : []
        const statusText: Record<string, string> = {
          passed: '通过',
          failed: '失败',
          skipped: '未执行',
        }
        const content = () =>
          h(
            'div',
            checks.length
              ? checks.map((item: any, index: number) =>
                  h(
                    'div',
                    { key: item.key || index },
                    `${index + 1}. ${item.name}：${statusText[item.status] || item.status}；${
                      item.message
                    }`
                  )
                )
              : res.data?.error || res.msg
          )
        const notification = res.data?.connected ? Notification.success : Notification.error
        notification({
          title: res.data?.connected ? '数据源连接测试通过' : '数据源连接测试失败',
          content,
          duration: 10000,
          closable: true,
        })
      })
      .catch((error: any) => Message.error(error?.message || error?.msg || '数据源连接测试失败'))
      .finally(() => {
        testingIds.value = testingIds.value.filter((id) => id !== record.id)
      })
  }

  function onDelete(record: any) {
    Modal.confirm({
      title: '删除数据库配置',
      content: `确认删除数据库配置「${dataSourceDisplayLabel(
        record
      )}」？已被逻辑数据库绑定时不允许删除。`,
      cancelText: '取消',
      okText: '删除',
      onBeforeOk: () =>
        deleteSystemDataSource(record.id).then((res) => {
          Message.success(res.msg)
          doRefresh()
        }),
    })
  }

  onMounted(() => {
    enumStore.getEnum()
    doRefresh()
  })
</script>

<style scoped>
  .mango-source-page :deep(.mango-table-body__content) {
    display: flex;
    flex-direction: column;
    min-height: 0;
    overflow: hidden;
  }
  .mango-source-page :deep(.mango-source-boundary) {
    flex: 1;
  }
</style>
