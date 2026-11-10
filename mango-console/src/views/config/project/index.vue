<template>
  <TableBody content-flush>
    <template #header>
      <TableHeader
        :show-filter="true"
        title="项目配置"
        @search="onSearch"
        @reset-search="onResetSearch"
      >
        <template #search-content>
          <a-form :model="{}" layout="inline" @keyup.enter="onSearch">
            <a-form-item v-for="item of conditionItems" :key="item.key" :label="item.label">
              <template v-if="item.type === 'input'">
                <a-input v-model="item.value" :placeholder="item.placeholder" @blur="onSearch" />
              </template>
              <template v-else-if="item.type === 'select'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="fieldNames"
                  :options="userOptions"
                  :loading="usersLoading"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="onSearch"
                />
              </template>
            </a-form-item>
          </a-form>
        </template>
      </TableHeader>
    </template>

    <template #default>

      <TableTabs>
        <template #extra>
          <a-space>
            <div>
              <a-button
                size="small"
                type="primary"
                :disabled="saving"
                @click="onAdd"
                data-testid="qa-views-config-project-button-新增"
                >新增</a-button
              >
            </div>
          </a-space>
        </template>
      </TableTabs>
      <a-table
        :scroll="{ x: 1100 }"
        :bordered="false"
        :columns="tableColumns"
        :data="rows"
        :loading="listLoading"
        :pagination="false"
        row-key="id"
      >
        <template #columns>
          <a-table-column
            v-for="item of tableColumns"
            :key="item.key"
            :align="item.align"
            :data-index="item.key"
            :fixed="item.fixed"
            :ellipsis="item.ellipsis"
            :tooltip="item.tooltip"
            :title="item.title"
            :width="item.width"
          >
            <template v-if="item.key === 'index'" #cell="{ record }">
              {{ record.id }}
            </template>
            <template v-else-if="item.key === 'status'" #cell="{ record }">
              <a-switch
                :before-change="(checked) => onModifyStatus(record, checked)"
                :loading="statusUpdatingIds.has(record.id)"
                :disabled="
                  deletingIds.has(record.id) || (saving && editor.recordId === record.id)
                "
                :model-value="record.status === 1"
              />
            </template>
            <template v-else-if="item.key === 'update_user'" #cell="{ record }">
              {{ record.update_user?.name || record.update_user?.username || '-' }}
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <MangoTableActions
                :actions="[
                  {
                    label: '编辑',
                    disabled: isMutating(record.id) || saving,
                    onClick: () => onUpdate(record),
                  },
                  { label: '通知组', onClick: () => clickNotice(record) },
                  {
                    label: '删除',
                    danger: true,
                    loading: deletingIds.has(record.id),
                    disabled:
                      statusUpdatingIds.has(record.id) ||
                      (saving && editor.recordId === record.id),
                    onClick: () => onDelete(record),
                  },
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
  <a-modal
    modal-class="mango-simple-form-modal"
    v-model:visible="editor.visible"
    :title="editorTitle"
    :width="560"
    :on-before-ok="save"
    :closable="!saving"
    :mask-closable="!saving"
    :esc-to-close="!saving"
    :cancel-button-props="{ disabled: saving }"
    unmount-on-close
    @cancel="closeEditor"
  >
    <a-form auto-label-width class="mango-simple-form" :model="draft" :disabled="saving" layout="horizontal">
      <a-form-item :label="projectNameField.label" class="mango-form-item__require mango-simple-form-item">
        <a-input v-model="draft.name" :placeholder="projectNameField.placeholder" />
      </a-form-item>
    </a-form>
  </a-modal>
