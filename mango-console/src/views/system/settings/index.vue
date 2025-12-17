<template>
  <TableBody ref="tableBody">
    <template #header>
      <TableHeader :show-filter="true" title="全局系统设置" />
    </template>
    <template #default>
      <div class="settings-container">
        <!-- 第一组：后端服务设置 和 邮箱配置 -->
        <div class="settings-row">
          <!-- 后端服务设置 -->
          <div class="settings-card">
            <div class="card-header">
              <h3 class="card-title">后端服务设置</h3>
            </div>
            <div class="card-content">
              <div class="debug-setting">
                <span class="setting-label">设置系统debug级别日志</span>
                <a-switch
                  v-model="settingsData.isDebug"
                  @change="doPostSystemSetDebugLog"
                  size="small"
                />
              </div>
            </div>
          </div>

          <!-- 邮箱配置 -->
          <div class="settings-card">
            <div class="card-header">
              <h3 class="card-title">邮箱配置</h3>
              <a-button
                size="small"
                type="primary"
                @click="handleEditToggle('email')"
                :loading="loading.email"
                class="edit-btn"
              >
                {{ editingStates.email ? '保存配置' : '修改配置' }}
              </a-button>
            </div>
            <div class="card-content">
              <div v-for="item in filteredConfig('email')" :key="item.key" class="setting-item">
                <div class="setting-row">
                  <!-- 将域名配置改名为测试报告地址 -->
                  <span class="setting-label" v-if="item.key === 'SYSTEM_DOMAIN_NAME'"
                    >测试报告地址</span
                  >
                  <span class="setting-label" v-else>{{ item.describe }}</span>
                  <div class="setting-control">
                    <a-input
                      v-if="editingStates.email"
                      v-model="item.value"
                      :placeholder="`请输入${item.describe}`"
                      allow-clear
                      size="small"
                      class="setting-input"
                    />
                    <span v-else class="setting-value">{{ item.value || '未配置' }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 第二组：接口自动化配置 和 界面自动化配置 -->
        <div class="settings-row">
          <!-- 接口自动化配置 -->
          <div class="settings-card">
            <div class="card-header">
              <h3 class="card-title">接口自动化配置</h3>
              <a-button
                size="small"
                type="primary"
                @click="handleEditToggle('api')"
                :loading="loading.api"
                class="edit-btn"
              >
                {{ editingStates.api ? '保存配置' : '修改配置' }}
              </a-button>
            </div>
            <div class="card-content">
              <div v-for="item in filteredConfig('api')" :key="item.key" class="setting-item">
                <div class="setting-row">
                  <span class="setting-label">{{ item.describe }}</span>
                  <div class="setting-control">
                    <a-input
                      v-if="editingStates.api"
                      v-model="item.value"
                      :placeholder="`请输入${item.describe}`"
                      allow-clear
                      size="small"
                      class="setting-input"
                    />
                    <span v-else class="setting-value">{{ item.value || '未配置' }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 界面自动化配置 -->
          <div class="settings-card">
            <div class="card-header">
              <h3 class="card-title">界面自动化配置</h3>
              <a-button
                size="small"
                type="primary"
                @click="handleEditToggle('ui')"
                :loading="loading.ui"
                class="edit-btn"
              >
                {{ editingStates.ui ? '保存配置' : '修改配置' }}
              </a-button>
            </div>
            <div class="card-content empty-content">
              <!-- 留空，后续添加设置项 -->
              <div class="empty-placeholder">
                <a-empty description="暂无配置项" />
              </div>
            </div>
          </div>
        </div>

        <!-- 第三组：单元自动化配置（独自占用一行） -->
        <div class="settings-row full-width">
          <!-- 单元自动化配置 -->
          <div class="settings-card">
            <div class="card-header">
              <h3 class="card-title">单元自动化配置</h3>
              <a-button
                size="small"
                type="primary"
                @click="handleEditToggle('pytest')"
                :loading="loading.pytest"
                class="edit-btn"
              >
                {{ editingStates.pytest ? '保存配置' : '修改配置' }}
              </a-button>
            </div>
            <div class="card-content">
              <div v-for="item in filteredConfig('pytest')" :key="item.key" class="setting-item">
                <div class="setting-row">
                  <span class="setting-label">{{ item.describe }}</span>
                  <div class="setting-control">
                    <a-input
                      v-if="editingStates.pytest"
                      v-model="item.value"
                      :placeholder="`请输入${item.describe}`"
                      allow-clear
                      size="small"
                      class="setting-input"
                    />
                    <span v-else class="setting-value">{{ item.value || '未配置' }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </TableBody>
</template>
<script lang="ts" setup>
  import { onMounted, reactive } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { getSystemCacheData, putSystemCacheData } from '@/api/system/cache_data'
  import { postSystemSetDebugLog } from '@/api/system/system'

  const loading = reactive({
    host: false,
    email: false,
    api: false,
    pytest: false,
    ui: false,
  })

  const editingStates = reactive({
    host: false,
    email: false,
    api: false,
    pytest: false,
    ui: false,
  })

  const settingsData = reactive({
    host: ['SYSTEM_DOMAIN_NAME'],
    email: ['SYSTEM_SEND_USER', 'SYSTEM_EMAIL_HOST', 'SYSTEM_STAMP_KET', 'SYSTEM_DOMAIN_NAME'],
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
    ui: [],
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

  // 处理编辑状态切换和保存
  const handleEditToggle = async (type) => {
    if (editingStates[type]) {
      // 保存配置
      loading[type] = true
      try {
        // 只保存当前类型的配置
        const currentTypeConfigs = filteredConfig(type)
        currentTypeConfigs.forEach((item) => {
          if (item.value === '') {
            item.value = null
          }
        })

        const res = await putSystemCacheData(currentTypeConfigs)
        Message.success(res.msg)
        await doRefresh()
      } catch (error) {
        console.error(error)
      } finally {
        loading[type] = false
      }
    }
    // 切换编辑状态
    editingStates[type] = !editingStates[type]
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
      // 显示接口返回的提示信息
      Message.success(res.msg)
    } catch (error) {
      console.error(error)
    }
  }

  onMounted(() => {
    doRefresh()
  })
</script>

<style scoped>
  .settings-container {
    padding: 20px;
    background-color: var(--color-bg-1);
    border-radius: 8px;
  }

  .settings-row {
    display: flex;
    gap: 20px;
    margin-bottom: 20px;
  }

  .settings-row.full-width {
    flex-direction: column;
  }

  .settings-row.full-width .settings-card {
    width: 100%;
  }

  .settings-card {
    flex: 1;
    background-color: var(--color-bg-2);
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    overflow: hidden;
    transition: all 0.3s ease;
  }

  .settings-card:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    transform: translateY(-2px);
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 20px;
    background-color: var(--color-fill-1);
    border-bottom: 1px solid var(--color-border);
  }

  .card-title {
    margin: 0;
    font-size: 16px;
    font-weight: 600;
    color: var(--color-text-1);
  }

  .edit-btn {
    font-size: 12px;
    padding: 4px 12px;
  }

  .card-content {
    padding: 20px;
    min-height: 150px;
  }

  .empty-content {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 150px;
  }

  .empty-placeholder {
    width: 100%;
    text-align: center;
    color: var(--color-text-3);
  }

  .debug-setting {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 0;
    border-bottom: 1px solid var(--color-border);
  }

  .setting-item {
    margin-bottom: 16px;
  }

  .setting-item:last-child {
    margin-bottom: 0;
  }

  .setting-row {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .setting-label {
    font-size: 14px;
    color: var(--color-text-1);
    font-weight: 500;
  }

  .setting-control {
    width: 100%;
  }

  .setting-input {
    width: 100%;
  }

  .setting-value {
    display: block;
    padding: 6px 12px;
    background-color: var(--color-fill-1);
    border-radius: 4px;
    font-size: 14px;
    color: var(--color-text-2);
    min-height: 32px;
    line-height: 1.5;
  }

  /* 响应式设计 */
  @media (max-width: 768px) {
    .settings-row {
      flex-direction: column;
    }

    .settings-card {
      width: 100%;
    }
  }
</style>
