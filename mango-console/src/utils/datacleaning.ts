import { useProject } from '@/store/modules/get-project'

interface Option {
  value: number
  label: string
}

// 替换表单中的数据成数字
export function getExpValue(exp: string, options: Option[]) {
  return options.find((item) => item.label === exp)?.value
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

// 根据项目名称获取项目ID
export function getKeyByTitle(groups: Group[], title: string): number {
  const group = groups.find((group) => group.title === title)
  if (group) {
    return group.key
  } else {
    throw new Error(`找不到title为${title}的group`)
  }
}
