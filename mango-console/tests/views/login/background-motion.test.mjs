import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'

const source = readFileSync(new URL('../../../src/views/login/background-motion.ts', import.meta.url), 'utf8')
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
})

function harness({ hidden = false, reduced = false } = {}) {
  const document = Object.assign(new EventTarget(), { hidden })
  const preference = Object.assign(new EventTarget(), { matches: reduced })
  const window = Object.assign(new EventTarget(), { matchMedia: () => preference })
  const animations = []
  const track = Object.assign(new EventTarget(), {
    animate(frames, options) {
      const animation = {
        frames, options, currentTime: 0, playState: 'running',
        play() { this.playState = 'running' },
        pause() { this.playState = 'paused' },
        cancel() { this.playState = 'idle' },
      }
      animations.push(animation)
      return animation
    },
  })
  const exports = {}
  new Function('exports', 'window', 'document', outputText)(exports, window, document)
  const start = () => exports.startLoginBackgroundMotion(track)
  return { document, window, preference, track, animations, start }
}

test('starts an infinite background loop on each login page mount and disposes on exit', () => {
  const h = harness()
  const stop = h.start()
  assert.equal(h.animations[0].options.duration, 160_000)
  assert.equal(h.animations[0].options.iterations, Infinity)
  stop()
  assert.equal(h.animations[0].playState, 'idle')
  h.start()()
  assert.equal(h.animations.length, 2)
})

test('pauses while hidden and rebuilds at the same progress when visible', () => {
  const h = harness()
  const stop = h.start()
  h.animations[0].currentTime = 12345
  h.document.hidden = true
  h.document.dispatchEvent(new Event('visibilitychange'))
  assert.equal(h.animations[0].playState, 'paused')
  h.document.hidden = false
  h.document.dispatchEvent(new Event('visibilitychange'))
  assert.equal(h.animations[1].currentTime, 12345)
  assert.equal(h.animations[1].playState, 'running')
  stop()
})

test('image loading and page-cache restoration restart the compositor without losing progress', () => {
  const h = harness()
  const stop = h.start()
  h.animations[0].currentTime = 9000
  h.track.dispatchEvent(new Event('load'))
  h.window.dispatchEvent(new Event('pageshow'))
  assert.equal(h.animations.length, 3)
  assert.equal(h.animations[2].currentTime, 9000)
  stop()
})

test('respects reduced motion, including live preference changes', () => {
  const h = harness({ reduced: true })
  const stop = h.start()
  assert.equal(h.animations.length, 0)
  h.preference.matches = false
  h.preference.dispatchEvent(new Event('change'))
  assert.equal(h.animations[0].playState, 'running')
  h.preference.matches = true
  h.preference.dispatchEvent(new Event('change'))
  assert.equal(h.animations[0].playState, 'idle')
  stop()
})

test('unmount removes every listener so later events cannot create orphan animations', () => {
  const h = harness()
  h.start()()
  for (const [target, event] of [[h.window, 'pageshow'], [h.document, 'visibilitychange'], [h.track, 'load'], [h.preference, 'change']]) {
    target.dispatchEvent(new Event(event))
  }
  assert.equal(h.animations.length, 1)
})
