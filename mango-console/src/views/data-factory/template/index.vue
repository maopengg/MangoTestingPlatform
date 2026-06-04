<template>
  <TableBody>
    <template #header>
      <TableHeader title="数据工厂 / 场景模板" @search="doRefresh" @reset-search="onResetSearch">
        <template #search-content>
          <a-form :model="{}" layout="inline" @keyup.enter="doRefresh">
            <a-form-item v-for="item of templateConditionItems" :key="item.key" :label="item.label">
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
                  @change="onSearchModuleChange"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'entity'">
                <a-select
                  v-model="item.value"
                  :field-names="{ value: 'id', label: 'name' }"
                  :options="searchEntityOptions"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
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
                  value-key="key"
                  @change="doRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'usage_scope'">
                <a-select
                  v-model="item.value"
                  :field-names="enumFieldNames"
                  :options="enumStore.data_factory_template_usage_scope"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
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
                >新增场景模板</a-button
              ></a-space
            >
          </div>
        </template>
      </a-tabs>
      <a-table
        :scroll="{ x: 1210 }"
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
              {{ formatProjectProductPath(record?.project_product) }}
            </template>
            <template v-else-if="item.key === 'module'" #cell="{ record }">
              {{ formatModulePath(record?.module) }}
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
                {{ record.is_default ? '默认使用' : '手动选择' }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'usage_scope'" #cell="{ record }">
              <a-tag :color="getUsageScopeColor(record.usage_scope)" size="small">
                {{ getUsageScopeTitle(record.usage_scope) }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'config_status'" #cell="{ record }">
              <a-tag :color="record.config_status === 1 ? 'green' : 'orange'" size="small">
                {{
                  enumTitle(
                    enumStore.data_factory_template_config_status,
                    record.config_status ?? 0
                  )
                }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'status'" #cell="{ record }">
              <a-switch
                :beforeChange="(newValue) => switchTemplateStatus(newValue, record.id)"
                :default-checked="record.status === 1"
              />
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <MangoTableActions
                :actions="[
                  {
                    label: '场景配置',
                    loading: actionLoading === `detail-${record.id}`,
                    onClick: () => openTemplateDetail(record),
                  },
                  { label: '编辑', onClick: () => openTemplate(record) },
                  {
                    label: '复制',
                    loading: actionLoading === `copy-${record.id}`,
                    onClick: () => copyTemplate(record),
                  },
                  {
                    label: '删除',
                    danger: true,
                    loading: actionLoading === `delete-${record.id}`,
                    onClick: () => removeTemplate(record),
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
    v-model:visible="templateVisible"
    :on-before-ok="saveTemplate"
    :ok-loading="templateSaving"
    :title="templateForm.id ? '编辑场景模板' : '新增场景模板'"
    width="720px"
  >
    <a-form :model="templateForm" layout="vertical">
      <a-grid :cols="2" :col-gap="16">
        <a-grid-item>
          <a-form-item label="产品" required
            ><ProjectProductSelect
              v-model="templateForm.project_product"
              @change="onTemplateProjectChange"
          /></a-form-item>
        </a-grid-item>
        <a-grid-item>
          <a-form-item label="模块" required
            ><ProductModuleSelect
              v-model="templateForm.module"
              :project-product-id="templateForm.project_product"
              :auto-clear="false"
              @change="onTemplateModuleChange"
          /></a-form-item>
        </a-grid-item>
        <a-grid-item>
          <a-form-item label="实体" required
            ><a-select
              v-model="templateForm.entity"
              :options="templateEntityOptions"
              :field-names="{ value: 'id', label: 'name' }"
              allow-search
          /></a-form-item>
        </a-grid-item>
        <a-grid-item
          ><a-form-item label="场景名称" required
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
          <a-form-item label="默认场景">
            <a-switch v-model="templateForm.is_default" />
          </a-form-item>
        </a-grid-item>
        <a-grid-item>
          <a-form-item label="场景用途" required>
            <a-select
              v-model="templateForm.usage_scope"
              :options="enumStore.data_factory_template_usage_scope"
              :field-names="enumFieldNames"
              placeholder="请选择场景用途"
            />
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
</template>

<script lang="ts" setup>
  import {
    deleteDataFactoryTemplate,
    getDataFactoryEntity,
    getDataFactoryTemplate,
    postDataFactoryTemplate,
    postDataFactoryTemplateCopy,
    putDataFactoryTemplate,
    putDataFactoryTemplateStatus,
  } from '@/api/data-factory'
  import { usePagination, useTable } from '@/hooks/table'
  import { useEnum } from '@/store/modules/get-enum'
  import useUserStore from '@/store/modules/user'
  import { usePageData } from '@/store/page-data'
  import { getFormItems } from '@/utils/datacleaning'
  import type { DataFactoryFieldOverrides, DataFactoryOutputConfig } from '@/types/data-factory'
  import { Message, Modal } from '@arco-design/web-vue'
  import { onMounted, reactive, ref, watch } from 'vue'
  import { useRouter } from 'vue-router'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import {
    formatModulePath,
    formatProjectProductPath,
    getItemValue,
  } from '@/utils/business-format'
  import { templateConditionItems, templateTableColumns } from './config'

  const table = useTable()
  const pagination = usePagination(doRefresh)
  const enumStore = useEnum()
  const userStore = useUserStore()
  const pageData = usePageData()
  const router = useRouter()
  const enumFieldNames = { value: 'key', label: 'title' }
  const searchEntityOptions = ref<any[]>([])
  const templateEntityOptions = ref<any[]>([])
  const templateVisible = ref(false)
  const templateForm = reactive<any>({})
  const templateSaving = ref(false)
  const resettingTemplateForm = ref(false)
  const actionLoading = ref('')
  const statusOptions = [
    { key: 1, title: '启用' },
    { key: 0, title: '禁用' },
  ]
  function enumTitle(options: any[] = [], value: any) {
    return options.find((it) => it.key === value)?.title || value
  }

  function getUsageScopeColor(value: any) {
    if (Number(value) === 2) {
      return 'orange'
    }
    return 'green'
  }

  function getUsageScopeTitle(value: any) {
    const normalizedValue = Number(value) === 2 ? 2 : 1
    return enumTitle(enumStore.data_factory_template_usage_scope, normalizedValue)
  }

  function getOptionId(value: any) {
    if (Array.isArray(value)) {
      return value[value.length - 1] ?? null
    }
    return value?.id ?? value
  }

  function getSearchItem(key: string) {
    return templateConditionItems.find((item) => item.key === key)
  }

  function getSearchItemValue(key: string) {
    return getItemValue(templateConditionItems, key)
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
    loadSearchEntities({
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
    loadSearchEntities({
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
      usage_scope: Number(record?.usage_scope) === 2 ? 2 : 1,
      status: record?.status || 1,
    })
    resettingTemplateForm.value = false
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

  function loadEntityOptions(params: any = {}, target = templateEntityOptions) {
    const query: any = { page: 1, pageSize: 9999 }
    const projectProduct = params.project_product ?? templateForm.project_product
    const module = params.module ?? templateForm.module
    if (projectProduct) {
      query.project_product = getOptionId(projectProduct)
    }
    if (module) {
      query.module = getOptionId(module)
    }
    return getDataFactoryEntity(query).then((res) => {
      target.value = res.data || []
    })
  }

  function loadSearchEntities(params: any = {}) {
    return loadEntityOptions(params, searchEntityOptions)
  }

  function loadTemplateEntities(params: any = {}) {
    return loadEntityOptions(params, templateEntityOptions)
  }

  function onTemplateProjectChange(value: any) {
    templateForm.module = null
    templateForm.entity = null
    templateForm.field_overrides = {}
    templateForm.output_config = []
    templateEntityOptions.value = []
  }

  function onTemplateModuleChange() {
    templateForm.entity = null
    templateForm.field_overrides = {}
    templateForm.output_config = []
    loadTemplateEntities()
  }

  function openTemplate(record?: any) {
    resetTemplateForm(record)
    loadTemplateEntities()
    templateVisible.value = true
  }

  async function saveTemplate() {
    if (
      !templateForm.project_product ||
      !templateForm.module ||
      !templateForm.entity ||
      !templateForm.name ||
      !templateForm.usage_scope
    ) {
      Message.error('请先填写产品、模块、实体、场景名称和场景用途')
      return false
    }

    const payload = {
      ...templateForm,
      field_overrides: templateForm.field_overrides || {},
      output_config: templateForm.output_config || [],
      test_env: userStore.selected_environment,
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

  function removeTemplate(record: any) {
    Modal.confirm({
      title: '删除场景模板',
      content: `确认删除 ${record.name}？`,
      onBeforeOk: () => {
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

  function openTemplateDetail(record: any) {
    if (!record?.id) {
      Message.error('场景模板不存在，请刷新后重试')
      return
    }
    actionLoading.value = `detail-${record.id}`
    pageData.setRecord(record)
    router.push({
      path: '/data-factory/template/preview',
      query: {
        template_id: record.id,
      },
    })
    actionLoading.value = ''
  }

  onMounted(() => {
    enumStore.getEnum()
    loadSearchEntities()
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
    }
  )
</script>
