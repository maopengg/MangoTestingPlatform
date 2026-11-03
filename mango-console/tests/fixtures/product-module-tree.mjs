import { createApp, h, ref } from 'vue'
import Arco from '@arco-design/web-vue'
import '@arco-design/web-vue/dist/arco.css'
import '../../src/styles/index.css'
import ModuleTree from '../../src/views/config/product/module/ModuleTree.vue'
import { applyDisplayDensity } from '../../src/hooks/useDisplayDensity'

applyDisplayDensity('auto')
const records = []
for (let i = 1; i <= 4; i++) {
  const root = { id: i * 100, name: `业务分类 ${i}`, level: 1 }
  const parent = { id: i * 100 + 1, name: `服务模块 ${i}`, level: 2, parent: root }
  records.push(root, parent)
  for (let j = 2; j <= 7; j++) records.push({ id: i * 100 + j, level: 3, parent,
    name: j === 2 ? '长名称业务模块：用于验证搜索定位、上下级层次与连续编辑操作不会相互遮挡' : `业务功能 ${i}-${j}` })
}
createApp({ setup() {
  const notice = ref('')
  const describe = action => record => { notice.value = `${action}：${record.name}` }
  return () => h('main', { class: 'fixture' }, [
    h(ModuleTree, { modules: records, loading: false, error: '',
      onAdd: describe('新增下级'), onEdit: describe('编辑'), onDelete: describe('删除'), onDetail: describe('详情') }),
    h('p', { role: 'status' }, notice.value),
  ])
} }).use(Arco).mount('#app')
