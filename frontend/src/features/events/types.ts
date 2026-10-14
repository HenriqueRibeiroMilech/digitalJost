import type { PaginatedResponse } from '@/shared/api/pagination'

export interface EventItem {
  id: number
  name: string
  description: string
}

export interface EventCreate {
  name: string
  description: string
}

export type EventList = PaginatedResponse<EventItem, { can_create: boolean }>

export interface EventsApi {
  list(page: number, perPage: number): Promise<EventList>
  create(payload: EventCreate): Promise<EventItem>
}
