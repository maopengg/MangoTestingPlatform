import { post } from '@/api/http'
import type { Response } from '@/api/http'
import { login, register } from '@/api/url'

export function loginAccount(username: string, password: string): Promise<Response<unknown>> {
  return post<unknown>({ url: login, data: { username, password, type: 1 } })
}

export function registerAccount(name: string, email: string): Promise<Response<unknown>> {
  return post<unknown>({ url: register, data: { name, email } })
}

export function resetAccountPassword(email: string): Promise<Response<unknown>> {
  return post<unknown>({ url: '/reset-password', data: { email } })
}
