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
      class="dj-record-card flex h-full min-w-0 flex-col rounded-dj-card border border-t-4 border-dj-border bg-dj-surface p-(--dj-card-padding) shadow-dj-card"
      :class="{ 'dj-record-card-compact': compact }">
      <div class="mb-(--dj-card-gap) flex flex-wrap items-start justify-between gap-x-3 gap-y-2">
        <Skeleton :width="compact ? '6rem' : 'var(--dj-card-marker-size)'"
          height="var(--dj-card-marker-size)" border-radius="0.75rem" />
        <Skeleton width="6rem" :height="compact ? '1.5rem' : '1.75rem'" border-radius="1rem" />
      </div>
      <Skeleton width="85%" height="calc(var(--dj-card-line-height) * 2)" />
      <Skeleton width="100%" height="calc(var(--dj-card-line-height) * 2)" :class="compact ? 'mt-1.5' : 'mt-2'" />
      <Skeleton width="100%" :height="compact ? '3.25rem' : '5rem'" class="mt-(--dj-card-gap)" border-radius="0.75rem" />
      <div class="mt-auto pt-(--dj-card-gap)">
        <div class="border-t border-dj-border" :class="compact ? 'pt-2' : 'pt-3'">
          <Skeleton width="100%" height="var(--dj-card-action-size)" />
        </div>
      </div>
    </div>
  </CardGrid>
</template>
