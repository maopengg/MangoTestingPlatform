import { readFile, readdir } from 'node:fs/promises'
import path from 'node:path'

const root = process.cwd()
const sourceRoot = path.join(root, 'src')
const requiredFoundation = [
  ['postcss.config.js', "require('./scripts/postcss-fluid-rem.cjs')"],
  ['src/styles/index.css', '--m-page-gap:'],
  ['src/styles/index.css', '--m-ui-scale:'],
  ['src/styles/index.css', '--m-card-padding:'],
  ['src/styles/index.css', '--m-overlay-viewport-gap:'],
  ['src/styles/index.css', '.mango-responsive-container'],
  ['src/styles/index.css', '@container (max-width: 1099px)'],
  ['src/layouts/MainLayout.vue', 'container-type: inline-size'],
  ['src/router/guard/flexMainHeight.ts', 'router.afterEach'],
  ['src/main.ts', 'applyDisplayDensity(DisplayDensity.AUTO)'],
  ['src/hooks/useDisplayDensity.ts', 'document.documentElement.clientWidth'],
  ['src/layouts/index.ts', "app.component('a-table', DensityTable)"],
  ['src/layouts/index.ts', "app.component('a-table-column', DensityTableColumn)"],
  ['src/layouts/index.ts', "app.component('a-modal', DensityModal)"],
  ['src/layouts/index.ts', "app.component('a-drawer', DensityDrawer)"],
  ['src/layouts/index.ts', "app.component('a-avatar', DensityAvatar)"],
  ['src/components/table/TableSearchPanel.vue', 'scaleDensityPixels(MIN_CELL_WIDTH)'],
]

async function walk(directory, pattern) {
  const entries = await readdir(directory, { withFileTypes: true })
  const files = []
  for (const entry of entries) {
    const target = path.join(directory, entry.name)
    if (entry.isDirectory()) files.push(...(await walk(target, pattern)))
    else if (pattern.test(entry.name)) files.push(target)
  }
  return files
}

function lineNumber(source, index) {
  return source.slice(0, index).split(/\r?\n/).length
}

const issues = []
for (const [relativePath, marker] of requiredFoundation) {
  const source = await readFile(path.join(root, relativePath), 'utf8')
  if (!source.includes(marker)) issues.push(`${relativePath}: 缺少全局响应式基础能力 ${marker}`)
}

const styleFiles = await walk(sourceRoot, /\.(vue|css|less|scss|sass)$/)
for (const file of styleFiles) {
  const source = await readFile(file, 'utf8')
  const relativePath = path.relative(root, file)
  for (const match of source.matchAll(/\bzoom\s*:\s*[^;]+/g)) {
    issues.push(`${relativePath}:${lineNumber(source, match.index)} 禁止使用 zoom 适配页面`)
  }
  for (const match of source.matchAll(/([^{}]+)\{[^{}]*transform\s*:\s*scale\([^)]*\)/g)) {
    const selector = match[1].trim()
    if (!/(?:page|workbench|container|layout|main)(?:\b|[-_])/i.test(selector)) continue
    issues.push(
      `${relativePath}:${lineNumber(source, match.index)} 禁止对页面布局使用 transform: scale()`
    )
  }
  for (const match of source.matchAll(
    /\bstyle\s*=\s*["'][^"']*\b(?:width|height|min-width|max-width)\s*:\s*\d+(?:\.\d+)?px/g
  )) {
    issues.push(
      `${relativePath}:${lineNumber(source, match.index)} 固定尺寸请写入样式块，由全局 rem 转换统一缩放`
    )
  }
  for (const match of source.matchAll(
    /:style\s*=\s*["'][^"']*\b(?:width|height|minWidth|maxWidth)\s*:\s*['"]\d+(?:\.\d+)?px['"]/g
  )) {
    issues.push(
      `${relativePath}:${lineNumber(source, match.index)} 内联 px 尺寸不会随显示密度缩放`
    )
  }
}

const sourceFiles = await walk(sourceRoot, /\.(vue|ts|tsx|js|jsx)$/)
for (const file of sourceFiles) {
  const source = await readFile(file, 'utf8')
  const relativePath = path.relative(root, file)
  if (relativePath !== 'src/layouts/index.ts') {
    for (const match of source.matchAll(
      /from\s+['"]@arco-design\/web-vue\/es\/(?:table|table\/table-column|modal|drawer|avatar)['"]/g
    )) {
      issues.push(
        `${relativePath}:${lineNumber(source, match.index)} 业务组件不得绕过全局密度适配直接渲染 Arco 原始布局组件`
      )
    }
  }
  for (const match of source.matchAll(
    /\bstyle\s*=\s*\{\{[^}]*\b(?:width|height|minWidth|maxWidth)\s*:\s*['"]\d+(?:\.\d+)?px['"]/g
  )) {
    issues.push(
      `${relativePath}:${lineNumber(source, match.index)} TSX 内联 px 尺寸不会随显示密度缩放`
    )
  }
}

console.log('Mango responsive layout audit')
console.log(`Scanned style files: ${styleFiles.length}`)
console.log(`Scanned source files: ${sourceFiles.length}`)
if (issues.length) {
  console.log(`Issues: ${issues.length}`)
  issues.forEach((issue) => console.log(`- ${issue}`))
  process.exitCode = 1
} else {
  console.log('Issues: 0')
}
