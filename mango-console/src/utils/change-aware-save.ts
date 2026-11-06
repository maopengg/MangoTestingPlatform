type RecordValue = Record<string, any>

function signature(field: string, value: any): string | undefined {
  if (['front_func', 'posterior_func', 'ass_text_all', 'params'].includes(field) && value === '')
    value = null
  if (['ass_json_all', 'ass_schema'].includes(field) && typeof value === 'string') {
    try {
      value = JSON.parse(value)
    } catch {
      /* Invalid editor text is not persisted. */
    }
  }
  return JSON.stringify(value, (_key, item) =>
    item && typeof item === 'object' && !Array.isArray(item)
      ? Object.fromEntries(
          Object.keys(item)
            .sort()
            .map((key) => [key, item[key]])
        )
      : item
  )
}

export function createChangeAwareSave<T>(write: (payload: any) => Promise<T>) {
  const records = new Map<
    string,
    {
      saved: Map<string, string | undefined>
      tail: Promise<unknown>
    }
  >()

  function seed(record: RecordValue) {
    if (!record?.id) return
    records.set(String(record.id), {
      saved: new Map(Object.entries(record).map(([key, value]) => [key, signature(key, value)])),
      tail: Promise.resolve(),
    })
  }

  function save(payload: RecordValue): Promise<T | null> {
    const id = String(payload.id)
    let entry = records.get(id)
    if (!entry) {
      entry = { saved: new Map(), tail: Promise.resolve() }
      records.set(id, entry)
    }
    // Freeze the submitted value: Vue models may continue changing while a request is pending.
    const snapshot = JSON.parse(JSON.stringify(payload))
    const current = entry
    const task = async () => {
      if (records.get(id) !== current) return null
      const changed = Object.keys(snapshot).filter(
        (key) =>
          key !== 'id' &&
          (!current.saved.has(key) || current.saved.get(key) !== signature(key, snapshot[key]))
      )
      if (!changed.length) return null
      const request = {
        id: snapshot.id,
        ...Object.fromEntries(changed.map((key) => [key, snapshot[key]])),
      }
      const response = await write(request)
      if (records.get(id) === current) {
        changed.forEach((key) => current.saved.set(key, signature(key, snapshot[key])))
      }
      return response
    }
    const pending = current.tail.then(task, task)
    current.tail = pending.catch(() => undefined)
    return pending
  }

  return { seed, save }
}
