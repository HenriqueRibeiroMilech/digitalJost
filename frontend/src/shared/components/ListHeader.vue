<script setup lang="ts">
withDefaults(defineProps<{
  id: string
  title: string
  total?: number
  totalLabel?: string
  description?: string
}>(), { totalLabel: 'Total de registros' })
</script>

<template>
  <div class="mb-4 flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
    <h2 :id="id" class="flex min-w-0 max-w-full flex-wrap items-center gap-2 text-sm font-semibold text-dj-ink">
      <span class="min-w-0 break-words">{{ title }}</span>
      <span v-if="total !== undefined" class="rounded-full bg-primary-100 px-2.5 py-0.5 text-xs text-dj-brand tabular-nums"
        :aria-label="totalLabel + ': ' + total">{{ total }}</span>
    </h2>
    <p v-if="description" class="max-w-xl text-xs leading-5 text-dj-muted">{{ description }}</p>
  </div>
</template>
