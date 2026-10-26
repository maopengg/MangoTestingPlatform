<template>
  <TableBody plain class="mango-detail-workbench-page mango-pytest-repository-page">
    <template #header>
      <TableHeader title="Pytest 仓库管理">
        <template #header-extra>
          <a-button v-permission="'pytest.repository:create'" type="primary" size="small" @click="openEditor()">新增仓库</a-button>
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
            class="
              mango-pytest-repository-page__metric mango-pytest-repository-page__metric--status
            "
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

        <div class="mango-pytest-repository-page__workbench">
          <aside class="mango-pytest-repository-page__tree-panel">
            <PytestCaseDirectoryTree
              :data="repositoryTree"
              :loading="selectedTreeLoading"
              :selected-key="selectedTreeKey"
              expand-selected
              @select="onTreeNodeSelect"
              @directory-toggle="onTreeNodeSelect"
            />
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
                  {{ selectedRepository.active_branch || selectedRepository.default_branch }}</span
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
                <div
                  v-if="isMarkdownPreview"
                  class="mango-pytest-repository-page__markdown mango-native-scrollbar"
                >
                  <MdPreview
                    id="mango-pytest-repository-markdown-preview"
                    :model-value="filePreviewContent"
                    :theme="markdownTheme"
                    preview-theme="github"
                  />
                </div>
                <CodeEditor
                  v-else
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
              :scroll="{ x: 1130, y: 'calc(100vh - 350px)' }"
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
                >
                  <template #cell="{ record }">
                    <div
                      v-if="column.key === 'repository'"
                      class="mango-pytest-repository-page__identity"
                    >
                      <strong :title="record.name">{{ record.name }}</strong>
                      <div>
                        <a-tag size="small">{{ providerLabel(record.provider) }}</a-tag>
                        <span>{{ record.credential?.configured ? '已配置凭证' : '公开仓库' }}</span>
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
        </div>
      </div>
    </template>
  </TableBody>

  <a-modal
    v-model:visible="editorVisible"
    :title="repositoryForm.id ? '编辑 Pytest 仓库' : '新增 Pytest 仓库'"
    :width="680"
    :body-style="{ maxHeight: 'calc(100vh - 180px)', overflowY: 'auto' }"
    :ok-loading="saving"
    unmount-on-close
    @before-ok="saveRepository"
  >
    <a-form
      :model="repositoryForm"
      class="mango-pytest-repository-page__editor-form"
      layout="horizontal"
      :label-col-props="{ span: 9 }"
      :wrapper-col-props="{ span: 15 }"
    >
      <section class="mango-pytest-repository-page__form-section">
        <div class="mango-section-title">
          <div class="mango-section-title__main">
            <h2>仓库配置</h2>
          </div>
        </div>
        <a-grid :cols="2" :col-gap="16" :row-gap="0">
          <a-grid-item
            ><a-form-item label="仓库名称" required
              ><a-input v-model="repositoryForm.name" /></a-form-item
          ></a-grid-item>
          <a-grid-item
            ><a-form-item label="Git 平台" required
              ><a-select
                v-model="repositoryForm.provider"
                :options="providerOptions" /></a-form-item
          ></a-grid-item>
          <a-grid-item :span="2"
            ><a-form-item label="仓库地址" required>
              <a-input
                v-model="repositoryForm.repo_url"
                placeholder="https://git.example.com/group/project.git" /></a-form-item
          ></a-grid-item>
          <a-grid-item
            ><a-form-item label="API 地址"
              ><a-input
                v-model="repositoryForm.api_base_url"
                placeholder="留空则根据仓库地址自动填写" /></a-form-item
          ></a-grid-item>
          <a-grid-item
            ><a-form-item label="远程项目标识"
              ><a-input
                v-model="repositoryForm.remote_project"
                placeholder="group/project" /></a-form-item
          ></a-grid-item>
          <a-grid-item
            ><a-form-item label="默认分支" required
              ><a-input v-model="repositoryForm.default_branch" /></a-form-item
          ></a-grid-item>
        </a-grid>
      </section>

      <section class="mango-pytest-repository-page__form-section">
        <div class="mango-section-title">
          <div class="mango-section-title__main">
            <h2>访问凭证</h2>
            <p>
              公开仓库选择“无需认证”，也可清空认证方式。已有凭证会在保存后移除；保留认证方式时，Token / 密码留空表示不修改。推送需要写入权限。
            </p>
          </div>
        </div>
        <a-grid :cols="2" :col-gap="16" :row-gap="0">
          <a-grid-item
            ><a-form-item label="认证方式"
              ><a-select
                v-model="repositoryForm.credential_auth_type"
                allow-clear
                placeholder="无需认证（公开仓库）"
                :options="credentialTypeOptions" /></a-form-item
          ></a-grid-item>
          <a-grid-item v-if="repositoryForm.credential_auth_type === 'username_password'"
            ><a-form-item label="用户名"
              ><a-input v-model="repositoryForm.credential_username" /></a-form-item
          ></a-grid-item>
          <a-grid-item v-if="repositoryForm.credential_auth_type && repositoryForm.credential_auth_type !== 'none'"
            ><a-form-item label="Token / 密码"
              ><a-input-password
                v-model="repositoryForm.credential_secret"
                :placeholder="
                  repositoryForm.id ? '留空表示不修改' : '请输入访问密钥'
                " /></a-form-item
          ></a-grid-item>
        </a-grid>
      </section>
    </a-form>
  </a-modal>

  <a-modal
    v-model:visible="branchVisible"
    title="切换仓库分支"
    :ok-loading="branchSwitching"
    @before-ok="confirmSwitchBranch"
  >
    <a-form :model="branchForm" layout="horizontal">
      <a-form-item label="目标分支" required>
        <a-select
          v-model="branchForm.branch"
          :options="branchOptions"
          :loading="branchLoading"
          allow-search
          placeholder="请选择分支"
        />
      </a-form-item>
    </a-form>
  </a-modal>
