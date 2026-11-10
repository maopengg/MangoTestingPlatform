<template>
  <a-modal :visible="visible" title="授权缓存" :width="720" :footer="false" @cancel="close">
    <MangoPanelSpin :loading="loading" class="mango-ui-auth-cache">
      <template v-if="error"><a-button size="small" :loading="loading" @click="loadCache">重新加载</a-button></template>
      <pre v-else-if="text" class="mango-code-panel mango-ui-auth-cache__content">{{ text }}</pre>
      <div v-else class="mango-empty-state">{{ loading ? '正在加载授权缓存' : '暂无缓存数据' }}</div>
    </MangoPanelSpin>
  </a-modal>
</template>

<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

import { onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from 'vue'
import { Message } from '@arco-design/web-vue'
import { useRoute } from 'vue-router'
import useUserStore from '@/store/modules/user'
import usePermissionStore from '@/store/modules/permission'
import MangoPanelSpin from '@/components/feedback/MangoPanelSpin.vue'
import { getUiAuthConfigCache } from '@/api/uitest/auth-config'
import { useLatestRequest } from '@/hooks/use-latest-request'
import { requiredUiAuthId, uiAuthObject, uiAuthResponse, type UiAuthId } from '../auth-editor-records'

const route = useRoute(), user = useUserStore(), permission = usePermissionStore(), pagePath = route.path
const visible = ref(false), recordId = ref<UiAuthId | null>(null)
const text = ref(''), loading = ref(false), error = ref('')
const request = useLatestRequest()
let active = true, disposed = false
const identity = () => JSON.stringify([route.path, route.fullPath, user.userId, user.roleId, user.token, user.selected_environment, permission.permissionKeys])
const available = () => active && !disposed && route.path === pagePath && document.visibilityState === 'visible'

function close() {
  request.invalidateRequests()
  visible.value = false
  recordId.value = null
  text.value = ''
  error.value = ''
  loading.value = false
}

async function loadCache() {
  if (!available() || !visible.value || recordId.value === null || loading.value) return
  const id = recordId.value, key = identity(), sequence = request.beginRequest()
  const current = () => available() && visible.value && key === identity() && request.isLatestRequest(sequence) && recordId.value === id
  loading.value = true
  text.value = ''
  error.value = ''
  try {
    const result = uiAuthObject(uiAuthResponse(await getUiAuthConfigCache(id)))
    if (String(requiredUiAuthId(result.id)) !== String(id)) throw Error('Unexpected authorization cache record')
    const snapshot = JSON.stringify(result, null, 2)
    if (current()) text.value = snapshot
  } catch (loadFailure0) {
    if (current()) (reportLoadError(loadFailure0, "授权缓存加载失败，请重试", false), error.value = '授权缓存加载失败，请重试')
  } finally {
    if (current()) loading.value = false
  }
}

function open(value: unknown) {
  if (!available()) return
  close()
  try {
    recordId.value = requiredUiAuthId(uiAuthObject(value).id)
    visible.value = true
    return loadCache()
  } catch {
    close()
    Message.error('授权记录异常，请刷新后重试')
  }
}

function visibilityChanged() { if (document.visibilityState !== 'visible') close() }
watch(identity, close, { flush: 'sync' })
onMounted(() => document.addEventListener('visibilitychange', visibilityChanged))
onActivated(() => { active = true })
onDeactivated(() => { active = false; close() })
onBeforeUnmount(() => { disposed = true; close(); document.removeEventListener('visibilitychange', visibilityChanged) })
defineExpose({ open, close })
</script>

<style scoped>
.mango-ui-auth-cache { display: block; width: 100%; min-width: 0; }
.mango-ui-auth-cache__content {
  max-height: 520px;
  overflow: auto;
  margin: 0;
  padding: var(--m-page-gap);
  color: var(--m-code-text);
  background: var(--m-code-bg);
}
</style>
