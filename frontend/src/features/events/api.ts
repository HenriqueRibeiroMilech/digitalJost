import { requestJson } from '@/shared/api/client'
import { paginationQuery } from '@/shared/api/pagination'
import type { EventDetail, EventItem, EventList, EventsApi, EventType, EventTypes } from './types'

export const eventsApi: EventsApi = {
  types() {
    return requestJson<EventTypes>('/api/v1/events/types')
  },
  createType(name) {
    return requestJson<EventType>('/api/v1/events/types', {
      method: 'POST', body: JSON.stringify({ name }),
    })
  },
  list(page, perPage, filters) {
    const query = paginationQuery(page, perPage)
    query.set('search', filters.search)
    query.set('status', (filters.statuses.length ? filters.statuses
      : ['upcoming', 'ongoing', 'completed', 'unscheduled']).join(','))
    return requestJson<EventList>('/api/v1/events?' + query.toString())
  },
  create(payload) {
    return requestJson<EventItem>('/api/v1/events', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },
  get(id) {
    return requestJson<EventDetail>(`/api/v1/events/${id}`)
  },
  update(id, payload) {
    return requestJson<EventItem>(`/api/v1/events/${id}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    })
  },
  delete(id) {
    return requestJson<{ id: number }>(`/api/v1/events/${id}`, { method: 'DELETE' })
  },
}
