<template>
  <TableBody plain class="mango-detail-workbench-page">
    <template #header>
      <TableHeader title="配置文件" />
    </template>
    <template #default>
      <ProjectProductNavigationWorkbench
        ref="navigationCreateRef"
        contained-body
        :model-value="query.project_product"
        :reset-key="sidebarResetKey"
        @filter-change="onSidebarFilterChange"
        @search="onSearchRefresh"
        @reset-search="onReset"
      >
        <template #search>
          <a-form layout="inline" :model="query" @keyup.enter="onSearchRefresh">
            <a-form-item label="配置名称">
                  <a-input
                    v-model="query.name"
                    allow-clear
                    placeholder="请输入配置名称"
                    @blur="onSearchRefresh"
                    @clear="onSearchRefresh"
                    data-testid="qa-views-gray-config-file-input-请输入配置名称"
                  />
            </a-form-item>
            <a-form-item label="状态">
                  <a-select
                    v-model="query.status"
                    multiple
                    :max-tag-count="1"
                    :options="enableStatusOptions"
                    allow-clear
                    placeholder="请选择状态"
                    @change="onSearchRefresh"
                    data-testid="qa-views-gray-config-file-select-请选择状态"
                  />
            </a-form-item>
          </a-form>
        </template>
        <template #toolbar>
      <div class="mango-gray-toolbar">
            <a-button
              size="small"
              type="primary"
              @click="onAdd"
              data-testid="qa-views-gray-config-file-button-新增配置文件"
              >新增配置文件</a-button
            >
      </div>
        </template>
      <a-table
        class="mango-native-scroll-table"
        :bordered="false"
        :columns="yamlColumns"
        :data="table.dataList"
        :loading="table.tableLoading.value"
        :pagination="false"
        :scroll="{ x: grayPageConfig.scrollX, y: '100%' }"
        row-key="id"
      >
        <template #columns>
          <a-table-column v-for="item in yamlColumns" :key="item.key" v-bind="item">
            <template v-if="item.key === 'index'" #cell="{ record }">{{ record.id }}</template>
            <template v-else-if="item.key === 'bindings'" #cell="{ record }">
              <a-space v-if="visibleBindings(record.bindings).length" size="mini" wrap>
                <a-tag
                  v-for="binding of visibleBindings(record.bindings)"
                  :key="binding.id"
                  :color="environmentColor(binding?.repository?.test_env)"
                  size="small"
                >
                  {{ bindingLabel(binding) }}
                </a-tag>
                  <a-tag v-if="hiddenBindings(record.bindings).length" color="gray" size="small"
                    >+{{ hiddenBindings(record.bindings).length }}</a-tag
                  >
              </a-space>
              <span v-else>-</span>
            </template>
            <template v-else-if="item.key === 'status'" #cell="{ record }">
              <a-switch
                :beforeChange="(newValue) => onModifyYamlStatus(newValue, record.id)"
                :default-checked="record.status === 1"
              />
            </template>
            <template v-else-if="item.key === 'project_product'" #cell="{ record }">
              {{ formatProjectProductPath(record.project_product) }}
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <MangoTableActions
                :actions="[
    { label: '绑定/查看', onClick: () => onBindingManage(record) },
    { label: '编辑', onClick: () => onEdit(record) },
    {
        label: '删除',
        danger: true,
        loading: actionLoading === `delete-${record.id}`,
        onClick: () => onDelete(record), },
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

  <ModalDialog
    ref="yamlDialogRef"
    :title="form.id ? '编辑配置文件' : '新增配置文件'"
    width="560px"
    @confirm="onSubmit"
  >
    <template #content>
      <a-form
        class="mango-gray-form"
        :model="form"
        layout="horizontal"
        :label-col-props="{ span: 5 }"
        :wrapper-col-props="{ span: 19 }"
      >
        <a-form-item label="项目/产品" class="mango-form-item__require"
          ><ProjectProductSelect v-model="form.project_product" placeholder="请选择项目/产品"
        /></a-form-item>
        <a-form-item label="配置名称" class="mango-form-item__require"
          ><a-input
            v-model="form.name"
            placeholder="请输入配置名称"
            data-testid="qa-views-gray-config-file-input-请输入配置名称-2"
        /></a-form-item>
        <a-form-item label="等待秒数"
          ><a-input-number
            v-model="form.effect_wait_seconds"
            :min="0"
            placeholder="请输入等待秒数"
            data-testid="qa-views-gray-config-file-input-number-请输入等待秒数"
        /></a-form-item>
        <a-form-item label="启用状态"
          ><a-switch v-model="form.status" :checked-value="1" :unchecked-value="0"
        /></a-form-item>
      </a-form>
    </template>
  </ModalDialog>

  <ModalDialog
    ref="bindingDialogRef"
    :title="bindingForm.id ? '编辑仓库绑定' : '新增仓库绑定'"
    width="560px"
    @confirm="onBindingSubmit"
  >
    <template #content>
      <a-form
        class="mango-gray-form"
        :model="bindingForm"
        layout="horizontal"
        :label-col-props="{ span: 5 }"
        :wrapper-col-props="{ span: 19 }"
      >
        <a-form-item label="所属仓库" class="mango-form-item__require">
          <a-select
            v-model="bindingForm.repository"
            :options="repositoryOptions"
            allow-search
            placeholder="请选择仓库"
            @change="onBindingRepositoryChange"
            data-testid="qa-views-gray-config-file-select-请选择仓库"
          />
        </a-form-item>
        <a-form-item label="文件路径" class="mango-form-item__require">
          <a-cascader
            v-model="bindingForm.file_path"
            :options="repositoryFilePathOptions"
            :loading="repositoryFilePathLoading"
            allow-search
            expand-trigger="hover"
            placeholder="请选择仓库配置目录下的文件"
          />
        </a-form-item>
        <a-form-item label="启用状态"
          ><a-switch v-model="bindingForm.status" :checked-value="1" :unchecked-value="0"
        /></a-form-item>
      </a-form>
    </template>
  </ModalDialog>

  <BaseSidePanel
    :visible="contentDrawer.visible"
    :title="contentDrawer.title"
    :width="1000"
    cancel-button-text="关闭"
    @update:visible="(value) => (contentDrawer.visible = value)"
    @cancel="contentDrawer.visible = false"
  >
    <template #default>
      <div class="mango-gray-code-drawer">
        <div class="mango-gray-code-drawer__path">{{ contentDrawer.filePath || '-' }}</div>
        <CodeEditor
          v-model="contentDrawer.content"
          readonly
          placeholder="暂无配置内容"
          :code-style="{ height: 'calc(100vh - 190px)' }"
        />
      </div>
    </template>
    <template #footer-buttons>
      <a-button
        @click="contentDrawer.visible = false"
        data-testid="qa-views-gray-config-file-button-关闭"
        >关闭</a-button
      >
    </template>
  </BaseSidePanel>

  <BaseSidePanel
    :visible="bindingDrawer.visible"
    :title="bindingDrawer.title"
    :width="900"
    cancel-button-text="关闭"
    @update:visible="(value) => (bindingDrawer.visible = value)"
    @cancel="bindingDrawer.visible = false"
  >
    <template #default>
      <div class="mango-gray-binding-drawer">
        <div class="mango-gray-toolbar">
          <a-button
            size="small"
            type="primary"
            @click="onBindingAdd"
            data-testid="qa-views-gray-config-file-button-新增仓库绑定"
            >新增仓库绑定</a-button
          >
        </div>
        <a-table
          :bordered="false"
          :columns="bindingColumns"
          :data="bindingDrawer.dataList"
          :loading="bindingDrawer.loading"
          :pagination="false"
          :scroll="{ x: grayPageConfig.bindingScrollX }"
          row-key="id"
        >
          <template #columns>
            <a-table-column v-for="item in bindingColumns" :key="item.key" v-bind="item">
              <template v-if="item.key === 'index'" #cell="{ record }">{{ record.id }}</template>
              <template v-else-if="item.key === 'test_env'" #cell="{ record }">
                <a-tag :color="environmentColor(record.repository?.test_env)" size="small">{{
                  formatEnvironmentText(record.repository?.test_env)
                }}</a-tag>
              </template>
              <template v-else-if="item.key === 'repository'" #cell="{ record }">
                {{ record.repository ? repositoryLabel(record.repository) : '-' }}
              </template>
              <template v-else-if="item.key === 'status'" #cell="{ record }">
                <a-switch
                  :beforeChange="(newValue) => onModifyBindingStatus(newValue, record.id)"
                  :default-checked="record.status === 1"
                />
              </template>
              <template v-else-if="item.key === 'actions'" #cell="{ record }">
                <MangoTableActions
                  :actions="[
    {
        label: '查看',
        loading: actionLoading === `binding-content-${record.id}`,
        onClick: () => onBindingContent(record), },
    { label: '编辑', onClick: () => onBindingEdit(record) },
    {
        label: '删除',
        danger: true,
        loading: actionLoading === `binding-delete-${record.id}`,
        onClick: () => onDeleteBinding(record), },
]"
                />
              </template>
            </a-table-column>
          </template>
        </a-table>
      </div>
    </template>
  </BaseSidePanel>
