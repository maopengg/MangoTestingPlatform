<template>
  <TableBody ref="tableBody">
    <template #header>
      <TableHeader :show-filter="true" title="全局系统设置" />
    </template>
    <template #default>
      <div style="text-align: right; margin-bottom: 3px">
        <a-button size="small" type="primary" @click="handleClick" :loading="loading">
          {{ settingsData.editing ? '保存配置' : '修改配置' }}
        </a-button>
      </div>

      <a-card v-if="hasConfig('host')" title="域名配置" :bordered="false">
        <a-space direction="vertical" size="large">
          <div v-for="item in filteredConfig('host')" :key="item.key">
            <a-space>
              <div>{{ item.describe }}:</div>
              <a-input
                v-if="settingsData.editing"
                v-model="item.value"
                :placeholder="`请输入${item.describe}`"
                allow-clear
              />
              <div v-else>
                {{ item.value || '未配置' }}
              </div></a-space
            >
          </div>
        </a-space>
      </a-card>

      <a-card v-if="hasConfig('email')" title="邮箱配置" :bordered="false">
        <a-space direction="vertical" size="large">
          <div v-for="item in filteredConfig('email')" :key="item.key">
            <a-space>
              <div>{{ item.describe }}:</div>
              <a-input
                v-if="settingsData.editing"
                v-model="item.value"
                :placeholder="`请输入${item.describe}`"
                allow-clear
              />
              <div v-else>
                {{ item.value || '未配置' }}
              </div></a-space
            >
          </div>
        </a-space>
      </a-card>

      <a-card v-if="hasConfig('api')" title="接口自动化配置" :bordered="false">
        <a-space direction="vertical" size="large">
          <div v-for="item in filteredConfig('api')" :key="item.key">
            <a-space>
              <div>{{ item.describe }}:</div>
              <a-input
                v-if="settingsData.editing"
                v-model="item.value"
                :placeholder="`请输入${item.describe}`"
                allow-clear
              />
              <div v-else>
                {{ item.value || '未配置' }}
              </div></a-space
            >
          </div>
        </a-space>
      </a-card>

      <a-card v-if="hasConfig('pytest')" title="单元自动化配置" :bordered="false">
        <a-space direction="vertical" size="large">
          <div v-for="item in filteredConfig('pytest')" :key="item.key">
            <a-space>
              <div>{{ item.describe }}:</div>
              <a-input
                v-if="settingsData.editing"
                v-model="item.value"
                :placeholder="`请输入${item.describe}`"
                allow-clear
                style="width: 600px"
              />
              <div v-else>
                {{ item.value || '未配置' }}
              </div></a-space
            >
          </div>
        </a-space>
      </a-card>
    </template>
  </TableBody>
</template>

<script lang="ts" setup>
  import { onMounted, reactive, ref } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { getSystemCacheData, putSystemCacheData } from '@/api/system/cache_data'

  const loading = ref(false)
  const settingsData = reactive({
    editing: false,
    host: ['DOMAIN_NAME'],
    email: ['SEND_USER', 'EMAIL_HOST', 'STAMP_KET'],
    api: ['API_TIMEOUT'],
    pytest: ['GIT_URL'],
    data: [],
  })

  // 检查是否有某类配置
  const hasConfig = (type) => {
    return settingsData.data.some((item) => settingsData[type].includes(item.key))
  }

  // 过滤出某类配置
  const filteredConfig = (type) => {
    return settingsData.data.filter((item) => settingsData[type].includes(item.key))
  }

  const handleClick = async () => {
    if (settingsData.editing) {
      loading.value = true
      try {
        settingsData.data.forEach((item) => {
          if (item.value === '') {
            item.value = null
          }
        })
        const res = await putSystemCacheData(settingsData.data)
        Message.success(res.msg)
        await doRefresh()
      } catch (error) {
        console.error(error)
      } finally {
        loading.value = false
      }
    }
    settingsData.editing = !settingsData.editing
  }

  async function doRefresh() {
    try {
      const res = await getSystemCacheData()
      settingsData.data = res.data
    } catch (error) {
      console.error(error)
    }
  }

  onMounted(() => {
    doRefresh()
  })
</script>

<style scoped></style>
