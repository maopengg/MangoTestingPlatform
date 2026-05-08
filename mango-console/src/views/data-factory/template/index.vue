<template>
  <TableBody>
    <template #header>
      <a-card title="数据工厂 / 状态模板" :bordered="false">
        <template #extra><a-button size="small" type="primary" @click="openTemplate()">新增模板</a-button></template>
      </a-card>
    </template>

    <template #default>
      <a-table :data="table.dataList" :loading="table.tableLoading.value" :pagination="false" :row-key="'id'">
        <template #columns>
          <a-table-column title="ID" data-index="id" :width="80" />
          <a-table-column title="名称" data-index="name" />
          <a-table-column title="实体" :width="180">
            <template #cell="{ record }">{{ record.entity?.name || record.entity }}</template>
          </a-table-column>
          <a-table-column title="清理策略" :width="120">
            <template #cell="{ record }">{{ enumTitle(enumStore.data_factory_cleanup_strategy, record.cleanup_strategy) }}</template>
          </a-table-column>
          <a-table-column title="状态" :width="90">
            <template #cell="{ record }"><a-tag :color="record.status === 1 ? 'green' : 'gray'">{{ record.status === 1 ? '启用' : '禁用' }}</a-tag></template>
          </a-table-column>
          <a-table-column title="操作" :width="360" fixed="right">
            <template #cell="{ record }">
              <a-space wrap>
                <a-button size="mini" type="text" @click="openTemplate(record)">编辑</a-button>
                <a-button size="mini" type="text" @click="copyTemplate(record)">复制</a-button>
                <a-button size="mini" type="text" @click="switchTemplate(record)">{{ record.status === 1 ? '禁用' : '启用' }}</a-button>
                <a-button size="mini" type="text" @click="previewRun(record)">预览数据</a-button>
                <a-button size="mini" type="text" @click="debugRun(record)">调试运行</a-button>
                <a-button size="mini" status="danger" type="text" @click="removeTemplate(record)">删除</a-button>
              </a-space>
            </template>
          </a-table-column>
        </template>
      </a-table>
    </template>

    <template #footer><TableFooter :pagination="pagination" /></template>
  </TableBody>

  <a-modal v-model:visible="templateVisible" :title="templateForm.id ? '编辑模板' : '新增模板'" width="820px" @ok="saveTemplate">
    <a-form :model="templateForm" layout="vertical">
      <a-grid :cols="2" :col-gap="16">
        <a-grid-item>
          <a-form-item label="产品" required><a-cascader v-model="templateForm.project_product" :options="projectInfo.projectProduct" allow-search allow-clear /></a-form-item>
        </a-grid-item>
        <a-grid-item>
          <a-form-item label="实体" required><a-select v-model="templateForm.entity" :options="entityOptions" :field-names="{ value: 'id', label: 'name' }" allow-search /></a-form-item>
        </a-grid-item>
        <a-grid-item><a-form-item label="模板名称" required><a-input v-model="templateForm.name" /></a-form-item></a-grid-item>
        <a-grid-item>
          <a-form-item label="清理策略"><a-select v-model="templateForm.cleanup_strategy" :options="enumStore.data_factory_cleanup_strategy" :field-names="enumFieldNames" /></a-form-item>
        </a-grid-item>
      </a-grid>
      <a-form-item label="字段覆盖(JSON)"><a-textarea v-model="templateForm.field_overrides_text" :auto-size="{ minRows: 4, maxRows: 8 }" /></a-form-item>
      <a-form-item label="输出配置(JSON)"><a-textarea v-model="templateForm.output_config_text" :auto-size="{ minRows: 3, maxRows: 6 }" /></a-form-item>
      <a-form-item label="描述"><a-textarea v-model="templateForm.description" /></a-form-item>
    </a-form>
  </a-modal>

  <a-modal v-model:visible="debugVisible" title="调试结果" width="760px" :footer="false">
    <a-space direction="vertical" style="width: 100%">
      <a-alert v-if="debugResult.execution_no" type="success">执行编号：{{ debugResult.execution_no }}</a-alert>
      <a-textarea :model-value="JSON.stringify(debugResult.context || debugResult, null, 2)" :auto-size="{ minRows: 12, maxRows: 20 }" readonly />
      <a-button v-if="debugResult.execution_id" status="danger" @click="debugCleanup">清理本次调试数据</a-button>
    </a-space>
  </a-modal>

  <a-modal v-model:visible="previewVisible" title="生成数据预览" width="920px" :footer="false">
    <a-space direction="vertical" style="width: 100%">
      <a-alert v-if="previewResult.missing_fields?.length" type="warning">
        当前还有 {{ previewResult.missing_fields.length }} 个字段需要配置，建议补齐后再调试运行。
      </a-alert>
      <a-alert v-else-if="previewResult.payload" type="success">当前模板字段已能生成 payload，可以继续调试运行。</a-alert>
      <a-table v-if="previewResult.fields?.length" :data="previewResult.fields" :pagination="false" :row-key="'name'" size="small">
        <template #columns>
          <a-table-column title="字段" data-index="name" :width="150" />
          <a-table-column title="生成值">
            <template #cell="{ record }">{{ formatPreviewValue(record.value) }}</template>
          </a-table-column>
          <a-table-column title="状态" :width="110">
            <template #cell="{ record }"><a-tag :color="record.valid ? 'green' : 'red'">{{ record.valid ? '正常' : '需配置' }}</a-tag></template>
          </a-table-column>
          <a-table-column title="说明" data-index="message" :width="260" />
        </template>
      </a-table>
      <a-textarea :model-value="JSON.stringify(previewResult, null, 2)" :auto-size="{ minRows: 10, maxRows: 20 }" readonly />
    </a-space>
  </a-modal>

