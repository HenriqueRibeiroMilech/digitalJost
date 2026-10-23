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
  relationship: 'requester' | 'contributor'
}

export interface RequestDetail extends RequestItem {
  contributor_id: string | null
  contributor_name: string | null
  assumptions: string | null
  current_problems: string | null
  expected_benefits: string | null
  updated_at: string
  row_version: string
  can_update: boolean
  attachments: { id: number; original_name: string; size_bytes: number }[]
  history: { id: number; event_type: string; actor_name: string | null; created_at: string }[]
}

export interface RequestFilters {
  search: string
  entry_kind: 'todos' | EntryKind
}

export interface Contributor { id: string; name: string }
export type RequestList = PaginatedResponse<RequestItem, { can_create: boolean }>
