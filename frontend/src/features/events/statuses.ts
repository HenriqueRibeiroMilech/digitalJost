import type { EventStatus } from './types'

// Apresentação apenas: a classificação vem da API, usando o relógio do TD.
export const eventStatuses = {
  upcoming: { label: 'Futuro', filterLabel: 'Futuros', icon: 'pi pi-calendar', tone: 'brand', severity: 'info' },
  ongoing: { label: 'Em andamento', filterLabel: 'Em andamento', icon: 'pi pi-play-circle', tone: 'success', severity: 'success' },
  completed: { label: 'Concluído', filterLabel: 'Concluídos', icon: 'pi pi-check-circle', tone: 'neutral', severity: 'secondary' },
  unscheduled: { label: 'Sem período', filterLabel: 'Sem período', icon: 'pi pi-clock', tone: 'neutral', severity: 'secondary' },
} as const

export const eventStatusOptions = (Object.keys(eventStatuses) as EventStatus[]).map(value => ({
  value, label: eventStatuses[value].filterLabel,
}))
export const defaultEventStatuses: EventStatus[] = ['upcoming', 'ongoing']
