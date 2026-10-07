export interface EventItem {
  id: number
  name: string
  description: string
}

export interface EventCreate {
  name: string
  description: string
}

export interface EventList {
  items: EventItem[]
  page: number
  per_page: number
  total: number
  capabilities: { can_create: boolean }
}

export interface EventsApi {
  list(page: number, perPage: number): Promise<EventList>
  create(payload: EventCreate): Promise<EventItem>
}