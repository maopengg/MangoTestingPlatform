import { readdir, readFile } from 'node:fs/promises'
import path from 'node:path'

const root = process.cwd()
const scanRoot = path.join(root, 'src')
const vueExt = '.vue'

const verticalOnlyAllowlist = new Map([])

async function walk(dir) {
  const entries = await readdir(dir, { withFileTypes: true })
  const files = []
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name)
    if (entry.isDirectory()) {
      files.push(...(await walk(fullPath)))
    } else if (path.extname(entry.name) === vueExt) {
      files.push(fullPath)
    }
  }
  return files
}

function lineNumber(content, index) {
  return content.slice(0, index).split(/\r?\n/).length
}

function compactTag(tag) {
  return tag.replace(/\s+/g, ' ').trim()
}

function scrollValue(tag) {
  const match = tag.match(/(?:^|\s)(?::scroll|scroll)\s*=\s*(?:"([^"]*)"|'([^']*)')/)
  return match?.[1] || match?.[2] || ''
}

function hasScrollX(tag) {
  const value = scrollValue(tag)
  return /\bx\s*:/.test(value)
}

function hasScrollY(tag) {
  const value = scrollValue(tag)
  return /\by\s*:/.test(value)
}

function overridesGlobalScrollbar(tag) {
  return /(?:^|\s)(?::scrollbar|scrollbar)(?:\s*=|\s|>)/.test(tag)
}

const files = await walk(scanRoot)
const findings = []
const exceptions = []
const overriddenGlobalScrollbars = []
const hiddenPersistentScrollbars = []
const uncontainedStickyTables = []
const incompleteNativeScrollTables = []
const unboundedWorkbenchTables = []

for (const file of files) {
  const content = await readFile(file, 'utf8')
  const relative = path.relative(root, file)
  const disablesPersistentScrollbar = /<TableBody\b[\s\S]*?:sticky-horizontal-scroll\s*=\s*["']false["'][\s\S]*?>/.test(
    content
  )
  const hasArcoTable = /<a-table(?![\w-])/.test(content)
  const hasStickyHorizontalTable = /<StickyHorizontalTable\b/.test(content)
  const hasNativeScrollTable = /mango-native-scroll-table/.test(content)
  const hasProjectNavigationWorkbench = /<ProjectProductNavigationWorkbench\b/.test(content)
  const hasContainedBody = /<ProjectProductNavigationWorkbench\b[\s\S]*?\bcontained-body\b[\s\S]*?>/.test(
    content
  )
  const primaryWorkbenchTableIndexes = new Set()
  let workbenchSearchIndex = 0
  while (workbenchSearchIndex < content.length) {
    const workbenchStart = content.indexOf(
      '<ProjectProductNavigationWorkbench',
      workbenchSearchIndex
    )
    if (workbenchStart < 0) break
    const workbenchEnd = content.indexOf('</ProjectProductNavigationWorkbench>', workbenchStart)
    if (workbenchEnd < 0) break
    const firstTableOffset = content
      .slice(workbenchStart, workbenchEnd)
      .search(/<a-table(?![\w-])/)
    if (firstTableOffset >= 0) {
      primaryWorkbenchTableIndexes.add(workbenchStart + firstTableOffset)
    }
    workbenchSearchIndex = workbenchEnd + 1
  }

  if (
    disablesPersistentScrollbar &&
    hasArcoTable &&
    !hasStickyHorizontalTable &&
    !hasProjectNavigationWorkbench &&
    !hasNativeScrollTable
  ) {
    const index = content.search(/:sticky-horizontal-scroll\s*=\s*["']false["']/)
    hiddenPersistentScrollbars.push({
      file: relative,
      line: lineNumber(content, index),
      tag: 'TableBody disables the persistent horizontal scrollbar without StickyHorizontalTable.',
    })
  }

  if (hasProjectNavigationWorkbench && hasStickyHorizontalTable && !hasContainedBody) {
    const index = content.search(/<ProjectProductNavigationWorkbench\b/)
    uncontainedStickyTables.push({
      file: relative,
      line: lineNumber(content, index),
      tag: 'ProjectProductNavigationWorkbench with StickyHorizontalTable must enable contained-body.',
    })
  }

  const tablePattern = /<a-table(?![\w-])[\s\S]*?>/g
  let match
  while ((match = tablePattern.exec(content))) {
    const tag = match[0]
    const line = lineNumber(content, match.index)
    const insideStickyTable =
      content.lastIndexOf('<StickyHorizontalTable', match.index) >
      content.lastIndexOf('</StickyHorizontalTable>', match.index)
    const usesNativeScroll = /mango-native-scroll-table/.test(tag)

    if (
      primaryWorkbenchTableIndexes.has(match.index) &&
      // 项目产品总览的多张分组表共用外层纵向滚动，各表仅承接横向滚动。
      !(relative === 'src/views/config/product/components/ProductOverview.vue' &&
        /data-navigation-layout="project-groups"/.test(content) && hasScrollX(tag)) &&
      (
        !hasContainedBody ||
        (!usesNativeScroll && !insideStickyTable) ||
        !hasScrollX(tag) ||
        !hasScrollY(tag)
      )
    ) {
      unboundedWorkbenchTables.push({
        file: relative,
        line,
        tag: compactTag(tag),
      })
    }

    if ((usesNativeScroll || insideStickyTable) && (!hasScrollX(tag) || !hasScrollY(tag))) {
      incompleteNativeScrollTables.push({
        file: relative,
        line,
        tag: compactTag(tag),
      })
    }
    if (overridesGlobalScrollbar(tag)) {
      overriddenGlobalScrollbars.push({ file: relative, line, tag: compactTag(tag) })
    }
    if (hasScrollX(tag)) continue

    const allowReason = verticalOnlyAllowlist.get(relative)
    const item = {
      file: relative,
      line,
      tag: compactTag(tag),
      reason: allowReason,
    }
    if (allowReason) {
      exceptions.push(item)
    } else {
      findings.push(item)
    }
  }
}

function printGroup(title, items) {
  console.log(`\n${title}: ${items.length}`)
  items.forEach((item) => {
    console.log(`- ${item.file}:${item.line}`)
    if (item.reason) console.log(`  ${item.reason}`)
    console.log(`  ${item.tag}`)
  })
}

console.log('Mango table scroll audit')
console.log(`Scanned Vue files: ${files.length}`)
printGroup('Missing scroll.x', findings)
printGroup('Allowed exceptions', exceptions)
printGroup('Overridden global scrollbar', overriddenGlobalScrollbars)
printGroup('Hidden persistent horizontal scrollbar', hiddenPersistentScrollbars)
printGroup('Uncontained sticky table workbench', uncontainedStickyTables)
printGroup('Incomplete native bidirectional table scroll', incompleteNativeScrollTables)
printGroup('Unbounded project workbench table', unboundedWorkbenchTables)

if (
  findings.length > 0 ||
  overriddenGlobalScrollbars.length > 0 ||
  hiddenPersistentScrollbars.length > 0 ||
  uncontainedStickyTables.length > 0 ||
  incompleteNativeScrollTables.length > 0 ||
  unboundedWorkbenchTables.length > 0
) {
  console.log(
    '\nTip: use the Arco table native scrollbars. A bounded table scroll area must configure both scroll.x and scroll.y so the horizontal and vertical thumbs remain visible on the table edges.'
  )
  process.exitCode = 1
}
