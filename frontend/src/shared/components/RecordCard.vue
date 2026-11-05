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
  compact?: boolean
  tone?: 'brand' | 'success' | 'neutral' | 'warning' | 'danger' | 'info' | 'indigo' | 'violet'
}>(), { tone: 'brand', compact: false })
defineEmits<{ open: [] }>()
</script>

<template>
  <article :aria-labelledby="titleId" class="dj-record-card group relative h-full min-w-0 rounded-dj-card motion-safe:transition-transform
    motion-safe:duration-200 motion-safe:hover:-translate-y-1" :class="['dj-tone-' + tone, { 'dj-record-card-compact': compact }]">
    <Card pt:root:class="dj-record-card-surface h-full overflow-hidden rounded-(--radius-dj-card) border border-t-4 border-dj-border bg-dj-surface shadow-(--shadow-dj-card) transition-shadow duration-200
      group-hover:border-(--dj-tone-border) group-hover:shadow-(--shadow-dj-card-hover)"
      pt:body:class="flex h-full flex-1 flex-col gap-0 p-(--dj-card-padding)"
      pt:content:class="flex flex-1 flex-col">
      <template #content>
        <div v-if="icon || $slots.marker || $slots.badge" class="mb-(--dj-card-gap) flex flex-wrap justify-between gap-x-3 gap-y-2"
          :class="compact ? 'items-center' : 'items-start'">
          <slot name="marker">
            <span v-if="icon" class="inline-flex size-(--dj-card-marker-size) shrink-0 items-center justify-center rounded-xl bg-(--dj-tone-soft) text-(--dj-tone)"
              aria-hidden="true">
              <i :class="[icon, compact ? 'text-base' : 'text-xl']" />
            </span>
          </slot>
          <slot name="badge" />
        </div>
        <h2 :id="titleId" class="min-h-(--dj-card-text-min-height) line-clamp-2 break-words font-semibold leading-(--dj-card-line-height) tracking-tight text-dj-ink transition-colors group-hover:text-(--dj-tone) group-focus-within:text-(--dj-tone)"
          :class="compact ? 'text-base' : 'text-lg'">
          {{ title }}
        </h2>
        <p v-if="description" class="min-h-(--dj-card-text-min-height) line-clamp-2 whitespace-pre-wrap break-words text-sm leading-(--dj-card-line-height) text-dj-muted"
          :class="compact ? 'mt-1.5' : 'mt-2'">
          {{ description }}
        </p>
        <div v-if="$slots.default" class="mt-(--dj-card-gap)">
          <slot />
        </div>
        <div class="mt-auto pt-(--dj-card-gap)">
          <div class="flex items-center justify-between gap-3 border-t border-dj-border text-sm font-semibold text-(--dj-tone)"
            :class="compact ? 'pt-2' : 'pt-3'" aria-hidden="true">
            <span class="min-w-0 break-words">{{ actionLabel }}</span>
            <span class="inline-flex shrink-0 items-center justify-center rounded-full bg-(--dj-tone-soft) transition-colors
              group-hover:bg-(--dj-tone) group-hover:text-white group-focus-within:bg-(--dj-tone) group-focus-within:text-white size-(--dj-card-action-size)">
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
