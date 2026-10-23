<script setup lang="ts">
import RecordCard from '@/shared/components/RecordCard.vue'
import Tag from '@/volt/Tag.vue'
import type { ManagedDemand } from '../managementTypes'
import { dayLabel, demandTypeLabel } from '../managementTypes'
import { statusLabel } from '../presentation'
defineProps<{ demand: ManagedDemand; today: string }>()
defineEmits<{ open: [] }>()
</script>
<template>
  <RecordCard :title-id="'managed-title-' + demand.id" :title="demand.title" :description="demand.description" action-label="Abrir demanda"
    :action-id="'managed-open-' + demand.id" opens-dialog compact :tone="demand.status === 'concluido' ? 'success' : 'brand'" @open="$emit('open')">
    <template #marker><span class="text-xs font-semibold">#{{ demand.id }} · {{ demandTypeLabel(demand.demand_type) }}</span></template>
    <template #badge><Tag :value="statusLabel(demand.status)" severity="secondary" /></template>
    <div class="mb-3 flex flex-wrap gap-1.5">
      <Tag v-if="demand.scheduled_start_date" value="Demanda agendada" severity="info" />
      <Tag v-if="demand.priority" :value="'Prioridade ' + demand.priority" />
      <Tag v-if="demand.difficulty" :value="'Dificuldade ' + demand.difficulty" severity="secondary" />
      <Tag v-if="demand.deadline && demand.deadline < today && demand.status !== 'concluido'" value="Atrasada" severity="danger" />
    </div>
    <p class="mb-3 line-clamp-1 text-xs text-dj-muted">{{ demand.origin === 'interna' ? 'Criada por' : 'Solicitante' }}: {{ demand.requester_name ?? 'Não informado' }}</p>
    <dl class="grid grid-cols-2 gap-x-3 gap-y-3 text-xs">
      <div><dt class="text-dj-muted">{{ demand.scheduled_start_date ? 'Início agendado' : 'Início' }}</dt><dd class="mt-1 font-medium">{{ dayLabel(demand.scheduled_start_date ?? demand.started_at) }}</dd></div>
      <div><dt class="text-dj-muted">Prazo</dt><dd class="mt-1 font-medium">{{ dayLabel(demand.deadline) }}</dd></div>
      <div><dt class="text-dj-muted">Estimado / realizado</dt><dd class="mt-1">{{ demand.estimated_hours ?? '—' }} / {{ demand.completed_hours ?? '—' }} h</dd></div>
      <div><dt class="text-dj-muted">Tempo diário</dt><dd class="mt-1">{{ demand.daily_hours ?? '—' }} h</dd></div>
      <div><dt class="text-dj-muted">Tarefas</dt><dd class="mt-1">{{ demand.completed_tasks }}/{{ demand.total_tasks }}</dd></div>
      <div v-if="demand.expected_return"><dt class="text-dj-muted">Previsão de retorno</dt><dd class="mt-1">{{ dayLabel(demand.expected_return) }}</dd></div>
    </dl>
    <p v-if="demand.observations" class="mt-3 line-clamp-2 whitespace-pre-wrap break-words text-xs leading-5 text-dj-muted">{{ demand.observations }}</p>
  </RecordCard>
</template>
