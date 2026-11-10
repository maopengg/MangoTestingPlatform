import { deleted, get, post, put } from '@/api/http'
import type { FlowData } from '@/types/components'
import type { UiPageStepsDetailPayload } from '@/types/ui-test/case'

export function getUiPageStepsDetailed(id: any) {
  return get({
    url: '/ui/page/steps/detailed',
    data: () => {
      return {
        page_step_id: id,
      }
    },
  })
}

export function getUiPageStepsDetailedById(id: any) {
  return get({
    url: '/ui/page/steps/detailed',
    data: () => {
      return {
        id,
      }
    },
  })
}

export function postUiPageStepsDetailed(data: UiPageStepsDetailPayload, parent_id: any) {
  data.parent_id = parent_id
  return post({
    url: '/ui/page/steps/detailed',
    data: () => {
      return data
    },
  })
}

export function postUiPageStepNodeCopy(data: {
  page_step_id: number | string
  source_detail_id: number | string
  node_id: string
  flow_data: FlowData
}) {
  return post({
    url: '/ui/page/steps/detailed/copy',
    data: () => data,
  })
}

export function putUiPageStepsDetailed(data: UiPageStepsDetailPayload, parent_id: any) {
  data.parent_id = parent_id
  return put({
    url: '/ui/page/steps/detailed',
    data: () => {
      return data
    },
  })
}

export function deleteUiPageStepsDetailed(id: number | string | Array<number | string>, parentId: number | string) {
  return deleted({
    url: '/ui/page/steps/detailed',
    data: () => {
      return {
        id: id,
        parent_id: parentId,
      }
    },
  })
}

// export function getUiPageStepsDetailedOpe(pageType: any) {
//   return get({
//     url: '/ui/page/steps/detailed/ope',
//     data: () => {
//       return {
//         page_type: pageType,
//       }
//     },
//   })
// }
//
// export function getUiPageStepsDetailedAss(pageType: any) {
//   return get({
//     url: '/ui/page/steps/detailed/ass',
//     data: () => {
//       return {
//         page_type: pageType,
//       }
//     },
//   })
// }

// export function getUiPageAssMethod() {
//   return get({
//     url: '/ui/page/steps/detailed/ass/method',
//     data: () => {
//       return {}
//     },
//   })
// }

export function putUiPagePutStepSort(data: any) {
  return put({
    url: '/ui/page/steps/detailed/sort',
    data: () => {
      return {
        step_sort_list: data,
      }
    },
  })
}