</template>
<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import {
    computed,
    onMounted,
    onActivated,
    onBeforeUnmount,
    onDeactivated,
    reactive,
    ref,
    watch,
  } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import { Message, Modal } from '@arco-design/web-vue'
  import { usePagination } from '@/hooks/table'
  import { getFormItems } from '@/utils/datacleaning'
  import { useProject } from '@/store/modules/get-project'
  import useUserStore from '@/store/modules/user'
  import { usePageData } from '@/store/page-data'
  import { fieldNames } from '@/setting'
  import { getUserName } from '@/api/user/user'
  import {
    deleteUserDepartmentList,
    getUserDepartmentList,
    postUserDepartmentList,
    putUserDepartmentList,
  } from '@/api/system/project'
  import TableTabs from '@/components/table/TableTabs.vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import {
    createConditionItems,
    createProjectDraft,
    projectNameField,
    tableColumns,
  } from './config'
  import type { ProjectRecord, ProjectUserOption } from './types'
  const route = useRoute(),
    router = useRouter(),
    user = useUserStore(),
    project = useProject(),
    pageData = usePageData()
  const ownerPath = route.path
  const rows = ref<ProjectRecord[]>([]),
    listLoading = ref(false),
    listError = ref('')
  const userOptions = ref<ProjectUserOption[]>([]),
    usersLoading = ref(false),
    usersError = ref('')
  const conditionItems = createConditionItems()
  const pagination = usePagination(doRefresh, listLoading)
  const editor = reactive<{ visible: boolean; recordId: number | null }>({
    visible: false,
    recordId: null,
  })
  const editorTitle = computed(() => (editor.recordId === null ? '新增' : '编辑'))
  const draft = reactive(createProjectDraft()),
    saving = ref(false)
  const deletingIds = reactive(new Set<number>()),
    statusUpdatingIds = reactive(new Set<number>())
  let active = true,
    contextVersion = 0,
    listRequest = 0,
    userRequest = 0,
    editorSession = 0
  let confirmation: ReturnType<typeof Modal.confirm> | null = null
  const isActive = () => active && route.path === ownerPath
  const current = (version: number) => isActive() && version === contextVersion
  const isMutating = (id: number) =>
    deletingIds.has(id) || statusUpdatingIds.has(id) || (saving.value && editor.recordId === id)
  function resetContext() {
    ++contextVersion
    ++listRequest
    ++userRequest
    rows.value = []
    userOptions.value = []
    listLoading.value = false
    usersLoading.value = false
    listError.value = ''
    usersError.value = ''
    closeEditor()
    confirmation?.close()
    confirmation = null
  }
  function resume() {
    void doRefresh()
    void loadUsers()
  }
  function onSearch() {
    pagination.page = 1
    return doRefresh()
  }
  function onResetSearch() {
    for (const item of conditionItems) item.value = item.multiple ? [] : ''
    return onSearch()
  }
  function requestParams() {
    const values = getFormItems(conditionItems)
    const params: Record<string, unknown> = Object.fromEntries(
      Object.entries(values).filter(
        ([, value]) =>
          value !== '' &&
          value !== null &&
          value !== undefined &&
          !(Array.isArray(value) && !value.length)
      )
    )
    return { ...params, page: pagination.page, pageSize: pagination.pageSize }
  }
  async function doRefresh() {
    if (!isActive()) return
    const request = ++listRequest,
      version = contextVersion,
      params = requestParams()
    listLoading.value = true
    listError.value = ''
    try {
      const response = await getUserDepartmentList(params)
      if (request !== listRequest || !current(version)) return
      rows.value = response.data || []
      pagination.setTotalSize(response.totalSize ?? 0)
    } catch (loadFailure0) {
      if (request === listRequest && current(version)) (reportLoadError(loadFailure0, "项目加载失败，请重试", false), listError.value = '项目加载失败，请重试')
    } finally {
      if (request === listRequest) listLoading.value = false
    }
  }
  async function loadUsers() {
    if (!isActive()) return
    const request = ++userRequest,
      version = contextVersion
    usersLoading.value = true
    usersError.value = ''
    try {
      const response = await getUserName()
      if (request === userRequest && current(version)) userOptions.value = response.data || []
    } catch (loadFailure1) {
      if (request === userRequest && current(version))
        void (reportLoadError(loadFailure1, "更新人选项加载失败，请重试", false), usersError.value = '更新人选项加载失败，请重试')
    } finally {
      if (request === userRequest) usersLoading.value = false
    }
  }
  function closeEditor() {
    ++editorSession
    editor.visible = false
  }
  function onAdd() {
    if (!isActive() || saving.value) return
    ++editorSession
    editor.recordId = null
    Object.assign(draft, createProjectDraft())
    editor.visible = true
  }
  function onUpdate(record: ProjectRecord) {
    if (!isActive() || saving.value || isMutating(record.id)) return
    ++editorSession
    editor.recordId = record.id
    Object.assign(draft, createProjectDraft(record))
    editor.visible = true
  }
  async function refreshCatalog(includeProducts = true) {
    const requests = [project.getProject()]
    if (includeProducts) requests.push(project.projectProductName())
    await Promise.allSettled(requests)
  }
  async function save(): Promise<boolean> {
    if (!isActive() || !editor.visible || saving.value) return false
    if (!draft.name) {
      Message.error(projectNameField.placeholder)
      return false
    }
    const version = contextVersion,
      session = editorSession,
      id = editor.recordId,
      payload = id === null ? { name: draft.name, status: 1 } : { id, name: draft.name }
    saving.value = true
    try {
      const response = await (id === null
        ? postUserDepartmentList(payload)
        : putUserDepartmentList(payload))
      project.invalidateProjectOptionsCache()
      if (!current(version) || session !== editorSession) return false
      Message.success(response.msg)
      closeEditor()
      await Promise.all([doRefresh(), refreshCatalog()])
      return true
    } catch {
      return false
    } finally {
      saving.value = false
    }
  }
  function onDelete(record: ProjectRecord) {
    if (!isActive() || confirmation || isMutating(record.id)) return
    const id = record.id,
      version = contextVersion
    const dialog = Modal.confirm({
      title: '提示',
      content: '是否要删除此项目？',
      cancelText: '取消',
      okText: '删除',
      okButtonProps: { status: 'danger' },
      async onBeforeOk() {
        if (!current(version) || isMutating(id)) return false
        deletingIds.add(id)
        try {
          const response = await deleteUserDepartmentList(id)
          project.invalidateProjectOptionsCache()
          if (current(version)) {
            Message.success(response.msg)
            if (rows.value.length === 1 && rows.value[0].id === id && pagination.page > 1)
              pagination.page--
            await Promise.all([doRefresh(), refreshCatalog()])
          }
          return true
        } catch {
          return false
        } finally {
          deletingIds.delete(id)
        }
      },
      onClose() {
        if (confirmation === dialog) confirmation = null
      },
    })
    confirmation = dialog
  }
  async function onModifyStatus(record: ProjectRecord, checked: boolean): Promise<boolean> {
    if (!isActive() || isMutating(record.id)) return false
    const id = record.id,
      name = record.name,
      version = contextVersion,
      status = checked ? 1 : 0
    statusUpdatingIds.add(id)
    ++listRequest
    listLoading.value = false
    try {
      const response = await putUserDepartmentList({ id, name, status })
      if (response.code !== 200) return false
      project.invalidateProjectOptionsCache()
      if (!current(version)) return false
      const target = rows.value.find((item) => item.id === id)
      if (target) target.status = status
      ++listRequest
      listLoading.value = false
      Message.success(response.msg)
      await Promise.all([doRefresh(), refreshCatalog(false)])
      return true
    } catch {
      return false
    } finally {
      statusUpdatingIds.delete(id)
    }
  }
  function clickNotice(record: ProjectRecord) {
    if (!isActive()) return
    pageData.setRecord({ id: record.id, name: record.name })
    void router.push({
      path: '/config/project/notice',
      query: { id: record.id, name: record.name },
    })
  }
  function deactivate() {
    active = false
    resetContext()
  }
  onMounted(resume)
  onDeactivated(deactivate)
  onBeforeUnmount(deactivate)
  onActivated(() => {
    if (!active) {
      active = true
      if (isActive()) resume()
    }
  })
  watch(
    () => [route.path, user.userId, user.roleId, user.token],
    () => {
      resetContext()
      if (isActive()) resume()
    },
    { flush: 'sync' }
  )
</script>
