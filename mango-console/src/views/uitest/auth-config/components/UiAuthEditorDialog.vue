<template>
  <a-modal modal-class="mango-simple-form-modal" v-model:visible="editorVisible" :title="editingId === null ? '新增授权' : '编辑授权'" :width="560" :mask-closable="false" :ok-loading="saving" :on-before-ok="onSubmit" @cancel="close">
      <a-alert v-if="saveError" type="error">{{ saveError }}</a-alert>

      <a-alert v-for="item in optionErrors" :key="item.key" type="error">{{ item.error }} <a-button size="small" :loading="item.loading" @click="item.retry">重试加载</a-button></a-alert>
      <a-form auto-label-width ref="formRef" :model="form" layout="horizontal" class="mango-ui-auth-editor mango-simple-form" :disabled="locked">
        <a-form-item label="项目/产品" class="mango-form-item__require mango-simple-form-item">
          <ProjectProductSelect v-model="productSelection" :disabled="locked" @change="onFormProjectProductChange" />
        </a-form-item>
        <a-form-item
          class="mango-form-item__require mango-simple-form-item"
          field="test_env"
          label="被测环境"
          :rules="[{ required: true, message: '请选择被测环境' }]"
        >
          <a-select :disabled="locked"
            v-model="form.test_env"
            :field-names="fieldNames"
            :options="environmentOptions" :loading="enumsLoading"
            allow-clear
            placeholder="请选择被测环境"
            value-key="key" data-testid="qa-views-uitest-auth-config-select-请选择绑定环境"
          />
        </a-form-item>
        <a-form-item label="授权名称" class="mango-form-item__require mango-simple-form-item">
          <a-input :disabled="locked" v-model="form.name" placeholder="请输入授权名称" data-testid="qa-views-uitest-auth-config-input-请输入授权名称-2" />
        </a-form-item>
        <a-form-item label="授权方式" class="mango-form-item__require mango-simple-form-item">
          <a-select :disabled="locked"
            v-model="form.auth_type"
            :field-names="fieldNames"
            :options="enabledAuthTypeOptions" :loading="enumsLoading"
            placeholder="请选择授权方式"
            value-key="key" @change="onAuthTypeChange" data-testid="qa-views-uitest-auth-config-select-请选择授权方式-2"
          />
        </a-form-item>
        <a-form-item v-if="form.auth_type === 3" label="页面步骤" class="mango-form-item__require mango-simple-form-item">
          <a-select :disabled="locked"
            v-model="form.page_step"
            :options="pageStepOptions" :loading="pageStepsLoading" :field-names="fieldNames"
            allow-clear
            allow-search
            placeholder="请选择登录页面步骤" data-testid="qa-views-uitest-auth-config-select-请选择登录页面步骤"
          />
        </a-form-item>
        <a-form-item v-if="form.auth_type === 2" label="登录接口" class="mango-form-item__require mango-simple-form-item">
          <a-select :disabled="locked"
            v-model="form.api_info"
            :options="apiInfoOptions" :field-names="fieldNames"
            :loading="apiInfoLoading"
            allow-clear
            allow-search
            placeholder="请选择接口转入的登录接口" data-testid="qa-views-uitest-auth-config-select-请选择接口转入的登录接口"
          />
        </a-form-item>
        <a-form-item v-if="form.auth_type === 0" label="手动缓存 JSON" class="mango-ui-auth-editor__wide mango-simple-form-item">
          <div class="mango-ui-auth-editor__json"><a-button size="small" :disabled="locked" @click="openJson('manual')">展开编辑</a-button><a-textarea :disabled="locked" v-model="json.manual" :auto-size="{ minRows: 5, maxRows: 10 }" /></div>
        </a-form-item>
        <a-form-item v-if="form.auth_type === 1" label="自动授权配置 JSON" class="mango-ui-auth-editor__wide mango-simple-form-item">
          <div class="mango-ui-auth-editor__json"><a-button size="small" :disabled="locked" @click="openJson('auto')">展开编辑</a-button><a-textarea :disabled="locked" v-model="json.auto" :auto-size="{ minRows: 5, maxRows: 10 }" /></div>
        </a-form-item>
        <a-form-item v-if="form.auth_type === 2" label="接口转入配置 JSON" class="mango-ui-auth-editor__wide mango-simple-form-item">
          <div class="mango-ui-auth-editor__json"><a-button size="small" :disabled="locked" @click="openJson('api')">展开编辑</a-button><a-textarea :disabled="locked" v-model="json.api" :auto-size="{ minRows: 5, maxRows: 10 }" /></div>
        </a-form-item>
        <a-form-item class="mango-simple-form-item" v-if="form.auth_type !== 3" label="刷新方式">
          <a-select :disabled="locked"
            v-model="form.refresh_mode"
            :field-names="fieldNames"
            :options="refreshModeOptions" @change="onRefreshModeChange"
            value-key="key"
          />
        </a-form-item>
        <a-form-item v-if="form.auth_type === 2 && form.refresh_mode === 1" label="定时策略" class="mango-form-item__require mango-simple-form-item">
          <a-select :disabled="locked"
            v-model="form.time_task"
            :options="timeTaskOptions" :loading="timeTaskLoading" :field-names="fieldNames"
            allow-clear
            allow-search
            placeholder="请选择定时策略" data-testid="qa-views-uitest-auth-config-select-请选择定时策略"
          />
        </a-form-item>
        <a-form-item v-if="form.auth_type !== 3 && form.refresh_mode === 2" label="通知组" class="mango-form-item__require mango-simple-form-item">
          <a-select :disabled="locked"
            v-model="form.notice_group"
            :options="noticeOptions" :loading="noticesLoading" :field-names="fieldNames"
            allow-clear
            allow-search
            placeholder="请选择到期提醒通知组" data-testid="qa-views-uitest-auth-config-select-请选择到期提醒通知组"
          />
        </a-form-item>
        <a-form-item class="mango-simple-form-item" v-if="form.auth_type !== 3" label="有效期(分钟)">
          <a-input-number :disabled="locked" v-model="form.token_ttl" :min="1" />
        </a-form-item>
        <a-form-item class="mango-simple-form-item"
          v-if="form.auth_type !== 3 && form.refresh_mode === 2"
          field="expire_notice_minutes"
          label="提前提醒(分钟)"
          :rules="[{ type: 'number', min: 10, message: '提前提醒时间不能少于10分钟' }]"
        >
          <a-input-number :disabled="locked" v-model="form.expire_notice_minutes" :min="10" />
        </a-form-item>
      </a-form>
  </a-modal>
  <MangoJsonEditDrawer v-model:visible="jsonVisible" :model-value="jsonText" title="授权配置 JSON" :saving="saving" @save="saveJson" />
