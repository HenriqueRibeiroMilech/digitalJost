<script setup lang="ts">
import { computed, defineAsyncComponent, nextTick, ref } from 'vue'
import { useMutation, useQuery } from '@tanstack/vue-query'
import { ApiError } from '@/shared/api/client'
import { validationMessages } from '@/shared/api/validation'
import RequestState from '@/shared/components/RequestState.vue'
import AppDialog from '@/shared/components/AppDialog.vue'
import Button from '@/volt/Button.vue'
import SecondaryButton from '@/volt/SecondaryButton.vue'
import Message from '@/volt/Message.vue'
import Tabs from '@/volt/Tabs.vue'
import Tab from '@/volt/Tab.vue'
import TabList from '@/volt/TabList.vue'
import TabPanels from '@/volt/TabPanels.vue'
import TabPanel from '@/volt/TabPanel.vue'
import { eventsApi } from '../api'
import { formatEventDateTime } from '../dates'
import { eventStatuses } from '../statuses'
import type { EventChange, EventCreate } from '../types'
import EventForm from './EventForm.vue'
import EventStatusBadge from './EventStatusBadge.vue'

const EventAttendance = defineAsyncComponent(() => import('./EventAttendance.vue'))

const props = defineProps<{ eventId: number | null }>()
const emit = defineEmits<{ closed: []; changed: [action: EventChange] }>()
const visible = ref(true)
const view = ref<'create' | 'details' | 'edit' | 'delete'>(props.eventId === null ? 'create' : 'details')
const submitError = ref('')
const emptyErrors = () => ({ name: '', description: '', event_type_id: '', instructor: '', syllabus: '', starts_at: '', ends_at: '' })
const fieldErrors = ref(emptyErrors())
const contentElement = ref<HTMLElement | null>(null)
const activeTab = ref<string | number>('details')
const attendanceBusy = ref(false)
const typeBusy = ref(false)
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
  refetchInterval: computed<number | false>(() => view.value === 'details' && activeTab.value === 'details' && visible.value ? 60_000 : false),
  refetchIntervalInBackground: false,
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
const busy = computed(() => saving.value || deleting.value || attendanceBusy.value || typeBusy.value)
const title = computed(() => view.value === 'create' ? 'Novo evento'
  : view.value === 'edit' ? 'Editar evento'
  : view.value === 'delete' ? 'Excluir evento' : 'Detalhes do evento')
const subtitle = computed(() => view.value === 'create' ? 'Defina as informações e o período de realização.'
  : view.value === 'edit' ? 'Atualize as informações e o período de realização.'
  : view.value === 'delete' ? 'Confira o evento antes de confirmar a exclusão.'
  : 'Informações, período e acompanhamento do evento.')
const dialogTone = computed<'brand' | 'success' | 'neutral' | 'danger'>(() => view.value === 'delete' ? 'danger'
  : view.value === 'details' && event.value ? eventStatuses[event.value.status].tone : 'brand')
const dialogIcon = computed(() => view.value === 'delete' ? 'pi pi-trash'
  : view.value === 'edit' ? 'pi pi-pencil' : 'pi pi-calendar')

