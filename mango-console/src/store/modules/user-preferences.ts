import { computed, nextTick, ref, watch } from 'vue'
import { defineStore } from 'pinia'
import useUserStore from './user'
import useAppConfigStore from './app-config'
import { getUserConfig, updateUserConfig } from '@/api/user/user'
import {
  normalizeInterfacePreferences,
  readUserInterfacePreferences,
  readUserSelectedEnvironment,
} from '@/utils/interface-preferences'
import { reportLoadError } from '@/utils/load-error'

export default defineStore('user-preferences', () => {
  const user = useUserStore()
  const app = useAppConfigStore()
  const loading = ref(false)
  const saving = ref(false)
  const ready = ref(false)
  const failed = ref(false)
  const snapshot = computed(() => JSON.stringify(normalizeInterfacePreferences(app.$state)))
  let version = 0
  const saved = ref('')
  const dirty = computed(() => ready.value && snapshot.value !== saved.value)
  let timer: ReturnType<typeof setTimeout> | undefined
  let stop: (() => void) | undefined
  function densityChanged(left: string, right: string) {
    const a = JSON.parse(left),
      b = JSON.parse(right)
    return (
      a.displayDensity !== b.displayDensity ||
      a.autoScale2k !== b.autoScale2k ||
      a.autoScale4k !== b.autoScale4k
    )
  }

  async function reload() {
    const current = ++version
    clearTimeout(timer)
    ready.value = false
    saving.value = false
    failed.value = false
    if (!user.token || !user.userId) {
      loading.value = false
      app.applyInterfacePreferences({})
      return
    }
    loading.value = true
    const environment = user.selected_environment
    try {
      const response = await getUserConfig()
      if (current !== version) return
      app.applyInterfacePreferences(readUserInterfacePreferences(response))
      if (user.selected_environment === environment)
        user.selected_environment = readUserSelectedEnvironment(response)
      await nextTick()
      if (current !== version) return
      saved.value = snapshot.value
      ready.value = true
    } catch (error) {
      if (current === version) {
        failed.value = true
        reportLoadError(error, '界面设置读取失败，请重试')
      }
    } finally {
      if (current === version) loading.value = false
    }
  }

  async function flush() {
    clearTimeout(timer)
    if (
      !ready.value ||
      saving.value ||
      !user.token ||
      !user.userId ||
      snapshot.value === saved.value
    )
      return
    const current = version
    const value = snapshot.value
    saving.value = true
    failed.value = false
    let success = false
    try {
      const response = await updateUserConfig([{ key: 'interface', value: JSON.parse(value) }])
      if (current !== version) return
      if (response.code !== 200) throw new Error('Invalid preferences response')
      saved.value = value
      success = true
    } catch (error) {
      if (current === version) {
        failed.value = true
        reportLoadError(error, '界面设置保存失败，请重试')
      }
    } finally {
      if (current === version) {
        saving.value = false
        if ((success || snapshot.value !== value) && snapshot.value !== saved.value) {
          if (densityChanged(snapshot.value, value)) void flush()
          else timer = setTimeout(() => void flush(), 500)
        }
      }
    }
  }

  function start() {
    if (stop) return stop
    const stopChanges = watch(snapshot, (value, previous) => {
      if (!ready.value) return
      clearTimeout(timer)
      if (densityChanged(value, previous)) void flush()
      else timer = setTimeout(() => void flush(), 500)
    })
    const stopIdentity = watch(
      () => [user.userId, user.token],
      () => {
        app.applyInterfacePreferences({})
        void reload()
      },
      { immediate: true, flush: 'sync' }
    )
    stop = () => {
      stopChanges()
      stopIdentity()
      clearTimeout(timer)
      version++
      ready.value = false
      stop = undefined
    }
    return stop
  }

  function retry() {
    return ready.value ? flush() : reload()
  }
  return { loading, saving, ready, failed, dirty, reload, flush, retry, start }
})
