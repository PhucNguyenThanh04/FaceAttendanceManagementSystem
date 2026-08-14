import { useMutation, useQueryClient } from '@tanstack/react-query'
import { departmentApi } from '@/features/departments/api/department.api'

export function useCreateDepartment() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: departmentApi.createDepartment,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['departments'] })
    },
  })
}

export function useUpdateDepartment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ departmentId, payload }: { departmentId: number; payload: Parameters<typeof departmentApi.updateDepartment>[1] }) =>
      departmentApi.updateDepartment(departmentId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['departments'] }),
  })
}

export function useDeactivateDepartment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: departmentApi.deactivateDepartment,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['departments'] }),
  })
}

export function useDeleteDepartment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: departmentApi.deleteDepartment,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['departments'] }),
  })
}
