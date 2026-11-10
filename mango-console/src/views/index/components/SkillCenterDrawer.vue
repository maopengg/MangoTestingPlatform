<template>
  <a-drawer
    class="mango-skill-center-drawer"
    :visible="visible"
    :width="'min(1120px, calc(100vw - 32px))'"
    :footer="false"
    unmount-on-close
    @cancel="close"
  >
    <template #title>
      <div class="mango-skill-center__drawer-title">
        <strong>Skill 中心</strong>
        <span>查看项目内置的测试规范与自动化能力</span>
      </div>
    </template>

    <div class="mango-skill-center">
      <aside class="mango-skill-center__sidebar mango-section-card">
        <header class="mango-skill-center__sidebar-header">
          <div><strong>项目 Skill</strong><span>{{ skills.length }} 个</span></div>
          <a-button size="mini" type="text" :loading="loading" aria-label="刷新 Skill 列表" @click="loadSkills">
            <template #icon><icon-refresh /></template>
          </a-button>
        </header>

        <a-input-search v-model="keyword" class="mango-skill-center__search" size="small" allow-clear placeholder="搜索 Skill" />

        <mango-panel-spin :loading="loading" class="mango-skill-center__list-spin">
          <div v-if="filteredSkills.length" class="mango-skill-center__list mango-custom-scrollbar">
            <button
              v-for="item in filteredSkills"
              :key="item.key"
              type="button"
              class="mango-skill-center__item"
              :class="{ 'mango-skill-center__item--active': item.key === selectedKey }"
              @click="selectSkill(item.key)"
            >
              <span class="mango-skill-center__item-icon"><icon-book /></span>
              <span class="mango-skill-center__item-content">
                <strong>{{ item.name || item.key }}</strong>
                <span>{{ item.description || '暂无说明' }}</span>
                <em v-if="item.category">{{ item.category }}</em>
              </span>
            </button>
          </div>
          <template v-else-if="!loading && loadFailed"></template>
          <div v-else-if="!loading" class="mango-empty-state mango-skill-center__list-empty">
            {{ skills.length ? '没有匹配的 Skill' : '暂无 Skill 文档' }}
          </div>
        </mango-panel-spin>
      </aside>

      <section class="mango-skill-center__detail mango-section-card">
        <mango-panel-spin :loading="detailLoading" class="mango-skill-center__detail-spin">
          <template v-if="detail">
            <header class="mango-skill-center__hero">
              <div class="mango-skill-center__hero-main">
                <span class="mango-skill-center__eyebrow">{{ detail.category || '项目规范' }}</span>
                <h2>{{ detail.name || detail.key }}</h2>
                <p>{{ detail.description || detail.original_description || '暂无说明' }}</p>
              </div>
              <a-button
                type="primary"
                size="small"
                :loading="downloadingKey === detail.key"
                :disabled="downloadingKey !== null"
                @click="downloadSkill(detail)"
              >
                <template #icon><icon-download /></template>
                下载 Skill
              </a-button>
            </header>

            <div class="mango-skill-center__meta">
              <div><span>目录名称</span><strong>{{ detail.key }}</strong></div>
              <div><span>规则章节</span><strong>{{ detail.sections?.length || 0 }}</strong></div>
              <div><span>介绍来源</span><strong>{{ detail.has_custom_introduction ? '介绍配置' : 'Skill 原文' }}</strong></div>
            </div>

            <div v-if="detail.sections?.length" class="mango-skill-center__catalog">
              <span>内容目录</span>
              <div>
                <a-tag v-for="section in detail.sections" :key="section.title" size="small">{{ section.title }}</a-tag>
              </div>
            </div>

            <article class="mango-skill-center__markdown mango-custom-scrollbar" v-html="detailHtml"></article>

          </template>
          <div v-else-if="!detailLoading" class="mango-empty-state mango-skill-center__detail-empty">
            {{ skills.length ? '请选择一个 Skill 查看详情' : '项目目录中暂无可展示的 Skill' }}
          </div>
        </mango-panel-spin>
      </section>
    </div>
  </a-drawer>
</template>

