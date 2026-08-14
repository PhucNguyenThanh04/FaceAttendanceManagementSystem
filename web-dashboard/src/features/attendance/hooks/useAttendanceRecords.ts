import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { attendanceApi } from '@/features/attendance/api/attendance.api'
import type {
  AttendanceRecordParams,
  AttendanceRecordUpdate,
} from '@/features/attendance/types/attendance.types'

export function useAttendanceRecords(params: AttendanceRecordParams) {
  return useQuery({
    queryFn: () => attendanceApi.listRecords(params),
    queryKey: ['attendance', 'records', params],
  })
}

export function useAttendanceRecordSummary(params: AttendanceRecordParams, enabled = true) {
  return useQuery({
    enabled,
    queryFn: () => attendanceApi.summarizeRecords(params),
    queryKey: ['attendance', 'records', 'summary', params],
  })
}

export function useUpdateAttendanceRecord() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ payload, recordId }: { payload: AttendanceRecordUpdate; recordId: string }) =>
      attendanceApi.updateRecord(recordId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['attendance', 'records'] }),
  })
}
