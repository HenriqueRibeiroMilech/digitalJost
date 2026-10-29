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
