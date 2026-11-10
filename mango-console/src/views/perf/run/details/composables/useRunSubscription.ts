import { ref } from 'vue'
import { subscribePerfRun, unsubscribePerfRun } from '@/api/perf'
import { runData } from '../records'
import type { RunContext, RunIdentity } from '../types'

const sameIdentity = (a: RunIdentity, b: RunIdentity) => a.userId === b.userId && a.roleId === b.roleId && a.token === b.token && a.environment === b.environment

export function useRunSubscription(identity: () => RunIdentity) {
  const subscriptionError = ref('')
  let desired: RunContext | null = null, lease: RunContext | null = null
  let worker: Promise<void> | null = null
  let timer: ReturnType<typeof setTimeout> | undefined
  let renew = false, disposed = false
  const clearTimer = () => { if (timer !== undefined) clearTimeout(timer); timer = undefined }
  const needsCleanup = () => lease && (!desired?.isCurrent() || desired.epoch !== lease.epoch || desired.id !== lease.id || !sameIdentity(desired.identity, lease.identity))

  function kick() {
    if (worker) return
    let failed: RunContext | null = null
    worker = Promise.resolve().then(async () => {
      clearTimer()
      while (true) {
        if (needsCleanup()) {
          const previous = lease!
          lease = null
          // Identity changes leave the old user lease to the server's 60-second TTL.
          if (sameIdentity(previous.identity, identity())) {
            try { await unsubscribePerfRun(previous.id, previous.identity.token) } catch { /* The server TTL still expires this lease. */ }
          }
          continue
        }
        const target = desired
        if (!target?.isCurrent()) { desired = null; break }
        if (lease && !renew) break
        renew = false
        lease = target
        try {
          runData(await subscribePerfRun(target.id, target.identity.token))
          if (target.isCurrent()) subscriptionError.value = ''
        } catch {
          if (target.isCurrent()) subscriptionError.value = '实时推送暂不可用，数据继续每 5 秒更新'
          if (target === desired && target.isCurrent()) { failed = target; break }
        }
      }
    }).finally(() => {
      worker = null
      if (needsCleanup() || (desired?.isCurrent() && desired !== failed && (!lease || renew))) kick()
      else if (!disposed && desired?.isCurrent()) timer = setTimeout(() => { timer = undefined; renew = true; kick() }, 30000)
    })
  }

  function resume(context: RunContext) {
    if (disposed || !context.isCurrent()) return
    clearTimer()
    desired = context
    kick()
  }
  function pause() {
    clearTimer()
    desired = null
    subscriptionError.value = ''
    kick()
  }
  function dispose() { disposed = true; pause() }

  return { subscriptionError, resume, pause, dispose }
}
