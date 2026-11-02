<template>
  <TableBody
    plain
    class="mango-detail-workbench-page mango-perf-page mango-perf-navigation-page"
    :sticky-horizontal-scroll="false"
  >
    <template #header><TableHeader title="性能测试 / 性能场景" /></template>
    <template #default>
      <ProjectProductNavigationWorkbench
        contained-body
        show-modules
        :model-value="filters.project_product"
        :module-value="filters.module"
        :reset-key="resetKey"
        @filter-change="onNavigation"
        @search="load"
        @reset-search="resetSearch"
      >
        <template #search>
          <a-form :model="filters" layout="inline" @keyup.enter="load">
            <a-form-item label="场景名称"
              ><a-input
                v-model="filters.name"
                allow-clear
                placeholder="请输入场景名称"
                @clear="load"
                @blur="load"
            /></a-form-item>
            <a-form-item label="负载模型"
              ><a-select
                v-model="filters.load_type"
                multiple
                :max-tag-count="1"
                :options="loadTypeOptions"
                allow-clear
                placeholder="请选择负载模型"
                @change="load"
            /></a-form-item>
          </a-form>
        </template>
        <template #toolbar
          ><a-button  type="primary" size="small" @click="openCreate">新建场景</a-button></template
        >
        <a-table
          class="mango-native-scroll-table"
          :columns="scenarioColumns"
          :data="rows"
          :loading="loading"
          :pagination="false"
          :scroll="{ x: scenarioScrollX, y: '100%' }"
          row-key="id"
        >
          <template #columns>
            <a-table-column v-for="column in scenarioColumns" :key="column.key" v-bind="column">
              <template v-if="column.key === 'index'" #cell="{ record }">{{ record.id }}</template>
              <template v-else-if="column.key === 'name'" #cell="{ record }"
                ><a-link @click="goDetail(record)">{{ record.name }}</a-link></template
              >
              <template v-else-if="column.key === 'project_product'" #cell="{ record }">{{
                formatProjectProductPath(record.project_product)
              }}</template>
              <template v-else-if="column.key === 'module'" #cell="{ record }">{{
                record.module_full_path || formatModulePath(record.module)
              }}</template>
              <template v-else-if="column.key === 'load_type'" #cell="{ record }">{{
                loadTitle(record.load_type)
              }}</template>
              <template v-else-if="column.key === 'load_target'" #cell="{ record }">{{
                loadTarget(record)
              }}</template>
              <template v-else-if="column.key === 'duration_seconds'" #cell="{ record }"
                >{{ record.duration_seconds || 0 }} 秒</template
              >
              <template v-else-if="column.key === 'status'" #cell="{ record }"
                ><a-switch
                  size="small"
                  :model-value="record.status"
                  :checked-value="1"
                  :unchecked-value="0"
                  :before-change="(value) => toggleStatus(record, value)"
              /></template>
              <template v-else-if="column.key === 'actions'" #cell="{ record }">
                <MangoTableActions
                  :actions="[
    {
        label: '执行',
        onClick: () => execute(record), },
    { label: '配置', onClick: () => goDetail(record) },
    { label: '删除', danger: true, onClick: () => remove(record) },
]"
                />
              </template>
            </a-table-column>
          </template>
        </a-table>
        <template #footer><TableFooter :pagination="pagination" /></template>
      </ProjectProductNavigationWorkbench>
    </template>
  </TableBody>

  <ModalDialog ref="createDialogRef" title="新建性能场景" :width="720" @confirm="saveCreate">
    <template #content>
      <a-form ref="createFormRef" :model="form" layout="horizontal" auto-label-width>
        <a-grid :cols="2" :col-gap="12" :row-gap="4">
          <a-grid-item
            ><a-form-item
              field="name"
              label="场景名称"
              class="mango-form-item__require"
              :rules="[{ required: true, message: '请输入场景名称' }]"
              ><a-input
                v-model="form.name"
                placeholder="请输入便于识别的场景名称"
                :max-length="128" /></a-form-item
          ></a-grid-item>
          <a-grid-item
            ><a-form-item
              field="project_product"
              label="项目产品"
              class="mango-form-item__require"
              :rules="[{ required: true, message: '请选择项目产品' }]"
              ><ProjectProductSelect v-model="form.project_product" /></a-form-item
          ></a-grid-item>
          <a-grid-item
            ><a-form-item
              field="module"
              label="产品模块"
              class="mango-form-item__require"
              :rules="[{ required: true, message: '请选择产品模块' }]"
              ><ProductModuleSelect
                v-model="form.module"
                :project-product-id="productId(form.project_product)" /></a-form-item
          ></a-grid-item>
          <a-grid-item
            ><a-form-item
              field="engine"
              label="执行引擎"
              class="mango-form-item__require"
              :rules="[{ required: true, message: '请选择执行引擎' }]"
              ><a-select v-model="form.engine" :options="engineOptions" placeholder="请选择执行引擎" /></a-form-item
          ></a-grid-item>
          <a-grid-item
            ><a-form-item
              field="load_type"
              label="负载模型"
              class="mango-form-item__require"
              :rules="[{ required: true, message: '请选择负载模型' }]"
              ><a-select
                v-model="form.load_type"
                :options="loadTypeOptions"
                placeholder="请选择负载模型" /></a-form-item
          ></a-grid-item>
          <a-grid-item
            ><a-form-item
              field="default_executor_count"
              label="执行器数"
              class="mango-form-item__require"
              :rules="[{ required: true, message: '请输入执行器数量' }]"
              ><a-input-number
                v-model="form.default_executor_count"
                :min="1"
                :max="100"
                placeholder="请输入 1-100" /></a-form-item
          ></a-grid-item>
          <a-grid-item :span="2"
            ><a-form-item field="description" label="说明"
              ><a-textarea
                v-model="form.description"
                placeholder="可填写测试目标、业务范围或注意事项"
                :max-length="1000"
                show-word-limit
                :auto-size="{ minRows: 2, maxRows: 4 }" /></a-form-item
          ></a-grid-item>
        </a-grid>
      </a-form>
    </template>
  </ModalDialog>
