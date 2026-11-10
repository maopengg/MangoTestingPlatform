<template>
  <TableBody plain class="mango-detail-workbench-page mango-pytest-repository-page">
    <template #header>
      <TableHeader title="Pytest 仓库管理">
        <template #header-extra>
          <a-button type="primary" size="small" @click="openEditor()">新增仓库</a-button>
        </template>
      </TableHeader>
    </template>
    <template #default>
      <div class="mango-pytest-repository-page__content">
        <div class="mango-pytest-repository-page__overview">
          <div class="mango-pytest-repository-page__metric">
            <span class="mango-pytest-repository-page__metric-label">仓库</span>
            <div class="mango-pytest-repository-page__metric-value">
              <strong>{{ repositoryMetrics.repositories }}</strong
              ><small>个</small>
            </div>
            <span class="mango-pytest-repository-page__metric-note">已纳管代码仓库</span>
          </div>
          <div class="mango-pytest-repository-page__metric">
            <span class="mango-pytest-repository-page__metric-label">已绑定项目</span>
            <div class="mango-pytest-repository-page__metric-value">
              <strong>{{ repositoryMetrics.projects }}</strong
              ><small>个</small>
            </div>
            <span class="mango-pytest-repository-page__metric-note">已关联测试项目</span>
          </div>
          <div class="mango-pytest-repository-page__metric">
            <span class="mango-pytest-repository-page__metric-label">Pytest Case</span>
            <div class="mango-pytest-repository-page__metric-value">
              <strong>{{ repositoryMetrics.cases }}</strong
              ><small>条</small>
            </div>
            <span class="mango-pytest-repository-page__metric-note">已发现测试用例</span>
          </div>
          <div
            class="mango-pytest-repository-page__metric mango-pytest-repository-page__metric--status"
            :class="{ 'mango-pytest-repository-page__metric--danger': repositoryMetrics.failed }"
          >
            <span class="mango-pytest-repository-page__metric-label">同步异常</span>
            <div class="mango-pytest-repository-page__metric-value">
              <strong>{{ repositoryMetrics.failed }}</strong
              ><small>个</small>
            </div>
            <span class="mango-pytest-repository-page__metric-note">
              {{ repositoryMetrics.failed ? '存在异常需处理' : '当前同步正常' }}
            </span>
          </div>
        </div>


        <div class="mango-workbench-scroll-x"
          ><div class="mango-pytest-repository-page__workbench">
            <aside class="mango-pytest-repository-page__tree-panel">
              <PytestCaseDirectoryTree
                :data="repositoryTree"
                :loading="selectedTreeLoading"
                :selected-key="selectedTreeKey"
                expand-selected
                @select="onTreeNodeSelect"
                @directory-toggle="onTreeNodeSelect"
              >
                <template #actions
                  ><a-button
                    v-if="selectedTreeFailed"
                    type="text"
                    status="danger"
                    size="small"
                    :loading="selectedTreeLoading"
                    @click="retryTree"
                    >重试</a-button
                  ></template
                >
              </PytestCaseDirectoryTree>
            </aside>

            <section class="mango-pytest-repository-page__main">
              <div v-if="selectedRepository" class="mango-pytest-repository-page__selection">
                <div class="mango-pytest-repository-page__selection-title">
                  <strong>{{ selectedRepository.name }}</strong>
                  <a-tag size="small">{{ providerLabel(selectedRepository.provider) }}</a-tag>
                  <a-tag :color="syncStatusColor(selectedRepository.sync_status)" size="small">
                    {{ syncStatusLabel(selectedRepository.sync_status) }}
                  </a-tag>
                </div>
                <div class="mango-pytest-repository-page__selection-meta">
                  <span
                    >分支
                    {{
                      selectedRepository.active_branch || selectedRepository.default_branch
                    }}</span
                  >
                  <span>目录 {{ selectedTreeStats.directory_count }}</span>
                  <span>文件 {{ selectedTreeStats.file_count }}</span>
                </div>
              </div>
              <div v-if="selectedFileNode" class="mango-pytest-repository-page__preview">
                <div class="mango-pytest-repository-page__preview-header">
                  <div>
                    <strong :title="selectedFileNode.path">{{ selectedFileNode.path }}</strong>
                    <a-tag v-if="isMarkdownPreview" color="blue" size="small">Markdown</a-tag>
                    <a-tag color="gray" size="small">只读</a-tag>
                  </div>
                  <a-button class="mango-back-button" size="small" @click="returnToRepositoryList">
                    返回仓库列表
                  </a-button>
                </div>
                <mango-panel-spin
                  :loading="filePreviewLoading"
                  class="mango-pytest-repository-page__preview-body"
                >

                  <template v-if="filePreviewFailed"></template>
                  <CodeEditor
                    v-else-if="!isMarkdownPreview"
                    v-model="filePreviewContent"
                    :language="filePreviewLanguage"
                    :code-style="{ height: '100%' }"
                    readonly
                    placeholder="暂无可预览内容"
                  />
                </mango-panel-spin>
              </div>
              <a-table
                v-else
                class="mango-native-scroll-table mango-pytest-repository-page__table"
                :columns="tableColumns"
                :data="repositories"
                :loading="loading"
                :pagination="false"
                :scroll="{ x: repositoryScrollWidth, y: '100%' }"
                :row-class="repositoryRowClass"
                row-key="id"
                @row-click="onRepositoryRowClick"
              >
                <template #columns>
                  <a-table-column
                    v-for="column in tableColumns"
                    :key="column.key"
                    :title="column.title"
                    :data-index="column.key"
                    :align="column.align"
                    :width="column.width"
                    :fixed="column.fixed"
                    :ellipsis="column.ellipsis"
                    :tooltip="column.tooltip"
                  >
                    <template #cell="{ record }">
                      <div
                        v-if="column.key === 'repository'"
                        class="mango-pytest-repository-page__identity"
                      >
                        <strong :title="record.name">{{ record.name }}</strong>
                        <div>
                          <a-tag size="small">{{ providerLabel(record.provider) }}</a-tag>
                          <span>{{
                            record.credential?.configured ? '已配置凭证' : '公开仓库'
                          }}</span>
                        </div>
                      </div>
                      <div
                        v-else-if="column.key === 'source'"
                        class="mango-pytest-repository-page__source"
                      >
                        <span :title="record.repo_url">{{ record.repo_url }}</span>
                        <div>
                          <a-tag size="small">{{
                            record.active_branch || record.default_branch
                          }}</a-tag>
                          <code v-if="record.current_commit">{{
                            shortCommit(record.current_commit)
                          }}</code>
                        </div>
                      </div>
                      <div
                        v-else-if="column.key === 'assets'"
                        class="mango-pytest-repository-page__assets"
                      >
                        <span
                          >项目 <strong>{{ record.project_count || 0 }}</strong></span
                        >
                        <span
                          >Case <strong>{{ record.case_count || 0 }}</strong></span
                        >
                      </div>
                      <div
                        v-else-if="column.key === 'sync'"
                        class="mango-pytest-repository-page__sync"
                      >
                        <div>
                          <a-tag :color="syncStatusColor(record.sync_status)" size="small">
                            {{ syncStatusLabel(record.sync_status) }}
                          </a-tag>
                          <span>{{ record.last_sync_time || '尚未同步' }}</span>
                        </div>
                        <small v-if="record.last_sync_error" :title="record.last_sync_error">
                          {{ record.last_sync_error }}
                        </small>
                      </div>
                      <template v-else-if="column.key === 'actions'">
                        <MangoTableActions :actions="repositoryActions(record)" />
                      </template>
                      <template v-else>{{ record[column.key] ?? '-' }}</template>
                    </template>
                  </a-table-column>
                </template>
                <template #empty>
                  <div class="mango-empty-state">暂无 Pytest 仓库</div>
                </template>
              </a-table>
            </section>
          </div></div
        >
      </div>
    </template>
  </TableBody>

  <PytestRepositoryEditor
    ref="editor"
    :busy-ids="busyIds"
    @busy="editorBusy"
    @saved="refreshAfterWrite"
  />
  <a-modal
    modal-class="mango-simple-form-modal"
    :visible="branchVisible"
    title="切换仓库分支"
    :width="560"
    :ok-loading="branchSwitching"
    :on-before-ok="confirmSwitchBranch"
    @cancel="closeBranch"
    @update:visible="onBranchVisible"
  >
    <a-form class="mango-simple-form" :model="branchForm" layout="horizontal" auto-label-width :disabled="branchSwitching">
      <a-form-item label="目标分支" class="mango-form-item__require mango-simple-form-item">
        <a-select
          v-model="branchForm.branch"
          :options="branchOptions"
          :loading="branchLoading"
          allow-search
          placeholder="请选择分支"
        />
        <template v-if="branchFailed" #extra
          ><a-button size="small" :loading="branchLoading" @click="loadBranchOptions"
            >重试</a-button
          ></template
        >
      </a-form-item>
    </a-form>
  </a-modal>
