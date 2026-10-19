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
  tone?: 'brand' | 'success' | 'neutral'
}>(), { tone: 'brand', compact: false })
defineEmits<{ open: [] }>()
</script>

<template>
  <article :aria-labelledby="titleId" class="group relative h-full min-w-0 rounded-dj-card motion-safe:transition-transform
    motion-safe:duration-200 motion-safe:hover:-translate-y-1" :class="'dj-tone-' + tone">
    <Card pt:root:class="dj-record-card-surface h-full overflow-hidden rounded-(--radius-dj-card) border border-t-4 border-dj-border bg-dj-surface shadow-(--shadow-dj-card) transition-shadow duration-200
      group-hover:border-(--dj-tone-border) group-hover:shadow-(--shadow-dj-card-hover)"
      :pt:body:class="'flex h-full flex-1 flex-col gap-0 ' + (compact ? 'p-4' : 'p-5')"
      pt:content:class="flex flex-1 flex-col">
      <template #content>
        <div v-if="icon || $slots.marker || $slots.badge" class="flex justify-between gap-3"
          :class="compact ? 'mb-3 items-center' : 'mb-4 items-start'">
          <slot name="marker">
            <span v-if="icon" class="inline-flex shrink-0 items-center justify-center bg-(--dj-tone-soft) text-(--dj-tone)"
              :class="compact ? 'size-8 rounded-lg' : 'size-11 rounded-xl'" aria-hidden="true">
              <i :class="[icon, compact ? 'text-base' : 'text-xl']" />
            </span>
          </slot>
          <slot name="badge" />
        </div>
        <h2 :id="titleId" class="line-clamp-2 break-words font-semibold tracking-tight text-dj-ink"
          :class="compact ? 'text-base leading-5' : 'min-h-12 text-lg leading-6'">
          {{ title }}
        </h2>
        <p v-if="description" class="line-clamp-2 whitespace-pre-wrap break-words text-sm text-dj-muted"
          :class="compact ? 'mt-1.5 leading-5' : 'mt-2 min-h-12 leading-6'">
          {{ description }}
        </p>
        <div v-if="$slots.default" :class="compact ? 'mt-3' : 'mt-4'">
          <slot />
        </div>
        <div class="mt-auto" :class="compact ? 'pt-3' : 'pt-4'">
          <div class="flex items-center justify-between gap-3 border-t border-dj-border text-sm font-semibold text-(--dj-tone)"
            :class="compact ? 'pt-2' : 'pt-3'" aria-hidden="true">
            <span>{{ actionLabel }}</span>
            <span class="inline-flex items-center justify-center rounded-full bg-(--dj-tone-soft) transition-colors
              group-hover:bg-(--dj-tone) group-hover:text-white" :class="compact ? 'size-7' : 'size-8'">
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
