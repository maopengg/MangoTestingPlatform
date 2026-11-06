import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import test from 'node:test'

const root = new URL('../../', import.meta.url)
const read = path => readFileSync(new URL(path, root), 'utf8')
const config = read('mango-console/nginx/default.conf')
const directives = config.replace(/#.*$/gm, '')

test('static text compression uses bounded cost and negotiates encoding with clients and caches', () => {
  assert.match(directives, /\bgzip\s+on;/)
  assert.match(directives, /\bgzip_vary\s+on;/)
  assert.match(directives, /\bgzip_min_length\s+1024;/)
  assert.match(directives, /\bgzip_comp_level\s+6;/)
  assert.match(directives, /\bgzip_proxied\s+any;/)
})

test('compression includes JS, CSS, JSON and SVG, without binary formats or wildcards', () => {
  const types = directives.match(/\bgzip_types\s+([^;]+);/)[1].trim().split(/\s+/)
  assert.deepEqual(types, ['text/plain', 'text/css', 'text/javascript', 'application/javascript',
    'application/json', 'application/xml', 'text/xml', 'image/svg+xml'])
  assert.doesNotMatch(directives, /gzip_types\s+\*|gzip_static\s+always/)
})

test('existing asset, HTML and runtime configuration cache policies are unchanged', () => {
  assert.match(config, /location \/assets\/\s*\{[^}]*try_files \$uri =404;[^}]*max-age=31536000, immutable/)
  assert.match(config, /location = \/index\.html\s*\{[^}]*no-cache, no-store, must-revalidate/)
  assert.match(config, /location = \/runtime-config\.js\s*\{[^}]*Cache-Control "no-store"/)
})

test('Compose and runtime frontend images both include the same gzip configuration', () => {
  assert.match(read('mango-console/Dockerfile'),
    /COPY mango-console\/nginx\/default\.conf \/etc\/nginx\/conf\.d\/default\.conf/)
  assert.match(read('mango-console/Dockerfile.runtime'),
    /COPY nginx\/default\.conf \/etc\/nginx\/conf\.d\/default\.conf/)
  for (const dockerfile of ['mango-console/Dockerfile', 'mango-console/Dockerfile.runtime']) {
    assert.match(read(dockerfile), /COPY[^\n]+default\.conf\nRUN nginx -t/)
  }
  const compose = JSON.parse(read('deploy/compose.single.json'))
  assert.equal(compose.services['mango-console'].build.dockerfile, 'mango-console/Dockerfile')
  const consoleDeployment = read('deploy/k8s.py').split("elif key=='mango-console':")[1]
    .split("elif key=='mango_gateway':")[0]
  assert.doesNotMatch(consoleDeployment, /\/etc\/nginx\/conf\.d\/default\.conf/)
  assert.match(consoleDeployment, /runtime-config\.js/)
})

test('GitLab frontend build uses the runtime Dockerfile', {
  skip: !existsSync(new URL('.gitlab-ci.yml', root)) && 'this repository has no GitLab pipeline',
}, () => {
  assert.match(read('.gitlab-ci.yml'), /DOCKERFILE_PATH: "mango-console\/Dockerfile\.runtime"/)
})
