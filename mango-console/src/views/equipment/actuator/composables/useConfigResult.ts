import { configPollAttempts, configPollInterval } from '../config'
import type { ConfigResult } from '../types'
export function useConfigResult() {
  const delays = new Map<ReturnType<typeof setTimeout>, (value: boolean) => void>()
  function sleep() {
    return new Promise<boolean>((resolve) => {
      const timer = setTimeout(() => {
        delays.delete(timer)
        resolve(true)
      }, configPollInterval)
      delays.set(timer, resolve)
    })
  }
  function cancel() {
    delays.forEach((resolve, timer) => {
      clearTimeout(timer)
      resolve(false)
    })
    delays.clear()
  }
  async function wait(
    requestId: string,
    username: string,
    read: (id: string) => Promise<{ data?: ConfigResult }>,
    current: () => boolean,
    kind: '读取' | '保存'
  ): Promise<ConfigResult | null> {
    if (!requestId) throw Error(`执行器配置${kind}请求未返回请求编号`)
    for (let index = 0; index < configPollAttempts; index++) {
      if (!current() || !(await sleep()) || !current()) return null
      const response = await read(requestId)
      if (!current()) return null
      const result = response.data
      if (result?.username && result.username !== username)
        throw Error(`执行器配置${kind}结果不匹配，请重试`)
      if (result?.status === 'success') return result
      if (result?.status === 'failed') throw Error(result.message || `执行器配置${kind}失败`)
      if (result?.status === 'expired') throw Error(`执行器配置${kind}超时`)
    }
    throw Error(`执行器配置${kind}超时`)
  }
  return { wait, cancel }
}
