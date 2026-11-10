<template>
  <ModalDialog ref="dialog" :title="recordId === null ? '新增' : '编辑'" width="min(760px, calc(100vw - 32px))" @confirm="save" @cancel="close">
    <template #content>
      
      <a-alert v-if="saveError" type="error" class="mango-task-editor-error">{{ saveError }}</a-alert>
      <a-form :model="form" layout="horizontal" class="mango-task-form" :disabled="saving">
        <section class="mango-task-form-group">
          <header class="mango-task-form-group__header"><strong>基础信息</strong><span>设置任务名称及所属产品、模块</span></header>
          <div class="mango-task-form-group__fields">
            <a-form-item label="任务名称" required class="mango-form-item__require mango-task-form-item--wide"><a-input v-model="form.name" placeholder="请输入任务名称" /></a-form-item>
            <a-form-item label="项目/产品" required class="mango-form-item__require">
              <ProjectProductSelect v-model="productSelection" placeholder="请选择项目名称" @change="productChanged" />
            </a-form-item>
            <a-form-item label="模块名称" class="mango-task-form-item--wide">
              <ProductModuleLevelSelect v-if="form.project_product !== null" v-model="form.module" :auto-clear="false" :project-product-id="form.project_product" :disabled="saving || form.execution_scope === 'full_product'" />
              <a-input v-else disabled placeholder="请先选择项目 / 产品" />
            </a-form-item>
          </div>
        </section>
        <section class="mango-task-form-group">
          <header class="mango-task-form-group__header"><strong>执行规则</strong><span>设置触发策略、运行环境、执行场景与用例匹配范围</span></header>
          <div class="mango-task-form-group__fields">
            <a-form-item label="定时策略" required class="mango-form-item__require"><a-select v-model="form.timing_strategies" multiple :max-tag-count="1" :field-names="fieldNames" :options="availableTimings" :loading="timingsLoading" placeholder="请选择定时器策略" allow-clear allow-search /></a-form-item>
            <a-form-item label="测试环境" required class="mango-form-item__require"><a-select v-model="form.test_envs" multiple :max-tag-count="1" :field-names="fieldNames" :options="environmentOptions" :loading="enumsLoading" placeholder="请选择执行环境" allow-clear allow-search /></a-form-item>
            <a-form-item label="执行场景" required class="mango-form-item__require"><a-select v-model="form.execution_scenes" multiple :max-tag-count="1" :field-names="fieldNames" :options="sceneOptions" :loading="enumsLoading" placeholder="请选择执行场景" allow-clear /></a-form-item>
            <a-form-item label="执行范围" required class="mango-form-item__require"><a-select v-model="form.execution_scope" :field-names="fieldNames" :options="scopeOptions" :loading="enumsLoading" placeholder="请选择执行范围" /></a-form-item>
            <a-form-item label="用例类型"><a-select v-model="form.case_types" multiple :max-tag-count="1" :field-names="fieldNames" :options="caseTypeOptions" :loading="enumsLoading" placeholder="留空表示全部类型" allow-clear /></a-form-item>
            <a-form-item v-if="supportsApi" label="API 并发"><a-input-number v-model="form.api_concurrency_limit" :min="1" :max="platformLimit ?? 1" :precision="0" :step="1" :disabled="saving || capacityLoading || platformLimit === null" allow-clear class="full-width" placeholder="留空则使用平台最大执行容量" /></a-form-item>
            <a-form-item label="报告保留策略" required class="mango-form-item__require"><a-select v-model="form.report_retention_policy" :field-names="fieldNames" :options="retentionOptions" :loading="enumsLoading" /></a-form-item>
          </div>
          <div class="mango-task-classification-summary"><span>当前规则</span><strong>{{ classificationSummary }}</strong></div>
        </section>
        <section class="mango-task-form-group">
          <header class="mango-task-form-group__header"><strong>责任与通知</strong><span>设置任务负责人和结果通知对象</span></header>
          <div class="mango-task-form-group__fields">
            <a-form-item label="负责人" required class="mango-form-item__require"><a-select v-model="form.case_people" :field-names="fieldNames" :options="availableUsers" :loading="usersLoading" placeholder="请选择定时任务负责人" allow-clear allow-search /></a-form-item>
            <a-form-item label="通知组"><a-select v-model="form.notice_group" :field-names="fieldNames" :options="availableNotices" :loading="noticesLoading" placeholder="请选择通知组" allow-clear allow-search /></a-form-item>
          </div>
        </section>
      </a-form>
    </template>
  </ModalDialog>
