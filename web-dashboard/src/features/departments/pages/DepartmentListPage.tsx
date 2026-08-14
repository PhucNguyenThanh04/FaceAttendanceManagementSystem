import { useState } from 'react'
import { PageHeader } from '@/components/layout/PageHeader'
import { EmptyState } from '@/components/ui/EmptyState'
import { Input } from '@/components/ui/Input'
import { Loading } from '@/components/ui/Loading'
import { StatusMessage } from '@/components/ui/StatusMessage'
import { DepartmentForm } from '@/features/departments/components/DepartmentForm'
import { DepartmentTable } from '@/features/departments/components/DepartmentTable'
import { useDepartments } from '@/features/departments/hooks/useDepartments'
import { getApiErrorMessage } from '@/lib/utils'
import { useAuthStore } from '@/stores/auth.store'
import type { Department } from '@/features/departments/types/department.types'
import { useDeactivateDepartment, useDeleteDepartment } from '@/features/departments/hooks/useCreateDepartment'

export function DepartmentListPage() {
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<Department | null>(null)
  const isAdmin = useAuthStore((state) => state.user?.role_name === 'admin')
  const departmentsQuery = useDepartments(search)
  const departments = departmentsQuery.data ?? []
  const deactivateMutation = useDeactivateDepartment()
  const deleteMutation = useDeleteDepartment()
  const mutationError = deactivateMutation.error || deleteMutation.error

  const deactivate = (department: Department) => {
    if (window.confirm(`Tạm ngưng phòng ban “${department.name}”?`)) deactivateMutation.mutate(department.department_id)
  }
  const remove = (department: Department) => {
    if (window.confirm(`Xóa vĩnh viễn phòng ban “${department.name}”? Chỉ thực hiện được khi không còn dữ liệu liên quan.`)) {
      deleteMutation.mutate(department.department_id, { onSuccess: () => selected?.department_id === department.department_id && setSelected(null) })
    }
  }

  return (
    <section className="page-grid">
      <div className="page-stack">
        <PageHeader
          description="Danh mục phòng ban từ /departments."
          eyebrow="Staff"
          title="Phòng ban"
        />
        <Input
          label="Tìm kiếm"
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Tên hoặc mã phòng ban"
          value={search}
        />
        {departmentsQuery.isLoading ? <Loading /> : null}
        {departmentsQuery.isError ? (
          <StatusMessage tone="error">
            {getApiErrorMessage(departmentsQuery.error, 'Không thể tải danh sách phòng ban.')}
          </StatusMessage>
        ) : null}
        {mutationError ? <StatusMessage tone="error">{getApiErrorMessage(mutationError, 'Không thể cập nhật phòng ban.')}</StatusMessage> : null}
        {!departmentsQuery.isLoading && !departmentsQuery.isError && departments.length === 0 ? (
          <EmptyState title="Chưa có phòng ban" />
        ) : null}
        {departments.length > 0 ? <DepartmentTable canManage={isAdmin} departments={departments} isMutating={deactivateMutation.isPending || deleteMutation.isPending} onDeactivate={deactivate} onDelete={remove} onEdit={setSelected} /> : null}
      </div>
      <aside className="side-panel">
        <h2>{selected ? 'Cập nhật phòng ban' : 'Tạo phòng ban'}</h2>
        {isAdmin ? <DepartmentForm department={selected} onCancel={() => setSelected(null)} onSaved={() => setSelected(null)} /> : <StatusMessage>HR có quyền tra cứu. Chỉ admin được thay đổi danh mục phòng ban.</StatusMessage>}
      </aside>
    </section>
  )
}
