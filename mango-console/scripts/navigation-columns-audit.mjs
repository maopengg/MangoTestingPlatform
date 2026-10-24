import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const scriptDir = path.dirname(fileURLToPath(import.meta.url))
const viewsRoot = path.resolve(scriptDir, '../src/views')

function walk(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const target = path.join(directory, entry.name)
    if (entry.isDirectory()) return walk(target)
    return entry.isFile() && entry.name === 'index.vue' ? [target] : []
  })
}

const issues = []
let checkedPages = 0
let modulePages = 0

function columnTitles(source) {
  const matches = []
  const patterns = [
    /title:\s*['"]([^'"]+)['"]/g,
    /<a-table-column\b[^>]*\btitle=['"]([^'"]+)['"][^>]*>/g,
  ]
  for (const pattern of patterns) {
    for (const match of source.matchAll(pattern)) {
      matches.push({ title: match[1], index: match.index })
    }
  }
  return matches.sort((left, right) => left.index - right.index)
}

function validateOwnershipColumnOrder(relativePath, source, showsModules) {
  const titles = columnTitles(source)
  const projectIndexes = titles.flatMap((item, index) =>
    item.title === '项目/产品' ? [index] : []
  )
  for (const projectIndex of projectIndexes) {
    const ownership = showsModules ? ['项目/产品', '模块'] : ['项目/产品']
    const actualOwnership = titles
      .slice(projectIndex, projectIndex + ownership.length)
      .map((item) => item.title)
    const ownershipEnd = projectIndex + ownership.length - 1
    const nextColumn = titles[ownershipEnd + 1]
    const closesBeforeNextColumn =
      !nextColumn || source.slice(titles[ownershipEnd].index, nextColumn.index).includes(']')
    const validTail = closesBeforeNextColumn || nextColumn.title === '操作'
    if (actualOwnership.join('\0') !== ownership.join('\0') || !validTail) {
      const actual = titles
        .slice(projectIndex, projectIndex + ownership.length + 1)
        .map((item) => item.title)
      const expected = [...ownership, '操作（存在操作列时）']
      issues.push(
        `${relativePath}: 归属列顺序必须是“${expected.join(' → ')}”，当前为“${
          actual.join(' → ') || '无法识别'
        }”`
      )
    }
  }
}

for (const vuePath of walk(viewsRoot)) {
  const vueSource = fs.readFileSync(vuePath, 'utf8')
  const componentStart = vueSource.indexOf('<ProjectProductNavigationWorkbench')
  if (componentStart < 0) continue

  checkedPages += 1
  const componentEnd = vueSource.indexOf('>', componentStart)
  const componentTag = vueSource.slice(componentStart, componentEnd + 1)
  const configPath = path.join(path.dirname(vuePath), 'config.ts')
  const configSource = fs.existsSync(configPath) ? fs.readFileSync(configPath, 'utf8') : ''
  const combinedSource = `${vueSource}\n${configSource}`
  const relativePath = path.relative(path.resolve(scriptDir, '..'), vuePath)
  const usesExplorerLayout = /\bdata-navigation-layout=["']explorer["']/.test(componentTag)

  // 产品目录本身按项目分组，归属由分组标题承载，不在每一行重复项目/产品列。
  if (relativePath === 'src/views/config/product/components/ProductOverview.vue') {
    if (!/data-navigation-layout=["']project-groups["']/.test(componentTag) || !/group\.name/.test(vueSource)) {
      issues.push(`${relativePath}: 项目分组总览必须展示项目标题`)
    }
    continue
  }

  if (usesExplorerLayout) {
    if (!/currentProjectProductLabel/.test(vueSource)) {
      issues.push(`${relativePath}: 资源浏览器必须展示当前项目/产品范围`)
    }
    if (/\bshow-modules\b/.test(componentTag) && !/currentModuleLabel/.test(vueSource)) {
      issues.push(`${relativePath}: 资源浏览器必须展示当前模块范围`)
    }
    continue
  }

  if (!/title:\s*['"]项目\/产品['"]/.test(combinedSource)) {
    issues.push(`${relativePath}: 导航列表缺少“项目/产品”列`)
  }
  const usesProjectProductPath = /formatProjectProductPath\(record\.project_product\)/.test(
    vueSource
  )
  if (!usesProjectProductPath) {
    issues.push(
      `${relativePath}: 项目/产品必须使用 formatProjectProductPath(record.project_product) 展示`
    )
  }

  const showsModules = /\bshow-modules\b/.test(componentTag)
  if (showsModules) {
    modulePages += 1
    if (!/title:\s*['"]模块['"]/.test(combinedSource)) {
      issues.push(`${relativePath}: 模块导航列表缺少“模块”列`)
    }
    if (!/formatModulePath\(record\.module\)/.test(vueSource)) {
      issues.push(`${relativePath}: 模块列必须使用 formatModulePath(record.module) 展示`)
    }
  }
  validateOwnershipColumnOrder(relativePath, configSource || vueSource, showsModules)
}

console.log('Navigation columns audit')
console.log(`Checked pages: ${checkedPages}`)
console.log(`Module navigation pages: ${modulePages}`)
if (issues.length) {
  console.log(`Issues: ${issues.length}`)
  issues.forEach((issue) => console.log(`- ${issue}`))
  process.exitCode = 1
} else {
  console.log('Issues: 0')
}
