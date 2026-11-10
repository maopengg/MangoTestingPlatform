<template>
  <a-modal
    modal-class="mango-simple-form-modal"
    :visible="visible"
    :title="recordId === null ? '新增配置文件' : '编辑配置文件'"
    :width="560"
    :ok-loading="saving"
    :on-before-ok="save"
    :on-before-cancel="canCancel"
    :mask-closable="!saving"
    :esc-to-close="!saving"
    @update:visible="onVisibleChange"
  >
    <a-alert v-if="saveError" type="error" class="mango-gray-file-editor__error"
      >保存失败，输入已保留，请重试。</a-alert
    >
    <a-form auto-label-width class="mango-simple-form" :model="form" layout="horizontal" :disabled="saving">
      <a-form-item label="项目/产品" class="mango-form-item__require mango-simple-form-item"
        ><ProjectProductSelect
          v-model="form.project_product"
          :disabled="saving"
          placeholder="请选择项目/产品"
      /></a-form-item>
      <a-form-item label="配置名称" class="mango-form-item__require mango-simple-form-item"
        ><a-input v-model="form.name" placeholder="请输入配置名称"
      /></a-form-item>
      <a-form-item class="mango-simple-form-item" label="等待秒数"
        ><a-input-number v-model="form.effect_wait_seconds" :min="0" placeholder="请输入等待秒数"
      /></a-form-item>
      <a-form-item class="mango-simple-form-item" label="启用状态"
        ><a-switch v-model="form.status" :checked-value="1" :unchecked-value="0"
      /></a-form-item>
    </a-form>
  </a-modal>
</template>
<script setup lang="ts">
  import { onActivated, onBeforeUnmount, onDeactivated, reactive, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import { postGrayYamlFile, putGrayYamlFile } from '@/api/gray'
  import { createYamlForm, yamlPayload, yamlValidation, object, selectionId } from '../forms'
  import type { Selection, YamlForm, YamlRecord } from '../forms'
  const props = defineProps<{ contextKey: string; blocked: boolean }>()
  const emit = defineEmits<{
    (event: 'saved', id: number): void
    (event: 'busy', value: boolean): void
    (event: 'visible', value: boolean): void
  }>()
  const visible = ref(false),
    saving = ref(false),
    saveError = ref(false),
    recordId = ref<number | null>(null)
  const form: YamlForm = reactive(createYamlForm())
  let active = true,
    generation = 0
  const current = (version: number) => active && visible.value && generation === version
  const canCancel = () => !saving.value
  function reset() {
    ++generation
    visible.value = false
    recordId.value = null
    saveError.value = false
    Object.assign(form, createYamlForm())
  }
  function onVisibleChange(value: boolean) {
    if (!value && canCancel()) reset()
  }
  function open(record?: YamlRecord, product?: Selection) {
    if (!active || saving.value || props.blocked || (record && !selectionId(record.id))) return
    reset()
    recordId.value = record?.id ?? null
    Object.assign(form, createYamlForm(record, product))
    visible.value = true
  }
  async function save() {
    if (!current(generation) || saving.value || props.blocked) return false
    const message = yamlValidation(form)
    if (message) {
      Message.warning(message)
      return false
    }
    const version = generation,
      payload = yamlPayload(form, recordId.value)
    saving.value = true
    saveError.value = false
    emit('busy', true)
    try {
      const response = await (recordId.value === null
        ? postGrayYamlFile(payload)
        : putGrayYamlFile(payload))
      if (!current(version)) return false
      const row = object(response.data),
        id = selectionId(row.id)
      if (
        response.code !== 200 ||
        !id ||
        ('id' in payload && payload.id !== id) ||
        row.project_product !== payload.project_product
      )
        throw Error('Invalid saved configuration')
      reset()
      Message.success('保存成功')
      emit('saved', id)
    } catch {
      if (current(version)) saveError.value = true
    } finally {
      saving.value = false
      emit('busy', false)
    }
    return false
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
  .mango-gray-file-editor__error {
    margin-bottom: var(--m-page-gap);
  }
</style>
