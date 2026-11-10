import type { ScenarioScriptPreview } from './types'

export function readScenarioScriptPreview(value: unknown, scenarioId: string): ScenarioScriptPreview {
  if (!value || typeof value !== 'object' || Array.isArray(value) || !('code' in value) || value.code !== 200 || !('data' in value))
    throw new Error('预览请求未成功')
  const data = value.data
  if (!data || typeof data !== 'object' || Array.isArray(data)) throw new Error('预览响应格式不正确')
  if (!('scenario_version' in data) || typeof data.scenario_version !== 'number' || !Number.isSafeInteger(data.scenario_version) || data.scenario_version < 1 ||
    !('snapshot_hash' in data) || typeof data.snapshot_hash !== 'string' || !/^[a-f0-9]{64}$/i.test(data.snapshot_hash) ||
    !('script' in data) || typeof data.script !== 'string' || !data.script.trim() ||
    !('snapshot' in data) || typeof data.snapshot !== 'string' || !data.snapshot.trim())
    throw new Error('预览响应格式不正确')
  const snapshot: unknown = JSON.parse(data.snapshot)
  if (!snapshot || typeof snapshot !== 'object' || Array.isArray(snapshot) ||
    !('schema_version' in snapshot) || (snapshot.schema_version !== 1 && snapshot.schema_version !== 2) ||
    !('scenario_id' in snapshot) || snapshot.scenario_id !== Number(scenarioId) ||
    !('scenario_version' in snapshot) || snapshot.scenario_version !== data.scenario_version)
    throw new Error('预览快照与当前场景不一致')
  return {
    scenario_version: data.scenario_version, snapshot_hash: data.snapshot_hash,
    script: data.script, snapshot: data.snapshot,
  }
}
