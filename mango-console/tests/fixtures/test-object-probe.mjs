import * as Vue from 'vue'
import { compile } from '@vue/compiler-dom/dist/compiler-dom.esm-browser.js'
import Arco, { Modal } from '@arco-design/web-vue'
import '@arco-design/web-vue/dist/arco.css'
import '../../src/styles/index.css'
import source from '../../src/views/config/test-object/components/TestConnectionDialog.vue?raw'
import { applyDisplayDensity, scaleDensityLength } from '../../src/hooks/useDisplayDensity'

applyDisplayDensity('auto')
const style = document.createElement('style')
style.textContent = source.match(/<style scoped>([\s\S]*?)<\/style>/)[1]
  .replace(/:deep\(([^)]+)\)/g, '$1')
  .replace(/\b(\d+(?:\.\d+)?)px\b/g, (match, value) => Number(value) <= 1 ? match : `${Number(value) / 16}rem`)
document.head.append(style)
const template = source.slice(source.indexOf('<template>') + 10, source.indexOf('\n<script')).replace(/<\/template>\s*$/, '')
const state = new URLSearchParams(location.search).get('state') || 'failure'
const host = 'platform-service-api.long-environment-name.example.com'
const result = { connected: state === 'success', message: state === 'success' ? '服务器 DNS 解析及 TCP 端口连接正常。' : '域名解析失败，请检查服务器 DNS 或域名配置。', host,
  port: 80, resolved_ips: state === 'success' ? ['192.0.2.10', '2001:db8::10'] : [], elapsed_ms: 705 }
const noop = () => {}
const context = { options: [{ label: '默认地址', value: `http://${host}` }], address: Vue.ref(`http://${host}`),
  loading: state === 'loading', result: Vue.ref(['empty', 'loading'].includes(state) ? null : result), error: '', runTest: noop, reset: noop, close: noop, clearResult: noop }
const app = Vue.createApp({ setup: () => context, render: new Function('Vue', compile(template).code)(Vue) })
app.use(Arco)
app.component('ModalDialog', Vue.defineComponent({ props: ['title', 'width'], setup(props, { slots }) {
  return () => Vue.h(Modal, { visible: true, title: props.title, width: scaleDensityLength(props.width), maskClosable: false }, {
    default: () => slots.content?.(), footer: () => slots.footer?.(),
  })
} }))
app.mount('#app')
