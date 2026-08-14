export type MonthlyReportParams = {
  year: number
  month: number
  department_id?: number
}

export type AttendanceSummary = {
  department_id: number
  department_name: string
  employee_count: number
  total_records: number
  present_days: number
  late_days: number
  early_leave_days: number
  absent_days: number
  on_leave_days: number
  holiday_days: number
  missing_check_in_days: number
  missing_check_out_days: number
  total_worked_minutes: number
  total_late_minutes: number
  total_early_leave_minutes: number
}

export type LeaveSummary = {
  department_id: number
  department_name: string
  employee_count: number
  total_requests: number
  pending_requests: number
  approved_requests: number
  rejected_requests: number
  cancelled_requests: number
  approved_leave_days: number
}

export type LateRanking = {
  rank: number
  employee_id: string
  employee_code: string
  full_name: string
  department_id: number | null
  department_name: string | null
  late_days: number
  total_late_minutes: number
  average_late_minutes: number
}

export type EmployeeMonthlyRecord = {
  record_id: string
  work_date: string
  check_in_time: string | null
  check_out_time: string | null
  status: string
  late_minutes: number
  early_leave_minutes: number
  worked_minutes: number
  source: string
  notes: string | null
}

export type EmployeeMonthlyReport = {
  employee_id: string
  employee_code: string
  full_name: string
  department_id: number | null
  department_name: string | null
  year: number
  month: number
  total_records: number
  present_days: number
  late_days: number
  early_leave_days: number
  absent_days: number
  on_leave_days: number
  holiday_days: number
  missing_check_in_days: number
  missing_check_out_days: number
  total_worked_minutes: number
  total_late_minutes: number
  total_early_leave_minutes: number
  records: EmployeeMonthlyRecord[]
}
