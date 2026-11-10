<template>
  <a-modal
    modal-class="mango-simple-form-modal"
    unmount-on-close
    v-model:visible="visible"
    :title="editingId === null ? '新增全局变量' : '编辑全局变量'"
    :width="560"
    :on-before-ok="save"
    :ok-loading="saving"
    :closable="!saving"
    :mask-closable="!saving"
    :esc-to-close="!saving"
    :cancel-button-props="{ disabled: saving }"
    @cancel="close"
  >
    <a-form auto-label-width :model="draft" layout="horizontal" class="mango-public-editor mango-simple-form">
      <div class="mango-public-editor__fields mango-simple-form-fields">
        <a-form-item label="项目/产品" class="mango-form-item__require mango-simple-form-item">
          <ProjectProductSelect
            :model-value="draft.project_product"
            :disabled="saving"
            placeholder="请选择项目/产品"
            @update:model-value="onProductChange"
          />
        </a-form-item>
        <a-form-item label="类型" class="mango-form-item__require mango-simple-form-item">
          <a-select
            :model-value="draft.type"
            :disabled="saving"
            :options="enumStore.api_public_type"
            :field-names="fieldNames"
            allow-clear
            @update:model-value="onTypeChange"
            placeholder="请选择变量类型"
          />
        </a-form-item>
        <a-form-item class="mango-simple-form-item" label="被测环境">
          <a-select
            :model-value="draft.test_envs"
            :disabled="saving"
            :options="environmentOptions"
            :field-names="fieldNames"
            multiple
            :max-tag-count="1"
            allow-clear
            @update:model-value="onEnvironmentChange"
          />
        </a-form-item>
        <a-form-item label="参数名称" class="mango-form-item__require mango-simple-form-item">
          <a-input v-model="draft.name" :disabled="saving" placeholder="请输入参数名称" />
        </a-form-item>
      </div>
      <a-form-item label="key" class="mango-form-item__require mango-simple-form-item">
        <a-input
          v-model="draft.key"
          :disabled="saving"
          placeholder="SQL 多值用英文逗号分隔；代码变量 key 仅作标识"
        />
      </a-form-item>
      <a-form-item v-if="draft.type === 1" label="逻辑数据库" class="mango-form-item__require mango-simple-form-item">
        <div class="mango-public-editor__alias">
          <a-select
            v-model="draft.datasource_alias"
            :disabled="saving || aliasesLoading"
            :loading="aliasesLoading"
            :options="aliasOptions"
            :field-names="{ value: 'id', label: 'name' }"
            allow-clear
            allow-search
            placeholder="请选择逻辑数据库"
          />
          <a-button v-if="aliasesFailed" size="small" :loading="aliasesLoading" @click="loadAliases"
            >重试</a-button
          >
        </div>
      </a-form-item>

      <a-form-item
        :label="draft.type === 2 ? '自定义代码' : 'value'"
        class="mango-form-item__require mango-simple-form-item"
      >
        <CodeEditor
          v-if="draft.type === 2"
          v-model="draft.value"
          :readonly="saving"
          :line-height="260"
          language="python"
        />
        <a-textarea
          v-else
          v-model="draft.value"
          :disabled="saving"
          :auto-size="{ minRows: 4, maxRows: 9 }"
          placeholder="自定义变量填写原始值，SQL 变量填写查询一行数据的语句"
        />
      </a-form-item>
    </a-form>
  </a-modal>
