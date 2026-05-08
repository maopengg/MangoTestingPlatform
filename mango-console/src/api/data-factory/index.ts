import { deleted, get, post, put } from '@/api/http'

export function getDataFactoryDatasourceAlias(data: object) {
  return get({ url: '/data-factory/datasource-alias', data: () => data })
}

export function postDataFactoryDatasourceAlias(data: object) {
  return post({ url: '/data-factory/datasource-alias', data: () => data })
}

export function putDataFactoryDatasourceAlias(data: object) {
  return put({ url: '/data-factory/datasource-alias', data: () => data })
}

export function deleteDataFactoryDatasourceAlias(id: number | string[] | number[]) {
  return deleted({ url: '/data-factory/datasource-alias', data: () => ({ id }) })
}

export function getDataFactoryDatasourceBinding(data: object) {
  return get({ url: '/data-factory/datasource-binding', data: () => data })
}

export function postDataFactoryDatasourceBinding(data: object) {
  return post({ url: '/data-factory/datasource-binding', data: () => data })
}

export function putDataFactoryDatasourceBinding(data: object) {
  return put({ url: '/data-factory/datasource-binding', data: () => data })
}

export function deleteDataFactoryDatasourceBinding(id: number | string[] | number[]) {
  return deleted({ url: '/data-factory/datasource-binding', data: () => ({ id }) })
}

export function getDataFactoryEntity(data: object) {
  return get({ url: '/data-factory/entity', data: () => data })
}

export function postDataFactoryEntity(data: object) {
  return post({ url: '/data-factory/entity', data: () => data })
}

export function putDataFactoryEntity(data: object) {
  return put({ url: '/data-factory/entity', data: () => data })
}

export function deleteDataFactoryEntity(id: number | string[] | number[]) {
  return deleted({ url: '/data-factory/entity', data: () => ({ id }) })
}

export function postDataFactoryEntityCopy(data: object) {
  return post({ url: '/data-factory/entity/copy', data: () => data })
}

export function putDataFactoryEntityStatus(data: object) {
  return put({ url: '/data-factory/entity/status', data: () => data })
}

export function getDataFactoryField(data: object) {
  return get({ url: '/data-factory/field', data: () => data })
}

export function postDataFactoryFieldBatchSave(data: object) {
  return post({ url: '/data-factory/field/batch-save', data: () => data })
}

export function postDataFactoryFieldPreviewValues(data: object) {
  return post({ url: '/data-factory/field/preview-values', data: () => data })
}

export function postDataFactoryDiscoverTestConnection(data: object) {
  return post({ url: '/data-factory/discover/test-connection', data: () => data })
}

export function postDataFactoryDiscoverTables(data: object) {
  return post({ url: '/data-factory/discover/tables', data: () => data })
}

export function postDataFactoryDiscoverTable(data: object) {
  return post({ url: '/data-factory/discover/table', data: () => data })
}

export function getDataFactoryTemplate(data: object) {
  return get({ url: '/data-factory/template', data: () => data })
}

export function postDataFactoryTemplate(data: object) {
  return post({ url: '/data-factory/template', data: () => data })
}

export function putDataFactoryTemplate(data: object) {
  return put({ url: '/data-factory/template', data: () => data })
}

export function deleteDataFactoryTemplate(id: number | string[] | number[]) {
  return deleted({ url: '/data-factory/template', data: () => ({ id }) })
}

export function postDataFactoryTemplateCopy(data: object) {
  return post({ url: '/data-factory/template/copy', data: () => data })
}

export function putDataFactoryTemplateStatus(data: object) {
  return put({ url: '/data-factory/template/status', data: () => data })
}

export function postDataFactoryTemplateDebugRun(data: object) {
  return post({ url: '/data-factory/template/debug-run', data: () => data })
}

export function postDataFactoryTemplatePreview(data: object) {
  return post({ url: '/data-factory/template/preview', data: () => data })
}

export function postDataFactoryTemplateDebugCleanup(data: object) {
  return post({ url: '/data-factory/template/debug-cleanup', data: () => data })
}

export function getDataFactoryExecution(data: object) {
  return get({ url: '/data-factory/execution', data: () => data })
}

export function getDataFactoryExecutionItem(data: object) {
  return get({ url: '/data-factory/execution/item', data: () => data })
}

export function getDataFactoryExecutionDetail(data: object) {
  return get({ url: '/data-factory/execution/detail', data: () => data })
}

export function postDataFactoryExecutionCleanup(data: object) {
  return post({ url: '/data-factory/execution/cleanup', data: () => data })
}

export function postDataFactoryExecutionCleanupRetry(data: object) {
  return post({ url: '/data-factory/execution/cleanup-retry', data: () => data })
}
