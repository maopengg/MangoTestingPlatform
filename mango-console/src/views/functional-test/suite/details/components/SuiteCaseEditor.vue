<template>
  <a-drawer
    :visible="visible"
    title="功能测试用例"
    :width="760"
    :on-before-cancel="canCancel"
    :mask-closable="!saving"
    :esc-to-close="!saving"
    @update:visible="onVisibleChange"
  >
    <a-alert v-if="saveError" type="error" class="mango-suite-case-editor__error"
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
        <a-grid-item :span="2"
          ><a-alert type="info" class="mango-suite-case-editor__tip"
            >P0 发布阻塞风险；P1 常规回归与重点分支；P2 边界和低频分支；P3
            低价值或暂不优先自动化。</a-alert
          ></a-grid-item
        >
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
          ><a-alert type="info" class="mango-suite-case-editor__tip"
            >层级建议：接口/组件级约 70%，模块级约 20%，端到端约
            10%。验证类型用于区分正常、异常、边界、权限、数据和流程；执行场景统一使用回归、发布验证、冒烟、稳定性监测、数据校验、效果评测、生产巡检和生产回归。</a-alert
          ></a-grid-item
        >
        <a-grid-item :span="2"
          ><a-form-item label="用例标题" required><a-input v-model="form.title" /></a-form-item
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
        <a-grid-item :span="2"
          ><a-form-item label="前置条件"
            ><a-textarea
              v-model="form.precondition"
              :auto-size="{ minRows: 2, maxRows: 5 }" /></a-form-item
        ></a-grid-item>
        <a-grid-item :span="2"
          ><a-form-item label="测试场景" required
            ><a-textarea
              v-model="form.test_point"
              :auto-size="{ minRows: 3, maxRows: 7 }" /></a-form-item
        ></a-grid-item>
        <a-grid-item :span="2"
          ><a-form-item label="测试数据"
            ><a-textarea
              v-model="form.test_data"
              :auto-size="{ minRows: 2, maxRows: 5 }" /></a-form-item
        ></a-grid-item>
        <a-grid-item :span="2"
          ><a-form-item label="备注"
            ><a-textarea
              v-model="form.remark"
              :auto-size="{ minRows: 2, maxRows: 5 }" /></a-form-item
        ></a-grid-item>
      </a-grid>
    </a-form>
    <template #footer
      ><a-space
        ><a-button size="small" :disabled="saving" @click="cancel">取消</a-button
        ><a-button size="small" type="primary" :loading="saving" :disabled="blocked" @click="save"
          >保存</a-button
        ></a-space
      ></template
    >
  </a-drawer>
