import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Table } from '@/components/ui/Table'
import type { Department } from '@/features/departments/types/department.types'
import { formatDateTime } from '@/lib/utils'

type DepartmentTableProps = {
  canManage?: boolean
  departments: Department[]
  isMutating?: boolean
  onDeactivate?: (department: Department) => void
  onDelete?: (department: Department) => void
  onEdit?: (department: Department) => void
}

export function DepartmentTable({ canManage, departments, isMutating, onDeactivate, onDelete, onEdit }: DepartmentTableProps) {
  return (
    <Table>
      <thead>
        <tr>
          <th>Tên phòng ban</th>
          <th>Mã</th>
          <th>Mô tả</th>
          <th>Trạng thái</th>
          <th>Cập nhật</th>
          {canManage ? <th>Thao tác</th> : null}
        </tr>
      </thead>
      <tbody>
        {departments.map((department) => (
          <tr key={department.department_id}>
            <td>
              <strong>{department.name}</strong>
            </td>
            <td>{department.code ?? '-'}</td>
            <td>{department.description ?? '-'}</td>
            <td>
              <Badge tone={department.is_active ? 'green' : 'gray'}>
                {department.is_active ? 'Hoạt động' : 'Tạm ngưng'}
              </Badge>
            </td>
            <td>{formatDateTime(department.updated_at)}</td>
            {canManage ? <td><div className="table-actions">
              <Button size="sm" variant="secondary" onClick={() => onEdit?.(department)}>Sửa</Button>
              {department.is_active ? <Button disabled={isMutating} size="sm" variant="ghost" onClick={() => onDeactivate?.(department)}>Tạm ngưng</Button> : null}
              <Button disabled={isMutating} size="sm" variant="danger" onClick={() => onDelete?.(department)}>Xóa</Button>
            </div></td> : null}
          </tr>
        ))}
      </tbody>
    </Table>
  )
}
