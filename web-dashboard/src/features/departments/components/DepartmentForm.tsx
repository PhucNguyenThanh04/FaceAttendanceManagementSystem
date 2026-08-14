import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { StatusMessage } from '@/components/ui/StatusMessage'
import { useCreateDepartment, useUpdateDepartment } from '@/features/departments/hooks/useCreateDepartment'
import type { Department } from '@/features/departments/types/department.types'
import {
  departmentSchema,
  type DepartmentFormValues,
} from '@/features/departments/schemas/department.schema'
import { getApiErrorMessage } from '@/lib/utils'

export function DepartmentForm({ department, onCancel, onSaved }: { department?: Department | null; onCancel?: () => void; onSaved?: () => void }) {
  const createDepartment = useCreateDepartment()
  const updateDepartment = useUpdateDepartment()
  const {
    formState: { errors },
    handleSubmit,
    register,
    reset,
  } = useForm<DepartmentFormValues>({
    resolver: zodResolver(departmentSchema),
    defaultValues: {
      code: '',
      description: '',
      is_active: true,
      name: '',
    },
  })

  useEffect(() => {
    reset({
      code: department?.code ?? '',
      description: department?.description ?? '',
      is_active: department?.is_active ?? true,
      name: department?.name ?? '',
    })
  }, [department, reset])

  const onSubmit = (values: DepartmentFormValues) => {
    const payload = { code: values.code || null, description: values.description || null, is_active: values.is_active, name: values.name }
    const options = { onSuccess: () => { reset(); onSaved?.() } }
    if (department) updateDepartment.mutate({ departmentId: department.department_id, payload }, options)
    else createDepartment.mutate(payload, options)
  }

  const mutation = department ? updateDepartment : createDepartment

  return (
    <form className="resource-form" onSubmit={handleSubmit(onSubmit)}>
      <Input error={errors.name?.message} label="Tên phòng ban" {...register('name')} />
      <Input error={errors.code?.message} label="Mã" {...register('code')} />
      <Input error={errors.description?.message} label="Mô tả" {...register('description')} />
      <label className="checkbox-field">
        <input type="checkbox" {...register('is_active')} />
        <span>Đang hoạt động</span>
      </label>
      {mutation.isError ? (
        <StatusMessage tone="error">
          {getApiErrorMessage(mutation.error, `Không thể ${department ? 'cập nhật' : 'tạo'} phòng ban.`)}
        </StatusMessage>
      ) : null}
      <div className="action-row">
        <Button isLoading={mutation.isPending} type="submit">{department ? 'Lưu thay đổi' : 'Tạo phòng ban'}</Button>
        {department ? <Button onClick={onCancel} variant="secondary">Hủy</Button> : null}
      </div>
    </form>
  )
}
