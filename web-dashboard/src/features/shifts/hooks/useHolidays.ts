import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { shiftApi } from '@/features/shifts/api/shift.api'

export function useHolidays(year: number) {
  return useQuery({ queryFn: () => shiftApi.listHolidays(year), queryKey: ['holidays', year] })
}

export function useCreateHoliday() {
  const client = useQueryClient()
  return useMutation({ mutationFn: shiftApi.createHoliday, onSuccess: () => client.invalidateQueries({ queryKey: ['holidays'] }) })
}

export function useUpdateHoliday() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: ({ holidayId, payload }: { holidayId: number; payload: Parameters<typeof shiftApi.updateHoliday>[1] }) => shiftApi.updateHoliday(holidayId, payload),
    onSuccess: () => client.invalidateQueries({ queryKey: ['holidays'] }),
  })
}

export function useDeleteHoliday() {
  const client = useQueryClient()
  return useMutation({ mutationFn: shiftApi.deleteHoliday, onSuccess: () => client.invalidateQueries({ queryKey: ['holidays'] }) })
}
