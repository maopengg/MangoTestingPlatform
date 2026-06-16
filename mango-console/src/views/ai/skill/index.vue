<template>
  <TableBody>
    <template #header>
      <TableHeader title="AI / 技能管理" @search="loadData" />
    </template>
    <template #default>
      <a-tabs>
        <template #extra>
          <div>
            <a-button size="small" type="primary" @click="openForm()">新增 Skill</a-button>
          </div>
        </template>
      </a-tabs>
      <a-table
        :bordered="false"
        :columns="columns"
        :data="rows"
        :loading="loading"
        :pagination="false"
        :row-key="'id'"
        :scroll="{ x: 1200 }"
      >
        <template #columns>
          <a-table-column v-for="item of columns" :key="item.key" v-bind="item">
            <template v-if="item.key === 'status'" #cell="{ record }">
              <a-switch
                :before-change="(newValue) => onModifyStatus(newValue, record.id)"
                :default-checked="record.status === 1"
              />
            </template>
            <template v-else-if="item.key === 'user'" #cell="{ record }">
              {{ record.user?.name || userName(record.user) }}
            </template>
            <template v-else-if="item.key === 'is_builtin'" #cell="{ record }">
              <a-switch
                :before-change="(newValue) => onModifyBuiltin(newValue, record)"
                :default-checked="!!record.is_builtin"
              />
            </template>
            <template v-else-if="item.key === 'skill_type'" #cell="{ record }">
              <a-tag :color="enumColor(record.skill_type)" size="small">
                {{ enumTitle(enumStore.ai_skill_type, record.skill_type) }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <MangoTableActions
                :actions="[
                  { label: '文件', onClick: () => openFile(record) },
                  { label: '编辑', onClick: () => openForm(record) },
                  { label: '删除', danger: true, onClick: () => deleteSkill(record) },
                ]"
              />
            </template>
          </a-table-column>
        </template>
      </a-table>
    </template>
    <template #footer>
      <TableFooter :pagination="pagination" />
    </template>
  </TableBody>
  <BaseSidePanel
    :visible="visible"
    title="Skill"
    :width="820"
    @update:visible="(val) => { visible = val }"
    @cancel="visible = false"
  >
    <template #default>
      <a-form :model="form" layout="vertical">
        <a-form-item label="名称" required><a-input v-model="form.name" /></a-form-item>
        <a-form-item label="负责人" required>
          <a-select
            v-model="form.user"
            :options="userOptions"
            :field-names="{ value: 'key', label: 'title' }"
            allow-search
            placeholder="请选择负责人"
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
          />
        </a-form-item>
        <a-form-item label="描述"><a-input v-model="form.description" /></a-form-item>
        <a-form-item label="内容">
          <a-textarea v-model="form.content" :auto-size="{ minRows: 16, maxRows: 28 }" />
        </a-form-item>
      </a-form>
    </template>
    <template #extra-buttons>
      <a-button type="primary" :loading="saving" @click="save">保存</a-button>
    </template>
  </BaseSidePanel>
  <BaseSidePanel
    :visible="fileVisible"
    :title="`${fileRecord?.name || '-'} / Skill 内容`"
    :width="900"
    @update:visible="(val) => { fileVisible = val }"
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
      <a-button type="primary" :loading="fileSaving" @click="saveFileContent">保存</a-button>
    </template>
  </BaseSidePanel>
</template>

<script setup lang="ts">
  import { Message, Modal } from '@arco-design/web-vue'
  import { onMounted, reactive, ref } from 'vue'
  import {
    deleteAiSkill,
    getAiSkill,
    postAiSkill,
    putAiSkill,
  } from '@/api/ai'
  import { getUserName } from '@/api/user/user'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import CodeEditor from '@/components/editors/CodeEditor.vue'
  import { usePagination } from '@/hooks/table'
  import { useEnum } from '@/store/modules/get-enum'

  const enumStore = useEnum()
  const rows = ref<any[]>([])
  const pagination = usePagination(loadData)
  const userOptions = ref<any[]>([])
  const loading = ref(false)
  const saving = ref(false)
  const visible = ref(false)
  const fileVisible = ref(false)
  const fileRecord = ref<any>(null)
  const fileContent = ref('')
  const fileSaving = ref(false)
  const form = reactive<any>({})
  const columns = [
    { title: 'ID', key: 'id', dataIndex: 'id', width: 80 },
    { title: '创建时间', key: 'create_time', dataIndex: 'create_time', width: 180 },
    { title: '更新时间', key: 'update_time', dataIndex: 'update_time', width: 180 },
    { title: '名称', key: 'name', dataIndex: 'name', ellipsis: true, tooltip: true },
    { title: '用途', key: 'skill_type', dataIndex: 'skill_type', width: 120 },
    { title: '描述', key: 'description', dataIndex: 'description', ellipsis: true, tooltip: true },
    { title: '负责人', key: 'user', dataIndex: 'user', width: 120 },
    { title: '是否内置', key: 'is_builtin', dataIndex: 'is_builtin', width: 110 },
    { title: '状态', key: 'status', dataIndex: 'status', width: 110 },
    { title: '操作', key: 'actions', dataIndex: 'actions', align: 'center', fixed: 'right', width: 170 },
  ]
  function userName(userId: number | string) {
    return userOptions.value.find((item) => item.key === userId)?.title || '-'
  }
  function enumTitle(options: any[] = [], value: any) {
    return options.find((item) => item.key === value)?.title || value || '-'
  }
  function enumColor(value: any) {
    return enumStore.colors?.[Number(value)]
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
  function openForm(record?: any) {
    Object.keys(form).forEach((key) => delete form[key])
    Object.assign(form, record ? {
      id: record.id,
      name: record.name,
      user: record.user?.id || record.user,
      is_builtin: !!record.is_builtin,
      skill_type: record.skill_type ?? 0,
      description: record.description,
      content: record.content,
    } : { name: '', user: undefined, is_builtin: false, skill_type: 0, description: '', content: '', status: 1 })
    visible.value = true
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
  async function save() {
    if (form.skill_type === undefined || form.skill_type === null || form.skill_type === '') {
      Message.error('请选择类型')
      return
    }
    saving.value = true
    try {
      await (form.id ? putAiSkill(form) : postAiSkill(form))
      Message.success('保存成功')
      visible.value = false
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
</script>

<style scoped>
  .mango-ai-skill-file-editor {
    height: calc(100vh - 146px);
    min-height: 420px;
  }

  .mango-ai-skill-file-editor :deep(.code-editor),
  .mango-ai-skill-file-editor :deep(.cm-editor),
  .mango-ai-skill-file-editor :deep(.cm-scroller) {
    height: 100%;
  }
</style>
