<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import FormField from '@/shared/components/FormField.vue'
import Button from '@/volt/Button.vue'
import DatePicker from '@/volt/DatePicker.vue'
import InputText from '@/volt/InputText.vue'
import Message from '@/volt/Message.vue'
import SecondaryButton from '@/volt/SecondaryButton.vue'
import Textarea from '@/volt/Textarea.vue'
import { eventDate, eventDateTime } from '../dates'
import type { EventCreate, EventItem } from '../types'

const props = defineProps<{
  busy: boolean
  serverError: string
  fieldErrors: Record<keyof EventCreate, string>
  event?: EventItem
}>()
const emit = defineEmits<{
  submit: [payload: EventCreate]
  cancel: []
}>()
const fields = reactive({
  name: props.event?.name ?? '',
  description: props.event?.description ?? '',
  starts_at: eventDate(props.event?.starts_at ?? null),
  ends_at: eventDate(props.event?.ends_at ?? null),
})
const errors = reactive({ name: '', description: '', starts_at: '', ends_at: '' })
const formElement = ref<HTMLFormElement | null>(null)
const nameError = computed(() => errors.name || props.fieldErrors.name)
const descriptionError = computed(() => errors.description || props.fieldErrors.description)
const startsAtError = computed(() => errors.starts_at || props.fieldErrors.starts_at)
const endsAtError = computed(() => errors.ends_at || props.fieldErrors.ends_at)

function validDate(value: Date | null): value is Date {
  return value instanceof Date && Number.isFinite(value.getTime())
    && value.getFullYear() >= 1 && value.getFullYear() <= 9999
}

function submit() {
  if (props.busy) return
  const name = fields.name.trim()
  const description = fields.description.trim()
  errors.name = name.length < 3 || name.length > 120
    ? 'Informe um nome entre 3 e 120 caracteres.' : ''
  errors.description = description.length < 1 || description.length > 2000
    ? 'Informe uma descrição entre 1 e 2.000 caracteres.' : ''
  errors.starts_at = validDate(fields.starts_at) ? '' : 'Informe a data e a hora de início.'
  errors.ends_at = validDate(fields.ends_at) ? '' : 'Informe a data e a hora de fim.'
  if (validDate(fields.starts_at) && validDate(fields.ends_at)
    && fields.ends_at <= fields.starts_at) {
    errors.ends_at = 'O fim deve ser posterior ao início do evento.'
  }
  const invalidField = (Object.keys(errors) as (keyof EventCreate)[]).find(key => errors[key])
  if (invalidField) {
    const ids = { name: 'event-name', description: 'event-description', starts_at: 'event-start', ends_at: 'event-end' }
    formElement.value?.querySelector<HTMLElement>('#' + ids[invalidField])?.focus()
    return
  }
  if (!validDate(fields.starts_at) || !validDate(fields.ends_at)) return
  emit('submit', {
    name, description,
    starts_at: eventDateTime(fields.starts_at),
    ends_at: eventDateTime(fields.ends_at),
  })
}
</script>

<template>
  <form ref="formElement" novalidate :aria-busy="busy" @submit.prevent="submit">
    <p id="event-form-help" class="mb-5 flex items-start gap-3 rounded-xl bg-dj-canvas p-4 text-xs leading-5 text-dj-muted">
      <i class="pi pi-info-circle mt-0.5 text-dj-brand" aria-hidden="true" />
      <span>Preencha todos os campos e informe o horário local do evento. O status será definido automaticamente pelo período.</span>
    </p>

    <fieldset class="min-w-0 rounded-2xl border border-dj-border p-4 sm:p-5">
      <legend class="px-2 text-xs font-semibold tracking-wide text-dj-muted uppercase">Informações do evento</legend>
      <FormField id="event-name" v-slot="{ controlProps }" label="Título do evento" :error="nameError">
        <InputText v-bind="controlProps" v-model="fields.name" pt:root:class="w-full rounded-xl py-3"
          placeholder="Informe o título do evento" autofocus required :maxlength="120" :disabled="busy" />
      </FormField>
      <FormField id="event-description" v-slot="{ controlProps }" label="Descrição"
        :error="descriptionError" class="mt-4">
        <Textarea v-bind="controlProps" v-model="fields.description" :rows="4" auto-resize
          placeholder="Descreva o objetivo e as informações importantes do evento"
          required :maxlength="2000" :disabled="busy" pt:root:class="w-full rounded-xl" />
      </FormField>
      <p class="mt-2 text-right text-xs text-dj-muted tabular-nums">{{ fields.description.length }} / 2.000 caracteres</p>
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
        :loading="busy" :disabled="busy" pt:root:class="rounded-xl px-5 py-3" />
    </div>
  </form>
</template>
