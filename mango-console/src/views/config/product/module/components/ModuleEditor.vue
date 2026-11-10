<template>
  <a-modal
    modal-class="mango-simple-form-modal"
    v-model:visible="visible"
    :title="
      moduleForm.id !== null
        ? '编辑模块'
        : `新增${moduleLevelLabels[moduleForm.level - 1] || '一级模块'}`
    "
    :width="560"
    :on-before-ok="saveModule"
    :closable="!saving"
    :mask-closable="!saving"
    :esc-to-close="!saving"
    :cancel-button-props="{ disabled: saving }"
    unmount-on-close
    @cancel="close"
  >
    <a-form auto-label-width :disabled="saving" layout="horizontal" :model="moduleForm" class="mango-module-form mango-simple-form">
      <a-form-item class="mango-simple-form-item" label="所属上级"
        ><span>{{ moduleForm.parentName || '无（一级模块）' }}</span></a-form-item
      >
      <a-form-item class="mango-form-item__require mango-simple-form-item" label="模块名称">
        <a-input v-model="moduleForm.name" :max-length="64" placeholder="请输入模块名称" />
      </a-form-item>
    </a-form> </a-modal
></template>
<script setup lang="ts">
  import { reactive, ref } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { useProject } from '@/store/modules/get-project'
  import { postUserModule, putUserModule } from '@/api/system/module'
  import { moduleCreateDraft, moduleLevelLabels } from '../config'
  import { useProductPageScope } from '../../composables/useProductPageScope'
  import type { ModuleDraft, ModuleRecord } from '../types'
  const props = defineProps<{ productId: number | null }>()
  const emit = defineEmits<{ (event: 'saved'): void }>()
  const visible = ref(false),
    saving = ref(false)
  const projectStore = useProject()
  const moduleForm: ModuleDraft = reactive({ id: null, ...moduleCreateDraft() })
  let session = 0
  const scope = useProductPageScope(() => [props.productId], close)
  function create(parent?: ModuleRecord) {
    if (
      saving.value ||
      !scope.isActive() ||
      props.productId === null ||
      Number(parent?.level || 0) >= 3
    )
      return
    ++session
    Object.assign(moduleForm, { id: null, ...moduleCreateDraft(parent) })
    visible.value = true
  }
  function edit(record: ModuleRecord) {
    if (saving.value || !scope.isActive() || props.productId === null) return
    ++session
    Object.assign(moduleForm, {
      id: record.id,
      name: record.name,
      parent: record.parent?.id ?? null,
      parentName: record.parent?.name ?? '',
      level: record.level,
    })
    visible.value = true
  }
  function close() {
    ++session
    visible.value = false
  }
  async function saveModule(): Promise<boolean> {
    if (!visible.value || saving.value || !scope.isActive() || props.productId === null)
      return false
    if (!moduleForm.name.trim()) {
      Message.error('请输入模块名称')
      return false
    }
    const current = session,
      version = scope.snapshot(),
      id = moduleForm.id,
      name = moduleForm.name.trim(),
      payload =
        id !== null
          ? { id, name }
          : { project_product: props.productId, parent: moduleForm.parent, name }
    saving.value = true
    try {
      await (id !== null ? putUserModule(payload) : postUserModule(payload))
      projectStore.invalidateAllProductModuleTreeCache()
      if (current !== session || !scope.current(version)) return false
      Message.success('保存成功')
      emit('saved')
      close()
      return true
    } catch {
      return false
    } finally {
      saving.value = false
    }
  }
  defineExpose({ create, edit, close })
</script>
