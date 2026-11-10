import { computed, ref } from 'vue'
import { getUserProjectProductName } from '@/api/system/project'
import { getUserModuleTree } from '@/api/system/module'

export interface RelationListOption {
  label: string
  value: string | number
  path: string
  legacy?: boolean
}
interface RelationNode {
  label: string
  value: string | number
  level?: number
  children: RelationNode[]
}
function nodes(value: unknown): RelationNode[] {
  if (!Array.isArray(value)) throw Error('关系选项格式错误')
  return value.map((item: unknown) => {
    if (!item || typeof item !== 'object' || Array.isArray(item))
      throw Error('关系选项节点格式错误')
    const node = item as Record<string, unknown>
    const id = node.key ?? node.value
    if (typeof id !== 'number' && typeof id !== 'string') throw Error('关系选项缺少 ID')
    const label = node.title ?? node.label ?? String(id)
    if (typeof label !== 'string') throw Error('关系选项名称格式错误')
    return {
      value: id,
      label,
      level: node.level === undefined || node.level === null ? undefined : Number(node.level),
      children: node.children === undefined || node.children === null ? [] : nodes(node.children),
    }
  })
}
function leaves(items: RelationNode[], parent: string[] = []): RelationListOption[] {
  return items.flatMap((item) => {
    const labels = [...parent, item.label]
    return item.children.length
      ? leaves(item.children, labels)
      : [{ value: item.value, label: labels.join('/'), path: labels.join('/') }]
  })
}
function thirdLevel(items: RelationNode[], depth = 1): RelationNode[] {
  return items.flatMap((item) => {
    const level = item.level ?? depth
    if (level > 3 || level < 1 || !Number.isInteger(level)) return []
    const children = level < 3 ? thirdLevel(item.children, depth + 1) : []
    return level < 3 && !children.length ? [] : [{ ...item, children }]
  })
}

// Only successful current-scope reads are reusable in this grid-owned cache.
export function useFunctionalGridOptions(options: { current: () => boolean }) {
  const productOptions = ref<RelationListOption[]>([])
  const moduleOptions = new Map<string, RelationListOption[]>()
  const failures = ref<string[]>([]),
    pendingKeys = ref<string[]>([])
  const requiredKeys = ref(new Set<string>())
  const loading = computed(() => pendingKeys.value.some((key) => requiredKeys.value.has(key)))
  const error = computed(() => failures.value.some((key) => requiredKeys.value.has(key)))
  let generation = 0,
    productLoaded = false
  let productRead: Promise<void> | null = null
  const moduleReads = new Map<string, Promise<void>>()
  const current = (version: number) => options.current() && generation === version
  function mark(key: string, failed: boolean) {
    failures.value = [
      ...new Set([...failures.value.filter((value) => value !== key), ...(failed ? [key] : [])]),
    ]
  }
  function track(key: string, run: () => Promise<void>): Promise<void> {
    const version = generation
    pendingKeys.value = [...pendingKeys.value, key]
    return Promise.resolve()
      .then(async () => {
        if (!current(version)) return
        await run()
        if (current(version)) mark(key, false)
      })
      .catch(() => {
        if (current(version)) mark(key, true)
      })
      .finally(() => {
        if (current(version)) pendingKeys.value = pendingKeys.value.filter((value) => value !== key)
      })
  }
  function products(): Promise<void> {
    if (productLoaded) return Promise.resolve()
    if (productRead) return productRead
    const version = generation
    const task = track('products', async () => {
      const response = await getUserProjectProductName()
      if (!current(version)) return
      productOptions.value = leaves(nodes(response.data))
      productLoaded = true
    })
    productRead = task
    void task.finally(() => {
      if (productRead === task) productRead = null
    })
    return task
  }
  function modules(id: string): Promise<void> {
    if (moduleOptions.has(id)) return Promise.resolve()
    const running = moduleReads.get(id)
    if (running) return running
    const version = generation
    const task = track(`module:${id}`, async () => {
      const response = await getUserModuleTree(id)
      if (!current(version)) return
      moduleOptions.set(id, leaves(thirdLevel(nodes(response.data))))
    })
    moduleReads.set(id, task)
    void task.finally(() => {
      if (moduleReads.get(id) === task) moduleReads.delete(id)
    })
    return task
  }
  async function prepare(ids: Array<string | number>) {
    if (!options.current()) return
    const required = [...new Set(ids.map(String))]
    requiredKeys.value = new Set(['products', ...required.map((id) => `module:${id}`)])
    await Promise.all([products(), ...required.map(modules)])
  }
  function reset() {
    ++generation
    productLoaded = false
    productRead = null
    productOptions.value = []
    moduleOptions.clear()
    moduleReads.clear()
    pendingKeys.value = []
    requiredKeys.value = new Set()
    failures.value = []
  }
  return { productOptions, moduleOptions, loading, error, prepare, reset }
}
