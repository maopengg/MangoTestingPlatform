import vue from '@vitejs/plugin-vue'
import viteSvgIcons from 'vite-plugin-svg-icons'
import path from 'path'
import { defineConfig } from 'vite'
import dotenv from 'dotenv'
import vueJsx from '@vitejs/plugin-vue-jsx'

const univerDependencies = [
  '@univerjs/presets',
  '@univerjs/preset-sheets-core',
  '@univerjs/preset-sheets-core/locales/zh-CN',
  '@univerjs/preset-sheets-data-validation',
  '@univerjs/preset-sheets-data-validation/locales/zh-CN',
  '@univerjs/preset-sheets-filter',
  '@univerjs/preset-sheets-filter/locales/zh-CN',
  '@univerjs/preset-sheets-sort',
  '@univerjs/preset-sheets-sort/locales/zh-CN',
  '@univerjs/preset-sheets-find-replace',
  '@univerjs/preset-sheets-find-replace/locales/zh-CN',
  '@univerjs/preset-sheets-conditional-formatting',
  '@univerjs/preset-sheets-conditional-formatting/locales/zh-CN',
  '@univerjs/preset-sheets-hyper-link',
  '@univerjs/preset-sheets-hyper-link/locales/zh-CN',
]
// 在正式打包的时候，可以把这两行代码放开
// import Components from 'unplugin-vue-components/vite'
// import { ArcoResolver } from 'unplugin-vue-components/resolvers'
export default defineConfig(({ mode }) => {
  const dotenvConfig = dotenv.config({ path: `./.env.${mode}` })
  const dotenvObj = dotenvConfig.parsed
  return {
    base: dotenvObj?.BUILD_PATH || '/',
    define: {
      __VUE_OPTIONS_API__: true,
      __VUE_PROD_DEVTOOLS__: false,
      __VUE_PROD_HYDRATION_MISMATCH_DETAILS__: false,
    },
    build: {
      outDir: dotenvObj?.BUILD_OUT_DIR || 'dist',
      // 项目包含 Univer、编辑器等大型依赖。按 npm 包逐个拆 chunk 会在 Rollup
      // 渲染阶段同时维护数百个 chunk，显著放大 CI 构建的内存峰值。
      // 保留路由动态导入形成的自然分包，并跳过仅用于提示的 gzip 体积统计。
      reportCompressedSize: false,
    },
    plugins: [
      vue(),
      viteSvgIcons({
        iconDirs: [path.resolve(process.cwd(), 'src/icons')],
        symbolId: 'icon-[dir]-[name]',
      }),
      vueJsx(),
      // 在正式打包的时候，可以把这三行代码放开
      // Components({
      //   resolvers: [ArcoResolver()],
      // }),
    ],
    css: {
      preprocessorOptions: {
        less: {
          additionalData: `@import "src/styles/variables.less";`,
          modifyVars: {},
          javascriptEnabled: true,
        },
      },
    },
    resolve: {
      // Univer 的依赖注入标识依赖模块单例。统一解析入口，避免混用 npm/pnpm
      // 或 Vite 分批预构建时生成多份 redi/core，导致 ConfigService 无法注入。
      dedupe: [
        '@wendellhu/redi',
        '@univerjs/core',
        '@univerjs/data-validation',
        '@univerjs/docs',
        '@univerjs/docs-ui',
        '@univerjs/engine-formula',
        '@univerjs/engine-render',
        '@univerjs/sheets',
        '@univerjs/sheets-data-validation',
        '@univerjs/sheets-ui',
        '@univerjs/ui',
        'react',
        'react-dom',
        'rxjs',
      ],
      alias: [
        ...['core', 'data-validation', 'filter'].map((name) => ({
          find: `@univerjs/preset-sheets-${name}/lib/index.css`,
          replacement: path.resolve(
            process.cwd(),
            `node_modules/@univerjs/preset-sheets-${name}/lib/index.css`
          ),
        })),
        {
          find: '@/',
          replacement: path.resolve(process.cwd(), 'src') + '/',
        },
      ],
    },
    optimizeDeps: {
      include: univerDependencies,
    },
    server: {
      open: process.env.MANGO_VITE_AUTO_OPEN !== 'false',
      // proxy:{
      //   '/api':{//表示拦截以/api开头的请求路径
      //     target:'http://localhost:8000/',
      //     changOrigin: true,//是否开启跨域
      //     pathRewrite:{
      //       '^/api':'' //重写api，把api变成空字符，因为我们真正请求的路径是没有api的
      //     }
      //   }
    },
    // optimizeDeps: {
    //   include: [
    //     'vue',
    //     'lodash',
    //     '@arco-design/web-vue',
    //     '@arco-design/web-vue/es/icon',
    //     'pinia',
    //     'vue-router',
    //   ],
    // },
  }
})
