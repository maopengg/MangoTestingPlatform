
import { reportLoadError } from '@/utils/load-error'
import { ref, type Ref } from 'vue'
import { getUiPage } from '@/api/uitest/page'
import { getUiElement, getUiElementCategory } from '@/api/uitest/element'
import { liveError, type LiveId } from '@/components/business/ui-live-workbench'
import { elementResponse, readElementPage, readElementList, readElementCategories, type ElementPage, type ElementRow, type ElementCategory, type ElementScope } from '../element-records'

export function useElementResources(options: { scope: ElementScope; pageId: () => LiveId | null; category: () => string; pagination: { page: number; pageSize: number; setTotalSize: (count: number) => void }; loading: Ref<boolean>; clearSelection: () => void }) {
  const page = ref<ElementPage | null>(null), rows = ref<ElementRow[]>([]), categories = ref<ElementCategory[]>([])
  const pageLoading = ref(false), listLoading = options.loading, categoryLoading = ref(false)
  const pageError = ref(''), listError = ref(''), categoryError = ref('')
  let pageSequence = 0, listSequence = 0, categorySequence = 0
  function invalidate() {
    pageSequence++; listSequence++; categorySequence++
    page.value = null; rows.value = []; categories.value = []
    pageLoading.value = listLoading.value = categoryLoading.value = false
    pageError.value = listError.value = categoryError.value = ''
    options.pagination.setTotalSize(0)
  }
  async function loadPage() {
    const id = options.pageId(), current = options.scope.capture(), request = ++pageSequence
    if (id === null || !current()) return false
    pageLoading.value = true; pageError.value = ''
    try { const response: unknown = await getUiPage({ id, page: 1, pageSize: 1 }); if (!current() || request !== pageSequence) return false; const data = elementResponse(response); if (!Array.isArray(data) || data.length !== 1) throw Error('未找到对应页面'); page.value = readElementPage(data[0], id); return true }
    catch (error) { if (current() && request === pageSequence) (reportLoadError(error, "页面信息加载失败，请重试", false), pageError.value = liveError(error, '页面信息加载失败，请重试')); return false }
    finally { if (current() && request === pageSequence) pageLoading.value = false }
  }
  async function loadList() {
    const pageId = options.pageId(), current = options.scope.capture(), request = ++listSequence
    if (pageId === null || !current()) return false
    const query = { page: options.pagination.page, pageSize: options.pagination.pageSize, page_id: pageId, ...(options.category() === '__all__' ? {} : { category: options.category() }) }
    listLoading.value = true; listError.value = ''; options.clearSelection()
    try {
      const response: unknown = await getUiElement(query)
      if (!current() || request !== listSequence) return false
      const result = readElementList(response), last = Math.max(1, Math.ceil(result.total / query.pageSize))
      if (query.page > last) { options.pagination.page = last; return await loadList() }
      rows.value = result.rows; options.pagination.setTotalSize(result.total); return true
    } catch (error) { if (current() && request === listSequence) (reportLoadError(error, "元素列表加载失败，请重试", false), listError.value = liveError(error, '元素列表加载失败，请重试')); return false }
    finally { if (current() && request === listSequence) listLoading.value = false }
  }
  async function loadCategories() {
    const pageId = options.pageId(), current = options.scope.capture(), request = ++categorySequence
    if (pageId === null || !current()) return false
    categoryLoading.value = true; categoryError.value = ''
    try { const response: unknown = await getUiElementCategory({ page_id: pageId }); if (!current() || request !== categorySequence) return false; categories.value = readElementCategories(response); return true }
    catch (error) { if (current() && request === categorySequence) (reportLoadError(error, "元素分类加载失败，请重试", false), categoryError.value = liveError(error, '元素分类加载失败，请重试')); return false }
    finally { if (current() && request === categorySequence) categoryLoading.value = false }
  }
  return { page, rows, categories, pageLoading, listLoading, categoryLoading, pageError, listError, categoryError, loadPage, loadList, loadCategories, invalidate }
}
