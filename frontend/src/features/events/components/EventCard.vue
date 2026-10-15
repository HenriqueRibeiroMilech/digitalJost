<script setup lang="ts">
import { computed } from 'vue'
import RecordCard from '@/shared/components/RecordCard.vue'
import Tag from '@/volt/Tag.vue'
import { eventDate, formatEventDateTime } from '../dates'
import type { EventItem } from '../types'
const props = defineProps<{ event: EventItem }>()
defineEmits<{ open: [id: number] }>()
const calendarDate = computed(() => {
  const date = eventDate(props.event.starts_at)
  return date ? {
    day: new Intl.DateTimeFormat('pt-BR', { day: '2-digit' }).format(date),
    month: new Intl.DateTimeFormat('pt-BR', { month: 'short' }).format(date).replace('.', ''),
  } : null
})
</script>

<template>
  <RecordCard :title-id="'event-title-' + event.id" :title="event.name" :description="event.description"
    :action-id="'event-open-' + event.id" action-label="Ver detalhes"
    opens-dialog @open="$emit('open', event.id)">
    <template #marker>
      <div class="flex size-12 shrink-0 flex-col items-center justify-center rounded-xl bg-primary-50 text-dj-brand" aria-hidden="true">
        <template v-if="calendarDate">
          <span class="text-[0.625rem] leading-4 font-bold tracking-widest uppercase">{{ calendarDate.month }}</span>
          <span class="text-xl leading-6 font-bold tabular-nums">{{ calendarDate.day }}</span>
        </template>
        <i v-else class="pi pi-calendar text-xl" />
      </div>
    </template>
    <template #badge>
      <Tag :value="'Evento #' + event.id" severity="secondary" rounded />
    </template>
    <dl class="space-y-3 rounded-xl bg-dj-canvas p-3.5 text-xs">
      <div class="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
        <dt class="inline-flex items-center gap-2 text-dj-muted">
          <i class="pi pi-calendar text-xs" aria-hidden="true" /> Início
        </dt>
        <dd class="font-medium text-dj-ink tabular-nums">
          <time v-if="event.starts_at" :datetime="event.starts_at">{{ formatEventDateTime(event.starts_at) }}</time>
          <span v-else>Não informado</span>
        </dd>
      </div>
      <div class="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
        <dt class="inline-flex items-center gap-2 text-dj-muted">
          <i class="pi pi-clock text-xs" aria-hidden="true" /> Fim
        </dt>
        <dd class="font-medium text-dj-ink tabular-nums">
          <time v-if="event.ends_at" :datetime="event.ends_at">{{ formatEventDateTime(event.ends_at) }}</time>
          <span v-else>Não informado</span>
        </dd>
      </div>
    </dl>
  </RecordCard>
</template>
