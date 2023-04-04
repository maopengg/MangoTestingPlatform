<template>
  <div>
    <a-space direction="vertical" class="w-full">
      <a-card size="small">
        <div class="text-lg">
          <span> 公共变量 </span>
          <a-space>
            <a-input :style="{ width: '320px' }" placeholder="请输入函数名称" v-model="input" va allow-clear />
          </a-space>
          <a-button type="primary" @click="obtain">查看</a-button>
        </div>
      </a-card>

      <a-card :body-style="{ padding: '10px' }">
        <a-descriptions bordered :column="3" title="将函数名称输入到输入框中，点击查看即可获取数据" :data="randomList" />
      </a-card>
    </a-space>
  </div>
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
        name: input.value
      }
    }
  })
    .then((res) => {
      Notification.success(res.data)
    })
    .catch()
}
</script>
