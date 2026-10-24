import * as echarts from 'echarts/core'

import {
  BarChart,
  HeatmapChart,
  LineChart,
  PictorialBarChart,
  PieChart,
  RadarChart,
  ScatterChart,
} from 'echarts/charts'

import { SVGRenderer } from 'echarts/renderers'

import {
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  TooltipComponent,
  VisualMapComponent,
} from 'echarts/components'

echarts.use([
  BarChart,
  LineChart,
  PieChart,
  RadarChart,
  ScatterChart,
  HeatmapChart,
  PictorialBarChart,
  SVGRenderer,
  TooltipComponent,
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  VisualMapComponent,
  MarkLineComponent,
])

export default echarts
