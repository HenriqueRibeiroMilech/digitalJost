<script setup lang="ts">
import { computed } from 'vue'
import RecordCard from '@/shared/components/RecordCard.vue'
import Tag from '@/volt/Tag.vue'
import { displayDate, kindLabel, requestStatus } from '../presentation'
import type { RequestItem } from '../types'

const props = defineProps<{ request: RequestItem; management?: boolean }>()
defineEmits<{ open: [] }>()
const status = computed(() => requestStatus(props.request.status))
const urgencyClass = computed(() => props.request.urgency === 'Alta' ? 'bg-dj-danger-soft text-dj-danger'
  : props.request.urgency === 'Média' ? 'bg-primary-50 text-dj-brand' : 'bg-surface-100 text-dj-muted')
</script>

<template>
  <RecordCard :title-id="'request-title-' + request.id" :title="request.title" :description="request.description"
    :action-id="'request-open-' + request.id" action-label="Ver solicitação" opens-dialog compact
    :tone="status.tone" @open="$emit('open')">
    <template #marker>
      <div class="flex min-w-0 items-center gap-2.5 text-xs leading-5">
        <span class="inline-flex size-(--dj-card-marker-size) shrink-0 items-center justify-center rounded-xl text-base"
          :class="request.entry_kind === 'erro' ? 'bg-dj-danger-soft text-dj-danger' : 'bg-primary-50 text-dj-brand'" aria-hidden="true">
          <i :class="request.entry_kind === 'erro' ? 'pi pi-exclamation-triangle' : 'pi pi-briefcase'" />
        </span>
        <span class="font-semibold text-dj-ink" :aria-label="'Solicitação número ' + request.id">#{{ request.id }}</span>
      </div>
    </template>
    <template #badge>
      <Tag :value="status.label" :icon="status.icon" severity="secondary" rounded
        class="dj-tone-badge text-xs" :class="'dj-tone-' + status.tone" />
    </template>
    <dl class="flex flex-wrap items-center gap-x-3 gap-y-2 text-xs leading-5">
      <div class="min-w-0">
        <dt class="sr-only">Tipo</dt>
        <dd class="text-dj-muted">{{ kindLabel(request.entry_kind) }}</dd>
      </div>
      <div>
        <dt class="sr-only">Urgência</dt>
        <dd class="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 font-semibold" :class="urgencyClass">
          <i class="pi pi-flag text-xs" aria-hidden="true" />{{ request.urgency }}
        </dd>
      </div>
      <div class="min-w-0 basis-full">
        <dt class="sr-only">Enviada em</dt>
        <dd class="flex min-w-0 items-center gap-1.5 text-dj-muted">
          <i class="pi pi-calendar shrink-0" aria-hidden="true" />
          <span class="min-w-0">{{ displayDate(request.created_at) }}</span>
        </dd>
      </div>
    </dl>
    <p v-if="management" class="mt-2 truncate text-xs leading-5 text-dj-muted" :title="request.requester_name ?? 'Não informado'">
      Solicitante: {{ request.requester_name ?? 'Não informado' }}
    </p>
    <p v-else-if="request.relationship === 'contributor'" class="mt-2 truncate text-xs leading-5 text-dj-muted"
      :title="'Você acompanha como contribuinte. Solicitante: ' + (request.requester_name ?? 'Não informado')">
      Contribuinte · Solicitante: {{ request.requester_name ?? 'Não informado' }}
    </p>
  </RecordCard>
</template>
