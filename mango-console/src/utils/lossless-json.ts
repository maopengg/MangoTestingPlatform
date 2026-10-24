import { parseTree, type Node, type ParseError } from 'jsonc-parser'

const LOSSLESS_NUMBER_MARKER = Symbol.for('mango.lossless-json-number')

export class LosslessJsonNumber {
  readonly [LOSSLESS_NUMBER_MARKER] = true

  constructor(readonly value: string) {}

  toString() {
    return this.value
  }

  valueOf() {
    return this.value
  }
}

export function isLosslessJsonNumber(value: unknown): value is LosslessJsonNumber {
  return Boolean(
    value &&
      typeof value === 'object' &&
      (value as LosslessJsonNumber)[LOSSLESS_NUMBER_MARKER]
  )
}

type PreserveNumber = (path: Array<string | number>) => boolean

function nodeValue(
  node: Node,
  source: string,
  path: Array<string | number>,
  preserveNumber: PreserveNumber
): any {
  if (node.type === 'object') {
    const result: Record<string, any> = {}
    ;(node.children || []).forEach((property) => {
      const keyNode = property.children?.[0]
      const valueNode = property.children?.[1]
      if (keyNode && valueNode) {
        const key = String(keyNode.value)
        result[key] = nodeValue(valueNode, source, [...path, key], preserveNumber)
      }
    })
    return result
  }
  if (node.type === 'array') {
    return (node.children || []).map((child, index) =>
      nodeValue(child, source, [...path, index], preserveNumber)
    )
  }
  if (node.type === 'number') {
    const rawValue = source.slice(node.offset, node.offset + node.length)
    const numericValue = Number(rawValue)
    if (
      Number.isInteger(numericValue) &&
      !Number.isSafeInteger(numericValue) &&
      preserveNumber(path)
    ) {
      return new LosslessJsonNumber(rawValue)
    }
    return numericValue
  }
  return node.value
}

function parseJson(source: string, preserveNumber: PreserveNumber): any {
  const errors: ParseError[] = []
  const node = parseTree(source, errors, {
    allowTrailingComma: false,
    disallowComments: true,
  })
  if (!node || errors.length) {
    throw new SyntaxError('JSON格式不合法')
  }
  return nodeValue(node, source, [], preserveNumber)
}

export function parseLosslessJson(source: string): any {
  return parseJson(source, () => true)
}

export function parseApiConfigLosslessJson(source: string): any {
  return parseJson(source, (path) => path.includes('body_config'))
}

export function stringifyLosslessJson(value: unknown, space?: number): string {
  const rawValues: string[] = []
  const marker = `__mango_lossless_${Date.now()}_${Math.random().toString(36).slice(2)}_`
  const serialized = JSON.stringify(
    value,
    (_key, item) => {
      if (!isLosslessJsonNumber(item)) return item
      const index = rawValues.push(item.value) - 1
      return `${marker}${index}__`
    },
    space
  )
  if (serialized === undefined) return ''
  const escapedMarker = marker.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  return serialized.replace(
    new RegExp(`"${escapedMarker}(\\d+)__"`, 'g'),
    (_matched, index) => rawValues[Number(index)]
  )
}

export function containsLosslessJsonNumber(value: unknown, seen = new WeakSet<object>()): boolean {
  if (isLosslessJsonNumber(value)) return true
  if (!value || typeof value !== 'object') return false
  if (seen.has(value)) return false
  seen.add(value)
  return Object.values(value).some((item) => containsLosslessJsonNumber(item, seen))
}

export function cloneLosslessJson<T>(value: T, seen = new WeakMap<object, any>()): T {
  if (isLosslessJsonNumber(value)) {
    return new LosslessJsonNumber(value.value) as T
  }
  if (!value || typeof value !== 'object') return value
  if (seen.has(value)) return seen.get(value)
  const result: any = Array.isArray(value) ? [] : {}
  seen.set(value, result)
  Object.entries(value).forEach(([key, item]) => {
    result[key] = cloneLosslessJson(item, seen)
  })
  return result
}
