<template>
  <a-modal
    v-model:visible="editorVisible"
    :title="editingId === null ? '新增' : '编辑'"
    :width="760"
    class="mango-auth-modal"
    :on-before-ok="onDataForm"
    :mask-closable="!saving"
    :closable="!saving"
    :cancel-button-props="{ disabled: saving }"
    @cancel="closeEditor"
  >
    <a-form :model="formModel" layout="horizontal" class="mango-auth-form">
      <section v-for="section of authFormGroups" :key="section.key" class="mango-auth-form-section">
        <header class="mango-section-title mango-auth-form-section__header">
          <h3 class="mango-section-heading">{{ section.title }}</h3>
          <span class="mango-section-description">{{ section.description }}</span>
        </header>
        <div class="mango-auth-form-section__fields">
          <a-form-item
            v-for="item of section.items"
            :key="item.key"
            :class="[
              item.required ? 'mango-form-item__require' : 'mango-form-item__no_require',
              {
                'mango-auth-form-item--wide': [
                  'name',
                  'target_address',
                  'public_variable_ids',
                  'custom_code',
                  'notice_group',
                ].includes(item.key),
              },
            ]"
            :label="item.label"
          >
            <template v-if="item.type === 'input'">
              <a-input v-model="item.value" :placeholder="item.placeholder" />
            </template>
            <template v-else-if="item.type === 'number'">
              <a-input-number
                v-model="item.value"
                :min="item.min ?? 0"
                :placeholder="item.placeholder"
              />
            </template>
            <template v-else-if="item.type === 'cascader'">
              <ProjectProductSelect
                v-model="item.value"
                :placeholder="item.placeholder"
                @change="item.key === 'project_product' ? onFormProjectProductChange() : undefined"
              />
            </template>
            <template v-else-if="item.type === 'select' && item.key === 'test_env'">
              <a-select
                v-model="item.value"
                :multiple="item.multiple"
                :max-tag-count="item.multiple ? 1 : undefined"
                :field-names="fieldNames"
                :options="enumStore.environment_type"
                :placeholder="item.placeholder"
                allow-clear
                allow-search
                value-key="key"
                @change="onAuthVariableContextChange"
              />
            </template>
            <template v-else-if="item.key === 'target_address'">
              <div class="mango-auth-variable-field">
                <a-select
                  v-model="item.value"
                  :options="targetOptions"
                  :loading="targetsLoading"
                  :disabled="
                    !projectProductItem?.value || authEnvironment == null || authEnvironment === ''
                  "
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  @clear="item.value = ''"
                />
                <div class="mango-auth-variable-hint"
                  >留空使用被测对象的默认地址，仅在请求地址匹配时加载授权。</div
                >
              </div>
            </template>
            <template v-else-if="item.key === 'public_variable_ids'">
              <div class="mango-auth-variable-field">
                <a-select
                  v-model="item.value"
                  :options="publicVariableOptions"
                  :loading="publicVariablesLoading"
                  :disabled="
                    !projectProductItem?.value || authEnvironment == null || authEnvironment === ''
                  "
                  :placeholder="item.placeholder"
                  multiple
                  allow-clear
                  allow-search
                  :filter-option="false"
                  @search="loadPublicVariableOptions"
                />
                <div class="mango-auth-variable-hint"
                  >仅用于准备认证上下文，同 key 覆盖默认值；Case
                  仍须选择匹配的变量，不会自动切换租户。</div
                >
              </div>
            </template>
            <template v-else-if="item.type === 'select' && item.key === 'auth_type'">
              <a-select
                v-model="item.value"
                :multiple="item.multiple"
                :max-tag-count="item.multiple ? 1 : undefined"
                :field-names="fieldNames"
                :options="enumStore.api_auth_type"
                :placeholder="item.placeholder"
                allow-clear
                value-key="key"
              />
            </template>
            <template v-else-if="item.type === 'select' && item.key === 'api_info'">
              <a-select
                v-model="item.value"
                :multiple="item.multiple"
                :max-tag-count="item.multiple ? 1 : undefined"
                :options="apiInfoOptions"
                :loading="apiInfoLoading"
                :placeholder="item.placeholder"
                allow-clear
                allow-search
              />
            </template>
            <template v-else-if="item.type === 'select' && item.key === 'refresh_mode'">
              <a-select
                v-model="item.value"
                :multiple="item.multiple"
                :max-tag-count="item.multiple ? 1 : undefined"
                :field-names="fieldNames"
                :options="enumStore.api_auth_refresh_mode"
                :placeholder="item.placeholder"
                allow-clear
                value-key="key"
              />
            </template>
            <template v-else-if="item.type === 'select' && item.key === 'time_task'">
              <a-select
                v-model="item.value"
                :multiple="item.multiple"
                :max-tag-count="item.multiple ? 1 : undefined"
                :options="timingOptions"
                :loading="timingLoading"
                :placeholder="item.placeholder"
                allow-clear
                allow-search
              />
            </template>
            <template v-else-if="item.type === 'select' && item.key === 'notice_group'">
              <a-select
                v-model="item.value"
                :multiple="item.multiple"
                :max-tag-count="item.multiple ? 1 : undefined"
                :options="noticeOptions"
                :loading="noticeLoading"
                :placeholder="item.placeholder"
                allow-clear
                allow-search
                value-key="key"
              />
            </template>
            <template v-else-if="item.type === 'code'">
              <CodeEditor
                v-model="item.value"
                :line-height="220"
                :placeholder="item.placeholder"
                :code-style="{ width: '100%' }"
              />
            </template>
          </a-form-item>
        </div>
      </section>
    </a-form>
  </a-modal>
