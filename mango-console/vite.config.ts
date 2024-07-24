import vue from '@vitejs/plugin-vue'
import viteSvgIcons from 'vite-plugin-svg-icons'
import path from 'path'
import { defineConfig } from 'vite'
import dotenv from 'dotenv'
import vueJsx from '@vitejs/plugin-vue-jsx'
// 在正式打包的时候，可以把这两行代码放开
// import Components from 'unplugin-vue-components/vite'
// import { ArcoResolver } from 'unplugin-vue-components/resolvers'
export default defineConfig(({ mode }) => {
  const dotenvConfig = dotenv.config({ path: `./.env.${mode}` })
  const dotenvObj = dotenvConfig.parsed
  console.log(dotenvConfig)
  console.log(dotenvObj)

  return {
    base: dotenvObj?.BUILD_PATH || '/',
    build: {
      outDir: dotenvObj?.BUILD_OUT_DIR || 'dist',
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (id.includes('node_modules')) {
              return id.toString().split('node_modules/')[1].split('/')[0].toString()
            }
          },
        },
      },
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
      alias: [
        {
          find: '@/',
          replacement: path.resolve(process.cwd(), 'src') + '/',
        },
      ],
    },
    server: {
      open: true,
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
