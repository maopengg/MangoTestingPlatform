<template>
  <a-modal
    modal-class="mango-simple-form-modal"
    v-model:visible="visible"
    :title="editingId === null ? '新增数据库' : '编辑数据库'"
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
        v-for="item in visibleFields"
        :key="item.key"
        :label="item.label"
        :class="item.required ? 'mango-form-item__require' : 'mango-form-item__no_require'"
      >
        <a-select
          v-if="item.key === 'source_category'"
          v-model="draft.source_category"
          :field-names="fieldNames"
          :options="enumStore.data_source_category"
          :loading="optionsLoading"
          :placeholder="item.placeholder"
          @change="onCategoryChange"
        />
        <a-select
          v-else-if="item.key === 'db_type'"
          v-model="draft.db_type"
          :field-names="fieldNames"
          :options="sourceTypeOptions"
          :loading="optionsLoading"
          allow-search
          :placeholder="item.placeholder"
          @change="onSourceTypeChange"
        />
        <a-input-password
          v-else-if="item.key === 'password'"
          v-model="draft.password"
          :placeholder="item.placeholder"
        />
        <a-input v-else v-model="draft[item.key]" :placeholder="item.placeholder" />
      </a-form-item>
      <a-form-item class="mango-simple-form-item" v-if="draft.db_type === 10" label="TLS"
        ><a-switch v-model="draft.extra_config.ssl" size="small"
      /></a-form-item>
      <template v-else-if="draft.db_type === 20">
        <a-form-item class="mango-simple-form-item" label="访问协议"
          ><a-select v-model="draft.extra_config.scheme" :options="['http', 'https']"
        /></a-form-item>
        <a-form-item class="mango-simple-form-item" label="路径前缀"
          ><a-input
            v-model="draft.extra_config.path_prefix"
            placeholder="例如 elasticsearch，可留空"
        /></a-form-item>
        <a-form-item class="mango-simple-form-item" label="校验证书"
          ><a-switch v-model="draft.extra_config.verify_certs" size="small"
        /></a-form-item>
      </template>
    </a-form>
  </a-modal>
</template>
<script setup lang="ts">
  import { computed, reactive, ref } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { postSystemDataSource, putSystemDataSource } from '@/api/system/data_source'
  import { useEnum } from '@/store/modules/get-enum'
  import { fieldNames } from '@/setting'
  import { sourceFormFields, sourceDefaultPorts } from '../config'
  import { createSourceDraft, sourcePayload, sourceExtraConfig } from '../form'
  import { useSourceScope } from '../composables/useSourceScope'
  import type { DataSourceRecord } from '../types'
  defineProps<{ optionsLoading: boolean }>()
  const emit = defineEmits<{ (event: 'saved'): void }>()
  const enumStore = useEnum()
  const visible = ref(false)
  const saving = ref(false)
  const editingId = ref<number | null>(null)
  const draft = reactive(createSourceDraft())
  let session = 0
  const scope = useSourceScope(close)
  const sourceTypeOptions = computed(() =>
    (enumStore.data_source_type || []).filter(
      (item) =>
        enumStore.data_source_type_category[item.key] === draft.source_category &&
        ![3, 4].includes(Number(item.key))
    )
  )
  const visibleFields = computed(() =>
    sourceFormFields.filter((item) => {
      if (item.key === 'file_path') return draft.db_type === 2
      if (['host', 'port', 'user', 'password'].includes(item.key)) return draft.db_type !== 2
      return true
    })
  )
  function onCategoryChange() {
    draft.db_type = sourceTypeOptions.value.length ? Number(sourceTypeOptions.value[0].key) : null
    onSourceTypeChange()
  }
  function onSourceTypeChange() {
    if (draft.db_type !== null && sourceDefaultPorts[draft.db_type] !== undefined)
      draft.port = sourceDefaultPorts[draft.db_type]
    draft.extra_config = sourceExtraConfig(draft.db_type)
  }
  function open(record?: DataSourceRecord) {
    if (saving.value || !scope.isActive()) return
    ++session
    editingId.value = record?.id ?? null
    Object.assign(draft, createSourceDraft(record))
    visible.value = true
  }
  function close() {
    ++session
    visible.value = false
    draft.password = ''
  }
  async function save(): Promise<boolean> {
    if (!visible.value || saving.value || !scope.isActive()) return false
    for (const field of visibleFields.value) {
      if (field.key === 'source_category' || field.key === 'password') continue
      const value = draft[field.key]
      if (
        value === null ||
        value === undefined ||
        value === '' ||
        (field.key === 'display_name' && !String(value).trim())
      ) {
        Message.error(field.placeholder)
        return false
      }
    }
    const current = session,
      version = scope.snapshot(),
      id = editingId.value,
      payload = sourcePayload(draft)
    saving.value = true
    try {
      const response = await (id === null
        ? postSystemDataSource(payload)
        : putSystemDataSource({ ...payload, id }))
      if (!scope.current(version) || current !== session) return false
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
  defineExpose({ open, close })
</script>
