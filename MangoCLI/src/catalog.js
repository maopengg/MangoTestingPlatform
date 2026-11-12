export const catalog = Object.freeze([
  {
    "legacy_name": "get_mcp_server_info",
    "domain": "system",
    "command": "get-mcp-server-info",
    "method": "GET",
    "path": "system/runtime/overview",
    "summary": "GET /api/system/runtime/overview",
    "status": "complete"
  },
  {
    "legacy_name": "list_mcp_skills",
    "domain": "system",
    "command": "list-mcp-skills",
    "method": "GET",
    "path": "system/skill/list",
    "summary": "GET /api/system/skill/list",
    "status": "complete"
  },
  {
    "legacy_name": "get_mcp_skill",
    "domain": "system",
    "command": "get-mcp-skill",
    "method": "GET",
    "path": "system/skill/detail",
    "summary": "GET /api/system/skill/detail",
    "status": "complete"
  },
  {
    "legacy_name": "get_current_user_context",
    "domain": "project",
    "command": "get-current-user-context",
    "method": "GET",
    "path": "user/info",
    "summary": "GET /api/user/info",
    "status": "complete"
  },
  {
    "legacy_name": "switch_user_test_environment",
    "domain": "project",
    "command": "switch-user-test-environment",
    "method": "PUT",
    "path": "user/info/config",
    "summary": "切换当前用户测试环境：--param selected_environment=环境ID",
    "status": "complete"
  },
  {
    "legacy_name": "ensure_user_test_environment",
    "domain": "project",
    "command": "ensure-user-test-environment",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "需要新增当前用户与产品测试环境可用性校验 API"
  },
  {
    "legacy_name": "list_test_environments",
    "domain": "project",
    "command": "list-test-environments",
    "method": "GET",
    "path": "system/enum",
    "summary": "GET /api/system/enum",
    "status": "complete"
  },
  {
    "legacy_name": "list_project_test_objects",
    "domain": "project",
    "command": "list-project-test-objects",
    "method": "GET",
    "path": "system/test/object",
    "summary": "GET /api/system/test/object",
    "status": "complete"
  },
  {
    "legacy_name": "list_project_products",
    "domain": "project",
    "command": "list-project-products",
    "method": "GET",
    "path": "system/product",
    "summary": "GET /api/system/product",
    "status": "complete"
  },
  {
    "legacy_name": "list_product_modules",
    "domain": "project",
    "command": "list-product-modules",
    "method": "GET",
    "path": "system/module/tree",
    "summary": "GET /api/system/module/tree",
    "status": "complete"
  },
  {
    "legacy_name": "create_product_module",
    "domain": "project",
    "command": "create-product-module",
    "method": "POST",
    "path": "system/module/path",
    "summary": "POST /api/system/module/path",
    "status": "complete"
  },
  {
    "legacy_name": "update_product_module",
    "domain": "project",
    "command": "update-product-module",
    "method": "PUT",
    "path": "system/module",
    "summary": "PUT /api/system/module",
    "status": "complete"
  },
  {
    "legacy_name": "preview_delete_product_module_impact",
    "domain": "project",
    "command": "preview-delete-product-module-impact",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面缺少模块删除影响预览 API"
  },
  {
    "legacy_name": "delete_product_module",
    "domain": "project",
    "command": "delete-product-module",
    "method": "DELETE",
    "path": "system/module",
    "summary": "DELETE /api/system/module",
    "status": "complete"
  },
  {
    "legacy_name": "list_case_owners",
    "domain": "project",
    "command": "list-case-owners",
    "method": "GET",
    "path": "user/info/name",
    "summary": "GET /api/user/info/name",
    "status": "complete"
  },
  {
    "legacy_name": "list_system_files",
    "domain": "file",
    "command": "list-system-files",
    "method": "GET",
    "path": "system/file",
    "summary": "GET /api/system/file",
    "status": "complete"
  },
  {
    "legacy_name": "upload_system_file",
    "domain": "file",
    "command": "upload-system-file",
    "method": "POST",
    "path": "system/file",
    "summary": "POST /api/system/file",
    "status": "complete",
    "multipart": true
  },
  {
    "legacy_name": "get_system_file_download_url",
    "domain": "file",
    "command": "get-system-file-download-url",
    "method": "GET",
    "path": "system/file/download/url",
    "summary": "GET /api/system/file/download/url",
    "status": "complete"
  },
  {
    "legacy_name": "list_test_data_methods",
    "domain": "data-method",
    "command": "list-test-data-methods",
    "method": "GET",
    "path": "system/variable/random/list",
    "summary": "GET /api/system/variable/random/list",
    "status": "complete"
  },
  {
    "legacy_name": "evaluate_test_data_expression",
    "domain": "data-method",
    "command": "evaluate-test-data-expression",
    "method": "GET",
    "path": "system/variable/value",
    "summary": "GET /api/system/variable/value",
    "status": "complete"
  },
  {
    "legacy_name": "list_workbench_todos",
    "domain": "todo",
    "command": "list-workbench-todos",
    "method": "GET",
    "path": "system/index/todos",
    "summary": "GET /api/system/index/todos",
    "status": "complete"
  },
  {
    "legacy_name": "get_workbench_todo_detail",
    "domain": "todo",
    "command": "get-workbench-todo-detail",
    "method": "GET",
    "path": "system/index/todos",
    "summary": "GET /api/system/index/todos",
    "status": "complete"
  },
  {
    "legacy_name": "refresh_workbench_todos",
    "domain": "todo",
    "command": "refresh-workbench-todos",
    "method": "GET",
    "path": "system/index/todos",
    "summary": "GET /api/system/index/todos",
    "status": "complete"
  },
  {
    "legacy_name": "update_workbench_todo_handled",
    "domain": "todo",
    "command": "update-workbench-todo-handled",
    "method": "POST",
    "path": "system/index/todos/handled",
    "summary": "POST /api/system/index/todos/handled",
    "status": "complete"
  },
  {
    "legacy_name": "preview_modify_published_api_info_impact",
    "domain": "api",
    "command": "preview-modify-published-api-info-impact",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面缺少已发布 API Info 修改影响预览 API"
  },
  {
    "legacy_name": "checkout_api_info_revision_to_editing",
    "domain": "api",
    "command": "checkout-api-info-revision-to-editing",
    "method": "POST",
    "path": "api/info/revision/checkout",
    "summary": "POST /api/api/info/revision/checkout",
    "status": "complete"
  },
  {
    "legacy_name": "create_api_info_revision_from_current",
    "domain": "api",
    "command": "create-api-info-revision-from-current",
    "method": "POST",
    "path": "api/info/revision",
    "summary": "POST /api/api/info/revision",
    "status": "complete"
  },
  {
    "legacy_name": "publish_api_info_revision",
    "domain": "api",
    "command": "publish-api-info-revision",
    "method": "POST",
    "path": "api/info/release",
    "summary": "POST /api/api/info/release",
    "status": "complete"
  },
  {
    "legacy_name": "search_api_infos",
    "domain": "api",
    "command": "search-api-infos",
    "method": "GET",
    "path": "api/info",
    "summary": "GET /api/api/info",
    "status": "complete"
  },
  {
    "legacy_name": "get_api_info_detail",
    "domain": "api",
    "command": "get-api-info-detail",
    "method": "GET",
    "path": "api/info",
    "summary": "GET /api/api/info",
    "status": "complete"
  },
  {
    "legacy_name": "create_api_info",
    "domain": "api",
    "command": "create-api-info",
    "method": "POST",
    "path": "api/info",
    "summary": "POST /api/api/info",
    "status": "complete"
  },
  {
    "legacy_name": "create_api_info_from_curl",
    "domain": "api",
    "command": "create-api-info-from-curl",
    "method": "POST",
    "path": "api/info/import/api",
    "summary": "POST /api/api/info/import/api",
    "status": "complete"
  },
  {
    "legacy_name": "update_api_info",
    "domain": "api",
    "command": "update-api-info",
    "method": "PUT",
    "path": "api/info",
    "summary": "PUT /api/api/info",
    "status": "complete"
  },
  {
    "legacy_name": "create_grpc_service",
    "domain": "api",
    "command": "create-grpc-service",
    "method": "POST",
    "path": "api/grpc/service",
    "summary": "POST /api/api/grpc/service",
    "status": "complete"
  },
  {
    "legacy_name": "update_grpc_service",
    "domain": "api",
    "command": "update-grpc-service",
    "method": "PUT",
    "path": "api/grpc/service",
    "summary": "PUT /api/api/grpc/service",
    "status": "complete"
  },
  {
    "legacy_name": "list_grpc_services",
    "domain": "api",
    "command": "list-grpc-services",
    "method": "GET",
    "path": "api/grpc/service",
    "summary": "GET /api/api/grpc/service",
    "status": "complete"
  },
  {
    "legacy_name": "list_grpc_methods",
    "domain": "api",
    "command": "list-grpc-methods",
    "method": "GET",
    "path": "api/grpc/method",
    "summary": "GET /api/api/grpc/method",
    "status": "complete"
  },
  {
    "legacy_name": "get_grpc_service_detail",
    "domain": "api",
    "command": "get-grpc-service-detail",
    "method": "GET",
    "path": "api/grpc/service",
    "summary": "GET /api/api/grpc/service",
    "status": "complete"
  },
  {
    "legacy_name": "sync_grpc_methods",
    "domain": "api",
    "command": "sync-grpc-methods",
    "method": "POST",
    "path": "api/grpc/method/sync",
    "summary": "POST /api/api/grpc/method/sync",
    "status": "complete"
  },
  {
    "legacy_name": "import_grpc_method_to_api_info",
    "domain": "api",
    "command": "import-grpc-method-to-api-info",
    "method": "POST",
    "path": "api/grpc/method/import/api-info",
    "summary": "POST /api/api/grpc/method/import/api-info",
    "status": "complete"
  },
  {
    "legacy_name": "run_api_info",
    "domain": "api",
    "command": "run-api-info",
    "method": "GET",
    "path": "api/info/test",
    "summary": "GET /api/api/info/test",
    "status": "complete"
  },
  {
    "legacy_name": "get_api_assertion_methods",
    "domain": "api",
    "command": "get-api-assertion-methods",
    "method": "GET",
    "path": "system/assertion/list",
    "summary": "GET /api/system/assertion/list",
    "status": "complete"
  },
  {
    "legacy_name": "get_api_assertion_schema",
    "domain": "api",
    "command": "get-api-assertion-schema",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面没有与 MCP 等价的断言 Schema API"
  },
  {
    "legacy_name": "get_api_auth_config_schema",
    "domain": "api",
    "command": "get-api-auth-config-schema",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面没有 API 鉴权配置 Schema 接口"
  },
  {
    "legacy_name": "list_api_auth_time_tasks",
    "domain": "api",
    "command": "list-api-auth-time-tasks",
    "method": "GET",
    "path": "system/time",
    "summary": "GET /api/system/time",
    "status": "complete"
  },
  {
    "legacy_name": "list_api_auth_configs",
    "domain": "api",
    "command": "list-api-auth-configs",
    "method": "GET",
    "path": "api/auth/config",
    "summary": "GET /api/api/auth/config",
    "status": "complete"
  },
  {
    "legacy_name": "get_api_auth_config_detail",
    "domain": "api",
    "command": "get-api-auth-config-detail",
    "method": "GET",
    "path": "api/auth/config",
    "summary": "GET /api/api/auth/config",
    "status": "complete"
  },
  {
    "legacy_name": "create_api_auth_config",
    "domain": "api",
    "command": "create-api-auth-config",
    "method": "POST",
    "path": "api/auth/config",
    "summary": "POST /api/api/auth/config",
    "status": "complete"
  },
  {
    "legacy_name": "update_api_auth_config",
    "domain": "api",
    "command": "update-api-auth-config",
    "method": "PUT",
    "path": "api/auth/config",
    "summary": "PUT /api/api/auth/config",
    "status": "complete"
  },
  {
    "legacy_name": "set_api_auth_config_status",
    "domain": "api",
    "command": "set-api-auth-config-status",
    "method": "PUT",
    "path": "api/auth/config/status",
    "summary": "PUT /api/api/auth/config/status",
    "status": "complete"
  },
  {
    "legacy_name": "refresh_api_auth_config",
    "domain": "api",
    "command": "refresh-api-auth-config",
    "method": "POST",
    "path": "api/auth/config/refresh",
    "summary": "POST /api/api/auth/config/refresh",
    "status": "complete"
  },
  {
    "legacy_name": "preview_clear_api_auth_config_cache_impact",
    "domain": "api",
    "command": "preview-clear-api-auth-config-cache-impact",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面缺少危险操作影响预览 API"
  },
  {
    "legacy_name": "clear_api_auth_config_cache",
    "domain": "api",
    "command": "clear-api-auth-config-cache",
    "method": "POST",
    "path": "api/auth/config/clear",
    "summary": "POST /api/api/auth/config/clear",
    "status": "complete"
  },
  {
    "legacy_name": "get_api_auth_config_cache",
    "domain": "api",
    "command": "get-api-auth-config-cache",
    "method": "GET",
    "path": "api/auth/config/cache",
    "summary": "GET /api/api/auth/config/cache",
    "status": "complete"
  },
  {
    "legacy_name": "preview_delete_api_auth_config_impact",
    "domain": "api",
    "command": "preview-delete-api-auth-config-impact",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面缺少危险操作影响预览 API"
  },
  {
    "legacy_name": "delete_api_auth_config",
    "domain": "api",
    "command": "delete-api-auth-config",
    "method": "DELETE",
    "path": "api/auth/config",
    "summary": "DELETE /api/api/auth/config",
    "status": "complete"
  },
  {
    "legacy_name": "preview_modify_published_api_case_impact",
    "domain": "api",
    "command": "preview-modify-published-api-case-impact",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面缺少等价影响预览 API"
  },
  {
    "legacy_name": "preview_checkout_api_case_revision_impact",
    "domain": "api",
    "command": "preview-checkout-api-case-revision-impact",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面缺少等价影响预览 API"
  },
  {
    "legacy_name": "checkout_api_case_revision_to_editing",
    "domain": "api",
    "command": "checkout-api-case-revision-to-editing",
    "method": "POST",
    "path": "api/case/revision/checkout",
    "summary": "POST /api/api/case/revision/checkout",
    "status": "complete"
  },
  {
    "legacy_name": "create_api_case_revision_from_current",
    "domain": "api",
    "command": "create-api-case-revision-from-current",
    "method": "POST",
    "path": "api/case/revision",
    "summary": "POST /api/api/case/revision",
    "status": "complete"
  },
  {
    "legacy_name": "update_api_case_publication_status",
    "domain": "api",
    "command": "update-api-case-publication-status",
    "summary": "等待统一的后端 REST API",
    "status": "pending_api",
    "reason": "MCP 已合并为状态流转工具，页面兼容 REST API 仍按提交、通过和退回拆分"
  },
  {
    "legacy_name": "search_api_cases",
    "domain": "api",
    "command": "search-api-cases",
    "method": "GET",
    "path": "api/case",
    "summary": "GET /api/api/case",
    "status": "complete"
  },
  {
    "legacy_name": "create_api_case",
    "domain": "api",
    "command": "create-api-case",
    "method": "POST",
    "path": "api/case",
    "summary": "POST /api/api/case",
    "status": "complete"
  },
  {
    "legacy_name": "update_api_case",
    "domain": "api",
    "command": "update-api-case",
    "method": "PUT",
    "path": "api/case",
    "summary": "PUT /api/api/case",
    "status": "complete"
  },
  {
    "legacy_name": "add_api_case_step",
    "domain": "api",
    "command": "add-api-case-step",
    "method": "POST",
    "path": "api/case/detailed",
    "summary": "POST /api/api/case/detailed",
    "status": "complete"
  },
  {
    "legacy_name": "list_api_case_steps",
    "domain": "api",
    "command": "list-api-case-steps",
    "method": "GET",
    "path": "api/case/detailed",
    "summary": "GET /api/api/case/detailed",
    "status": "complete"
  },
  {
    "legacy_name": "sort_api_case_steps",
    "domain": "api",
    "command": "sort-api-case-steps",
    "method": "PUT",
    "path": "api/case/detailed/sort",
    "summary": "PUT /api/api/case/detailed/sort",
    "status": "complete"
  },
  {
    "legacy_name": "refresh_api_case_step_from_api_info",
    "domain": "api",
    "command": "refresh-api-case-step-from-api-info",
    "method": "PUT",
    "path": "api/case/detailed/refresh",
    "summary": "PUT /api/api/case/detailed/refresh",
    "status": "complete"
  },
  {
    "legacy_name": "get_api_case_detail_full",
    "domain": "api",
    "command": "get-api-case-detail-full",
    "method": "GET",
    "path": "api/case",
    "summary": "GET /api/api/case",
    "status": "complete"
  },
  {
    "legacy_name": "create_complete_api_case",
    "domain": "api",
    "command": "create-complete-api-case",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面缺少一次事务创建完整 Case 的 API"
  },
  {
    "legacy_name": "run_api_case",
    "domain": "api",
    "command": "run-api-case",
    "method": "GET",
    "path": "api/case/test",
    "summary": "GET /api/api/case/test",
    "status": "complete"
  },
  {
    "legacy_name": "debug_api_case_step",
    "domain": "api",
    "command": "debug-api-case-step",
    "method": "POST",
    "path": "api/case/step/debug",
    "summary": "POST /api/api/case/step/debug",
    "status": "complete"
  },
  {
    "legacy_name": "run_api_case_batch",
    "domain": "api",
    "command": "run-api-case-batch",
    "method": "POST",
    "path": "api/case/batch",
    "summary": "POST /api/api/case/batch",
    "status": "complete"
  },
  {
    "legacy_name": "get_api_case_run_result",
    "domain": "api",
    "command": "get-api-case-run-result",
    "method": "GET",
    "path": "system/execution/result/latest",
    "summary": "GET /api/system/execution/result/latest",
    "status": "complete"
  },
  {
    "legacy_name": "get_api_case_step_result",
    "domain": "api",
    "command": "get-api-case-step-result",
    "method": "GET",
    "path": "system/execution/result/latest",
    "summary": "GET /api/system/execution/result/latest",
    "status": "complete"
  },
  {
    "legacy_name": "get_api_case_execution_trace",
    "domain": "api",
    "command": "get-api-case-execution-trace",
    "method": "GET",
    "path": "system/test/suite/details/execution-trace",
    "summary": "GET /api/system/test/suite/details/execution-trace",
    "status": "complete"
  },
  {
    "legacy_name": "analyze_api_case_failure",
    "domain": "api",
    "command": "analyze-api-case-failure",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面缺少结构化 API Case 失败分析接口"
  },
  {
    "legacy_name": "preview_delete_api_info_impact",
    "domain": "api",
    "command": "preview-delete-api-info-impact",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面缺少对应删除影响预览 API"
  },
  {
    "legacy_name": "delete_api_info",
    "domain": "api",
    "command": "delete-api-info",
    "method": "DELETE",
    "path": "api/info",
    "summary": "DELETE /api/api/info",
    "status": "complete"
  },
  {
    "legacy_name": "preview_delete_api_info_revision_impact",
    "domain": "api",
    "command": "preview-delete-api-info-revision-impact",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面缺少对应删除影响预览 API"
  },
  {
    "legacy_name": "delete_api_info_revision",
    "domain": "api",
    "command": "delete-api-info-revision",
    "method": "DELETE",
    "path": "api/info/revision",
    "summary": "DELETE /api/api/info/revision",
    "status": "complete"
  },
  {
    "legacy_name": "preview_delete_api_case_impact",
    "domain": "api",
    "command": "preview-delete-api-case-impact",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面缺少对应删除影响预览 API"
  },
  {
    "legacy_name": "delete_api_case",
    "domain": "api",
    "command": "delete-api-case",
    "method": "DELETE",
    "path": "api/case",
    "summary": "DELETE /api/api/case",
    "status": "complete"
  },
  {
    "legacy_name": "preview_delete_api_case_revision_impact",
    "domain": "api",
    "command": "preview-delete-api-case-revision-impact",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面缺少对应删除影响预览 API"
  },
  {
    "legacy_name": "delete_api_case_revision",
    "domain": "api",
    "command": "delete-api-case-revision",
    "method": "DELETE",
    "path": "api/case/revision",
    "summary": "DELETE /api/api/case/revision",
    "status": "complete"
  },
  {
    "legacy_name": "preview_delete_api_case_step_impact",
    "domain": "api",
    "command": "preview-delete-api-case-step-impact",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面缺少对应删除影响预览 API"
  },
  {
    "legacy_name": "delete_api_case_step",
    "domain": "api",
    "command": "delete-api-case-step",
    "method": "DELETE",
    "path": "api/case/detailed",
    "summary": "DELETE /api/api/case/detailed",
    "status": "complete"
  },
  {
    "legacy_name": "preview_delete_api_case_scenario_impact",
    "domain": "api",
    "command": "preview-delete-api-case-scenario-impact",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面缺少对应删除影响预览 API"
  },
  {
    "legacy_name": "delete_api_case_scenario",
    "domain": "api",
    "command": "delete-api-case-scenario",
    "method": "DELETE",
    "path": "api/case/detailed/parameter",
    "summary": "DELETE /api/api/case/detailed/parameter",
    "status": "complete"
  },
  {
    "legacy_name": "list_api_headers",
    "domain": "api",
    "command": "list-api-headers",
    "method": "GET",
    "path": "api/headers",
    "summary": "GET /api/api/headers",
    "status": "complete"
  },
  {
    "legacy_name": "preview_create_api_header_impact",
    "domain": "api",
    "command": "preview-create-api-header-impact",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面缺少创建公共请求头影响预览 API"
  },
  {
    "legacy_name": "create_api_header",
    "domain": "api",
    "command": "create-api-header",
    "method": "POST",
    "path": "api/headers",
    "summary": "POST /api/api/headers",
    "status": "complete"
  },
  {
    "legacy_name": "update_api_header",
    "domain": "api",
    "command": "update-api-header",
    "method": "PUT",
    "path": "api/headers",
    "summary": "PUT /api/api/headers",
    "status": "complete"
  },
  {
    "legacy_name": "create_module_coverage_scan",
    "domain": "api",
    "command": "create-module-coverage-scan",
    "method": "POST",
    "path": "api/module-coverage/scans",
    "summary": "POST /api/api/module-coverage/scans",
    "status": "complete"
  },
  {
    "legacy_name": "batch_upsert_module_coverage_interfaces",
    "domain": "api",
    "command": "batch-upsert-module-coverage-interfaces",
    "method": "POST",
    "path": "api/module-coverage/scan-interfaces/batch",
    "summary": "POST /api/api/module-coverage/scan-interfaces/batch",
    "status": "complete"
  },
  {
    "legacy_name": "batch_upsert_module_coverage_cases",
    "domain": "api",
    "command": "batch-upsert-module-coverage-cases",
    "method": "POST",
    "path": "api/module-coverage/scan-cases/batch",
    "summary": "POST /api/api/module-coverage/scan-cases/batch",
    "status": "complete"
  },
  {
    "legacy_name": "get_module_coverage_scan_validation",
    "domain": "api",
    "command": "get-module-coverage-scan-validation",
    "method": "GET",
    "path": "api/module-coverage/scans/validation",
    "summary": "GET /api/api/module-coverage/scans/validation",
    "status": "complete"
  },
  {
    "legacy_name": "get_module_coverage_scan_upload_status",
    "domain": "api",
    "command": "get-module-coverage-scan-upload-status",
    "method": "GET",
    "path": "api/module-coverage/scans/upload-status",
    "summary": "GET /api/api/module-coverage/scans/upload-status",
    "status": "complete"
  },
  {
    "legacy_name": "get_module_coverage_scan",
    "domain": "api",
    "command": "get-module-coverage-scan",
    "method": "GET",
    "path": "api/module-coverage/scans/detail",
    "summary": "GET /api/api/module-coverage/scans/detail",
    "status": "complete"
  },
  {
    "legacy_name": "update_module_coverage_scan",
    "domain": "api",
    "command": "update-module-coverage-scan",
    "method": "PUT",
    "path": "api/module-coverage/scans/status",
    "summary": "PUT /api/api/module-coverage/scans/status",
    "status": "complete"
  },
  {
    "legacy_name": "list_module_coverage_scans",
    "domain": "api",
    "command": "list-module-coverage-scans",
    "method": "GET",
    "path": "api/module-coverage/scans",
    "summary": "GET /api/api/module-coverage/scans",
    "status": "complete"
  },
  {
    "legacy_name": "list_module_coverage_cases",
    "domain": "api",
    "command": "list-module-coverage-cases",
    "method": "GET",
    "path": "api/module-coverage/cases",
    "summary": "GET /api/api/module-coverage/cases",
    "status": "complete"
  },
  {
    "legacy_name": "list_module_coverage_interfaces",
    "domain": "api",
    "command": "list-module-coverage-interfaces",
    "method": "GET",
    "path": "api/module-coverage/interfaces",
    "summary": "GET /api/api/module-coverage/interfaces",
    "status": "complete"
  },
  {
    "legacy_name": "get_module_coverage_interface",
    "domain": "api",
    "command": "get-module-coverage-interface",
    "method": "GET",
    "path": "api/module-coverage/interfaces/detail",
    "summary": "GET /api/api/module-coverage/interfaces/detail",
    "status": "complete"
  },
  {
    "legacy_name": "list_module_coverage_interface_snapshots",
    "domain": "api",
    "command": "list-module-coverage-interface-snapshots",
    "method": "GET",
    "path": "api/module-coverage/interfaces/snapshots",
    "summary": "GET /api/api/module-coverage/interfaces/snapshots",
    "status": "complete"
  },
  {
    "legacy_name": "get_module_coverage_interface_diff",
    "domain": "api",
    "command": "get-module-coverage-interface-diff",
    "method": "GET",
    "path": "api/module-coverage/interfaces/diff",
    "summary": "GET /api/api/module-coverage/interfaces/diff",
    "status": "complete"
  },
  {
    "legacy_name": "list_module_coverage_interface_cases",
    "domain": "api",
    "command": "list-module-coverage-interface-cases",
    "method": "GET",
    "path": "api/module-coverage/cases",
    "summary": "GET /api/api/module-coverage/cases",
    "status": "complete"
  },
  {
    "legacy_name": "get_module_coverage_case",
    "domain": "api",
    "command": "get-module-coverage-case",
    "method": "GET",
    "path": "api/module-coverage/cases/detail",
    "summary": "GET /api/api/module-coverage/cases/detail",
    "status": "complete"
  },
  {
    "legacy_name": "list_module_coverage_case_snapshots",
    "domain": "api",
    "command": "list-module-coverage-case-snapshots",
    "method": "GET",
    "path": "api/module-coverage/cases/snapshots",
    "summary": "GET /api/api/module-coverage/cases/snapshots",
    "status": "complete"
  },
  {
    "legacy_name": "get_module_coverage_case_flow",
    "domain": "api",
    "command": "get-module-coverage-case-flow",
    "method": "GET",
    "path": "api/module-coverage/cases/flow",
    "summary": "GET /api/api/module-coverage/cases/flow",
    "status": "complete"
  },
  {
    "legacy_name": "get_module_coverage_case_diff",
    "domain": "api",
    "command": "get-module-coverage-case-diff",
    "method": "GET",
    "path": "api/module-coverage/cases/diff",
    "summary": "GET /api/api/module-coverage/cases/diff",
    "status": "complete"
  },
  {
    "legacy_name": "update_module_coverage_case_binding",
    "domain": "api",
    "command": "update-module-coverage-case-binding",
    "method": "PUT",
    "path": "api/module-coverage/cases/binding",
    "summary": "PUT /api/api/module-coverage/cases/binding",
    "status": "complete"
  },
  {
    "legacy_name": "batch_archive_module_coverage_cases",
    "domain": "api",
    "command": "batch-archive-module-coverage-cases",
    "method": "POST",
    "path": "api/module-coverage/cases/archive/batch",
    "summary": "POST /api/api/module-coverage/cases/archive/batch",
    "status": "complete"
  },
  {
    "legacy_name": "get_module_coverage_metrics",
    "domain": "api",
    "command": "get-module-coverage-metrics",
    "method": "GET",
    "path": "api/module-coverage/metrics",
    "summary": "GET /api/api/module-coverage/metrics",
    "status": "complete"
  },
  {
    "legacy_name": "list_api_public_variables",
    "domain": "api",
    "command": "list-api-public-variables",
    "method": "GET",
    "path": "api/public",
    "summary": "GET /api/api/public",
    "status": "complete"
  },
  {
    "legacy_name": "create_api_public_variable",
    "domain": "api",
    "command": "create-api-public-variable",
    "method": "POST",
    "path": "api/public",
    "summary": "POST /api/api/public",
    "status": "complete"
  },
  {
    "legacy_name": "update_api_public_variable",
    "domain": "api",
    "command": "update-api-public-variable",
    "method": "PUT",
    "path": "api/public",
    "summary": "PUT /api/api/public",
    "status": "complete"
  },
  {
    "legacy_name": "set_api_public_variable_status",
    "domain": "api",
    "command": "set-api-public-variable-status",
    "method": "PUT",
    "path": "api/public/status",
    "summary": "PUT /api/api/public/status",
    "status": "complete"
  },
  {
    "legacy_name": "preview_delete_api_public_variable_impact",
    "domain": "api",
    "command": "preview-delete-api-public-variable-impact",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面缺少删除影响预览 API"
  },
  {
    "legacy_name": "delete_api_public_variable",
    "domain": "api",
    "command": "delete-api-public-variable",
    "method": "DELETE",
    "path": "api/public",
    "summary": "DELETE /api/api/public",
    "status": "complete"
  },
  {
    "legacy_name": "list_api_case_scenarios",
    "domain": "api",
    "command": "list-api-case-scenarios",
    "method": "GET",
    "path": "api/case/detailed/parameter",
    "summary": "GET /api/api/case/detailed/parameter",
    "status": "complete"
  },
  {
    "legacy_name": "create_api_case_scenario",
    "domain": "api",
    "command": "create-api-case-scenario",
    "method": "POST",
    "path": "api/case/detailed/parameter",
    "summary": "POST /api/api/case/detailed/parameter",
    "status": "complete"
  },
  {
    "legacy_name": "update_api_case_scenario",
    "domain": "api",
    "command": "update-api-case-scenario",
    "method": "PUT",
    "path": "api/case/detailed/parameter",
    "summary": "PUT /api/api/case/detailed/parameter",
    "status": "complete"
  },
  {
    "legacy_name": "generate_api_case_scenario_assertions",
    "domain": "api",
    "command": "generate-api-case-scenario-assertions",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面缺少根据响应样例生成断言或提取器草稿的 API"
  },
  {
    "legacy_name": "generate_api_case_scenario_extractors",
    "domain": "api",
    "command": "generate-api-case-scenario-extractors",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面缺少根据响应样例生成断言或提取器草稿的 API"
  },
  {
    "legacy_name": "auto_generate_api_case_scenario_schema",
    "domain": "api",
    "command": "auto-generate-api-case-scenario-schema",
    "method": "PUT",
    "path": "api/case/detailed/parameter/schema",
    "summary": "PUT /api/api/case/detailed/parameter/schema",
    "status": "complete"
  },
  {
    "legacy_name": "get_api_case_schema",
    "domain": "api",
    "command": "get-api-case-schema",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面没有完整 API Case Schema 接口"
  },
  {
    "legacy_name": "get_ui_auth_config_schema",
    "domain": "ui",
    "command": "get-ui-auth-config-schema",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面缺少与 MCP 返回内容等价的 Schema/方法目录 API"
  },
  {
    "legacy_name": "list_ui_auth_time_tasks",
    "domain": "ui",
    "command": "list-ui-auth-time-tasks",
    "method": "GET",
    "path": "system/time",
    "summary": "GET /api/system/time",
    "status": "complete"
  },
  {
    "legacy_name": "list_ui_auth_configs",
    "domain": "ui",
    "command": "list-ui-auth-configs",
    "method": "GET",
    "path": "ui/auth/config",
    "summary": "GET /api/ui/auth/config",
    "status": "complete"
  },
  {
    "legacy_name": "get_ui_auth_config_detail",
    "domain": "ui",
    "command": "get-ui-auth-config-detail",
    "method": "GET",
    "path": "ui/auth/config",
    "summary": "GET /api/ui/auth/config",
    "status": "complete"
  },
  {
    "legacy_name": "create_ui_auth_config",
    "domain": "ui",
    "command": "create-ui-auth-config",
    "method": "POST",
    "path": "ui/auth/config",
    "summary": "POST /api/ui/auth/config",
    "status": "complete"
  },
  {
    "legacy_name": "update_ui_auth_config",
    "domain": "ui",
    "command": "update-ui-auth-config",
    "method": "PUT",
    "path": "ui/auth/config",
    "summary": "PUT /api/ui/auth/config",
    "status": "complete"
  },
  {
    "legacy_name": "set_ui_auth_config_status",
    "domain": "ui",
    "command": "set-ui-auth-config-status",
    "method": "PUT",
    "path": "ui/auth/config/status",
    "summary": "PUT /api/ui/auth/config/status",
    "status": "complete"
  },
  {
    "legacy_name": "refresh_ui_auth_config",
    "domain": "ui",
    "command": "refresh-ui-auth-config",
    "method": "POST",
    "path": "ui/auth/config/refresh",
    "summary": "POST /api/ui/auth/config/refresh",
    "status": "complete"
  },
  {
    "legacy_name": "preview_clear_ui_auth_config_cache_impact",
    "domain": "ui",
    "command": "preview-clear-ui-auth-config-cache-impact",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面缺少危险操作影响预览 API"
  },
  {
    "legacy_name": "clear_ui_auth_config_cache",
    "domain": "ui",
    "command": "clear-ui-auth-config-cache",
    "method": "POST",
    "path": "ui/auth/config/clear",
    "summary": "POST /api/ui/auth/config/clear",
    "status": "complete"
  },
  {
    "legacy_name": "get_ui_auth_config_cache",
    "domain": "ui",
    "command": "get-ui-auth-config-cache",
    "method": "GET",
    "path": "ui/auth/config/cache",
    "summary": "GET /api/ui/auth/config/cache",
    "status": "complete"
  },
  {
    "legacy_name": "save_ui_manual_auth_cache",
    "domain": "ui",
    "command": "save-ui-manual-auth-cache",
    "method": "PUT",
    "path": "ui/auth/config/manual-cache",
    "summary": "PUT /api/ui/auth/config/manual-cache",
    "status": "complete"
  },
  {
    "legacy_name": "preview_delete_ui_auth_config_impact",
    "domain": "ui",
    "command": "preview-delete-ui-auth-config-impact",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面缺少危险操作影响预览 API"
  },
  {
    "legacy_name": "delete_ui_auth_config",
    "domain": "ui",
    "command": "delete-ui-auth-config",
    "method": "DELETE",
    "path": "ui/auth/config",
    "summary": "DELETE /api/ui/auth/config",
    "status": "complete"
  },
  {
    "legacy_name": "search_ui_cases",
    "domain": "ui",
    "command": "search-ui-cases",
    "method": "GET",
    "path": "ui/case",
    "summary": "GET /api/ui/case",
    "status": "complete"
  },
  {
    "legacy_name": "get_ui_case_detail_full",
    "domain": "ui",
    "command": "get-ui-case-detail-full",
    "method": "GET",
    "path": "ui/case",
    "summary": "GET /api/ui/case",
    "status": "complete"
  },
  {
    "legacy_name": "create_ui_case",
    "domain": "ui",
    "command": "create-ui-case",
    "method": "POST",
    "path": "ui/case",
    "summary": "POST /api/ui/case",
    "status": "complete"
  },
  {
    "legacy_name": "update_ui_case",
    "domain": "ui",
    "command": "update-ui-case",
    "method": "PUT",
    "path": "ui/case",
    "summary": "PUT /api/ui/case",
    "status": "complete"
  },
  {
    "legacy_name": "add_ui_case_step",
    "domain": "ui",
    "command": "add-ui-case-step",
    "method": "POST",
    "path": "ui/case/steps/detailed",
    "summary": "POST /api/ui/case/steps/detailed",
    "status": "complete"
  },
  {
    "legacy_name": "list_ui_case_steps",
    "domain": "ui",
    "command": "list-ui-case-steps",
    "method": "GET",
    "path": "ui/case/steps/detailed",
    "summary": "GET /api/ui/case/steps/detailed",
    "status": "complete"
  },
  {
    "legacy_name": "sort_ui_case_steps",
    "domain": "ui",
    "command": "sort-ui-case-steps",
    "method": "PUT",
    "path": "ui/case/steps/detailed/sort",
    "summary": "PUT /api/ui/case/steps/detailed/sort",
    "status": "complete"
  },
  {
    "legacy_name": "refresh_ui_case_step_cache_data",
    "domain": "ui",
    "command": "refresh-ui-case-step-cache-data",
    "method": "GET",
    "path": "ui/case/steps/detailed/refresh",
    "summary": "GET /api/ui/case/steps/detailed/refresh",
    "status": "complete"
  },
  {
    "legacy_name": "run_ui_case",
    "domain": "ui",
    "command": "run-ui-case",
    "method": "GET",
    "path": "ui/case/test",
    "summary": "GET /api/ui/case/test",
    "status": "complete"
  },
  {
    "legacy_name": "run_ui_case_batch",
    "domain": "ui",
    "command": "run-ui-case-batch",
    "method": "POST",
    "path": "ui/case/batch",
    "summary": "POST /api/ui/case/batch",
    "status": "complete"
  },
  {
    "legacy_name": "preview_delete_ui_page_impact",
    "domain": "ui",
    "command": "preview-delete-ui-page-impact",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面缺少对应删除影响预览 API"
  },
  {
    "legacy_name": "delete_ui_page",
    "domain": "ui",
    "command": "delete-ui-page",
    "method": "DELETE",
    "path": "ui/page",
    "summary": "DELETE /api/ui/page",
    "status": "complete"
  },
  {
    "legacy_name": "preview_delete_ui_element_impact",
    "domain": "ui",
    "command": "preview-delete-ui-element-impact",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面缺少对应删除影响预览 API"
  },
  {
    "legacy_name": "delete_ui_element",
    "domain": "ui",
    "command": "delete-ui-element",
    "method": "DELETE",
    "path": "ui/element",
    "summary": "DELETE /api/ui/element",
    "status": "complete"
  },
  {
    "legacy_name": "preview_delete_ui_page_step_impact",
    "domain": "ui",
    "command": "preview-delete-ui-page-step-impact",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面缺少对应删除影响预览 API"
  },
  {
    "legacy_name": "delete_ui_page_step",
    "domain": "ui",
    "command": "delete-ui-page-step",
    "method": "DELETE",
    "path": "ui/page/steps",
    "summary": "DELETE /api/ui/page/steps",
    "status": "complete"
  },
  {
    "legacy_name": "preview_delete_ui_page_step_detail_impact",
    "domain": "ui",
    "command": "preview-delete-ui-page-step-detail-impact",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面缺少对应删除影响预览 API"
  },
  {
    "legacy_name": "delete_ui_page_step_detail",
    "domain": "ui",
    "command": "delete-ui-page-step-detail",
    "method": "DELETE",
    "path": "ui/page/steps/detailed",
    "summary": "DELETE /api/ui/page/steps/detailed",
    "status": "complete"
  },
  {
    "legacy_name": "preview_delete_ui_case_impact",
    "domain": "ui",
    "command": "preview-delete-ui-case-impact",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面缺少对应删除影响预览 API"
  },
  {
    "legacy_name": "delete_ui_case",
    "domain": "ui",
    "command": "delete-ui-case",
    "method": "DELETE",
    "path": "ui/case",
    "summary": "DELETE /api/ui/case",
    "status": "complete"
  },
  {
    "legacy_name": "preview_delete_ui_case_step_impact",
    "domain": "ui",
    "command": "preview-delete-ui-case-step-impact",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面缺少对应删除影响预览 API"
  },
  {
    "legacy_name": "delete_ui_case_step",
    "domain": "ui",
    "command": "delete-ui-case-step",
    "method": "DELETE",
    "path": "ui/case/steps/detailed",
    "summary": "DELETE /api/ui/case/steps/detailed",
    "status": "complete"
  },
  {
    "legacy_name": "search_ui_elements",
    "domain": "ui",
    "command": "search-ui-elements",
    "method": "GET",
    "path": "ui/element",
    "summary": "GET /api/ui/element",
    "status": "complete"
  },
  {
    "legacy_name": "get_ui_element_detail",
    "domain": "ui",
    "command": "get-ui-element-detail",
    "method": "GET",
    "path": "ui/element",
    "summary": "GET /api/ui/element",
    "status": "complete"
  },
  {
    "legacy_name": "create_ui_element",
    "domain": "ui",
    "command": "create-ui-element",
    "method": "POST",
    "path": "ui/element",
    "summary": "POST /api/ui/element",
    "status": "complete"
  },
  {
    "legacy_name": "update_ui_element",
    "domain": "ui",
    "command": "update-ui-element",
    "method": "PUT",
    "path": "ui/element",
    "summary": "PUT /api/ui/element",
    "status": "complete"
  },
  {
    "legacy_name": "list_ui_element_categories",
    "domain": "ui",
    "command": "list-ui-element-categories",
    "method": "GET",
    "path": "ui/element/category",
    "summary": "GET /api/ui/element/category",
    "status": "complete"
  },
  {
    "legacy_name": "get_ui_element_ai_info",
    "domain": "ui",
    "command": "get-ui-element-ai-info",
    "method": "GET",
    "path": "ui/element/ai/info",
    "summary": "GET /api/ui/element/ai/info",
    "status": "complete"
  },
  {
    "legacy_name": "create_ui_element_snapshot",
    "domain": "ui",
    "command": "create-ui-element-snapshot",
    "method": "POST",
    "path": "ui/element/ai/snapshot",
    "summary": "POST /api/ui/element/ai/snapshot",
    "status": "complete"
  },
  {
    "legacy_name": "create_ui_element_heal_record",
    "domain": "ui",
    "command": "create-ui-element-heal-record",
    "method": "POST",
    "path": "ui/element/ai/heal-record",
    "summary": "POST /api/ui/element/ai/heal-record",
    "status": "complete"
  },
  {
    "legacy_name": "update_ui_element_from_heal_record",
    "domain": "ui",
    "command": "update-ui-element-from-heal-record",
    "method": "PUT",
    "path": "ui/element/ai/heal-record/apply",
    "summary": "PUT /api/ui/element/ai/heal-record/apply",
    "status": "complete"
  },
  {
    "legacy_name": "update_ui_element_ai_records_page",
    "domain": "ui",
    "command": "update-ui-element-ai-records-page",
    "method": "PUT",
    "path": "ui/element",
    "summary": "PUT /api/ui/element",
    "status": "complete"
  },
  {
    "legacy_name": "set_ui_element_iframe",
    "domain": "ui",
    "command": "set-ui-element-iframe",
    "method": "PUT",
    "path": "ui/element/iframe",
    "summary": "PUT /api/ui/element/iframe",
    "status": "complete"
  },
  {
    "legacy_name": "test_ui_element",
    "domain": "ui",
    "command": "test-ui-element",
    "method": "POST",
    "path": "ui/element/check",
    "summary": "POST /api/ui/element/check",
    "status": "complete"
  },
  {
    "legacy_name": "get_ui_operation_methods",
    "domain": "ui",
    "command": "get-ui-operation-methods",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面缺少与 MCP 返回内容等价的 Schema/方法目录 API"
  },
  {
    "legacy_name": "get_ui_assertion_methods",
    "domain": "ui",
    "command": "get-ui-assertion-methods",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面缺少与 MCP 返回内容等价的 Schema/方法目录 API"
  },
  {
    "legacy_name": "get_ui_public_assertion_methods",
    "domain": "ui",
    "command": "get-ui-public-assertion-methods",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面缺少与 MCP 返回内容等价的 Schema/方法目录 API"
  },
  {
    "legacy_name": "search_ui_pages",
    "domain": "ui",
    "command": "search-ui-pages",
    "method": "GET",
    "path": "ui/page",
    "summary": "GET /api/ui/page",
    "status": "complete"
  },
  {
    "legacy_name": "get_ui_page_detail",
    "domain": "ui",
    "command": "get-ui-page-detail",
    "method": "GET",
    "path": "ui/page",
    "summary": "GET /api/ui/page",
    "status": "complete"
  },
  {
    "legacy_name": "create_ui_page",
    "domain": "ui",
    "command": "create-ui-page",
    "method": "POST",
    "path": "ui/page",
    "summary": "POST /api/ui/page",
    "status": "complete"
  },
  {
    "legacy_name": "update_ui_page",
    "domain": "ui",
    "command": "update-ui-page",
    "method": "PUT",
    "path": "ui/page",
    "summary": "PUT /api/ui/page",
    "status": "complete"
  },
  {
    "legacy_name": "search_ui_page_steps",
    "domain": "ui",
    "command": "search-ui-page-steps",
    "method": "GET",
    "path": "ui/page/steps",
    "summary": "GET /api/ui/page/steps",
    "status": "complete"
  },
  {
    "legacy_name": "get_ui_page_step_detail_full",
    "domain": "ui",
    "command": "get-ui-page-step-detail-full",
    "method": "GET",
    "path": "ui/page/steps",
    "summary": "GET /api/ui/page/steps",
    "status": "complete"
  },
  {
    "legacy_name": "create_ui_page_step",
    "domain": "ui",
    "command": "create-ui-page-step",
    "method": "POST",
    "path": "ui/page/steps",
    "summary": "POST /api/ui/page/steps",
    "status": "complete"
  },
  {
    "legacy_name": "update_ui_page_step",
    "domain": "ui",
    "command": "update-ui-page-step",
    "method": "PUT",
    "path": "ui/page/steps",
    "summary": "PUT /api/ui/page/steps",
    "status": "complete"
  },
  {
    "legacy_name": "run_ui_page_step",
    "domain": "ui",
    "command": "run-ui-page-step",
    "method": "GET",
    "path": "ui/page/steps/test",
    "summary": "GET /api/ui/page/steps/test",
    "status": "complete"
  },
  {
    "legacy_name": "list_ui_page_step_details",
    "domain": "ui",
    "command": "list-ui-page-step-details",
    "method": "GET",
    "path": "ui/page/steps/detailed",
    "summary": "GET /api/ui/page/steps/detailed",
    "status": "complete"
  },
  {
    "legacy_name": "create_ui_page_step_detail",
    "domain": "ui",
    "command": "create-ui-page-step-detail",
    "method": "POST",
    "path": "ui/page/steps/detailed",
    "summary": "POST /api/ui/page/steps/detailed",
    "status": "complete"
  },
  {
    "legacy_name": "update_ui_page_step_detail",
    "domain": "ui",
    "command": "update-ui-page-step-detail",
    "method": "PUT",
    "path": "ui/page/steps/detailed",
    "summary": "PUT /api/ui/page/steps/detailed",
    "status": "complete"
  },
  {
    "legacy_name": "sort_ui_page_step_details",
    "domain": "ui",
    "command": "sort-ui-page-step-details",
    "method": "PUT",
    "path": "ui/page/steps/detailed/sort",
    "summary": "PUT /api/ui/page/steps/detailed/sort",
    "status": "complete"
  },
  {
    "legacy_name": "import_ui_page_step_from_playwright_code",
    "domain": "ui",
    "command": "import-ui-page-step-from-playwright-code",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面缺少 Playwright 代码原子导入 API"
  },
  {
    "legacy_name": "list_ui_public_variables",
    "domain": "ui",
    "command": "list-ui-public-variables",
    "method": "GET",
    "path": "ui/public",
    "summary": "GET /api/ui/public",
    "status": "complete"
  },
  {
    "legacy_name": "create_ui_public_variable",
    "domain": "ui",
    "command": "create-ui-public-variable",
    "method": "POST",
    "path": "ui/public",
    "summary": "POST /api/ui/public",
    "status": "complete"
  },
  {
    "legacy_name": "update_ui_public_variable",
    "domain": "ui",
    "command": "update-ui-public-variable",
    "method": "PUT",
    "path": "ui/public",
    "summary": "PUT /api/ui/public",
    "status": "complete"
  },
  {
    "legacy_name": "set_ui_public_variable_status",
    "domain": "ui",
    "command": "set-ui-public-variable-status",
    "method": "PUT",
    "path": "ui/public/status",
    "summary": "PUT /api/ui/public/status",
    "status": "complete"
  },
  {
    "legacy_name": "get_ui_automation_schema",
    "domain": "ui",
    "command": "get-ui-automation-schema",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面缺少与 MCP 返回内容等价的 Schema/方法目录 API"
  },
  {
    "legacy_name": "list_data_factory_case_configs",
    "domain": "data-factory",
    "command": "list-data-factory-case-configs",
    "method": "GET",
    "path": "data-factory/case-config",
    "summary": "GET /api/data-factory/case-config",
    "status": "complete"
  },
  {
    "legacy_name": "bind_data_factory_to_case_source",
    "domain": "data-factory",
    "command": "bind-data-factory-to-case-source",
    "method": "POST",
    "path": "data-factory/case-config",
    "summary": "POST /api/data-factory/case-config",
    "status": "complete"
  },
  {
    "legacy_name": "update_data_factory_case_config",
    "domain": "data-factory",
    "command": "update-data-factory-case-config",
    "method": "PUT",
    "path": "data-factory/case-config",
    "summary": "PUT /api/data-factory/case-config",
    "status": "complete"
  },
  {
    "legacy_name": "sort_data_factory_case_configs",
    "domain": "data-factory",
    "command": "sort-data-factory-case-configs",
    "method": "PUT",
    "path": "data-factory/case-config/sort",
    "summary": "PUT /api/data-factory/case-config/sort",
    "status": "complete"
  },
  {
    "legacy_name": "preview_data_factory_case_config",
    "domain": "data-factory",
    "command": "preview-data-factory-case-config",
    "method": "POST",
    "path": "data-factory/case-config/preview",
    "summary": "POST /api/data-factory/case-config/preview",
    "status": "complete"
  },
  {
    "legacy_name": "list_data_factory_datasource_aliases",
    "domain": "data-factory",
    "command": "list-data-factory-datasource-aliases",
    "method": "GET",
    "path": "data-factory/datasource-alias",
    "summary": "GET /api/data-factory/datasource-alias",
    "status": "complete"
  },
  {
    "legacy_name": "create_data_factory_datasource_alias",
    "domain": "data-factory",
    "command": "create-data-factory-datasource-alias",
    "method": "POST",
    "path": "data-factory/datasource-alias",
    "summary": "POST /api/data-factory/datasource-alias",
    "status": "complete"
  },
  {
    "legacy_name": "list_data_factory_datasource_bindings",
    "domain": "data-factory",
    "command": "list-data-factory-datasource-bindings",
    "method": "GET",
    "path": "data-factory/datasource-binding",
    "summary": "GET /api/data-factory/datasource-binding",
    "status": "complete"
  },
  {
    "legacy_name": "create_data_factory_datasource_binding",
    "domain": "data-factory",
    "command": "create-data-factory-datasource-binding",
    "method": "POST",
    "path": "data-factory/datasource-binding",
    "summary": "POST /api/data-factory/datasource-binding",
    "status": "complete"
  },
  {
    "legacy_name": "update_data_factory_datasource_binding",
    "domain": "data-factory",
    "command": "update-data-factory-datasource-binding",
    "method": "PUT",
    "path": "data-factory/datasource-binding",
    "summary": "PUT /api/data-factory/datasource-binding",
    "status": "complete"
  },
  {
    "legacy_name": "test_data_factory_datasource_connection",
    "domain": "data-factory",
    "command": "test-data-factory-datasource-connection",
    "method": "POST",
    "path": "data-factory/data-source/execute",
    "summary": "POST /api/data-factory/data-source/execute",
    "status": "complete"
  },
  {
    "legacy_name": "list_data_factory_database_tables",
    "domain": "data-factory",
    "command": "list-data-factory-database-tables",
    "method": "POST",
    "path": "data-factory/discover/tables",
    "summary": "POST /api/data-factory/discover/tables",
    "status": "complete"
  },
  {
    "legacy_name": "get_data_factory_table_schema",
    "domain": "data-factory",
    "command": "get-data-factory-table-schema",
    "method": "POST",
    "path": "data-factory/discover/table",
    "summary": "POST /api/data-factory/discover/table",
    "status": "complete"
  },
  {
    "legacy_name": "query_data_factory_datasource_sql",
    "domain": "data-factory",
    "command": "query-data-factory-datasource-sql",
    "method": "POST",
    "path": "data-factory/data-source/execute",
    "summary": "POST /api/data-factory/data-source/execute",
    "status": "complete"
  },
  {
    "legacy_name": "query_data_factory_datasource_redis",
    "domain": "data-factory",
    "command": "query-data-factory-datasource-redis",
    "method": "POST",
    "path": "data-factory/data-source/execute",
    "summary": "POST /api/data-factory/data-source/execute",
    "status": "complete"
  },
  {
    "legacy_name": "query_data_factory_datasource_elasticsearch",
    "domain": "data-factory",
    "command": "query-data-factory-datasource-elasticsearch",
    "method": "POST",
    "path": "data-factory/data-source/execute",
    "summary": "POST /api/data-factory/data-source/execute",
    "status": "complete"
  },
  {
    "legacy_name": "list_data_factory_entities",
    "domain": "data-factory",
    "command": "list-data-factory-entities",
    "method": "GET",
    "path": "data-factory/entity",
    "summary": "GET /api/data-factory/entity",
    "status": "complete"
  },
  {
    "legacy_name": "get_data_factory_entity_detail",
    "domain": "data-factory",
    "command": "get-data-factory-entity-detail",
    "method": "GET",
    "path": "data-factory/entity",
    "summary": "GET /api/data-factory/entity",
    "status": "complete"
  },
  {
    "legacy_name": "list_data_factory_entity_status_logs",
    "domain": "data-factory",
    "command": "list-data-factory-entity-status-logs",
    "method": "GET",
    "path": "data-factory/entity/status-log",
    "summary": "GET /api/data-factory/entity/status-log",
    "status": "complete"
  },
  {
    "legacy_name": "create_data_factory_entity",
    "domain": "data-factory",
    "command": "create-data-factory-entity",
    "method": "POST",
    "path": "data-factory/entity",
    "summary": "POST /api/data-factory/entity",
    "status": "complete"
  },
  {
    "legacy_name": "update_data_factory_entity",
    "domain": "data-factory",
    "command": "update-data-factory-entity",
    "method": "PUT",
    "path": "data-factory/entity",
    "summary": "PUT /api/data-factory/entity",
    "status": "complete"
  },
  {
    "legacy_name": "batch_generate_data_factory_entities",
    "domain": "data-factory",
    "command": "batch-generate-data-factory-entities",
    "method": "POST",
    "path": "data-factory/entity/batch-generate",
    "summary": "POST /api/data-factory/entity/batch-generate",
    "status": "complete"
  },
  {
    "legacy_name": "list_data_factory_executions",
    "domain": "data-factory",
    "command": "list-data-factory-executions",
    "method": "GET",
    "path": "data-factory/execution",
    "summary": "GET /api/data-factory/execution",
    "status": "complete"
  },
  {
    "legacy_name": "get_data_factory_execution_detail",
    "domain": "data-factory",
    "command": "get-data-factory-execution-detail",
    "method": "GET",
    "path": "data-factory/execution/detail",
    "summary": "GET /api/data-factory/execution/detail",
    "status": "complete"
  },
  {
    "legacy_name": "preview_cleanup_data_factory_execution_impact",
    "domain": "data-factory",
    "command": "preview-cleanup-data-factory-execution-impact",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面缺少执行记录清理影响预览 API"
  },
  {
    "legacy_name": "cleanup_data_factory_execution",
    "domain": "data-factory",
    "command": "cleanup-data-factory-execution",
    "method": "POST",
    "path": "data-factory/execution/cleanup",
    "summary": "POST /api/data-factory/execution/cleanup",
    "status": "complete"
  },
  {
    "legacy_name": "list_data_factory_fields",
    "domain": "data-factory",
    "command": "list-data-factory-fields",
    "method": "GET",
    "path": "data-factory/field",
    "summary": "GET /api/data-factory/field",
    "status": "complete"
  },
  {
    "legacy_name": "batch_save_data_factory_fields",
    "domain": "data-factory",
    "command": "batch-save-data-factory-fields",
    "method": "POST",
    "path": "data-factory/field/batch-save",
    "summary": "POST /api/data-factory/field/batch-save",
    "status": "complete"
  },
  {
    "legacy_name": "preview_data_factory_field_values",
    "domain": "data-factory",
    "command": "preview-data-factory-field-values",
    "method": "POST",
    "path": "data-factory/field/preview-values",
    "summary": "POST /api/data-factory/field/preview-values",
    "status": "complete"
  },
  {
    "legacy_name": "get_data_factory_schema",
    "domain": "data-factory",
    "command": "get-data-factory-schema",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面没有完整数据工厂 Schema API"
  },
  {
    "legacy_name": "list_data_factory_templates",
    "domain": "data-factory",
    "command": "list-data-factory-templates",
    "method": "GET",
    "path": "data-factory/template",
    "summary": "GET /api/data-factory/template",
    "status": "complete"
  },
  {
    "legacy_name": "get_data_factory_template_detail",
    "domain": "data-factory",
    "command": "get-data-factory-template-detail",
    "method": "GET",
    "path": "data-factory/template",
    "summary": "GET /api/data-factory/template",
    "status": "complete"
  },
  {
    "legacy_name": "create_data_factory_template",
    "domain": "data-factory",
    "command": "create-data-factory-template",
    "method": "POST",
    "path": "data-factory/template",
    "summary": "POST /api/data-factory/template",
    "status": "complete"
  },
  {
    "legacy_name": "update_data_factory_template",
    "domain": "data-factory",
    "command": "update-data-factory-template",
    "method": "PUT",
    "path": "data-factory/template",
    "summary": "PUT /api/data-factory/template",
    "status": "complete"
  },
  {
    "legacy_name": "preview_data_factory_template",
    "domain": "data-factory",
    "command": "preview-data-factory-template",
    "method": "POST",
    "path": "data-factory/template/preview",
    "summary": "POST /api/data-factory/template/preview",
    "status": "complete"
  },
  {
    "legacy_name": "preview_run_data_factory_template_impact",
    "domain": "data-factory",
    "command": "preview-run-data-factory-template-impact",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面缺少模板真实执行影响预览 API"
  },
  {
    "legacy_name": "execute_data_factory_template",
    "domain": "data-factory",
    "command": "execute-data-factory-template",
    "method": "POST",
    "path": "data-factory/template/debug-run",
    "summary": "POST /api/data-factory/template/debug-run",
    "status": "complete"
  },
  {
    "legacy_name": "set_data_factory_template_status",
    "domain": "data-factory",
    "command": "set-data-factory-template-status",
    "method": "PUT",
    "path": "data-factory/template/status",
    "summary": "PUT /api/data-factory/template/status",
    "status": "complete"
  },
  {
    "legacy_name": "preview_delete_data_factory_template_impact",
    "domain": "data-factory",
    "command": "preview-delete-data-factory-template-impact",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面缺少模板删除影响预览 API"
  },
  {
    "legacy_name": "delete_data_factory_template",
    "domain": "data-factory",
    "command": "delete-data-factory-template",
    "method": "DELETE",
    "path": "data-factory/template",
    "summary": "DELETE /api/data-factory/template",
    "status": "complete"
  },
  {
    "legacy_name": "list_functional_test_suites",
    "domain": "functional-test",
    "command": "list-functional-test-suites",
    "method": "GET",
    "path": "functional-test/suite",
    "summary": "GET /api/functional-test/suite",
    "status": "complete"
  },
  {
    "legacy_name": "get_functional_test_suite_detail",
    "domain": "functional-test",
    "command": "get-functional-test-suite-detail",
    "method": "GET",
    "path": "functional-test/suite",
    "summary": "GET /api/functional-test/suite",
    "status": "complete"
  },
  {
    "legacy_name": "create_functional_test_suite",
    "domain": "functional-test",
    "command": "create-functional-test-suite",
    "method": "POST",
    "path": "functional-test/suite",
    "summary": "POST /api/functional-test/suite",
    "status": "complete"
  },
  {
    "legacy_name": "update_functional_test_suite",
    "domain": "functional-test",
    "command": "update-functional-test-suite",
    "method": "PUT",
    "path": "functional-test/suite",
    "summary": "PUT /api/functional-test/suite",
    "status": "complete"
  },
  {
    "legacy_name": "delete_functional_test_suite",
    "domain": "functional-test",
    "command": "delete-functional-test-suite",
    "method": "DELETE",
    "path": "functional-test/suite",
    "summary": "DELETE /api/functional-test/suite",
    "status": "complete"
  },
  {
    "legacy_name": "list_functional_test_cases",
    "domain": "functional-test",
    "command": "list-functional-test-cases",
    "method": "GET",
    "path": "functional-test/case",
    "summary": "GET /api/functional-test/case",
    "status": "complete"
  },
  {
    "legacy_name": "get_functional_test_case_detail",
    "domain": "functional-test",
    "command": "get-functional-test-case-detail",
    "method": "GET",
    "path": "functional-test/case/detail",
    "summary": "GET /api/functional-test/case/detail",
    "status": "complete"
  },
  {
    "legacy_name": "create_functional_test_case",
    "domain": "functional-test",
    "command": "create-functional-test-case",
    "method": "POST",
    "path": "functional-test/case",
    "summary": "POST /api/functional-test/case",
    "status": "complete"
  },
  {
    "legacy_name": "update_functional_test_case",
    "domain": "functional-test",
    "command": "update-functional-test-case",
    "method": "PUT",
    "path": "functional-test/case",
    "summary": "PUT /api/functional-test/case",
    "status": "complete"
  },
  {
    "legacy_name": "delete_functional_test_case",
    "domain": "functional-test",
    "command": "delete-functional-test-case",
    "method": "DELETE",
    "path": "functional-test/case",
    "summary": "DELETE /api/functional-test/case",
    "status": "complete"
  },
  {
    "legacy_name": "batch_delete_functional_test_cases",
    "domain": "functional-test",
    "command": "batch-delete-functional-test-cases",
    "method": "DELETE",
    "path": "functional-test/case",
    "summary": "DELETE /api/functional-test/case",
    "status": "complete"
  },
  {
    "legacy_name": "list_functional_test_context_resources",
    "domain": "functional-test",
    "command": "list-functional-test-context-resources",
    "method": "GET",
    "path": "functional-test/context-resource",
    "summary": "GET /api/functional-test/context-resource",
    "status": "complete"
  },
  {
    "legacy_name": "get_functional_test_context_resource_detail",
    "domain": "functional-test",
    "command": "get-functional-test-context-resource-detail",
    "method": "GET",
    "path": "functional-test/context-resource",
    "summary": "GET /api/functional-test/context-resource",
    "status": "complete"
  },
  {
    "legacy_name": "create_functional_test_context_resource",
    "domain": "functional-test",
    "command": "create-functional-test-context-resource",
    "method": "POST",
    "path": "functional-test/context-resource",
    "summary": "POST /api/functional-test/context-resource",
    "status": "complete"
  },
  {
    "legacy_name": "update_functional_test_context_resource",
    "domain": "functional-test",
    "command": "update-functional-test-context-resource",
    "method": "PUT",
    "path": "functional-test/context-resource",
    "summary": "PUT /api/functional-test/context-resource",
    "status": "complete"
  },
  {
    "legacy_name": "delete_functional_test_context_resource",
    "domain": "functional-test",
    "command": "delete-functional-test-context-resource",
    "method": "DELETE",
    "path": "functional-test/context-resource",
    "summary": "DELETE /api/functional-test/context-resource",
    "status": "complete"
  },
  {
    "legacy_name": "list_functional_test_automation_bindings",
    "domain": "functional-test",
    "command": "list-functional-test-automation-bindings",
    "method": "GET",
    "path": "functional-test/case/automation/binding",
    "summary": "GET /api/functional-test/case/automation/binding",
    "status": "complete"
  },
  {
    "legacy_name": "bind_functional_test_automation_case",
    "domain": "functional-test",
    "command": "bind-functional-test-automation-case",
    "method": "POST",
    "path": "functional-test/case/automation/bind",
    "summary": "POST /api/functional-test/case/automation/bind",
    "status": "complete"
  },
  {
    "legacy_name": "list_functional_test_case_modules",
    "domain": "functional-test",
    "command": "list-functional-test-case-modules",
    "method": "GET",
    "path": "functional-test/case/modules",
    "summary": "GET /api/functional-test/case/modules",
    "status": "complete"
  },
  {
    "legacy_name": "get_functional_test_suite_stats",
    "domain": "functional-test",
    "command": "get-functional-test-suite-stats",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面没有刷新并返回完整需求统计的等价 API"
  },
  {
    "legacy_name": "list_functional_test_plans",
    "domain": "functional-test",
    "command": "list-functional-test-plans",
    "method": "GET",
    "path": "functional-test/plan",
    "summary": "GET /api/functional-test/plan",
    "status": "complete"
  },
  {
    "legacy_name": "create_functional_test_plan",
    "domain": "functional-test",
    "command": "create-functional-test-plan",
    "method": "POST",
    "path": "functional-test/plan",
    "summary": "POST /api/functional-test/plan",
    "status": "complete"
  },
  {
    "legacy_name": "add_functional_test_plan_cases",
    "domain": "functional-test",
    "command": "add-functional-test-plan-cases",
    "method": "POST",
    "path": "functional-test/plan/case/add",
    "summary": "POST /api/functional-test/plan/case/add",
    "status": "complete"
  },
  {
    "legacy_name": "start_functional_test_plan",
    "domain": "functional-test",
    "command": "start-functional-test-plan",
    "method": "POST",
    "path": "functional-test/plan/start",
    "summary": "POST /api/functional-test/plan/start",
    "status": "complete"
  },
  {
    "legacy_name": "update_functional_test_plan_case",
    "domain": "functional-test",
    "command": "update-functional-test-plan-case",
    "method": "PUT",
    "path": "functional-test/plan/case",
    "summary": "PUT /api/functional-test/plan/case",
    "status": "complete"
  },
  {
    "legacy_name": "finish_functional_test_plan",
    "domain": "functional-test",
    "command": "finish-functional-test-plan",
    "method": "POST",
    "path": "functional-test/plan/finish",
    "summary": "POST /api/functional-test/plan/finish",
    "status": "complete"
  },
  {
    "legacy_name": "search_pytest_cases",
    "domain": "pytest",
    "command": "search-pytest-cases",
    "method": "GET",
    "path": "pytest/case",
    "summary": "GET /api/pytest/case",
    "status": "complete"
  },
  {
    "legacy_name": "get_pytest_case_detail",
    "domain": "pytest",
    "command": "get-pytest-case-detail",
    "method": "GET",
    "path": "pytest/case",
    "summary": "GET /api/pytest/case",
    "status": "complete"
  },
  {
    "legacy_name": "sync_pytest_cases",
    "domain": "pytest",
    "command": "sync-pytest-cases",
    "method": "POST",
    "path": "pytest/case/update",
    "summary": "POST /api/pytest/case/update",
    "status": "complete"
  },
  {
    "legacy_name": "read_pytest_case_file",
    "domain": "pytest",
    "command": "read-pytest-case-file",
    "method": "GET",
    "path": "pytest/case/read",
    "summary": "GET /api/pytest/case/read",
    "status": "complete"
  },
  {
    "legacy_name": "preview_update_pytest_case_file_impact",
    "domain": "pytest",
    "command": "preview-update-pytest-case-file-impact",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面缺少对应危险操作影响预览 API"
  },
  {
    "legacy_name": "update_pytest_case_file",
    "domain": "pytest",
    "command": "update-pytest-case-file",
    "method": "POST",
    "path": "pytest/case/write",
    "summary": "POST /api/pytest/case/write",
    "status": "complete"
  },
  {
    "legacy_name": "run_pytest_case",
    "domain": "pytest",
    "command": "run-pytest-case",
    "method": "GET",
    "path": "pytest/case/test",
    "summary": "GET /api/pytest/case/test",
    "status": "complete"
  },
  {
    "legacy_name": "run_pytest_case_batch",
    "domain": "pytest",
    "command": "run-pytest-case-batch",
    "method": "POST",
    "path": "pytest/case/batch",
    "summary": "POST /api/pytest/case/batch",
    "status": "complete"
  },
  {
    "legacy_name": "preview_delete_pytest_case_impact",
    "domain": "pytest",
    "command": "preview-delete-pytest-case-impact",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面缺少对应危险操作影响预览 API"
  },
  {
    "legacy_name": "delete_pytest_case",
    "domain": "pytest",
    "command": "delete-pytest-case",
    "method": "DELETE",
    "path": "pytest/case",
    "summary": "DELETE /api/pytest/case",
    "status": "complete"
  },
  {
    "legacy_name": "list_pytest_products",
    "domain": "pytest",
    "command": "list-pytest-products",
    "method": "GET",
    "path": "pytest/product",
    "summary": "GET /api/pytest/product",
    "status": "complete"
  },
  {
    "legacy_name": "get_pytest_product_detail",
    "domain": "pytest",
    "command": "get-pytest-product-detail",
    "method": "GET",
    "path": "pytest/product",
    "summary": "GET /api/pytest/product",
    "status": "complete"
  },
  {
    "legacy_name": "create_pytest_product",
    "domain": "pytest",
    "command": "create-pytest-product",
    "method": "POST",
    "path": "pytest/product",
    "summary": "POST /api/pytest/product",
    "status": "complete"
  },
  {
    "legacy_name": "update_pytest_product",
    "domain": "pytest",
    "command": "update-pytest-product",
    "method": "PUT",
    "path": "pytest/product",
    "summary": "PUT /api/pytest/product",
    "status": "complete"
  },
  {
    "legacy_name": "sync_pytest_products_from_repo",
    "domain": "pytest",
    "command": "sync-pytest-products-from-repo",
    "method": "GET",
    "path": "pytest/product/update",
    "summary": "GET /api/pytest/product/update",
    "status": "complete"
  },
  {
    "legacy_name": "read_pytest_product_init_file",
    "domain": "pytest",
    "command": "read-pytest-product-init-file",
    "method": "GET",
    "path": "pytest/product/read",
    "summary": "GET /api/pytest/product/read",
    "status": "complete"
  },
  {
    "legacy_name": "preview_update_pytest_product_init_file_impact",
    "domain": "pytest",
    "command": "preview-update-pytest-product-init-file-impact",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面缺少对应危险操作影响预览 API"
  },
  {
    "legacy_name": "update_pytest_product_init_file",
    "domain": "pytest",
    "command": "update-pytest-product-init-file",
    "method": "POST",
    "path": "pytest/product/write",
    "summary": "POST /api/pytest/product/write",
    "status": "complete"
  },
  {
    "legacy_name": "preview_push_pytest_repo_impact",
    "domain": "pytest",
    "command": "preview-push-pytest-repo-impact",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面缺少对应危险操作影响预览 API"
  },
  {
    "legacy_name": "push_pytest_repo",
    "domain": "pytest",
    "command": "push-pytest-repo",
    "method": "POST",
    "path": "git/management/local/push",
    "summary": "POST /api/git/management/local/push",
    "status": "complete"
  },
  {
    "legacy_name": "preview_delete_pytest_product_impact",
    "domain": "pytest",
    "command": "preview-delete-pytest-product-impact",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面缺少对应危险操作影响预览 API"
  },
  {
    "legacy_name": "delete_pytest_product",
    "domain": "pytest",
    "command": "delete-pytest-product",
    "method": "DELETE",
    "path": "pytest/product",
    "summary": "DELETE /api/pytest/product",
    "status": "complete"
  },
  {
    "legacy_name": "get_pytest_automation_schema",
    "domain": "pytest",
    "command": "get-pytest-automation-schema",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面没有完整 Pytest 自动化 Schema API"
  },
  {
    "legacy_name": "list_execution_results",
    "domain": "result",
    "command": "list-execution-results",
    "method": "GET",
    "path": "system/execution/result/list",
    "summary": "GET /api/system/execution/result/list",
    "status": "complete"
  },
  {
    "legacy_name": "get_execution_result_detail",
    "domain": "result",
    "command": "get-execution-result-detail",
    "method": "GET",
    "path": "system/execution/result/detail",
    "summary": "GET /api/system/execution/result/detail",
    "status": "complete"
  },
  {
    "legacy_name": "get_latest_execution_result",
    "domain": "result",
    "command": "get-latest-execution-result",
    "method": "GET",
    "path": "system/execution/result/latest",
    "summary": "GET /api/system/execution/result/latest",
    "status": "complete"
  },
  {
    "legacy_name": "upload_test_report_diagnostic_markdown",
    "domain": "report",
    "command": "upload-test-report-diagnostic-markdown",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面只有诊断 Markdown 查询接口，没有上传绑定 API"
  },
  {
    "legacy_name": "get_test_report_schema",
    "domain": "report",
    "command": "get-test-report-schema",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面没有完整测试报告 Schema API"
  },
  {
    "legacy_name": "list_test_reports",
    "domain": "report",
    "command": "list-test-reports",
    "method": "GET",
    "path": "system/test/suite",
    "summary": "GET /api/system/test/suite",
    "status": "complete"
  },
  {
    "legacy_name": "get_test_report_detail",
    "domain": "report",
    "command": "get-test-report-detail",
    "method": "GET",
    "path": "system/test/suite",
    "summary": "GET /api/system/test/suite",
    "status": "complete"
  },
  {
    "legacy_name": "get_test_report_summary",
    "domain": "report",
    "command": "get-test-report-summary",
    "method": "GET",
    "path": "system/test/suite/details/summary",
    "summary": "GET /api/system/test/suite/details/summary",
    "status": "complete"
  },
  {
    "legacy_name": "list_test_report_cases",
    "domain": "report",
    "command": "list-test-report-cases",
    "method": "GET",
    "path": "system/test/suite/details",
    "summary": "GET /api/system/test/suite/details",
    "status": "complete"
  },
  {
    "legacy_name": "get_test_report_case_detail",
    "domain": "report",
    "command": "get-test-report-case-detail",
    "method": "GET",
    "path": "system/test/suite/details",
    "summary": "GET /api/system/test/suite/details",
    "status": "complete"
  },
  {
    "legacy_name": "analyze_test_report_failures",
    "domain": "report",
    "command": "analyze-test-report-failures",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面缺少失败聚类分析 API"
  },
  {
    "legacy_name": "retry_test_report_case",
    "domain": "report",
    "command": "retry-test-report-case",
    "method": "GET",
    "path": "system/test/suite/details/retry",
    "summary": "GET /api/system/test/suite/details/retry",
    "status": "complete"
  },
  {
    "legacy_name": "retry_test_report",
    "domain": "report",
    "command": "retry-test-report",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面重试接口缺少服务端 preview token 约束"
  },
  {
    "legacy_name": "upload_scheduled_task_diagnostic_markdown",
    "domain": "task",
    "command": "upload-scheduled-task-diagnostic-markdown",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面只有诊断 Markdown 查询接口，没有上传绑定 API"
  },
  {
    "legacy_name": "list_scheduled_task_strategies",
    "domain": "task",
    "command": "list-scheduled-task-strategies",
    "method": "GET",
    "path": "system/tasks/execution/options",
    "summary": "GET /api/system/tasks/execution/options",
    "status": "complete"
  },
  {
    "legacy_name": "list_scheduled_tasks",
    "domain": "task",
    "command": "list-scheduled-tasks",
    "method": "GET",
    "path": "system/tasks",
    "summary": "GET /api/system/tasks",
    "status": "complete"
  },
  {
    "legacy_name": "get_scheduled_task_detail",
    "domain": "task",
    "command": "get-scheduled-task-detail",
    "method": "GET",
    "path": "system/tasks",
    "summary": "GET /api/system/tasks",
    "status": "complete"
  },
  {
    "legacy_name": "list_scheduled_task_cases",
    "domain": "task",
    "command": "list-scheduled-task-cases",
    "method": "GET",
    "path": "system/tasks/selection/cases",
    "summary": "GET /api/system/tasks/selection/cases",
    "status": "complete"
  },
  {
    "legacy_name": "preview_trigger_scheduled_task_impact",
    "domain": "task",
    "command": "preview-trigger-scheduled-task-impact",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面手动触发 API 缺少等价的 preview/confirm 契约"
  },
  {
    "legacy_name": "trigger_scheduled_task",
    "domain": "task",
    "command": "trigger-scheduled-task",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面手动触发 API 缺少等价的 preview/confirm 契约"
  },
  {
    "legacy_name": "preview_bind_cases_to_scheduled_task_impact",
    "domain": "task",
    "command": "preview-bind-cases-to-scheduled-task-impact",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面批量设置接口与 MCP 增量绑定/解绑及 preview 契约不等价"
  },
  {
    "legacy_name": "bind_cases_to_scheduled_task",
    "domain": "task",
    "command": "bind-cases-to-scheduled-task",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面批量设置接口与 MCP 增量绑定/解绑及 preview 契约不等价"
  },
  {
    "legacy_name": "preview_unbind_cases_from_scheduled_task_impact",
    "domain": "task",
    "command": "preview-unbind-cases-from-scheduled-task-impact",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面批量设置接口与 MCP 增量绑定/解绑及 preview 契约不等价"
  },
  {
    "legacy_name": "unbind_cases_from_scheduled_task",
    "domain": "task",
    "command": "unbind-cases-from-scheduled-task",
    "summary": "等待后端 REST API",
    "status": "pending_api",
    "reason": "页面批量设置接口与 MCP 增量绑定/解绑及 preview 契约不等价"
  }
]);
