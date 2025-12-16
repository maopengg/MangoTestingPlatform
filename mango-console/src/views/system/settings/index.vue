<template>
  <TableBody ref="tableBody">
    <template #header>
      <TableHeader :show-filter="true" title="全局系统设置" />
    </template>
    <template #default>
      <div style="margin-bottom: 10px; text-align: right">
        <a-button size="small" type="primary" @click="handleClick" :loading="loading">
          {{ settingsData.editing ? '保存配置' : '修改配置' }}
        </a-button>
      </div>

      <a-space direction="vertical" size="mini" style="width: 100%">
        <!-- Debug日志设置 -->
        <a-card :bordered="false" style="border-radius: 4px; background-color: var(--color-fill-1)">
          <div
            style="display: flex; align-items: center; justify-content: space-between; padding: 8px"
          >
            <span style="color: var(--color-text-1)">设置系统debug级别日志</span>
            <a-switch
              v-model="settingsData.isDebug"
              @change="doPostSystemSetDebugLog"
              size="small"
            />
          </div>
        </a-card>

        <!-- 域名配置 -->
        <a-card
          v-if="hasConfig('host')"
          title="域名配置"
          :bordered="false"
          style="border-radius: 4px; background-color: var(--color-fill-1)"
        >
          <div style="padding: 8px">
            <a-space direction="vertical" size="mini" style="width: 100%">
              <div
                v-for="item in filteredConfig('host')"
                :key="item.key"
                style="display: flex; align-items: center; gap: 12px; padding: 4px 0"
              >
                <span style="color: var(--color-text-1); min-width: 110px"
                  >{{ item.describe }}:</span
                >
                <a-input
                  v-if="settingsData.editing"
                  v-model="item.value"
                  :placeholder="`请输入${item.describe}`"
                  allow-clear
                  size="small"
                  style="flex: 1"
                />
                <span v-else style="color: var(--color-text-2); flex: 1">{{
                  item.value || '未配置'
                }}</span>
              </div>
            </a-space>
          </div>
        </a-card>

        <!-- 邮箱配置 -->
        <a-card
          v-if="hasConfig('email')"
          title="邮箱配置"
          :bordered="false"
          style="border-radius: 4px; background-color: var(--color-fill-1)"
        >
          <div style="padding: 8px">
            <a-space direction="vertical" size="mini" style="width: 100%">
              <div
                v-for="item in filteredConfig('email')"
                :key="item.key"
                style="display: flex; align-items: center; gap: 12px; padding: 4px 0"
              >
                <span style="color: var(--color-text-1); min-width: 110px"
                  >{{ item.describe }}:</span
                >
                <a-input
                  v-if="settingsData.editing"
                  v-model="item.value"
                  :placeholder="`请输入${item.describe}`"
                  allow-clear
                  size="small"
                  style="flex: 1"
                />
                <span v-else style="color: var(--color-text-2); flex: 1">{{
                  item.value || '未配置'
                }}</span>
              </div>
            </a-space>
          </div>
        </a-card>

        <!-- 接口自动化配置 -->
        <a-card
          v-if="hasConfig('api')"
          title="接口自动化配置"
          :bordered="false"
          style="border-radius: 4px; background-color: var(--color-fill-1)"
        >
          <div style="padding: 8px">
            <a-space direction="vertical" size="mini" style="width: 100%">
              <div
                v-for="item in filteredConfig('api')"
                :key="item.key"
                style="display: flex; align-items: center; gap: 12px; padding: 4px 0"
              >
                <span style="color: var(--color-text-1); min-width: 110px"
                  >{{ item.describe }}:</span
                >
                <a-input
                  v-if="settingsData.editing"
                  v-model="item.value"
                  :placeholder="`请输入${item.describe}`"
                  allow-clear
                  size="small"
                  style="flex: 1"
                />
                <span v-else style="color: var(--color-text-2); flex: 1">{{
                  item.value || '未配置'
                }}</span>
              </div>
            </a-space>
          </div>
        </a-card>

        <!-- 单元自动化配置 -->
        <a-card
          v-if="hasConfig('pytest')"
          title="单元自动化配置"
          :bordered="false"
          style="border-radius: 4px; background-color: var(--color-fill-1)"
        >
          <div style="padding: 8px">
            <a-space direction="vertical" size="mini" style="width: 100%">
              <div
                v-for="item in filteredConfig('pytest')"
                :key="item.key"
                style="display: flex; align-items: center; gap: 12px; padding: 4px 0"
              >
                <span style="color: var(--color-text-1); min-width: 110px"
                  >{{ item.describe }}:</span
                >
                <a-input
                  v-if="settingsData.editing"
                  v-model="item.value"
                  :placeholder="`请输入${item.describe}`"
                  allow-clear
                  size="small"
                  style="flex: 1; max-width: 450px"
                />
                <span v-else style="color: var(--color-text-2); flex: 1">{{
                  item.value || '未配置'
                }}</span>
              </div>
            </a-space>
          </div>
        </a-card>
      </a-space>
    </template>
  </TableBody>
</template>

<script lang="ts" setup>
  import { onMounted, reactive, ref } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { getSystemCacheData, putSystemCacheData } from '@/api/system/cache_data'
  import { postSystemSetDebugLog } from '@/api/system/system'

  const loading = ref(false)
  const settingsData = reactive({
    editing: false,
    host: ['SYSTEM_DOMAIN_NAME'],
    email: ['SYSTEM_SEND_USER', 'SYSTEM_EMAIL_HOST', 'SYSTEM_STAMP_KET'],
    api: ['API_TIMEOUT'],
    pytest: [
      'PYTEST_GIT_URL',
      'PYTEST_GIT_USERNAME',
      'PYTEST_GIT_PASSWORD',
      'PYTEST_ACT',
      'PYTEST_TESTCASE',
      'PYTEST_TOOLS',
      'PYTEST_UPLOAD',
    ],
    data: [],
    isDebug: false,
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
  async function doPostSystemSetDebugLog(isDebug) {
    try {
      const res = await postSystemSetDebugLog(isDebug)
      settingsData.isDebug = res.data.is_debug
    } catch (error) {
      console.error(error)
    }
  }
  onMounted(() => {
    doRefresh()
    doPostSystemSetDebugLog(null)
  })
</script>

<style scoped></style>
