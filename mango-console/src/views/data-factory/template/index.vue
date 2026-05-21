<template>
  <TableBody>
    <template #header>
      <TableHeader title="数据工厂 / 状态模板" @search="doRefresh" @reset-search="onResetSearch">
        <template #search-content>
          <a-form :model="{}" layout="inline" @keyup.enter="doRefresh">
            <a-form-item v-for="item of templateConditionItems" :key="item.key" :label="item.label">
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
                  style="width: 150px"
                  value-key="key"
                  @change="onSearchProjectChange(item.value)"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'module'">
                <a-select
                  v-model="item.value"
                  :field-names="enumFieldNames"
                  :options="productModule.data"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  style="width: 150px"
                  value-key="key"
                  @change="onSearchModuleChange"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'entity'">
                <a-select
                  v-model="item.value"
                  :field-names="{ value: 'id', label: 'name' }"
                  :options="entityOptions"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  style="width: 150px"
                  @change="doRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'cleanup_strategy'">
                <a-select
                  v-model="item.value"
                  :field-names="enumFieldNames"
                  :options="enumStore.data_factory_cleanup_strategy"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  style="width: 140px"
                  value-key="key"
                  @change="doRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'status'">
                <a-select
                  v-model="item.value"
                  :field-names="enumFieldNames"
                  :options="statusOptions"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  style="width: 120px"
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
              <a-button size="small" type="primary" @click="openTemplate()"
                >新增模板</a-button
              ></a-space
            >
          </div>
        </template>
      </a-tabs>
      <a-table
        :columns="templateTableColumns"
        :data="table.dataList"
        :loading="table.tableLoading.value"
        :pagination="false"
        :row-key="'id'"
      >
        <template #columns>
          <a-table-column
            v-for="item of templateTableColumns"
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
            <template v-else-if="item.key === 'module'" #cell="{ record }">
              {{ record?.module?.superior_module ? record?.module?.superior_module + '/' : ''
              }}{{ record?.module?.name }}
            </template>
            <template v-else-if="item.key === 'entity'" #cell="{ record }">
              {{ record.entity?.name || record.entity }}
            </template>
            <template v-else-if="item.key === 'cleanup_strategy'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record.cleanup_strategy]" size="small">
                {{ enumTitle(enumStore.data_factory_cleanup_strategy, record.cleanup_strategy) }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'is_default'" #cell="{ record }">
              <a-tag :color="record.is_default ? 'green' : 'gray'" size="small">
                {{ record.is_default ? '默认' : '普通' }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'status'" #cell="{ record }">
              <a-switch
                :beforeChange="(newValue) => switchTemplateStatus(newValue, record.id)"
                :default-checked="record.status === 1"
              />
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <a-space>
                <a-button
                  :loading="actionLoading === `preview-${record.id}`"
                  size="mini"
                  type="text"
                  class="custom-mini-btn"
                  @click="previewRun(record)"
                  >预览数据</a-button
                >
                <a-button
                  :loading="actionLoading === `fields-${record.id}`"
                  size="mini"
                  type="text"
                  class="custom-mini-btn"
                  @click="openFieldConfig(record)"
                  >字段配置</a-button
                >
                <a-dropdown trigger="hover">
                  <a-button size="mini" type="text" class="custom-mini-btn">···</a-button>
                  <template #content>
                    <a-doption @click="openTemplate(record)">
                      <a-button size="mini" type="text" class="custom-mini-btn">编辑</a-button>
                    </a-doption>
                    <a-doption @click="syncTemplateFields(record)">
                      <a-button
                        :loading="actionLoading === `sync-${record.id}`"
                        size="mini"
                        type="text"
                        class="custom-mini-btn"
                        >同步实体规则</a-button
                      >
                    </a-doption>
                    <a-doption @click="copyTemplate(record)">
                      <a-button
                        :loading="actionLoading === `copy-${record.id}`"
                        size="mini"
                        type="text"
                        class="custom-mini-btn"
                        >复制</a-button
                      >
                    </a-doption>
                    <a-doption @click="removeTemplate(record)">
                      <a-button
                        :loading="actionLoading === `delete-${record.id}`"
                        size="mini"
                        status="danger"
                        type="text"
                        class="custom-mini-btn"
                        >删除</a-button
                      >
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

  <a-modal
    v-model:visible="templateVisible"
    :on-before-ok="saveTemplate"
    :ok-loading="templateSaving"
    :title="templateForm.id ? '编辑模板' : '新增模板'"
    width="720px"
  >
    <a-form :model="templateForm" layout="vertical">
      <a-grid :cols="2" :col-gap="16">
        <a-grid-item>
          <a-form-item label="产品" required
            ><a-cascader
              v-model="templateForm.project_product"
              :options="projectInfo.projectProduct"
              allow-search
              allow-clear
              @change="onTemplateProjectChange"
          /></a-form-item>
        </a-grid-item>
        <a-grid-item>
          <a-form-item label="模块" required
            ><a-select
              v-model="templateForm.module"
              :options="productModule.data"
              :field-names="enumFieldNames"
              allow-search
              allow-clear
              @change="onTemplateModuleChange"
          /></a-form-item>
        </a-grid-item>
        <a-grid-item>
          <a-form-item label="实体" required
            ><a-select
              v-model="templateForm.entity"
              :options="entityOptions"
              :field-names="{ value: 'id', label: 'name' }"
              allow-search
          /></a-form-item>
        </a-grid-item>
        <a-grid-item
          ><a-form-item label="模板名称" required
            ><a-input v-model="templateForm.name" /></a-form-item
        ></a-grid-item>
        <a-grid-item>
          <a-form-item label="清理策略"
            ><a-select
              v-model="templateForm.cleanup_strategy"
              :options="enumStore.data_factory_cleanup_strategy"
              :field-names="enumFieldNames"
          /></a-form-item>
        </a-grid-item>
        <a-grid-item>
          <a-form-item label="默认模板">
            <a-switch v-model="templateForm.is_default" />
          </a-form-item>
        </a-grid-item>
        <a-grid-item>
          <a-form-item label="描述"
            ><a-textarea v-model="templateForm.description" :auto-size="{ minRows: 1, maxRows: 4 }"
          /></a-form-item>
        </a-grid-item>
      </a-grid>
    </a-form>
  </a-modal>

  <a-modal
    v-model:visible="fieldConfigVisible"
    :on-before-ok="saveFieldConfig"
    :ok-loading="fieldConfigSaving"
    :title="`${fieldConfigForm.name || ''} 字段配置`"
    width="960px"
  >
    <a-space direction="vertical" style="width: 100%">
      <a-space>
        <a-button
          :loading="fieldConfigSyncLoading"
          size="small"
          type="primary"
          @click="syncCurrentFieldConfig"
          >同步实体规则</a-button
        >
        <a-button :loading="fieldConfigPreviewLoading" size="small" @click="previewFieldConfig"
          >预览</a-button
        >
      </a-space>
      <a-spin :loading="fieldOverrideLoading" style="width: 100%">
        <TemplateFieldConfigEditor
          v-if="fieldConfigForm.entity"
          :fields="fieldOverrideRows"
          v-model:field-overrides="fieldConfigForm.field_overrides"
          v-model:output-config="fieldConfigForm.output_config"
          :generator-options="enumStore.data_factory_generator_type"
          :dependency-template-options="dependencyTemplateOptions"
          :load-dependency-template-options="loadDependencyTemplateOptions"
        />
      </a-spin>
    </a-space>
  </a-modal>

  <a-modal v-model:visible="debugVisible" title="调试结果" width="760px" :footer="false">
    <a-space direction="vertical" style="width: 100%">
      <a-alert v-if="debugResult.execution_no" type="success"
        >执行编号：{{ debugResult.execution_no }}</a-alert
      >
      <a-textarea
        :model-value="JSON.stringify(debugResult.context || debugResult, null, 2)"
        :auto-size="{ minRows: 12, maxRows: 20 }"
        readonly
      />
      <a-button
        v-if="debugResult.execution_id"
        :loading="debugCleanupLoading"
        status="danger"
        @click="debugCleanup"
        >清理本次调试数据</a-button
      >
    </a-space>
  </a-modal>

  <a-modal v-model:visible="previewVisible" title="生成数据预览" width="920px">
    <a-space class="template-preview-content" direction="vertical">
      <a-alert v-if="previewResult.missing_fields?.length" type="warning">
        当前还有 {{ previewResult.missing_fields.length }} 个字段需要配置，建议补齐后再调试运行。
      </a-alert>
      <a-alert v-else-if="previewResult.payload" type="success"
        >当前模板字段已能生成 payload，可以继续调试运行。</a-alert
      >
      <a-textarea
        v-if="Object.keys(previewResult.output || {}).length"
        :model-value="JSON.stringify(previewResult.output, null, 2)"
        :auto-size="{ minRows: 3, maxRows: 8 }"
        readonly
      />
      <a-table
        v-if="flattenDependencyTree(previewResult.dependency_tree).length"
        :columns="dependencyTreeColumns"
        :data="flattenDependencyTree(previewResult.dependency_tree)"
        :pagination="false"
        :row-key="'path'"
        :scroll="{ x: 900, y: 220 }"
        size="small"
      >
        <template #columns>
          <a-table-column
            v-for="item of dependencyTreeColumns"
            :key="item.key"
            :data-index="item.key"
            :ellipsis="item.ellipsis"
            :tooltip="item.tooltip"
            :title="item.title"
            :width="item.width"
          >
            <template v-if="item.key === 'node'" #cell="{ record }">
              <span :style="{ paddingLeft: `${record.level * 18}px` }">{{
                record.template_name
              }}</span>
              <a-tag
                v-if="record.level === 0"
                size="small"
                color="arcoblue"
                style="margin-left: 8px"
                >根节点</a-tag
              >
              <a-tag v-else-if="record.reused" size="small" color="green" style="margin-left: 8px"
                >复用</a-tag
              >
              <a-tag v-else size="small" color="orange" style="margin-left: 8px">创建</a-tag>
            </template>
            <template v-else-if="item.key === 'action'" #cell="{ record }">
              <a-tag :color="getDependencyActionColor(record.action)" size="small">{{
                getDependencyActionText(record.action)
              }}</a-tag>
            </template>
          </a-table-column>
        </template>
      </a-table>
      <TemplateFieldConfigEditor
        v-if="previewResult.fields?.length"
        :fields="previewResult.fields || []"
        :field-overrides="{}"
        :output-config="[]"
        :generator-options="enumStore.data_factory_generator_type"
        :preview-fields="previewResult.fields || []"
        readonly
        :show-config="false"
        :show-output="false"
        show-preview
      />
    </a-space>
    <template #footer>
      <a-space class="template-preview-footer">
        <a-button @click="previewVisible = false">关闭</a-button>
        <a-button
          type="primary"
          :disabled="!previewResult.can_debug_run"
          :loading="previewDebugLoading"
          @click="debugRunFromPreview"
        >
          调试运行
        </a-button>
      </a-space>
    </template>
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
    postDataFactoryTemplateSyncFields,
    putDataFactoryTemplate,
    putDataFactoryTemplateStatus,
  } from '@/api/data-factory'
  import { usePagination, useTable, useTableColumn } from '@/hooks/table'
  import { useEnum } from '@/store/modules/get-enum'
  import { useProject } from '@/store/modules/get-project'
  import { useProductModule } from '@/store/modules/project_module'
  import useUserStore from '@/store/modules/user'
  import { getFormItems } from '@/utils/datacleaning'
  import TemplateFieldConfigEditor from '@/components/DataFactory/TemplateFieldConfigEditor.vue'
  import type {
    DataFactoryFieldOverrides,
    DataFactoryFieldRule,
    DataFactoryOutputConfig,
  } from '@/types/data-factory'
  import { Message, Modal } from '@arco-design/web-vue'
  import { onMounted, reactive, ref, watch } from 'vue'
  import { templateConditionItems, templateTableColumns } from './config'

  const table = useTable()
  const pagination = usePagination(doRefresh)
  const enumStore = useEnum()
  const projectInfo = useProject()
  const productModule = useProductModule()
  const userStore = useUserStore()
  const enumFieldNames = { value: 'key', label: 'title' }
  const entityOptions = ref<any[]>([])
  const dependencyTemplateOptions = ref<Record<string, any[]>>({})
  const templateVisible = ref(false)
  const debugVisible = ref(false)
  const previewVisible = ref(false)
  const previewTemplate = ref<any>(null)
  const currentPreviewTemplate = ref<any>(null)
  const currentPreviewOverrides = ref<any>({})
  const debugResult = ref<any>({})
  const previewResult = ref<any>({})
  const templateForm = reactive<any>({})
  const fieldConfigForm = reactive<any>({})
  const templateSaving = ref(false)
  const fieldConfigSaving = ref(false)
  const fieldConfigVisible = ref(false)
  const fieldConfigSyncLoading = ref(false)
  const fieldConfigPreviewLoading = ref(false)
  const fieldOverrideLoading = ref(false)
  const fieldOverrideRows = ref<DataFactoryFieldRule[]>([])
  const resettingTemplateForm = ref(false)
  const debugCleanupLoading = ref(false)
  const previewDebugLoading = ref(false)
  const actionLoading = ref('')
  const statusOptions = [
    { key: 1, title: '启用' },
    { key: 0, title: '禁用' },
  ]
  const dependencyTreeColumns = useTableColumn([
    { title: '依赖节点', key: 'node', dataIndex: 'node', width: 260 },
    { title: '来源字段', key: 'field', dataIndex: 'field', width: 140 },
    { title: '取值字段', key: 'target_field', dataIndex: 'target_field', width: 100 },
    { title: '策略', key: 'strategy', dataIndex: 'strategy', width: 140 },
    { title: '动作', key: 'action', dataIndex: 'action', width: 100 },
    { title: '说明', key: 'message', dataIndex: 'message' },
  ])

  function enumTitle(options: any[] = [], value: any) {
    return options.find((it) => it.key === value)?.title || value
  }

  function getOptionId(value: any) {
    return value?.id ?? value
  }

  function getSearchItem(key: string) {
    return templateConditionItems.find((item) => item.key === key)
  }

  function onSearchProjectChange(value: any) {
    const moduleItem = getSearchItem('module')
    const entityItem = getSearchItem('entity')
    if (moduleItem) {
      moduleItem.value = ''
    }
    if (entityItem) {
      entityItem.value = ''
    }
    productModule.getProjectModule(getOptionId(value))
    loadEntities({
      project_product: getOptionId(value),
    })
    doRefresh()
  }

  function onSearchModuleChange() {
    const projectProduct = getSearchItem('project_product')?.value
    const module = getSearchItem('module')?.value
    const entityItem = getSearchItem('entity')
    if (entityItem) {
      entityItem.value = ''
    }
    loadEntities({
      project_product: getOptionId(projectProduct),
      module: getOptionId(module),
    })
    doRefresh()
  }

  function resetTemplateForm(record?: any) {
    resettingTemplateForm.value = true
    Object.keys(templateForm).forEach((key) => delete templateForm[key])
    Object.assign(templateForm, {
      id: record?.id,
      project_product: record?.project_product?.id || record?.project_product || null,
      module: record?.module?.id || record?.module || null,
      entity: record?.entity?.id || record?.entity || null,
      name: record?.name || '',
      description: record?.description || '',
      field_overrides: (record?.field_overrides || {}) as DataFactoryFieldOverrides,
      output_config: (record?.output_config || []) as DataFactoryOutputConfig,
      cleanup_strategy: record?.cleanup_strategy || 2,
      is_default: record?.is_default || false,
      status: record?.status || 1,
    })
    resettingTemplateForm.value = false
  }

  function resetFieldConfigForm(record?: any) {
    Object.keys(fieldConfigForm).forEach((key) => delete fieldConfigForm[key])
    Object.assign(fieldConfigForm, {
      id: record?.id,
      project_product: record?.project_product?.id || record?.project_product || null,
      module: record?.module?.id || record?.module || null,
      entity: record?.entity?.id || record?.entity || null,
      name: record?.name || '',
      field_overrides: (record?.field_overrides || {}) as DataFactoryFieldOverrides,
      output_config: (record?.output_config || []) as DataFactoryOutputConfig,
    })
  }

  function doRefresh() {
    table.tableLoading.value = true
    const query = getFormItems(templateConditionItems)
    getDataFactoryTemplate({ ...query, page: pagination.page, pageSize: pagination.pageSize }).then(
      (res) => {
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
      }
    )
  }

  function onResetSearch() {
    templateConditionItems.forEach((it) => {
      it.value = ''
    })
    doRefresh()
  }

  function loadEntities(params: any = {}) {
    const query: any = { page: 1, pageSize: 9999 }
    const projectProduct = params.project_product ?? templateForm.project_product
    const module = params.module ?? templateForm.module
    if (projectProduct) {
      query.project_product = getOptionId(projectProduct)
    }
    if (module) {
      query.module = getOptionId(module)
    }
    getDataFactoryEntity(query).then((res) => {
      entityOptions.value = res.data || []
    })
  }

  function onTemplateProjectChange(value: any) {
    templateForm.module = null
    templateForm.entity = null
    templateForm.field_overrides = {}
    templateForm.output_config = []
    fieldOverrideRows.value = []
    entityOptions.value = []
    productModule.getProjectModule(getOptionId(value))
  }

  function onTemplateModuleChange() {
    templateForm.entity = null
    templateForm.field_overrides = {}
    templateForm.output_config = []
    fieldOverrideRows.value = []
    loadEntities()
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
        preloadDependencyTemplateOptions()
      })
      .finally(() => {
        fieldOverrideLoading.value = false
      })
  }

  function loadDependencyTemplateOptions(row: DataFactoryFieldRule) {
    const dependencyEntityId = row.generator_config?.dependency_entity_id
    const projectProduct = getOptionId(fieldConfigForm.project_product || templateForm.project_product)
    if (!dependencyEntityId || !projectProduct) {
      return
    }
    const cacheKey = String(dependencyEntityId)
    if (dependencyTemplateOptions.value[cacheKey]) {
      return
    }
    getDataFactoryTemplate({
      project_product: projectProduct,
      entity: dependencyEntityId,
      page: 1,
      pageSize: 9999,
    }).then((res) => {
      dependencyTemplateOptions.value = {
        ...dependencyTemplateOptions.value,
        [cacheKey]: (res.data || []).map((template: any) => ({
          label: template.name,
          value: template.id,
        })),
      }
    })
  }

  function preloadDependencyTemplateOptions() {
    fieldOverrideRows.value
      .filter((row: any) => row.generator_config?.dependency_entity_id)
      .forEach((row) => loadDependencyTemplateOptions(row))
  }

  function openTemplate(record?: any) {
    resetTemplateForm(record)
    if (templateForm.project_product) {
      productModule.getProjectModule(getOptionId(templateForm.project_product))
    }
    loadEntities()
    templateVisible.value = true
  }

  function openFieldConfig(record: any) {
    actionLoading.value = `fields-${record.id}`
    resetFieldConfigForm(record)
    loadTemplateFields(getOptionId(fieldConfigForm.entity))
      .then(() => {
        fieldConfigVisible.value = true
      })
      .finally(() => {
        actionLoading.value = ''
      })
  }

  async function saveTemplate() {
    if (
      !templateForm.project_product ||
      !templateForm.module ||
      !templateForm.entity ||
      !templateForm.name
    ) {
      Message.error('请先填写产品、模块、实体和模板名称')
      return false
    }

    const payload = {
      ...templateForm,
      field_overrides: templateForm.field_overrides || {},
      output_config: templateForm.output_config || [],
    }
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

  async function saveFieldConfig() {
    if (!fieldConfigForm.id) {
      Message.error('状态模板不存在，请刷新后重试')
      return false
    }
    fieldConfigSaving.value = true
    try {
      const res = await putDataFactoryTemplate({
        id: fieldConfigForm.id,
        field_overrides: fieldConfigForm.field_overrides || {},
        output_config: fieldConfigForm.output_config || [],
      })
      Message.success(res.msg)
      doRefresh()
      return true
    } catch (error) {
      return false
    } finally {
      fieldConfigSaving.value = false
    }
  }

  function syncTemplateFields(record: any) {
    actionLoading.value = `sync-${record.id}`
    postDataFactoryTemplateSyncFields({ id: record.id })
      .then((res) => {
        Message.success(res.msg)
        doRefresh()
      })
      .finally(() => {
        actionLoading.value = ''
      })
  }

  function syncCurrentFieldConfig() {
    if (!fieldConfigForm.id) {
      Message.error('状态模板不存在，请刷新后重试')
      return
    }
    fieldConfigSyncLoading.value = true
    postDataFactoryTemplateSyncFields({ id: fieldConfigForm.id })
      .then((res) => {
        fieldConfigForm.field_overrides = res.data?.field_overrides || {}
        Message.success(res.msg)
        loadTemplateFields(getOptionId(fieldConfigForm.entity))
        doRefresh()
      })
      .finally(() => {
        fieldConfigSyncLoading.value = false
      })
  }

  function previewFieldConfig() {
    if (!ensureSelectedEnvironment()) {
      return
    }
    if (!fieldConfigForm.id) {
      Message.error('状态模板不存在，请刷新后重试')
      return
    }
    fieldConfigPreviewLoading.value = true
    postDataFactoryTemplatePreview({
      template_id: fieldConfigForm.id,
      overrides: fieldConfigForm.field_overrides || {},
      output_config: fieldConfigForm.output_config || [],
      test_env: userStore.selected_environment,
    })
      .then((res) => {
        previewResult.value = res.data || {}
        currentPreviewTemplate.value = { ...fieldConfigForm }
        currentPreviewOverrides.value = fieldConfigForm.field_overrides || {}
        previewVisible.value = true
      })
      .finally(() => {
        fieldConfigPreviewLoading.value = false
      })
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

  function switchTemplateStatus(newValue: boolean, id: number) {
    return new Promise<boolean>((resolve, reject) => {
      putDataFactoryTemplateStatus({ id, status: newValue ? 1 : 0 })
        .then((res) => {
          Message.success(res.msg)
          doRefresh()
          resolve(res.code === 200)
        })
        .catch(reject)
    })
  }

  function previewRun(record: any) {
    if (!ensureSelectedEnvironment()) {
      return
    }
    if (!record?.id) {
      Message.error('状态模板不存在，请刷新后重试')
      return
    }
    actionLoading.value = `preview-${record.id}`
    previewTemplate.value = record
    confirmPreviewRun().finally(() => {
      actionLoading.value = ''
    })
  }

  function confirmPreviewRun() {
    if (!ensureSelectedEnvironment()) {
      return Promise.resolve()
    }
    if (previewTemplate.value?.id) {
      return postDataFactoryTemplatePreview({
        template_id: previewTemplate.value.id,
        test_env: userStore.selected_environment,
      }).then((res) => {
        previewResult.value = res.data || {}
        currentPreviewTemplate.value = previewTemplate.value
        currentPreviewOverrides.value = {}
        previewTemplate.value = null
        previewVisible.value = true
      })
    }
    return Promise.resolve()
  }

  function debugRunFromPreview() {
    if (!ensureSelectedEnvironment() || !currentPreviewTemplate.value) {
      return
    }
    previewDebugLoading.value = true
    postDataFactoryTemplateDebugRun({
      template_id: currentPreviewTemplate.value.id,
      overrides: currentPreviewOverrides.value || {},
      test_env: userStore.selected_environment,
    })
      .then((res) => {
        debugResult.value = res.data || {}
        previewVisible.value = false
        debugVisible.value = true
      })
      .finally(() => {
        previewDebugLoading.value = false
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
    productModule.getProjectModule()
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
      templateForm.output_config = []
      loadTemplateFields(entityId)
    }
  )
</script>

<style scoped>
  .template-preview-content {
    max-height: 70vh;
    overflow-y: auto;
    padding-right: 8px;
    width: 100%;
  }

  .template-preview-footer {
    justify-content: flex-end;
    width: 100%;
  }
</style>
