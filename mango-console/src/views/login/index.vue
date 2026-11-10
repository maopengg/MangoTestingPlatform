<template>
  <main class="login-container">
    <div class="login-code-background" aria-hidden="true">
      <div ref="codeTextureTrack" class="code-texture-track">
        <img class="code-texture" :src="loginCodeTexture" alt="" />
        <img class="code-texture" :src="loginCodeTexture" alt="" />
      </div>
    </div>

    <section class="login-stage" :aria-label="`${branding.projectName}登录`">
      <div class="login-copy">
        <div class="brand-row">
          <div class="brand-mark">
            <img :src="brandLogo" alt="" />
          </div>
          <div>
            <div class="brand-name" :title="branding.projectName">{{ branding.projectName }}</div>
            <div class="brand-meta" :title="branding.englishName">{{ branding.englishName }}</div>
          </div>
        </div>
        <div class="hero-copy">
          <h2>面向测试团队的一站式自动化平台</h2>
          <div class="module-viewport" aria-label="平台核心能力">
            <div class="module-track">
              <div v-for="capability in loginCapabilities" :key="capability.title" class="module-card">
                <component :is="capability.icon" />
                <div><strong>{{ capability.title }}</strong><span :title="capability.description">{{ capability.description }}</span></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <aside class="login-panel">
        <div v-if="mode === 'login'" class="form-content">
          <div class="form-kicker">secure sign in</div>
          <h1 class="title">登录测试平台</h1>
          <p class="subtitle">统一开展自动化测试、效果测评与性能测试</p>
          <div class="item-wrapper">
            <a-input
              v-model="loginForm.username"
              placeholder="请输入账号邮箱"
              allow-clear
              size="large"
              class="custom-input"
              data-testid="qa-views-login-input-请输入用户名-手机号"
            >
              <template #prefix>
                <icon-user />
              </template>
            </a-input>
          </div>
          <div class="item-wrapper">
            <a-input-password
              v-model="loginForm.password"
              placeholder="请输入密码"
              allow-clear
              size="large"
              class="custom-input"
              @keyup.enter="onLogin"
              data-testid="qa-views-login-input-password-请输入密码"
            >
              <template #prefix>
                <icon-lock />
              </template>
            </a-input-password>
          </div>
          <div class="remember-forgot">
            <a-checkbox v-model="loginForm.remember" data-testid="qa-views-login-checkbox-记住我"
              >记住我</a-checkbox
            >
            <a-link @click="forgotPassword" data-testid="qa-views-login-link-忘记密码"
              >忘记密码？</a-link
            >
          </div>
          <a-button
            type="primary"
            class="login-btn"
            :loading="submission === 'login'"
            :disabled="busy"
            @click="onLogin"
            data-testid="qa-views-login-button-登录"
          >
            登录
          </a-button>
        </div>
        <div v-else class="form-content">
          <div class="form-kicker">create account</div>
          <h1 class="title">注册用户</h1>
          <p class="subtitle">注册后，随机初始密码将发送到您的邮箱</p>
          <div class="item-wrapper">
            <a-input
              v-model="registrationForm.name"
              placeholder="请输入用户昵称"
              allow-clear
              size="large"
              class="custom-input"
              data-testid="qa-views-login-input-请输入用户昵称"
            />
          </div>
          <div class="item-wrapper">
            <a-input
              v-model="registrationForm.email"
              placeholder="请输入登录邮箱"
              allow-clear
              size="large"
              class="custom-input"
              data-testid="qa-views-login-input-请输入登录用户名"
            >
              <template #prefix>
                <icon-email />
              </template>
            </a-input>
          </div>
          <a-button
            type="primary"
            class="login-btn"
            :loading="submission === 'register'"
            :disabled="busy"
            @click="onRegister"
            data-testid="qa-views-login-button-注册"
          >
            注册
          </a-button>
        </div>
        <div class="links-wrapper">
          <a-link
            v-if="mode === 'login'"
            :underline="false"
            type="primary"
            :loading="registrationState.loading"
            :disabled="registrationState.loading || busy"
            @click="register1"
            data-testid="qa-views-login-link-注册用户"
            >注册用户</a-link
          >
          <a-link
            v-if="mode === 'register'"
            :underline="false"
            type="primary"
            :disabled="busy"
            @click="returnToLogin"
            data-testid="qa-views-login-link-返回登录"
            >返回登录</a-link
          >
        </div>
        <section v-if="!registrationState.configLoading && registrationState.showAuthor" class="mango-login-author" aria-label="开源项目与作者">
          <div class="mango-login-author__identity">
            <icon-code-block aria-hidden="true" />
            <strong>芒果味 · maopeng</strong>
            <span>项目作者</span>
          </div>
          <p>芒果测试平台 · AGPL-3.0 开源</p>
          <nav aria-label="开源项目链接">
            <a href="https://gitee.com/mao-peng/MangoTestingPlatform" target="_blank" rel="noopener noreferrer">Gitee <icon-launch aria-hidden="true" /></a>
            <a href="https://github.com/maopengg/MangoTestingPlatform" target="_blank" rel="noopener noreferrer">GitHub <icon-launch aria-hidden="true" /></a>
            <a href="https://gitee.com/mao-peng" target="_blank" rel="noopener noreferrer">作者主页 <icon-launch aria-hidden="true" /></a>
          </nav>
        </section>
      </aside>
    </section>
    <a-modal
      modal-class="mango-simple-form-modal"
      v-model:visible="resetPassword.visible"
      title="通过邮箱重置密码"
      :width="560"
      :on-before-ok="resetPasswordByEmail"
      :on-before-cancel="cancelPasswordReset"
      :ok-loading="submission === 'reset'"
    >
      <a-form auto-label-width class="mango-simple-form" layout="horizontal" :model="resetPassword">
        <a-form-item class="mango-form-item__require mango-simple-form-item" label="登录邮箱">
          <a-input v-model="resetPassword.email" placeholder="请输入注册时使用的邮箱" allow-clear>
            <template #prefix><icon-email /></template>
          </a-input>
          <template #extra>系统将生成新的随机密码并发送到该邮箱。</template>
        </a-form-item>
      </a-form>
    </a-modal>
    <div class="bottom">{{ branding.projectName }} Copyright © 芒果味 2022年-至今 Version：{{ version }}</div>
  </main>
