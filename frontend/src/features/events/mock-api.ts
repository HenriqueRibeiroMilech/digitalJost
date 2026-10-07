import type { EventItem, EventsApi } from './types'

let nextId = 3
const events: EventItem[] = [
  { id: 2, name: 'Encontro de integração', description: 'Apresentação das rotinas da equipe.' },
  { id: 1, name: 'Oficina de melhoria', description: 'Discussão de oportunidades no processo.' },
]

export const mockEventsApi: EventsApi = {
  async list(page, perPage) {
    const start = (page - 1) * perPage
    return {
      items: events.slice(start, start + perPage).map(event => ({ ...event })),
      page,
      per_page: perPage,
      total: events.length,
      capabilities: { can_create: true },
    }
  },
  async create(payload) {
    const event = { id: nextId++, ...payload }
    events.unshift(event)
    return { ...event }
  },
}