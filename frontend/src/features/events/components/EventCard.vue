<script setup lang="ts">
import Card from '@/volt/Card.vue'
import type { EventItem } from '../types'
defineProps<{ event: EventItem }>()
</script>

<template>
  <article :aria-labelledby="'event-title-' + event.id">
    <Card pt:root:class="h-full border border-dj-border shadow-none" pt:body:class="p-6">
      <template #title>
        <h2 :id="'event-title-' + event.id" class="break-words text-lg font-semibold text-dj-ink">
          {{ event.name }}
        </h2>
      </template>
      <template #content>
        <p class="whitespace-pre-wrap break-words text-sm leading-6 text-dj-muted">
          {{ event.description }}
        </p>
      </template>
    </Card>
  </article>
</template>