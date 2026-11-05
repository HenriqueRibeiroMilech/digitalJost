<script setup lang="ts">
import { computed } from 'vue'
import Message from '@/volt/Message.vue'

const props = defineProps<{ id: string; label: string; error?: string }>()
const controlProps = computed(() => ({
  id: props.id,
  invalid: Boolean(props.error),
  'aria-invalid': Boolean(props.error),
  'aria-describedby': props.error ? props.id + '-error' : undefined,
}))
</script>

<template>
  <div>
    <label :for="id" class="dj-field-label mb-2 block text-sm font-medium">{{ label }}</label>
    <slot :controlProps="controlProps" />
    <Message v-if="error" :id="id + '-error'" severity="error" variant="simple"
      size="small" class="mt-2">{{ error }}</Message>
  </div>
</template>
