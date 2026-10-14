<script setup lang="ts">
import { ref } from 'vue'
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { ApiError } from '@/shared/api/client'
import { validationMessages } from '@/shared/api/validation'
import { usePagination } from '@/shared/composables/usePagination'
import PageHeader from '@/shared/components/PageHeader.vue'
import RequestState from '@/shared/components/RequestState.vue'
import ListPagination from '@/shared/components/ListPagination.vue'
import Button from '@/volt/Button.vue'
import Dialog from '@/volt/Dialog.vue'
import Message from '@/volt/Message.vue'
import Skeleton from '@/volt/Skeleton.vue'
import EventCard from '../components/EventCard.vue'
import EventForm from '../components/EventForm.vue'
import { eventsApi } from '../api'
import type { EventCreate } from '../types'

const { page, perPage, resetPage } = usePagination()
const showForm = ref(false)
const feedback = ref('')
const submitError = ref('')
const fieldErrors = ref({ name: '', description: '' })
const newEventAction = ref<HTMLElement | null>(null)
const queryClient = useQueryClient()
const { data, isPending: loading, isError, error: listError, refetch } = useQuery({
  queryKey: ['events', page],
  queryFn: () => eventsApi.list(page.value, perPage),
  retry: false,
})
const { mutateAsync, isPending: saving } = useMutation({
  mutationFn: eventsApi.create,
  retry: false,
})

function openForm() {
  feedback.value = ''
  submitError.value = ''
  fieldErrors.value = { name: '', description: '' }
  showForm.value = true
}

function updateDialogVisibility(visible: boolean) {
  if (saving.value) return
  showForm.value = visible
}

function closeForm() {
  updateDialogVisibility(false)
}

function restoreFocus() {
  newEventAction.value?.querySelector('button')?.focus()
}

async function createEvent(payload: EventCreate) {
  if (saving.value) return
  submitError.value = ''
  fieldErrors.value = { name: '', description: '' }
  try {
    await mutateAsync(payload)
  } catch (error) {
    if (error instanceof ApiError && error.status === 422) {
      fieldErrors.value = validationMessages(error.detail, ['name', 'description'] as const)
      if (fieldErrors.value.name || fieldErrors.value.description) return
    }
    submitError.value = error instanceof Error ? error.message : 'Não foi possível criar o evento.'
    return
  }
  // A gravação terminou. Uma falha posterior ao listar não transforma o POST em falha.
  feedback.value = 'Evento criado com sucesso.'
  resetPage()
  showForm.value = false
  await queryClient.invalidateQueries({ queryKey: ['events'] })
}
</script>

<template>
  <section aria-labelledby="events-title">
    <PageHeader id="events-title" title="Eventos" description="Organize os eventos do Digital JOST.">
      <template #actions>
        <div v-if="data?.capabilities.can_create" ref="newEventAction">
          <Button type="button" label="Novo evento" icon="pi pi-plus"
            :disabled="showForm" @click="openForm" />
        </div>
      </template>
    </PageHeader>

    <Message v-if="feedback" severity="success" role="status" aria-live="polite" class="mb-6">
      {{ feedback }}
    </Message>

    <RequestState :loading="loading" :failed="isError" :error="listError"
      :empty="data?.items.length === 0" loading-label="Carregando eventos…"
      empty-title="Nenhum evento cadastrado"
      empty-description="Os eventos aparecerão aqui quando forem criados."
      error-message="Não foi possível carregar os eventos."
      forbidden-message="Você não tem permissão para ver os eventos."
      not-found-message="Eventos não está disponível para seu acesso." @retry="refetch()">
      <template #loading>
        <div class="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
          <div v-for="index in 6" :key="index" class="rounded-xl border border-dj-border bg-white p-6">
            <Skeleton width="70%" height="1.5rem" />
            <Skeleton width="100%" height="4.5rem" class="mt-4" />
          </div>
        </div>
      </template>
      <div class="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
        <EventCard v-for="event in data?.items ?? []" :key="event.id" :event="event" />
      </div>
    </RequestState>

    <ListPagination v-if="!loading && !isError && data" v-model:page="page"
      :per-page="perPage" :total="data.total" label="Páginas de eventos" />

    <Dialog :visible="showForm" header="Novo evento" modal :draggable="false"
      :closable="!saving" :close-on-escape="!saving" :dismissable-mask="false"
      :style="{ width: '36rem', maxWidth: 'calc(100vw - 2rem)' }"
      aria-describedby="event-form-help"
      @update:visible="updateDialogVisibility" @after-hide="restoreFocus">
      <EventForm v-if="showForm" :busy="saving" :server-error="submitError"
        :field-errors="fieldErrors"
        @submit="createEvent" @cancel="closeForm" />
    </Dialog>
  </section>
</template>
