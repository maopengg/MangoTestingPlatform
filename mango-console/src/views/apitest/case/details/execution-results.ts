export function latestScenarioAttempts(steps: any[]) {
  const latest = new Map<string, any>()
  steps.forEach((step, index) => {
    const key = step.parameter_id == null ? `legacy-${index}` : `${step.id}-${step.parameter_id}`
    const previous = latest.get(key)
    if (!previous || Number(step.retry_index || 0) >= Number(previous.retry_index || 0)) {
      latest.set(key, step)
    }
  })
  return [...latest.values()]
}
