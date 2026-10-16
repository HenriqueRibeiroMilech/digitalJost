<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import Column from 'primevue/column'
import jostLogo from '@/assets/images/jost_logo.jpg'
import { ApiError } from '@/shared/api/client'
import ListPagination from '@/shared/components/ListPagination.vue'
import RequestState from '@/shared/components/RequestState.vue'
import Button from '@/volt/Button.vue'
import DataTable from '@/volt/DataTable.vue'
import Message from '@/volt/Message.vue'
import SecondaryButton from '@/volt/SecondaryButton.vue'
import { attendanceApi } from '../attendanceApi'
import type { AttendanceAction, AttendanceEntries, AttendanceListDetail, AttendanceLists, AttendanceRegistered } from '../types'
import AttendanceActionDialog from './AttendanceActionDialog.vue'
import AttendanceReader from './AttendanceReader.vue'

const props = defineProps<{ eventId: number; eventName: string; listId: number }>()
const emit = defineEmits<{ back: []; busy: [value: boolean] }>()
const readerOpen = ref(false)
const action = ref<AttendanceAction | null>(null)
const exportError = ref('')
const { mutateAsync: loadPdf, isPending: exporting } = useMutation({
  mutationFn: () => attendanceApi.pdf(props.eventId, props.listId),
  retry: false,
})
const managing = computed(() => readerOpen.value || action.value !== null || exporting.value)
const page = ref(1)
const perPage = 25
const queryClient = useQueryClient()
const baseKey = ['events', 'attendance', props.eventId]
const listKey = [...baseKey, 'list', props.listId]
const entriesKey = [...baseKey, 'entries', props.listId]
const { data: list, isPending, isError, error, refetch } = useQuery({
  queryKey: listKey,
  queryFn: () => attendanceApi.get(props.eventId, props.listId),
  retry: false,
  refetchOnWindowFocus: false,
  refetchOnReconnect: false,
})
const { data: entries, isPending: entriesPending, isError: entriesError, error: entriesFailure, refetch: refetchEntries } = useQuery({
  queryKey: [...entriesKey, page],
  queryFn: () => attendanceApi.entries(props.eventId, props.listId, page.value, perPage),
  enabled: computed(() => Boolean(list.value) && !managing.value),
  retry: false,
  refetchOnWindowFocus: false,
  refetchInterval: computed<number | false>(() => managing.value ? false : 5_000),
  refetchIntervalInBackground: false,
})
watch(managing, value => emit('busy', value), { immediate: true, flush: 'sync' })
watch(entries, value => {
  if (value) page.value = Math.min(page.value, Math.max(1, Math.ceil(value.total / perPage)))
})
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
    queryClient.setQueryData(listKey, { ...list.value, total: list.value.total + 1 })
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
  void queryClient.invalidateQueries({ queryKey: listKey, exact: true })
  await nextTick()
  document.getElementById('attendance-start-reader')?.focus()
}

function openAction(next: AttendanceAction) {
  if (!managing.value) action.value = next
}

async function exportPdf() {
  if (managing.value || !list.value?.capabilities.can_export) return
  exportError.value = ''
  try {
    const blob = await loadPdf()
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    try {
      link.href = url
      link.download = `lista-presenca-evento-${props.eventId}-lista-${props.listId}.pdf`
      document.body.appendChild(link)
      link.click()
    } finally {
      link.remove()
      // Aguarda o navegador iniciar o download antes de liberar o Blob.
      window.setTimeout(() => URL.revokeObjectURL(url), 10000)
    }
  } catch (error) {
    exportError.value = error instanceof ApiError && error.status === 503
      ? 'A geração de PDF está indisponível. Tente novamente ou chame o responsável pelo sistema.'
      : error instanceof Error ? error.message : 'Não foi possível baixar a lista em PDF.'
  } finally {
    await nextTick()
    document.getElementById('attendance-download-pdf')?.focus()
  }
}

async function actionClosed(changed: boolean) {
  const previous = action.value
  if (!previous) return
  if (changed && previous.kind === 'delete-list') {
    queryClient.setQueriesData<AttendanceLists>({ queryKey: [...baseKey, 'lists'] }, current => current && ({
      ...current,
      items: current.items.filter(item => item.id !== props.listId),
      total: Math.max(0, current.total - 1),
    }))
    void queryClient.invalidateQueries({ queryKey: [...baseKey, 'lists'] })
    emit('back')
    await nextTick()
    queryClient.removeQueries({ queryKey: listKey, exact: true })
    queryClient.removeQueries({ queryKey: entriesKey })
    return
  }
  if (changed && previous.kind === 'delete-entry') {
    const total = Math.max(0, (entries.value?.total ?? list.value?.total ?? 1) - 1)
    queryClient.setQueryData<AttendanceListDetail>(listKey, current => current && ({ ...current, total }))
    queryClient.setQueriesData<AttendanceEntries>({ queryKey: entriesKey }, current => current && ({
      ...current, items: current.items.filter(item => item.id !== previous.entry.id), total,
    }))
    page.value = Math.min(page.value, Math.max(1, Math.ceil(total / perPage)))
  }
  action.value = null
  // Atualiza também após cancelamento/falha: outra sessão pode ter alterado a lista.
  void queryClient.invalidateQueries({ queryKey: listKey, exact: true })
  void queryClient.invalidateQueries({ queryKey: entriesKey })
  void queryClient.invalidateQueries({ queryKey: [...baseKey, 'lists'] })
  await nextTick()
  const target = previous.kind === 'rename' ? 'attendance-list-rename'
    : previous.kind === 'delete-list' ? 'attendance-list-delete'
    : changed ? 'attendance-list-title' : 'attendance-entry-delete-' + previous.entry.id
  const control = document.getElementById(target) ?? document.getElementById('attendance-back-to-lists')
  control?.focus()
}
</script>

