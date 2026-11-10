<template>
  <a-modal
    :visible="visible"
    :title="draft.id !== null ? '编辑 Pytest 仓库' : '新增 Pytest 仓库'"
    :width="760"
    :ok-loading="saving"
    unmount-on-close
    :on-before-ok="save"
    @cancel="close"
    @update:visible="onVisibleChange"
  >
    <a-form
      :model="draft"
      :disabled="saving"
      class="mango-pytest-repository-page__editor-form"
      layout="horizontal"
      :label-col-props="{ span: 9 }"
      :wrapper-col-props="{ span: 15 }"
    >
      <section class="mango-pytest-repository-page__form-section">
        <div class="mango-section-title">
          <div class="mango-section-title__main">
            <h2>仓库配置</h2>
          </div>
        </div>
        <a-grid :cols="2" :col-gap="16" :row-gap="0">
          <a-grid-item
            ><a-form-item label="仓库名称" required><a-input v-model="draft.name" /></a-form-item
          ></a-grid-item>
          <a-grid-item
            ><a-form-item label="Git 平台" required
              ><a-select v-model="draft.provider" :options="providerOptions" /></a-form-item
          ></a-grid-item>
          <a-grid-item :span="2"
            ><a-form-item label="仓库地址" required>
              <a-input
                v-model="draft.repo_url"
                placeholder="https://git.example.com/group/project.git" /></a-form-item
          ></a-grid-item>
          <a-grid-item
            ><a-form-item label="API 地址"
              ><a-input
                v-model="draft.api_base_url"
                placeholder="留空则根据仓库地址自动填写" /></a-form-item
          ></a-grid-item>
          <a-grid-item
            ><a-form-item label="远程项目标识"
              ><a-input v-model="draft.remote_project" placeholder="group/project" /></a-form-item
          ></a-grid-item>
          <a-grid-item
            ><a-form-item label="默认分支" required
              ><a-input v-model="draft.default_branch" /></a-form-item
          ></a-grid-item>
        </a-grid>
      </section>

      <section class="mango-pytest-repository-page__form-section">
        <div class="mango-section-title">
          <div class="mango-section-title__main">
            <h2>访问凭证</h2>
            <p>
              公开仓库选择“无需认证”，也可清空认证方式。已有凭证会在保存后移除；保留认证方式时，Token
              / 密码留空表示不修改。推送需要写入权限。
            </p>
          </div>
        </div>
        <a-grid :cols="2" :col-gap="16" :row-gap="0">
          <a-grid-item
            ><a-form-item label="认证方式"
              ><a-select
                v-model="draft.credential_auth_type"
                allow-clear
                placeholder="无需认证（公开仓库）"
                :options="credentialTypeOptions" /></a-form-item
          ></a-grid-item>
          <a-grid-item v-if="draft.credential_auth_type === 'username_password'"
            ><a-form-item label="用户名"
              ><a-input v-model="draft.credential_username" /></a-form-item
          ></a-grid-item>
          <a-grid-item v-if="draft.credential_auth_type && draft.credential_auth_type !== 'none'"
            ><a-form-item label="Token / 密码"
              ><a-input-password
                v-model="draft.credential_secret"
                :placeholder="draft.id ? '留空表示不修改' : '请输入访问密钥'" /></a-form-item
          ></a-grid-item>
        </a-grid>
      </section>
    </a-form>
  </a-modal>
</template>

