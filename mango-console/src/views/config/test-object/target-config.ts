export interface TestTargetConfig {
  default: string
  selector: string
  mapping: Record<string, string>
}

export const emptyTargetConfig = (): TestTargetConfig => ({
  default: '', selector: '', mapping: {},
})

export function validateTargetConfig(config: TestTargetConfig): string {
  if (config.default.length > 1024) return '默认地址最多 1024 个字符'
  if (!config.selector) return config.default.trim() ? '' : '请填写默认地址或配置变量映射'
  if (!/^[^{}$|()]+$/.test(config.selector.trim())) return '条件变量直接填写缓存键名，例如租户id，不使用模板语法'
  const entries = Object.entries(config.mapping)
  if (!entries.length || entries.length > 200) return '请配置 1 至 200 项地址映射'
  if (entries.some(([key, value]) => !key.trim() || key !== key.trim() || !value.trim() || value.length > 1024)) return '条件值与地址不能为空，地址最多 1024 个字符'
  return ''
}
