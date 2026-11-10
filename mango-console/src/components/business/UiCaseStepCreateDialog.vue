<template>
  <ModalDialog modal-class="mango-simple-form-modal" ref="dialogRef" title="新增执行编排" :width="560" @confirm="submit" @cancel="close">
    <template #content>
      <div v-if="visible">
        <a-alert v-if="saveError" type="error">{{ saveError }}</a-alert>
        <a-alert v-for="item in optionErrors" :key="item.key" type="error">{{ item.error }} <a-button size="small" :loading="loading[item.key]" :disabled="locked" @click="item.retry">重试加载</a-button></a-alert>
        <a-form auto-label-width :model="form" layout="horizontal" class="mango-ui-case-step-create-form mango-simple-form">
          <a-form-item class="mango-simple-form-item" required label="项目/产品">
            <a-cascader v-model="form.projectProduct" :loading="loading.products" :disabled="locked" :options="options.products" placeholder="请选择项目/产品" allow-search expand-trigger="hover" path-mode @change="onProductChange" data-testid="qa-components-business-uicasestepcreatedialog-cascader-请选择项目-产品" />
          </a-form-item>
          <a-form-item class="mango-simple-form-item" required label="模块">
            <a-select v-model="form.module" :disabled="locked || productId === null" :loading="loading.modules" :options="options.modules" placeholder="请选择模块" allow-search @change="onModuleChange" data-testid="qa-components-business-uicasestepcreatedialog-select-请选择模块" />
          </a-form-item>
          <a-form-item class="mango-simple-form-item" required label="页面/步骤">
            <a-cascader v-model="form.pageStep" :disabled="locked || form.module === null" :loading="loading.steps" :options="pageStepOptions" placeholder="请选择页面及页面步骤" allow-search expand-trigger="hover" path-mode @change="clearSaveError" data-testid="qa-components-business-uicasestepcreatedialog-cascader-请选择页面-页面步骤" />
          </a-form-item>
        </a-form>
      </div>
    </template>
    <template #footer>
      <a-space class="mango-modal-dialog-footer-actions">
        <a-button size="small" @click="close">取消</a-button>
        <a-button size="small" type="primary" :loading="saving" :disabled="creationAccepted && createdStepId === null" @click="submit">{{ createdStepId === null ? '提交' : '重试初始化' }}</a-button>
      </a-space>
    </template>
  </ModalDialog>
</template>

<script lang="ts" setup>
import { reportLoadError } from '@/utils/load-error'

import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, reactive, ref, watch } from 'vue'
import { Message } from '@arco-design/web-vue'
import { useRoute } from 'vue-router'
import useUserStore from '@/store/modules/user'
import usePermissionStore from '@/store/modules/permission'
import ModalDialog from '@/components/overlays/ModalDialog.vue'
import { useLatestRequest } from '@/hooks/use-latest-request'
import { getUiPageStepAssetModules, getUiPageStepAssetProducts, getUiPageStepAssetSteps } from '@/api/uitest/page-steps'
import { getUiCaseStepsRefreshCacheData, postUiCaseStepsDetailed } from '@/api/uitest/case-steps-detailed'
import { uiCaseAssetId, requiredUiCaseAssetId, uiCaseAssetObject, uiCaseAssetResponse, readUiCaseAssetProducts, readUiCaseAssetModules, readUiCaseAssetSteps, uiCaseAssetStepOptions, uiCaseAssetCreatePayload, type UiCaseAssetId, type UiCaseAssetOption, type UiCaseAssetStep } from './ui-case-step-create'

