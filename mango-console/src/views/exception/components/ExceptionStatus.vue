<template>
  <div class="exception-container">
    <div class="img-wrapper">
      <img :src="statusImage" />
    </div>
    <div class="title">
      <div>{{ statusTip }}</div>
      <div class="margin-top-lg">
        <a-button class="mango-back-button" size="small" type="primary" @click="backHome" data-testid="qa-views-exception-components-exceptionstatus-button-返回首页"> 返回首页</a-button>
      </div>
    </div>
  </div>
</template>

<script>
  import image_404 from '@/assets/img_404.png'
  import image_403 from '@/assets/img_403.png'
  import image_500 from '@/assets/img_500.png'
  import { defineComponent } from 'vue'
  import usePermissionStore from '@/store/modules/permission'
  import useUserStore from '@/store/modules/user'

  function replaceHash(path) {
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
    data() {
      return {
        image404: image_404,
        image403: image_403,
        image500: image_500,
      }
    },
    computed: {
      statusImage() {
        if (this.status.toString() === '404') {
          return this.image404
        } else if (this.status.toString() === '403') {
          return this.image403
        } else {
          return this.image500
        }
      },
      statusTip() {
        if (this.status.toString() === '404') {
          return '您访问的页面不存在'
        } else if (this.status.toString() === '403') {
          return '您没有权限访问该页面'
        } else {
          return '您访问的页面出错啦'
        }
      },
    },
    methods: {
      async backHome() {
        const userStore = useUserStore()
        if (userStore.isTokenExpire()) {
          replaceHash('/login')
          return
        }

        const permissionStore = usePermissionStore()
        try {
          await permissionStore.initPermissionRoute(true)
          const homePath = permissionStore.homePath || '/index/home'
          if (homePath === '/login') {
            replaceHash('/login')
            return
          }
          await this.$router.replace({ path: homePath })
          if (['/404', '/403', '/500'].includes(this.$route.path)) {
            replaceHash(homePath)
          }
        } catch (error) {
          replaceHash(permissionStore.homePath || '/index/home')
        }
      },
    },
  })
</script>

<style lang="less" scoped>
  .exception-container {
    text-align: center;
    height: 100%;

    .img-wrapper {
      width: 80%;
      margin: 0 auto;

      & > img {
        width: 100%;
      }
    }

    .title {
      margin-top: -50px;
    }
  }
</style>