<template>
  <SecondaryButton id="attendance-back-to-lists" type="button" label="Todas as listas" icon="pi pi-arrow-left" text :disabled="managing" class="mb-4" @click="emit('back')" />
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
          <img :src="jostLogo" alt="JOST" class="h-10 w-28 shrink-0 object-contain object-right" />
        </div>
        <div class="mt-4 flex flex-wrap gap-2">
          <SecondaryButton v-if="list.capabilities.can_export" id="attendance-download-pdf" type="button"
            :label="exporting ? 'Gerando PDF…' : 'Baixar PDF'" icon="pi pi-file-pdf" outlined :loading="exporting"
            :disabled="managing" pt:root:class="rounded-xl" @click="exportPdf" />
          <SecondaryButton v-if="list.capabilities.can_update" id="attendance-list-rename" type="button"
            label="Editar nome" icon="pi pi-pencil" outlined :disabled="managing"
            pt:root:class="rounded-xl" @click="openAction({ kind: 'rename' })" />
          <SecondaryButton v-if="list.capabilities.can_delete" id="attendance-list-delete" type="button"
            label="Excluir lista" icon="pi pi-trash" outlined :disabled="managing"
            pt:root:class="rounded-xl border-dj-danger/20 text-dj-danger enabled:hover:bg-dj-danger-soft"
            @click="openAction({ kind: 'delete-list' })" />
          <Button v-if="list.capabilities.can_register" id="attendance-start-reader" type="button"
            label="Iniciar preenchimento por leitor" icon="pi pi-id-card" :disabled="managing"
            pt:root:class="rounded-xl" @click="readerOpen = true" />
        </div>
        <p class="mt-4 text-xs leading-5 text-dj-muted">A presença só é registrada após identificar o participante. Empresa, nome e setor são preenchidos quando disponíveis.</p>
      </div>
      <Message v-if="exportError" severity="error" class="mb-4">{{ exportError }}</Message>
      <RequestState :loading="entriesPending" :failed="entriesError" :error="entriesFailure" :empty="false"
        loading-label="Carregando presenças…" @retry="refetchEntries()">
        <div class="overflow-x-auto rounded-2xl border border-dj-border">
          <DataTable :value="entries?.items ?? []" data-key="id" :table-props="{ 'aria-label': 'Participantes da lista ' + list.name }"
            :table-style="{ minWidth: '48rem' }">
            <Column field="company" header="Empresa">
              <template #body="{ data: entry }"><span :class="{ 'text-dj-muted': !entry.company }">{{ entry.company || 'Não informado' }}</span></template>
            </Column>
            <Column field="registration" header="Matrícula" body-class="font-mono tabular-nums">
              <template #body="{ data: entry }">{{ entry.registration.slice(-8) }}</template>
            </Column>
            <Column field="name" header="Nome">
              <template #body="{ data: entry }"><span :class="{ 'text-dj-muted': !entry.name }">{{ entry.name || 'Não informado' }}</span></template>
            </Column>
            <Column field="department" header="Setor">
              <template #body="{ data: entry }"><span :class="{ 'text-dj-muted': !entry.department }">{{ entry.department || 'Não informado' }}</span></template>
            </Column>
            <Column v-if="list.capabilities.can_delete_entry" header="Ações" body-class="whitespace-nowrap">
              <template #body="{ data: entry }">
                <SecondaryButton :id="'attendance-entry-delete-' + entry.id" type="button" label="Remover"
                  icon="pi pi-trash" text :disabled="managing"
                  :aria-label="'Remover ' + (entry.name || 'matrícula ' + entry.registration.slice(-8)) + ' desta lista'"
                  pt:root:class="rounded-xl text-dj-danger enabled:hover:bg-dj-danger-soft"
                  @click="openAction({ kind: 'delete-entry', entry })" />
              </template>
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
  <AttendanceActionDialog v-if="action && list" :event-id="eventId" :list="list" :action="action" @closed="actionClosed" />
</template>
