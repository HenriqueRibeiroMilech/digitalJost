<script setup lang="ts">
defineProps<{ id: string; title: string; description?: string; eyebrow?: string; icon?: string }>()
</script>

<template>
  <div class="dj-page-header mb-6 flex flex-wrap items-center justify-between gap-4 rounded-dj-card border border-dj-border p-4 sm:p-6">
    <div class="min-w-0 flex-1 basis-80">
      <div class="flex items-start gap-3">
        <span v-if="icon" class="inline-flex size-10 shrink-0 items-center justify-center rounded-xl border border-primary-100 bg-dj-surface text-lg text-dj-brand shadow-sm sm:size-12" aria-hidden="true">
          <i :class="icon" />
        </span>
        <div class="min-w-0">
          <p v-if="eyebrow" class="mb-1.5 text-xs font-semibold tracking-[0.12em] text-dj-brand uppercase">{{ eyebrow }}</p>
          <h1 :id="id" class="break-words text-2xl font-bold tracking-tight text-dj-ink sm:text-3xl">{{ title }}</h1>
          <p v-if="description" class="mt-2 max-w-2xl text-sm leading-6 text-dj-muted">{{ description }}</p>
        </div>
      </div>
    </div>
    <div v-if="$slots.actions" class="flex max-w-full flex-wrap items-center gap-3">
      <slot name="actions" />
    </div>
  </div>
</template>
