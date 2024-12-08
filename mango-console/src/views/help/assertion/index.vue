<template>
  <a-card>
    <a-space direction="vertical" class="w-full">
      <div class="container">
        <span>断言策略</span>
      </div>
      <a-card
        :body-style="{ padding: '10px' }"
        :bordered="false"
        v-for="item of randomList"
        :key="item.title"
      >
        <a-descriptions :column="3" :title="item.title" :data="item.func_list" :bordered="true" />
      </a-card>
    </a-space>
  </a-card>
</template>

<script lang="ts" setup>
  import { onMounted, ref } from 'vue'
  import { getUiPageAssMethod } from '@/api/uitest/page-steps-detailed'

  const randomList = ref([])
  onMounted(() => {
    getUiPageAssMethod()
      .then((res) => {
        randomList.value = res.data
      })
      .catch(console.log)
  })
</script>
<style>
  .container span {
    font-size: 25px;
  }
</style>
