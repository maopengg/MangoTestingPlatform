import assert from 'node:assert/strict'
import test from 'node:test'

import {
  buildProjectProductFilterTree,
  buildAllProductModuleFilterTree,
  buildModuleFilterTree,
  filterProjectProductOptions,
  getFirstProductId,
  flattenProjectProducts,
  getFirstProductIdWithModules,
  getModuleIdFromTreeKey,
  getModuleLevelStats,
  getFirstSelectableModulePath,
  getModuleIdsForSelection,
  getExpandableTreeKeys,
  getProductIdFromTreeKey,
  getProductIdForTreeSelection,
  getTreeSelectionPath,
  groupModuleTreeByProjectProduct,
} from '../../../src/components/business/project-product-filter.ts'

const options = [
  {
    label: '示例项目',
    value: 1,
    children: [
      { label: '主服务', value: 11 },
      { label: '开放平台', value: 12 },
    ],
  },
  {
    label: '示例应用平台',
    value: 2,
    children: [{ label: '主服务', value: 21 }],
  },
]

test('构建项目分组，并只让产品节点携带可查询的产品 ID', () => {
  assert.deepEqual(buildProjectProductFilterTree(options), [
    {
      key: 'project:1',
      title: '示例项目',
      selectable: false,
      children: [
        { key: 'product:11', title: '主服务', productId: 11 },
        { key: 'product:12', title: '开放平台', productId: 12 },
      ],
    },
    {
      key: 'project:2',
      title: '示例应用平台',
      selectable: false,
      children: [{ key: 'product:21', title: '主服务', productId: 21 }],
    },
  ])
})

test('产品关键字保留匹配产品及所属项目', () => {
  assert.deepEqual(filterProjectProductOptions(options, '开放'), [
    {
      label: '示例项目',
      value: 1,
      children: [{ label: '开放平台', value: 12 }],
    },
  ])
})

test('项目关键字保留项目下的全部产品', () => {
  assert.deepEqual(filterProjectProductOptions(options, '示例应用'), [options[1]])
})

test('默认选择第一个拥有产品的项目中的第一个产品', () => {
  assert.equal(getFirstProductId(options), 11)
  assert.equal(getFirstProductId([{ label: '空项目', value: 3, children: [] }, ...options]), 11)
  assert.equal(getFirstProductId([]), null)
})

test('将所有项目产品展开为模块导航入口，并保留完整名称', () => {
  assert.deepEqual(flattenProjectProducts(options), [
    { projectProductId: 11, title: '示例项目 / 主服务' },
    { projectProductId: 12, title: '示例项目 / 开放平台' },
    { projectProductId: 21, title: '示例应用平台 / 主服务' },
  ])
})

test('默认优先选择第一个存在模块数据的产品', () => {
  const entries = flattenProjectProducts(options)
  assert.equal(
    getFirstProductIdWithModules(entries, {
      11: [],
      12: [{ key: 1, title: '开放模块' }],
      21: [{ key: 2, title: '审查模块' }],
    }),
    12
  )
  assert.equal(getFirstProductIdWithModules(entries, { 11: [], 12: [], 21: [] }), 11)
  assert.equal(getFirstProductIdWithModules([], {}), null)
})

test('只从产品节点解析查询 ID', () => {
  assert.equal(getProductIdFromTreeKey('product:12'), 12)
  assert.equal(getProductIdFromTreeKey('project:1'), null)
})

test('模块树保留三级层级，并保留各层模块 ID', () => {
  assert.deepEqual(
    buildModuleFilterTree([
      {
        key: 100,
        title: 'AI能力',
        children: [
          {
            key: 110,
            title: '智能审查',
            children: [{ key: 111, title: '订单风险' }],
          },
        ],
      },
    ]),
    [
      {
        key: 'module-group:100',
        title: 'AI能力',
        moduleId: 100,
        selectable: false,
        children: [
          {
            key: 'module-group:110',
            title: '智能审查',
            moduleId: 110,
            selectable: false,
            children: [
              {
                key: 'module:111',
                title: '订单风险',
                moduleId: 111,
                selectable: true,
              },
            ],
          },
        ],
      },
    ]
  )
  assert.equal(getModuleIdFromTreeKey('module:111'), 111)
  assert.equal(getModuleIdFromTreeKey('module-group:110'), null)
})

test('模块树压平横杠占位层级，但保留真实模块的可筛选语义', () => {
  assert.deepEqual(
    buildModuleFilterTree([
      {
        key: 1,
        title: '-',
        children: [
          {
            key: 2,
            title: '-',
            children: [{ key: 3, title: '内部审查' }],
          },
        ],
      },
    ]),
    [{ key: 'module:3', title: '内部审查', moduleId: 3, selectable: true }]
  )
})

