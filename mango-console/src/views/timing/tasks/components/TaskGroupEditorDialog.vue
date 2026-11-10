<template>
  <a-modal
    v-model:visible="editorVisible"
    :title="editingId !== null ? '编辑任务组' : '新增任务组'"
    width="min(760px, calc(100vw - 32px))"
    class="mango-task-group-editor-modal"
    body-class="mango-task-group-editor-body"
    :mask-closable="false"
    @cancel="close"
  >
    <mango-panel-spin :loading="editorLoading" class="mango-task-group-editor__spin">
      <a-form :model="form" :disabled="editorLocked" layout="horizontal" class="mango-task-group-editor">
        <div class="mango-task-group-editor__configuration">






        <section class="mango-task-group-editor__section">
          <header class="mango-task-group-editor__section-header">
            <div>
              <strong>基础信息</strong>
              <span>设置任务组名称及所属项目产品</span>
            </div>
          </header>
          <div class="mango-task-group-editor__grid">
            <a-form-item label="任务组名称" required>
              <a-input :disabled="editorLocked" v-model="form.name" :max-length="64" placeholder="例如：WEB前端－测试回归" />
            </a-form-item>
            <a-form-item label="项目/产品" required>
              <ProjectProductSelect
                v-model="productSelection"
                :disabled="editingId !== null || editorLocked"
                placeholder="请选择项目/产品"
                @change="onEditorProductChange"
              />
            </a-form-item>
            <a-form-item label="子任务名称模板" class="mango-task-group-editor__wide">
              <a-input
                :model-value="DEFAULT_TASK_NAME_TEMPLATE"
                disabled
                title="子任务名称由系统按任务组名称和模块完整路径自动生成"
              />
            </a-form-item>
          </div>
        </section>

        <section class="mango-task-group-editor__section">
          <header class="mango-task-group-editor__section-header">
            <div>
              <strong>公共执行规则</strong>
              <span>调度、环境、场景、用例类型和通知统一同步；负责人仅作为新子任务默认值</span>
            </div>
          </header>
          <div class="mango-task-group-editor__grid">
            <a-form-item label="定时策略" required>
              <a-select
                :disabled="editorLocked"
                v-model="form.timing_strategies"
                multiple
                allow-search
                :max-tag-count="1"
                :field-names="fieldNames"
                :options="availableTimings"
                :loading="timingsLoading"
                placeholder="请选择定时策略"
              />
            </a-form-item>
            <a-form-item label="测试环境" required>
              <a-select
                :disabled="editorLocked"
                v-model="form.test_envs"
                multiple
                :max-tag-count="1"
                :field-names="fieldNames"
                :options="environmentOptions"
                :loading="enumsLoading"
                placeholder="请选择测试环境"
                @change="onEnvironmentChange"
              />
            </a-form-item>
            <a-form-item label="用例类型">
              <a-select
                :disabled="editorLocked"
                v-model="form.case_types"
                multiple
                :max-tag-count="1"
                :field-names="fieldNames"
                :options="caseTypeOptions"
                placeholder="留空表示全部类型"
              />
            </a-form-item>
            <a-form-item label="执行场景" required>
              <a-select
                :disabled="editorLocked"
                v-model="form.execution_scenes"
                multiple
                :max-tag-count="1"
                :field-names="fieldNames"
                :options="mutuallyExclusiveSceneOptions"
                placeholder="请选择执行场景"
              />
            </a-form-item>
            <a-form-item label="默认负责人" required>
              <a-select
                :disabled="editorLocked"
                v-model="form.case_people"
                allow-search
                :field-names="fieldNames"
                :options="availableUsers"
                :loading="usersLoading"
                placeholder="请选择负责人"
              />
            </a-form-item>
            <a-form-item label="是否开启">
              <a-switch size="small" :disabled="editorLocked" v-model="form.status" :checked-value="1" :unchecked-value="0" />
            </a-form-item>
            <a-form-item label="发送通知">
              <a-switch size="small" :disabled="editorLocked" v-model="form.is_notice" :checked-value="1" :unchecked-value="0" />
            </a-form-item>
            <a-form-item label="失败通知">
              <a-switch size="small" :disabled="editorLocked" v-model="form.fail_notice" :checked-value="1" :unchecked-value="0" />
            </a-form-item>
            <a-form-item label="通知组">
              <a-select
                :disabled="editorLocked"
                v-model="form.notice_group"
                allow-clear
                :options="availableNotices"
                :field-names="fieldNames"
                :loading="noticesLoading"
                placeholder="可先选择，开启通知后生效"
              />
            </a-form-item>
            <a-form-item v-if="editingId === null" label="报告保留策略">
              <a-select :disabled="editorLocked" v-model="form.new_task_report_retention_policy" :field-names="fieldNames"
                :options="retentionOptions"
                :loading="enumsLoading" />
            </a-form-item>
          </div>
        </section>

        </div>
        <section class="mango-task-group-editor__section mango-task-group-editor__modules">
          <header class="mango-task-group-editor__section-header">
            <div>
              <strong>拆分模块</strong>
              <span>每个选中模块生成一条“模块全量”定时任务</span>
            </div>
            <a-tag size="small">已选择 {{ form.module_ids.length }} 个</a-tag>
          </header>
          <div v-if="form.project_product_id === null" class="mango-task-group-editor__module-empty">
            请先选择项目/产品，再选择需要拆分的模块
          </div>
          <div v-else class="mango-task-group-editor__tree">

            <a-tree
              v-model:expanded-keys="expandedModuleKeys"
              :checked-keys="form.module_ids"
              :disabled="editorLocked"
              :data="selectableModuleTree"
              :loading="!editorLoading && moduleLoading"
              checkable
              check-strictly
              block-node
              @check="onModuleCheck"
            />
          </div>
          <div v-if="form.project_product_id !== null" class="mango-task-group-editor__module-help">
            选中上级模块后将覆盖其整个子树，下级模块无需重复选择。
          </div>
        </section>
      </a-form>
    </mango-panel-spin>
    <template #footer>
      <a-space :size="12" class="mango-modal-dialog-footer-actions">
        <a-button @click="close">取消</a-button>
        <a-button  type="primary" :loading="previewLoading" :disabled="saveLoading || editorLoading || !detailReady" @click="openPreview">
          预览并保存
        </a-button>
      </a-space>
    </template>
  </a-modal>

  <a-modal
    v-model:visible="previewVisible"
    title="任务组拆分预览"
    width="min(960px, calc(100vw - 32px))"
    :mask-closable="false"
    :ok-loading="saveLoading"
    ok-text="确认保存"
    cancel-text="返回修改"
    :on-before-ok="saveGroup"
    @cancel="closePreview"
  >
    <a-alert v-if="saveError" type="error">{{ saveError }}</a-alert>
    <a-space class="mango-task-group-preview__summary">
      <a-tag color="green">新增 {{ preview?.create_count ?? 0 }}</a-tag>
      <a-tag color="blue">更新 {{ preview?.update_count ?? 0 }}</a-tag>
      <a-tag color="orange">移除 {{ preview?.remove_count ?? 0 }}</a-tag>
    </a-space>
    <a-table
      :data="preview?.rows || []"
      :pagination="false"
      :scroll="{ x: 760, y: 420 }"
      class="mango-native-scroll-table"
      row-key="module_id"
    >
      <template #columns>
        <a-table-column title="变更" :width="90" align="center">
          <template #cell="{ record }">
            <a-tag :color="previewActionColor(record.action)" size="small">
              {{ previewActionText(record.action) }}
            </a-tag>
          </template>
        </a-table-column>
        <a-table-column title="模块" data-index="module_full_path" :width="300" ellipsis tooltip />
        <a-table-column title="定时任务名称" data-index="task_name" :width="360" ellipsis tooltip />
      </template>
    </a-table>
  </a-modal>

