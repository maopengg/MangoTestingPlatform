export interface ProjectQualityItem {
  project_id: number | null
  project_name: string | null
  report_count: number
  success_count: number
  fail_count: number
  warning_count: number
  other_count: number
  pass_rate: number | null
}

export interface HomeReportCounts {
  success: number
  fail: number
  warning: number
  proceed: number
  stay_begin: number
  stopped: number
}

export interface HomeReportSummary {
  counts: HomeReportCounts
  passRate: number | null
}

export interface HomeExecutionTrend {
  labels: string[]
  api_count: number[]
  ui_count: number[]
  pytest_count: number[]
}

export interface HomeActivityRow { id: string; name: string; count: number }
export interface HomeActivitySnapshot {
  rows: HomeActivityRow[]
  total: number
  activeUsers: number
  activityRate: number
  visitCount: number
  daily: Array<{ date: string; active_users: number }>
}

export interface UpcomingTaskRecord {
  id: number
  name: string
  test_envs: number[]
  execution_scenes: string[]
  execution_scope: string | null
  latest_result_status: number | null
  next_run_at: string
  next_run_time: string
  seconds_until_run: number
  project_product: { name: string; project: { name: string } }
  timing_strategies: Array<{ id: number; name: string; cron: string }>
  case_people: { id: number | null; name: string }
}

export interface RiskTodoItem {
  id: number
  source_type: number
  source_id: number
  event_type: number
  event_type_name: string
  severity: number
  title: string
  summary: string
  due_at: string | null
  occurred_at: string
  project_product: { name: string; project: { name: string } }
  module: { id: number; name: string } | null
  details: Record<string, unknown>
  owners: Array<{ id: number; name: string; username: string }>
  can_mark_handled: boolean
}

export interface RiskCleanupDetail {
  item_id: string | number | null
  alias: string
  table_name: string
  environment_name: string
  database_name: string
  error: string
  primary_key: string
  primary_value: unknown
}

export interface StatisticsData {
    uiStats: {
      elementCount: number | null
      pageCount: number | null
      stepCount: number | null
      caseCount: number | null
      publicCount: number | null
      authConfigCount: number | null
    }
    apiStats: {
      interfaceCount: number | null
      caseCount: number | null
      scenarioCount: number | null
      publicCount: number | null
      headerCount: number | null
      authConfigCount: number | null
    }
    pytestStats: {
      projectCount: number | null
      caseCount: number | null
      fileCount: number | null
      boundProjectCount: number | null
      boundProductCount: number | null
    }
    dataFactoryStats: {
      datasourceCount: number | null
      datasourceBindingCount: number | null
      entityCount: number | null
      fieldCount: number | null
      templateCount: number | null
      caseConfigCount: number | null
    }
    testConfigStats: {
      projectCount: number | null
      projectProductCount: number | null
      databaseCount: number | null
      testObjectCount: number | null
      testFileCount: number | null
    }
    scheduledTaskStats: {
      taskCount: number | null
      strategyCount: number | null
      fireRecordCount: number | null
      systemJobCount: number | null
    }
  }


export interface SkillRecord {
    key: string
    name: string
    description: string
    category?: string
    original_description?: string
    has_custom_introduction?: boolean
    sections?: Array<{ title: string; summary: string }>
    content?: string
  }

export interface SkillIntroduction {
    title?: string
    description?: string
    category?: string
  }

