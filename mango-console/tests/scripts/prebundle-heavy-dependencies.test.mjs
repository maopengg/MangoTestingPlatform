import assert from 'node:assert/strict'
import test from 'node:test'
import esbuild from 'esbuild'
import { rollup } from 'rollup'
import { prebundleHeavyDependencies } from '../../scripts/prebundle-heavy-dependencies.mjs'

async function fixture(base = '/') {
  const assets = [], errors = [], options = []
  const plugin = prebundleHeavyDependencies(async value => {
    options.push(value)
    return { outputFiles: [...Object.keys(value.entryPoints).map(name => `${name}-${name === 'mermaid' ? 'BBB' : 'AAA'}.js`), 'shared-DDD.js']
      .map(name => ({ path: `/workspace/.mango-heavy-output/${name}`, contents: Buffer.from(`export const value = ${JSON.stringify(name)};`) })) }
  })
  plugin.configResolved({ root: '/workspace', base, build: { assetsDir: 'assets', minify: 'esbuild' }, logger: { info() {} } })
  await plugin.buildStart.call({ emitFile(asset) { assets.push(asset) }, error(error) { errors.push(error); throw Error(error) } })
  return { plugin, assets, errors, options }
}

test('large dependencies stay in one esbuild graph and leave the Rollup graph through validated entry wrappers', async () => {
  const { plugin, assets, options } = await fixture()
  assert.equal(plugin.apply, 'build')
  assert.equal(options[0].entryPoints['echarts-core'], 'echarts/core')
  assert.equal(options[0].entryPoints['codemirror-state'], '@codemirror/state')
  assert.equal(options[0].entryPoints['codemirror-view'], '@codemirror/view')
  assert.equal(options[0].entryPoints['lezer-highlight'], '@lezer/highlight')
  assert.equal(options[0].splitting, true)
  assert.equal(options[0].write, false)
  assert.equal(options[0].define['process.env.NODE_ENV'], '"production"')
  assert.equal(assets.length, Object.keys(options[0].entryPoints).length + 1)
  assert.equal(new Set(assets.map(asset => asset.fileName.split('/')[1])).size, 1)
  for (const source of ['@/plugins/univer-sheets', '/workspace/src/plugins/univer-sheets.js', 'C:\\workspace\\src\\plugins\\univer-sheets.js', 'mermaid', 'xlsx', 'echarts', 'echarts/core', 'echarts/charts', 'echarts/components', 'echarts/renderers', 'codemirror', '@codemirror/state', '@codemirror/view', '@lezer/highlight']) {
    const id = plugin.resolveId(source)
    const code = plugin.load(id)
    await esbuild.transform(code, { loader: 'js' })
    const url = code.match(/from "([^"]+)"/)[1]
    assert.equal(plugin.resolveId(url).external, 'absolute')
    assert.ok(assets.some(asset => `/${asset.fileName}` === url))
  }
  const sheet = plugin.load(plugin.resolveId('@/plugins/univer-sheets'))
  assert.match(sheet, /preset-sheets-core\/lib\/index.css/)
  assert.match(sheet, /preset-sheets-data-validation\/lib\/index.css/)
  assert.match(sheet, /preset-sheets-filter\/lib\/index.css/)
  assert.match(sheet, /export \{ createFunctionalSheet \}/)
  assert.match(plugin.load(plugin.resolveId('mermaid')), /export \{ default \}/)
  assert.match(plugin.load(plugin.resolveId('xlsx')), /export \*/)
})

test('entry URLs support deployment prefixes and relative base paths without double assets segments', async () => {
  for (const base of ['/console/', './']) {
    const { plugin, assets } = await fixture(base)
    const code = plugin.load(plugin.resolveId('mermaid'))
    const url = code.match(/from "([^"]+)"/)[1]
    assert.equal(plugin.resolveId(url).external, base === './' ? true : 'absolute')
    assert.equal(url, base === './' ? `./${assets[1].fileName.split('/').slice(1).join('/')}` : `${base}${assets[1].fileName}`)
  }
})

test('Rollup preserves browser asset URLs when generating nested route chunks', async () => {
  const { plugin } = await fixture('/console/')
  const bundle = await rollup({
    input: 'mermaid',
    plugins: [{ resolveId: plugin.resolveId, load: plugin.load }],
  })
  try {
    const { output } = await bundle.generate({ format: 'es', entryFileNames: 'assets/route.js' })
    assert.match(output[0].code, /from ['"]\/console\/assets\/heavy-[^'"]+\/mermaid-BBB\.js['"]/)
    assert.doesNotMatch(output[0].code, /\.\.\//)
  } finally {
    await bundle.close()
  }
})
