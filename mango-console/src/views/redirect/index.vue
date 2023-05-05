<!--<template>-->
<!--  <div class="redirect-contianer"></div>-->
<!--</template>-->

<!--<script lang="ts">-->
<!--import { defineComponent } from 'vue'-->
<!--import { Notification } from '@arco-design/web-vue'-->
<!--import useUserStore from '@/store/modules/user'-->

<!--export default defineComponent({-->
<!--  created() {-->
<!--    const { params, query } = this.$route-->
<!--    const { path } = params-->
<!--    this.$router.replace({-->
<!--      path: '/' + (typeof path === 'string' ? path : path.join('/')),-->
<!--      query-->
<!--    })-->

<!--    const userStore = useUserStore()-->
<!--    const socket = new WebSocket('ws://127.0.0.1:8000/web/socket?' + userStore.userName)-->
<!--    console.log('执行了吗？')-->

<!--    // 客户端主动给服务器发送消息-->
<!--    function sendMessage() {-->
<!--      let data = {-->
<!--        code: 200,-->
<!--        func: null,-->
<!--        user_info: 1807171,-->
<!--        msg: '前端发送的消息',-->
<!--        data: null-->
<!--      }-->
<!--      socket.send(JSON.stringify(data))-->
<!--    }-->

<!--    // 当服务器给客户端发送数据时触发-->
<!--    socket.onmessage = (event) => {-->
<!--      let res = JSON.parse(event.data)-->
<!--      Notification.success(res.msg)-->
<!--    }-->

<!--    // 创建好连接之后自动触发-->
<!--    socket.onopen = () => {-->
<!--      console.log('与服务器实时对话连接成功！')-->
<!--    }-->
<!--    // 服务器与我断开连接时触发-->
<!--    socket.onclose = () => {-->
<!--      Notification.info('服务器跟我断开连接了！')-->
<!--    }-->
<!--  }-->
<!--})-->
<!--</script>-->
