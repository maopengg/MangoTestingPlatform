
import { reportLoadError } from '@/utils/load-error'
import { ref } from 'vue'
import { getUserModuleName } from '@/api/system/module'
import { getDataFactoryEntity, getDataFactoryField } from '@/api/data-factory'
import { formatModulePath } from '@/utils/business-format'
import { optionId } from '../form'
import type { DependencyOption, EntityRecord, FieldRow, FieldRecord, Id } from '../types'
interface ModuleOption {
  id?: Id
  key?: Id
  name?: string
  title?: string
  full_path?: string
}
export function useEntityDependencies() {
  const options = ref<DependencyOption[]>([]),
    loading = ref(false),
    error = ref(false)
  let version = 0,
    entity: EntityRecord | null = null
  function clear() {
    ++version
    entity = null
    options.value = []
    loading.value = false
    error.value = false
  }
  function find(value: string, list = options.value): DependencyOption | null {
    for (const item of list) {
      if (item.value === value) return item
      const child = find(value, item.children || [])
      if (child) return child
    }
    return null
  }
  async function children(option: DependencyOption, current: number): Promise<DependencyOption[]> {
    const product = optionId(entity?.project_product),
      id = entity?.id
    if (product === null || current !== version) return []
    if (option.level === 'module') {
      const response = await getDataFactoryEntity({
        project_product: product,
        module: option.raw_id,
        page: 1,
        pageSize: 9999,
      })
      if (current !== version) return []
      return (response.data || [])
        .filter((item: EntityRecord) => item.id !== id)
        .map((item: EntityRecord) => ({
          label: `${item.name || item.id}${item.table_name ? ` / ${item.table_name}` : ''}`,
          value: `entity:${item.id}`,
          raw_id: item.id,
          level: 'entity',
          isLeaf: false,
        }))
    }
    if (option.level === 'entity') {
      const response = await getDataFactoryField({ entity: option.raw_id })
      if (current !== version) return []
      return (response.data || []).map((field: FieldRecord) => ({
        label: `${field.label || field.name} / ${field.name}`,
        value: `field:${field.name}`,
        raw_id: field.name,
        level: 'field',
        isLeaf: true,
      }))
    }
    return []
  }
  async function preload(id: Id, current: number) {
    if (!entity || current !== version) return
    const response = await getDataFactoryEntity({
      id,
      project_product: optionId(entity.project_product),
      page: 1,
      pageSize: 1,
    })
    if (current !== version) return
    const dependency: EntityRecord | undefined = (response.data || [])[0],
      moduleId = optionId(dependency?.module)
    const module = moduleId === null ? null : find(`module:${moduleId}`)
    if (!module) return
    if (!module.children?.length) module.children = await children(module, current)
    if (current !== version) return
    const item = module.children?.find((item) => String(item.raw_id) === String(id))
    if (item && !item.children?.length) item.children = await children(item, current)
  }
  async function load(record: EntityRecord, rows: FieldRow[]) {
    clear()
    entity = { ...record }
    const current = version,
      product = optionId(record.project_product)
    if (product === null) return
    loading.value = true
    try {
      const response = await getUserModuleName(product)
      if (current !== version) return
      options.value = (response.data || []).map((module: ModuleOption) => ({
        label: formatModulePath({ ...module, name: module.name || module.title || String(module.id ?? module.key ?? '') }),
        value: `module:${module.key ?? module.id}`,
        raw_id: module.key ?? module.id ?? '',
        level: 'module',
        isLeaf: false,
      }))
      const ids = Array.from(
        new Set(
          rows
            .map((row) => row.generator_config.dependency_entity_id)
            .filter((id): id is Id => id !== undefined && id !== null && id !== '')
        )
      )
      for (const id of ids) {
        await preload(id, current)
        if (current !== version) return
      }
      options.value = [...options.value]
    } catch (loadFailure0) {
      if (current === version) (reportLoadError(loadFailure0, "加载失败，请重试", false), error.value = true)
    } finally {
      if (current === version) loading.value = false
    }
  }
  async function loadMore(option: DependencyOption, done: (children?: DependencyOption[]) => void) {
    const current = version
    try {
      const result = await children(option, current)
      if (current !== version) {
        done([])
        return
      }
      const item = find(option.value)
      if (item) item.children = result
      options.value = [...options.value]
      done(result)
    } catch (loadFailure1) {
      if (current === version) (reportLoadError(loadFailure1, "加载失败，请重试", false), error.value = true)
      done([])
    }
  }
  function path(entityId: Id | null | undefined, field = 'id'): string[] {
    if (entityId === null || entityId === undefined) return []
    const visit = (list: DependencyOption[], parents: string[]): string[] => {
      for (const item of list) {
        const route = [...parents, item.value]
        if (item.value === `entity:${entityId}`) {
          const child = item.children?.find((child) => child.value === `field:${field}`)
          return child ? [...route, child.value] : route
        }
        const child = visit(item.children || [], route)
        if (child.length) return child
      }
      return []
    }
    return visit(options.value, [])
  }
  return { options, loading, error, clear, load, loadMore, path }
}
