import { FormItem } from '@/types/components'

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

export function getTitleByKey(groups: Group[], key: number): string {
  const group = groups.find((group) => group.key === key)
  if (group) {
    return group.title
  } else {
    throw new Error(`找不到key为${key}的group`)
  }
}

export function convertEmptyStringToNull(obj: any): any {
  for (const key in obj) {
    if (obj[key] === '') {
      obj[key] = null
    }
  }
  return obj
}

type KeyValueObject = {
  [key: string]: any
}

export function getFormItems1(formItems: FormItem[]): KeyValueObject {
  return formItems.reduce((obj: any, item) => {
    if (item.value === '' || item.value === null) {
      obj[item.key] = null
    } else {
      obj[item.key] = item.value
    }
    return obj
  }, {})
}

export function getFormItems(formItems: FormItem[]): KeyValueObject {
  const obj: any = {}
  formItems.forEach((item: any) => {
    // 特殊处理多选框，过滤掉空字符串
    if (item.type === 'select' && Array.isArray(item.value)) {
      // 过滤掉空字符串和无效值
      const filteredValues = item.value.filter((val: any) => val !== '' && val != null)
      obj[item.key] = filteredValues.length > 0 ? filteredValues : null
    }
    // 特殊处理input-tag类型，确保它作为数组发送
    else if (item.type === 'input-tag') {
      // 确保input-tag的值是数组格式
      if (Array.isArray(item.value)) {
        // 过滤掉空字符串
        const filteredValues = item.value.filter((val: any) => val !== '' && val != null)
        obj[item.key] = filteredValues.length > 0 ? filteredValues : []
      } else if (typeof item.value === 'string' && item.value.trim() !== '') {
        // 如果是字符串且非空，则转为包含单个元素的数组
        obj[item.key] = [item.value.trim()]
      } else {
        // 其他情况（空字符串或null）设置为空数组
        obj[item.key] = []
      }
    } else if (item.value === '') {
      obj[item.key] = null
    } else {
      obj[item.key] = item.value
    }
  })
  return obj
}
