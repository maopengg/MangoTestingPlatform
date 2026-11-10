<template>
  <TableBody class="mango-detail-workbench-page mango-notice-page">
    <template #header>
      <div class="mango-detail-toolbar">
        <div class="mango-detail-heading">
          <div class="mango-detail-title">{{ noticeDetailTitle }}</div>
          <div class="mango-detail-subtitle">维护项目通知接收人、邮箱和消息测试配置</div>
        </div>
        <a-space class="mango-detail-actions" wrap>
          <a-button
            size="small"
            type="primary"
            :disabled="projectId === null || editorSaving"
            @click="onAdd"
            data-testid="qa-views-config-project-notice-button-新增"
            >新增</a-button
          >
          <a-button
            class="mango-back-button"
            size="small"
            @click="doResetSearch"
            data-testid="qa-views-config-project-notice-button-返回"
            >返回</a-button
          >
        </a-space>
      </div>
    </template>

    <template #default>
      <section class="mango-section-card mango-project-notice-section">
        <div class="mango-section-title">
          <div class="mango-section-title__main">
            <h2>通知组配置</h2>
            <p>维护当前项目的通知接收人、邮箱和消息测试配置</p>
          </div>
          <a-tag size="small">{{ pagination.pageCount || 0 }}</a-tag>
        </div>
        
        <div class="mango-project-notice-table">
          <a-table
            class="mango-native-scroll-table"
            :scroll="{ x: 1350, y: '100%' }"
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
                <template v-else-if="item.key === 'mail'" #cell="{ record }">
                  {{ Array.isArray(record.mail) ? record.mail.join(', ') : record.mail }}
                </template>
                <template v-else-if="item.key === 'update_user'" #cell="{ record }">
                  {{ record.update_user?.name || record.update_user?.username || '-' }}
                </template>
                <template v-else-if="item.key === 'actions'" #cell="{ record }">
                  <MangoTableActions
                    :actions="[
                      {
                        label: '测试',
                        loading: testingIds.has(record.id),
                        disabled: isWriting(record.id),
                        onClick: () => onTest(record),
                      },
                      {
                        label: '编辑',
                        disabled: editorSaving || isBusy(record.id),
                        onClick: () => onUpdate(record),
                      },
                      {
                        label: '删除',
                        danger: true,
                        loading: deletingIds.has(record.id),
                        disabled: testingIds.has(record.id) || editingIds.has(record.id),
                        onClick: () => onDelete(record),
                      },
                    ]"
                  />
                </template>
              </a-table-column>
            </template>
          </a-table>
        </div>
      </section>
    </template>
    <template #footer>
      <TableFooter :pagination="pagination" />
    </template>
  </TableBody>
  <NoticeGroupEditor
    ref="editorRef"
    :project-id="projectId"
    @saved="doRefresh"
    @saving-change="onEditorSaving"
  />
