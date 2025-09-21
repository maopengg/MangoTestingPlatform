import { defineStore } from 'pinia'
import { getSystemCacheDataKeyValue } from '@/api/system/cache_data'

// 参数配置项类型
interface ParameterItem {
  f: string // 字段名
  n: string // 名称
  p: string // 提示信息
  d: boolean // 是否默认
  v: string // 默认值
}

// 子项类型
interface ChildrenItem {
  value: string // 值
  label: string // 标签
  parameter: ParameterItem[] // 参数配置
  sort: number // 排序
}

// 主项类型
interface SelectValueItem {
  label: string // 标签
  value: string // 值
  children: ChildrenItem[] // 子项列表
}

type StateValueType = SelectValueItem[]

interface SlsectValueState {
  data: StateValueType
  webOpe: ChildrenItem[]
  androidOpe: ChildrenItem[]
  assAndroid: (ChildrenItem | SelectValueItem)[]
  assWeb: (ChildrenItem | SelectValueItem)[]
  ass: SelectValueItem[]
}

export const useSelectValueStore = defineStore('get-select-value', {
  state: (): SlsectValueState => ({
    data: [],
    webOpe: [],
    androidOpe: [],
    assAndroid: [],
    assWeb: [],
    ass: [],
  }),
  getters: {},
  actions: {
    getSelectValue() {
      getSystemCacheDataKeyValue('select_value')
        .then((res) => {
          this.data = res.data
          this.webOpe = []
          this.androidOpe = []
          this.assAndroid = []
          this.assWeb = []
          this.ass = []
          this.data.forEach((item: SelectValueItem) => {
            if (item.value === 'web') {
              this.webOpe.push(...item.children)
            } else if (item.value === 'android') {
              this.androidOpe.push(...item.children)
            } else if (item.value === 'ass_android') {
              this.assAndroid.push(...item.children)
              this.ass.push(...item.children)
            } else if (item.value === 'ass_web') {
              this.assWeb.push(...item.children)
              this.ass.push(...item.children)
            } else if (item.value.includes('断言')) {
              this.ass.push(item)
            }
          })
        })
        .catch(console.log)
    },
    getSelectLabel(value: string): ChildrenItem[] {
      const list = [...this.data]
      for (const item of list) {
        if (item.children) {
          list.push(...item.children)
        }
      }
      return list.find((item: any) => item.value === value)?.label
    },
    findItemByValue(value: string): ChildrenItem | undefined {
      // 检查数据是否存在
      if (!this.data || !Array.isArray(this.data)) {
        return undefined
      }

      const findItem = (data: SelectValueItem[], targetValue: string): ChildrenItem | undefined => {
        if (!data || !Array.isArray(data)) {
          return undefined
        }

        for (let i = 0; i < data.length; i++) {
          const item = data[i]
          if (!item) continue

          // 检查children是否存在且为数组
          if (item.children && Array.isArray(item.children)) {
            // 在children中查找
            for (let j = 0; j < item.children.length; j++) {
              const childItem = item.children[j]
              if (childItem && childItem.value === targetValue) {
                return childItem
              }
            }
            // 递归查找子项的children（如果存在）
            const foundChild = findItem(item.children as any, targetValue)
            if (foundChild) {
              return foundChild
            }
          }
        }
        return undefined
      }

      return findItem(this.data, value)
    },
  },
  presist: {
    enable: true,
    resetToState: true,
  },
})
