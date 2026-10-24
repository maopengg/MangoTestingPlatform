<template>
  <TableBody plain class="mango-detail-workbench-page">
    <template #header>
      <TableHeader title="灰度开关" />
    </template>

    <template #default>
      <ProjectProductNavigationWorkbench
        contained-body
        :model-value="query.project_product"
        :module-value="query.module"
        :reset-key="sidebarResetKey"
        show-modules
        @filter-change="onNavigationFilterChange"
        @search="onSearchRefresh"
        @reset-search="onReset"
      >
        <template #search>
          <a-form layout="inline" :model="query" @keyup.enter="onSearchRefresh">
            <a-form-item label="配置类型">
              <a-select v-model="query.config_type" multiple :max-tag-count="1" :options="configTypeOptions" allow-clear placeholder="请选择类型" @change="onSearchRefresh" data-testid="qa-views-gray-feature-select-请选择类型" />
            </a-form-item>
            <a-form-item label="状态">
              <a-select v-model="query.status" multiple :max-tag-count="1" :options="enableStatusOptions" allow-clear placeholder="请选择状态" @change="onSearchRefresh" data-testid="qa-views-gray-feature-select-请选择状态" />
            </a-form-item>
            <a-form-item label="配置文件">
              <a-select v-model="query.yaml_file" multiple :max-tag-count="1" :options="yamlOptions" allow-clear allow-search placeholder="请选择配置文件" @change="onSearchRefresh" data-testid="qa-views-gray-feature-select-请选择配置文件" />
            </a-form-item>
            <a-form-item label="灰度编号">
              <a-input v-model="query.gray_code" allow-clear placeholder="请输入灰度编号" @blur="onSearchRefresh" @clear="onSearchRefresh" data-testid="qa-views-gray-feature-input-请输入灰度编号" />
            </a-form-item>
            <a-form-item label="灰度名称">
              <a-input v-model="query.name" allow-clear placeholder="请输入灰度名称" @blur="onSearchRefresh" @clear="onSearchRefresh" data-testid="qa-views-gray-feature-input-请输入灰度名称" />
            </a-form-item>
            <a-form-item label="灰度Key">
              <a-input v-model="query.feature_key" allow-clear placeholder="请输入灰度Key" @blur="onSearchRefresh" @clear="onSearchRefresh" data-testid="qa-views-gray-feature-input-请输入灰度key" />
            </a-form-item>
          </a-form>
        </template>
        <template #toolbar>
        <a-button v-permission="'gray.feature:create'" size="small" type="primary" @click="onAdd" data-testid="qa-views-gray-feature-button-新增灰度">新增灰度</a-button>
        </template>
      <a-table
        class="mango-native-scroll-table"
        :bordered="false"
        :columns="featureColumns"
        :data="table.dataList"
        :loading="table.tableLoading.value"
        :pagination="false"
        :scroll="{ x: grayPageConfig.scrollX, y: '100%' }"
        row-key="id"
      >
        <template #columns>
          <a-table-column v-for="item in featureColumns" :key="item.key" v-bind="item">
            <template v-if="item.key === 'index'" #cell="{ record }">{{ record.id }}</template>
            <template v-else-if="item.key === 'config_type'" #cell="{ record }">
              <a-tag :color="configTypeColor(record.config_type)" size="small">{{ configTypeText(record.config_type) }}</a-tag>
            </template>
            <template v-else-if="item.key === 'status'" #cell="{ record }">
              <a-switch v-permission="'gray.feature:status'"
                :beforeChange="(newValue) => onModifyStatus(newValue, record.id)"
                :default-checked="record.status === 1"
              />
            </template>
            <template v-else-if="item.key === 'project_product'" #cell="{ record }">
              {{ formatProjectProductPath(record.project_product) }}
            </template>
            <template v-else-if="item.key === 'module'" #cell="{ record }">
              {{ formatModulePath(record.module) }}
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <MangoTableActions
                :actions="[
                  { permission: 'gray.feature:debug', label: '预览/执行', onClick: () => onPreview(record) },
                  { permission: 'gray.feature:edit', label: '编辑', onClick: () => onEdit(record) },
                  { permission: 'gray.feature:delete', label: '删除', danger: true, loading: actionLoading === `delete-${record.id}`, onClick: () => onDelete(record) },
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

  <ModalDialog ref="dialogRef" :title="form.id ? '编辑灰度开关' : '新增灰度开关'" width="560px" @confirm="onSubmit">
    <template #content>
      <a-form class="mango-gray-form" :model="form" layout="horizontal" :label-col-props="{ span: 5 }" :wrapper-col-props="{ span: 19 }">
        <a-form-item label="项目/产品" class="mango-form-item__require"><ProjectProductSelect v-model="form.project_product" placeholder="请选择项目/产品" @change="onFormProjectProductChange" data-testid="qa-views-gray-feature-projectproductselect-请选择项目-产品" /></a-form-item>
        <a-form-item label="模块" class="mango-form-item__require"><ProductModuleSelect v-model="form.module" :project-product-id="form.project_product" :auto-clear="false" placeholder="请选择模块" /></a-form-item>
        <a-form-item label="灰度编号" class="mango-form-item__require"><a-input v-model="form.gray_code" placeholder="请输入灰度编号" data-testid="qa-views-gray-feature-input-请输入灰度编号-2" /></a-form-item>
        <a-form-item label="灰度名称" class="mango-form-item__require"><a-input v-model="form.name" placeholder="请输入灰度名称" data-testid="qa-views-gray-feature-input-请输入灰度名称-2" /></a-form-item>
        <a-form-item label="配置类型" class="mango-form-item__require"><a-select v-model="form.config_type" :options="configTypeOptions" placeholder="请选择配置类型" data-testid="qa-views-gray-feature-select-请选择配置类型" /></a-form-item>
        <a-form-item label="灰度Key" class="mango-form-item__require mango-gray-form__full"><a-input v-model="form.feature_key" placeholder="请输入灰度Key" data-testid="qa-views-gray-feature-input-请输入灰度key-2" /></a-form-item>
        <a-form-item v-if="form.config_type === 1" label="配置文件" class="mango-form-item__require mango-gray-form__full">
          <a-select v-model="form.yaml_file" :options="yamlOptions" allow-search placeholder="请选择配置文件" data-testid="qa-views-gray-feature-select-请选择配置文件-2" />
        </a-form-item>
        <a-form-item v-if="form.config_type === 2" label="逻辑数据源" class="mango-form-item__require mango-gray-form__full">
          <a-select v-model="form.datasource_alias" :options="datasourceAliasOptions" allow-clear allow-search placeholder="请选择逻辑数据源" data-testid="qa-views-gray-feature-select-请选择逻辑数据源" />
        </a-form-item>
        <a-form-item v-if="form.config_type === 2" label="执行SQL" class="mango-gray-form__full"><a-textarea v-model="form.enable_sql" :auto-size="{ minRows: 3, maxRows: 8 }" placeholder="请输入执行SQL" data-testid="qa-views-gray-feature-textarea-请输入执行sql" /></a-form-item>
        <a-form-item v-if="form.config_type === 2" label="恢复SQL" class="mango-gray-form__full"><a-textarea v-model="form.restore_sql" :auto-size="{ minRows: 2, maxRows: 6 }" placeholder="执行完成后用于恢复配置" data-testid="qa-views-gray-feature-textarea-执行完成后用于恢复配置" /></a-form-item>
        <a-form-item v-if="form.config_type === 3" label="执行代码" class="mango-form-item__require mango-gray-form__full"><a-textarea v-model="form.enable_code" :auto-size="{ minRows: 4, maxRows: 10 }" placeholder="必须定义 gray(context) 函数" data-testid="qa-views-gray-feature-textarea-必须定义-gray-context-函数" /></a-form-item>
        <a-form-item v-if="form.config_type === 3" label="恢复代码" class="mango-form-item__require mango-gray-form__full"><a-textarea v-model="form.restore_code" :auto-size="{ minRows: 3, maxRows: 8 }" placeholder="执行完成后用于恢复配置，必须定义 gray(context) 函数" data-testid="qa-views-gray-feature-textarea-执行完成后用于恢复配置-必须定义-gray-context-函数" /></a-form-item>
        <a-form-item label="启用状态"><a-switch v-model="form.status" :checked-value="1" :unchecked-value="0" /></a-form-item>
        <a-form-item label="说明" class="mango-gray-form__full"><a-textarea v-model="form.description" :auto-size="{ minRows: 3, maxRows: 6 }" placeholder="请输入说明" data-testid="qa-views-gray-feature-textarea-请输入说明" /></a-form-item>
      </a-form>
    </template>
  </ModalDialog>

  <BaseSidePanel
    :visible="previewDrawer.visible"
    :title="previewDrawer.title"
    :width="1000"
    cancel-button-text="关闭"
    @update:visible="(value) => (previewDrawer.visible = value)"
    @cancel="previewDrawer.visible = false"
  >
    <template #default>
      <div class="mango-gray-preview-drawer">
        <div class="mango-gray-preview-drawer__config">
          <div class="mango-gray-preview-drawer__config-header">
            <div class="mango-gray-preview-drawer__title">灰度配置</div>
            <div class="mango-gray-preview-drawer__config-actions">
              <a-button v-permission="'gray.feature:edit'" size="small" type="outline" @click="addPreviewPathConfig" data-testid="qa-views-gray-feature-button-新增路径">新增路径</a-button>
              <a-button v-permission="'gray.feature:edit'" size="small" type="primary" :loading="previewDrawer.saveLoading" @click="onPreviewConfigSave" data-testid="qa-views-gray-feature-button-保存配置">保存配置</a-button>
            </div>
          </div>
          <a-form class="mango-gray-preview-config-form" :model="previewDrawer.config" layout="horizontal">
            <a-form-item v-if="previewDrawer.record?.config_type === 1" class="mango-gray-preview-config-form__full" label="路径配置">
              <div class="mango-gray-path-config">
                <div v-for="(item, index) in previewDrawer.config.path_config" :key="index" class="mango-gray-path-config__row">
                  <a-cascader
                    v-model="item.path"
                    :options="previewDrawer.pathOptions"
                    allow-clear
                    allow-search
                    check-strictly
                    path-mode
                    placeholder="请选择路径"
                    @change="invalidateConfigPreview"
                    @clear="invalidateConfigPreview" data-testid="qa-views-gray-feature-cascader-请选择路径"
                  />
                  <a-select v-model="item.value_type" :options="grayValueTypeOptions" placeholder="值类型" @change="invalidateConfigPreview" data-testid="qa-views-gray-feature-select-值类型" />
                  <a-input v-model="item.original_value" allow-clear placeholder="原值，可选" @input="invalidateConfigPreview" @clear="invalidateConfigPreview" data-testid="qa-views-gray-feature-input-原值-可选" />
                  <a-input v-model="item.value" allow-clear placeholder="替换值，如 ${{tenant_id}}" @input="invalidateConfigPreview" @clear="invalidateConfigPreview" data-testid="qa-views-gray-feature-input-替换值-如-tenant_id" />
                  <a-button v-permission="'gray.feature:delete'" size="mini" status="danger" @click="removePreviewPathConfig(index)" data-testid="qa-views-gray-feature-button-删除">删除</a-button>
                </div>
              </div>
            </a-form-item>
          </a-form>
        </div>
        <div class="mango-gray-preview-drawer__control">
          <a-form layout="inline" :model="previewDrawer">
            <a-form-item v-if="previewNeedVariableSource" label="变量来源">
              <a-select v-model="previewDrawer.variableSource" :options="variableSourceOptions" placeholder="请选择变量来源" @change="invalidatePreview" data-testid="qa-views-gray-feature-select-请选择变量来源" />
            </a-form-item>
            <a-form-item v-if="previewNeedVariableSource" label="变量环境">
              <a-select
                v-model="previewDrawer.variableTestEnv"
                :options="environmentOptions"
                :field-names="{ value: 'key', label: 'title' }"
                allow-search
                placeholder="请选择变量环境"
                @change="invalidatePreview" data-testid="qa-views-gray-feature-select-请选择变量环境"
              />
            </a-form-item>
            <a-form-item>
              <a-button v-permission="'gray.feature:debug'" size="small" type="primary" :loading="previewDrawer.loading" @click="onPreviewGenerate" data-testid="qa-views-gray-feature-button-重新预览">重新预览</a-button>
            </a-form-item>
          </a-form>
        </div>
        <section class="mango-gray-preview-drawer__section">
          <div class="mango-gray-preview-drawer__title">原文</div>
          <CodeEditor v-model="previewDrawer.beforeText" readonly placeholder="暂无原文" :code-style="{ height: 'calc((100vh - 280px) / 2)' }" />
        </section>
        <section class="mango-gray-preview-drawer__section">
          <div class="mango-gray-preview-drawer__title">修改后</div>
          <CodeEditor v-model="previewDrawer.afterText" readonly placeholder="暂无修改内容" :code-style="{ height: 'calc((100vh - 280px) / 2)' }" />
        </section>
      </div>
    </template>
    <template #footer-buttons>
      <a-button @click="previewDrawer.visible = false" data-testid="qa-views-gray-feature-button-关闭">关闭</a-button>
      <a-button v-permission="'gray.feature:execute'" type="primary" :disabled="!previewDrawer.hasPreview" :loading="previewDrawer.executeLoading" @click="onPreviewExecute" data-testid="qa-views-gray-feature-button-执行">执行</a-button>
    </template>
  </BaseSidePanel>
