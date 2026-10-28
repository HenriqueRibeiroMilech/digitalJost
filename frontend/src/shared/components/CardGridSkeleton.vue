<script setup lang="ts">
import Skeleton from '@/volt/Skeleton.vue'
import CardGrid from './CardGrid.vue'

withDefaults(defineProps<{ count?: number; compact?: boolean }>(), {
  count: 12,
  compact: false,
})
</script>

<template>
  <CardGrid aria-hidden="true">
    <div v-for="index in count" :key="index"
      class="rounded-dj-card border border-t-4 border-dj-border bg-dj-surface shadow-dj-card"
      :class="compact ? 'p-4' : 'p-5'">
      <template v-if="compact">
        <div class="flex items-center justify-between gap-3">
          <Skeleton width="7rem" height="2.5rem" />
          <Skeleton width="4rem" height="1.5rem" border-radius="1rem" />
        </div>
        <Skeleton width="85%" height="2.5rem" class="mt-3" />
        <Skeleton width="100%" height="2.5rem" class="mt-1.5" />
        <Skeleton width="100%" height="4.75rem" class="mt-3" border-radius="0.75rem" />
        <Skeleton width="100%" height="1.75rem" class="mt-3" />
      </template>
      <template v-else>
        <div class="mb-4 flex items-start justify-between gap-3">
          <Skeleton width="3.5rem" height="3.5rem" border-radius="1rem" />
          <Skeleton width="4rem" height="1.5rem" border-radius="1rem" />
        </div>
        <Skeleton width="85%" height="3rem" />
        <Skeleton width="100%" height="3rem" class="mt-2" />
        <Skeleton width="100%" height="5rem" class="mt-4" border-radius="0.75rem" />
        <Skeleton width="100%" height="2rem" class="mt-4" />
      </template>
    </div>
  </CardGrid>
</template>
