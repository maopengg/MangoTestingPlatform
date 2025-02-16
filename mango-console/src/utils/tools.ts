import { Message } from '@arco-design/web-vue'

/**
 * 将给定的对象转换为格式化的 JSON 字符串。
 * @param items - 需要格式化的对象，可以为 null。
 * @returns 格式化后的 JSON 字符串，如果 items 为 null，则返回 null。
 */
export function formatJson(items: any) {
  if (items === null) {
    return null
  }
  return JSON.stringify(items, null, 2)
}

/**
 * 解析 JSON 字符串并返回对应的对象。
 * 如果解析失败，或输入的字符串不是有效的 JSON 格式，则会显示错误消息。
 * @param key - 错误消息中使用的键名，用于提示用户。
 * @param value1 - 需要解析的 JSON 字符串。
 * @returns 解析后的对象，如果解析失败或输入无效，则返回 false。
 */
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

/**
 * 将 JSON 字符串转换为格式化的 JSON 字符串。
 * 如果输入为 null，直接返回 null；如果解析失败，则返回原始字符串的格式化结果。
 * @param value - 需要格式化的 JSON 字符串，可以为 null。
 * @returns 格式化后的 JSON 字符串，如果解析失败，则返回格式化后的原始字符串。
 */
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
