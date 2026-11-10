<template>
  <TableBody class="mango-detail-workbench-page mango-module-page">
    <template #header>
      <div class="mango-detail-toolbar">
        <div class="mango-detail-heading">
          <div class="mango-detail-title">{{ productModuleDetailTitle }}</div>
          <div class="mango-detail-subtitle"
            >在树中管理上下级模块，点击名称查看详情；三级模块用于绑定业务数据</div
          >
        </div>
        <a-space class="mango-detail-actions">
          <a-button
            size="small"
            type="primary"
            :disabled="loading || projectProductId === null"
            @click="openCreate()"
            >新增一级模块</a-button
          >
          <a-button class="mango-back-button" size="small" @click="goBack">返回</a-button>
        </a-space>
      </div>
    </template>
    <template #default>
      <ModuleTree
        :key="projectProductId"
        :modules="modules"
        :loading="loading"
        :error="loadError"
        @retry="loadModules"
        @add="openCreate"
        @edit="openModule"
        @delete="removeModule"
        @detail="detailId = $event.id"
      />
    </template>
  </TableBody>

  <a-modal
    :visible="!!detailRecord"
    title="模块详情"
    :footer="false"
    :width="560"
    @cancel="detailId = null"
  >
    <a-descriptions v-if="detailRecord" :column="1" size="small" class="mango-module-description">
      <a-descriptions-item label="模块名称">{{ detailRecord.name }}</a-descriptions-item>
      <a-descriptions-item label="模块 ID">{{ detailRecord.id }}</a-descriptions-item>
      <a-descriptions-item label="完整路径">{{
        formatModulePath(detailRecord)
      }}</a-descriptions-item>
      <a-descriptions-item label="所属上级">{{
        detailRecord.parent?.name || '无（一级模块）'
      }}</a-descriptions-item>
      <a-descriptions-item label="层级">{{
        moduleLevelLabels[Number(detailRecord.level) - 1]
      }}</a-descriptions-item>
      <a-descriptions-item label="创建时间">{{
        detailRecord.create_time || '-'
      }}</a-descriptions-item>
      <a-descriptions-item label="更新时间">{{
        detailRecord.update_time || '-'
      }}</a-descriptions-item>
      <a-descriptions-item label="更新人">{{
        detailRecord.update_user?.name || detailRecord.update_user?.username || '-'
      }}</a-descriptions-item>
    </a-descriptions>
  </a-modal>

  <ModuleEditor ref="moduleEditorRef" :product-id="projectProductId" @saved="onSaved" />
</template>
<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { computed, reactive, ref, onMounted, watch } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import { useRoute } from 'vue-router'
  import { useProject } from '@/store/modules/get-project'
  import { formatModulePath } from '@/utils/business-format'
  import { getUserModule, deleteUserModule } from '@/api/system/module'
  import ModuleTree from './components/ModuleTree.vue'
  import ModuleEditor from './components/ModuleEditor.vue'
  import { moduleLevelLabels } from './config'
  import { useProductPageScope } from '../composables/useProductPageScope'
  import type { ModuleRecord, ModuleEditorHandle } from './types'
  const route = useRoute(),
    projectStore = useProject()
  const loading = ref(false),
    loadError = ref(''),
    modules = ref<ModuleRecord[]>([])
  const moduleEditorRef = ref<ModuleEditorHandle | null>(null),
    detailId = ref<number | null>(null)
  const detailRecord = computed(
    () => modules.value.find((record) => record.id === detailId.value) ?? null
  )
  let requestVersion = 0
  let confirmation: ReturnType<typeof Modal.confirm> | null = null
  const deleting = reactive(new Set<number>())
  const projectProductId = computed(() => {
    const raw = route.query.id
    if (typeof raw !== 'string' || !/^\d+$/.test(raw)) return null
    const id = Number(raw)
    return Number.isSafeInteger(id) && id > 0 ? id : null
  })
  const productModuleDetailTitle = computed(
    () =>
      `产品模块配置 / ${projectProductId.value ?? '-'} / ${
        typeof route.query.name === 'string' ? route.query.name : '-'
      }`
  )
  const scope = useProductPageScope(
    () => [projectProductId.value],
    reset,
    () => void loadModules()
  )
  function reset() {
    ++requestVersion
    modules.value = []
    loading.value = false
    loadError.value = ''
    detailId.value = null
    moduleEditorRef.value?.close()
    confirmation?.close()
    confirmation = null
  }
  function openCreate(parent?: ModuleRecord) {
    if (scope.isActive() && !loading.value) moduleEditorRef.value?.create(parent)
  }
  function openModule(record: ModuleRecord) {
    if (scope.isActive() && !loading.value && !deleting.has(record.id))
      moduleEditorRef.value?.edit(record)
  }
  function onSaved() {
    void loadModules()
  }
  function removeModule(record: ModuleRecord) {
    if (!scope.isActive() || confirmation || deleting.has(record.id)) return
    const id = record.id,
      version = scope.snapshot()
    const dialog = Modal.confirm({
      title: '删除模块',
      content: `确认删除模块「${record.name}」吗？存在子模块或业务引用时后端会阻止删除。`,
      okText: '删除',
      cancelText: '取消',
      okButtonProps: { status: 'danger' },
      async onBeforeOk() {
        if (!scope.current(version) || deleting.has(id)) return false
        deleting.add(id)
        try {
          await deleteUserModule(id)
          projectStore.invalidateAllProductModuleTreeCache()
          if (scope.current(version)) {
            Message.success('删除成功')
            await loadModules()
          }
          return true
        } catch {
          return false
        } finally {
          deleting.delete(id)
        }
      },
      onClose() {
        if (confirmation === dialog) confirmation = null
      },
    })
    confirmation = dialog
  }
  async function loadModules() {
    if (!scope.isActive()) return
    const current = ++requestVersion,
      version = scope.snapshot(),
      product = projectProductId.value
    if (product === null) {
      modules.value = []
      loadError.value = '缺少产品 ID，请从产品配置重新进入'
      loading.value = false
      return
    }
    loading.value = true
    loadError.value = ''
    try {
      const res = await getUserModule({ project_product: product })
      if (current === requestVersion && scope.current(version)) modules.value = res.data || []
    } catch (loadFailure0) {
      if (current === requestVersion && scope.current(version))
        void (reportLoadError(loadFailure0, '模块加载失败，请重试'), loadError.value = '')
    } finally {
      if (current === requestVersion) loading.value = false
    }
  }
  watch(modules, (records) => {
    if (detailId.value !== null && !records.some((record) => record.id === detailId.value))
      detailId.value = null
  })
  function goBack() {
    window.history.back()
  }
  onMounted(() => void loadModules())
</script>
<style scoped>
  .mango-module-page,
  .mango-module-page :deep(.mango-table-body__content) {
    background: var(--m-surface);
  }
  .mango-module-description {
    overflow-wrap: anywhere;
  }
</style>
