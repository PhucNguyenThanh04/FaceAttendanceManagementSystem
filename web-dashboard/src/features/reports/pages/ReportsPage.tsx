import { useState } from 'react'
import { PageHeader } from '@/components/layout/PageHeader'
import { EmptyState } from '@/components/ui/EmptyState'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Loading } from '@/components/ui/Loading'
import { Select } from '@/components/ui/Select'
import { StatusMessage } from '@/components/ui/StatusMessage'
import { Table } from '@/components/ui/Table'
import { useDepartments } from '@/features/departments/hooks/useDepartments'
import {
  useAttendanceSummary,
  useLateRanking,
  useLeaveSummary,
  useEmployeeMonthlyReport,
} from '@/features/reports/hooks/useReports'
import { formatDate, formatDateTime, formatNumber, getApiErrorMessage } from '@/lib/utils'
import { useAuthStore } from '@/stores/auth.store'
import { useEmployees } from '@/features/employees/hooks/useEmployees'

export function ReportsPage() {
  const now = new Date()
  const role = useAuthStore((state) => state.user?.role_name)
  const [year, setYear] = useState(now.getFullYear())
  const [month, setMonth] = useState(now.getMonth() + 1)
  const [departmentId, setDepartmentId] = useState('')
  const [employeeId, setEmployeeId] = useState('')
  const params = {
    department_id: departmentId ? Number(departmentId) : undefined,
    month,
    year,
  }
  const departmentsQuery = useDepartments()
  const attendanceQuery = useAttendanceSummary(params)
  const leaveQuery = useLeaveSummary(params, role === 'admin' || role === 'hr')
  const rankingQuery = useLateRanking(params)
  const employeesQuery = useEmployees({ department_id: departmentId ? Number(departmentId) : undefined, page: 1, page_size: 200 })
  const employeeReportQuery = useEmployeeMonthlyReport(employeeId, { month, year })
  const attendance = attendanceQuery.data ?? []
  const totals = attendance.reduce(
      (sum, item) => ({
        absent: sum.absent + item.absent_days,
        employees: sum.employees + item.employee_count,
        late: sum.late + item.late_days,
        records: sum.records + item.total_records,
      }),
      { absent: 0, employees: 0, late: 0, records: 0 },
    )
  const error = attendanceQuery.error || leaveQuery.error || rankingQuery.error || departmentsQuery.error

  const exportCsv = () => {
    const header = ['Phòng ban', 'Nhân viên', 'Bản ghi', 'Hiện diện', 'Đi muộn', 'Về sớm', 'Vắng', 'Giờ làm']
    const rows = attendance.map((item) => [item.department_name, item.employee_count, item.total_records, item.present_days, item.late_days, item.early_leave_days, item.absent_days, (item.total_worked_minutes / 60).toFixed(2)])
    const csv = [header, ...rows].map((row) => row.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(',')).join('\n')
    const url = URL.createObjectURL(new Blob([`\uFEFF${csv}`], { type: 'text/csv;charset=utf-8' }))
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `bao-cao-cham-cong-${year}-${String(month).padStart(2, '0')}.csv`
    anchor.click()
    URL.revokeObjectURL(url)
  }

  return (
    <section className="page-stack">
      <PageHeader
        actions={<Button disabled={attendance.length === 0} onClick={exportCsv} variant="secondary">Xuất CSV</Button>}
        description="Tổng hợp chấm công, nghỉ phép và xếp hạng đi muộn theo tháng từ API báo cáo."
        eyebrow="Analytics"
        title="Báo cáo vận hành"
      />
      <div className="toolbar toolbar--three">
        <Input label="Năm" min={1900} max={9998} type="number" value={year} onChange={(event) => setYear(Number(event.target.value))} />
        <Select label="Tháng" value={month} onChange={(event) => setMonth(Number(event.target.value))}>
          {Array.from({ length: 12 }, (_, index) => <option key={index + 1} value={index + 1}>Tháng {index + 1}</option>)}
        </Select>
        <Select label="Phòng ban" value={departmentId} onChange={(event) => setDepartmentId(event.target.value)}>
          <option value="">Tất cả phòng ban</option>
          {(departmentsQuery.data ?? []).map((department) => <option key={department.department_id} value={department.department_id}>{department.name}</option>)}
        </Select>
      </div>
      <section className="panel panel--padded report-drilldown">
        <div><p className="eyebrow">Chi tiết nhân viên</p><h2>Báo cáo công cá nhân</h2><p className="muted-text">Chọn nhân viên để rà từng ngày trong kỳ đang xem.</p></div>
        <Select label="Nhân viên" value={employeeId} onChange={(event) => setEmployeeId(event.target.value)}>
          <option value="">Chọn nhân viên</option>
          {(employeesQuery.data?.items ?? []).map((employee) => <option key={employee.employee_id} value={employee.employee_id}>{employee.employee_code} · {employee.full_name}</option>)}
        </Select>
      </section>
      <div className="stat-grid">
        <article className="stat-card stat-card--teal"><span>Nhân viên</span><strong>{formatNumber(totals.employees)}</strong></article>
        <article className="stat-card stat-card--blue"><span>Bản ghi công</span><strong>{formatNumber(totals.records)}</strong></article>
        <article className="stat-card stat-card--amber"><span>Lượt đi muộn</span><strong>{formatNumber(totals.late)}</strong></article>
        <article className="stat-card stat-card--gray"><span>Lượt vắng</span><strong>{formatNumber(totals.absent)}</strong></article>
      </div>
      {attendanceQuery.isLoading || leaveQuery.isLoading || rankingQuery.isLoading ? <Loading /> : null}
      {error ? <StatusMessage tone="error">{getApiErrorMessage(error, 'Không thể tải báo cáo.')}</StatusMessage> : null}
      {!attendanceQuery.isLoading && !error && attendance.length === 0 ? <EmptyState title="Chưa có dữ liệu báo cáo" description="Không có bản ghi phù hợp kỳ và phòng ban đã chọn." /> : null}
      {attendance.length > 0 ? (
        <section className="panel page-stack">
          <div className="panel__header"><h2>Chấm công theo phòng ban</h2></div>
          <Table>
            <thead><tr><th>Phòng ban</th><th>Nhân viên</th><th>Hiện diện</th><th>Đi muộn</th><th>Về sớm</th><th>Vắng</th><th>Thiếu check-in/out</th><th>Giờ làm</th></tr></thead>
            <tbody>
              {attendance.map((item) => (
                <tr key={item.department_id}>
                  <td><strong>{item.department_name}</strong></td>
                  <td>{formatNumber(item.employee_count)}</td>
                  <td>{formatNumber(item.present_days)}</td>
                  <td>{formatNumber(item.late_days)}</td>
                  <td>{formatNumber(item.early_leave_days)}</td>
                  <td>{formatNumber(item.absent_days)}</td>
                  <td>{formatNumber(item.missing_check_in_days + item.missing_check_out_days)}</td>
                  <td>{(item.total_worked_minutes / 60).toFixed(1)}</td>
                </tr>
              ))}
            </tbody>
          </Table>
        </section>
      ) : null}
      <div className="report-grid">
        <section className="panel page-stack">
          <div className="panel__header"><h2>Top đi muộn</h2></div>
          {(rankingQuery.data ?? []).length > 0 ? (
            <Table>
              <thead><tr><th>#</th><th>Nhân viên</th><th>Số ngày</th><th>Tổng phút</th></tr></thead>
              <tbody>{(rankingQuery.data ?? []).map((item) => <tr key={item.employee_id}><td>{item.rank}</td><td><strong>{item.full_name}</strong><div className="mono-cell">{item.employee_code}</div></td><td>{item.late_days}</td><td>{item.total_late_minutes}</td></tr>)}</tbody>
            </Table>
          ) : <p className="muted-text">Không có dữ liệu đi muộn.</p>}
        </section>
        {role === 'admin' || role === 'hr' ? (
          <section className="panel page-stack">
            <div className="panel__header"><h2>Nghỉ phép theo phòng ban</h2></div>
            {(leaveQuery.data ?? []).length > 0 ? (
              <Table>
                <thead><tr><th>Phòng ban</th><th>Chờ duyệt</th><th>Đã duyệt</th><th>Số ngày</th></tr></thead>
                <tbody>{(leaveQuery.data ?? []).map((item) => <tr key={item.department_id}><td><strong>{item.department_name}</strong></td><td>{item.pending_requests}</td><td>{item.approved_requests}</td><td>{item.approved_leave_days}</td></tr>)}</tbody>
              </Table>
            ) : <p className="muted-text">Không có dữ liệu nghỉ phép.</p>}
          </section>
        ) : null}
      </div>
      {employeeId ? <div className="modal-backdrop" role="presentation" onMouseDown={() => setEmployeeId('')}><div className="modal modal--wide" role="dialog" aria-modal="true" aria-labelledby="employee-report-title" onMouseDown={(event) => event.stopPropagation()}>
        <div className="panel__header"><div><p className="eyebrow">Tháng {month}/{year}</p><h2 id="employee-report-title">{employeeReportQuery.data?.full_name ?? 'Báo cáo nhân viên'}</h2></div><Button variant="ghost" onClick={() => setEmployeeId('')}>Đóng</Button></div>
        {employeeReportQuery.isLoading ? <Loading label="Đang tổng hợp bảng công nhân viên" /> : null}
        {employeeReportQuery.isError ? <StatusMessage tone="error">{getApiErrorMessage(employeeReportQuery.error, 'Không thể tải báo cáo nhân viên.')}</StatusMessage> : null}
        {employeeReportQuery.data ? <div className="page-stack">
          <div className="stat-grid stat-grid--compact"><article className="stat-card stat-card--teal"><span>Bản ghi</span><strong>{employeeReportQuery.data.total_records}</strong></article><article className="stat-card stat-card--blue"><span>Giờ làm</span><strong>{(employeeReportQuery.data.total_worked_minutes / 60).toFixed(1)}</strong></article><article className="stat-card stat-card--amber"><span>Đi muộn</span><strong>{employeeReportQuery.data.late_days}</strong></article><article className="stat-card stat-card--gray"><span>Vắng</span><strong>{employeeReportQuery.data.absent_days}</strong></article></div>
          {employeeReportQuery.data.records.length > 0 ? <Table><thead><tr><th>Ngày</th><th>Giờ vào</th><th>Giờ ra</th><th>Trạng thái</th><th>Phút công</th></tr></thead><tbody>{employeeReportQuery.data.records.map((record) => <tr key={record.record_id}><td>{formatDate(record.work_date)}</td><td>{formatDateTime(record.check_in_time)}</td><td>{formatDateTime(record.check_out_time)}</td><td>{record.status}</td><td>{record.worked_minutes}</td></tr>)}</tbody></Table> : <EmptyState title="Chưa có bản ghi trong kỳ" />}
        </div> : null}
      </div></div> : null}
    </section>
  )
}
