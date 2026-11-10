<template>
  <TableBody class="mango-source-page" content-flush>
    <template #header><TableHeader title="数据源工作台" :show-filter="false" /></template>
    <template v-if="loadFailed"><a-button size="small" :loading="loading" @click="doRefresh">重新加载</a-button></template>
    <DataSourceWorkbench
      :sources="sources"
      :loading="loading"
      :testing-ids="testingIds"
      @add="editorRef?.open()"
      @edit="editorRef?.open($event)"
      @remove="onDelete"
      @test="onTest"
    />
  </TableBody>
  <DataSourceEditor ref="editorRef" :options-loading="optionsLoading" @saved="doRefresh" />
</template>
<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { h, onMounted, ref } from 'vue'
  import { Message, Modal, Notification } from '@arco-design/web-vue'
  import { deleteSystemDataSource, getSystemDataSource } from '@/api/system/data_source'
  import { postDataSourceExecution } from '@/api/data-source-execution'
  import { useEnum } from '@/store/modules/get-enum'
  import DataSourceWorkbench from './components/DataSourceWorkbench.vue'
  import DataSourceEditor from './components/DataSourceEditor.vue'
  import { useSourceScope } from './composables/useSourceScope'
  import { connectionStatusLabels } from './config'
  import { sourceDisplayLabel, sourceError } from './form'
  import type { DataSourceRecord, SourceEditorHandle, ConnectionResult } from './types'
  const sources = ref<DataSourceRecord[]>([])
  const loading = ref(false)
  const loadFailed = ref(false)
  const optionsLoading = ref(false)
  const testingIds = ref<number[]>([])
  const editorRef = ref<SourceEditorHandle | null>(null)
  const enumStore = useEnum()
  let listRequest = 0,
    enumRequest = 0
  let confirmation: ReturnType<typeof Modal.confirm> | null = null
  const deletingIds = new Set<number>()
  const scope = useSourceScope(reset, resume)
  function reset() {
    ++listRequest
    ++enumRequest
    sources.value = []
    loading.value = false
    optionsLoading.value = false
    loadFailed.value = false
    editorRef.value?.close()
    confirmation?.close()
    confirmation = null
  }
  function resume() {
    void doRefresh()
    void loadEnums()
  }
  async function loadEnums() {
    if (!scope.isActive()) return
    const request = ++enumRequest,
      version = scope.snapshot()
    optionsLoading.value = true
    try {
      await enumStore.getEnum()
    } catch {
      if (scope.current(version)) Message.error('数据源类型加载失败，请重新打开页面重试')
    } finally {
      if (request === enumRequest) optionsLoading.value = false
    }
  }
  async function doRefresh() {
    if (!scope.isActive()) return
    const request = ++listRequest,
      version = scope.snapshot()
    loading.value = true
    loadFailed.value = false
    try {
      const response = await getSystemDataSource({})
      if (request === listRequest && scope.current(version)) sources.value = response.data || []
    } catch (loadFailure0) {
      if (request === listRequest && scope.current(version)) (reportLoadError(loadFailure0, "加载失败，请重试", false), loadFailed.value = true)
    } finally {
      if (request === listRequest) loading.value = false
    }
  }
  async function onTest(record: DataSourceRecord) {
    const id = record.id,
      version = scope.snapshot()
    if (!scope.isActive() || testingIds.value.includes(id) || deletingIds.has(id)) return
    testingIds.value = [...testingIds.value, id]
    try {
      const response = await postDataSourceExecution({
        action: 'test_connection',
        data_source_id: id,
      })
      if (!scope.current(version)) return
      const result: ConnectionResult = response.data
      const checks = Array.isArray(result?.checks) ? result.checks : []
      const notify = result?.connected ? Notification.success : Notification.error
      notify({
        title: result?.connected ? '数据源连接测试通过' : '数据源连接测试失败',
        content: () =>
          h(
            'div',
            checks.length
              ? checks.map((item, index) =>
                  h(
                    'div',
                    { key: item.key || index },
                    `${index + 1}. ${item.name}：${
                      connectionStatusLabels[item.status] || item.status
                    }；${item.message}`
                  )
                )
              : result?.error || response.msg
          ),
        duration: 10000,
        closable: true,
      })
    } catch (error: unknown) {
      if (scope.current(version)) Message.error(sourceError(error, '数据源连接测试失败'))
    } finally {
      testingIds.value = testingIds.value.filter((value) => value !== id)
    }
  }
  function onDelete(record: DataSourceRecord) {
    const id = record.id,
      version = scope.snapshot()
    if (!scope.isActive() || confirmation || deletingIds.has(id) || testingIds.value.includes(id))
      return
    const dialog = Modal.confirm({
      title: '删除数据库配置',
      content: `确认删除数据库配置「${sourceDisplayLabel(
        record
      )}」？已被逻辑数据库绑定时不允许删除。`,
      cancelText: '取消',
      okText: '删除',
      okButtonProps: { status: 'danger' },
      async onBeforeOk() {
        if (!scope.current(version) || deletingIds.has(id)) return false
        deletingIds.add(id)
        try {
          const response = await deleteSystemDataSource(id)
          if (scope.current(version)) {
            Message.success(response.msg)
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
  onMounted(resume)
</script>

<style scoped>
  .mango-source-page :deep(.mango-table-body__content) {
    display: flex;
    flex-direction: column;
    min-height: 0;
    overflow: hidden;
  }
  .mango-source-page :deep(.mango-source-boundary) {
    flex: 1;
  }
</style>
