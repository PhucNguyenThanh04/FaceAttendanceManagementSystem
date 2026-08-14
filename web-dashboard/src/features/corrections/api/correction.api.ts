import { api } from '@/lib/axios'
import type {
  CorrectionListParams,
  CorrectionListResponse,
  CorrectionLog,
  CorrectionRequest,
  ReviewCorrectionPayload,
} from '@/features/corrections/types/correction.types'

export const correctionApi = {
  listRequests: async (params: CorrectionListParams): Promise<CorrectionListResponse> => {
    const response = await api.get<CorrectionListResponse>('/corrections/requests', { params })
    return response.data
  },
  getRequest: async (requestId: string): Promise<CorrectionRequest> => {
    const response = await api.get<CorrectionRequest>(`/corrections/requests/${requestId}`)
    return response.data
  },
  reviewRequest: async (
    requestId: string,
    payload: ReviewCorrectionPayload,
  ): Promise<CorrectionRequest> => {
    const response = await api.post<CorrectionRequest>(
      `/corrections/requests/${requestId}/review`,
      payload,
    )
    return response.data
  },
  listLogs: async (requestId: string): Promise<CorrectionLog[]> => {
    const response = await api.get<CorrectionLog[]>(`/corrections/requests/${requestId}/logs`)
    return response.data
  },
}
