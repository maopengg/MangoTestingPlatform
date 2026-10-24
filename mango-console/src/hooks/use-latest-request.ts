export function useLatestRequest() {
  let latestRequestId = 0

  function beginRequest() {
    latestRequestId += 1
    return latestRequestId
  }

  function isLatestRequest(requestId: number) {
    return requestId === latestRequestId
  }

  function invalidateRequests() {
    latestRequestId += 1
  }

  return {
    beginRequest,
    isLatestRequest,
    invalidateRequests,
  }
}
