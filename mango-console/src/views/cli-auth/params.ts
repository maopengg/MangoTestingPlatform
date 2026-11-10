import type { CliAuthorizationRequest, CliAuthorizationResult } from '@/api/cli-auth'
import { authorizationMessages, callbackPolicy } from './config'

export function validatedCallback(value: string): URL | null {
  try {
    const url = new URL(value)
    if (
      url.protocol !== callbackPolicy.protocol ||
      url.hostname !== callbackPolicy.hostname ||
      url.pathname !== callbackPolicy.pathname
    )
      return null
    if (!url.port || url.username || url.password || url.search || url.hash) return null
    return url
  } catch {
    return null
  }
}

export function authorizationParams(
  query: Record<string, unknown>
): CliAuthorizationRequest | null {
  const value = (key: string) => {
    const item = query[key]
    return typeof item === 'string' ? item : ''
  }
  const data = {
    redirect_uri: value('redirect_uri'),
    state: value('state'),
    code_challenge: value('code_challenge'),
    version: value('version'),
  }
  return validatedCallback(data.redirect_uri) && data.state && data.code_challenge && data.version
    ? data
    : null
}

export function isAuthorizationResult(value: unknown): value is CliAuthorizationResult {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false
  return (
    'code' in value &&
    typeof value.code === 'string' &&
    value.code.length > 0 &&
    'expires_in' in value &&
    typeof value.expires_in === 'number' &&
    Number.isInteger(value.expires_in) &&
    value.expires_in > 0
  )
}

export function authorizationErrorMessage(error: unknown): string {
  if (
    error &&
    typeof error === 'object' &&
    'message' in error &&
    typeof error.message === 'string' &&
    error.message
  )
    return error.message
  return authorizationMessages.failed
}
