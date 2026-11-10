import path from 'node:path'
import { createHash } from 'node:crypto'
import esbuild from 'esbuild'

const virtualPrefix = '\0mango:heavy:'
const packages = {
  mermaid: 'mermaid',
  xlsx: 'xlsx',
  echarts: 'echarts',
  'echarts-core': 'echarts/core',
  'echarts-charts': 'echarts/charts',
  'echarts-components': 'echarts/components',
  'echarts-renderers': 'echarts/renderers',
  codemirror: 'codemirror',
  ...Object.fromEntries([
    'autocomplete', 'commands', 'lang-javascript', 'lang-json', 'lang-markdown',
    'lang-python', 'language', 'language-data', 'lint', 'search', 'state',
    'theme-one-dark', 'view',
  ].map(name => [`codemirror-${name}`, `@codemirror/${name}`])),
  'lezer-highlight': '@lezer/highlight',
}
const styles = [
  '@univerjs/preset-sheets-core/lib/index.css',
  '@univerjs/preset-sheets-data-validation/lib/index.css',
  '@univerjs/preset-sheets-filter/lib/index.css',
]

// 大型纯 JS 依赖由 esbuild 单独处理，避免 Rollup 保留其整棵语法树及渲染状态。
// 每套依赖的入口共享模块图，保持 Univer 注入标识、ECharts 注册表和 CodeMirror 类型单例。
export function prebundleHeavyDependencies(bundle = esbuild.build) {
  let config
  const entries = new Map()
  return {
    name: 'mango-prebundle-heavy-dependencies',
    apply: 'build',
    enforce: 'pre',
    configResolved(value) { config = value },
    async buildStart() {
      entries.clear()
      const result = await bundle({
        absWorkingDir: config.root,
        entryPoints: {
          'univer-sheets': path.resolve(config.root, 'src/plugins/univer-sheets.js'),
          ...packages,
        },
        outdir: path.resolve(config.root, '.mango-heavy-output'),
        bundle: true,
        format: 'esm',
        platform: 'browser',
        target: ['es2020'],
        splitting: true,
        minify: config.build.minify !== false,
        sourcemap: false,
        write: false,
        entryNames: '[name]-[hash]',
        chunkNames: 'shared-[hash]',
        define: { 'process.env.NODE_ENV': JSON.stringify('production') },
        plugins: [{
          name: 'univer-css-via-vite',
          setup(build) {
            // CSS 继续由 Vite 处理相对 URL、主题资源和按需加载。
            build.onLoad({ filter: /\.css$/ }, () => ({ contents: '', loader: 'js' }))
          },
        }],
      })
      const directoryHash = createHash('sha256')
      for (const file of result.outputFiles) directoryHash.update(file.contents)
      const directory = `${config.build.assetsDir}/heavy-${directoryHash.digest('hex').slice(0, 12)}`
      for (const file of result.outputFiles) {
        const name = path.basename(file.path)
        this.emitFile({ type: 'asset', fileName: `${directory}/${name}`, source: file.contents })
        for (const entry of ['univer-sheets', ...Object.keys(packages)]) {
          if (new RegExp(`^${entry}-[A-Z0-9]+\\.js$`).test(name)) entries.set(entry,
            config.base === './' || config.base === ''
              ? `./${path.posix.basename(directory)}/${name}`
              : `${config.base}${directory}/${name}`)
        }
      }
      if (entries.size !== Object.keys(packages).length + 1) this.error('大型依赖预构建未生成全部入口文件')
      config.logger.info(`大型依赖预构建完成：${result.outputFiles.length} 个静态文件`)
    },
    resolveId(id) {
      if (id.startsWith(virtualPrefix)) return id
      if (id === '@/plugins/univer-sheets' || id.replace(/\\/g, '/').replace(/\.js$/, '').endsWith('/src/plugins/univer-sheets')) return `${virtualPrefix}univer-sheets`
      const entry = Object.entries(packages).find(([, source]) => source === id)
      if (entry) return virtualPrefix + entry[0]
      // 部署前缀是浏览器 URL，不能让 Rollup 当作文件系统绝对路径重新相对化。
      if ([...entries.values()].includes(id)) return { id, external: id.startsWith('.') ? true : 'absolute' }
    },
    load(id) {
      if (!id.startsWith(virtualPrefix)) return
      const entry = id.slice(virtualPrefix.length), url = JSON.stringify(entries.get(entry))
      if (entry === 'mermaid') return `export { default } from ${url};`
      if (entry !== 'univer-sheets') return `export * from ${url};`
      return [...styles.map(style => 'import ' + JSON.stringify(style) + ';'), 'export { createFunctionalSheet } from ' + url + ';'].join("\n")
    },
  }
}
