import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { correctionApi } from '@/features/corrections/api/correction.api'
import type {
  CorrectionListParams,
  ReviewCorrectionPayload,
} from '@/features/corrections/types/correction.types'

export function useCorrectionRequests(params: CorrectionListParams, enabled = true) {
  return useQuery({
    enabled,
    queryFn: () => correctionApi.listRequests(params),
    queryKey: ['correction-requests', params],
  })
}

export function useCorrectionLogs(requestId?: string) {
  return useQuery({
    enabled: Boolean(requestId),
    queryFn: () => correctionApi.listLogs(requestId!),
    queryKey: ['correction-logs', requestId],
  })
}

export function useReviewCorrection() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      payload,
      requestId,
    }: {
      payload: ReviewCorrectionPayload
      requestId: string
    }) => correctionApi.reviewRequest(requestId, payload),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['correction-requests'] })
      queryClient.invalidateQueries({ queryKey: ['correction-logs', variables.requestId] })
    },
  })
}
