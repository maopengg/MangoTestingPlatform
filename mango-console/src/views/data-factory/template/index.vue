<template>
  <TableBody>
    <template #header>
      <a-card title="数据工厂 / 状态模板" :bordered="false">
        <template #extra><a-button size="small" type="primary" @click="openTemplate()">新增模板</a-button></template>
      </a-card>
    </template>

    <template #default>
      <a-table :columns="templateTableColumns" :data="table.dataList" :loading="table.tableLoading.value" :pagination="false" :row-key="'id'">
        <template #columns>
          <a-table-column
            v-for="item of templateTableColumns"
            :key="item.key"
            :data-index="item.key"
            :fixed="item.fixed"
            :title="item.title"
            :width="item.width"
          >
            <template v-if="item.key === 'index'" #cell="{ record }">
              {{ record.id }}
            </template>
            <template v-else-if="item.key === 'entity'" #cell="{ record }">
              {{ record.entity?.name || record.entity }}
            </template>
            <template v-else-if="item.key === 'cleanup_strategy'" #cell="{ record }">
              {{ enumTitle(enumStore.data_factory_cleanup_strategy, record.cleanup_strategy) }}
            </template>
            <template v-else-if="item.key === 'status'" #cell="{ record }">
              <a-tag :color="record.status === 1 ? 'green' : 'gray'">{{ record.status === 1 ? '启用' : '禁用' }}</a-tag>
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <a-space wrap>
                <a-button :loading="actionLoading === `preview-${record.id}`" size="mini" type="text" @click="previewRun(record)">预览数据</a-button>
                <a-button :loading="actionLoading === `debug-${record.id}`" size="mini" type="text" @click="debugRun(record)">调试运行</a-button>
                <a-dropdown trigger="hover">
                  <a-button size="mini" type="text">···</a-button>
                  <template #content>
                    <a-doption>
                      <a-button size="mini" type="text" @click="openTemplate(record)">编辑</a-button>
                    </a-doption>
                    <a-doption>
                      <a-button :loading="actionLoading === `copy-${record.id}`" size="mini" type="text" @click="copyTemplate(record)">复制</a-button>
                    </a-doption>
                    <a-doption>
                      <a-button :loading="actionLoading === `switch-${record.id}`" size="mini" type="text" @click="switchTemplate(record)">{{ record.status === 1 ? '禁用' : '启用' }}</a-button>
                    </a-doption>
                    <a-doption>
                      <a-button :loading="actionLoading === `delete-${record.id}`" size="mini" status="danger" type="text" @click="removeTemplate(record)">删除</a-button>
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

  <a-modal v-model:visible="templateVisible" :on-before-ok="saveTemplate" :ok-loading="templateSaving" :title="templateForm.id ? '编辑模板' : '新增模板'" width="1100px">
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
      <a-form-item label="字段覆盖规则">
        <a-spin :loading="fieldOverrideLoading" style="width: 100%">
          <FieldOverrideEditor
            v-if="templateForm.entity"
            v-model="templateForm.field_overrides"
            :fields="fieldOverrideRows"
            :generator-options="enumStore.data_factory_generator_type"
          />
          <a-alert v-else type="info">请先选择实体</a-alert>
        </a-spin>
      </a-form-item>
      <a-form-item label="输出配置(JSON)"><a-textarea v-model="templateForm.output_config_text" :auto-size="{ minRows: 3, maxRows: 6 }" /></a-form-item>
      <a-form-item label="描述"><a-textarea v-model="templateForm.description" /></a-form-item>
    </a-form>
  </a-modal>

  <a-modal v-model:visible="debugVisible" title="调试结果" width="760px" :footer="false">
    <a-space direction="vertical" style="width: 100%">
      <a-alert v-if="debugResult.execution_no" type="success">执行编号：{{ debugResult.execution_no }}</a-alert>
      <a-textarea :model-value="JSON.stringify(debugResult.context || debugResult, null, 2)" :auto-size="{ minRows: 12, maxRows: 20 }" readonly />
      <a-button v-if="debugResult.execution_id" :loading="debugCleanupLoading" status="danger" @click="debugCleanup">清理本次调试数据</a-button>
    </a-space>
  </a-modal>

  <a-modal v-model:visible="previewVisible" title="生成数据预览" width="920px" :footer="false">
    <a-space direction="vertical" style="width: 100%">
      <a-alert v-if="previewResult.missing_fields?.length" type="warning">
        当前还有 {{ previewResult.missing_fields.length }} 个字段需要配置，建议补齐后再调试运行。
      </a-alert>
      <a-alert v-else-if="previewResult.payload" type="success">当前模板字段已能生成 payload，可以继续调试运行。</a-alert>
      <a-table
        v-if="flattenDependencyTree(previewResult.dependency_tree).length"
        :columns="dependencyTreeColumns"
        :data="flattenDependencyTree(previewResult.dependency_tree)"
        :pagination="false"
        :row-key="'path'"
        size="small"
      >
        <template #columns>
          <a-table-column
            v-for="item of dependencyTreeColumns"
            :key="item.key"
            :data-index="item.key"
            :title="item.title"
            :width="item.width"
          >
            <template v-if="item.key === 'node'" #cell="{ record }">
              <span :style="{ paddingLeft: `${record.level * 18}px` }">{{ record.template_name }}</span>
              <a-tag v-if="record.level === 0" size="small" color="arcoblue" style="margin-left: 8px">根节点</a-tag>
              <a-tag v-else-if="record.reused" size="small" color="green" style="margin-left: 8px">复用</a-tag>
              <a-tag v-else size="small" color="orange" style="margin-left: 8px">创建</a-tag>
            </template>
            <template v-else-if="item.key === 'action'" #cell="{ record }">
              <a-tag :color="getDependencyActionColor(record.action)" size="small">{{ getDependencyActionText(record.action) }}</a-tag>
            </template>
          </a-table-column>
        </template>
      </a-table>
      <a-table v-if="previewResult.fields?.length" :columns="previewFieldColumns" :data="previewResult.fields" :pagination="false" :row-key="'name'" size="small">
        <template #columns>
          <a-table-column
            v-for="item of previewFieldColumns"
            :key="item.key"
            :data-index="item.key"
            :title="item.title"
            :width="item.width"
          >
            <template v-if="item.key === 'value'" #cell="{ record }">
              {{ formatPreviewValue(record.value) }}
            </template>
            <template v-else-if="item.key === 'valid'" #cell="{ record }">
              <a-tag :color="record.valid ? 'green' : 'red'">{{ record.valid ? '正常' : '需配置' }}</a-tag>
            </template>
          </a-table-column>
        </template>
      </a-table>
    </a-space>
  </a-modal>

