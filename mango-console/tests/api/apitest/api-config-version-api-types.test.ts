import {
  getApiConfigVersionDetail,
  getApiConfigVersionList,
} from '../../../src/api/apitest/config-version'

export interface AxiosRequestConfig {
  headers?: Record<string, string>
}

export interface AxiosResponse<T = any> {
  data: T
  status: number
}

declare const Axios: {
  create(config?: unknown): any
}

export default Axios

type IsAny<T> = 0 extends 1 & T ? true : false
type AssertFalse<T extends false> = T

type ApiConfigVersionListData = Awaited<
  ReturnType<typeof getApiConfigVersionList>
>['data']
type ApiConfigVersionDetailData = Awaited<
  ReturnType<typeof getApiConfigVersionDetail>
>['data']

type ApiConfigVersionListDataIsTyped = AssertFalse<IsAny<ApiConfigVersionListData>>
type ApiConfigVersionDetailDataIsTyped = AssertFalse<IsAny<ApiConfigVersionDetailData>>

export {}
