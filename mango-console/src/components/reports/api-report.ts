import { historyId, historyObject, historyText } from '../business/execution-history'

const scalar = (value: unknown): number | string | null => typeof value === 'string' || (typeof value === 'number' && Number.isFinite(value)) ? value : null
const status = (value: unknown) => typeof value === 'number' && Number.isInteger(value) ? (value === 6 ? 0 : value) : null
const counter = (value: unknown) => typeof value === 'number' && Number.isFinite(value) && value >= 0 ? value : null

export function apiReport(value: unknown) {
  const row = historyObject(value), request = historyObject(row?.request), response = historyObject(row?.response)
  const retry = historyObject(row?.snapshot_retry), progress = historyObject(row?.snapshot_progress)
  const recoveryErrors = row?.recovery_errors, assertions = row?.ass
  return {
    id: historyId(row?.id), name: historyText(row?.name), test_time: scalar(row?.test_time),
    status: status(row?.status), main_status: status(row?.main_status), recovery_status: status(row?.recovery_status),
    is_recovery: row?.is_recovery === true,
    recovery_errors: Array.isArray(recoveryErrors) ? recoveryErrors.filter((item): item is string => typeof item === 'string') : [],
    error_message: historyText(row?.error_message), result_mode: historyText(row?.result_mode),
    failure_category: historyText(row?.failure_category), protocol_status: historyText(row?.protocol_status),
    posterior_skipped_reason: historyText(row?.posterior_skipped_reason),
    assertion_skipped_reason: historyText(row?.assertion_skipped_reason),
    snapshot_updated_at: scalar(row?.snapshot_updated_at),
    snapshot_retry: { current: counter(retry?.current), max: counter(retry?.max) },
    snapshot_progress: { done: counter(progress?.done), total: counter(progress?.total) },
    cache_data: row?.cache_data, data_factory_cache_data: row?.data_factory_cache_data,
    ass: Array.isArray(assertions) ? assertions.map(historyObject).filter((item): item is Record<string, unknown> => item !== null) : [],
    request: {
      method: historyText(request?.method), url: historyText(request?.url), headers: request?.headers,
      params: request?.params, request_body: request?.request_body, data: request?.data, json: request?.json,
      sse_config: request?.sse_config, request_files: request?.request_files, file: request?.file,
    },
    response: {
      code: scalar(response?.code), time: scalar(response?.time), headers: response?.headers,
      json: response?.json, text: response?.text, sse_events: response?.sse_events,
      ws_messages: response?.ws_messages, ws_stop_reason: response?.ws_stop_reason,
      ws_close_code: response?.ws_close_code, ws_close_reason: response?.ws_close_reason,
      request_headers: response?.request_headers, request_params: response?.request_params,
      request_body: response?.request_body, request_file: response?.request_file,
    },
  }
}

export function responseCorrelationIds(headers: unknown): Array<{ name: string; value: string }> {
  const allowed = new Set(['x-request-id', 'x-trace-id', 'x-log-id', 'xlog'])
  return Object.entries(historyObject(headers) || {}).flatMap(([key, raw]) => {
    const name = key.toLowerCase(), value = historyText(raw).trim()
    return allowed.has(name) && /^[A-Za-z0-9._:-]{1,128}$/.test(value) ? [{ name, value }] : []
  })
}
