import type { PaginatedResponse } from '@/shared/api/pagination'

export type EntryKind = 'demanda' | 'erro'

export interface RequestFields {
  entry_kind: EntryKind
  title: string
  description: string
  urgency: 'Alta' | 'Média' | 'Baixa'
  contributor_id: string | null
  assumptions: string | null
  current_problems: string | null
  expected_benefits: string | null
}

export interface RequestItem {
  id: number
  entry_kind: EntryKind
  title: string
  description: string
  urgency: string
  status: string
  created_at: string
  requester_name: string | null
  relationship: 'requester' | 'contributor' | 'manager'
}

export interface RequestDetail extends RequestItem {
  contributor_id: string | null
  contributor_name: string | null
  responsible_id: string | null
  responsible_name: string | null
  classification: string | null
  assumptions: string | null
  current_problems: string | null
  expected_benefits: string | null
  updated_at: string
  row_version: string
  can_update: boolean
  can_review: boolean
  attachments: { id: number; original_name: string; size_bytes: number }[]
  history: { id: number; event_type: string; actor_name: string | null; created_at: string; message: string | null }[]
}

export interface RequestFilters {
  search: string
  entry_kind: 'todos' | EntryKind
}

export interface Contributor { id: string; name: string }
export type RequestList = PaginatedResponse<RequestItem, { can_create: boolean }>

export interface ManagementFilters extends RequestFilters {
  status: 'pendentes' | 'todos' | 'em_analise' | 'aguardando_informacoes' | 'a_fazer' | 'recusado'
}

export interface ReviewFields {
  action: 'accept' | 'reject' | 'request_information'
  row_version: string
  responsible_id: string | null
  classification: 'melhoria' | 'projeto' | null
  message: string | null
}

export type WorkKind = 'projeto' | 'melhoria' | 'erro' | 'atividade' | 'aviso'
export type WorkActionName = 'start' | 'cancel' | 'schedule' | 'request_information' | 'complete'
  | 'validate' | 'pause' | 'wait_third_party' | 'resume' | 'change_deadline' | 'reopen' | 'cancel_schedule'

export interface WorkAction {
  action: WorkActionName
  row_version: string
  scheduled_start_on: string | null
  due_on: string | null
  expected_return_on: string | null
  message: string | null
}

export interface WorkCreate {
  kind: WorkKind
  title: string
  description: string
  responsible_id: string
  contributor_id: string | null
  urgency: RequestFields['urgency'] | null
  assumptions: string | null
  current_problems: string | null
  expected_benefits: string | null
  starts_at: string | null
  ends_at: string | null
  hide_after_end: boolean
  submission_key: string
}

export type WorkContent = Omit<WorkCreate, 'submission_key'> & { row_version: string }

export interface WorkPlanning {
  difficulty: 'Baixa' | 'Média' | 'Alta' | null
  priority: number | null
  estimated_hours: number | null
  daily_hours: number | null
  completed_hours: number
  observations: string | null
}

export interface WorkItem extends WorkPlanning {
  id: number
  source_request_id: number | null
  kind: WorkKind
  title: string
  description: string
  responsible_id: string
  requester_id: string
  contributor_id: string | null
  responsible_name: string | null
  requester_name: string | null
  contributor_name: string | null
  urgency: string | null
  assumptions: string | null
  current_problems: string | null
  expected_benefits: string | null
  starts_at: string | null
  ends_at: string | null
  hide_after_end: boolean
  notice_finalized_at: string | null
  notice_state: 'active' | 'upcoming' | 'expired' | 'finalized' | null
  status: string
  scheduled_start_on: string | null
  started_on: string | null
  due_on: string | null
  expected_return_on: string | null
  is_overdue: boolean
  closed_at: string | null
  created_at: string
  updated_at: string
}

export interface WorkDetail extends WorkItem {
  row_version: string
  can_update: boolean
  can_edit_content: boolean
  can_manage_tasks: boolean
  available_actions: WorkActionName[]
  attachments: RequestDetail['attachments']
  history: { id: number; event_type: string; actor_name: string | null; created_at: string; fields: string[]
    message: string | null; transitions: { field: string; before: string | null; after: string | null }[] }[]
}

export interface WorkBoard {
  owners: { id: string; name: string; total: number }[]
  notice_total: number
  actor_id: string
  can_create: boolean
}

export interface WorkFilters {
  view: 'users' | 'notices'
  owner_id: string | null
  search: string
  kind: 'todos' | Exclude<WorkKind, 'aviso'>
  status: 'todos' | 'ativos' | 'atrasados' | 'a_fazer' | 'agendado' | 'em_andamento' | 'aguardando_informacoes'
    | 'em_validacao' | 'pausado' | 'aguardando_terceiros' | 'concluido' | 'cancelado'
  difficulty: 'todas' | 'Baixa' | 'Média' | 'Alta'
  sort: 'priority' | 'deadline' | 'newest'
  notice_state: 'visible' | 'all' | 'active' | 'upcoming' | 'expired' | 'finalized'
}
export type WorkList = PaginatedResponse<WorkItem, { can_create: boolean }>

export interface TaskFields {
  title: string
  description: string | null
  responsible_id: string
  priority: number | null
  due_on: string | null
  completed: boolean
}
export interface TaskItem extends Omit<TaskFields, 'completed'> {
  id: number
  responsible_name: string | null
  completed_at: string | null
  row_version: string
}
export type TaskStatus = 'all' | 'pending' | 'completed'
export type TaskSort = 'priority' | 'deadline'
export type TaskList = PaginatedResponse<TaskItem, { can_update: boolean }>
