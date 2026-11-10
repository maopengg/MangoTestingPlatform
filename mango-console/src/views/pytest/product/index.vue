<template>
  <TableBody plain class="mango-detail-workbench-page">
    <template #header>
      <TableHeader title="项目绑定">
        <template #header-extra>
          <a-button size="small" type="primary" @click="onAdd"> 导入项目 </a-button>
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
              :scroll="{ x: tableScroll.x, y: tableScroll.y }"
              :bordered="false"
              :columns="tableColumns"
              :data="rows"
              :loading="tableLoading"
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
                        {
                          label: '编辑',
                          disabled: deletingIds.includes(record.id),
                          onClick: () => onUpdate(record),
                        },
                        {
                          label: '删除',
                          danger: true,
                          loading: deletingIds.includes(record.id),
                          onClick: () => onDelete(record),
                        },
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
          <div v-else-if="!tableLoading" class="mango-pytest-product-page__detail-empty">
            选择一条项目绑定后查看目录链路和配置详情
          </div>
        </div>
        <template #footer>
          <TableFooter :pagination="pagination" />
        </template>
      </ProjectProductNavigationWorkbench>
    </template>
  </TableBody>

  <PytestBindingEditor ref="editor" @saved="onSaved" />
</template>

<script lang="ts" setup>
import { reportLoadError } from '@/utils/load-error'

  import { formatProjectProductPath } from '@/utils/business-format'
  import { usePagination } from '@/hooks/table'
  import { Message, Modal } from '@arco-design/web-vue'
  import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from 'vue'
  import { useRoute } from 'vue-router'
  import { tableColumns, tableScroll } from './config'
  import { useProject } from '@/store/modules/get-project'
  import { useEnum } from '@/store/modules/get-enum'
  import useUserStore from '@/store/modules/user'
  import { deletePytestProduct, getPytestProduct } from '@/api/pytest/product'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import PytestBindingEditor from './components/PytestBindingEditor.vue'
  import { checkBindingResponse, readBindingList } from './binding'
  import type { BindingRecord } from './binding'

  const projectInfo = useProject(),
    enumStore = useEnum(),
    user = useUserStore(),
    route = useRoute()
  const editor = ref<InstanceType<typeof PytestBindingEditor> | null>(null)
  const tableLoading = ref(false),
    listFailed = ref(false)
  const rows = ref<BindingRecord[]>([]),
    selectedId = ref<number | null>(null)
  const selectedProjectProduct = ref<string | number | null>(null)
  const pagination = usePagination(doRefresh, tableLoading)
  const deletingIds = ref<number[]>([])
  const selectedBinding = computed(
    () => rows.value.find((row) => row.id === selectedId.value) ?? null
  )
  const bindingMetrics = computed(() => ({
    bindings: pagination.pageCount,
    repositories: new Set(rows.value.flatMap((row) => (row.repository ? [row.repository.id] : [])))
      .size,
    cases: rows.value.reduce((total, row) => total + row.case_count, 0),
    directories: rows.value.reduce((total, row) => total + row.test_dir.length, 0),
  }))
  let version = 0,
    request = 0,
    confirmationVersion = 0,
    active = true,
    disposed = false
  let pending: { key: string; promise: Promise<void> } | null = null
  let confirmation: ReturnType<typeof Modal.confirm> | null = null
  const available = () =>
    !disposed && active && (typeof document === 'undefined' || !document.hidden)
  const current = (context: number) => available() && context === version
  function testDirectories(record: BindingRecord): string[] {
    return record.test_dir
  }
  function selectBinding(record: BindingRecord): void {
    if (available() && rows.value.some((row) => row.id === record.id)) selectedId.value = record.id
  }
  function bindingRowClass(record: BindingRecord): string {
    return record.id === selectedId.value ? 'mango-pytest-product-page__row--selected' : ''
  }
  function onAdd(): void {
    if (available()) editor.value?.open()
  }
  function onUpdate(record: BindingRecord): void {
    const row = rows.value.find((row) => row.id === record.id)
    if (available() && row && !deletingIds.value.includes(row.id)) editor.value?.open(row)
  }
  function invalidate(clear = false): void {
    version++
    request++
    confirmationVersion++
    pending = null
    tableLoading.value = false
    confirmation?.close()
    confirmation = null
    editor.value?.close()
    if (clear) {
      rows.value = []
      selectedId.value = null
      pagination.pageCount = 0
      listFailed.value = false
    }
  }
  function doRefresh(): Promise<void> {
    if (!available()) return Promise.resolve()
    const query = {
      page: pagination.page,
      pageSize: pagination.pageSize,
      ...(selectedProjectProduct.value !== null && selectedProjectProduct.value !== ''
        ? { project_product: selectedProjectProduct.value }
        : {}),
    }
    const key = JSON.stringify([version, query])
    if (pending?.key === key) return pending.promise
    const context = version,
      read = ++request
    tableLoading.value = true
    listFailed.value = false
    const promise = (async () => {
      try {
        const result = readBindingList(await getPytestProduct(query))
        if (!current(context) || read !== request) return
        rows.value = result.rows
        pagination.setTotalSize(result.total)
        selectedId.value =
          rows.value.find((row) => row.id === selectedId.value)?.id ?? rows.value[0]?.id ?? null
      } catch (loadFailure0) {
        if (current(context) && read === request) (reportLoadError(loadFailure0, "加载失败，请重试", false), listFailed.value = true)
      } finally {
        if (current(context) && read === request) {
          tableLoading.value = false
          pending = null
        }
      }
    })()
    pending = { key, promise }
    return promise
  }
  function onNavigationFilterChange(filter: { projectProduct: string | number | null }): void {
    if (!available()) return
    invalidate(true)
    selectedProjectProduct.value = filter.projectProduct
    pagination.page = 1
    void doRefresh()
  }
  async function onSaved(): Promise<void> {
    if (!available()) return
    invalidate()
    await Promise.allSettled([doRefresh(), projectInfo.projectPytestName()])
  }
  function onDelete(record: BindingRecord): void {
    if (
      !available() ||
      !rows.value.some((row) => row.id === record.id) ||
      deletingIds.value.includes(record.id)
    )
      return
    confirmation?.close()
    const context = version,
      window = ++confirmationVersion,
      id = record.id
    const confirmationCurrent = () => current(context) && window === confirmationVersion
    confirmation = Modal.confirm({
      title: '删除项目绑定',
      content: '该删除只会删除数据库数据，不会影响 Git 文件！是否删除此数据？',
      cancelText: '取消',
      okText: '删除',
      onCancel: () => {
        if (window === confirmationVersion) {
          confirmationVersion++
          confirmation = null
        }
      },
      onBeforeOk: async () => {
        if (
          !confirmationCurrent() ||
          deletingIds.value.includes(id) ||
          !rows.value.some((row) => row.id === id)
        )
          return false
        deletingIds.value = [...deletingIds.value, id]
        try {
          checkBindingResponse(await deletePytestProduct(id))
          if (!confirmationCurrent()) return false
          Message.success('删除成功')
          // 已发出的列表请求可能仍包含被删除记录，必须先失效。
          request++
          pending = null
          if (rows.value.length === 1 && pagination.page > 1) pagination.page--
          await Promise.allSettled([doRefresh(), projectInfo.projectPytestName()])
          return confirmationCurrent()
        } catch {
          if (confirmationCurrent()) Message.error('删除失败，请重试')
          return false
        } finally {
          deletingIds.value = deletingIds.value.filter((value) => value !== id)
        }
      },
    })
  }
  watch(
    () => [user.userId, user.roleId, user.token, user.selected_environment, route.fullPath],
    () => {
      invalidate(true)
      pagination.page = 1
      void doRefresh()
    },
    { flush: 'sync' }
  )
  function visibilityChanged(): void {
    if (typeof document !== 'undefined' && document.hidden) invalidate()
    else void doRefresh()
  }
  onMounted(() => {
    if (typeof document !== 'undefined')
      document.addEventListener('visibilitychange', visibilityChanged)
    void doRefresh()
  })
  onActivated(() => {
    active = true
    void doRefresh()
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
