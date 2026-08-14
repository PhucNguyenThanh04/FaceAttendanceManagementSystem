import { Link } from 'react-router-dom'
import { AccessDeniedPanel } from '@/components/layout/AccessDeniedPanel'
import { Loading } from '@/components/ui/Loading'
import { StatusMessage } from '@/components/ui/StatusMessage'
import { routePaths } from '@/constants/routes'
import { useAttendanceRecordSummary } from '@/features/attendance/hooks/useAttendanceRecords'
import { useCorrectionRequests } from '@/features/corrections/hooks/useCorrections'
import { useDepartments } from '@/features/departments/hooks/useDepartments'
import { EmployeeTable } from '@/features/employees/components/EmployeeTable'
import { useEmployees } from '@/features/employees/hooks/useEmployees'
import { useLeaveRequests } from '@/features/leave/hooks/useLeave'
import { usePositions } from '@/features/positions/hooks/usePositions'
import { formatNumber, getApiErrorMessage } from '@/lib/utils'
import { useAuthStore } from '@/stores/auth.store'
import type { RoleName } from '@/types/common.types'

const roleCopy: Record<Exclude<RoleName, 'employee'>, {
  description: string
  eyebrow: string
  title: string
}> = {
  admin: {
    description: 'Tổng quan nhân sự và các đầu việc cần xử lý trong ngày.',
    eyebrow: 'Toàn hệ thống',
    title: 'Trung tâm điều hành',
  },
  hr: {
    description: 'Theo dõi lực lượng lao động, công hôm nay và các yêu cầu đang chờ.',
    eyebrow: 'Nhân sự',
    title: 'Bàn làm việc HR',
  },
  manager: {
    description: 'Dữ liệu được giới hạn theo team và phòng ban bạn phụ trách.',
    eyebrow: 'Quản lý đội ngũ',
    title: 'Tổng quan team',
  },
}

function localDateKey(value = new Date()) {
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

export function DashboardPage() {
  const role = useAuthStore((state) => state.user?.role_name)
  const canAccess = role === 'admin' || role === 'hr' || role === 'manager'
  const copy = canAccess ? roleCopy[role] : null
  const today = localDateKey()

  const employeesQuery = useEmployees({ page: 1, page_size: 6 }, canAccess)
  const departmentsQuery = useDepartments(undefined, canAccess)
  const positionsQuery = usePositions(undefined, canAccess)
  const attendanceQuery = useAttendanceRecordSummary({
    work_date_from: today,
    work_date_to: today,
  }, canAccess)
  const leaveQuery = useLeaveRequests({ page: 1, page_size: 1, status: 'pending' }, canAccess)
  const correctionQuery = useCorrectionRequests({ page: 1, page_size: 1, status: 'pending' }, canAccess)

  if (!canAccess || !copy) return <AccessDeniedPanel />

  const employees = employeesQuery.data?.items ?? []
  const departmentNames = new Map((departmentsQuery.data ?? []).map((item) => [item.department_id, item.name]))
  const positionNames = new Map((positionsQuery.data ?? []).map((item) => [item.position_id, item.name]))
  const error = employeesQuery.error || attendanceQuery.error || leaveQuery.error || correctionQuery.error
  const isLoading = employeesQuery.isLoading || attendanceQuery.isLoading || leaveQuery.isLoading || correctionQuery.isLoading

  return (
    <section className="page-stack">
      <div className="dashboard-hero dashboard-hero--command">
        <div>
          <p className="eyebrow">{copy.eyebrow}</p>
          <h2>{copy.title}</h2>
          <p>{copy.description}</p>
        </div>
        <div className="dashboard-hero__meta">
          <span>Hôm nay</span>
          <strong>{new Intl.DateTimeFormat('vi-VN', { dateStyle: 'full' }).format(new Date())}</strong>
        </div>
      </div>

      <div className="stat-grid">
        <Link className="stat-card stat-card--teal stat-card--link" to={routePaths.employees}>
          <span>{role === 'manager' ? 'Nhân viên trong phạm vi' : 'Tổng nhân viên'}</span>
          <strong>{formatNumber(employeesQuery.data?.total ?? 0)}</strong>
          <small>Xem danh sách →</small>
        </Link>
        <Link className="stat-card stat-card--blue stat-card--link" to={routePaths.attendance}>
          <span>Có bản ghi công hôm nay</span>
          <strong>{formatNumber(attendanceQuery.data?.total_records ?? 0)}</strong>
          <small>{formatNumber(attendanceQuery.data?.late_days ?? 0)} lượt đi muộn</small>
        </Link>
        <Link className="stat-card stat-card--amber stat-card--link" to={routePaths.leave}>
          <span>Đơn nghỉ chờ xử lý</span>
          <strong>{formatNumber(leaveQuery.data?.total ?? 0)}</strong>
          <small>Mở hàng đợi duyệt →</small>
        </Link>
        <Link className="stat-card stat-card--gray stat-card--link" to={routePaths.corrections}>
          <span>Yêu cầu sửa công</span>
          <strong>{formatNumber(correctionQuery.data?.total ?? 0)}</strong>
          <small>Cần xác nhận</small>
        </Link>
      </div>

      {isLoading ? <Loading label="Đang tổng hợp dữ liệu vận hành" /> : null}
      {error ? <StatusMessage tone="error">{getApiErrorMessage(error, 'Không thể tải đầy đủ số liệu tổng quan.')}</StatusMessage> : null}

      <div className="dashboard-grid">
        <section className="panel panel--padded page-stack">
          <div className="panel__header">
            <div><p className="eyebrow">Danh sách mới nhất</p><h2>Nhân viên</h2></div>
            <Link to={routePaths.employees}>Xem tất cả</Link>
          </div>
          {employees.length > 0 ? (
            <EmployeeTable departmentNames={departmentNames} employees={employees} positionNames={positionNames} />
          ) : !isLoading ? <p className="muted-text">Chưa có nhân viên trong phạm vi quản lý.</p> : null}
        </section>
        <aside className="panel panel--padded page-stack">
          <div><p className="eyebrow">Lối tắt</p><h2>Thao tác thường dùng</h2></div>
          <Link className="quick-action" to={routePaths.attendance}><strong>Kiểm tra bảng công</strong><span>Rà soát thiếu check-in/out và dữ liệu bất thường.</span></Link>
          <Link className="quick-action" to={routePaths.leave}><strong>Xử lý nghỉ phép</strong><span>Duyệt đơn và theo dõi số dư phép.</span></Link>
          <Link className="quick-action" to={routePaths.reports}><strong>Xem báo cáo tháng</strong><span>Phân tích đi muộn, vắng và giờ làm.</span></Link>
          {role !== 'manager' ? <Link className="quick-action" to={routePaths.onboarding}><strong>Onboard nhân viên</strong><span>Tạo tài khoản và đăng ký khuôn mặt.</span></Link> : null}
        </aside>
      </div>
    </section>
  )
}
