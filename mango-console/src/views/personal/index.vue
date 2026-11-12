<template>
  <TableBody class="mango-personal-workbench">
    <template #header>
      <TableHeader title="个人中心" />
    </template>
    <main class="mango-personal-page">
      <section class="mango-section-card mango-personal-profile" :aria-busy="loading">
        <div class="mango-section-title"><h2>个人资料</h2></div>
        <MangoPanelSpin :loading="loading" class="mango-personal-profile__loading">
        <header class="mango-personal-profile__header">
          <div class="mango-personal-profile__identity">
            <a-avatar :size="48" class="mango-personal-profile__avatar">
              <icon-user />
            </a-avatar>
            <div class="mango-personal-profile__name">
              <h2 :title="profile?.name">{{ profile?.name || '-' }}</h2>
              <p :title="profile?.username">{{ profile?.username || '-' }}</p>
            </div>
          </div>
        </header>

        <dl class="mango-personal-profile__details">
          <div class="mango-personal-profile__detail">
            <dt>角色</dt>
            <dd :title="profile?.roleName || '未分配角色'">
              <a-tag size="small">{{ profile?.roleName || '未分配角色' }}</a-tag>
            </dd>
          </div>
          <div class="mango-personal-profile__detail">
            <dt>部门</dt>
            <dd :title="profile?.departmentNames.join('、') || '-'">{{ profile?.departmentNames.join('、') || '-' }}</dd>
          </div>
          <div class="mango-personal-profile__detail">
            <dt>登录 IP</dt>
            <dd :title="profile?.ip || ''">{{ profile?.ip || '-' }}</dd>
          </div>
        </dl>

        <div class="mango-personal-profile__actions">
          <a-button
            size="small"
            :disabled="!profile || loading || loggingOut"
            :loading="loggingOut"
            @click="openPassword"
            data-testid="qa-views-personal-button-修改密码"
          >
            修改密码
          </a-button>
          <a-button size="small" :disabled="!profile || loading || loggingOut" @click="openResetPassword">
            重置密码
          </a-button>
        </div>
        </MangoPanelSpin>
      </section>

      <UserConfigPanel />
    </main>
  </TableBody>
  <PasswordChangeDialog ref="passwordDialog" :user-id="profile?.id || 0" :requires-email-migration="profile?.requiresEmailMigration || false"
    :context-version="contextVersion" :is-context-current="isContextCurrent" @changed="handlePasswordChanged" />
  <PasswordResetDialog ref="resetPasswordDialog" :username="profile?.username || ''" :requires-email-migration="profile?.requiresEmailMigration || false"
    :context-version="contextVersion" :is-context-current="isContextCurrent" @reset="handlePasswordReset" />
</template>

