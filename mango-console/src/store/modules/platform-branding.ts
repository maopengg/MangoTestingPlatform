import { defineStore } from 'pinia'
import { get } from '@/api/http'

export interface PublicPlatformConfig {
  allow_registration: boolean
  disabled_message: string
  show_author_info: boolean
  show_home_author_popup: boolean
  platform_name: string
  platform_name_en: string
}

let pendingConfig: Promise<PublicPlatformConfig> | undefined

export default defineStore('platform-branding', {
  state: () => ({ projectName: '芒果测试平台', englishName: 'mango-test-platform', loading: false }),
  actions: {
    apply(config: Partial<PublicPlatformConfig>) {
      if (typeof config.platform_name === 'string' && config.platform_name.trim()) {
        this.projectName = config.platform_name.trim()
      }
      if (typeof config.platform_name_en === 'string' && config.platform_name_en.trim()) {
        this.englishName = config.platform_name_en.trim()
      }
    },
    async loadPublicConfig() {
      this.loading = true
      try {
        if (!pendingConfig) {
          pendingConfig = get<PublicPlatformConfig>({
            url: '/user/registration-config', silentError: true, timeout: 10_000,
          }).then((res) => res.data).finally(() => { pendingConfig = undefined })
        }
        const config = await pendingConfig
        this.apply(config)
        return config
      } finally {
        this.loading = false
      }
    },
  },
})
