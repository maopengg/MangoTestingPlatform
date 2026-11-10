import type { ActuatorConfig, PartialConfig } from './types'
export const normalizeConfig = (config: PartialConfig = {}): ActuatorConfig => ({
  server: {
    host: config.server?.host || '',
    ws: config.server?.ws || '',
    proxy_url: config.server?.proxy_url || '',
    username: config.server?.username || '',
  },
  ui: {
    web_type: Number(config.ui?.web_type ?? 0),
    web_path: config.ui?.web_path || '',
    web_parallel: Number(config.ui?.web_parallel ?? 5),
    ui_queue_size: Number(config.ui?.ui_queue_size ?? 10),
    web_h5: config.ui?.web_h5 || '',
    web_max: Boolean(config.ui?.web_max),
    web_recording: Boolean(config.ui?.web_recording),
    web_headers: Boolean(config.ui?.web_headers),
    web_step_screenshot: Boolean(config.ui?.web_step_screenshot),
    web_static_cache_enabled: Boolean(config.ui?.web_static_cache_enabled),
    web_static_cache_path: config.ui?.web_static_cache_path || '',
  },
  pytest: {
    pytest_parallel: Number(config.pytest?.pytest_parallel ?? 5),
    pytest_queue_size: Number(config.pytest?.pytest_queue_size ?? 10),
  },
  runtime: {
    is_open: Boolean(config.runtime?.is_open),
    debug: Boolean(config.runtime?.debug),
    web_live_stream_supported: Boolean(config.runtime?.web_live_stream_supported),
  },
})