</template>

<script setup lang="ts">
  import { computed, nextTick, onMounted, reactive, ref } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import TableBody from '@/components/table/TableBody.vue'
  import TableHeader from '@/components/table/TableHeader.vue'
  import TableFooter from '@/components/table/TableFooter.vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import ModalDialog from '@/components/overlays/ModalDialog.vue'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import CodeEditor from '@/components/editors/CodeEditor.vue'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import { getDataFactoryDatasourceAlias } from '@/api/data-factory'
  import { useEnum } from '@/store/modules/get-enum'
  import { usePagination, useTable } from '@/hooks/table'
  import {
    formatModulePath,
    formatProjectProductPath,
    getOptionId,
  } from '@/utils/business-format'
  import type { ModalDialogType } from '@/types/components'
  import {
    deleteGrayFeature,
    getGrayFeature,
    getGrayYamlFile,
    postGrayFeature,
    postGrayFeatureExecute,
    postGrayFeaturePreview,
    putGrayFeature,
  } from '@/api/gray'
  import {
    configTypeOptions,
    enableStatusOptions,
    grayPageConfig,
    grayValueTypeOptions,
    variableSourceOptions,
  } from './config'

  const COMMON_ENV_VALUE = '__common__'
  const table = useTable()
  const enumStore = useEnum()
  const pagination = usePagination(onSearch, () => table.tableLoading)
  const sidebarResetKey = ref(0)
  const dialogRef = ref<ModalDialogType | null>(null)
  const query = reactive<any>({})
  const form = reactive<any>({})
  const yamlList = ref<any[]>([])
  const datasourceAliasList = ref<any[]>([])
  const actionLoading = ref('')
  const previewDrawer = reactive<any>({
    visible: false,
    title: '',
    filePath: '',
    beforeText: '',
    afterText: '',
    record: null,
    action: 'enable',
    variableSource: 'api',
    variableTestEnv: COMMON_ENV_VALUE,
    config: {},
    configDirty: false,
    loading: false,
    saveLoading: false,
    executeLoading: false,
    hasPreview: false,
    pathOptions: [],
  })
  const featureColumns = computed(() => grayPageConfig.columns)
  const yamlOptions = computed(() => yamlList.value.map((item) => ({ label: yamlLabel(item), value: item.id })))
  const datasourceAliasOptions = computed(() =>
    datasourceAliasList.value.map((item) => ({
      label: `${item.name} / ${
        enumStore.data_source_type?.find((option: any) => option.key === item.db_type)?.title ||
        item.db_type
      }`,
      value: item.id,
    }))
  )
  const environmentOptions = computed(() => [
    { key: COMMON_ENV_VALUE, title: '环境通用' },
    ...(Array.isArray(enumStore.environment_type) ? enumStore.environment_type : []),
  ])
  const previewNeedVariableSource = computed(() => pathConfigHasVariable(previewDrawer.config?.path_config))

  function cleanParams(params: Record<string, any>) {
    const result: Record<string, any> = {}
    Object.entries(params).forEach(([key, value]) => {
      if (value !== '' && value !== null && value !== undefined) {
        result[key] = value
      }
    })
    return result
  }

  function requestParams() {
    return cleanParams({
      page: pagination.page,
      pageSize: pagination.pageSize,
      project_product: getOptionId(query.project_product),
      module: getOptionId(query.module),
      config_type__in: Array.isArray(query.config_type) ? query.config_type.join(',') : undefined,
      status__in: Array.isArray(query.status) ? query.status.join(',') : undefined,
      yaml_file__in: Array.isArray(query.yaml_file) ? query.yaml_file.join(',') : undefined,
      gray_code: query.gray_code,
      name: query.name,
      feature_key: query.feature_key,
    })
  }

  function yamlLabel(item: any) {
    return `${item.name} / ${formatProjectProductPath(item.project_product)}`
  }

  function isCommonEnvironment(value: any) {
    return value === null || value === undefined || value === ''
  }

  function normalizeEnvironmentValue(value: any) {
    if (value === COMMON_ENV_VALUE || isCommonEnvironment(value)) {
      return null
    }
    const numericValue = Number(value)
    return Number.isFinite(numericValue) ? numericValue : value
  }

  function defaultVariableTestEnv() {
    const options = Array.isArray(enumStore.environment_type) ? enumStore.environment_type : []
    const testOption = options.find((item: any) => {
      return [item.title, item.key, item.value].some((value) => {
        const text = String(value || '').toLowerCase()
        return text.includes('测试') || text === 'test' || text === '2'
      })
    })
    return testOption?.key ?? testOption?.value ?? COMMON_ENV_VALUE
  }

  async function loadOptions() {
    const [yamlFiles] = await Promise.all([getGrayYamlFile({})])
    yamlList.value = yamlFiles.data || []
  }

  async function loadDatasourceAliases(projectProduct?: any) {
    const projectProductId = getOptionId(projectProduct)
    datasourceAliasList.value = []
    if (!projectProductId) return
    const result = await getDataFactoryDatasourceAlias({
      project_product: projectProductId,
      status: 1,
      page: 1,
      pageSize: 500,
    })
    datasourceAliasList.value = (result.data || []).filter((item: any) =>
      [0, 1, 2].includes(Number(item.db_type))
    )
  }

  async function onSearch() {
    table.tableLoading.value = true
    try {
      const res = await getGrayFeature(requestParams())
      table.handleSuccess(res)
      pagination.setTotalSize(res.totalSize || 0)
    } finally {
      table.tableLoading.value = false
    }
  }

  function onSearchRefresh() {
    pagination.page = 1
    onSearch()
  }

  function onNavigationFilterChange({ projectProduct, module }: { projectProduct: any; module: any }) {
    query.project_product = projectProduct ?? undefined
    query.module = module ?? undefined
    onSearchRefresh()
  }

  function onSearchProjectProductChange() {
    query.module = undefined
    onSearchRefresh()
  }

  function onFormProjectProductChange(value: any) {
    form.module = undefined
    form.datasource_alias = undefined
    loadDatasourceAliases(value)
  }

  function onReset() {
    Object.keys(query).forEach((key) => {
      query[key] = ['config_type', 'status', 'yaml_file'].includes(key) ? [] : undefined
    })
    sidebarResetKey.value += 1
    onSearchRefresh()
  }

  function openDialog(data: any) {
    Object.keys(form).forEach((key) => delete form[key])
    Object.assign(form, data)
    loadDatasourceAliases(form.project_product)
    dialogRef.value?.show()
  }

  function onAdd() {
    openDialog({ config_type: 1, status: 1, default_restore: true })
  }

  function onEdit(record: any) {
    openDialog({
      ...record,
      project_product: record.project_product?.id || record.project_product,
      module: record.module?.id || record.module,
      yaml_file: record.yaml_file?.id || record.yaml_file,
      datasource_alias: record.datasource_alias?.id || record.datasource_alias,
      database: record.database?.id || record.database,
      path_config: normalizePathConfig(record.path_config),
    })
  }

  async function onSubmit() {
    try {
      if (!validateForm()) {
        return
      }
      const payload = normalizeFeaturePayload()
      form.id ? await putGrayFeature(payload) : await postGrayFeature(payload)
      Message.success('保存成功')
      dialogRef.value?.close()
      await loadOptions()
      await onSearch()
    } finally {
      dialogRef.value?.setConfirmLoading(false)
    }
  }

  function validateForm() {
    if (!form.project_product) {
      Message.warning('请选择项目/产品')
      return false
    }
    if (!form.module) {
      Message.warning('请选择模块')
      return false
    }
    if (!form.config_type) {
      Message.warning('请选择配置类型')
      return false
    }
    if (form.config_type === 1 && !form.yaml_file) {
      Message.warning('请选择配置文件')
      return false
    }
    if (form.config_type === 2 && !form.datasource_alias) {
      Message.warning('请选择逻辑数据源')
      return false
    }
    if (form.config_type === 2 && (!form.enable_sql || !form.restore_sql)) {
      Message.warning('请填写执行SQL和恢复SQL')
      return false
    }
    if (form.config_type === 3 && (!form.enable_code || !form.restore_code)) {
      Message.warning('请填写执行代码和恢复代码')
      return false
    }
    return true
  }

  function normalizeFeaturePayload() {
    const payload: any = {
      ...form,
      project_product: getOptionId(form.project_product),
      module: getOptionId(form.module),
    }
    delete payload.path_config
    if (payload.config_type === 1) {
      payload.datasource_alias = null
      payload.database = null
      payload.enable_sql = null
      payload.disable_sql = null
      payload.restore_sql = null
      payload.enable_code = null
      payload.disable_code = null
      payload.restore_code = null
    }
    if (payload.config_type === 2) {
      payload.yaml_file = null
      payload.database = null
      payload.enable_code = null
      payload.disable_code = null
      payload.restore_code = null
      payload.disable_sql = null
    }
    if (payload.config_type === 3) {
      payload.yaml_file = null
      payload.datasource_alias = null
      payload.database = null
      payload.enable_sql = null
      payload.disable_sql = null
      payload.restore_sql = null
      payload.disable_code = null
    }
    return payload
  }

  async function onModifyStatus(newValue: boolean, id: number) {
    try {
      const res = await putGrayFeature({ id, status: newValue ? 1 : 0 })
      const success = res.code === 200
      if (success) {
        Message.success(res.msg || '状态更新成功')
        await onSearch()
      }
      return success
    } catch (error) {
      return false
    }
  }

  function onDelete(record: any) {
    Modal.confirm({
      title: '删除灰度开关',
      content: `确认删除 ${record.name}？`,
      onOk: async () => {
        actionLoading.value = `delete-${record.id}`
        try {
          await deleteGrayFeature(record.id)
          await onSearch()
        } finally {
          actionLoading.value = ''
        }
      },
    })
  }

  async function onPreview(record: any) {
    previewDrawer.filePath =
      record.yaml_file?.file_path ||
      record.datasource_alias?.name ||
      record.database?.name ||
      configTypeText(record.config_type)
    refreshPreviewTitle(record, previewDrawer.filePath)
    previewDrawer.beforeText = ''
    previewDrawer.afterText = ''
    previewDrawer.record = record
    previewDrawer.config = buildPreviewConfig(record)
    previewDrawer.configDirty = false
    previewDrawer.action = 'enable'
    previewDrawer.variableSource = 'api'
    previewDrawer.variableTestEnv = defaultVariableTestEnv()
    previewDrawer.loading = false
    previewDrawer.saveLoading = false
    previewDrawer.executeLoading = false
    previewDrawer.hasPreview = false
    previewDrawer.pathOptions = []
    previewDrawer.visible = true
    await nextTick()
    await onPreviewGenerate()
  }

  function refreshPreviewTitle(record: any, filePath?: string) {
    const pathText = filePath ? ` / ${filePath}` : ''
    previewDrawer.title = `${record?.name || '-'} 预执行预览${pathText}`
  }

  function invalidatePreview() {
    previewDrawer.beforeText = ''
    previewDrawer.afterText = ''
    previewDrawer.hasPreview = false
  }

  function invalidateConfigPreview() {
    invalidatePreview()
    previewDrawer.configDirty = true
  }

  async function onPreviewGenerate() {
    const record = previewDrawer.record
    if (!record?.id) {
      Message.warning('请选择灰度开关')
      return
    }
    if (previewNeedVariableSource.value && !previewDrawer.variableSource) {
      Message.warning('请选择变量来源')
      return
    }
    previewDrawer.loading = true
    try {
      const res = await postGrayFeaturePreview(previewPayload())
      previewDrawer.filePath =
        res.data?.file_path ||
        record.yaml_file?.file_path ||
        record.datasource_alias?.name ||
        record.database?.name ||
        ''
      refreshPreviewTitle(record, previewDrawer.filePath)
      previewDrawer.pathOptions = buildYamlPathOptions(res.data?.before_snapshot)
      previewDrawer.beforeText = res.data?.before_text || JSON.stringify(res.data?.before_snapshot ?? {}, null, 2)
      previewDrawer.afterText = res.data?.after_text || JSON.stringify(res.data?.after_snapshot ?? {}, null, 2)
      previewDrawer.hasPreview = true
    } finally {
      previewDrawer.loading = false
    }
  }

  async function onPreviewExecute() {
    if (!previewDrawer.hasPreview) {
      Message.warning('请先生成预览，确认变更内容后再执行')
      return
    }
    previewDrawer.executeLoading = true
    try {
      const res = await postGrayFeatureExecute(previewPayload())
      if (res.data?.status === 1) {
        Message.success('执行成功')
      } else {
        Message.error('执行失败，请在执行记录中查看详情')
      }
      previewDrawer.visible = false
      await onSearch()
    } finally {
      previewDrawer.executeLoading = false
    }
  }

  async function onPreviewConfigSave() {
    const record = previewDrawer.record
    if (!record?.id) {
      Message.warning('请选择灰度开关')
      return
    }
    previewDrawer.saveLoading = true
    try {
      const payload = normalizePreviewFeaturePayload(record)
      await putGrayFeature(payload)
      const updatedRecord = { ...record, path_config: normalizePathConfig(previewDrawer.config.path_config) }
      previewDrawer.record = updatedRecord
      previewDrawer.config = buildPreviewConfig(updatedRecord)
      previewDrawer.configDirty = false
      Message.success('灰度配置已保存')
      await onSearch()
      await onPreviewGenerate()
    } finally {
      previewDrawer.saveLoading = false
    }
  }

  function previewPayload() {
    const record = previewDrawer.record
    return {
      feature_id: record?.id,
      target_value: '',
      action: previewDrawer.action,
      variable_source: previewNeedVariableSource.value ? previewDrawer.variableSource : '',
      variable_test_env: previewNeedVariableSource.value ? normalizeEnvironmentValue(previewDrawer.variableTestEnv) : null,
      path_config: normalizePathConfig(previewDrawer.config?.path_config),
    }
  }

  function buildPreviewConfig(record: any) {
    return {
      path_config: normalizePathConfig(record?.path_config).map((item) => ({ ...item, path: pathToCascaderValue(item.path) })),
    }
  }

  function normalizePreviewFeaturePayload(record: any) {
    return {
      ...record,
      project_product: record.project_product?.id || record.project_product,
      module: record.module?.id || record.module,
      yaml_file: record.yaml_file?.id || record.yaml_file,
      datasource_alias: record.datasource_alias?.id || record.datasource_alias,
      database: record.database?.id || record.database,
      path_config: normalizePathConfig(previewDrawer.config.path_config),
    }
  }

  function addPreviewPathConfig() {
    if (!Array.isArray(previewDrawer.config.path_config)) {
      previewDrawer.config.path_config = []
    }
    previewDrawer.config.path_config.push({ path: [], value_type: 'number', original_value: '', value: '' })
    invalidateConfigPreview()
  }

  function removePreviewPathConfig(index: number) {
    previewDrawer.config.path_config.splice(index, 1)
    invalidateConfigPreview()
  }

  function normalizePathConfig(value: any) {
    if (!Array.isArray(value)) {
      return []
    }
    return value
      .map((item) => ({
        path: normalizePathValue(item?.path),
        value_type: item?.value_type || 'number',
        original_value: item?.original_value === undefined || item?.original_value === null ? '' : String(item.original_value).trim(),
        value: item?.value,
      }))
      .filter((item) => item.path)
  }

  function normalizePathValue(value: any) {
    if (Array.isArray(value)) {
      return String(value[value.length - 1] || '').trim()
    }
    return String(value || '').trim()
  }

  function pathToCascaderValue(path: string) {
    const parts = String(path || '').split('.').filter(Boolean)
    return parts.map((_, index) => parts.slice(0, index + 1).join('.'))
  }

  function pathConfigHasVariable(pathConfig: any) {
    return normalizePathConfig(pathConfig).some((item) => {
      return [item.original_value, item.value].some((value) => typeof value === 'string' && /\$\{\{[^}]+}}|\$\{[^}]+}/.test(value))
    })
  }

  function buildYamlPathOptions(snapshot: any) {
    return buildYamlPathTree(snapshot, '')
  }

  function buildYamlPathTree(value: any, prefix: string): any[] {
    if (value === null || value === undefined || Array.isArray(value)) {
      return []
    }
    if (typeof value === 'object') {
      return Object.entries(value).map(([key, child]) => {
        const path = prefix ? `${prefix}.${key}` : key
        const children = buildYamlPathTree(child, path)
        return { label: key, value: path, children: children.length ? children : undefined }
      })
    }
    return []
  }

  function configTypeText(configType: number | string) {
    return configTypeOptions.find((item) => Number(item.value) === Number(configType))?.label || '-'
  }

  function configTypeColor(configType: number | string) {
    return enumStore.colors?.[Number(configType)] || 'gray'
  }

  onMounted(async () => {
    await loadOptions()
    await onSearch()
  })