</template>

<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, reactive, ref, watch } from 'vue'
import { Message } from '@arco-design/web-vue'
import { useRoute } from 'vue-router'
import useUserStore from '@/store/modules/user'
import usePermissionStore from '@/store/modules/permission'
import { useEnum } from '@/store/modules/get-enum'
import { fieldNames } from '@/setting'
import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
import { getUserModuleTree } from '@/api/system/module'
import { getSystemTimingList } from '@/api/system/time'
import { getSystemNoticeName } from '@/api/system/notice_group'
import { getUserName } from '@/api/user/user'
import { createScheduledTaskGroup, getScheduledTaskGroupDetail, previewScheduledTaskGroup, updateScheduledTaskGroup } from '@/api/system/tasks'
import type { NavigationCreateSelection } from '@/utils/navigation-create-defaults'
import { taskEditorId, taskEditorResponse, readTaskEditorOptions, taskEditorSelectedOptions, type TaskEditorId, type TaskEditorOption } from '../task-editor-records'
import { taskListId } from '../task-list-records'
import { DEFAULT_TASK_NAME_TEMPLATE, createTaskGroupDraft, readTaskGroupDraft, readTaskGroupEditorDetail, taskGroupPayload, validateTaskGroupDraft, groupSceneOptions,
  readTaskModuleTree, flattenTaskModuleKeys, normalizeTaskGroupModules, taskGroupSelectableTree, readTaskGroupPreview, type TaskModuleNode, type TaskGroupPayload, type TaskGroupPreview } from '../task-group-editor-records'
