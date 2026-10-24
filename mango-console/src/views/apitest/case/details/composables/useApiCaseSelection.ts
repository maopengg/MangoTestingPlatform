export function useApiCaseSelection() {
  let parameterLoadToken = 0
  let executionResultLoadToken = 0

  function nextParameterLoadToken() {
    parameterLoadToken += 1
    return parameterLoadToken
  }

  function isCurrentParameterLoad(token: number) {
    return token === parameterLoadToken
  }

  function invalidateParameterLoad() {
    parameterLoadToken += 1
  }

  function nextExecutionResultLoadToken() {
    executionResultLoadToken += 1
    return executionResultLoadToken
  }

  function isCurrentExecutionResultLoad(token: number) {
    return token === executionResultLoadToken
  }

  function invalidateExecutionResultLoad() {
    executionResultLoadToken += 1
  }

  return {
    nextParameterLoadToken,
    isCurrentParameterLoad,
    invalidateParameterLoad,
    nextExecutionResultLoadToken,
    isCurrentExecutionResultLoad,
    invalidateExecutionResultLoad,
  }
}
