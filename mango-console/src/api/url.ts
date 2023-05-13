import { baseURL } from './axios.config'

export const baseAddress = baseURL

// 项目原始接口
export const updateUserInfo = '/updateUser'
export const deleteUserById = '/deleteUserById'
export const addDepartment = '/addDepartment'
export const getParentMenuList = '/getParentMenuList'
export const getCardList = '/getCardList'
export const getCommentList = '/getCommentList'
export const addUserInfo = '/addUser'

// 修改原始接口后的
export const login = '/login'
export const getMenuListByRoleId = '/menu/'

export const getAllMenuByRoleId = '/role'
export const getMenuList = '/menu_1'
export const test = '/testconfig/test'
// -
export const getDepartmentList = '/user/project'
export const getRoleList = '/user/role'
export const getAllRole = '/user/role/all'

export const getUserList = '/user/user'
export const getAllItems = '/user/project/all'
export const getNickname = '/user/get/nickname/'

// -
export const ApiCase = '/api/case'
export const ApiCaseGroup = '/api/case/group'
export const ApiPublic = '/api/public'
export const GetHeader = '/api/public/header'
export const ApiRelyOn = '/api/relyon'
export const ApiPublicEnd = '/api/public/end'
export const ApiPublicPublic = '/api/public/public'
export const ApiRun = '/api/run'
export const ApiCaseSynchronous = '/api/case/synchronous'

// -
export const uiPage = '/ui/page'
export const uiPageQuery = '/ui/page/query'
export const uiPageName = '/ui/page/name'
export const uiUiElement = '/ui/element'
export const uiUiElementName = '/ui/element/name'
export const getUiElementExp = '/ui/element/exp'
export const uiCase = '/ui/case'
export const uiCasePutType = '/ui/case/put/type'
export const uiCaseGroup = '/ui/case/group'
export const uiRunSort = '/ui/runsort'
export const uiRunSortAss = '/ui/runsort/ass'
export const uiRunSortOpe = '/ui/runsort/ope'
export const UiRun = '/ui/run'
export const uiRunCaseGroup = '/ui/run/group'
export const uiRunCaseGroupBatch = '/ui/run/group/batch'

// -
export const getProjectConfig = '/system/test/object'
export const getEnvironmentEnum = '/system/get/environment/enum'
export const getTestObjName = '/system/get/test/obj/name'
export const getPlatformEnum = '/system/get/platform/enum'
export const getNoticeConfig = '/system/notice'
export const getNoticeType = '/system/notice/type'
export const getDatabase = '/system/database'
export const getRandomList = 'system/variable/random/list'
export const getRandomData = 'system/variable/value'
export const getTimeList = 'system/time'
export const getTimeData = 'system/time/data'
export const triggerTiming = 'system/trigger/timing'

declare module '@vue/runtime-core' {
  interface ComponentCustomProperties {
    $urlPath: Record<string, string>
  }
}
