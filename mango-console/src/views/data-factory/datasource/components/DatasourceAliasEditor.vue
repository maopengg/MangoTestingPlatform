<template>
  <a-modal
    modal-class="mango-simple-form-modal"
    v-model:visible="visible"
    :width="560"
    :title="editingId === null ? '新增逻辑数据库' : '编辑逻辑数据库'"
    :on-before-ok="save"
    :ok-loading="saving"
    :closable="!saving"
    :mask-closable="!saving"
    :esc-to-close="!saving"
    :cancel-button-props="{ disabled: saving }"
    unmount-on-close
    @cancel="close"
  >
    <a-form auto-label-width class="mango-simple-form" :model="draft" :disabled="saving" layout="horizontal">
      <a-form-item class="mango-simple-form-item" label="产品" required
        ><ProjectProductSelect v-model="draft.project_product" :disabled="saving"
      /></a-form-item>
      <a-form-item class="mango-simple-form-item" label="名称" required><a-input v-model="draft.name" /></a-form-item>
      <a-form-item class="mango-simple-form-item" label="数据库分类" required>
        <a-select
          v-model="draft.source_category"
          :options="enumStore.data_source_category"
          :loading="optionsLoading"
          :field-names="enumFieldNames"
          @change="onCategoryChange"
        />
      </a-form-item>
      <a-form-item class="mango-simple-form-item" label="数据库类型" required>
        <a-select
          v-model="draft.db_type"
          :options="sourceTypeOptions"
          :loading="optionsLoading"
          :field-names="enumFieldNames"
        />
      </a-form-item>
      <a-form-item class="mango-simple-form-item" label="描述"
        ><a-textarea v-model="draft.description" :auto-size="{ minRows: 2, maxRows: 4 }"
      /></a-form-item>
    </a-form>
  </a-modal>
</template>
<script setup lang="ts">
  import { computed, reactive, ref } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { postDataFactoryDatasourceAlias, putDataFactoryDatasourceAlias } from '@/api/data-factory'
  import { useEnum } from '@/store/modules/get-enum'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import { enumFieldNames } from '../config'
  import { createAliasDraft, aliasPayload, productId } from '../form'
  import { useDatasourceScope } from '../composables/useDatasourceScope'
  import type { LogicalSource, EntityId } from '../types'
  const props = defineProps<{ optionsLoading: boolean }>()
  const emit = defineEmits<{
    (event: 'saved'): void
    (event: 'saving-change', id: number | null, pending: boolean): void
  }>()
  const enumStore = useEnum()
  const visible = ref(false),
    saving = ref(false),
    editingId = ref<number | null>(null)
  const draft = reactive(createAliasDraft())
  const sourceTypeOptions = computed(() =>
    (enumStore.data_source_type || []).filter(
      (item) =>
        Number(enumStore.data_source_type_category[item.key]) === Number(draft.source_category)
    )
  )
  let session = 0
  const scope = useDatasourceScope(close)
  function open(record?: LogicalSource, product: EntityId | null = null) {
    if (saving.value || !scope.isActive()) return
    ++session
    editingId.value = record?.id ?? null
    Object.assign(draft, createAliasDraft(record, product))
    visible.value = true
  }
  function close() {
    ++session
    visible.value = false
    editingId.value = null
    Object.assign(draft, createAliasDraft())
  }
  function onCategoryChange() {
    if (!saving.value)
      draft.db_type = sourceTypeOptions.value.length ? Number(sourceTypeOptions.value[0].key) : null
  }
  async function save(): Promise<boolean> {
    if (!visible.value || saving.value || props.optionsLoading || !scope.isActive()) return false
    if (productId(draft.project_product) === null || !draft.name || draft.db_type == null) {
      Message.error('请先填写产品、名称和数据库类型')
      return false
    }
    const id = editingId.value,
      current = session,
      version = scope.snapshot()
    const payload = id === null ? aliasPayload(draft) : { ...aliasPayload(draft), id }
    saving.value = true
    emit('saving-change', id, true)
    try {
      const response = await (id === null
        ? postDataFactoryDatasourceAlias(payload)
        : putDataFactoryDatasourceAlias(payload))
      if (current !== session || !scope.current(version)) return false
      Message.success(response.msg)
      emit('saved')
      close()
      return true
    } catch {
      return false
    } finally {
      saving.value = false
      emit('saving-change', id, false)
    }
  }
  defineExpose({ open, close })
</script>
