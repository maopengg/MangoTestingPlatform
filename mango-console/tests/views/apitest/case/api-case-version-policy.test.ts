import {
  buildScheduledTaskCaseItems,
  buildPublishedBatchItems,
  getApiCasePublicationMeta,
  toApiCaseBatchRunItems,
} from '../../../../src/utils/api-case-version'
import type { ApiCaseVersionListRow } from '../../../../src/types/api-test/case-version'

function assertEqual(actual: unknown, expected: unknown, message: string) {
  const actualJson = JSON.stringify(actual)
  const expectedJson = JSON.stringify(expected)
  if (actualJson !== expectedJson) {
    throw new Error(`${message}: expected ${expectedJson}, received ${actualJson}`)
  }
}

assertEqual(
  getApiCasePublicationMeta('unpublished', null, false),
  { label: '未发布', color: 'gray' },
  'unpublished case should have an explicit label'
)
assertEqual(
  getApiCasePublicationMeta('published', 'V1', false),
  { label: '已发布 V1', color: 'green' },
  'published case should show its release label'
)
assertEqual(
  getApiCasePublicationMeta('draft_changed', 'V1', true),
  { label: '已发布 V1 / 有未发布变更', color: 'orange' },
  'draft_changed case should keep the published version visible'
)

const rows: ApiCaseVersionListRow[] = [
  {
    id: 100,
    name: '已发布且有草稿',
    publication_status: 'draft_changed',
    published_release_id: 58,
    published_revision_id: 312,
    published_version_label: 'V1',
    current_revision_id: 313,
    current_revision_no: 13,
    has_unpublished_changes: true,
  },
  {
    id: 101,
    name: '未发布',
    publication_status: 'unpublished',
    published_release_id: null,
    published_revision_id: null,
    published_version_label: null,
    current_revision_id: 314,
    current_revision_no: 1,
    has_unpublished_changes: false,
  },
]

assertEqual(
  buildPublishedBatchItems(rows),
  {
    executable: [
      {
        case_id: 100,
        case_release_id: 58,
        case_revision_id: 312,
        version_label: 'V1',
      },
    ],
    blocked: [{ case_id: 101, case_name: '未发布', reason: '请先发布用例' }],
  },
  'batch execution must pin V1 and block an unpublished case'
)

assertEqual(
  buildScheduledTaskCaseItems(
    [
      {
        key: 100,
        title: '创建订单',
        published_release_id: 58,
        release_options: [
          { release_id: 58, revision_id: 312, version_label: 'V1', status: 'published' },
        ],
      },
      {
        key: 101,
        title: '删除订单',
        published_release_id: null,
        release_options: [],
      },
    ],
    { '100': 58 }
  ),
  {
    items: [{ case_id: 100, case_release_id: 58 }],
    blocked: [{ case_id: 101, case_name: '删除订单', reason: '请先发布用例' }],
  },
  'scheduled task binding must save the exact selected release'
)

assertEqual(
  buildScheduledTaskCaseItems(
    [
      {
        key: 102,
        title: '已废弃旧版本',
        published_release_id: 60,
        release_options: [
          { release_id: 60, revision_id: 320, version_label: 'V1', status: 'deprecated' },
        ],
      },
    ],
    { '102': 60 }
  ),
  {
    items: [],
    blocked: [{ case_id: 102, case_name: '已废弃旧版本', reason: '所选版本不可执行' }],
  },
  'deprecated release cannot be added to a new scheduled task binding'
)

assertEqual(
  toApiCaseBatchRunItems(buildPublishedBatchItems(rows).executable),
  [{ case_id: 100, case_release_id: 58 }],
  'batch request must submit the exact published release binding'
)
