export const configPollInterval = 1000
export const configPollAttempts = 20
export const configDrawerWidth = 860
export const browserOptions = [
  { value: 0, label: '谷歌浏览器' },
  { value: 1, label: '微软Edge浏览器' },
  { value: 2, label: '火狐浏览器' },
  { value: 3, label: 'Safari浏览器' },
]
export const h5Options = ['', 'iPhone 12', 'Pixel 5', 'iPad Pro 11'].map((value) => ({
  value,
  label: value || '不开启',
}))
const actuatorTypes: Record<string, { label: string; className: string }> = {
  pytest: { label: 'Pytest', className: 'mango-type-pytest' },
  pytest_web: { label: 'Pytest Web', className: 'mango-type-pytest-web' },
  web_ui: { label: 'Web UI', className: 'mango-type-web-ui' },
  android_ui: { label: 'Android UI', className: 'mango-type-android-ui' },
}
export const getTypeLabel = (type = '') =>
  (actuatorTypes[type] ?? actuatorTypes.pytest_web).label
export const getTypeClass = (type = '') =>
  (actuatorTypes[type] ?? actuatorTypes.pytest_web).className
