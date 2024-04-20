import { Message } from '@arco-design/web-vue'

export function formatJson(items: any) {
  if (items === null) {
    return null
  }
  return JSON.stringify(items, null, 2)
}

export function formatJsonObj(key: string, value1: string) {
  try {
    if (value1) {
      const parsedValue = JSON.parse(value1)
      if (typeof parsedValue === 'object') {
        return parsedValue
      } else {
        Message.error(`请输入json格式的：${key}`)
        return false
      }
    } else {
      return null
    }
  } catch (e) {
    Message.error(`请输入json格式的：${key}`)
    return false
  }
}

export function strJson(value: string | null) {
  if (value === null) {
    return value
  }
  try {
    return formatJson(JSON.parse(value))
  } catch (e) {
    return formatJson(value)
  }
}
