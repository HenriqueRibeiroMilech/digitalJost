export interface PaginatedResponse<Item, Capabilities> {
  items: Item[]
  page: number
  per_page: number
  total: number
  capabilities: Capabilities
}

export function paginationQuery(page: number, perPage: number): URLSearchParams {
  return new URLSearchParams({ page: String(page), per_page: String(perPage) })
}
