<template>
  <div>
    <a-card>
      <template #title>
        <span>系统设置</span>
      </template>
      <template #extra>
        <a-button type="primary" size="small" @click="handleClick">{{
          settingsData.editing ? '保存' : '修改'
        }}</a-button>
      </template>
      <a-space direction="vertical">
        <a-space v-for="item of settingsData.data" :key="item.key" direction="horizontal">
          <span
            >{{ item.describe }}:
            <template v-if="settingsData.editing">
              <a-input placeholder="请输入对应的配置" v-model="item.value" />
            </template>
            <template v-else>
              {{ item.value }}
            </template>
          </span>
        </a-space>
      </a-space>
    </a-card>
  </div>
</template>

<script lang="ts" setup>
  import { onMounted, reactive } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { getSystemCacheData, putSystemCacheData } from '@/api/system/cache_data'

  const settingsData: any = reactive({
    editing: false,
    data: [],
  })
  const handleClick = () => {
    if (settingsData.editing) {
      settingsData.data.forEach((item: any) => {
        if (item.value === '') {
          item.value = null
        }
      })
      putSystemCacheData(settingsData.data)
        .then((res) => {
          Message.success(res.msg)
          doRefresh()
        })
        .catch(console.log)
    }
    settingsData.editing = !settingsData.editing
  }
  function doRefresh() {
    getSystemCacheData()
      .then((res) => {
        settingsData.data = res.data
      })
      .catch(console.log)
  }

  onMounted(() => {
    doRefresh()
  })
</script>
