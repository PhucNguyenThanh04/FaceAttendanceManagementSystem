import { useState } from 'react'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { EmptyState } from '@/components/ui/EmptyState'
import { Input } from '@/components/ui/Input'
import { Loading } from '@/components/ui/Loading'
import { Select } from '@/components/ui/Select'
import { StatusMessage } from '@/components/ui/StatusMessage'
import { Table } from '@/components/ui/Table'
import { Textarea } from '@/components/ui/Textarea'
import {
  useAttendanceRecords,
  useAttendanceRecordSummary,
  useUpdateAttendanceRecord,
} from '@/features/attendance/hooks/useAttendanceRecords'
import type {
  AttendanceRecord,
  AttendanceRecordStatus,
} from '@/features/attendance/types/attendance.types'
import type { Employee } from '@/features/employees/types/employee.types'
import { formatDate, formatDateTime, formatNumber, getApiErrorMessage } from '@/lib/utils'
import type { RoleName } from '@/types/common.types'

const statuses: AttendanceRecordStatus[] = [
  'present', 'late', 'early_leave', 'late_and_early_leave', 'absent', 'on_leave',
  'holiday', 'missing_check_in', 'missing_check_out', 'manually_edited',
]

const labels: Record<AttendanceRecordStatus, string> = {
  absent: 'Vắng',
  early_leave: 'Về sớm',
  holiday: 'Ngày lễ',
  late: 'Đi muộn',
  late_and_early_leave: 'Muộn & về sớm',
  manually_edited: 'Đã chỉnh tay',
  missing_check_in: 'Thiếu check-in',
  missing_check_out: 'Thiếu check-out',
  on_leave: 'Nghỉ phép',
  present: 'Có mặt',
}

function toLocalDateTime(value?: string | null) {
  if (!value) return ''
  const date = new Date(value)
  return new Date(date.getTime() - date.getTimezoneOffset() * 60_000).toISOString().slice(0, 16)
}