</template>

<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, reactive, ref, watch } from 'vue'
import { Message } from '@arco-design/web-vue'
import type { FormInstance } from '@arco-design/web-vue'
import { useRoute } from 'vue-router'
import useUserStore from '@/store/modules/user'
import usePermissionStore from '@/store/modules/permission'
import { useEnum } from '@/store/modules/get-enum'
import { fieldNames } from '@/setting'
import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
import MangoJsonEditDrawer from '@/components/editors/MangoJsonEditDrawer.vue'
import { getUiSteps } from '@/api/uitest/page-steps'
import { getApiInfoOptions } from '@/api/apitest/info'
import { getSystemTimingList } from '@/api/system/time'
import { getSystemNoticeName } from '@/api/system/notice_group'
import { postUiAuthConfig, putUiAuthConfig } from '@/api/uitest/auth-config'
import { createUiAuthDraft, createUiAuthJsonDraft, readUiAuthDraft, readUiAuthJsonDraft, readUiAuthOptions, selectedUiAuthOptions, uiAuthId, requiredUiAuthId, uiAuthObject, uiAuthResponse, uiAuthPayload, validateUiAuthDraft, parseUiAuthJson, type UiAuthId, type UiAuthOption, type UiAuthJsonDraft } from '../auth-editor-records'
import { useAuthEditorOption } from '../composables/useAuthEditorOption'