async function changeView(next: 'details' | 'edit' | 'delete') {
  if (busy.value || (next !== 'details' && isFetching.value)) return
  submitError.value = ''
  fieldErrors.value = emptyErrors()
  view.value = next
  await nextTick()
  const selector = next === 'edit' ? '#event-name'
    : next === 'delete' ? '#event-delete-cancel' : '#event-details-title'
  document.getElementById('event-dialog')?.querySelector<HTMLElement>(selector)?.focus()
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
      fieldErrors.value = validationMessages(error.detail, ['name', 'description', 'event_type_id', 'instructor', 'syllabus', 'starts_at', 'ends_at'] as const)
      if (Object.values(fieldErrors.value).some(Boolean)) {
        await nextTick()
        contentElement.value?.querySelector<HTMLElement>('input[aria-invalid="true"], textarea[aria-invalid="true"], [role="combobox"][aria-invalid="true"]')?.focus()
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
  <AppDialog id="event-dialog" :visible="visible" :title="title" :subtitle="subtitle" :icon="dialogIcon"
    :busy="busy" :tone="dialogTone"
    :description-id="view === 'create' || view === 'edit' ? 'event-form-help' : undefined"
    @update:visible="updateVisibility" @closed="emit('closed')">
    <div ref="contentElement">
      <EventForm v-if="view === 'create'" :busy="busy" :server-error="submitError"
        :field-errors="fieldErrors" @submit="saveEvent" @cancel="cancelForm" @busy="typeBusy = $event" />

      <RequestState v-else :loading="loading"
        :failed="isError" :error="error" :empty="false"
        loading-label="Carregando evento…" error-message="Não foi possível carregar o evento."
        forbidden-message="Você não tem permissão para ver este evento."
        not-found-message="Este evento não existe ou já foi excluído." @retry="refetch()">
        <template v-if="event">
          <EventForm v-if="view === 'edit'" :event="event" :busy="busy"
            :server-error="submitError" :field-errors="fieldErrors"
            @submit="saveEvent" @cancel="cancelForm" @busy="typeBusy = $event" />

          <div v-else-if="view === 'delete'" :aria-busy="busy">
            <div class="rounded-2xl border border-dj-border bg-dj-canvas p-5">
              <div class="mb-3 flex flex-wrap items-center justify-between gap-2">
                <EventStatusBadge :status="event.status" />
              </div>
              <h3 class="break-words text-lg font-semibold text-dj-ink">{{ event.name }}</h3>
              <p class="mt-3 text-sm leading-6 text-dj-muted">
                {{ formatEventDateTime(event.starts_at) }} → {{ formatEventDateTime(event.ends_at) }}
              </p>
            </div>
            <Message severity="warn" class="mt-5">O evento, suas listas de presença e os participantes registrados serão excluídos permanentemente. Esta ação não pode ser desfeita.</Message>
            <Message v-if="submitError" severity="error" class="mt-4">{{ submitError }}</Message>
          </div>

          <div v-else>
            <div class="mb-5 flex flex-wrap items-center gap-3">
              <EventStatusBadge :status="event.status" />
            </div>
            <h3 id="event-details-title" tabindex="-1" class="break-words text-2xl leading-8 font-bold tracking-tight text-dj-ink">{{ event.name }}</h3>
            <Tabs v-model:value="activeTab" class="mt-4">
              <TabList>
                <Tab value="details" :disabled="busy || isFetching">Informações</Tab>
                <Tab value="attendance" :disabled="busy || isFetching"><i class="pi pi-users mr-2" aria-hidden="true" />Listas de presença</Tab>
              </TabList>
              <TabPanels pt:root:class="px-0 pt-5 pb-0">
                <TabPanel value="details">
                  <dl class="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    <div class="rounded-2xl border border-dj-border bg-dj-canvas p-4">
                      <dt class="flex items-center gap-2 text-xs font-semibold text-dj-muted"><i class="pi pi-tag" aria-hidden="true" /> Tipo de evento</dt>
                      <dd class="mt-3 break-words text-sm font-semibold text-dj-ink">{{ event.event_type_name || 'Não informado' }}</dd>
                    </div>
                    <div class="rounded-2xl border border-dj-border bg-dj-canvas p-4">
                      <dt class="flex items-center gap-2 text-xs font-semibold text-dj-muted"><i class="pi pi-user" aria-hidden="true" /> Instrutor</dt>
                      <dd class="mt-3 break-words text-sm font-semibold text-dj-ink">{{ event.instructor || 'Não informado' }}</dd>
                    </div>
                    <div class="rounded-2xl border border-dj-border bg-dj-canvas p-4">
                      <dt class="flex items-center gap-2 text-xs font-semibold text-dj-muted"><i class="pi pi-calendar" aria-hidden="true" /> Início</dt>
                      <dd class="mt-3 text-sm font-semibold text-dj-ink tabular-nums">{{ formatEventDateTime(event.starts_at) }}</dd>
                    </div>
                    <div class="rounded-2xl border border-dj-border bg-dj-canvas p-4">
                      <dt class="flex items-center gap-2 text-xs font-semibold text-dj-muted"><i class="pi pi-clock" aria-hidden="true" /> Fim</dt>
                      <dd class="mt-3 text-sm font-semibold text-dj-ink tabular-nums">{{ formatEventDateTime(event.ends_at) }}</dd>
                    </div>
                  </dl>
                  <Message v-if="event.status === 'unscheduled'" severity="info" class="mt-4">
                    Preencha as datas na edição para que o evento acompanhe os status de realização.
                  </Message>
                  <section class="mt-6 rounded-2xl border border-dj-border p-5">
                    <h4 class="mb-3 text-xs font-semibold tracking-wide text-dj-muted uppercase">Sobre o evento</h4>
                    <p class="whitespace-pre-wrap break-words text-sm leading-7 text-dj-ink">{{ event.description }}</p>
                  </section>
                  <section class="mt-4 rounded-2xl border border-dj-border p-5">
                    <h4 class="mb-3 text-xs font-semibold tracking-wide text-dj-muted uppercase">Conteúdo programático</h4>
                    <p class="whitespace-pre-wrap break-words text-sm leading-7 text-dj-ink">{{ event.syllabus || 'Não informado' }}</p>
                  </section>
                </TabPanel>
                <TabPanel value="attendance">
                  <EventAttendance v-if="activeTab === 'attendance'" :event-id="event.id" :event-name="event.name"
                    @busy="attendanceBusy = $event" />
                </TabPanel>
              </TabPanels>
            </Tabs>
          </div>
        </template>
      </RequestState>
    </div>
    <template v-if="view === 'delete' || view === 'details'" #footer>
      <template v-if="view === 'delete'">
        <SecondaryButton id="event-delete-cancel" type="button" label="Cancelar" outlined :disabled="busy"
          pt:root:class="rounded-xl" @click="changeView('details')" />
        <Button type="button" :label="deleting ? 'Excluindo…' : 'Excluir evento'" icon="pi pi-trash"
          :loading="deleting" :disabled="busy || isError || !event?.capabilities.can_delete"
          pt:root:class="dj-danger-action rounded-xl" @click="deleteEvent" />
      </template>
      <template v-else>
        <SecondaryButton type="button" label="Fechar" outlined :disabled="busy" pt:root:class="rounded-xl" @click="updateVisibility(false)" />
        <template v-if="event && !loading && !isError">
          <Button v-if="event.capabilities.can_update" type="button" label="Editar"
            icon="pi pi-pencil" outlined :disabled="isFetching || busy" pt:root:class="rounded-xl" @click="changeView('edit')" />
          <SecondaryButton v-if="event.capabilities.can_delete" type="button" label="Excluir"
            icon="pi pi-trash" outlined :disabled="isFetching || busy"
            pt:root:class="rounded-xl border-dj-danger/20 text-dj-danger enabled:hover:bg-dj-danger-soft enabled:hover:text-dj-danger"
            @click="changeView('delete')" />
        </template>
      </template>
    </template>
  </AppDialog>
</template>