</template>

<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

import { computed, nextTick, onActivated, onBeforeUnmount, onDeactivated, onMounted, reactive, ref, watch } from 'vue'
import { Message } from '@arco-design/web-vue'
import { useRoute } from 'vue-router'
import useUserStore from '@/store/modules/user'
import usePermissionStore from '@/store/modules/permission'
import { useEnum } from '@/store/modules/get-enum'
import type { ModalDialogType } from '@/types/components'
import type { NavigationCreateSelection } from '@/utils/navigation-create-defaults'
import ModalDialog from '@/components/overlays/ModalDialog.vue'
import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
import ProductModuleLevelSelect from '@/components/business/ProductModuleLevelSelect.vue'
import { getSystemTaskExecutionOptions, postSystemTasks, putSystemTasks } from '@/api/system/tasks'
import { getSystemTimingList } from '@/api/system/time'
import { getUserName } from '@/api/user/user'
import { getSystemNoticeName } from '@/api/system/notice_group'
import { useTaskEditorResource } from '../composables/useTaskEditorResource'
import { createTaskEditorDraft, readTaskEditorDraft, readTaskEditorOptions, readTaskEditorCapacity, taskEditorId,
  taskEditorPayload, taskEditorResponse, taskEditorRecordOptions, taskEditorSelectedOptions, taskEditorScenes, taskEditorScopes,
  validateTaskEditor, type TaskEditorId, type TaskEditorOption } from '../task-editor-records'

const emit = defineEmits<{ (event: 'saved'): void }>()
const fieldNames = { value: 'key', label: 'title' }
const dialog = ref<Pick<ModalDialogType, 'show' | 'close' | 'setConfirmLoading'> | null>(null)
const recordId = ref<TaskEditorId | null>(null), opened = ref(false), saving = ref(false), saveError = ref('')
const form = reactive(createTaskEditorDraft())
const fallbackUsers = ref<TaskEditorOption[]>([]), fallbackTimings = ref<TaskEditorOption[]>([]), fallbackNotices = ref<TaskEditorOption[]>([])
const route = useRoute(), user = useUserStore(), permission = usePermissionStore(), enumStore = useEnum(), pagePath = route.path
let editorVersion = 0, active = true, disposed = false, hydrating = false, enumVersion = 0
const identity = () => JSON.stringify([route.path, route.fullPath, user.userId, user.roleId, user.token, user.selected_environment, permission.permissionKeys])
const available = () => active && !disposed && route.path === pagePath && document.visibilityState === 'visible'
function capture() {
  const version = editorVersion, key = identity()
  return () => opened.value && available() && version === editorVersion && key === identity()
}
const users = useTaskEditorResource<TaskEditorOption[]>(capture, '负责人加载失败')
const timings = useTaskEditorResource<TaskEditorOption[]>(capture, '定时策略加载失败')
const capacity = useTaskEditorResource<number>(capture, '执行容量加载失败')
const notices = useTaskEditorResource<TaskEditorOption[]>(() => {
  const valid = capture(), product = form.project_product
  return () => valid() && product === form.project_product
}, '通知组加载失败')
const { value: userOptions, loading: usersLoading } = users
const { value: timingOptions, loading: timingsLoading } = timings
const { value: noticeOptions, loading: noticesLoading } = notices
const { value: platformLimit, loading: capacityLoading } = capacity
const enumsLoading = ref(false), enumsError = ref(''), enumsReady = ref(false)
const metadataErrors = computed(() => [users.error.value, timings.error.value, capacity.error.value, notices.error.value, enumsError.value].filter(Boolean))
const metadataLoading = computed(() => usersLoading.value || timingsLoading.value || capacityLoading.value || noticesLoading.value || enumsLoading.value)
const availableUsers = computed(() => {
  const owner = taskEditorId(form.case_people)
  return taskEditorSelectedOptions(userOptions.value || [], owner === null ? [] : [owner], fallbackUsers.value)
})
const availableTimings = computed(() => taskEditorSelectedOptions(timingOptions.value || [], form.timing_strategies, fallbackTimings.value))
const availableNotices = computed(() => {
  const notice = taskEditorId(form.notice_group)
  return taskEditorSelectedOptions(noticeOptions.value || [], notice === null ? [] : [notice], fallbackNotices.value)
})
const enumOptions = (value: unknown) => readTaskEditorOptions(value ?? [])
const environmentOptions = computed(() => enumOptions(enumStore.environment_type))
const caseTypeOptions = computed(() => enumOptions(enumStore.test_case_type).map(option => ({ ...option, disabled: [3, 4].includes(Number(option.key)) })))
const sceneOptions = computed(() => taskEditorScenes(enumOptions(enumStore.automation_execution_scene), form))
const scopeOptions = computed(() => taskEditorScopes(enumOptions(enumStore.automation_execution_scope), form))
const retentionOptions = computed(() => enumOptions(enumStore.report_retention_policy))
const supportsApi = computed(() => !form.case_types.length || form.case_types.includes(1))
const title = (options: TaskEditorOption[], key: TaskEditorId) => options.find(option => String(option.key) === String(key))?.title || '未分类'
const classificationSummary = computed(() => {
  const types = form.case_types.length ? form.case_types.map(key => title(caseTypeOptions.value, key)).join('、') : '全部类型'
  const scenes = form.execution_scenes.length ? form.execution_scenes.map(key => title(enumOptions(enumStore.api_case_scenario_tag), key)).join('、') : '待选择执行场景'
  const scope = form.execution_scope ? title(scopeOptions.value, form.execution_scope) : '待选择执行范围'
  const hint = form.execution_scope === 'module' ? (form.module !== null ? ' · 已选择模块' : ' · 待选择模块') : ''
  return `${types} · ${scenes} · ${scope}${hint}`
})
const productSelection = computed({ get: () => form.project_product, set: (value: unknown) => { form.project_product = taskEditorId(value) } })

