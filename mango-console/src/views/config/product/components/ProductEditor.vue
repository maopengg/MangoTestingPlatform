<template
  ><a-modal
    modal-class="mango-simple-form-modal"
    v-model:visible="visible"
    :title="editingId === null ? '新增' : '编辑'"
    :width="560"
    :on-before-ok="save"
    :closable="!saving"
    :mask-closable="!saving"
    :esc-to-close="!saving"
    :cancel-button-props="{ disabled: saving }"
    unmount-on-close
    @cancel="close"
  >
    <a-form auto-label-width class="mango-simple-form" :model="draft" :disabled="saving" layout="horizontal">
      <a-form-item class="mango-simple-form-item"
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
            :placeholder="item.placeholder"
            :max-length="5000"
            show-word-limit
            :auto-size="{ minRows: 3, maxRows: 8 }"
          />
        </template>
        <template v-else-if="item.type === 'select' && item.key === 'project'">
          <a-select
            v-model="item.value"
            :multiple="item.multiple"
            :max-tag-count="item.multiple ? 1 : undefined"
            :field-names="fieldNames"
            :options="editorProjectOptions"
            :loading="optionsLoading"
            :placeholder="item.placeholder"
            allow-clear
            allow-search
            value-key="key"
          />
        </template>
        <template v-else-if="item.type === 'select' && item.key === 'ui_client_type'">
          <a-select
            v-model="item.value"
            :multiple="item.multiple"
            :max-tag-count="item.multiple ? 1 : undefined"
            :field-names="fieldNames"
            :options="enumStore.drive_type"
            :placeholder="item.placeholder"
            allow-clear
            allow-search
            value-key="key"
          />
        </template>
        <template v-else-if="item.type === 'select' && item.key === 'api_client_type'">
          <a-select
            v-model="item.value"
            :multiple="item.multiple"
            :max-tag-count="item.multiple ? 1 : undefined"
            :field-names="fieldNames"
            :options="enumStore.api_client"
            :placeholder="item.placeholder"
            allow-clear
            allow-search
            value-key="key"
          />
        </template>
        <template v-else-if="item.type === 'select' && item.key === 'owners'">
          <a-select
            v-model="item.value"
            :multiple="item.multiple"
            :max-tag-count="1"
            :field-names="fieldNames"
            :options="users"
            :loading="usersLoading"
            :placeholder="item.placeholder"
            allow-clear
            allow-search
            value-key="key"
          />
        </template>
      </a-form-item>
    </a-form> </a-modal
></template>
<script setup lang="ts">
  import { computed, reactive, ref } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { postUserProduct, putUserProduct } from '@/api/system/product'
  import { useEnum } from '@/store/modules/get-enum'
  import { useProject } from '@/store/modules/get-project'
  import { fieldNames } from '@/setting'
  import { createFormItems } from '../config'
  import { productEditorProjectOptions } from '../overview'
  import { useProductPageScope } from '../composables/useProductPageScope'
  import type { ProductRecord, ProductDraft, ProductId, ProductOption } from '../types'
  const props = defineProps<{
    projects: ProductOption[]
    users: ProductOption[]
    optionsLoading?: boolean
    usersLoading?: boolean
  }>()
  const emit = defineEmits<{ (event: 'saved'): void }>()
  const enumStore = useEnum(),
    visible = ref(false),
    saving = ref(false),
    editingId = ref<ProductId | null>(null)
  const projectStore = useProject()
  const editingProject = ref<ProductRecord['project'] | null>(null)
  const editorProjectOptions = computed(() =>
    productEditorProjectOptions(props.projects, editingProject.value)
  )
  const defaults = (): ProductDraft => ({
    project: null,
    name: '',
    owners: [],
    ui_client_type: null,
    api_client_type: null,
    description: '',
  })
  const draft = reactive(defaults()),
    formItems = createFormItems()
  for (const item of formItems) {
    const key = item.key as keyof ProductDraft
    Object.defineProperty(item, 'value', {
      enumerable: true,
      get: () => draft[key],
      set: (value: ProductDraft[keyof ProductDraft]) => Object.assign(draft, { [key]: value }),
    })
  }
  let session = 0
  const scope = useProductPageScope(() => [], close)
  function open(record?: ProductRecord, projectId?: string) {
    if (saving.value || !scope.isActive()) return
    ++session
    editingId.value = record?.id ?? null
    editingProject.value = record?.project ?? null
    Object.assign(
      draft,
      defaults(),
      record
        ? {
            project: record.project?.id ?? null,
            name: record.name,
            owners: (record.owners || []).map((owner) => owner.id),
            ui_client_type: record.ui_client_type,
            api_client_type: record.api_client_type,
            description: record.description ?? '',
          }
        : {
            project:
              props.projects.find((option) => String(option.key) === projectId)?.key ??
              projectId ??
              null,
          }
    )
    visible.value = true
  }
  function close() {
    ++session
    visible.value = false
  }
  async function save(): Promise<boolean> {
    if (
      !visible.value ||
      saving.value ||
      !scope.isActive() ||
      !formItems.every((item) => !item.validator || item.validator())
    )
      return false
    const current = session,
      version = scope.snapshot(),
      id = editingId.value,
      payload = {
        project: draft.project,
        name: draft.name,
        owners: [...draft.owners],
        ui_client_type: draft.ui_client_type,
        api_client_type: draft.api_client_type,
        description: draft.description || null,
      }
    saving.value = true
    try {
      const res = await (id === null
        ? postUserProduct({ ...payload, status: 1 })
        : putUserProduct({ ...payload, id }))
      projectStore.invalidateProjectOptionsCache()
      if (current !== session || !scope.current(version)) return false
      Message.success(res.msg)
      emit('saved')
      close()
      return true
    } catch {
      return false
    } finally {
      saving.value = false
    }
  }
  defineExpose({ open, close })
</script>
