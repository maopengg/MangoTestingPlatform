<template>
  <a-space direction="vertical" fill>
    <div v-if="showAddButton" class="data-factory-case-config__toolbar">
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
          <template v-else-if="item.key === 'cleanup_strategy'" #cell="{ record }">
            {{ enumTitle(enumStore.data_factory_cleanup_strategy, record.cleanup_strategy || record.template?.cleanup_strategy) }}
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
              <a-button size="mini" status="danger" type="text" @click="deleteConfig(record)">删除</a-button>
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
          <a-form-item label="状态模板" required>
            <a-select
              v-model="form.template"
              :options="templateList"
              :field-names="{ value: 'id', label: 'name' }"
              allow-clear
              allow-search
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
        <a-spin :loading="fieldLoading" style="width: 100%">
          <TemplateFieldConfigEditor
            v-if="form.template"
            v-model:field-overrides="form.field_overrides"
            v-model:output-config="templateOutputConfig"
            :fields="fieldRows"
            :generator-options="enumStore.data_factory_generator_type"
            :show-output="false"
          />
          <a-empty v-else class="field-empty" description="请先选择状态模板" />
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

  <DataFactoryPreviewModal v-model:visible="previewVisible" :result="previewResult" />
</template>

<script lang="ts" setup>
  import { computed, onMounted, reactive, ref, watch } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import useUserStore from '@/store/modules/user'
  import { useEnum } from '@/store/modules/get-enum'
  import TemplateFieldConfigEditor from '@/components/DataFactory/TemplateFieldConfigEditor.vue'
  import DataFactoryPreviewModal from '@/components/DataFactory/PreviewModal.vue'
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

  const columns = [
    { title: '数据名称', key: 'name', dataIndex: 'name', width: 150 },
    { title: '状态模板', key: 'template', dataIndex: 'template', width: 160 },
    { title: '基础实体', key: 'entity', dataIndex: 'entity', width: 120 },
    { title: '清理策略', key: 'cleanup_strategy', dataIndex: 'cleanup_strategy', width: 120 },
    { title: '状态', key: 'status', dataIndex: 'status', width: 90, align: 'center' },
    { title: '操作', key: 'actions', dataIndex: 'actions', width: 180, align: 'center' },
  ]

  const caseConfigList = ref<any[]>([])
  const templateList = ref<any[]>([])
  const fieldRows = ref<DataFactoryFieldRule[]>([])
  const templateOutputConfig = ref<DataFactoryOutputConfig>([])
  const loading = ref(false)
  const fieldLoading = ref(false)
  const saving = ref(false)
  const visible = ref(false)
  const previewVisible = ref(false)
  const previewLoading = ref<any>(null)
  const previewResult = ref({})

  const form = reactive<{
    id: number | null
    source_type: number
    source_id: string | number | null
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

  function enumTitle(options: any[] = [], value: any) {
    return options.find((item) => item.key === value)?.title || value || '-'
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
    const query: any = {
      page: 1,
      pageSize: 10000,
    }
    if (props.projectProductId) {
      query.project_product = props.projectProductId
    }
    getDataFactoryTemplate(query).then((res) => {
      templateList.value = res.data || []
    })
  }

  function resetForm(record: any = null) {
    form.id = record?.id || null
    form.source_type = props.sourceType
    form.source_id = props.caseId
    form.template = record?.template?.id || record?.template || null
    form.name = record?.name || ''
    form.sort = record?.sort ?? caseConfigList.value.length
    form.field_overrides = record?.field_overrides || {}
    form.cleanup_strategy = record?.cleanup_strategy ?? null
    form.status = record?.status ?? 1
    form.stage = record?.stage || 1
    templateOutputConfig.value = record?.template?.output_config || []
    fieldRows.value = []
  }

  function open(record: any = null) {
    resetForm(record)
    visible.value = true
    if (form.template) {
      loadFields()
    }
  }

  function onTemplateChange() {
    const template = templateList.value.find((item) => item.id === form.template)
    if (!form.name && template?.name) {
      form.name = template.name
    }
    templateOutputConfig.value = template?.output_config || []
    form.field_overrides = template?.field_overrides || {}
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
      })
      .finally(() => {
        fieldLoading.value = false
      })
  }

  async function save() {
    if (!form.template) {
      Message.error('请选择状态模板')
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
      ...form,
      source_type: props.sourceType,
      source_id: props.caseId,
      cleanup_strategy: (form.cleanup_strategy as any) === '' ? null : form.cleanup_strategy,
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
      onOk: () => {
        deleteDataFactoryCaseConfig(record.id).then((res) => {
          Message.success(res.msg)
          refresh()
        })
      },
    })
  }

  function preview(record: any = null) {
    const target = record || form
    const templateId = target?.template?.id || target?.template
    if (!templateId) {
      Message.error('请选择状态模板')
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

  watch(
    () => [props.caseId, props.sourceType],
    () => {
      refresh()
    }
  )

  watch(
    () => props.projectProductId,
    () => {
      loadTemplates()
    }
  )

  onMounted(() => {
    refresh()
    loadTemplates()
  })

  defineExpose({
    open,
    refresh,
  })
</script>

<style scoped>
  .data-factory-case-config__toolbar {
    display: flex;
    justify-content: flex-end;
  }

  .field-empty {
    padding: 24px 0;
    background: var(--color-fill-1);
    border: 1px dashed var(--color-border-2);
    border-radius: 4px;
  }
</style>
