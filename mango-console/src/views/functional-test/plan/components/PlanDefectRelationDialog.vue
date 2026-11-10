<template>
  <a-modal
    modal-class="mango-simple-form-modal"
    v-model:visible="visible"
    :title="mode === 'bind' ? '关联已有缺陷' : '取消缺陷关联'"
    :width="560"
    :ok-loading="saving"
    :on-before-ok="save"
    :on-before-cancel="canCancel"
    @cancel="reset"
  >

    <a-alert v-if="saveError" type="error" class="mango-plan-relation__notice"
      >操作失败，选择已保留，请重试。</a-alert
    >
    <a-form class="mango-simple-form" :model="form" layout="horizontal" auto-label-width :disabled="saving">
      <a-form-item class="mango-simple-form-item" label="缺陷" required
        ><a-select
          v-model="form.defectId"
          :options="options"
          :loading="loading"
          allow-search
          :placeholder="mode === 'bind' ? '当前产品下未关闭缺陷' : '请选择关联缺陷'"
      /></a-form-item>
    </a-form>
    <a-alert :type="mode === 'bind' ? 'info' : 'warning'"
      >{{ mode === 'bind' ? '关联' : '取消关联' }}已选的
      {{ subject?.caseIds.length || 0 }} 条计划用例，不会删除缺陷或修改执行结果。</a-alert
    >
  </a-modal>
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
  import {
    bindFunctionalDefectCases,
    getFunctionalDefectOptions,
    unbindFunctionalDefectCases,
  } from '@/api/functional-test'
  import type { PlanDefectOption } from '../types'
  const props = defineProps<{ contextKey: string; planId: number; productId: number | null }>()
  const emit = defineEmits<{ (event: 'changed', planId: number): void }>()
  const visible = ref(false),
    saving = ref(false),
    loading = ref(false)
  const readError = ref(false),
    saveError = ref(false)
  const mode = ref<'bind' | 'unbind'>('bind')
  const form = reactive({ defectId: null as number | null })
  const options = shallowRef<PlanDefectOption[]>([])
  const subject = shallowRef<{ planId: number; productId: number; caseIds: number[] } | null>(null)
  let active = true,
    generation = 0,
    readSequence = 0
  const positiveId = (value: unknown): value is number =>
    typeof value === 'number' && Number.isSafeInteger(value) && value > 0
  const current = (version: number) => active && visible.value && generation === version
  const canCancel = () => !saving.value
  const isSaving = () => saving.value
  function reset() {
    ++generation
    ++readSequence
    visible.value = false
    subject.value = null
    form.defectId = null
    options.value = []
    loading.value = false
    readError.value = false
    saveError.value = false
  }
  function open(operation: 'bind' | 'unbind', caseIds: number[], related: PlanDefectOption[] = []) {
    if (!active || saving.value || !positiveId(props.planId) || !positiveId(props.productId)) return
    const ids = [...new Set(caseIds)].filter(positiveId)
    if (!ids.length || (operation === 'unbind' && !related.length)) return
    reset()
    mode.value = operation
    subject.value = { planId: props.planId, productId: props.productId, caseIds: ids }
    visible.value = true
    if (operation === 'bind') void loadOptions()
    else {
      options.value = related
        .filter((item) => positiveId(item.value))
        .map((item) => ({ value: item.value, label: item.label }))
      form.defectId = options.value[0]?.value ?? null
    }
  }
  async function loadOptions() {
    if (!active || !visible.value || !subject.value || mode.value !== 'bind' || saving.value)
      return false
    const version = generation,
      sequence = ++readSequence
    const valid = () => current(version) && readSequence === sequence
    loading.value = true
    readError.value = false
    try {
      const data: unknown = (
        await getFunctionalDefectOptions({ project_product: subject.value.productId })
      ).data
      if (!valid()) return false
      if (!Array.isArray(data)) throw Error('缺陷选项格式错误')
      options.value = data.map((value) => {
        if (!value || typeof value !== 'object' || Array.isArray(value))
          throw Error('缺陷选项格式错误')
        const row = value as Readonly<Record<string, unknown>>
        if (
          !positiveId(row.id) ||
          typeof row.title !== 'string' ||
          typeof row.defect_no !== 'string'
        )
          throw Error('缺陷选项格式错误')
        return { value: row.id, label: `${row.defect_no} ${row.title}` }
      })
      if (!options.value.some((item) => item.value === form.defectId)) form.defectId = null
      return true
    } catch (loadFailure0) {
      if (valid()) (reportLoadError(loadFailure0, "加载失败，请重试", false), readError.value = true)
      return false
    } finally {
      if (valid()) loading.value = false
    }
  }
  async function save() {
    if (!active || !visible.value || !subject.value || saving.value || loading.value) return false
    if (!form.defectId || !options.value.some((item) => item.value === form.defectId)) {
      Message.warning('请选择缺陷')
      return false
    }
    const version = generation,
      planId = subject.value.planId,
      operation = mode.value
    const payload = { id: form.defectId, plan_case_ids: [...subject.value.caseIds] }
    saving.value = true
    saveError.value = false
    try {
      const data: unknown = (
        await (operation === 'bind'
          ? bindFunctionalDefectCases(payload)
          : unbindFunctionalDefectCases(payload))
      ).data
      if (!current(version)) return false
      const count: unknown =
        data && typeof data === 'object' && !Array.isArray(data)
          ? Reflect.get(data, operation === 'bind' ? 'created_count' : 'deleted_count')
          : null
      if (typeof count !== 'number' || !Number.isSafeInteger(count) || count < 0)
        throw Error('操作结果未确认')
      reset()
      Message.success(operation === 'bind' ? '已关联缺陷' : '已取消缺陷关联')
      emit('changed', planId)
    } catch {
      if (current(version)) saveError.value = true
    } finally {
      saving.value = false
    }
    return false
  }
  watch([() => props.contextKey, () => props.planId, () => props.productId], reset, {
    flush: 'sync',
  })
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
  .mango-plan-relation__notice {
    margin-bottom: var(--m-page-gap);
  }
</style>
