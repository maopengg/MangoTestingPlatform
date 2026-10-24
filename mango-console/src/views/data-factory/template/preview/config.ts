import { fieldRuleColumns } from '../../entity/config'

export const entityRuleColumns = fieldRuleColumns.filter((item) => item.key !== 'preview_value')

export const entityRuleTableScrollWidth = 1340
