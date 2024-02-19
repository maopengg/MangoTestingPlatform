import { useUserStoreContext } from '@/store/modules/user'
import { AxiosRequestConfig } from 'axios'
import { useProject } from '@/store/modules/get-project'

export default function (config: AxiosRequestConfig) {
  const project = useProject()
  const useStore = useUserStoreContext()
  if (config) {
    if (!config.headers) {
      config.headers = {}
    }
    if (!config.headers['Authorization']) {
      config.headers['Authorization'] = useStore.token
      if (project.selectValue) {
        config.headers['project'] = project.selectValue.toString()
      }
    }
  }
  return config
}
