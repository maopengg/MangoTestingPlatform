<template>
  <a-drawer
    :visible="visible"
    title="编辑测试用例"
    :width="760"
    :on-before-cancel="canCancel"
    :mask-closable="!saving"
    :esc-to-close="!saving"
    @update:visible="onVisibleChange"
  >
    <a-alert v-if="saveError" type="error" class="mango-suite-list-case-editor__notice"
      >保存失败，输入已保留。若版本冲突，请核对最新记录后重试。</a-alert
    >

    <a-form :model="form" layout="horizontal" :disabled="saving">
      <a-grid :cols="2" :col-gap="16">
        <a-grid-item
          ><a-form-item label="用例编号" required><a-input v-model="form.case_no" /></a-form-item
        ></a-grid-item>
        <a-grid-item
          ><a-form-item label="优先级" required
            ><a-select
              v-model="form.priority"
              :options="enumStore.case_level"
              :field-names="fieldNames" /></a-form-item
        ></a-grid-item>
        <a-grid-item :span="2"
          ><a-form-item label="用例标题" required><a-input v-model="form.title" /></a-form-item
        ></a-grid-item>
        <a-grid-item :span="2"
          ><a-form-item label="测试场景" required
            ><a-textarea
              v-model="form.test_point"
              :auto-size="{ minRows: 3, maxRows: 7 }" /></a-form-item
        ></a-grid-item>
        <a-grid-item :span="2"
          ><a-form-item label="测试类型" required
            ><a-select
              v-model="form.test_types"
              :options="enumStore.manual_test_type"
              :field-names="fieldNames"
              multiple /></a-form-item
        ></a-grid-item>
        <a-grid-item
          ><a-form-item label="项目产品" required
            ><ProjectProductSelect
              v-model="form.project_product"
              :disabled="saving"
              @change="onProductChange" /></a-form-item
        ></a-grid-item>
        <a-grid-item
          ><a-form-item label="模块名称" required
            ><ProductModuleSelect
              v-model="form.module"
              :project-product-id="form.project_product"
              :auto-clear="false"
              :disabled="saving" /></a-form-item
        ></a-grid-item>
        <a-grid-item
          ><a-form-item label="测试层级" required
            ><a-select
              v-model="form.scenario_layer"
              :options="enumStore.api_case_scenario_layer"
              :field-names="fieldNames" /></a-form-item
        ></a-grid-item>
        <a-grid-item
          ><a-form-item label="验证类型" required
            ><a-select
              v-model="form.scenario_type"
              :options="enumStore.api_case_scenario_type"
              :field-names="fieldNames" /></a-form-item
        ></a-grid-item>
        <a-grid-item :span="2"
          ><a-form-item label="执行场景" required
            ><a-select
              v-model="form.scenario_tags"
              :options="enumStore.api_case_scenario_tag"
              :field-names="fieldNames"
              multiple /></a-form-item
        ></a-grid-item>
        <a-grid-item :span="2"
          ><a-form-item label="负责人" required
            ><a-select
              v-model="form.owner"
              :options="ownerOptions"
              :loading="usersLoading"
              :field-names="fieldNames"
              allow-search
              placeholder="请选择负责人" /></a-form-item
        ></a-grid-item>
      </a-grid>
    </a-form>
    <template #footer
      ><a-space
        ><a-button :disabled="saving" @click="cancel">取消</a-button
        ><a-button type="primary" :loading="saving" :disabled="blocked" @click="save"
          >保存</a-button
        ></a-space
      ></template
    >
  </a-drawer>
</template>
<script setup lang="ts">
  import { computed, onActivated, onBeforeUnmount, onDeactivated, reactive, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import { useEnum } from '@/store/modules/get-enum'
  import { putManualCase } from '@/api/functional-test'
  import { suiteSelectionId } from '../editor-form'
  import type { SuiteProductSelection } from '../editor-form'
  import { createListCaseForm, listCasePayload, listCaseValidation } from '../list-case-form'
  import type { ListCaseRecord, ListCaseForm } from '../list-case-form'
  const props = defineProps<{
    contextKey: string
    blocked: boolean
    users: Array<{ key: number | string; title: string }>
    usersLoading: boolean
    usersError: boolean
  }>()
  const emit = defineEmits<{
    (event: 'saved', id: number): void
    (event: 'busy', value: boolean): void
    (event: 'visible', value: boolean): void
    (event: 'retry-users'): void
  }>()
  const enumStore = useEnum(),
    fieldNames = { value: 'key', label: 'title' }
  const form: ListCaseForm = reactive(createListCaseForm())
  const visible = ref(false),
    saving = ref(false),
    saveError = ref(false)
  const source = ref<ListCaseRecord | null>(null)
  let active = true,
    generation = 0,
    previousProduct: number | null = null
  const current = (version: number) => active && visible.value && generation === version
  const canCancel = () => !saving.value
  const ownerOptions = computed(() => {
    const options = [...props.users],
      owner = source.value?.owner,
      id = suiteSelectionId(owner)
    if (id !== null && !options.some((option) => String(option.key) === String(id))) {
      const name = owner && typeof owner === 'object' ? owner.name || owner.username : ''
      options.push({ key: id, title: name || `ID ${id}` })
    }
    return options
  })
  function reset() {
    ++generation
    visible.value = false
    source.value = null
    previousProduct = null
    saveError.value = false
    Object.assign(form, createListCaseForm())
  }
  function cancel() {
    if (canCancel()) reset()
  }
  function onVisibleChange(value: boolean) {
    if (!value) cancel()
  }
  function open(record: ListCaseRecord) {
    if (!active || saving.value || props.blocked || !suiteSelectionId(record.id)) return
    reset()
    source.value = {
      id: record.id,
      version_no: record.version_no,
      suite: suiteSelectionId(record.suite),
      owner: record.owner && typeof record.owner === 'object' ? { ...record.owner } : record.owner,
    }
    Object.assign(form, createListCaseForm(record))
    previousProduct = suiteSelectionId(form.project_product)
    visible.value = true
  }
  function onProductChange(value: SuiteProductSelection) {
    const id = suiteSelectionId(value)
    if (id === previousProduct) return
    previousProduct = id
    form.module = null
  }
  async function save() {
    if (!current(generation) || saving.value || props.blocked || !source.value) return
    const message = listCaseValidation(form)
    if (message) {
      Message.error(message)
      return
    }
    const version = generation,
      payload = listCasePayload(form, source.value)
    saving.value = true
    saveError.value = false
    emit('busy', true)
    try {
      const response = await putManualCase(payload)
      if (!current(version)) return
      const result: unknown = response.data
      if (!result || typeof result !== 'object' || Array.isArray(result))
        throw Error('Invalid case acknowledgment')
      const row = result as Record<string, unknown>
      if (
        row.id !== payload.id ||
        row.suite !== payload.suite ||
        row.project_product !== payload.project_product ||
        typeof row.version_no !== 'number' ||
        !Number.isSafeInteger(row.version_no) ||
        row.version_no <= (payload.version_no ?? 0)
      )
        throw Error('Invalid saved case')
      reset()
      Message.success('保存成功')
      emit('saved', payload.id)
    } catch {
      if (current(version)) saveError.value = true
    } finally {
      saving.value = false
      emit('busy', false)
    }
  }
  watch(visible, (value) => emit('visible', value), { flush: 'sync' })
  watch(() => props.contextKey, reset, { flush: 'sync' })
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
  defineExpose({ open })
</script>
<style scoped>
  .mango-suite-list-case-editor__notice {
    margin-bottom: var(--m-page-gap);
  }
</style>
