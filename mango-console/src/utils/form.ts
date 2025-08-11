export function isValidInteger(value, allowZero = false) {
  // 检查数字类型
  if (typeof value === 'number') {
    return Number.isInteger(value) && (allowZero || value !== 0)
  }
  if (typeof value === 'string') {
    const str = value.trim()
    if (!str) return true
    const regex = allowZero ? /^-?\d+$/ : /^[1-9]\d*$/
    return regex.test(str)
  }

  return false
}
