import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { employeeApi } from '@/features/employees/api/employee.api'
import type { EmployeeListParams } from '@/features/employees/types/employee.types'

export function useEmployees(params: EmployeeListParams, enabled = true) {
  return useQuery({
    enabled,
    queryFn: () => employeeApi.listEmployees(params),
    queryKey: ['employees', params],
  })
}

export function useMyEmployeeProfile(enabled = true) {
  return useQuery({
    enabled,
    queryFn: () => employeeApi.getMyEmployeeProfile(),
    queryKey: ['my-employee-profile'],
  })
}

export function useUpdateEmployee() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ employeeId, payload }: { employeeId: string; payload: Parameters<typeof employeeApi.updateEmployee>[1] }) => employeeApi.updateEmployee(employeeId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['employees'] }),
  })
}

export function useActivateEmployee() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: employeeApi.activateEmployee,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['employees'] }),
  })
}

export function useDeleteEmployee() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: employeeApi.deleteEmployee,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['employees'] }),
  })
}
