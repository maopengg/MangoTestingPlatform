<template>
  <a-card>
    <div>
      <a-input-tag
        :default-value="tags"
        :style="{ width: '380px' }"
        placeholder="Please Enter"
        :max-tag-count="4"
        allow-clear
        @change="handleTagChange"
      />
    </div>
    <a-form @submit="handleSubmit">
      <a-form-item>
        <a-button type="primary" html-type="submit">Submit</a-button>
      </a-form-item>
    </a-form>
  </a-card>
  <a-button @click="test">点击测试</a-button>
</template>

<script setup lang="ts">
  import { onMounted, reactive } from 'vue'
  import { get } from '@/api/http'
  import { systemTest } from '@/api/url'
  import { Message } from '@arco-design/web-vue'

  const tags = reactive<string[]>([])

  function handleTagChange(value: string[]) {
    tags.splice(0, tags.length, ...value)
  }

  function handleSubmit() {
    console.log('Submitted tags:', tags)
  }

  function test() {
    get({
      url: systemTest,
      data: () => {
        return {}
      },
    })
      .then((res) => {
        Message.success(res.msg)
        console.log(res.data)
      })
      .catch(console.log)
  }

  onMounted(() => {})
</script>
