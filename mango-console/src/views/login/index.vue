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
              <div class="module-card">
                <icon-find-replace />
                <div>
                  <strong>UI自动化</strong>
                  <span>页面、元素、步骤、公共能力与执行链路统一管理</span>
                </div>
              </div>
              <div class="module-card">
                <icon-thunderbolt />
                <div>
                  <strong>API自动化</strong>
                  <span>接口用例、断言、环境变量和场景编排</span>
                </div>
              </div>
              <div class="module-card">
                <icon-storage />
                <div>
                  <strong>数据工厂</strong>
                  <span>实体、关系、变量与测试数据快速构造</span>
                </div>
              </div>
              <div class="module-card">
                <icon-calendar-clock />
                <div>
                  <strong>报告分析</strong>
                  <span>执行趋势、失败定位和质量结果追踪</span>
                </div>
              </div>
              <div class="module-card">
                <icon-file />
                <div>
                  <strong>研发协同</strong>
                  <span>迭代、需求、用例、计划与缺陷协同管理</span>
                </div>
              </div>
              <div class="module-card">
                <icon-schedule />
                <div>
                  <strong>任务调度</strong>
                  <span>定时任务、任务组、触发策略与结果通知</span>
                </div>
              </div>
              <div class="module-card">
                <icon-command />
                <div>
                  <strong>测试配置</strong>
                  <span>项目产品、模块、环境、文件和测试对象配置</span>
                </div>
              </div>
              <div class="module-card">
                <icon-experiment />
                <div>
                  <strong>评测中心</strong>
                  <span>评测数据集、测试用例与评分器管理</span>
                </div>
              </div>
              <div class="module-card">
                <icon-code-block />
                <div>
                  <strong>Pytest自动化</strong>
                  <span>代码用例、Fixture、Allure 和分层架构管理</span>
                </div>
              </div>
              <div class="module-card">
                <icon-dashboard />
                <div>
                  <strong>性能测试</strong>
                  <span>压测场景、执行容量和性能结果分析</span>
                </div>
              </div>
              <div class="module-card">
                <icon-play-circle />
                <div>
                  <strong>监控中心</strong>
                  <span>脚本定时运行、异常预警与监控报告</span>
                </div>
              </div>
              <div class="module-card">
                <icon-robot />
                <div>
                  <strong>智能能力</strong>
                  <span>Skill、MCP 工具与 AI 任务执行</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <aside class="login-panel">
        <div v-if="baseData.isLogin === true" class="form-content">
          <div class="form-kicker">secure sign in</div>
          <h1 class="title">登录测试平台</h1>
          <p class="subtitle">统一开展自动化测试、效果测评与性能测试</p>
          <div class="item-wrapper">
            <a-input
              v-model="baseData.username"
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
              v-model="baseData.password"
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
            <a-checkbox v-model="baseData.remember" data-testid="qa-views-login-checkbox-记住我"
              >记住我</a-checkbox
            >
            <a-link @click="forgotPassword" data-testid="qa-views-login-link-忘记密码"
              >忘记密码？</a-link
            >
          </div>
          <a-button
            type="primary"
            class="login-btn"
            :loading="baseData.loading"
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
              v-model="baseData.name"
              placeholder="请输入用户昵称"
              allow-clear
              size="large"
              class="custom-input"
              data-testid="qa-views-login-input-请输入用户昵称"
            />
          </div>
          <div class="item-wrapper">
            <a-input
              v-model="baseData.email"
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
            :loading="baseData.loading"
            @click="onRegister"
            data-testid="qa-views-login-button-注册"
          >
            注册
          </a-button>
        </div>
        <div class="links-wrapper">
          <a-link
            v-if="baseData.isLogin === true"
            :underline="false"
            type="primary"
            :loading="registrationState.loading"
            :disabled="registrationState.loading"
            @click="register1"
            data-testid="qa-views-login-link-注册用户"
            >注册用户</a-link
          >
          <a-link
            v-if="baseData.isLogin === false"
            :underline="false"
            type="primary"
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
      v-model:visible="resetPassword.visible"
      title="通过邮箱重置密码"
      width="540px"
      :on-before-ok="resetPasswordByEmail"
      @cancel="resetPassword.email = ''"
    >
      <a-form layout="vertical" :model="resetPassword">
        <a-form-item class="mango-form-item__require" label="登录邮箱">
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
  import { reactive, ref, onMounted, onBeforeUnmount } from 'vue'
  import { startLoginBackgroundMotion } from './background-motion'
  import { useRoute, useRouter } from 'vue-router'
  import { post, Response } from '@/api/http'
  import { md5 } from 'js-md5'

  import { login, register } from '@/api/url'
  import { Message } from '@arco-design/web-vue'
  import { UserState } from '@/store/types'
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
  const registrationState = reactive({ loading: false, configLoading: true, showAuthor: false })
  type RegistrationConfig = PublicPlatformConfig
  let registrationConfigRequest: Promise<RegistrationConfig> | undefined
  const codeTextureTrack = ref<HTMLElement>()
  let stopBackgroundMotion: (() => void) | undefined
  const baseData: any = reactive({
    name: '',
    email: '',
    username: '',
    password: '',
    confirm_password: '',
    remember: false,
    loading: false,
    isLogin: true,
  })
  const resetPassword = reactive({
    visible: false,
    email: '',
  })

  function forgotPassword() {
    resetPassword.email = ''
    resetPassword.visible = true
  }

  function isEmail(value: string) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)
  }

  async function resetPasswordByEmail() {
    const email = resetPassword.email.trim().toLowerCase()
    if (!isEmail(email)) {
      Message.error('请输入正确的邮箱地址')
      return false
    }
    const res = await post({ url: '/reset-password', data: { email } })
    Message.success(res.msg)
    return true
  }

  function passwordDigest(password: string) {
    return md5(md5(password))
  }

  const onLogin = async () => {
    const username = baseData.username?.trim()
    const password = baseData.password?.trim()
    if (!username) {
      Message.error('请输入用户名/手机号')
      return
    }
    if (!password) {
      Message.error('请输入密码')
      return
    }
    if (username === 'open') {
      Message.warning('open账号默认给执行器登录使用，请使用个人账号登录测试平台')
      return
    }
    baseData.loading = true
    const encryptedPassword = passwordDigest(password)
    try {
      const res = await post({
        url: login,
        data: {
          username,
          password: encryptedPassword,
          type: 1,
        },
      })
      const data = res.data as UserState
      await userStore.saveUser(data, encryptedPassword)

      // 每次登录都清理旧路由并重新请求菜单，菜单加载完成后才允许跳转。
      await permissionStore.initPermissionRoute(true)

      markWebSocketLoginSession()
      connectWebSocket(username, encryptedPassword)
      const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : ''
      const safeRedirect = redirect.startsWith('/') && !redirect.startsWith('//') ? redirect : ''
      await router.replace(safeRedirect || permissionStore.homePath || '/index/home')
      const roleName = data.roles?.[0]?.roleName || '游客'
      const permissionType = data.is_super_admin ? '超级管理员' : '普通用户'
      Message.success(
        `登录成功，欢迎用户：${data.name}，您的角色是：${roleName}，您的权限是：${permissionType}`
      )
    } catch (error) {
      console.error('登录流程执行失败', error)
    } finally {
      baseData.loading = false
    }
  }

  async function loadRegistrationConfig() {
    if (!registrationConfigRequest) {
      registrationState.configLoading = true
      registrationConfigRequest = branding.loadPublicConfig().then((config) => {
        if (typeof config?.allow_registration !== 'boolean' || typeof config.disabled_message !== 'string') {
          throw new Error('Invalid registration configuration')
        }
        registrationState.showAuthor = config.show_author_info === true
        return config
      }).finally(() => {
        registrationConfigRequest = undefined
        registrationState.configLoading = false
      })
    }
    return registrationConfigRequest
  }

  async function register1() {
    if (registrationState.loading) return
    registrationState.loading = true
    try {
      const config = await loadRegistrationConfig()
      if (!config.allow_registration) {
        Message.info(config.disabled_message)
        return
      }
      baseData.isLogin = false
    } catch {
      Message.error('注册配置加载失败，请稍后重试')
    } finally {
      registrationState.loading = false
    }
  }

  function returnToLogin() {
    baseData.isLogin = true
  }

  function onRegister() {
    const name = baseData.name?.trim()
    const email = baseData.email?.trim().toLowerCase()
    if (!name || !email) {
      Message.error('用户昵称和登录邮箱不允许为空')
      return
    }
    if (!isEmail(email)) {
      Message.error('请输入正确的邮箱地址')
      return
    }
    baseData.loading = true
    post({
      url: register,
      data: {
        name,
        email,
      },
    })
      .then((res: Response) => {
        if (res.code === 200) {
          Message.success(res.msg)
          baseData.username = email
          baseData.password = ''
          returnToLogin()
        }
      })
      .finally(() => {
        baseData.loading = false
      })
  }

  onMounted(() => {
    appStore.applyCurrentThemePreset()
    void loadRegistrationConfig().catch(() => {
      registrationState.showAuthor = false
    })
    if (codeTextureTrack.value) {
      stopBackgroundMotion = startLoginBackgroundMotion(codeTextureTrack.value)
    }
  })
  onBeforeUnmount(() => stopBackgroundMotion?.())
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
    position: absolute;
    right: 42px;
    bottom: 24px;
    left: 42px;
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