test('按层级统计模块数量，为导航摘要提供稳定数据', () => {
  assert.deepEqual(
    getModuleLevelStats([
      {
        key: 1,
        children: [
          { key: 2, children: [{ key: 3 }, { key: 4 }] },
          { key: 5, children: [{ key: 6 }] },
        ],
      },
    ]),
    { level1: 1, level2: 2, level3: 3 }
  )
})

test('默认定位第一个真实可筛选模块及其完整路径', () => {
  const tree = buildModuleFilterTree([
    {
      key: 10,
      title: '账户中心',
      children: [
        {
          key: 20,
          title: '组织管理',
          children: [
            { key: 30, title: '组织信息' },
            { key: 31, title: '成员信息' },
          ],
        },
      ],
    },
  ])
  assert.deepEqual(getFirstSelectableModulePath(tree), [
    'module-group:10',
    'module-group:20',
    'module:30',
  ])
  assert.deepEqual(getFirstSelectableModulePath([]), [])
})

test('选择父模块时返回其全部真实三级模块 ID', () => {
  const tree = buildModuleFilterTree([
    { key: 1, children: [{ key: 2, children: [{ key: 3 }, { key: 4 }] }] },
  ])
  assert.deepEqual(getModuleIdsForSelection(tree, 'module-group:1'), [3, 4])
  assert.deepEqual(getModuleIdsForSelection(tree, 'module-group:2'), [3, 4])
  assert.deepEqual(getModuleIdsForSelection(tree, 'module:3'), [3])
})

test('模块导航同时展示全部产品及各自的模块树', () => {
  assert.deepEqual(
    buildAllProductModuleFilterTree(
      [
        { projectProductId: 11, title: '示例项目 / 主服务' },
        { projectProductId: 12, title: '示例项目 / 开放平台' },
      ],
      {
        11: [{ key: 101, title: '订单管理', children: [{ key: 102, title: '订单列表' }] }],
        12: [{ key: 201, title: '开放接口' }],
      }
    ),
    [
      {
        key: 'product-group:11',
        title: '示例项目 / 主服务',
        productId: 11,
        selectable: true,
        children: [
          {
            key: 'module-group:101',
            title: '订单管理',
            moduleId: 101,
            selectable: false,
            children: [
              {
                key: 'module-group:102',
                title: '订单列表',
                moduleId: 102,
                selectable: false,
              },
            ],
          },
        ],
      },
      {
        key: 'product-group:12',
        title: '示例项目 / 开放平台',
        productId: 12,
        selectable: true,
        children: [
          {
            key: 'module-group:201',
            title: '开放接口',
            moduleId: 201,
            selectable: false,
          },
        ],
      },
    ]
  )
})

test('模块选择可解析所属项目产品和完整展开路径', () => {
  const tree = buildAllProductModuleFilterTree(
    [{ projectProductId: 11, title: '示例项目 / 主服务' }],
    {
      11: [
        {
          key: 101,
          title: '订单管理',
          children: [
            {
              key: 102,
              title: '订单列表',
              children: [{ key: 103, title: '订单详情' }],
            },
          ],
        },
      ],
    }
  )
  assert.equal(getProductIdForTreeSelection(tree, 'module:103'), 11)
  assert.deepEqual(getTreeSelectionPath(tree, 'module:103'), [
    'product-group:11',
    'module-group:101',
    'module-group:102',
    'module:103',
  ])
})

test('没有模块的项目产品仍保留在导航中用于跨页面恢复筛选', () => {
  assert.deepEqual(
    buildAllProductModuleFilterTree([{ projectProductId: 11, title: '示例项目 / 主服务' }], {
      11: [],
    }),
    [
      {
        key: 'product-group:11',
        title: '示例项目 / 主服务',
        productId: 11,
        selectable: true,
      },
    ]
  )
})

test('一次返回的模块树按项目产品分组供导航复用', () => {
  const product11Tree = { key: 101, title: '订单管理', project_product_id: 11 }
  const product12Tree = { key: 201, title: '开放接口', project_product_id: 12 }
  assert.deepEqual(groupModuleTreeByProjectProduct([product11Tree, product12Tree] as any[]), {
    11: [product11Tree],
    12: [product12Tree],
  })
})

test('模块搜索自动展开命中结果的父级路径', () => {
  const tree = [
    {
      key: 'product-group:11',
      title: '示例项目 / 主服务',
      children: [
        {
          key: 'module-group:101',
          title: '订单管理',
          children: [{ key: 'module:102', title: '订单列表', moduleId: 102 }],
        },
      ],
    },
  ]
  assert.deepEqual(getExpandableTreeKeys(tree), ['product-group:11', 'module-group:101'])
  assert.deepEqual(getExpandableTreeKeys([]), [])
})