import { useTaskEditorResource } from '../composables/useTaskEditorResource'

const emit = defineEmits<{ (event: 'saved'): void }>()
const route = useRoute(), user = useUserStore(), permission = usePermissionStore(), enumStore = useEnum(), pagePath = route.path
let active = true, disposed = false, editorVersion = 0, detailVersion = 0, previewVersion = 0, enumVersion = 0, moduleSelectionVersion = 0, pendingEnvironmentSync = false
const editorVisible = ref(false), editingId = ref<TaskEditorId | null>(null), editorLoading = ref(false), detailReady = ref(false), detailError = ref('')
const previewVisible = ref(false), previewLoading = ref(false), saveLoading = ref(false), previewError = ref(''), saveError = ref('')
const preview = ref<TaskGroupPreview | null>(null), previewSnapshot = ref<TaskGroupPayload | null>(null)
const form = reactive(createTaskGroupDraft()), expandedModuleKeys = ref<TaskEditorId[]>([])
const fallbackUsers = ref<TaskEditorOption[]>([]), fallbackTimings = ref<TaskEditorOption[]>([]), fallbackNotices = ref<TaskEditorOption[]>([])
const identity = () => JSON.stringify([route.path, route.fullPath, user.userId, user.roleId, user.token, user.selected_environment, permission.permissionKeys])
const available = () => active && !disposed && route.path === pagePath && document.visibilityState === 'visible'
function capture() {
  const version = editorVersion, key = identity()
  return () => available() && editorVisible.value && version === editorVersion && key === identity()
}
const captureProduct = () => { const valid = capture(), product = form.project_product_id; return () => valid() && product === form.project_product_id }
const users = useTaskEditorResource<TaskEditorOption[]>(capture, '负责人加载失败')
const timings = useTaskEditorResource<TaskEditorOption[]>(capture, '定时策略加载失败')
const notices = useTaskEditorResource<TaskEditorOption[]>(captureProduct, '通知组加载失败')
const modules = useTaskEditorResource<TaskModuleNode[]>(captureProduct, '模块树加载失败')
const { value: userOptions, loading: usersLoading, error: usersError } = users, { value: timingOptions, loading: timingsLoading, error: timingsError } = timings
const { value: noticeOptions, loading: noticesLoading, error: noticesError } = notices, { value: moduleTree, loading: moduleLoading, error: moduleError } = modules
const enumsLoading = ref(false), enumsError = ref(''), enumsReady = ref(false)
const metadataErrors = computed(() => [users.error.value, timings.error.value, notices.error.value, enumsError.value].filter(Boolean))
const metadataLoading = computed(() => usersLoading.value || timingsLoading.value || noticesLoading.value || moduleLoading.value || enumsLoading.value)
const editorLocked = computed(() => editorLoading.value || !detailReady.value || previewLoading.value || previewVisible.value || saveLoading.value)
const enumOptions = (value: unknown) => readTaskEditorOptions(value ?? [])
const environmentOptions = computed(() => enumOptions(enumStore.environment_type))
const caseTypeOptions = computed(() => enumOptions(enumStore.test_case_type).map(item => ({ ...item, disabled: [3,4].includes(Number(item.key)) })))
const mutuallyExclusiveSceneOptions = computed(() => groupSceneOptions(enumOptions(enumStore.automation_execution_scene), form.test_envs, form.execution_scenes))
const retentionOptions = computed(() => enumOptions(enumStore.report_retention_policy))
const availableUsers = computed(() => { const id = taskEditorId(form.case_people); return taskEditorSelectedOptions(userOptions.value || [], id === null ? [] : [id], fallbackUsers.value) })
const availableTimings = computed(() => taskEditorSelectedOptions(timingOptions.value || [], form.timing_strategies, fallbackTimings.value))
const availableNotices = computed(() => { const id = taskEditorId(form.notice_group); return taskEditorSelectedOptions(noticeOptions.value || [], id === null ? [] : [id], fallbackNotices.value) })
const selectableModuleTree = computed(() => taskGroupSelectableTree(moduleTree.value || [], form.module_ids))
const productSelection = computed({ get: () => form.project_product_id, set: (value: unknown) => { if (editingId.value === null && !editorLocked.value) form.project_product_id = taskEditorId(value) } })
function closePreview() { previewVersion++; previewVisible.value = false; previewLoading.value = false; preview.value = null; previewSnapshot.value = null; previewError.value = ''; saveError.value = '' }
function close() {
  editorVersion++; detailVersion++; enumVersion++; moduleSelectionVersion++; pendingEnvironmentSync = false; closePreview()
  editorVisible.value = false; editingId.value = null; Object.assign(form, createTaskGroupDraft())
  editorLoading.value = false; detailReady.value = false; detailError.value = ''; expandedModuleKeys.value = []
  users.clear(); timings.clear(); notices.clear(); modules.clear(); fallbackUsers.value = []; fallbackTimings.value = []; fallbackNotices.value = []
  enumsLoading.value = false; enumsError.value = ''; enumsReady.value = false
}
async function loadEnums() {
  if (!editorVisible.value || !available()) return
  const version = ++enumVersion, current = capture(); enumsLoading.value = true; enumsError.value = ''; enumsReady.value = false
  try {
    await enumStore.getEnum()
    if (version === enumVersion && current()) { enumsReady.value = true; if (pendingEnvironmentSync) onEnvironmentChange() }
  }
  catch (loadFailure0) { if (version === enumVersion && current()) (reportLoadError(loadFailure0, "枚举加载失败", false), enumsError.value = '枚举加载失败') }
  finally { if (version === enumVersion && current()) enumsLoading.value = false }
}
function loadUsers() { if (editorVisible.value && available()) return users.load(getUserName, readTaskEditorOptions) }
function loadTimings() { if (editorVisible.value && available()) return timings.load(getSystemTimingList, readTaskEditorOptions) }
function loadCommonEditorOptions() { return Promise.allSettled([loadUsers(), loadTimings(), loadEnums()]) }
async function loadModules(initialModule?: TaskEditorId | null) {
  if (!editorVisible.value || !available()) return
  const product = form.project_product_id
  if (product === null) { modules.clear(); return }
  const current = captureProduct(), selection = moduleSelectionVersion
  const loaded = await modules.load(() => getUserModuleTree(product), readTaskModuleTree)
  if (!loaded || !current()) return
  const tree = moduleTree.value || []
  expandedModuleKeys.value = flattenTaskModuleKeys(tree)
  if (initialModule != null && selection === moduleSelectionVersion && !form.module_ids.length && expandedModuleKeys.value.some(id => String(id) === String(initialModule))) form.module_ids = [initialModule]
  form.module_ids = normalizeTaskGroupModules(form.module_ids, tree)
}
function loadNotices() {
  if (!editorVisible.value || !available()) return
  const product = form.project_product_id
  if (product === null) { notices.clear(); return }
  return notices.load(() => getSystemNoticeName(product), readTaskEditorOptions)
}
function loadProductEditorOptions(initialModule?: TaskEditorId | null) {
  return Promise.allSettled([loadModules(initialModule), loadNotices()])
}
async function onEditorProductChange(value: unknown) {
  if (editingId.value !== null || editorLocked.value || !editorVisible.value) return
  form.project_product_id = taskEditorId(value); moduleSelectionVersion++; closePreview()
  form.module_ids = []; form.notice_group = null; expandedModuleKeys.value = []; fallbackNotices.value = []
  modules.clear(); notices.clear(); return loadProductEditorOptions()
}
function onModuleCheck(keys: TaskEditorId[]) {
  if (editorLocked.value) return
  moduleSelectionVersion++; form.module_ids = normalizeTaskGroupModules(keys, moduleTree.value || [])
}
function onEnvironmentChange() {
  if (editorLocked.value) return
  if (!enumsReady.value) { pendingEnvironmentSync = true; return }
  pendingEnvironmentSync = false
  const allowed = new Set(mutuallyExclusiveSceneOptions.value.map(item => String(item.key)))
  form.execution_scenes = form.execution_scenes.filter(scene => allowed.has(scene))
}
async function openCreate(selection?: NavigationCreateSelection) {
  if (!available() || saveLoading.value) return
  close()
  try {
    form.project_product_id = taskEditorId(selection?.projectProduct)
    editorVisible.value = true; detailReady.value = true
    await Promise.allSettled([loadCommonEditorOptions(), loadProductEditorOptions(selection?.module)])
  } catch { close(); Message.error('任务组初始数据格式异常，请重新打开') }
}
async function loadDetail() {
  if (!editorVisible.value || !available() || editingId.value === null || saveLoading.value) return
  const id = editingId.value, version = ++detailVersion, current = capture()
  editorLoading.value = true; detailError.value = ''; detailReady.value = false
  try {
    const result = readTaskGroupEditorDetail(await getScheduledTaskGroupDetail(id), id)
    if (version !== detailVersion || !current()) return
    Object.assign(form, result.draft); fallbackUsers.value = result.users; fallbackTimings.value = result.timings; fallbackNotices.value = result.notices
    detailReady.value = true
    void loadProductEditorOptions()
  } catch (loadFailure1) { if (version === detailVersion && current()) (reportLoadError(loadFailure1, "任务组配置加载失败，请重试", false), detailError.value = '任务组配置加载失败，请重试') }
  finally { if (version === detailVersion && current()) editorLoading.value = false }
}
async function openEdit(id: TaskEditorId) {
  if (!available() || saveLoading.value) return
  close()
  try { editingId.value = taskListId(id); editorVisible.value = true; await Promise.allSettled([loadDetail(), loadCommonEditorOptions()]) }
  catch { close(); Message.error('任务组数据格式异常，请刷新后重试') }
}
function retryMetadata() {
  if (!editorVisible.value || !available() || saveLoading.value || metadataLoading.value) return Promise.resolve([])
  return Promise.allSettled([loadCommonEditorOptions(), loadProductEditorOptions()])
}
async function openPreview() {
  if (!editorVisible.value || !available() || previewLoading.value || saveLoading.value || previewVisible.value) return
  const current = capture(), version = ++previewVersion
  previewError.value = ''; saveError.value = ''
  if (!detailReady.value || editorLoading.value || moduleLoading.value || moduleError.value || moduleTree.value === null || !enumsReady.value || enumsLoading.value) { previewError.value = '请等待配置加载完成，加载失败时先重试'; return }
  try {
    const draft = readTaskGroupDraft(form), error = validateTaskGroupDraft(draft)
    if (error) { previewError.value = error; return }
    const payload = taskGroupPayload(draft, editingId.value)
    previewLoading.value = true
    const result = readTaskGroupPreview(taskEditorResponse(await previewScheduledTaskGroup(payload)))
    if (version !== previewVersion || !current()) return
    preview.value = result; previewSnapshot.value = payload; previewVisible.value = true
  } catch (loadFailure2) { if (version === previewVersion && current()) (reportLoadError(loadFailure2, "加载失败，请重试", false), previewError.value = '任务组预览失败，请重试') }
  finally { if (version === previewVersion) previewLoading.value = false }
}
async function saveGroup(): Promise<boolean> {
  if (!available() || !editorVisible.value || !previewVisible.value || !previewSnapshot.value || saveLoading.value) return false
  const snapshot = previewSnapshot.value, payload = taskGroupPayload(readTaskGroupDraft(snapshot), snapshot.id ?? null)
  const current = capture(), version = previewVersion, key = identity(), id = payload.id
  const validWindow = () => current() && version === previewVersion && previewVisible.value
  saveLoading.value = true; saveError.value = ''
  try {
    taskEditorResponse(await (id === undefined ? createScheduledTaskGroup(payload) : updateScheduledTaskGroup(payload)))
    if (key === identity() && available()) emit('saved')
    if (validWindow()) { close(); Message.success('任务组已保存') }
    return true
  } catch { if (validWindow()) saveError.value = '任务组保存失败，请重试'; return false }
  finally { saveLoading.value = false }
}
function previewActionText(value: string) { return value === 'create' ? '新增' : value === 'update' ? '更新' : '移除' }
function previewActionColor(value: string) { return value === 'create' ? 'green' : value === 'update' ? 'blue' : 'orange' }
function visibilityChanged() { if (document.visibilityState !== 'visible') close() }
watch(identity, close, { flush: 'sync' })
onMounted(() => document.addEventListener('visibilitychange', visibilityChanged))
onActivated(() => { active = true })
onDeactivated(() => { active = false; close() })
onBeforeUnmount(() => { disposed = true; close(); document.removeEventListener('visibilitychange', visibilityChanged) })
defineExpose({ openCreate, openEdit, close })
</script>

