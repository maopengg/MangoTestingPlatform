<template>
  <div class="redirect-contianer"></div>
</template>

<script lang="ts">
  import { defineComponent } from 'vue'
  // import { Notification } from '@arco-design/web-vue'
  // import useUserStore from '@/store/modules/user'
  // import { websocket } from '@/utils/socket'

  export default defineComponent({
    created() {
      const { params, query } = this.$route
      const { path } = params
      this.$router.replace({
        path: '/' + (typeof path === 'string' ? path : path.join('/')),
        query,
      })
      // const userStore = useUserStore()

      // websocket(parseInt(userStore.userName))

      // const socket = new WebSocket('ws://127.0.0.1:8000/web/socket?' + userStore.userName)
    },
  })
</script>
