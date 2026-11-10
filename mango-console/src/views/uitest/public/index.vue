<template>
  <TableBody plain class="mango-detail-workbench-page">
    <template #header>
      <TableHeader title="全局变量" />
    </template>

    <template #default>
      <ProjectProductNavigationWorkbench
        contained-body
        :model-value="projectProduct"
        :reset-key="sidebarResetKey"
        @filter-change="onNavigationFilterChange"
        @search="onSearchRefresh"
        @reset-search="onResetSearch"
      >
        <template #search>
          <a-form :model="{}" layout="inline" @keyup.enter="onSearchRefresh">
            <a-form-item v-for="item of headerConditionItems" :key="item.key" :label="item.label">
              <template v-if="item.type === 'input'">
                <a-input
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  allow-clear
                  @blur="onSearchRefresh"
                  @clear="onSearchRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'type'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="fieldNames"
                  :options="typeOptions"
                  :loading="enumsLoading"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="onSearchRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select'">
                <a-select
                  v-model="item.value"
                  :field-names="fieldNames"
                  :options="item.key === 'test_envs' ? environmentOptions : userOptions"
                  :loading="item.key === 'test_envs' ? enumsLoading : usersLoading"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  :multiple="item.multiple || item.key === 'test_envs'"
                  :max-tag-count="item.multiple || item.key === 'test_envs' ? 1 : undefined"
                  value-key="key"
                  @change="onSearchRefresh"
                />
              </template>
            </a-form-item>
          </a-form>
        </template>
        <template #toolbar>
          <a-space wrap>
            <a-button size="small" type="primary" :disabled="editingBusy" @click="onAdd"
              >新增</a-button
            >
            
            <a-alert v-if="actionError" type="error">{{ actionError }}</a-alert>
          </a-space>
        </template>
        <a-table
          class="mango-native-scroll-table"
          :scroll="{ x: TABLE_SCROLL_X, y: '100%' }"
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
              :ellipsis="item.ellipsis"
              :fixed="item.fixed"
              :title="item.title"
              :tooltip="item.tooltip"
              :width="item.width"
            >
              <template v-if="item.key === 'index'" #cell="{ record }">
                {{ record.id }}
              </template>
              <template v-else-if="item.key === 'test_env'" #cell="{ record }">
                <a-tag v-if="record.test_envs.length === 0" color="gray" size="small"
                  >环境通用</a-tag
                >
                <a-space v-else wrap :size="4">
                  <a-tag
                    v-for="env in record.test_envs"
                    :key="env"
                    :color="enumStore.colors[env]"
                    size="small"
                  >
                    {{
                      environments.find((item) => String(item.key) === String(env))?.title || '-'
                    }}
                  </a-tag>
                </a-space>
              </template>
              <template v-else-if="item.key === 'type'" #cell="{ record }">
                <a-tag :color="enumStore.colors[record.type]" size="small">
                  {{
                    typeOptions.find((option) => String(option.key) === String(record.type))
                      ?.title || '-'
                  }}
                </a-tag>
              </template>
              <template v-else-if="item.key === 'datasource_alias'" #cell="{ record }">
                <a-tag v-if="record.datasource_alias" color="blue" size="small">
                  {{ record.datasource_alias.name }}
                </a-tag>
                <span v-else>-</span>
              </template>
              <template v-else-if="item.key === 'status'" #cell="{ record }">
                <a-switch
                  :beforeChange="(newValue) => onModifyStatus(newValue, record.id)"
                  :model-value="record.status === 1"
                  :loading="statusIds.has(String(record.id))"
                  :disabled="deletingIds.has(String(record.id)) || editingBusy"
                />
              </template>
              <template v-else-if="item.key === 'project_product'" #cell="{ record }">
                {{ formatProjectProductPath(record.project_product) }}
              </template>
              <template v-else-if="item.key === 'update_user'" #cell="{ record }">
                {{ record.update_user?.name || record.update_user?.username || '-' }}
              </template>
              <template v-else-if="item.key === 'actions'" #cell="{ record }">
                <MangoTableActions
                  :actions="[
                    {
                      label: '编辑',
                      disabled: editingBusy || busy(record.id),
                      onClick: () => onUpdate(record),
                    },
                    {
                      label: '删除',
                      danger: true,
                      loading: deletingIds.has(String(record.id)),
                      disabled: editingBusy || statusIds.has(String(record.id)),
                      onClick: () => onDelete(record),
                    },
                  ]"
                />
              </template>
            </a-table-column>
          </template>
        </a-table>
        <template #footer>
          <TableFooter :pagination="pagination" />
        </template>
      </ProjectProductNavigationWorkbench>
    </template>
  </TableBody>
  <PublicVariableEditor
    ref="editorRef"
    :type-options="typeOptions"
    :environments="environments"
    :options-loading="enumsLoading"
    :options-error="enumsError"
    @busy-change="editingBusy = $event"
    @saved="onSaved"
    @retry-options="loadEnums"
  />
