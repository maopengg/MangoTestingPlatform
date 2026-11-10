<template>
  <a-modal modal-class="mango-simple-form-modal" v-model:visible="visible" :title="title" :width="560" :on-before-cancel="cancel" :footer="false" class="mango-modal-dialog-wrapper" @keydown.enter="onEnter">
    <a-form auto-label-width :model="draft" layout="horizontal" class="mango-monitoring-task-editor mango-simple-form" :disabled="saving">
      <a-form-item label="项目/产品" class="mango-form-item__require mango-simple-form-item">
        <ProjectProductSelect v-model="draft.project_product" placeholder="请选择项目名称" :disabled="saving" @change="onProductChange" />
      </a-form-item>
      <a-form-item label="任务名称" class="mango-form-item__require mango-simple-form-item">
        <a-input v-model="draft.name" placeholder="请输入任务名称" />
      </a-form-item>
      <a-form-item label="任务描述" class="mango-monitoring-task-editor__wide mango-simple-form-item">
        <a-input :model-value="draft.description ?? ''" placeholder="请输入任务描述" @update:model-value="draft.description = $event" />
      </a-form-item>
      <a-form-item class="mango-simple-form-item" label="测试环境">
        <a-select v-model="draft.test_env" :options="enumStore.environment_type" :field-names="fieldNames" placeholder="可选；选择后向脚本注入域名和数据库配置" allow-clear allow-search value-key="key" />
      </a-form-item>
      <a-form-item class="mango-simple-form-item" label="是否通知">
        <a-switch v-model="draft.is_notice" :checked-value="1" :unchecked-value="0" size="small" />
      </a-form-item>
      <a-form-item label="通知组" class="mango-monitoring-task-editor__wide mango-simple-form-item">
        <a-select v-model="draft.notice_group" :options="noticeOptions" :loading="noticeLoading" placeholder="请选择通知组" allow-clear allow-search />
        <template v-if="noticeFailed" #extra><a-button type="text" size="small" :loading="noticeLoading" @click="loadNotices">重试</a-button>
        </template>
      </a-form-item>
      <a-form-item v-if="recordId === null" label="脚本内容" class="mango-form-item__require mango-monitoring-task-editor__wide mango-simple-form-item">
        <a-textarea v-model="draft.script_content" placeholder="请粘贴 python 脚本内容" :auto-size="{ minRows: 3, maxRows: 6 }" />
      </a-form-item>
    </a-form>
    <a-space class="mango-modal-dialog-footer-actions mango-monitoring-task-editor__footer">
      <a-button :disabled="saving" @click="cancel">取消</a-button>
      <a-button type="primary" :loading="saving" @click="save">提交</a-button>
    </a-space>
  </a-modal>
</template>