</template>
<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { computed, onActivated, onBeforeUnmount, onDeactivated, reactive, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import { useEnum } from '@/store/modules/get-enum'
  import { postManualCase, putManualCase } from '@/api/functional-test'
  import { getUserName } from '@/api/user/user'
  import {
    createSuiteCaseForm,
    relationId,
    suiteCasePayload,
    suiteCaseValidation,
    savedCaseMatches,
  } from '../case-form'
  import type {
    ProductSelection,
    SuiteCaseDefaults,
    SuiteCaseForm,
    SuiteCaseRecord,
  } from '../case-form'
  import { resourceId, objectValue } from '../resource-form'
  const props = defineProps<{
    suiteId: number | null
    contextKey: string
    available: boolean
    blocked: boolean
    defaults: SuiteCaseDefaults
  }>()
  const emit = defineEmits<{
    (event: 'changed', suiteId: number): void
    (event: 'busy', value: boolean): void
  }>()
  const enumStore = useEnum(),
    fieldNames = { value: 'key', label: 'title' }
  const visible = ref(false),
    saving = ref(false),
    saveError = ref(false)
  const usersLoading = ref(false),
    usersError = ref(false)
  const users = ref<Array<{ key: number; title: string }>>([])
  const fallbackOwner = ref('')
  const form: SuiteCaseForm = reactive(createSuiteCaseForm())
  const ownerOptions = computed(() => {
    const id = relationId(form.owner)
    return id !== null && !users.value.some((item) => item.key === id)
      ? [...users.value, { key: id, title: fallbackOwner.value || `ID ${id}` }]
      : users.value
  })
  let active = true,
    generation = 0,
    userSequence = 0,
    previousProduct: number | null = null
  let subject: { suiteId: number; contextKey: string } | null = null
  const current = (version: number) =>
    active &&
    visible.value &&
    props.available &&
    generation === version &&
    subject?.suiteId === props.suiteId &&
    subject?.contextKey === props.contextKey
  const canCancel = () => !saving.value
  function reset() {
    ++generation
    ++userSequence
    visible.value = false
    saveError.value = false
    subject = null
    users.value = []
    usersError.value = false
    usersLoading.value = false
    fallbackOwner.value = ''
    previousProduct = null
    Object.assign(form, createSuiteCaseForm())
  }
  function cancel() {
    if (canCancel()) reset()
  }
  function onVisibleChange(value: boolean) {
    if (!value) cancel()
  }
  function open(record?: SuiteCaseRecord) {
    if (!active || saving.value || props.blocked || !props.available || !resourceId(props.suiteId))
      return
    if (record && (!resourceId(record.id) || relationId(record.suite) !== props.suiteId)) return
    reset()
    subject = { suiteId: props.suiteId!, contextKey: props.contextKey }
    Object.assign(form, createSuiteCaseForm(props.defaults, record))
    const owner = objectValue(record?.owner)
    fallbackOwner.value =
      typeof owner.name === 'string'
        ? owner.name
        : typeof owner.username === 'string'
        ? owner.username
        : ''
    previousProduct = relationId(form.project_product)
    visible.value = true
    void loadUsers()
  }
  function onProductChange(value: ProductSelection) {
    const id = relationId(value)
    if (id !== previousProduct) form.module = null
    previousProduct = id
  }
  async function loadUsers() {
    if (!current(generation) || saving.value) return
    const version = generation,
      sequence = ++userSequence
    usersLoading.value = true
    usersError.value = false
    try {
      const response = await getUserName()
      if (!current(version) || sequence !== userSequence) return
      if (!Array.isArray(response.data)) throw new Error('Invalid users response')
      const options: Array<{ key: number; title: string }> = []
      for (const item of response.data as unknown[]) {
        const option = objectValue(item),
          id = resourceId(option.key)
        if (!id || typeof option.title !== 'string') throw new Error('Invalid user option')
        options.push({ key: id, title: option.title })
      }
      users.value = options
    } catch (loadFailure0) {
      if (current(version) && sequence === userSequence) (reportLoadError(loadFailure0, "加载失败，请重试", false), usersError.value = true)
    } finally {
      if (current(version) && sequence === userSequence) usersLoading.value = false
    }
  }
  async function save() {
    if (saving.value || props.blocked || !subject || !current(generation)) return false
    const message = suiteCaseValidation(form)
    if (message) {
      Message.error(message)
      return false
    }
    const version = generation,
      target = { ...subject },
      id = form.id
    const payload = suiteCasePayload(form, target.suiteId)
    saving.value = true
    emit('busy', true)
    saveError.value = false
    try {
      const response = await (id === null ? postManualCase(payload) : putManualCase(payload))
      if (!current(version)) return false
      if (!savedCaseMatches(response.data, target.suiteId, id))
        throw new Error('Invalid case response')
      reset()
      Message.success('保存成功')
      emit('changed', target.suiteId)
      return true
    } catch {
      if (current(version)) saveError.value = true
      return false
    } finally {
      saving.value = false
      emit('busy', false)
    }
  }
  watch(() => [props.contextKey, props.suiteId, props.available], reset, { flush: 'sync' })
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
  .mango-suite-case-editor__error,
  .mango-suite-case-editor__tip {
    margin-bottom: var(--m-page-gap);
  }
</style>
