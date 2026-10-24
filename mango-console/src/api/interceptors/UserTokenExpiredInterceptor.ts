import { AxiosResponse } from 'axios'
import { handleAuthExpired, isAuthExpiredResponse } from '../auth-expired'

export default function (response: AxiosResponse): AxiosResponse {
  const data = response.data || {}
  if (isAuthExpiredResponse(response.status, data.code, data.msg)) {
    handleAuthExpired(data.msg)
  }
  return response
}
