<template>
  <a-drawer
    :visible="visible"
    title="从用例库选择"
    :width="900"
    :on-before-cancel="canCancel"
    @update:visible="onVisibleChange"
  >
    <div class="mango-plan-picker">
      <TableSearchPanel
        class="mango-plan-picker__search"
        @search="loadCases"
        @reset-search="resetSearch"
      >
        <a-form :model="filters" layout="inline" :disabled="saving" @keyup.enter="loadCases">
          <a-form-item label="模块"
            ><ProductModuleSelect
              v-if="visible"
              v-model="filters.module"
              :project-product-id="subject?.productId"
              :selectable-level="0"
              :refresh-token="contextKey"
              :disabled="saving"
              placeholder="全部模块"
          /></a-form-item>
          <a-form-item label="用例标题"
            ><a-input v-model="filters.title" allow-clear
          /></a-form-item>
          <a-form-item label="分类一"
            ><a-input v-model="filters.category_level_1" allow-clear
          /></a-form-item>
        </a-form>
      </TableSearchPanel>

      <a-alert v-if="saveError" type="error">加入计划失败，已保留勾选项，请重试。</a-alert>
      <a-table
        class="mango-native-scroll-table mango-plan-picker__table"
        :data="rows"
        :columns="planLibraryColumns"
        :selected-keys="selectedKeys"
        :row-selection="{ type: 'checkbox', showCheckedAll: true }"
        :loading="loading"
        :pagination="false"
        row-key="id"
        :scroll="{ x: 1000, y: '100%' }"
        @selection-change="selectRows"
      >
        <template #priority="{ record }"
          ><a-tag :color="priorityColors?.[record.priority]">{{
            priorityOptions.find((item) => Number(item.key) === record.priority)?.title || '-'
          }}</a-tag></template
        >
      </a-table>
    </div>
    <template #footer>
      <a-space wrap>
        <span>已选 {{ selectedKeys.length }} 条</span>
        <a-button size="small" :disabled="saving" @click="onVisibleChange(false)">取消</a-button>
        <a-button
          size="small"
          type="primary"
          :loading="saving"
          :disabled="loading || !selectedKeys.length"
          @click="save"
          >加入计划</a-button
        >
      </a-space>
    </template>
  </a-drawer>
