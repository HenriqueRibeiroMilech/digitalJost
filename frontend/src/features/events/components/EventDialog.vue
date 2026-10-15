<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import { useMutation, useQuery } from '@tanstack/vue-query'
import { ApiError } from '@/shared/api/client'
import { validationMessages } from '@/shared/api/validation'
import RequestState from '@/shared/components/RequestState.vue'
import Button from '@/volt/Button.vue'
import Dialog from '@/volt/Dialog.vue'
import Message from '@/volt/Message.vue'
import { eventsApi } from '../api'
import { formatEventDateTime } from '../dates'
import type { EventChange, EventCreate } from '../types'
import EventForm from './EventForm.vue'

const props = defineProps<{ eventId: number | null }>()
const emit = defineEmits<{ closed: []; changed: [action: EventChange] }>()
const visible = ref(true)
const view = ref<'create' | 'details' | 'edit' | 'delete'>(props.eventId === null ? 'create' : 'details')
const submitError = ref('')
const emptyErrors = () => ({ name: '', description: '', starts_at: '', ends_at: '' })
const fieldErrors = ref(emptyErrors())
const contentElement = ref<HTMLElement | null>(null)
const { data: event, isPending: loading, isFetching, isError, error, refetch } = useQuery({
  queryKey: ['events', 'detail', props.eventId],
  queryFn: () => {
    if (props.eventId === null) throw new Error('Selecione um evento.')
    return eventsApi.get(props.eventId)
  },
  enabled: props.eventId !== null,
  retry: false,
  // Não substituir dados do formulário enquanto o usuário está editando.
  refetchOnWindowFocus: false,
  refetchOnReconnect: false,
})
const { mutateAsync: save, isPending: saving } = useMutation({
  mutationFn: (payload: EventCreate) => props.eventId === null
    ? eventsApi.create(payload) : eventsApi.update(props.eventId, payload),
  retry: false,
})
const { mutateAsync: remove, isPending: deleting } = useMutation({
  mutationFn: () => {
    if (props.eventId === null) throw new Error('Selecione um evento.')
    return eventsApi.delete(props.eventId)
  },
  retry: false,
})
const busy = computed(() => saving.value || deleting.value)
const title = computed(() => view.value === 'create' ? 'Novo evento'
  : view.value === 'edit' ? 'Editar evento'
  : view.value === 'delete' ? 'Excluir evento' : 'Detalhes do evento')

async function changeView(next: 'details' | 'edit' | 'delete') {
  if (busy.value) return
  submitError.value = ''
  fieldErrors.value = emptyErrors()
  view.value = next
  await nextTick()
  const selector = next === 'edit' ? '#event-name'
    : next === 'delete' ? '#event-delete-cancel' : '#event-details-title'
  contentElement.value?.querySelector<HTMLElement>(selector)?.focus()
}

function updateVisibility(next: boolean) {
  if (!busy.value) visible.value = next
}

function cancelForm() {
  if (view.value === 'create') updateVisibility(false)
  else changeView('details')
}

async function saveEvent(payload: EventCreate) {
  if (busy.value) return
  submitError.value = ''
  fieldErrors.value = emptyErrors()
  try {
    await save(payload)
  } catch (error) {
    if (error instanceof ApiError && error.status === 422) {
      fieldErrors.value = validationMessages(error.detail, ['name', 'description', 'starts_at', 'ends_at'] as const)
      if (Object.values(fieldErrors.value).some(Boolean)) {
        await nextTick()
        contentElement.value?.querySelector<HTMLElement>('input[aria-invalid="true"], textarea[aria-invalid="true"]')?.focus()
        return
      }
    }
    submitError.value = error instanceof Error ? error.message : 'Não foi possível salvar o evento.'
    return
  }
  // A operação terminou; atualizar a lista não faz parte da gravação.
  visible.value = false
  emit('changed', props.eventId === null ? 'created' : 'updated')
}

async function deleteEvent() {
  if (busy.value) return
  submitError.value = ''
  try {
    await remove()
  } catch (error) {
    submitError.value = error instanceof Error ? error.message : 'Não foi possível excluir o evento.'
    return
  }
  visible.value = false
  emit('changed', 'deleted')
}
</script>

<template>
  <Dialog :visible="visible" :header="title" modal :draggable="false"
    :closable="!busy" :close-on-escape="!busy" :dismissable-mask="false"
    :style="{ width: '42rem', maxWidth: 'calc(100vw - 2rem)' }"
    :aria-describedby="view === 'create' || view === 'edit' ? 'event-form-help' : undefined"
    @update:visible="updateVisibility" @after-hide="emit('closed')">
    <div ref="contentElement">
      <EventForm v-if="view === 'create'" :busy="busy" :server-error="submitError"
        :field-errors="fieldErrors" @submit="saveEvent" @cancel="cancelForm" />

      <RequestState v-else :loading="loading || (isFetching && view === 'details')"
        :failed="isError" :error="error" :empty="false"
        loading-label="Carregando evento…" error-message="Não foi possível carregar o evento."
        forbidden-message="Você não tem permissão para ver este evento."
        not-found-message="Este evento não existe ou já foi excluído." @retry="refetch()">
        <template v-if="event">
          <EventForm v-if="view === 'edit'" :event="event" :busy="busy"
            :server-error="submitError" :field-errors="fieldErrors"
            @submit="saveEvent" @cancel="cancelForm" />

          <div v-else-if="view === 'delete'" :aria-busy="busy">
            <p class="break-words">Deseja excluir o evento <strong>{{ event.name }}</strong>?</p>
            <Message severity="warn" class="mt-4">Esta ação é permanente.</Message>
            <Message v-if="submitError" severity="error" class="mt-4">{{ submitError }}</Message>
            <div class="mt-6 flex flex-wrap justify-end gap-3">
              <Button id="event-delete-cancel" type="button" label="Cancelar" outlined :disabled="busy"
                @click="changeView('details')" />
              <Button type="button" :label="deleting ? 'Excluindo…' : 'Excluir evento'"
                icon="pi pi-trash" :loading="deleting" :disabled="busy || !event.capabilities.can_delete"
                @click="deleteEvent" />
            </div>
          </div>

          <div v-else>
            <div class="mb-6 flex flex-wrap justify-end gap-3">
              <Button v-if="event.capabilities.can_update" type="button" label="Editar"
                icon="pi pi-pencil" outlined @click="changeView('edit')" />
              <Button v-if="event.capabilities.can_delete" type="button" label="Excluir"
                icon="pi pi-trash" outlined @click="changeView('delete')" />
            </div>
            <h2 id="event-details-title" tabindex="-1" class="break-words text-xl font-semibold text-dj-ink">{{ event.name }}</h2>
            <dl class="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div><dt class="text-sm font-medium">Data e hora de início</dt>
                <dd class="mt-1 text-dj-muted">{{ formatEventDateTime(event.starts_at) }}</dd></div>
              <div><dt class="text-sm font-medium">Data e hora de fim</dt>
                <dd class="mt-1 text-dj-muted">{{ formatEventDateTime(event.ends_at) }}</dd></div>
              <div class="sm:col-span-2"><dt class="text-sm font-medium">Descrição</dt>
                <dd class="mt-2 whitespace-pre-wrap break-words leading-6 text-dj-muted">{{ event.description }}</dd></div>
            </dl>
          </div>
        </template>
      </RequestState>
    </div>
  </Dialog>
</template>
