<template>
  <TableBody ref="tableBody" plain class="mango-detail-workbench-page">
    <template #header>
      <TableHeader title="项目绑定">
        <template #header-extra>
          <a-button v-permission="'pytest.product:create'" size="small" type="primary" :loading="repositoryLoading" @click="onAdd">
            导入项目
          </a-button>
        </template>
      </TableHeader>
    </template>

    <template #default>
      <ProjectProductNavigationWorkbench
        contained-body
        :model-value="selectedProjectProduct"
        :show-search="false"
        emit-initial-filter
        @filter-change="onNavigationFilterChange"
      >
        <div class="mango-pytest-product-page">
          <div class="mango-pytest-product-page__overview">
            <div class="mango-pytest-product-page__metric">
              <span class="mango-pytest-product-page__metric-label">项目绑定</span>
              <div class="mango-pytest-product-page__metric-value">
                <strong>{{ bindingMetrics.bindings }}</strong
                ><small>个</small>
              </div>
              <span class="mango-pytest-product-page__metric-note">已关联项目产品</span>
            </div>
            <div class="mango-pytest-product-page__metric">
              <span class="mango-pytest-product-page__metric-label">涉及仓库</span>
              <div class="mango-pytest-product-page__metric-value">
                <strong>{{ bindingMetrics.repositories }}</strong
                ><small>个</small>
              </div>
              <span class="mango-pytest-product-page__metric-note">当前引用仓库</span>
            </div>
            <div class="mango-pytest-product-page__metric">
              <span class="mango-pytest-product-page__metric-label">Pytest Case</span>
              <div class="mango-pytest-product-page__metric-value">
                <strong>{{ bindingMetrics.cases }}</strong
                ><small>条</small>
              </div>
              <span class="mango-pytest-product-page__metric-note">已同步测试用例</span>
            </div>
            <div class="mango-pytest-product-page__metric">
              <span class="mango-pytest-product-page__metric-label">测试目录</span>
              <div class="mango-pytest-product-page__metric-value">
                <strong>{{ bindingMetrics.directories }}</strong
                ><small>个</small>
              </div>
              <span class="mango-pytest-product-page__metric-note">已配置执行目录</span>
            </div>
          </div>

          <div class="mango-pytest-product-page__table-region">
            <a-table
              class="mango-native-scroll-table mango-pytest-product-page__table"
              :scroll="{ x: 1090, y: '100%' }"
              :bordered="false"
              :columns="tableColumns"
              :data="table.dataList"
              :loading="table.tableLoading.value"
              :pagination="false"
              :row-class="bindingRowClass"
              @row-click="selectBinding"
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
                  <template v-else-if="item.key === 'binding'" #cell="{ record }">
                    <div class="mango-pytest-product-page__binding-cell">
                      <strong :title="record.name">{{ record.name || '-' }}</strong>
                      <span :title="record.file_name">{{ record.file_name || '仓库根目录' }}</span>
                    </div>
                  </template>
                  <template v-else-if="item.key === 'auto_type'" #cell="{ record }">
                    <a-tag :color="enumStore.colors[record?.auto_type]" size="small">
                      {{ enumStore.test_case_type[record?.auto_type]?.title || '-' }}
                    </a-tag>
                  </template>
                  <template v-else-if="item.key === 'project_product'" #cell="{ record }">
                    <span :title="formatProjectProductPath(record.project_product)">
                      {{ formatProjectProductPath(record.project_product) }}
                    </span>
                  </template>
                  <template v-else-if="item.key === 'repository'" #cell="{ record }">
                    <div class="mango-pytest-product-page__repository-cell">
                      <strong>{{ record.repository?.name || '-' }}</strong>
                      <a-tag size="small">
                        {{
                          record.repository?.active_branch ||
                          record.repository?.default_branch ||
                          '-'
                        }}
                      </a-tag>
                    </div>
                  </template>
                  <template v-else-if="item.key === 'test_dir'" #cell="{ record }">
                    <div class="mango-pytest-product-page__directory-cell">
                      <a-tag
                        v-for="directory in testDirectories(record).slice(0, 2)"
                        :key="directory"
                        size="small"
                      >
                        {{ directory === '.' ? '项目根目录' : directory }}
                      </a-tag>
                      <a-tag v-if="testDirectories(record).length > 2" size="small">
                        +{{ testDirectories(record).length - 2 }}
                      </a-tag>
                      <span v-if="!testDirectories(record).length">-</span>
                    </div>
                  </template>
                  <template v-else-if="item.key === 'actions'" #cell="{ record }">
                    <MangoTableActions
                      :actions="[
                        { permission: 'pytest.product:edit', label: '编辑', onClick: () => onUpdate(record) },
                        { permission: 'pytest.product:delete', label: '删除', danger: true, onClick: () => onDelete(record) },
                      ]"
                    />
                  </template>
                </a-table-column>
              </template>
              <template #empty>
                <div class="mango-empty-state">当前范围暂无项目绑定</div>
              </template>
            </a-table>
          </div>

          <section v-if="selectedBinding" class="mango-pytest-product-page__detail">
            <header class="mango-pytest-product-page__detail-header">
              <div>
                <span>绑定详情</span>
                <strong>{{ selectedBinding.name }}</strong>
              </div>
              <div>
                <a-tag :color="enumStore.colors[selectedBinding.auto_type]" size="small">
                  {{ enumStore.test_case_type[selectedBinding.auto_type]?.title || '-' }}
                </a-tag>
                <span>{{ formatProjectProductPath(selectedBinding.project_product) }}</span>
              </div>
            </header>

            <div class="mango-pytest-product-page__flow">
              <div class="mango-pytest-product-page__flow-node">
                <span>Git 仓库</span>
                <strong>{{ selectedBinding.repository?.name || '-' }}</strong>
                <small>{{
                  selectedBinding.repository?.active_branch ||
                  selectedBinding.repository?.default_branch ||
                  '未记录分支'
                }}</small>
              </div>
              <i>→</i>
              <div class="mango-pytest-product-page__flow-node">
                <span>项目目录</span>
                <strong :title="selectedBinding.file_name">{{
                  selectedBinding.file_name || '仓库根目录'
                }}</strong>
                <small>Pytest 项目入口</small>
              </div>
              <i>→</i>
              <div class="mango-pytest-product-page__flow-node">
                <span>测试目录</span>
                <strong>{{ testDirectories(selectedBinding).length }} 个</strong>
                <small :title="testDirectories(selectedBinding).join('、')">
                  {{
                    testDirectories(selectedBinding)
                      .map((item) => (item === '.' ? '项目根目录' : item))
                      .join('、') || '未配置'
                  }}
                </small>
              </div>
              <i>→</i>
              <div class="mango-pytest-product-page__flow-node">
                <span>配置文件</span>
                <strong :title="selectedBinding.pytest_config_path">
                  {{ selectedBinding.pytest_config_path || '自动发现' }}
                </strong>
                <small>{{
                  selectedBinding.pytest_config_path ? '执行时通过 -c 指定' : '使用 Pytest 默认规则'
                }}</small>
              </div>
            </div>

            <div class="mango-pytest-product-page__detail-meta">
              <div
                ><span>Case 数量</span><strong>{{ selectedBinding.case_count || 0 }}</strong></div
              >
              <div
                ><span>初始化文件</span
                ><strong :title="selectedBinding.init_file">{{
                  selectedBinding.init_file || '未配置'
                }}</strong></div
              >
              <div
                ><span>更新人</span
                ><strong>{{
                  selectedBinding.update_user?.name || selectedBinding.update_user?.username || '-'
                }}</strong></div
              >
              <div
                ><span>更新时间</span><strong>{{ selectedBinding.update_time || '-' }}</strong></div
              >
            </div>
          </section>
          <div
            v-else-if="!table.tableLoading.value"
            class="mango-pytest-product-page__detail-empty"
          >
            选择一条项目绑定后查看目录链路和配置详情
          </div>
        </div>
        <template #footer>
          <TableFooter :pagination="pagination" />
        </template>
      </ProjectProductNavigationWorkbench>
    </template>
  </TableBody>

  <ModalDialog ref="modalDialogRef" :title="data.actionTitle" @confirm="onDataForm">
    <template #content>
      <a-form :model="formModel">
        <a-form-item
          v-for="item of formItems"
          :key="item.key"
          :class="[item.required ? 'mango-form-item__require' : 'mango-form-item__no_require']"
          :label="item.label"
        >
          <template v-if="item.type === 'input'">
            <a-input v-model="item.value" :placeholder="item.placeholder" />
          </template>
          <template v-else-if="item.type === 'textarea'">
            <a-textarea
              v-model="item.value"
              :auto-size="{ minRows: 3, maxRows: 5 }"
              :placeholder="item.placeholder"
            />
          </template>
          <template v-else-if="item.type === 'cascader' && item.key === 'project_product'">
            <a-cascader
              v-model="item.value"
              :options="projectInfo.projectProduct"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
            />
          </template>
          <template v-else-if="item.type === 'repository-directory'">
            <a-cascader
              v-model="item.value"
              :disabled="!data.isAdd"
              :loading="repositoryDirectoryLoading"
              :options="repositoryDirectoryOptions"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              check-strictly
              @change="onProjectDirectoryChange"
            />
          </template>
          <template v-else-if="item.type === 'pytest-repository'">
            <a-select
              v-model="item.value"
              :disabled="!data.isAdd"
              :loading="repositoryLoading"
              :options="repositoryOptions"
              :placeholder="item.placeholder"
              allow-search
              @change="onImportRepositoryChange"
            />
          </template>
          <template v-else-if="item.type === 'cascader' && item.key === 'test_dir'">
            <a-cascader
              v-model="item.value"
              :loading="testDirectoryLoading"
              :options="testDirectoryOptions"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              check-strictly
              multiple
              :max-tag-count="2"
            />
          </template>

          <template v-else-if="item.type === 'select' && item.key === 'auto_type'">
            <a-select
              v-model="item.value"
              :field-names="fieldNames"
              :options="enumStore.test_case_type"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              value-key="key"
            />
          </template>
        </a-form-item>
      </a-form>
    </template>
  </ModalDialog>
