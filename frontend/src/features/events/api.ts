import { requestJson } from '@/shared/api/client'
import { paginationQuery } from '@/shared/api/pagination'
import type { EventItem, EventList, EventsApi } from './types'

export const eventsApi: EventsApi = {
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
