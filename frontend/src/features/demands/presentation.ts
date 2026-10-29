import type { WorkKind } from './types'

export const entryOptions = [
  { value: 'demanda', label: 'Solicitar demanda' },
  { value: 'erro', label: 'Reportar erro' },
]
export const urgencyOptions = ['Alta', 'Média', 'Baixa']
export const fileAccept = '.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.pdf,.png,.jpg,.jpeg,.gif,.bmp,.webp'

const statuses: Record<string, { label: string; icon: string; tone: 'brand' | 'success' | 'neutral' }> = {
  em_analise: { label: 'Em análise', icon: 'pi pi-search', tone: 'brand' },
  aguardando_informacoes: { label: 'Aguardando informações', icon: 'pi pi-comment', tone: 'neutral' },
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

const historyLabels: Record<string, string> = {
  created: 'Solicitação enviada', updated: 'Dados atualizados', accepted: 'Solicitação aceita',
  rejected: 'Solicitação recusada', information_requested: 'Mais informações solicitadas',
  information_provided: 'Informações complementadas pelo solicitante',
}
export function historyLabel(event: string) { return historyLabels[event] ?? 'Atualização registrada' }

export const workKindOptions: { value: WorkKind; label: string; icon: string }[] = [
  { value: 'projeto', label: 'Projeto', icon: 'pi pi-briefcase' },
  { value: 'melhoria', label: 'Melhoria', icon: 'pi pi-lightbulb' },
  { value: 'erro', label: 'Erro', icon: 'pi pi-exclamation-triangle' },
  { value: 'atividade', label: 'Atividade', icon: 'pi pi-check-square' },
  { value: 'aviso', label: 'Aviso', icon: 'pi pi-megaphone' },
]
export function workKind(kind: string) {
  return workKindOptions.find(option => option.value === kind)
    ?? { value: 'atividade', label: 'Atividade', icon: 'pi pi-check-square' }
}
export const planningLabels: Record<string, string> = {
  difficulty: 'Dificuldade', priority: 'Prioridade', estimated_hours: 'Tempo total (h)',
  daily_hours: 'Tempo diário (h)', completed_hours: 'Tempo total realizado (h)', observations: 'Observações',
}
export function displayHours(value: number | null) {
  return value === null ? 'Não informado' : new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2 }).format(value) + ' h'
}

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