<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { computed, reactive, ref } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import { getSystemNoticeName } from '@/api/system/notice_group'
  import { postMonitoringTask, putMonitoringTask } from '@/api/monitoring/task'
  import { useEnum } from '@/store/modules/get-enum'
  import { fieldNames } from '@/setting'
  import { createTaskEditorDraft, productId, readNoticeOptions, readTaskEditorRecord, taskEditorPayload } from '../editor-draft'
  import { useMonitoringTaskScope } from '../composables/useMonitoringTaskScope'
  import type { NoticeOption, ProductSelection, TaskEditorHandle } from '../types'

  const emit = defineEmits<{
    (event: 'saved'): void
    (event: 'saving-change', pending: boolean, recordId: number | null): void
  }>()
  const enumStore = useEnum()
  const visible = ref(false), recordId = ref<number | null>(null), saving = ref(false)
  const draft = reactive(createTaskEditorDraft())
  const title = computed(() => recordId.value === null ? '新增' : '编辑')
  const noticeOptions = ref<NoticeOption[]>([]), noticeLoading = ref(false), noticeFailed = ref(false)
  let currentNotice: NoticeOption | null = null
  let windowVersion = 0, noticeSequence = 0
  const scope = useMonitoringTaskScope(close)

  function close() {
    ++windowVersion
    ++noticeSequence
    visible.value = false
    recordId.value = null
    Object.assign(draft, createTaskEditorDraft())
    currentNotice = null
    noticeOptions.value = []
    noticeLoading.value = false
    noticeFailed.value = false
  }
  function cancel() {
    if (saving.value) return false
    close()
    return true
  }
  function openCreate(product: ProductSelection = null) {
    if (!scope.available() || saving.value) return
    close()
    Object.assign(draft, createTaskEditorDraft(product))
    visible.value = true
    void loadNotices()
  }
  function openEdit(value: unknown) {
    if (!scope.available() || saving.value) return
    close()
    try {
      const record = readTaskEditorRecord(value)
      recordId.value = record.id
      Object.assign(draft, record.draft)
      currentNotice = record.group
      noticeOptions.value = record.group ? [{ ...record.group }] : []
      visible.value = true
      void loadNotices()
    } catch { Message.error('任务配置加载失败，请重试') }
  }
  function onProductChange(value: ProductSelection) {
    draft.project_product = value
    draft.notice_group = null
    currentNotice = null
    noticeOptions.value = []
    return loadNotices()
  }
  function onEnter(event: KeyboardEvent) {
    if (event.isComposing || event.keyCode === 229) return
    const target = event.target as HTMLElement | null
    if (target?.tagName === 'TEXTAREA' || target?.closest('.arco-input-tag, .CodeMirror-code, .ace_editor, .cm-content')) return
    event.preventDefault()
    void save()
  }
  async function loadNotices() {
    if (!scope.available() || !visible.value) return
    const id = productId(draft.project_product), sequence = ++noticeSequence
    const window = windowVersion, version = scope.snapshot()
    const current = () => scope.current(version) && visible.value && window === windowVersion && sequence === noticeSequence && id === productId(draft.project_product)
    noticeFailed.value = false
    if (id === null) { noticeOptions.value = []; noticeLoading.value = false; return }
    noticeLoading.value = true
    try {
      const response = await getSystemNoticeName(id)
      if (!current()) return
      const options = readNoticeOptions(response)
      if (currentNotice && draft.notice_group === currentNotice.value && !options.some(item => item.value === currentNotice?.value)) options.unshift({ ...currentNotice })
      noticeOptions.value = options
    } catch (loadFailure0) { if (current()) (reportLoadError(loadFailure0, "加载失败，请重试", false), noticeFailed.value = true) }
    finally { if (current()) noticeLoading.value = false }
  }
  async function save() {
    if (!scope.available() || !visible.value || saving.value) return false
    let payload: ReturnType<typeof taskEditorPayload>
    try { payload = taskEditorPayload(draft, recordId.value) }
    catch (error) { Message.error(error instanceof Error ? error.message : '请检查任务配置'); return false }
    const window = windowVersion, version = scope.snapshot(), id = recordId.value
    const current = () => scope.current(version) && visible.value && window === windowVersion
    saving.value = true
    emit('saving-change', true, id)
    try {
      const response = 'id' in payload ? await putMonitoringTask(payload) : await postMonitoringTask(payload)
      if (!current()) return false
      if (response.code !== 200) throw new Error('Task save failed')
      Message.success(response.msg)
      close()
      emit('saved')
      return true
    } catch { if (current()) Message.error('任务保存失败，请重试'); return false }
    finally { saving.value = false; emit('saving-change', false, id) }
  }

  defineExpose<TaskEditorHandle>({ openCreate, openEdit, close })
</script>

<style scoped lang="less">
  .mango-monitoring-task-editor {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0 16px;
  }
  .mango-monitoring-task-editor__wide { grid-column: 1 / -1; }
  .mango-monitoring-task-editor__footer { display: flex; justify-content: flex-end; width: 100%; margin-top: var(--m-page-gap); }
</style>
