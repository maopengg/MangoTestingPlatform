export function createUiElementCheckSession() {
  let sequence = 0
  let current = null

  function start(elementId, workspaceId = '') {
    current = {
      token: ++sequence,
      elementId: String(elementId || ''),
      workspaceId: String(workspaceId || ''),
      checkId: '',
    }
    return current.token
  }

  function bindCheckId(token, checkId) {
    if (!current || current.token !== token) return false
    current.checkId = String(checkId || '')
    return true
  }

  function accept(result) {
    if (!current || !result) return false
    if (
      current.workspaceId &&
      result.workspace_id &&
      String(result.workspace_id) !== current.workspaceId
    ) {
      return false
    }
    if (
      current.elementId &&
      String(result.element_id || '') !== current.elementId
    ) {
      return false
    }
    if (current.checkId && String(result.check_id || '') !== current.checkId) {
      return false
    }
    current = null
    return true
  }

  function cancel(token) {
    if (!current || (token != null && current.token !== token)) return false
    current = null
    return true
  }

  function isActive(token) {
    return Boolean(current && (token == null || current.token === token))
  }

  return {
    start,
    bindCheckId,
    accept,
    cancel,
    isActive,
  }
}