const props = defineProps<{ caseId: string | number; caseStepCount: number }>()
const emit = defineEmits<{ (event: 'created'): void }>()
const dialogRef = ref<{ show: () => Promise<boolean>; close: () => Promise<boolean>; setConfirmLoading: (loading: boolean) => void } | null>(null)
const route = useRoute(), user = useUserStore(), permission = usePermissionStore(), pagePath = route.path
const visible = ref(false), saving = ref(false), saveError = ref(''), createdStepId = ref<UiCaseAssetId | null>(null), creationAccepted = ref(false)
const createForm = () => ({ projectProduct: [] as UiCaseAssetId[], module: null as UiCaseAssetId | null, pageStep: [] as UiCaseAssetId[] })
const form = reactive(createForm())
const options = reactive<{ products: UiCaseAssetOption[]; modules: UiCaseAssetOption[]; steps: UiCaseAssetStep[] }>({ products: [], modules: [], steps: [] })
const loading = reactive({ products: false, modules: false, steps: false }), errors = reactive({ products: '', modules: '', steps: '' })
const requests = { products: useLatestRequest(), modules: useLatestRequest(), steps: useLatestRequest() }
let active = true, disposed = false, version = 0
const identity = () => JSON.stringify([route.path, route.fullPath, props.caseId, user.userId, user.roleId, user.token, user.selected_environment, permission.permissionKeys])
const available = () => active && !disposed && route.path === pagePath && document.visibilityState === 'visible'
function capture() { const key = identity(), sequence = version; return () => available() && visible.value && key === identity() && sequence === version }
const productId = computed(() => {
  const leaf = form.projectProduct[form.projectProduct.length - 1]
  return typeof leaf === 'string' && leaf.startsWith('project:') ? null : uiCaseAssetId(leaf)
})
const pageStepOptions = computed(() => uiCaseAssetStepOptions(options.steps))
const locked = computed(() => saving.value || creationAccepted.value)
const optionErrors = computed(() => [
  { key: 'products' as const, error: errors.products, retry: loadProducts },
  { key: 'modules' as const, error: errors.modules, retry: loadModules },
  { key: 'steps' as const, error: errors.steps, retry: loadSteps },
].filter(item => item.error))

