<script setup lang="ts">
import { computed } from 'vue'
import RecordCard from '@/shared/components/RecordCard.vue'
import Tag from '@/volt/Tag.vue'
import { displayDate, displayDay, displayHours, noticeStateLabel, requestStatus, workKind } from '../presentation'
import type { WorkItem } from '../types'

const props = defineProps<{ item: WorkItem }>()
defineEmits<{ open: [] }>()
const kind = computed(() => workKind(props.item.kind))
const status = computed(() => requestStatus(props.item.status))
</script>

<template>
  <RecordCard :title-id="'work-title-' + item.id" :title="item.title" :description="item.description"
    :action-id="'work-open-' + item.id" :action-label="item.kind === 'aviso' ? 'Ver aviso' : 'Ver demanda'"
    :tone="item.kind === 'aviso' ? 'neutral' : status.tone" opens-dialog compact @open="$emit('open')">
    <template #marker>
      <span class="inline-flex items-center gap-2 text-xs font-semibold text-dj-ink">
        <span class="inline-flex size-(--dj-card-marker-size) items-center justify-center rounded-xl bg-primary-50 text-dj-brand" aria-hidden="true"><i :class="kind.icon" /></span>
        <span :aria-label="'Registro número ' + item.id">#{{ item.id }}</span>
      </span>
    </template>
    <template #badge>
      <Tag :value="kind.label" severity="secondary" rounded />
    </template>
    <template v-if="item.kind === 'aviso'">
      <Tag :value="noticeStateLabel(item.notice_state)" severity="secondary" rounded class="mb-3" />
      <dl class="grid gap-2 text-xs leading-5 text-dj-muted">
        <div class="flex min-w-0 gap-2"><dt>Responsável:</dt><dd class="min-w-0 truncate text-dj-ink" :title="item.responsible_name ?? 'Usuário indisponível'">{{ item.responsible_name ?? 'Usuário indisponível' }}</dd></div>
        <div><dt class="font-semibold">Início</dt><dd>{{ item.starts_at ? displayDate(item.starts_at) : 'Não informado' }}</dd></div>
        <div><dt class="font-semibold">Fim</dt><dd>{{ item.ends_at ? displayDate(item.ends_at) : 'Não informado' }}</dd></div>
      </dl>
    </template>
    <template v-else>
      <div class="flex flex-wrap gap-2">
        <Tag :value="status.label" :icon="status.icon" severity="secondary" rounded class="dj-tone-badge text-xs" :class="'dj-tone-' + status.tone" />
        <Tag v-if="item.priority !== null" :value="'Prioridade ' + item.priority" severity="secondary" rounded />
        <Tag v-if="item.difficulty" :value="'Dificuldade ' + item.difficulty" severity="secondary" rounded />
        <Tag v-if="item.is_overdue" value="Atrasada" severity="danger" rounded icon="pi pi-clock" />
      </div>
      <p class="mt-3 break-words text-xs leading-5 text-dj-muted">
        {{ item.source_request_id ? 'Solicitante' : 'Criada por' }}: {{ item.requester_name ?? 'Usuário indisponível' }}
        <span v-if="item.source_request_id"> · Solicitação #{{ item.source_request_id }}</span>
      </p>
      <dl class="mt-3 grid grid-cols-2 gap-3 border-t border-dj-border pt-3 text-xs leading-5">
        <div><dt class="text-dj-muted">Tempo total</dt><dd class="font-semibold text-dj-ink">{{ displayHours(item.estimated_hours) }}</dd></div>
        <div><dt class="text-dj-muted">Realizado</dt><dd class="font-semibold text-dj-ink">{{ displayHours(item.completed_hours) }}</dd></div>
        <div><dt class="text-dj-muted">Tempo diário</dt><dd class="font-semibold text-dj-ink">{{ displayHours(item.daily_hours) }}</dd></div>
        <div v-if="item.due_on"><dt class="text-dj-muted">Prazo de entrega</dt><dd class="font-semibold text-dj-ink">{{ displayDay(item.due_on) }}</dd></div>
        <div v-if="item.scheduled_start_on && !item.started_on"><dt class="text-dj-muted">Início agendado</dt><dd class="font-semibold text-dj-ink">{{ displayDay(item.scheduled_start_on) }}</dd></div>
        <div v-if="item.started_on"><dt class="text-dj-muted">Início realizado</dt><dd class="font-semibold text-dj-ink">{{ displayDay(item.started_on) }}</dd></div>
        <div v-if="item.expected_return_on"><dt class="text-dj-muted">Previsão de retorno</dt><dd class="font-semibold text-dj-ink">{{ displayDay(item.expected_return_on) }}</dd></div>
      </dl>
      <p v-if="item.observations" class="mt-3 line-clamp-2 whitespace-pre-wrap break-words text-xs leading-5 text-dj-muted">
        <span class="font-semibold">Observações:</span> {{ item.observations }}
      </p>
    </template>
  </RecordCard>
</template>
