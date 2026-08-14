import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { StatusMessage } from '@/components/ui/StatusMessage'
import { useCreatePosition, useUpdatePosition } from '@/features/positions/hooks/useCreatePosition'
import type { Position } from '@/features/positions/types/position.types'
import { positionSchema, type PositionFormValues } from '@/features/positions/schemas/position.schema'
import { getApiErrorMessage } from '@/lib/utils'

export function PositionForm({ onCancel, onSaved, position }: { onCancel?: () => void; onSaved?: () => void; position?: Position | null }) {
  const createPosition = useCreatePosition()
  const updatePosition = useUpdatePosition()
  const {
    formState: { errors },
    handleSubmit,
    register,
    reset,
  } = useForm<PositionFormValues>({
    resolver: zodResolver(positionSchema),
    defaultValues: {
      code: '',
      description: '',
      is_active: true,
      name: '',
    },
  })

  useEffect(() => {
    reset({ code: position?.code ?? '', description: position?.description ?? '', is_active: position?.is_active ?? true, name: position?.name ?? '' })
  }, [position, reset])

  const onSubmit = (values: PositionFormValues) => {
    const payload = { code: values.code || null, description: values.description || null, is_active: values.is_active, name: values.name }
    const options = { onSuccess: () => { reset(); onSaved?.() } }
    if (position) updatePosition.mutate({ positionId: position.position_id, payload }, options)
    else createPosition.mutate(payload, options)
  }

  const mutation = position ? updatePosition : createPosition

  return (
    <form className="resource-form" onSubmit={handleSubmit(onSubmit)}>
      <Input error={errors.name?.message} label="Tên chức vụ" {...register('name')} />
      <Input error={errors.code?.message} label="Mã" {...register('code')} />
      <Input error={errors.description?.message} label="Mô tả" {...register('description')} />
      <label className="checkbox-field">
        <input type="checkbox" {...register('is_active')} />
        <span>Đang hoạt động</span>
      </label>
      {mutation.isError ? (
        <StatusMessage tone="error">
          {getApiErrorMessage(mutation.error, `Không thể ${position ? 'cập nhật' : 'tạo'} chức vụ.`)}
        </StatusMessage>
      ) : null}
      <div className="action-row">
        <Button isLoading={mutation.isPending} type="submit">{position ? 'Lưu thay đổi' : 'Tạo chức vụ'}</Button>
        {position ? <Button onClick={onCancel} variant="secondary">Hủy</Button> : null}
      </div>
    </form>
  )
}
