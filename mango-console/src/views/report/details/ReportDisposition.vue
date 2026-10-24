<template>
  <slot :open="open" :eligible="editable && (record.status === 0 || record.fail > 0 || record.is_excluded || record.failure_reason || record.failure_description)" />
  <a-modal v-model:visible="visible" title="排查与排除" :width="560" :mask-closable="false"
    :closable="!saving" :cancel-button-props="{ disabled: saving }" :ok-loading="saving"
    ok-text="保存" @before-ok="save">
    <a-descriptions :column="1" size="small">
      <a-descriptions-item label="执行项">{{ record.case_name || record.name || record.id }}</a-descriptions-item>
      <a-descriptions-item label="影响范围">整条执行项，共 {{ record.case_sum || 1 }} 个用例；原始结果保留</a-descriptions-item>
    </a-descriptions>
    <a-form :model="form" layout="horizontal" class="mango-disposition-form">
      <a-form-item label="排除统计"><a-switch v-model="form.is_excluded" size="small" :disabled="saving" /></a-form-item>
      <a-form-item label="原因分类" :required="form.is_excluded">
        <a-select v-model="form.failure_reason" :options="reasonOptions" :disabled="saving" allow-clear placeholder="请选择失败原因" />
      </a-form-item>
      <a-form-item label="排查说明" :required="form.is_excluded">
        <a-textarea v-model="form.failure_description" :disabled="saving" :max-length="1000" show-word-limit placeholder="填写排查结论；也可不排除，仅保存原因和说明" />
      </a-form-item>
    </a-form>
  </a-modal>
</template>

<script setup lang="ts">
  import { computed, reactive, ref } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { useEnum } from '@/store/modules/get-enum'
  import usePermissionStore from '@/store/modules/permission'
  import { updateReportDisposition } from '@/api/system/test_sute_details'

  const props = defineProps<{ record: any; editable?: boolean }>()
  const emit = defineEmits<{ (event: 'saved'): void }>()
  const enumStore = useEnum()
  const permissionStore = usePermissionStore()
  const visible = ref(false)
  const saving = ref(false)
  const form = reactive({ is_excluded: false, failure_reason: '', failure_description: '' })
  const reasonOptions = computed(() => enumStore.report_failure_reason.map((item: any) => ({ value: item.key, label: item.title })))

  function open() {
    if (saving.value) return
    Object.assign(form, { is_excluded: !!props.record.is_excluded, failure_reason: props.record.failure_reason || '', failure_description: props.record.failure_description || '' })
    visible.value = true
  }
  async function save() {
    if (saving.value || !permissionStore.hasPermission('report:exclude')) return false
    // 分类与说明独立保存；手工提交排除时由界面要求补全结论。
    if (form.is_excluded && (!form.failure_reason || !form.failure_description.trim())) {
      Message.warning('排除统计时，请填写原因分类和排查说明')
      return false
    }
    saving.value = true
    try {
      await updateReportDisposition(props.record.id, { ...form, failure_reason: form.failure_reason || '', failure_description: form.failure_description.trim() })
      emit('saved')
      Message.success('排查结论已保存')
      return true
    } catch {
      return false
    } finally {
      saving.value = false
    }
  }
</script>

<style scoped>
  .mango-disposition-form { margin-top: var(--m-space-md); }
</style>
