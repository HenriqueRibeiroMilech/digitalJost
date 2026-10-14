import { requestJson } from '@/shared/api/client'
import { paginationQuery } from '@/shared/api/pagination'
import type { EventItem, EventList, EventsApi } from './types'

const realEventsApi: EventsApi = {
  list(page, perPage) {
    const query = paginationQuery(page, perPage)
    return requestJson<EventList>('/api/v1/events?' + query.toString())
  },
  create(payload) {
    return requestJson<EventItem>('/api/v1/events', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },
}

async function adapter(): Promise<EventsApi> {
  if (import.meta.env.DEV && import.meta.env.VITE_EVENTS_MOCK === 'true') {
    return (await import('./mock-api')).mockEventsApi
  }
  return realEventsApi
}

export const eventsApi: EventsApi = {
  async list(page, perPage) {
    return (await adapter()).list(page, perPage)
  },
  async create(payload) {
    return (await adapter()).create(payload)
  },
}
