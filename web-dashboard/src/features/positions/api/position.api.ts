import { api } from '@/lib/axios'
import type { CreatePositionPayload, Position, UpdatePositionPayload } from '@/features/positions/types/position.types'

export const positionApi = {
  listPositions: async (search?: string): Promise<Position[]> => {
    const response = await api.get<Position[]>('/positions/', {
      params: { search: search || undefined },
    })
    return response.data
  },
  createPosition: async (payload: CreatePositionPayload): Promise<Position> => {
    const response = await api.post<Position>('/positions/', payload)
    return response.data
  },
  updatePosition: async (positionId: number, payload: UpdatePositionPayload): Promise<Position> => {
    const response = await api.patch<Position>(`/positions/${positionId}`, payload)
    return response.data
  },
  deactivatePosition: async (positionId: number): Promise<void> => {
    await api.post(`/positions/deactivate/${positionId}`)
  },
  deletePosition: async (positionId: number): Promise<void> => {
    await api.delete(`/positions/${positionId}`)
  },
}