</template>

<script lang="ts" setup>
import { reportLoadError, runLoadRequest } from '@/utils/load-error'

  import {
    computed,
    onActivated,
    onBeforeUnmount,
    onDeactivated,
    onMounted,
    reactive,
    ref,
    watch,
  } from 'vue'
  import { useRoute } from 'vue-router'
  import { Message, Modal } from '@arco-design/web-vue'
  import { MdPreview } from 'md-editor-v3'
  import 'md-editor-v3/lib/preview.css'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import {
    deletePytestRepository,
    getPytestRepositories,
    getPytestRepositoryBranches,
    getPytestRepositoryFile,
    getPytestRepositoryTree,
    pullPytestRepository,
    switchPytestRepositoryBranch,
    testPytestRepository,
    type PytestRepository,
  } from '@/api/pytest/repository'
  import { providerOptions, repositoryScrollWidth, tableColumns } from './config'
  import {
    buildRepositoryTree,
    readBranches,
    readRepositories,
    readRepositoryFile,
    readRepositoryTree,
    repositoryResponse,
    repositoryRevision,
    repositoryRootKey,
  } from './records'
  import type { BranchOption } from './records'
  import type { DirectoryNode } from '../case/records'
  import PytestCaseDirectoryTree from '@/views/pytest/case/components/PytestCaseDirectoryTree.vue'
  import PytestRepositoryEditor from './components/PytestRepositoryEditor.vue'
  import CodeEditor from '@/components/editors/CodeEditor.vue'
  import useAppConfigStore from '@/store/modules/app-config'
  import useUserStore from '@/store/modules/user'
  import { usePagePolling } from '@/hooks/use-page-polling'

  interface TreeCache {
    revision: string
    nodes: DirectoryNode[]
    directory_count: number
    file_count: number
  }
  const repositories = ref<PytestRepository[]>([]),
    loading = ref(false),
    listFailed = ref(false)
  const user = useUserStore(),
    route = useRoute(),
    appStore = useAppConfigStore()
  const editor = ref<InstanceType<typeof PytestRepositoryEditor> | null>(null)
  const actionIds = ref<number[]>([]),
    editorBusyIds = ref<number[]>([])
  const busyIds = computed(() => [...new Set([...actionIds.value, ...editorBusyIds.value])])
  const selectedRepositoryId = ref<number | null>(null),
    selectedTreeKey = ref('')
  const trees = reactive(new Map<number, TreeCache>()),
    treeLoading = ref<number[]>([]),
    treeFailed = ref<number[]>([])
  const selectedFileNode = ref<DirectoryNode | null>(null),
    filePreviewContent = ref(''),
    filePreviewLoading = ref(false),
    filePreviewFailed = ref(false)
  const branchVisible = ref(false),
    branchLoading = ref(false),
    branchFailed = ref(false),
    branchSwitching = ref(false)
  const branchOptions = ref<BranchOption[]>([]),
    branchForm = reactive<{ repositoryId: number | null; branch: string }>({
      repositoryId: null,
      branch: '',
    })
  let version = 0,
    listRequest = 0,
    fileRequest = 0,
    treeRequest = 0,
    branchVersion = 0,
    branchRequest = 0,
    confirmationVersion = 0
  let active = true,
    disposed = false,
    openedEditorId: number | null = null
  let listPending: { version: number; promise: Promise<void> } | null = null
  const treePending = new Map<number, { request: number; promise: Promise<void> }>()
  let confirmation: ReturnType<typeof Modal.confirm> | null = null
  const available = () =>
    !disposed && active && (typeof document === 'undefined' || !document.hidden)
  const current = (context: number) => available() && context === version
  const selectedRepository = computed(
    () => repositories.value.find((row) => row.id === selectedRepositoryId.value) ?? null
  )
  const selectedTreeStats = computed(() =>
    selectedRepositoryId.value === null
      ? { directory_count: 0, file_count: 0 }
      : trees.get(selectedRepositoryId.value) ?? { directory_count: 0, file_count: 0 }
  )
  const selectedTreeLoading = computed(
    () =>
      selectedRepositoryId.value !== null && treeLoading.value.includes(selectedRepositoryId.value)
  )
  const selectedTreeFailed = computed(
    () =>
      selectedRepositoryId.value !== null && treeFailed.value.includes(selectedRepositoryId.value)
  )
  const repositoryMetrics = computed(() => ({
    repositories: repositories.value.length,
    projects: repositories.value.reduce((n, row) => n + row.project_count, 0),
    cases: repositories.value.reduce((n, row) => n + row.case_count, 0),
    failed: repositories.value.filter((row) => row.sync_status === 3).length,
  }))
  const repositoryTree = computed<DirectoryNode[]>(() =>
    repositories.value.map((row) => ({
      key: repositoryRootKey(row.id),
      title: row.name,
      type: 'repository',
      path: '',
      breadcrumb: [row.name],
      repository_id: row.id,
      case_count: 0,
      count: trees.get(row.id)?.file_count ?? 0,
      children: trees.get(row.id)?.nodes ?? [],
    }))
  )
  const filePreviewLanguage = computed<'python' | 'json'>(() =>
    selectedFileNode.value?.path.toLowerCase().endsWith('.json') ? 'json' : 'python'
  )
  const isMarkdownPreview = computed(() =>
    /\.(md|markdown|mdown|mkd)$/i.test(selectedFileNode.value?.path ?? '')
  )
  const markdownTheme = computed<'light' | 'dark'>(() =>
    appStore.theme === 'dark' ? 'dark' : 'light'
  )
  function providerLabel(value: string): string {
    return providerOptions.find((item) => item.value === value)?.label || value || '-'
  }
  function syncStatusLabel(value: number): string {
    return ['空闲', '同步中', '成功', '失败'][value] || '-'
  }
  function syncStatusColor(value: number): string {
    return ['gray', 'arcoblue', 'green', 'red'][value] || 'gray'
  }
  function shortCommit(value?: string | null): string {
    return (value ?? '').slice(0, 8)
  }
  function clearPreview(): void {
    fileRequest++
    selectedFileNode.value = null
    filePreviewContent.value = ''
    filePreviewLoading.value = false
    filePreviewFailed.value = false
  }
  function closeBranch(): void {
    branchVersion++
    branchRequest++
    branchVisible.value = false
    branchLoading.value = false
    branchFailed.value = false
    branchOptions.value = []
    branchForm.repositoryId = null
    branchForm.branch = ''
  }
  function invalidateTree(id: number): void {
    treePending.delete(id)
    trees.delete(id)
    treeLoading.value = treeLoading.value.filter((value) => value !== id)
    treeFailed.value = treeFailed.value.filter((value) => value !== id)
    if (selectedFileNode.value?.repository_id === id) clearPreview()
    if (selectedRepositoryId.value === id) selectedTreeKey.value = repositoryRootKey(id)
  }
  function invalidate(clear = false): void {
    version++
    listRequest++
    confirmationVersion++
    listPending = null
    loading.value = false
    confirmation?.close()
    confirmation = null
    editor.value?.close()
    closeBranch()
    clearPreview()
    treePending.clear()
    trees.clear()
    treeLoading.value = []
    treeFailed.value = []
    selectedTreeKey.value =
      selectedRepositoryId.value === null ? '' : repositoryRootKey(selectedRepositoryId.value)
    if (clear) {
      repositories.value = []
      selectedRepositoryId.value = null
      selectedTreeKey.value = ''
      listFailed.value = false
    }
  }
  function editorBusy(id: number | null, busy: boolean): void {
    if (id === null) return
    editorBusyIds.value = busy
      ? [...new Set([...editorBusyIds.value, id])]
      : editorBusyIds.value.filter((value) => value !== id)
  }
  function openEditor(row?: PytestRepository): void {
    if (!available() || (row && busyIds.value.includes(row.id))) return
    const record = row ? repositories.value.find((item) => item.id === row.id) : undefined
    if (row && !record) return
    closeBranch()
    openedEditorId = record?.id ?? null
    editor.value?.open(record)
  }
  function repositoryRowClass(row: PytestRepository): string {
    return row.id === selectedRepositoryId.value
      ? 'mango-pytest-repository-page__row--selected'
      : ''
  }
  function repositoryActions(row: PytestRepository) {
    const busy = busyIds.value.includes(row.id)
    return [
      { label: '编辑', disabled: busy, onClick: () => openEditor(row) },
      { label: '拉取', loading: busy, onClick: () => void runAction(row, 'pull') },
      { label: '测试连接', loading: busy, onClick: () => void runAction(row, 'test') },
      { label: '切换分支', disabled: busy, onClick: () => void openBranch(row) },
      { label: '删除', danger: true, disabled: busy, onClick: () => removeRepository(row) },
    ]
  }
  function loadRepositories(silent = false): Promise<void> {
    if (!available()) return Promise.resolve()
    if (listPending?.version === version) {
      if (!silent) loading.value = true
      return listPending.promise
    }
    const context = version,
      request = ++listRequest
    if (!silent) loading.value = true
    listFailed.value = false
    const promise = (async () => {
      try {
        const rows = readRepositories(await runLoadRequest(silent, () => getPytestRepositories()))
        if (!current(context) || request !== listRequest) return
        for (const old of repositories.value) {
          const next = rows.find((row) => row.id === old.id)
          if (!next || repositoryRevision(next) !== repositoryRevision(old)) {
            invalidateTree(old.id)
            if (openedEditorId === old.id) editor.value?.close()
            if (branchForm.repositoryId === old.id) closeBranch()
          }
        }
        repositories.value = rows
        if (!rows.some((row) => row.id === selectedRepositoryId.value)) {
          clearPreview()
          selectedRepositoryId.value = rows[0]?.id ?? null
          selectedTreeKey.value =
            selectedRepositoryId.value === null ? '' : repositoryRootKey(selectedRepositoryId.value)
        }
        if (selectedRepositoryId.value !== null) void loadRepositoryTree(selectedRepositoryId.value)
      } catch (loadFailure0) {
        if (current(context) && request === listRequest) (reportLoadError(loadFailure0, "加载失败，请重试", silent), listFailed.value = true)
      } finally {
        if (current(context) && request === listRequest) {
          loading.value = false
          listPending = null
        }
      }
    })()
    listPending = { version, promise }
    return promise
  }
  function loadRepositoryTree(id: number, force = false): Promise<void> {
    const row = repositories.value.find((row) => row.id === id)
    if (!available() || !row) return Promise.resolve()
    if (!force && treePending.has(id)) return treePending.get(id)!.promise
    const revision = repositoryRevision(row)
    if (!force && trees.get(id)?.revision === revision) return Promise.resolve()
    if (force) invalidateTree(id)
    const context = version,
      request = ++treeRequest
    treeLoading.value = [...new Set([...treeLoading.value, id])]
    treeFailed.value = treeFailed.value.filter((value) => value !== id)
    const valid = () =>
      current(context) &&
      treePending.get(id)?.request === request &&
      repositories.value.some((row) => row.id === id && repositoryRevision(row) === revision)
    const promise = (async () => {
      try {
        const data = readRepositoryTree(await getPytestRepositoryTree(id))
        if (!valid()) return
        trees.set(id, {
          revision,
          nodes: buildRepositoryTree(row, data.entries),
          directory_count: data.directory_count,
          file_count: data.file_count,
        })
      } catch (loadFailure0) {
        if (valid()) (reportLoadError(loadFailure0, "加载失败，请重试", false), treeFailed.value = [...new Set([...treeFailed.value, id])])
      } finally {
        if (valid()) {
          treeLoading.value = treeLoading.value.filter((value) => value !== id)
          treePending.delete(id)
        }
      }
    })()
    treePending.set(id, { request, promise })
    return promise
  }
  function findNode(key: string, nodes = repositoryTree.value): DirectoryNode | null {
    for (const node of nodes) {
      if (node.key === key) return node
      const child = findNode(key, node.children)
      if (child) return child
    }
    return null
  }
  async function selectRepository(id: number): Promise<void> {
    if (!available() || !repositories.value.some((row) => row.id === id)) return
    clearPreview()
    selectedRepositoryId.value = id
    selectedTreeKey.value = repositoryRootKey(id)
    await loadRepositoryTree(id)
  }
  function onRepositoryRowClick(row: PytestRepository): void {
    void selectRepository(row.id)
  }
  function onTreeNodeSelect(value: DirectoryNode | null): void {
    if (!available() || !value) return
    const node = findNode(value.key)
    if (!node || node.repository_id == null) return
    if (node.type === 'file') {
      void loadFilePreview(node)
      return
    }
    clearPreview()
    selectedRepositoryId.value = node.repository_id
    selectedTreeKey.value = node.key
    void loadRepositoryTree(node.repository_id)
  }
  async function loadFilePreview(value: DirectoryNode): Promise<void> {
    const node = findNode(value.key)
    if (!available() || !node || node.type !== 'file' || node.repository_id == null) return
    const row = repositories.value.find((row) => row.id === node.repository_id)
    if (!row) return
    const context = version,
      request = ++fileRequest,
      revision = repositoryRevision(row)
    selectedRepositoryId.value = row.id
    selectedTreeKey.value = node.key
    selectedFileNode.value = node
    filePreviewContent.value = ''
    filePreviewLoading.value = true
    filePreviewFailed.value = false
    const valid = () =>
      current(context) &&
      request === fileRequest &&
      repositories.value.some(
        (row) => row.id === node.repository_id && repositoryRevision(row) === revision
      )
    try {
      const content = readRepositoryFile(
        await getPytestRepositoryFile(row.id, node.path),
        node.path
      )
      if (valid()) filePreviewContent.value = content
    } catch (loadFailure1) {
      if (valid()) (reportLoadError(loadFailure1, "加载失败，请重试", false), filePreviewFailed.value = true)
    } finally {
      if (valid()) filePreviewLoading.value = false
    }
  }
  function retryFilePreview(): void {
    if (selectedFileNode.value) void loadFilePreview(selectedFileNode.value)
  }
  function retryTree(): void {
    if (selectedRepositoryId.value !== null)
      void loadRepositoryTree(selectedRepositoryId.value, true)
  }
  function returnToRepositoryList(): void {
    clearPreview()
    selectedTreeKey.value =
      selectedRepositoryId.value === null ? '' : repositoryRootKey(selectedRepositoryId.value)
  }
  async function refreshAfterWrite(id: number | null): Promise<void> {
    if (!available()) return
    listRequest++
    listPending = null
    if (id !== null) invalidateTree(id)
    await loadRepositories()
  }
  async function runAction(row: PytestRepository, action: 'pull' | 'test'): Promise<boolean> {
    if (
      !available() ||
      busyIds.value.includes(row.id) ||
      !repositories.value.some((item) => item.id === row.id)
    )
      return false
    const id = row.id,
      context = version
    actionIds.value = [...actionIds.value, id]
    try {
      repositoryResponse(
        await (action === 'pull' ? pullPytestRepository(id) : testPytestRepository(id))
      )
      if (!current(context)) return false
      Message.success(action === 'pull' ? '仓库拉取成功' : '连接测试成功')
      await refreshAfterWrite(id)
      return current(context)
    } catch {
      if (current(context)) Message.error('仓库操作失败，请重试')
      return false
    } finally {
      actionIds.value = actionIds.value.filter((value) => value !== id)
    }
  }
  async function loadBranchOptions(): Promise<void> {
    const id = branchForm.repositoryId
    if (!available() || !branchVisible.value || id === null || branchLoading.value) return
    const context = version,
      window = branchVersion,
      request = ++branchRequest
    branchLoading.value = true
    branchFailed.value = false
    const valid = () =>
      current(context) &&
      window === branchVersion &&
      request === branchRequest &&
      branchVisible.value
    try {
      const options = readBranches(await getPytestRepositoryBranches(id))
      if (valid()) branchOptions.value = options
    } catch (loadFailure1) {
      if (valid()) (reportLoadError(loadFailure1, "加载失败，请重试", false), branchFailed.value = true)
    } finally {
      if (valid()) branchLoading.value = false
    }
  }
  async function openBranch(row: PytestRepository): Promise<void> {
    if (!available() || branchSwitching.value || busyIds.value.includes(row.id)) return
    const record = repositories.value.find((item) => item.id === row.id)
    if (!record) return
    editor.value?.close()
    closeBranch()
    branchForm.repositoryId = record.id
    branchForm.branch = record.active_branch || record.default_branch
    branchVisible.value = true
    await loadBranchOptions()
  }
  async function confirmSwitchBranch(): Promise<boolean> {
    const id = branchForm.repositoryId,
      branch = branchForm.branch
    if (
      !available() ||
      !branchVisible.value ||
      id === null ||
      busyIds.value.includes(id) ||
      branchSwitching.value ||
      branchLoading.value ||
      branchFailed.value
    )
      return false
    if (!branchOptions.value.some((option) => option.value === branch)) {
      Message.warning('请选择有效的目标分支')
      return false
    }
    const context = version,
      window = branchVersion
    branchSwitching.value = true
    actionIds.value = [...actionIds.value, id]
    try {
      repositoryResponse(await switchPytestRepositoryBranch(id, branch))
      if (!current(context) || window !== branchVersion || !branchVisible.value) return false
      closeBranch()
      Message.success('分支切换成功')
      await refreshAfterWrite(id)
      return current(context)
    } catch {
      if (current(context) && window === branchVersion) Message.error('分支切换失败，请重试')
      return false
    } finally {
      branchSwitching.value = false
      actionIds.value = actionIds.value.filter((value) => value !== id)
    }
  }
  function onBranchVisible(value: boolean): void {
    if (!value) closeBranch()
  }
  function removeRepository(row: PytestRepository): void {
    if (
      !available() ||
      busyIds.value.includes(row.id) ||
      !repositories.value.some((item) => item.id === row.id)
    )
      return
    confirmation?.close()
    const id = row.id,
      context = version,
      window = ++confirmationVersion
    const revision = repositoryRevision(repositories.value.find((item) => item.id === id)!)
    const valid = () => current(context) && window === confirmationVersion
    confirmation = Modal.confirm({
      title: '删除 Pytest 仓库',
      content: '只有未绑定 Pytest 项目的仓库才能删除。确定继续吗？',
      okButtonProps: { status: 'danger' },
      onCancel: () => {
        if (window === confirmationVersion) {
          confirmationVersion++
          confirmation = null
        }
      },
      onBeforeOk: async () => {
        if (
          !valid() ||
          busyIds.value.includes(id) ||
          !repositories.value.some((row) => row.id === id && repositoryRevision(row) === revision)
        )
          return false
        actionIds.value = [...actionIds.value, id]
        try {
          repositoryResponse(await deletePytestRepository(id))
          if (!valid()) return false
          repositories.value = repositories.value.filter((row) => row.id !== id)
          if (selectedRepositoryId.value === id) {
            clearPreview()
            selectedRepositoryId.value = repositories.value[0]?.id ?? null
            selectedTreeKey.value =
              selectedRepositoryId.value === null
                ? ''
                : repositoryRootKey(selectedRepositoryId.value)
          }
          if (branchForm.repositoryId === id) closeBranch()
          if (openedEditorId === id) editor.value?.close()
          Message.success('仓库删除成功')
          await refreshAfterWrite(id)
          return valid()
        } catch {
          if (valid()) Message.error('仓库删除失败，请重试')
          return false
        } finally {
          actionIds.value = actionIds.value.filter((value) => value !== id)
        }
      },
    })
  }
  watch(
    () => [user.userId, user.roleId, user.token, user.selected_environment, route.fullPath],
    () => {
      invalidate(true)
      void loadRepositories()
    },
    { flush: 'sync' }
  )
  function visibilityChanged(): void {
    if (typeof document !== 'undefined' && document.hidden) invalidate()
    else void loadRepositories()
  }
  const polling = usePagePolling(async (context) => {
    if (!context.isCurrent() || !repositories.value.some((row) => row.sync_status === 1)) return
    await loadRepositories(true)
  })
  watch(
    () => repositories.value.some((row) => row.sync_status === 1),
    (pending) => {
      if (pending) polling.start()
      else polling.stop()
    },
    { flush: 'sync' }
  )
  onMounted(() => {
    if (typeof document !== 'undefined')
      document.addEventListener('visibilitychange', visibilityChanged)
    void loadRepositories()
  })
  onActivated(() => {
    active = true
    void loadRepositories()
  })
  onDeactivated(() => {
    active = false
    invalidate()
  })
  onBeforeUnmount(() => {
    disposed = true
    invalidate(true)
    if (typeof document !== 'undefined')
      document.removeEventListener('visibilitychange', visibilityChanged)
  })
