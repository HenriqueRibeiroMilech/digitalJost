<script setup lang="ts">
defineProps<{ id: string; title: string; description?: string }>()
</script>

<template>
  <div class="mb-8 flex flex-wrap items-start justify-between gap-4">
    <div>
      <h1 :id="id" class="text-3xl font-semibold">{{ title }}</h1>
      <p v-if="description" class="mt-2 text-dj-muted">{{ description }}</p>
    </div>
    <slot name="actions" />
  </div>
</template>
