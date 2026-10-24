import useCachedGuard from './cached'
import useFlexMainHeightGuard from './flexMainHeight'
import usePermissionGuard from './permission'
import setupChunkLoadRecovery from '../chunk-load-recovery'
// import useVisitedGuard from './visited'

export default function setupRouterGuard() {
  setupChunkLoadRecovery()
  usePermissionGuard()
  // useVisitedGuard()
  useCachedGuard()
  useFlexMainHeightGuard()
}
