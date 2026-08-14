import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { userApi } from '@/features/users/api/user.api'
import type { UserListParams } from '@/features/users/types/user.types'
import type { RoleName, UserStatus } from '@/types/common.types'

export function useUsers(params: UserListParams) {
  return useQuery({
    queryFn: () => userApi.list(params),
    queryKey: ['users', params],
  })
}

function useUserMutation<TVariables>(mutationFn: (variables: TVariables) => Promise<unknown>) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['users'] }),
  })
}

export function useAssignUserRole() {
  return useUserMutation(({ role, userId }: { role: RoleName; userId: string }) =>
    userApi.assignRole(userId, role),
  )
}

export function useUpdateUserStatus() {
  return useUserMutation(({ status, userId }: { status: UserStatus; userId: string }) =>
    userApi.updateStatus(userId, status),
  )
}

export function useResetUserPassword() {
  return useUserMutation(({ password, userId }: { password: string; userId: string }) =>
    userApi.resetPassword(userId, password),
  )
}
