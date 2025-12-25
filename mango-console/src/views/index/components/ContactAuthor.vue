<template>
  <a-modal
    v-model:visible="visible"
    @cancel="handleCancel"
    @ok="handleOk"
    :width="500"
    :body-style="{ height: '410px', 'text-align': 'center' }"
  >
    <template #title>联系作者</template>
    <div>
      <p>进群需要GitHub点Starred（点点星）</p>
      <a-space>
        <div>
          <p>作者微信</p>
          <img alt="作者微信" src="/static/images/author.jpg" />
        </div>
        <div>
          <p>交流群</p>
          <img alt="交流群" src="/static/images/group.jpg" />
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
