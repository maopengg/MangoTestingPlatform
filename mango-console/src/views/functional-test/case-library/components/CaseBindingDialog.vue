<template>
  <a-modal
    modal-class="mango-simple-form-modal"
    v-model:visible="visible"
    title="自动化绑定"
    :width="560"
    :ok-loading="saving"
    :on-before-ok="save"
    :on-before-cancel="canCancel"
    @cancel="reset"
  >
    <a-alert v-if="saveError" type="error" class="mango-library-binding__error"
      >绑定失败，输入已保留，请重试。</a-alert
    >
    <a-form auto-label-width class="mango-simple-form" :model="form" layout="horizontal" :disabled="saving">
      <a-form-item class="mango-simple-form-item" label="自动化类型" required>
        <a-select
          v-model="form.automation_type"
          :options="automationTypes"
          :field-names="fieldNames"
          @change="loadBindingId"
        />
      </a-form-item>
      <a-form-item class="mango-simple-form-item" label="自动化 Case ID" required>
        <a-input-number
          v-model="form.automation_case_id"
          :min="1"
          :precision="0"
          placeholder="输入 API 或 UI 自动化 Case ID"
        />
      </a-form-item>
    </a-form>
  </a-modal>
</template>

<script setup lang="ts">
  import { computed, onActivated, onBeforeUnmount, onDeactivated, reactive, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { useEnum } from '@/store/modules/get-enum'
  import { postManualAutomationBind } from '@/api/functional-test'
  import type { CaseBindingSubject } from '../types'

  const props = defineProps<{ contextKey: string }>()
  const emit = defineEmits<{ (event: 'saved'): void }>()
  const enumStore = useEnum()
  const fieldNames = { value: 'key', label: 'title' }
  const automationTypes = computed(() =>
    (enumStore.manual_test_automation_type ?? []).filter(
      (item) => item.key === 0 || item.key === 1
    )
  )
  const visible = ref(false),
    saving = ref(false),
    saveError = ref(false)
  const subject = ref<CaseBindingSubject | null>(null)
  const form = reactive<{ automation_type: number; automation_case_id: number | null }>({
    automation_type: 0,
    automation_case_id: null,
  })
  let active = true,
    generation = 0
  const current = (value: number) => active && visible.value && value === generation
  const canCancel = () => !saving.value

  function reset() {
    ++generation
    visible.value = false
    saveError.value = false
    subject.value = null
    form.automation_type = 0
    form.automation_case_id = null
  }

  function open(record: CaseBindingSubject) {
    if (!active || saving.value) return
    reset()
    subject.value = {
      id: record.id,
      bindings:
        record.bindings?.map((binding) => ({
          automation_type: binding.automation_type,
          automation_case_id: binding.automation_case_id,
        })) ?? [],
    }
    loadBindingId()
    visible.value = true
  }

  function loadBindingId() {
    form.automation_case_id =
      subject.value?.bindings?.find((item) => item.automation_type === form.automation_type)
        ?.automation_case_id ?? null
  }

  async function save() {
    if (!active || !visible.value || saving.value) return false
    if (!subject.value?.id || !form.automation_case_id) {
      Message.warning('请选择自动化类型并填写 Case ID')
      return false
    }
    const version = generation
    const payload = {
      case_id: subject.value.id,
      automation_type: form.automation_type,
      automation_case_id: form.automation_case_id,
    }
    saving.value = true
    saveError.value = false
    try {
      await postManualAutomationBind(payload)
      if (current(version)) {
        reset()
        Message.success('自动化用例绑定成功')
        emit('saved')
      }
    } catch {
      if (current(version)) saveError.value = true
    } finally {
      saving.value = false
    }
    return false
  }

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
  .mango-library-binding__error {
    margin-bottom: var(--m-page-gap);
  }
</style>
