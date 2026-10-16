<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { ApiError } from '@/shared/api/client'
import { validationMessages } from '@/shared/api/validation'
import FormField from '@/shared/components/FormField.vue'
import Button from '@/volt/Button.vue'
import DatePicker from '@/volt/DatePicker.vue'
import InputText from '@/volt/InputText.vue'
import Message from '@/volt/Message.vue'
import SecondaryButton from '@/volt/SecondaryButton.vue'
import Select from '@/volt/Select.vue'
import Textarea from '@/volt/Textarea.vue'
import { eventDate, eventDateTime } from '../dates'
import { eventsApi } from '../api'
import type { EventCreate, EventItem, EventType, EventTypes } from '../types'
import EventTypeDeleteDialog from './EventTypeDeleteDialog.vue'

const props = defineProps<{
  busy: boolean
  serverError: string
  fieldErrors: Record<keyof EventCreate, string>
  event?: EventItem
}>()
const emit = defineEmits<{
  submit: [payload: EventCreate]
  cancel: []
  busy: [value: boolean]
}>()
const fields = reactive({
  name: props.event?.name ?? '',
  description: props.event?.description ?? '',
  event_type_id: props.event?.event_type_id ?? null,
  instructor: props.event?.instructor ?? '',
  syllabus: props.event?.syllabus ?? '',
  starts_at: eventDate(props.event?.starts_at ?? null),
  ends_at: eventDate(props.event?.ends_at ?? null),
})
const errors = reactive({ name: '', description: '', event_type_id: '', instructor: '', syllabus: '', starts_at: '', ends_at: '' })
const formElement = ref<HTMLFormElement | null>(null)
const nameError = computed(() => errors.name || props.fieldErrors.name)
const descriptionError = computed(() => errors.description || props.fieldErrors.description)
const startsAtError = computed(() => errors.starts_at || props.fieldErrors.starts_at)
const endsAtError = computed(() => errors.ends_at || props.fieldErrors.ends_at)
const typeError = computed(() => errors.event_type_id || props.fieldErrors.event_type_id)
const instructorError = computed(() => errors.instructor || props.fieldErrors.instructor)
const syllabusError = computed(() => errors.syllabus || props.fieldErrors.syllabus)
const addingType = ref(false)
const typeName = ref('')
const typeNameError = ref('')
const typeSaveError = ref('')
const pendingType = ref<EventType | null>(null)
const typeSelectVersion = ref(0)
const queryClient = useQueryClient()
const { data: types, isPending: typesLoading, isError: typesFailed, refetch: refetchTypes } = useQuery({
  queryKey: ['events', 'types'],
  queryFn: () => eventsApi.types(),
  retry: false,
  refetchOnWindowFocus: false,
  refetchOnReconnect: false,
})
const { mutateAsync: createType, isPending: typeSaving } = useMutation({
  mutationFn: (name: string) => eventsApi.createType(name),
  retry: false,
})
const typeDescription = computed(() => [
  typeError.value ? 'event-type-error' : '',
  types.value?.can_delete ? 'event-type-keyboard-help' : '',
].filter(Boolean).join(' ') || undefined)
watch(() => typeSaving.value || pendingType.value !== null, value => emit('busy', value), { immediate: true, flush: 'sync' })
watch(types, value => {
  if (value && fields.event_type_id !== null && !value.items.some(item => item.id === fields.event_type_id)) {
    fields.event_type_id = null
  }
})
onBeforeUnmount(() => emit('busy', false))

function requestTypeDeletion(eventType: EventType) {
  if (props.busy || typeSaving.value || pendingType.value || addingType.value || !types.value?.can_delete) return
  pendingType.value = { ...eventType }
  // Encerra o overlay do Select Volt antes de abrir a confirmação, preservando o v-model.
  typeSelectVersion.value += 1
}

function typeKeydown(event: KeyboardEvent) {
  if (event.key !== 'Delete' || !event.altKey || !(event.target instanceof HTMLElement)
    || event.target.getAttribute('role') !== 'combobox') return
  const selected = types.value?.items.find(item => item.id === fields.event_type_id)
  if (selected) {
    event.preventDefault()
    event.stopPropagation()
    requestTypeDeletion(selected)
  }
}

