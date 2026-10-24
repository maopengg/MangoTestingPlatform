<template>
  <TableBody>
    <template #header>
      <TableHeader title="AI / 技能管理" @search="loadData" />
    </template>
    <template #default>
      <TableTabs>
        <template #extra>
          <a-space>
            <a-button v-permission="'ai.task:create'"
              size="small"
              @click="openAiAssistant"
              data-testid="qa-views-ai-skill-button-打开-ai-助手"
            >
              <template #icon><icon-robot /></template>
              打开 AI 助手
            </a-button>
            <a-button v-permission="'ai.skill:create'"
              size="small"
              type="primary"
              @click="openCreateForm"
              data-testid="qa-views-ai-skill-button-上传-skill"
              >上传 Skill</a-button
            >
          </a-space>
        </template>
      </TableTabs>
      <a-spin :loading="loading" class="mango-ai-skill-spin">
        <div v-if="rows.length" class="mango-ai-skill-grid">
          <section
            v-for="record in rows"
            :key="record.id"
            class="mango-section-card mango-ai-skill-card"
          >
            <div class="mango-ai-skill-card__header">
              <div class="mango-ai-skill-card__title">
                <span>{{ record.name || '-' }}</span>
              </div>
              <a-tag :color="enumColor(enumStore.ai_skill_type, record.skill_type)" size="small">
                {{ enumTitle(enumStore.ai_skill_type, record.skill_type) }}
              </a-tag>
            </div>
            <div class="mango-ai-skill-card__info">
              <span>负责人：{{ record.user?.name || userName(record.user) }}</span>
              <span
                >更新人：{{ record.update_user?.name || record.update_user?.username || '-' }}</span
              >
              <span>内置：{{ record.is_builtin ? '是' : '否' }}</span>
              <span>描述：{{ shortDescription(record.description) }}</span>
            </div>
            <div class="mango-ai-skill-card__switches">
              <label>
                <span>状态</span>
                <a-switch v-permission="'ai.skill:status'"
                  size="small"
                  :before-change="(newValue) => onModifyStatus(newValue, record.id)"
                  :default-checked="record.status === 1"
                />
              </label>
              <label>
                <span>内置</span>
                <a-switch v-permission="'ai.skill:status'"
                  size="small"
                  :before-change="(newValue) => onModifyBuiltin(newValue, record)"
                  :default-checked="!!record.is_builtin"
                />
              </label>
            </div>
            <div class="mango-ai-skill-card__actions">
              <a-button v-permission="'ai.skill:detail'"
                size="mini"
                @click="openFile(record)"
                data-testid="qa-views-ai-skill-button-文件"
                >文件</a-button
              >
              <a-button v-permission="'ai.skill:download'"
                size="mini"
                :loading="downloadLoadingId === record.id"
                @click="downloadSkill(record)"
                data-testid="qa-views-ai-skill-button-下载"
                >下载</a-button
              >
              <a-button v-permission="'ai.skill:edit'"
                size="mini"
                @click="openEditForm(record)"
                data-testid="qa-views-ai-skill-button-编辑"
                >编辑</a-button
              >
              <a-button v-permission="'ai.skill:delete'"
                size="mini"
                status="danger"
                @click="deleteSkill(record)"
                data-testid="qa-views-ai-skill-button-删除"
                >删除</a-button
              >
            </div>
          </section>
        </div>
        <div v-else class="mango-empty-state mango-ai-skill-empty">暂无 Skill</div>
      </a-spin>
    </template>
    <template #footer>
      <TableFooter :pagination="pagination" />
    </template>
  </TableBody>
  <a-modal
    :visible="visible"
    :title="form.id ? '编辑 Skill' : '上传 Skill'"
    :width="skillFormWidth"
    @update:visible="
      (val) => {
        visible = val
      }
    "
    @cancel="visible = false"
    @ok="save"
  >
    <a-form :model="form" layout="vertical">
      <a-form-item v-if="!form.id" label="Skill 文件" required>
        <a-upload
          v-model:file-list="uploadFileList"
          :auto-upload="false"
          :limit="1"
          accept=".md,.txt"
          @change="onUploadFileChange"
          @before-remove="onRemoveUploadFile"
        />
      </a-form-item>
      <a-form-item label="名称" required><a-input v-model="form.name" /></a-form-item>
      <a-form-item label="负责人" required>
        <a-select
          v-model="form.user"
          :options="userOptions"
          :field-names="{ value: 'key', label: 'title' }"
          allow-search
          placeholder="请选择负责人"
          data-testid="qa-views-ai-skill-select-请选择负责人"
        />
      </a-form-item>
      <a-form-item label="是否内置">
        <a-switch v-model="form.is_builtin" />
      </a-form-item>
      <a-form-item label="类型" required>
        <a-select
          v-model="form.skill_type"
          :options="enumStore.ai_skill_type"
          :field-names="{ value: 'key', label: 'title' }"
          placeholder="请选择类型"
          data-testid="qa-views-ai-skill-select-请选择类型"
        />
      </a-form-item>
      <a-form-item label="描述"><a-input v-model="form.description" /></a-form-item>
    </a-form>
    <template #footer>
      <a-button @click="visible = false" data-testid="qa-views-ai-skill-button-取消">取消</a-button>
      <a-button v-permission="['ai.skill:create', 'ai.skill:edit']"
        type="primary"
        :loading="saving"
        @click="save"
        data-testid="qa-views-ai-skill-button-保存"
        >保存</a-button
      >
    </template>
  </a-modal>
  <BaseSidePanel
    :visible="fileVisible"
    :title="`${fileRecord?.name || '-'} / Skill 内容`"
    :width="skillFilePanelWidth"
    @update:visible="
      (val) => {
        fileVisible = val
      }
    "
    @cancel="fileVisible = false"
  >
    <template #default>
      <div class="mango-ai-skill-file-editor">
        <CodeEditor
          v-model="fileContent"
          placeholder="请输入 Skill 内容"
          :code-style="{ height: '100%' }"
        />
      </div>
    </template>
    <template #extra-buttons>
      <a-button v-permission="['ai.skill:create', 'ai.skill:edit']"
        type="primary"
        :loading="fileSaving"
        @click="saveFileContent"
        data-testid="qa-views-ai-skill-button-保存-2"
        >保存</a-button
      >
    </template>
  </BaseSidePanel>
