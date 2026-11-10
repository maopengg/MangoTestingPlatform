<template>
  <a-modal
    modal-class="mango-simple-form-modal"
    :visible="visible"
    :title="recordId === null ? '新增灰度仓库' : '编辑灰度仓库'"
    :width="560"
    :ok-loading="saving"
    :on-before-ok="save"
    :on-before-cancel="canCancel"
    :mask-closable="!saving"
    :esc-to-close="!saving"
    @update:visible="onVisibleChange"
  >
    <a-alert v-if="saveError" type="error"
      >保存失败或结果未确认，输入已保留，请核对后重试。</a-alert
    >
    
    <a-form auto-label-width class="mango-repository-form mango-simple-form" :model="form" layout="horizontal" :disabled="saving">
      <a-form-item label="仓库名称" class="mango-form-item__require mango-simple-form-item"
        ><a-input
          v-model="form.name"
          placeholder="请输入仓库名称"
          data-testid="qa-views-gray-repository-input-请输入仓库名称-2"
      /></a-form-item>
      <a-form-item label="仓库地址" class="mango-form-item__require mango-simple-form-item"
        ><a-input
          v-model="form.repo_url"
          placeholder="请输入仓库地址"
          data-testid="qa-views-gray-repository-input-请输入仓库地址-2"
      /></a-form-item>
      <a-form-item label="平台类型" class="mango-form-item__require mango-simple-form-item"
        ><a-select
          v-model="form.provider"
          :options="providerOptions"
          placeholder="请选择平台类型"
          data-testid="qa-views-gray-repository-select-请选择平台类型"
      /></a-form-item>
      <a-form-item label="平台域名" class="mango-form-item__require mango-simple-form-item"
        ><a-input
          v-model="form.api_base_url"
          placeholder="请输入平台域名"
          data-testid="qa-views-gray-repository-input-请输入平台域名"
      /></a-form-item>
      <a-form-item class="mango-simple-form-item" label="访问令牌"
        ><a-input-password
          v-model="form.access_token"
          :placeholder="recordId === null ? '请输入访问令牌' : '留空保留原令牌'"
          data-testid="qa-views-gray-repository-input-password-请输入访问令牌"
      /></a-form-item>
      <a-form-item label="测试环境" class="mango-form-item__require mango-simple-form-item"
        ><a-select
          v-model="form.test_env"
          :options="environmentOptions"
          :field-names="{ value: 'key', label: 'title' }"
          :loading="enumLoading"
          allow-search
          placeholder="请选择测试环境"
          data-testid="qa-views-gray-repository-select-请选择测试环境"
      /></a-form-item>
      <a-form-item label="分支" class="mango-form-item__require mango-simple-form-item"
        ><a-input
          v-model="form.branch"
          placeholder="请输入分支"
          data-testid="qa-views-gray-repository-input-请输入分支-2"
      /></a-form-item>
      <a-form-item label="配置目录" class="mango-form-item__require mango-simple-form-item"
        ><a-input-tag
          v-model="form.config_dirs"
          allow-clear
          placeholder="输入仓库内相对目录后回车，例如 app/config"
          data-testid="qa-views-gray-repository-input-tag-输入仓库内相对目录后回车-例如-clm-api-nacos"
      /></a-form-item>
      <a-form-item class="mango-simple-form-item" label="启用状态"
        ><a-switch v-model="form.status" :checked-value="1" :unchecked-value="0"
      /></a-form-item>
    </a-form>
  </a-modal>
