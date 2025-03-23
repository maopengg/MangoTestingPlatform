<template>
  <a-card>
    <a-space class="w-full" direction="vertical">
      <div class="container">
        <span>断言策略</span>
      </div>
      <a-card
        v-for="item of randomList"
        :key="item.title"
        :body-style="{ padding: '10px' }"
        :bordered="false"
      >
        <a-descriptions :bordered="true" :column="3" :data="item.children" :title="item.label" />
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
