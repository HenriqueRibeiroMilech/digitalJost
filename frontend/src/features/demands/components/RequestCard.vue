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
    :action-id="'request-open-' + request.id" action-label="Ver solicitação" opens-dialog compact
    :tone="request.status === 'concluido' ? 'success' : 'brand'" @open="$emit('open')">
    <template #marker>
      <div class="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1 text-xs leading-5">
        <span class="font-semibold text-dj-ink" :aria-label="'Solicitação número ' + request.id">#{{ request.id }}</span>
        <span class="inline-flex items-center gap-1 text-dj-muted">
          <i :class="request.entry_kind === 'erro' ? 'pi pi-exclamation-triangle' : 'pi pi-briefcase'" aria-hidden="true" />
          {{ kindLabel(request.entry_kind) }}
        </span>
      </div>
    </template>
    <template #badge><Tag :value="statusLabel(request.status)" severity="secondary" class="shrink-0" /></template>
    <dl class="flex flex-wrap items-baseline gap-x-4 gap-y-1 text-xs leading-5">
      <div class="inline-flex items-baseline gap-1.5">
        <dt class="text-dj-muted">Urgência</dt><dd class="font-medium">{{ request.urgency }}</dd>
      </div>
      <div class="min-w-0">
        <dt class="sr-only">Enviada em</dt>
        <dd class="flex min-w-0 items-center gap-1.5 text-dj-muted">
          <i class="pi pi-calendar shrink-0" aria-hidden="true" />
          <span class="min-w-0">{{ displayDate(request.created_at) }}</span>
        </dd>
      </div>
    </dl>
    <p v-if="request.relationship === 'contributor'" class="mt-2 truncate text-xs leading-5 text-dj-muted"
      :title="'Você acompanha como contribuinte. Solicitante: ' + (request.requester_name ?? 'Não informado')">
      Contribuinte · Solicitante: {{ request.requester_name ?? 'Não informado' }}
    </p>
  </RecordCard>
</template>
