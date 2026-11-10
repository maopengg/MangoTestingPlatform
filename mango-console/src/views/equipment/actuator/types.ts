export interface ActuatorRecord {
  id: string | number
  name: string
  username: string
  ip: string
  type?: string
  is_open: boolean
  debug: boolean
  web_live_stream_supported?: boolean
}
export interface ActuatorConfig {
  server: { host: string; ws: string; proxy_url: string; username: string }
  ui: {
    web_type: number
    web_path: string
    web_parallel: number
    ui_queue_size: number
    web_h5: string
    web_max: boolean
    web_recording: boolean
    web_headers: boolean
    web_step_screenshot: boolean
    web_static_cache_enabled: boolean
    web_static_cache_path: string
  }
  pytest: { pytest_parallel: number; pytest_queue_size: number }
  runtime: { is_open: boolean; debug: boolean; web_live_stream_supported: boolean }
}
export interface ConfigResult {
  status?: string
  username?: string
  message?: string
  config?: PartialConfig
}
export interface ActuatorDraft extends Omit<ActuatorConfig, 'ui' | 'pytest'> {
  ui: Omit<ActuatorConfig['ui'], 'web_h5' | 'web_parallel' | 'ui_queue_size'> & {
    web_h5: string | undefined
    web_parallel: number | undefined
    ui_queue_size: number | undefined
  }
  pytest: { pytest_parallel: number | undefined; pytest_queue_size: number | undefined }
}
export interface PartialConfig {
  server?: Partial<ActuatorConfig['server']>
  ui?: Partial<ActuatorConfig['ui']>
  pytest?: Partial<ActuatorConfig['pytest']>
  runtime?: Partial<ActuatorConfig['runtime']>
}
export interface ConfigHandle {
  open(record: ActuatorRecord): void
  close(): void
}
