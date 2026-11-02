<template>
  <a-modal v-model:visible="visible" title="步骤执行时机" :width="560" :mask-closable="!saving">
    <a-form :model="form" layout="horizontal" :disabled="saving">
      <a-form-item label="最终恢复步骤">
        <a-switch v-model="form.is_recovery" size="small" />
      </a-form-item>
      <p class="mango-recovery-hint">
        关闭时按正常流程执行；开启后在主流程结束或失败后执行，沿用场景重试配置。
      </p>
      <p class="mango-recovery-hint">
        恢复步骤按排序依次尝试，一个失败仍继续后续恢复；恢复失败会使整个用例失败。
        此开关不提供并发隔离或进程崩溃补偿。
      </p>
    </a-form>
    <template #footer>
      <a-button :disabled="saving" @click="visible = false">取消</a-button>
      <a-button  type="primary" :loading="saving" @click="save">保存</a-button>
    </template>
  </a-modal>
</template>

<script setup lang="ts">
  import { reactive, ref } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { putApiCaseDetailed } from '@/api/apitest/case_detailed'

  const emit = defineEmits<{ (event: 'saved'): void }>()
  const visible = ref(false)
  const saving = ref(false)
  const form = reactive({
    id: 0,
    case: 0,
    is_recovery: false,
  })

  function open(step: any) {
    Object.assign(form, {
      id: Number(step.id),
      case: Number(step.case?.id ?? step.case),
      is_recovery: Boolean(step.execution_config?.is_recovery),
    })
    visible.value = true
  }

  async function save() {
    if (saving.value) return
    saving.value = true
    try {
      await putApiCaseDetailed({
        id: form.id,
        execution_config: form.is_recovery ? { is_recovery: true } : {},
      }, form.case)
      Message.success('执行时机已保存；已有发布版本需重新生成修订并发布后生效')
      visible.value = false
      emit('saved')
    } catch {
      // 公共请求层展示错误；保留窗口及输入供重试。
    } finally {
      saving.value = false
    }
  }

  defineExpose({ open })
</script>

<style scoped>
  .mango-recovery-hint {
    color: var(--m-muted);
    line-height: 1.6;
    margin: 0 0 16px;
  }
</style>
