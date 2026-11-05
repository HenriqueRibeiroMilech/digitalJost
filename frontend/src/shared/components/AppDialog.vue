<script setup lang="ts">
import { nextTick } from 'vue'
import Dialog from '@/volt/Dialog.vue'

const props = withDefaults(defineProps<{
  id: string
  visible: boolean
  title: string
  subtitle?: string
  icon?: string
  busy?: boolean
  descriptionId?: string
  initialFocusId?: string
  size?: 'standard' | 'small'
  tone?: 'brand' | 'success' | 'neutral' | 'danger'
}>(), { busy: false, tone: 'brand', icon: 'pi pi-calendar', size: 'standard' })
const emit = defineEmits<{ 'update:visible': [visible: boolean]; closed: [] }>()

function updateVisibility(visible: boolean) {
  if (!props.busy) emit('update:visible', visible)
}

async function focusInitial() {
  const target = props.initialFocusId
  if (!target) return
  await nextTick()
  if (props.visible) document.getElementById(target)?.focus()
}
</script>

<template>
  <Dialog :id="id" :visible="visible" :header="title" modal :draggable="false"
    :closable="!busy" :close-on-escape="!busy" :dismissable-mask="false"
    :style="{ width: size === 'small' ? '32rem' : '64rem', maxWidth: 'calc(100vw - 2rem)' }"
    :aria-labelledby="id + '-title'" :aria-describedby="descriptionId"
    :class="'dj-tone-' + tone"
    pt:root:class="dj-dialog max-h-[calc(100dvh_-_2rem)] overflow-hidden rounded-(--radius-dj-card) border-dj-border bg-dj-surface shadow-xl"
    pt:header:class="gap-3 border-b border-dj-border bg-dj-canvas px-4 py-3 sm:px-5"
    pt:content:class="px-4 py-4 sm:px-5"
    pt:footer:class="flex-wrap gap-2 border-t border-dj-border bg-dj-canvas px-4 py-3 sm:px-5"
    pt:mask:class="p-modal:bg-dj-header/55 backdrop-blur-sm"
    :pt:transition:onAfterEnter="focusInitial"
    @update:visible="updateVisibility" @after-hide="emit('closed')">
    <template #header>
      <div class="flex min-w-0 items-center gap-3">
        <span class="inline-flex size-9 shrink-0 items-center justify-center rounded-xl bg-(--dj-tone-soft) text-(--dj-tone)" aria-hidden="true">
          <i :class="icon" class="text-base" />
        </span>
        <div class="min-w-0">
          <h2 :id="id + '-title'" class="break-words text-base leading-5 font-bold tracking-tight text-dj-ink">{{ title }}</h2>
          <p v-if="subtitle" class="mt-1 text-xs leading-4 text-dj-muted">{{ subtitle }}</p>
        </div>
      </div>
    </template>
    <slot />
    <template v-if="$slots.footer" #footer>
      <slot name="footer" />
    </template>
  </Dialog>
</template>
