<template>
  <TableBody ref="tableBody">
    <template #header> </template>
    <template #default>
      <a-card title="公共变量" :bordered="false">
        <a-space>
          <a-input :style="{ width: '320px' }" placeholder="请直接输入函数试一试" v-model="input" />
          <a-button type="primary" @click="obtain">测试一下</a-button>
        </a-space>
        <a-card
          :body-style="{ padding: '10px' }"
          :bordered="false"
          v-for="item of randomList"
          :key="item.label"
        >
          <a-descriptions :column="3" :title="item.label" :data="item.children" :bordered="true" />
        </a-card>
      </a-card>
    </template>
  </TableBody>
</template>

<script lang="ts" setup>
  import { onMounted, ref } from 'vue'
  import { Notification } from '@arco-design/web-vue'
  import { getSystemRandomData, getSystemRandomList } from '@/api/system/system'

  const randomList = ref([])
  onMounted(() => {
    getSystemRandomList()
      .then((res) => {
        randomList.value = res.data
      })
      .catch(console.log)
  })

  const input = ref('')

  function obtain() {
    getSystemRandomData('${' + input.value + '}')
      .then((res) => {
        Notification.success(res.data)
      })
      .catch()
  }
</script>
<style lang="less"></style>
