<template>
  <a-modal modal-class="mango-simple-form-modal" :visible="visible" title="编辑" :width="560" :ok-loading="saving" :on-before-ok="save" @cancel="close" @update:visible="onVisibleChange">
    <a-form :model="draft" layout="horizontal" auto-label-width :disabled="saving" class="mango-pytest-case-editor mango-simple-form">
      <a-form-item label="项目/产品" class="mango-form-item__require mango-simple-form-item">
        <a-cascader :model-value="draft.project_product" :options="projects.projectPytest2" :loading="projectLoading" :disabled="saving || projectLoading || projectFailed" allow-search allow-clear placeholder="请选择项目名称" @change="changeProject" />
        <template v-if="projectFailed" #extra><a-button size="small" :loading="projectLoading" @click="loadProjects">重试</a-button></template>
      </a-form-item>
      <a-form-item label="所属模块" class="mango-form-item__require mango-simple-form-item">
        <ProductModuleSelect v-model="draft.module" :project-product-id="realProductId" :disabled="saving || projectLoading || projectFailed || !realProductId" :auto-clear="false" :selectable-level="3" placeholder="请选择模块名称" />
      </a-form-item>
      <a-form-item label="用例名称" class="mango-form-item__require mango-pytest-case-editor__wide mango-simple-form-item"><a-input v-model="draft.name" placeholder="请输入名称" /></a-form-item>
      <a-form-item v-for="field of enumFields" :key="field.key" :label="field.label" class="mango-form-item__require mango-simple-form-item">
        <a-select v-model="draft[field.key]" :options="field.options" :field-names="fieldNames" allow-clear allow-search :placeholder="`请选择${field.label}`" />
      </a-form-item>
      <a-form-item label="执行场景" class="mango-form-item__require mango-simple-form-item"><a-select v-model="draft.scenario_tags" :options="enumStore.api_case_scenario_tag" :field-names="fieldNames" multiple :max-tag-count="1" allow-clear allow-search placeholder="请选择执行场景" /></a-form-item>
      <a-form-item label="用例负责人" class="mango-form-item__require mango-simple-form-item">
        <a-select v-model="draft.case_people" :options="userOptions" :field-names="fieldNames" :loading="userLoading" :disabled="saving || userLoading || userFailed" allow-clear allow-search placeholder="请设置用例负责人" />
        <template v-if="userFailed" #extra><a-button size="small" :loading="userLoading" @click="loadUsers">重试</a-button></template>
      </a-form-item>
      <a-form-item label="场景描述" class="mango-pytest-case-editor__wide mango-simple-form-item"><a-textarea v-model="draft.scenario_description" placeholder="请输入场景描述" :auto-size="{ minRows: 2, maxRows: 5 }" /></a-form-item>
    </a-form>
  </a-modal>
</template>

