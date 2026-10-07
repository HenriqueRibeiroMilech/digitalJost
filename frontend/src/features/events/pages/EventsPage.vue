<script setup lang="ts">
import { computed, ref } from 'vue'
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { ApiError } from '@/shared/api/client'
import Button from '@/volt/Button.vue'
import Dialog from '@/volt/Dialog.vue'
import Message from '@/volt/Message.vue'
import Paginator from '@/volt/Paginator.vue'
import Skeleton from '@/volt/Skeleton.vue'
import EventCard from '../components/EventCard.vue'
import EventForm from '../components/EventForm.vue'
import { eventsApi } from '../api'
import type { EventCreate } from '../types'

const page = ref(1)
const perPage = 12
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
const listStatus = computed(() => listError.value instanceof ApiError ? listError.value.status : 0)

function fieldMessage(detail: unknown, field: 'name' | 'description'): string {
  if (typeof detail !== 'object' || detail === null) return ''
  const json = (detail as Record<string, unknown>).json
  if (typeof json !== 'object' || json === null) return ''
  const messages = (json as Record<string, unknown>)[field]
  return Array.isArray(messages) && typeof messages[0] === 'string' ? messages[0] : ''
}

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

function changePage(event: { page: number }) {
  // O Paginator começa em zero; a API começa em um.
  page.value = event.page + 1
}

async function createEvent(payload: EventCreate) {
  if (saving.value) return
  submitError.value = ''
  fieldErrors.value = { name: '', description: '' }
  try {
    await mutateAsync(payload)
  } catch (error) {
    if (error instanceof ApiError && error.status === 422) {
      fieldErrors.value = {
        name: fieldMessage(error.detail, 'name'),
        description: fieldMessage(error.detail, 'description'),
      }
      if (fieldErrors.value.name || fieldErrors.value.description) return
    }
    submitError.value = error instanceof Error ? error.message : 'Não foi possível criar o evento.'
    return
  }
  // A gravação terminou. Uma falha posterior ao listar não transforma o POST em falha.
  feedback.value = 'Evento criado com sucesso.'
  page.value = 1
  showForm.value = false
  await queryClient.invalidateQueries({ queryKey: ['events'] })
}
</script>

<template>
  <section aria-labelledby="events-title">
    <div class="mb-8 flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 id="events-title" class="text-3xl font-semibold">Eventos</h1>
        <p class="mt-2 text-dj-muted">Organize os eventos do Digital JOST.</p>
      </div>
      <div v-if="data?.capabilities.can_create" ref="newEventAction">
        <Button type="button" label="Novo evento" icon="pi pi-plus"
          :disabled="showForm" @click="openForm" />
      </div>
    </div>

    <Message v-if="feedback" severity="success" role="status" aria-live="polite" class="mb-6">
      {{ feedback }}
    </Message>

    <div v-if="loading" aria-busy="true">
      <p role="status" class="sr-only">Carregando eventos…</p>
      <div aria-hidden="true" class="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
        <div v-for="index in 6" :key="index" class="rounded-xl border border-dj-border bg-white p-6">
          <Skeleton width="70%" height="1.5rem" />
          <Skeleton width="100%" height="4.5rem" class="mt-4" />
        </div>
      </div>
    </div>
    <div v-else-if="isError">
      <Message severity="error" class="mb-4">
        {{ listStatus === 401 ? 'Sua sessão expirou. Acesse novamente o portal.'
          : listStatus === 403 ? 'Você não tem permissão para ver os eventos.'
          : listStatus === 404 ? 'Eventos não está disponível para seu acesso.'
          : 'Não foi possível carregar os eventos.' }}
      </Message>
      <a v-if="[401, 403, 404].includes(listStatus)" href="/" class="text-primary underline">
        Voltar ao portal
      </a>
      <Button v-else type="button" label="Tentar novamente" outlined @click="refetch()" />
    </div>
    <div v-else-if="data?.items.length === 0" class="rounded-xl border border-dj-border bg-white p-8">
      <h2 class="text-lg font-semibold">Nenhum evento cadastrado</h2>
      <p class="mt-2 text-dj-muted">Os eventos aparecerão aqui quando forem criados.</p>
    </div>
    <div v-else class="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
      <EventCard v-for="event in data?.items ?? []" :key="event.id" :event="event" />
    </div>

    <nav v-if="!loading && !isError && data && data.total > perPage"
      aria-label="Páginas de eventos" class="mt-8">
      <Paginator :first="(page - 1) * perPage" :rows="perPage" :total-records="data.total"
        @page="changePage" />
    </nav>

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
