<script setup lang="ts">
import { ref } from 'vue'
import { useMutation } from '@tanstack/vue-query'
import AppDialog from '@/shared/components/AppDialog.vue'
import Button from '@/volt/Button.vue'
import Message from '@/volt/Message.vue'
import SecondaryButton from '@/volt/SecondaryButton.vue'
import { eventsApi } from '../api'
import type { EventType } from '../types'

const props = defineProps<{ eventType: EventType; allowed: boolean }>()
const emit = defineEmits<{ closed: [deleted: boolean] }>()
const visible = ref(true)
const deleted = ref(false)
const submitError = ref('')
const { mutateAsync: remove, isPending: deleting } = useMutation({
  mutationFn: () => eventsApi.deleteType(props.eventType.id),
  retry: false,
})

async function confirm() {
  if (!visible.value || deleted.value || deleting.value || !props.allowed) return
  submitError.value = ''
  try {
    await remove()
  } catch (error) {
    submitError.value = error instanceof Error ? error.message : 'Não foi possível excluir o tipo de evento.'
    return
  }
  deleted.value = true
  visible.value = false
}
</script>

<template>
  <AppDialog id="event-type-delete-dialog" v-model:visible="visible" title="Excluir tipo de evento" size="small"
    subtitle="Confira o tipo antes de confirmar a exclusão." icon="pi pi-trash" tone="danger" :busy="deleting"
    description-id="event-type-delete-help" initial-focus-id="event-type-delete-cancel" @closed="emit('closed', deleted)">
    <p class="break-words rounded-2xl border border-dj-border bg-dj-canvas p-5 font-semibold text-dj-ink">{{ eventType.name }}</p>
    <p id="event-type-delete-help" class="mt-4 text-sm leading-6 text-dj-muted">
      O tipo será removido das opções de todos os eventos. A exclusão só é permitida se nenhum evento estiver usando este tipo.
    </p>
    <Message severity="warn" class="mt-4">Esta ação não pode ser desfeita.</Message>
    <Message v-if="submitError" severity="error" class="mt-4">{{ submitError }}</Message>
    <template #footer>
      <SecondaryButton id="event-type-delete-cancel" type="button" label="Cancelar" outlined :disabled="deleting"
        pt:root:class="rounded-xl" @click="visible = false" />
      <Button type="button" :label="deleting ? 'Excluindo…' : 'Excluir tipo'" icon="pi pi-trash"
        :loading="deleting" :disabled="deleting || !allowed" class="dj-danger-action" pt:root:class="rounded-xl" @click="confirm" />
    </template>
  </AppDialog>
</template>
