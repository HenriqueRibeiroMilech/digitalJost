import type { Contributor, HistoryEvent, InformationRequest } from './types'

export type DemandType = 'projeto' | 'melhoria' | 'erro' | 'atividade'
export interface ManagementFields {
  title: string; description: string; responsible_id: string; urgency: 'Alta' | 'Média' | 'Baixa'
  assumptions: string | null; current_problems: string | null; expected_benefits: string | null
  estimated_hours: number | null; daily_hours: number | null; completed_hours: number | null
  difficulty: string | null; priority: number | null; observations: string | null
}
export interface ManagedDemand extends Omit<ManagementFields, 'responsible_id'> {
  id: number; entry_kind: string; demand_type: DemandType | null; origin: string; status: string
  requester_name: string | null; responsible_name: string | null; responsible_id: string | null
  created_at: string; started_at: string | null; completed_at: string | null
  deadline: string | null; scheduled_start_date: string | null; expected_return: string | null
  total_tasks: number; completed_tasks: number; row_version: string; can_edit: boolean
}
export interface Task {
  id: number; description: string; responsible_id: string | null; responsible_name: string | null
  priority: number | null; deadline: string | null; observations: string | null; completed_at: string | null; row_version: string
}
export interface ManagedDetail extends ManagedDemand {
  contributor_name: string | null
  attachments: { id: number; original_name: string; size_bytes: number }[]
  tasks: Task[]; history: HistoryEvent[]; information_requests: InformationRequest[]
  notification_warning?: string | null
}
export interface Notice {
  id: number; title: string; description: string; starts_at: string | null; ends_at: string | null
  hide_after_end: boolean; created_by_name: string | null; row_version: string; can_edit: boolean
}
export interface ManagementOptions { responsibles: Contributor[]; contributors: Contributor[]; current_user_id: string; today: string }
export interface BoardFilters { search: string; responsible_id: string; demand_type: string; status: string; difficulty: string; sort: string; completed_from: string | null; completed_to: string | null }
export interface Board { items: ManagedDemand[]; notices: Notice[]; today: string }

export function blankManagementFields(user = '', demand?: ManagedDemand): ManagementFields {
  return {
    title: demand?.title ?? '', description: demand?.description ?? '', responsible_id: demand?.responsible_id ?? user,
    urgency: demand?.urgency ?? 'Média', assumptions: demand?.assumptions ?? '', current_problems: demand?.current_problems ?? '',
    expected_benefits: demand?.expected_benefits ?? '', estimated_hours: demand?.estimated_hours ?? null,
    daily_hours: demand?.daily_hours ?? null, completed_hours: demand?.completed_hours ?? null,
    difficulty: demand?.difficulty ?? null, priority: demand?.priority ?? null, observations: demand?.observations ?? '',
  }
}
export const demandTypes = [
  { value: 'projeto', label: 'Projeto' }, { value: 'melhoria', label: 'Melhoria' },
  { value: 'erro', label: 'Erro' }, { value: 'atividade', label: 'Atividade' },
]
export function demandTypeLabel(type: string | null) { return demandTypes.find(item => item.value === type)?.label ?? 'Demanda' }
export function dayLabel(value: string | null) {
  if (!value) return 'Não informado'
  if (value.length === 10) return value.split('-').reverse().join('/')
  const date = new Date(/(?:Z|[+-]\d{2}:\d{2})$/.test(value) ? value : value + 'Z')
  return Number.isNaN(date.getTime()) ? 'Não informado' : new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short' }).format(date)
}
export function dateValue(date: Date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}
export function localDateTimeLabel(value: string | null) {
  if (!value) return 'Não informado'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Não informado' : new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' }).format(date)
}