</template>

<script setup lang="ts">
  import { Message, Modal } from '@arco-design/web-vue'
  import { onBeforeUnmount, onMounted, reactive, ref } from 'vue'
  import { deleteAiSkill, downloadAiSkill, getAiSkill, postAiSkill, putAiSkill } from '@/api/ai'
  import { getUserName } from '@/api/user/user'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import CodeEditor from '@/components/editors/CodeEditor.vue'
  import TableTabs from '@/components/table/TableTabs.vue'
  import { usePagination } from '@/hooks/table'
  import { useAiAssistantPanel } from '@/hooks/use-ai-assistant-panel'
  import { useEnum } from '@/store/modules/get-enum'
  import { getEnumTagColor } from '@/utils/business-format'
  import { skillDescriptionMaxLength, skillFilePanelWidth, skillFormWidth } from './config'

  const enumStore = useEnum()
  const { closeAiAssistant, openAiAssistant } = useAiAssistantPanel()
  const rows = ref<any[]>([])
  const pagination = usePagination(loadData, () => loading)
  const userOptions = ref<any[]>([])
  const loading = ref(false)
  const saving = ref(false)
  const visible = ref(false)
  const fileVisible = ref(false)
  const fileRecord = ref<any>(null)
  const fileContent = ref('')
  const fileSaving = ref(false)
  const downloadLoadingId = ref<number | null>(null)
  const uploadFile = ref<File | null>(null)
  const uploadFileList = ref<any[]>([])
  const form = reactive<any>({})

  function userName(userId: number | string) {
    return userOptions.value.find((item) => item.key === userId)?.title || '-'
  }
  function enumTitle(options: any[] = [], value: any) {
    return options.find((item) => item.key === value)?.title || value || '-'
  }
  function enumColor(options: any[], value: any) {
    return getEnumTagColor(options, value, enumStore.colors)
  }
  function shortDescription(value: any) {
    const text = String(value || '暂无描述')
    return text.length > skillDescriptionMaxLength
      ? `${text.slice(0, skillDescriptionMaxLength)}...`
      : text
  }
  async function loadData() {
    loading.value = true
    try {
      const res = await getAiSkill({ page: pagination.page, pageSize: pagination.pageSize })
      rows.value = res.data || []
      pagination.setTotalSize((res as any).totalSize || rows.value.length)
    } finally {
      loading.value = false
    }
  }
  function resetUploadFile() {
    uploadFile.value = null
    uploadFileList.value = []
  }
  function openCreateForm() {
    Object.keys(form).forEach((key) => delete form[key])
    resetUploadFile()
    Object.assign(form, {
      name: '',
      user: undefined,
      is_builtin: false,
      skill_type: 0,
      description: '',
      status: 1,
    })
    visible.value = true
  }
  function openEditForm(record: any) {
    Object.keys(form).forEach((key) => delete form[key])
    resetUploadFile()
    Object.assign(form, {
      id: record.id,
      name: record.name,
      user: record.user?.id || record.user,
      is_builtin: !!record.is_builtin,
      skill_type: record.skill_type ?? 0,
      description: record.description,
      status: record.status,
    })
    visible.value = true
  }
  function onUploadFileChange(fileList: any[], fileItem: any) {
    uploadFileList.value = fileList.slice(-1)
    uploadFile.value = fileItem?.file || uploadFileList.value[0]?.file || null
    if (!form.name && uploadFile.value?.name) {
      form.name = uploadFile.value.name.replace(/\.[^.]+$/, '')
    }
  }
  function onRemoveUploadFile() {
    resetUploadFile()
    return true
  }
  function openFile(record: any) {
    fileRecord.value = record
    fileContent.value = record.content || ''
    fileVisible.value = true
  }
  async function saveFileContent() {
    if (!fileRecord.value?.id) return
    fileSaving.value = true
    try {
      await putAiSkill({
        id: fileRecord.value.id,
        name: fileRecord.value.name,
        user: fileRecord.value.user?.id || fileRecord.value.user,
        description: fileRecord.value.description,
        status: fileRecord.value.status,
        is_builtin: !!fileRecord.value.is_builtin,
        skill_type: fileRecord.value.skill_type ?? 0,
        content: fileContent.value,
      })
      Message.success('保存成功')
      fileRecord.value.content = fileContent.value
      await loadData()
    } finally {
      fileSaving.value = false
    }
  }
  function deleteSkill(record: any) {
    Modal.warning({
      title: '删除 Skill',
      content: `确认删除 Skill「${record.name || record.id}」吗？`,
      hideCancel: false,
      onOk: async () => {
        await deleteAiSkill(record.id)
        Message.success('删除成功')
        await loadData()
      },
    })
  }
  async function downloadSkill(record: any) {
    downloadLoadingId.value = record.id
    try {
      const res = await downloadAiSkill(record.id)
      const blob = new Blob([res.data], { type: 'text/markdown;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const aLink = document.createElement('a')
      // Skill 名称用于下载文件名，内容仍以数据库 content 为准。
      aLink.download = `${record.name || record.id}.md`
      aLink.href = url
      document.body.appendChild(aLink)
      aLink.click()
      document.body.removeChild(aLink)
      URL.revokeObjectURL(url)
      Message.success('开始下载 Skill')
    } finally {
      downloadLoadingId.value = null
    }
  }
  async function save() {
    if (!String(form.name || '').trim()) {
      Message.error('请输入名称')
      return
    }
    if (!form.user && form.user !== 0) {
      Message.error('请选择负责人')
      return
    }
    if (form.skill_type === undefined || form.skill_type === null || form.skill_type === '') {
      Message.error('请选择类型')
      return
    }
    if (!form.id && !uploadFile.value) {
      Message.error('请选择 Skill 文件')
      return
    }
    saving.value = true
    try {
      if (form.id) {
        await putAiSkill(form)
      } else {
        const formData = new FormData()
        // 新增 Skill 只上传文件，后端会把文件文本写入 content。
        formData.append('skill_file', uploadFile.value as File)
        formData.append('name', String(form.name).trim())
        formData.append('user', String(form.user))
        formData.append('is_builtin', String(!!form.is_builtin))
        formData.append('skill_type', String(form.skill_type))
        formData.append('description', form.description || '')
        formData.append('status', String(form.status || 1))
        await postAiSkill(formData)
      }
      Message.success('保存成功')
      visible.value = false
      resetUploadFile()
      await loadData()
    } finally {
      saving.value = false
    }
  }
  async function loadUsers() {
    userOptions.value = (await getUserName()).data || []
  }
  async function onModifyStatus(newValue: any, id: number) {
    return new Promise<any>((resolve, reject) => {
      setTimeout(async () => {
        try {
          let value = false
          await putAiSkill({ id, status: newValue ? 1 : 2 })
            .then((res: any) => {
              Message.success(res.msg || '操作成功')
              value = res.code === 200
            })
            .catch(reject)
          resolve(value)
        } catch (error) {
          reject(error)
        }
      }, 300)
    })
  }
  async function onModifyBuiltin(newValue: any, record: any) {
    return new Promise<any>((resolve, reject) => {
      setTimeout(async () => {
        try {
          let value = false
          await putAiSkill({ id: record.id, is_builtin: !!newValue })
            .then((res: any) => {
              Message.success(res.msg || '操作成功')
              value = res.code === 200
            })
            .catch(reject)
          if (value) {
            await loadData()
          }
          resolve(value)
        } catch (error) {
          reject(error)
        }
      }, 300)
    })
  }
  onMounted(async () => {
    await enumStore.getEnum()
    await loadUsers()
    loadData()
  })
  onBeforeUnmount(closeAiAssistant)
</script>

<style scoped>
  .mango-ai-skill-spin {
    display: block;
    min-height: 240px;
  }

  .mango-ai-skill-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: var(--m-page-gap);
    padding: 2px 0 4px;
  }

  .mango-ai-skill-card {
    display: flex;
    min-height: 150px;
    flex-direction: column;
    gap: 8px;
    padding: 10px;
  }

  .mango-ai-skill-card__header,
  .mango-ai-skill-card__actions {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 6px;
  }

  .mango-ai-skill-card__title {
    min-width: 0;
    color: var(--m-text);
    font-size: 13px;
    font-weight: 600;
  }

  .mango-ai-skill-card__title span {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-ai-skill-card__info {
    display: grid;
    gap: 4px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 1.45;
  }

  .mango-ai-skill-card__info span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-ai-skill-card__switches {
    display: flex;
    padding-top: 6px;
    border-top: 1px solid var(--m-border);
  }

  .mango-ai-skill-card__switches label {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    color: var(--m-text-2);
    font-size: 12px;
  }

  .mango-ai-skill-card__actions {
    margin-top: auto;
    flex-wrap: wrap;
    justify-content: flex-start;
  }

  .mango-ai-skill-empty {
    display: flex;
    min-height: 220px;
    align-items: center;
    justify-content: center;
    color: var(--m-muted);
    border: 1px dashed var(--m-border);
    border-radius: var(--m-radius-lg);
    background: var(--m-surface);
  }

  .mango-ai-skill-file-editor {
    height: 100%;
    min-height: 0;
  }

  .mango-ai-skill-file-editor :deep(.code-editor),
  .mango-ai-skill-file-editor :deep(.cm-editor),
  .mango-ai-skill-file-editor :deep(.cm-scroller) {
    height: 100%;
  }
</style>
