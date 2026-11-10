
import { reportLoadError } from '@/utils/load-error'
import { onActivated, onBeforeUnmount, onDeactivated, reactive, watch } from 'vue'
import { getGrayYamlFileBinding } from '@/api/gray'
import { selectionId } from '../forms'
import type { BindingRecord, YamlRecord } from '../forms'
import { bindingPage } from '../binding-rows'

interface BindingWindow {
  visible: boolean
  title: string
  record: Pick<YamlRecord, 'id' | 'name'> | null
  dataList: BindingRecord[]
  loading: boolean
  error: boolean
}

export function useYamlBindings(options: { contextKey: () => string; blocked: () => boolean }) {
  const drawer: BindingWindow = reactive({
    visible: false,
    title: '',
    record: null,
    dataList: [],
    loading: false,
    error: false,
  })
  let active = true,
    generation = 0,
    sequence = 0
  function reset() {
    ++generation
    ++sequence
    drawer.visible = false
    drawer.title = ''
    drawer.record = null
    drawer.dataList = []
    drawer.loading = false
    drawer.error = false
  }
  function onVisibleChange(value: boolean) {
    if (!value && !options.blocked()) reset()
  }
  async function loadBindings(yamlId = drawer.record?.id): Promise<boolean> {
    if (!active || !drawer.visible || !yamlId || yamlId !== drawer.record?.id) return false
    const version = generation,
      request = ++sequence,
      context = options.contextKey()
    const current = () =>
      active &&
      drawer.visible &&
      version === generation &&
      request === sequence &&
      options.contextKey() === context &&
      drawer.record?.id === yamlId
    drawer.loading = true
    drawer.error = false
    try {
      const rows: BindingRecord[] = [],
        seen = new Set<number>()
      let page = 1,
        total: number | null = null
      do {
        const response = await getGrayYamlFileBinding({ yaml_file: yamlId, page, pageSize: 200 })
        if (!current()) return false
        const result = bindingPage(response, yamlId)
        if (total !== null && result.total !== total) throw Error('Binding list changed')
        total = result.total
        for (const row of result.rows) {
          if (seen.has(row.id)) throw Error('Duplicate binding')
          seen.add(row.id)
          rows.push(row)
        }
        if (rows.length > total || (!result.rows.length && rows.length < total))
          throw Error('Incomplete binding list')
        page++
      } while (rows.length < total)
      drawer.dataList = rows
      return true
    } catch (loadFailure0) {
      if (current()) (reportLoadError(loadFailure0, "加载失败，请重试", false), drawer.error = true)
      return false
    } finally {
      if (current()) drawer.loading = false
    }
  }
  function open(record: Pick<YamlRecord, 'id' | 'name'>) {
    if (!active || options.blocked() || !selectionId(record.id)) return
    reset()
    drawer.record = { id: record.id, name: record.name }
    drawer.title = `${record.name} 仓库绑定`
    drawer.visible = true
    void loadBindings(record.id)
  }
  function applyMutation(id: number, status?: number) {
    ++sequence
    drawer.loading = false
    drawer.error = false
    drawer.dataList =
      status === undefined
        ? drawer.dataList.filter((row) => row.id !== id)
        : drawer.dataList.map((row) => (row.id === id ? { ...row, status } : row))
  }
  watch(options.contextKey, reset, { flush: 'sync' })
  onDeactivated(() => {
    active = false
    reset()
  })
  onActivated(() => {
    active = true
  })
  onBeforeUnmount(() => {
    active = false
    reset()
  })
  return { drawer, open, loadBindings, onVisibleChange, applyMutation }
}
