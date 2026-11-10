import { computed, onScopeDispose, reactive, ref } from 'vue'
import { getPytestCase, getPytestCaseRead, getPytestCaseMethodNodes } from '@/api/pytest/case'
import { readCase } from '../records'
import type { CaseRecord, DirectoryNode } from '../records'
import { methodNodes, sourceSnapshot, unboundFeature } from '../source'
import type { PytestFileType, PytestMethodNode, SourceSnapshot } from '../source'

interface SourceFile { snapshot: SourceSnapshot | null; loading: boolean; failed: boolean }
export function useCaseSource(scope: { available: () => boolean; version: () => number; loaded: (record: CaseRecord) => void }) {
  const selectedFile = ref<DirectoryNode | null>(null), record = ref<CaseRecord | null>(null), metadataLoading = ref(false), metadataFailed = ref(false)
  const empty = (): SourceFile => ({ snapshot: null, loading: false, failed: false })
  const files = reactive({ py: empty(), feature: empty() }), fileType = ref<PytestFileType>('py'), featureAbsent = ref(false)
  const nodes = ref<PytestMethodNode[]>([]), methodsLoading = ref(false), methodsFailed = ref(false)
  let generation = 0, disposed = false
  const pending = new Map<string, { current: () => boolean; promise: Promise<boolean> }>()
  const hasFeature = computed(() => !featureAbsent.value && Boolean(record.value?.feature_file_path || files.feature.snapshot))
  const currentFile = computed(() => files[fileType.value]), text = computed(() => currentFile.value.snapshot?.content ?? '')
  function invalidate(clear = true): void {
    generation++; pending.clear(); metadataLoading.value = false; methodsLoading.value = false
    files.py.loading = false; files.feature.loading = false
    if (clear) {
      selectedFile.value = null; record.value = null; metadataFailed.value = false; methodsFailed.value = false; nodes.value = []
      Object.assign(files.py, empty()); Object.assign(files.feature, empty()); fileType.value = 'py'; featureAbsent.value = false
    }
  }
  function read(key: string, loading: (value: boolean) => void, failed: (value: boolean) => void, work: (id: number, current: () => boolean) => Promise<void>): Promise<boolean> {
    const id = selectedFile.value?.case_id
    if (!id || disposed || !scope.available()) return Promise.resolve(false)
    const existing = pending.get(key)
    if (existing?.current()) return existing.promise
    const window = generation, epoch = scope.version()
    const current = () => !disposed && scope.available() && scope.version() === epoch && generation === window && pending.get(key) === job
    const job = { current, promise: Promise.resolve(false) }
    pending.set(key, job); loading(true); failed(false)
    job.promise = Promise.resolve().then(async () => {
      try { if (!current()) return false; await work(id, current); return current() }
      catch { if (current()) failed(true); return false }
      finally { if (pending.get(key) === job) { pending.delete(key); loading(false) } }
    })
    return job.promise
  }
  function loadMetadata(): Promise<boolean> {
    return read('metadata', value => { metadataLoading.value = value }, value => { metadataFailed.value = value }, async (id, current) => {
      const next = readCase(await getPytestCase({ id, page: 1, pageSize: 1 }), id)
      if (!current()) return
      record.value = next; scope.loaded(next)
    })
  }
  function loadFile(type: PytestFileType): Promise<boolean> {
    const file = files[type]
    return read(type, value => { file.loading = value }, value => { file.failed = value }, async (id, current) => {
      try {
        const next = sourceSnapshot(await getPytestCaseRead(id, type, type === 'feature'))
        if (!current()) return
        file.snapshot = next; if (type === 'feature') featureAbsent.value = false
      } catch (error) {
        if (type === 'feature' && unboundFeature(error)) {
          if (current()) { featureAbsent.value = true; if (fileType.value === 'feature') fileType.value = 'py' }
        } else throw error
      }
    })
  }
  function loadMethods(): Promise<boolean> {
    return read('methods', value => { methodsLoading.value = value }, value => { methodsFailed.value = value }, async (id, current) => {
      const next = methodNodes(await getPytestCaseMethodNodes(id, true)); if (current()) nodes.value = next
    })
  }
  async function select(file: DirectoryNode): Promise<void> {
    if (disposed || !scope.available() || !file.case_id) return
    invalidate(); selectedFile.value = file
    await Promise.all([loadMetadata(), loadFile('py'), loadFile('feature'), loadMethods()])
  }
  function invalidateMetadata(): void { pending.delete('metadata'); metadataLoading.value = false }
  onScopeDispose(() => { disposed = true; invalidate() })
  return { selectedFile, record, metadataLoading, metadataFailed, files, fileType, hasFeature, currentFile, text, nodes, methodsLoading, methodsFailed, invalidate, invalidateMetadata, select, loadMetadata, loadFile, loadMethods }
}