async function typeDeleteClosed(deleted: boolean) {
  const previous = pendingType.value
  if (!previous) return
  if (deleted) {
    queryClient.setQueryData<EventTypes>(['events', 'types'], current => current && ({
      ...current, items: current.items.filter(item => item.id !== previous.id),
    }))
    if (fields.event_type_id === previous.id) fields.event_type_id = null
    errors.event_type_id = ''
  }
  pendingType.value = null
  // Reconcilia também cancelamentos e respostas incertas, sem repetir o DELETE.
  void queryClient.invalidateQueries({ queryKey: ['events', 'types'], exact: true })
  await nextTick()
  document.getElementById('event-type')?.focus()
}

async function toggleTypeForm(open: boolean) {
  if (props.busy) return
  addingType.value = open
  typeName.value = ''
  typeNameError.value = ''
  typeSaveError.value = ''
  await nextTick()
  document.getElementById(open ? 'event-type-name' : 'event-type-add')?.focus()
}

async function saveType() {
  if (props.busy || typeSaving.value || !types.value?.can_create) return
  const name = typeName.value.trim()
  typeNameError.value = name.length < 1 || name.length > 80 ? 'Informe um nome entre 1 e 80 caracteres.' : ''
  typeSaveError.value = ''
  if (typeNameError.value) {
    document.getElementById('event-type-name')?.focus()
    return
  }
  try {
    const created = await createType(name)
    queryClient.setQueryData<EventTypes>(['events', 'types'], current => ({
      items: [...(current?.items ?? []).filter(item => item.id !== created.id), created]
        .sort((a, b) => a.name.localeCompare(b.name, 'pt-BR')),
      can_create: current?.can_create ?? false,
      can_delete: current?.can_delete ?? false,
    }))
    fields.event_type_id = created.id
    errors.event_type_id = ''
    addingType.value = false
    typeName.value = ''
    await nextTick()
    document.getElementById('event-type')?.focus()
  } catch (error) {
    if (error instanceof ApiError && error.status === 422) {
      typeNameError.value = validationMessages(error.detail, ['name'] as const).name
    }
    typeSaveError.value = error instanceof Error ? error.message : 'Não foi possível salvar o tipo de evento.'
  }
}

function validDate(value: Date | null): value is Date {
  return value instanceof Date && Number.isFinite(value.getTime())
    && value.getFullYear() >= 1 && value.getFullYear() <= 9999
}

function submit() {
  if (props.busy || typeSaving.value || addingType.value || typesLoading.value || typesFailed.value) return
  const name = fields.name.trim()
  const description = fields.description.trim()
  const instructor = fields.instructor.trim()
  const syllabus = fields.syllabus.trim()
  errors.name = name.length < 3 || name.length > 120
    ? 'Informe um nome entre 3 e 120 caracteres.' : ''
  errors.description = description.length < 1 || description.length > 2000
    ? 'Informe uma descrição entre 1 e 2.000 caracteres.' : ''
  errors.event_type_id = fields.event_type_id !== null && types.value?.items.some(item => item.id === fields.event_type_id)
    ? '' : 'Selecione um tipo de evento cadastrado.'
  errors.instructor = instructor.length > 200 ? 'Use até 200 caracteres para o instrutor.' : ''
  errors.syllabus = syllabus.length > 4000 ? 'Use até 4.000 caracteres para o conteúdo programático.' : ''
  errors.starts_at = validDate(fields.starts_at) ? '' : 'Informe a data e a hora de início.'
  errors.ends_at = validDate(fields.ends_at) ? '' : 'Informe a data e a hora de fim.'
  if (validDate(fields.starts_at) && validDate(fields.ends_at)
    && fields.ends_at <= fields.starts_at) {
    errors.ends_at = 'O fim deve ser posterior ao início do evento.'
  }
  const invalidField = (Object.keys(errors) as (keyof EventCreate)[]).find(key => errors[key])
  if (invalidField) {
    const ids = { name: 'event-name', description: 'event-description', event_type_id: 'event-type', instructor: 'event-instructor', syllabus: 'event-syllabus', starts_at: 'event-start', ends_at: 'event-end' }
    formElement.value?.querySelector<HTMLElement>('#' + ids[invalidField])?.focus()
    return
  }
  if (!validDate(fields.starts_at) || !validDate(fields.ends_at) || fields.event_type_id === null) return
  emit('submit', {
    name, description,
    event_type_id: fields.event_type_id,
    instructor: instructor || null,
    syllabus: syllabus || null,
    starts_at: eventDateTime(fields.starts_at),
    ends_at: eventDateTime(fields.ends_at),
  })
}
</script>

