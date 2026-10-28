export const entryOptions = [
  { value: 'demanda', label: 'Solicitar demanda' },
  { value: 'erro', label: 'Reportar erro' },
]
export const urgencyOptions = ['Alta', 'Média', 'Baixa']
export const fileAccept = '.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.pdf,.png,.jpg,.jpeg,.gif,.bmp,.webp'

const statuses: Record<string, { label: string; icon: string; tone: 'brand' | 'success' | 'neutral' }> = {
  em_analise: { label: 'Em análise', icon: 'pi pi-search', tone: 'brand' },
  a_fazer: { label: 'A fazer', icon: 'pi pi-list', tone: 'brand' },
  em_andamento: { label: 'Em andamento', icon: 'pi pi-play-circle', tone: 'brand' },
  pausado: { label: 'Pausado', icon: 'pi pi-pause-circle', tone: 'neutral' },
  concluido: { label: 'Concluído', icon: 'pi pi-check-circle', tone: 'success' },
  cancelado: { label: 'Cancelado', icon: 'pi pi-times-circle', tone: 'neutral' },
  recusado: { label: 'Recusado', icon: 'pi pi-ban', tone: 'neutral' },
}
export function requestStatus(status: string) {
  return statuses[status] ?? { label: status, icon: 'pi pi-info-circle', tone: 'neutral' as const }
}
export function statusLabel(status: string) { return requestStatus(status).label }
export function kindLabel(kind: string) { return kind === 'erro' ? 'Relato de erro' : 'Demanda' }

export function displayDate(value: string) {
  // As tabelas modernas desta feature armazenam UTC; o portal exibe a hora local.
  const date = new Date(/(?:Z|[+-]\d{2}:\d{2})$/.test(value) ? value : value + 'Z')
  return Number.isNaN(date.getTime()) ? 'Data indisponível'
    : new Intl.DateTimeFormat('pt-BR', { dateStyle: 'medium', timeStyle: 'short' }).format(date)
}

export function fileSize(bytes: number) {
  return bytes >= 1024 * 1024 ? `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    : `${Math.max(1, Math.ceil(bytes / 1024))} KB`
}
