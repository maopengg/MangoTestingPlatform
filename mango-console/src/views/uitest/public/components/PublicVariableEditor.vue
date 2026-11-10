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
    <a-alert v-if="error" type="error">{{ error }}</a-alert>
    
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
            :options="typeOptions"
            :loading="optionsLoading"
            :disabled="saving || optionsLoading"
            :field-names="fieldNames"
            allow-clear
            @update:model-value="onTypeChange"
            placeholder="请选择变量类型"
          />
        </a-form-item>
        <a-form-item class="mango-simple-form-item" label="被测环境">
          <a-select
            :model-value="draft.test_envs"
            :disabled="saving || optionsLoading"
            :loading="optionsLoading"
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

  import { computed, reactive, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { fieldNames } from '@/setting'
  import { useLiveWorkbenchScope } from '@/hooks/use-live-workbench-scope'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import CodeEditor from '@/components/editors/CodeEditor.vue'
  import { getDataFactoryDatasourceAlias } from '@/api/data-factory'
  import { postUiPublic, putUiPublic } from '@/api/uitest/public'
  import { codeVariableExample } from '../config'
  import {
    COMMON_ENV_VALUE,
    createPublicDraft,
    environmentSelection,
    publicOptionId,
    publicPayload,
    publicResponse,
    readPublicRow,
    readPublicAliases,
    type PublicAlias,
    type PublicId,
    type PublicRow,
    type PublicOption,
  } from '../public-records'
  const props = defineProps<{
    typeOptions: PublicOption[]
    environments: PublicOption[]
    optionsLoading: boolean
    optionsError: string
  }>()
  const emit = defineEmits<{
    (event: 'saved'): void
    (event: 'busy-change', value: boolean): void
    (event: 'retry-options'): void
  }>()
  const visible = ref(false),
    saving = ref(false),
    editingId = ref<PublicId | null>(null),
    error = ref('')
  const draft = reactive(createPublicDraft())
  const aliasOptions = ref<PublicAlias[]>([]),
    aliasesLoading = ref(false),
    aliasesFailed = ref(false)
  const environmentOptions = computed(() => [
    { key: COMMON_ENV_VALUE, title: '环境通用' },
    ...props.environments,
  ])
  let session = 0,
    aliasRequest = 0
  let retainedAlias: PublicAlias | null = null
  function resetAliases() {
    ++aliasRequest
    aliasOptions.value = []
    aliasesLoading.value = false
    aliasesFailed.value = false
  }
  function close() {
    ++session
    visible.value = false
    editingId.value = null
    error.value = ''
    retainedAlias = null
    resetAliases()
    Object.assign(draft, createPublicDraft())
  }
  const scope = useLiveWorkbenchScope(() => null, { invalidate: close, resume: () => {} })
  async function loadAliases() {
    const product = publicOptionId(draft.project_product)
    resetAliases()
    if (retainedAlias && String(retainedAlias.id) === String(draft.datasource_alias))
      aliasOptions.value = [{ ...retainedAlias, disabled: true }]
    if (!visible.value || !scope.available() || draft.type !== 1 || product === null) return
    const valid = scope.capture(),
      token = session,
      request = aliasRequest
    const current = () => valid() && visible.value && token === session && request === aliasRequest
    aliasesLoading.value = true
    try {
      const rows = readPublicAliases(
        await getDataFactoryDatasourceAlias({
          project_product: product,
          status: 1,
          page: 1,
          pageSize: 999,
        })
      )
      if (!current()) return
      aliasOptions.value = rows
      if (
        retainedAlias &&
        String(retainedAlias.id) === String(draft.datasource_alias) &&
        !rows.some((row) => String(row.id) === String(retainedAlias?.id))
      )
        aliasOptions.value.push({ ...retainedAlias, disabled: true })
    } catch (loadFailure0) {
      if (current()) (reportLoadError(loadFailure0, "加载失败，请重试", false), aliasesFailed.value = true)
    } finally {
      if (current()) aliasesLoading.value = false
    }
  }
  function open(record: PublicRow | null = null, product: PublicId | null = null) {
    if (saving.value || !scope.available()) return
    close()
    const row = record === null ? null : readPublicRow(record)
    editingId.value = row?.id ?? null
    Object.assign(draft, createPublicDraft(row, product))
    retainedAlias = row?.datasource_alias ? { ...row.datasource_alias } : null
    visible.value = true
    void loadAliases()
  }
  function onProductChange(value: PublicId | PublicId[] | null) {
    if (saving.value || !visible.value) return
    draft.project_product = Array.isArray(value) ? [...value] : value
    draft.datasource_alias = null
    retainedAlias = null
    void loadAliases()
  }
  function onTypeChange(value: number | string | null | undefined) {
    if (saving.value || !visible.value) return
    draft.type = value == null || value === '' ? null : Number(value)
    if (draft.type !== 1) {
      draft.datasource_alias = null
      resetAliases()
    } else void loadAliases()
    if (draft.type === 2 && !draft.value) draft.value = codeVariableExample
    else if (draft.type !== 2 && draft.value === codeVariableExample) draft.value = ''
  }
  function onEnvironmentChange(value: PublicId[]) {
    if (!saving.value) draft.test_envs = environmentSelection(value)
  }
  async function save(): Promise<boolean> {
    if (saving.value || !visible.value || !scope.available()) return false
    let payload: ReturnType<typeof publicPayload>
    try {
      payload = publicPayload(draft, editingId.value)
    } catch (cause) {
      error.value = cause instanceof Error ? cause.message : '请检查变量配置'
      return false
    }
    if (
      props.optionsLoading ||
      props.optionsError ||
      (draft.type === 1 && (aliasesLoading.value || aliasesFailed.value))
    ) {
      error.value = '请等待选项加载完成；加载失败时请先重试'
      return false
    }
    const valid = scope.capture(),
      version = session,
      isAdd = editingId.value === null
    const current = () => valid() && visible.value && version === session
    saving.value = true
    error.value = ''
    emit('busy-change', true)
    try {
      publicResponse(await (isAdd ? postUiPublic(payload) : putUiPublic(payload)))
      if (!current()) return false
      Message.success('保存成功')
      close()
      emit('saved')
      return true
    } catch {
      if (current()) error.value = '保存失败，草稿已保留，请重试'
      return false
    } finally {
      saving.value = false
      emit('busy-change', false)
    }
  }
  watch(
    visible,
    (value) => {
      if (!value) {
        ++session
        resetAliases()
      }
    },
    { flush: 'sync' }
  )
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