function close() {
  editorVersion++; enumVersion++; opened.value = false; hydrating = false
  recordId.value = null; Object.assign(form, createTaskEditorDraft()); saveError.value = ''
  fallbackUsers.value = []; fallbackTimings.value = []; fallbackNotices.value = []
  users.clear(); timings.clear(); capacity.clear(); notices.clear()
  enumsLoading.value = false; enumsError.value = ''; enumsReady.value = false
  void dialog.value?.close()
}
async function loadEnums() {
  const version = ++enumVersion, current = capture()
  enumsLoading.value = true; enumsError.value = ''; enumsReady.value = false
  try { await enumStore.getEnum(); if (version === enumVersion && current()) enumsReady.value = true }
  catch (loadFailure0) { if (version === enumVersion && current()) (reportLoadError(loadFailure0, "枚举加载失败", false), enumsError.value = '枚举加载失败') }
  finally { if (version === enumVersion && current()) enumsLoading.value = false }
}
async function loadNotices() {
  const product = form.project_product
  if (product === null) { notices.clear(); return }
  return notices.load(() => getSystemNoticeName(product), readTaskEditorOptions)
}
function retryMetadata() {
  if (!opened.value || !available() || saving.value || metadataLoading.value) return Promise.resolve([])
  return loadMetadata()
}
function loadMetadata() {
  return Promise.allSettled([
    users.load(getUserName, readTaskEditorOptions), timings.load(getSystemTimingList, readTaskEditorOptions),
    capacity.load(getSystemTaskExecutionOptions, readTaskEditorCapacity), loadEnums(), loadNotices(),
  ])
}
function productChanged() {
  form.module = null; form.notice_group = null; fallbackNotices.value = []; notices.clear()
  void loadNotices()
}
async function openEditor(value: unknown, selection: NavigationCreateSelection | undefined, editing: boolean) {
  if (!available() || saving.value) return
  close(); hydrating = true
  try {
    if (editing) {
      const draft = readTaskEditorDraft(value), id = taskEditorId(value)
      if (id === null) throw Error('Missing task ID')
      recordId.value = id; Object.assign(form, draft)
      fallbackUsers.value = taskEditorRecordOptions(value, 'case_people')
      fallbackTimings.value = taskEditorRecordOptions(value, 'timing_strategies')
      fallbackNotices.value = taskEditorRecordOptions(value, 'notice_group')
    } else if (selection) {
      form.project_product = taskEditorId(selection.projectProduct)
      form.module = form.project_product !== null ? taskEditorId(selection.module) : null
    }
    if (!supportsApi.value) form.api_concurrency_limit = null
    opened.value = true
    const version = editorVersion
    void dialog.value?.show()
    const loading = loadMetadata()
    await nextTick()
    if (version === editorVersion) hydrating = false
    await loading
  } catch { close(); Message.error('任务数据格式异常，请刷新后重试') }
}
function openCreate(selection?: NavigationCreateSelection) { return openEditor(undefined, selection, false) }
function openEdit(value: unknown) { return openEditor(value, undefined, true) }
watch(() => [form.execution_scope, ...form.test_envs], () => {
  if (hydrating || !opened.value) return
  if (form.execution_scope === 'full_product') form.module = null
  if (!enumsReady.value) return
  const allowed = new Set(sceneOptions.value.map(option => String(option.key)))
  form.execution_scenes = form.execution_scenes.filter(scene => allowed.has(scene))
})
watch(supportsApi, value => { if (!hydrating && opened.value && !value) form.api_concurrency_limit = null })
async function save(): Promise<boolean> {
  if (saving.value) return false
  const current = capture(), key = identity(), version = editorVersion
  try {
    if (!current()) return false
    saveError.value = ''
    if (capacityLoading.value || capacity.error.value || enumsLoading.value || platformLimit.value === null || !enumsReady.value) {
      saveError.value = '请等待配置加载完成；加载失败时请先重试'; return false
    }
    const draft = readTaskEditorDraft(form)
    const error = validateTaskEditor(draft, platformLimit.value)
    if (error) { saveError.value = error; return false }
    const id = recordId.value, payload = taskEditorPayload(draft, id)
    saving.value = true
    taskEditorResponse(await (id === null ? postSystemTasks(payload) : putSystemTasks(payload)))
    if (key === identity() && available()) emit('saved')
    if (current()) { close(); Message.success(id === null ? '任务已新增' : '任务已保存') }
    return true
  } catch { if (current()) saveError.value = '任务保存失败，请重试'; return false }
  finally { saving.value = false; if (version === editorVersion) dialog.value?.setConfirmLoading(false) }
}
function visibilityChanged() { if (document.visibilityState !== 'visible') close() }
watch(identity, close, { flush: 'sync' })
onMounted(() => document.addEventListener('visibilitychange', visibilityChanged))
onActivated(() => { active = true })
onDeactivated(() => { active = false; close() })
onBeforeUnmount(() => { disposed = true; close(); document.removeEventListener('visibilitychange', visibilityChanged) })
defineExpose({ openCreate, openEdit, close })
</script>

