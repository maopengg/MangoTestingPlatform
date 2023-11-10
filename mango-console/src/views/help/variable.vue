<template>
  <a-card>
    <a-space direction="vertical" class="w-full">
      <div class="container">
        <span>公共变量</span>
      </div>
      <a-space>
        <a-input :style="{ width: '320px' }" placeholder="请直接输入函数试一试" v-model="input" />
        <a-button type="primary" @click="obtain">测试一下</a-button>
      </a-space>
      <a-card :body-style="{ padding: '10px' }" :bordered="false" v-for="item of randomList" :key="item.title">
        <a-descriptions :column="3" :title="item.title" :data="item.func_list" :bordered="true" />
      </a-card>
    </a-space>
  </a-card>
</template>

<script lang="ts" setup>
import { onMounted, ref } from 'vue'
import { get } from '@/api/http'
import { getRandomList, getRandomData } from '@/api/url'
import { Notification } from '@arco-design/web-vue'

const randomList = ref([])
onMounted(() => {
  get({
    url: getRandomList
  })
    .then((res) => {
      randomList.value = res.data
    })
    .catch(console.log)
})

const input = ref('')

function obtain() {
  get({
    url: getRandomData,
    data: () => {
      return {
        name: '${' + input.value + '}'
      }
    }
  })
    .then((res) => {
      Notification.success(res.data)
    })
    .catch()
}
</script>
<style>
.container span {
  font-size: 25px;
}
</style>
