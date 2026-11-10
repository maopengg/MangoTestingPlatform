export interface ContentTarget {
  yamlId: number
  bindingId: number
  repositoryId: number
  title: string
  filePath: string
}
export interface ContentDrawerHandle {
  open(target: ContentTarget): void
}