</template>

<script lang="ts" setup>
  import { formatProjectProductPath } from '@/utils/business-format'
  import { usePagination, useTable } from '@/hooks/table'
  import { ModalDialogType } from '@/types/components'
  import { Message, Modal } from '@arco-design/web-vue'
  import { computed, nextTick, onMounted, reactive, ref } from 'vue'
  import { getFormItems } from '@/utils/datacleaning'
  import { fieldNames } from '@/setting'
  import { formItems, tableColumns } from './config'
  import { useProject } from '@/store/modules/get-project'
  import { useEnum } from '@/store/modules/get-enum'
  import {
    deletePytestProduct,
    getPytestProduct,
    getPytestProductTestDirectories,
    postPytestProductImport,
    putPytestProduct,
  } from '@/api/pytest/product'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import { useLatestRequest } from '@/hooks/use-latest-request'
  import {
    getPytestRepositories,
    getPytestRepositoryDirectories,
    type PytestRepository,
  } from '@/api/pytest/repository'

  const projectInfo = useProject()
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const pagination = usePagination(doRefresh, () => table.tableLoading)
  const table = useTable()
  const { beginRequest, isLatestRequest } = useLatestRequest()
  const selectedProjectProduct = ref<string | number | null>(null)
  const formModel = ref({})
  const enumStore = useEnum()
  const testDirectoryLoading = ref(false)
  interface TestDirectoryOption {
    label: string
    value: string
    children?: TestDirectoryOption[]
    fileCount?: number
    stale?: boolean
  }
  const testDirectoryOptions = ref<TestDirectoryOption[]>([])
  const repositoryDirectoryLoading = ref(false)
  const repositoryDirectoryOptions = ref<TestDirectoryOption[]>([])
  const repositories = ref<PytestRepository[]>([])
  const repositoryLoading = ref(false)
  const repositoryOptions = computed(() =>
    repositories.value.map((item) => ({
      label: item.name,
      value: item.id,
    }))
  )
  const selectedBinding = ref<any | null>(null)
  const bindingMetrics = computed(() => {
    const rows = Array.isArray(table.dataList) ? table.dataList : []
    return {
      bindings: pagination.pageCount || rows.length,
      repositories: new Set(rows.map((item: any) => item.repository?.id).filter(Boolean)).size,
      cases: rows.reduce((total: number, item: any) => total + Number(item.case_count || 0), 0),
      directories: rows.reduce(
        (total: number, item: any) => total + testDirectories(item).length,
        0
      ),
    }
  })

  const data: any = reactive({
    isAdd: false,
    updateId: 0,
    actionTitle: '新增',
  })

  function testDirectories(record: any): string[] {
    if (!Array.isArray(record?.test_dir)) return []
    return record.test_dir.map((item: unknown) => String(item)).filter(Boolean)
  }

  function selectBinding(record: any) {
    selectedBinding.value = record
  }

  function bindingRowClass(record: any) {
    return record.id === selectedBinding.value?.id ? 'mango-pytest-product-page__row--selected' : ''
  }

  function onDelete(record: any) {
    Modal.confirm({
      title: '提示',
      content: '该删除只会删除数据库数据，不会影响git文件！是否要删除此数据？',
      cancelText: '取消',
      okText: '删除',
      onBeforeOk: () => {
        return deletePytestProduct(record.id)
          .then((res) => {
            Message.success(res.msg)
          })
          .catch(() => undefined)
          .finally(() => {
            doRefresh()
            projectInfo.projectPytestName()
          })
      },
    })
  }

  function onDataForm() {
    if (formItems.every((it) => (it.validator ? it.validator() : true))) {
      let value = getFormItems(formItems)
      if (data.isAdd) {
        postPytestProductImport(value)
          .then((res) => {
            modalDialogRef.value?.toggle()
            Message.success(res.msg)
            doRefresh()
            projectInfo.projectPytestName()
          })
          .catch(() => undefined)
          .finally(() => {
            modalDialogRef.value?.setConfirmLoading(false)
          })
      } else {
        value['id'] = data.updateId
        putPytestProduct(value)
          .then((res) => {
            modalDialogRef.value?.toggle()
            Message.success(res.msg)
            doRefresh()
            projectInfo.projectPytestName()
          })
          .catch(() => undefined)
          .finally(() => {
            modalDialogRef.value?.setConfirmLoading(false)
          })
      }
    } else {
      modalDialogRef.value?.setConfirmLoading(false)
    }
  }

  function buildTestDirectoryTree(discoveredOptions: any[], configuredDirectories: string[]) {
    const topLevelOptions: TestDirectoryOption[] = []
    const optionMap = new Map<string, TestDirectoryOption>()
    const discoveredValues = new Set(discoveredOptions.map((option: any) => option.value))

    function ensureDirectoryPath(directory: string, stale = false) {
      let children = topLevelOptions
      let currentPath = ''
      directory
        .split('/')
        .filter(Boolean)
        .forEach((segment) => {
          currentPath = currentPath ? `${currentPath}/${segment}` : segment
          let node = optionMap.get(currentPath)
          if (!node) {
            node = { label: segment, value: currentPath, children: [], fileCount: 0 }
            optionMap.set(currentPath, node)
            children.push(node)
          }
          if (stale && currentPath === directory) node.stale = true
          children = node.children || []
        })
    }

    discoveredOptions
      .filter((option: any) => option.value !== '.')
      .forEach((option: any) => {
        const directory = String(option.value)
        ensureDirectoryPath(directory)
        const fileCount = Number(option.file_count) || 0
        let currentPath = ''
        directory
          .split('/')
          .filter(Boolean)
          .forEach((segment) => {
            currentPath = currentPath ? `${currentPath}/${segment}` : segment
            const node = optionMap.get(currentPath)
            if (node) node.fileCount = (node.fileCount || 0) + fileCount
          })
      })

    configuredDirectories
      .filter(
        (directory) =>
          directory !== '.' &&
          !discoveredValues.has(directory) &&
          (optionMap.get(directory)?.fileCount || 0) === 0
      )
      .forEach((directory) => ensureDirectoryPath(directory, true))

    function finishLabels(options: TestDirectoryOption[]) {
      options.sort((left, right) => left.value.localeCompare(right.value))
      options.forEach((option) => {
        const name = option.value.split('/').at(-1) || option.value
        option.label = option.stale ? `${name}（当前配置，当前分支未发现）` : name
        if (option.children?.length) {
          finishLabels(option.children)
        } else {
          delete option.children
        }
      })
    }
    finishLabels(topLevelOptions)

    const totalFileCount = discoveredOptions.reduce(
      (total: number, option: any) => total + (Number(option.file_count) || 0),
      0
    )
    const showProjectRoot = totalFileCount > 0 || configuredDirectories.includes('.')
    return [...(showProjectRoot ? [{ label: '项目根目录', value: '.' }] : []), ...topLevelOptions]
  }

  function buildRepositoryDirectoryTree(options: any[]) {
    const roots: TestDirectoryOption[] = []
    const optionMap = new Map<string, TestDirectoryOption>()
    options.forEach((option: any) => {
      let children = roots
      let currentPath = ''
      String(option.value)
        .split('/')
        .filter(Boolean)
        .forEach((segment) => {
          currentPath = currentPath ? `${currentPath}/${segment}` : segment
          let node = optionMap.get(currentPath)
          if (!node) {
            node = { label: segment, value: currentPath, children: [] }
            optionMap.set(currentPath, node)
            children.push(node)
          }
          children = node.children || []
        })
    })
    const finish = (nodes: TestDirectoryOption[]) => {
      nodes.sort((left, right) => left.value.localeCompare(right.value))
      nodes.forEach((node) => {
        if (node.children?.length) finish(node.children)
        else delete node.children
      })
    }
    finish(roots)
    return roots
  }

  async function loadRepositoryDirectoryOptions() {
    repositoryDirectoryLoading.value = true
    try {
      const repositoryItem = formItems.find((item) => item.key === 'repository')
      const repositoryId = Number(repositoryItem?.value || 0)
      if (!repositoryId) {
        repositoryDirectoryOptions.value = []
        return
      }
      const res = await getPytestRepositoryDirectories(repositoryId)
      repositoryDirectoryOptions.value = buildRepositoryDirectoryTree(
        Array.isArray(res.data) ? res.data : []
      )
    } finally {
      repositoryDirectoryLoading.value = false
    }
  }

  async function loadTestDirectoryOptions(item: any) {
    const configuredDirectories = Array.isArray(item.test_dir) ? item.test_dir : []
    testDirectoryOptions.value = buildTestDirectoryTree([], configuredDirectories)
    testDirectoryLoading.value = true
    try {
      const repositoryItem = formItems.find((formItem) => formItem.key === 'repository')
      const repositoryId =
        Number(item.repository?.id || item.repository || repositoryItem?.value || 0) || undefined
      const res = await getPytestProductTestDirectories(item.id, item.file_name, repositoryId)
      const discoveredOptions = Array.isArray(res.data) ? res.data : []
      testDirectoryOptions.value = buildTestDirectoryTree(discoveredOptions, configuredDirectories)
    } catch {
      // 请求失败时保留已有配置，避免弹窗中已保存的目录不可见。
    } finally {
      testDirectoryLoading.value = false
    }
  }

  async function onProjectDirectoryChange(projectPath: string) {
    if (!data.isAdd || !projectPath) return
    const nameItem = formItems.find((item) => item.key === 'name')
    const testDirItem = formItems.find((item) => item.key === 'test_dir')
    if (nameItem) nameItem.value = projectPath.split('/').at(-1) || projectPath
    if (testDirItem) testDirItem.value = []
    await loadTestDirectoryOptions({ file_name: projectPath, test_dir: [] })
  }

  async function onImportRepositoryChange(repositoryId: number) {
    const fileNameItem = formItems.find((item) => item.key === 'file_name')
    const testDirItem = formItems.find((item) => item.key === 'test_dir')
    if (fileNameItem) fileNameItem.value = ''
    if (testDirItem) testDirItem.value = []
    repositoryDirectoryOptions.value = []
    if (repositoryId) await loadRepositoryDirectoryOptions()
  }

  async function loadRepositories() {
    repositoryLoading.value = true
    try {
      const res = await getPytestRepositories()
      repositories.value = Array.isArray(res.data) ? res.data : []
    } finally {
      repositoryLoading.value = false
    }
  }

  async function onAdd() {
    data.actionTitle = '导入项目'
    data.isAdd = true
    data.updateId = 0
    formItems.forEach((item) => {
      item.value = item.multiple || item.key === 'test_dir' ? [] : ''
    })
    const repositoryItem = formItems.find((item) => item.key === 'repository')
    if (repositoryItem) repositoryItem.value = repositories.value[0]?.id || ''
    testDirectoryOptions.value = []
    modalDialogRef.value?.toggle()
    await loadRepositoryDirectoryOptions()
  }

  function onUpdate(item: any) {
    data.actionTitle = '编辑'
    data.isAdd = false
    data.updateId = item.id
    modalDialogRef.value?.toggle()
    nextTick(async () => {
      formItems.forEach((it) => {
        const propName = item[it.key]
        if (Array.isArray(propName)) {
          it.value = propName
        } else if (typeof propName === 'object' && propName !== null) {
          it.value = propName.id
        } else {
          it.value = propName
        }
      })
      await loadRepositoryDirectoryOptions()
      await loadTestDirectoryOptions(item)
    })
  }

  function onNavigationFilterChange(filter: { projectProduct: string | number | null }) {
    selectedProjectProduct.value = filter.projectProduct
    pagination.page = 1
    selectedBinding.value = null
    doRefresh()
  }

  function doRefresh() {
    const requestId = beginRequest()
    table.tableLoading.value = true
    const value: Record<string, any> = {}
    if (selectedProjectProduct.value !== null && selectedProjectProduct.value !== '') {
      value['project_product'] = selectedProjectProduct.value
    }
    value['page'] = pagination.page
    value['pageSize'] = pagination.pageSize
    getPytestProduct(value)
      .then((res) => {
        if (!isLatestRequest(requestId)) return
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
        const currentId = selectedBinding.value?.id
        selectedBinding.value =
          table.dataList.find((item: any) => item.id === currentId) || table.dataList[0] || null
      })
      .catch(() => undefined)
      .finally(() => {
        if (isLatestRequest(requestId)) table.tableLoading.value = false
      })
  }

  onMounted(() => {
    nextTick(async () => {
      await loadRepositories()
    })
  })
