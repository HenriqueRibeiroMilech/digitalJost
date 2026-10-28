<script setup lang="ts">
defineProps<{ id: string; title: string; description?: string; eyebrow?: string; icon?: string }>()
</script>

<template>
  <div class="dj-page-header mb-7 flex flex-wrap items-end justify-between gap-5 rounded-dj-card border border-dj-border p-5 sm:p-7">
    <div class="min-w-0 flex-1 basis-80">
      <div class="flex items-start gap-4">
        <span v-if="icon" class="inline-flex size-12 shrink-0 items-center justify-center rounded-2xl border border-primary-100 bg-dj-surface text-xl text-dj-brand shadow-sm sm:size-14" aria-hidden="true">
          <i :class="icon" />
        </span>
        <div class="min-w-0">
          <p v-if="eyebrow" class="mb-2 text-xs font-semibold tracking-[0.16em] text-dj-brand uppercase">{{ eyebrow }}</p>
          <h1 :id="id" class="break-words text-3xl font-bold tracking-tight text-dj-ink sm:text-4xl">{{ title }}</h1>
        </div>
      </div>
      <p v-if="description" class="mt-3 max-w-2xl text-sm leading-6 text-dj-muted sm:text-base">{{ description }}</p>
    </div>
    <div v-if="$slots.actions" class="flex max-w-full flex-wrap items-center gap-3">
      <slot name="actions" />
    </div>
  </div>
</template>