</template>
<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import {
    onActivated,
    onBeforeUnmount,
    onDeactivated,
    reactive,
    ref,
    shallowRef,
    watch,
  } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { addFunctionalPlanCases, getManualCase } from '@/api/functional-test'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import TableSearchPanel from '@/components/table/TableSearchPanel.vue'
  import { planLibraryColumns } from '../case-picker-config'
  import type { PlanLibraryCase } from '../types'

  const props = defineProps<{
    contextKey: string
    planId: number
    productId: number | null
    editable: boolean
    priorityOptions: Array<{ key: number | string; title: string }>
    priorityColors?: Record<number, string>
  }>()
  const emit = defineEmits<{ (event: 'changed', planId: number): void }>()
  const visible = ref(false),
    loading = ref(false),
    saving = ref(false)
  const readError = ref(false),
    saveError = ref(false)
  const rows = shallowRef<PlanLibraryCase[]>([])
  const selectedKeys = ref<number[]>([])
  const filters = reactive({
    module: null as number | string | null,
    title: '',
    category_level_1: '',
  })
  const subject = shallowRef<{ planId: number; productId: number } | null>(null)
  let active = true,
    generation = 0,
    readSequence = 0
  const positiveId = (value: unknown): value is number =>
    typeof value === 'number' && Number.isSafeInteger(value) && value > 0
  const current = (version: number) =>
    active && visible.value && generation === version && props.editable
  const canCancel = () => !saving.value
  const isSaving = () => saving.value
  function reset() {
    ++generation
    ++readSequence
    visible.value = false
    subject.value = null
    rows.value = []
    selectedKeys.value = []
    loading.value = false
    readError.value = false
    saveError.value = false
    Object.assign(filters, { module: null, title: '', category_level_1: '' })
  }
  function onVisibleChange(value: boolean) {
    if (!value && !saving.value) reset()
  }
  function open() {
    if (
      !active ||
      saving.value ||
      !props.editable ||
      !positiveId(props.planId) ||
      !positiveId(props.productId)
    )
      return
    reset()
    subject.value = { planId: props.planId, productId: props.productId }
    visible.value = true
    void loadCases()
  }
  function selectRows(keys: Array<string | number>) {
    if (!active || !visible.value || loading.value || saving.value) return
    const available = new Set(rows.value.map((row) => row.id))
    selectedKeys.value = [...new Set(keys.map(Number))].filter(
      (key) => positiveId(key) && available.has(key)
    )
  }
  function parseRow(value: unknown): PlanLibraryCase {
    if (!value || typeof value !== 'object' || Array.isArray(value)) throw Error('用例格式错误')
    const item = value as Readonly<Record<string, unknown>>
    if (!positiveId(item.id)) throw Error('用例 ID 无效')
    const text = (key: string) => (typeof item[key] === 'string' ? (item[key] as string) : '')
    return {
      id: item.id,
      case_no: text('case_no'),
      title: text('title'),
      category_level_1: text('category_level_1'),
      category_level_2: text('category_level_2'),
      category_level_3: text('category_level_3'),
      priority: typeof item.priority === 'number' ? item.priority : null,
    }
  }
  async function loadCases() {
    if (!subject.value || !active || !visible.value || !props.editable || saving.value) return false
    const version = generation,
      sequence = ++readSequence
    const valid = () => current(version) && readSequence === sequence
    const query: Record<string, unknown> = {
      project_product: subject.value.productId,
      status: 1,
      page: 1,
      pageSize: 500,
    }
    for (const key of ['module', 'title', 'category_level_1'] as const) {
      const value = filters[key]
      if (value !== null && value !== undefined && value !== '') query[key] = value
    }
    loading.value = true
    readError.value = false
    try {
      const data: unknown = (await getManualCase(query)).data
      if (!valid()) return false
      if (!Array.isArray(data)) throw Error('列表格式错误')
      rows.value = data.map(parseRow)
      const available = new Set(rows.value.map((row) => row.id))
      selectedKeys.value = selectedKeys.value.filter((key) => available.has(key))
      return true
    } catch (loadFailure0) {
      if (valid()) (reportLoadError(loadFailure0, "加载失败，请重试", false), readError.value = true)
      return false
    } finally {
      if (valid()) loading.value = false
    }
  }
  function resetSearch() {
    if (saving.value) return
    Object.assign(filters, { module: null, title: '', category_level_1: '' })
    selectedKeys.value = []
    return loadCases()
  }
  async function save() {
    if (
      !subject.value ||
      !active ||
      !visible.value ||
      loading.value ||
      saving.value ||
      !props.editable
    )
      return false
    const version = generation,
      planId = subject.value.planId
    const available = new Set(rows.value.map((row) => row.id))
    const ids = selectedKeys.value.filter((id) => available.has(id))
    if (!ids.length) {
      Message.warning('请选择用例')
      return false
    }
    const payload = { plan_id: planId, case_ids: [...ids] }
    saving.value = true
    saveError.value = false
    try {
      const data: unknown = (await addFunctionalPlanCases(payload)).data
      if (!current(version)) return false
      if (!data || typeof data !== 'object' || Array.isArray(data)) throw Error('加入结果未确认')
      for (const key of ['created_count', 'ignored_count']) {
        const count: unknown = Reflect.get(data, key)
        if (typeof count !== 'number' || !Number.isSafeInteger(count) || count < 0)
          throw Error('加入结果未确认')
      }
      reset()
      Message.success('已加入计划')
      emit('changed', planId)
      return true
    } catch {
      if (current(version)) saveError.value = true
      return false
    } finally {
      saving.value = false
    }
  }
  watch(
    [() => props.contextKey, () => props.planId, () => props.productId, () => props.editable],
    reset,
    { flush: 'sync' }
  )
  onDeactivated(() => {
    active = false
    reset()
  })
  onActivated(() => {
    active = true
  })
  onBeforeUnmount(() => {
    active = false
    reset()
  })
  defineExpose({ open, isSaving, isOpen: () => visible.value })
</script>
<style scoped>
  .mango-plan-picker {
    display: flex;
    height: 100%;
    min-height: 0;
    flex-direction: column;
    gap: var(--m-page-gap);
  }
  .mango-plan-picker__search {
    flex: none;
  }
  .mango-plan-picker__table {
    flex: 1;
    height: 0;
    min-height: 0;
  }
</style>
