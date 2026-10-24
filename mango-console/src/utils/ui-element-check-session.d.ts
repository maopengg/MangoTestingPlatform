export interface UiElementCheckSession {
  start(elementId: string | number, workspaceId?: string): number
  bindCheckId(token: number, checkId: string | number): boolean
  accept(result: Record<string, any>): boolean
  cancel(token?: number): boolean
  isActive(token?: number): boolean
}

export function createUiElementCheckSession(): UiElementCheckSession