export function AttendanceRecordsPanel({
  employees,
  role,
}: {
  employees: Employee[]
  role?: RoleName
}) {
  const now = new Date()
  const firstDay = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().slice(0, 10)
  const [employeeId, setEmployeeId] = useState('')
  const [status, setStatus] = useState<AttendanceRecordStatus | ''>('')
  const [fromDate, setFromDate] = useState(firstDay)
  const [toDate, setToDate] = useState(now.toISOString().slice(0, 10))
  const [selected, setSelected] = useState<AttendanceRecord | null>(null)
  const [checkIn, setCheckIn] = useState('')
  const [checkOut, setCheckOut] = useState('')
  const [editStatus, setEditStatus] = useState<AttendanceRecordStatus>('present')
  const [notes, setNotes] = useState('')
  const params = {
    employee_id: employeeId || undefined,
    page: 1,
    page_size: 200,
    status: status || undefined,
    work_date_from: fromDate || undefined,
    work_date_to: toDate || undefined,
  }
  const recordsQuery = useAttendanceRecords(params)
  const summaryQuery = useAttendanceRecordSummary(params)
  const updateMutation = useUpdateAttendanceRecord()
  const employeeNames = new Map(employees.map((item) => [item.employee_id, item]))
  const canEdit = role === 'admin' || role === 'hr'

  const openEdit = (record: AttendanceRecord) => {
    setSelected(record)
    setCheckIn(toLocalDateTime(record.check_in_time))
    setCheckOut(toLocalDateTime(record.check_out_time))
    setEditStatus(record.status)
    setNotes(record.notes ?? '')
  }

  const submit = () => {
    if (!selected) return
    updateMutation.mutate({
      payload: {
        check_in_time: checkIn ? new Date(checkIn).toISOString() : undefined,
        check_out_time: checkOut ? new Date(checkOut).toISOString() : undefined,
        notes: notes || undefined,
        status: editStatus,
      },
      recordId: selected.record_id,
    }, { onSuccess: () => setSelected(null) })
  }

  const summary = summaryQuery.data
  const records = recordsQuery.data ?? []

  return (
    <div className="page-stack">
      <div className="toolbar toolbar--four">
        <Select label="Nhân viên" value={employeeId} onChange={(event) => setEmployeeId(event.target.value)}>
          <option value="">Tất cả nhân viên</option>
          {employees.map((employee) => <option key={employee.employee_id} value={employee.employee_id}>{employee.full_name} ({employee.employee_code})</option>)}
        </Select>
        <Select label="Trạng thái" value={status} onChange={(event) => setStatus(event.target.value as AttendanceRecordStatus | '')}>
          <option value="">Tất cả</option>
          {statuses.map((item) => <option key={item} value={item}>{labels[item]}</option>)}
        </Select>
        <Input label="Từ ngày" type="date" value={fromDate} onChange={(event) => setFromDate(event.target.value)} />
        <Input label="Đến ngày" type="date" value={toDate} onChange={(event) => setToDate(event.target.value)} />
      </div>
      <div className="stat-grid">
        <article className="stat-card stat-card--teal"><span>Tổng bản ghi</span><strong>{formatNumber(summary?.total_records ?? 0)}</strong></article>
        <article className="stat-card stat-card--blue"><span>Có mặt</span><strong>{formatNumber(summary?.present_days ?? 0)}</strong></article>
        <article className="stat-card stat-card--amber"><span>Đi muộn</span><strong>{formatNumber(summary?.late_days ?? 0)}</strong></article>
        <article className="stat-card stat-card--gray"><span>Vắng</span><strong>{formatNumber(summary?.absent_days ?? 0)}</strong></article>
      </div>
      {recordsQuery.isLoading || summaryQuery.isLoading ? <Loading /> : null}
      {recordsQuery.isError || summaryQuery.isError ? <StatusMessage tone="error">{getApiErrorMessage(recordsQuery.error || summaryQuery.error, 'Không thể tải bảng công.')}</StatusMessage> : null}
      {!recordsQuery.isLoading && !recordsQuery.isError && records.length === 0 ? <EmptyState title="Chưa có bản ghi công" /> : null}
      {records.length > 0 ? (
        <Table>
          <thead><tr><th>Ngày</th><th>Nhân viên</th><th>Check-in</th><th>Check-out</th><th>Trạng thái</th><th>Phút công</th><th>Nguồn</th>{canEdit ? <th>Thao tác</th> : null}</tr></thead>
          <tbody>{records.map((record) => {
            const employee = employeeNames.get(record.employee_id)
            return (
              <tr key={record.record_id}>
                <td><strong>{formatDate(record.work_date)}</strong></td>
                <td><strong>{employee?.full_name ?? 'Không xác định'}</strong><div className="mono-cell">{employee?.employee_code ?? record.employee_id.slice(0, 8)}</div></td>
                <td>{formatDateTime(record.check_in_time)}</td>
                <td>{formatDateTime(record.check_out_time)}</td>
                <td><Badge tone={record.status === 'present' ? 'green' : record.status === 'absent' ? 'red' : 'amber'}>{labels[record.status]}</Badge></td>
                <td>{record.worked_minutes} <span className="muted-text">({record.late_minutes} muộn)</span></td>
                <td>{record.source}</td>
                {canEdit ? <td><Button size="sm" variant="secondary" onClick={() => openEdit(record)}>Chỉnh sửa</Button></td> : null}
              </tr>
            )
          })}</tbody>
        </Table>
      ) : null}
      {selected ? (
        <div className="modal-backdrop" role="presentation" onMouseDown={() => setSelected(null)}>
          <div className="modal" role="dialog" aria-modal="true" onMouseDown={(event) => event.stopPropagation()}>
            <div className="panel__header"><h2>Chỉnh sửa bản ghi công</h2></div>
            <div className="resource-form">
              <Input label="Giờ vào" type="datetime-local" value={checkIn} onChange={(event) => setCheckIn(event.target.value)} />
              <Input label="Giờ ra" type="datetime-local" value={checkOut} onChange={(event) => setCheckOut(event.target.value)} />
              <Select label="Trạng thái" value={editStatus} onChange={(event) => setEditStatus(event.target.value as AttendanceRecordStatus)}>
                {statuses.map((item) => <option key={item} value={item}>{labels[item]}</option>)}
              </Select>
              <Textarea label="Ghi chú chỉnh sửa" value={notes} onChange={(event) => setNotes(event.target.value)} />
              {updateMutation.isError ? <StatusMessage tone="error">{getApiErrorMessage(updateMutation.error, 'Không thể cập nhật bản ghi công.')}</StatusMessage> : null}
              <div className="action-row">
                <Button isLoading={updateMutation.isPending} onClick={submit}>Lưu thay đổi</Button>
                <Button variant="secondary" onClick={() => setSelected(null)}>Đóng</Button>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}