const emit = defineEmits<{ (event: 'saved'): void }>()
const route = useRoute(), user = useUserStore(), permission = usePermissionStore(), enumStore = useEnum(), pagePath = route.path
const editorVisible = ref(false), editingId = ref<UiAuthId | null>(null), saving = ref(false), saveError = ref(''), formRef = ref<FormInstance | null>(null)
const form = reactive(createUiAuthDraft()), json = reactive(createUiAuthJsonDraft()), jsonKind = ref<keyof UiAuthJsonDraft | null>(null), jsonVisible = ref(false)
const fallbackPages = ref<UiAuthOption[]>([]), fallbackApis = ref<UiAuthOption[]>([]), fallbackTimings = ref<UiAuthOption[]>([]), fallbackNotices = ref<UiAuthOption[]>([])
const enumsLoading = ref(false), enumsError = ref('')
let active = true, disposed = false, version = 0, enumVersion = 0
const identity = () => JSON.stringify([route.path, route.fullPath, user.userId, user.roleId, user.token, user.selected_environment, permission.permissionKeys])
const available = () => active && !disposed && route.path === pagePath && document.visibilityState === 'visible'
function capture() { const request = version, key = identity(); return () => available() && editorVisible.value && request === version && key === identity() }
function captureProduct() { const current = capture(), product = form.project_product; return () => current() && product === form.project_product }
const pages = useAuthEditorOption(captureProduct, '页面步骤加载失败'), apis = useAuthEditorOption(captureProduct, '登录接口加载失败')
const timings = useAuthEditorOption(capture, '定时策略加载失败'), notices = useAuthEditorOption(captureProduct, '通知组加载失败')
const { loading: pageStepsLoading } = pages, { loading: apiInfoLoading } = apis, { loading: timeTaskLoading } = timings, { loading: noticesLoading } = notices
const pageStepOptions = computed(() => selectedUiAuthOptions(pages.options.value, form.page_step, fallbackPages.value))
const apiInfoOptions = computed(() => selectedUiAuthOptions(apis.options.value, form.api_info, fallbackApis.value))
const timeTaskOptions = computed(() => selectedUiAuthOptions(timings.options.value, form.time_task, fallbackTimings.value))
const noticeOptions = computed(() => selectedUiAuthOptions(notices.options.value, form.notice_group, fallbackNotices.value))
const environmentOptions = computed(() => readUiAuthOptions(enumStore.environment_type ?? []))
const enabledAuthTypeOptions = computed(() => readUiAuthOptions(enumStore.ui_auth_type ?? []).filter(option => Number(option.key) !== 4))
const refreshModeOptions = computed(() => readUiAuthOptions(enumStore.ui_auth_refresh_mode ?? []).filter(option => form.auth_type === 2 || Number(option.key) !== 1))
const locked = computed(() => saving.value || jsonVisible.value)
const productSelection = computed({ get: () => form.project_product, set: (value: unknown) => { if (!locked.value) form.project_product = uiAuthId(value) } })
const optionErrors = computed(() => [
  { key: 'pages', error: pages.error.value, loading: pages.loading.value, retry: loadPageSteps },
  { key: 'apis', error: apis.error.value, loading: apis.loading.value, retry: loadApiInfoList },
  { key: 'timings', error: timings.error.value, loading: timings.loading.value, retry: loadTimeTaskList },
  { key: 'notices', error: notices.error.value, loading: notices.loading.value, retry: loadNoticeList },
].filter(item => item.error))
const jsonText = computed(() => jsonKind.value === null ? '' : json[jsonKind.value])
function close() {
  version++; enumVersion++; editorVisible.value = false; editingId.value = null; saveError.value = ''; jsonVisible.value = false; jsonKind.value = null
  Object.assign(form, createUiAuthDraft()); Object.assign(json, createUiAuthJsonDraft())
  pages.clear(); apis.clear(); timings.clear(); notices.clear(); enumsLoading.value = false; enumsError.value = ''
  fallbackPages.value = []; fallbackApis.value = []; fallbackTimings.value = []; fallbackNotices.value = []
  formRef.value?.clearValidate()
}
async function loadEnums() {
  if (!editorVisible.value || !available()) return
  const request = ++enumVersion, current = capture(); enumsLoading.value = true; enumsError.value = ''
  try { await enumStore.getEnum() }
  catch (loadFailure0) { if (request === enumVersion && current()) (reportLoadError(loadFailure0, "授权选项加载失败，请重试", false), enumsError.value = '授权选项加载失败，请重试') }
  finally { if (request === enumVersion && current()) enumsLoading.value = false }
}
function loadPageSteps() {
  const product = form.project_product
  if (!editorVisible.value || !available()) return
  if (product === null) { pages.clear(); return }
  return pages.load(() => getUiSteps({ page: 1, pageSize: 500, project_product: product }))
}
function loadApiInfoList() {
  const product = form.project_product
  if (!editorVisible.value || !available()) return
  if (product === null) { apis.clear(); return }
  const current = captureProduct()
  return apis.load(async () => {
    const items: unknown = await getApiInfoOptions(product, current)
    if (!Array.isArray(items)) throw Error('Invalid login API options')
    return { code: 200, data: items.map(value => { const row = uiAuthObject(value); return { key: requiredUiAuthId(row.id), title: `${typeof row.name === 'string' ? row.name : ''}${typeof row.url === 'string' && row.url ? ` / ${row.url}` : ''}` } }) }
  })
}
function loadTimeTaskList() { if (editorVisible.value && available()) return timings.load(getSystemTimingList) }
function loadNoticeList() {
  const product = form.project_product
  if (!editorVisible.value || !available()) return
  if (product === null) { notices.clear(); return }
  return notices.load(() => getSystemNoticeName(product))
}
function loadRelatedOptions() { return Promise.allSettled([loadPageSteps(), loadApiInfoList(), loadNoticeList()]) }
function loadOptions() { return Promise.allSettled([loadEnums(), loadTimeTaskList(), loadRelatedOptions()]) }
function onFormProjectProductChange(value: unknown) {
  if (locked.value || !editorVisible.value) return
  form.project_product = uiAuthId(value); form.page_step = null; form.api_info = null; form.notice_group = null
  fallbackPages.value = []; fallbackApis.value = []; fallbackNotices.value = []; pages.clear(); apis.clear(); notices.clear()
  return loadRelatedOptions()
}
function onAuthTypeChange() {
  if (locked.value) return
  if (form.auth_type === 3) { form.refresh_mode = 0; form.time_task = null; form.notice_group = null }
  else if (form.auth_type !== 2 && form.refresh_mode === 1) { form.refresh_mode = 0; form.time_task = null }
}
function onRefreshModeChange() { if (!locked.value) { if (form.refresh_mode !== 1) form.time_task = null; if (form.refresh_mode !== 2) form.notice_group = null } }
async function openCreate(product: unknown = null) {
  if (!available() || saving.value) return
  close()
  try { form.project_product = uiAuthId(product); editorVisible.value = true; await loadOptions() }
  catch { close(); Message.error('授权初始数据异常，请重新打开') }
}
async function openEdit(value: unknown) {
  if (!available() || saving.value) return
  close()
  try {
    const row = uiAuthObject(value), draft = readUiAuthDraft(row), configs = readUiAuthJsonDraft(row)
    editingId.value = requiredUiAuthId(row.id); Object.assign(form, draft); Object.assign(json, configs)
    const fallback = (value: unknown) => value !== null && typeof value === 'object' ? readUiAuthOptions([value]) : []
    fallbackPages.value = fallback(row.page_step); fallbackTimings.value = fallback(row.time_task); fallbackNotices.value = fallback(row.notice_group)
    fallbackApis.value = draft.api_info === null ? [] : [{ key: draft.api_info, title: `ID ${draft.api_info}` }]
    editorVisible.value = true; await loadOptions()
  } catch { close(); Message.error('授权配置格式异常，请刷新后重试') }
}
function openJson(kind: keyof UiAuthJsonDraft) { if (available() && editorVisible.value && !locked.value) { jsonKind.value = kind; jsonVisible.value = true } }
function saveJson(value: string) {
  if (!available() || !editorVisible.value || !jsonVisible.value || jsonKind.value === null || saving.value) return
  try { parseUiAuthJson(value); json[jsonKind.value] = value; jsonVisible.value = false; jsonKind.value = null }
  catch { Message.error('JSON格式不正确，必须为对象') }
}
async function onSubmit(): Promise<boolean> {
  if (!available() || !editorVisible.value || locked.value) return false
  const current = capture(), key = identity(), id = editingId.value
  saveError.value = ''
  const validation = validateUiAuthDraft(form)
  if (validation) { saveError.value = validation; return false }
  let payload
  try { payload = uiAuthPayload({ ...form }, { ...json }, id) }
  catch { saveError.value = 'JSON格式不正确，配置必须为JSON对象'; return false }
  saving.value = true
  try {
    const errors = await formRef.value?.validate()
    if (errors || !current()) return false
    uiAuthResponse(await (id === null ? postUiAuthConfig(payload) : putUiAuthConfig(payload)))
    if (key === identity() && available()) emit('saved')
    if (current()) { close(); Message.success('保存成功') }
    return true
  } catch { if (current()) saveError.value = '授权保存失败，请重试'; return false }
  finally { saving.value = false }
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
.mango-ui-auth-editor { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: var(--m-space-lg); }
.mango-ui-auth-editor :deep(.arco-form-item-label-col) { flex: 0 0 112px; width: 112px; max-width: 112px; }
.mango-ui-auth-editor :deep(.arco-form-item-wrapper-col) { min-width: 0; flex: 1; }
.mango-ui-auth-editor__wide { grid-column: 1 / -1; }
.mango-ui-auth-editor__json { display: grid; width: 100%; min-width: 0; gap: var(--m-page-gap); }
.mango-ui-auth-editor__json > .arco-btn { justify-self: end; }
</style>
