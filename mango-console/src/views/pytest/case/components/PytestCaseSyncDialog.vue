<template>
  <a-modal modal-class="mango-simple-form-modal" :visible="visible" title="选择项目进行同步" :width="560" :ok-loading="syncing" :on-before-ok="confirm" @cancel="close" @update:visible="onVisibleChange">
    <a-form class="mango-simple-form" :model="draft" layout="horizontal" auto-label-width :disabled="syncing">
      <a-form-item label="项目/产品" class="mango-form-item__require mango-simple-form-item">
        <a-cascader v-model="draft.projectId" :options="projects.projectPytest2" :loading="loading" :disabled="syncing || loading || failed" allow-search allow-clear placeholder="请选择项目/产品" />
        <template v-if="failed" #extra><a-button size="small" :loading="loading" @click="loadProjects">重试</a-button></template>
      </a-form-item>
    </a-form>
  </a-modal>
</template>

<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { onActivated, onBeforeUnmount, onDeactivated, onMounted, reactive, ref, watch } from 'vue'
  import { useRoute } from 'vue-router'
  import { Message } from '@arco-design/web-vue'
  import { useProject } from '@/store/modules/get-project'
  import useUserStore from '@/store/modules/user'
  import { postPytestCaseUpdate } from '@/api/pytest/case'
  import { checkCaseSave, selectedPytestProject } from '../editor'

  const emit = defineEmits<{ (event: 'synced', projectId: number): void }>()
  const projects = useProject(), user = useUserStore(), route = useRoute()
  const visible = ref(false), loading = ref(false), failed = ref(false), syncing = ref(false)
  const draft = reactive<{ projectId: number | string | Array<number | string> | null }>({ projectId: null })
  let version = 0, request = 0, active = true, disposed = false
  const available = () => !disposed && active && (typeof document === 'undefined' || !document.hidden)
  const current = (window: number) => available() && visible.value && window === version
  function close(): void { version++; request++; visible.value = false; draft.projectId = null; loading.value = false; failed.value = false }
  function onVisibleChange(value: boolean): void { if (!value) close() }
  function open(): void {
    if (!available() || syncing.value) return
    close(); visible.value = true; void loadProjects()
  }
  async function loadProjects(): Promise<void> {
    if (!current(version) || loading.value) return
    const window = version, read = ++request
    loading.value = true; failed.value = false
    try { await projects.projectPytestName(); if (projects.optionErrors.pytest) throw new Error('项目加载失败') }
    catch (loadFailure0) { if (current(window) && read === request) (reportLoadError(loadFailure0, "加载失败，请重试", false), failed.value = true) }
    finally { if (current(window) && read === request) loading.value = false }
  }
  async function confirm(): Promise<boolean> {
    if (!current(version) || syncing.value || loading.value || failed.value) return false
    const window = version
    let projectId: number
    try { projectId = selectedPytestProject(draft.projectId, projects.projectPytest2) }
    catch { Message.warning('请选择有效的项目/产品'); return false }
    syncing.value = true
    try {
      checkCaseSave(await postPytestCaseUpdate(projectId))
      if (!current(window)) return false
      close(); Message.success('同步成功'); emit('synced', projectId)
      return true
    } catch { if (current(window)) Message.error('同步失败，请重试'); return false }
    finally { syncing.value = false }
  }
  watch(() => [user.userId, user.roleId, user.token, user.selected_environment, route.fullPath], close, { flush: 'sync' })
  function visibilityChanged(): void { if (typeof document !== 'undefined' && document.hidden) close() }
  onMounted(() => { if (typeof document !== 'undefined') document.addEventListener('visibilitychange', visibilityChanged) })
  onActivated(() => { active = true })
  onDeactivated(() => { active = false; close() })
  onBeforeUnmount(() => { disposed = true; close(); if (typeof document !== 'undefined') document.removeEventListener('visibilitychange', visibilityChanged) })
  defineExpose({ open, close })
</script>