</template>
<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { computed, onMounted, ref, watch } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import { usePagination } from '@/hooks/table'
  import { useLiveWorkbenchScope } from '@/hooks/use-live-workbench-scope'
  import { formatProjectProductPath } from '@/utils/business-format'
  import { getFormItems } from '@/utils/datacleaning'
  import { fieldNames } from '@/setting'
  import { useEnum } from '@/store/modules/get-enum'
  import useUserStore from '@/store/modules/user'
  import usePermissionStore from '@/store/modules/permission'
  import { getUserName } from '@/api/user/user'
  import { getUiPublic, deleteUiPublic, putUiPublicPutStatus } from '@/api/uitest/public'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import PublicVariableEditor from './components/PublicVariableEditor.vue'
  import { createConditionItems, tableColumns, TABLE_SCROLL_X } from './config'
  import {
    COMMON_ENV_VALUE,
    publicId,
    publicOptionId,
    publicQuery,
    publicResponse,
    readPublicList,
    readPublicOptions,
    type PublicId,
    type PublicRow,
    type PublicOption,
  } from './public-records'
  const enumStore = useEnum(),
    conditionItems = createConditionItems()
  const projectProductCondition = computed(() =>
    conditionItems.find((item) => item.key === 'project_product')
  )
  const projectProduct = computed(() => publicOptionId(projectProductCondition.value?.value))
  const headerConditionItems = computed(() =>
    conditionItems.filter((item) => item.key !== 'project_product')
  )
  const rows = ref<PublicRow[]>([]),
    listLoading = ref(false),
    listError = ref('')
  const userOptions = ref<PublicOption[]>([]),
    usersLoading = ref(false),
    usersError = ref('')
  const typeOptions = ref<PublicOption[]>([]),
    environments = ref<PublicOption[]>([]),
    enumsLoading = ref(false),
    enumsError = ref('')
  const environmentOptions = computed(() => [
    { key: COMMON_ENV_VALUE, title: '环境通用' },
    ...environments.value,
  ])
  const statusIds = ref(new Set<string>()),
    deletingIds = ref(new Set<string>()),
    actionError = ref(''),
    editingBusy = ref(false),
    sidebarResetKey = ref(0)
  const editorRef = ref<{
    open: (row?: PublicRow | null, product?: PublicId | null) => void
    close: () => void
  } | null>(null)
  const pagination = usePagination(doRefresh, listLoading)
  let listSequence = 0,
    usersSequence = 0,
    enumsSequence = 0,
    confirmationVersion = 0
  let confirmation: ReturnType<typeof Modal.confirm> | null = null
  function closeConfirmation() {
    confirmationVersion++
    confirmation?.close()
    confirmation = null
  }
  function invalidateReads() {
    ++listSequence
    ++usersSequence
    ++enumsSequence
    listLoading.value = false
    usersLoading.value = false
    enumsLoading.value = false
    rows.value = []
    userOptions.value = []
    typeOptions.value = []
    environments.value = []
    pagination.setTotalSize(0)
    listError.value = ''
    usersError.value = ''
    enumsError.value = ''
    actionError.value = ''
    closeConfirmation()
    editorRef.value?.close()
  }
  const user = useUserStore(),
    permission = usePermissionStore()
  watch(
    () => JSON.stringify([user.userId, user.roleId, user.token, permission.permissionKeys]),
    () => {
      resetConditions()
    },
    { flush: 'sync' }
  )
  const scope = useLiveWorkbenchScope(() => null, {
    invalidate: invalidateReads,
    resume: initialize,
  })
  function busy(id: PublicId) {
    return statusIds.value.has(String(id)) || deletingIds.value.has(String(id))
  }
  async function doRefresh() {
    if (!scope.available()) return
    const valid = scope.capture(),
      sequence = ++listSequence,
      current = () => valid() && sequence === listSequence
    listLoading.value = true
    listError.value = ''
    try {
      const result = readPublicList(
        await getUiPublic(
          publicQuery(getFormItems(conditionItems), pagination.page, pagination.pageSize)
        )
      )
      if (!current()) return
      rows.value = result.rows
      pagination.setTotalSize(result.total)
    } catch (loadFailure0) {
      if (current()) (reportLoadError(loadFailure0, "变量列表加载失败，请重试", false), listError.value = '变量列表加载失败，请重试')
    } finally {
      if (current()) listLoading.value = false
    }
  }
  async function loadUsers() {
    if (!scope.available()) return
    const valid = scope.capture(),
      sequence = ++usersSequence,
      current = () => valid() && sequence === usersSequence
    usersLoading.value = true
    usersError.value = ''
    try {
      const result = readPublicOptions(publicResponse(await getUserName()))
      if (current()) userOptions.value = result
    } catch (loadFailure1) {
      if (current()) (reportLoadError(loadFailure1, "更新人选项加载失败", false), usersError.value = '更新人选项加载失败')
    } finally {
      if (current()) usersLoading.value = false
    }
  }
  async function loadEnums() {
    if (!scope.available()) return
    const valid = scope.capture(),
      sequence = ++enumsSequence,
      current = () => valid() && sequence === enumsSequence
    enumsLoading.value = true
    enumsError.value = ''
    try {
      await enumStore.getEnum()
      const types = readPublicOptions(enumStore.ui_public),
        envs = readPublicOptions(enumStore.environment_type)
      if (!types.length || !envs.length) throw Error('枚举未就绪')
      if (current()) {
        typeOptions.value = types
        environments.value = envs
      }
    } catch (loadFailure2) {
      if (current()) (reportLoadError(loadFailure2, "变量类型与环境选项加载失败", false), enumsError.value = '变量类型与环境选项加载失败')
    } finally {
      if (current()) enumsLoading.value = false
    }
  }
  function initialize() {
    void doRefresh()
    void loadUsers()
    void loadEnums()
  }
  function resetConditions() {
    conditionItems.forEach((item) => {
      item.value = item.multiple || item.key === 'test_envs' ? [] : ''
    })
    sidebarResetKey.value++
    pagination.page = 1
  }
  function onSearchRefresh() {
    closeConfirmation()
    editorRef.value?.close()
    pagination.page = 1
    void doRefresh()
  }
  function onNavigationFilterChange({ projectProduct: product }: { projectProduct: unknown }) {
    if (projectProductCondition.value) projectProductCondition.value.value = publicOptionId(product)
    onSearchRefresh()
  }
  function onResetSearch() {
    resetConditions()
    onSearchRefresh()
  }
  function onAdd() {
    if (!editingBusy.value && scope.available()) editorRef.value?.open(null, projectProduct.value)
  }
  function onUpdate(record: PublicRow) {
    if (!editingBusy.value && !busy(record.id) && scope.available()) editorRef.value?.open(record)
  }
  function onSaved() {
    ++listSequence
    void doRefresh()
  }
  function onDelete(record: PublicRow) {
    const id = publicId(record.id)
    if (id === null || !scope.available() || editingBusy.value || busy(id) || confirmation) return
    const key = String(id),
      valid = scope.capture(),
      version = ++confirmationVersion
    const current = () => valid() && version === confirmationVersion
    let accepted = false
    const dialog = Modal.confirm({
      title: '删除全局变量',
      content: '是否要删除此参数？',
      cancelText: '取消',
      okText: '删除',
      okButtonProps: { status: 'danger' },
      async onBeforeOk() {
        if (accepted) return true
        if (!current() || editingBusy.value || busy(id)) return false
        deletingIds.value.add(key)
        ++listSequence
        listLoading.value = false
        actionError.value = ''
        try {
          publicResponse(await deleteUiPublic(id))
          accepted = true
          if (current()) {
            rows.value = rows.value.filter((row) => String(row.id) !== key)
            if (!rows.value.length && pagination.page > 1) pagination.page--
            Message.success('删除成功')
            await doRefresh()
          }
          return true
        } catch {
          if (current()) actionError.value = '删除失败，请重试'
          return false
        } finally {
          deletingIds.value.delete(key)
        }
      },
      onClose() {
        if (confirmation === dialog) confirmation = null
      },
    })
    confirmation = dialog
  }
  async function onModifyStatus(value: boolean, id: PublicId): Promise<boolean> {
    if (!scope.available() || editingBusy.value || busy(id)) return false
    const key = String(id),
      valid = scope.capture(),
      status = value ? 1 : 0
    statusIds.value.add(key)
    ++listSequence
    listLoading.value = false
    actionError.value = ''
    try {
      publicResponse(await putUiPublicPutStatus(id, status))
      if (!valid()) return false
      const row = rows.value.find((row) => String(row.id) === key)
      if (row) row.status = status
      await doRefresh()
      return true
    } catch {
      if (valid()) actionError.value = '状态更新失败，请重试'
      return false
    } finally {
      statusIds.value.delete(key)
    }
  }
  onMounted(initialize)
</script>