<script setup lang="ts">
  import { onActivated, onBeforeUnmount, onDeactivated, onMounted, reactive, ref, watch } from 'vue'
  import { useRoute } from 'vue-router'
  import { Message } from '@arco-design/web-vue'
  import useUserStore from '@/store/modules/user'
  import { savePytestRepository } from '@/api/pytest/repository'
  import { credentialTypeOptions, providerOptions } from '../config'
  import {
    emptyRepositoryDraft,
    readRepository,
    repositoryDraft,
    repositoryPayload,
    repositoryResponse,
  } from '../records'
  import type { PytestRepositoryInput } from '@/api/pytest/repository'

  const props = withDefaults(defineProps<{ busyIds?: number[] }>(), { busyIds: () => [] })
  const emit = defineEmits<{
    (event: 'saved', id: number | null): void
    (event: 'busy', id: number | null, value: boolean): void
  }>()
  const user = useUserStore(),
    route = useRoute()
  const visible = ref(false),
    saving = ref(false),
    draft = reactive(emptyRepositoryDraft())
  let version = 0,
    active = true,
    disposed = false
  const available = () =>
    !disposed && active && (typeof document === 'undefined' || !document.hidden)
  const current = (window: number) => available() && visible.value && window === version
  function close(): void {
    version++
    visible.value = false
    Object.assign(draft, emptyRepositoryDraft())
  }
  function onVisibleChange(value: boolean): void {
    if (!value) close()
  }
  function open(value?: unknown): void {
    if (!available() || saving.value) return
    let next = emptyRepositoryDraft()
    try {
      if (value != null) next = repositoryDraft(readRepository(value))
    } catch {
      Message.error('仓库数据格式不正确，请刷新列表')
      return
    }
    if (next.id !== null && props.busyIds.includes(next.id)) return
    close()
    Object.assign(draft, next)
    visible.value = true
  }
  async function save(): Promise<boolean> {
    if (
      !current(version) ||
      saving.value ||
      (draft.id !== null && props.busyIds.includes(draft.id))
    )
      return false
    let payload: PytestRepositoryInput
    try {
      payload = repositoryPayload(draft)
    } catch (error) {
      Message.warning(error instanceof Error ? error.message : '请检查仓库配置')
      return false
    }
    const window = version,
      id = draft.id
    saving.value = true
    emit('busy', id, true)
    try {
      repositoryResponse(await savePytestRepository(payload))
      if (!current(window)) return false
      close()
      Message.success('仓库保存成功')
      emit('saved', id)
      return true
    } catch {
      if (current(window)) Message.error('仓库保存失败，请重试')
      return false
    } finally {
      saving.value = false
      emit('busy', id, false)
    }
  }
  watch(
    () => draft.credential_auth_type,
    () => {
      draft.credential_secret = ''
    },
    { flush: 'sync' }
  )
  watch(
    () => [user.userId, user.roleId, user.token, user.selected_environment, route.fullPath],
    close,
    { flush: 'sync' }
  )
  function visibilityChanged(): void {
    if (typeof document !== 'undefined' && document.hidden) close()
  }
  onMounted(() => {
    if (typeof document !== 'undefined')
      document.addEventListener('visibilitychange', visibilityChanged)
  })
  onActivated(() => {
    active = true
  })
  onDeactivated(() => {
    active = false
    close()
  })
  onBeforeUnmount(() => {
    disposed = true
    close()
    if (typeof document !== 'undefined')
      document.removeEventListener('visibilitychange', visibilityChanged)
  })
  defineExpose({ open, close })
</script>

<style scoped lang="less">
  .mango-pytest-repository-page__editor-form {
    display: flex;
    max-height: calc(100vh - 180px);
    overflow-y: auto;
    flex-direction: column;
  }

  .mango-pytest-repository-page__form-section {
    padding: 0 0 2px;
  }

  .mango-pytest-repository-page__form-section + .mango-pytest-repository-page__form-section {
    margin-top: 8px;
    padding-top: 12px;
    border-top: 1px solid var(--m-border);
  }

  .mango-pytest-repository-page__form-section :deep(.arco-form-item) {
    margin-bottom: 8px;
  }

  .mango-pytest-repository-page__form-section :deep(.arco-form-item-label-col.arco-col) {
    width: 112px;
    max-width: 112px;
    flex: 0 0 112px;
  }

  .mango-pytest-repository-page__form-section :deep(.arco-form-item-label) {
    white-space: nowrap;
  }

  .mango-pytest-repository-page__form-section :deep(.arco-form-item-wrapper-col.arco-col) {
    width: auto;
    max-width: none;
    flex: 1 1 0;
  }

  .mango-pytest-repository-page__form-section :deep(.arco-grid-item:last-child .arco-form-item) {
    margin-bottom: 0;
  }
</style>
