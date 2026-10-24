export interface ProductGroup {
  id: string
  name: string
  products: any[]
  total: number
}

/** 逐页读取权限范围内的完整数据；不把当前页误当成产品总览。 */
export async function loadAllProducts(
  request: (params: object) => Promise<any>,
  isCurrent = () => true
) {
  const records = new Map<string, any>()
  let page = 1
  while (isCurrent()) {
    const response = await request({ page, pageSize: 100 })
    if (!isCurrent()) return []
    if (!Array.isArray(response.data)) throw new Error('产品列表响应格式异常')
    const rows: any[] = response.data
    const previousSize = records.size
    rows.forEach((row) => records.set(String(row.id), row))
    const total = response.totalSize == null ? NaN : Number(response.totalSize)
    if (Number.isFinite(total) && records.size >= total) return [...records.values()]
    if (!Number.isFinite(total) && !rows.length) return [...records.values()]
    if (!rows.length || records.size === previousSize) throw new Error('产品列表未完整加载，请重试')
    // 未提供总数时按实际返回数量继续读取，不能假设服务端使用请求的页大小。
    page += 1
  }
  return []
}

export function groupProducts(products: any[], projects: any[], conditions: any[]): ProductGroup[] {
  const groups = new Map<string, ProductGroup>()
  projects
    .filter((project) => project.key != null)
    .forEach((project) => {
      groups.set(String(project.key), {
        id: String(project.key),
        name: project.title,
        products: [],
        total: 0,
      })
    })
  const keyword = String(conditions.find((item) => item.key === 'keyword')?.value || '')
    .trim()
    .toLocaleLowerCase()
  for (const product of products) {
    const id = String(product.project?.id)
    if (!groups.has(id))
      groups.set(id, { id, name: product.project?.name || '未归属项目', products: [], total: 0 })
    const group = groups.get(id)!
    group.total += 1
    const matches = conditions.every((item) => {
      const value = item.value
      if (
        item.key === 'keyword' ||
        value == null ||
        value === '' ||
        (Array.isArray(value) && !value.length)
      )
        return true
      if (item.key === 'id')
        return String(value)
          .split(/[,，]/)
          .some((id) => id.trim() === String(product.id))
      const values = (Array.isArray(value) ? value : [value]).map(String)
      if (item.key === 'owners')
        return (product.owners || []).some((owner: any) => values.includes(String(owner.id)))
      const actual = item.key === 'update_user' ? product.update_user?.id : product[item.key]
      return values.includes(String(actual))
    })
    if (
      matches &&
      (!keyword || `${group.name} ${product.name}`.toLocaleLowerCase().includes(keyword))
    )
      group.products.push(product)
  }
  const hasFilters = conditions.some((item) =>
    Array.isArray(item.value) ? item.value.length > 0 : String(item.value ?? '').trim() !== ''
  )
  return [...groups.values()]
    .filter(
      (group) =>
        !hasFilters ||
        group.products.length > 0 ||
        (!group.total &&
          keyword &&
          group.name.toLocaleLowerCase().includes(keyword) &&
          conditions.every(
            (item) =>
              item.key === 'keyword' ||
              !item.value ||
              (Array.isArray(item.value) && !item.value.length)
          ))
    )
    .sort((left, right) => left.name.localeCompare(right.name, 'zh-CN', { numeric: true }))
    .map((group) => ({
      ...group,
      products: group.products.sort((left, right) =>
        left.name.localeCompare(right.name, 'zh-CN', { numeric: true })
      ),
    }))
}