</template>

<script lang="ts" setup>
  import { computed, onMounted, reactive, ref } from 'vue'
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
    savePytestRepository,
    switchPytestRepositoryBranch,
    testPytestRepository,
    type PytestRepository,
  } from '@/api/pytest/repository'
  import { tableColumns } from './config'
  import PytestCaseDirectoryTree, {
    type PytestDirectoryNode,
  } from '@/views/pytest/case/components/PytestCaseDirectoryTree.vue'
  import CodeEditor from '@/components/editors/CodeEditor.vue'
  import useAppConfigStore from '@/store/modules/app-config'

  const repositories = ref<PytestRepository[]>([])
  const appStore = useAppConfigStore()
  const loading = ref(false)
  const saving = ref(false)
  const actionLoading = reactive<Record<number, boolean>>({})
  const editorVisible = ref(false)
  const branchVisible = ref(false)
  const branchLoading = ref(false)
  const branchSwitching = ref(false)
  const branchOptions = ref<Array<{ label: string; value: string }>>([])
  const branchForm = reactive({ repositoryId: 0, branch: '' })
  const repositoryForm = reactive<Record<string, any>>({})
  const selectedRepositoryId = ref<number | null>(null)
  const selectedTreeKey = ref('')
  const repositoryTreeChildren = reactive<Record<number, PytestDirectoryNode[]>>({})
  const repositoryTreeStats = reactive<
    Record<number, { directory_count: number; file_count: number }>
  >({})
  const repositoryTreeLoading = reactive<Record<number, boolean>>({})
  const selectedFileNode = ref<PytestDirectoryNode | null>(null)
  const filePreviewContent = ref('')
  const filePreviewLoading = ref(false)
  let filePreviewRequestId = 0
  const providerOptions = [
    { label: 'GitLab', value: 'gitlab' },
    { label: 'GitHub', value: 'github' },
    { label: 'Gitee', value: 'gitee' },
  ]
  const publicRepositoryProviders: Record<string, string> = {
    'github.com': 'github',
    'gitlab.com': 'gitlab',
    'gitee.com': 'gitee',
  }

  function repositoryHost(repoUrl: string): string {
    const sshMatch = repoUrl.match(/^git@([^:]+):/i)
    if (sshMatch) return sshMatch[1].toLowerCase()
    try {
      return new URL(repoUrl).hostname.toLowerCase()
    } catch {
      return ''
    }
  }
  const credentialTypeOptions = [
    { label: '无需认证（公开仓库）', value: 'none' },
    { label: 'Access Token', value: 'token' },
    { label: '用户名 / 密码', value: 'username_password' },
  ]
  const selectedRepository = computed(
    () => repositories.value.find((item) => item.id === selectedRepositoryId.value) || null
  )
  const selectedTreeStats = computed(
    () =>
      repositoryTreeStats[selectedRepositoryId.value || 0] || {
        directory_count: 0,
        file_count: 0,
      }
  )
  const selectedTreeLoading = computed(() =>
    Boolean(repositoryTreeLoading[selectedRepositoryId.value || 0])
  )
  const repositoryMetrics = computed(() => ({
    repositories: repositories.value.length,
    projects: repositories.value.reduce(
      (total, item) => total + Number(item.project_count || 0),
      0
    ),
    cases: repositories.value.reduce((total, item) => total + Number(item.case_count || 0), 0),
    failed: repositories.value.filter((item) => Number(item.sync_status) === 3).length,
  }))
  const repositoryTree = computed<PytestDirectoryNode[]>(() =>
    repositories.value.map((repository) => ({
      key: repositoryRootKey(repository.id),
      title: repository.name,
      type: 'repository',
      path: '',
      breadcrumb: [repository.name],
      repository_id: repository.id,
      case_count: 0,
      count: repositoryTreeStats[repository.id]?.file_count || 0,
      children: repositoryTreeChildren[repository.id] || [],
    }))
  )
  const filePreviewLanguage = computed<'python' | 'json'>(() =>
    selectedFileNode.value?.path.toLocaleLowerCase().endsWith('.json') ? 'json' : 'python'
  )
  const isMarkdownPreview = computed(() =>
    /\.(md|markdown|mdown|mkd)$/i.test(selectedFileNode.value?.path || '')
  )
  const markdownTheme = computed<'light' | 'dark'>(() =>
    appStore.theme === 'dark' ? 'dark' : 'light'
  )
  function providerLabel(value: string) {
    return providerOptions.find((item) => item.value === value)?.label || value || '-'
  }

  function syncStatusLabel(value: number) {
    return ['空闲', '同步中', '成功', '失败'][Number(value)] || '-'
  }

  function syncStatusColor(value: number) {
    return ['gray', 'arcoblue', 'green', 'red'][Number(value)] || 'gray'
  }

  function shortCommit(value?: string | null) {
    return String(value || '').slice(0, 8)
  }

  function repositoryRootKey(repositoryId: number) {
    return `repository:${repositoryId}`
  }

  function buildRepositoryTree(
    repository: PytestRepository,
    entries: Array<{ path: string; type: 'directory' | 'file' }>
  ): PytestDirectoryNode[] {
    const roots: PytestDirectoryNode[] = []
    const directoryMap = new Map<string, PytestDirectoryNode>()

    const ensureDirectory = (path: string): PytestDirectoryNode | null => {
      if (!path) return null
      const existing = directoryMap.get(path)
      if (existing) return existing
      const parts = path.split('/').filter(Boolean)
      const parentPath = parts.slice(0, -1).join('/')
      const parent = ensureDirectory(parentPath)
      const node: PytestDirectoryNode = {
        key: `repository:${repository.id}:directory:${path}`,
        title: parts[parts.length - 1],
        type: 'directory',
        path,
        breadcrumb: [repository.name, ...parts],
        repository_id: repository.id,
        case_count: 0,
        children: [],
      }
      directoryMap.set(path, node)
      if (parent) parent.children?.push(node)
      else roots.push(node)
      return node
    }

    entries
      .filter((entry) => entry.type === 'directory')
      .sort((left, right) => left.path.localeCompare(right.path))
      .forEach((entry) => ensureDirectory(entry.path))
    entries
      .filter((entry) => entry.type === 'file')
      .sort((left, right) => left.path.localeCompare(right.path))
      .forEach((entry) => {
        const parts = entry.path.split('/').filter(Boolean)
        const parent = ensureDirectory(parts.slice(0, -1).join('/'))
        const node: PytestDirectoryNode = {
          key: `repository:${repository.id}:file:${entry.path}`,
          title: parts[parts.length - 1],
          type: 'file',
          path: entry.path,
          breadcrumb: [repository.name, ...parts],
          repository_id: repository.id,
          case_count: 0,
        }
        if (parent) parent.children?.push(node)
        else roots.push(node)
      })

    const sortAndCount = (nodes: PytestDirectoryNode[]): number => {
      nodes.sort((left, right) => {
        if (left.type !== right.type) return left.type === 'directory' ? -1 : 1
        return left.title.localeCompare(right.title)
      })
      return nodes.reduce((total, node) => {
        const fileCount = node.type === 'file' ? 1 : sortAndCount(node.children || [])
        if (node.type === 'directory') node.count = fileCount
        return total + fileCount
      }, 0)
    }
    sortAndCount(roots)
    return roots
  }

  async function loadRepositoryTree(repositoryId: number, force = false) {
    if (!force && repositoryTreeChildren[repositoryId]) return
    const repository = repositories.value.find((item) => item.id === repositoryId)
    if (!repository) return
    repositoryTreeLoading[repositoryId] = true
    try {
      const response = await getPytestRepositoryTree(repositoryId)
      const entries = Array.isArray(response.data?.entries) ? response.data.entries : []
      repositoryTreeChildren[repositoryId] = buildRepositoryTree(repository, entries)
      repositoryTreeStats[repositoryId] = {
        directory_count: Number(response.data?.directory_count || 0),
        file_count: Number(response.data?.file_count || 0),
      }
    } finally {
      repositoryTreeLoading[repositoryId] = false
    }
  }

  async function selectRepository(repositoryId: number, force = false) {
    filePreviewRequestId += 1
    selectedFileNode.value = null
    filePreviewContent.value = ''
    selectedRepositoryId.value = repositoryId
    selectedTreeKey.value = repositoryRootKey(repositoryId)
    await loadRepositoryTree(repositoryId, force)
  }

  function onTreeNodeSelect(node: PytestDirectoryNode | null) {
    if (!node) return
    selectedTreeKey.value = node.key
    if (node.type === 'file') {
      void loadFilePreview(node)
      return
    }
    filePreviewRequestId += 1
    selectedFileNode.value = null
    filePreviewContent.value = ''
    if (node.repository_id && node.repository_id !== selectedRepositoryId.value) {
      void selectRepository(node.repository_id)
    } else if (node.type === 'repository' && node.repository_id) {
      void loadRepositoryTree(node.repository_id)
    }
  }

  async function loadFilePreview(node: PytestDirectoryNode) {
    if (!node.repository_id || !node.path) return
    const requestId = ++filePreviewRequestId
    selectedFileNode.value = node
    filePreviewContent.value = ''
    filePreviewLoading.value = true
    try {
      const response = await getPytestRepositoryFile(node.repository_id, node.path)
      if (requestId !== filePreviewRequestId) return
      filePreviewContent.value = String(response.data?.content || '')
    } catch {
      if (requestId === filePreviewRequestId) filePreviewContent.value = ''
    } finally {
      if (requestId === filePreviewRequestId) filePreviewLoading.value = false
    }
  }

  function returnToRepositoryList() {
    filePreviewRequestId += 1
    selectedFileNode.value = null
    filePreviewContent.value = ''
    if (selectedRepositoryId.value) {
      selectedTreeKey.value = repositoryRootKey(selectedRepositoryId.value)
    }
  }

  function onRepositoryRowClick(record: PytestRepository) {
    void selectRepository(record.id)
  }

  function repositoryRowClass(record: PytestRepository) {
    return record.id === selectedRepositoryId.value
      ? 'mango-pytest-repository-page__row--selected'
      : ''
  }

  function repositoryActions(record: PytestRepository) {
    return [
      { permission: 'pytest.repository:edit', label: '编辑', onClick: () => openEditor(record) },
      { permission: 'pytest.repository:execute',
        label: '拉取',
        loading: actionLoading[record.id],
        onClick: () => void runAction(record, () => pullPytestRepository(record.id)),
      },
      { permission: 'pytest.repository:debug',
        label: '测试连接',
        loading: actionLoading[record.id],
        onClick: () => void runAction(record, () => testPytestRepository(record.id)),
      },
      { permission: 'pytest.repository:edit', label: '切换分支', onClick: () => void openBranch(record) },
      { permission: 'pytest.repository:delete', label: '删除', danger: true, onClick: () => removeRepository(record) },
    ]
  }

  async function loadRepositories() {
    loading.value = true
    try {
      const response = await getPytestRepositories()
      repositories.value = Array.isArray(response.data) ? response.data : []
      const selectedExists = repositories.value.some(
        (item) => item.id === selectedRepositoryId.value
      )
      if (!selectedExists) {
        selectedRepositoryId.value = repositories.value[0]?.id || null
        selectedTreeKey.value = selectedRepositoryId.value
          ? repositoryRootKey(selectedRepositoryId.value)
          : ''
      }
      if (selectedRepositoryId.value) await loadRepositoryTree(selectedRepositoryId.value)
    } finally {
      loading.value = false
    }
  }

  function resetForm(record?: PytestRepository) {
    Object.keys(repositoryForm).forEach((key) => delete repositoryForm[key])
    Object.assign(repositoryForm, {
      id: record?.id,
      name: record?.name || '',
      provider: record?.provider || 'gitlab',
      repo_url: record?.repo_url || '',
      api_base_url: record?.api_base_url || '',
      remote_project: record?.remote_project || '',
      default_branch: record?.default_branch || 'master',
      credential_auth_type: record?.credential?.auth_type || 'none',
      credential_username: record?.credential?.username || '',
      credential_secret: '',
    })
  }

  function openEditor(record?: PytestRepository) {
    resetForm(record)
    editorVisible.value = true
  }

  async function saveRepository(done: (closed: boolean) => void) {
    if (!repositoryForm.name || !repositoryForm.repo_url || !repositoryForm.default_branch) {
      Message.error('请填写仓库名称、仓库地址和默认分支')
      done(false)
      return
    }
    const actualProvider = publicRepositoryProviders[repositoryHost(repositoryForm.repo_url)]
    if (actualProvider && actualProvider !== repositoryForm.provider) {
      const platformName = providerOptions.find((item) => item.value === actualProvider)?.label
      Message.error(`仓库地址属于 ${platformName}，请将 Git 平台改为 ${platformName}`)
      done(false)
      return
    }
    saving.value = true
    try {
      const response = await savePytestRepository({
        ...repositoryForm,
        credential_auth_type: repositoryForm.credential_auth_type || 'none',
        credential_username: !repositoryForm.credential_auth_type || repositoryForm.credential_auth_type === 'none'
          ? '' : repositoryForm.credential_username,
        credential_secret: !repositoryForm.credential_auth_type || repositoryForm.credential_auth_type === 'none'
          ? '' : repositoryForm.credential_secret,
      })
      Message.success(response.msg)
      await loadRepositories()
      done(true)
    } catch {
      done(false)
    } finally {
      saving.value = false
    }
  }

  async function runAction(record: PytestRepository, action: () => Promise<any>) {
    actionLoading[record.id] = true
    try {
      const response = await action()
      Message.success(response.msg)
      await loadRepositories()
      await loadRepositoryTree(record.id, true)
    } finally {
      actionLoading[record.id] = false
    }
  }

  async function openBranch(record: PytestRepository) {
    branchForm.repositoryId = record.id
    branchForm.branch = record.active_branch || record.default_branch || ''
    branchVisible.value = true
    branchLoading.value = true
    try {
      const response = await getPytestRepositoryBranches(record.id)
      branchOptions.value = (response.data || []).map((item: any) => ({
        label: item.default ? `${item.name}（默认）` : item.name,
        value: item.name,
      }))
    } finally {
      branchLoading.value = false
    }
  }

  async function confirmSwitchBranch(done: (closed: boolean) => void) {
    if (!branchForm.branch) {
      Message.error('请选择目标分支')
      done(false)
      return
    }
    branchSwitching.value = true
    try {
      const response = await switchPytestRepositoryBranch(
        branchForm.repositoryId,
        branchForm.branch
      )
      Message.success(response.msg)
      await loadRepositories()
      done(true)
    } catch {
      done(false)
    } finally {
      branchSwitching.value = false
    }
  }

  function removeRepository(record: PytestRepository) {
    Modal.confirm({
      title: '删除 Pytest 仓库',
      content: '只有未绑定 Pytest 项目的仓库才能删除。确定继续吗？',
      okButtonProps: { status: 'danger' },
      onBeforeOk: async () => {
        const response = await deletePytestRepository(record.id)
        Message.success(response.msg)
        await loadRepositories()
        return true
      },
    })
  }

  onMounted(loadRepositories)
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

  .mango-pytest-repository-page__workbench {
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

  .mango-pytest-repository-page__editor-form {
    display: flex;
    flex-direction: column;
  }

  .mango-pytest-repository-page__form-section {
    padding: 0 0 2px;
  }

  .mango-pytest-repository-page__form-section + .mango-pytest-repository-page__form-section {
    margin-top: 8px;
    padding-top: 12px;
    border-top: 1px solid var(--m-border);
  }

  .mango-pytest-repository-page__form-section :deep(.arco-form-item) {
    margin-bottom: 8px;
  }

  .mango-pytest-repository-page__form-section :deep(.arco-form-item-label-col.arco-col) {
    width: 112px;
    max-width: 112px;
    flex: 0 0 112px;
  }

  .mango-pytest-repository-page__form-section :deep(.arco-form-item-label) {
    white-space: nowrap;
  }

  .mango-pytest-repository-page__form-section :deep(.arco-form-item-wrapper-col.arco-col) {
    width: auto;
    max-width: none;
    flex: 1 1 0;
  }

  .mango-pytest-repository-page__form-section :deep(.arco-grid-item:last-child .arco-form-item) {
    margin-bottom: 0;
  }
</style>
