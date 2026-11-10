import { reactive, ref } from 'vue'
import type { ShallowRef } from 'vue'
import { putFunctionalRequirement, putManualSuite } from '@/api/functional-test'
import {
  createRequirementForm,
  createVersionForm,
  parseRequirement,
  requirementObject,
  requirementId,
  versionFieldPayload,
  versionFormFrom,
} from '../presentation'
import type {
  RequirementFlag,
  RequirementForm,
  RequirementVersion,
  RequirementVersionField,
  RequirementVersionForm,
} from '../types'

type Field = RequirementVersionField | 'requirement'
type Job =
  | {
      kind: 'suite'
      field: RequirementVersionField
      value: RequirementVersionForm[RequirementVersionField]
    }
  | { kind: 'requirement'; id: number; form: RequirementForm }
export function useRequirementSave(options: {
  suite: ShallowRef<RequirementVersion | null>
  form: RequirementVersionForm
  requirementForm: RequirementForm
  getEpoch: () => number
  isCurrent: (epoch: number) => boolean
  canSave: () => boolean
  invalidateRead: () => void
  iterationLabel: (id: number | null) => string
}) {
  const writing = ref(false),
    failed = reactive(new Set<Field>())
  const queue = new Map<Field, Job>()
  let physical: Promise<boolean> | null = null
  function reset() {
    queue.clear()
    failed.clear()
  }
  function run() {
    if (physical) return physical
    if (!options.suite.value || !options.canSave()) return Promise.resolve(false)
    const epoch = options.getEpoch(),
      target = options.suite.value.id
    options.invalidateRead()
    writing.value = true
    physical = (async () => {
      await Promise.resolve()
      let success = true
      try {
        while (options.isCurrent(epoch) && options.suite.value && queue.size) {
          const [key, job] = queue.entries().next().value as [Field, Job]
          queue.delete(key)
          try {
            const previous = options.suite.value
            if (job.kind === 'suite') {
              const data: unknown = (
                await putManualSuite(versionFieldPayload(job.field, job.value, target))
              ).data
              if (!options.isCurrent(epoch) || !options.suite.value) return false
              const ack = requirementObject(data)
              if (
                requirementId(ack.id) !== target ||
                typeof ack.update_time !== 'string' ||
                !(job.field in ack)
              )
                throw Error('保存结果未确认')
              const value = versionFormFrom(ack)[job.field]
              const draft = options.form[job.field]
              if (
                draft === job.value ||
                (typeof job.value === 'boolean' && draft === previous.form[job.field])
              )
                Object.assign(options.form, { [job.field]: value })
              options.suite.value = {
                ...options.suite.value,
                update_time: ack.update_time,
                form: { ...options.suite.value.form, [job.field]: value },
                ...(job.field === 'iteration_ref'
                  ? { iterationName: options.iterationLabel(value as number | null) }
                  : {}),
              }
            } else {
              const data: unknown = (
                await putFunctionalRequirement({ id: job.id, ...createRequirementForm(job.form) })
              ).data
              if (!options.isCurrent(epoch) || !options.suite.value) return false
              const ack = parseRequirement(data)
              if (ack.id !== job.id || options.suite.value.requirement?.id !== job.id)
                throw Error('保存目标未确认')
              for (const field of Object.keys(job.form) as Array<keyof RequirementForm>) {
                if (options.requirementForm[field] === job.form[field])
                  Object.assign(options.requirementForm, { [field]: ack.form[field] })
              }
              options.suite.value = { ...options.suite.value, requirement: ack }
            }
            const pending = queue.get(key)
            if (
              pending &&
              ((pending.kind === 'suite' && job.kind === 'suite' && pending.value === job.value) ||
                (pending.kind === 'requirement' &&
                  job.kind === 'requirement' &&
                  JSON.stringify(pending.form) === JSON.stringify(job.form)))
            )
              queue.delete(key)
            failed.delete(key)
          } catch {
            if (!options.isCurrent(epoch)) return false
            success = false
            queue.delete(key)
            failed.add(key)
          }
        }
        return success
      } finally {
        writing.value = false
        physical = null
      }
    })()
    return physical
  }
  function saveField(field: RequirementVersionField, value = options.form[field]) {
    if (
      !options.suite.value ||
      !options.canSave() ||
      !Object.prototype.hasOwnProperty.call(createVersionForm(), field)
    )
      return Promise.resolve(false)
    if (!writing.value && options.suite.value.form[field] === value) {
      failed.delete(field)
      return Promise.resolve(true)
    }
    queue.set(field, { kind: 'suite', field, value })
    return run()
  }
  function saveRequirement() {
    const requirement = options.suite.value?.requirement
    if (!requirement || !options.canSave()) return Promise.resolve(false)
    const form = createRequirementForm(options.requirementForm)
    if (!writing.value && JSON.stringify(form) === JSON.stringify(requirement.form)) {
      failed.delete('requirement')
      return Promise.resolve(true)
    }
    queue.set('requirement', { kind: 'requirement', id: requirement.id, form })
    return run()
  }
  async function retry() {
    if (!options.canSave() || writing.value) return false
    for (const key of failed) {
      if (key === 'requirement') {
        const requirement = options.suite.value?.requirement
        if (requirement)
          queue.set(key, {
            kind: 'requirement',
            id: requirement.id,
            form: createRequirementForm(options.requirementForm),
          })
      } else queue.set(key, { kind: 'suite', field: key, value: options.form[key] })
    }
    return run()
  }
  async function toggleFlag(field: RequirementFlag) {
    if (!options.canSave() || writing.value) return false
    await saveField(field, !options.form[field])
    return false
  }
  return { writing, failed, saveField, saveRequirement, retry, toggleFlag, reset }
}