</script>

<style lang="less" scoped>
  .mango-pytest-repository-page__content {
    display: flex;
    height: 100%;
    min-height: 0;
    flex-direction: column;
    gap: var(--m-page-gap);
    padding: var(--m-page-gap);
  }

  .mango-pytest-repository-page__overview {
    display: grid;
    flex: 0 0 auto;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: var(--m-page-gap);
  }

  .mango-pytest-repository-page__metric {
    position: relative;
    display: grid;
    min-height: 82px;
    padding: 10px 14px 10px 16px;
    grid-template-columns: minmax(0, 1fr) auto;
    align-content: center;
    align-items: end;
    gap: 4px 12px;
    overflow: hidden;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);

    &::before {
      position: absolute;
      top: 10px;
      bottom: 10px;
      left: 0;
      width: 3px;
      border-radius: 0 var(--m-radius-sm) var(--m-radius-sm) 0;
      background: var(--m-primary);
      content: '';
    }
  }

  .mango-pytest-repository-page__metric-label {
    align-self: start;
    color: var(--m-text-2);
    font-size: 12px;
    font-weight: 500;
  }

  .mango-pytest-repository-page__metric-value {
    display: flex;
    grid-row: 1 / span 2;
    grid-column: 2;
    align-items: baseline;
    gap: 5px;

    strong {
      color: var(--m-text);
      font-size: 26px;
      font-variant-numeric: tabular-nums;
      line-height: 1;
    }

    small {
      color: var(--m-muted);
      font-size: 12px;
    }
  }

  .mango-pytest-repository-page__metric-note {
    overflow: hidden;
    color: var(--m-muted);
    font-size: 11px;
    line-height: 16px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-pytest-repository-page__metric--status {
    &::before {
      background: var(--m-success);
    }

    .mango-pytest-repository-page__metric-value strong,
    .mango-pytest-repository-page__metric-note {
      color: var(--m-success);
    }
  }

  .mango-pytest-repository-page__metric--danger {
    &::before {
      background: var(--m-danger);
    }

    .mango-pytest-repository-page__metric-value strong,
    .mango-pytest-repository-page__metric-note {
      color: var(--m-danger);
    }
  }

  .mango-workbench-scroll-x {
    --mango-workbench-min-width: 960px;
    flex: 1 1 auto;
    min-height: 0;
  }

  .mango-pytest-repository-page__workbench {
    height: 100%;
    min-width: var(--mango-workbench-min-width);
    display: grid;
    min-height: 0;
    flex: 1 1 auto;
    grid-template-columns: 300px minmax(0, 1fr);
    gap: var(--m-page-gap);
    overflow: hidden;
  }

  .mango-pytest-repository-page__tree-panel,
  .mango-pytest-repository-page__main {
    min-width: 0;
    min-height: 0;
    overflow: hidden;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
  }

  .mango-pytest-repository-page__tree-panel {
    padding: 8px;
  }

  .mango-pytest-repository-page__main {
    display: flex;
    flex-direction: column;
  }

  .mango-pytest-repository-page__selection {
    display: flex;
    min-height: 46px;
    flex: 0 0 auto;
    padding: 7px 12px;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    border-bottom: 1px solid var(--m-border);
    background: var(--m-surface-soft);
  }

  .mango-pytest-repository-page__selection-title,
  .mango-pytest-repository-page__selection-meta,
  .mango-pytest-repository-page__identity > div,
  .mango-pytest-repository-page__source > div,
  .mango-pytest-repository-page__sync > div {
    display: flex;
    min-width: 0;
    align-items: center;
    gap: 6px;
  }

  .mango-pytest-repository-page__selection-title strong {
    color: var(--m-text);
  }

  .mango-pytest-repository-page__selection-meta {
    color: var(--m-muted);
    font-size: 11px;

    span + span {
      padding-left: 8px;
      border-left: 1px solid var(--m-border);
    }
  }

  .mango-pytest-repository-page__table {
    min-height: 0;
    flex: 1 1 auto;

    :deep(.arco-table-cell) {
      padding: 8px 10px;
    }

    :deep(.mango-pytest-repository-page__row--selected .arco-table-td) {
      background: var(--m-primary-soft);
    }
  }

  .mango-pytest-repository-page__preview {
    display: flex;
    min-width: 0;
    min-height: 0;
    flex: 1 1 auto;
    flex-direction: column;
    overflow: hidden;
  }

  .mango-pytest-repository-page__preview-header {
    display: flex;
    min-height: 42px;
    flex: 0 0 auto;
    padding: 6px 10px;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    border-bottom: 1px solid var(--m-border);
  }

  .mango-pytest-repository-page__preview-header > div {
    display: flex;
    min-width: 0;
    align-items: center;
    gap: 8px;
  }

  .mango-pytest-repository-page__preview-header strong {
    min-width: 0;
    overflow: hidden;
    color: var(--m-text);
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-pytest-repository-page__preview-body {
    min-height: 0;
    flex: 1 1 auto;
    overflow: hidden;

    :deep(> .mango-panel-spin__content),
    :deep(.arco-spin),
    :deep(.code-editor),
    :deep(.cm-editor) {
      height: 100%;
      min-height: 0;
    }

    :deep(.cm-scroller) {
      overflow: auto;
    }
  }

  .mango-pytest-repository-page__markdown {
    height: 100%;
    padding: 20px 24px 48px;
    overflow: auto;
    background: var(--m-surface);

    :deep(.md-editor) {
      --md-color: var(--m-text-2);
      --md-bk-color: transparent;
      --md-bk-color-outstand: var(--m-surface-soft);
      --md-border-color: var(--m-border);
      background: transparent;
    }

    :deep(.md-editor-preview) {
      --md-theme-color: var(--m-text-2);
      --md-theme-heading-color: var(--m-text);
      --md-theme-border-color: var(--m-border);
      --md-theme-bg-color: transparent;
      --md-theme-bg-color-inset: var(--m-surface-soft);
      --md-theme-link-color: var(--m-primary);
      --md-theme-link-hover-color: var(--m-primary-hover);
      color: var(--m-text-2);
      font-size: 14px;
      line-height: 1.75;
      word-break: break-word;
    }

    :deep(.md-editor-preview-wrapper) {
      max-width: 980px;
      margin: 0 auto;
    }

    :deep(.md-editor-preview h1),
    :deep(.md-editor-preview h2),
    :deep(.md-editor-preview h3),
    :deep(.md-editor-preview h4) {
      color: var(--m-text);
    }

    :deep(.md-editor-preview a) {
      color: var(--m-primary);
    }

    :deep(.md-editor-preview table) {
      display: block;
      overflow-x: auto;
    }
  }

  .mango-pytest-repository-page__identity,
  .mango-pytest-repository-page__source,
  .mango-pytest-repository-page__sync {
    display: flex;
    min-width: 0;
    flex-direction: column;
    align-items: flex-start;
    gap: 5px;
  }

  .mango-pytest-repository-page__identity > strong,
  .mango-pytest-repository-page__source > span,
  .mango-pytest-repository-page__sync small {
    display: block;
    width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-pytest-repository-page__identity > div span,
  .mango-pytest-repository-page__source code,
  .mango-pytest-repository-page__sync span,
  .mango-pytest-repository-page__sync small {
    color: var(--m-muted);
    font-size: 11px;
  }

  .mango-pytest-repository-page__source code {
    padding: 1px 5px;
    border-radius: var(--m-radius-sm);
    background: var(--m-fill-2);
  }

  .mango-pytest-repository-page__assets {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 6px;

    span {
      display: flex;
      padding: 6px;
      align-items: center;
      justify-content: space-between;
      gap: 4px;
      border-radius: var(--m-radius-sm);
      color: var(--m-muted);
      background: var(--m-surface-soft);
      font-size: 11px;
    }

    strong {
      color: var(--m-text);
      font-size: 14px;
    }
  }

  .mango-pytest-repository-page__sync small {
    color: var(--m-danger);
  }
</style>