<style scoped>
  .mango-task-group-editor__spin {
    display: block;
    width: 100%;
  }

  :global(.arco-modal-body.mango-task-group-editor-body) {
    box-sizing: border-box;
    height: min(760px, calc(100dvh - 144px));
    min-height: 0;
    overflow: hidden;
  }

  .mango-task-group-editor__spin,
  .mango-task-group-editor__spin :deep(> .mango-panel-spin__content) {
    height: 100%;
    min-height: 0;
  }

  .mango-task-group-editor {
    display: grid;
    grid-template-rows: minmax(0, auto) minmax(120px, 1fr);
    height: 100%;
    min-height: 0;
    overflow: hidden;
  }

  .mango-task-group-editor__configuration {
    min-height: 0;
    overflow: auto;
    overscroll-behavior: contain;
  }

  .mango-task-group-editor__section {
    padding: var(--m-space-md) 0 var(--m-space-xs);
    border-bottom: 1px solid var(--m-border);
  }

  .mango-task-group-editor__section:first-child {
    padding-top: 0;
  }

  .mango-task-group-editor__section:last-child {
    border-bottom: 0;
  }

  .mango-task-group-editor__section-header {
    display: flex;
    min-height: 28px;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 10px;
    flex-shrink: 0;
  }

  .mango-task-group-editor__section-header > div,
  .mango-task-group-editor__section-header > strong {
    display: flex;
    align-items: center;
  }

  .mango-task-group-editor__section-header strong {
    color: var(--m-text);
    font-size: 15px;
    font-weight: 600;
  }

  .mango-task-group-editor__section-header span {
    margin-left: 10px;
    color: var(--m-muted);
    font-size: 13px;
    font-weight: 400;
  }

  .mango-task-group-editor__grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    column-gap: var(--m-space-lg);
  }

  .mango-task-group-editor__grid :deep(.arco-form-item) {
    display: flex;
    flex-direction: row;
    flex-wrap: nowrap;
    align-items: center;
    margin-bottom: var(--m-space-sm);
  }

  .mango-task-group-editor__grid :deep(.arco-form-item-label-col) {
    display: flex;
    width: 112px;
    max-width: 112px;
    flex: 0 0 112px;
    align-items: center;
    justify-content: flex-end;
    padding-right: var(--m-space-sm);
  }

  .mango-task-group-editor__grid :deep(.arco-form-item-wrapper-col) {
    min-width: 0;
    width: 0;
    max-width: none;
    flex: 1 1 0;
  }

  .mango-task-group-editor__grid :deep(.arco-form-item-content-flex) {
    width: 100%;
  }

  .mango-task-group-editor__wide {
    grid-column: 1 / -1;
  }

  .mango-task-group-editor__modules {
    display: flex;
    flex-direction: column;
    min-height: 0;
  }

  .mango-task-group-editor__tree {
    flex: 1;
    min-height: 0;
    overflow: auto;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius);
    background: var(--m-surface-soft);
    padding: var(--m-space-sm) var(--m-card-padding);
    overscroll-behavior: contain;
  }

  .mango-task-group-editor__module-empty {
    display: flex;
    flex: 1;
    min-height: 0;
    align-items: center;
    justify-content: center;
    border: 1px dashed var(--m-border);
    border-radius: var(--m-radius);
    color: var(--m-muted);
  }

  .mango-task-group-editor__module-help {
    flex-shrink: 0;
    margin-top: 6px;
    color: var(--m-muted);
    font-size: 12px;
  }

  .mango-task-group-preview__summary {
    margin-bottom: var(--m-page-gap);
  }

</style>
