<template>
  <span class="mango-ui-step-url-switch">
    <a-switch :model-value="enabled" :loading="saving" :before-change="save" aria-label="切换步骤 URL" />
    <span v-if="error" class="mango-ui-step-url-switch__error" role="alert">{{ error }}</span>
  </span>
</template>

<script setup lang="ts">
import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import useUserStore from '@/store/modules/user'
import usePermissionStore from '@/store/modules/permission'
import { putUiCaseStepsDetailed } from '@/api/uitest/case-steps-detailed'
import { requiredUiCaseAssetId, uiCaseAssetResponse } from '@/components/business/ui-case-step-create'

const props = defineProps<{ caseId: number | string; recordId: number | string; value: unknown }>()
const emit = defineEmits<{ (event: 'saved', value: { caseId: number | string; recordId: number | string; value: 0 | 1 }): void }>()
const route = useRoute(), user = useUserStore(), permission = usePermissionStore(), pagePath = route.path
const saving = ref(false), error = ref(''), enabled = computed(() => props.value === 1)
let active = true, disposed = false, version = 0
const identity = () => JSON.stringify([route.path, route.fullPath, props.caseId, props.recordId, user.userId, user.roleId, user.token, user.selected_environment, permission.permissionKeys])
const available = () => active && !disposed && route.path === pagePath && document.visibilityState === 'visible'
function invalidate() { version++; error.value = '' }
async function save(next: unknown): Promise<boolean> {
  if (!available() || saving.value) return false
  if (typeof next !== 'boolean') return false
  const value: 0 | 1 = next ? 1 : 0
  let caseId: number | string, recordId: number | string
  try { caseId = requiredUiCaseAssetId(props.caseId); recordId = requiredUiCaseAssetId(props.recordId) }
  catch { error.value = '步骤或用例ID异常，请重新加载核对'; return false }
  const snapshot = { caseId, recordId, value }
  const key = identity(), sequence = version
  const current = () => available() && key === identity() && sequence === version
  saving.value = true; error.value = ''
  try {
    uiCaseAssetResponse(await putUiCaseStepsDetailed({ id: snapshot.recordId, switch_step_open_url: value }, snapshot.caseId))
    if (!current()) return false
    emit('saved', snapshot); Message.success('切换 URL 设置已保存'); return true
  } catch {
    if (current()) error.value = '保存失败，请重试'
    return false
  } finally { saving.value = false }
}
function visibilityChanged() { if (document.visibilityState !== 'visible') invalidate() }
watch(identity, invalidate, { flush: 'sync' })
onMounted(() => document.addEventListener('visibilitychange', visibilityChanged))
onActivated(() => { active = true })
onDeactivated(() => { active = false; invalidate() })
onBeforeUnmount(() => { disposed = true; invalidate(); document.removeEventListener('visibilitychange', visibilityChanged) })
</script>

<style scoped>
.mango-ui-step-url-switch { display: inline-flex; align-items: center; flex-wrap: wrap; gap: 6px; }
.mango-ui-step-url-switch__error { color: var(--m-danger); font-size: 12px; }
</style>
