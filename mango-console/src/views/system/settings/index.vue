<template>
  <TableBody ref="tableBody">
    <template #header>
      <TableHeader :show-filter="true" title="全局系统设置" />
    </template>
    <template #default>
      <div class="settings-container">
        <div class="settings-columns">
          <div class="settings-column">
            <div class="settings-card">
              <div class="card-header">
                <h3 class="card-title">后端服务设置</h3>
              </div>
              <div class="card-content compact-content">
                <div class="debug-setting">
                  <span class="setting-label">设置系统debug级别日志</span>
                  <a-switch
                    v-model="settingsData.isDebug"
                    size="small"
                    @change="doPostSystemSetDebugLog"
                  />
                </div>
              </div>
            </div>

            <div v-for="group in leftGroups" :key="group.key" class="settings-card">
              <div class="card-header">
                <h3 class="card-title">{{ group.title }}</h3>
                <div class="card-actions">
                  <a-button
                    v-if="isAiGroup(group)"
                    size="small"
                    :loading="aiTestLoading"
                    :disabled="groupEditing(group.key)"
                    @click="handleAiTest"
                  >
                    测试配置
                  </a-button>
                  <a-button
                    size="small"
                    type="primary"
                    :loading="groupLoading(group.key)"
                    class="edit-btn"
                    @click="handleEditToggle(group)"
                  >
                    {{ groupEditing(group.key) ? '保存配置' : '修改配置' }}
                  </a-button>
                </div>
              </div>
              <div class="card-content">
                <div v-if="group.items.length === 0" class="mango-empty-state empty-placeholder">
                  暂无配置项
                </div>
                <div v-for="item in group.items" :key="item.key" class="setting-item">
                  <div class="setting-row">
                    <span class="setting-label">{{ item.describe }}</span>
                    <div class="setting-control">
                      <a-switch
                        v-if="groupEditing(group.key) && isSwitchType(item)"
                        :model-value="switchValue(item)"
                        size="small"
                        @change="(value) => setSwitchValue(item, value)"
                      />
                      <a-input-number
                        v-else-if="groupEditing(group.key) && isNumberType(item)"
                        v-model="item.value"
                        :precision="item.value_type === VALUE_TYPE_INT ? 0 : undefined"
                        :placeholder="getPlaceholder(item)"
                        size="small"
                        class="setting-input"
                      />
                      <a-textarea
                        v-else-if="groupEditing(group.key) && isLongTextType(item)"
                        v-model="item.value"
                        :placeholder="getPlaceholder(item)"
                        allow-clear
                        auto-size
                        size="small"
                        class="setting-input"
                      />
                      <a-input-password
                        v-else-if="groupEditing(group.key) && item.is_secret"
                        v-model="item.value"
                        :placeholder="getPlaceholder(item)"
                        allow-clear
                        size="small"
                        class="setting-input"
                      />
                      <a-input
                        v-else-if="groupEditing(group.key)"
                        v-model="item.value"
                        :placeholder="getPlaceholder(item)"
                        allow-clear
                        size="small"
                        class="setting-input"
                      />
                      <span v-else class="setting-value">{{ displayValue(item) }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="settings-column">
            <div v-for="group in rightGroups" :key="group.key" class="settings-card">
              <div class="card-header">
                <h3 class="card-title">{{ group.title }}</h3>
                <div class="card-actions">
                  <a-button
                    v-if="isAiGroup(group)"
                    size="small"
                    :loading="aiTestLoading"
                    :disabled="groupEditing(group.key)"
                    @click="handleAiTest"
                  >
                    测试配置
                  </a-button>
                  <a-button
                    size="small"
                    type="primary"
                    :loading="groupLoading(group.key)"
                    class="edit-btn"
                    @click="handleEditToggle(group)"
                  >
                    {{ groupEditing(group.key) ? '保存配置' : '修改配置' }}
                  </a-button>
                </div>
              </div>
              <div class="card-content">
                <div v-if="group.items.length === 0" class="mango-empty-state empty-placeholder">
                  暂无配置项
                </div>
                <div v-for="item in group.items" :key="item.key" class="setting-item">
                  <div class="setting-row">
                    <span class="setting-label">{{ item.describe }}</span>
                    <div class="setting-control">
                      <a-switch
                        v-if="groupEditing(group.key) && isSwitchType(item)"
                        :model-value="switchValue(item)"
                        size="small"
                        @change="(value) => setSwitchValue(item, value)"
                      />
                      <a-input-number
                        v-else-if="groupEditing(group.key) && isNumberType(item)"
                        v-model="item.value"
                        :precision="item.value_type === VALUE_TYPE_INT ? 0 : undefined"
                        :placeholder="getPlaceholder(item)"
                        size="small"
                        class="setting-input"
                      />
                      <a-textarea
                        v-else-if="groupEditing(group.key) && isLongTextType(item)"
                        v-model="item.value"
                        :placeholder="getPlaceholder(item)"
                        allow-clear
                        auto-size
                        size="small"
                        class="setting-input"
                      />
                      <a-input-password
                        v-else-if="groupEditing(group.key) && item.is_secret"
                        v-model="item.value"
                        :placeholder="getPlaceholder(item)"
                        allow-clear
                        size="small"
                        class="setting-input"
                      />
                      <a-input
                        v-else-if="groupEditing(group.key)"
                        v-model="item.value"
                        :placeholder="getPlaceholder(item)"
                        allow-clear
                        size="small"
                        class="setting-input"
                      />
                      <span v-else class="setting-value">{{ displayValue(item) }}</span>
                    </div>
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
  import { computed, onMounted, reactive, ref } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { postSystemAiTest } from '@/api/system/ai'
  import { getSystemCacheDataGrouped, putSystemCacheData } from '@/api/system/cache_data'
  import { postSystemSetDebugLog } from '@/api/system/system'

  const VALUE_TYPE_INT = 1
  const VALUE_TYPE_FLOAT = 2
  const VALUE_TYPE_BOOL = 3
  const VALUE_TYPE_LIST = 5
  const VALUE_TYPE_DICT = 6
  const VALUE_TYPE_JSON = 8

  interface ConfigItem {
    id: number
    key: string
    describe: string
    value: any
    value_type: number
    is_secret: boolean
    has_value: boolean
    placeholder?: string
  }

  interface ConfigGroup {
    key: string
    title: string
    items: ConfigItem[]
  }

  const settingsGroups = ref<ConfigGroup[]>([])
  const aiTestLoading = ref(false)
  const loading = reactive<Record<string, boolean>>({})
  const editingStates = reactive<Record<string, boolean>>({})
  const hiddenConfigKeys = ['AI_PROVIDER_TYPE']
  const integerSwitchKeys = ['AI_UI_LOCATOR_ENABLED']

  const settingsData = reactive({
    isDebug: false,
  })

  const visibleGroups = computed(() =>
    settingsGroups.value
      .map((group) => ({
        ...group,
        items: group.items.filter((item) => !hiddenConfigKeys.includes(item.key)),
      }))
      .filter((group) => group.items.length > 0),
  )
  const leftGroups = computed(() => visibleGroups.value.filter((_, index) => index % 2 === 1))
  const rightGroups = computed(() => visibleGroups.value.filter((_, index) => index % 2 === 0))
  const groupLoading = (key: string) => loading[key] === true
  const groupEditing = (key: string) => editingStates[key] === true
  const isAiGroup = (group: ConfigGroup) => group.key === 'ai'
  const isNumberType = (item: ConfigItem) =>
    item.value_type === VALUE_TYPE_INT || item.value_type === VALUE_TYPE_FLOAT
  const isBoolType = (item: ConfigItem) => item.value_type === VALUE_TYPE_BOOL
  const isIntegerSwitchType = (item: ConfigItem) => integerSwitchKeys.includes(item.key)
  const isSwitchType = (item: ConfigItem) => isBoolType(item) || isIntegerSwitchType(item)
  const isLongTextType = (item: ConfigItem) =>
    [VALUE_TYPE_LIST, VALUE_TYPE_DICT, VALUE_TYPE_JSON].includes(item.value_type)
  const getPlaceholder = (item: ConfigItem) => item.placeholder || `请输入${item.describe}`
  const isEnabledValue = (value: any) => [true, 1, '1', 'true', 'True'].includes(value)
  const switchValue = (item: ConfigItem) => isEnabledValue(item.value)
  const setSwitchValue = (item: ConfigItem, value: boolean | string | number) => {
    item.value = isEnabledValue(value)
  }

  const displayValue = (item: ConfigItem) => {
    if (item.is_secret) {
      return item.has_value ? '已配置' : '未配置'
    }
    if (item.value === null || item.value === undefined || item.value === '') {
      return '未配置'
    }
    if (isSwitchType(item)) {
      return switchValue(item) ? '开启' : '关闭'
    }
    return String(item.value)
  }

  const normalizeEditValue = (item: ConfigItem) => {
    if (isSwitchType(item)) {
      return switchValue(item)
    }
    if (isLongTextType(item) && typeof item.value !== 'string') {
      return JSON.stringify(item.value, null, 2)
    }
    return item.value
  }

  const normalizePayloadValue = (item: ConfigItem) => {
    if (isIntegerSwitchType(item)) {
      return switchValue(item) ? 1 : 0
    }
    return item.value === '' ? null : item.value
  }

  const ensureGroupState = (groups: ConfigGroup[]) => {
    groups.forEach((group) => {
      loading[group.key] = loading[group.key] || false
      editingStates[group.key] = editingStates[group.key] || false
    })
  }

  const buildPayload = (group: ConfigGroup) => {
    return group.items.map((item) => ({
      id: item.id,
      key: item.key,
      value: normalizePayloadValue(item),
    }))
  }

  const handleEditToggle = async (group: ConfigGroup) => {
    if (!groupEditing(group.key)) {
      group.items.forEach((item) => {
        item.value = normalizeEditValue(item)
      })
      editingStates[group.key] = true
      return
    }

    loading[group.key] = true
    try {
      const res = await putSystemCacheData(buildPayload(group))
      Message.success(res.msg)
      editingStates[group.key] = false
      await doRefresh()
    } catch (error) {
      console.error(error)
    } finally {
      loading[group.key] = false
    }
  }

  const handleAiTest = async () => {
    aiTestLoading.value = true
    try {
      const res = await postSystemAiTest()
      if (res.data?.status) {
        Message.success(res.data.message || res.msg)
      } else {
        Message.error(res.data?.message || 'AI配置测试失败')
      }
    } catch (error) {
      console.error(error)
    } finally {
      aiTestLoading.value = false
    }
  }

  async function doRefresh() {
    try {
      const res = await getSystemCacheDataGrouped()
      settingsGroups.value = res.data || []
      ensureGroupState(settingsGroups.value)
    } catch (error) {
      console.error(error)
    }
  }

  async function doPostSystemSetDebugLog(isDebug: boolean) {
    try {
      const res = await postSystemSetDebugLog(isDebug)
      settingsData.isDebug = res.data.is_debug
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
    padding: 16px;
    background-color: var(--m-bg);
  }

  .settings-columns {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    align-items: start;
    gap: 16px;
  }

  .settings-column {
    display: flex;
    flex-direction: column;
    gap: 16px;
    min-width: 0;
  }

  .settings-card {
    min-width: 0;
    background-color: var(--m-surface);
    border: 1px solid var(--m-border);
    border-radius: 8px;
    overflow: hidden;
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    min-height: 48px;
    padding: 10px 14px;
    background-color: var(--m-surface-soft);
    border-bottom: 1px solid var(--m-border);
  }

  .card-title {
    margin: 0;
    font-size: 15px;
    font-weight: 600;
    color: var(--m-text);
  }

  .edit-btn {
    flex: 0 0 auto;
  }

  .card-actions {
    display: flex;
    align-items: center;
    gap: 8px;
    flex: 0 0 auto;
  }

  .card-content {
    padding: 14px;
    min-height: 126px;
  }

  .compact-content {
    min-height: auto;
  }

  .debug-setting {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    min-height: 32px;
  }

  .setting-item + .setting-item {
    margin-top: 12px;
  }

  .setting-row {
    display: grid;
    grid-template-columns: minmax(128px, 180px) minmax(0, 1fr);
    align-items: center;
    gap: 12px;
  }

  .setting-label {
    min-width: 0;
    font-size: 14px;
    line-height: 20px;
    color: var(--m-text);
  }

  .setting-control {
    min-width: 0;
  }

  .setting-input {
    width: 100%;
  }

  .setting-value {
    display: block;
    min-height: 30px;
    padding: 5px 10px;
    overflow: hidden;
    color: var(--m-text-2);
    font-size: 14px;
    line-height: 20px;
    text-overflow: ellipsis;
    white-space: nowrap;
    background-color: var(--m-surface-soft);
    border: 1px solid var(--m-border);
    border-radius: 6px;
  }

  .empty-placeholder {
    height: 88px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--m-muted);
  }

  @media (max-width: 960px) {
    .settings-columns {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 640px) {
    .setting-row {
      grid-template-columns: 1fr;
      align-items: stretch;
      gap: 6px;
    }
  }
</style>
