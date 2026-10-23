export const entryOptions = [
  { value: 'demanda', label: 'Solicitar demanda' },
  { value: 'erro', label: 'Reportar erro' },
]
export const urgencyOptions = ['Alta', 'Média', 'Baixa']
export const fileAccept = '.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.pdf,.png,.jpg,.jpeg,.gif,.bmp,.webp'

const statuses: Record<string, string> = {
  em_analise: 'Em análise', a_fazer: 'A fazer', em_andamento: 'Em andamento',
  pausado: 'Pausado', concluido: 'Concluído', cancelado: 'Cancelado', recusado: 'Recusado',
  em_validacao: 'Em validação', aguardando_terceiros: 'Aguardando terceiros', aguardando_informacoes: 'Aguardando informações',
}
export function statusLabel(status: string) { return statuses[status] ?? status }
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
