<script setup lang="ts">
import { displayDate, statusLabel } from '../presentation'
import { dayLabel } from '../managementTypes'
import type { HistoryEvent } from '../types'
defineProps<{ events: HistoryEvent[] }>()
const labels: Record<string, string> = {
  created: 'Solicitação enviada', updated: 'Dados da solicitação atualizados', created_internal: 'Demanda cadastrada',
  management_updated: 'Gerenciamento atualizado', review_accept: 'Solicitação aceita', review_decline: 'Solicitação recusada',
  review_information: 'Informações ou reunião solicitadas', information_replied: 'Resposta do solicitante',
  status_start: 'Demanda iniciada', scheduled_start: 'Início automático agendado', status_complete: 'Demanda concluída',
  status_cancel: 'Demanda cancelada', status_schedule: 'Início agendado', status_unschedule: 'Agendamento cancelado',
  status_information: 'Informações ou reunião solicitadas', status_validate: 'Validação iniciada', status_pause: 'Demanda pausada',
  status_third_party: 'Aguardando terceiros', status_resume: 'Demanda retomada', deadline_changed: 'Prazo alterado',
  task_created: 'Tarefa criada', task_updated: 'Tarefa atualizada', task_deleted: 'Tarefa removida',
  attachments_added: 'Anexos adicionados', attachment_removed: 'Anexo removido',
}
const fields: Record<string, string> = { status: 'Status', deadline: 'Prazo', scheduled_start_date: 'Início agendado',
  title: 'Título', description: 'Descrição', urgency: 'Urgência', responsible_id: 'Responsável', assumptions: 'Premissas',
  current_problems: 'Problemas atuais', expected_benefits: 'Ganhos esperados', estimated_hours: 'Horas estimadas',
  daily_hours: 'Horas diárias', completed_hours: 'Horas realizadas', priority: 'Prioridade', difficulty: 'Dificuldade', observations: 'Observações',
  classification: 'Tipo', expected_return: 'Previsão de retorno', completed_at: 'Conclusão da tarefa' }
function changes(event: HistoryEvent) {
  return Object.entries(event.changes ?? {}).filter(([, value]) => value !== null && typeof value === 'object' && 'before' in value && 'after' in value)
    .map(([key, value]) => ({ key, label: fields[key] ?? key, ...(value as { before: unknown; after: unknown }) }))
}
function display(key: string, value: unknown): string {
  if (value === null || value === '') return 'Não informado'
  if (typeof value === 'boolean') return value ? 'Sim' : 'Não'
  if (key === 'status') return statusLabel(String(value))
  if (key === 'completed_at') return displayDate(String(value))
  if (key === 'deadline' || key === 'scheduled_start_date') return dayLabel(String(value))
  return String(value)
}
</script>
<template>
  <p v-if="!events.length" class="text-sm text-dj-muted">Nenhum evento registrado.</p>
  <ol class="space-y-5">
    <li v-for="event in events" :key="event.id" class="border-l-2 border-dj-border pl-4">
      <p class="text-sm font-semibold">{{ labels[event.event_type] ?? 'Atualização registrada' }}</p>
      <p class="mt-1 text-xs text-dj-muted">{{ event.actor_name ?? (event.event_type === 'scheduled_start' ? 'Sistema' : 'Autor indisponível') }} · {{ displayDate(event.created_at) }}</p>
      <p v-if="event.changes?.reason" class="mt-2 whitespace-pre-wrap break-words text-sm">{{ event.changes.reason }}</p>
      <p v-if="event.changes?.reply" class="mt-2 whitespace-pre-wrap break-words text-sm">{{ event.changes.reply }}</p>
      <p v-if="event.changes?.files" class="mt-2 break-words text-sm">{{ event.changes.files }}</p>
      <details v-if="changes(event).length" class="mt-2 text-sm">
        <summary class="cursor-pointer text-dj-brand">Ver alterações</summary>
        <dl class="mt-2 space-y-3 rounded-xl bg-dj-canvas p-3">
          <div v-for="change in changes(event)" :key="change.key">
            <dt class="font-medium">{{ change.label }}</dt>
            <dd class="whitespace-pre-wrap break-words text-xs leading-6 text-dj-muted">Anterior: {{ display(change.key, change.before) }}<br>Novo: {{ display(change.key, change.after) }}</dd>
          </div>
        </dl>
      </details>
    </li>
  </ol>
</template>
