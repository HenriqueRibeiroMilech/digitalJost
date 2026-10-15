<script setup lang="ts">
import { nextTick, ref } from 'vue'
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { usePagination } from '@/shared/composables/usePagination'
import PageHeader from '@/shared/components/PageHeader.vue'
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
    <PageHeader id="events-title" title="Eventos" description="Organize os eventos do Digital JOST.">
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
        <EventCard v-for="event in data?.items ?? []" :key="event.id" :event="event" @open="openEvent" />
      </div>
    </RequestState>

    <ListPagination v-if="!loading && !isError && data" v-model:page="page"
      :per-page="perPage" :total="data.total" label="Páginas de eventos" />

    <EventDialog v-if="dialogOpen" :event-id="selectedId"
      @changed="eventChanged" @closed="restoreFocus" />
  </section>
</template>
