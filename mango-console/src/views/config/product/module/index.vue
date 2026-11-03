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
            :disabled="loading || !projectProductId"
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
        @detail="detailRecord = $event"
      />
    </template>
  </TableBody>

  <a-modal
    :visible="!!detailRecord"
    title="模块详情"
    :footer="false"
    :width="560"
    @cancel="detailRecord = null"
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

  <ModalDialog
    ref="moduleDialogRef"
    :title="
      moduleForm.id ? '编辑模块' : `新增${moduleLevelLabels[moduleForm.level - 1] || '一级模块'}`
    "
    width="540px"
    @confirm="saveModule"
  >
    <template #content>
      <a-form :model="moduleForm" class="mango-module-form">
        <a-form-item label="所属上级"
          ><span>{{ moduleForm.parentName || '无（一级模块）' }}</span></a-form-item
        >
        <a-form-item class="mango-form-item__require" label="模块名称">
          <a-input v-model="moduleForm.name" :max-length="64" placeholder="请输入模块名称" />
        </a-form-item>
      </a-form>
    </template>
  </ModalDialog>
</template>

<script lang="ts" setup>
  import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import { useRoute } from 'vue-router'
  import ModalDialog from '@/components/overlays/ModalDialog.vue'
  import ModuleTree from './ModuleTree.vue'
  import { moduleLevelLabels, moduleCreateDraft } from './config'
  import { useProject } from '@/store/modules/get-project'
  import { formatModulePath } from '@/utils/business-format'
  import {
    deleteUserModule,
    getUserModule,
    postUserModule,
    putUserModule,
  } from '@/api/system/module'

  const route = useRoute()
  const projectStore = useProject()
  const loading = ref(false)
  const loadError = ref('')
  const moduleDialogRef = ref<InstanceType<typeof ModalDialog> | null>(null)
  const modules = ref<any[]>([])
  const moduleForm = reactive<any>({})
  const detailRecord = ref<any>(null)
  let requestVersion = 0
  const projectProductId = computed(() => Number(route.query.id) || undefined)
  const productModuleDetailTitle = computed(
    () => `产品模块配置 / ${route.query.id || '-'} / ${route.query.name || '-'}`
  )
  function resetForm() {
    Object.keys(moduleForm).forEach((key) => delete moduleForm[key])
  }
  function openCreate(parent?: any) {
    resetForm()
    if (Number(parent?.level || 0) >= 3) return
    Object.assign(moduleForm, moduleCreateDraft(parent))
    moduleDialogRef.value?.show()
  }
  function openModule(record: any) {
    resetForm()
    Object.assign(moduleForm, { id: record.id, name: record.name, parentName: record.parent?.name })
    moduleDialogRef.value?.show()
  }

  async function saveModule() {
    if (!String(moduleForm.name || '').trim()) {
      Message.error('请输入模块名称')
      moduleDialogRef.value?.setConfirmLoading(false)
      return
    }
    try {
      if (moduleForm.id)
        await putUserModule({ id: moduleForm.id, name: String(moduleForm.name).trim() })
      else
        await postUserModule({
          project_product: projectProductId.value,
          parent: moduleForm.parent,
          name: String(moduleForm.name).trim(),
        })
      projectStore.invalidateAllProductModuleTreeCache()
      Message.success('保存成功')
      await moduleDialogRef.value?.close()
      await loadModules()
    } catch {
      // 请求层展示具体错误，保留表单供用户修正。
    } finally {
      moduleDialogRef.value?.setConfirmLoading(false)
    }
  }

  function removeModule(record: any) {
    Modal.confirm({
      title: '删除模块',
      content: `确认删除模块「${record.name}」吗？存在子模块或业务引用时后端会阻止删除。`,
      okText: '删除',
      cancelText: '取消',
      okButtonProps: { status: 'danger' },
      onBeforeOk: async () => {
        try {
          await deleteUserModule(record.id)
          projectStore.invalidateAllProductModuleTreeCache()
          Message.success('删除成功')
          await loadModules()
          return true
        } catch {
          return false
        }
      },
    })
  }

  async function loadModules() {
    const version = ++requestVersion
    if (!projectProductId.value) {
      modules.value = []
      loadError.value = '缺少产品 ID，请从产品配置重新进入'
      loading.value = false
      return
    }
    loading.value = true
    loadError.value = ''
    try {
      const res = await getUserModule({ project_product: projectProductId.value })
      if (version === requestVersion) modules.value = res.data || []
    } catch {
      if (version === requestVersion) loadError.value = '模块加载失败，请重试'
    } finally {
      if (version === requestVersion) loading.value = false
    }
  }

  function goBack() {
    window.history.back()
  }
  watch(
    projectProductId,
    () => {
      modules.value = []
      detailRecord.value = null
      moduleDialogRef.value?.close()
      loadModules()
    },
    { immediate: true }
  )
  onBeforeUnmount(() => {
    requestVersion++
  })
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
