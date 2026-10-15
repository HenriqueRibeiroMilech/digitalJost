<script setup lang="ts">
defineProps<{ id: string; title: string; description?: string; eyebrow?: string }>()
</script>

<template>
  <div class="mb-7 flex flex-wrap items-end justify-between gap-5 border-b border-dj-border pb-7">
    <div class="min-w-0">
      <p v-if="eyebrow" class="mb-2 text-xs font-semibold tracking-[0.16em] text-dj-brand uppercase">{{ eyebrow }}</p>
      <h1 :id="id" class="break-words text-3xl font-bold tracking-tight text-dj-ink sm:text-4xl">{{ title }}</h1>
      <p v-if="description" class="mt-3 max-w-2xl text-sm leading-6 text-dj-muted sm:text-base">{{ description }}</p>
    </div>
    <div v-if="$slots.actions" class="flex shrink-0 flex-wrap items-center gap-3">
      <slot name="actions" />
    </div>
  </div>
</template>
