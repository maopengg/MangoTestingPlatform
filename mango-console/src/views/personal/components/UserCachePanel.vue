<template>
  <section class="mango-section-card mango-personal-cache" :aria-busy="loading">
    <div class="mango-personal-cache__header">
      <div>
        <h3 class="mango-section-title">个人缓存</h3>
        <p>这里的数据仅属于当前用户。删除后，相关功能会在下次使用时重新生成或要求重新选择。</p>
      </div>
    </div>

    <a-spin :loading="loading" class="mango-personal-cache__loading">
      <div v-if="groups.length" class="mango-personal-cache__groups">
        <section
          v-for="group in groups"
          :key="group.group_key"
          class="mango-personal-cache__group"
        >
          <div class="mango-personal-cache__group-header">
            <div class="mango-personal-cache__group-title">
              <strong>{{ group.title }}</strong>
              <span>{{ group.value_count }} / {{ group.count }} 项有值</span>
            </div>
            <a-button
              size="small"
              status="danger"
              :disabled="group.value_count === 0"
              :loading="clearingKey === group.group_key"
              @click="confirmDeleteGroup(group)"
            >
              删除分组缓存
            </a-button>
          </div>
          <a-table
            :columns="cacheColumns"
            :data="group.items"
            :pagination="false"
            :scroll="{ x: 1250 }"
            row-key="cache_key"
          >
            <template #display_value="{ record }">
              <span v-if="record.has_value" class="mango-personal-cache__value">
                {{ formatDisplayValue(record.display_value) }}
              </span>
              <span v-else class="mango-personal-cache__empty">未设置</span>
            </template>
            <template #updated_at="{ record }">{{ record.updated_at || '-' }}</template>
            <template #actions="{ record }">
              <MangoTableActions :actions="cacheActions(group, record)" />
            </template>
          </a-table>
        </section>
      </div>
      <div v-else class="mango-empty-state">暂无个人缓存</div>
    </a-spin>
  </section>
</template>

<script lang="ts" setup>
  import { onMounted, ref } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import { clearUserCacheData, getUserCacheData } from '@/api/user/user'
  import useUserStore from '@/store/modules/user'
  import { cacheColumns, UserCacheGroup, UserCacheItem } from '../config'

  const userStore = useUserStore()
  const groups = ref<UserCacheGroup[]>([])
  const loading = ref(false)
  const clearingKey = ref('')

  function formatDisplayValue(value: any) {
    if (typeof value === 'object') return JSON.stringify(value)
    if (typeof value === 'boolean') return value ? '是' : '否'
    return String(value)
  }

  async function loadData() {
    loading.value = true
    try {
      const res = await getUserCacheData()
      groups.value = res.data || []
    } finally {
      loading.value = false
    }
  }

  function confirmDeleteGroup(group: UserCacheGroup) {
    Modal.confirm({
      title: `删除“${group.title}”缓存`,
      content: `将删除该分组内 ${group.value_count} 项个人缓存，相关功能可能需要重新选择或生成数据。`,
      okText: '删除',
      onOk: () => deleteCache(group.group_key),
    })
  }

  function confirmDeleteItem(group: UserCacheGroup, item: UserCacheItem) {
    Modal.confirm({
      title: `删除“${item.title}”`,
      content: '删除后该值不可恢复，相关功能可能需要重新选择或生成数据。',
      okText: '删除',
      onOk: () => deleteCache(group.group_key, item.cache_key),
    })
  }

  async function deleteCache(groupKey: string, cacheKey?: string) {
    clearingKey.value = cacheKey ? `${groupKey}:${cacheKey}` : groupKey
    try {
      await clearUserCacheData({ group_key: groupKey, cache_key: cacheKey })
      if (!cacheKey || cacheKey === 'selected_environment') {
        userStore.selected_environment = null
      }
      Message.success('个人缓存已删除')
      await loadData()
    } finally {
      clearingKey.value = ''
    }
  }

  function cacheActions(group: UserCacheGroup, item: UserCacheItem) {
    const itemKey = `${group.group_key}:${item.cache_key}`
    return [
      {
        label: '删除',
        danger: true,
        disabled: !item.clearable || !item.has_value,
        loading: clearingKey.value === itemKey,
        onClick: () => confirmDeleteItem(group, item),
      },
    ]
  }

  onMounted(loadData)
</script>

<style lang="less" scoped>
  .mango-personal-cache {
    min-width: 0;
    padding: 16px;
  }

  .mango-personal-cache__header,
  .mango-personal-cache__group-header,
  .mango-personal-cache__group-title {
    display: flex;
    align-items: center;
  }

  .mango-personal-cache__header,
  .mango-personal-cache__group-header {
    justify-content: space-between;
    gap: var(--m-page-gap);
  }

  .mango-personal-cache__header p,
  .mango-personal-cache__group-title span {
    margin: 4px 0 0;
    color: var(--m-muted);
  }

  .mango-personal-cache__header h3 {
    margin: 0;
    font-size: 16px;
  }

  .mango-personal-cache__loading {
    display: block;
    min-height: 160px;
  }

  .mango-personal-cache__groups {
    display: grid;
    gap: var(--m-page-gap);
    margin-top: var(--m-page-gap);
  }

  .mango-personal-cache__group {
    min-width: 0;
    overflow: hidden;
    background: var(--m-surface);
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
  }

  .mango-personal-cache__group-header {
    padding: 8px 12px;
  }

  .mango-personal-cache__group-title {
    gap: 12px;
  }

  .mango-personal-cache__value,
  .mango-personal-cache__empty {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-personal-cache__empty {
    color: var(--m-muted);
  }
</style>
