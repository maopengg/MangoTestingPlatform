<template>
  <div>
    <a-card :title="value">
      <a-input :v-model="content" placeholder="请输入信息" />
      <a-button @click="sendMessage">发送</a-button>
    </a-card>
  </div>
</template>

<script lang="ts" setup>
import { Message } from '@arco-design/web-vue'
import { ref } from 'vue'

const value = ref('测试页面')
const content = ref('')

function sendMessage(msg = '执行失败') {
  const title = '用例执行结果'
  const msg1 = msg
  if (Notification.permission != 'granted') {
    Notification.requestPermission()
  }
  if (Notification.permission === 'granted') {
    const notification = new Notification(title, { body: msg1 })
    notification.addEventListener('click', () => {
      Message.success('请点击确认按钮，给浏览器授权发送消息到windows桌面！')
    })
  }
}
</script>
