export function createCaseRequestScope() {
  let generation = 0
  const sequences = new Map<string, number>()
  function capture() {
    const current = generation
    return () => current === generation
  }
  function begin(key: string) {
    const current = capture(),
      sequence = (sequences.get(key) || 0) + 1
    sequences.set(key, sequence)
    return () => current() && sequences.get(key) === sequence
  }
  function invalidate() {
    generation++
    sequences.clear()
  }
  return { begin, capture, invalidate }
}