function invalidateOptions(key: keyof typeof loading) { requests[key].invalidateRequests(); loading[key] = false; errors[key] = '' }
function clearSaveError() { if (!locked.value) saveError.value = '' }
function close() {
  version++; visible.value = false; createdStepId.value = null; creationAccepted.value = false; saveError.value = ''
  Object.assign(form, createForm()); options.products = []; options.modules = []; options.steps = []
  for (const key of ['products', 'modules', 'steps'] as const) invalidateOptions(key)
  void dialogRef.value?.close()
}
async function open() {
  if (!available() || saving.value) return false
  close(); visible.value = true
  const current = capture()
  await dialogRef.value?.show()
  if (!current()) return false
  await loadProducts(); return true
}
async function loadProducts() {
  if (!available() || !visible.value || locked.value) return
  const sequence = requests.products.beginRequest(), valid = capture()
  const current = () => valid() && requests.products.isLatestRequest(sequence)
  loading.products = true; errors.products = ''
  try { const result = readUiCaseAssetProducts(await getUiPageStepAssetProducts()); if (current()) options.products = result }
  catch (loadFailure0) { if (current()) (reportLoadError(loadFailure0, "项目/产品加载失败，请重试", false), errors.products = '项目/产品加载失败，请重试') }
  finally { if (current()) loading.products = false }
}
async function loadModules() {
  if (!available() || !visible.value || locked.value || productId.value === null) return
  const product = productId.value, sequence = requests.modules.beginRequest(), valid = capture()
  const current = () => valid() && requests.modules.isLatestRequest(sequence) && productId.value === product
  loading.modules = true; errors.modules = ''
  try { const result = readUiCaseAssetModules(await getUiPageStepAssetModules(product), product); if (current()) options.modules = result }
  catch (loadFailure1) { if (current()) (reportLoadError(loadFailure1, "模块加载失败，请重试", false), errors.modules = '模块加载失败，请重试') }
  finally { if (current()) loading.modules = false }
}
async function loadSteps() {
  if (!available() || !visible.value || locked.value || productId.value === null || form.module === null) return
  const product = productId.value, moduleId = form.module, sequence = requests.steps.beginRequest(), valid = capture()
  const current = () => valid() && requests.steps.isLatestRequest(sequence) && productId.value === product && form.module === moduleId
  loading.steps = true; errors.steps = ''
  try { const result = readUiCaseAssetSteps(await getUiPageStepAssetSteps(product, moduleId), product, moduleId); if (current()) options.steps = result }
  catch (loadFailure2) { if (current()) (reportLoadError(loadFailure2, "页面步骤加载失败，请重试", false), errors.steps = '页面步骤加载失败，请重试') }
  finally { if (current()) loading.steps = false }
}
function onProductChange() {
  if (locked.value) return
  clearSaveError(); form.module = null; form.pageStep = []; options.modules = []; options.steps = []
  invalidateOptions('modules'); invalidateOptions('steps'); return loadModules()
}
function onModuleChange() {
  if (locked.value) return
  clearSaveError(); form.pageStep = []; options.steps = []; invalidateOptions('steps'); return loadSteps()
}
async function submit(): Promise<boolean> {
  const releaseShell = () => dialogRef.value?.setConfirmLoading(false)
  if (!available() || !visible.value || saving.value || (creationAccepted.value && createdStepId.value === null)) { if (!saving.value) releaseShell(); return false }
  const current = capture(), key = identity(), parentCurrent = () => available() && key === identity()
  let caseId: UiCaseAssetId | null
  try { caseId = uiCaseAssetId(props.caseId) }
  catch { saveError.value = '用例ID异常，请重新加载核对'; releaseShell(); return false }
  const selectedId = form.pageStep[form.pageStep.length - 1]
  const selected = options.steps.find(item => String(item.stepId) === String(selectedId) && String(item.productId) === String(productId.value) && String(item.moduleId) === String(form.module))
  saveError.value = ''
  if (caseId === null || (createdStepId.value === null && (productId.value === null || form.module === null || !selected))) {
    saveError.value = caseId === null ? '未找到用例ID' : productId.value === null ? '请选择项目/产品' : form.module === null ? '请选择模块' : '请选择页面及页面步骤'
    releaseShell(); return false
  }
  let payload: ReturnType<typeof uiCaseAssetCreatePayload> | null = null
  try { if (createdStepId.value === null && selected) payload = uiCaseAssetCreatePayload(caseId, { ...selected }, props.caseStepCount) }
  catch { saveError.value = '编排数据异常，请重新加载核对'; releaseShell(); return false }
  let stepId = createdStepId.value, accepted = creationAccepted.value
  saving.value = true
  try {
    if (stepId === null) {
      if (!payload) return false
      const response: unknown = await postUiCaseStepsDetailed(payload, caseId)
      uiCaseAssetResponse(response); accepted = true
      if (current()) creationAccepted.value = true
      stepId = requiredUiCaseAssetId(uiCaseAssetObject(uiCaseAssetResponse(response)).id)
      if (current()) createdStepId.value = stepId
    }
    if (!parentCurrent()) return false
    uiCaseAssetResponse(await getUiCaseStepsRefreshCacheData(stepId))
    if (current()) { close(); Message.success('页面步骤添加成功') }
    return true
  } catch {
    if (current()) saveError.value = accepted ? stepId === null ? '步骤已创建，但返回信息异常，请关闭并重新加载核对' : '步骤已创建，缓存初始化失败；请点击“重试初始化”，不会重复创建' : '页面步骤添加失败，请重试'
    return false
  } finally {
    saving.value = false; releaseShell()
    if (accepted && parentCurrent()) emit('created')
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
.mango-ui-case-step-create-form { padding-top: var(--m-page-gap); }
.mango-ui-case-step-create-form :deep(.arco-form-item-label-col) { flex: 0 0 96px; width: 96px; max-width: 96px; }
.mango-ui-case-step-create-form :deep(.arco-form-item-wrapper-col) { min-width: 0; flex: 1; }
</style>
