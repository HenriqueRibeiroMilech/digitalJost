<script setup lang="ts">
import { computed } from 'vue'
import Tag from '@/volt/Tag.vue'
import { eventStatuses } from '../statuses'
import type { EventStatus } from '../types'

const props = defineProps<{ status: EventStatus }>()
const presentation = computed(() => eventStatuses[props.status])
</script>

<template>
  <Tag :value="presentation.label" :icon="presentation.icon" :severity="presentation.severity" rounded
    class="dj-tone-badge" :class="'dj-tone-' + presentation.tone" />
</template>
