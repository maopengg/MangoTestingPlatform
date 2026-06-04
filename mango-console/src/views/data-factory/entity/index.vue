<template>
  <TableBody>
    <template #header>
      <TableHeader title="数据工厂 / 工厂实体" @search="doRefresh" @reset-search="onResetSearch">
        <template #search-content>
          <a-form :model="{}" layout="inline" @keyup.enter="doRefresh">
            <a-form-item v-for="item of entityConditionItems" :key="item.key" :label="item.label">
              <template v-if="item.type === 'input'">
                <a-input
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  allow-clear
                  @blur="doRefresh"
                  @clear="doRefresh"
                />
              </template>
              <template v-else-if="item.type === 'cascader' && item.key === 'project_product'">
                <ProjectProductSelect
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  @change="onSearchProjectChange(item.value)"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'module'">
                <ProductModuleSelect
                  v-model="item.value"
                  :project-product-id="getSearchItemValue('project_product')"
                  :placeholder="item.placeholder"
                  :auto-clear="false"
                  @change="doRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'datasource_alias'">
                <a-select
                  v-model="item.value"
                  :field-names="{ value: 'id', label: 'name' }"
                  :options="datasourceAliasOptions"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
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
              <a-button size="small" type="primary" @click="openEntity()">新增实体</a-button>
              <a-button size="small" @click="openBatchGenerate">批量生成</a-button>
            </a-space></div
          >
        </template>
      </a-tabs>
      <a-table
        :columns="entityTableColumns"
        :data="table.dataList"
        :loading="table.tableLoading.value"
        :pagination="false"
        :row-key="'id'"
      >
        <template #columns>
          <a-table-column
            v-for="item of entityTableColumns"
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
              {{ formatProjectProductPath(record?.project_product) }}
            </template>
            <template v-else-if="item.key === 'module'" #cell="{ record }">
              {{ formatModulePath(record?.module) }}
            </template>
            <template v-else-if="item.key === 'datasource_alias'" #cell="{ record }">
              {{ record?.datasource_alias?.name || '-' }}
            </template>
            <template v-else-if="item.key === 'create_type'" #cell="{ record }">
              <a-tag color="arcoblue" size="small">
                {{ enumTitle(enumStore.data_factory_operation_type, record.create_type || 2) }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'status'" #cell="{ record }">
              <a-switch
                :beforeChange="(newValue) => switchEntityStatus(newValue, record.id)"
                :default-checked="record.status === 1"
              />
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <MangoTableActions
                :actions="[
                  { label: '编辑', onClick: () => openEntity(record) },
                  {
                    label: '字段规则',
                    loading: actionLoading === `fields-${record.id}`,
                    onClick: () => openFields(record),
                  },
                  {
                    label: '删除',
                    danger: true,
                    loading: actionLoading === `delete-${record.id}`,
                    onClick: () => removeEntity(record),
                  },
                ]"
              />
            </template>
          </a-table-column>
        </template>
      </a-table>
    </template>

    <template #footer>
      <TableFooter :pagination="pagination" />
    </template>
  </TableBody>

  <a-drawer v-model:visible="batchVisible" title="批量生成工厂实体" width="50%">
    <a-form :model="batchForm" layout="vertical">
      <a-grid :cols="2" :col-gap="16">
        <a-grid-item>
          <a-form-item label="产品" required>
            <ProjectProductSelect
              v-model="batchForm.project_product"
              @change="onBatchProjectChange"
            />
          </a-form-item>
        </a-grid-item>
        <a-grid-item>
          <a-form-item label="模块" required>
            <ProductModuleSelect
              v-model="batchForm.module"
              :project-product-id="batchForm.project_product"
              :auto-clear="false"
            />
          </a-form-item>
        </a-grid-item>
        <a-grid-item>
          <a-form-item label="逻辑数据源" required>
            <a-select
              v-model="batchForm.datasource_alias"
              :field-names="{ value: 'id', label: 'name' }"
              :options="datasourceAliasOptions"
              allow-clear
              allow-search
            />
          </a-form-item>
        </a-grid-item>
      </a-grid>
      <a-space class="entity-toolbar">
        <a-switch
          v-model="batchForm.sync_fields"
          checked-text="同步字段规则"
          unchecked-text="不同步字段"
        />
        <a-switch
          v-model="batchForm.skip_exists"
          checked-text="跳过已存在"
          unchecked-text="已存在报错"
        />
        <a-button :loading="batchLoading" type="primary" @click="loadBatchTables">加载表</a-button>
        <a-button :loading="batchGenerating" status="success" @click="batchGenerateEntities"
          >生成</a-button
        >
      </a-space>
    </a-form>
    <a-alert class="entity-alert" type="info">
      当前使用顶部全局测试环境读取表结构。实体名称默认使用表注释，没有表注释时使用表名。
    </a-alert>
    <a-table
      :columns="batchEntityTableColumns"
      :data="batchRows"
      :loading="batchLoading || batchGenerating"
      :pagination="false"
      :row-key="'table_name'"
      :row-selection="batchRowSelection"
      :scroll="{ x: 900, y: 520 }"
      @selection-change="onBatchSelectionChange"
    >
      <template #columns>
        <a-table-column
          v-for="item of batchEntityTableColumns"
          :key="item.key"
          :align="item.align"
          :data-index="item.key"
          :ellipsis="item.ellipsis"
          :tooltip="item.tooltip"
          :title="item.title"
          :width="item.width"
        >
          <template v-if="item.key === 'name'" #cell="{ record }">
            <a-input v-model="record.name" :disabled="record.disabled" />
          </template>
          <template v-else-if="item.key === 'status'" #cell="{ record }">
            <a-tag :color="getBatchStatusColor(record.status)">{{
              getBatchStatusText(record.status)
            }}</a-tag>
          </template>
        </a-table-column>
      </template>
    </a-table>
    <template #footer>
      <a-space>
        <a-button @click="batchVisible = false">关闭</a-button>
        <a-button :loading="batchLoading" @click="loadBatchTables">重新加载</a-button>
        <a-button
          :loading="batchGenerating"
          status="success"
          type="primary"
          @click="batchGenerateEntities"
        >
          确认生成
        </a-button>
      </a-space>
    </template>
  </a-drawer>

  <a-modal
    v-model:visible="entityVisible"
    :on-before-ok="saveEntity"
    :ok-loading="entitySaving"
    :title="entityForm.id ? '编辑实体' : '新增实体'"
    width="760px"
  >
    <a-form :model="entityForm" layout="vertical">
      <a-grid :cols="2" :col-gap="16">
        <a-grid-item>
          <a-form-item label="产品" required>
            <ProjectProductSelect
              v-model="entityForm.project_product"
              @change="onEntityProjectChange"
            />
          </a-form-item>
        </a-grid-item>
        <a-grid-item>
          <a-form-item label="模块" required>
            <ProductModuleSelect
              v-model="entityForm.module"
              :project-product-id="entityForm.project_product"
              :auto-clear="false"
            />
          </a-form-item>
        </a-grid-item>
        <a-grid-item>
          <a-form-item label="逻辑数据源" required>
            <a-select
              v-model="entityForm.datasource_alias"
              :field-names="{ value: 'id', label: 'name' }"
              :options="datasourceAliasOptions"
              allow-clear
              allow-search
              @change="onEntityDatasourceChange"
            />
          </a-form-item>
        </a-grid-item>
        <a-grid-item>
          <a-form-item label="表名" required>
            <a-input-group class="entity-table-select-group">
              <a-select
                v-model="entityForm.table_name"
                :loading="entityTableLoading"
                :options="entityTableOptions"
                allow-clear
                allow-search
                placeholder="选择逻辑源和环境后自动读取表"
                class="entity-table-select"
                @change="onEntityTableChange"
              />
              <a-button
                :loading="entityTableRefreshLoading"
                class="entity-table-refresh"
                @click="refreshEntityTables"
                >清理缓存重试</a-button
              >
            </a-input-group>
          </a-form-item>
        </a-grid-item>
        <a-grid-item
          ><a-form-item label="实体名称" required><a-input v-model="entityForm.name" /></a-form-item
        ></a-grid-item>
        <a-grid-item
          ><a-form-item label="主键字段"><a-input v-model="entityForm.primary_key" /></a-form-item
        ></a-grid-item>
        <a-grid-item
          ><a-form-item label="唯一字段"><a-input v-model="entityForm.unique_key" /></a-form-item
        ></a-grid-item>
        <a-grid-item>
          <a-form-item label="创建方式">
            <a-select
              v-model="entityForm.create_type"
              :field-names="enumFieldNames"
              :options="enumStore.data_factory_operation_type"
              disabled
            />
          </a-form-item>
        </a-grid-item>
        <a-grid-item
          ><a-form-item label="清理顺序"
            ><a-input-number v-model="entityForm.cleanup_order" class="full-width" /></a-form-item
        ></a-grid-item>
      </a-grid>
      <a-form-item label="同步字段规则">
        <a-switch v-model="syncFieldsAfterSave" checked-text="保存后同步" unchecked-text="不同步" />
      </a-form-item>
      <a-form-item label="描述"><a-textarea v-model="entityForm.description" /></a-form-item>
    </a-form>
  </a-modal>

  <a-modal
    v-model:visible="fieldVisible"
    :on-before-ok="saveFields"
    :ok-loading="fieldSaving"
    :title="`${currentEntity?.name || ''} 字段规则`"
    width="1180px"
  >
    <a-space class="entity-toolbar">
      <a-tag color="arcoblue">当前表：{{ currentEntity?.table_name || '-' }}</a-tag>
      <a-button :loading="fieldSyncLoading" type="primary" @click="syncCurrentEntityFields"
        >同步当前表字段</a-button
      >
      <a-button :loading="fieldPreviewLoading" @click="previewFieldValues">生成实际值</a-button>
      <a-switch v-model="replaceFields" checked-text="替换" unchecked-text="追加" />
    </a-space>
    <a-table
      :columns="fieldRuleColumns"
      :data="fieldRows"
      :loading="fieldSyncLoading || fieldPreviewLoading"
      :pagination="false"
      :scroll="{ x: 1600, y: 460 }"
    >
      <template #columns>
        <a-table-column
          v-for="item of fieldRuleColumns"
          :key="item.key"
          :align="item.align"
          :data-index="item.key"
          :fixed="item.fixed"
          :ellipsis="item.ellipsis"
          :tooltip="item.tooltip"
          :title="item.title"
          :width="item.width"
        >
          <template v-if="item.key === 'label'" #cell="{ record }">
            <a-input v-model="record.label" />
          </template>
          <template v-else-if="item.key === 'db_type'" #cell="{ record }">
            <a-tooltip :content="record.db_type || '-'">
              <span class="field-rule-db-type">{{ record.db_type || '-' }}</span>
            </a-tooltip>
          </template>
          <template v-else-if="item.key === 'nullable'" #cell="{ record }">
            <a-tag :color="enumStore.colors[record.nullable]" size="small">
              {{ record.nullable ? '可空' : '必填' }}
            </a-tag>
          </template>
          <template v-else-if="item.key === 'primary_key'" #cell="{ record }">
            <a-tag :color="enumStore.colors[record.primary_key]" size="small">
              {{ record.primary_key ? '主键' : '普通' }}
            </a-tag>
          </template>
          <template v-else-if="item.key === 'autoincrement'" #cell="{ record }">
            <a-tag :color="enumStore.colors[record.autoincrement]" size="small">
              {{ record.autoincrement ? '自增' : '非自增' }}
            </a-tag>
          </template>
          <template v-else-if="item.key === 'platform_type'" #cell="{ record }">
            <a-tag :color="enumStore.colors[record.platform_type]" size="small">
              {{ record.platform_type }}
            </a-tag>
          </template>
          <template v-else-if="item.key === 'generator_type'" #cell="{ record }">
            <a-select
              v-model="record.generator_type"
              :options="dataFactoryGeneratorOptions"
              :field-names="enumFieldNames"
            />
          </template>
          <template v-else-if="item.key === 'generator_config'" #cell="{ record }">
            <a-space
              v-if="record.generator_type === GENERATOR_TYPE_DEPENDENCY_FIELD"
              direction="vertical"
              fill
            >
              <a-cascader
                :model-value="getDependencyCascaderValue(record)"
                :options="dependencyCascaderOptions"
                :load-more="loadDependencyCascaderMore"
                allow-clear
                allow-search
                path-mode
                placeholder="请选择模块/实体/字段"
                @change="(value) => changeDependencyCascader(record, value)"
              />
            </a-space>
            <a-space
              v-else-if="record.generator_type === GENERATOR_TYPE_ENUM"
              direction="vertical"
              fill
            >
              <a-select
                v-model="record.generator_config.value"
                :options="getEnumSelectOptions(record)"
                allow-clear
                placeholder="请选择默认枚举值"
                @change="refreshEnumConfigValue(record)"
              />
              <a-button size="mini" type="text" @click="openEnumEditor(record)">
                配置枚举（{{ getEnumOptionRows(record).length }}项）
              </a-button>
            </a-space>
            <a-input
              v-else
              v-model="record.generator_config_value"
              :disabled="isReadonlyGeneratorConfig(record)"
              :placeholder="getGeneratorConfigPlaceholder(record)"
            />
          </template>
          <template v-else-if="item.key === 'preview_value'" #cell="{ record }">
            <a-tooltip v-if="record.preview_message" :content="record.preview_message">
              <a-tag :color="record.preview_valid ? 'green' : 'red'">{{
                formatPreviewValue(record.preview_value)
              }}</a-tag>
            </a-tooltip>
            <span v-else>{{ formatPreviewValue(record.preview_value) }}</span>
          </template>
          <template v-else-if="item.key === 'sort'" #cell="{ record }">
            <a-input-number v-model="record.sort" />
          </template>
        </a-table-column>
      </template>
    </a-table>
  </a-modal>

  <a-modal
    v-model:visible="enumEditorVisible"
    :on-before-ok="saveEnumOptions"
    :title="`${currentEnumRow?.name || ''} 枚举配置`"
    width="620px"
  >
    <a-space direction="vertical" fill>
      <div class="enum-editor-tip">
        枚举值会按字段平台类型转换后保存。比如 integer 字段中输入 1，会保存为数字 1。
      </div>
      <a-grid
        v-for="(option, index) in enumOptionRows"
        :key="index"
        class="enum-option-row"
        :cols="24"
        :col-gap="8"
        align="center"
      >
        <a-grid-item :span="3">
          <span class="enum-option-label">显示文案</span>
        </a-grid-item>
        <a-grid-item :span="7">
          <a-input v-model="option.label" />
        </a-grid-item>
        <a-grid-item :span="3">
          <span class="enum-option-label">入库值</span>
        </a-grid-item>
        <a-grid-item :span="7">
          <a-input v-model="option.value" />
        </a-grid-item>
        <a-grid-item :span="4">
          <a-button size="mini" status="danger" type="text" @click="removeEnumOption(index)">
            删除
          </a-button>
        </a-grid-item>
      </a-grid>
      <a-button type="dashed" @click="addEnumOption">新增枚举项</a-button>
    </a-space>
  </a-modal>
