import { readFileSync, readdirSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { parse } from '@vue/compiler-sfc'
import { baseParse } from '@vue/compiler-dom'

function collectFiles(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const target = path.join(directory, entry.name)
    return entry.isDirectory() ? collectFiles(target) : target.endsWith('.vue') ? [target] : []
  })
}

function contentRoots(node) {
  return (node.children || []).filter((child) => child.type === 1).flatMap((child) => {
    if (child.tag !== 'template') return [child]
    const slot = child.props.find((prop) => prop.type === 7 && prop.name === 'slot')
    return slot && slot.arg?.content !== 'default' ? [] : contentRoots(child)
  })
}

export function inspectDrawerSpacing(source, filename = '') {
  const { descriptor, errors } = parse(source, { filename })
  if (errors.length) throw new Error(`Unable to parse ${filename}`)
  const issues = []
  let drawers = 0
  let sidePanels = 0
  if (!descriptor.template) return { issues, drawers, sidePanels }
  const styles = descriptor.styles.map((style) => style.content).join('\n')
  function visit(node) {
    if (node.type === 1 && node.tag === 'a-drawer') drawers++
    if (node.type === 1 && node.tag === 'BaseSidePanel') {
      sidePanels++
      const mode = node.props.find((prop) => prop.type === 6 && prop.name === 'mode')?.value?.content
      if (mode !== 'page') {
        for (const root of contentRoots(node)) {
          const names = root.props.find((prop) => prop.type === 6 && prop.name === 'class')?.value?.content
          for (const name of names?.split(/\s+/) || []) {
            const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
            for (const block of styles.matchAll(new RegExp(`\\.${escaped}\\s*\\{([^}]+)`, 'g'))) {
              for (const padding of block[1].matchAll(/(?:^|;)\s*(padding(?:-\w+)?)\s*:\s*([^;]+)/g)) {
                if (!/^0(?:\s+0){0,3}(?:\s*!important)?$/.test(padding[2].trim())) {
                  issues.push(`${filename}: ${name} 重复设置 ${padding[1]}: ${padding[2].trim()}`)
                }
              }
            }
          }
        }
      }
    }
    for (const child of node.children || []) visit(child)
  }
  visit(baseParse(descriptor.template.content))
  return { issues, drawers, sidePanels }
}

export function auditDrawerSpacing(root = process.cwd()) {
  const files = collectFiles(path.join(root, 'src'))
  const totals = { scanned: files.length, drawers: 0, sidePanels: 0, issues: [] }
  for (const file of files) {
    const filename = path.relative(root, file).split(path.sep).join('/')
    const result = inspectDrawerSpacing(readFileSync(file, 'utf8'), filename)
    totals.drawers += result.drawers
    totals.sidePanels += result.sidePanels
    totals.issues.push(...result.issues)
  }
  return totals
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const result = auditDrawerSpacing()
  console.log(`Mango drawer spacing audit\nScanned Vue files: ${result.scanned}`)
  console.log(`Raw drawer declarations: ${result.drawers}\nSide panel declarations: ${result.sidePanels}`)
  console.log(`Issues: ${result.issues.length}`)
  result.issues.forEach((issue) => console.log(`- ${issue}`))
  if (result.issues.length) process.exitCode = 1
}
