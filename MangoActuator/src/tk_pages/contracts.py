"""Visible UI contracts that must remain stable during the tkinter migration."""

VISIBLE_CONFIG_KEYS = {
    "login": ("host", "proxy_url", "username", "password", "remember_password"),
    "web": (
        "web_type", "web_path", "web_parallel", "ui_queue_size", "web_h5",
        "web_max", "web_recording", "web_headers", "web_step_screenshot",
        "web_static_cache_enabled",
    ),
    "android": ("and_equipment",),
    "ios": (
        "ios_appium_url", "ios_device_name", "ios_udid", "ios_platform_version",
        "ios_xcode_org_id", "ios_wda_bundle_id",
    ),
    "pytest": ("pytest_parallel", "pytest_queue_size"),
}

HOME_VISIBLE_FIELDS = (
    "connection_status", "username", "host", "ws", "receive_mode", "open",
    "task_status", "active_count", "task_name", "task_type", "task_id", "current_action",
    "started_at", "elapsed", "progress", "recent_result", "local_directories",
)

LOG_VISIBLE_FIELDS = (
    "logs", "log_count", "level_filter", "display_limit", "keyword_search", "debug",
    "auto_scroll", "open_log_directory", "clear_logs",
)
