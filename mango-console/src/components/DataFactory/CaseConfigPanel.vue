<template>
  <a-space direction="vertical" fill>
    <div v-if="showAddButton" class="mango-data-factory-case-config__toolbar">
      <a-button size="small" type="primary" @click="open()">增加</a-button>
    </div>
    <a-table
      :bordered="false"
      :columns="columns"
      :data="caseConfigList"
      :loading="loading"
      :pagination="false"
      :row-key="'id'"
      :draggable="{ type: 'handle', width: 40 }"
      size="small"
      @change="handleChange"
    >
      <template #columns>
        <a-table-column
          v-for="item of columns"
          :key="item.key"
          :data-index="item.key"
          :ellipsis="item.ellipsis"
          :tooltip="item.tooltip"
          :title="item.title"
          :width="item.width"
          :align="item.align"
        >
          <template v-if="item.key === 'template'" #cell="{ record }">
            {{ record.template?.name }}
          </template>
          <template v-else-if="item.key === 'entity'" #cell="{ record }">
            {{ record.template?.entity?.name }}
          </template>
          <template v-else-if="item.key === 'table_name'" #cell="{ record }">
            {{ record.template?.entity?.table_name }}
          </template>
          <template v-else-if="item.key === 'cleanup_strategy'" #cell="{ record }">
            <a-tag :color="enumStore.colors[record.cleanup_strategy]" size="small">
              {{
                enumTitle(
                  enumStore.data_factory_cleanup_strategy,
                  record.cleanup_strategy || record.template?.cleanup_strategy
                )
              }}
            </a-tag>
          </template>
          <template v-else-if="item.key === 'status'" #cell="{ record }">
            <a-switch
              :beforeChange="(newValue) => switchStatus(newValue, record)"
              :default-checked="record.status === 1"
            />
          </template>
          <template v-else-if="item.key === 'actions'" #cell="{ record }">
            <a-space>
              <a-button size="mini" type="text" @click="open(record)">编辑</a-button>
              <a-button
                size="mini"
                type="text"
                :loading="previewLoading === record.id"
                @click="preview(record)"
              >
                预览
              </a-button>
              <a-button
                size="mini"
                status="danger"
                type="text"
                :loading="deleteLoading === record.id"
                @click="deleteConfig(record)"
                >删除</a-button
              >
            </a-space>
          </template>
        </a-table-column>
      </template>
    </a-table>
  </a-space>

  <a-modal
    v-model:visible="visible"
    :title="form.id ? '编辑数据工厂配置' : '新增数据工厂配置'"
    width="1120px"
    :ok-loading="saving"
    :on-before-ok="save"
  >
    <a-form :model="form" layout="vertical">
      <a-grid :cols="2" :col-gap="16">
        <a-grid-item>
          <a-form-item label="项目/产品" required>
            <a-cascader
              v-model="form.project_product"
              :options="projectInfo.projectProduct"
              allow-clear
              allow-search
              value-key="key"
              @change="onProjectProductChange"
            />
          </a-form-item>
        </a-grid-item>
        <a-grid-item>
          <a-form-item label="模块" required>
            <a-select
              v-model="form.module"
              :field-names="enumFieldNames"
              :options="productModule.data"
              allow-clear
              allow-search
              value-key="key"
              @change="onModuleChange"
            />
          </a-form-item>
        </a-grid-item>
        <a-grid-item>
          <a-form-item label="场景模板" required>
            <a-select
              v-model="form.template"
              :options="templateList"
              :field-names="{ value: 'id', label: 'name' }"
              :disabled="!form.project_product || !form.module"
              :loading="templateLoading"
              allow-clear
              allow-search
              placeholder="请先选择项目/产品和模块"
              @change="onTemplateChange"
            />
          </a-form-item>
        </a-grid-item>
        <a-grid-item>
          <a-form-item label="数据名称" required>
            <a-input v-model="form.name" placeholder="例如：订单数据；用例中按“订单数据.id”取值" />
          </a-form-item>
        </a-grid-item>
        <a-grid-item>
          <a-form-item label="清理策略">
            <a-select
              v-model="form.cleanup_strategy"
              :options="cleanupStrategyOptions"
              :field-names="{ value: 'key', label: 'title' }"
              allow-clear
              placeholder="默认使用模板清理策略"
            />
          </a-form-item>
        </a-grid-item>
        <a-grid-item>
          <a-form-item label="状态">
            <a-switch
              :model-value="form.status === 1"
              @change="(value) => (form.status = value ? 1 : 0)"
            />
          </a-form-item>
        </a-grid-item>
      </a-grid>
      <a-form-item label="字段覆盖">
        <a-spin :loading="fieldLoading" class="full-width">
          <a-space v-if="form.template" direction="vertical" fill>
            <section class="mango-section-card mango-case-config-field-card">
              <div class="mango-section-title">
                <div>
                  <h2>主模板字段</h2>
                  <p>配置主模板字段生成规则和输出字段</p>
                </div>
              </div>
              <TemplateFieldConfigEditor
                :field-overrides="mainCaseOverrides"
                :output-config="templateOutputConfig"
                :fields="fieldRows"
                :generator-options="enumStore.data_factory_generator_type"
                :dependency-template-options="dependencyTemplateOptions"
                :load-dependency-template-options="loadDependencyTemplateOptions"
                :loading="fieldLoading"
                :show-output="false"
                @update:field-overrides="updateMainCaseOverrides"
                @update:output-config="updateTemplateOutputConfig"
              />
            </section>
            <section
              v-for="item in selectedTemplateItems"
              :key="item.id"
              class="mango-section-card mango-case-config-field-card"
            >
              <div class="mango-section-title">
                <div>
                  <h2>关联模板</h2>
                  <p>{{ item.name || item.child_template_detail?.name || item.child_template }}</p>
                </div>
              </div>
              <TemplateFieldConfigEditor
                :field-overrides="getItemCaseOverrides(item)"
                :output-config="[]"
                :fields="itemFieldsMap[String(item.id)] || []"
                :generator-options="enumStore.data_factory_generator_type"
                :dependency-template-options="dependencyTemplateOptions"
                :load-dependency-template-options="loadDependencyTemplateOptions"
                :loading="fieldLoading"
                :show-output="false"
                @update:field-overrides="(value) => updateItemCaseOverrides(item, value)"
              />
            </section>
          </a-space>
          <div v-else class="mango-empty-state mango-field-empty">请先选择场景模板</div>
        </a-spin>
      </a-form-item>
    </a-form>
    <template #footer>
      <a-space>
        <a-button @click="visible = false">取消</a-button>
        <a-button :loading="previewLoading === 'form'" @click="preview()">预览</a-button>
        <a-button type="primary" :loading="saving" @click="save()">确定</a-button>
      </a-space>
    </template>
  </a-modal>

  <a-modal v-model:visible="previewVisible" title="生成数据预览" width="920px">
    <a-space class="mango-data-factory-case-preview-content" direction="vertical">
      <a-alert v-if="previewResult.missing_fields?.length" type="warning">
        当前还有 {{ previewResult.missing_fields.length }} 个字段需要配置，建议补齐后再运行用例。
      </a-alert>
      <a-alert v-else-if="previewResult.payload" type="success"
        >当前场景模板字段已能生成 payload。</a-alert
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
        :loading="previewLoading === 'form'"
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
              <span
                class="mango-dependency-node-name"
                :style="{ '--dependency-indent': `${record.level * 18}px` }"
                >{{ record.template_name }}</span
              >
              <a-tag
                v-if="record.level === 0"
                size="small"
                color="arcoblue"
                class="mango-dependency-node-tag"
                >根节点</a-tag
              >
              <a-tag
                v-else-if="record.reused"
                size="small"
                color="green"
                class="mango-dependency-node-tag"
                >复用</a-tag
              >
              <a-tag v-else size="small" color="orange" class="mango-dependency-node-tag">创建</a-tag>
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
        :loading="previewLoading === 'form'"
        readonly
        :show-config="false"
        :show-output="false"
        show-preview
      />
    </a-space>
    <template #footer>
      <a-space class="mango-data-factory-case-preview-footer">
        <a-button @click="previewVisible = false">关闭</a-button>
      </a-space>
    </template>
  </a-modal>