<style scoped>
.mango-task-editor-error { margin-bottom: 12px; }
.mango-task-form { display: grid; gap: 0; }
.mango-task-form-group { padding: 14px 0; border-bottom: 1px solid var(--m-border); }
.mango-task-form-group:first-child { padding-top: 0; }
.mango-task-form-group:last-child { padding-bottom: 0; border-bottom: 0; }
.mango-task-form-group__header { display: flex; align-items: baseline; gap: 10px; margin-bottom: 12px; }
.mango-task-form-group__header strong { color: var(--m-text); font-size: 14px; font-weight: 600; }
.mango-task-form-group__header span { color: var(--m-muted); font-size: 12px; }
.mango-task-form-group__fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px 16px; }
.mango-task-form-group__fields :deep(.arco-form-item) { flex-wrap: nowrap; min-width: 0; margin-bottom: 0; }
.mango-task-form-group__fields :deep(.arco-form-item-label-col) { flex: 0 0 120px; width: 120px; max-width: 120px; white-space: nowrap; }
.mango-task-form-group__fields :deep(.arco-form-item-wrapper-col) { flex: 1 1 0; width: 0; max-width: none; min-width: 0; }
.mango-task-form-item--wide { grid-column: 1 / -1; }
.mango-task-classification-summary { display: flex; align-items: center; padding: 10px 12px; gap: 10px; margin-top: 12px; border: 1px solid var(--m-border); border-radius: var(--m-radius-md); background: var(--m-surface-soft); }
.mango-task-classification-summary > span { color: var(--m-muted); font-size: 12px; white-space: nowrap; }
.mango-task-classification-summary > strong { color: var(--m-text); font-size: 13px; font-weight: 600; }
</style>