</template>
<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { computed, onActivated, onBeforeUnmount, onDeactivated, reactive, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { postGrayRepository, putGrayRepository } from '@/api/gray'
  import { useEnum } from '@/store/modules/get-enum'
  import { providerOptions } from '../config'
  import {
    COMMON_ENV,
    contextOf,
    createForm,
    formPayload,
    normalizeDirs,
    object,
    positiveId,
    validation,
    type ContextSource,
    type RepositoryRow,
  } from '../records'
  const props = defineProps<{ contextKey: ContextSource; blocked: boolean }>()
  const emit = defineEmits<{
    (e: 'saved', id: number): void
    (e: 'visible', value: boolean): void
    (e: 'busy', value: boolean): void
  }>()
  const contextKey = computed(() => contextOf(props.contextKey)),
    enums = useEnum()
  const visible = ref(false),
    recordId = ref<number | null>(null),
    form = reactive(createForm()),
    saving = ref(false),
    saveError = ref(false),
    enumLoading = ref(false),
    enumError = ref(false)
  const environmentOptions = computed(() => [
    { key: COMMON_ENV, title: '环境通用' },
    ...(Array.isArray(enums.environment_type) ? enums.environment_type : []),
  ])
  let active = true,
    generation = 0,
    enumSequence = 0
  function reset() {
    ++generation
    ++enumSequence
    visible.value = false
    recordId.value = null
    Object.assign(form, createForm())
    saveError.value = false
    enumLoading.value = false
    enumError.value = false
  }
  function canCancel() {
    return !saving.value
  }
  function onVisibleChange(value: boolean) {
    if (!value && !saving.value) reset()
  }
  function open(record?: RepositoryRow) {
    if (!active || props.blocked || saving.value || (record && !positiveId(record.id))) return
    reset()
    recordId.value = record?.id ?? null
    Object.assign(form, createForm(record))
    visible.value = true
    void loadEnums()
  }
  async function loadEnums() {
    if (!active || !visible.value || saving.value) return
    const version = generation,
      sequence = ++enumSequence,
      current = () => active && visible.value && version === generation && sequence === enumSequence
    enumLoading.value = true
    enumError.value = false
    try {
      await enums.getEnum()
    } catch (loadFailure0) {
      if (current()) (reportLoadError(loadFailure0, "加载失败，请重试", false), enumError.value = true)
    } finally {
      if (current()) enumLoading.value = false
    }
  }
  async function save(): Promise<boolean> {
    if (!active || !visible.value || saving.value || props.blocked) return false
    const message = validation(form)
    if (message) {
      Message.warning(message)
      return false
    }
    const version = generation,
      id = recordId.value,
      request = formPayload(form, id),
      current = () => active && visible.value && version === generation
    saving.value = true
    saveError.value = false
    try {
      const response = await (id === null
        ? postGrayRepository(request)
        : putGrayRepository(request))
      if (!current()) return false
      const row = object(response.data)
      if (
        response.code !== 200 ||
        !positiveId(row.id) ||
        (id !== null && row.id !== id) ||
        row.name !== request.name ||
        row.repo_url !== request.repo_url ||
        row.provider !== request.provider ||
        row.api_base_url !== request.api_base_url ||
        row.test_env !== request.test_env ||
        row.branch !== request.branch ||
        row.status !== request.status ||
        !Array.isArray(row.config_dirs) ||
        JSON.stringify(normalizeDirs(row.config_dirs)) !== JSON.stringify(request.config_dirs)
      )
        throw Error('Invalid repository acknowledgment')
      const savedId = row.id
      reset()
      Message.success('保存成功')
      emit('saved', savedId)
    } catch {
      if (current()) saveError.value = true
    } finally {
      saving.value = false
    }
    return false
  }
  watch(contextKey, reset, { flush: 'sync' })
  watch(visible, (value) => emit('visible', value), { flush: 'sync' })
  watch(saving, (value) => emit('busy', value), { flush: 'sync' })
  onDeactivated(() => {
    active = false
    reset()
  })
  onActivated(() => {
    active = true
  })
  onBeforeUnmount(() => {
    active = false
    reset()
  })
  defineExpose({ open })
</script>
<style scoped lang="less">
  .mango-repository-form :deep(.arco-form-item) {
    margin-bottom: 12px;
  }
</style>
