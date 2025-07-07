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
        <a-descriptions :bordered="true" :column="3" :data="item.children" :title="item.label">
          <template #label="{ data }">{{ data.value }}</template>
          <template #value="{ data }">{{ data.label }}</template>
        </a-descriptions>
      </a-card>
    </a-space>
  </a-card>
</template>

<script lang="ts" setup>
  import { onMounted, ref } from 'vue'
  import { getSystemCacheDataKeyValue } from '@/api/system/cache_data'

  const randomList = ref([])
  onMounted(() => {
    getSystemCacheDataKeyValue('select_value')
      .then((res) => {
        res.data.forEach((item: any) => {
          if (item.value.includes('断言') || item.value.includes('ass')) {
            randomList.value.push(...item.children)
          }
        })
      })
      .catch(console.log)
  })
</script>
<style scoped>
  .container span {
    font-size: 25px;
  }
</style>
