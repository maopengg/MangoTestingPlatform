import { onBeforeUnmount, onDeactivated, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Message, Modal } from '@arco-design/web-vue'
import { useUserStoreContext } from '@/store/modules/user'
import { getSystemTestSuiteDetailsRetry } from '@/api/system/test_sute_details'
import { reportIdentifier, reportPayload } from '../report-overview'

interface RetryOptions {
  reportId(): string
  available(): boolean
  onSuccess(): Promise<unknown>
}

export function useReportCaseRetry(options: RetryOptions) {
  const route = useRoute(), userStore = useUserStoreContext()
  const busyIds = ref<string[]>([])
  let version = 0, disposed = false
  let confirmation: ReturnType<typeof Modal.confirm> | null = null
  function dismiss() {
    version += 1
    const previous = confirmation
    confirmation = null
    previous?.close()
  }
  function confirm(input: unknown) {
    const id = reportIdentifier(input)
    if (disposed || !options.available() || id === null || busyIds.value.includes(id)) return
    dismiss()
    const currentVersion = version, reportId = options.reportId()
    const current = () => !disposed && options.available() && currentVersion === version && reportId === options.reportId()
    confirmation = Modal.confirm({
      title: '确认重试', content: '是否重试？如原执行因平台受阻中断，请确认相关数据及清理状态，避免重复写入。', cancelText: '取消', okText: '确认重试',
      onCancel: () => { if (currentVersion === version) dismiss() },
      onBeforeOk: async () => {
        if (!current() || busyIds.value.includes(id)) return false
        busyIds.value = [...busyIds.value, id]
        let accepted = false
        try {
          reportPayload(await getSystemTestSuiteDetailsRetry(id, true))
          accepted = true
          if (!current()) return false
          Message.success('重试任务已提交')
          await options.onSuccess()
          if (!current()) return false
          confirmation = null
          return true
        } catch {
          if (current()) {
            if (accepted) { Message.warning('重试任务已提交，结果刷新失败，请稍后查看'); confirmation = null }
            else Message.error('重试任务提交失败，请重试')
          }
          return accepted && current()
        } finally {
          busyIds.value = busyIds.value.filter(value => value !== id)
        }
      },
    })
  }
  function visibilityChanged() { if (document.visibilityState !== 'visible') dismiss() }
  watch(() => [options.reportId(), route.fullPath, userStore.userId, userStore.roleId, userStore.token, userStore.selected_environment], dismiss, { flush: 'sync' })
  onMounted(() => document.addEventListener('visibilitychange', visibilityChanged))
  onDeactivated(dismiss)
  onBeforeUnmount(() => { disposed = true; dismiss(); document.removeEventListener('visibilitychange', visibilityChanged) })
  return { busyIds, confirm }
}
