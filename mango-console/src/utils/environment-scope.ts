export const COMMON_ENV_VALUE = '__common__'

export function normalizeEnvironmentList(value: any): any[] {
  if (Array.isArray(value)) return value.filter((item) => item !== null && item !== undefined && item !== '')
  if (value === null || value === undefined || value === '') return []
  return [value]
}

export function normalizeEnvironmentValues(value: any): number[] {
  const list = normalizeEnvironmentList(value)
  if (list.length === 0 || list.includes(COMMON_ENV_VALUE)) {
    return []
  }
  return list
    .filter((item) => item !== null && item !== undefined && item !== '')
    .map((item) => Number(item))
}

export function toEnvironmentSelectValue(testEnvs: any): any[] {
  const envs = normalizeEnvironmentList(testEnvs)
  return envs.length > 0 ? envs : [COMMON_ENV_VALUE]
}

export function normalizeEnvironmentSelectChange(value: any): any[] {
  const list = normalizeEnvironmentList(value)
  if (list.length === 0) {
    return [COMMON_ENV_VALUE]
  }
  if (list.includes(COMMON_ENV_VALUE)) {
    return list[list.length - 1] === COMMON_ENV_VALUE
      ? [COMMON_ENV_VALUE]
      : list.filter((item) => item !== COMMON_ENV_VALUE)
  }
  return list
}
