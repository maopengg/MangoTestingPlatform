import assert from 'node:assert/strict'
import path from 'node:path'
import test from 'node:test'
import { ref, markRaw } from 'vue'
import { harness } from './helpers/case-details-harness.mjs'

function trend(items = []) {
  const density = ref(1)
  const h = harness('ReportTrendChart', 'items,batchTotal,scheduledTotal,otherTotal,total,chartOption,chartContainer,shouldShowTrendLabel,tooltip', {
    base: path.resolve('src/views/report'), props: { items },
    modules: { '@/hooks/useDisplayDensity': { scaleDensityPixels: value => value * density.value } },
  })
  h.chartContainer.value = markRaw({ clientWidth: 1000 })
  return { ...h, density }
}
test('趋势输入是有限字段，拒绝坏数组与非有限数字，缺失通过率保留null', t => {
  const h = trend([null, false, {}, { label: 'Example', batch_count: 0, scheduled_count: '2', other_count: NaN, pass_rate: false }]); t.after(h.close)
  assert.equal(h.items.value.length, 1); assert.equal(h.total.value, 2)
  assert.deepEqual(h.chartOption.value.series.map(item => item.name), ['批量执行', '定时任务', '其他执行', '最终通过率'])
  assert.deepEqual(h.chartOption.value.series[3].data, [null])
  h.props.items = { label: 'Wrong' }; assert.equal(h.items.value.length, 0); assert.equal(h.total.value, 0)
})
test('tooltip非法索引不选第一条，标签转义，合法0通过率仍显示0%', t => {
  const h = trend([{ label: '<img src="example">', pass_rate: 0 }]); t.after(h.close)
  for (const value of [null, undefined, [], [{}], [{ dataIndex: false }], [{ dataIndex: '' }], [{ dataIndex: -1 }], [{ dataIndex: 0.5 }], [{ dataIndex: 9 }]]) assert.equal(h.tooltip(value), '')
  const text = h.tooltip([{ dataIndex: 0 }]); assert.match(text, /&lt;img src=&quot;example&quot;&gt;/)
  assert.match(text, /0\.00%/); assert.doesNotMatch(text, /<img|NaN/)
  h.props.items = [{ label: 'Missing', pass_rate: 100.1 }]; assert.match(h.tooltip([{ dataIndex: 0 }]), /最终通过率：-/)
})
test('密度仅缩放标签设计尺寸，不再缩放实测容器宽度或数据坐标', t => {
  const h = trend(Array.from({ length: 12 }, (_, i) => ({ label: '01/01-01/07', batch_count: i, pass_rate: i }))); t.after(h.close)
  assert.equal(h.shouldShowTrendLabel(2), true)
  h.density.value = 1.35; assert.equal(h.shouldShowTrendLabel(2), false)
  assert.equal(h.shouldShowTrendLabel(0), true); assert.equal(h.shouldShowTrendLabel(11), true)
  for (const index of [-1, 12, 0.5, NaN]) assert.equal(h.shouldShowTrendLabel(index), false)
  assert.deepEqual(h.chartOption.value.series[0].data, Array.from({ length: 12 }, (_, i) => i))
  assert.equal(h.chartOption.value.series[0].barMaxWidth, 26)
})
