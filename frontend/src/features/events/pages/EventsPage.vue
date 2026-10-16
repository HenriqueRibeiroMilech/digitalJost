<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { ApiError } from '@/shared/api/client'
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
import EventFilters from '../components/EventFilters.vue'
import { eventsApi } from '../api'
import { defaultEventStatuses } from '../statuses'
import type { EventChange, EventFilters as EventFilterValues } from '../types'

const { page, perPage, resetPage } = usePagination()
const dialogOpen = ref(false)
const selectedId = ref<number | null>(null)
const feedback = ref('')
const newEventAction = ref<HTMLElement | null>(null)
const pageElement = ref<HTMLElement | null>(null)
const canCreate = ref(false)
const filters = ref<EventFilterValues>({ search: '', statuses: [...defaultEventStatuses] })
const initialFilters = computed(() => !filters.value.search
  && filters.value.statuses.join(',') === defaultEventStatuses.join(','))
const queryClient = useQueryClient()
const { data, isPending: loading, isError, error: listError, refetch } = useQuery({
  queryKey: ['events', 'list', page, filters],
  queryFn: () => eventsApi.list(page.value, perPage, filters.value),
  retry: false,
  refetchInterval: computed<number | false>(() => dialogOpen.value ? false : 60_000),
  refetchIntervalInBackground: false,
})

watch(data, result => {
  if (!result) return
  canCreate.value = result.capabilities.can_create
  const lastPage = Math.max(1, Math.ceil(result.total / perPage))
  if (page.value > lastPage) page.value = lastPage
}, { immediate: true })

watch(listError, error => {
  if (error instanceof ApiError && [401, 403, 404].includes(error.status)) canCreate.value = false
}, { immediate: true })

function applyFilters(next: EventFilterValues) {
  if (next.search === filters.value.search && next.statuses.join(',') === filters.value.statuses.join(',')) return
  resetPage()
  filters.value = next
}

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
    <PageHeader id="events-title" title="Eventos"
      description="Organize os eventos, acompanhe os períodos de realização e listas de presença.">
      <template #actions>
        <div v-if="canCreate" ref="newEventAction">
          <Button type="button" label="Novo evento" icon="pi pi-plus"
            :disabled="dialogOpen" pt:root:class="rounded-xl px-5 py-3 shadow-sm" @click="openEvent()" />
        </div>
      </template>
    </PageHeader>

    <Message v-if="feedback" severity="success" role="status" aria-live="polite" class="mb-6">
      {{ feedback }}
    </Message>

    <EventFilters @change="applyFilters" />

    <div class="mb-5 flex flex-wrap items-center justify-between gap-3">
      <h2 class="flex items-center gap-2.5 text-sm font-semibold text-dj-ink">
        Eventos encontrados
        <span v-if="data && !isError" class="rounded-full border border-dj-border bg-dj-surface px-2.5 py-0.5 text-xs text-dj-muted tabular-nums"
          :aria-label="'Total de eventos: ' + data.total">{{ data.total }}</span>
      </h2>
      <p class="text-xs text-dj-muted">Selecione um evento para ver os detalhes.</p>
    </div>

    <RequestState :loading="loading" :failed="isError" :error="listError"
      :empty="data?.items.length === 0" loading-label="Carregando eventos…"
      :empty-title="initialFilters ? 'Nenhum evento futuro ou em andamento' : 'Nenhum evento para estes filtros'"
      empty-description="Altere a pesquisa ou os status para consultar outros eventos, incluindo os concluídos e os que ainda não têm período."
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
