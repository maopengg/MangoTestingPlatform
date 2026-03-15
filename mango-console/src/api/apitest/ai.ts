import { get, post } from '@/api/http'

/**
 * 步骤1：AI 解析任意文本，写入 ApiInfo，返回解析结果
 */
export function postAiImport(data: object) {
  return post({
    url: '/api/info/ai/import',
    data: () => data,
  })
}

/**
 * 步骤2：根据 ApiInfo ID，AI 推断用例配置，返回预览数据（不写库）
 */
export function postAiPreviewCase(data: object) {
  return post({
    url: '/api/info/ai/preview_case',
    data: () => data,
  })
}

/**
 * 步骤3：用户确认后，将预览数据写入三张表
 */
export function postAiConfirmCase(data: object) {
  return post({
    url: '/api/info/ai/confirm_case',
    data: () => data,
  })
}

/**
 * 执行接口测试（复用已有接口）
 */
export function getApiInfoRun(id: number, testEnv: any) {
  return get({
    url: '/api/info/test',
    data: () => ({ id, test_env: testEnv }),
  })
}