<script lang="ts" setup>
import { reportLoadError } from '@/utils/load-error'

  import { computed, nextTick, onActivated, onBeforeUnmount, onDeactivated, ref, watch } from 'vue'
  import { IconBook, IconDownload, IconRefresh } from '@arco-design/web-vue/es/icon'
  import { Message } from '@arco-design/web-vue'
  import { zipSync } from 'fflate'
  import { useRoute } from 'vue-router'
  import useUserStore from '@/store/modules/user'
  import { createSkillRecord, parseIntroductions, renderMarkdown } from '../skill-documents'
  import type { SkillRecord } from '../types'

  const skillDocuments = import.meta.glob('../../../../../skill/*/SKILL.md', {
    eager: true,
    query: '?raw',
    import: 'default',
  }) as Record<string, string>
  const introductionDocuments = import.meta.glob('../../../../../skill/introductions.json', {
    eager: true,
    query: '?raw',
    import: 'default',
  }) as Record<string, string>
  const skillAssetUrls = import.meta.glob(
    [
      '../../../../../skill/*/**',
      '!../../../../../skill/**/.DS_Store',
      '!../../../../../skill/**/__pycache__/**',
      '!../../../../../skill/**/*.pyc',
    ],
    {
      eager: true,
      query: '?url',
      import: 'default',
    }
  ) as Record<string, string>

  const props = withDefaults(defineProps<{ visible?: boolean }>(), { visible: false })
  const emit = defineEmits<{ (event: 'update:visible', value: boolean): void }>()
  const loading = ref(false)
  const detailLoading = ref(false)
  const skills = ref<SkillRecord[]>([])
  const selectedKey = ref<string | null>(null)
  const detail = computed(() => skills.value.find(item => item.key === selectedKey.value) ?? null)
  const keyword = ref('')
  const downloadingKey = ref<string | null>(null)
  const loadFailed = ref(false)
  const route = useRoute(), user = useUserStore(), entryPath = route.path
  const contextKey = computed(() => JSON.stringify([
    route.fullPath, user.userId, user.roleId, user.token, user.selected_environment,
  ]))
  let active = true, generation = 0, detailSequence = 0
  let downloadController: AbortController | null = null
  const urls = new Map<string, ReturnType<typeof setTimeout>>()
  const available = () => active && route.path === entryPath && props.visible
  function releaseUrl(url: string) {
    const timer = urls.get(url)
    if (timer !== undefined) clearTimeout(timer)
    URL.revokeObjectURL(url)
    urls.delete(url)
  }
  function invalidate() {
    generation++; detailSequence++
    downloadController?.abort()
    loading.value = false; detailLoading.value = false; loadFailed.value = false
    skills.value = []; selectedKey.value = null; keyword.value = ''
    for (const url of urls.keys()) releaseUrl(url)
  }

  const visible = computed(() => props.visible)
  const filteredSkills = computed(() => {
    const query = keyword.value.trim().toLowerCase()
    if (!query) return skills.value
    return skills.value.filter((item) =>
      [item.key, item.name, item.description, item.category]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(query))
    )
  })
  const detailHtml = computed(() => renderMarkdown(detail.value?.content || ''))

  function close() {
    invalidate()
    emit('update:visible', false)
  }

  async function loadSkills() {
    if (!available()) return
    const currentGeneration = ++generation
    detailSequence++
    detailLoading.value = false
    loading.value = true
    loadFailed.value = false
    try {
      const introductions = parseIntroductions(introductionDocuments)
      const rows = Object.entries(skillDocuments)
        .map(([path, content]) => createSkillRecord(path, content, introductions))
        .filter((item): item is SkillRecord => Boolean(item))
        .sort((previous, next) => previous.name.localeCompare(next.name, 'zh-CN'))
      await nextTick()
      if (!available() || generation !== currentGeneration) return
      skills.value = rows
      const key = rows.some(item => item.key === selectedKey.value) ? selectedKey.value : rows[0]?.key ?? null
      if (key) selectSkill(key)
      else selectedKey.value = null
    } catch (loadFailure0) {
      if (available() && generation === currentGeneration) (reportLoadError(loadFailure0, "加载失败，请重试", false), loadFailed.value = true)
    } finally {
      if (available() && generation === currentGeneration) loading.value = false
    }
  }

  function selectSkill(key: string) {
    if (!available()) return
    const sequence = ++detailSequence, currentGeneration = generation
    selectedKey.value = skills.value.some(item => item.key === key) ? key : null
    detailLoading.value = true
    nextTick(() => {
      if (available() && currentGeneration === generation && sequence === detailSequence) detailLoading.value = false
    })
  }

  async function downloadSkill(record: SkillRecord) {
    if (!available() || downloadingKey.value !== null || !skills.value.some(item => item.key === record.key)) return
    const currentGeneration = generation, key = record.key
    const current = () => available() && currentGeneration === generation
    const controller = new AbortController()
    downloadController = controller
    downloadingKey.value = key
    try {
      const skillRoot = `/skill/${key}/`
      const assets = Object.entries(skillAssetUrls).filter(([path]) => path.includes(skillRoot))
      if (!assets.length) throw Error('Empty Skill assets')
      // 一个文件失败后仍等待其余请求结束，避免提前释放物理下载锁。
      const results = await Promise.allSettled(assets.map(async ([path, assetUrl]) => {
        const relativePath = path.slice(path.indexOf(skillRoot) + skillRoot.length)
        const response = await fetch(assetUrl, { signal: controller.signal })
        if (!response.ok) throw Error('Skill asset unavailable')
        return [relativePath, new Uint8Array(await response.arrayBuffer())] as const
      }))
      if (!current()) return
      const files = results.map(result => {
        if (result.status === 'rejected') throw Error('Skill asset unavailable')
        return result.value
      })
      const archive = zipSync(Object.fromEntries(files), { level: 6 })
      if (!current()) return
      const url = URL.createObjectURL(new Blob([archive], { type: 'application/zip' }))
      urls.set(url, setTimeout(() => releaseUrl(url), 1000))
      const link = document.createElement('a')
      link.href = url
      link.download = `${key}.zip`
      document.body.appendChild(link)
      try { link.click() } finally { document.body.removeChild(link) }
      Message.success(`已打包 ${files.length} 个文件，开始下载`)
    } catch {
      if (current()) Message.error('Skill 打包失败，请重试')
    } finally {
      downloadingKey.value = null
      if (downloadController === controller) downloadController = null
    }
  }

  watch(() => props.visible, value => {
    if (value) void loadSkills()
    else invalidate()
  }, { immediate: true, flush: 'sync' })
  watch(contextKey, () => { invalidate(); emit('update:visible', false) }, { flush: 'sync' })
  onDeactivated(() => { active = false; close() })
  onActivated(() => { if (!active) { active = true; if (props.visible) void loadSkills() } })
  onBeforeUnmount(() => { active = false; invalidate() })
