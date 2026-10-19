<script setup lang="ts">
import RecordCard from '@/shared/components/RecordCard.vue'
import Tag from '@/volt/Tag.vue'
import { displayDate, kindLabel, statusLabel } from '../presentation'
import type { RequestItem } from '../types'

defineProps<{ request: RequestItem }>()
defineEmits<{ open: [] }>()
</script>

<template>
  <RecordCard :title-id="'request-title-' + request.id" :title="request.title" :description="request.description"
    :icon="request.entry_kind === 'erro' ? 'pi pi-exclamation-triangle' : 'pi pi-briefcase'"
    :action-id="'request-open-' + request.id" action-label="Ver solicitação" opens-dialog
    :tone="request.status === 'concluido' ? 'success' : 'brand'" @open="$emit('open')">
    <template #badge><Tag :value="statusLabel(request.status)" severity="secondary" /></template>
    <dl class="grid gap-2 text-xs leading-5">
      <div class="flex justify-between gap-3"><dt class="text-dj-muted">Identificação</dt><dd class="font-semibold">#{{ request.id }}</dd></div>
      <div class="flex justify-between gap-3"><dt class="text-dj-muted">Tipo</dt><dd>{{ kindLabel(request.entry_kind) }}</dd></div>
      <div class="flex justify-between gap-3"><dt class="text-dj-muted">Urgência</dt><dd>{{ request.urgency }}</dd></div>
      <div><dt class="text-dj-muted">Enviada em</dt><dd>{{ displayDate(request.created_at) }}</dd></div>
      <div v-if="request.relationship === 'contributor'" class="rounded-lg bg-dj-canvas px-3 py-2 text-dj-muted">
        Você acompanha como contribuinte. Solicitante: {{ request.requester_name ?? 'Não informado' }}.
      </div>
    </dl>
  </RecordCard>
</template>