</template>

<script lang="ts" setup>
  import { computed, reactive, ref, watch, onMounted, onActivated, onDeactivated, onBeforeUnmount } from 'vue'
  import { startLoginBackgroundMotion } from './background-motion'
  import { loginCapabilities, loginEmailPattern } from './config'
  import { readLoginUser } from './records'
  import { useRoute, useRouter } from 'vue-router'
  import { loginAccount, registerAccount, resetAccountPassword } from '@/api/user/authentication'
  import { md5 } from 'js-md5'
  import { Message } from '@arco-design/web-vue'
  import usePlatformBrandingStore from '@/store/modules/platform-branding'
  import type { PublicPlatformConfig } from '@/store/modules/platform-branding'
  import brandLogo from '@/assets/logo.svg'
  import loginCodeTexture from '@/assets/login-code-texture.jpg'
  import useAppInfo from '@/hooks/useAppInfo'
  import useAppConfigStore from '@/store/modules/app-config'
  import usePermissionStore from '@/store/modules/permission'
  import useUserStore from '@/store/modules/user'
  import { connectWebSocket, markWebSocketLoginSession } from '@/utils/socket'

  const branding = usePlatformBrandingStore()
  const { version } = useAppInfo()
  const router = useRouter()
  const route = useRoute()
  const userStore = useUserStore()
  const permissionStore = usePermissionStore()
  const appStore = useAppConfigStore()
  const mode = ref<'login' | 'register'>('login')
  const loginForm = reactive({ username: '', password: '', remember: false })
  const registrationForm = reactive({ name: '', email: '' })
  const submission = ref<'login' | 'register' | 'reset' | null>(null)
  const busy = computed(() => submission.value !== null)
  const registrationState = reactive({ loading: false, configLoading: true, showAuthor: false })
  const resetPassword = reactive({ visible: false, email: '' })
  const codeTextureTrack = ref<HTMLElement>()
  let stopBackgroundMotion: (() => void) | undefined
  let registrationConfigRequest: Promise<PublicPlatformConfig> | undefined
  let generation = 0
  let configSequence = 0
  let mounted = false
  let active = false
  let applyingLoginIdentity = false
  const identity = computed(() => JSON.stringify([userStore.userId, userStore.roleId, userStore.token, userStore.selected_environment]))
  const available = () => mounted && active && route.path === '/login'
  const isCurrent = (version: number) => available() && generation === version

  function invalidate() {
    generation++
    configSequence++
    registrationConfigRequest = undefined
    registrationState.loading = false
    registrationState.configLoading = false
    registrationState.showAuthor = false
    resetPassword.visible = false
    resetPassword.email = ''
    loginForm.password = ''
    Object.assign(registrationForm, { name: '', email: '' })
    mode.value = 'login'
  }

  watch(() => [route.fullPath, identity.value], () => {
    if (applyingLoginIdentity) return
    invalidate()
    if (available()) void loadRegistrationConfig().catch(() => {})
  }, { flush: 'sync' })

  function forgotPassword() {
    if (!available() || busy.value) return
    resetPassword.email = ''
    resetPassword.visible = true
  }

  function cancelPasswordReset() {
    if (submission.value === 'reset') return false
    resetPassword.email = ''
    return true
  }

  function isEmail(value: string) {
    return loginEmailPattern.test(value)
  }

  async function resetPasswordByEmail() {
    if (!available() || busy.value || !resetPassword.visible) return false
    const email = resetPassword.email.trim().toLowerCase()
    if (!isEmail(email)) {
      Message.error('请输入正确的邮箱地址')
      return false
    }
    const version = generation
    submission.value = 'reset'
    try {
      const res = await resetAccountPassword(email)
      if (!isCurrent(version)) return false
      if (res.code !== 200) throw new Error('Password reset failed')
      Message.success(res.msg)
      resetPassword.email = ''
      return true
    } catch {
      if (isCurrent(version)) Message.error('密码重置失败，请稍后重试')
      return false
    } finally {
      submission.value = null
    }
  }

  function passwordDigest(password: string) {
    return md5(md5(password))
  }

  async function onLogin() {
    if (!available() || busy.value || mode.value !== 'login') return
    const username = loginForm.username.trim()
    const password = loginForm.password.trim()
    if (!username) { Message.error('请输入用户名/手机号'); return }
    if (!password) { Message.error('请输入密码'); return }
    if (username === 'open') {
      Message.warning('open账号默认给执行器登录使用，请使用个人账号登录测试平台')
      return
    }
    const version = generation
    submission.value = 'login'
    const encryptedPassword = passwordDigest(password)
    try {
      const res = await loginAccount(username, encryptedPassword)
      if (!isCurrent(version)) return
      if (res.code !== 200) throw new Error('Login failed')
      const user = readLoginUser(res.data)
      // saveUser 同步写入身份；只豁免本次写入，后续外部身份变化仍使登录失效。
      applyingLoginIdentity = true
      let saved: ReturnType<typeof userStore.saveUser>
      try { saved = userStore.saveUser(user, encryptedPassword) }
      finally { applyingLoginIdentity = false }
      const savedIdentity = identity.value
      await saved
      if (!isCurrent(version) || identity.value !== savedIdentity) return
      await permissionStore.initPermissionRoute(true, () => isCurrent(version) && identity.value === savedIdentity)
      if (!isCurrent(version) || identity.value !== savedIdentity) return
      markWebSocketLoginSession()
      connectWebSocket(username, encryptedPassword)
      const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : ''
      const safeRedirect = redirect.startsWith('/') && !redirect.startsWith('//') ? redirect : ''
      const navigationFailure = await router.replace(safeRedirect || permissionStore.homePath || '/index/home')
      if (navigationFailure || identity.value !== savedIdentity) return
      Message.success(`登录成功，欢迎用户：${user.name}，您的角色是：${user.roles?.[0]?.roleName || '游客'}，您的权限是：${user.is_super_admin ? '超级管理员' : '普通用户'}`)
    } catch {
      if (isCurrent(version)) Message.error('登录未完成，请重试')
    } finally {
      submission.value = null
    }
  }

  async function loadRegistrationConfig() {
    if (!available()) throw new Error('Login page inactive')
    if (!registrationConfigRequest) {
      const version = generation
      const sequence = ++configSequence
      registrationState.configLoading = true
      registrationConfigRequest = branding.loadPublicConfig().then((config) => {
        if (typeof config?.allow_registration !== 'boolean' || typeof config.disabled_message !== 'string') {
          throw new Error('Invalid registration configuration')
        }
        if (isCurrent(version) && sequence === configSequence) registrationState.showAuthor = config.show_author_info === true
        return config
      }).finally(() => {
        if (isCurrent(version) && sequence === configSequence) {
          registrationConfigRequest = undefined
          registrationState.configLoading = false
        }
      })
    }
    return registrationConfigRequest
  }

  async function register1() {
    if (!available() || busy.value || registrationState.loading) return
    const version = generation
    registrationState.loading = true
    try {
      const config = await loadRegistrationConfig()
      if (!isCurrent(version) || busy.value) return
      if (!config.allow_registration) { Message.info(config.disabled_message); return }
      Object.assign(registrationForm, { name: '', email: '' })
      loginForm.password = ''
      mode.value = 'register'
    } catch {
      if (isCurrent(version)) Message.error('注册配置加载失败，请稍后重试')
    } finally {
      if (isCurrent(version)) registrationState.loading = false
    }
  }

  function returnToLogin() {
    if (!available() || busy.value) return
    Object.assign(registrationForm, { name: '', email: '' })
    mode.value = 'login'
  }

  async function onRegister() {
    if (!available() || busy.value || mode.value !== 'register') return
    const name = registrationForm.name.trim()
    const email = registrationForm.email.trim().toLowerCase()
    if (!name || !email) { Message.error('用户昵称和登录邮箱不允许为空'); return }
    if (!isEmail(email)) { Message.error('请输入正确的邮箱地址'); return }
    const version = generation
    submission.value = 'register'
    try {
      const res = await registerAccount(name, email)
      if (!isCurrent(version)) return
      if (res.code !== 200) throw new Error('Registration failed')
      Message.success(res.msg)
      loginForm.username = email
      loginForm.password = ''
      Object.assign(registrationForm, { name: '', email: '' })
      mode.value = 'login'
    } catch {
      if (isCurrent(version)) Message.error('注册失败，请稍后重试')
    } finally {
      submission.value = null
    }
  }

  function resume() {
    if (!mounted || active) return
    active = true
    appStore.applyCurrentThemePreset()
    void loadRegistrationConfig().catch(() => {})
    if (codeTextureTrack.value) stopBackgroundMotion = startLoginBackgroundMotion(codeTextureTrack.value)
  }
  function suspend() {
    active = false
    invalidate()
    stopBackgroundMotion?.()
    stopBackgroundMotion = undefined
  }
  onMounted(() => { mounted = true; resume() })
  onActivated(resume)
  onDeactivated(suspend)
  onBeforeUnmount(() => { mounted = false; suspend() })
