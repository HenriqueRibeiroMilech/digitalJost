// A API e o TD usam o horário local do evento. Não converter com toISOString().
export function eventDate(value: string | null): Date | null {
  return value ? new Date(value) : null
}

export function eventDateTime(value: Date): string {
  const pad = (part: number, length = 2) => String(part).padStart(length, '0')
  return `${pad(value.getFullYear(), 4)}-${pad(value.getMonth() + 1)}-${pad(value.getDate())}`
    + `T${pad(value.getHours())}:${pad(value.getMinutes())}:${pad(value.getSeconds())}`
    + `.${pad(value.getMilliseconds(), 3)}`
}

export function formatEventDateTime(value: string | null): string {
  const date = eventDate(value)
  return date ? new Intl.DateTimeFormat('pt-BR', {
    day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
  }).format(date) : 'Não informado'
}

export function formatAttendanceDateTime(value: string | null | undefined): string {
  if (!value) return 'Não informado'
  // A API explicita UTC; tela e Excel mostram a primeira presença no fuso de Brasília.
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Não informado' : new Intl.DateTimeFormat('pt-BR', {
    timeZone: 'America/Sao_Paulo', hourCycle: 'h23',
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  }).format(date)
}
