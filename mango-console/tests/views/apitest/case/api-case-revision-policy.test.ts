import {
  getApiCaseRevisionLabel,
  getApiCaseRevisionStats,
  toApiCaseExecutionVersion,
} from '../../../../src/utils/api-case-revision'
import type {
  ApiCaseRevisionDetail,
  ApiCaseRevisionListItem,
} from '../../../../src/types/api-test/case-version'

function assertEqual(actual: unknown, expected: unknown, message: string) {
  const actualJson = JSON.stringify(actual)
  const expectedJson = JSON.stringify(expected)
  if (actualJson !== expectedJson) {
    throw new Error(`${message}: expected ${expectedJson}, received ${actualJson}`)
  }
}

const draft = {
  id: 12,
  api_case: 100,
  revision_no: 4,
  parent_revision: 11,
  restored_from_revision: null,
  snapshot_schema_version: 1,
  checksum: 'draft-checksum',
  source: 'page',
  operator: 1,
  operator_name: '张三',
  summary: '修改测试环境请求体',
  change_group_id: null,
  create_time: '2026-07-14 10:00:00',
  release: null,
} satisfies ApiCaseRevisionListItem

const published = {
  ...draft,
  id: 10,
  revision_no: 3,
  checksum: 'published-checksum',
  release: {
    id: 58,
    api_case: 100,
    revision: 10,
    revision_no: 3,
    version_no: 1,
    version_label: 'V1',
    status: 'published',
    is_current: true,
    release_note: '线上稳定版本',
    published_by: 2,
    published_by_name: '李四',
    published_at: '2026-07-13 10:00:00',
    replaced_release: null,
  },
} satisfies ApiCaseRevisionListItem

assertEqual(getApiCaseRevisionLabel(draft), '草稿 r4', 'draft revision label')
assertEqual(getApiCaseRevisionLabel(published), 'V1（当前已发布）', 'published revision label')
assertEqual(
  toApiCaseExecutionVersion(published),
  {
    revisionId: 10,
    releaseId: 58,
    label: 'V1（当前已发布）',
    readOnly: true,
  },
  'execution must pin selected release and revision'
)

const detail = {
  ...draft,
  payload: {
    name: '订单链路',
    steps: [
      { id: 1, parameters: [{ id: 11 }, { id: 12 }] },
      { id: 2, parameters: [{ id: 21 }] },
    ],
  },
  api_bindings: [],
} satisfies ApiCaseRevisionDetail

assertEqual(
  getApiCaseRevisionStats(detail),
  { stepCount: 2, scenarioCount: 3 },
  'version panel should summarize the whole aggregate'
)