</template>

<script lang="ts" setup>
  import {
    deleteDataFactoryTemplate,
    getDataFactoryEntity,
    getDataFactoryTemplate,
    postDataFactoryTemplate,
    postDataFactoryTemplateCopy,
    postDataFactoryTemplateDebugCleanup,
    postDataFactoryTemplateDebugRun,
    postDataFactoryTemplatePreview,
    putDataFactoryTemplate,
    putDataFactoryTemplateStatus,
  } from '@/api/data-factory'
  import { usePagination, useTable } from '@/hooks/table'
  import { useEnum } from '@/store/modules/get-enum'
  import { useProject } from '@/store/modules/get-project'
  import useUserStore from '@/store/modules/user'
  import { Message, Modal } from '@arco-design/web-vue'
  import { onMounted, reactive, ref } from 'vue'

  const table = useTable()
  const pagination = usePagination(doRefresh)
  const enumStore = useEnum()
  const projectInfo = useProject()
  const userStore = useUserStore()
  const enumFieldNames = { value: 'key', label: 'title' }
  const entityOptions = ref<any[]>([])
  const templateVisible = ref(false)
  const debugVisible = ref(false)
  const previewVisible = ref(false)
  const debugTemplate = ref<any>(null)
  const previewTemplate = ref<any>(null)
  const debugResult = ref<any>({})
  const previewResult = ref<any>({})
  const templateForm = reactive<any>({})

  function enumTitle(options: any[] = [], value: any) {
    return options.find((it) => it.key === value)?.title || value
  }

  function resetTemplateForm(record?: any) {
    Object.keys(templateForm).forEach((key) => delete templateForm[key])
    Object.assign(templateForm, {
      id: record?.id,
      project_product: record?.project_product?.id || record?.project_product || null,
      entity: record?.entity?.id || record?.entity || null,
      name: record?.name || '',
      description: record?.description || '',
      field_overrides_text: JSON.stringify(record?.field_overrides || {}, null, 2),
      output_config_text: JSON.stringify(record?.output_config || [], null, 2),
      cleanup_strategy: record?.cleanup_strategy || 2,
      status: record?.status || 1,
    })
  }

  function doRefresh() {
    table.tableLoading.value = true
    getDataFactoryTemplate({ page: pagination.page, pageSize: pagination.pageSize }).then((res) => {
      table.handleSuccess(res)
      pagination.setTotalSize((res as any).totalSize)
    })
  }

  function loadEntities() {
    getDataFactoryEntity({}).then((res) => {
      entityOptions.value = res.data || []
    })
  }

  function openTemplate(record?: any) {
    resetTemplateForm(record)
    templateVisible.value = true
  }

  function saveTemplate() {
    if (!templateForm.project_product || !templateForm.entity || !templateForm.name) {
      Message.error('请先填写产品、实体和模板名称')
      return
    }

    let fieldOverrides = {}
    let outputConfig: any[] = []
    try {
      fieldOverrides = templateForm.field_overrides_text ? JSON.parse(templateForm.field_overrides_text) : {}
      outputConfig = templateForm.output_config_text ? JSON.parse(templateForm.output_config_text) : []
    } catch (error) {
      Message.error('字段覆盖或输出配置不是合法 JSON')
      return
    }

    const payload = {
      ...templateForm,
      field_overrides: fieldOverrides,
      output_config: outputConfig,
    }
    delete payload.field_overrides_text
    delete payload.output_config_text
    const request = payload.id ? putDataFactoryTemplate : postDataFactoryTemplate
    request(payload).then((res) => {
      Message.success(res.msg)
      templateVisible.value = false
      doRefresh()
    })
  }

  function removeTemplate(record: any) {
    Modal.confirm({
      title: '删除模板',
      content: `确认删除 ${record.name}？`,
      onOk: () => deleteDataFactoryTemplate(record.id).then(() => doRefresh()),
    })
  }

  function copyTemplate(record: any) {
    postDataFactoryTemplateCopy({ id: record.id }).then((res) => {
      Message.success(res.msg)
      doRefresh()
    })
  }

  function switchTemplate(record: any) {
    putDataFactoryTemplateStatus({ id: record.id, status: record.status === 1 ? 0 : 1 }).then(() => doRefresh())
  }

  function formatPreviewValue(value: any) {
    if (value === null || value === undefined || value === '') {
      return '空'
    }
    if (typeof value === 'object') {
      return JSON.stringify(value)
    }
    return String(value)
  }

  function previewRun(record: any) {
    if (!ensureSelectedEnvironment()) {
      return
    }
    previewTemplate.value = record
    debugTemplate.value = null
    confirmDebugRun()
  }

  function debugRun(record: any) {
    if (!ensureSelectedEnvironment()) {
      return
    }
    debugTemplate.value = record
    previewTemplate.value = null
    confirmDebugRun()
  }

  function resetRunMode() {
    debugTemplate.value = null
    previewTemplate.value = null
  }

  function confirmDebugRun() {
    if (!ensureSelectedEnvironment()) {
      return
    }
    if (previewTemplate.value) {
      postDataFactoryTemplatePreview({ template_id: previewTemplate.value.id, test_env: userStore.selected_environment }).then((res) => {
        previewResult.value = res.data || {}
        previewTemplate.value = null
        previewVisible.value = true
      })
      return
    }
    postDataFactoryTemplateDebugRun({ template_id: debugTemplate.value.id, test_env: userStore.selected_environment }).then((res) => {
      debugResult.value = res.data || {}
      debugVisible.value = true
      debugTemplate.value = null
    })
  }

  function debugCleanup() {
    postDataFactoryTemplateDebugCleanup({ execution_id: debugResult.value.execution_id }).then((res) => {
      Message.success(res.msg)
    })
  }

  function ensureSelectedEnvironment() {
    if (userStore.selected_environment == null) {
      Message.error('请先在顶部选择测试环境')
      return false
    }
    return true
  }

  onMounted(() => {
    enumStore.getEnum()
    projectInfo.projectProductName()
    loadEntities()
    doRefresh()
  })

</script>