</template>

<script lang="ts" setup>
  import {
    deleteDataFactoryEntity,
    getDataFactoryDatasourceAlias,
    getDataFactoryEntity,
    getDataFactoryField,
    postDataFactoryDiscoverTable,
    postDataFactoryDiscoverTables,
    postDataFactoryEntity,
    postDataFactoryEntityBatchGenerate,
    postDataFactoryFieldBatchSave,
    postDataFactoryFieldPreviewValues,
    putDataFactoryEntity,
    putDataFactoryEntityStatus,
  } from '@/api/data-factory'
  import { usePagination, useTable } from '@/hooks/table'
  import { useEnum } from '@/store/modules/get-enum'
  import { useProductModule } from '@/store/modules/project_module'
  import useUserStore from '@/store/modules/user'
  import { getFormItems } from '@/utils/datacleaning'
  import { Message, Modal } from '@arco-design/web-vue'
  import { computed, onMounted, reactive, ref } from 'vue'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import { formatModulePath, formatProjectProductPath, getItemValue } from '@/utils/business-format'
  import {
    batchEntityTableColumns,
    entityConditionItems,
    entityTableColumns,
    fieldRuleColumns,
  } from './config'

  const table = useTable()
  const pagination = usePagination(doRefresh)
  const enumStore = useEnum()
  const productModule = useProductModule()
  const userStore = useUserStore()
  const enumFieldNames = { value: 'key', label: 'title' }
  const datasourceAliasOptions = ref<any[]>([])
  const dependencyCascaderOptions = ref<any[]>([])
  const entityTableOptions = ref<any[]>([])
  const entityDiscoveredColumns = ref<any[]>([])
  const entityTableLoading = ref(false)
  const entityTableRefreshLoading = ref(false)
  const syncFieldsAfterSave = ref(true)
  const replaceFields = ref(true)
  const entityVisible = ref(false)
  const fieldVisible = ref(false)
  const batchVisible = ref(false)
  const batchLoading = ref(false)
  const batchGenerating = ref(false)
  const fieldPreviewLoading = ref(false)
  const entitySaving = ref(false)
  const fieldSaving = ref(false)
  const fieldSyncLoading = ref(false)
  const actionLoading = ref('')
  const currentEntity = ref<any>(null)
  const fieldRows = ref<any[]>([])
  const batchRows = ref<any[]>([])
  const batchSelectedKeys = ref<any[]>([])
  const entityForm = reactive<any>({})
  const batchForm = reactive<any>({
    project_product: null,
    module: null,
    datasource_alias: null,
    sync_fields: true,
    skip_exists: true,
  })
  const batchRowSelection = computed(() => ({
    selectedRowKeys: batchSelectedKeys.value,
    showCheckedAll: true,
    getCheckboxProps: (record: any) => ({ disabled: record.disabled }),
  }))
  const GENERATOR_TYPE_SKIP = 0
  const GENERATOR_TYPE_FIXED = 1
  const GENERATOR_TYPE_RANDOM_STRING = 2
  const GENERATOR_TYPE_RANDOM_INTEGER = 3
  const GENERATOR_TYPE_RANDOM_DECIMAL = 4
  const GENERATOR_TYPE_NOW = 5
  const GENERATOR_TYPE_RELATIVE_TIME = 6
  const GENERATOR_TYPE_UUID = 7
  const GENERATOR_TYPE_ENUM = 9
  const GENERATOR_TYPE_DEPENDENCY_FIELD = 11
  const GENERATOR_TYPE_FUNCTION = 13
  const REMOVED_GENERATOR_TYPES = [8, 10, 12]
  const GENERATOR_TYPE_ORDER = [
    GENERATOR_TYPE_SKIP,
    GENERATOR_TYPE_FIXED,
    GENERATOR_TYPE_FUNCTION,
    GENERATOR_TYPE_RANDOM_STRING,
    GENERATOR_TYPE_RANDOM_INTEGER,
    GENERATOR_TYPE_RANDOM_DECIMAL,
    GENERATOR_TYPE_NOW,
    GENERATOR_TYPE_RELATIVE_TIME,
    GENERATOR_TYPE_UUID,
    GENERATOR_TYPE_ENUM,
    GENERATOR_TYPE_DEPENDENCY_FIELD,
  ]
  const statusOptions = [
    { key: 1, title: '启用' },
    { key: 0, title: '禁用' },
  ]
  const enumEditorVisible = ref(false)
  const currentEnumRow = ref<any>(null)
  const enumOptionRows = ref<any[]>([])
  const dataFactoryGeneratorOptions = computed(() =>
    (enumStore.data_factory_generator_type || [])
      .filter((item: any) => !REMOVED_GENERATOR_TYPES.includes(Number(item.key)))
      .map((item: any) => ({
        ...item,
        title: getGeneratorTypeTitle(item),
      }))
      .sort(
        (left: any, right: any) =>
          getGeneratorTypeOrder(left.key) - getGeneratorTypeOrder(right.key)
      )
  )

  function getGeneratorTypeOrder(value: any) {
    const index = GENERATOR_TYPE_ORDER.indexOf(Number(value))
    return index === -1 ? GENERATOR_TYPE_ORDER.length + Number(value) : index
  }

  function getOptionId(value: any) {
    if (Array.isArray(value)) {
      return value[value.length - 1] ?? null
    }
    return value?.id ?? value
  }

  function enumTitle(options: any[] = [], value: any) {
    return options.find((item: any) => Number(item.key) === Number(value))?.title || value
  }

  function getSearchItem(key: string) {
    return entityConditionItems.find((item) => item.key === key)
  }

  function getSearchItemValue(key: string) {
    return getItemValue(entityConditionItems, key)
  }

  function onSearchProjectChange(value: any) {
    const moduleItem = getSearchItem('module')
    if (moduleItem) {
      moduleItem.value = ''
    }
    const datasourceAliasItem = getSearchItem('datasource_alias')
    if (datasourceAliasItem) {
      datasourceAliasItem.value = ''
    }
    loadDatasourceAliases(value)
    doRefresh()
  }

  function onEntityProjectChange(value: any) {
    entityForm.module = null
    entityForm.datasource_alias = null
    entityForm.table_name = ''
    entityDiscoveredColumns.value = []
    entityTableOptions.value = []
    loadDatasourceAliases(value)
  }

  function onBatchProjectChange(value: any) {
    batchForm.module = null
    batchForm.datasource_alias = null
    batchRows.value = []
    batchSelectedKeys.value = []
    loadDatasourceAliases(value)
  }

  function getGeneratorTypeTitle(option: any) {
    const titleMap: Record<number, string> = {
      [GENERATOR_TYPE_RANDOM_STRING]: '随机字符串（长度8）',
      [GENERATOR_TYPE_RANDOM_INTEGER]: '随机整数（1-100）',
      [GENERATOR_TYPE_RANDOM_DECIMAL]: '随机小数（1-100，2位）',
    }
    return titleMap[Number(option.key)] || option.title
  }

  function resetEntityForm(record?: any) {
    Object.keys(entityForm).forEach((key) => delete entityForm[key])
    Object.assign(entityForm, {
      id: record?.id,
      project_product: record?.project_product?.id || record?.project_product || null,
      module: record?.module?.id || record?.module || null,
      datasource_alias: record?.datasource_alias?.id || record?.datasource_alias || null,
      name: record?.name || '',
      description: record?.description || '',
      table_name: record?.table_name || '',
      primary_key: record?.primary_key || 'id',
      unique_key: record?.unique_key || '',
      create_type: 2,
      delete_type: record?.delete_type || 2,
      cleanup_order: record?.cleanup_order || 100,
      status: record?.status || 1,
    })
  }

  function doRefresh() {
    table.tableLoading.value = true
    const query = getFormItems(entityConditionItems)
    getDataFactoryEntity({ ...query, page: pagination.page, pageSize: pagination.pageSize }).then(
      (res) => {
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
      }
    )
  }

  function onResetSearch() {
    entityConditionItems.forEach((it) => {
      it.value = ''
    })
    datasourceAliasOptions.value = []
    doRefresh()
  }

  function loadDatasourceAliases(projectProduct: any) {
    const projectProductId = getOptionId(projectProduct)
    datasourceAliasOptions.value = []
    if (!projectProductId) {
      return Promise.resolve()
    }
    return getDataFactoryDatasourceAlias({ project_product: projectProductId }).then((res) => {
      datasourceAliasOptions.value = res.data || []
    })
  }

  function loadOptions() {
    const searchProjectProduct = getSearchItemValue('project_product')
    if (searchProjectProduct) {
      loadDatasourceAliases(searchProjectProduct)
    }
  }

  function loadDependencyTemplates(record?: any) {
    const projectProduct =
      record?.project_product?.id || record?.project_product || entityForm.project_product
    if (!projectProduct) {
      dependencyCascaderOptions.value = []
      return Promise.resolve()
    }
    return productModule.getProjectModule(getOptionId(projectProduct)).then(() => {
      dependencyCascaderOptions.value = (productModule.data || []).map((module: any) => ({
        label: getModuleDisplayName(module),
        value: `module:${module.key ?? module.id}`,
        raw_id: module.key ?? module.id,
        level: 'module',
        isLeaf: false,
      }))
    })
  }

  function openEntity(record?: any) {
    resetEntityForm(record)
    loadDatasourceAliases(entityForm.project_product)
    syncFieldsAfterSave.value = !record?.id
    entityDiscoveredColumns.value = []
    entityTableOptions.value = record?.table_name
      ? [{ label: record.table_name, value: record.table_name }]
      : []
    if (record?.datasource_alias && userStore.selected_environment != null) {
      loadEntityTables(record.datasource_alias?.id || record.datasource_alias)
    }
    entityVisible.value = true
  }

  function openBatchGenerate() {
    batchForm.project_product = entityForm.project_product || null
    batchForm.module = entityForm.module || null
    batchForm.datasource_alias = null
    batchForm.sync_fields = true
    batchForm.skip_exists = true
    batchRows.value = []
    batchSelectedKeys.value = []
    loadDatasourceAliases(batchForm.project_product)
    batchVisible.value = true
  }

  async function saveEntity() {
    if (!entityForm.project_product) {
      Message.error('请选择产品')
      return false
    }
    if (!entityForm.module) {
      Message.error('请选择模块')
      return false
    }
    if (!entityForm.datasource_alias) {
      Message.error('请选择逻辑数据源')
      return false
    }
    if (!entityForm.table_name) {
      Message.error('请选择表名')
      return false
    }
    if (!entityForm.name) {
      Message.error('请填写实体名称')
      return false
    }
    entityForm.create_type = 2
    fillEntitySystemFields()
    const request = entityForm.id ? putDataFactoryEntity : postDataFactoryEntity
    entitySaving.value = true
    try {
      const res = await request({ ...entityForm })
      const entityId = res.data?.id || entityForm.id
      if (syncFieldsAfterSave.value && entityId) {
        await ensureEntityDiscoveredColumns()
        if (!entityDiscoveredColumns.value.length) {
          Message.warning('实体已保存，但没有发现可同步的字段，请进入字段规则手动同步')
          doRefresh()
          return true
        }
        await syncEntityFields(entityId)
        Message.success('实体和字段规则保存成功')
        doRefresh()
        return true
      }
      Message.success(res.msg)
      doRefresh()
      return true
    } catch (error) {
      return false
    } finally {
      entitySaving.value = false
    }
  }

  function onEntityDatasourceChange(value: any) {
    entityForm.table_name = ''
    entityForm.primary_key = 'id'
    entityForm.unique_key = ''
    entityDiscoveredColumns.value = []
    entityTableOptions.value = []
    if (value && userStore.selected_environment != null) {
      loadEntityTables(value)
    }
  }

  function loadEntityTables(datasourceAliasId: any, refresh = false) {
    if (!ensureSelectedEnvironment()) {
      return Promise.resolve()
    }
    const projectProduct =
      entityForm.project_product ||
      currentEntity.value?.project_product?.id ||
      currentEntity.value?.project_product
    if (!projectProduct) {
      Message.error('请先选择产品')
      return Promise.resolve()
    }
    entityTableLoading.value = true
    return postDataFactoryDiscoverTables({
      datasource_alias_id: getOptionId(datasourceAliasId),
      project_product: getOptionId(projectProduct),
      test_env: userStore.selected_environment,
      refresh,
    })
      .then((res) => {
        entityTableOptions.value = (res.data || []).map(normalizeTableOption)
      })
      .finally(() => {
        entityTableLoading.value = false
      })
  }

  function refreshEntityTables() {
    if (!entityForm.datasource_alias) {
      Message.error('请先选择逻辑数据源')
      return
    }
    entityTableRefreshLoading.value = true
    loadEntityTables(entityForm.datasource_alias, true)
      .then(() => {
        Message.success('表名缓存已清理并重新加载')
      })
      .finally(() => {
        entityTableRefreshLoading.value = false
      })
  }

  function normalizeTableOption(table: any) {
    if (typeof table === 'string') {
      return { label: table, value: table, comment: '' }
    }
    const name = table.name || table.table || ''
    const comment = table.comment || table.table_comment || ''
    return {
      label: comment ? `${name} / ${comment}` : name,
      value: name,
      comment,
    }
  }

  function normalizeBatchTable(table: any, existsMap: Map<string, any>) {
    const name = typeof table === 'string' ? table : table.name || table.table || ''
    const comment = typeof table === 'string' ? '' : table.comment || table.table_comment || ''
    const existed = existsMap.get(name)
    return {
      table_name: name,
      table_comment: comment,
      name: existed?.name || comment || name,
      status: existed ? 'exists' : 'ready',
      message: existed ? `已存在实体：${existed.name}` : '可生成',
      disabled: Boolean(existed),
    }
  }

  function loadBatchTables() {
    if (!batchForm.project_product) {
      Message.error('请选择产品')
      return
    }
    if (!batchForm.module) {
      Message.error('请选择模块')
      return
    }
    if (!batchForm.datasource_alias) {
      Message.error('请选择逻辑数据源')
      return
    }
    if (!ensureSelectedEnvironment()) {
      return
    }
    batchLoading.value = true
    Promise.all([
      postDataFactoryDiscoverTables({
        datasource_alias_id: getOptionId(batchForm.datasource_alias),
        project_product: getOptionId(batchForm.project_product),
        test_env: userStore.selected_environment,
      }),
      getDataFactoryEntity({
        project_product: getOptionId(batchForm.project_product),
        module: getOptionId(batchForm.module),
        datasource_alias: getOptionId(batchForm.datasource_alias),
        page: 1,
        pageSize: 9999,
      }),
    ])
      .then(([tableRes, entityRes]) => {
        const existsMap = new Map(
          (entityRes.data || []).map((entity: any) => [entity.table_name, entity])
        )
        batchRows.value = (tableRes.data || []).map((it: any) => normalizeBatchTable(it, existsMap))
        batchSelectedKeys.value = batchRows.value
          .filter((it) => !it.disabled)
          .map((it) => it.table_name)
        Message.success('表加载完成')
      })
      .finally(() => {
        batchLoading.value = false
      })
  }

  function onBatchSelectionChange(keys: any[]) {
    const disabledKeys = batchRows.value.filter((it) => it.disabled).map((it) => it.table_name)
    batchSelectedKeys.value = keys.filter((key) => !disabledKeys.includes(key))
  }

  function batchGenerateEntities() {
    const selectedRows = batchRows.value.filter(
      (it) => batchSelectedKeys.value.includes(it.table_name) && !it.disabled
    )
    if (!selectedRows.length) {
      Message.error('请至少选择一张可生成的表')
      return
    }
    if (!batchForm.module) {
      Message.error('请选择模块')
      return
    }
    const emptyNameRow = selectedRows.find((it) => !it.name)
    if (emptyNameRow) {
      Message.error(`表 ${emptyNameRow.table_name} 的实体名称不能为空`)
      return
    }
    batchGenerating.value = true
    postDataFactoryEntityBatchGenerate({
      project_product: getOptionId(batchForm.project_product),
      module: getOptionId(batchForm.module),
      datasource_alias: getOptionId(batchForm.datasource_alias),
      test_env: userStore.selected_environment,
      sync_fields: batchForm.sync_fields,
      skip_exists: batchForm.skip_exists,
      tables: selectedRows.map((it) => ({
        table_name: it.table_name,
        name: it.name,
      })),
    })
      .then((res) => {
        const resultMap = new Map((res.data?.items || []).map((it: any) => [it.table_name, it]))
        batchRows.value = batchRows.value.map((row) => {
          const result = resultMap.get(row.table_name) as any
          if (!result) {
            return row
          }
          return {
            ...row,
            status: result.status,
            message: result.message,
            entity_id: result.entity_id,
            field_count: result.field_count,
            disabled: result.status === 'success' || result.status === 'skipped',
          }
        })
        batchSelectedKeys.value = batchRows.value
          .filter((it) => batchSelectedKeys.value.includes(it.table_name) && !it.disabled)
          .map((it) => it.table_name)
        Message.success(
          `生成完成：成功 ${res.data?.success || 0}，跳过 ${res.data?.skipped || 0}，失败 ${
            res.data?.failed || 0
          }`
        )
        batchVisible.value = false
        doRefresh()
      })
      .finally(() => {
        batchGenerating.value = false
      })
  }

  function getBatchStatusText(status: string) {
    const statusMap: Record<string, string> = {
      ready: '可生成',
      exists: '已存在',
      success: '成功',
      skipped: '跳过',
      failed: '失败',
    }
    return statusMap[status] || status || '-'
  }

  function getBatchStatusColor(status: string) {
    const colorMap: Record<string, string> = {
      ready: 'arcoblue',
      exists: 'gray',
      success: 'green',
      skipped: 'orange',
      failed: 'red',
    }
    return colorMap[status] || 'gray'
  }

  function onEntityTableChange(tableName: string) {
    entityDiscoveredColumns.value = []
    if (!entityForm.datasource_alias || !tableName || !ensureSelectedEnvironment()) {
      return
    }
    postDataFactoryDiscoverTable({
      datasource_alias_id: getOptionId(entityForm.datasource_alias),
      project_product: getOptionId(entityForm.project_product),
      test_env: userStore.selected_environment,
      table_name: tableName,
    }).then((res) => {
      const schema = res.data || {}
      entityDiscoveredColumns.value = schema.columns || []
      entityForm.primary_key = schema.primary_keys?.[0] || entityForm.primary_key || 'id'
      const uniqueIndex = (schema.indexes || []).find(
        (item: any) => item.unique && item.column_names?.length === 1
      )
      entityForm.unique_key = uniqueIndex?.column_names?.[0] || entityForm.unique_key || ''
      applyEntityNameSuggestion(tableName, schema.table_comment)
    })
  }

  function applyEntityNameSuggestion(tableName: string, tableComment?: string) {
    const selectedTable = entityTableOptions.value.find((item: any) => item.value === tableName)
    const suggestedName = tableComment || selectedTable?.comment || tableName
    if (!entityForm.id || !entityForm.name || entityForm.name === entityForm.table_name) {
      entityForm.name = suggestedName
    }
  }

  function fillEntitySystemFields() {
    // 保留方法入口，后续如有表级默认值可集中补齐。
  }

  function ensureEntityDiscoveredColumns() {
    if (entityDiscoveredColumns.value.length) {
      return Promise.resolve()
    }
    if (!entityForm.datasource_alias || !entityForm.table_name) {
      return Promise.resolve()
    }
    if (!ensureSelectedEnvironment()) {
      return Promise.resolve()
    }
    return postDataFactoryDiscoverTable({
      datasource_alias_id: getOptionId(entityForm.datasource_alias),
      project_product: getOptionId(entityForm.project_product),
      test_env: userStore.selected_environment,
      table_name: entityForm.table_name,
    }).then((res) => {
      const schema = res.data || {}
      entityDiscoveredColumns.value = schema.columns || []
      entityForm.primary_key = schema.primary_keys?.[0] || entityForm.primary_key || 'id'
      const uniqueIndex = (schema.indexes || []).find(
        (item: any) => item.unique && item.column_names?.length === 1
      )
      entityForm.unique_key = uniqueIndex?.column_names?.[0] || entityForm.unique_key || ''
    })
  }

  function syncEntityFields(entityId: any) {
    const fields = entityDiscoveredColumns.value.map((it: any, index: number) => ({
      ...it,
      entity: entityId,
      generator_type: it.generator_type ?? it.recommend?.generator_type ?? 1,
      generator_config: it.generator_config || it.recommend?.generator_config || {},
      sort: index,
    }))
    return postDataFactoryFieldBatchSave({ entity_id: entityId, replace: true, fields })
  }

  function removeEntity(record: any) {
    Modal.confirm({
      title: '删除实体',
      content: `确认删除 ${record.name}？`,
      onBeforeOk: () => {
        actionLoading.value = `delete-${record.id}`
        return deleteDataFactoryEntity(record.id)
          .then(() => doRefresh())
          .finally(() => {
            actionLoading.value = ''
          })
      },
    })
  }

  function switchEntityStatus(newValue: boolean, id: number) {
    return new Promise<boolean>((resolve, reject) => {
      putDataFactoryEntityStatus({ id, status: newValue ? 1 : 0 })
        .then((res) => {
          Message.success(res.msg)
          doRefresh()
          resolve(res.code === 200)
        })
        .catch(reject)
    })
  }

  function openFields(record: any) {
    actionLoading.value = `fields-${record.id}`
    currentEntity.value = record
    Promise.all([
      loadDependencyTemplates(record),
      getDataFactoryField({ entity: record.id }).then((res) => {
        fieldRows.value = (res.data || []).map((it: any) => normalizeFieldRow(it))
      }),
    ])
      .then(() => preloadDependencyCascaderPaths())
      .then(() => {
        fieldVisible.value = true
      })
      .finally(() => {
        actionLoading.value = ''
      })
  }

  function syncCurrentEntityFields() {
    if (!currentEntity.value?.table_name) {
      Message.error('当前实体未绑定表名，请先编辑实体选择表')
      return
    }
    if (!currentEntity.value?.datasource_alias || !ensureSelectedEnvironment()) {
      Message.error('请先选择逻辑数据源和顶部测试环境')
      return
    }
    fieldSyncLoading.value = true
    postDataFactoryDiscoverTable({
      datasource_alias_id: getOptionId(currentEntity.value.datasource_alias),
      project_product: getOptionId(currentEntity.value.project_product),
      test_env: userStore.selected_environment,
      table_name: currentEntity.value.table_name,
    })
      .then((res) => {
        fieldRows.value = mergeDiscoveredFields(res.data.columns || [])
        Message.success('字段同步完成')
      })
      .finally(() => {
        fieldSyncLoading.value = false
      })
  }

  async function saveFields() {
    const fields = buildFieldPayload()
    if (!fields) {
      return false
    }
    fieldSaving.value = true
    try {
      const res = await postDataFactoryFieldBatchSave({
        entity_id: currentEntity.value.id,
        replace: replaceFields.value,
        fields,
      })
      Message.success(res.msg)
      return true
    } catch (error) {
      return false
    } finally {
      fieldSaving.value = false
    }
  }

  function buildFieldPayload() {
    return fieldRows.value.map((it) => buildFieldPayloadItem(it))
  }

  function previewFieldValues() {
    if (!ensureSelectedEnvironment()) {
      return
    }
    const fields = buildFieldPayload()
    if (!fields) {
      return
    }
    fieldPreviewLoading.value = true
    postDataFactoryFieldPreviewValues({
      entity_id: currentEntity.value?.id,
      fields,
      test_env: userStore.selected_environment,
    })
      .then((res) => {
        const previewMap = new Map((res.data?.fields || []).map((it: any) => [it.name, it]))
        fieldRows.value = fieldRows.value.map((row) => {
          const preview = previewMap.get(row.name) as any
          return {
            ...row,
            preview_value: preview?.value,
            preview_valid: preview?.valid ?? true,
            preview_message: preview?.message || '',
          }
        })
        Message.success('实际值生成完成')
      })
      .finally(() => {
        fieldPreviewLoading.value = false
      })
  }

  function formatPreviewValue(value: any) {
    if (value === undefined) {
      return 'null'
    }
    if (value === null) {
      return 'null'
    }
    if (typeof value === 'object') {
      return JSON.stringify(value)
    }
    return String(value)
  }

  function normalizeFieldRow(row: any) {
    const generatorConfig = row.generator_config || row.recommend?.generator_config || {}
    if (row.generator_type === GENERATOR_TYPE_DEPENDENCY_FIELD && !generatorConfig.field) {
      generatorConfig.field = 'id'
    }
    return {
      ...row,
      generator_config: generatorConfig,
      generator_config_value: getGeneratorConfigValue({
        ...row,
        generator_config: generatorConfig,
      }),
      preview_value: undefined,
      preview_valid: true,
      preview_message: '',
    }
  }

  function mergeDiscoveredFields(columns: any[]) {
    const existingMap = new Map(
      fieldRows.value.map((field) => [field.name, buildFieldPayloadItem(field)])
    )
    return columns.map((column: any, index: number) => {
      const existing = existingMap.get(column.name) as any
      const generatorType =
        existing?.generator_type ?? column.generator_type ?? column.recommend?.generator_type ?? 1
      const generatorConfig =
        existing?.generator_config ??
        column.generator_config ??
        column.recommend?.generator_config ??
        {}
      return normalizeFieldRow({
        ...existing,
        ...column,
        entity: currentEntity.value.id,
        generator_type: generatorType,
        generator_config: generatorConfig,
        label: existing?.label || column.label || column.comment || column.name,
        sort: existing?.sort ?? index,
      })
    })
  }

  function buildFieldPayloadItem(row: any) {
    let generatorConfig = { ...(row.generator_config || {}) }
    if (row.generator_type === GENERATOR_TYPE_ENUM) {
      normalizeEnumFieldForSave(row, generatorConfig)
    } else if (row.generator_type === GENERATOR_TYPE_DEPENDENCY_FIELD) {
      generatorConfig = {
        dependency_entity_id: generatorConfig.dependency_entity_id,
        field: generatorConfig.field || 'id',
      }
    } else if (row.generator_type === GENERATOR_TYPE_SKIP) {
      generatorConfig = generatorConfig.reason ? { reason: generatorConfig.reason } : {}
    } else if (row.generator_type === GENERATOR_TYPE_RANDOM_STRING) {
      generatorConfig = pickGeneratorConfig(generatorConfig, ['prefix', 'length'])
    } else if (row.generator_type === GENERATOR_TYPE_RANDOM_INTEGER) {
      generatorConfig = pickGeneratorConfig(generatorConfig, ['min', 'max'])
    } else if (row.generator_type === GENERATOR_TYPE_RANDOM_DECIMAL) {
      generatorConfig = pickGeneratorConfig(generatorConfig, ['min', 'max', 'precision'])
    } else if (row.generator_type === GENERATOR_TYPE_NOW) {
      generatorConfig = {}
    } else if (row.generator_type === GENERATOR_TYPE_RELATIVE_TIME) {
      generatorConfig = pickGeneratorConfig(generatorConfig, ['days', 'hours', 'minutes'])
    } else if (row.generator_type === GENERATOR_TYPE_UUID) {
      generatorConfig = pickGeneratorConfig(generatorConfig, ['dash'])
    } else if (!isReadonlyGeneratorConfig(row)) {
      const value = row.generator_config_value ?? ''
      if (row.generator_type === GENERATOR_TYPE_FIXED) {
        generatorConfig.value = value
      } else if (row.generator_type === GENERATOR_TYPE_FUNCTION) {
        generatorConfig = { value }
      } else if (value === '') {
        delete generatorConfig.value
      } else {
        generatorConfig.value = value
      }
    }
    return {
      ...row,
      generator_config: generatorConfig,
    }
  }

  function pickGeneratorConfig(config: Record<string, any>, keys: string[]) {
    return keys.reduce((result: Record<string, any>, key) => {
      if (config[key] !== undefined && config[key] !== null && config[key] !== '') {
        result[key] = config[key]
      }
      return result
    }, {})
  }

  function getEnumOptionRows(row: any) {
    const config = row.generator_config || {}
    const optionRows = Array.isArray(config.options) ? config.options : []
    if (optionRows.length) {
      return optionRows.map((option: any) => ({
        label: option.label ?? String(option.value ?? ''),
        value: option.value,
      }))
    }
    const values = config.values || row.enum_values || []
    return values.map((value: any) => ({
      label: String(value),
      value,
    }))
  }

  function getEnumSelectOptions(row: any) {
    return getEnumOptionRows(row).map((option: any) => ({
      label: `${option.label}（${formatPreviewValue(option.value)}）`,
      value: option.value,
    }))
  }

  function openEnumEditor(row: any) {
    currentEnumRow.value = row
    enumOptionRows.value = getEnumOptionRows(row).map((option: any) => ({
      label: option.label,
      value: formatPreviewValue(option.value),
    }))
    if (!enumOptionRows.value.length) {
      enumOptionRows.value = [{ label: '', value: '' }]
    }
    enumEditorVisible.value = true
  }

  function addEnumOption() {
    enumOptionRows.value.push({ label: '', value: '' })
  }

  function removeEnumOption(index: number) {
    enumOptionRows.value.splice(index, 1)
  }

  function saveEnumOptions() {
    const row = currentEnumRow.value
    if (!row) {
      return true
    }
    const options = enumOptionRows.value
      .filter(
        (option) => option.value !== undefined && option.value !== null && option.value !== ''
      )
      .map((option) => {
        const value = castEnumValue(option.value, row.platform_type)
        return {
          label: option.label || String(value),
          value,
        }
      })
    if (options.some((option) => typeof option.value === 'number' && Number.isNaN(option.value))) {
      Message.error('枚举值类型不合法，请按字段平台类型填写')
      return false
    }
    if (!options.length) {
      Message.error('请至少配置一个枚举项')
      return false
    }
    const values = options.map((option) => option.value)
    row.enum_values = values
    row.generator_config = {
      ...(row.generator_config || {}),
      values,
      options,
    }
    if (!values.some((value) => value === row.generator_config.value)) {
      row.generator_config.value = values[0]
    }
    refreshEnumConfigValue(row)
    return true
  }

  function castEnumValue(value: any, platformType?: string) {
    if (platformType === 'integer') {
      return Number.parseInt(String(value), 10)
    }
    if (platformType === 'decimal') {
      return Number(value)
    }
    if (platformType === 'boolean') {
      if (value === true || value === 'true' || value === '1' || value === 1) {
        return true
      }
      if (value === false || value === 'false' || value === '0' || value === 0) {
        return false
      }
    }
    return value
  }

  function refreshEnumConfigValue(row: any) {
    row.generator_config = row.generator_config || {}
    row.generator_config_value = getGeneratorConfigValue(row)
    row.preview_value = undefined
    row.preview_message = ''
  }

  function normalizeEnumFieldForSave(row: any, generatorConfig: any) {
    const options = getEnumOptionRows({ ...row, generator_config: generatorConfig })
    const values = options.map((option: any) => castEnumValue(option.value, row.platform_type))
    row.enum_values = values
    generatorConfig.values = values
    generatorConfig.options = options.map((option: any, index: number) => ({
      label: option.label || String(values[index]),
      value: values[index],
    }))
    if (
      generatorConfig.value !== undefined &&
      generatorConfig.value !== null &&
      generatorConfig.value !== ''
    ) {
      generatorConfig.value = castEnumValue(generatorConfig.value, row.platform_type)
    } else if (values.length) {
      generatorConfig.value = values[0]
    }
  }

  function getGeneratorConfigValue(row: any) {
    const config = row.generator_config || {}
    if (config.value !== undefined && config.value !== null) {
      return String(config.value)
    }
    if (row.generator_type === GENERATOR_TYPE_SKIP) {
      return config.reason || '数据库生成'
    }
    if (row.generator_type === GENERATOR_TYPE_DEPENDENCY_FIELD) {
      const targetField = config.field || 'id'
      if (config.alias) {
        return `${config.alias}.${targetField}`
      }
      if (config.dependency_entity_id) {
        return `entity:${config.dependency_entity_id}.${targetField}`
      }
      return `请选择依赖实体.${targetField}`
    }
    if (row.generator_type === GENERATOR_TYPE_ENUM) {
      if (config.value !== undefined && config.value !== null) {
        return String(config.value)
      }
      return ''
    }
    return ''
  }

  function getModuleDisplayName(module: any) {
    if (!module) {
      return '未分配模块'
    }
    return formatModulePath({
      ...module,
      name: module.name || module.title || module.id || module,
    })
  }

  function getDependencyCascaderValue(row: any) {
    const config = row.generator_config || {}
    if (!config.dependency_entity_id) {
      return []
    }
    return findDependencyEntityFieldPath(
      dependencyCascaderOptions.value,
      `entity:${config.dependency_entity_id}`,
      `field:${config.field || 'id'}`
    )
  }

  function findDependencyEntityFieldPath(
    options: any[],
    entityValue: string,
    fieldValue: string,
    parents: any[] = []
  ): any[] {
    for (const option of options || []) {
      const path = [...parents, option.value]
      if (option.value === entityValue) {
        const field = (option.children || []).find((item: any) => item.value === fieldValue)
        return field ? [...path, field.value] : path
      }
      if (option.children?.length) {
        const childPath = findDependencyEntityFieldPath(
          option.children,
          entityValue,
          fieldValue,
          path
        )
        if (childPath.length) {
          return childPath
        }
      }
    }
    return []
  }

  function loadDependencyCascaderMore(option: any, done: (children?: any[]) => void) {
    const projectProduct = getOptionId(
      entityForm.project_product || currentEntity.value?.project_product
    )
    if (!projectProduct) {
      done([])
      return
    }
    if (option.level === 'module') {
      loadDependencyEntities(option.raw_id).then((children) => {
        const moduleOption = findDependencyOption(`module:${option.raw_id}`)
        if (moduleOption) {
          moduleOption.children = children
          dependencyCascaderOptions.value = [...dependencyCascaderOptions.value]
        }
        done(children)
      })
      return
    }
    if (option.level === 'entity') {
      loadDependencyFields(option.raw_id).then((children) => {
        const entityOption = findDependencyOption(`entity:${option.raw_id}`)
        if (entityOption) {
          entityOption.children = children
          dependencyCascaderOptions.value = [...dependencyCascaderOptions.value]
        }
        done(children)
      })
      return
    }
    done([])
  }

  function findDependencyOption(value: string, options = dependencyCascaderOptions.value): any {
    for (const option of options || []) {
      if (option.value === value) {
        return option
      }
      const child = findDependencyOption(value, option.children || [])
      if (child) {
        return child
      }
    }
    return null
  }

  function loadDependencyEntities(moduleId: any) {
    const projectProduct = getOptionId(
      entityForm.project_product || currentEntity.value?.project_product
    )
    if (!projectProduct || !moduleId) {
      return Promise.resolve([])
    }
    return getDataFactoryEntity({
      project_product: projectProduct,
      module: moduleId,
      page: 1,
      pageSize: 9999,
    }).then((res) =>
      (res.data || [])
        .filter((entity: any) => entity.id !== currentEntity.value?.id)
        .map((entity: any) => ({
          label: `${entity.name || entity.id}${entity.table_name ? ` / ${entity.table_name}` : ''}`,
          value: `entity:${entity.id}`,
          raw_id: entity.id,
          level: 'entity',
          isLeaf: false,
        }))
    )
  }

  function loadDependencyFields(entityId: any) {
    if (!entityId) {
      return Promise.resolve([])
    }
    return getDataFactoryField({ entity: entityId }).then((res) =>
      (res.data || []).map((field: any) => ({
        label: `${field.label || field.name} / ${field.name}`,
        value: `field:${field.name}`,
        raw_id: field.name,
        level: 'field',
        isLeaf: true,
      }))
    )
  }

  async function preloadDependencyCascaderPaths() {
    const dependencyEntityIds = Array.from(
      new Set(
        fieldRows.value
          .map((row) => row.generator_config?.dependency_entity_id)
          .filter((value) => value !== undefined && value !== null && value !== '')
      )
    )
    for (const dependencyEntityId of dependencyEntityIds) {
      await preloadDependencyCascaderPath(dependencyEntityId)
    }
  }

  async function preloadDependencyCascaderPath(dependencyEntityId: any) {
    const projectProduct = getOptionId(
      entityForm.project_product || currentEntity.value?.project_product
    )
    if (!projectProduct || !dependencyEntityId) {
      return
    }
    const entityRes = await getDataFactoryEntity({
      id: dependencyEntityId,
      project_product: projectProduct,
      page: 1,
      pageSize: 1,
    })
    const entity = (entityRes.data || [])[0]
    const moduleId = entity?.module?.id || entity?.module
    if (!moduleId) {
      return
    }
    const moduleOption = dependencyCascaderOptions.value.find(
      (option: any) => String(option.raw_id) === String(moduleId)
    )
    if (!moduleOption) {
      return
    }
    if (!moduleOption.children?.length) {
      moduleOption.children = await loadDependencyEntities(moduleId)
    }
    const entityOption = (moduleOption.children || []).find(
      (option: any) => String(option.raw_id) === String(dependencyEntityId)
    )
    if (entityOption && !entityOption.children?.length) {
      entityOption.children = await loadDependencyFields(dependencyEntityId)
    }
    dependencyCascaderOptions.value = [...dependencyCascaderOptions.value]
  }

  function changeDependencyCascader(row: any, value: any) {
    const path = Array.isArray(value) ? value : []
    const entityValue = path.find((item: string) => String(item).startsWith('entity:'))
    const fieldValue = path.find((item: string) => String(item).startsWith('field:'))
    if (!entityValue) {
      row.generator_config = {}
      refreshDependencyConfigValue(row)
      return
    }
    row.generator_config = {
      dependency_entity_id: entityValue ? Number(String(entityValue).replace('entity:', '')) : null,
      field: fieldValue ? String(fieldValue).replace('field:', '') : 'id',
    }
    refreshDependencyConfigValue(row)
  }

  function refreshDependencyConfigValue(row: any) {
    row.generator_config_value = getGeneratorConfigValue(row)
    row.preview_value = undefined
    row.preview_message = ''
  }

  function isReadonlyGeneratorConfig(row: any) {
    return [
      GENERATOR_TYPE_SKIP,
      GENERATOR_TYPE_RANDOM_STRING,
      GENERATOR_TYPE_RANDOM_INTEGER,
      GENERATOR_TYPE_RANDOM_DECIMAL,
      GENERATOR_TYPE_NOW,
      GENERATOR_TYPE_RELATIVE_TIME,
      GENERATOR_TYPE_UUID,
      GENERATOR_TYPE_DEPENDENCY_FIELD,
    ].includes(row.generator_type)
  }

  function getGeneratorConfigPlaceholder(row: any) {
    if (isReadonlyGeneratorConfig(row)) {
      return '自动生成'
    }
    if (row.generator_type === GENERATOR_TYPE_FIXED) {
      return '输入值'
    }
    if (row.generator_type === GENERATOR_TYPE_ENUM) {
      return '选枚举'
    }
    if (row.generator_type === GENERATOR_TYPE_FUNCTION) {
      return '测试方法'
    }
    return '生成配置'
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
    loadOptions()
    doRefresh()
  })
</script>

<style scoped>
  .entity-table-select-group {
    display: flex;
    width: 100%;
  }

  .entity-table-select {
    flex: 1;
    min-width: 0;
  }

  .entity-table-refresh {
    flex: 0 0 112px;
  }

  .field-rule-db-type {
    display: inline-block;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    vertical-align: middle;
    white-space: nowrap;
  }

  .entity-toolbar,
  .entity-alert {
    margin-bottom: 12px;
  }

  .full-width {
    width: 100%;
  }

  .enum-editor-tip {
    background: var(--m-surface-soft);
    border-left: 3px solid var(--m-border-strong);
    border-radius: 3px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 20px;
    padding: 6px 10px;
  }

  .enum-option-row {
    margin-bottom: 6px;
  }

  .enum-option-label {
    color: var(--m-text-2);
    display: inline-block;
    font-size: 14px;
    line-height: 18px;
    white-space: nowrap;
  }
</style>