</template>

<script lang="ts" setup>
  import { computed, onMounted, reactive, ref, watch } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import { useTableColumn } from '@/hooks/table'
  import useUserStore from '@/store/modules/user'
  import { useEnum } from '@/store/modules/get-enum'
  import { useProject } from '@/store/modules/get-project'
  import { useProductModule } from '@/store/modules/project_module'
  import TemplateFieldConfigEditor from '@/components/DataFactory/TemplateFieldConfigEditor.vue'
  import {
    deleteDataFactoryCaseConfig,
    getDataFactoryCaseConfig,
    getDataFactoryField,
    getDataFactoryTemplate,
    postDataFactoryCaseConfig,
    postDataFactoryCaseConfigPreview,
    putDataFactoryCaseConfig,
    putDataFactoryCaseConfigSort,
  } from '@/api/data-factory'
  import type {
    DataFactoryFieldOverrides,
    DataFactoryFieldRule,
    DataFactoryOutputConfig,
  } from '@/types/data-factory'

  const props = withDefaults(
    defineProps<{
      caseId?: string | number | null
      projectProductId?: string | number | null
      sourceType: number
      showAddButton?: boolean
    }>(),
    {
      caseId: null,
      projectProductId: null,
      showAddButton: false,
    }
  )

  const enumStore = useEnum()
  const userStore = useUserStore()
  const projectInfo = useProject()
  const productModule = useProductModule()
  const enumFieldNames = { value: 'key', label: 'title' }

  const columns = [
    {
      title: '数据名称',
      key: 'name',
      dataIndex: 'name',
      width: 200,
      align: 'left',
      ellipsis: true,
      tooltip: true,
    },
    {
      title: '场景模板',
      key: 'template',
      dataIndex: 'template',
      width: 200,
      align: 'left',
      ellipsis: true,
      tooltip: true,
    },
    {
      title: '基础实体',
      key: 'entity',
      dataIndex: 'entity',
      width: 100,
      align: 'left',
      ellipsis: true,
      tooltip: true,
    },
    {
      title: '表名',
      key: 'table_name',
      dataIndex: 'table_name',
      width: 100,
      align: 'left',
      ellipsis: true,
      tooltip: true,
    },
    { title: '清理策略', key: 'cleanup_strategy', dataIndex: 'cleanup_strategy', width: 120 },
    { title: '状态', key: 'status', dataIndex: 'status', width: 90, align: 'center' },
    { title: '操作', key: 'actions', dataIndex: 'actions', width: 170, align: 'center' },
  ]

  const caseConfigList = ref<any[]>([])
  const templateList = ref<any[]>([])
  const fieldRows = ref<DataFactoryFieldRule[]>([])
  const itemFieldsMap = ref<Record<string, DataFactoryFieldRule[]>>({})
  const dependencyTemplateOptions = ref<Record<string, any[]>>({})
  const templateOutputConfig = ref<DataFactoryOutputConfig>([])
  const loading = ref(false)
  const templateLoading = ref(false)
  const fieldLoading = ref(false)
  const saving = ref(false)
  const visible = ref(false)
  const previewVisible = ref(false)
  const previewLoading = ref<any>(null)
  const deleteLoading = ref<number | null>(null)
  const previewResult = ref<any>({})

  const form = reactive<{
    id: number | null
    source_type: number
    source_id: string | number | null
    project_product: string | number | null
    module: string | number | null
    template: number | null
    name: string
    sort: number
    field_overrides: DataFactoryFieldOverrides
    cleanup_strategy: number | null
    status: number
    stage: number
  }>({
    id: null,
    source_type: props.sourceType,
    source_id: props.caseId,
    project_product: props.projectProductId,
    module: null,
    template: null,
    name: '',
    sort: 0,
    field_overrides: {},
    cleanup_strategy: null,
    status: 1,
    stage: 1,
  })

  const cleanupStrategyOptions = computed(() => [
    { key: null, title: '使用模板默认策略' },
    ...(enumStore.data_factory_cleanup_strategy || []),
  ])
  const currentTemplate = computed(() =>
    templateList.value.find((item) => String(item.id) === String(form.template))
  )
  const selectedTemplateItems = computed(() => currentTemplate.value?.items || [])
  const isSceneOverrideShape = computed(
    () =>
      Object.prototype.hasOwnProperty.call(form.field_overrides || {}, '__main__') ||
      Object.prototype.hasOwnProperty.call(form.field_overrides || {}, '__items__')
  )
  const mainCaseOverrides = computed(() =>
    isSceneOverrideShape.value ? form.field_overrides?.__main__ || {} : form.field_overrides || {}
  )
  const dependencyTreeColumns = useTableColumn([
    { title: '依赖节点', key: 'node', dataIndex: 'node', width: 260 },
    { title: '来源字段', key: 'field', dataIndex: 'field', width: 140 },
    { title: '取值字段', key: 'target_field', dataIndex: 'target_field', width: 100 },
    { title: '策略', key: 'strategy', dataIndex: 'strategy', width: 140 },
    { title: '动作', key: 'action', dataIndex: 'action', width: 100 },
    { title: '说明', key: 'message', dataIndex: 'message' },
  ])

  function enumTitle(options: any[] = [], value: any) {
    return options.find((item) => item.key === value)?.title || value || '-'
  }

  function getOptionId(value: any) {
    return value?.id ?? value
  }

  function refresh() {
    if (!props.caseId || !props.sourceType) {
      caseConfigList.value = []
      return
    }
    loading.value = true
    getDataFactoryCaseConfig({ source_type: props.sourceType, source_id: props.caseId })
      .then((res) => {
        caseConfigList.value = res.data || []
      })
      .finally(() => {
        loading.value = false
      })
  }

  function handleChange(_data: any[]) {
    caseConfigList.value = _data.map((item, index) => ({
      ...item,
      sort: index,
    }))
    putDataFactoryCaseConfigSort({
      source_type: props.sourceType,
      case_sort_list: caseConfigList.value.map((item, index) => ({
        id: item.id,
        sort: index,
      })),
    })
      .then((res) => {
        Message.success(res.msg)
      })
      .catch(() => {
        refresh()
      })
  }

  function loadTemplates() {
    const projectProduct = getOptionId(form.project_product || props.projectProductId)
    const module = getOptionId(form.module)
    if (!projectProduct || !module) {
      templateList.value = []
      return Promise.resolve()
    }
    const query: any = {
      page: 1,
      pageSize: 9999,
      project_product: projectProduct,
      module,
    }
    templateLoading.value = true
    return getDataFactoryTemplate(query)
      .then((res) => {
        templateList.value = res.data || []
      })
      .finally(() => {
        templateLoading.value = false
      })
  }

  function resetForm(record: any = null) {
    const template = record?.template || {}
    form.id = record?.id || null
    form.source_type = props.sourceType
    form.source_id = props.caseId
    form.project_product =
      template?.project_product?.id || template?.project_product || props.projectProductId || null
    form.module = template?.module?.id || template?.module || null
    form.template = template?.id || record?.template || null
    form.name = record?.name || ''
    form.sort = record?.sort ?? caseConfigList.value.length
    form.field_overrides = record?.field_overrides || {}
    form.cleanup_strategy = record?.cleanup_strategy ?? null
    form.status = record?.status ?? 1
    form.stage = record?.stage || 1
    templateOutputConfig.value = record?.template?.output_config || []
    fieldRows.value = []
    itemFieldsMap.value = {}
  }

  function open(record: any = null) {
    resetForm(record)
    visible.value = true
    if (form.project_product) {
      productModule.getProjectModule(getOptionId(form.project_product))
    }
    if (form.project_product && form.module) {
      loadTemplates().then(() => {
        if (form.template) {
          loadFields()
        }
      })
    } else {
      templateList.value = []
    }
  }

  function onProjectProductChange() {
    form.module = null
    form.template = null
    form.field_overrides = {}
    templateOutputConfig.value = []
    templateList.value = []
    fieldRows.value = []
    if (form.project_product) {
      productModule.getProjectModule(getOptionId(form.project_product))
    }
  }

  function onModuleChange() {
    form.template = null
    form.field_overrides = {}
    templateOutputConfig.value = []
    fieldRows.value = []
    loadTemplates()
  }

  function onTemplateChange() {
    const template = templateList.value.find((item) => item.id === form.template)
    if (!form.name && template?.name) {
      form.name = template.name
    }
    templateOutputConfig.value = template?.output_config || []
    form.field_overrides = normalizeSceneOverrides(template?.field_overrides || {})
    loadFields()
  }

  function loadFields() {
    const template = templateList.value.find((item) => item.id === form.template)
    const entityId = template?.entity?.id || template?.entity
    if (!entityId) {
      fieldRows.value = []
      return
    }
    fieldLoading.value = true
    getDataFactoryField({ entity: entityId })
      .then((res) => {
        fieldRows.value = res.data || []
        preloadDependencyTemplateOptions()
        loadItemFields()
      })
      .finally(() => {
        fieldLoading.value = false
      })
  }

  function loadDependencyTemplateOptions(row: DataFactoryFieldRule) {
    const dependencyEntityId = row.generator_config?.dependency_entity_id
    const projectProduct = getOptionId(form.project_product || props.projectProductId)
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
    fieldRows.value
      .filter((row: any) => row.generator_config?.dependency_entity_id)
      .forEach((row) => loadDependencyTemplateOptions(row))
  }

  function normalizeSceneOverrides(overrides: any) {
    if (
      Object.prototype.hasOwnProperty.call(overrides || {}, '__main__') ||
      Object.prototype.hasOwnProperty.call(overrides || {}, '__items__')
    ) {
      return {
        __main__: overrides.__main__ || {},
        __items__: overrides.__items__ || {},
      }
    }
    return {
      __main__: overrides || {},
      __items__: {},
    }
  }

  function updateMainCaseOverrides(value: DataFactoryFieldOverrides) {
    form.field_overrides = {
      __main__: value,
      __items__: form.field_overrides?.__items__ || {},
    }
  }

  function updateTemplateOutputConfig(value: DataFactoryOutputConfig) {
    templateOutputConfig.value = value
  }

  function getItemCaseKey(item: any) {
    return String(item.id || item.name || item.child_template)
  }

  function getItemCaseOverrides(item: any) {
    return form.field_overrides?.__items__?.[getItemCaseKey(item)] || {}
  }

  function updateItemCaseOverrides(item: any, value: DataFactoryFieldOverrides) {
    form.field_overrides = {
      __main__: mainCaseOverrides.value,
      __items__: {
        ...(form.field_overrides?.__items__ || {}),
        [getItemCaseKey(item)]: value,
      },
    }
  }

  function loadItemFields() {
    const tasks = selectedTemplateItems.value.map((item: any) => {
      const entityId = item.child_template_detail?.entity?.id || item.child_template_detail?.entity
      if (!entityId) {
        return Promise.resolve()
      }
      return getDataFactoryField({ entity: entityId }).then((res) => {
        itemFieldsMap.value = {
          ...itemFieldsMap.value,
          [String(item.id)]: res.data || [],
        }
      })
    })
    return Promise.all(tasks)
  }

  async function save() {
    if (!form.template) {
      Message.error('请选择场景模板')
      return false
    }
    if (!form.name) {
      Message.error('请填写数据名称')
      return false
    }
    if (!props.caseId) {
      Message.error('用例ID不能为空')
      return false
    }
    saving.value = true
    const payload = {
      id: form.id,
      source_type: props.sourceType,
      source_id: props.caseId,
      template: form.template,
      name: form.name,
      sort: form.sort,
      field_overrides: form.field_overrides,
      cleanup_strategy: (form.cleanup_strategy as any) === '' ? null : form.cleanup_strategy,
      status: form.status,
      stage: form.stage,
    }
    try {
      const res = payload.id
        ? await putDataFactoryCaseConfig(payload)
        : await postDataFactoryCaseConfig(payload)
      Message.success(res.msg)
      visible.value = false
      refresh()
      return true
    } catch (error) {
      return false
    } finally {
      saving.value = false
    }
  }

  function switchStatus(newValue: boolean, record: any) {
    return new Promise<boolean>((resolve, reject) => {
      putDataFactoryCaseConfig({
        id: record.id,
        source_type: props.sourceType,
        source_id: props.caseId,
        template: record.template?.id || record.template,
        name: record.name,
        sort: record.sort,
        field_overrides: record.field_overrides || {},
        cleanup_strategy: record.cleanup_strategy ?? null,
        status: newValue ? 1 : 0,
        stage: record.stage || 1,
      })
        .then((res) => {
          Message.success(res.msg)
          refresh()
          resolve(res.code === 200)
        })
        .catch(reject)
    })
  }

  function deleteConfig(record: any) {
    Modal.confirm({
      title: '提示',
      content: '确定要删除这个数据工厂配置吗？',
      cancelText: '取消',
      okText: '删除',
      onBeforeOk: () => {
        deleteLoading.value = record.id
        return deleteDataFactoryCaseConfig(record.id)
          .then((res) => {
            Message.success(res.msg)
            refresh()
          })
          .finally(() => {
            deleteLoading.value = null
          })
      },
    })
  }

  function preview(record: any = null) {
    const target = record || form
    const templateId = target?.template?.id || target?.template
    if (!templateId) {
      Message.error('请选择场景模板')
      return
    }
    if (userStore.selected_environment == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    previewLoading.value = record ? target.id : 'form'
    postDataFactoryCaseConfigPreview({
      source_type: props.sourceType,
      source_id: props.caseId,
      template_id: templateId,
      field_overrides: target.field_overrides || {},
      test_env: userStore.selected_environment,
    })
      .then((res) => {
        previewResult.value = res.data
        previewVisible.value = true
      })
      .finally(() => {
        previewLoading.value = null
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

  watch(
    () => [props.caseId, props.sourceType],
    () => {
      refresh()
    }
  )

  watch(
    () => props.projectProductId,
    () => {
      if (!visible.value) {
        return
      }
      form.project_product = props.projectProductId || null
      onProjectProductChange()
    }
  )

  onMounted(() => {
    projectInfo.projectProductName()
    productModule.getProjectModule()
    refresh()
  })

  defineExpose({
    open,
    refresh,
  })
</script>

<style scoped>
  .mango-data-factory-case-config__toolbar {
    display: flex;
    justify-content: flex-end;
  }

  .full-width {
    width: 100%;
  }

  .mango-dependency-node-name {
    padding-left: var(--dependency-indent);
  }

  .mango-dependency-node-tag {
    margin-left: 8px;
  }

  .mango-case-config-field-card {
    box-shadow: none;
  }

  .mango-field-empty {
    min-height: 96px;
  }

  .mango-data-factory-case-preview-content {
    max-height: 70vh;
    overflow-y: auto;
    padding-right: 8px;
    width: 100%;
  }

  .mango-data-factory-case-preview-footer {
    justify-content: flex-end;
    width: 100%;
  }
</style>