<script lang="ts" setup>
import { reportLoadError } from '@/utils/load-error'

  import useUserStore from '@/store/modules/user'
  import { onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from 'vue'
  import { useRoute } from 'vue-router'
  import { Message } from '@arco-design/web-vue'
  import { getUserInfo } from '@/api/user/user'
  import MangoPanelSpin from '@/components/feedback/MangoPanelSpin.vue'
  import UserConfigPanel from './components/UserConfigPanel.vue'
  import PasswordChangeDialog from './components/PasswordChangeDialog.vue'
  import PasswordResetDialog from './components/PasswordResetDialog.vue'
  import { readPersonalProfile } from './records'
  import type { PasswordDialogHandle, PersonalProfile } from './types'

  const userStore = useUserStore()
  const route = useRoute()
  const profile = ref<PersonalProfile | null>(null), passwordDialog = ref<PasswordDialogHandle | null>(null)
  const resetPasswordDialog = ref<PasswordDialogHandle | null>(null)
  const loading = ref(false), failed = ref(false), loggingOut = ref(false), contextVersion = ref(0)
  let mounted = false, active = true, disposed = false, needsRead = true, readVersion = 0
  let pending: { version: number; promise: Promise<void> } | null = null
  const available = () => !disposed && active && route.path === '/personal/info' && (typeof document === 'undefined' || !document.hidden)
  const isContextCurrent = (version: number) => available() && version === contextVersion.value
  function suspend(clear: boolean): void {
    contextVersion.value++; readVersion++; pending = null; needsRead = true; loading.value = false
    passwordDialog.value?.close()
    resetPasswordDialog.value?.close()
    if (clear) { profile.value = null; failed.value = false }
  }
  function loadProfile(): Promise<void> {
    if (!mounted || !available() || userStore.userId < 1) return Promise.resolve()
    if (pending) return pending.promise
    const version = contextVersion.value, request = ++readVersion, id = userStore.userId
    const current = () => isContextCurrent(version) && request === readVersion
    loading.value = true; failed.value = false
    const promise = Promise.resolve().then(async () => {
      try {
        if (!current()) return
        const response = await getUserInfo({ id })
        if (!current()) return
        profile.value = readPersonalProfile(response, id)
        needsRead = false
      } catch (loadFailure0) { if (current()) (reportLoadError(loadFailure0, "加载失败，请重试", false), failed.value = true) }
      finally { if (current()) { loading.value = false; pending = null } }
    })
    pending = { version, promise }
    return promise
  }
  function resume(): void { if (mounted && needsRead) void loadProfile() }
  function openPassword(): void { if (available() && profile.value && !loading.value && !loggingOut.value) { resetPasswordDialog.value?.close(); passwordDialog.value?.open() } }
  function openResetPassword(): void { if (available() && profile.value && !loading.value && !loggingOut.value) { passwordDialog.value?.close(); resetPasswordDialog.value?.open() } }
  function handlePasswordReset(version: number): Promise<void> { return handlePasswordChanged(version, '随机密码已发送到登录邮箱，请使用新密码重新登录') }
  async function handlePasswordChanged(version: number, message = '密码已修改，请重新登录'): Promise<void> {
    if (!isContextCurrent(version) || loggingOut.value) return
    loggingOut.value = true
    const userId = userStore.userId, token = userStore.token
    Message.success(message)
    try {
      await userStore.logout()
      if (!userStore.token && userStore.userId === 0) {
        window.localStorage.removeItem('visited-routes')
        window.location.reload()
      }
    } catch {
      if (!disposed && userStore.userId === userId && userStore.token === token) Message.error('退出登录失败，请重新登录')
    } finally { loggingOut.value = false }
  }
  watch(() => [userStore.userId, userStore.roleId, userStore.token, userStore.selected_environment], () => {
    suspend(true)
    void Promise.resolve().then(resume)
  }, { flush: 'sync' })
  watch(() => route.path, () => { suspend(false); void Promise.resolve().then(resume) }, { flush: 'sync' })
  function onVisibilityChange(): void { if (document.hidden) suspend(false); else resume() }
  onMounted(() => { mounted = true; if (typeof document !== 'undefined') document.addEventListener('visibilitychange', onVisibilityChange); resume() })
  onActivated(() => { active = true; resume() })
  onDeactivated(() => { active = false; suspend(false) })
  onBeforeUnmount(() => { disposed = true; suspend(true); if (typeof document !== 'undefined') document.removeEventListener('visibilitychange', onVisibilityChange) })
</script>
<style lang="less" scoped>
  .mango-personal-page {
    display: grid;
    grid-template-columns: 280px minmax(0, 1fr);
    align-items: start;
    gap: var(--m-page-gap);
    width: 100%;
    padding-top: var(--m-page-gap);
  }

  .mango-personal-profile {
    min-width: 0;
  }

  .mango-personal-profile__loading {
    display: block;
    width: 100%;
  }

  .mango-personal-profile__header,
  .mango-personal-profile__identity {
    display: flex;
    align-items: center;
  }

  .mango-personal-profile__header {
    padding-bottom: var(--m-card-padding);
    border-bottom: 1px solid var(--m-border);
  }

  .mango-personal-profile__identity {
    min-width: 0;
    width: 100%;
    gap: var(--m-card-padding);
  }

  .mango-personal-profile__avatar {
    flex: 0 0 auto;
    color: var(--m-primary);
    background: var(--m-surface-soft);
    border: 1px solid var(--m-primary-border);
    font-size: 24px;
  }

  .mango-personal-profile__name {
    width: 100%;
    min-width: 0;

    h2,
    p {
      overflow: hidden;
      margin: 0;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    h2 {
      color: var(--m-text);
      font-size: 18px;
      line-height: 26px;
    }

    p {
      margin-top: 2px;
      color: var(--m-muted);
      font-size: 13px;
    }
  }

  .mango-personal-profile__details {
    margin: var(--m-page-gap) 0 0;
  }

  .mango-personal-profile__detail {
    display: grid;
    grid-template-columns: 64px minmax(0, 1fr);
    align-items: center;
    min-width: 0;
    padding: var(--m-card-padding) 0;
    border-bottom: 1px solid var(--m-border);

    dt {
      color: var(--m-muted);
      font-size: 13px;
    }

    dd {
      overflow: hidden;
      margin: 0;
      color: var(--m-text);
      font-size: 13px;
      text-align: left;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .mango-personal-profile__actions {
    display: flex;
    flex-wrap: wrap;
    gap: var(--m-page-gap);
    margin-top: var(--m-card-padding);
  }
</style>
