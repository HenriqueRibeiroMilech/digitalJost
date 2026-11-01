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
  agendado: { label: 'Início agendado', icon: 'pi pi-calendar', tone: 'brand' },
  em_andamento: { label: 'Em andamento', icon: 'pi pi-play-circle', tone: 'brand' },
  pausado: { label: 'Pausado', icon: 'pi pi-pause-circle', tone: 'neutral' },
  em_validacao: { label: 'Em validação', icon: 'pi pi-verified', tone: 'brand' },
  aguardando_terceiros: { label: 'Aguardando terceiros', icon: 'pi pi-users', tone: 'neutral' },
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
export const workFieldLabels: Record<string, string> = {
  ...planningLabels, status: 'Situação', scheduled_start_on: 'Início agendado', started_on: 'Início realizado',
  due_on: 'Prazo de entrega', closed_at: 'Encerramento',
  expected_return_on: 'Previsão de retorno', responsible_id: 'Responsável', title: 'Título', description: 'Descrição',
  contributor_id: 'Contribuinte', urgency: 'Urgência', assumptions: 'Premissas', current_problems: 'Problemas atuais',
  expected_benefits: 'Ganhos esperados', starts_at: 'Início do aviso', ends_at: 'Fim do aviso', hide_after_end: 'Ocultar após o fim',
  task: 'Tarefa',
}
const workHistoryLabels: Record<string, string> = {
  created: 'Cadastro criado', request_accepted: 'Criada a partir de solicitação aceita', planning_updated: 'Planejamento atualizado',
  start: 'Demanda iniciada', schedule: 'Início agendado', cancel: 'Demanda cancelada', complete: 'Demanda concluída',
  request_information: 'Mais informações solicitadas', validate: 'Validação iniciada', pause: 'Demanda pausada',
  wait_third_party: 'Aguardando terceiros', resume: 'Demanda retomada', change_deadline: 'Prazo alterado',
  reopen: 'Demanda reaberta', cancel_schedule: 'Agendamento cancelado', content_updated: 'Conteúdo e pessoas atualizados',
  notice_finalized: 'Aviso finalizado', task_created: 'Tarefa criada', task_updated: 'Tarefa atualizada', task_deleted: 'Tarefa excluída',
  auto_started: 'Início automático pelo agendamento',
}
export function workHistoryLabel(event: string) { return workHistoryLabels[event] ?? 'Atualização registrada' }

export function displayDay(value: string) {
  const parts = value.split('-')
  return parts.length === 3 ? `${parts[2]}/${parts[1]}/${parts[0]}` : 'Data indisponível'
}
export function workHistoryValue(field: string, value: string | null) {
  if (value === null) return 'Não informado'
  if (field === 'status') return statusLabel(value)
  if (['closed_at', 'starts_at', 'ends_at'].includes(field)) return displayDate(value.replace(' ', 'T'))
  return ['scheduled_start_on', 'started_on', 'due_on', 'expected_return_on'].includes(field) ? displayDay(value) : value
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

export const workStatusOptions = [
  { value: 'ativos', label: 'Em aberto' }, { value: 'todos', label: 'Todas as situações' },
  { value: 'atrasados', label: 'Atrasadas' },
  ...['a_fazer', 'agendado', 'em_andamento', 'aguardando_informacoes', 'em_validacao', 'pausado', 'aguardando_terceiros', 'concluido', 'cancelado']
    .map(value => ({ value, label: statusLabel(value) })),
]
export const noticeStateOptions = [
  { value: 'visible', label: 'Visíveis no mural' }, { value: 'all', label: 'Todos os avisos' },
  { value: 'active', label: 'Em vigor' }, { value: 'upcoming', label: 'Agendados' },
  { value: 'expired', label: 'Vencidos' }, { value: 'finalized', label: 'Finalizados' },
]
export function noticeStateLabel(state: string | null) {
  const labels: Record<string, string> = { active: 'Em vigor', upcoming: 'Agendado', expired: 'Vencido', finalized: 'Finalizado' }
  return state ? labels[state] ?? 'Aviso' : 'Aviso'
}

export function noticeInputTime(value: string | null) {
  if (!value) return ''
  const date = new Date(/(?:Z|[+-]\d{2}:\d{2})$/.test(value) ? value : value + 'Z')
  if (Number.isNaN(date.getTime())) return ''
  const pad = (number: number) => String(number).padStart(2, '0')
  return `${String(date.getFullYear()).padStart(4, '0')}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}.${String(date.getMilliseconds()).padStart(3, '0')}`
}
