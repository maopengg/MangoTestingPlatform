<template>
  <section class="mango-exception-status" :aria-label="statusTip">
    <div class="mango-exception-status__image">
      <img :src="statusImage" alt="" />
    </div>
    <h1>{{ statusTip }}</h1>
    <a-button
      class="mango-back-button"
      size="small"
      type="primary"
      :loading="returnPending"
      @click="backHome"
      data-testid="qa-views-exception-components-exceptionstatus-button-返回首页"
    >
      返回首页
    </a-button>
  </section>
</template>

<script lang="ts">
  import image_404 from '@/assets/img_404.png'
  import image_403 from '@/assets/img_403.png'
  import image_500 from '@/assets/img_500.png'
  import {
    computed,
    defineComponent,
    onActivated,
    onBeforeUnmount,
    onDeactivated,
    ref,
    watch,
  } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import usePermissionStore from '@/store/modules/permission'
  import useUserStore from '@/store/modules/user'

  function replaceHash(path: string) {
    window.location.replace(
      `${window.location.origin}${window.location.pathname}${window.location.search}#${path}`
    )
  }

  export default defineComponent({
    name: 'ExceptionStatus',
    props: {
      status: {
        type: [Number, String],
        default: '404',
      },
    },
    setup(props) {
      const userStore = useUserStore()
      const permissionStore = usePermissionStore()
      const route = useRoute()
      const router = useRouter()
      const returnPending = ref(false)
      const statusImage = computed(() =>
        String(props.status) === '404'
          ? image_404
          : String(props.status) === '403'
          ? image_403
          : image_500
      )
      const statusTip = computed(() =>
        String(props.status) === '404'
          ? '您访问的页面不存在'
          : String(props.status) === '403'
          ? '您没有权限访问该页面'
          : '您访问的页面出错啦'
      )
      let active = true,
        generation = 0
      const context = () =>
        JSON.stringify([
          route.fullPath,
          userStore.userId,
          userStore.roleId,
          userStore.token,
          userStore.selected_environment,
        ])
      watch(
        context,
        () => {
          ++generation
        },
        { flush: 'sync' }
      )
      onDeactivated(() => {
        active = false
        ++generation
      })
      onActivated(() => {
        active = true
      })
      onBeforeUnmount(() => {
        active = false
        ++generation
      })
      async function backHome() {
        if (!active || returnPending.value) return
        returnPending.value = true
        const request = ++generation,
          snapshot = context()
        const current = () => active && request === generation && context() === snapshot
        try {
          if (userStore.isTokenExpire()) {
            replaceHash('/login')
            return
          }
          await permissionStore.initPermissionRoute(true)
          if (!current()) return
          const homePath = permissionStore.homePath || '/index/home'
          if (homePath === '/login') {
            replaceHash('/login')
            return
          }
          await router.replace({ path: homePath })
          if (current() && ['/404', '/403', '/500'].includes(route.path)) {
            replaceHash(homePath)
          }
        } catch {
          if (current()) replaceHash(permissionStore.homePath || '/index/home')
        } finally {
          returnPending.value = false
        }
      }
      return { statusImage, statusTip, returnPending, backHome }
    },
  })
</script>

<style lang="less" scoped>
  .mango-exception-status {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: var(--m-space-lg);
    min-height: 100vh;
    padding: var(--m-page-gap);
    box-sizing: border-box;
    text-align: center;
    background: var(--m-bg);
    color: var(--m-text);
  }
  .mango-exception-status__image {
    width: min(100%, 480px);
  }
  .mango-exception-status__image > img {
    display: block;
    width: 100%;
    height: auto;
  }
  .mango-exception-status h1 {
    margin: 0;
    font-size: var(--m-font-title);
    font-weight: 600;
    line-height: 1.5;
    overflow-wrap: anywhere;
  }
</style>