<template>
  <form ref="formElement" novalidate :aria-busy="busy" @submit.prevent="submit">
    <p id="event-form-help" class="mb-5 flex items-start gap-3 rounded-xl bg-dj-canvas p-4 text-xs leading-5 text-dj-muted">
      <i class="pi pi-info-circle mt-0.5 text-dj-brand" aria-hidden="true" />
      <span>Informe o título, o tipo, a descrição e o horário local do evento. Instrutor e conteúdo programático são opcionais. O status será definido automaticamente pelo período.</span>
    </p>

    <fieldset class="min-w-0 rounded-2xl border border-dj-border p-4 sm:p-5">
      <legend class="px-2 text-xs font-semibold tracking-wide text-dj-muted uppercase">Informações do evento</legend>
      <FormField id="event-name" v-slot="{ controlProps }" label="Título do evento" :error="nameError">
        <InputText v-bind="controlProps" v-model="fields.name" pt:root:class="w-full rounded-xl py-3"
          placeholder="Informe o título do evento" autofocus required :maxlength="120" :disabled="busy" />
      </FormField>
      <div class="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <FormField id="event-type" v-slot="{ controlProps }" label="Tipo de evento" :error="typeError">
          <div class="flex items-start gap-2">
            <Select :key="typeSelectVersion" v-model="fields.event_type_id" input-id="event-type" :options="types?.items ?? []"
              option-label="name" option-value="id" filter :loading="typesLoading"
              placeholder="Selecione um tipo" empty-message="Nenhum tipo cadastrado" empty-filter-message="Nenhum tipo encontrado"
              :invalid="controlProps.invalid" aria-label="Tipo de evento"
              :pt:label:aria-describedby="typeDescription" pt:label:aria-required="true"
              :pt:label:aria-keyshortcuts="types?.can_delete ? 'Alt+Delete' : undefined"
              :disabled="busy || addingType || typesLoading || typesFailed" class="min-w-0 flex-1" pt:root:class="rounded-xl"
              @keydown="typeKeydown">
              <template #option="{ option }">
                <div class="flex w-full min-w-0 items-center justify-between gap-3">
                  <span class="min-w-0 whitespace-normal break-words">{{ option.name }}</span>
                  <SecondaryButton v-if="types?.can_delete" type="button" icon="pi pi-trash" text :tabindex="-1"
                    :aria-label="'Excluir tipo ' + option.name" :title="'Excluir tipo ' + option.name" :disabled="busy"
                    pt:root:class="size-9 shrink-0 rounded-xl text-dj-danger enabled:hover:bg-dj-danger-soft"
                    @mousedown.stop.prevent @click.stop="requestTypeDeletion(option)" @keydown.enter.stop @keydown.space.stop />
                </div>
              </template>
            </Select>
            <SecondaryButton v-if="types?.can_create" id="event-type-add" type="button" icon="pi pi-plus" outlined
              aria-label="Adicionar tipo de evento" :aria-expanded="addingType" aria-controls="event-type-editor"
              :disabled="busy || typesLoading || typesFailed || addingType" pt:root:class="shrink-0 rounded-xl"
              @click="toggleTypeForm(true)" />
          </div>
          <p v-if="!typesLoading && !typesFailed && !types?.items.length" class="mt-2 text-xs text-dj-muted">Use o botão + para cadastrar o primeiro tipo.</p>
          <p v-if="types?.can_delete" id="event-type-keyboard-help" class="mt-2 text-xs leading-5 text-dj-muted">
            Para excluir pelo teclado, selecione um tipo e pressione Alt+Delete.
          </p>
        </FormField>
        <FormField id="event-instructor" v-slot="{ controlProps }" label="Instrutor (opcional)" :error="instructorError">
          <InputText v-bind="controlProps" v-model="fields.instructor" placeholder="Nome do instrutor"
            :maxlength="200" :disabled="busy" pt:root:class="w-full rounded-xl" />
        </FormField>
      </div>
      <Message v-if="typesFailed" severity="error" class="mt-3">
        Não foi possível carregar os tipos de evento.
        <SecondaryButton type="button" label="Tentar novamente" text :disabled="busy" @click="refetchTypes()" />
      </Message>
      <section v-if="addingType" id="event-type-editor" aria-labelledby="event-type-editor-title"
        class="mt-4 rounded-xl border border-dj-border bg-dj-canvas p-4" :aria-busy="typeSaving">
        <h4 id="event-type-editor-title" class="mb-3 text-sm font-semibold text-dj-ink">Adicionar tipo de evento</h4>
        <FormField id="event-type-name" v-slot="{ controlProps }" label="Nome do tipo" :error="typeNameError">
          <InputText v-bind="controlProps" v-model="typeName" :maxlength="80" :disabled="busy"
            placeholder="Informe o novo tipo" pt:root:class="w-full rounded-xl" @keydown.enter.prevent.stop="saveType" />
        </FormField>
        <p class="mt-2 text-xs leading-5 text-dj-muted">O tipo ficará disponível para outros eventos, mesmo se você cancelar este cadastro. Nomes já cadastrados serão reutilizados.</p>
        <Message v-if="typeSaveError" severity="error" class="mt-3">{{ typeSaveError }}</Message>
        <div class="mt-3 flex flex-wrap justify-end gap-2">
          <SecondaryButton type="button" label="Cancelar tipo" outlined :disabled="busy" @click="toggleTypeForm(false)" />
          <Button type="button" :label="typeSaving ? 'Salvando tipo…' : 'Salvar tipo'" icon="pi pi-check"
            :loading="typeSaving" :disabled="busy" @click="saveType" />
        </div>
      </section>
      <FormField id="event-description" v-slot="{ controlProps }" label="Descrição"
        :error="descriptionError" class="mt-4">
        <Textarea v-bind="controlProps" v-model="fields.description" :rows="4" auto-resize
          placeholder="Descreva o objetivo e as informações importantes do evento"
          required :maxlength="2000" :disabled="busy" pt:root:class="w-full rounded-xl" />
      </FormField>
      <p class="mt-2 text-right text-xs text-dj-muted tabular-nums">{{ fields.description.length }} / 2.000 caracteres</p>
      <FormField id="event-syllabus" v-slot="{ controlProps }" label="Conteúdo programático (opcional)"
        :error="syllabusError" class="mt-4">
        <Textarea v-bind="controlProps" v-model="fields.syllabus" :rows="4" auto-resize
          placeholder="Informe os assuntos e atividades previstos para o evento"
          :maxlength="4000" :disabled="busy" pt:root:class="w-full rounded-xl" />
      </FormField>
      <p class="mt-2 text-right text-xs text-dj-muted tabular-nums">{{ fields.syllabus.length }} / 4.000 caracteres</p>
    </fieldset>

    <fieldset class="mt-5 min-w-0 rounded-2xl border border-dj-border p-4 sm:p-5">
      <legend class="px-2 text-xs font-semibold tracking-wide text-dj-muted uppercase">Período de realização</legend>
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <FormField id="event-start" v-slot="{ controlProps }" label="Data e hora de início" :error="startsAtError">
          <DatePicker v-model="fields.starts_at" input-id="event-start" :invalid="controlProps.invalid"
            :input-props="{ 'aria-describedby': controlProps['aria-describedby'], 'aria-invalid': controlProps['aria-invalid'] }"
            date-format="dd/mm/yy" show-time hour-format="24" show-icon fluid input-class="rounded-xl py-3"
            pt:dropdown:class="rounded-e-xl"
            :manual-input="false" :disabled="busy" required class="w-full" />
        </FormField>
        <FormField id="event-end" v-slot="{ controlProps }" label="Data e hora de fim" :error="endsAtError">
          <DatePicker v-model="fields.ends_at" input-id="event-end" :invalid="controlProps.invalid"
            :input-props="{ 'aria-describedby': controlProps['aria-describedby'], 'aria-invalid': controlProps['aria-invalid'] }"
            date-format="dd/mm/yy" show-time hour-format="24" show-icon fluid input-class="rounded-xl py-3"
            pt:dropdown:class="rounded-e-xl"
            :manual-input="false" :min-date="fields.starts_at ?? undefined"
            :disabled="busy" required class="w-full" />
        </FormField>
      </div>
    </fieldset>

    <Message v-if="serverError" severity="error" class="mt-4">
      {{ serverError }}
    </Message>
    <div class="mt-6 flex flex-wrap justify-end gap-3 border-t border-dj-border pt-5">
      <SecondaryButton type="button" label="Cancelar" outlined :disabled="busy" pt:root:class="rounded-xl px-5 py-3" @click="emit('cancel')" />
      <Button type="submit" :label="busy ? 'Salvando…' : event ? 'Salvar alterações' : 'Criar evento'"
        :loading="busy" :disabled="busy || addingType || typesLoading || typesFailed" pt:root:class="rounded-xl px-5 py-3" />
    </div>
  </form>
  <EventTypeDeleteDialog v-if="pendingType" :event-type="pendingType" :allowed="types?.can_delete ?? false" @closed="typeDeleteClosed" />
</template>
