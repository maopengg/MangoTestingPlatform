import type { SkillRecord, SkillIntroduction } from './types'

export function parseIntroductions(documents: Record<string, string>): Record<string, SkillIntroduction> {
    const content = Object.values(documents)[0]
    if (!content) return {}
    try {
      const payload: unknown = JSON.parse(content)
      if (!payload || typeof payload !== 'object' || Array.isArray(payload)) return {}
      const result: Record<string, SkillIntroduction> = {}
      for (const [key, value] of Object.entries(payload)) {
        if (!value || typeof value !== 'object' || Array.isArray(value)) continue
        const item = value as Record<string, unknown>
        result[key] = {
          title: typeof item.title === 'string' ? item.title : undefined,
          description: typeof item.description === 'string' ? item.description : undefined,
          category: typeof item.category === 'string' ? item.category : undefined,
        }
      }
      return result
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

export function createSkillRecord(
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

export function renderMarkdown(value: string) {
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