</template>

<script lang="ts" setup>
  import {
    deleteDataFactoryTemplate,
    getDataFactoryEntity,
    getDataFactoryField,
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
  import FieldOverrideEditor from '@/components/DataFactory/FieldOverrideEditor.vue'
  import type { DataFactoryFieldOverrides, DataFactoryFieldRule } from '@/types/data-factory'
  import { Message, Modal } from '@arco-design/web-vue'
  import { onMounted, reactive, ref, watch } from 'vue'
  import { dependencyTreeColumns, previewFieldColumns, templateTableColumns } from './config'

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
  const templateSaving = ref(false)
  const fieldOverrideLoading = ref(false)
  const fieldOverrideRows = ref<DataFactoryFieldRule[]>([])
  const resettingTemplateForm = ref(false)
  const debugCleanupLoading = ref(false)
  const actionLoading = ref('')

  function enumTitle(options: any[] = [], value: any) {
    return options.find((it) => it.key === value)?.title || value
  }

  function resetTemplateForm(record?: any) {
    resettingTemplateForm.value = true
    Object.keys(templateForm).forEach((key) => delete templateForm[key])
    Object.assign(templateForm, {
      id: record?.id,
      project_product: record?.project_product?.id || record?.project_product || null,
      entity: record?.entity?.id || record?.entity || null,
      name: record?.name || '',
      description: record?.description || '',
      field_overrides: (record?.field_overrides || {}) as DataFactoryFieldOverrides,
      output_config_text: JSON.stringify(record?.output_config || [], null, 2),
      cleanup_strategy: record?.cleanup_strategy || 2,
      status: record?.status || 1,
    })
    resettingTemplateForm.value = false
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

  function loadTemplateFields(entityId?: number) {
    fieldOverrideRows.value = []
    if (!entityId) {
      return Promise.resolve()
    }
    fieldOverrideLoading.value = true
    return getDataFactoryField({ entity: entityId })
      .then((res) => {
        fieldOverrideRows.value = res.data || []
      })
      .finally(() => {
        fieldOverrideLoading.value = false
      })
  }

  function openTemplate(record?: any) {
    resetTemplateForm(record)
    loadTemplateFields(templateForm.entity)
    templateVisible.value = true
  }

  async function saveTemplate() {
    if (!templateForm.project_product || !templateForm.entity || !templateForm.name) {
      Message.error('请先填写产品、实体和模板名称')
      return false
    }

    let outputConfig: any[] = []
    try {
      outputConfig = templateForm.output_config_text ? JSON.parse(templateForm.output_config_text) : []
    } catch (error) {
      Message.error('输出配置不是合法 JSON')
      return false
    }

    const payload = {
      ...templateForm,
      field_overrides: templateForm.field_overrides || {},
      output_config: outputConfig,
    }
    delete payload.output_config_text
    const request = payload.id ? putDataFactoryTemplate : postDataFactoryTemplate
    templateSaving.value = true
    try {
      const res = await request(payload)
      Message.success(res.msg)
      doRefresh()
      return true
    } catch (error) {
      return false
    } finally {
      templateSaving.value = false
    }
  }

  function removeTemplate(record: any) {
    Modal.confirm({
      title: '删除模板',
      content: `确认删除 ${record.name}？`,
      onOk: () => {
        actionLoading.value = `delete-${record.id}`
        return deleteDataFactoryTemplate(record.id)
          .then(() => doRefresh())
          .finally(() => {
            actionLoading.value = ''
          })
      },
    })
  }

  function copyTemplate(record: any) {
    actionLoading.value = `copy-${record.id}`
    postDataFactoryTemplateCopy({ id: record.id })
      .then((res) => {
        Message.success(res.msg)
        doRefresh()
      })
      .finally(() => {
        actionLoading.value = ''
      })
  }

  function switchTemplate(record: any) {
    actionLoading.value = `switch-${record.id}`
    putDataFactoryTemplateStatus({ id: record.id, status: record.status === 1 ? 0 : 1 })
      .then(() => doRefresh())
      .finally(() => {
        actionLoading.value = ''
      })
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

  function flattenDependencyTree(tree: any, level = 0, path = '0'): any[] {
    if (!tree) {
      return []
    }
    const current = {
      ...tree,
      level,
      path,
      node: tree.template_name,
      message: tree.message || (tree.reused ? '复用上下文已有数据' : ''),
    }
    const children = (tree.children || []).flatMap((child: any, index: number) =>
      flattenDependencyTree(child, level + 1, `${path}-${index}`)
    )
    return [current, ...children]
  }

  function getDependencyActionText(action: string) {
    const map: Record<string, string> = {
      root: '根节点',
      create: '创建',
      reuse: '复用',
    }
    return map[action] || action || '-'
  }

  function getDependencyActionColor(action: string) {
    const map: Record<string, string> = {
      root: 'arcoblue',
      create: 'orange',
      reuse: 'green',
    }
    return map[action] || 'gray'
  }

  function previewRun(record: any) {
    if (!ensureSelectedEnvironment()) {
      return
    }
    actionLoading.value = `preview-${record.id}`
    previewTemplate.value = record
    debugTemplate.value = null
    confirmDebugRun().finally(() => {
      actionLoading.value = ''
    })
  }

  function debugRun(record: any) {
    if (!ensureSelectedEnvironment()) {
      return
    }
    actionLoading.value = `debug-${record.id}`
    debugTemplate.value = record
    previewTemplate.value = null
    confirmDebugRun().finally(() => {
      actionLoading.value = ''
    })
  }

  function resetRunMode() {
    debugTemplate.value = null
    previewTemplate.value = null
  }

  function confirmDebugRun() {
    if (!ensureSelectedEnvironment()) {
      return Promise.resolve()
    }
    if (previewTemplate.value) {
      return postDataFactoryTemplatePreview({ template_id: previewTemplate.value.id, test_env: userStore.selected_environment }).then((res) => {
        previewResult.value = res.data || {}
        previewTemplate.value = null
        previewVisible.value = true
      })
    }
    return postDataFactoryTemplateDebugRun({ template_id: debugTemplate.value.id, test_env: userStore.selected_environment }).then((res) => {
      debugResult.value = res.data || {}
      debugVisible.value = true
      debugTemplate.value = null
    })
  }

  function debugCleanup() {
    debugCleanupLoading.value = true
    postDataFactoryTemplateDebugCleanup({ execution_id: debugResult.value.execution_id })
      .then((res) => {
        Message.success(res.msg)
      })
      .finally(() => {
        debugCleanupLoading.value = false
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

  watch(
    () => templateForm.entity,
    (entityId) => {
      if (!templateVisible.value || resettingTemplateForm.value) {
        return
      }
      templateForm.field_overrides = {}
      loadTemplateFields(entityId)
    }
  )

</script>
