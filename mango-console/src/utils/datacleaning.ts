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
    result[item.key] = item.value._value || null
  })
  return result
}
