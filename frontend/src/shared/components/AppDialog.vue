<script setup lang="ts">
import Dialog from '@/volt/Dialog.vue'

const props = withDefaults(defineProps<{
  id: string
  visible: boolean
  title: string
  subtitle?: string
  icon?: string
  busy?: boolean
  descriptionId?: string
  tone?: 'brand' | 'success' | 'neutral' | 'danger'
}>(), { busy: false, tone: 'brand', icon: 'pi pi-calendar' })
const emit = defineEmits<{ 'update:visible': [visible: boolean]; closed: [] }>()

function updateVisibility(visible: boolean) {
  if (!props.busy) emit('update:visible', visible)
}
</script>

<template>
  <Dialog :id="id" :visible="visible" :header="title" modal :draggable="false"
    :closable="!busy" :close-on-escape="!busy" :dismissable-mask="false"
    :style="{ width: '48rem', maxWidth: 'calc(100vw - 2rem)' }"
    :aria-labelledby="id + '-title'" :aria-describedby="descriptionId"
    :class="'dj-tone-' + tone"
    pt:root:class="max-h-[calc(100dvh_-_2rem)] overflow-hidden rounded-(--radius-dj-card) border-dj-border bg-dj-surface shadow-2xl"
    pt:header:class="gap-4 border-b border-dj-border bg-dj-canvas px-6 py-5"
    pt:content:class="px-6 pt-6 pb-6"
    pt:footer:class="flex-wrap gap-3 border-t border-dj-border bg-dj-canvas px-6 py-4"
    pt:mask:class="p-modal:bg-dj-header/55 backdrop-blur-sm"
    @update:visible="updateVisibility" @after-hide="emit('closed')">
    <template #header>
      <div class="flex min-w-0 items-center gap-3.5">
        <span class="inline-flex size-12 shrink-0 items-center justify-center rounded-2xl bg-(--dj-tone-soft) text-(--dj-tone)" aria-hidden="true">
          <i :class="icon" class="text-xl" />
        </span>
        <div class="min-w-0">
          <h2 :id="id + '-title'" class="text-lg leading-6 font-bold tracking-tight text-dj-ink">{{ title }}</h2>
          <p v-if="subtitle" class="mt-1 text-xs leading-5 text-dj-muted">{{ subtitle }}</p>
        </div>
      </div>
    </template>
    <slot />
    <template v-if="$slots.footer" #footer>
      <slot name="footer" />
    </template>
  </Dialog>
</template>
