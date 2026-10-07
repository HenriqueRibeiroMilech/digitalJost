import { requestJson } from '@/shared/api/client'
import type { EventItem, EventList } from './types'

const realEventsApi: EventsApi = {
  list(page, perPage) {
    const query = new URLSearchParams({
      page: String(page),
      per_page: String(perPage),
    })
    return requestJson<EventList>('/api/v1/events?' + query.toString())
  },
  create(payload) {
    return requestJson<EventItem>('/api/v1/events', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },
}