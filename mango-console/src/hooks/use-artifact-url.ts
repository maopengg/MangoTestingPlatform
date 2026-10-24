import { type ComputedRef, ref, watch } from 'vue'
import { getExecutionArtifactDownloadUrl } from '@/api/system/file_data'
import { baseURL, minioURL } from '@/api/axios.config'

export function resolveBackendArtifactUrl(value: string) {
  const url = String(value || '').trim()
  if (!url || /^[a-z][a-z\d+.-]*:/i.test(url) || url.startsWith('//')) {
    return url
  }
  if (typeof window === 'undefined') {
    return url
  }
  try {
    const apiOrigin = new URL(baseURL || '/', window.location.origin).origin
    return new URL(url.startsWith('/') ? url : `/${url}`, apiOrigin).toString()
  } catch (_error) {
    return url
  }
}

export function useArtifactUrl(path: ComputedRef<string>) {
  const artifactUrl = ref('')
  let requestId = 0

  watch(
    path,
    async (value) => {
      const currentRequestId = ++requestId
      artifactUrl.value = ''
      if (!value) return
      if (/^https?:\/\//i.test(value)) {
        artifactUrl.value = value
        return
      }
      try {
        const response = await getExecutionArtifactDownloadUrl(value)
        if (currentRequestId === requestId) {
          artifactUrl.value = response.data
            ? resolveBackendArtifactUrl(response.data)
            : legacyArtifactUrl(value)
        }
      } catch (_error) {
        if (currentRequestId === requestId) {
          artifactUrl.value = legacyArtifactUrl(value)
        }
      }
    },
    { immediate: true }
  )

  return artifactUrl
}

function legacyArtifactUrl(path: string) {
  if (/^\/?mango-file\//i.test(path)) {
    return resolveBackendArtifactUrl(path)
  }
  return `${String(minioURL || '').replace(/\/$/, '')}/${path.replace(/^\//, '')}`
}
