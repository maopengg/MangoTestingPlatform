<template>
  <a-modal v-model:visible="visible" @cancel="handleCancel" @ok="handleOk" :width="800">
    <template #title> 联系作者</template>
    <div style="text-align: center">
      <p>进群需要GitHub点Starred（点星）</p>
      <a-space>
        <div>
          <p>作者微信</p>
          <img alt="作者微信" src="/static/images/author.jpg" style="width: 200px; height: 200px;" />
        </div>
        <div>
          <p>交流群</p>
          <img alt="交流群" src="/static/images/group.jpg" style="width: 200px; height: 200px;" />
        </div>
      </a-space>
    </div>
  </a-modal>
</template>

<script lang="ts" setup>
  import { ref } from 'vue'
  import { Message } from '@arco-design/web-vue'

  const visible = defineModel<boolean>('visible', { default: false })

  function handleCancel() {
    visible.value = false
  }
  
  function handleOk() {
    visible.value = false
  }
</script>