</template>
<script setup lang="ts">
  import { computed, onBeforeUnmount, onDeactivated, reactive, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { fieldNames } from '@/setting'
  import { useEnum } from '@/store/modules/get-enum'
  import useUserStore from '@/store/modules/user'
  import CodeEditor from '@/components/editors/CodeEditor.vue'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import { getOptionId } from '@/utils/business-format'
  import { getApiInfoOptions } from '@/api/apitest/info'
  import { getSystemTimingList } from '@/api/system/time'
  import { getSystemNoticeName } from '@/api/system/notice_group'
  import {
    getApiAuthTargets,
    getApiAuthPublicVariables,
    postApiAuthConfig,
    putApiAuthConfig,
  } from '@/api/apitest/auth-config'
  import { createFormItems, authFormSections } from '../config'
  import { createAuthDraft, normalizeSubmitValue, customAuthCodeExample } from '../auth-form'
  import type { AuthDraft, AuthRecord, EntityId, SelectOption } from '../types'

  const emit = defineEmits<{ (event: 'saved'): void }>()
  const enumStore = useEnum()
  const userStore = useUserStore()
  const editorVisible = ref(false)
  const editingId = ref<number | null>(null)
  const saving = ref(false)
  const formModel = reactive<AuthDraft>(createAuthDraft())
  const formItems = createFormItems(formModel)
  const apiInfoOptions = ref<SelectOption[]>([])
  const timingOptions = ref<SelectOption[]>([])
  const noticeOptions = ref<Array<{ key: number; title: string }>>([])
  const timingLoading = ref(false)
  const noticeLoading = ref(false)
  let session = 0
  let noticeRequest = 0
  let timingRequest = 0
  const publicVariableOptions = ref<Array<{ label: string; value: number }>>([])
  const publicVariablesLoading = ref(false)
  const authEnvironment = computed(() => formItems.find((item) => item.key === 'test_env')?.value)
  let publicVariableRequest = 0
  const targetOptions = ref<Array<{ label: string; value: string }>>([])
  const targetsLoading = ref(false)
  const apiInfoLoading = ref(false)
  let apiInfoRequest = 0
  let targetRequest = 0

  async function loadTargetOptions() {
    const request = ++targetRequest
    const product = getOptionId(projectProductItem.value?.value)
    const env = authEnvironment.value
    targetOptions.value = []
    if (!product || env == null || env === '') {
      targetsLoading.value = false
      return
    }
    targetsLoading.value = true
    try {
      const res = await getApiAuthTargets({ project_product: product, test_env: env })
      if (request === targetRequest) targetOptions.value = res.data || []
    } catch {
      if (request === targetRequest) targetOptions.value = []
    } finally {
      if (request === targetRequest) targetsLoading.value = false
    }
  }

  async function loadPublicVariableOptions(keyword = '') {
    const request = ++publicVariableRequest
    const product = getOptionId(projectProductItem.value?.value)
    const env = authEnvironment.value
    if (!product || env == null || env === '') {
      publicVariableOptions.value = []
      publicVariablesLoading.value = false
      return
    }
    publicVariablesLoading.value = true
    try {
      const res = await getApiAuthPublicVariables({
        project_product: product,
        test_env: env,
        keyword,
        page: 1,
        pageSize: 200,
      })
      if (request !== publicVariableRequest) return
      const selected = formModel.public_variable_ids
      const options = publicVariableOptions.value.filter((item) => selected.includes(item.value))
      const merged = new Map(options.map((item) => [item.value, item]))
      for (const item of res.data || [])
        merged.set(item.id, { value: item.id, label: `${item.name} / ${item.key} (#${item.id})` })
      publicVariableOptions.value = [...merged.values()]
    } catch {
      if (request === publicVariableRequest) publicVariableOptions.value = []
    } finally {
      if (request === publicVariableRequest) publicVariablesLoading.value = false
    }
  }

  function onAuthVariableContextChange() {
    const target = formItems.find((item) => item.key === 'target_address')
    if (target) target.value = ''
    void loadTargetOptions()
    const item = formItems.find((item) => item.key === 'public_variable_ids')
    if (item) item.value = []
    publicVariableOptions.value = []
    void loadPublicVariableOptions()
  }
  const authTypeItem = computed(() => formItems.find((it) => it.key === 'auth_type'))
  const refreshModeItem = computed(() => formItems.find((it) => it.key === 'refresh_mode'))
  const projectProductItem = computed(() => formItems.find((it) => it.key === 'project_product'))
  const isExecutionCheckRefreshMode = computed(() => [0, 2].includes(formModel.refresh_mode))
  const visibleFormItems = computed(() => {
    return formItems.filter((it) => {
      if (it.key === 'api_info') {
        return authTypeItem.value?.value === 0
      }
      if (it.key === 'custom_code') {
        return authTypeItem.value?.value === 1
      }
      if (it.key === 'token_ttl') {
        return [0, 2, 4].includes(formModel.refresh_mode)
      }
      if (it.key === 'refresh_margin') {
        return isExecutionCheckRefreshMode.value
      }
      if (it.key === 'expire_notice_minutes' || it.key === 'notice_group') {
        return refreshModeItem.value?.value === 4
      }
      if (it.key === 'time_task') {
        return [1, 2].includes(formModel.refresh_mode)
      }
      return true
    })
  })
  const authFormGroups = computed(() => {
    const items = new Map(visibleFormItems.value.map((item) => [item.key, item]))
    return authFormSections
      .map((section) => ({
        ...section,
        items: section.itemKeys.flatMap((key) => {
          const item = items.get(key)
          return item ? [item] : []
        }),
      }))
      .filter((section) => section.items.length)
  })

  function validateVisibleForm() {
    const authType = formModel.auth_type
    const refreshMode = formModel.refresh_mode
    if (authType === 0 && !formItems.find((it) => it.key === 'api_info')?.value) {
      Message.error('请选择登录接口')
      return false
    }
    if (authType === 1 && !formItems.find((it) => it.key === 'custom_code')?.value) {
      Message.error('请输入自定义授权代码')
      return false
    }
    if ([1, 2].includes(refreshMode) && !formItems.find((it) => it.key === 'time_task')?.value) {
      Message.error('请选择定时策略')
      return false
    }
    if (refreshMode === 4 && !formItems.find((it) => it.key === 'notice_group')?.value) {
      Message.error('请选择通知组')
      return false
    }
    return visibleFormItems.value.every((it) => (it.validator ? it.validator() : true))
  }

  function invalidateOptions() {
    targetRequest++
    publicVariableRequest++
    apiInfoRequest++
    noticeRequest++
    timingRequest++
    targetsLoading.value = publicVariablesLoading.value = apiInfoLoading.value = false
    noticeLoading.value = timingLoading.value = false
  }
  function closeEditor() {
    session++
    editorVisible.value = false
    invalidateOptions()
  }
  function open(record?: AuthRecord, product: EntityId | null = null) {
    if (saving.value) return
    invalidateOptions()
    session++
    editingId.value = record?.id ?? null
    Object.assign(
      formModel,
      createAuthDraft(record, userStore.selected_environment ?? null, product)
    )
    apiInfoOptions.value = []
    noticeOptions.value = []
    targetOptions.value = []
    publicVariableOptions.value = []
    editorVisible.value = true
    void getTiming()
    loadContextOptions()
  }
  function loadContextOptions() {
    void getApiInfoList(getOptionId(formModel.project_product))
    void getNoticeList(getOptionId(formModel.project_product))
    void loadTargetOptions()
    void loadPublicVariableOptions()
  }
  function onFormProjectProductChange() {
    onAuthVariableContextChange()
    formModel.api_info = null
    formModel.notice_group = null
    void getApiInfoList(getOptionId(formModel.project_product))
    void getNoticeList(getOptionId(formModel.project_product))
  }
  async function onDataForm(): Promise<boolean> {
    if (saving.value || !validateVisibleForm()) return false
    const currentSession = session
    const id = editingId.value
    const payload = normalizeSubmitValue(formModel)
    saving.value = true
    try {
      const response = await (id === null
        ? postApiAuthConfig({ ...payload, status: 1 })
        : putApiAuthConfig({ ...payload, id }))
      emit('saved')
      if (session !== currentSession) return false
      Message.success(response.msg)
      closeEditor()
      return true
    } catch {
      return false
    } finally {
      saving.value = false
    }
  }
  async function getApiInfoList(product?: EntityId | null) {
    const request = ++apiInfoRequest
    apiInfoOptions.value = []
    apiInfoLoading.value = false
    if (!product) return
    apiInfoLoading.value = true
    try {
      const items = await getApiInfoOptions(product, () => request === apiInfoRequest)
      if (request === apiInfoRequest)
        apiInfoOptions.value = items.map((item: { id: number; name: string }) => ({
          label: `${item.id} - ${item.name}`,
          value: item.id,
        }))
    } catch {
      // 公共请求层展示错误，保留草稿以便重试。
    } finally {
      if (request === apiInfoRequest) apiInfoLoading.value = false
    }
  }
  async function getTiming() {
    const request = ++timingRequest
    timingLoading.value = true
    try {
      const response = await getSystemTimingList()
      if (request === timingRequest)
        timingOptions.value = (response.data || []).map((item: { key: number; title: string }) => ({
          label: item.title,
          value: item.key,
        }))
    } catch {
      if (request === timingRequest) timingOptions.value = []
    } finally {
      if (request === timingRequest) timingLoading.value = false
    }
  }
  async function getNoticeList(product?: EntityId | null) {
    const request = ++noticeRequest
    noticeOptions.value = []
    noticeLoading.value = false
    if (!product) return
    noticeLoading.value = true
    try {
      const response = await getSystemNoticeName(Number(product))
      if (request === noticeRequest) noticeOptions.value = response.data || []
    } catch {
      if (request === noticeRequest) noticeOptions.value = []
    } finally {
      if (request === noticeRequest) noticeLoading.value = false
    }
  }
  watch(
    () => formModel.auth_type,
    (value) => {
      if (value === 1 && !formModel.custom_code) formModel.custom_code = customAuthCodeExample
    }
  )
  onBeforeUnmount(closeEditor)
  onDeactivated(closeEditor)
  defineExpose({ open })
</script>
<style scoped>
  .mango-auth-form {
    container-type: inline-size;
  }

  .mango-auth-form-section {
    padding: 14px 0;
    border-bottom: 1px solid var(--m-border);
  }

  .mango-auth-form-section:first-child {
    padding-top: 0;
  }
  .mango-auth-form-section:last-child {
    padding-bottom: 0;
    border-bottom: 0;
  }

  .mango-auth-form-section__header {
    align-items: baseline;
    justify-content: flex-start;
    flex-wrap: wrap;
    gap: var(--m-page-gap);
    margin-bottom: 12px;
  }

  .mango-auth-form-section__fields {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px 16px;
  }

  .mango-auth-form-section__fields :deep(.arco-form-item) {
    flex-wrap: nowrap;
    min-width: 0;
    margin-bottom: 0;
  }

  .mango-auth-form-section__fields :deep(.arco-form-item-label-col) {
    flex: 0 0 136px;
    width: 136px;
    max-width: 136px;
    white-space: nowrap;
  }

  .mango-auth-form-section__fields :deep(.arco-form-item-label-col > label) {
    white-space: nowrap;
  }

  .mango-auth-form-section__fields :deep(.arco-form-item-wrapper-col) {
    flex: 1 1 0;
    width: 0;
    max-width: none;
    min-width: 0;
  }

  .mango-auth-form-item--wide {
    grid-column: 1 / -1;
  }

  @container (max-width: 640px) {
    .mango-auth-form-section__fields {
      grid-template-columns: minmax(0, 1fr);
    }
  }

  .mango-auth-variable-field {
    width: 100%;
    min-width: 0;
  }
  .mango-auth-variable-hint {
    margin-top: 4px;
    color: var(--m-muted);
    font-size: 12px;
  }
</style>
