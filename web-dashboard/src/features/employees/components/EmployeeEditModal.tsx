import { useState } from 'react'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { StatusMessage } from '@/components/ui/StatusMessage'
import { Textarea } from '@/components/ui/Textarea'
import type { Department } from '@/features/departments/types/department.types'
import { useActivateEmployee, useDeleteEmployee, useUpdateEmployee } from '@/features/employees/hooks/useEmployees'
import type { Employee } from '@/features/employees/types/employee.types'
import type { Position } from '@/features/positions/types/position.types'
import { getApiErrorMessage } from '@/lib/utils'

export function EmployeeEditModal({ departments, employee, isAdmin, onClose, positions }: {
  departments: Department[]
  employee: Employee
  isAdmin: boolean
  onClose: () => void
  positions: Position[]
}) {
  const [values, setValues] = useState(() => ({
    address: employee.address ?? '', date_of_birth: employee.date_of_birth ?? '', department_id: employee.department_id?.toString() ?? '',
    employee_code: employee.employee_code, full_name: employee.full_name, gender: employee.gender ?? '', hire_date: employee.hire_date ?? '',
    phone: employee.phone ?? '', position_id: employee.position_id?.toString() ?? '', resignation_date: employee.resignation_date ?? '', status: employee.status,
  }))
  const updateMutation = useUpdateEmployee()
  const activateMutation = useActivateEmployee()
  const deleteMutation = useDeleteEmployee()

  const set = (key: keyof typeof values, value: string) => setValues((current) => ({ ...current, [key]: value }))
  const save = () => updateMutation.mutate({
    employeeId: employee.employee_id,
    payload: {
      address: values.address || null, date_of_birth: values.date_of_birth || null,
      department_id: values.department_id ? Number(values.department_id) : null,
      employee_code: values.employee_code.trim(), full_name: values.full_name.trim(), gender: values.gender || null,
      hire_date: values.hire_date || null, phone: values.phone || null,
      position_id: values.position_id ? Number(values.position_id) : null,
      resignation_date: values.resignation_date || null, status: values.status as Employee['status'],
    },
  }, { onSuccess: onClose })
  const activate = () => activateMutation.mutate(employee.employee_id, { onSuccess: onClose })
  const remove = () => {
    if (window.confirm(`Xóa hồ sơ “${employee.full_name}”? Face profile và các dữ liệu liên quan có thể bị ảnh hưởng.`)) {
      deleteMutation.mutate(employee.employee_id, { onSuccess: onClose })
    }
  }
  const error = updateMutation.error || activateMutation.error || deleteMutation.error

  return <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
    <div className="modal modal--wide" role="dialog" aria-modal="true" aria-labelledby="employee-edit-title" onMouseDown={(event) => event.stopPropagation()}>
      <div className="panel__header"><div><p className="eyebrow">Hồ sơ nhân sự</p><h2 id="employee-edit-title">{employee.full_name}</h2></div><Button variant="ghost" onClick={onClose}>Đóng</Button></div>
      <div className="form-grid">
        <Input label="Mã nhân viên" value={values.employee_code} onChange={(e) => set('employee_code', e.target.value)} />
        <Input label="Họ và tên" value={values.full_name} onChange={(e) => set('full_name', e.target.value)} />
        <Input label="Số điện thoại" value={values.phone} onChange={(e) => set('phone', e.target.value)} />
        <Select label="Giới tính" value={values.gender} onChange={(e) => set('gender', e.target.value)}><option value="">Chưa cập nhật</option><option value="male">Nam</option><option value="female">Nữ</option><option value="other">Khác</option></Select>
        <Select label="Phòng ban" value={values.department_id} onChange={(e) => set('department_id', e.target.value)}><option value="">Chưa phân phòng</option>{departments.map((item) => <option key={item.department_id} value={item.department_id}>{item.name}</option>)}</Select>
        <Select label="Chức vụ" value={values.position_id} onChange={(e) => set('position_id', e.target.value)}><option value="">Chưa có chức vụ</option>{positions.map((item) => <option key={item.position_id} value={item.position_id}>{item.name}</option>)}</Select>
        <Input label="Ngày sinh" type="date" value={values.date_of_birth} onChange={(e) => set('date_of_birth', e.target.value)} />
        <Input label="Ngày vào làm" type="date" value={values.hire_date} onChange={(e) => set('hire_date', e.target.value)} />
        <Input label="Ngày nghỉ việc" type="date" value={values.resignation_date} onChange={(e) => set('resignation_date', e.target.value)} />
        <Select label="Trạng thái" value={values.status} onChange={(e) => set('status', e.target.value)}><option value="active">Đang làm</option><option value="inactive">Tạm ngưng</option><option value="resigned">Đã nghỉ</option></Select>
      </div>
      <Textarea label="Địa chỉ" value={values.address} onChange={(e) => set('address', e.target.value)} />
      {error ? <StatusMessage tone="error">{getApiErrorMessage(error, 'Không thể cập nhật hồ sơ nhân viên.')}</StatusMessage> : null}
      <div className="modal-footer">
        <div>{employee.status !== 'active' ? <Button isLoading={activateMutation.isPending} variant="secondary" onClick={activate}>Kích hoạt lại</Button> : null}{isAdmin ? <Button isLoading={deleteMutation.isPending} variant="danger" onClick={remove}>Xóa hồ sơ</Button> : null}</div>
        <div><Button variant="secondary" onClick={onClose}>Hủy</Button><Button disabled={!values.full_name.trim() || !values.employee_code.trim()} isLoading={updateMutation.isPending} onClick={save}>Lưu hồ sơ</Button></div>
      </div>
    </div>
  </div>
}
