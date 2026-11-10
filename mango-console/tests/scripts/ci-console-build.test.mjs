import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { createRequire } from 'node:module'
import test from 'node:test'

const require = createRequire(import.meta.url)
const yaml = require('js-yaml')
const script = path.resolve('scripts/ci-console-build.sh')

function run(t, { cached = false, installExit = 0, buildExit = 0, registry } = {}) {
  const cwd = fs.mkdtempSync(path.join(os.tmpdir(), 'mango-ci-timing-'))
  t.after(() => fs.rmSync(cwd, { recursive: true, force: true }))
  fs.mkdirSync(path.join(cwd, 'bin'))
  fs.writeFileSync(path.join(cwd, 'bin/npm'), `#!/bin/sh
printf '%s|%s\\n' "$*" "\${npm_config_registry:-project}" >> npm-calls
case "$1" in
  ci) exit "\${INSTALL_EXIT:-0}" ;;
  run) exit "\${BUILD_EXIT:-0}" ;;
esac
`, { mode: 0o755 })
  if (cached) {
    fs.mkdirSync(path.join(cwd, 'node_modules/.bin'), { recursive: true })
    fs.writeFileSync(path.join(cwd, 'node_modules/.package-lock.json'), '{}')
    fs.writeFileSync(path.join(cwd, 'node_modules/.bin/vite'), '', { mode: 0o755 })
  }
  const env = { ...process.env, PATH: `${cwd}/bin:${process.env.PATH}`, INSTALL_EXIT: String(installExit), BUILD_EXIT: String(buildExit) }
  delete env.NPM_REGISTRY
  delete env.npm_config_registry
  if (registry) env.NPM_REGISTRY = registry
  const result = spawnSync('sh', [script, 'all', 'dev'], { cwd, env, encoding: 'utf8' })
  return { ...result, calls: fs.readFileSync(path.join(cwd, 'npm-calls'), 'utf8') }
}

test('cold install uses download cache and prints both successful stage durations', t => {
  const result = run(t)
  assert.equal(result.status, 0)
  assert.match(result.calls, /ci --cache \.npm --prefer-offline --no-audit --no-fund --timing/)
  assert.match(result.calls, /run build:dev/)
  assert.match(result.stdout, /依赖准备（缓存检查\/安装）耗时：\d+ 秒（退出码 0）/)
  assert.match(result.stdout, /前端打包耗时：\d+ 秒（退出码 0）/)
})

test('warm node_modules cache skips installation and supports an explicit registry', t => {
  const result = run(t, { cached: true, registry: 'https://example.com/npm/' })
  assert.equal(result.status, 0)
  assert.doesNotMatch(result.calls, /^ci /m)
  assert.match(result.calls, /run build:dev\|https:\/\/example.com\/npm\//)
  assert.match(result.stdout, /复用 node_modules 缓存/)
})

test('install failure prints duration, preserves exit status and never starts the build', t => {
  const result = run(t, { installExit: 17 })
  assert.equal(result.status, 17)
  assert.match(result.stdout, /依赖准备（缓存检查\/安装）耗时：\d+ 秒（退出码 17）/)
  assert.doesNotMatch(result.calls, /run build/)
})

test('build failure prints duration and preserves exit status', t => {
  const result = run(t, { buildExit: 23 })
  assert.equal(result.status, 23)
  assert.match(result.stdout, /前端打包耗时：\d+ 秒（退出码 23）/)
})

test('download cache is independent of lockfile and cached even after a failed job', t => {
  if (!fs.existsSync('../.gitlab-ci.yml')) {
    t.skip('此仓库不包含 GitLab 流水线；安装和构建脚本由其他测试覆盖')
    return
  }
  const job = yaml.load(fs.readFileSync('../.gitlab-ci.yml', 'utf8'))['build-console-dist']
  assert.equal(job.variables.NODE_OPTIONS, '--max-old-space-size=4096')
  assert.deepEqual(job.cache[0].key.files, ['mango-console/package.json', 'mango-console/package-lock.json'])
  assert.equal(typeof job.cache[1].key, 'string')
  assert.deepEqual(job.cache[1].paths, ['mango-console/.npm/_cacache/'])
  assert.equal(job.cache[1].when, 'always')
  assert.ok(job.script.includes('sh scripts/ci-console-build.sh all "$VUE_ENV"'))
})

test('lockfile matches the manifest and uses public registry URLs with integrity checks', () => {
  const after = JSON.parse(fs.readFileSync('package-lock.json', 'utf8'))
  const manifest = JSON.parse(fs.readFileSync('package.json', 'utf8'))
  assert.equal(after.version, manifest.version)
  assert.deepEqual(after.packages[''].dependencies, manifest.dependencies)
  assert.deepEqual(after.packages[''].devDependencies, manifest.devDependencies)
  for (const pkg of Object.values(after.packages)) {
    if (!pkg.resolved) continue
    assert.equal(new URL(pkg.resolved).origin, 'https://registry.npmjs.org')
    assert.match(pkg.integrity, /^sha(?:512|256|1)-/)
  }
  const registry = fs.readFileSync('.npmrc', 'utf8').trim().slice('registry='.length)
  assert.ok(fs.readFileSync('Dockerfile', 'utf8').includes(`ARG NPM_REGISTRY=${registry}`))
  assert.ok(fs.readFileSync('../.env.example', 'utf8').includes(`NPM_REGISTRY=${registry}`))
  assert.ok(fs.readFileSync('../deploy/defaults.env', 'utf8').includes(`NPM_REGISTRY=${registry}`))
  assert.ok(fs.readFileSync('../deploy/compose.single.json', 'utf8').includes(`NPM_REGISTRY:-${registry}`))
})
