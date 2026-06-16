import { readdir, readFile } from 'node:fs/promises'
import path from 'node:path'

const root = process.cwd()
const scanRoot = path.join(root, 'src')
const vueExt = '.vue'

const verticalOnlyAllowlist = new Map([
  [
    'src/views/index/components/PendingTasks.vue',
    '首页待执行任务卡片是固定高度嵌入区，只需要内部纵向滚动',
  ],
])

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

const files = await walk(scanRoot)
const findings = []
const exceptions = []

for (const file of files) {
  const content = await readFile(file, 'utf8')
  const relative = path.relative(root, file)
  const tablePattern = /<a-table(?![\w-])[\s\S]*?>/g
  let match
  while ((match = tablePattern.exec(content))) {
    const tag = match[0]
    const line = lineNumber(content, match.index)
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

if (findings.length > 0) {
  console.log('\nTip: regular list/workbench tables must set scroll.x. Fixed-height embedded tables may be added to the allowlist with a reason.')
  process.exitCode = 1
}
