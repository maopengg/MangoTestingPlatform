import * as echarts from 'echarts/core'

import { BarChart, LineChart, PictorialBarChart, PieChart, RadarChart } from 'echarts/charts'

import { SVGRenderer } from 'echarts/renderers'

import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'

echarts.use([
  BarChart,
  LineChart,
  PieChart,
  RadarChart,
  PictorialBarChart,
  SVGRenderer,
  TooltipComponent,
  GridComponent,
  LegendComponent,
])

export default echarts