<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, reactive, ref, watch } from 'vue'
  import { useRoute } from 'vue-router'
  import { Message } from '@arco-design/web-vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import { useProject } from '@/store/modules/get-project'
  import useUserStore from '@/store/modules/user'
  import { useEnum } from '@/store/modules/get-enum'
  import { getUserName } from '@/api/user/user'
  import { putPytestCase } from '@/api/pytest/case'
  import { fieldNames } from '@/setting'
  import { batchId, batchSuccess } from '../batch-editor'
  import type { BatchUserOption } from '../batch-editor'
  import { caseDraft, caseEditorPayload, caseEditorRecord, checkCaseSave, emptyCaseDraft } from '../editor'
  import type { CaseEditorRecord } from '../editor'

  const emit = defineEmits<{ (event: 'saved', caseId: number): void }>()
  const projects = useProject(), user = useUserStore(), route = useRoute(), enumStore = useEnum()
  const visible = ref(false), saving = ref(false), record = ref<CaseEditorRecord | null>(null)
  const draft = reactive(emptyCaseDraft()), userOptions = ref<BatchUserOption[]>([])
  const projectLoading = ref(false), projectFailed = ref(false), userLoading = ref(false), userFailed = ref(false)
  let version = 0, projectRequest = 0, userRequest = 0, active = true, disposed = false
  const available = () => !disposed && active && (typeof document === 'undefined' || !document.hidden)
  const current = (window: number) => available() && visible.value && version === window
  const realProductId = computed(() => projectFailed.value ? null : projects.getPytestProjectProductId(draft.project_product))
  const assetOptions = computed(() => (enumStore.pytest_asset_status || []).filter(option => record.value?.publication_status === 'prepublished'
    ? Number(option.key) === Number(record.value.asset_status)
    : (Number(option.key) === 1) === (record.value?.publication_status === 'published')))
  const enumFields = computed(() => [
    { key: 'asset_status' as const, label: '资产状态', options: assetOptions.value },
    { key: 'level' as const, label: '优先级', options: enumStore.case_level },
    { key: 'scenario_layer' as const, label: '测试层级', options: enumStore.api_case_scenario_layer },
    { key: 'scenario_type' as const, label: '验证类型', options: enumStore.api_case_scenario_type },
  ])
  function close(): void {
    version++; projectRequest++; userRequest++; visible.value = false; record.value = null
    Object.assign(draft, emptyCaseDraft()); userOptions.value = []
    projectLoading.value = false; userLoading.value = false; projectFailed.value = false; userFailed.value = false
  }
  function onVisibleChange(value: boolean): void { if (!value) close() }
  function open(value: unknown): void {
    if (!available() || saving.value) return
    let next: CaseEditorRecord
    try { next = caseEditorRecord(value) } catch { Message.error('用例信息不完整，请重新加载'); return }
    close(); record.value = next; Object.assign(draft, caseDraft(next)); visible.value = true
    void loadProjects(); void loadUsers()
  }
  async function loadProjects(): Promise<void> {
    if (!current(version) || projectLoading.value) return
    const window = version, request = ++projectRequest
    projectLoading.value = true; projectFailed.value = false
    try { await projects.projectPytestName(); if (projects.optionErrors.pytest) throw new Error('项目加载失败') }
    catch (loadFailure0) { if (current(window) && request === projectRequest) (reportLoadError(loadFailure0, "加载失败，请重试", false), projectFailed.value = true) }
    finally { if (current(window) && request === projectRequest) projectLoading.value = false }
  }
  async function loadUsers(): Promise<void> {
    if (!current(version) || userLoading.value) return
    const window = version, request = ++userRequest
    userLoading.value = true; userFailed.value = false
    try {
      const response = batchSuccess(await getUserName())
      if (!current(window) || request !== userRequest) return
      if (!Array.isArray(response.data)) throw new Error('用户选项格式不正确')
      const options = response.data.map(value => {
        if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('用户选项格式不正确')
        const row = value as Record<string, unknown>
        if (typeof row.title !== 'string') throw new Error('用户名称格式不正确')
        return { key: batchId(row.key), title: row.title }
      })
      userOptions.value = options
    } catch (loadFailure1) { if (current(window) && request === userRequest) (reportLoadError(loadFailure1, "加载失败，请重试", false), userFailed.value = true) }
    finally { if (current(window) && request === userRequest) userLoading.value = false }
  }
  function changeProject(value: unknown): void {
    if (saving.value || projectLoading.value || projectFailed.value) return
    const leaf = Array.isArray(value) ? value[value.length - 1] : value
    let next: number | null = null
    try { if (leaf != null && leaf !== '') next = batchId(leaf) } catch { return }
    if (next !== draft.project_product) { draft.project_product = next; draft.module = null }
  }
  async function save(): Promise<boolean> {
    if (!current(version) || saving.value || !record.value || projectLoading.value || userLoading.value || projectFailed.value || userFailed.value) return false
    const window = version
    let payload: ReturnType<typeof caseEditorPayload>
    try { payload = caseEditorPayload(draft, record.value, projects.projectPytest2) }
    catch (error) { Message.warning(error instanceof Error ? error.message : '请检查输入'); return false }
    saving.value = true
    try {
      checkCaseSave(await putPytestCase(payload))
      if (!current(window)) return false
      close(); Message.success('保存成功'); emit('saved', payload.id)
      return true
    } catch { if (current(window)) Message.error('保存失败，请重试'); return false }
    finally { saving.value = false }
  }
  watch(() => [user.userId, user.roleId, user.token, user.selected_environment, route.fullPath], close, { flush: 'sync' })
  function visibilityChanged(): void { if (typeof document !== 'undefined' && document.hidden) close() }
  onMounted(() => { if (typeof document !== 'undefined') document.addEventListener('visibilitychange', visibilityChanged) })
  onActivated(() => { active = true })
  onDeactivated(() => { active = false; close() })
  onBeforeUnmount(() => { disposed = true; close(); if (typeof document !== 'undefined') document.removeEventListener('visibilitychange', visibilityChanged) })
  defineExpose({ open, close })
</script>

<style scoped lang="less">
  .mango-pytest-case-editor {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    column-gap: 16px;
    &__wide { grid-column: 1 / -1; }
  }
</style>
