<template>
  <a-modal
    :visible="visible"
    title="从用例库关联用例"
    :width="760"
    :ok-loading="saving"
    :ok-button-props="{ disabled: loading || !selectedKeys.length }"
    :on-before-ok="save"
    :on-before-cancel="canCancel"
    @update:visible="onVisibleChange"
  >
    <div class="mango-requirement-picker">
      
      <MangoRequestFeedback v-if="saveError" :message="&quot;关联失败，勾选项已保留，请重试。&quot;" />
      <a-table
        class="mango-native-scroll-table mango-requirement-picker__table"
        :data="rows"
        :columns="casePickerColumns"
        :selected-keys="selectedKeys"
        :row-selection="{ type: 'checkbox', showCheckedAll: true }"
        :loading="loading"
        :pagination="false"
        :scroll="{ x: 740, y: '100%' }"
        row-key="id"
        @selection-change="selectRows"
      >
        <template #priority="{ record }">
          <a-tag :color="priorityColors?.[record.priority]">{{
            priorityOptions.find((item) => Number(item.key) === record.priority)?.title || '-'
          }}</a-tag>
        </template>
      </a-table>
    </div>
  </a-modal>
</template>
<script setup lang="ts">
  import { requestFailureMessage, reportLoadError } from '@/utils/load-error'
  import { onActivated, onBeforeUnmount, onDeactivated, ref, shallowRef, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { bindFunctionalRequirementCases, getManualCase } from '@/api/functional-test'
  import { casePickerColumns } from '../config'
  import type { RequirementCaseRow } from '../types'

  const props = defineProps<{
    contextKey: string
    requirementId: number | null
    productId: number | null
    available: boolean
    boundIds: number[]
    priorityOptions: Array<{ key: number | string; title: string }>
    priorityColors?: Record<number, string>
  }>()
  const emit = defineEmits<{ (event: 'changed', requirementId: number): void }>()
  const visible = ref(false),
    loading = ref(false),
    saving = ref(false)
  const readError = ref(false),
    saveError = ref(false)
  const rows = shallowRef<RequirementCaseRow[]>([])
  const selectedKeys = ref<number[]>([])
  const subject = shallowRef<{
    requirementId: number
    productId: number
    boundIds: number[]
  } | null>(null)
  let active = true,
    generation = 0,
    readSequence = 0
  const positiveId = (value: unknown): value is number =>
    typeof value === 'number' && Number.isSafeInteger(value) && value > 0
  const current = (version: number) =>
    active && visible.value && props.available && generation === version
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
  }
  function onVisibleChange(value: boolean) {
    if (!value && !saving.value) reset()
  }
  function open() {
    if (
      !active ||
      saving.value ||
      !props.available ||
      !positiveId(props.requirementId) ||
      !positiveId(props.productId)
    )
      return
    reset()
    subject.value = {
      requirementId: props.requirementId,
      productId: props.productId,
      boundIds: [...props.boundIds],
    }
    visible.value = true
    void loadCases()
  }
  function parseCase(value: unknown): RequirementCaseRow {
    if (!value || typeof value !== 'object' || Array.isArray(value)) throw Error('用例格式错误')
    const row = value as Readonly<Record<string, unknown>>
    if (!positiveId(row.id)) throw Error('用例 ID 无效')
    const owner = row.owner && typeof row.owner === 'object' ? Reflect.get(row.owner, 'name') : null
    return {
      id: row.id,
      case_no: typeof row.case_no === 'string' ? row.case_no : '',
      title: typeof row.title === 'string' ? row.title : '',
      priority: typeof row.priority === 'number' ? row.priority : null,
      owner: typeof owner === 'string' ? { name: owner } : null,
    }
  }
  async function loadCases() {
    if (!active || !visible.value || !props.available || !subject.value || saving.value)
      return false
    const version = generation,
      sequence = ++readSequence,
      target = subject.value
    const valid = () => current(version) && readSequence === sequence
    loading.value = true
    readError.value = false
    try {
      const data: unknown = (
        await getManualCase({ project_product: target.productId, page: 1, pageSize: 500 })
      ).data
      if (!valid()) return false
      if (!Array.isArray(data)) throw Error('用例列表格式错误')
      const bound = new Set([...target.boundIds, ...props.boundIds])
      const next = data.map(parseCase).filter((row) => !bound.has(row.id))
      const available = new Set(next.map((row) => row.id))
      rows.value = next
      selectedKeys.value = selectedKeys.value.filter((id) => available.has(id))
      return true
    } catch (loadFailure0) {
      if (valid()) (reportLoadError(loadFailure0, "加载失败，请重试", false), readError.value = true)
      return false
    } finally {
      if (valid()) loading.value = false
    }
  }
  function selectRows(keys: Array<number | string>) {
    if (!active || !visible.value || !props.available || loading.value || saving.value) return
    const available = new Set(rows.value.map((row) => row.id))
    selectedKeys.value = [...new Set(keys.map(Number))].filter(
      (id) => positiveId(id) && available.has(id)
    )
  }
  async function save() {
    if (
      !active ||
      !visible.value ||
      !props.available ||
      !subject.value ||
      loading.value ||
      saving.value
    )
      return false
    const version = generation,
      target = subject.value.requirementId
    const available = new Set(rows.value.map((row) => row.id))
    const bound = new Set(props.boundIds)
    const ids = [...new Set(selectedKeys.value)].filter(
      (id) => positiveId(id) && available.has(id) && !bound.has(id)
    )
    if (!ids.length) {
      Message.warning('请选择用例')
      return false
    }
    saving.value = true
    saveError.value = false
    try {
      const data: unknown = (await bindFunctionalRequirementCases(target, [...ids])).data
      if (!current(version)) return false
      const count: unknown =
        data && typeof data === 'object' && !Array.isArray(data)
          ? Reflect.get(data, 'bound_count')
          : null
      if (typeof count !== 'number' || !Number.isSafeInteger(count) || count < 0)
        throw Error('关联结果未确认')
      reset()
      Message.success('用例已关联')
      emit('changed', target)
    } catch (requestFailure) {
      if (current(version)) saveError.value = requestFailureMessage(requestFailure, true, "关联失败，勾选项已保留，请重试。")
    } finally {
      saving.value = false
    }
    return false
  }
  watch(
    [
      () => props.contextKey,
      () => props.requirementId,
      () => props.productId,
      () => props.available,
    ],
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
  .mango-requirement-picker {
    display: flex;
    height: min(460px, 55vh);
    min-height: 0;
    flex-direction: column;
    gap: var(--m-page-gap);
  }
  .mango-requirement-picker__table {
    flex: 1;
    height: 0;
    min-height: 0;
  }
</style>
