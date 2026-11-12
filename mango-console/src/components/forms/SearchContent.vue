<template>
  <a-modal v-model:visible="visible" title="站内搜索" :footer="false" :width="760" @close="close">
    <div class="mango-site-search">
      <a-input v-model="keyword" placeholder="搜索菜单、用例、接口或报告；支持名称、ID、接口路径" allow-clear
        aria-label="站内搜索关键词" @press-enter="searchNow">
        <template #prefix><icon-search /></template>
      </a-input>
      <div class="mango-site-search__results">
        <section v-if="menuMatches.length" class="mango-site-search__group">
          <h3>菜单</h3>
          <button v-for="menu in menuMatches" :key="menu.path" class="mango-site-search__row" @click="navigate(menu.path)">
            <strong>{{ menu.title }}</strong><small>{{ menu.context }}</small>
          </button>
        </section>
        <section v-for="group in groups" :key="group.source.key" class="mango-site-search__group">
          <h3>{{ group.source.title }} <small>{{ group.total }} 条</small></h3>
          <button v-for="row in group.rows" :key="row.id" class="mango-site-search__row"
            @click="navigate(group.source.detail, row.id)">
            <strong>{{ row.title }}</strong><small>ID {{ row.id }}<template v-if="row.context"> · {{ row.context }}</template></small>
          </button>
          <a-button v-if="group.rows.length < group.total" type="text" size="small" :loading="group.loading" @click="loadMore(group)">加载更多</a-button>
        </section>
        <mango-panel-spin v-if="loading" :loading="loading" class="mango-site-search__loading" />
        <div v-if="!keyword.trim()" class="mango-empty-state">输入名称、ID 或接口路径开始搜索</div>
        <div v-else-if="!loading && !searchFailed && !groups.length && !menuMatches.length" class="mango-empty-state">没有匹配的结果</div>
        <a-button v-if="searchFailed" size="small" :loading="loading" @click="searchNow">重新搜索</a-button>
      </div>
    </div>
  </a-modal>
</template>

<script lang="ts" setup>
  import { computed, onBeforeUnmount, ref, watch } from 'vue'
  import { useRouter } from 'vue-router'
  import usePermissionStore from '@/store/modules/permission'
  import useUserStore from '@/store/modules/user'
  import { get } from '@/api/http'
  import { reportLoadError } from '@/utils/load-error'
  import { buildSearchQueries, collectSearchMenus, searchSources, toSearchRow } from './site-search'
  import type { SearchSource, SearchRow } from './site-search'

  interface SearchGroup { source: SearchSource; rows: SearchRow[]; total: number; page: number; loading: boolean }
  const router = useRouter(), permission = usePermissionStore(), user = useUserStore()
  const visible = ref(false), keyword = ref(''), loading = ref(false), searchFailed = ref(false)
  const groups = ref<SearchGroup[]>([])
  const menus = computed(() => collectSearchMenus(permission.getPermissionSideBar))
  const availableSources = computed(() => searchSources.filter(source => menus.value.some(menu => menu.path === source.menu)))
  const menuMatches = computed(() => keyword.value.trim() ? menus.value.filter(menu => menu.context.toLowerCase().includes(keyword.value.trim().toLowerCase())).slice(0, 12) : [])
  let timer: ReturnType<typeof setTimeout> | undefined, sequence = 0
  function cancel() { if (timer) clearTimeout(timer); timer = undefined; ++sequence; loading.value = false }
  function show() { visible.value = true }
  function close() { cancel(); visible.value = false; keyword.value = ''; groups.value = []; searchFailed.value = false }
  async function request(source: SearchSource, text: string, page: number) {
    const response = await get<unknown>({ url: source.endpoint, data: () => buildSearchQueries(source, text, page)[0] }) as { code?: number; data?: unknown; totalSize?: unknown }
    if (response.code !== 200 || !Array.isArray(response.data)) throw new Error('搜索响应格式不正确')
    const rows = response.data.map(toSearchRow).filter((row): row is SearchRow => row !== null)
    const total = response.totalSize == null && !rows.length ? 0 : Number(response.totalSize)
    if (!Number.isSafeInteger(total) || total < rows.length) throw new Error('搜索总数格式不正确')
    return { rows, total }
  }
  async function searchNow() {
    cancel(); groups.value = []; searchFailed.value = false
    const text = keyword.value.trim(), current = sequence
    if (!visible.value || !text) return
    loading.value = true
    const results = await Promise.allSettled(availableSources.value.map(async source => ({ source, ...await request(source, text, 1), page: 1, loading: false })))
    if (current !== sequence || !visible.value) return
    groups.value = results.flatMap(result => result.status === 'fulfilled' && result.value.rows.length ? [result.value] : [])
    const failure = results.find(result => result.status === 'rejected')
    if (failure?.status === 'rejected') { searchFailed.value = true; reportLoadError(failure.reason, '搜索失败，请重试') }
    loading.value = false
  }
  async function loadMore(group: SearchGroup) {
    if (group.loading || loading.value) return
    const current = sequence, text = keyword.value.trim()
    group.loading = true
    try {
      const result = await request(group.source, text, group.page + 1)
      if (current !== sequence || !visible.value) return
      group.rows = [...new Map([...group.rows, ...result.rows].map(row => [row.id, row])).values()]
      group.total = result.rows.length ? result.total : group.rows.length
      group.page += 1
    } catch (error) { if (current === sequence) reportLoadError(error, '搜索失败，请重试') }
    finally { group.loading = false }
  }
  async function navigate(path: string, id?: string) {
    try { await router.push(id === undefined ? path : { path, query: { id } }); close() }
    catch (error) { reportLoadError(error, '页面打开失败，请重试') }
  }
  watch(keyword, () => { cancel(); groups.value = []; searchFailed.value = false; if (visible.value && keyword.value.trim()) timer = setTimeout(() => { void searchNow() }, 500) })
  watch(availableSources, () => { cancel(); groups.value = [] })
  watch(() => [user.userId, user.roleId, user.token, user.selected_environment], close, { flush: 'sync' })
  onBeforeUnmount(close)
  defineExpose({ show, close })
</script>

<style scoped lang="less">
  .mango-site-search { display: flex; min-height: 0; flex-direction: column; gap: 16px; }
  .mango-site-search__results { max-height: 62vh; overflow: auto; overscroll-behavior: contain; }
  .mango-site-search__group { margin-bottom: 16px; }
  .mango-site-search__group h3 { margin: 0 0 8px; color: var(--m-text); font-size: 14px; }
  .mango-site-search__group small { color: var(--m-muted); font-size: 12px; font-weight: 400; }
  .mango-site-search__row { display: flex; width: 100%; min-width: 0; padding: 10px 12px; flex-direction: column; gap: 4px; border: 0; border-bottom: 1px solid var(--m-border); background: var(--m-surface); text-align: left; cursor: pointer; }
  .mango-site-search__row:hover { background: var(--m-surface-soft); }
  .mango-site-search__row:focus-visible { outline: 2px solid var(--m-primary); outline-offset: -2px; }
  .mango-site-search__row strong { overflow: hidden; color: var(--m-text); text-overflow: ellipsis; white-space: nowrap; font-size: 14px; }
  .mango-site-search__row small { overflow-wrap: anywhere; color: var(--m-muted); font-size: 12px; }
  .mango-site-search__loading { display: block; min-height: 60px; }
</style>
