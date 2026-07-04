import { useMemo, useState } from 'react'
import { PageHeader } from '@/components/layout/PageHeader'
import { Badge } from '@/components/ui/Badge'
import { EmptyState } from '@/components/ui/EmptyState'
import { Loading } from '@/components/ui/Loading'
import { Select } from '@/components/ui/Select'
import { StatusMessage } from '@/components/ui/StatusMessage'
import { Table } from '@/components/ui/Table'
import { useAttendanceEvents } from '@/features/attendance/hooks/useAttendanceEvents'
import type { AttendanceEventType } from '@/features/attendance/types/attendance.types'
import { useEmployees } from '@/features/employees/hooks/useEmployees'
import { formatDateTime, getApiErrorMessage } from '@/lib/utils'

export function AttendancePage() {
  const [employeeId, setEmployeeId] = useState<string>('')
  const [eventType, setEventType] = useState<AttendanceEventType | ''>('')
  const [status, setStatus] = useState<'accepted' | 'rejected' | ''>('')

  // Load all active employees for filtering and mapping names
  const employeesQuery = useEmployees({ page: 1, page_size: 200 })
  const employees = employeesQuery.data?.items

  const employeeMap = useMemo(() => {
    return new Map((employees ?? []).map((emp) => [emp.employee_id, emp]))
  }, [employees])

  const attendanceEventsQuery = useAttendanceEvents({
    employee_id: employeeId || undefined,
    event_type: eventType || undefined,
    accepted: status === 'accepted' ? true : status === 'rejected' ? false : undefined,
  })

  const events = attendanceEventsQuery.data ?? []

  return (
    <section className="page-stack">
      <PageHeader
        description="Theo dõi lịch sử chấm công nhận diện khuôn mặt thực tế qua API /attendance/events."
        eyebrow="Attendance"
        title="Lịch sử chấm công"
      />

      <div className="toolbar">
        <Select
          label="Nhân viên"
          onChange={(e) => setEmployeeId(e.target.value)}
          value={employeeId}
        >
          <option value="">Tất cả nhân viên</option>
          {employees?.map((emp) => (
            <option key={emp.employee_id} value={emp.employee_id}>
              {emp.full_name} ({emp.employee_code})
            </option>
          ))}
        </Select>

        <Select
          label="Loại sự kiện"
          onChange={(e) => setEventType(e.target.value as AttendanceEventType | '')}
          value={eventType}
        >
          <option value="">Tất cả loại</option>
          <option value="check_in">Vào ca (Check-in)</option>
          <option value="check_out">Ra ca (Check-out)</option>
        </Select>

        <Select
          label="Trạng thái"
          onChange={(e) => setStatus(e.target.value as 'accepted' | 'rejected' | '')}
          value={status}
        >
          <option value="">Tất cả trạng thái</option>
          <option value="accepted">Hợp lệ (Accepted)</option>
          <option value="rejected">Bị từ chối (Rejected)</option>
        </Select>
      </div>

      {attendanceEventsQuery.isLoading || employeesQuery.isLoading ? <Loading /> : null}

      {attendanceEventsQuery.isError || employeesQuery.isError ? (
        <StatusMessage tone="error">
          {getApiErrorMessage(
            attendanceEventsQuery.error || employeesQuery.error,
            'Không thể tải dữ liệu lịch sử chấm công.'
          )}
        </StatusMessage>
      ) : null}

      {!attendanceEventsQuery.isLoading && !attendanceEventsQuery.isError && events.length === 0 ? (
        <EmptyState
          description="Chưa có sự kiện chấm công nào phù hợp với bộ lọc đã chọn."
          title="Không tìm thấy sự kiện chấm công"
        />
      ) : null}

      {!attendanceEventsQuery.isLoading && events.length > 0 ? (
        <Table>
          <thead>
            <tr>
              <th>Nhân viên</th>
              <th>Thời gian</th>
              <th>Loại sự kiện</th>
              <th>Trạng thái</th>
              <th>Tin cậy (Confidence)</th>
              <th>Chống giả mạo</th>
              <th>Ảnh check-in</th>
              <th>Lý do từ chối</th>
            </tr>
          </thead>
          <tbody>
            {events.map((event) => {
              const emp = event.employee_id ? employeeMap.get(event.employee_id) : null
              return (
                <tr key={event.event_id}>
                  <td>
                    {emp ? (
                      <div>
                        <strong>{emp.full_name}</strong>
                        <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                          {emp.employee_code}
                        </div>
                      </div>
                    ) : (
                      <span style={{ color: 'var(--text-secondary)' }}>Không xác định</span>
                    )}
                  </td>
                  <td>{formatDateTime(event.event_time)}</td>
                  <td>
                    <Badge tone={event.event_type === 'check_in' ? 'green' : 'blue'}>
                      {event.event_type === 'check_in' ? 'Vào ca' : 'Ra ca'}
                    </Badge>
                  </td>
                  <td>
                    <Badge tone={event.is_accepted ? 'green' : 'red'}>
                      {event.is_accepted ? 'Hợp lệ' : 'Bị từ chối'}
                    </Badge>
                  </td>
                  <td>
                    {event.confidence_score !== null
                      ? `${(event.confidence_score * 100).toFixed(1)}%`
                      : '-'}
                  </td>
                  <td>
                    {event.anti_spoof_score !== null
                      ? `${(event.anti_spoof_score * 100).toFixed(1)}%`
                      : '-'}
                  </td>
                  <td>
                    {event.image_url ? (
                      <a
                        href={event.image_url}
                        target="_blank"
                        rel="noreferrer"
                        className="button button--secondary button--sm"
                        style={{ display: 'inline-flex', padding: '4px 8px', fontSize: '12px' }}
                      >
                        Xem ảnh
                      </a>
                    ) : (
                      <span style={{ color: 'var(--text-secondary)' }}>Không có</span>
                    )}
                  </td>
                  <td>
                    {event.rejection_reason ? (
                      <span style={{ color: 'var(--status-error)', fontSize: '13px' }}>
                        {event.rejection_reason}
                      </span>
                    ) : (
                      '-'
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </Table>
      ) : null}
    </section>
  )
}
