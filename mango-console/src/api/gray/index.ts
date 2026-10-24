import { deleted, get, post, put } from '@/api/http'

export function getGrayRepository(data: object) {
  return get({ url: '/gray/repository', data: () => data })
}

export function postGrayRepository(data: object) {
  return post({ url: '/gray/repository', data: () => data })
}

export function putGrayRepository(data: object) {
  return put({ permissionKey: 'gray.repository', url: '/gray/repository', data: () => data })
}

export function deleteGrayRepository(id: number | string[] | number[]) {
  return deleted({ url: '/gray/repository', data: () => ({ id }) })
}

export function postGrayRepositoryTest(data: object) {
  return post({ url: '/gray/repository/test', data: () => data })
}

export function postGrayRepositorySync(data: object) {
  return post({ url: '/gray/repository/sync', data: () => data })
}

export function getGrayYamlFile(data: object) {
  return get({ url: '/gray/yaml-file', data: () => data })
}

export function postGrayYamlFile(data: object) {
  return post({ url: '/gray/yaml-file', data: () => data })
}

export function putGrayYamlFile(data: object) {
  return put({ permissionKey: 'gray.config_file', url: '/gray/yaml-file', data: () => data })
}

export function deleteGrayYamlFile(id: number | string[] | number[]) {
  return deleted({ url: '/gray/yaml-file', data: () => ({ id }) })
}

export function getGrayYamlFileBinding(data: object) {
  return get({ url: '/gray/yaml-file-binding', data: () => data })
}

export function postGrayYamlFileBinding(data: object) {
  return post({ url: '/gray/yaml-file-binding', data: () => data })
}

export function putGrayYamlFileBinding(data: object) {
  return put({ permissionKey: 'gray.config_file', url: '/gray/yaml-file-binding', data: () => data })
}

export function deleteGrayYamlFileBinding(id: number | string[] | number[]) {
  return deleted({ url: '/gray/yaml-file-binding', data: () => ({ id }) })
}

export function getGrayYamlFileContent(data: object) {
  return get({ url: '/gray/yaml-file/content', data: () => data })
}

export function getGrayYamlRepositoryFiles(data: object) {
  return get({ url: '/gray/yaml-file/repository-files', data: () => data })
}

export function getGrayFeature(data: object) {
  return get({ url: '/gray/feature', data: () => data })
}

export function postGrayFeature(data: object) {
  return post({ url: '/gray/feature', data: () => data })
}

export function putGrayFeature(data: object) {
  return put({ permissionKey: 'gray.feature', url: '/gray/feature', data: () => data })
}

export function deleteGrayFeature(id: number | string[] | number[]) {
  return deleted({ url: '/gray/feature', data: () => ({ id }) })
}

export function postGrayFeaturePreview(data: object) {
  return post({ url: '/gray/feature/preview', data: () => data })
}

export function postGrayFeatureExecute(data: object) {
  return post({ url: '/gray/feature/execute', data: () => data })
}

export function getGrayCaseConfig(data: object) {
  return get({ url: '/gray/case-config', data: () => data })
}

export function postGrayCaseConfigBatchSave(data: object) {
  return post({ url: '/gray/case-config/batch-save', data: () => data })
}

export function postGrayCaseConfigReplaceScope(data: object) {
  return post({ url: '/gray/case-config/replace-scope', data: () => data })
}

export function getGrayExecutionLog(data: object) {
  return get({ url: '/gray/execution-log', data: () => data })
}

export function postGrayExecutionRetryRestore(data: object) {
  return post({ url: '/gray/execution-log/retry-restore', data: () => data })
}

export function postGrayExecutionLogCleanupExpired(data: object) {
  return post({ url: '/gray/execution-log/cleanup-expired', data: () => data })
}