</template>
<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { computed, onBeforeUnmount, onDeactivated, reactive, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { fieldNames } from '@/setting'
  import { useEnum } from '@/store/modules/get-enum'
  import { getOptionId } from '@/utils/business-format'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import CodeEditor from '@/components/editors/CodeEditor.vue'
  import { getDataFactoryDatasourceAlias } from '@/api/data-factory'
  import { postApiPublic, putApiPublic } from '@/api/apitest/public'
  import { COMMON_ENV_VALUE, codeVariableExample } from '../config'
  import {
    createPublicDraft,
    normalizeEnvironmentSelection,
    publicPayload,
    publicValidation,
  } from '../form'
  import type { PublicDatasource, PublicEntityId, PublicEnvironment, PublicRecord } from '../types'
  const emit = defineEmits<{ (event: 'saved'): void }>()
  const enumStore = useEnum(),
    visible = ref(false),
    saving = ref(false),
    editingId = ref<number | null>(null)
  const draft = reactive(createPublicDraft())
  const aliasOptions = ref<PublicDatasource[]>([]),
    aliasesLoading = ref(false),
    aliasesFailed = ref(false)
  const environmentOptions = computed(() => [
    { key: COMMON_ENV_VALUE, title: '环境通用' },
    ...enumStore.environment_type,
  ])
  let session = 0,
    aliasRequest = 0
  let retainedAlias: PublicDatasource | null = null
  function close() {
    ++session
    ++aliasRequest
    visible.value = false
    aliasesLoading.value = false
  }
  function resetAliases() {
    ++aliasRequest
    aliasOptions.value = []
    aliasesLoading.value = false
    aliasesFailed.value = false
  }
  async function loadAliases() {
    const product = getOptionId(draft.project_product)
    resetAliases()
    if (retainedAlias && String(retainedAlias.id) === String(draft.datasource_alias)) {
      aliasOptions.value = [{ ...retainedAlias, disabled: true }]
    }
    if (!visible.value || draft.type !== 1 || product == null || product === '') return
    const token = session,
      request = aliasRequest
    aliasesLoading.value = true
    try {
      const response = await getDataFactoryDatasourceAlias({
        project_product: product,
        status: 1,
        page: 1,
        pageSize: 999,
      })
      if (!visible.value || token !== session || request !== aliasRequest) return
      aliasOptions.value = ((response.data || []) as PublicDatasource[]).filter(
        (item) => Number(item.status) === 1 && [0, 1, 2].includes(Number(item.db_type))
      )
      if (
        retainedAlias &&
        String(retainedAlias.id) === String(draft.datasource_alias) &&
        !aliasOptions.value.some((item) => String(item.id) === String(retainedAlias?.id))
      ) {
        aliasOptions.value.push({ ...retainedAlias, disabled: true })
      }
    } catch (loadFailure0) {
      if (visible.value && token === session && request === aliasRequest) (reportLoadError(loadFailure0, "加载失败，请重试", false), aliasesFailed.value = true)
    } finally {
      if (token === session && request === aliasRequest) aliasesLoading.value = false
    }
  }
  function open(record?: PublicRecord, product: PublicEntityId | null = null) {
    if (saving.value) return
    ++session
    editingId.value = record?.id ?? null
    Object.assign(draft, createPublicDraft(record, product))
    retainedAlias =
      record?.datasource_alias && typeof record.datasource_alias === 'object'
        ? { ...record.datasource_alias }
        : null
    resetAliases()
    visible.value = true
    return loadAliases()
  }
  function onProductChange(value: PublicEntityId | PublicEntityId[] | null) {
    if (saving.value || !visible.value) return
    draft.project_product = value
    draft.datasource_alias = null
    retainedAlias = null
    return loadAliases()
  }
  function onTypeChange(value: number | null | undefined) {
    if (saving.value || !visible.value) return
    draft.type = value ?? null
    if (value !== 1) {
      draft.datasource_alias = null
      resetAliases()
    } else void loadAliases()
    if (value === 2 && !draft.value) draft.value = codeVariableExample
    else if (value !== 2 && draft.value === codeVariableExample) draft.value = ''
  }
  function onEnvironmentChange(value: PublicEnvironment[]) {
    if (!saving.value) draft.test_envs = normalizeEnvironmentSelection(value)
  }
  async function save(): Promise<boolean> {
    if (saving.value || !visible.value) return false
    const error = publicValidation(draft)
    if (error) {
      Message.error(error)
      return false
    }
    if (draft.type === 1 && (aliasesLoading.value || aliasesFailed.value)) {
      Message.warning('请等待逻辑数据库加载完成，失败时请重试')
      return false
    }
    const token = session,
      id = editingId.value,
      payload = publicPayload(draft)
    saving.value = true
    try {
      const response = await (id === null
        ? postApiPublic({ ...payload, status: 1 })
        : putApiPublic({ ...payload, id }))
      if (!visible.value || token !== session) return false
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
  watch(
    visible,
    (value) => {
      if (!value) {
        ++session
        ++aliasRequest
        aliasesLoading.value = false
      }
    },
    { flush: 'sync' }
  )
  onDeactivated(close)
  onBeforeUnmount(close)
  defineExpose({ open, close })
</script>
<style scoped>
  .mango-public-editor__fields {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0 var(--m-page-gap);
  }
  .mango-public-editor__alias {
    display: flex;
    align-items: center;
    gap: var(--m-page-gap);
    width: 100%;
  }
  .mango-public-editor__alias :deep(.arco-select) {
    flex: 1;
    min-width: 0;
  }
</style>