</script>

<style lang="less" scoped>
  .login-container {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    min-height: 100vh;
    min-height: 100dvh;
    overflow-x: hidden;
    overflow-y: auto;
    padding: clamp(28px, 5vh, 48px) clamp(24px, 4vw, 56px) 64px;
    background: linear-gradient(
        90deg,
        color-mix(in srgb, var(--m-bg) 82%, transparent) 0%,
        transparent 46%
      ),
      linear-gradient(160deg, var(--m-bg) 0%, var(--m-surface-soft) 48%, var(--m-bg) 100%);
  }

  .login-container::before {
    position: absolute;
    inset: 0;
    content: '';
    background-image: linear-gradient(
        color-mix(in srgb, var(--m-border) 42%, transparent) 1px,
        transparent 1px
      ),
      linear-gradient(
        90deg,
        color-mix(in srgb, var(--m-border) 42%, transparent) 1px,
        transparent 1px
      );
    background-size: 48px 48px;
    mask-image: linear-gradient(
      to bottom,
      color-mix(in srgb, var(--m-text) 72%, transparent),
      transparent 82%
    );
    opacity: 0.42;
  }

  .login-code-background {
    position: absolute;
    inset: 0;
    z-index: 0;
    overflow: hidden;
    pointer-events: none;
  }

  .login-code-background::after {
    position: absolute;
    inset: 0;
    content: '';
    background: linear-gradient(
        90deg,
        color-mix(in srgb, var(--m-bg) 28%, transparent) 0%,
        transparent 18%,
        transparent 54%,
        color-mix(in srgb, var(--m-bg) 88%, transparent) 70%,
        var(--m-bg) 100%
      ),
      linear-gradient(
        0deg,
        color-mix(in srgb, var(--m-bg) 58%, transparent) 0%,
        transparent 22%,
        color-mix(in srgb, var(--m-bg) 48%, transparent) 100%
      );
  }

  .code-texture-track {
    position: absolute;
    top: clamp(-118px, -11vh, -64px);
    left: clamp(72px, 12vw, 190px);
    width: clamp(760px, 64vw, 1080px);
    display: flex;
    flex-direction: column;
    gap: 0;
    transform: rotate(7deg);
    transform-origin: left top;
  }

  .code-texture {
    display: block;
    width: 100%;
    height: auto;
    border-radius: var(--m-radius-sm);
    box-shadow: var(--m-shadow);
    opacity: 0.68;
    filter: saturate(0.74) contrast(1.04);
    user-select: none;
  }

  .login-stage {
    position: relative;
    z-index: 1;
    display: grid;
    grid-template-columns: minmax(360px, 1fr) minmax(360px, 420px);
    gap: clamp(22px, 3vw, 34px);
    width: min(1120px, 100%);
    min-height: min(620px, calc(100dvh - 132px));
  }

  .login-panel {
    position: relative;
    border: 1px solid color-mix(in srgb, var(--m-border) 72%, transparent);
    border-radius: var(--m-radius);
    background: color-mix(in srgb, var(--m-surface) 94%, transparent);
    box-shadow: var(--m-shadow);
    backdrop-filter: blur(18px);
  }

  .login-copy {
    display: flex;
    flex-direction: column;
    justify-content: center;
    min-width: 0;
    padding: clamp(18px, 4vh, 34px) 0;
  }

  .brand-row {
    display: flex;
    align-items: center;
    gap: 14px;
  }

  .brand-row > div:last-child {
    min-width: 0;
  }

  .brand-name,
  .brand-meta {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .brand-mark {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 46px;
    height: 46px;
    border: 1px solid var(--m-primary-border);
    border-radius: var(--m-radius-sm);
    background: var(--m-primary-soft);
    padding: 8px;

    img {
      display: block;
      width: 100%;
      height: 100%;
    }
  }

  .brand-name {
    color: var(--m-text);
    font-size: 24px;
    font-weight: 700;
    line-height: 30px;
  }

  .brand-meta,
  .form-kicker {
    font-family: 'Fira Code', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  }

  .brand-meta {
    margin-top: 3px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .hero-copy {
    max-width: clamp(390px, 38vw, 460px);
    margin-top: clamp(24px, 4vh, 34px);
  }

  .hero-copy h2 {
    margin: 0;
    color: var(--m-text);
    font-size: clamp(34px, 3.6vw, 42px);
    font-weight: 760;
    line-height: 1.26;
  }

  .module-viewport {
    position: relative;
    margin-top: clamp(18px, 3vh, 24px);
  }

  .module-track {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
  }

  .module-card {
    display: grid;
    grid-template-columns: 34px minmax(0, 1fr);
    align-items: center;
    gap: 10px;
    min-height: 62px;
    padding: 10px 12px;
    border: 1px solid color-mix(in srgb, var(--m-border) 70%, transparent);
    border-radius: var(--m-radius-sm);
    background: color-mix(in srgb, var(--m-surface) 78%, transparent);
    box-shadow: var(--m-shadow-sm);
    backdrop-filter: blur(14px);
  }

  .module-card > svg {
    width: 34px;
    height: 34px;
    padding: 8px;
    border: 1px solid var(--m-primary-border);
    border-radius: var(--m-radius-sm);
    background: var(--m-primary-soft);
    color: var(--m-primary);
  }

  .module-card div {
    min-width: 0;
  }

  .module-card strong,
  .module-card span {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .module-card strong {
    color: var(--m-text);
    font-size: 14px;
    font-weight: 700;
    line-height: 22px;
  }

  .module-card span {
    margin-top: 3px;
    color: var(--m-text-2);
    font-size: 12px;
    line-height: 18px;
  }

  .login-panel {
    display: flex;
    flex-direction: column;
    justify-content: center;
    min-width: 0;
    padding: 42px;
  }

  .form-content {
    display: flex;
    flex-direction: column;
    min-width: 0;
  }

  .form-kicker {
    margin-bottom: 8px;
    color: var(--m-primary);
    font-size: 12px;
    font-weight: 700;
    line-height: 18px;
    text-transform: uppercase;
  }

  .title {
    margin: 0;
    color: var(--m-text);
    font-size: 30px;
    font-weight: 750;
    line-height: 38px;
  }

  .subtitle {
    margin: 10px 0 28px;
    color: var(--m-muted);
    font-size: 14px;
    line-height: 22px;
  }

  .item-wrapper + .item-wrapper {
    margin-top: 14px;
  }

  .form-content > .item-wrapper + .login-btn {
    margin-top: var(--m-space-lg);
  }

  .custom-input {
    width: 100%;

    :deep(.arco-input-wrapper) {
      height: 46px;
      border-color: var(--m-form-border);
      border-radius: var(--m-radius-sm);
      background: var(--m-form-bg);
      box-shadow: none;
      transition: border-color 0.2s ease, box-shadow 0.2s ease, background-color 0.2s ease;
    }

    :deep(.arco-input-wrapper:hover),
    :deep(.arco-input-focus) {
      border-color: var(--m-primary);
      background: var(--m-surface);
      box-shadow: var(--m-form-focus-shadow);
    }

    :deep(.arco-input-prefix) {
      color: var(--m-primary);
      font-size: 18px;
    }
  }

  .remember-forgot {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin: 18px 0 24px;
  }

  .login-btn {
    width: 100%;
    height: 46px;
    border: none;
    border-radius: var(--m-radius-sm);
    background: linear-gradient(135deg, var(--m-primary) 0%, var(--m-primary-hover) 100%);
    color: var(--m-on-primary);
    font-size: 16px;
    font-weight: 700;
    transition: filter 0.2s ease, box-shadow 0.2s ease;
  }

  .login-btn:hover {
    filter: brightness(1.04);
    box-shadow: var(--m-shadow);
  }

  .links-wrapper {
    display: flex;
    justify-content: flex-end;
    margin-top: 18px;
  }

  .mango-login-author {
    margin-top: 28px;
    padding-top: 14px;
    border-top: 1px solid var(--m-border);
    color: var(--m-text-2);
    font-size: 12px;
    line-height: 18px;
  }

  .mango-login-author__identity,
  .mango-login-author nav,
  .mango-login-author a {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }

  .mango-login-author__identity strong {
    color: var(--m-text);
    font-weight: 600;
  }

  .mango-login-author p {
    margin: 5px 0 8px;
  }

  .mango-login-author nav {
    gap: 16px;
  }

  .mango-login-author a {
    gap: 4px;
    color: var(--m-primary);
    text-decoration: none;
  }

  .mango-login-author a:hover {
    text-decoration: underline;
    text-underline-offset: 3px;
  }

  .mango-login-author a:focus-visible {
    outline: 2px solid var(--m-primary);
    outline-offset: 3px;
  }

  .bottom {
    position: fixed;
    right: 24px;
    bottom: 18px;
    left: 24px;
    z-index: 2;
    overflow: hidden;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
    text-align: center;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  @media (max-width: 1180px) {
    .login-stage {
      grid-template-columns: minmax(0, 1fr) minmax(340px, 392px);
      width: min(1040px, 100%);
      min-height: min(580px, calc(100dvh - 120px));
    }

    .login-panel {
      padding: 36px;
    }

    .mango-login-author {
      right: 36px;
      left: 36px;
    }

    .code-texture-track {
      top: -82px;
      left: clamp(42px, 9vw, 118px);
      width: clamp(720px, 68vw, 900px);
    }

    .code-texture {
      opacity: 0.64;
    }
  }

  @media (max-width: 920px) {
    .login-container {
      align-items: flex-start;
      padding: 24px 16px 56px;
    }

    .login-code-background::after {
      background: linear-gradient(
          90deg,
          color-mix(in srgb, var(--m-bg) 64%, transparent) 0%,
          transparent 52%,
          color-mix(in srgb, var(--m-bg) 82%, transparent) 100%
        ),
        linear-gradient(
          0deg,
          color-mix(in srgb, var(--m-bg) 72%, transparent) 0%,
          transparent 32%,
          color-mix(in srgb, var(--m-bg) 58%, transparent) 100%
        );
    }

    .login-stage {
      grid-template-columns: 1fr;
      gap: 20px;
      width: min(680px, 100%);
      min-height: 0;
    }

    .login-copy {
      padding: 10px 0 0;
    }

    .hero-copy {
      margin-top: 22px;
      max-width: 100%;
    }

    .hero-copy h2 {
      max-width: 540px;
      font-size: 30px;
      line-height: 38px;
    }

    .login-panel {
      padding: 28px 24px;
    }

    .mango-login-author {
      position: static;
      margin-top: 28px;
    }

    .code-texture-track {
      top: -54px;
      left: clamp(-180px, -18vw, -90px);
      width: 820px;
    }

    .code-texture {
      opacity: 0.42;
    }

    .module-viewport {
      margin-top: 16px;
    }

    .module-track {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 560px) {
    .login-code-background {
      display: none;
    }

    .login-copy {
      display: block;
    }

    .brand-row {
      justify-content: center;
    }

    .hero-copy {
      display: none;
    }

    .login-stage {
      width: 100%;
    }

    .login-panel {
      padding: 28px 20px;
    }

    .title {
      font-size: 26px;
      line-height: 34px;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    *,
    *::before,
    *::after {
      animation-duration: 0.01ms !important;
      animation-iteration-count: 1 !important;
      scroll-behavior: auto !important;
      transition-duration: 0.01ms !important;
    }

    .code-texture-track {
      animation: none !important;
    }
  }
</style>
