import { useMemo, useState } from 'react'
import { PageHeader } from '@/components/layout/PageHeader'
import { EmptyState } from '@/components/ui/EmptyState'
import { Input } from '@/components/ui/Input'
import { Loading } from '@/components/ui/Loading'
import { Pagination } from '@/components/ui/Pagination'
import { Select } from '@/components/ui/Select'
import { StatusMessage } from '@/components/ui/StatusMessage'
import { useDepartments } from '@/features/departments/hooks/useDepartments'
import { useEmployees } from '@/features/employees/hooks/useEmployees'
import { EmployeeTable } from '@/features/employees/components/EmployeeTable'
import { EmployeeEditModal } from '@/features/employees/components/EmployeeEditModal'
import { usePositions } from '@/features/positions/hooks/usePositions'
import { getApiErrorMessage } from '@/lib/utils'
import type { EmployeeStatus } from '@/types/common.types'
import type { Employee } from '@/features/employees/types/employee.types'
import { useAuthStore } from '@/stores/auth.store'

const PAGE_SIZE = 12

export function EmployeeListPage() {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState<EmployeeStatus | ''>('')
  const [departmentId, setDepartmentId] = useState('')
  const [positionId, setPositionId] = useState('')
  const [selected, setSelected] = useState<Employee | null>(null)
  const role = useAuthStore((state) => state.user?.role_name)
  const canManage = role === 'admin' || role === 'hr'
  const employeesQuery = useEmployees({
    page,
    page_size: PAGE_SIZE,
    search: search || undefined,
    status: status || undefined,
    department_id: departmentId ? Number(departmentId) : undefined,
    position_id: positionId ? Number(positionId) : undefined,
  })
  const departmentsQuery = useDepartments()
  const positionsQuery = usePositions()

  const departmentNames = useMemo(
    () => new Map((departmentsQuery.data ?? []).map((department) => [department.department_id, department.name])),
    [departmentsQuery.data],
  )
  const positionNames = useMemo(
    () => new Map((positionsQuery.data ?? []).map((position) => [position.position_id, position.name])),
    [positionsQuery.data],
  )

  const employees = employeesQuery.data?.items ?? []

  return (
    <section className="page-stack">
      <PageHeader
        description="Tra cứu nhân sự theo contract /employees của API service."
        eyebrow="Staff"
        title="Nhân viên"
      />
      <div className="toolbar toolbar--four">
        <Input
          label="Tìm kiếm"
          onChange={(event) => {
            setSearch(event.target.value)
            setPage(1)
          }}
          placeholder="Tên hoặc mã nhân viên"
          value={search}
        />
        <Select
          label="Trạng thái"
          onChange={(event) => {
            setStatus(event.target.value as EmployeeStatus | '')
            setPage(1)
          }}
          value={status}
        >
          <option value="">Tất cả</option>
          <option value="active">Đang làm</option>
          <option value="inactive">Tạm ngưng</option>
          <option value="resigned">Đã nghỉ</option>
        </Select>
        <Select label="Phòng ban" value={departmentId} onChange={(event) => { setDepartmentId(event.target.value); setPage(1) }}>
          <option value="">Tất cả phòng ban</option>
          {(departmentsQuery.data ?? []).map((item) => <option key={item.department_id} value={item.department_id}>{item.name}</option>)}
        </Select>
        <Select label="Chức vụ" value={positionId} onChange={(event) => { setPositionId(event.target.value); setPage(1) }}>
          <option value="">Tất cả chức vụ</option>
          {(positionsQuery.data ?? []).map((item) => <option key={item.position_id} value={item.position_id}>{item.name}</option>)}
        </Select>
      </div>
      {employeesQuery.isLoading ? <Loading /> : null}
      {employeesQuery.isError ? (
        <StatusMessage tone="error">
          {getApiErrorMessage(employeesQuery.error, 'Không thể tải danh sách nhân viên.')}
        </StatusMessage>
      ) : null}
      {!employeesQuery.isLoading && !employeesQuery.isError && employees.length === 0 ? (
        <EmptyState
          description="Thử đổi bộ lọc hoặc tạo nhân viên qua màn onboarding."
          title="Chưa có nhân viên phù hợp"
        />
      ) : null}
      {employees.length > 0 ? (
        <>
          <EmployeeTable
            canManage={canManage}
            departmentNames={departmentNames}
            employees={employees}
            onSelect={setSelected}
            positionNames={positionNames}
          />
          <Pagination
            currentPage={employeesQuery.data?.page ?? page}
            isFetching={employeesQuery.isFetching}
            onPageChange={setPage}
            pageSize={employeesQuery.data?.page_size ?? PAGE_SIZE}
            total={employeesQuery.data?.total ?? 0}
          />
        </>
      ) : null}
      {selected ? <EmployeeEditModal key={selected.employee_id} departments={departmentsQuery.data ?? []} employee={selected} isAdmin={role === 'admin'} onClose={() => setSelected(null)} positions={positionsQuery.data ?? []} /> : null}
    </section>
  )
}
