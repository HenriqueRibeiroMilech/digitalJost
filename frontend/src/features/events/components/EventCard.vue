<script setup lang="ts">
import Card from '@/volt/Card.vue'
import { formatEventDateTime } from '../dates'
import type { EventItem } from '../types'
defineProps<{ event: EventItem }>()
defineEmits<{ open: [id: number] }>()
</script>

<template>
  <article :aria-labelledby="'event-title-' + event.id" class="relative h-full rounded-xl transition-shadow hover:shadow-md">
    <Card pt:root:class="h-full border border-dj-border shadow-none" pt:body:class="p-6">
      <template #title>
        <h2 :id="'event-title-' + event.id" class="break-words text-lg font-semibold text-dj-ink">
          {{ event.name }}
        </h2>
      </template>
      <template #content>
        <p class="line-clamp-3 whitespace-pre-wrap break-words text-sm leading-6 text-dj-muted">
          {{ event.description }}
        </p>
        <dl class="mt-4 space-y-2 text-sm">
          <div><dt class="font-medium">Início</dt><dd class="text-dj-muted">{{ formatEventDateTime(event.starts_at) }}</dd></div>
          <div><dt class="font-medium">Fim</dt><dd class="text-dj-muted">{{ formatEventDateTime(event.ends_at) }}</dd></div>
        </dl>
        <span class="mt-4 inline-flex items-center gap-2 text-sm font-medium text-primary">
          Ver detalhes <i class="pi pi-arrow-right" aria-hidden="true" />
        </span>
      </template>
    </Card>
    <button :id="'event-open-' + event.id" type="button" class="absolute inset-0 w-full rounded-xl cursor-pointer
      focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-primary"
      :aria-label="'Ver detalhes de ' + event.name" aria-haspopup="dialog" @click="$emit('open', event.id)">
      <span class="sr-only">Ver detalhes de {{ event.name }}</span>
    </button>
  </article>
</template>