</template>

<script setup lang="ts">
  import { Message, Modal } from '@arco-design/web-vue'
  import { onMounted, reactive, ref } from 'vue'
  import { useRouter } from 'vue-router'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import ModalDialog from '@/components/overlays/ModalDialog.vue'
  import { usePagination } from '@/hooks/table'
  import { formatModulePath, formatProjectProductPath } from '@/utils/business-format'
  import {
    createPerfScenario,
    deletePerfScenario,
    getPerfScenarios,
    updatePerfScenario,
  } from '@/api/perf'
  import { engineOptions, loadTypeOptions, scenarioColumns, scenarioScrollX } from './config'

  const router = useRouter()
  const rows = ref<any[]>([])
  const loading = ref(false)
  const createDialogRef = ref<InstanceType<typeof ModalDialog> | null>(null)
  const createFormRef = ref<any>(null)
  const resetKey = ref(0)
  const filters = reactive<any>({
    name: '',
    load_type: [],
    project_product: undefined,
    module: undefined,
  })
  const form = reactive<any>({
    name: '',
    project_product: undefined,
    module: undefined,
    engine: 'k6',
    load_type: 'concurrency',
    default_executor_count: 1,
    execution_mode: 'sequential',
    node_failure_policy: 'strict',
    user_wait_min_ms: 0,
    user_wait_max_ms: 0,
    status: 1,
    tags: [],
  })
  const pagination = usePagination(load, () => loading)

  function productId(value: any) {
    return Array.isArray(value) ? value[value.length - 1] : value
  }
  function loadTitle(value: string) {
    return loadTypeOptions.find((item) => item.value === value)?.label || value
  }
  function loadTarget(record: any) {
    if (record.load_type === 'concurrency') return `${record.target_users || 0} 用户`
    return `${record.target_rate || 0} 请求/${record.rate_time_unit === 'minute' ? '分钟' : '秒'}`
  }
  function query() {
    const params = Object.fromEntries(
      Object.entries({
        ...filters,
        project_product: productId(filters.project_product),
        page: pagination.page,
        pageSize: pagination.pageSize,
      }).filter(([, value]) => value !== '' && value !== undefined && value !== null)
    )
    delete params.load_type
    if (filters.load_type.length) params.load_type__in = filters.load_type.join(',')
    return params
  }
  async function load() {
    loading.value = true
    try {
      const response: any = await getPerfScenarios(query())
      rows.value = response.data || []
      pagination.setTotalSize(response.totalSize || 0)
    } finally {
      loading.value = false
    }
  }
  function onNavigation(value: any) {
    filters.project_product = value.projectProduct || undefined
    filters.module = value.module || undefined
    pagination.page = 1
    load()
  }
  function resetSearch() {
    filters.name = ''
    filters.load_type = []
    resetKey.value += 1
    load()
  }
  async function openCreate() {
    Object.assign(form, {
      name: '',
      project_product: filters.project_product,
      module: filters.module,
      engine: 'k6',
      load_type: 'concurrency',
      default_executor_count: 1,
      execution_mode: 'sequential',
      node_failure_policy: 'strict',
      user_wait_min_ms: 0,
      user_wait_max_ms: 0,
      status: 1,
      tags: [],
    })
    createFormRef.value?.clearValidate?.()
    await createDialogRef.value?.show()
  }
  async function saveCreate() {
    const errors = await createFormRef.value?.validate()
    if (errors) {
      createDialogRef.value?.setConfirmLoading(false)
      return
    }
    try {
      const response: any = await createPerfScenario({
        ...form,
        project_product: productId(form.project_product),
      })
      await createDialogRef.value?.close()
      Message.success('场景已创建')
      router.push({ path: '/perf/scenario/details', query: { id: response.data.id } })
    } finally {
      createDialogRef.value?.setConfirmLoading(false)
    }
  }
  function goDetail(record: any) {
    router.push({ path: '/perf/scenario/details', query: { id: record.id } })
  }
  async function toggleStatus(record: any, value: any) {
    await updatePerfScenario({ id: record.id, status: value })
    record.status = value
    return true
  }
  function execute(record: any) {
    router.push({ path: '/perf/scenario/details', query: { id: record.id, execute: '1' } })
  }
  function remove(record: any) {
    Modal.warning({
      title: '删除性能场景',
      content: `确认删除“${record.name}”吗？`,
      hideCancel: false,
      okButtonProps: { status: 'danger' },
      async onOk() {
        await deletePerfScenario(record.id)
        Message.success('删除成功')
        load()
      },
    })
  }
  onMounted(load)
</script>
