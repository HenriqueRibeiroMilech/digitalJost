<script setup lang="ts">
import { computed } from 'vue'
import RecordCard from '@/shared/components/RecordCard.vue'
import Tag from '@/volt/Tag.vue'
import { displayDate, displayHours, requestStatus, workKind } from '../presentation'
import type { WorkItem } from '../types'

const props = defineProps<{ item: WorkItem }>()
defineEmits<{ open: [] }>()
const kind = computed(() => workKind(props.item.kind))
const status = computed(() => requestStatus(props.item.status))
</script>

<template>
  <RecordCard :title-id="'work-title-' + item.id" :title="item.title" :description="item.description" :icon="kind.icon"
    :action-id="'work-open-' + item.id" :action-label="item.kind === 'aviso' ? 'Ver aviso' : 'Ver demanda'"
    :tone="item.kind === 'aviso' ? 'neutral' : status.tone" opens-dialog compact @open="$emit('open')">
    <template #badge>
      <Tag :value="kind.label + ' #' + item.id" severity="secondary" rounded />
    </template>
    <dl class="grid gap-2 text-xs leading-5 text-dj-muted">
      <div class="flex min-w-0 gap-2"><dt>Responsável:</dt><dd class="min-w-0 truncate text-dj-ink" :title="item.responsible_name ?? 'Usuário indisponível'">{{ item.responsible_name ?? 'Usuário indisponível' }}</dd></div>
      <template v-if="item.kind === 'aviso'">
        <div><dt class="font-semibold">Início</dt><dd>{{ item.starts_at ? displayDate(item.starts_at) : 'Não informado' }}</dd></div>
        <div><dt class="font-semibold">Fim</dt><dd>{{ item.ends_at ? displayDate(item.ends_at) : 'Não informado' }}</dd></div>
      </template>
      <template v-else>
        <div class="flex flex-wrap gap-x-3 gap-y-1">
          <dt class="sr-only">Situação</dt><dd>{{ status.label }}</dd>
          <dt class="sr-only">Prioridade</dt><dd>{{ item.priority === null ? 'Sem prioridade' : 'Prioridade ' + item.priority }}</dd>
        </div>
        <div><dt class="sr-only">Tempo realizado e total</dt><dd>Realizado: {{ displayHours(item.completed_hours) }} · Total: {{ displayHours(item.estimated_hours) }}</dd></div>
        <div v-if="item.source_request_id"><dt class="sr-only">Origem</dt><dd>Solicitação #{{ item.source_request_id }}</dd></div>
      </template>
    </dl>
  </RecordCard>
</template>
