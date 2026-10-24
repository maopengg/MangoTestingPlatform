import { useUserStoreContext } from '@/store/modules/user'
import { AxiosRequestConfig } from 'axios'

export default function (config: AxiosRequestConfig) {
  const useStore = useUserStoreContext()
  if (config) {
    if (!config.headers) {
      config.headers = {}
    }
    config.headers['Source-Type'] = '1'
    if (useStore.token && !config.headers['Authorization']) {
      config.headers['Authorization'] = useStore.token
    }
  }
  return config
}
