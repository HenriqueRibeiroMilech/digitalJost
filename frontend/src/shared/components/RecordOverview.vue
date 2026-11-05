<script setup lang="ts">
withDefaults(defineProps<{
  title: string
  titleId: string
  tone?: 'brand' | 'success' | 'neutral' | 'danger'
}>(), { tone: 'brand' })
</script>

<template>
  <section class="dj-record-overview" :class="'dj-tone-' + tone" :aria-labelledby="titleId">
    <div class="dj-record-overview-heading">
      <h3 :id="titleId" tabindex="-1" class="dj-detail-title">{{ title }}</h3>
      <div v-if="$slots.badges" class="flex max-w-full flex-wrap items-center gap-2">
        <slot name="badges" />
      </div>
    </div>
    <dl v-if="$slots.default" class="dj-record-overview-facts">
      <slot />
    </dl>
  </section>
</template>
