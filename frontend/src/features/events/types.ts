import type { PaginatedResponse } from '@/shared/api/pagination'

export type EventStatus = 'upcoming' | 'ongoing' | 'completed' | 'unscheduled'

export interface EventFilters {
  search: string
  statuses: EventStatus[]
}

export interface EventItem {
  id: number
  name: string
  description: string
  starts_at: string | null
  ends_at: string | null
  status: EventStatus
}

export interface EventCreate {
  name: string
  description: string
  starts_at: string
  ends_at: string
}

export interface EventCapabilities {
  can_create: boolean
  can_update: boolean
  can_delete: boolean
}

export interface EventDetail extends EventItem {
  capabilities: EventCapabilities
}

export type EventList = PaginatedResponse<EventItem, EventCapabilities>
export type EventChange = 'created' | 'updated' | 'deleted'

export interface EventsApi {
  list(page: number, perPage: number, filters: EventFilters): Promise<EventList>
  create(payload: EventCreate): Promise<EventItem>
  get(id: number): Promise<EventDetail>
  update(id: number, payload: EventCreate): Promise<EventItem>
  delete(id: number): Promise<{ id: number }>
}

export interface AttendanceCapabilities {
  can_create: boolean
  can_register: boolean
}

export interface AttendanceListItem {
  id: number
  event_id: number
  name: string
  total: number
}

export interface AttendanceListDetail extends AttendanceListItem {
  capabilities: AttendanceCapabilities
}

export interface AttendanceEntry {
  id: number
  registration: string
  name: string | null
  department: string | null
  company: string | null
  shift: string | null
}

export interface AttendanceRegistered {
  item: AttendanceEntry
  created: boolean
  lookup_status: AttendanceLookupStatus
}

export type AttendanceLookupStatus = 'complete' | 'partial'
export type AttendanceLookupFailure = 'not_found' | 'unavailable' | 'ambiguous' | 'unsupported_badge'

export type AttendanceLists = PaginatedResponse<AttendanceListItem, AttendanceCapabilities>
export type AttendanceEntries = PaginatedResponse<AttendanceEntry, AttendanceCapabilities>
