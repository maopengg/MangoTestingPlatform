<template>
  <a-popover trigger="click" position="bottom" :popup-visible="visible" @popup-visible-change="changeVisible">
    <a-button size="mini" type="text" class="mango-ui-step-retry-trigger" :loading="saving" data-testid="qa-views-uitest-case-details-button-重试-次">
      重试 {{ retryCount ?? 0 }} 次
    </a-button>
    <template #content>
      <div class="mango-ui-step-retry-editor">
        <label :for="inputId">失败重试次数</label>
        <a-input-number :id="inputId" v-model="draft" size="small" :min="0" :precision="0" :disabled="saving" placeholder="请输入重试次数" @press-enter="save" data-testid="qa-views-uitest-case-details-input-number-请输入重试次数" />
        <span v-if="error" class="mango-ui-step-retry-error" role="alert">{{ error }}</span>
        <a-space :size="6">
          <a-button size="mini" :disabled="saving" @click="close" data-testid="qa-views-uitest-case-details-button-取消">取消</a-button>
          <a-button size="mini" type="primary" :loading="saving" @click="save" data-testid="qa-views-uitest-case-details-button-保存">保存</a-button>
        </a-space>
      </div>
    </template>
  </a-popover>
</template>

<script setup lang="ts">
import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import useUserStore from '@/store/modules/user'
import usePermissionStore from '@/store/modules/permission'
import { putUiCaseStepsDetailed } from '@/api/uitest/case-steps-detailed'
import { requiredUiCaseAssetId, uiCaseAssetResponse } from '@/components/business/ui-case-step-create'

const props = defineProps<{ caseId: number | string; recordId: number | string; retryCount: unknown }>()
const emit = defineEmits<{ (event: 'saved', value: { caseId: number | string; recordId: number | string; retryCount: number }): void }>()
const route = useRoute(), user = useUserStore(), permission = usePermissionStore(), pagePath = route.path
const visible = ref(false), saving = ref(false), error = ref(''), draft = ref<number | undefined>(0)
const inputId = computed(() => `mango-ui-step-retry-${props.caseId}-${props.recordId}`)
let active = true, disposed = false, version = 0, contextVersion = 0
const identity = () => JSON.stringify([route.path, route.fullPath, props.caseId, props.recordId, user.userId, user.roleId, user.token, user.selected_environment, permission.permissionKeys])
const available = () => active && !disposed && route.path === pagePath && document.visibilityState === 'visible'
function close() { version++; visible.value = false; draft.value = 0; error.value = '' }
function changeVisible(value: boolean) {
  if (!value) { close(); return }
  if (!available() || saving.value) return
  close(); visible.value = true
  const valueAsNumber = props.retryCount == null ? 0 : typeof props.retryCount === 'number' || typeof props.retryCount === 'string' && props.retryCount.trim() !== '' ? Number(props.retryCount) : NaN
  if (!Number.isSafeInteger(valueAsNumber) || valueAsNumber < 0) { error.value = '重试次数异常，请重新加载核对'; draft.value = undefined }
  else draft.value = valueAsNumber
}
async function save(): Promise<boolean> {
  if (!available() || !visible.value || saving.value) return false
  if (typeof draft.value !== 'number' || !Number.isSafeInteger(draft.value) || draft.value < 0) {
    error.value = '失败重试次数请输入大于或等于 0 的整数'; return false
  }
  let caseId: number | string, recordId: number | string
  try { caseId = requiredUiCaseAssetId(props.caseId); recordId = requiredUiCaseAssetId(props.recordId) }
  catch { error.value = '步骤或用例ID异常，请重新加载核对'; return false }
  const snapshot = { caseId, recordId, retryCount: draft.value }
  const key = identity(), sequence = version, context = contextVersion
  const current = () => available() && visible.value && key === identity() && sequence === version
  const parentCurrent = () => available() && key === identity() && context === contextVersion
  saving.value = true; error.value = ''
  try {
    uiCaseAssetResponse(await putUiCaseStepsDetailed({ id: snapshot.recordId, error_retry: snapshot.retryCount }, snapshot.caseId))
    if (!parentCurrent()) return false
    emit('saved', snapshot)
    if (current()) { close(); Message.success('重试次数保存成功') }
    return true
  } catch {
    if (current()) error.value = '重试次数保存失败，请重试'
    return false
  } finally { saving.value = false }
}
function invalidate() { contextVersion++; close() }
function visibilityChanged() { if (document.visibilityState !== 'visible') invalidate() }
watch(identity, invalidate, { flush: 'sync' })
onMounted(() => document.addEventListener('visibilitychange', visibilityChanged))
onActivated(() => { active = true })
onDeactivated(() => { active = false; invalidate() })
onBeforeUnmount(() => { disposed = true; invalidate(); document.removeEventListener('visibilitychange', visibilityChanged) })
</script>

<style scoped>
.mango-ui-step-retry-trigger { padding: 0 4px; color: var(--m-text-2); font-size: 12px; }
.mango-ui-step-retry-editor { display: grid; grid-template-columns: 96px 128px; align-items: center; gap: 10px; color: var(--m-text); font-size: 12px; }
.mango-ui-step-retry-editor > .arco-space { grid-column: 1 / -1; justify-self: end; }
.mango-ui-step-retry-error { grid-column: 1 / -1; max-width: 234px; color: var(--m-danger); }
</style>