</template>

<script setup lang="ts">
  import { computed, onMounted, reactive, ref } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import TableBody from '@/components/table/TableBody.vue'
  import TableHeader from '@/components/table/TableHeader.vue'
  import TableFooter from '@/components/table/TableFooter.vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import ModalDialog from '@/components/overlays/ModalDialog.vue'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import CodeEditor from '@/components/editors/CodeEditor.vue'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import { useEnum } from '@/store/modules/get-enum'
  import { usePagination, useTable } from '@/hooks/table'
  import { useLatestRequest } from '@/hooks/use-latest-request'
  import { formatProjectProductPath, getOptionId } from '@/utils/business-format'
  import type { ModalDialogType } from '@/types/components'
  import {
    deleteGrayYamlFile,
    deleteGrayYamlFileBinding,
    getGrayRepository,
    getGrayYamlFile,
    getGrayYamlFileBinding,
    getGrayYamlFileContent,
    getGrayYamlRepositoryFiles,
    postGrayYamlFile,
    postGrayYamlFileBinding,
    putGrayYamlFile,
    putGrayYamlFileBinding,
  } from '@/api/gray'
  import { enableStatusOptions, grayPageConfig } from './config'
  import { prefillNavigationModel, NavigationCreateSource } from '@/utils/navigation-create-defaults'

  const navigationCreateRef = ref<NavigationCreateSource | null>(null)

  const table = useTable()
  const enumStore = useEnum()
  const pagination = usePagination(onSearch, () => table.tableLoading)
  const { beginRequest, isLatestRequest } = useLatestRequest()
  const sidebarResetKey = ref(0)
  const yamlDialogRef = ref<ModalDialogType | null>(null)
  const bindingDialogRef = ref<ModalDialogType | null>(null)
  const query = reactive<any>({})
  const form = reactive<any>({})
  const bindingForm = reactive<any>({})
  const repositoryList = ref<any[]>([])
  const repositoryFiles = ref<string[]>([])
  const repositoryFilePathLoading = ref(false)
  const actionLoading = ref('')
  const contentDrawer = reactive({ visible: false, title: '', content: '', filePath: '' })
  const bindingDrawer = reactive<any>({
    visible: false,
    title: '',
    record: null,
    dataList: [],
    loading: false,
  })
  const yamlColumns = computed(() => grayPageConfig.columns)
  const bindingColumns = computed(() => grayPageConfig.yamlBindingColumns || [])
  const repositoryOptions = computed(() =>
    repositoryList.value.map((item) => ({ label: repositoryLabel(item), value: item.id }))
  )
  const repositoryFilePathOptions = computed(() => buildPathTree(repositoryFiles.value))

  function cleanParams(params: Record<string, any>) {
    const result: Record<string, any> = {}
    Object.entries(params).forEach(([key, value]) => {
      if (value !== '' && value !== null && value !== undefined) {
        result[key] = value
      }
    })
    return result
  }

  function requestParams() {
    return cleanParams({
      page: pagination.page,
      pageSize: pagination.pageSize,
      project_product: getOptionId(query.project_product),
      name: query.name,
      status__in: Array.isArray(query.status) ? query.status.join(',') : undefined,
    })
  }

  function isCommonEnvironment(value: any) {
    return value === null || value === undefined || value === ''
  }

  function formatEnvironmentText(value: any) {
    if (isCommonEnvironment(value)) {
      return '环境通用'
    }
    return findEnvironmentOption(value)?.title || String(value)
  }

  function environmentColor(value: any) {
    if (isCommonEnvironment(value)) {
      return 'gray'
    }
    const optionIndex = findEnvironmentOptionIndex(value)
    if (optionIndex >= 0) {
      return enumStore.colors?.[optionIndex + 1] || enumStore.colors?.[optionIndex] || 'gray'
    }
    const numericValue = Number(value)
    if (Number.isFinite(numericValue)) {
      return enumStore.colors?.[numericValue] || 'gray'
    }
    return 'gray'
  }

  function findEnvironmentOption(value: any) {
    const index = findEnvironmentOptionIndex(value)
    return index >= 0 ? enumStore.environment_type?.[index] : undefined
  }

  function findEnvironmentOptionIndex(value: any) {
    const text = String(value)
    return (enumStore.environment_type || []).findIndex((item: any) => {
      return [item.key, item.value, item.title].some((itemValue) => String(itemValue) === text)
    })
  }

  function repositoryLabel(item: any) {
    return `${item.name || '-'} / ${formatEnvironmentText(item.test_env)} / ${item.branch || '-'}`
  }

  function normalizeBindings(bindings: any[]) {
    return Array.isArray(bindings) ? bindings.filter((item) => item?.status !== 0) : []
  }

  function visibleBindings(bindings: any[]) {
    return normalizeBindings(bindings).slice(0, 3)
  }

  function hiddenBindings(bindings: any[]) {
    return normalizeBindings(bindings).slice(3)
  }

  function bindingLabel(binding: any) {
    return `${formatEnvironmentText(binding?.repository?.test_env)} / ${
      binding?.repository?.name || '-'
    }`
  }

  function normalizeRepoPath(value: any) {
    return String(value || '')
      .trim()
      .replace(/\\/g, '/')
      .replace(/^\/+|\/+$/g, '')
  }

  function normalizePathValue(value: any) {
    if (Array.isArray(value)) {
      return String(value[value.length - 1] || '').trim()
    }
    return String(value || '').trim()
  }

  function buildPathTree(paths: string[]) {
    const root: any[] = []
    const nodeMap = new Map<string, any>()
    paths
      .map((item) => normalizeRepoPath(item))
      .filter(Boolean)
      .sort()
      .forEach((filePath) => {
        const parts = filePath.split('/')
        let parentChildren = root
        let currentPath = ''
        parts.forEach((part) => {
          currentPath = currentPath ? `${currentPath}/${part}` : part
          let node = nodeMap.get(currentPath)
          if (!node) {
            node = { label: part, value: currentPath, children: [] }
            nodeMap.set(currentPath, node)
            parentChildren.push(node)
          }
          parentChildren = node.children
        })
      })
    return pruneEmptyChildren(root)
  }

  function pruneEmptyChildren(nodes: any[]) {
    return nodes.map((node) => {
      if (!node.children?.length) {
        const { children, ...rest } = node
        return rest
      }
      return { ...node, children: pruneEmptyChildren(node.children) }
    })
  }

  async function loadRepositories() {
    const res = await getGrayRepository({})
    repositoryList.value = res.data || []
  }

  async function onSearch() {
    const requestId = beginRequest()
    table.tableLoading.value = true
    try {
      const res = await getGrayYamlFile(requestParams())
      if (!isLatestRequest(requestId)) return
      table.handleSuccess(res)
      pagination.setTotalSize(res.totalSize || 0)
    } finally {
      if (isLatestRequest(requestId)) table.tableLoading.value = false
    }
    }

  function onSidebarFilterChange(filter: { projectProduct: any }) {
    query.project_product = filter.projectProduct
    pagination.page = 1
    onSearch()
  }

  function onSearchRefresh() {
    pagination.page = 1
    onSearch()
  }

  function onReset() {
    Object.keys(query).forEach((key) => {
      query[key] = key === 'status' ? [] : undefined
    })
    sidebarResetKey.value += 1
    onSearchRefresh()
  }

  function openDialog(dialog: any, target: any, data: any) {
    Object.keys(target).forEach((key) => delete target[key])
    Object.assign(target, data)
    dialog.value?.show()
  }

  function onAdd() {
    openDialog(yamlDialogRef, form, { project_product: null, effect_wait_seconds: 10, status: 1 })
    void prefillNavigationModel(navigationCreateRef.value, form)
  }

  function onEdit(record: any) {
    openDialog(yamlDialogRef, form, {
      ...record,
      project_product: record.project_product?.id || record.project_product,
    })
  }

  async function onSubmit() {
    try {
      if (!form.project_product) {
        Message.warning('请选择项目/产品')
        return
      }
      if (!form.name) {
        Message.warning('请输入配置名称')
        return
      }
      const payload = {
        ...form,
        project_product: getOptionId(form.project_product),
      }
      form.id ? await putGrayYamlFile(payload) : await postGrayYamlFile(payload)
      Message.success('保存成功')
      yamlDialogRef.value?.close()
      await onSearch()
    } finally {
      yamlDialogRef.value?.setConfirmLoading(false)
    }
  }

  async function onModifyYamlStatus(newValue: boolean, id: number) {
    try {
      const res = await putGrayYamlFile({ id, status: newValue ? 1 : 0 })
      const success = res.code === 200
      if (success) {
        Message.success(res.msg || '状态更新成功')
        await onSearch()
      }
      return success
    } catch (error) {
      return false
    }
  }

  async function onModifyBindingStatus(newValue: boolean, id: number) {
    try {
      const res = await putGrayYamlFileBinding({ id, status: newValue ? 1 : 0 })
      const success = res.code === 200
      if (success) {
        Message.success(res.msg || '状态更新成功')
        await loadBindings(bindingDrawer.record?.id)
        await onSearch()
      }
      return success
    } catch (error) {
      return false
    }
  }

  async function onContent(record: any) {
    const binding = normalizeBindings(record.bindings)[0]
    if (!binding) {
      Message.warning('请先为配置文件增加仓库绑定')
      return
    }
    actionLoading.value = `content-${record.id}`
    try {
      const res = await getGrayYamlFileContent({ id: record.id, binding_id: binding.id })
      contentDrawer.title = record.name
      contentDrawer.filePath = res.data?.file_path || binding.file_path || ''
      contentDrawer.content = res.data?.content || ''
      contentDrawer.visible = true
    } finally {
      actionLoading.value = ''
    }
  }

  function onDelete(record: any) {
    Modal.confirm({
      title: '删除配置文件',
      content: `确认删除 ${record.name}？`,
      onOk: async () => {
        actionLoading.value = `delete-${record.id}`
        try {
          await deleteGrayYamlFile(record.id)
          await onSearch()
        } finally {
          actionLoading.value = ''
        }
      },
    })
  }

  async function onBindingManage(record: any) {
    bindingDrawer.record = record
    bindingDrawer.title = `${record.name} 仓库绑定`
    bindingDrawer.visible = true
    await loadBindings(record.id)
  }

  async function loadBindings(yamlFileId: any) {
    bindingDrawer.loading = true
    try {
      const res = await getGrayYamlFileBinding({ yaml_file: yamlFileId, page: 1, pageSize: 200 })
      bindingDrawer.dataList = res.data || []
    } finally {
      bindingDrawer.loading = false
    }
  }

  function onBindingAdd() {
    if (!bindingDrawer.record?.id) {
      Message.warning('请先选择配置文件')
      return
    }
    repositoryFiles.value = []
    openDialog(bindingDialogRef, bindingForm, { yaml_file: bindingDrawer.record.id, status: 1 })
  }

  async function onBindingEdit(record: any) {
    repositoryFiles.value = record.file_path ? [record.file_path] : []
    openDialog(bindingDialogRef, bindingForm, {
      ...record,
      yaml_file: record.yaml_file?.id || record.yaml_file || bindingDrawer.record?.id,
      repository: record.repository?.id || record.repository,
    })
    await loadRepositoryFiles(bindingForm.repository)
  }

  async function onBindingRepositoryChange() {
    bindingForm.file_path = undefined
    await loadRepositoryFiles(bindingForm.repository)
  }

  async function loadRepositoryFiles(repositoryId: any) {
    if (!repositoryId) {
      repositoryFiles.value = []
      return
    }
    repositoryFilePathLoading.value = true
    try {
      const res = await getGrayYamlRepositoryFiles({ repository_id: repositoryId })
      repositoryFiles.value = Array.isArray(res.data) ? res.data : []
    } finally {
      repositoryFilePathLoading.value = false
    }
  }

  async function onBindingSubmit() {
    try {
      if (!bindingForm.repository) {
        Message.warning('请选择所属仓库')
        return
      }
      if (!bindingForm.file_path) {
        Message.warning('请选择文件路径')
        return
      }
      const payload = {
        ...bindingForm,
        yaml_file: bindingForm.yaml_file || bindingDrawer.record?.id,
        file_path: normalizePathValue(bindingForm.file_path),
      }
      bindingForm.id
        ? await putGrayYamlFileBinding(payload)
        : await postGrayYamlFileBinding(payload)
      Message.success('保存成功')
      bindingDialogRef.value?.close()
      await loadBindings(payload.yaml_file)
      await onSearch()
    } finally {
      bindingDialogRef.value?.setConfirmLoading(false)
    }
  }

  async function onBindingContent(record: any) {
    const yamlFileId = record.yaml_file?.id || record.yaml_file || bindingDrawer.record?.id
    actionLoading.value = `binding-content-${record.id}`
    try {
      const res = await getGrayYamlFileContent({ id: yamlFileId, binding_id: record.id })
      contentDrawer.title = bindingDrawer.record?.name || record.yaml_file?.name || '配置文件'
      contentDrawer.filePath = res.data?.file_path || record.file_path || ''
      contentDrawer.content = res.data?.content || ''
      contentDrawer.visible = true
    } finally {
      actionLoading.value = ''
    }
  }

  function onDeleteBinding(record: any) {
    Modal.confirm({
      title: '删除仓库绑定',
      content: `确认删除 ${record.file_path}？`,
      onOk: async () => {
        actionLoading.value = `binding-delete-${record.id}`
        try {
          await deleteGrayYamlFileBinding(record.id)
          await loadBindings(bindingDrawer.record?.id)
          await onSearch()
        } finally {
          actionLoading.value = ''
        }
      },
    })
  }

  onMounted(async () => {
    await loadRepositories()
  })
</script>

<style scoped lang="less">
  .mango-gray-toolbar {
    display: flex;
    justify-content: flex-end;
  }

  .mango-gray-form {
    :deep(.arco-form-item) {
      margin-bottom: 12px;
    }
  }

  .mango-gray-code-drawer {
    display: flex;
    flex-direction: column;
    gap: 10px;
    min-height: 0;
  }

  .mango-gray-code-drawer__path {
    overflow: hidden;
    padding: 8px 10px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    background: var(--m-surface-soft);
    color: var(--m-text-2);
    font-size: 13px;
    line-height: 20px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
</style>
