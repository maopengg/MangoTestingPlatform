import useAppConfigStore from '@/store/modules/app-config'
import router from '..'

const fixedHeightRouteNames = ['Home']
const fixedHeightRoutePaths = [
  '/functional-test/case/index',
  '/functional-test/plan/details',
]

function useFlexMainHeightGuard() {
  router.afterEach((to, _from, failure) => {
    if (failure) return
    const appConfigStore = useAppConfigStore()
    appConfigStore.setFlexMainHeight(
      fixedHeightRouteNames.includes(to.name as string) || fixedHeightRoutePaths.includes(to.path)
    )
  })
}

export default useFlexMainHeightGuard
