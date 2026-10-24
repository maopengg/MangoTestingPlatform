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
  import { computed, nextTick, ref, watch } from 'vue'
  import { IconBook, IconDownload, IconRefresh } from '@arco-design/web-vue/es/icon'
  import { Message } from '@arco-design/web-vue'
  import { zipSync } from 'fflate'

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

  interface SkillRecord {
    key: string
    name: string
    description: string
    category?: string
    original_description?: string
    has_custom_introduction?: boolean
    sections?: Array<{ title: string; summary: string }>
    content?: string
  }

  interface SkillIntroduction {
    title?: string
    description?: string
    category?: string
  }

  const props = defineProps({ visible: { type: Boolean, default: false } })
  const emit = defineEmits(['update:visible'])
  const loading = ref(false)
  const detailLoading = ref(false)
  const skills = ref<SkillRecord[]>([])
  const selectedKey = ref('')
  const detail = ref<SkillRecord | null>(null)
  const keyword = ref('')
  const downloadingKey = ref('')

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
    emit('update:visible', false)
  }

  async function loadSkills() {
    loading.value = true
    try {
      const introductions = parseIntroductions()
      skills.value = Object.entries(skillDocuments)
        .map(([path, content]) => createSkillRecord(path, content, introductions))
        .filter((item): item is SkillRecord => Boolean(item))
        .sort((previous, next) => previous.name.localeCompare(next.name, 'zh-CN'))
      const nextKey = skills.value.some((item) => item.key === selectedKey.value)
        ? selectedKey.value
        : skills.value[0]?.key || ''
      if (!nextKey) {
        selectedKey.value = ''
        detail.value = null
        return
      }
      selectSkill(nextKey)
    } catch (error) {
      skills.value = []
      selectedKey.value = ''
      detail.value = null
      console.log(error)
    } finally {
      await nextTick()
      loading.value = false
    }
  }

  function selectSkill(key: string) {
    selectedKey.value = key
    detailLoading.value = true
    detail.value = skills.value.find((item) => item.key === key) || null
    nextTick(() => {
      detailLoading.value = false
    })
  }

  async function downloadSkill(record: SkillRecord) {
    if (downloadingKey.value) return
    downloadingKey.value = record.key
    try {
      const skillRoot = `/skill/${record.key}/`
      const assets = Object.entries(skillAssetUrls).filter(([path]) => path.includes(skillRoot))
      if (!assets.length) throw new Error('Skill 目录为空')

      const files = await Promise.all(
        assets.map(async ([path, assetUrl]) => {
          const relativePath = path.slice(path.indexOf(skillRoot) + skillRoot.length)
          const response = await fetch(assetUrl)
          if (!response.ok) throw new Error(`读取 ${relativePath} 失败`)
          return [relativePath, new Uint8Array(await response.arrayBuffer())] as const
        })
      )
      const archive = zipSync(Object.fromEntries(files), { level: 6 })
      const url = URL.createObjectURL(new Blob([archive], { type: 'application/zip' }))
      const link = document.createElement('a')
      link.href = url
      link.download = `${record.key}.zip`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.setTimeout(() => URL.revokeObjectURL(url), 1000)
      Message.success(`已打包 ${files.length} 个文件，开始下载`)
    } catch (error) {
      Message.error(error instanceof Error ? error.message : 'Skill 打包失败')
    } finally {
      downloadingKey.value = ''
    }
  }

  function parseIntroductions(): Record<string, SkillIntroduction> {
    const content = Object.values(introductionDocuments)[0]
    if (!content) return {}
    try {
      const payload = JSON.parse(content)
      return payload && typeof payload === 'object' ? payload : {}
    } catch {
      return {}
    }
  }

  function parseFrontmatter(content: string) {
    if (!content.startsWith('---')) return {} as Record<string, string>
    const endIndex = content.indexOf('\n---', 3)
    if (endIndex < 0) return {} as Record<string, string>
    return content
      .slice(3, endIndex)
      .trim()
      .split(/\r?\n/)
      .reduce<Record<string, string>>((result, line) => {
        const separator = line.indexOf(':')
        if (separator > 0) result[line.slice(0, separator).trim()] = line.slice(separator + 1).trim()
        return result
      }, {})
  }

  function extractSections(content: string) {
    const frontmatterEnd = content.startsWith('---') ? content.indexOf('\n---', 3) : -1
    const body = frontmatterEnd >= 0 ? content.slice(frontmatterEnd + 4) : content
    return body
      .split(/\r?\n/)
      .filter((line) => line.startsWith('## '))
      .slice(0, 12)
      .map((line) => ({ title: line.slice(3).trim(), summary: '' }))
  }

  function createSkillRecord(
    path: string,
    content: string,
    introductions: Record<string, SkillIntroduction>
  ): SkillRecord | null {
    const key = path.match(/\/skill\/([^/]+)\/SKILL\.md$/)?.[1]
    if (!key) return null
    const meta = parseFrontmatter(content)
    const introduction = introductions[key]
    const originalDescription = meta.description || content.trim()
    return {
      key,
      name: introduction?.title || meta.name || key,
      description: introduction?.description || originalDescription,
      category: introduction?.category || '',
      original_description: originalDescription,
      has_custom_introduction: Boolean(introduction),
      sections: extractSections(content),
      content,
    }
  }

  function escapeHtml(value: string) {
    return String(value || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;')
  }

  function renderInlineMarkdown(value: string) {
    return escapeHtml(value).replace(/`([^`]+)`/g, '<code>$1</code>').replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  }

  function renderMarkdown(value: string) {
    const text = String(value || '')
    const frontmatterEnd = text.startsWith('---') ? text.indexOf('\n---', 3) : -1
    const lines = (frontmatterEnd >= 0 ? text.slice(frontmatterEnd + 4) : text).split(/\r?\n/)
    const html: string[] = []
    let inCode = false
    let codeLines: string[] = []
    let listType = ''
    const closeList = () => {
      if (!listType) return
      html.push(`</${listType}>`)
      listType = ''
    }

    lines.forEach((line) => {
      if (line.trim().startsWith('```')) {
        if (inCode) {
          html.push(`<pre><code>${escapeHtml(codeLines.join('\n'))}</code></pre>`)
          codeLines = []
          inCode = false
        } else {
          closeList()
          inCode = true
        }
        return
      }
      if (inCode) {
        codeLines.push(line)
        return
      }
      const heading = line.match(/^(#{1,4})\s+(.+)$/)
      if (heading) {
        closeList()
        const level = Math.min(heading[1].length + 1, 4)
        html.push(`<h${level}>${renderInlineMarkdown(heading[2])}</h${level}>`)
        return
      }
      const ordered = line.match(/^\s*\d+\.\s+(.+)$/)
      const unordered = line.match(/^\s*[-*]\s+(.+)$/)
      if (ordered || unordered) {
        const type = ordered ? 'ol' : 'ul'
        if (listType !== type) {
          closeList()
          html.push(`<${type}>`)
          listType = type
        }
        html.push(`<li>${renderInlineMarkdown((ordered || unordered)?.[1] || '')}</li>`)
        return
      }
      closeList()
      if (!line.trim()) return
      if (line.startsWith('> ')) html.push(`<blockquote>${renderInlineMarkdown(line.slice(2))}</blockquote>`)
      else if (/^---+$/.test(line.trim())) html.push('<hr />')
      else html.push(`<p>${renderInlineMarkdown(line)}</p>`)
    })
    closeList()
    if (inCode) html.push(`<pre><code>${escapeHtml(codeLines.join('\n'))}</code></pre>`)
    return html.join('')
  }

  watch(() => props.visible, (value) => {
    if (value) loadSkills()
  })
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
