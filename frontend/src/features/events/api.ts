import type { EventsApi } from './types'

async function adapter(): Promise<EventsApi> {
  if (import.meta.env.DEV && import.meta.env.VITE_EVENTS_MOCK === 'true') {
    return (await import('./mock-api')).mockEventsApi
  }
  throw new Error('O adaptador real de Eventos ainda precisa ser implementado.')
}

export const eventsApi: EventsApi = {
  async list(page, perPage) {
    return (await adapter()).list(page, perPage)
  },
  async create(payload) {
    return (await adapter()).create(payload)
  },
}