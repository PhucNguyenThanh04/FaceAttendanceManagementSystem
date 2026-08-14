import { useMutation, useQueryClient } from '@tanstack/react-query'
import { positionApi } from '@/features/positions/api/position.api'

export function useCreatePosition() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: positionApi.createPosition,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['positions'] })
    },
  })
}

export function useUpdatePosition() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ positionId, payload }: { positionId: number; payload: Parameters<typeof positionApi.updatePosition>[1] }) => positionApi.updatePosition(positionId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['positions'] }),
  })
}

export function useDeactivatePosition() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: positionApi.deactivatePosition,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['positions'] }),
  })
}

export function useDeletePosition() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: positionApi.deletePosition,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['positions'] }),
  })
}
