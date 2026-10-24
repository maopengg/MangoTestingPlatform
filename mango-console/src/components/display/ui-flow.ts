export const UI_FLOW_NODE_WIDTH = 208
export const UI_FLOW_NODE_HEIGHT = 88
export const UI_FLOW_MIN_ZOOM = 0.25
export const UI_FLOW_MAX_ZOOM = 1.2
export const UI_FLOW_INITIAL_MAX_ZOOM = 0.85
export const UI_FLOW_RESPONSIVE_MAX_ZOOM = 1

export type UiFlowNodeTone =
  | 'pending'
  | 'ready'
  | 'passed'
  | 'running'
  | 'failed'
  | 'warning'
  | 'unsaved'
  | 'isolated'

export interface UiFlowNodeBadge {
  label: string
  title?: string
  tone?: UiFlowNodeTone
}
