import type { RoleName } from '@/types/common.types'

export const permissions = {
  employees: {
    read: ['admin', 'hr', 'manager'],
    update: ['admin', 'hr'],
    delete: ['admin'],
  },
  departments: {
    read: ['admin', 'hr', 'manager'],
    create: ['admin'],
    update: ['admin'],
    delete: ['admin'],
  },
  positions: {
    read: ['admin', 'hr', 'manager'],
    create: ['admin'],
    update: ['admin'],
    delete: ['admin'],
  },
  faceProfiles: {
    read: ['admin', 'hr', 'manager'],
    update: ['admin', 'hr'],
    delete: ['admin'],
  },
  onboarding: {
    create: ['admin', 'hr'],
  },
} as const

export function hasPermission(role: RoleName | null | undefined, allowedRoles: readonly RoleName[]): boolean {
  return Boolean(role && allowedRoles.includes(role))
}
