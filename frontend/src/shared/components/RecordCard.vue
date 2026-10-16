<script setup lang="ts">
import Card from '@/volt/Card.vue'

withDefaults(defineProps<{
  titleId: string
  title: string
  description?: string
  icon?: string
  actionLabel: string
  actionId?: string
  opensDialog?: boolean
  tone?: 'brand' | 'success' | 'neutral'
}>(), { tone: 'brand' })
defineEmits<{ open: [] }>()
</script>

<template>
  <article :aria-labelledby="titleId" class="group relative h-full min-w-0 rounded-dj-card motion-safe:transition-transform
    motion-safe:duration-200 motion-safe:hover:-translate-y-1" :class="'dj-tone-' + tone">
    <Card pt:root:class="dj-record-card-surface h-full overflow-hidden rounded-(--radius-dj-card) border border-t-4 border-dj-border bg-dj-surface shadow-(--shadow-dj-card) transition-shadow duration-200
      group-hover:border-(--dj-tone-border) group-hover:shadow-(--shadow-dj-card-hover)"
      pt:body:class="flex h-full flex-1 flex-col gap-0 p-5"
      pt:content:class="flex flex-1 flex-col">
      <template #content>
        <div v-if="icon || $slots.marker || $slots.badge" class="mb-4 flex items-start justify-between gap-3">
          <slot name="marker">
            <span v-if="icon" class="inline-flex size-11 shrink-0 items-center justify-center rounded-xl bg-(--dj-tone-soft) text-(--dj-tone)" aria-hidden="true">
              <i :class="icon" class="text-xl" />
            </span>
          </slot>
          <slot name="badge" />
        </div>
        <h2 :id="titleId" class="line-clamp-2 min-h-12 break-words text-lg leading-6 font-semibold tracking-tight text-dj-ink">
          {{ title }}
        </h2>
        <p v-if="description" class="mt-2 line-clamp-2 min-h-12 whitespace-pre-wrap break-words text-sm leading-6 text-dj-muted">
          {{ description }}
        </p>
        <div v-if="$slots.default" class="mt-4">
          <slot />
        </div>
        <div class="mt-auto pt-4">
          <div class="flex items-center justify-between gap-3 border-t border-dj-border pt-3 text-sm font-semibold text-(--dj-tone)" aria-hidden="true">
            <span>{{ actionLabel }}</span>
            <span class="inline-flex size-8 items-center justify-center rounded-full bg-(--dj-tone-soft) transition-colors
              group-hover:bg-(--dj-tone) group-hover:text-white">
              <i class="pi pi-arrow-up-right text-xs" />
            </span>
          </div>
        </div>
      </template>
    </Card>
    <button :id="actionId" type="button" class="absolute inset-0 w-full cursor-pointer rounded-dj-card"
      :aria-label="actionLabel + ': ' + title" :aria-haspopup="opensDialog ? 'dialog' : undefined" @click="$emit('open')">
      <span class="sr-only">{{ actionLabel }}: {{ title }}</span>
    </button>
  </article>
</template>
