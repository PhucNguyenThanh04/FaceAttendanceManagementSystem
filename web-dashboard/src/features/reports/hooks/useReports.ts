import { useQuery } from '@tanstack/react-query'
import { reportApi } from '@/features/reports/api/report.api'
import type { MonthlyReportParams } from '@/features/reports/types/report.types'

export function useAttendanceSummary(params: MonthlyReportParams) {
  return useQuery({
    queryFn: () => reportApi.attendanceSummary(params),
    queryKey: ['reports', 'attendance-summary', params],
  })
}

export function useLeaveSummary(params: MonthlyReportParams, enabled = true) {
  return useQuery({
    enabled,
    queryFn: () => reportApi.leaveSummary(params),
    queryKey: ['reports', 'leave-summary', params],
  })
}

export function useLateRanking(params: MonthlyReportParams) {
  return useQuery({
    queryFn: () => reportApi.lateRanking({ ...params, limit: 20 }),
    queryKey: ['reports', 'late-ranking', params],
  })
}

export function useEmployeeMonthlyReport(employeeId: string, params: Pick<MonthlyReportParams, 'month' | 'year'>) {
  return useQuery({
    enabled: Boolean(employeeId),
    queryFn: () => reportApi.employeeMonthly(employeeId, params),
    queryKey: ['reports', 'employee-monthly', employeeId, params],
  })
}
