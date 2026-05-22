import { readdir, readFile } from 'node:fs/promises'
import path from 'node:path'

const root = process.cwd()
const scanRoots = ['src/views', 'src/components', 'src/layouts'].map((item) => path.join(root, item))
const fileExts = new Set(['.vue', '.ts', '.css', '.less'])
const colorPattern = /#[0-9a-fA-F]{3,8}(?![0-9a-fA-Fa-zA-Z])|rgba?\([^)]+\)|rgb\([^)]+\)|var\(--color-[^)]+\)|var\(--primary-[^)]+\)|rgb\(var\(--[^)]+\)\)/g

const allowedLineHints = [
  'syntax-',
  'token(',
  'pattern-color',
  '业务枚举',
  'levelColor',
  'statusColor',
  'tagColor',
]

const pycharmCodeThemeValues = [
  '#2f3542',
  '#2b2b2b',
  '#a9b7c6',
  '#3c3f41',
  '#313335',
  '#bbbbbb',
  '#d4d4d4',
  '#808080',
  '#ffc66d',
  '#6a8759',
  '#cc7832',
  '#6897bb',
  'rgba(255, 255, 255, 0.04)',
]

async function walk(dir) {
  const entries = await readdir(dir, { withFileTypes: true })
  const files = []
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name)
    if (entry.isDirectory()) {
      files.push(...(await walk(fullPath)))
    } else if (fileExts.has(path.extname(entry.name))) {
      files.push(fullPath)
    }
  }
  return files
}

function isAllowed(file, line) {
  const normalized = file.replace(root + path.sep, '')
  const isHelpThemeLab = /src[\\/]views[\\/]help[\\/]test\.vue$/.test(normalized)
  const isCodeThemeLine =
    isHelpThemeLab &&
    (/editor-|mini-json|syntax-/.test(line) ||
      line.includes('"#') ||
      line.includes('PyCharm') ||
      line.includes('color-mix(in srgb, var(--m-') ||
      pycharmCodeThemeValues.some((value) => line.includes(value)))
  return isCodeThemeLine || allowedLineHints.some((hint) => line.includes(hint))
}

const files = (await Promise.all(scanRoots.map(walk))).flat()
const findings = []
const exceptions = []

for (const file of files) {
  const content = await readFile(file, 'utf8')
  const lines = content.split(/\r?\n/)
  lines.forEach((line, index) => {
    const matches = line.match(colorPattern)
    if (!matches) return
    const item = {
      file: path.relative(root, file),
      line: index + 1,
      matches: [...new Set(matches)],
      text: line.trim(),
    }
    if (isAllowed(file, line)) {
      exceptions.push(item)
    } else {
      findings.push(item)
    }
  })
}

function printGroup(title, items, limit = 80) {
  console.log(`\n${title}: ${items.length}`)
  items.slice(0, limit).forEach((item) => {
    console.log(`- ${item.file}:${item.line} ${item.matches.join(', ')}`)
    console.log(`  ${item.text}`)
  })
  if (items.length > limit) {
    console.log(`  ... and ${items.length - limit} more`)
  }
}

console.log('Mango theme audit')
console.log(`Scanned files: ${files.length}`)
printGroup('Needs review', findings)
printGroup('Allowed exceptions', exceptions, 40)

if (findings.length > 0) {
  console.log('\nTip: prefer --m-* tokens for custom styles. Keep exceptions intentional and documented.')
  console.log('Set THEME_AUDIT_STRICT=1 when you want this audit to fail on findings.')
  if (process.env.THEME_AUDIT_STRICT === '1') {
    process.exitCode = 1
  }
}
