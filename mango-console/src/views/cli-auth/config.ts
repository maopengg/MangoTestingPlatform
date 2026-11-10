export const authorizationStatusText = {
  loading: '正在安全地授权当前 CLI…',
  success: '授权已完成，正在返回终端…',
  error: '未能完成授权',
} as const

export const authorizationMessages = {
  invalidParams: 'CLI 授权参数无效，请返回终端重新执行登录命令。',
  invalidResult: '未收到有效的 CLI 授权结果，请重试。',
  loginRedirectFailed: '未能打开登录页面，请重试。',
  failed: '授权失败，请重试。',
}

export const callbackPolicy = {
  protocol: 'http:',
  hostname: '127.0.0.1',
  pathname: '/callback',
} as const
