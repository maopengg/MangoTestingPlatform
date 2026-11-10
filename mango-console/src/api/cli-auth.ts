import { post, type Response } from '@/api/http'

export interface CliAuthorizationRequest {
  redirect_uri: string
  state: string
  code_challenge: string
  version: string
}

export interface CliAuthorizationResult {
  code: string
  expires_in: number
}

export function authorizeCli(
  data: CliAuthorizationRequest
): Promise<Response<CliAuthorizationResult>> {
  return post<CliAuthorizationResult>({
    url: '/cli/auth/authorize',
    data: {
      redirect_uri: data.redirect_uri,
      state: data.state,
      code_challenge: data.code_challenge,
      version: data.version,
    },
    silentError: true,
  })
}