</script>

<style scoped lang="less">
  .mango-gray-toolbar {
    display: flex;
    justify-content: flex-end;
    margin-bottom: 12px;
  }

  .mango-gray-form {
    :deep(.arco-form-item) {
      margin-bottom: 12px;
    }
  }

  .mango-gray-preview-drawer {
    display: flex;
    flex-direction: column;
    gap: 12px;
    min-height: 0;
  }

  .mango-gray-preview-drawer__config {
    padding: 10px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    background: var(--m-surface);
  }

  .mango-gray-preview-config-form {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    column-gap: 14px;
    row-gap: 8px;

    :deep(.arco-form-item) {
      min-width: 0;
      margin-bottom: 0;
    }

    :deep(.arco-form-item-label-col) {
      flex: 0 0 76px !important;
      max-width: 76px !important;
      min-width: 76px !important;
      padding-right: 10px;
    }

    :deep(.arco-form-item-wrapper-col) {
      flex: 1 1 0 !important;
      max-width: none !important;
      min-width: 0;
    }

    :deep(.arco-form-item-label) {
      justify-content: flex-end;
      width: 100%;
    }

    :deep(.mango-gray-preview-config-form__full) {
      grid-column: 1 / -1;
    }
  }

  .mango-gray-path-config {
    display: flex;
    flex-direction: column;
    gap: 8px;
    width: 100%;
  }

  .mango-gray-path-config__row {
    display: grid;
    grid-template-columns: 200px 88px minmax(150px, 1fr) minmax(180px, 1.2fr) auto;
    gap: 8px;
    align-items: center;
  }

  .mango-gray-preview-drawer__control {
    padding: 10px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    background: var(--m-surface-soft);

    :deep(.arco-form-item) {
      margin-bottom: 0;
    }

    :deep(.arco-select) {
      width: 150px;
    }
  }

  .mango-gray-preview-drawer__section {
    min-height: 0;
  }

  .mango-gray-preview-drawer__title {
    margin-bottom: 6px;
    color: var(--m-text);
    font-size: 14px;
    font-weight: 600;
    line-height: 22px;
  }

  .mango-gray-preview-drawer__config-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 6px;

    .mango-gray-preview-drawer__title {
      margin-bottom: 0;
    }
  }

  .mango-gray-preview-drawer__config-actions {
    display: flex;
    flex: 0 0 auto;
    gap: 8px;
  }
</style>
