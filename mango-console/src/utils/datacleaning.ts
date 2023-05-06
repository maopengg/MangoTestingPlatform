interface Option {
  key: number
  title: string
}

// 替换表单中的数据成数字
export function getExpValue(exp: string, options: Option[]) {
  return options.find((item) => item.title === exp)?.key
}

// 取出表单中的数据
export function transformData(data: any) {
  const result: any = {}
  data.forEach((item: any) => {
    if (item.value._value === 0) {
      result[item.key] = 0
    } else {
      result[item.key] = item.value._value || null
    }
  })
  return result
}

interface Group {
  title: string
  key: number
}

// 根据title的文字获取key的值
export function getKeyByTitle(groups: Group[], title: string): number {
  const group = groups.find((group) => group.title === title)
  if (group) {
    return group.key
  } else {
    throw new Error(`找不到title为${title}的group`)
  }
}

// 根据key的值获取title

export function getKeyByKey(groups: Group[], key: number): string {
  const group = groups.find((group) => group.key === key)
  if (group) {
    return group.title
  } else {
    throw new Error(`找不到key为${key}的group`)
  }
}