</script>

<style scoped lang="less">
  :deep(.mango-skill-center-drawer .arco-drawer-body) {
    min-height: 0;
    padding: var(--m-page-gap);
    overflow: hidden;
    background: var(--m-bg);
  }

  .mango-skill-center__drawer-title {
    display: flex;
    min-width: 0;
    flex-direction: column;

    strong { color: var(--m-text); font-size: 16px; line-height: 20px; }
    span { color: var(--m-muted); font-size: 12px; font-weight: 400; line-height: 15px; }
  }

  .mango-skill-center {
    display: grid;
    width: 100%;
    height: 100%;
    min-width: 0;
    min-height: 0;
    grid-template-columns: 286px minmax(0, 794px);
    gap: var(--m-page-gap);
  }

  .mango-skill-center > .mango-section-card + .mango-section-card {
    margin-top: 0;
  }

  .mango-skill-center__sidebar,
  .mango-skill-center__detail { min-width: 0; min-height: 0; overflow: hidden; }

  .mango-skill-center__sidebar { display: flex; padding: 12px; flex-direction: column; }
  .mango-skill-center__sidebar-header {
    display: flex; align-items: center; justify-content: space-between;
    > div { display: flex; align-items: baseline; gap: 6px; }
    strong { color: var(--m-text); font-size: 14px; }
    span { color: var(--m-muted); font-size: 12px; }
  }
  .mango-skill-center__search { margin: 10px 0; }

  .mango-skill-center__list-spin,
  :deep(.mango-skill-center__list-spin > .mango-panel-spin__content),
  .mango-skill-center__detail-spin,
  :deep(.mango-skill-center__detail-spin > .mango-panel-spin__content) {
    display: flex; height: 100%; min-height: 0; flex-direction: column;
  }
  .mango-skill-center__list { min-height: 0; overflow-y: auto; }

  .mango-skill-center__item {
    display: grid;
    width: 100%;
    min-width: 0;
    min-height: 78px;
    padding: 10px;
    grid-template-columns: 30px minmax(0, 1fr);
    align-items: start;
    gap: 9px;
    border: 1px solid transparent;
    border-radius: var(--m-radius-md);
    background: transparent;
    color: var(--m-text);
    cursor: pointer;
    text-align: left;
    transition: border-color 0.18s ease, background-color 0.18s ease;
  }
  .mango-skill-center__item + .mango-skill-center__item { margin-top: 4px; }
  .mango-skill-center__item:hover { background: var(--m-surface-soft); }
  .mango-skill-center__item--active { border-color: var(--m-primary-border); background: var(--m-primary-soft); }

  .mango-skill-center__item-icon {
    display: inline-flex; width: 30px; height: 30px; align-items: center; justify-content: center;
    border-radius: var(--m-radius-md); background: var(--m-surface-soft); color: var(--m-primary); font-size: 17px;
  }
  .mango-skill-center__item-content {
    display: flex; min-width: 0; flex-direction: column;
    strong, span { overflow: hidden; text-overflow: ellipsis; }
    strong { color: var(--m-text); font-size: 13px; line-height: 17px; white-space: nowrap; }
    span { display: -webkit-box; margin-top: 2px; color: var(--m-muted); font-size: 12px; line-height: 15px; -webkit-box-orient: vertical; -webkit-line-clamp: 2; }
    em { margin-top: 4px; color: var(--m-primary); font-size: 11px; font-style: normal; }
  }
  .mango-skill-center__list-empty,
  .mango-skill-center__detail-empty { flex: 1; min-height: 160px; }

  .mango-skill-center__detail { display: flex; padding: 0; flex-direction: column; }
  .mango-skill-center__hero {
    display: flex; padding: 18px 20px; align-items: flex-start; justify-content: space-between; gap: 16px;
    border-bottom: 1px solid var(--m-border); background: var(--m-surface);
  }
  .mango-skill-center__hero-main {
    min-width: 0;
    h2 { margin: 3px 0 0; color: var(--m-text); font-size: 18px; line-height: 24px; }
    p { max-width: 760px; margin: 6px 0 0; color: var(--m-text-2); font-size: 13px; line-height: 18px; }
  }
  .mango-skill-center__eyebrow { color: var(--m-primary); font-size: 12px; font-weight: 600; }

  .mango-skill-center__meta {
    display: grid; margin: 12px 20px 0; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--m-page-gap);
    div { min-width: 0; padding: 9px 10px; border: 1px solid var(--m-border); border-radius: var(--m-radius-md); background: var(--m-surface-soft); }
    span, strong { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    span { color: var(--m-muted); font-size: 11px; }
    strong { margin-top: 3px; color: var(--m-text); font-size: 13px; }
  }

  .mango-skill-center__catalog {
    display: flex; margin: 12px 20px 0; align-items: flex-start; gap: 10px;
    > span { flex: 0 0 auto; padding-top: 2px; color: var(--m-muted); font-size: 12px; }
    > div { display: flex; flex-wrap: wrap; gap: 5px; }
  }

  .mango-skill-center__markdown {
    min-height: 0; padding: 6px 20px 20px; margin-top: 8px; overflow-y: auto;
    color: var(--m-text-2); font-size: 12px; line-height: 1.7;
    :deep(h2), :deep(h3), :deep(h4) { margin: 20px 0 8px; color: var(--m-text); line-height: 1.4; }
    :deep(h2) { padding-bottom: 7px; border-bottom: 1px solid var(--m-border); font-size: 17px; }
    :deep(h3) { font-size: 15px; }
    :deep(h4) { font-size: 14px; }
    :deep(p) { margin: 7px 0; }
    :deep(ul), :deep(ol) { padding-left: 22px; margin: 7px 0; }
    :deep(code) { padding: 1px 4px; border-radius: 4px; background: var(--m-code-bg); color: var(--m-code-text); }
    :deep(pre) { padding: 12px; overflow-x: auto; border: 1px solid var(--m-code-border); border-radius: var(--m-radius-md); background: var(--m-code-bg); }
    :deep(pre code) { padding: 0; background: transparent; white-space: pre; }
    :deep(blockquote) { padding: 8px 10px; border-left: 3px solid var(--m-primary); margin: 8px 0; background: var(--m-primary-soft); color: var(--m-text-2); }
  }

</style>
