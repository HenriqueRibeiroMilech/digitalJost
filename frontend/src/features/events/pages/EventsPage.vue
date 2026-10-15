<script setup lang="ts">
import { nextTick, ref } from 'vue'
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { usePagination } from '@/shared/composables/usePagination'
import PageHeader from '@/shared/components/PageHeader.vue'
import CardGrid from '@/shared/components/CardGrid.vue'
import RequestState from '@/shared/components/RequestState.vue'
import ListPagination from '@/shared/components/ListPagination.vue'
import Button from '@/volt/Button.vue'
import Message from '@/volt/Message.vue'
import Skeleton from '@/volt/Skeleton.vue'
import EventCard from '../components/EventCard.vue'
import EventDialog from '../components/EventDialog.vue'
import { eventsApi } from '../api'
import type { EventChange } from '../types'

const { page, perPage, resetPage } = usePagination()
const dialogOpen = ref(false)
const selectedId = ref<number | null>(null)
const feedback = ref('')
const newEventAction = ref<HTMLElement | null>(null)
const pageElement = ref<HTMLElement | null>(null)
const queryClient = useQueryClient()
const { data, isPending: loading, isError, error: listError, refetch } = useQuery({
  queryKey: ['events', 'list', page],
  queryFn: () => eventsApi.list(page.value, perPage),
  retry: false,
})

function openEvent(id: number | null = null) {
  selectedId.value = id
  feedback.value = ''
  dialogOpen.value = true
}

async function restoreFocus() {
  dialogOpen.value = false
  await nextTick()
  const eventAction = selectedId.value === null ? null
    : document.getElementById('event-open-' + selectedId.value)
  if (eventAction) {
    eventAction.focus()
    return
  }
  const fallback = newEventAction.value?.querySelector('button') ?? pageElement.value
  fallback?.focus()
}

async function eventChanged(action: EventChange) {
  const messages = {
    created: 'Evento criado com sucesso.',
    updated: 'Evento atualizado com sucesso.',
    deleted: 'Evento excluído com sucesso.',
  }
  feedback.value = messages[action]
  if (action === 'created' || action === 'deleted') resetPage()
  await queryClient.invalidateQueries({ queryKey: ['events', 'list'] })
}
</script>

<template>
  <section ref="pageElement" tabindex="-1" aria-labelledby="events-title">
    <PageHeader id="events-title" eyebrow="Agenda corporativa" title="Eventos"
      description="Organize os eventos do Digital JOST e acompanhe os períodos de realização.">
      <template #actions>
        <div v-if="data?.capabilities.can_create" ref="newEventAction">
          <Button type="button" label="Novo evento" icon="pi pi-plus"
            :disabled="dialogOpen" @click="openEvent()" />
        </div>
      </template>
    </PageHeader>

    <Message v-if="feedback" severity="success" role="status" aria-live="polite" class="mb-6">
      {{ feedback }}
    </Message>

    <div class="mb-5 flex flex-wrap items-center justify-between gap-3">
      <h2 class="flex items-center gap-2.5 text-sm font-semibold text-dj-ink">
        Todos os eventos
        <span v-if="data && !isError" class="rounded-full border border-dj-border bg-dj-surface px-2.5 py-0.5 text-xs text-dj-muted tabular-nums"
          :aria-label="'Total de eventos: ' + data.total">{{ data.total }}</span>
      </h2>
      <p class="text-xs text-dj-muted">Selecione um evento para ver os detalhes.</p>
    </div>

    <RequestState :loading="loading" :failed="isError" :error="listError"
      :empty="data?.items.length === 0" loading-label="Carregando eventos…"
      empty-title="Nenhum evento cadastrado"
      empty-description="Os eventos aparecerão aqui quando forem criados."
      empty-icon="pi pi-calendar"
      error-message="Não foi possível carregar os eventos."
      forbidden-message="Você não tem permissão para ver os eventos."
      not-found-message="Eventos não está disponível para seu acesso." @retry="refetch()">
      <template #loading>
        <CardGrid>
          <div v-for="index in 8" :key="index" class="rounded-dj-card border border-dj-border bg-dj-surface p-5 shadow-dj-card">
            <div class="mb-4 flex items-start justify-between gap-3">
              <Skeleton width="3rem" height="3rem" border-radius="0.75rem" />
              <Skeleton width="4rem" height="1.5rem" border-radius="1rem" />
            </div>
            <Skeleton width="85%" height="3rem" />
            <Skeleton width="100%" height="3rem" class="mt-2" />
            <Skeleton width="100%" height="5rem" class="mt-4" border-radius="0.75rem" />
            <Skeleton width="100%" height="2rem" class="mt-4" />
          </div>
        </CardGrid>
      </template>
      <CardGrid>
        <EventCard v-for="event in data?.items ?? []" :key="event.id" :event="event" @open="openEvent" />
      </CardGrid>
    </RequestState>

    <ListPagination v-if="!loading && !isError && data" v-model:page="page"
      :per-page="perPage" :total="data.total" label="Páginas de eventos" />

    <EventDialog v-if="dialogOpen" :event-id="selectedId"
      @changed="eventChanged" @closed="restoreFocus" />
  </section>
</template>