</script>

<style lang="less" scoped>
  .mango-pytest-product-page {
    display: flex;
    height: 100%;
    min-height: 0;
    flex-direction: column;
    gap: var(--m-page-gap);
    padding: var(--m-page-gap);
    overflow: hidden;
  }

  .mango-pytest-product-page__overview {
    display: grid;
    flex: 0 0 auto;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: var(--m-page-gap);
  }

  .mango-pytest-product-page__metric {
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

  .mango-pytest-product-page__metric-label {
    align-self: start;
    color: var(--m-text-2);
    font-size: 12px;
    font-weight: 500;
  }

  .mango-pytest-product-page__metric-value {
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

  .mango-pytest-product-page__metric-note {
    overflow: hidden;
    color: var(--m-muted);
    font-size: 11px;
    line-height: 16px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-pytest-product-page__table-region {
    min-height: 190px;
    flex: 0 1 46%;
    overflow: hidden;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
  }

  .mango-pytest-product-page__table {
    height: 100%;
  }

  .mango-pytest-product-page__binding-cell,
  .mango-pytest-product-page__repository-cell {
    display: flex;
    min-width: 0;
    flex-direction: column;
    align-items: flex-start;
    gap: 3px;

    strong,
    span {
      max-width: 100%;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    span {
      color: var(--m-muted);
      font-size: 12px;
    }
  }

  .mango-pytest-product-page__directory-cell {
    display: flex;
    min-width: 0;
    align-items: center;
    gap: 4px;
    overflow: hidden;
  }

  :deep(.mango-pytest-product-page__row--selected td) {
    background: var(--m-primary-soft) !important;
  }

  .mango-pytest-product-page__detail,
  .mango-pytest-product-page__detail-empty {
    min-height: 210px;
    flex: 1 1 auto;
    overflow: auto;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
  }

  .mango-pytest-product-page__detail {
    display: flex;
    flex-direction: column;
  }

  .mango-pytest-product-page__detail-empty {
    display: grid;
    place-items: center;
    color: var(--m-muted);
  }

  .mango-pytest-product-page__detail-header {
    display: flex;
    min-height: 46px;
    flex: 0 0 auto;
    padding: 8px 12px;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    border-bottom: 1px solid var(--m-border);
    background: var(--m-surface-soft);

    > div {
      display: flex;
      min-width: 0;
      align-items: center;
      gap: 8px;
    }

    span {
      color: var(--m-muted);
      font-size: 12px;
    }

    strong {
      overflow: hidden;
      color: var(--m-text);
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .mango-pytest-product-page__flow {
    display: grid;
    padding: 14px;
    align-items: stretch;
    grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr) auto minmax(0, 1fr) auto minmax(
        0,
        1fr
      );
    gap: 8px;

    > i {
      align-self: center;
      color: var(--m-muted);
      font-style: normal;
      font-size: 18px;
    }
  }

  .mango-pytest-product-page__flow-node {
    display: flex;
    min-width: 0;
    min-height: 84px;
    padding: 10px 12px;
    flex-direction: column;
    justify-content: center;
    gap: 4px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface-soft);

    span,
    small {
      color: var(--m-muted);
      font-size: 12px;
    }

    strong,
    small {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    strong {
      color: var(--m-text);
      font-size: 14px;
    }
  }

  .mango-pytest-product-page__detail-meta {
    display: grid;
    padding: 0 14px 14px;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 8px;

    > div {
      display: flex;
      min-width: 0;
      padding: 8px 10px;
      align-items: center;
      gap: 8px;
      border-top: 1px solid var(--m-border);
    }

    span {
      flex: 0 0 auto;
      color: var(--m-muted);
      font-size: 12px;
    }

    strong {
      min-width: 0;
      overflow: hidden;
      color: var(--m-text);
      font-size: 12px;
      font-weight: 500;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  @media (max-width: 1200px) {
    .mango-pytest-product-page__flow {
      grid-template-columns: repeat(2, minmax(0, 1fr));

      > i {
        display: none;
      }
    }

    .mango-pytest-product-page__detail-meta {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }
</style>