</template>
<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { computed, onMounted, reactive, ref } from 'vue'
  import { useRoute } from 'vue-router'
  import { usePageData } from '@/store/page-data'
  import { usePagination } from '@/hooks/table'
  import { Message, Modal } from '@arco-design/web-vue'
  import {
    deleteSystemNotice,
    getSystemNotice,
    getSystemNoticeTest,
  } from '@/api/system/notice_group'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import NoticeGroupEditor from './components/NoticeGroupEditor.vue'
  import { tableColumns } from './config'
  import { resolveNoticeProject } from './context'
  import { useNoticeScope } from './composables/useNoticeScope'
  import type { NoticeRecord, NoticeEditorHandle } from './types'
  const route = useRoute(),
    pageData = usePageData()
  const projectContext = computed(() => resolveNoticeProject(route.query, pageData.record))
  const projectId = computed(() => projectContext.value.id)
  const noticeDetailTitle = computed(
    () => `通知组配置 / ${projectId.value ?? '-'} / ${projectContext.value.name}`
  )
  const rows = ref<NoticeRecord[]>([]),
    listLoading = ref(false),
    loadError = ref('')
  const pagination = usePagination(doRefresh, listLoading)
  const editorRef = ref<NoticeEditorHandle | null>(null),
    editorSaving = ref(false)
  const testingIds = reactive(new Set<number>()),
    deletingIds = reactive(new Set<number>()),
    editingIds = reactive(new Set<number>())
  let listRequest = 0,
    lastProject = projectId.value
  let confirmation: ReturnType<typeof Modal.confirm> | null = null
  const scope = useNoticeScope(
    () => [projectId.value],
    reset,
    () => void doRefresh()
  )
  const isWriting = (id: number) => deletingIds.has(id) || editingIds.has(id)
  const isBusy = (id: number) => isWriting(id) || testingIds.has(id)
  function reset() {
    ++listRequest
    rows.value = []
    pagination.setTotalSize(0)
    listLoading.value = false
    loadError.value = ''
    if (lastProject !== projectId.value) {
      pagination.page = 1
      lastProject = projectId.value
    }
    editorRef.value?.close()
    confirmation?.close()
    confirmation = null
  }
  async function doRefresh() {
    if (!scope.isActive()) return
    const request = ++listRequest,
      version = scope.snapshot(),
      id = projectId.value
    if (id === null) {
      rows.value = []
      pagination.setTotalSize(0)
      loadError.value = '缺少有效项目 ID，请从项目配置重新进入'
      listLoading.value = false
      return
    }
    const payload = { project: id, page: pagination.page, pageSize: pagination.pageSize }
    listLoading.value = true
    loadError.value = ''
    try {
      const response = await getSystemNotice(payload)
      if (request !== listRequest || !scope.current(version)) return
      rows.value = response.data || []
      pagination.setTotalSize(response.totalSize ?? 0)
    } catch (loadFailure0) {
      if (request === listRequest && scope.current(version))
        void (reportLoadError(loadFailure0, "通知组加载失败，请重试", false), loadError.value = '通知组加载失败，请重试')
    } finally {
      if (request === listRequest) listLoading.value = false
    }
  }
  function onEditorSaving(id: number | null, pending: boolean) {
    editorSaving.value = pending
    if (id !== null) {
      if (pending) editingIds.add(id)
      else editingIds.delete(id)
    }
  }
  function onAdd() {
    if (scope.isActive() && !editorSaving.value && projectId.value !== null) editorRef.value?.open()
  }
  function onUpdate(record: NoticeRecord) {
    if (scope.isActive() && !editorSaving.value && !isBusy(record.id)) editorRef.value?.open(record)
  }
  function onDelete(record: NoticeRecord) {
    if (!scope.isActive() || projectId.value === null || confirmation || isBusy(record.id)) return
    const id = record.id,
      version = scope.snapshot()
    const dialog = Modal.confirm({
      title: '提示',
      content: '是否要删除此配置？',
      okText: '删除',
      cancelText: '取消',
      okButtonProps: { status: 'danger' },
      async onBeforeOk() {
        if (!scope.current(version) || isBusy(id)) return false
        deletingIds.add(id)
        try {
          const response = await deleteSystemNotice(id)
          if (scope.current(version)) {
            Message.success(response.msg)
            if (rows.value.length === 1 && rows.value[0].id === id && pagination.page > 1)
              pagination.page--
            await doRefresh()
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
  async function onTest(record: NoticeRecord) {
    if (!scope.isActive() || projectId.value === null || isBusy(record.id)) return
    const id = record.id,
      version = scope.snapshot()
    testingIds.add(id)
    try {
      const response = await getSystemNoticeTest(id)
      if (scope.current(version)) Message.success(response.msg)
    } catch (error: unknown) {
      if (scope.current(version)) {
        const message =
          error &&
          typeof error === 'object' &&
          'message' in error &&
          typeof error.message === 'string'
            ? error.message
            : error && typeof error === 'object' && 'msg' in error && typeof error.msg === 'string'
            ? error.msg
            : '通知测试失败，请重试'
        Message.error(message)
      }
    } finally {
      testingIds.delete(id)
    }
  }
  function doResetSearch() {
    window.history.back()
  }
  onMounted(() => void doRefresh())
</script>
<style lang="less" scoped>
  .mango-notice-page :deep(.mango-table-body__content) {
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  .mango-project-notice-section {
    display: flex;
    flex: 1;
    height: calc(100% - var(--m-page-gap));
    min-height: 0;
    margin-top: var(--m-page-gap);
    flex-direction: column;
  }

  .mango-project-notice-section > :not(.mango-project-notice-table) {
    flex: none;
  }

  .mango-project-notice-table {
    flex: 1;
    min-height: 0;
    overflow: hidden;
  }
</style>
