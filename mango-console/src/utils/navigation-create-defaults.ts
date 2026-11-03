import { nextTick } from 'vue'

export type NavigationCreateSelection = {
  projectProduct: string | number | null
  module: string | number | null
}

export type NavigationCreateSource = {
  getCreateDefaults: () => NavigationCreateSelection
}

type Field = { key: string; value: any }
const pending = new WeakMap<object, symbol>()

function hasValue(value: any) {
  return value !== null && value !== undefined && value !== '' && (!Array.isArray(value) || value.length > 0)
}

function leaf(value: any) {
  return Array.isArray(value) ? value[value.length - 1] : value
}

async function prefill(
  source: NavigationCreateSource | null | undefined,
  target: object,
  read: (key: string) => any,
  write: (key: string, value: any) => void,
  isCreate: () => boolean
) {
  const version = Symbol()
  pending.set(target, version)
  if (!source || !isCreate()) return
  const selection = source.getCreateDefaults()
  if (!hasValue(selection.projectProduct)) return
  if (!hasValue(read('project_product'))) write('project_product', selection.projectProduct)
  // 产品选择器联动会清空模块，等这一轮更新完成后再填；不覆盖用户输入或迟到的编辑数据。
  await nextTick()
  if (pending.get(target) !== version || !isCreate()) return
  if (String(leaf(read('project_product'))) !== String(selection.projectProduct)) return
  if (!hasValue(read('module')) && hasValue(selection.module)) write('module', selection.module)
}

export function prefillNavigationFormItems(
  source: NavigationCreateSource | null | undefined,
  items: Field[],
  isCreate: () => boolean
) {
  return prefill(source, items, (key) => items.find((item) => item.key === key)?.value,
    (key, value) => { const item = items.find((field) => field.key === key); if (item) item.value = value }, isCreate)
}

export function prefillNavigationModel(
  source: NavigationCreateSource | null | undefined,
  model: Record<string, any>,
  isCreate: () => boolean = () => !model.id
) {
  return prefill(source, model, (key) => model[key],
    (key, value) => { if (Object.prototype.hasOwnProperty.call(model, key)) model[key] = value }, isCreate)
}
