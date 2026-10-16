<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { ApiError } from '@/shared/api/client'
import { validationMessages } from '@/shared/api/validation'
import FormField from '@/shared/components/FormField.vue'
import ListPagination from '@/shared/components/ListPagination.vue'
import RequestState from '@/shared/components/RequestState.vue'
import Button from '@/volt/Button.vue'
import InputText from '@/volt/InputText.vue'
import Message from '@/volt/Message.vue'
import SecondaryButton from '@/volt/SecondaryButton.vue'
import { attendanceApi } from '../attendanceApi'
import AttendanceListView from './AttendanceListView.vue'

const props = defineProps<{ eventId: number; eventName: string }>()
const emit = defineEmits<{ busy: [value: boolean] }>()
const page = ref(1)
const perPage = 6
const selectedId = ref<number | null>(null)
const creating = ref(false)
const name = ref('')
const nameError = ref('')
const submitError = ref('')
const childBusy = ref(false)
const queryClient = useQueryClient()
const { data, isPending, isError, error, refetch } = useQuery({
  queryKey: ['events', 'attendance', props.eventId, 'lists', page],
  queryFn: () => attendanceApi.list(props.eventId, page.value, perPage),
  enabled: computed(() => selectedId.value === null),
  retry: false,
  refetchOnWindowFocus: false,
})
const { mutateAsync: create, isPending: saving } = useMutation({
  mutationFn: (value: string) => attendanceApi.create(props.eventId, value),
  retry: false,
})
watch(() => saving.value || childBusy.value, value => emit('busy', value), { immediate: true, flush: 'sync' })
watch(data, value => {
  if (value) page.value = Math.min(page.value, Math.max(1, Math.ceil(value.total / perPage)))
})
onBeforeUnmount(() => emit('busy', false))

async function showCreate() {
  creating.value = true
  submitError.value = ''
  nameError.value = ''
  await nextTick()
  document.getElementById('attendance-list-name')?.focus()
}

async function createList() {
  if (saving.value) return
  nameError.value = ''
  submitError.value = ''
  const value = name.value.trim()
  if (!value || value.length > 120) {
    nameError.value = 'Informe um nome entre 1 e 120 caracteres.'
    document.getElementById('attendance-list-name')?.focus()
    return
  }
  let created
  try {
    created = await create(value)
  } catch (error) {
    if (error instanceof ApiError && error.status === 422) {
      nameError.value = validationMessages(error.detail, ['name'] as const).name
    }
    submitError.value = error instanceof Error ? error.message : 'Não foi possível criar a lista.'
    return
  }
  name.value = ''
  creating.value = false
  page.value = 1
  selectedId.value = created.id
  void queryClient.invalidateQueries({ queryKey: ['events', 'attendance', props.eventId, 'lists'] })
}

async function backToLists() {
  const previous = selectedId.value
  selectedId.value = null
  await nextTick()
  const action = document.getElementById('attendance-list-' + previous)
    ?? document.getElementById('attendance-lists-title')
  action?.focus()
}
</script>

<template>
  <AttendanceListView v-if="selectedId !== null" :key="selectedId" :event-id="eventId" :event-name="eventName"
    :list-id="selectedId" @back="backToLists" @busy="childBusy = $event" />
  <div v-else>
    <div class="mb-5 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h4 id="attendance-lists-title" tabindex="-1" class="font-semibold text-dj-ink">Listas de presença</h4>
        <p class="mt-1 text-sm leading-6 text-dj-muted">Crie uma lista para cada sessão, turma ou momento do evento.</p>
      </div>
      <Button v-if="data?.capabilities.can_create && !isError && !creating" type="button" label="Nova lista"
        icon="pi pi-plus" pt:root:class="rounded-xl" @click="showCreate" />
    </div>
    <form v-if="creating" class="mb-5 rounded-2xl border border-dj-border bg-dj-canvas p-5" novalidate
      :aria-busy="saving" @submit.prevent="createList">
      <FormField id="attendance-list-name" v-slot="{ controlProps }" label="Nome da lista" :error="nameError">
        <InputText v-bind="controlProps" v-model="name" :maxlength="120" :disabled="saving" required
          placeholder="Ex.: Treinamento — turma da manhã" pt:root:class="w-full rounded-xl" />
      </FormField>
      <Message v-if="submitError" severity="error" class="mt-3">{{ submitError }}</Message>
      <div class="mt-4 flex flex-wrap justify-end gap-2">
        <SecondaryButton type="button" label="Cancelar" outlined :disabled="saving" @click="creating = false" />
        <Button type="submit" :label="saving ? 'Criando…' : 'Criar lista'" :loading="saving" :disabled="saving" />
      </div>
    </form>
    <RequestState :loading="isPending" :failed="isError" :error="error" :empty="data?.items.length === 0"
      empty-title="A primeira lista começa aqui" empty-description="Crie uma lista para registrar os participantes deste evento."
      empty-icon="pi pi-users" not-found-message="Este evento não existe ou já foi excluído." @retry="refetch()">
      <ul class="space-y-3">
        <li v-for="list in data?.items" :key="list.id">
          <button :id="'attendance-list-' + list.id" type="button" :disabled="saving"
            class="group flex w-full items-center gap-4 rounded-2xl border border-dj-border bg-dj-surface p-5 text-left transition-colors hover:border-dj-brand focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-dj-brand"
            :aria-label="'Abrir lista ' + list.name" @click="selectedId = list.id">
            <span class="flex size-11 shrink-0 items-center justify-center rounded-xl bg-primary-50 text-dj-brand" aria-hidden="true"><i class="pi pi-users text-xl" /></span>
            <span class="min-w-0 flex-1">
              <span class="block break-words font-semibold text-dj-ink">{{ list.name }}</span>
              <span class="mt-1 block text-sm text-dj-muted">{{ list.total }} {{ list.total === 1 ? 'presença registrada' : 'presenças registradas' }}</span>
            </span>
            <i class="pi pi-arrow-right text-dj-brand" aria-hidden="true" />
          </button>
        </li>
      </ul>
      <ListPagination v-if="data" v-model:page="page" :per-page="perPage" :total="data.total" label="Páginas das listas de presença" />
    </RequestState>
  </div>
</template>
