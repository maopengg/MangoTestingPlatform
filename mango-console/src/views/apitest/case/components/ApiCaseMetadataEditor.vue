<template>
  <a-modal
    modal-class="mango-simple-form-modal"
    v-model:visible="visible"
    :title="editingId === null ? '新增' : '编辑'"
    :width="560"
    :on-before-ok="save"
    :closable="!saving"
    :mask-closable="!saving"
    :cancel-button-props="{ disabled: saving }"
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
        <template v-else-if="item.type === 'cascader'">
          <ProjectProductSelect
            v-model="item.value"
            :placeholder="item.placeholder"
            @change="onFormProjectProductChange"
          />
        </template>
        <template v-else-if="item.type === 'select' && item.key === 'module'">
          <ProductModuleSelect
            v-model="item.value"
            :project-product-id="draft.project_product"
            :placeholder="item.placeholder"
            :auto-clear="false"
          />
        </template>
        <template v-else-if="item.type === 'select' && item.key === 'case_people'">
          <a-select
            v-model="item.value"
            :multiple="item.multiple"
            :max-tag-count="item.multiple ? 1 : undefined"
            :field-names="fieldNames"
            :options="userOptions"
            :loading="usersLoading"
            :placeholder="item.placeholder"
            allow-clear
            allow-search
            value-key="key"
          />
        </template>
        <template v-else-if="item.type === 'select' && item.key === 'level'">
          <a-select
            v-model="item.value"
            :multiple="item.multiple"
            :max-tag-count="item.multiple ? 1 : undefined"
            :field-names="fieldNames"
            :options="enumStore.case_level"
            :placeholder="item.placeholder"
            allow-clear
            allow-search
            value-key="key"
          />
        </template>
        <template v-else-if="item.type === 'select' && item.key === 'scenario_layer'">
          <a-select
            v-model="item.value"
            :multiple="item.multiple"
            :max-tag-count="item.multiple ? 1 : undefined"
            :field-names="fieldNames"
            :options="enumStore.api_case_scenario_layer"
            :placeholder="item.placeholder"
            allow-clear
            allow-search
            value-key="key"
          />
        </template>
        <template v-else-if="item.type === 'select' && item.key === 'scenario_type'">
          <a-select
            v-model="item.value"
            :multiple="item.multiple"
            :max-tag-count="item.multiple ? 1 : undefined"
            :field-names="fieldNames"
            :options="enumStore.api_case_scenario_type"
            :placeholder="item.placeholder"
            allow-clear
            allow-search
            value-key="key"
          />
        </template>
        <template v-else-if="item.type === 'select' && item.key === 'scenario_tags'">
          <a-select
            v-model="item.value"
            :field-names="fieldNames"
            :options="enumStore.api_case_scenario_tag"
            :placeholder="item.placeholder"
            allow-clear
            allow-search
            multiple
            value-key="key"
          />
        </template>
        <template v-else-if="item.type === 'textarea'">
          <a-textarea
            v-model="item.value"
            :placeholder="item.placeholder"
            :auto-size="{ minRows: 3, maxRows: 5 }"
          />
        </template>
      </a-form-item>
    </a-form>
  </a-modal>
</template>
<script setup lang="ts">
  import { reactive, ref, onBeforeUnmount, onDeactivated } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { fieldNames } from '@/setting'
  import { useEnum } from '@/store/modules/get-enum'
  import { postApiCase, putApiCase } from '@/api/apitest/case'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import { createMetadataFormItems } from '../config'
  import { createMetadataDraft, metadataPayload } from '../metadata'
  import type { CaseListRow, CaseMetadataDraft, UserOption } from '../types'
  defineProps<{ userOptions: UserOption[]; usersLoading?: boolean }>()
  const enumStore = useEnum()
  const emit = defineEmits<{ (event: 'saved'): void }>()
  const visible = ref(false),
    saving = ref(false),
    editingId = ref<number | null>(null)
  const draft = reactive<CaseMetadataDraft>(createMetadataDraft())
  const formItems = createMetadataFormItems()
  for (const item of formItems) {
    const key = item.key as keyof CaseMetadataDraft
    Object.defineProperty(item, 'value', {
      enumerable: true,
      get: () => draft[key],
      set: (value) => Object.assign(draft, { [key]: value }),
    })
  }
  let session = 0
  function close() {
    session++
    visible.value = false
  }
  function open(record?: CaseListRow, defaults?: Parameters<typeof createMetadataDraft>[1]) {
    if (saving.value) return
    session++
    editingId.value = record?.id ?? null
    Object.assign(draft, createMetadataDraft(record, defaults))
    visible.value = true
  }
  function onFormProjectProductChange() {
    draft.module = null
  }
  async function save(): Promise<boolean> {
    if (
      saving.value ||
      !visible.value ||
      !formItems.every((item) => !item.validator || item.validator())
    )
      return false
    const token = session,
      id = editingId.value,
      payload = metadataPayload(draft)
    saving.value = true
    try {
      const response = await (id === null ? postApiCase(payload) : putApiCase({ ...payload, id }))
      if (token !== session) return false
      Message.success(response.msg)
      emit('saved')
      close()
      return true
    } catch {
      return false
    } finally {
      saving.value = false
    }
  }
  onBeforeUnmount(close)
  onDeactivated(close)
  defineExpose({ open, close })
</script>
