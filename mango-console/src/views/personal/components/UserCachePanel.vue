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
              :disabled="!group.items.some(item => item.clearable && item.has_value) || !!clearingKey || loading || failed"
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
            :scroll="{ x: cacheScrollX }"
            row-key="cache_key"
          >
            <template #display_value="{ record }">
              <span v-if="record.has_value" class="mango-personal-cache__value" :title="formatDisplayValue(record.display_value)">
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
      <div v-else-if="!loading && !failed" class="mango-empty-state">暂无个人缓存</div>
    </a-spin>
  </section>
</template>

<script lang="ts" setup>
import { reportLoadError } from '@/utils/load-error'

  import { onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, shallowRef, watch } from 'vue'
  import { useRoute } from 'vue-router'
  import { Message, Modal } from '@arco-design/web-vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import { clearUserCacheData, getUserCacheData } from '@/api/user/user'
  import useUserStore from '@/store/modules/user'
  import { cacheColumns, cacheScrollX } from '../config'
  import type { UserCacheGroup, UserCacheItem } from '../types'
  import { clearedCacheCount, formatDisplayValue, readCacheGroups } from '../records'

  const userStore = useUserStore()
  const groups = shallowRef<UserCacheGroup[]>([])
  const loading = ref(false)
  const clearingKey = ref('')
  const failed = ref(false)
  const route = useRoute()
  let mounted = false, active = true, disposed = false, needsRead = true, contextVersion = 0, readVersion = 0, dialogVersion = 0
  let pending: { promise: Promise<void> } | null = null
  let confirmation: ReturnType<typeof Modal.confirm> | null = null
  const available = () => !disposed && active && route.path === '/personal/info' && (typeof document === 'undefined' || !document.hidden)
  function closeConfirmation(): void { dialogVersion++; confirmation?.close(); confirmation = null }
  function suspend(clear: boolean): void {
    contextVersion++; readVersion++; pending = null; loading.value = false; needsRead = true
    closeConfirmation()
    if (clear) { groups.value = []; failed.value = false }
  }
  function loadData(): Promise<void> {
    if (!mounted || !available()) return Promise.resolve()
    if (pending) return pending.promise
    const context = contextVersion, request = ++readVersion
    const current = () => available() && context === contextVersion && request === readVersion
    loading.value = true
    failed.value = false
    const promise = Promise.resolve().then(async () => {
      try {
        if (!current()) return
        const response = await getUserCacheData()
        if (!current()) return
        groups.value = readCacheGroups(response)
        needsRead = false
      } catch (loadFailure0) { if (current()) (reportLoadError(loadFailure0, "加载失败，请重试", false), failed.value = true) }
      finally { if (current()) { loading.value = false; pending = null } }
    })
    pending = { promise }
    return promise
  }

  function confirmDeleteGroup(group: UserCacheGroup): void {
    confirmDelete(group.group_key)
  }

  function confirmDeleteItem(group: UserCacheGroup, item: UserCacheItem): void {
    confirmDelete(group.group_key, item.cache_key)
  }
  function confirmDelete(groupKey: string, cacheKey?: string): void {
    if (!available() || clearingKey.value || loading.value || failed.value) return
    const group = groups.value.find(item => item.group_key === groupKey)
    const item = cacheKey ? group?.items.find(item => item.cache_key === cacheKey) : null
    if (!group || (cacheKey ? !item?.clearable || !item.has_value : !group.items.some(item => item.clearable && item.has_value))) return
    closeConfirmation()
    const context = contextVersion, dialog = dialogVersion
    const current = () => available() && context === contextVersion && dialog === dialogVersion
    const clearsEnvironment = groupKey === 'preferences' && group.items.some(item =>
      item.cache_key === 'selected_environment' && item.value_type === 'environment' && item.has_value && item.clearable && (!cacheKey || cacheKey === item.cache_key))
    confirmation = Modal.confirm({
      title: item ? `删除“${item.title}”` : `删除“${group.title}”缓存`,
      content: item ? '删除后该值不可恢复，相关功能可能需要重新选择或生成数据。' : `将删除该分组内 ${group.value_count} 项个人缓存，相关功能可能需要重新选择或生成数据。`,
      okText: '删除', cancelText: '取消', okButtonProps: { status: 'danger' },
      onCancel: () => { dialogVersion++; confirmation = null },
      onBeforeOk: async () => {
        if (!current() || clearingKey.value) return false
        clearingKey.value = cacheKey ? `${groupKey}:${cacheKey}` : groupKey
        try {
          const count = clearedCacheCount(await clearUserCacheData({ group_key: groupKey, ...(cacheKey ? { cache_key: cacheKey } : {}) }))
          if (!current()) return false
          // 清除环境会使本页上下文失效；随后按新环境重新读取，不沿用旧请求。
          if (count > 0 && clearsEnvironment) userStore.selected_environment = null
          Message.success('个人缓存已删除')
          if (pending) { readVersion++; pending = null; loading.value = false }
          await loadData()
          return true
        } catch {
          if (current()) Message.error('缓存删除失败，请重试')
          return false
        } finally { clearingKey.value = '' }
      },
    })
  }

  function cacheActions(group: UserCacheGroup, item: UserCacheItem) {
    const itemKey = `${group.group_key}:${item.cache_key}`
    return [
      {
        label: '删除',
        danger: true,
        disabled: !item.clearable || !item.has_value || !!clearingKey.value || loading.value || failed.value,
        loading: clearingKey.value === itemKey,
        onClick: () => confirmDeleteItem(group, item),
      },
    ]
  }

  function resume(): void { if (mounted && needsRead) void loadData() }
  watch(() => [userStore.userId, userStore.roleId, userStore.token, userStore.selected_environment], () => {
    suspend(true); void Promise.resolve().then(resume)
  }, { flush: 'sync' })
  watch(() => route.path, () => { suspend(false); void Promise.resolve().then(resume) }, { flush: 'sync' })
  function onVisibilityChange(): void { if (document.hidden) suspend(false); else resume() }
  onMounted(() => { mounted = true; if (typeof document !== 'undefined') document.addEventListener('visibilitychange', onVisibilityChange); resume() })
  onActivated(() => { active = true; resume() })
  onDeactivated(() => { active = false; suspend(false) })
  onBeforeUnmount(() => { disposed = true; suspend(true); if (typeof document !== 'undefined') document.removeEventListener('visibilitychange', onVisibilityChange) })
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
