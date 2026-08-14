import { api } from '@/lib/axios'
import type {
  AttendanceSummary,
  LateRanking,
  LeaveSummary,
  MonthlyReportParams,
  EmployeeMonthlyReport,
} from '@/features/reports/types/report.types'

export const reportApi = {
  employeeMonthly: async (employeeId: string, params: Pick<MonthlyReportParams, 'month' | 'year'>): Promise<EmployeeMonthlyReport> => {
    const response = await api.get<EmployeeMonthlyReport>(`/reports/monthly/${employeeId}`, { params })
    return response.data
  },
  attendanceSummary: async (params: MonthlyReportParams): Promise<AttendanceSummary[]> => {
    const response = await api.get<AttendanceSummary[]>('/reports/attendance-summary', { params })
    return response.data
  },
  leaveSummary: async (params: MonthlyReportParams): Promise<LeaveSummary[]> => {
    const response = await api.get<LeaveSummary[]>('/reports/leave-summary', { params })
    return response.data
  },
  lateRanking: async (params: MonthlyReportParams & { limit?: number }): Promise<LateRanking[]> => {
    const response = await api.get<LateRanking[]>('/reports/late-ranking', { params })
    return response.data
  },
}
