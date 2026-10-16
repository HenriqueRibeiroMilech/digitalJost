<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import Column from 'primevue/column'
import ListPagination from '@/shared/components/ListPagination.vue'
import RequestState from '@/shared/components/RequestState.vue'
import Button from '@/volt/Button.vue'
import DataTable from '@/volt/DataTable.vue'
import SecondaryButton from '@/volt/SecondaryButton.vue'
import { attendanceApi } from '../attendanceApi'
import type { AttendanceEntries, AttendanceRegistered } from '../types'
import AttendanceReader from './AttendanceReader.vue'

const props = defineProps<{ eventId: number; eventName: string; listId: number }>()
const emit = defineEmits<{ back: []; busy: [value: boolean] }>()
const readerOpen = ref(false)
const page = ref(1)
const perPage = 25
const queryClient = useQueryClient()
const baseKey = ['events', 'attendance', props.eventId]
const entriesKey = [...baseKey, 'entries', props.listId]
const { data: list, isPending, isError, error, refetch } = useQuery({
  queryKey: [...baseKey, 'list', props.listId],
  queryFn: () => attendanceApi.get(props.eventId, props.listId),
  retry: false,
  refetchOnWindowFocus: false,
  refetchOnReconnect: false,
})
const { data: entries, isPending: entriesPending, isError: entriesError, error: entriesFailure, refetch: refetchEntries } = useQuery({
  queryKey: [...entriesKey, page],
  queryFn: () => attendanceApi.entries(props.eventId, props.listId, page.value, perPage),
  enabled: computed(() => Boolean(list.value) && !readerOpen.value),
  retry: false,
  refetchOnWindowFocus: false,
  refetchInterval: computed<number | false>(() => readerOpen.value ? false : 5_000),
  refetchIntervalInBackground: false,
})
watch(readerOpen, value => emit('busy', value), { immediate: true })
watch(list, async (value, previous) => {
  if (value && !previous) {
    await nextTick()
    document.getElementById('attendance-list-title')?.focus()
  }
}, { immediate: true })
onBeforeUnmount(() => emit('busy', false))

function registered(result: AttendanceRegistered) {
  // A escrita já terminou. A atualização da tabela não deve repetir a leitura.
  if (result.created && list.value) {
    queryClient.setQueryData([...baseKey, 'list', props.listId], { ...list.value, total: list.value.total + 1 })
  }
  page.value = 1
  if (result.created) {
    queryClient.setQueryData<AttendanceEntries>([...entriesKey, 1], current => current && ({
      ...current,
      items: [result.item, ...current.items.filter(item => item.id !== result.item.id)].slice(0, perPage),
      total: current.total + 1,
    }))
  } else {
    queryClient.setQueryData<AttendanceEntries>([...entriesKey, 1], current => current && ({
      ...current,
      items: current.items.map(item => item.id === result.item.id ? result.item : item),
    }))
  }
  void queryClient.invalidateQueries({ queryKey: entriesKey })
  void queryClient.invalidateQueries({ queryKey: [...baseKey, 'lists'] })
}

async function readerClosed() {
  readerOpen.value = false
  void queryClient.invalidateQueries({ queryKey: [...baseKey, 'list', props.listId] })
  await nextTick()
  document.getElementById('attendance-start-reader')?.focus()
}
</script>

<template>
  <SecondaryButton type="button" label="Todas as listas" icon="pi pi-arrow-left" text :disabled="readerOpen" class="mb-4" @click="emit('back')" />
  <RequestState :loading="isPending" :failed="isError" :error="error" :empty="false"
    loading-label="Carregando lista…" not-found-message="Esta lista não existe neste evento." @retry="refetch()">
    <template v-if="list">
      <div class="mb-5 rounded-2xl border border-dj-border bg-dj-canvas p-5">
        <div class="flex flex-wrap items-start justify-between gap-4">
          <div class="min-w-0 flex-1">
            <p class="text-xs font-semibold tracking-wide text-dj-muted uppercase">Lista de presença</p>
            <h4 id="attendance-list-title" tabindex="-1" class="mt-2 break-words text-lg font-bold text-dj-ink">{{ list.name }}</h4>
            <p class="mt-2 text-sm text-dj-muted">{{ entries?.total ?? list.total }} {{ (entries?.total ?? list.total) === 1 ? 'participante registrado' : 'participantes registrados' }}</p>
          </div>
          <Button v-if="list.capabilities.can_register" id="attendance-start-reader" type="button"
            label="Iniciar preenchimento por leitor" icon="pi pi-id-card" pt:root:class="rounded-xl" @click="readerOpen = true" />
        </div>
        <p class="mt-4 text-xs leading-5 text-dj-muted">Nome e setor são preenchidos automaticamente quando encontrados. Dados ausentes aparecem como “Não informado”.</p>
      </div>
      <RequestState :loading="entriesPending" :failed="entriesError" :error="entriesFailure" :empty="false"
        loading-label="Carregando presenças…" @retry="refetchEntries()">
        <div class="overflow-x-auto rounded-2xl border border-dj-border">
          <DataTable :value="entries?.items ?? []" data-key="id" :table-props="{ 'aria-label': 'Participantes da lista ' + list.name }"
            :table-style="{ minWidth: '30rem' }">
            <Column field="registration" header="Matrícula" body-class="font-mono tabular-nums" />
            <Column field="name" header="Nome">
              <template #body="{ data: entry }"><span :class="{ 'text-dj-muted': !entry.name }">{{ entry.name || 'Não informado' }}</span></template>
            </Column>
            <Column field="department" header="Setor">
              <template #body="{ data: entry }"><span :class="{ 'text-dj-muted': !entry.department }">{{ entry.department || 'Não informado' }}</span></template>
            </Column>
            <template #empty><p class="py-6 text-center text-sm text-dj-muted">Nenhuma presença registrada. Inicie o leitor para receber os participantes.</p></template>
          </DataTable>
        </div>
        <ListPagination v-if="entries" v-model:page="page" :per-page="perPage" :total="entries.total" label="Páginas das presenças" />
      </RequestState>
      <AttendanceReader v-if="readerOpen" :event-id="eventId" :event-name="eventName" :list-id="listId" :list-name="list.name"
        @registered="registered" @closed="readerClosed" />
    </template>
  </RequestState>
</template>
