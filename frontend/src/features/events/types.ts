import type { PaginatedResponse } from '@/shared/api/pagination'

export interface EventItem {
  id: number
  name: string
  description: string
  starts_at: string | null
  ends_at: string | null
}

export interface EventCreate {
  name: string
  description: string
  starts_at: string
  ends_at: string
}

export interface EventCapabilities {
  can_create: boolean
  can_update: boolean
  can_delete: boolean
}

export interface EventDetail extends EventItem {
  capabilities: EventCapabilities
}

export type EventList = PaginatedResponse<EventItem, EventCapabilities>
export type EventChange = 'created' | 'updated' | 'deleted'

export interface EventsApi {
  list(page: number, perPage: number): Promise<EventList>
  create(payload: EventCreate): Promise<EventItem>
  get(id: number): Promise<EventDetail>
  update(id: number, payload: EventCreate): Promise<EventItem>
  delete(id: number): Promise<{ id: number }>
}
